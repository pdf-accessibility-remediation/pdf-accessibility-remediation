"""intake.py: get an untagged PDF ready for the pipeline (local tools only: no model, no cost).

    python3 intake.py <original.pdf> <out_dir> [--plan-only]

Sponsor checklist steps: 1.2 (is the text layer usable?), 2.1 and 3.1 (OCR at 300 dpi or more), 3.6 (characters the
OCR font lacks), 3.7 (language), 10.3/10.4 (page image + invisible Unicode text), 10.5 (structure tree and tags).

What it does, in order, and only where needed:
  1. triage   every page: visible text, image only (no text, an image covering >= 25%: a scan or a picture page),
              an existing invisible OCR layer, or blank. Text operators that draw no character (an empty text object
              over a scan) do not count as text. Every text page: private-use characters (3.6), text outside the
              visible page area, and word breaks that are only gaps with no space character (3.4: a note; narrow
              gaps, under 19% of the type size, are a CHECK when they average 10 or more per text page) are counted
  2. 1.2 test OCR up to 20 scorable pages that have text and compare with their text layer (books with 40+ text
              pages: not from the first 5% of them, at least 6, which is front matter in small type; suspicious
              pages may come from anywhere). Page score = the lower of the in-order and any-order character
              error; book score = median of the page scores:
              <= 5% usable · > 15% unusable · in between: a person decides (the book goes on, with a CHECK).
              Only text inside the visible page area (CropBox) is compared. Pages whose images cover >= 25%, under 300 characters, or CJK text without a CJK OCR pack are not
              scored (replaced by the next scorable page further on); fewer than 5 scored: "not enough pages scored" (CHECK).
              Math pages (a math font and 10+ math symbols) are not scored either, nor a page where OCR read the letters
              but not the diacritics the text layer has (listed: a note on born-digital text, a CHECK on an OCR layer). Underscores (fill-in rules) are ignored.
              An "unusable" text layer from a born-digital producer or with math stops for a person, without
              suggesting FORCE_OCR
  3. OCR      OCRmyPDF + Tesseract, only on pages with no text (--mode skip: pages with text are copied untouched).
              An image-only page whose OCR text is not text-like (a cover, a Part-opener picture) gets no OCR text:
              it is left for the figure step.
              If the 1.2 test says the text layer is unusable, the book STOPS (flagged) unless FORCE_OCR=1 is set;
              then every page is OCR'd with --mode force (page images + new invisible text; the old text is replaced).
  4. tag      OpenDataLoader adds a tag tree to a still-untagged file (--format tagged-pdf). A whole-page scan image
              on an OCR'd page is then marked as decoration (it is the page, not a figure: checklist 5.1)
  5. checks   after each step: page appearance and text unchanged where nothing should change; a tag tree exists
              and covers the text; bookmarks, links and page labels kept. A failed check stops the book.

Never: writing to the original; --mode force without FORCE_OCR=1; a general AI model reading or "cleaning up" text.
A tagged PDF is left alone (status "skipped"). A placeholder tag tree (no text-bearing element: only Document, Part
and the like, or only Figure tags) is not a tag tree: it is recorded in intake.json (with any publisher alt text), removed
from intake's working copy (never the original), and the book is handled as untagged. Output in <out_dir>: intake.json always; intake.pdf when anything
changed (it is then the file the rest of the pipeline works on, and it is kept so FROM= reruns stay identical).

Environment: FORCE_OCR=1 · OCR=off (no OCR: image-only pages are only listed) · OCR_LANG=eng+jpn (Tesseract
languages for OCR; by default eng. CJK text on pages to be OCR'd stops the book unless OCR_LANG names a CJK pack, for
Chinese, Japanese and Korean alike; a trial on up to 3 of those pages suggests a _vert pack when the text looks
vertical. The scripts found (kana jpn, hangul kor, Vietnamese vie) choose extra packs only for the 1.2 sample pages).
Needs, only when used: Tesseract and OCRmyPDF 17 (brew install ocrmypdf tesseract-lang) for untagged books; Java 11+
and the opendataloader-pdf package for auto-tagging. Exit codes: 0 done or nothing to do · 3 flagged (stopped, see
intake.json) · 1 error.
"""
import sys, os, re, json, time, shutil, hashlib, subprocess, tempfile, unicodedata, difflib, collections, datetime, statistics, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import support
import pikepdf, pypdfium2 as pdfium, pypdfium2.raw as pdfium_raw

SCHEMA = 'intake/0.2'
CER_OK, CER_BAD = 0.05, 0.15              # checklist 1.2 thresholds on the book score (starting point; tune on real scores)
SAMPLE, EXTRA = 20, 4                      # pages for the 1.2 test: up to 20 scored, spread evenly, plus suspicious pages
MIN_SCORED = 5                             # fewer scored pages than this: "not enough pages scored" (CHECK)
SCORE_MIN_CHARS = 300                      # a sample page with fewer text-layer characters (after normalising) is not scored
SCORE_IMAGE_COVER = 0.25                   # a sample page whose images together cover this share of the page is not scored
CJK_CHARS, CJK_SHARE = 20, 0.10            # a sample page with this many CJK characters or this share of its letters is
                                           #   not scored when the OCR language has no CJK pack
IMAGE_ONLY_COVER = 0.25                    # triage: no text and images covering this share of the page together = image-only
SCAN_MIN_COVER = 0.05                      # images smaller than this share of the page are ignored for the scan resolution
OCR_LAYER_COVER = 0.5                      # triage: invisible text over an image covering this share = existing OCR layer
OCR_DPI = 300                              # checklist 2.1: rasterise at 300–400 dpi
TEXTLIKE_WORDS, TEXTLIKE_SHARE = 15, 0.6   # OCR text on an image-only page is kept only above both
SPACING_LOW = 0.85                         # text-layer words / OCR words below this: words run together (3.4)
PUA_CHECK = 100                            # more private-use characters than this in the text layer: CHECK (3.6)
OUTSIDE_MIN_CHARS = 3                      # a page with at least this many characters outside the visible area (CropBox)
GAP_SHARE, GAP_MIN_BREAKS = 0.5, 20        # word breaks (3.4): a page with at least 20 breaks, more than half of them only
                                           #   gaps between letters (no space character), relies on gaps (a note, not a CHECK)
NARROW_GAP = 0.19                          # a gap-only word break narrower than 0.19 of the type size (font size x text matrix),
                                           #   measured between advance widths (what a text extractor sees), is narrow. Calibrated:
                                           #   Acrobat ran words together at 0.149-0.183 on bringing PDF 86 and spaced 0.198 on
                                           #   9798880703272 PDF 9 correctly
NARROW_BOOK_RATE = 10                      # narrow breaks per text page, averaged over the book: at or above, a CHECK; below, a note
CJK_PROBE_LANGS = 'chi_tra+chi_sim+jpn+kor'  # before OCR, each planned page is read once with these Tesseract packs:
CJK_PROBE_MIN, CJK_PROBE_CONF = 10, 60     #   10 or more CJK characters at 60% confidence or more = the page holds CJK text.
                                           #   Calibrated: sojourners' glossary 47-229, every cover and Part opener 0-1
JUNK_SHARE, JUNK_MIN_TOKENS = 0.05, 30     # after OCR: a page with 30+ tokens, 5% or more of them junk (symbols such as # @ (R),
                                           #   or capital clusters without vowels like "MBH"), is flagged. Calibrated: clean
                                           #   OCR 0%; sojourners' glossary 3.8-10.9% with chi_tra+eng, 5.7-20.5% with eng only
JUNK_SYMBOLS = set('#@®©&§¶|\\^~{}<>¤¢£¥€°±×÷=+*_™')
TILE_DPI, TILE_PX, TILE_MAX = 300, 75, 50  # auto-tag appearance check, second look for a page over NEAR at 72 dpi: rendered at
                                           #   300 dpi in quarter-inch tiles; it passes when no tile has more than 50 changed pixels
FRONT_SKIP_FROM = 40                       # books with at least this many text pages: the evenly spread 1.2 sample
FRONT_SKIP_SHARE, FRONT_SKIP_MIN = 0.05, 6 #   skips the first 5% of text pages (at least 6): front matter in small type
PUA_NAMED = [(0xF730, 0xF739, 'old-style digits 0–9 (Adobe)'),      # known private-use ranges in legacy fonts
             (0xF761, 0xF77A, 'small capitals a–z (Adobe)')]
TXT_OPS = {'Tj', 'TJ', "'", '"'}
TEXT_BEARING = {'/P', '/H', '/H1', '/H2', '/H3', '/H4', '/H5', '/H6', '/L', '/LI', '/LBody', '/Lbl', '/Table', '/TR', '/TH',
                '/TD', '/THead', '/TBody', '/TFoot', '/Span', '/Quote', '/BlockQuote', '/Note', '/Reference', '/BibEntry',
                '/Code', '/Caption', '/TOC', '/TOCI', '/Index', '/Title', '/Formula', '/Link', '/Em', '/Strong'}
                                           # a tag tree with none of these (after RoleMap) is a placeholder: only grouping
                                           #   (Document, Part, Sect, Div, Art …) or Figure tags. Counted on the sponsors' 148:
                                           #   25 of 59 tagged books (Document + one Part per page; Prince's Figure-only trees)
PUBLISHER_PLACEHOLDER_ALT = re.compile(r'(?i)\s*(decorative element|image( \d+)?|figure( \d+)?|graphic|picture|photo|untitled)\s*')
                                           # alt text on an existing Figure that says nothing (Prince writes "Decorative element")
OSD_SCRIPTS = {'Japanese': 'kana', 'Hiragana': 'kana', 'Katakana': 'kana', 'Korean': 'hangul', 'Hangul': 'hangul',
               'Han': 'han', 'HanS': 'han', 'HanT': 'han'}   # Tesseract OSD's script names (5.5.3 says "Korean", not "Hangul")
VERT_PROBE_LANGS = 'jpn_vert+chi_tra_vert+chi_sim_vert+kor_vert'   # vertical-text trial on a few CJK pages to be OCR'd:
VERT_SAMPLE, VERT_GAIN = 3, 1.5            #   when the _vert packs read 1.5x the confident CJK characters of the horizontal
                                           #   packs on most of up to 3 pages, the text is likely vertical
VIET_LETTERS = set(chr(o) for o in range(0x1EA0, 0x1EFA)) | set('ĂăĐđƠơƯư')
VIET_MIN = 50                              # this many Vietnamese letters in the sampled text layer: vie reads the 1.2 sample pages
MATH_FONT = re.compile(r'(?i)CMMI|CMSY|CMEX|CMBSY|MSAM|MSBM|EUFM|EUSM|RSFS|STIX|Symbol|MT ?Extra|Math|esint|wasy')
MATH_SYMBOLS, MATH_SYMBOLS_NO_FONT = 10, 20  # 1.2 test: a sample page with a math font and 10+ math symbols or Greek letters in
                                           #   its text layer (20+ without a math font) is not scored: OCR cannot read math
MARKS_MISSED, MARKS_MIN = 1.5, 20          # 1.2 test: the text layer has 20+ letters with diacritics and 1.5x as many as OCR
                                           #   read, and the score without diacritics is usable: OCR missed the marks, the
                                           #   page is not scored (a layer missing marks that OCR read still scores badly).
                                           #   A note on born-digital text; a CHECK on an existing OCR layer
OCRL_SAMPLE = 10                           # existing OCR layer on scanned pages: up to 10 sample pages, read again by Tesseract's
SCRIPT_MODELS = {'latin': 'script/Latin', 'kana': 'script/Japanese_vert+script/Japanese',      #   script model for the
                 'hangul': 'script/Hangul_vert+script/Hangul',                                 #   layer's script (a different
                 'han': 'script/HanS_vert+script/HanS+script/HanT_vert+script/HanT'}           #   model from the book packs)
MARKED_VOWELS, MARKS_LAYER_SHARE = 5, 0.10  # OCR layer: the script model reads 5+ marked vowels a page on average and the layer
                                           #   has under 10% as many, counted on pages whose letters agree (error without the
                                           #   marks 15% or less): the page images show diacritics the layer lacks (CHECK); such a
                                           #   page is then judged on its letters.
                                           #   Calibrated on henrycukim (about 20 a page, layer 0) and gelfand/liouville
                                           #   (1-2 stray marks a page, mostly on consonants)
SPREAD_ASPECT, SPREAD_BAND = 1.15, (0.40, 0.60)   # two printed pages per PDF page: as displayed, width >= 1.15 x height,
GUTTER_INK, GUTTER_MIN, SPREAD_SIDE = 0.10, 0.006, 0.25   # a gutter in the middle 40-60% (columns under 10% of the median
                                           #   ink, 0.6%+ of the width) and 25%+ of the ink on each side; a landscape page of
                                           #   the same size next to one counts too (a chapter end leaves a half blank).
                                           #   Calibrated: mohr 16+1 of 17, reynolds-magazines 10 of 10, 0 in the 148 and the 30
BORN_DIGITAL = re.compile(r'(?i)pdftex|xetex|luatex|prince|microsoft|adobe pdf library|indesign')
                                           # producers that write text, not scan it: an "unusable" verdict on them is no
                                           #   reason to suggest FORCE_OCR

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)
def now(): return datetime.datetime.now().isoformat(timespec='seconds')

# ------------------------------------------------------------------ tools (checked only when the plan needs them)
def tool_versions():
    v = {}
    try: v['tesseract'] = run(['tesseract', '--version']).stdout.split('\n')[0].split()[-1]
    except Exception: v['tesseract'] = None
    try:
        out = run(['tesseract', '--list-langs']).stdout.split('\n')[1:]
        v['tesseract_langs'] = sorted(x.strip() for x in out if x.strip())
    except Exception: v['tesseract_langs'] = []
    try: v['ocrmypdf'] = run(['ocrmypdf', '--version']).stdout.strip() or None
    except Exception: v['ocrmypdf'] = None
    try:
        j = run(['java', '-version']); m = re.search(r'version "(\d+)(?:\.(\d+))?', j.stderr + j.stdout)
        v['java'] = (int(m.group(2)) if m and m.group(1) == '1' else int(m.group(1))) if m else None
    except Exception: v['java'] = None
    try:
        from importlib.metadata import version
        v['opendataloader_pdf'] = version('opendataloader-pdf')
    except Exception: v['opendataloader_pdf'] = None
    return v
INSTALL = {'tesseract': 'Tesseract is not installed: brew install tesseract tesseract-lang',
           'ocrmypdf': 'OCRmyPDF 17 is not installed: brew install ocrmypdf',
           'java': 'Java 11 or later is needed for auto-tagging (for example brew install --cask temurin)',
           'opendataloader_pdf': 'opendataloader-pdf is not installed: from pipeline/, python3 -m pip install -r requirements.txt'}

# ------------------------------------------------------------------ 1. triage
def _mul(a, b):
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2],
            a[2] * b[1] + a[3] * b[3], a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
def visible_rect(page):
    """The visible page area (CropBox within the MediaBox), in PDF user space: x0, y0, x1, y1."""
    mb = [float(x) for x in page.mediabox]; cb = [float(x) for x in page.cropbox]
    return max(mb[0], cb[0]), max(mb[1], cb[1]), min(mb[2], cb[2]), min(mb[3], cb[3])
def visible_cover(ctm, vr):
    """Share of the visible area covered by the unit square drawn with this matrix (an image), clipped to that area."""
    pts = [(ctm[0] * u + ctm[2] * v + ctm[4], ctm[1] * u + ctm[3] * v + ctm[5]) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1))]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts); y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    area = max(vr[2] - vr[0], 0) * max(vr[3] - vr[1], 0)
    inside = max(min(x1, vr[2]) - max(x0, vr[0]), 0) * max(min(y1, vr[3]) - max(y0, vr[1]), 0)
    return min(inside / max(area, 1), 1.0)
