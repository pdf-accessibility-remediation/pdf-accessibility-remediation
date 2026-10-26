"""Synthetic test PDFs for intake's page and tag-tree classification and its CJK language rule, and a check of what
intake.py does with each (no book content; nothing is sent anywhere; no model).

    python3 tools/intake_cases.py <out_dir> [--full]

Builds each case in <out_dir>/<case>.pdf, runs `intake.py --plan-only` on it (with the case's OCR_LANG), and compares
intake.json with what the case expects: PASS or FAIL per case, exit 1 on any FAIL. --full also runs the whole intake
(OCR + auto-tag, local) on the empty-text scan (the empty text object is removed so OCR text is added) and on the two
placeholder-tree cases (the old tree is set aside and a real one made) and on the two-up page (read half by half).
The empty-text scan needs OCRmyPDF 17; without it that case is SKIPped. Two OCR-layer cases need Tesseract's
script/Latin model (tesseract-ocr-script-latn on Debian/Ubuntu); without it they are SKIPped. A failing OCR-layer case
prints intake's OCR-layer test (verdict, each sample page's score or why it was not scored).
Japanese and Korean pages are drawn with a system font (Arial Unicode on macOS, Noto Sans CJK on Linux: the
fonts-noto-cjk package; INTAKE_CASES_FONT=/path/to/font overrides); text is the test's own. Without such a font the
CJK cases, the breves case and the full empty-text scan are SKIPped (the default font draws no CJK and no breves, and
its text is too small to OCR) and the last line says so.
The CJK cases also need Tesseract's osd, jpn, jpn_vert, kor, chi_sim and chi_tra packs (with their _vert packs).
"""
import json, os, shutil, subprocess, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE)
sys.path.insert(0, PIPE)
import pikepdf
from PIL import Image, ImageDraw, ImageFont

FONT = next((p for p in (os.environ.get('INTAKE_CASES_FONT') or '', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                          '/Library/Fonts/Arial Unicode.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                          '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc') if p and os.path.exists(p)), None)
FONT_CASES = {'japanese-scan', 'japanese-vertical-scan', 'korean-scan', 'japanese-scan-14', 'english-scan-cjk-on-13',   # need FONT: the
              'ocr-layer-missing-marks'}   # default font draws no CJK and no breves, and its text is too small to OCR
LATIN_CASES = {'ocr-layer-missing-marks', 'ocr-layer-matching'}   # scored with Tesseract's script/Latin model


def tesseract_langs():
    """The models `tesseract --list-langs` shows, as intake.py reads them (empty if Tesseract is missing)."""
    try: return {x.strip() for x in subprocess.run(['tesseract', '--list-langs'], capture_output=True, text=True).stdout.split('\n')[1:] if x.strip()}
    except OSError: return set()


def ocr_layer_details(j):
    """intake's OCR-layer test in one line: its verdict and each sample page's score or why it was not scored."""
    ol = j.get('ocr_layer_test')
    if not ol: return 'no OCR-layer test in intake.json (no page counted as an OCR layer)'
    pages = '; '.join(f'p{r["page"]}: ' + (f'cer {r["cer"]} ({r.get("model")})' if 'cer' in r else r.get('reason') or r.get('verdict', ''))
                      for r in ol.get('pages') or [])
    return f'verdict {ol.get("verdict")}, median cer {ol.get("median_cer")}' + (f', diacritics {ol["diacritics"]}' if ol.get('diacritics') else '') + f'; {pages}'
EN = 'This page is a scanned test page with a few lines of plain English text on it.'
JA = 'これは試験用の日本語の文章です。縦書きと横書きの両方を確認します。'
KO = '이것은 시험용 한국어 문장입니다. 가로쓰기와 세로쓰기를 확인합니다.'
RO = 'Sŏngwŏn met Hŏ Chŏk and Pak Yŏng-man in Ch\'ŏngju; Wŏllyang wrote to Kŭmsŏng.'   # McCune-Reischauer breves
RO_PLAIN = 'Songwon met Ho Chok and Pak Yong-man in Ch\'ongju; Wollyang wrote to Kumsong.'
W_IN, H_IN, DPI = 6, 8, 300


def text_image(text, lines=12, vertical=False, size=44):
    """A white page image with the text drawn in black, horizontally or in vertical columns right to left."""
    w, h = W_IN * DPI, H_IN * DPI
    img = Image.new('L', (w, h), 255); d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size) if FONT else ImageFont.load_default()
    if not vertical:
        for k in range(lines): d.text((150, 150 + k * int(size * 1.8)), text, fill=0, font=f)
    else:
        per_col = (h - 300) // int(size * 1.15); chars = list(text * 4); x = w - 200
        while chars and x > 150:
            for j in range(per_col):
                if not chars: break
                d.text((x, 150 + j * int(size * 1.15)), chars.pop(0), fill=0, font=f)
            x -= int(size * 1.9)
    return img


def image_xobject(pdf, img):
    return pikepdf.Stream(pdf, zlib.compress(img.tobytes()), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image,
                          Width=img.width, Height=img.height, ColorSpace=pikepdf.Name.DeviceGray, BitsPerComponent=8,
                          Filter=pikepdf.Name.FlateDecode)


def new_page(pdf, content, images=(), font=False, size=None, font_name='Helvetica'):
    res = pikepdf.Dictionary()
    if images: res.XObject = pikepdf.Dictionary({f'/Im{i}': image_xobject(pdf, im) for i, im in enumerate(images)})
    if font: res.Font = pikepdf.Dictionary(F1=pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1,
                                                                BaseFont=pikepdf.Name('/' + font_name), Encoding=pikepdf.Name.WinAnsiEncoding))
    page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, *(size or (W_IN * 72, H_IN * 72))], Resources=res,
                              Contents=pikepdf.Stream(pdf, content.encode('latin-1')))
    pdf.pages.append(pikepdf.Page(page))
    return pdf.pages[-1]


