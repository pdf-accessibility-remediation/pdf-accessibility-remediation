"""intake.py: get an untagged PDF ready for the pipeline (local tools only: no model, no cost).

    python3 intake.py <original.pdf> <out_dir> [--plan-only]

Sponsor checklist steps: 1.2 (is the text layer usable?), 2.1 and 3.1 (OCR at 300 dpi or more), 3.6 (characters the
OCR font lacks), 3.7 (language), 10.3/10.4 (page image + invisible Unicode text), 10.5 (structure tree and tags).

What it does, in order, and only where needed:
  1. triage   every page: visible text, image only (no text, an image covering >= 25%: a scan or a picture page),
              an existing invisible OCR layer, or blank. Every text page: private-use characters (3.6), text outside the
              visible page area, and word breaks that are only gaps with no space character (3.4: a note; narrow
              gaps, under 19% of the type size, are a CHECK when they average 10 or more per text page) are counted
  2. 1.2 test OCR up to 20 scorable pages that have text and compare with their text layer (books with 40+ text
              pages: not from the first 5% of them, at least 6, which is front matter in small type; suspicious
              pages may come from anywhere). Page score = the lower of the in-order and any-order character
              error; book score = median of the page scores:
              <= 5% usable · > 15% unusable · in between: a person decides (the book goes on, with a CHECK).
              Only text inside the visible page area (CropBox) is compared. Pages whose images cover >= 25%, under 300 characters, or CJK text without a CJK OCR pack are not
              scored (replaced by the next scorable page further on); fewer than 5 scored: "not enough pages scored" (CHECK)
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
A tagged PDF is left alone (status "skipped"). Output in <out_dir>: intake.json always; intake.pdf when anything
changed (it is then the file the rest of the pipeline works on, and it is kept so FROM= reruns stay identical).

Environment: FORCE_OCR=1 · OCR=off (no OCR: image-only pages are only listed) · OCR_LANG=eng+jpn (Tesseract
languages; by default chosen from the scripts found: Latin eng, kana jpn, hangul kor; Chinese characters with no kana
are never guessed as Chinese or Japanese: OCR_LANG must say, else those pages go to a person).
Needs, only when used: Tesseract and OCRmyPDF 17 (brew install ocrmypdf tesseract-lang) for untagged books; Java 11+
and the opendataloader-pdf package for auto-tagging. Exit codes: 0 done or nothing to do · 3 flagged (stopped, see
intake.json) · 1 error.
"""
import sys, os, re, json, time, shutil, hashlib, subprocess, tempfile, unicodedata, difflib, collections, datetime, statistics, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
def page_inventory(page):
    """Visible and invisible text operators, and the images drawn (share of the visible page area covered, effective dpi)."""
    vr = visible_rect(page)
    out = {'visible': 0, 'invisible': 0, 'images': []}
    def walk(owner, res, ctm, depth):
        try: ops = pikepdf.parse_content_stream(owner)
        except Exception: return
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
    if out['visible']: kind = 'text'
    elif out['invisible'] and big: kind = 'ocr-layer'
    elif out['invisible']: kind = 'text'
    elif total >= IMAGE_ONLY_COVER: kind = 'image-only'
    else: kind = 'blank'
    scan = [i for i in out['images'] if i['cover'] >= SCAN_MIN_COVER] if kind == 'image-only' else big
    return {'kind': kind, 'visible_ops': out['visible'], 'invisible_ops': out['invisible'],
            'scan_dpi': min(i['dpi'] for i in scan) if scan else None,
            'max_cover': max((i['cover'] for i in out['images']), default=0),
            'image_cover': round(total, 3)}