def page_inventory(page, text_drawn=True):
    """Visible and invisible text operators, and the images drawn (share of the visible page area covered, effective dpi).
    text_drawn=False: the page's text operators draw no character (empty_text_pages), so the page is judged by its
    images alone."""
    vr = visible_rect(page)
    out = {'visible': 0, 'invisible': 0, 'images': [], 'fonts': set()}
    def walk(owner, res, ctm, depth):
        try: ops = pikepdf.parse_content_stream(owner)
        except Exception: return
        try: out['fonts'].update(str(f.get('/BaseFont') or '') for f in ((res or {}).get('/Font') or {}).values())
        except Exception: pass
        stack, tr = [], 0
        for a, o in ops:
            o = str(o)
            if o == 'q': stack.append((ctm, tr))
            elif o == 'Q' and stack: ctm, tr = stack.pop()
            elif o == 'cm': ctm = _mul([float(x) for x in a], ctm)
            elif o == 'Tr': tr = int(a[0])
            elif o in TXT_OPS: out['invisible' if tr == 3 else 'visible'] += 1
            elif o == 'Do' and res is not None:
                x = (res.get('/XObject') or {}).get(a[0])
                if x is None: continue
                st = x.get('/Subtype')
                if st == '/Image':
                    w, h = abs(ctm[0]) + abs(ctm[2]), abs(ctm[1]) + abs(ctm[3])
                    cover = visible_cover(ctm, vr)
                    dpi = int(x.get('/Width', 0)) / max(w / 72, 1e-6) if w else 0
                    out['images'].append({'cover': round(cover, 3), 'dpi': round(dpi), 'bits': int(x.get('/BitsPerComponent', 8) or 8)})
                elif st == '/Form' and depth < 4:
                    m = [float(v) for v in x.get('/Matrix', [1, 0, 0, 1, 0, 0])]
                    walk(x, x.get('/Resources', res), _mul(m, ctm), depth + 1)
    walk(page, page.obj.get('/Resources'), [1, 0, 0, 1, 0, 0], 0)
    big = [i for i in out['images'] if i['cover'] >= OCR_LAYER_COVER]
    total = min(sum(i['cover'] for i in out['images']), 1.0)
    vis, inv = (out['visible'], out['invisible']) if text_drawn else (0, 0)
    if vis: kind = 'text'
    elif inv and big: kind = 'ocr-layer'
    elif inv: kind = 'text'
    elif total >= IMAGE_ONLY_COVER: kind = 'image-only'
    else: kind = 'blank'
    scan = [i for i in out['images'] if i['cover'] >= SCAN_MIN_COVER] if kind == 'image-only' else big
    return {'kind': kind, 'visible_ops': out['visible'], 'invisible_ops': out['invisible'],
            'scan_dpi': min(i['dpi'] for i in scan) if scan else None,
            'max_cover': max((i['cover'] for i in out['images']), default=0),
            'image_cover': round(total, 3), 'math_fonts': any(MATH_FONT.search(f) for f in out['fonts'])}
def empty_text_pages(path, inv):
    """Pages triaged as text (or an OCR layer) whose text operators draw no character: PDFium finds nothing but white
    space and invisible marks on them (e.g. an empty text object over a scan), and neither does pdfplumber (PDFium misses
    most of Acrobat's hidden vertical OCR text, Identity-V: such a page is not empty). Checklist 1.2, 2.1."""
    doc = pdfium.PdfDocument(path)
    try: cand = [i for i, x in enumerate(inv, 1) if x['kind'] in ('text', 'ocr-layer') and not INVISIBLE.sub('', doc[i - 1].get_textpage().get_text_range())]
    finally: doc.close()
    if not cand: return []
    from lib import plumb_fix  # noqa: F401  (patches pdfplumber; import before it)
    import pdfplumber
    with pdfplumber.open(path) as pl:
        return [i for i in cand if not any(c['text'].strip() for c in pl.pages[i - 1].chars)]
def strip_empty_text(path, pages):
    """On intake's own working copy only: remove the text objects (BT … ET) from pages whose text draws no character, so
    OCRmyPDF's --mode skip, which passes over any page with a text object, OCRs them. Returns the pages changed and the
    pages that still have text operators (inside form XObjects: left as they are). The caller checks nothing visible moved."""
    done, left = [], []
    with pikepdf.open(path, allow_overwriting_input=True) as p:
        for n in pages:
            pg = p.pages[n - 1]; ops = list(pikepdf.parse_content_stream(pg)); keep, inside = [], False
            for a, o in ops:
                if str(o) == 'BT': inside = True; continue
                if str(o) == 'ET': inside = False; continue
                if not inside: keep.append((a, o))
            if len(keep) != len(ops):
                pg.obj.Contents = p.make_stream(pikepdf.unparse_content_stream(keep)); done.append(n)
            if page_inventory(pg)['visible_ops'] or page_inventory(pg)['invisible_ops']: left.append(n)
        p.save(path)
    return done, left

# ------------------------------------------------------------------ two printed pages per PDF page (4.1, 4.2, 6.1-6.4)
def _gutter(img):
    """The gutter of a two-page spread in a rendered page image (as displayed), as a share of the width, or None."""
    w, h = img.size; px = img.load()
    ink = [sum(1 for y in range(0, h, 2) if px[x, y] < 128) for x in range(w)]
    inked = sorted(v for v in ink if v > 0)
    if not inked: return None
    med = inked[len(inked) // 2]; best, run_, start = None, 0, None
    for x in range(int(SPREAD_BAND[0] * w), int(SPREAD_BAND[1] * w)):
        if ink[x] < GUTTER_INK * med:
            run_ += 1; start = x if run_ == 1 else start
            if not best or run_ > best[1]: best = (start, run_)
        else: run_ = 0
    if not best or best[1] < GUTTER_MIN * w: return None
    mid = best[0] + best[1] // 2; tot = sum(ink) or 1
    if sum(ink[:mid]) / tot < SPREAD_SIDE or sum(ink[mid:]) / tot < SPREAD_SIDE: return None
    return round(mid / w, 3)
def detect_spreads(path):
    """Pages that hold two printed pages side by side: {'pages', 'gutter': {page: share}, 'vertical_fonts', 'printed'}.
    Never splits a page. 'printed' holds the two printed page numbers when the halves' top/bottom bands show a pair that
    differ by one (not guessed otherwise)."""
    doc = pdfium.PdfDocument(path); size, gut = {}, {}
    try:
        for i in range(len(doc)):
            W, H = doc[i].get_size(); size[i + 1] = (round(W), round(H))
            if W >= SPREAD_ASPECT * H:
                g = _gutter(doc[i].render(scale=50 / 72, grayscale=True).to_pil())
                if g: gut[i + 1] = g
    finally: doc.close()
    if not gut: return None
    for p in list(gut):                                  # a landscape neighbour of the same size: a spread with a blank half
        for q in (p - 1, p + 1):
            if q in size and q not in gut and size[q][0] >= SPREAD_ASPECT * size[q][1] \
                    and abs(size[q][0] - size[p][0]) <= 0.03 * size[p][0] and abs(size[q][1] - size[p][1]) <= 0.03 * size[p][1]:
                gut[q] = 0.5
    pages = sorted(gut); vert = []
    with pikepdf.open(path) as pdf:
        for p in pages:
            fonts = ((pdf.pages[p - 1].obj.get('/Resources') or {}).get('/Font') or {}).values()
            if any(str(f.get('/Encoding')) == '/Identity-V' or 'Vert' in str(f.get('/BaseFont') or '') for f in fonts): vert.append(p)
        rot = {p: int(pdf.pages[p - 1].obj.get('/Rotate', 0)) % 360 for p in pages}
    from lib import plumb_fix  # noqa: F401
    import pdfplumber
    printed = {}
    with pdfplumber.open(path) as pl:
        for p in pages:
            if rot[p]: continue                         # rotated page: the bands are not where the reader sees them
            pg = pl.pages[p - 1]; W, H = float(pg.width), float(pg.height); x = gut[p] * W; nums = {'L': set(), 'R': set()}
            for top, bottom in ((0, 0.08 * H), (0.92 * H, H)):
                for side, (x0, x1) in (('L', (0, x)), ('R', (x, W))):
                    for w in pg.crop((x0, top, x1, bottom)).extract_words():
                        if re.fullmatch(r'\d{1,4}', w['text']): nums[side].add(int(w['text']))
            rf = p in vert
            pair = [(r, l) for r in nums['R'] for l in nums['L'] if (l == r + 1 if rf else r == l + 1)]
            if len(pair) == 1:
                r, l = pair[0]; printed[p] = f'{r}–{l}' if rf else f'{l}–{r}'
    return {'pages': pages, 'gutter': gut, 'rotation': {p: r for p, r in rot.items() if r}, 'vertical_fonts': vert, 'printed': printed}
def reorder_spreads(path, spreads, right_first):
    """After auto-tag, on spread pages only: reorder the tagger's elements of each page by half (the right half first for
    vertical CJK, else the left). Within a half, vertical CJK runs right to left by position; otherwise the tagger's order stays. Only the tree order changes, never page content.
    Returns per page the half sequence switches before and after, and the elements that span the gutter."""
    from lib import plumb_fix  # noqa: F401
    import pdfplumber
    out = {}
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        st = pdf.Root.get('/StructTreeRoot')
        if st is None: return out
        doc_el = st.K[0] if isinstance(st.K, pikepdf.Array) and len(st.K) == 1 else st.K
        if not isinstance(doc_el, pikepdf.Dictionary) or not isinstance(doc_el.get('/K'), pikepdf.Array): return out
        kids = list(doc_el.K); idx = _page_index(pdf); changed = False
        with pdfplumber.open(path) as pl:
            for p in spreads['pages']:
                pobj = pdf.pages[p - 1].obj; slots = [k for k, c in enumerate(kids) if isinstance(c, pikepdf.Dictionary)
                                                     and '/Pg' in c and idx.get(c.Pg.objgen) == p]
                if len(slots) < 2: continue
                pg = pl.pages[p - 1]; W, H = float(pg.width), float(pg.height); rot = spreads.get('rotation', {}).get(p, 0)
                def share(x, top):                       # position across the page as displayed (after /Rotate)
                    return {0: x / W, 90: 1 - top / H, 180: 1 - x / W, 270: top / H}.get(rot, x / W)
                xs = collections.defaultdict(list)
                for c in pg.chars:
                    if c.get('mcid') is not None and c['text'].strip(): xs[c['mcid']].append(share((c['x0'] + c['x1']) / 2, (c['top'] + c['bottom']) / 2))
                boxes = None; g = spreads['gutter'][p]; side, span, ctr = {}, [], {}
                for k in slots:
                    mc, todo = [], [kids[k]]
                    while todo:                          # the element's MCIDs on this page
                        e = todo.pop()
                        if isinstance(e, int): mc.append(int(e)); continue
                        if isinstance(e, pikepdf.Array): todo.extend(list(e)); continue
                        if not isinstance(e, pikepdf.Dictionary): continue
                        if e.get('/Type') == '/MCR' and '/MCID' in e: mc.append(int(e.MCID)); continue
                        if '/K' in e: todo.append(e.K)
                    v = [x for m in mc for x in xs.get(m, [])]
                    if not v and mc:                     # a figure: its image box
                        boxes = boxes if boxes is not None else _mcid_image_boxes(pdf.pages[p - 1], None)
                        v = [share((b[0] + b[2]) / 2, H - (b[1] + b[3]) / 2) for m in mc for b in [boxes.get(m)] if b]
                    if not v: side[k] = None; continue
                    ctr[k] = sum(v) / len(v)
                    first = [s > g if right_first else s < g for s in v]
                    side[k] = sum(first) * 2 >= len(first)
                    if min(sum(first), len(first) - sum(first)) >= 0.2 * len(first): span.append(k)
                known = [side[k] for k in slots if side[k] is not None]
                if not known: continue
                last = known[0]
                for k in slots:                          # an element with no content of its own goes with the one before it
                    if side[k] is None: side[k] = last
                    last = side[k]
                seq = lambda order: ''.join('A' if side[k] else 'B' for k in order)
                before = seq(slots)
                for k in slots: ctr.setdefault(k, None)
                lastc = next((ctr[k] for k in slots if ctr[k] is not None), 0.5)
                for k in slots:                          # likewise for position
                    if ctr[k] is None: ctr[k] = lastc
                    lastc = ctr[k]
                # vertical CJK: columns run right to left within a half too (the tagger's xycut reads them left to right)
                new = sorted(slots, key=lambda k: (0 if side[k] else 1, -ctr[k] if right_first else 0, slots.index(k)))
                after = seq(new); span_names = [str(kids[k].get('/S')) for k in span][:10]
                reordered = [kids[k] for k in new]
                for slot, el in zip(slots, reordered): kids[slot] = el
                sw = lambda s: sum(1 for a, b in zip(s, s[1:]) if a != b)
                out[p] = {'switches_before': sw(before), 'switches_after': sw(after), 'elements': len(slots),
                          'spanning': span_names}
                changed = changed or before != after
        if changed:
            doc_el.K = pikepdf.Array(kids); pdf.save(path)
    return out

# ------------------------------------------------------------------ the existing tag tree (checklist 10.5)
def _page_index(pdf):
    return {pg.obj.objgen: n for n, pg in enumerate(pdf.pages, 1)}
def _mcid_image_boxes(page, mcids):
    """The box (PDF user space) of the images drawn inside marked content with these MCIDs on one page: {mcid: [x0, y0, x1, y1]}."""
    out = {}
    try: ops = pikepdf.parse_content_stream(page)
    except Exception: return out
    ctm, stk, open_mc, xo = [1, 0, 0, 1, 0, 0], [], [], (page.obj.get('/Resources') or {}).get('/XObject') or {}
    for a, o in ops:
        o = str(o)
        if o == 'q': stk.append(ctm)
        elif o == 'Q' and stk: ctm = stk.pop()
        elif o == 'cm': ctm = _mul([float(x) for x in a], ctm)
        elif o == 'BDC': open_mc.append(int(a[1].MCID) if isinstance(a[1], pikepdf.Dictionary) and '/MCID' in a[1] else None)
        elif o == 'BMC': open_mc.append(None)
        elif o == 'EMC' and open_mc: open_mc.pop()
        elif o == 'Do' and open_mc and (mcids is None or open_mc[-1] in mcids):      # None: every MCID
            x = xo.get(a[0])
            if x is None or x.get('/Subtype') != '/Image': continue
            pts = [(ctm[0] * u + ctm[2] * v + ctm[4], ctm[1] * u + ctm[3] * v + ctm[5]) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1))]
            box = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
            old = out.get(open_mc[-1])
            out[open_mc[-1]] = [round(v, 1) for v in (box if old is None else [min(old[0], box[0]), min(old[1], box[1]), max(old[2], box[2]), max(old[3], box[3])])]
    return out