FULL_IMAGE = f'q {W_IN * 72} 0 0 {H_IN * 72} 0 0 cm /Im0 Do Q\n'
TEXT_LINES = ''.join(f'BT /F1 11 Tf 72 {H_IN * 72 - 80 - k * 16} Td ({EN}) Tj ET\n' for k in range(20))


def tree(pdf, page, kind, markinfo, alts=()):
    """A tag tree on a one-page PDF: 'doc-part' (Document > Part holding MCID 0), 'figures' (Figures holding MCIDs
    0, 1 … with these /Alt) or 'full' (Document > P holding MCID 0)."""
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    kids, leaves = [], []
    if kind == 'figures':
        for i, alt in enumerate(alts):
            e = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=doc, Pg=page.obj, K=i,
                                                     Alt=pikepdf.String(alt)))
            kids.append(e); leaves.append(e)
    else:
        e = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/Part' if kind == 'doc-part' else '/P'),
                                                 P=doc, Pg=page.obj, K=0))
        kids.append(e); leaves.append(e)
    doc.K = pikepdf.Array(kids); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pikepdf.Array(leaves)])))
    page.obj.StructParents = 0
    pdf.Root.StructTreeRoot = root
    if markinfo is not None: pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=markinfo)


def build(out):
    os.makedirs(out, exist_ok=True); made = {}
    def save(name, pdf):
        p = os.path.join(out, f'{name}.pdf'); pdf.save(p); made[name] = p
    en_img = text_image(EN)
    pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE + 'BT /F1 12 Tf 72 72 Td ( ) Tj ET\n', [en_img], font=True); save('empty-text-over-scan', pdf)
    pdf = pikepdf.new(); new_page(pdf, 'BT /F1 12 Tf 72 72 Td ( ) Tj ET\n', font=True); save('empty-text-no-image', pdf)
    pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE + '3 Tr\n' + TEXT_LINES, [en_img], font=True); save('ocr-layer', pdf)
    pdf = pikepdf.new(); new_page(pdf, TEXT_LINES, font=True); save('text-page', pdf)
    body = '/P <</MCID 0>> BDC\n' + TEXT_LINES + 'EMC\n'
    pdf = pikepdf.new(); pg = new_page(pdf, body.replace('/P <<', '/Part <<'), font=True); tree(pdf, pg, 'doc-part', None); save('tree-document-part', pdf)
    pdf = pikepdf.new(); pg = new_page(pdf, body, font=True); tree(pdf, pg, 'full', False); save('tree-full-marked-false', pdf)
    pdf = pikepdf.new(); pg = new_page(pdf, body, font=True); tree(pdf, pg, 'full', True); save('tree-full', pdf)
    pic = Image.new('L', (600, 400), 200); ImageDraw.Draw(pic).ellipse((100, 80, 500, 320), fill=60)
    figs = ('/Figure <</MCID 0>> BDC q 216 0 0 144 72 360 cm /Im0 Do Q EMC\n'
            '/Figure <</MCID 1>> BDC q 72 0 0 48 300 300 cm /Im1 Do Q EMC\n'
            '/Figure <</MCID 2>> BDC q 72 0 0 48 300 200 cm /Im2 Do Q EMC\n' + ''.join(TEXT_LINES.splitlines(True)[:3]))
    pdf = pikepdf.new(); pg = new_page(pdf, figs, [pic, pic, pic], font=True)
    tree(pdf, pg, 'figures', True, ('A grey oval on a light background.', ' Decorative Element ', 'Photo of a grey oval.'))
    save('tree-figures-only', pdf)
    def layer_lines(text, n=12, size=44):        # invisible text over text_image's lines, same text, same places
        return '3 Tr\n' + ''.join(f'BT /F1 10.5 Tf 36 {H_IN * 72 - 36 - 10.5 - k * size * 1.8 * 72 / DPI:.1f} Td ({text.replace(chr(39), chr(92) + chr(39))}) Tj ET\n' for k in range(n))
    pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE + layer_lines(RO_PLAIN), [text_image(RO)], font=True); save('ocr-layer-missing-marks', pdf)
    pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE + layer_lines(RO_PLAIN), [text_image(RO_PLAIN)], font=True); save('ocr-layer-matching', pdf)
    pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE + layer_lines(RO_PLAIN, n=2), [text_image(RO_PLAIN)], font=True)   # 2 lines of 12:
    save('ocr-layer-too-short', pdf)                 #   under 300 characters, so no page can be scored
    def lines_at(x, text, n=24):                    # born-digital lines on a landscape page (11 x 8.5 in)
        return ''.join(f'BT /F1 11 Tf {x} {560 - k * 20} Td ({text} {k + 1}) Tj ET\n' for k in range(n))
    def blocks(x, side):                             # three blocks per half, the gaps between them wider than the gutter,
        out = ''                                     #   so the tagger's xycut cuts across the page first and interleaves
        for b, top in enumerate((580, 340, 100)):
            out += ''.join(f'BT /F1 10 Tf {x} {top - k * 14} Td ({side} page, block {b + 1}, line {k + 1}: some words to fill the half) Tj ET\n' for k in range(4))
        return out
    pdf = pikepdf.new(); new_page(pdf, blocks(36, 'Left') + blocks(340, 'Right'), font=True, size=(792, 612)); save('spread-two-up', pdf)
    pdf = pikepdf.new(); new_page(pdf, blocks(36, 'Left') + blocks(340, 'Right'), font=True, size=(792, 612), font_name='HiddenVertOCR')
    save('spread-two-up-vertical', pdf)            # a 'Vert' font, as Acrobat's vertical OCR has: read right half first
    pdf = pikepdf.new()                              # years in every running head, page numbers at the foot: only the
    for k in range(2):                               #   numbers rise by 2 from spread to spread
        heads = 'BT /F1 9 Tf 60 590 Td (1994) Tj ET\nBT /F1 9 Tf 700 590 Td (1995) Tj ET\n'
        feet = f'BT /F1 9 Tf 180 20 Td ({12 + 2 * k}) Tj ET\nBT /F1 9 Tf 560 20 Td ({13 + 2 * k}) Tj ET\n'
        new_page(pdf, heads + feet + blocks(36, 'Left') + blocks(340, 'Right'), font=True, size=(792, 612))
    save('spreads-years-in-heads', pdf)
    pdf = pikepdf.new(); new_page(pdf, lines_at(50, 'One wide column of text runs across the whole width of this landscape page, line'),
                                  font=True, size=(792, 612)); save('landscape-one-column', pdf)
    ja_img, en_img2 = text_image(JA), text_image(EN)
    pdf = pikepdf.new()
    for _ in range(14): new_page(pdf, FULL_IMAGE, [ja_img])
    save('japanese-scan-14', pdf)
    pdf = pikepdf.new()
    for k in range(14): new_page(pdf, FULL_IMAGE, [ja_img if k == 12 else en_img2])
    save('english-scan-cjk-on-13', pdf)
    for name, txt, vert in (('japanese-scan', JA, False), ('japanese-vertical-scan', JA, True), ('korean-scan', KO, False)):
        pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE, [text_image(txt, vertical=vert)]); save(name, pdf)
    return made