def tagged(pdf):
    st = pdf.Root.get('/StructTreeRoot')
    return st is not None and st.get('/K') is not None and (not isinstance(st.K, pikepdf.Array) or len(st.K) > 0)

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
    return ''.join(ch for ch in t.lower() if not ch.isspace() and not is_cjk(ch))
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
        if la and lb and (la != str(a) or lb != str(b)): txt += f' (printed {la})' if a == b else f' (printed {la}–{lb})'
        out.append(txt); i = j + 1
    return ', '.join(out) if out else 'none'
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
    rows = []
    if t: rows.append(('Pages', ' · '.join(f'{v} {k.replace("-", " ")}' for k, v in t.items())))
    if tt:
        v = tt.get('verdict') or 'not tested'
        rows.append(('Text-layer test (1.2)', v + (f": median {tt['median_cer']:.1%} on {tt.get('scored')} pages" if tt.get('median_cer') is not None and tt.get('scored') else '')))
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
        if same and old.get('status') == 'skipped' or same and old.get('status') == 'done' and (not old.get('result', {}).get('pdf') or
                (os.path.exists(PDF_OUT) and sha256(PDF_OUT) == old['result'].get('sha256'))):
            if not os.path.exists(os.path.join(OUTD, 'intake.md')): write_md(old, os.path.join(OUTD, 'intake.md'))
            print(f'intake: reusing the earlier intake ({old["status"]}: {old.get("summary")})'); return 0
    rec = {'schema': SCHEMA, 'written': now(), 'original': {'file': os.path.basename(SRC), 'sha256': src_sha},
           'settings': settings, 'tools': {}, 'status': None, 'summary': None, 'flags': [], 'steps': [], 'checks': {},
           'result': {'pdf': None}, 'review': {'ocr_text_approved': None}}     # set by review_ocr.py (rule 2)
    page_labels = {}
    def save():
        cited = {int(p) for f in rec['flags'] for p in f.get('pages') or []} | set((rec.get('plan') or {}).get('ocr_pages') or []) \
            | {int(p) for k in ('pages_with_ocr_text', 'image_pages_without_text') for p in (rec.get('ocr') or {}).get(k) or []}
        rec['cited_labels'] = {str(p): page_labels[p] for p in sorted(cited) if p in page_labels}    # printed labels for intake.md
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
    if tagged(pdf):
        pdf.close(); rec['summary'] = 'none (already tagged)'; rec['status'] = 'skipped'; save()
        print('intake: already tagged, nothing to do'); return 0
    # ---- 1. triage
    t0 = time.time()
    inv = [page_inventory(pg) for pg in pdf.pages]; pdf.close()
    kinds = collections.defaultdict(list)
    for i, x in enumerate(inv, 1): kinds[x['kind']].append(i)
    rec['triage'] = {'pages': {k: v for k, v in kinds.items()}, 'counts': {k: len(v) for k, v in kinds.items()},
                     'seconds': round(time.time() - t0, 1)}
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
        sc = collections.Counter()
        step = max(1, len(text_pages) // 40)
        for i in text_pages[::step]: sc += scripts(doc[i - 1].get_textpage().get_text_range())
        osd = collections.Counter()
        for i in scan_pages[:: max(1, len(scan_pages) // 5)][:5]:
            img = os.path.join(tmp, f'osd{i}.png'); render(doc, i - 1, OCR_DPI, img)
            s = osd_script(img)
            if s: osd[s] += 1
        lang_why = []; han_no_kana = False
        if settings['OCR_LANG']:
            ocr_lang = settings['OCR_LANG']; lang_why.append('set by OCR_LANG')
        else:
            langs = ['eng']
            if sc['kana'] or osd.get('Japanese') or osd.get('Katakana') or osd.get('Hiragana'): langs.append('jpn'); lang_why.append('kana found: Japanese')
            if sc['hangul'] or osd.get('Hangul'): langs.append('kor'); lang_why.append('hangul found: Korean')
            han_no_kana = (sc['han'] or osd.get('Han')) and 'jpn' not in langs
            if han_no_kana: lang_why.append('Chinese characters with no kana: Chinese or Japanese is not guessed')
            ocr_lang = '+'.join(langs)
        missing = [l for l in ocr_lang.split('+') if l not in tv['tesseract_langs']]
        if missing:
            flag('OCR language', f'Tesseract has no language pack for {", ".join(missing)}: OCR used what is installed '
                 '(brew install tesseract-lang)')
            ocr_lang = '+'.join(l for l in ocr_lang.split('+') if l in tv['tesseract_langs']) or 'eng'
        rec['language'] = {'text_layer_scripts': dict(sc), 'scan_scripts': dict(osd), 'ocr_lang': ocr_lang, 'why': lang_why}
        def lang_flag(pages):                         # a CHECK only when OCR text is planned (plan-only) or kept (run)
            if han_no_kana and pages:
                flag('OCR language', 'Chinese characters were found with no kana, so OCR used English only. Set OCR_LANG '
                     '(e.g. chi_tra+eng or jpn+eng) and run again, or a person reads the CJK text on the OCR\'d pages', pages)
        cjk_pack = any(l in ocr_lang for l in ('jpn', 'chi', 'kor'))
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
                ocr = tesseract_text(img, ocr_lang); os.remove(img)
                a, b = norm(ocr), norm(layer)
                ci, ca = cer(a, b), bag_diff(a, b); c = min(ci, ca)
                v = 'usable' if c <= CER_OK else ('unusable' if c > CER_BAD else 'doubtful')
                if v == 'usable' and ci > CER_OK: v = 'usable (reading order differs)'
                wo, wl = len(ocr.split()), len(layer.split())
                rows.append({'page': i, 'chars': len(b), 'ocr_chars': len(a), 'suspicious': i in sus, 'cer': round(c, 3),
                             'cer_in_order': round(ci, 3), 'cer_any_order': round(ca, 3), 'verdict': v,
                             'words_ratio': round(wl / max(wo, 1), 2), 'private_use': s['private_use']})
            tt['pages'] = sorted(rows, key=lambda r: r['page'])
            scored = [r for r in tt['pages'] if 'cer' in r]
            tt['scored'] = len(scored); tt['not_scored'] = len(tt['pages']) - len(scored)
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
        # ---- the plan
        force = tt['verdict'] == 'unusable'
        plan = {'ocr_mode': None, 'ocr_pages': [], 'autotag': True}
        if force and not settings['FORCE_OCR']:
            rec['plan'] = plan
            flag('Text layer unusable', f'OCR and the text layer disagree (median character error {tt["median_cer"]:.0%}). '
                 'Run again with FORCE_OCR=1 to replace the text with OCR text over page images, or send the book to a person')
            return stop('stopped', f'text layer unusable (median CER {tt["median_cer"]:.0%}): flagged; FORCE_OCR=1 would OCR every page', 3)
        dpages = tt.get('doubtful_pages') or None
        if tt['verdict'] == 'doubtful':
            flag('Text layer', f'OCR and the text layer partly disagree (median character error {tt["median_cer"]:.0%}): '
                 'a person should compare a few pages' + (', starting with the doubtful ones listed' if dpages else '')
                 + '; FORCE_OCR=1 would replace the text with OCR text', dpages)
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
                cjk_pages = sorted(p for p, n in found.items() if n >= CJK_PROBE_MIN)
                rec['cjk_probe'] = {'langs': '+'.join(have), 'min_chars': CJK_PROBE_MIN, 'min_conf': CJK_PROBE_CONF,
                                    'cjk_characters': {str(p): n for p, n in found.items()}, 'cjk_pages': cjk_pages}
                cjk_lang = any(l in ocr_lang for l in ('chi', 'jpn', 'kor'))
                if cjk_pages and not cjk_lang:
                    flag('OCR language needed', 'these pages to be OCR\'d hold Chinese, Japanese or Korean text, and the language is never '
                         'guessed: set OCR_LANG (e.g. chi_tra+eng, chi_sim+eng, jpn+eng, kor+eng) and run again', cjk_pages)
                    return stop('stopped', f'CJK text on pages to be OCR\'d ({", ".join(map(str, cjk_pages))}): set OCR_LANG and run again', 3)
                if cjk_pages:
                    flag('CJK OCR: needs a person', f'these pages hold CJK text, OCR\'d with OCR_LANG={ocr_lang}: CJK OCR is often wrong '
                         '(sojourners\' glossary: many entries junk) and multi-column CJK lists may be read across the columns; a person '
                         'checks the text and its reading order', cjk_pages)
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
    parts = []
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
    return ' · '.join(parts)

if __name__ == '__main__':
    sys.exit(main())