def tag_status(pdf, figures=False):
    """('untagged' | 'placeholder' | 'tagged', details). A tree with no text-bearing element (TEXT_BEARING, after RoleMap) is a
    placeholder: it says nothing about the text's structure, so intake treats the book as untagged. MarkInfo is recorded
    but does not decide it (12 of the sponsors' 148 have full trees with MarkInfo missing or Marked false).
    figures=True also lists every Figure's /Alt or /ActualText with its page, MCIDs and image box."""
    st = pdf.Root.get('/StructTreeRoot'); mi = pdf.Root.get('/MarkInfo')
    info = {'markinfo': None if mi is None else bool(mi.get('/Marked', False))}
    if st is None or st.get('/K') is None or isinstance(st.K, pikepdf.Array) and len(st.K) == 0: return 'untagged', info
    rolemap = {str(k): str(v) for k, v in (st.get('/RoleMap') or {}).items()}
    counts, figs, seen, todo = collections.Counter(), [], set(), [st.K]
    pages = _page_index(pdf) if figures else {}
    while todo:
        k = todo.pop()
        if isinstance(k, pikepdf.Array): todo.extend(list(k)); continue
        if not isinstance(k, pikepdf.Dictionary) or k.get('/Type') in ('/MCR', '/OBJR'): continue
        if k.is_indirect:
            if k.objgen in seen: continue
            seen.add(k.objgen)
        s = k.get('/S')
        if s is None: continue
        role = rolemap.get(str(s), str(s)); counts[role] += 1
        if figures and role == '/Figure':
            kids = k.get('/K'); kids = list(kids) if isinstance(kids, pikepdf.Array) else [kids]
            mcids = [int(x) for x in kids if isinstance(x, int)] + [int(x.MCID) for x in kids if isinstance(x, pikepdf.Dictionary) and x.get('/Type') == '/MCR' and '/MCID' in x]
            pg = k.get('/Pg') or next((x.get('/Pg') for x in kids if isinstance(x, pikepdf.Dictionary) and '/Pg' in x), None)
            alt = str(k.Alt).rstrip('\x00') if '/Alt' in k else None
            figs.append({'page': pages.get(pg.objgen) if pg is not None else None, 'mcids': mcids, 'alt': alt,
                         'actual_text': str(k.ActualText).rstrip('\x00') if '/ActualText' in k else None,
                         'kind': None if alt is None else ('placeholder' if PUBLISHER_PLACEHOLDER_ALT.fullmatch(alt) else 'publisher')})
        if '/K' in k: todo.append(k.K)
    info.update({'elements': dict(counts.most_common()), 'text_elements': sum(v for r, v in counts.items() if r in TEXT_BEARING)})
    if figures:
        figs.sort(key=lambda f: (f['page'] or 0, f['mcids']))
        for f in figs:
            if f['page'] and f['mcids']:
                boxes = _mcid_image_boxes(pdf.pages[f['page'] - 1], set(f['mcids']))
                if boxes:
                    b = list(boxes.values()); f['image_box'] = [min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b)]
        info['figures'] = figs
    return ('tagged' if info['text_elements'] else 'placeholder'), info
def tagged(pdf):
    """A real tag tree (text-bearing elements), not a placeholder: intake leaves such a book alone."""
    return tag_status(pdf)[0] == 'tagged'
def remove_tag_tree(path):
    """On intake's own working copy only: drop the placeholder tree (StructTreeRoot, MarkInfo, StructParents/StructParent
    on pages, annotations and forms) so the book is auto-tagged as untagged. Marked-content operators stay in the pages;
    page appearance and text do not change (checked by the caller)."""
    with pikepdf.open(path, allow_overwriting_input=True) as p:
        for k in ('/StructTreeRoot', '/MarkInfo'):
            if k in p.Root: del p.Root[k]
        for pg in p.pages:
            if '/StructParents' in pg.obj: del pg.obj['/StructParents']
            for a in pg.obj.get('/Annots') or []:
                if isinstance(a, pikepdf.Dictionary) and '/StructParent' in a: del a['/StructParent']
            for x in ((pg.obj.get('/Resources') or {}).get('/XObject') or {}).values():
                if isinstance(x, pikepdf.Stream) and '/StructParents' in x: del x['/StructParents']
        p.save(path)

def scripts(text):
    c = collections.Counter()
    for ch in text:
        o = ord(ch)
        if 0x3040 <= o <= 0x30ff or 0x31f0 <= o <= 0x31ff: c['kana'] += 1
        elif 0xac00 <= o <= 0xd7af or 0x1100 <= o <= 0x11ff: c['hangul'] += 1
        elif 0x4e00 <= o <= 0x9fff or 0x3400 <= o <= 0x4dbf or 0xf900 <= o <= 0xfaff: c['han'] += 1
        elif ch.isalpha() and o < 0x250 or 0x1e00 <= o <= 0x1eff: c['latin'] += 1
        elif 0xe000 <= o <= 0xf8ff: c['private_use'] += 1
        elif ch.isalpha(): c['other'] += 1
    return c

def private_use_ranges(counter):
    """Private-use code points grouped into the known ranges (PUA_NAMED) and runs of consecutive other codes."""
    out, other = [], sorted(o for o in counter if not any(a <= o <= b for a, b, _ in PUA_NAMED))
    for a, b, what in PUA_NAMED:
        n = sum(v for o, v in counter.items() if a <= o <= b)
        if n: out.append({'range': f'U+{a:04X}–U+{b:04X}', 'what': what, 'count': n})
    run = []
    for o in other + [None]:
        if run and (o is None or o != run[-1] + 1):
            out.append({'range': f'U+{run[0]:04X}' + (f'–U+{run[-1]:04X}' if len(run) > 1 else ''), 'what': 'other private-use codes',
                        'count': sum(counter[x] for x in run)}); run = []
        if o is not None: run.append(o)
    return sorted(out, key=lambda r: -r['count'])

def word_breaks(tp):
    """(space characters, gap-only breaks, narrow gap-only breaks) on one PDFium text page. A gap-only break is a space
    PDFium made up from a gap between letters. The gap is measured between advance widths (PDFium's loose character box
    runs from a glyph's origin to origin + advance, which is what a text extractor uses), relative to the type size
    (font size x text matrix scale); under NARROW_GAP it is narrow."""
    R = pdfium_raw; n = R.FPDFText_CountChars(tp.raw); real = gen = narrow = 0
    a, b, m = R.FS_RECTF(), R.FS_RECTF(), R.FS_MATRIX()
    def size(i):
        R.FPDFText_GetMatrix(tp.raw, i, m); return R.FPDFText_GetFontSize(tp.raw, i) * math.hypot(m.a, m.b)
    for c in range(n):
        if R.FPDFText_GetUnicode(tp.raw, c) != 32: continue
        if R.FPDFText_IsGenerated(tp.raw, c) != 1: real += 1; continue
        gen += 1
        if not 0 < c < n - 1 or R.FPDFText_GetUnicode(tp.raw, c - 1) in (9, 10, 13, 32) or R.FPDFText_GetUnicode(tp.raw, c + 1) in (9, 10, 13, 32): continue
        R.FPDFText_GetLooseCharBox(tp.raw, c - 1, a); R.FPDFText_GetLooseCharBox(tp.raw, c + 1, b)
        sz = max(size(c - 1), size(c + 1))
        if sz <= 0 or abs(a.bottom - b.bottom) > 0.3 * sz: continue              # not on one horizontal line
        if (b.left - a.right) / sz < NARROW_GAP: narrow += 1
    return real, gen, narrow
INVISIBLE = re.compile('[\\s\x00-\x1f\x7f-\x9f\u00ad\u200b-\u200f\u2028-\u202e\u2060-\u2064\ufeff\ufffe\uffff]')
                                           # white space and the invisible marks PDFium adds to page text (U+FFFE at a line-end
                                           #   hyphen, U+200B): only these are left out when text outside the page is counted
def layer_scan(doc, text_pages):
    """Every text page: its text, the part inside the visible page area (CropBox), private-use characters (3.6),
    characters outside the visible area, and word breaks (3.4). Local, no OCR."""
    out = {'text': {}, 'visible': {}, 'pua': collections.Counter(), 'pua_pages': [], 'outside': {},
           'gaps': [], 'narrow': {}, 'real': 0, 'gen': 0, 'narrow_total': 0}
    for i in text_pages:
        page = doc[i - 1]; tp = page.get_textpage()
        t = out['text'][i] = tp.get_text_range()
        out['visible'][i] = tp.get_text_bounded(*page.get_cropbox())
        k = [ord(ch) for ch in t if 0xe000 <= ord(ch) <= 0xf8ff]
        if k: out['pua'].update(k); out['pua_pages'].append(i)
        n_out = len(INVISIBLE.sub('', t)) - len(INVISIBLE.sub('', out['visible'][i]))
        if n_out >= OUTSIDE_MIN_CHARS: out['outside'][i] = n_out
        r_, g_, nw = word_breaks(tp)
        out['real'] += r_; out['gen'] += g_; out['narrow_total'] += nw
        if r_ + g_ >= GAP_MIN_BREAKS and g_ / (r_ + g_) > GAP_SHARE: out['gaps'].append(i)
        if nw: out['narrow'][i] = nw
    return out

# ------------------------------------------------------------------ OCR helpers (Tesseract directly for the 1.2 test)
def render(doc, i, dpi, path):
    doc[i].render(scale=dpi / 72, grayscale=True).to_pil().save(path)
def tesseract_text(img, lang):
    r = run(['tesseract', img, 'stdout', '-l', lang, '--psm', '3'])
    if r.returncode: raise RuntimeError(f'tesseract failed: {r.stderr.strip()[:200]}')
    return r.stdout
def osd_script(img):
    r = run(['tesseract', img, 'stdout', '--psm', '0'])
    m = re.search(r'Script:\s*(\S+)', r.stdout)
    return m.group(1) if m else None

QUOTES = str.maketrans({'‘': "'", '’': "'", '‚': "'", '‛': "'", '“': '"', '”': '"',
                        '„': '"', '–': '-', '—': '-', '−': '-', '‐': '-', '‑': '-',
                        ' ': ' ', '­': ''})
def is_cjk(ch):
    o = ord(ch)
    return 0x3040 <= o <= 0x30ff or 0x4e00 <= o <= 0x9fff or 0x3400 <= o <= 0x4dbf or 0xac00 <= o <= 0xd7af or 0xff00 <= o <= 0xffef
def norm(t):
    t = unicodedata.normalize('NFKC', t).translate(QUOTES)
    t = re.sub(r'-\s*\n\s*', '', t)                       # a word hyphenated at a line end counts once
    return ''.join(ch for ch in t.lower() if not ch.isspace() and not is_cjk(ch) and ch != '_')   # OCR never reads fill-in rules
def marked_letters(t):
    """Letters carrying a diacritic (tone marks, accents, breves: anything that decomposes with a combining mark)."""
    return sum(1 for ch in t if ch.isalpha() and any(unicodedata.combining(c) for c in unicodedata.normalize('NFD', ch)))
def strip_marks(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if not unicodedata.combining(c))
def marked_vowels(t):
    """Vowels carrying a mark (ö ŏ ù ā …): what romanized and accented text has, and stray OCR marks rarely are."""
    return sum(1 for ch in t if ch.isalpha() and unicodedata.normalize('NFD', ch)[0].lower() in 'aeiouy'
               and any(unicodedata.combining(c) for c in unicodedata.normalize('NFD', ch)))
def norm_cjk(t):
    """norm() with CJK characters kept: for comparing CJK OCR layers."""
    t = unicodedata.normalize('NFKC', t).translate(QUOTES)
    t = re.sub(r'-\s*\n\s*', '', t)
    return ''.join(ch for ch in t.lower() if not ch.isspace() and ch != '_')
def tesseract_words(img, lang):
    """Tesseract's words with their confidence, and the text they make (one line per Tesseract line)."""
    import csv, io
    r = run(['tesseract', img, 'stdout', '-l', lang, '--psm', '3', 'tsv'])
    if r.returncode: raise RuntimeError(f'tesseract failed: {r.stderr.strip()[:200]}')
    words, lines = [], collections.OrderedDict()
    for w in csv.DictReader(io.StringIO(r.stdout), delimiter='\t', quoting=csv.QUOTE_NONE):
        t = (w.get('text') or '').strip()
        if not t: continue
        words.append((t, float(w.get('conf') or -1)))
        lines.setdefault((w.get('block_num'), w.get('par_num'), w.get('line_num')), []).append(t)
    return words, '\n'.join(' '.join(v) for v in lines.values())
def math_symbols(t):
    """Math symbols (Unicode Sm, apart from + = < > | ~ ¬ and arrows, which glosses use: dakine's →), Greek letters and
    math alphanumerics in a text."""
    return sum(1 for ch in t if unicodedata.category(ch) == 'Sm' and ch not in '+=<>|~¬' and not 0x2190 <= ord(ch) <= 0x21ff
               or 0x370 <= ord(ch) <= 0x3ff or 0x1d400 <= ord(ch) <= 0x1d7ff)
def cer(ocr, layer):
    """Edits needed to turn the OCR text into the text layer, per OCR character (difflib alignment)."""
    sm = difflib.SequenceMatcher(None, ocr, layer, autojunk=False)
    edits = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal')
    return edits / max(len(ocr), 1)
def bag_diff(ocr, layer):
    """Same characters in any order (the any-order error rate): tells a reading-order difference from wrong characters."""
    a, b = collections.Counter(ocr), collections.Counter(layer)
    return sum(((a - b) + (b - a)).values()) / max(len(ocr), 1)
WORDLIKE = re.compile(r"^[^\W\d_]{2,}$")
def textlike(text):
    toks = [t.strip('.,;:!?()[]"\'') for t in text.split()]; toks = [t for t in toks if t]
    good = [t for t in toks if WORDLIKE.match(t) and re.search(r'[aeiouyAEIOUY]', t) or any(is_cjk(c) for c in t)]
    return len(good) >= TEXTLIKE_WORDS and len(good) / max(len(toks), 1) >= TEXTLIKE_SHARE, len(good), len(toks)

def cjk_char(ch):
    o = ord(ch)
    return 0x3040 <= o <= 0x30ff or 0x4e00 <= o <= 0x9fff or 0x3400 <= o <= 0x4dbf or 0xac00 <= o <= 0xd7af or 0xf900 <= o <= 0xfaff
def cjk_probe(img, langs):
    """CJK characters Tesseract reads on the page image at CJK_PROBE_CONF confidence or more, with the CJK packs only."""
    import csv, io
    r = run(['tesseract', img, 'stdout', '-l', langs, '--psm', '3', 'tsv'])
    rows = csv.DictReader(io.StringIO(r.stdout), delimiter='\t', quoting=csv.QUOTE_NONE)
    return sum(sum(1 for ch in (w.get('text') or '') if cjk_char(ch)) for w in rows if float(w.get('conf') or -1) >= CJK_PROBE_CONF)
def junk_stats(text):
    """Share of OCR tokens that look like junk: a symbol from JUNK_SYMBOLS, capitals with no vowel ("MBH"), or letters and
    digits mixed ("f7") other than ordinals; CJK tokens and plain numbers are fine."""
    toks = [t.strip('.,;:!?()[]"\'’‘“”-–—') for t in text.split()]; toks = [t for t in toks if t]; bad = []
    for t in toks:
        if any(cjk_char(c) for c in t): continue
        letters = re.sub(r'[^A-Za-z]', '', t)
        if any(c in JUNK_SYMBOLS for c in t) or (t.isupper() and len(letters) >= 2 and not re.search(r'[AEIOUY]', letters)) \
                or (letters and re.search(r'\d', t) and not re.fullmatch(r'\d+(st|nd|rd|th|s)|\d+[a-z]', t)):
            bad.append(t)
    return {'share': round(len(bad) / max(len(toks), 1), 3), 'junk': len(bad), 'tokens': len(toks), 'examples': bad[:8]}

# ------------------------------------------------------------------ comparisons used by the checks
def page_pixels(doc, i, dpi=40):
    return doc[i].render(scale=dpi / 72, grayscale=True).to_pil()
def _blurred_diff(a, b, i):
    """Share of a 72-dpi page that changes by more than a faint step once both renderings are softened slightly:
    sub-pixel glyph shifts vanish, a missing word does not."""
    from PIL import ImageChops, ImageFilter
    ia = page_pixels(a, i, 72).filter(ImageFilter.GaussianBlur(1)); ib = page_pixels(b, i, 72).filter(ImageFilter.GaussianBlur(1))
    if ia.size != ib.size: return 1.0
    h = ImageChops.difference(ia, ib).histogram()
    return sum(h[49:]) / (ia.width * ia.height)