def reorder_saved_case(out):
    """reorder_spreads on a tagged spread whose halves are already right-first but whose columns run left to right (as a
    tagger reads them): the order must change within the half, be saved, and be what is recorded. No tagger involved."""
    import intake as I
    cols = [(420, 'Right half, left column'), (600, 'Right half, right column'), (60, 'Left half, left column'), (230, 'Left half, right column')]
    content = ''.join(f'/P <</MCID {k}>> BDC\n' + ''.join(f'BT /F1 10 Tf {x} {560 - n * 14} Td ({t} {n + 1}) Tj ET\n' for n in range(20)) + 'EMC\n'
                      for k, (x, t) in enumerate(cols))
    pdf = pikepdf.new(); pg = new_page(pdf, content, font=True, size=(792, 612))
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    els = [pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg.obj, K=k)) for k in range(4)]
    doc.K = pikepdf.Array(els); root.K = pikepdf.Array([doc])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pikepdf.Array(els)])))
    pg.obj.StructParents = 0; pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
    path = os.path.join(out, 'reorder-saved.pdf'); pdf.save(path)
    res, left = I.reorder_spreads(path, {'pages': [1], 'gutter': {1: 0.5}, 'rotation': {}}, True)
    with pikepdf.open(path) as p:
        d = p.Root.StructTreeRoot.K[0]; saved = [int(e.K) for e in d.K]
    want = [1, 0, 3, 2]                              # right half first, its columns right to left, then the left half
    ok = res.get(1, {}).get('reordered') is True and saved == want
    return ok, f'recorded reordered={res.get(1, {}).get("reordered")}, saved order {saved} (want {want})'


