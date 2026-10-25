"""Synthetic test PDFs for intake's page and tag-tree classification and its CJK language rule, and a check of what
intake.py does with each (no book content; nothing is sent anywhere; no model).

    python3 tools/intake_cases.py <out_dir> [--full]

Builds each case in <out_dir>/<case>.pdf, runs `intake.py --plan-only` on it (with the case's OCR_LANG), and compares
intake.json with what the case expects: PASS or FAIL per case, exit 1 on any FAIL. --full also runs the whole intake
(OCR + auto-tag, local) on the empty-text scan (the empty text object is removed so OCR text is added) and on the two
placeholder-tree cases (the old tree is set aside and a real one made).
Japanese and Korean pages are drawn with a system font (Arial Unicode); text is the test's own.
"""
import json, os, subprocess, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE)
sys.path.insert(0, PIPE)
import pikepdf
from PIL import Image, ImageDraw, ImageFont

FONT = next((p for p in ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', '/Library/Fonts/Arial Unicode.ttf') if os.path.exists(p)), None)
EN = 'This page is a scanned test page with a few lines of plain English text on it.'
JA = 'これは試験用の日本語の文章です。縦書きと横書きの両方を確認します。'
KO = '이것은 시험용 한국어 문장입니다. 가로쓰기와 세로쓰기를 확인합니다.'
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


def new_page(pdf, content, images=(), font=False):
    res = pikepdf.Dictionary()
    if images: res.XObject = pikepdf.Dictionary({f'/Im{i}': image_xobject(pdf, im) for i, im in enumerate(images)})
    if font: res.Font = pikepdf.Dictionary(F1=pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1,
                                                                BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding))
    page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, W_IN * 72, H_IN * 72], Resources=res,
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
    for name, txt, vert in (('japanese-scan', JA, False), ('japanese-vertical-scan', JA, True), ('korean-scan', KO, False)):
        pdf = pikepdf.new(); new_page(pdf, FULL_IMAGE, [text_image(txt, vertical=vert)]); save(name, pdf)
    return made


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
    ('Japanese scan, OCR_LANG unset → stops', 'japanese-scan', None, 'stopped: CJK text, set OCR_LANG',
     lambda j: j['status'] == 'stopped' and 'set OCR_LANG' in j['summary']),
    ('Japanese scan, OCR_LANG=jpn+eng → planned', 'japanese-scan', 'jpn+eng', 'planned, CJK OCR needs a person',
     lambda j: j['status'] == 'planned' and any(f['what'] == 'CJK OCR: needs a person' for f in j['flags'])),
    ('vertical Japanese scan, OCR_LANG unset → stops, suggests _vert', 'japanese-vertical-scan', None, 'stopped, vertical text likely',
     lambda j: j['status'] == 'stopped' and 'vertical' in j['summary']),
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
    out = os.path.abspath(args[0]); made = build(os.path.join(out, 'pdfs')); bad = 0
    for k, (what, case, lang, expect, test) in enumerate(CASES, 1):
        j = run_intake(made[case], os.path.join(out, 'plan', f'{k:02d}-{case}' + (f'-{lang}' if lang else '')), lang)
        ok = test(j); bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  {what}  (expected: {expect}; got: {j["status"]}: {j.get("summary")})', flush=True)
    if '--full' in sys.argv:
        j = run_intake(made['empty-text-over-scan'], os.path.join(out, 'full', 'empty-text-over-scan'), None, plan=False)
        ok = j['status'] == 'done' and (j.get('ocr') or {}).get('pages_with_ocr_text') == [1] \
            and (j['checks'].get('empty_text_removed') or {}).get('pages') == [1]
        bad += not ok
        print(f'{"PASS" if ok else "FAIL"}  full intake on empty-text-over-scan: empty text object removed, OCR text added, '
              f'auto-tagged (got: {j["status"]}: {j.get("summary")})', flush=True)
        for case in ('tree-document-part', 'tree-figures-only'):
            j = run_intake(made[case], os.path.join(out, 'full', case), None, plan=False)
            ok = j['status'] == 'done' and not any((j['checks'].get('placeholder_tree_removed') or {}).get(k) for k in ('pixels_differ', 'text_differs'))
            if ok:
                with pikepdf.open(os.path.join(out, 'full', case, 'intake.pdf')) as p:
                    import intake as I
                    st, info = I.tag_status(p); ok = st == 'tagged'
            bad += not ok
            print(f'{"PASS" if ok else "FAIL"}  full intake on {case}: old tree set aside, auto-tagged with text structure '
                  f'(got: {j["status"]}: {j.get("summary")})', flush=True)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