NEAR, REDRAWN = 0.0005, 0.003
def compare(a_path, b_path, redrawn=(), near=False):
    """Pages whose appearance or text (ignoring white space) differs.
    exact (default): the 40-dpi renderings must be identical (OCR --mode skip adds only invisible text).
    near=True: auto-tagging may split a text run to tag a list label or a link separately, which can move glyph
      edges by a fraction of a pixel; at most 0.05% of the softened page may differ.
    redrawn pages (force OCR re-draws the page as an image: 400 dpi, 1-bit in our test): at most 0.3% may differ, and their text is not
      compared (it was replaced on purpose)."""
    # near=True also: a page over NEAR gets a second look at TILE_DPI in quarter-inch tiles (sub-pixel shifts vanish,
    #   a missing mark does not), and a page whose text holds exactly the same characters in a different order passes
    #   as "reordered" (the tagger re-sequenced text runs), with the moved fragments listed
    a, b = pdfium.PdfDocument(a_path), pdfium.PdfDocument(b_path)
    if len(a) != len(b): return {'page_count': [len(a), len(b)], 'pixels': [], 'text': []}
    px, tx, tiles, reord = [], [], [], []
    for i in range(len(a)):
        if (i + 1) in redrawn:
            if _blurred_diff(a, b, i) > REDRAWN: px.append(i + 1)
            continue
        if near:
            if _blurred_diff(a, b, i) > NEAR:
                worst = _worst_tile(a, b, i)
                if worst > TILE_MAX: px.append(i + 1)
                else: tiles.append({'page': i + 1, 'worst_tile': worst})
        elif page_pixels(a, i).tobytes() != page_pixels(b, i).tobytes(): px.append(i + 1)
        ta = re.sub(r'\s+', '', a[i].get_textpage().get_text_range()); tb = re.sub(r'\s+', '', b[i].get_textpage().get_text_range())
        if ta != tb:
            if near:                            # PDFium marks a hyphen it sees at a line end as U+FFFE or U+0002: the same glyph
                ha, hb = ta.translate(HYPHEN_MARKS), tb.translate(HYPHEN_MARKS)
                if ha == hb: continue
                if collections.Counter(ha) == collections.Counter(hb): reord.append({'page': i + 1, 'moved': moved_fragments(ha, hb)}); continue
            tx.append(i + 1)
    a.close(); b.close()
    return {'page_count': None, 'pixels': px, 'text': tx, 'tile_passed': tiles, 'reordered': reord}
HYPHEN_MARKS = str.maketrans({'\ufffe': '-', '\x02': '-'})
def _worst_tile(a, b, i):
    """Changed pixels in the worst quarter-inch tile at TILE_DPI, after the same softening and step as the 72-dpi check."""
    from PIL import ImageChops, ImageFilter
    ia = a[i].render(scale=TILE_DPI / 72, grayscale=True).to_pil().filter(ImageFilter.GaussianBlur(1))
    ib = b[i].render(scale=TILE_DPI / 72, grayscale=True).to_pil().filter(ImageFilter.GaussianBlur(1))
    if ia.size != ib.size: return 10 ** 9
    d = ImageChops.difference(ia, ib).point(lambda v: 255 if v > 48 else 0)
    if d.getbbox() is None: return 0
    worst = 0
    for y in range(0, d.height, TILE_PX):
        for x in range(0, d.width, TILE_PX):
            worst = max(worst, d.crop((x, y, min(x + TILE_PX, d.width), min(y + TILE_PX, d.height))).histogram()[255])
    return worst
def moved_fragments(a, b, n=5):
    """Up to n stretches of text that sit elsewhere in b than in a (white space removed), each at most 60 characters."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False); out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ('delete', 'replace') and a[i1:i2] not in out: out.append(a[i1:i2])
    return [f[:60] for f in out[:n]]
def keepers(path):
    """What must survive every step: bookmarks, link annotations, page labels, page count."""
    with pikepdf.open(path) as p:
        n_out = 0
        try:
            with p.open_outline() as ol:
                stack = list(ol.root)
                while stack:
                    it = stack.pop(); n_out += 1; stack.extend(it.children)
        except Exception: n_out = None
        links = sum(1 for pg in p.pages for a in (pg.obj.get('/Annots') or []) if a.get('/Subtype') == '/Link')
        labels = [str(pg.label) for pg in p.pages] if '/PageLabels' in p.Root else None
        return {'pages': len(p.pages), 'bookmarks': n_out, 'links': links, 'page_labels': labels}
def coverage(path):
    """Text operators inside marked content that the tag tree reaches, inside an Artifact, or neither (untagged)."""
    p = pikepdf.open(path); st = p.Root.get('/StructTreeRoot'); pt = {}
    if st is not None and '/ParentTree' in st:
        def nums(n, d=0):
            if '/Nums' in n:
                a = n.Nums
                for k in range(0, len(a) - 1, 2): pt[int(a[k])] = a[k + 1]
            for kid in n.get('/Kids', []) if d < 20 else []: nums(kid, d + 1)
        nums(st.ParentTree)
    tot = collections.Counter(); untagged_pages = []
    for i, pg in enumerate(p.pages, 1):
        arr = pt.get(int(pg.obj.StructParents)) if '/StructParents' in pg.obj else None
        c = collections.Counter()
        def walk(owner, res, depth, stack, arr):
            try: ops = pikepdf.parse_content_stream(owner)
            except Exception: return
            for a, o in ops:
                o = str(o)
                if o in ('BDC', 'BMC'):
                    tag = str(a[0]); mc = None
                    if o == 'BDC' and len(a) > 1 and isinstance(a[1], pikepdf.Dictionary) and '/MCID' in a[1]: mc = int(a[1].MCID)
                    stack.append('art' if tag == '/Artifact' else ('tree' if mc is not None and isinstance(arr, pikepdf.Array)
                                 and mc < len(arr) and isinstance(arr[mc], pikepdf.Dictionary) else ('stale' if mc is not None else 'other')))
                elif o == 'EMC':
                    if stack: stack.pop()
                elif o in TXT_OPS:
                    c['artifact' if 'art' in stack else ('tagged' if 'tree' in stack else 'untagged')] += 1
                elif o == 'Do' and depth < 3 and res is not None:
                    x = (res.get('/XObject') or {}).get(a[0])
                    if x is not None and x.get('/Subtype') == '/Form':        # a form numbers its own marked content
                        farr = pt.get(int(x.StructParents)) if '/StructParents' in x else arr
                        walk(x, x.get('/Resources', res), depth + 1, list(stack), farr)
        walk(pg, pg.obj.get('/Resources'), 0, [], arr)
        tot += c
        if c['untagged']: untagged_pages.append(i)
    p.close()
    return {'tagged': tot['tagged'], 'artifact': tot['artifact'], 'untagged': tot['untagged'], 'untagged_pages': untagged_pages[:50]}

# ------------------------------------------------------------------ post-steps on our own intermediate files
PLACEHOLDER_ALT = {'/Figure': re.compile(r'image \d+'), '/Link': re.compile(r'Annotation')}   # OpenDataLoader 2.5.12's own words

def drop_placeholder_alt(path):
    """Remove the alt text OpenDataLoader writes on every Figure ("image 12") and Link ("Annotation"): a screen reader
    would say it instead of describing the figure or reading the link's text. Exact matches only; any other alt is kept.
    Changes no page content (checklist 8.2, 2.4.4)."""
    n = {'figures': 0, 'links': 0}
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        st = pdf.Root.get('/StructTreeRoot'); todo = [st] if st is not None else []; seen = set()
        while todo:
            e = todo.pop()
            if not isinstance(e, pikepdf.Dictionary): continue
            if e.is_indirect:
                if e.objgen in seen: continue
                seen.add(e.objgen)
            pat = PLACEHOLDER_ALT.get(str(e.get('/S')))
            if pat and '/Alt' in e and pat.fullmatch(str(e.Alt)):
                del e['/Alt']; n['figures' if str(e.S) == '/Figure' else 'links'] += 1
            K = e.get('/K')
            todo.extend(k for k in (list(K) if isinstance(K, pikepdf.Array) else [K]) if isinstance(k, pikepdf.Dictionary) and '/S' in k)
        if n['figures'] or n['links']: pdf.save(path)
    return n

def strip_ocr_layer(path, pages):
    """Remove OCRmyPDF's invisible text (its /OCR-… form, drawn as q /OCR-… Do Q) from the given pages."""
    with pikepdf.open(path, allow_overwriting_input=True) as p:
        for n in pages:
            pg = p.pages[n - 1]; xo = pg.Resources.get('/XObject') or {}
            names = [k for k in xo.keys() if str(k).startswith('/OCR-')]
            if not names: continue
            ops = list(pikepdf.parse_content_stream(pg)); keep = []; i = 0
            while i < len(ops):
                a, o = ops[i]
                if str(o) == 'q' and i + 2 < len(ops) and str(ops[i + 1][1]) == 'Do' and str(ops[i + 1][0][0]) in map(str, names) and str(ops[i + 2][1]) == 'Q':
                    i += 3; continue
                keep.append((a, o)); i += 1
            pg.obj.Contents = p.make_stream(pikepdf.unparse_content_stream(keep))
            for k in names: del xo[k]
        p.save(path)
def artifact_page_scans(path, pages):
    """On OCR'd pages, a Figure that is only the whole-page scan image becomes decoration (checklist 5.1: an image
    covering the whole page is the scan itself, not a figure). Returns the pages changed."""
    done = []
    with pikepdf.open(path, allow_overwriting_input=True) as p:
        st = p.Root.get('/StructTreeRoot')
        if st is None: return done
        pt = {}
        def nums(n, d=0):
            if '/Nums' in n:
                a = n.Nums
                for k in range(0, len(a) - 1, 2): pt[int(a[k])] = a[k + 1]
            for kid in n.get('/Kids', []) if d < 20 else []: nums(kid, d + 1)
        nums(st.ParentTree)
        for n in pages:
            pg = p.pages[n - 1]; vr = visible_rect(pg)
            arr = pt.get(int(pg.obj.StructParents)) if '/StructParents' in pg.obj else None
            if not isinstance(arr, pikepdf.Array): continue
            ops = list(pikepdf.parse_content_stream(pg)); xo = pg.Resources.get('/XObject') or {}
            ctm, stk, open_mc, changed = [1, 0, 0, 1, 0, 0], [], [], False
            hits = []                                   # (index of BDC op, mcid) whose content is one big image
            for idx, (a, o) in enumerate(ops):
                o = str(o)
                if o == 'q': stk.append(ctm)
                elif o == 'Q' and stk: ctm = stk.pop()
                elif o == 'cm': ctm = _mul([float(x) for x in a], ctm)
                elif o == 'BDC':
                    mc = int(a[1].MCID) if isinstance(a[1], pikepdf.Dictionary) and '/MCID' in a[1] else None
                    open_mc.append([idx, str(a[0]), mc, 0, 0])
                elif o == 'BMC': open_mc.append([idx, str(a[0]), None, 0, 0])
                elif o == 'EMC' and open_mc:
                    bi, tag, mc, imgs, other = open_mc.pop()
                    if tag == '/Figure' and mc is not None and imgs == 1 and other == 0: hits.append((bi, mc))
                elif o in TXT_OPS and open_mc: open_mc[-1][4] += 1
                elif o == 'Do' and open_mc:
                    x = xo.get(a[0])
                    if x is not None and x.get('/Subtype') == '/Image':
                        if visible_cover(ctm, vr) >= 0.85: open_mc[-1][3] += 1        # the whole visible page: the scan
                        else: open_mc[-1][4] += 1
                    else: open_mc[-1][4] += 1
            for bi, mc in hits:
                el = arr[mc] if mc < len(arr) else None
                if not isinstance(el, pikepdf.Dictionary) or str(el.get('/S')) != '/Figure': continue
                k = el.get('/K'); kids = list(k) if isinstance(k, pikepdf.Array) else [k]
                if len(kids) != 1: continue                       # the Figure holds more than this image: leave it
                ops[bi] = ([pikepdf.Name('/Artifact'), pikepdf.Dictionary(Type=pikepdf.Name('/Layout'))], pikepdf.Operator('BDC'))
                arr[mc] = None
                par = el.get('/P')
                if par is not None:
                    pk = par.get('/K')
                    if isinstance(pk, pikepdf.Array):
                        par.K = pikepdf.Array([x for x in pk if not (isinstance(x, pikepdf.Dictionary) and x.objgen == el.objgen)])
                    elif isinstance(pk, pikepdf.Dictionary) and pk.objgen == el.objgen: del par['/K']
                changed = True
            if changed:
                pg.obj.Contents = p.make_stream(pikepdf.unparse_content_stream(ops)); done.append(n)
        p.save(path)
    return done

# ------------------------------------------------------------------ intake.md: the record for a person
def _pages(ps, labels):
    """PDF page numbers as collapsed ranges, with printed labels where they exist and differ: "PDF 381–386 (printed 391–396)"."""
    ps = sorted({int(p) for p in ps or []}); out, i = [], 0
    def lab(p): return (labels or {}).get(str(p))
    while i < len(ps):
        j = i
        while j + 1 < len(ps) and ps[j + 1] == ps[j] + 1: j += 1
        a, b = ps[i], ps[j]; la, lb = lab(a), lab(b)
        txt = f'PDF {a}' if a == b else f'PDF {a}–{b}'
        if la and lb and (la != str(a) or lb != str(b)):
            txt += f' (printed {la})' if a == b else (f' (printed {la} to {lb})' if '–' in la + lb else f' (printed {la}–{lb})')   # spreads: "210–211"
        out.append(txt); i = j + 1
    return ', '.join(out) if out else 'none'
def intake_glance(rec):
    """The numbers behind intake.md's "Overview", kept in intake.json (and so in record.json) as `glance`."""
    o, tt, fl = rec.get('ocr') or {}, rec.get('text_test') or {}, rec.get('flags') or []
    ocr_pages = o.get('pages_with_ocr_text') or []
    v = (rec.get('review') or {}).get('ocr_text_approved')
    ocr_open = bool(ocr_pages) and not (isinstance(v, dict) and v.get('verdict') == 'approved')
    sc = [p for p in tt.get('pages') or [] if p.get('cer') is not None]
    return {'schema': 'intake-glance/0.1', 'status': rec.get('status'),
            'needs_person': sum(1 for f in fl if f.get('check')) + (1 if ocr_open else 0), 'notes': sum(1 for f in fl if not f.get('check')),
            'ocr_pages': ocr_pages, 'picture_pages': o.get('image_pages_without_text') or [],
            'placeholder_alt_removed': (rec.get('checks') or {}).get('placeholder_alt_removed'),
            'text_test': {'verdict': tt.get('verdict'), 'median_cer': tt.get('median_cer'), 'sampled': len(sc),
                          'suspicious_added': sum(1 for p in sc if p.get('suspicious')), 'front_matter_skipped': bool(tt.get('front_matter_skipped')),
                          'best': min(sc, key=lambda p: p['cer'])['page'] if sc else None, 'best_cer': min(p['cer'] for p in sc) if sc else None,
                          'worst': max(sc, key=lambda p: p['cer'])['page'] if sc else None, 'worst_cer': max(p['cer'] for p in sc) if sc else None,
                          'over_ok': sorted(p['page'] for p in sc if p['cer'] > CER_OK), 'over_bad': sorted(p['page'] for p in sc if p['cer'] > CER_BAD)}}