def triage(j): return (j.get('triage') or {}).get('pages') or {}
CASES = [  # (case, pdf, OCR_LANG, what is expected, test on intake.json)
    ('empty text over a scan → image-only, OCR planned', 'empty-text-over-scan', None, 'image-only p1, empty_text_pages [1], OCR planned',
     lambda j: triage(j).get('image-only') == [1] and j['triage'].get('empty_text_pages') == [1] and (j.get('plan') or {}).get('ocr_pages') == [1]),
    ('empty text, no image → blank', 'empty-text-no-image', None, 'stopped: nothing to tag',
     lambda j: j['status'] == 'stopped' and 'nothing to tag' in j['summary']),
    ('invisible OCR text over a scan → ocr-layer (unchanged)', 'ocr-layer', None, 'ocr-layer p1',
     lambda j: triage(j).get('ocr-layer') == [1]),
    ('visible text → text (unchanged)', 'text-page', None, 'text p1',
     lambda j: triage(j).get('text') == [1] and not j['triage'].get('empty_text_pages')),
    ('Document + Part tree, no MarkInfo → placeholder', 'tree-document-part', None, 'planned, tag_tree placeholder',
     lambda j: j['status'] == 'planned' and j['tag_tree']['status'] == 'placeholder' and j['tag_tree']['markinfo'] is None),
    ('Figure-only tree with alt → placeholder, alt recorded (whole-text match only)', 'tree-figures-only', None,
     'placeholder; kinds publisher (real alt), placeholder (" Decorative Element "), publisher ("Photo of a grey oval."), with image boxes',
     lambda j: j['tag_tree']['status'] == 'placeholder' and [f['kind'] for f in j['tag_tree']['figures']] == ['publisher', 'placeholder', 'publisher']
     and all(f.get('image_box') for f in j['tag_tree']['figures'])),
    ('full tree, Marked false → tagged (skipped)', 'tree-full-marked-false', None, 'skipped',
     lambda j: j['status'] == 'skipped' and j['tag_tree']['markinfo'] is False),
    ('full tree, Marked true → tagged (skipped)', 'tree-full', None, 'skipped', lambda j: j['status'] == 'skipped'),
    ('OCR layer without the breves the scan shows → diacritics CHECK', 'ocr-layer-missing-marks', None, 'OCR layer test: diacritics flagged',
     lambda j: bool((j.get('ocr_layer_test') or {}).get('diacritics')) and any(f['what'] == 'OCR layer: diacritics' for f in j['flags'])),
    ('OCR layer matching its scan → usable, no CHECK', 'ocr-layer-matching', None, 'OCR layer test: usable, no OCR-layer flag',
     lambda j: (j.get('ocr_layer_test') or {}).get('verdict') == 'usable' and not any(f['what'].startswith('OCR layer') for f in j['flags'])),
    ('two printed pages side by side → spread CHECK', 'spread-two-up', None, 'spreads [1], left half first, CHECK',
     lambda j: (j.get('spreads') or {}).get('pages') == [1] and j['spreads'].get('order') == 'left half first'
     and any(f['what'] == 'Two printed pages per PDF page' for f in j['flags'])),
    ('two printed pages, vertical font → spread, right half first', 'spread-two-up-vertical', None, 'spreads [1], right half first',
     lambda j: (j.get('spreads') or {}).get('pages') == [1] and j['spreads'].get('order', '').startswith('right half first')),
    ('spreads with years in the running heads → page numbers, not years', 'spreads-years-in-heads', None, 'printed 12–13, 14–15',
     lambda j: ((j.get('spreads') or {}).get('printed') or {}) == {1: '12–13', 2: '14–15'} or ((j.get('spreads') or {}).get('printed') or {}) == {'1': '12–13', '2': '14–15'}),
    ('one wide column on a landscape page → not a spread', 'landscape-one-column', None, 'no spreads',
     lambda j: not j.get('spreads')),
    ('OCR layer too short to score → "OCR layer not checked" CHECK, OCR text approval needed', 'ocr-layer-too-short', None,
     'verdict not enough pages scored; CHECK; intake glance asks for the OCR review',
     lambda j: (j.get('ocr_layer_test') or {}).get('verdict') == 'not enough pages scored'
     and any(f['what'] == 'OCR layer not checked' and f['check'] for f in j['flags']) and (j.get('glance') or {}).get('ocr_layer_flagged') is True),
    ('Japanese scan, OCR_LANG unset → stops', 'japanese-scan', None, 'stopped: CJK text, set OCR_LANG',
     lambda j: j['status'] == 'stopped' and 'set OCR_LANG' in j['summary']),
    ('Japanese scan, OCR_LANG=jpn+eng → planned', 'japanese-scan', 'jpn+eng', 'planned, CJK OCR needs a person',
     lambda j: j['status'] == 'planned' and any(f['what'] == 'CJK OCR: needs a person' for f in j['flags'])),
    ('vertical Japanese scan, OCR_LANG unset → stops, suggests _vert', 'japanese-vertical-scan', None, 'stopped, vertical text likely',
     lambda j: j['status'] == 'stopped' and 'vertical' in j['summary']),
    ('14-page Japanese scan, OCR_LANG unset → stops after the first CJK page', 'japanese-scan-14', None, 'stopped; 1 page checked',
     lambda j: j['status'] == 'stopped' and (j.get('cjk_probe') or {}).get('pages_checked') == 1),
    ('14-page English scan with CJK only on page 13 → still found', 'english-scan-cjk-on-13', None, 'stopped; CJK page [13]',
     lambda j: j['status'] == 'stopped' and (j.get('cjk_probe') or {}).get('cjk_pages') == [13]),
    ('Korean scan, OCR_LANG unset → stops, no _vert hint', 'korean-scan', None, 'stopped, no vertical hint',
     lambda j: j['status'] == 'stopped' and 'set OCR_LANG' in j['summary'] and 'vertical' not in j['summary']),
]