def glance_lines(rec, labels):
    """intake.md's "## Overview" block (checklist 1.2, 3.1, rule 2), from rec['glance']."""
    g = rec.get('glance') or intake_glance(rec); st = g['status']; t = g['text_test']
    def P(ps): return _pages(ps, labels)
    def pl(n, w): return f'{n} {w}{"" if n == 1 else "s"}'
    if st == 'done':
        parts = ['auto-tagged']
        if g['ocr_pages']: parts.append(f'OCR text added on {pl(len(g["ocr_pages"]), "page")} ({P(g["ocr_pages"])})')
        if g['picture_pages']: parts.append(f'{pl(len(g["picture_pages"]), "picture page")} left for alt text ({P(g["picture_pages"])})')
        ph = g.get('placeholder_alt_removed') or {}
        if ph.get('figures') or ph.get('links'):
            parts.append(f'placeholder alt text removed from {ph.get("figures", 0):,} figures and {ph.get("links", 0):,} links')
        result = 'ready for the pipeline: ' + ' · '.join(parts)
    else:
        result = {'planned': 'plan only, nothing changed', 'stopped': 'stopped for a person', 'failed': 'failed'}.get(st, st or 'not finished') \
                 + f': {rec.get("summary") or "no summary recorded"}'
    L = ['## Overview', '', f'**Result:** {result}  ', f'**Needs a person:** {g["needs_person"]} (below) · **Notes:** {g["notes"]}  ']
    v = (rec.get('review') or {}).get('ocr_text_approved')
    if g['ocr_pages']:
        L.append('**OCR text reviewed by a person:** ' + (
            f'{v.get("verdict")} by {v.get("reviewer")} on {v.get("date")}' + (f' (PDF {v["pages"]})' if v.get('pages') else '') + f': {v.get("reason")}'
            if isinstance(v, dict) else 'not yet reviewed (on the review page, or with review_ocr.py)'))
    L.append('')
    if t['sampled']:
        n_ok = len(t['over_ok'])
        head = {'usable': 'Yes, usable.' if not n_ok else f'Usable overall, with {pl(n_ok, "page")} to check by eye.',
                'doubtful': 'Doubtful: a person decides.', 'unusable': 'No: unusable.'}.get(t['verdict'], f'{t["verdict"]}.')
        L += [f'**Is the existing text trustworthy?** {head}',
              f'{pl(t["sampled"], "sample page")} {"was" if t["sampled"] == 1 else "were"} read by OCR and compared with the PDF\'s own text.',
              'The samples are spread evenly through the book' + (', skipping the front matter.' if t['front_matter_skipped'] else '.')
              + (f' {pl(t["suspicious_added"], "page")} that looked suspicious {"was" if t["suspicious_added"] == 1 else "were"} added.' if t['suspicious_added'] else '')]
        if t['median_cer'] is not None:
            L.append(f'On a typical page, {100 - 100 * t["median_cer"]:.1f}% of characters matched (median error {t["median_cer"]:.1%}).')
        L.append(f'Best page {t["best_cer"]:.1%} ({P([t["best"]])}) · worst {t["worst_cer"]:.1%} ({P([t["worst"]])})'
                 + (f' · {pl(n_ok, "page")} over 5%: {P(t["over_ok"])}' + (f' ({len(t["over_bad"])} of them over 15%: {P(t["over_bad"])})' if t['over_bad'] else '')
                    if n_ok else ' · no page over 5%') + '.')
        L += ['How to read this: 5% or less = usable · 5–15% = a person decides · over 15% = unusable.',
              'The book is judged on the median, so a few bad pages don\'t stop it; they are listed for a person.',
              'Even a perfect text layer doesn\'t score 0%: OCR makes its own mistakes.',
              'A bad page can mean the text layer is wrong there, or that OCR misread the page (tables, pictures, phonetic symbols, foreign words).', '']
    elif t['verdict'] == 'not tested': L += ['**Is the existing text trustworthy?** Not tested: no page had a text layer.', '']
    items = []
    for f in rec.get('flags') or []:
        if not f.get('check'): continue
        w, why, ps = f['what'], f.get('why') or '', f.get('pages') or []
        if w == 'Text layer' and 'unusable' in why: txt = f'Text layer unusable on {pl(len(ps), "sample page")}'
        elif w == 'Text layer' and 'partly disagree' in why: txt = f'Text layer doubtful on {pl(len(ps), "sample page")}'
        elif w == 'CJK OCR: needs a person': txt = 'CJK OCR text needs a person'
        elif w == 'Low-resolution scans': txt = 'Low-resolution scan' + ('s' if len(ps) != 1 else '') + ', read enlarged by OCR'
        else: txt = w
        items.append(txt + (f': {P(ps)}' if ps else ''))
    if g['ocr_pages'] and not (isinstance(v, dict) and v.get('verdict') == 'approved'):
        items.append(('OCR text not approved' if isinstance(v, dict) else 'OCR text not yet reviewed') + f': {P(g["ocr_pages"])}')
    if items: L += ['**Needs a person**'] + [f'{i}. {x}' for i, x in enumerate(items, 1)] + ['']
    return L

def write_md(rec, path):
    """intake.md beside intake.json: the same record for a person, for every outcome (planned, done, stopped, failed,
    skipped). Rewritten whenever intake.json is saved, and by review_ocr.py when a verdict is recorded."""
    o, t, tt = rec.get('ocr') or {}, (rec.get('triage') or {}).get('counts') or {}, rec.get('text_test') or {}
    c, tv, lang = rec.get('checks') or {}, rec.get('tools') or {}, rec.get('language') or {}
    labels = rec.get('cited_labels') or {}; st = rec.get('status') or 'not finished'
    L = [f"# Intake: {(rec.get('original') or {}).get('file', 'file name not recorded')}", '',
         f"**Status:** {st}: {rec.get('summary') or 'no summary recorded'}  ",
         ' · '.join(x for x in [f"{(rec.get('original') or {}).get('pages')} pages" if (rec.get('original') or {}).get('pages') else None,
                                rec.get('written'), f"OCR_LANG {lang['ocr_lang']}" if lang.get('ocr_lang') else None,
                                ', '.join(f'{k} {v}' for k, v in (('Tesseract', tv.get('tesseract')), ('OCRmyPDF', tv.get('ocrmypdf')),
                                          ('OpenDataLoader', tv.get('opendataloader_pdf'))) if v) or None] if x)]
    if st == 'skipped':
        L += ['', 'The PDF already has a tag tree: intake leaves it alone and the pipeline works on the original.']
        open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n'); return
    L += [''] + glance_lines(rec, labels)
    rows = []
    tg = rec.get('tag_tree') or {}
    if tg.get('status') == 'placeholder':
        figs = tg.get('figures') or []
        rows.append(('Existing tag tree', 'a placeholder (' + ', '.join(f'{k.lstrip("/")} {v}' for k, v in (tg.get('elements') or {}).items())
                     + '; no text structure): set aside, the book is auto-tagged. Figures with alt text recorded: '
                     f"{sum(1 for f in figs if f.get('kind') == 'publisher')} publisher, {sum(1 for f in figs if f.get('kind') == 'placeholder')} placeholder"))
    if t: rows.append(('Pages', ' · '.join(f'{v} {k.replace("-", " ")}' for k, v in t.items())))
    if tt:
        v = tt.get('verdict') or 'not tested'
        rows.append(('Text-layer test (1.2)', v + (f": median {tt['median_cer']:.1%} on {tt.get('scored')} pages" if tt.get('median_cer') is not None and tt.get('scored') else '')))
    olt = rec.get('ocr_layer_test') or {}
    if olt:
        rows.append(('Existing OCR layer (scanned pages)', olt.get('verdict', 'not tested') + (f": median {olt['median_cer']:.1%} on {olt.get('scored')} "
                     'pages against a fresh reading by a different OCR model' if olt.get('median_cer') is not None else '')
                     + ('; diacritics missing from the layer' if olt.get('diacritics') else '')))
    cp = rec.get('cjk_probe') or {}
    if cp: rows.append(('CJK on pages to be OCR\'d', _pages(cp.get('cjk_pages'), labels) if cp.get('cjk_pages') else 'none found'))
    if st == 'planned' or not o:
        pl = rec.get('plan') or {}
        rows.append(('Plan', (f"OCR ({pl.get('ocr_mode')} mode) on {_pages(pl.get('ocr_pages'), labels)}" if pl.get('ocr_pages') else 'no OCR')
                     + ('; then auto-tagging' if pl.get('autotag') else '')))
    if o:
        rows.append(('OCR text added', _pages(o.get('pages_with_ocr_text'), labels)))
        rows.append(('Picture pages (no OCR text kept)', _pages(o.get('image_pages_without_text'), labels)))
    cov = c.get('coverage')
    if st == 'done':
        rows.append(('Checks', 'appearance and text unchanged after ' + ('OCR and ' if o else '') + 'auto-tagging'
                     + (f"; tag tree reaches {cov['tagged']:,} text runs, {cov['untagged']} untagged" if cov else '')
                     + '; bookmarks, links and page labels kept'))
    if o.get('pages_with_ocr_text'):
        v = (rec.get('review') or {}).get('ocr_text_approved')
        rows.append(('OCR text reviewed by a person', f"{v.get('verdict')} by {v.get('reviewer')} on {v.get('date')}" + (f" (pages {v['pages']})" if v.get('pages') else '')
                     + f": {v.get('reason')}" if isinstance(v, dict) else 'not yet reviewed (record a verdict with review_ocr.py)'))
    if rows: L += ['', '| | |', '|---|---|'] + [f'| {a} | {b} |' for a, b in rows]
    fl = rec.get('flags') or []
    def item(f): return f"- **{f['what']}**" + (f" ({_pages(f.get('pages'), labels)})" if f.get('pages') else '') + f": {f['why']}"
    ch = [f for f in fl if f.get('check')]; nt = [f for f in fl if not f.get('check')]
    L += ['', '## For a person (CHECK)', ''] + ([item(f) for f in ch] or ['- none'])
    L += ['', '## Notes', ''] + ([item(f) for f in nt] or ['- none'])
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2: sys.exit(__doc__.split('\n\n')[0])
    SRC, OUTD = os.path.abspath(args[0]), os.path.abspath(args[1]); PLAN_ONLY = '--plan-only' in sys.argv
    os.makedirs(OUTD, exist_ok=True)
    settings = {'FORCE_OCR': os.environ.get('FORCE_OCR') == '1', 'OCR': os.environ.get('OCR', 'auto'),
                'OCR_LANG': os.environ.get('OCR_LANG') or None, 'plan_only': PLAN_ONLY,
                'thresholds': {'cer_ok': CER_OK, 'cer_bad': CER_BAD, 'ocr_dpi': OCR_DPI, 'sample': SAMPLE, 'extra': EXTRA,
                               'min_scored': MIN_SCORED, 'score_min_chars': SCORE_MIN_CHARS,
                               'score_image_cover': SCORE_IMAGE_COVER, 'cjk_chars': CJK_CHARS, 'cjk_share': CJK_SHARE,
                               'image_only_cover': IMAGE_ONLY_COVER, 'ocr_layer_cover': OCR_LAYER_COVER,
                               'pua_check': PUA_CHECK, 'front_skip_from': FRONT_SKIP_FROM,
                               'front_skip_share': FRONT_SKIP_SHARE, 'front_skip_min': FRONT_SKIP_MIN,
                               'outside_min_chars': OUTSIDE_MIN_CHARS, 'gap_share': GAP_SHARE, 'gap_min_breaks': GAP_MIN_BREAKS,
                               'narrow_gap': NARROW_GAP, 'narrow_book_rate': NARROW_BOOK_RATE, 'scan_min_cover': SCAN_MIN_COVER,
                               'tile_dpi': TILE_DPI, 'tile_px': TILE_PX, 'tile_max': TILE_MAX}}
    J = os.path.join(OUTD, 'intake.json'); PDF_OUT = os.path.join(OUTD, 'intake.pdf')
    src_sha = sha256(SRC)
    # an earlier finished intake for the same file and settings is reused (batch estimate → run, FROM= reruns)
    if os.path.exists(J) and not PLAN_ONLY:
        old = json.load(open(J))
        same = old.get('original', {}).get('sha256') == src_sha and {k: old.get('settings', {}).get(k) for k in ('FORCE_OCR', 'OCR', 'OCR_LANG')} \
               == {k: settings[k] for k in ('FORCE_OCR', 'OCR', 'OCR_LANG')}
        if os.environ.get('INTAKE_REUSE') == '1' and old.get('original', {}).get('sha256') == src_sha:
            same = True                                  # FROM= rerun: the saved reply was written for this intake result
        elif same and old.get('status') == 'skipped':    # skipped by an older intake: still a real tag tree today?
            with pikepdf.open(SRC) as p_: same = tagged(p_)
        if same and old.get('status') == 'skipped' or same and old.get('status') == 'done' and (not old.get('result', {}).get('pdf') or
                (os.path.exists(PDF_OUT) and sha256(PDF_OUT) == old['result'].get('sha256'))):
            if old.get('status') == 'done':             # derived only: the glance and intake.md follow the current code
                old['glance'] = intake_glance(old); json.dump(old, open(J, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
            write_md(old, os.path.join(OUTD, 'intake.md'))
            print(f'intake: reusing the earlier intake ({old["status"]}: {old.get("summary")})'); return 0
    rec = {'schema': SCHEMA, 'written': now(), 'original': {'file': os.path.basename(SRC), 'sha256': src_sha},
           'settings': settings, 'tools': {}, 'status': None, 'summary': None, 'flags': [], 'steps': [], 'checks': {},
           'result': {'pdf': None}, 'review': {'ocr_text_approved': None}}     # set by review_ocr.py (rule 2)
    page_labels = {}
    def save():
        cited = {int(p) for f in rec['flags'] for p in f.get('pages') or []} | set((rec.get('plan') or {}).get('ocr_pages') or []) \
            | {int(p) for k in ('pages_with_ocr_text', 'image_pages_without_text') for p in (rec.get('ocr') or {}).get(k) or []} \
            | {int(r['page']) for r in (rec.get('text_test') or {}).get('pages') or [] if r.get('page') is not None}
        rec['cited_labels'] = {str(p): page_labels[p] for p in sorted(cited) if p in page_labels}    # printed labels for intake.md
        for p, lab in ((rec.get('spreads') or {}).get('printed') or {}).items():   # a spread: both printed numbers
            if int(p) in cited and page_labels.get(int(p), str(p)) == str(p): rec['cited_labels'][str(p)] = lab
        if rec.get('status') != 'skipped': rec['glance'] = intake_glance(rec)   # intake.md's "Overview" numbers
        json.dump(rec, open(J, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        write_md(rec, os.path.join(OUTD, 'intake.md'))
    def flag(what, why, pages=None, check=True):
        rec['flags'].append({'what': what, 'why': why, **({'pages': pages} if pages else {}), 'check': check})
    def stop(status, why, code):
        rec['status'] = status; rec['summary'] = why; save(); print(f'intake: {status}: {why}'); return code
    if os.path.exists(PDF_OUT): os.remove(PDF_OUT)
    # ---- open
    try: pdf = pikepdf.open(SRC)
    except pikepdf.PasswordError: return stop('stopped', 'the PDF needs a password to open; a person must supply an unlocked copy', 3)
    except Exception as e: return stop('failed', f'the PDF could not be opened ({str(e)[:120]})', 1)
    rec['original']['pages'] = len(pdf.pages); rec['original']['encrypted'] = pdf.is_encrypted
    if '/PageLabels' in pdf.Root:
        try: page_labels.update({i: str(pg.label) for i, pg in enumerate(pdf.pages, 1)})
        except Exception: pass
    rec['original']['pdf_version'] = support.version(pdf)
    why = support.unsupported(pdf)                     # PDF 2.0 / namespaced tags: tagged or not, a person takes it
    if why:
        pdf.close(); flag('Not supported yet: PDF 2.0', why); return stop('stopped', why, 3)
    rec['original']['producer'] = str(pdf.docinfo.get('/Producer', '')).strip() or None if '/Info' in pdf.trailer else None
    ts, tinfo = tag_status(pdf, figures=True)
    rec['tag_tree'] = {'status': ts, **{k: v for k, v in tinfo.items() if k != 'figures'}}
    if ts == 'tagged':
        pdf.close(); rec['summary'] = 'none (already tagged)'; rec['status'] = 'skipped'; save()
        print('intake: already tagged, nothing to do'); return 0
    if ts == 'placeholder':                              # 10.5: a tree with no text structure is no tag tree; it is set aside
        figs = tinfo.get('figures') or []
        rec['tag_tree']['figures'] = figs                # the publisher's alt text, recorded only (passing it on is a later step)
        pub = [f for f in figs if f['kind'] == 'publisher']; phd = [f for f in figs if f['kind'] == 'placeholder']
        els = ', '.join(f'{k.lstrip("/")} {v}' for k, v in tinfo['elements'].items())
        flag('Placeholder tag tree', f'the PDF has a tag tree with no text structure ({els}; MarkInfo '
             f'{ {None: "missing", True: "true", False: "Marked false"}[tinfo["markinfo"]]}): it is treated as untagged. The old '
             'tree is removed from intake\'s working copy (the original is unchanged) and the book is auto-tagged'
             + (f'. {len(phd)} of its figures had alt text that says nothing (e.g. "{phd[0]["alt"]}"): recorded as placeholder alt' if phd else ''),
             check=False)
        if pub:
            flag('Publisher alt text', f'{len(pub)} figures in the old tag tree carry the publisher\'s alt text (e.g. "{pub[0]["alt"][:80]}"). '
                 'It is recorded in intake.json (tag_tree.figures) but not yet carried into intake.pdf: a person compares it '
                 'with the alt text the pipeline writes', sorted({f['page'] for f in pub if f['page']})[:20])
    # ---- 1. triage
    t0 = time.time()
    inv = [page_inventory(pg) for pg in pdf.pages]
    empty = empty_text_pages(SRC, inv)                   # text operators that draw no character: judged by the images
    for i in empty: inv[i - 1] = page_inventory(pdf.pages[i - 1], text_drawn=False)
    pdf.close()
    kinds = collections.defaultdict(list)
    for i, x in enumerate(inv, 1): kinds[x['kind']].append(i)
    rec['triage'] = {'pages': {k: v for k, v in kinds.items()}, 'counts': {k: len(v) for k, v in kinds.items()},
                     'seconds': round(time.time() - t0, 1)}
    sp = detect_spreads(SRC)                             # 4.1: two printed pages per PDF page (never split)
    if sp: rec['spreads'] = sp
    if empty:
        rec['triage']['empty_text_pages'] = empty
        flag('Text objects with no characters', f'{len(empty)} pages have text operators that draw no character (e.g. an empty '
             'text object over a scan): they are triaged by their images, so a scanned page is OCR\'d', empty[:20], check=False)
    scan_pages = kinds['image-only']; text_pages = kinds['text'] + kinds['ocr-layer']
    low = sorted(i for i in scan_pages if (inv[i - 1]['scan_dpi'] or 0) < OCR_DPI)
    if low: rec['triage']['low_dpi_pages'] = {str(i): inv[i - 1]['scan_dpi'] for i in low}
    if not text_pages and not scan_pages: return stop('stopped', 'no page has text or a page image: nothing to tag', 3)
    # ---- tools
    tv = tool_versions(); rec['tools'] = tv
    if not tv['tesseract']: return stop('failed', INSTALL['tesseract'], 1)
    # ---- language (3.7): scripts in the text layer, and Tesseract's script detection on image-only pages
    doc = pdfium.PdfDocument(SRC); tmp = tempfile.mkdtemp(prefix='intake_', dir=OUTD)
    try:
        sc = collections.Counter(); viet = 0
        step = max(1, len(text_pages) // 40)
        for i in text_pages[::step]:
            t_ = doc[i - 1].get_textpage().get_text_range(); sc += scripts(t_); viet += sum(1 for ch in t_ if ch in VIET_LETTERS)
        osd = collections.Counter()
        for i in scan_pages[:: max(1, len(scan_pages) // 5)][:5]:
            img = os.path.join(tmp, f'osd{i}.png'); render(doc, i - 1, OCR_DPI, img)
            s = osd_script(img)
            if s: osd[s] += 1
        found_ = collections.Counter({OSD_SCRIPTS.get(s, s): n for s, n in osd.items()})   # "Korean" and "Hangul" alike
        lang_why = []; han_no_kana = False
        if settings['OCR_LANG']:
            ocr_lang = score_lang = settings['OCR_LANG']; lang_why.append('set by OCR_LANG')
        else:                                            # 3.7: OCR on the pages to be OCR'd uses eng unless OCR_LANG says
            langs = ['eng']                              #   otherwise; these packs only read sample pages for the 1.2 test
            if sc['kana'] or found_['kana']: langs.append('jpn'); lang_why.append('kana found: Japanese (text-layer test only)')
            if sc['hangul'] or found_['hangul']: langs.append('kor'); lang_why.append('hangul found: Korean (text-layer test only)')
            if viet >= VIET_MIN: langs.append('vie'); lang_why.append('Vietnamese letters found (text-layer test only)')
            han_no_kana = (sc['han'] or found_['han']) and 'jpn' not in langs
            if han_no_kana: lang_why.append('Chinese characters with no kana: Chinese or Japanese is not guessed')
            score_lang, ocr_lang = '+'.join(langs), 'eng'
        def installed(lang, what):
            missing = [l for l in lang.split('+') if l not in tv['tesseract_langs']]
            if missing: flag('OCR language', f'Tesseract has no language pack for {", ".join(missing)}: {what} used what is installed '
                             '(brew install tesseract-lang)')
            return '+'.join(l for l in lang.split('+') if l in tv['tesseract_langs']) or 'eng'
        ocr_lang = installed(ocr_lang, 'OCR')
        score_lang = ocr_lang if score_lang == settings['OCR_LANG'] else installed(score_lang, 'the text-layer test')
        rec['language'] = {'text_layer_scripts': dict(sc), 'scan_scripts': dict(osd), 'ocr_lang': ocr_lang, 'score_lang': score_lang,
                           'why': lang_why}
        cjk_seen = any(sc[k] or found_[k] for k in ('han', 'kana', 'hangul'))
        def lang_flag(pages):                         # a CHECK only when OCR text is planned (plan-only) or kept (run)
            if cjk_seen and pages and not any(l in ocr_lang for l in ('jpn', 'chi', 'kor')):
                flag('OCR language', 'Chinese, Japanese or Korean text was found and OCR_LANG names no CJK pack, so OCR used English '
                     'only. Set OCR_LANG (e.g. chi_tra+eng, jpn+eng or kor+eng) and run again, or a person reads the CJK text on the '
                     'OCR\'d pages', pages)
        cjk_pack = any(l in score_lang for l in ('jpn', 'chi', 'kor'))
        # ---- every text page: private-use characters (3.6), text outside the visible page area, word breaks (3.4)
        L = layer_scan(doc, text_pages)
        pua, pua_pages, layer_text, visible_text, outside = L['pua'], L['pua_pages'], L['text'], L['visible'], L['outside']
        rec['outside_page_area'] = {'chars': sum(outside.values()), 'pages': sorted(outside), 'per_page': {str(k): v for k, v in outside.items()}}
        if outside:
            flag('Text outside the page area', f'{sum(outside.values())} characters on {len(outside)} pages lie outside the visible '
                 'page area (CropBox): no one sees them on screen or in print, but a screen reader reads them unless they are '
                 'marked as artifacts (e.g. a printer\'s slug). Not used in the text-layer test; first 20 pages listed', sorted(outside)[:20])
        gaps, narrow = L['gaps'], L['narrow']
        rec['word_breaks'] = {'space_characters': L['real'], 'gaps_only': L['gen'], 'pages_relying_on_gaps': gaps,
                              'share_of_text_pages': round(len(gaps) / max(len(text_pages), 1), 3),
                              'narrow_gaps': L['narrow_total'], 'narrow_per_text_page': round(L['narrow_total'] / max(len(text_pages), 1), 2),
                              'pages_with_narrow_gaps': {str(k): v for k, v in narrow.items()}}
        if len(gaps) / max(len(text_pages), 1) > GAP_SHARE:
            flag('Word breaks rely on gaps', f'{len(gaps) / max(len(text_pages), 1):.0%} of text pages ({len(gaps)} of {len(text_pages)}) '
                 'mark most word breaks only by a gap between letters, with no space character (checklist 3.4). A note: readers '
                 'infer such gaps differently; narrow ones are checked separately', check=False)
        rate = L['narrow_total'] / max(len(text_pages), 1)
        if L['narrow_total']:
            worst = [p for p, _ in sorted(narrow.items(), key=lambda kv: (-kv[1], kv[0]))[:20]]
            flag('Narrow word gaps', f'{rate:.1f} narrow word breaks per text page on average ({L["narrow_total"]} in all): gaps '
                 f'narrower than {NARROW_GAP:.0%} of the type size with no space character (checklist 3.4), where readers such as '
                 'Acrobat may run words together (e.g. "concernedwithChinese" on bringing PDF 86). '
                 + (f'At or above {NARROW_BOOK_RATE} per page: a CHECK. The 20 pages with the most are listed' if rate >= NARROW_BOOK_RATE
                    else f'Below {NARROW_BOOK_RATE} per page: a note'), sorted(worst) if rate >= NARROW_BOOK_RATE else None,
                 check=rate >= NARROW_BOOK_RATE)
        n_pua = sum(pua.values())
        rec['private_use'] = {'count': n_pua, 'pages': pua_pages, 'ranges': private_use_ranges(pua)}
        if n_pua > PUA_CHECK:
            top = rec['private_use']['ranges'][0]
            flag('Private-use characters', f'{n_pua} characters on {len(pua_pages)} pages of the text layer use private-use codes '
                 f'(most: {top["range"]}, {top["what"]}): a screen reader may read nothing or nonsense for them (checklist 3.6). '
                 'Ranges in intake.json; first 20 pages listed', pua_pages[:20])
        # ---- 2. text-layer test (1.2)
        tt = {'pages': [], 'verdict': 'not tested', 'median_cer': None}
        if text_pages:
            def unscorable(i):
                """Why page i cannot be scored fairly against OCR, or None."""
                if inv[i - 1]['image_cover'] >= SCORE_IMAGE_COVER:
                    return 'image', f'images cover {inv[i - 1]["image_cover"]:.0%} of the page'
                t = visible_text[i]; n = len(norm(t))
                if n < SCORE_MIN_CHARS: return 'short', f'only {n} characters in the text layer'
                s = scripts(t); cjk = s['han'] + s['kana'] + s['hangul']; letters = sum(s.values()) or 1
                if not cjk_pack and (cjk >= CJK_CHARS or cjk / letters >= CJK_SHARE):
                    return 'cjk', f'{cjk} CJK characters and the OCR language has no CJK pack'
                m = math_symbols(t)
                if m >= MATH_SYMBOLS_NO_FONT or inv[i - 1]['math_fonts'] and m >= MATH_SYMBOLS:
                    return 'math', f'math on the page ({m} math symbols or Greek letters' + (', math fonts' if inv[i - 1]['math_fonts'] else '') \
                        + '): OCR cannot read it'
                return None
            why_not = {i: unscorable(i) for i in text_pages}
            tt['unscorable_in_book'] = dict(collections.Counter(w[0] for w in why_not.values() if w))
            scorable = [i for i in text_pages if not why_not[i]]
            skip = max(FRONT_SKIP_MIN, math.ceil(FRONT_SKIP_SHARE * len(text_pages))) if len(text_pages) >= FRONT_SKIP_FROM else 0
            body = text_pages[skip:]; tt['front_matter_skipped'] = text_pages[:skip]
            ns = min(SAMPLE, len(body))                   # fewer text pages than SAMPLE: take them all
            spread = sorted({body[int(k * (len(body) - 1) / max(ns - 1, 1))] for k in range(ns)})
            used, chosen, rows = set(spread), [i for i in spread if not why_not[i]], []
            for i in spread:                             # an unscorable spread page is replaced by the next scorable page
                if not why_not[i]: continue              #   further into the book (never an earlier one)
                rep_ = next((q for q in scorable if q > i and q not in used), None)
                rows.append({'page': i, 'verdict': 'not scored', 'reason': why_not[i][1], 'replaced_by': rep_})
                if rep_ is not None: used.add(rep_); chosen.append(rep_)
            sus = []
            for i in text_pages:
                if len(sus) >= EXTRA: break
                if i in used: continue
                t = layer_text[i]
                s = scripts(t); words = t.split()
                if s['private_use'] > 5 or sum(1 for w in words if len(w) >= 25 and w.isalpha()) >= 3: sus.append(i)
            for i in sus:
                if why_not[i]: rows.append({'page': i, 'verdict': 'not scored', 'reason': why_not[i][1], 'suspicious': True})
            t1 = time.time()
            for i in sorted(chosen + [i for i in sus if not why_not[i]]):
                layer = visible_text[i]; s = scripts(layer)
                img = os.path.join(tmp, f'p{i}.png'); render(doc, i - 1, OCR_DPI, img)
                ocr = tesseract_text(img, score_lang); os.remove(img)
                a, b = norm(ocr), norm(layer)
                ci, ca = cer(a, b), bag_diff(a, b); c = min(ci, ca)
                ma, mb = marked_letters(a), marked_letters(b)
                if c > CER_OK and mb >= MARKS_MIN and mb >= MARKS_MISSED * ma:     # the layer has the marks, OCR did not read them
                    a2, b2 = strip_marks(a), strip_marks(b); c2 = min(cer(a2, b2), bag_diff(a2, b2))
                    if c2 <= CER_OK:                     # the letters agree: OCR's fault, not the layer's; never passed, a person looks
                        rows.append({'page': i, 'verdict': 'not scored', 'reason': f'OCR did not read the diacritics ({mb} marked '
                                     f'letters in the text layer, {ma} in OCR; {c:.0%} with them, {c2:.0%} without)',
                                     'marks': True, 'cer_with_marks': round(c, 3), 'cer_without_marks': round(c2, 3)})
                        continue
                v = 'usable' if c <= CER_OK else ('unusable' if c > CER_BAD else 'doubtful')
                if v == 'usable' and ci > CER_OK: v = 'usable (reading order differs)'
                wo, wl = len(ocr.split()), len(layer.split())
                rows.append({'page': i, 'chars': len(b), 'ocr_chars': len(a), 'suspicious': i in sus, 'cer': round(c, 3),
                             'cer_in_order': round(ci, 3), 'cer_any_order': round(ca, 3), 'verdict': v,
                             'words_ratio': round(wl / max(wo, 1), 2), 'private_use': s['private_use']})
            tt['pages'] = sorted(rows, key=lambda r: r['page'])
            scored = [r for r in tt['pages'] if 'cer' in r]
            tt['scored'] = len(scored); tt['not_scored'] = len(tt['pages']) - len(scored)
            mk = [r['page'] for r in tt['pages'] if r.get('marks')]
            if mk:                                       # on a scan's OCR layer the marks may be missing from the layer: a CHECK;
                tt['diacritics_not_read_pages'] = mk     #   on born-digital text it is the OCR that missed them: a note
                mk_ocr = [p for p in mk if inv[p - 1]['kind'] == 'ocr-layer']; mk_txt = [p for p in mk if p not in mk_ocr]
                if mk_ocr: flag('Text layer: diacritics', 'on these sample pages (an existing OCR layer) OCR read the letters but not '
                                'their diacritics (tone marks, accents), so the page was not scored: a person compares the marks in '
                                'the text layer with the page image', mk_ocr)
                if mk_txt: flag('Text layer: diacritics', 'on these sample pages OCR read the letters but not the diacritics (tone '
                                'marks, accents) that the born-digital text layer has, so the page was not scored (the OCR missed '
                                'them, not the text layer)', mk_txt, check=False)
            mp = [r['page'] for r in tt['pages'] if r.get('verdict') == 'not scored' and str(r.get('reason', '')).startswith('math')]
            if mp: tt['math_pages_not_scored'] = mp
            if scored:
                med = statistics.median(r['cer'] for r in scored); tt['median_cer'] = round(med, 3)
            if len(scored) < MIN_SCORED:
                tt['verdict'] = 'not enough pages scored'
                flag('Text layer', f'only {len(scored)} sample page{"s" if len(scored) != 1 else ""} could be scored (fewer than '
                     f'{MIN_SCORED}): the text layer was not tested enough; a person should compare a few pages by eye')
            else:
                tt['verdict'] = 'usable' if med <= CER_OK else ('unusable' if med > CER_BAD else 'doubtful')
            if scored:
                bad = [r['page'] for r in scored if r['verdict'] == 'unusable']
                if bad and tt['verdict'] != 'unusable':
                    flag('Text layer', 'these sample pages have an unusable text layer although most do not', bad)
                tt['doubtful_pages'] = [r['page'] for r in scored if r['verdict'] == 'doubtful']
                runs = [r['page'] for r in scored if r.get('words_ratio', 1) < SPACING_LOW]
                if runs:
                    tt['words_run_together_pages'] = runs
                    flag('Words run together', 'the text layer has fewer word breaks than the printed page (checklist 3.4): '
                         'a screen reader may read several words as one', runs)
            tt['seconds'] = round(time.time() - t1, 1)
        rec['text_test'] = tt
        # ---- 2b. an existing OCR layer on scanned pages (1.2, 3.1, 3.7): read again by a different model, CHECK only
        ocrl = [i for i in text_pages if inv[i - 1]['kind'] == 'ocr-layer'
                or inv[i - 1]['invisible_ops'] and inv[i - 1]['image_cover'] >= OCR_LAYER_COVER]
        if ocrl:
            ol = {'pages': [], 'verdict': 'not tested', 'median_cer': None, 'sample': OCRL_SAMPLE}
            skip = max(FRONT_SKIP_MIN, math.ceil(FRONT_SKIP_SHARE * len(ocrl))) if len(ocrl) >= FRONT_SKIP_FROM else 0
            body = ocrl[skip:] or ocrl; ns = min(OCRL_SAMPLE, len(body))
            pick = sorted({body[int(k * (len(body) - 1) / max(ns - 1, 1))] for k in range(ns)})
            from lib import plumb_fix  # noqa: F401
            import pdfplumber
            t1 = time.time(); mv_ocr = mv_layer = 0; mark_pages = []
            with pdfplumber.open(SRC) as pl:
                for i in pick:
                    page = doc[i - 1]; layer = page.get_textpage().get_text_bounded(*page.get_cropbox())
                    alt = ''.join(c['text'] for c in pl.pages[i - 1].chars)
                    src_ = 'pdfium'
                    if len(INVISIBLE.sub('', alt)) > 2 * len(INVISIBLE.sub('', layer)) + 20:   # e.g. Acrobat's hidden vertical OCR
                        layer, src_ = alt, 'pdfplumber'
                    s = scripts(layer)
                    script = max(('kana', 'hangul', 'han'), key=lambda k: s[k]) if s['kana'] + s['hangul'] + s['han'] >= CJK_CHARS else 'latin'
                    if s['kana'] >= CJK_CHARS: script = 'kana'
                    model = SCRIPT_MODELS[script]
                    if any(m not in tv['tesseract_langs'] for m in model.split('+')):
                        ol['pages'].append({'page': i, 'verdict': 'not scored', 'reason': f'Tesseract model {model} is not installed'}); continue
                    f = norm if script == 'latin' else norm_cjk
                    if len(f(layer)) < SCORE_MIN_CHARS:
                        ol['pages'].append({'page': i, 'verdict': 'not scored', 'reason': f'only {len(f(layer))} characters in the OCR layer'}); continue
                    img = os.path.join(tmp, f'ol{i}.png'); render(doc, i - 1, OCR_DPI, img)
                    words, ocr = tesseract_words(img, model); os.remove(img)
                    m = max(math_symbols(ocr), math_symbols(layer))
                    if script == 'latin' and m >= MATH_SYMBOLS:            # (CJK text uses ～ and stray Greek: not math)
                        ol['pages'].append({'page': i, 'verdict': 'not scored', 'reason': f'math on the page ({m} math symbols or Greek letters)'}); continue
                    a, b = f(ocr), f(layer); c = min(cer(a, b), bag_diff(a, b))
                    a2, b2 = strip_marks(a), strip_marks(b); c2 = min(cer(a2, b2), bag_diff(a2, b2))   # the letters alone
                    mo, ml_ = (marked_vowels(ocr), marked_vowels(layer)) if script == 'latin' and c2 <= CER_BAD else (None, None)
                    lacks = mo is not None and mo >= MARKED_VOWELS and ml_ < MARKS_LAYER_SHARE * mo
                    c_marks = c
                    if lacks: c = c2                     # the marks are what differ: the page is judged on its letters, the marks CHECKed
                    toks = set(re.sub(r'\W', '', x.lower()) for x in layer.split())
                    conf = [re.sub(r'\W', '', t.lower()) for t, cf in words if cf >= 90 and len(re.sub(r'\W', '', t)) >= 3]
                    row = {'page': i, 'script': script, 'model': model, 'layer_read_with': src_, 'chars': len(b), 'cer': round(c, 3),
                           'verdict': 'usable' if c <= CER_OK else ('unusable' if c > CER_BAD else 'doubtful'),
                           'confident_words_missing': round(sum(1 for t in conf if t not in toks) / len(conf), 3) if conf and script == 'latin' else None}
                    if mo is not None:                   # marks count only where the letters agree (junk pages have stray marks)
                        row['marked_vowels_ocr'], row['marked_vowels_layer'] = mo, ml_; mv_ocr += mo; mv_layer += ml_
                        if lacks: mark_pages.append(i); row['cer_with_marks'] = round(c_marks, 3)
                    ol['pages'].append(row)
            scored = [r for r in ol['pages'] if 'cer' in r]; ol['scored'] = len(scored); ol['seconds'] = round(time.time() - t1, 1)
            if any(r.get('layer_read_with') == 'pdfplumber' for r in scored): ol['note'] = 'PDFium reads little of this OCR layer; read with pdfplumber'
            if scored:
                med = statistics.median(r['cer'] for r in scored); ol['median_cer'] = round(med, 3)
                ol['verdict'] = 'usable' if med <= CER_OK else ('unusable' if med > CER_BAD else 'doubtful')
                worst = [r['page'] for r in sorted(scored, key=lambda r: -r['cer']) if r['cer'] > CER_OK]
                if ol['verdict'] != 'usable':
                    flag('OCR layer', f'the existing OCR layer on the scanned pages and a fresh reading by a different OCR model disagree '
                         f'(median character error {med:.0%} on {len(scored)} sample pages; worst first): a person compares these pages '
                         'with the page image. The layer is kept as it is (it may be the library\'s record)', worst[:20])
                elif worst:
                    flag('OCR layer', f'on these sample pages the existing OCR layer and a fresh OCR reading partly disagree (over '
                         f'{CER_OK:.0%}): compare them by eye', worst[:20])
                n_lat = sum(1 for r in scored if 'marked_vowels_ocr' in r)
                if n_lat and mv_ocr / n_lat >= MARKED_VOWELS and mv_layer < MARKS_LAYER_SHARE * mv_ocr:
                    ol['diacritics'] = {'marked_vowels_ocr': mv_ocr, 'marked_vowels_layer': mv_layer, 'pages': mark_pages}
                    flag('OCR layer: diacritics', f'the page images show diacritics the existing OCR layer lacks ({mv_ocr} marked vowels '
                         f'read on {n_lat} sample pages, {mv_layer} in the layer: e.g. ŏ/ŭ lost as o/u). The OCR model reads the marks '
                         'only roughly, so a person compares the pages; the layer is not changed', mark_pages[:20] or None)
            else:
                ol['verdict'] = 'not enough pages scored'
            rec['ocr_layer_test'] = ol
        # ---- the plan
        force = tt['verdict'] == 'unusable'
        plan = {'ocr_mode': None, 'ocr_pages': [], 'autotag': True}
        # born-digital text or math: OCR may simply not read it, so FORCE_OCR (which would replace the text) is not suggested
        written = BORN_DIGITAL.search(rec['original'].get('producer') or '') or tt.get('math_pages_not_scored') \
            or sum(1 for i in text_pages if inv[i - 1]['math_fonts']) >= max(3, 0.1 * len(text_pages))
        why_ocr = (f'the producer ({rec["original"]["producer"][:40]}) writes text rather than scanning it' if BORN_DIGITAL.search(rec['original'].get('producer') or '')
                   else 'the book has math') if written else None
        if force and not settings['FORCE_OCR']:
            rec['plan'] = plan
            if written:
                flag('Text layer unusable', f'OCR and the text layer disagree (median character error {tt["median_cer"]:.0%}), but '
                     f'{why_ocr}: OCR may simply not read this text (math, tone marks, tables). A person compares a few sample '
                     'pages with the page image and decides; replacing the text with OCR is not suggested')
                return stop('stopped', f'text layer unusable by OCR (median CER {tt["median_cer"]:.0%}), but {why_ocr}: a person compares pages and decides', 3)
            flag('Text layer unusable', f'OCR and the text layer disagree (median character error {tt["median_cer"]:.0%}). '
                 'Run again with FORCE_OCR=1 to replace the text with OCR text over page images, or send the book to a person')
            return stop('stopped', f'text layer unusable (median CER {tt["median_cer"]:.0%}): flagged; FORCE_OCR=1 would OCR every page', 3)
        dpages = tt.get('doubtful_pages') or None
        if tt['verdict'] == 'doubtful':
            flag('Text layer', f'OCR and the text layer partly disagree (median character error {tt["median_cer"]:.0%}): '
                 'a person should compare a few pages' + (', starting with the doubtful ones listed' if dpages else '')
                 + (f' ({why_ocr}: OCR may not read this text well)' if written else '; FORCE_OCR=1 would replace the text with OCR text'), dpages)
        elif dpages and tt['verdict'] != 'unusable':
            flag('Text layer', f'OCR and the text layer partly disagree ({CER_OK:.0%}–{CER_BAD:.0%}) on these sample pages: '
                 'compare them by eye', dpages)
        if force:
            plan['ocr_mode'] = 'force'; plan['ocr_pages'] = list(range(1, len(inv) + 1))
            flag('Force OCR', 'FORCE_OCR=1: every page is now a page image with OCR text over it; the original text layer '
                 'was replaced. OCR text is machine output: a person should check it before it ships')
        elif scan_pages:
            if settings['OCR'] == 'off':
                flag('OCR off', 'OCR=off: these image-only pages have no text for a screen reader', scan_pages)
            else: plan['ocr_mode'] = 'skip'; plan['ocr_pages'] = scan_pages
        rec['plan'] = plan
        # ---- CJK text on the pages to be OCR'd (3.7): never guessed; OCR_LANG must name the language
        if plan['ocr_mode'] == 'skip' and plan['ocr_pages']:
            have = [l for l in CJK_PROBE_LANGS.split('+') if l in tv['tesseract_langs']]
            if not have:
                flag('CJK check not run', f'none of the Tesseract packs {CJK_PROBE_LANGS} is installed: CJK text on the OCR pages '
                     'cannot be detected (brew install tesseract-lang)')
            else:
                found = {}
                for p in plan['ocr_pages']:
                    img = os.path.join(tmp, f'cjk{p}.png'); render(doc, p - 1, OCR_DPI, img)
                    n = cjk_probe(img, '+'.join(have)); os.remove(img)
                    if n: found[p] = n
                cjk_lang = any(l in ocr_lang for l in ('chi', 'jpn', 'kor'))
                vhave = [l for l in VERT_PROBE_LANGS.split('+') if l in tv['tesseract_langs']]
                vt = {}                                  # vertical packs on a few sample pages only: up to VERT_SAMPLE of the
                weak = [p for p in plan['ocr_pages'] if CJK_PROBE_MIN // 2 <= found.get(p, 0) < CJK_PROBE_MIN]
                if weak and vhave and '_vert' not in ocr_lang:   # pages where the horizontal packs found a little CJK
                    for p in weak[:: max(1, len(weak) // VERT_SAMPLE)][:VERT_SAMPLE]:   # (vertical text reads poorly with
                        img = os.path.join(tmp, f'vert{p}.png'); render(doc, p - 1, OCR_DPI, img)   # them), spread
                        vt[p] = cjk_probe(img, '+'.join(vhave)); os.remove(img)
                weak_cjk = any(n >= CJK_PROBE_MIN for n in vt.values())   # one confirmed: every such page counts as CJK
                cjk_pages = sorted(p for p in plan['ocr_pages'] if found.get(p, 0) >= CJK_PROBE_MIN or weak_cjk and p in weak)
                rec['cjk_probe'] = {'langs': '+'.join(have), 'min_chars': CJK_PROBE_MIN, 'min_conf': CJK_PROBE_CONF,
                                    'cjk_characters': {str(p): n for p, n in found.items()}, 'cjk_pages': cjk_pages}
                vert = []
                if cjk_pages and vhave and '_vert' not in ocr_lang:
                    for p in sorted([p for p in cjk_pages if p not in vt], key=lambda p: -found.get(p, 0))[:max(0, VERT_SAMPLE - len(vt))]:
                        img = os.path.join(tmp, f'vert{p}.png'); render(doc, p - 1, OCR_DPI, img)
                        vt[p] = cjk_probe(img, '+'.join(vhave)); os.remove(img)
                    trial = sorted(p for p in vt if p in cjk_pages)
                    vert = [p for p in trial if vt[p] >= VERT_GAIN * found.get(p, 0)]
                    rec['cjk_probe']['vertical_trial'] = {'langs': '+'.join(vhave), 'gain': VERT_GAIN, 'pages': trial,
                                                          'cjk_characters_vertical': {str(p): n for p, n in vt.items()}, 'vertical_pages': vert}
                    if len(vert) * 2 <= len(trial): vert = []          # most trial pages must read better vertically
                vhint = (f' Vertical text is likely (on {len(vert)} of the trial pages, the _vert packs read {VERT_GAIN}x or more of the '
                         'CJK characters): add the matching _vert pack, e.g. OCR_LANG=jpn_vert+jpn+eng, kor_vert+kor+eng or '
                         'chi_tra_vert+chi_tra+eng') if vert else ''
                if cjk_pages and not cjk_lang:
                    flag('OCR language needed', 'these pages to be OCR\'d hold Chinese, Japanese or Korean text, and the language is never '
                         'guessed: set OCR_LANG (e.g. chi_tra+eng, chi_sim+eng, jpn+eng, kor+eng) and run again.' + vhint, cjk_pages)
                    return stop('stopped', f'CJK text on pages to be OCR\'d ({", ".join(map(str, cjk_pages))}): set OCR_LANG and run again'
                                + (' (vertical text likely: add a _vert pack)' if vert else ''), 3)
                if vert:
                    flag('Vertical text likely', f'OCR_LANG={ocr_lang} has no _vert pack, but these pages read better with one.' + vhint, vert)
                if cjk_pages:
                    flag('CJK OCR: needs a person', f'these pages hold CJK text, OCR\'d with OCR_LANG={ocr_lang}: CJK OCR is often wrong '
                         '(sojourners\' glossary: many entries junk) and multi-column CJK lists may be read across the columns; a person '
                         'checks the text and its reading order', cjk_pages)
        if rec.get('spreads'):                           # 6.1-6.4: the tag tree reads a spread half by half
            vt = ((rec.get('cjk_probe') or {}).get('vertical_trial') or {}).get('vertical_pages')
            right_first = bool(rec['spreads']['vertical_fonts'] or vt or '_vert' in ocr_lang)
            rec['spreads']['order'] = 'right half first (vertical CJK)' if right_first else 'left half first'
            pr = rec['spreads']['printed']
            flag('Two printed pages per PDF page', f'these pages each hold two printed pages side by side (a spread; pages are never '
                 f'split). After auto-tagging the tag tree reads each spread half by half, {rec["spreads"]["order"]}'
                 + (f'; both printed page numbers were read on {len(pr)} of them and are cited as "PDF N (printed a–b)"' if pr else '')
                 + ': a person checks the reading order and the page numbers', rec['spreads']['pages'][:20])
        if PLAN_ONLY:                                    # at run time these are raised for the pages that keep OCR text
            lowp = [p for p in plan['ocr_pages'] if p in low]
            if lowp: flag('Low-resolution scans', f'scanned below {OCR_DPI} dpi (checklist 2.1): OCR will read them enlarged, '
                          'so recognition errors are more likely (a note: a full run flags the pages that keep OCR text)',
                          lowp, check=False)
            if plan['ocr_mode'] == 'force': lang_flag(plan['ocr_pages'])     # skip mode: the CJK check above
            rec['status'] = 'planned'; rec['summary'] = describe(rec); save(); print(f'intake plan: {rec["summary"]}'); return 0
        # ---- tools the plan needs
        need = (['ocrmypdf'] if plan['ocr_mode'] else []) + ['java', 'opendataloader_pdf']
        for t in need:
            if not tv.get(t) or t == 'java' and tv['java'] < 11: return stop('failed', INSTALL[t], 1)
        if plan['ocr_mode'] and not re.match(r'^(1[7-9]|[2-9]\d)\.', tv['ocrmypdf'] or ''):
            return stop('failed', f'OCRmyPDF 17 or later is needed (found {tv["ocrmypdf"]}): brew upgrade ocrmypdf', 1)
        before = keepers(SRC); rec['checks']['original'] = {k: v for k, v in before.items() if k != 'page_labels'}
        cur = os.path.join(tmp, 'work.pdf'); shutil.copyfile(SRC, cur)
        if rec['tag_tree']['status'] == 'placeholder':   # set the placeholder tree aside (working copy only), then check nothing moved
            remove_tag_tree(cur); cmp = compare(SRC, cur)
            rec['checks']['placeholder_tree_removed'] = {'pixels_differ': cmp['pixels'], 'text_differs': cmp['text'], 'page_count': cmp['page_count']}
            if cmp['page_count'] or cmp['pixels'] or cmp['text']:
                return stop('failed', f'removing the placeholder tag tree changed pages (appearance {cmp["pixels"][:8]}, text {cmp["text"][:8]}): stopped', 1)
        strip = [p for p in (rec['triage'].get('empty_text_pages') or []) if p in plan['ocr_pages']] if plan['ocr_mode'] == 'skip' else []
        if strip:                                        # OCRmyPDF skips a page with any text object: drop the empty ones first
            done, left = strip_empty_text(cur, strip); cmp = compare(SRC, cur)
            rec['checks']['empty_text_removed'] = {'pages': done, 'left_in_forms': left, 'pixels_differ': cmp['pixels'],
                                                   'text_differs': cmp['text'], 'page_count': cmp['page_count']}
            if cmp['page_count'] or cmp['pixels'] or cmp['text']:
                return stop('failed', f'removing empty text objects changed pages (appearance {cmp["pixels"][:8]}, text {cmp["text"][:8]}): stopped', 1)
            if left: flag('Empty text objects left', 'on these pages the empty text objects sit inside form XObjects and were left as '
                          'they are, so OCRmyPDF may skip the pages: a person checks that they got OCR text', left)
        # ---- 3. OCR
        if plan['ocr_mode']:
            out = os.path.join(tmp, 'ocr.pdf')
            cmd = ['ocrmypdf', '--mode', plan['ocr_mode'], '--output-type', 'pdf', '--optimize', '0', '--oversample', str(OCR_DPI),
                   '-l', ocr_lang] + (['--pages', ','.join(map(str, plan['ocr_pages']))] if plan['ocr_mode'] == 'skip' else []) + [cur, out]
            t1 = time.time(); r = run(cmd)
            rec['steps'].append({'step': 'ocr', 'tool': f'OCRmyPDF {tv["ocrmypdf"]} / Tesseract {tv["tesseract"]}',
                                 'command': ' '.join(cmd[:-2]) + ' <in> <out>', 'seconds': round(time.time() - t1, 1),
                                 'exit': r.returncode, 'log_tail': (r.stderr or '')[-1500:]})
            if r.returncode != 0: return stop('failed', f'OCRmyPDF failed (exit {r.returncode}): see intake.json', 1)
            # image-only pages whose OCR text is not text-like keep no OCR text (they are pictures)
            if plan['ocr_mode'] == 'skip':
                od = pdfium.PdfDocument(out); kept, dropped = [], []
                for i in plan['ocr_pages']:
                    ok, good, toks = textlike(od[i - 1].get_textpage().get_text_range())
                    (kept if ok else dropped).append({'page': i, 'words': good, 'tokens': toks})
                od.close()
                if dropped: strip_ocr_layer(out, [d['page'] for d in dropped])
                rec['ocr'] = {'mode': 'skip', 'pages_with_ocr_text': [k['page'] for k in kept],
                              'image_pages_without_text': [d['page'] for d in dropped], 'per_page': kept + dropped}
                if dropped:
                    flag('Image pages with no text', 'image-only pages where OCR found no readable text: left as pictures '
                         'for the figure step (alt text). Check none is a page of text', [d['page'] for d in dropped], check=False)
            else:
                rec['ocr'] = {'mode': 'force', 'pages_with_ocr_text': plan['ocr_pages']}
            ocr_pages = rec['ocr']['pages_with_ocr_text']
            if plan['ocr_mode'] == 'force': lang_flag(ocr_pages)
            cmp = compare(cur, out, redrawn=set(plan['ocr_pages']) if plan['ocr_mode'] == 'force' else set())
            text_changed_ok = [p for p in cmp['text'] if p in ocr_pages]
            bad_px = cmp['pixels']; bad_tx = [p for p in cmp['text'] if p not in ocr_pages]
            rec['checks']['after_ocr'] = {'pixels_differ': bad_px, 'text_differs_outside_ocr_pages': bad_tx,
                                          'pages_that_gained_text': text_changed_ok, 'page_count': cmp['page_count'],
                                          'keepers': keepers(out)}
            if cmp['page_count'] or bad_px or bad_tx:
                return stop('failed', f'OCR changed pages it should not have (appearance {bad_px[:8]}, text {bad_tx[:8]}): stopped', 1)
            if plan['ocr_mode'] == 'skip':
                missing_txt = [p for p in ocr_pages if p not in text_changed_ok]
                if missing_txt: flag('OCR', 'OCR text was expected on these pages but none was added', missing_txt)
                lowk = [p for p in ocr_pages if p in low]
                if lowk: flag('Low-resolution scans', f'scanned below {OCR_DPI} dpi (checklist 2.1): OCR read them enlarged, '
                              'so recognition errors are more likely', lowk)
            # 3.6: characters the OCR text font could not map come out as U+FFFD or private-use codes
            od = pdfium.PdfDocument(out); bad = {}
            for p_ in ocr_pages:
                t = od[p_ - 1].get_textpage().get_text_range()
                n = sum(1 for ch in t if ch == '\ufffd' or 0xe000 <= ord(ch) <= 0xf8ff)
                if n: bad[p_] = n
            junk = {p_: junk_stats(od[p_ - 1].get_textpage().get_text_range()) for p_ in ocr_pages}
            od.close(); rec['ocr']['unmapped_characters'] = bad
            rec['ocr']['junk'] = {str(p_): j for p_, j in junk.items()}
            jp = sorted(p_ for p_, j in junk.items() if j['tokens'] >= JUNK_MIN_TOKENS and j['share'] >= JUNK_SHARE)
            if jp:
                flag('OCR text looks like junk', f'on these pages {JUNK_SHARE:.0%} or more of the OCR tokens look like junk (symbols, '
                     'capital clusters with no vowel, letters mixed with digits), e.g. ' + ', '.join(f'"{x}"' for x in junk[jp[0]]['examples'][:5])
                     + ': a person compares the text with the page image', jp)
            if bad: flag('OCR characters not mapped', f'{sum(bad.values())} OCR characters have no Unicode value in the text '
                         'layer (checklist 3.6)', sorted(bad))
            cur = out
        # ---- 4. auto-tag
        import opendataloader_pdf
        odl_dir = os.path.join(tmp, 'odl'); os.makedirs(odl_dir, exist_ok=True)
        hidden = bool(plan['ocr_mode']) or bool(kinds['ocr-layer'])           # invisible OCR text must not be filtered out
        kw = dict(input_path=[cur], output_dir=odl_dir, format='tagged-pdf', quiet=True)
        if hidden: kw['content_safety_off'] = 'hidden-text'
        t1 = time.time()
        try: opendataloader_pdf.convert(**kw); err = None
        except Exception as e: err = str(e)[-600:]
        tagged_out = os.path.join(odl_dir, os.path.splitext(os.path.basename(cur))[0] + '_tagged.pdf')
        rec['steps'].append({'step': 'autotag', 'tool': f'OpenDataLoader {tv["opendataloader_pdf"]} (Java {tv["java"]})',
                             'options': {k: v for k, v in kw.items() if k not in ('input_path', 'output_dir')},
                             'seconds': round(time.time() - t1, 1), 'error': err})
        if err or not os.path.exists(tagged_out): return stop('failed', f'auto-tagging failed: {err or "no output file"}', 1)
        cmp = compare(cur, tagged_out, near=True)
        rec['checks']['after_autotag'] = {'pixels_differ': cmp['pixels'], 'text_differs': cmp['text'], 'page_count': cmp['page_count'],
                                          'tile_passed': cmp['tile_passed'], 'reordered': cmp['reordered']}
        if cmp['reordered']:
            flag('Text reordered by auto-tagging', 'on these pages the text holds exactly the same characters as before, in a different '
                 'order: the tagger re-sequenced text runs, so text extraction meets some fragments elsewhere. Nothing was lost; '
                 'the moved fragments are listed in intake.json and review.md, and the tag tree sets the reading order',
                 [r['page'] for r in cmp['reordered']], check=False)
        if cmp['tile_passed']:
            flag('Appearance passed at 300 dpi', f'these pages differed by more than {NEAR:.2%} of a softened 72-dpi page after '
                 f'auto-tagging, but at {TILE_DPI} dpi no quarter-inch tile has more than {TILE_MAX} changed pixels (edge rounding '
                 'where a text run was split)', [r['page'] for r in cmp['tile_passed']], check=False)
        if cmp['page_count'] or cmp['pixels'] or cmp['text']:
            return stop('failed', f'auto-tagging changed page appearance or text (appearance {cmp["pixels"][:8]}, text {cmp["text"][:8]}): stopped', 1)
        with pikepdf.open(tagged_out) as tp:
            if not tagged(tp): return stop('failed', 'auto-tagging produced no tag tree', 1)
        if plan['ocr_mode']:
            art = artifact_page_scans(tagged_out, rec['ocr']['pages_with_ocr_text'])
            rec['ocr']['scan_images_marked_decoration'] = art
            cmp = compare(cur, tagged_out, near=True)
            if cmp['pixels'] or cmp['text']: return stop('failed', 'marking page scans as decoration changed a page: stopped', 1)
        ph = drop_placeholder_alt(tagged_out); rec['checks']['placeholder_alt_removed'] = ph
        if rec.get('spreads'):                           # each spread read half by half: tree order only, checked
            res = reorder_spreads(tagged_out, rec['spreads'], rec['spreads']['order'].startswith('right'))
            cmp = compare(cur, tagged_out, near=True)
            rec['checks']['spreads_reordered'] = {'pages': {str(k): v for k, v in res.items()}, 'pixels_differ': cmp['pixels'], 'text_differs': cmp['text']}
            if cmp['pixels'] or cmp['text']: return stop('failed', 'reordering spread pages changed a page: stopped', 1)
        if ph['figures'] or ph['links']:
            flag('Placeholder alt text removed', f'the auto-tagger wrote alt text that says nothing ({ph["figures"]} figures "image N", '
                 f'{ph["links"]} links "Annotation"); it was removed, so those figures count as having no alt text (the AI or a '
                 'person writes it) and each link is read by its own text', check=False)
        cov = coverage(tagged_out); rec['checks']['coverage'] = cov
        total = cov['tagged'] + cov['artifact'] + cov['untagged']
        if cov['untagged'] and cov['untagged'] / max(total, 1) > 0.02:
            flag('Untagged text', f'{cov["untagged"]} text runs were left out of the tag tree by auto-tagging '
                 '(e.g. tiny or off-page text the tagger skips): the pipeline checks list them', cov['untagged_pages'][:20])
        after = keepers(tagged_out); rec['checks']['keepers_after'] = {k: v for k, v in after.items() if k != 'page_labels'}
        lost = [k for k in ('pages', 'bookmarks', 'links') if (before[k] or 0) > (after[k] or 0)]
        if before['page_labels'] != after['page_labels']: lost.append('page_labels')
        if lost: return stop('failed', f'auto-tag or OCR lost {", ".join(lost)}: stopped', 1)
        shutil.copyfile(tagged_out, PDF_OUT)
        rec['result'] = {'pdf': 'intake.pdf', 'sha256': sha256(PDF_OUT)}
        rec['status'] = 'done'; rec['summary'] = describe(rec); save()
        print(f'intake: {rec["summary"]}')
        return 0
    finally:
        try: doc.close()
        except Exception: pass
        shutil.rmtree(tmp, ignore_errors=True)

def describe(rec):
    """One line for the batch summary and review.md."""
    if rec.get('status') == 'skipped': return rec.get('summary')
    plan, o = rec.get('plan') or {}, rec.get('ocr') or {}
    parts = ['placeholder tag tree set aside'] if (rec.get('tag_tree') or {}).get('status') == 'placeholder' else []
    if plan.get('ocr_mode') == 'force': parts.append(f'force OCR, {len(plan["ocr_pages"])} pages')
    elif plan.get('ocr_mode') and not o:
        parts.append(f'OCR planned for {len(plan["ocr_pages"])} image-only page{"s" if len(plan["ocr_pages"]) != 1 else ""}')
    elif plan.get('ocr_mode'):
        n, m = len(o.get('pages_with_ocr_text', [])), len(o.get('image_pages_without_text', []))
        if n: parts.append(f'OCR {n} page{"s" if n != 1 else ""}')
        if m: parts.append(f'{m} picture page{"s" if m != 1 else ""} without OCR text')
    off = next((f for f in rec.get('flags') or [] if f['what'] == 'OCR off'), None)
    if off: parts.append(f'OCR off: {len(off.get("pages") or [])} image-only pages without text')
    parts.append('auto-tagged' if rec.get('status') == 'done' else 'auto-tag planned')
    v = (rec.get('text_test') or {}).get('verdict')
    if v == 'not enough pages scored': parts.append('text layer: not enough pages scored')
    elif v and v not in ('usable', 'not tested'): parts.append(f'text layer {v}')
    ol = rec.get('ocr_layer_test') or {}
    if ol.get('verdict') in ('doubtful', 'unusable'): parts.append(f'OCR layer {ol["verdict"]}')
    if ol.get('diacritics'): parts.append('OCR layer lacks diacritics')
    return ' · '.join(parts)

if __name__ == '__main__':
    sys.exit(main())