def run_intake(pdf, out, lang, plan=True):
    env = dict(os.environ); env.pop('OCR_LANG', None)
    if lang: env['OCR_LANG'] = lang
    subprocess.run([sys.executable, os.path.join(PIPE, 'intake.py'), pdf, out] + (['--plan-only'] if plan else []), env=env,
                   capture_output=True, text=True)
    return json.load(open(os.path.join(out, 'intake.json')))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1: sys.exit(__doc__.split('\n\n')[1])
    out = os.path.abspath(args[0]); made = build(os.path.join(out, 'pdfs')); bad = good = skipped = 0
    latin = 'script/Latin' in tesseract_langs()
    for k, (what, case, lang, expect, test) in enumerate(CASES, 1):
        if case in FONT_CASES and not FONT:
            skipped += 1; print(f'SKIP  {what}  (no font for its text: install fonts-noto-cjk or set INTAKE_CASES_FONT)', flush=True); continue
        if case in LATIN_CASES and not latin:
            skipped += 1; print(f'SKIP  {what}  (Tesseract\'s script/Latin model is not installed: tesseract-ocr-script-latn)', flush=True); continue
        j = run_intake(made[case], os.path.join(out, 'plan', f'{k:02d}-{case}' + (f'-{lang}' if lang else '')), lang)
        ok = test(j); bad += not ok; good += ok
        print(f'{"PASS" if ok else "FAIL"}  {what}  (expected: {expect}; got: {j["status"]}: {j.get("summary")})', flush=True)
        if not ok and case.startswith('ocr-layer'): print(f'      OCR-layer test: {ocr_layer_details(j)}', flush=True)
    ok, got = reorder_saved_case(out); bad += not ok; good += ok
    print(f'{"PASS" if ok else "FAIL"}  right-first spread already in half order, columns left to right → reorder saved  (got: {got})', flush=True)
    if '--full' in sys.argv:
        if not shutil.which('ocrmypdf') or not FONT:  # real OCR of the drawn page: a missing tool or font, not a failing case
            skipped += 1; print('SKIP  full intake on empty-text-over-scan  (' + ('OCRmyPDF 17 is not installed' if FONT else 'no font: install fonts-noto-cjk or set INTAKE_CASES_FONT') + ')', flush=True)
        else:
            j = run_intake(made['empty-text-over-scan'], os.path.join(out, 'full', 'empty-text-over-scan'), None, plan=False)
            ok = j['status'] == 'done' and (j.get('ocr') or {}).get('pages_with_ocr_text') == [1] \
                and (j['checks'].get('empty_text_removed') or {}).get('pages') == [1]
            bad += not ok; good += ok
            print(f'{"PASS" if ok else "FAIL"}  full intake on empty-text-over-scan: empty text object removed, OCR text added, '
                  f'auto-tagged (got: {j["status"]}: {j.get("summary")})', flush=True)
        for case, first, before in (('spread-two-up', 'Left', 3), ('spread-two-up-vertical', 'Right', 1)):   # left-first: the tagger
            j = run_intake(made[case], os.path.join(out, 'full', case), None, plan=False)   #   interleaves the halves; right-first: it reads
                                                                                          #   left then right, the reorder must turn it round
            r = ((j['checks'].get('spreads_reordered') or {}).get('pages') or {}).get('1') or {}
            with pikepdf.open(os.path.join(out, 'full', case, 'intake.pdf')) as p:
                import pdfplumber, intake as I
                st = p.Root.StructTreeRoot; doc_el = st.K[0] if isinstance(st.K, pikepdf.Array) else st.K
                with pdfplumber.open(os.path.join(out, 'full', case, 'intake.pdf')) as pl:
                    by = {}
                    for c in pl.pages[0].chars:
                        if c.get('mcid') is not None: by.setdefault(c['mcid'], []).append(c['text'])
                def text_of(e):
                    k = e.get('/K'); ks = list(k) if isinstance(k, pikepdf.Array) else [k]
                    return ''.join(''.join(by.get(int(x), [])) if isinstance(x, int) else text_of(x) if isinstance(x, pikepdf.Dictionary) else '' for x in ks)
                first_text = next((t for t in (text_of(e) for e in doc_el.K) if t.strip()), '')
            ok = j['status'] == 'done' and r.get('switches_before', 0) >= before and r.get('switches_after', 9) <= 1 and r.get('reordered') \
                and first_text.startswith(first) and not j['checks']['spreads_reordered'].get('pixels_differ')
            bad += not ok; good += ok
            print(f'{"PASS" if ok else "FAIL"}  full intake on {case}: '
                  + ('the tagger interleaves the halves, the reorder reads the left half first' if first == 'Left' else 'the reorder puts the right half first')
                  + f' (got: {j["status"]}: switches {r.get("switches_before")} → {r.get("switches_after")}, first element "{first_text[:30]}")', flush=True)
        for case in ('tree-document-part', 'tree-figures-only'):
            j = run_intake(made[case], os.path.join(out, 'full', case), None, plan=False)
            ok = j['status'] == 'done' and not any((j['checks'].get('placeholder_tree_removed') or {}).get(k) for k in ('pixels_differ', 'text_differs'))
            if ok:
                with pikepdf.open(os.path.join(out, 'full', case, 'intake.pdf')) as p:
                    import intake as I
                    st, info = I.tag_status(p); ok = st == 'tagged'
            bad += not ok; good += ok
            print(f'{"PASS" if ok else "FAIL"}  full intake on {case}: old tree set aside, auto-tagged with text structure '
                  f'(got: {j["status"]}: {j.get("summary")})', flush=True)
    print(f'{good} passed, {bad} failed, {skipped} skipped' + (' (see the SKIP lines for what is missing)' if skipped else ''))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
