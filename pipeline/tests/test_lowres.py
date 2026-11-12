"""test_lowres.py: figures drawn at a low resolution (issue #97, lib/lowres.py): the ppi rule, the audit's list on a
hand-made PDF, and the review page's cards.

    python -m pytest tests/test_lowres.py -q

The expected results follow docs/hand-edits.md ("Limits"). No book content; nothing is sent anywhere; veraPDF is off.
"""
import os, sys, json, subprocess
import pikepdf
from lib import lowres

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def img(w_px, h_px, w_pt, h_pt):
    return {'x0': 72, 'x1': 72 + w_pt, 'top': 100, 'bottom': 100 + h_pt, 'srcsize': (w_px, h_px)}

# ---- the rule
def test_ppi_is_stored_pixels_over_drawn_inches():
    assert round(lowres.ppi(img(100, 100, 216, 216))) == 33          # 100 px over 3 in
    assert lowres.ppi(img(400, 400, 144, 144)) == 200                # 400 px over 2 in

def test_the_lower_side_counts():
    assert lowres.ppi(img(600, 100, 144, 144)) == 50                 # squeezed: 300 ppi across, 50 down

def test_an_image_turned_90_degrees_measures_the_same():
    assert lowres.ppi(img(600, 300, 72, 144)) == lowres.ppi(img(600, 300, 144, 72)) == 300

def test_small_images_and_images_with_no_size_do_not_count():
    assert lowres.ppi(img(8, 8, 24, 24)) is None                     # an icon: long side under 1 inch
    assert lowres.ppi({'x0': 0, 'x1': 144, 'top': 0, 'bottom': 144}) is None
    assert lowres.ppi(img(0, 100, 144, 144)) is None
    assert lowres.ppi(img(100, 100, 144, 0)) is None

def test_a_figure_takes_its_lowest_image_and_a_drawing_has_none():
    assert lowres.figure_ppi([img(400, 400, 144, 144), img(100, 100, 144, 144), img(8, 8, 24, 24)]) == 50
    assert lowres.figure_ppi([]) is None and lowres.figure_ppi(None) is None

def test_flag_threshold_and_what_is_left_out():
    figs = [{'obj': '1 0', 'page': 2}, {'obj': '2 0', 'page': 1}, {'obj': '3 0', 'page': 1, 'image_is_whole_page': True},
            {'obj': '4 0', 'page': 3, 'outside_visible_area': True}, {'obj': '5 0', 'page': None}, {'obj': '6 0', 'page': 4}]
    ims = {'1 0': [img(149, 149, 72, 72)], '2 0': [img(150, 150, 72, 72)], '3 0': [img(10, 10, 72, 72)],
           '4 0': [img(10, 10, 72, 72)], '5 0': [img(10, 10, 72, 72)]}            # 6 0: a drawing, no image
    assert lowres.flag(figs, ims) == [{'obj': '1 0', 'page': 2, 'ppi': 149}]
    assert [x['obj'] for x in lowres.flag(figs, ims, threshold=200)] == ['2 0', '1 0']   # by page

def test_an_image_made_at_the_threshold_is_not_flagged_for_a_rounding_slip():
    # hawaii3: 639 px drawn 306.911 pt wide measures 149.9 ppi; made at 150
    figs = [{'obj': '1 0', 'page': 1}, {'obj': '2 0', 'page': 1}]
    ims = {'1 0': [img(639, 363, 306.911, 173.938)], '2 0': [img(639, 363, 308.6, 174)]}
    assert lowres.flag(figs, ims) == [{'obj': '2 0', 'page': 1, 'ppi': 149}]

# ---- the audit, on a hand-made PDF
def figures_pdf(path, producer=None):
    """One page of text and three tagged figures: 100x100 px over 3 in (33 ppi), 400x400 px over 2 in (200 ppi), and an
    8x8 px icon over a third of an inch."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    def image(n): return pikepdf.Stream(pdf, bytes((x * 13) % 256 for x in range(n * n)), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image,
                                         Width=n, Height=n, ColorSpace=pikepdf.Name.DeviceGray, BitsPerComponent=8)
    content = ('/P <</MCID 0>> BDC BT /F1 11 Tf 36 540 Td (A page with three pictures.) Tj ET EMC\n'
               '/Figure <</MCID 1>> BDC q 216 0 0 216 36 300 cm /Im1 Do Q EMC\n'
               '/Figure <</MCID 2>> BDC q 144 0 0 144 270 300 cm /Im2 Do Q EMC\n'
               '/Figure <</MCID 3>> BDC q 24 0 0 24 36 200 cm /Im3 Do Q EMC\n')
    pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], StructParents=0,
                     Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(Im1=image(100), Im2=image(400), Im3=image(8))),
                     Contents=pikepdf.Stream(pdf, content.encode('latin-1')))))
    pg = pdf.pages[0].obj
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    ks = [pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + s), P=doc, Pg=pg, K=i))
          for i, s in enumerate(['P', 'Figure', 'Figure', 'Figure'])]
    doc.K = pikepdf.Array(ks); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pikepdf.Array(ks)])))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    if producer: pdf.docinfo['/Producer'] = producer
    pdf.save(path, deterministic_id=True)
    with pikepdf.open(path) as saved:                  # object numbers as saved: the audit's obj
        return path, [f'{k.objgen[0]} {k.objgen[1]}' for k in saved.Root.StructTreeRoot.K.K][1:]

def audit(src, out):
    r = subprocess.run([sys.executable, os.path.join(PIPE, 'audit.py'), str(src), str(out)], env=dict(os.environ, VERAPDF='off'),
                       capture_output=True, text=True)
    assert r.returncode == 0, f'audit.py failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}'
    return json.load(open(os.path.join(out, 'digest.json'), encoding='utf-8')), r.stdout

def test_the_audit_lists_only_the_blurry_figure(tmp_path):
    src, (blurry, sharp, icon) = figures_pdf(tmp_path / 'figs.pdf')
    d, out = audit(src, tmp_path / 'audit')
    assert {f['obj'] for f in d['figures']} == {blurry, sharp, icon}
    assert d['low_resolution'] == [{'obj': blurry, 'page': 1, 'ppi': 33}]
    assert '1 figures below 150 ppi' in out
    assert all('ppi' not in f and 'srcsize' not in f for f in d['figures'])      # the figures the AI sees are as before

def test_a_scanned_pdf_is_left_to_intake(tmp_path):
    src, _ = figures_pdf(tmp_path / 'scan.pdf', producer='OCRmyPDF')
    d, _ = audit(src, tmp_path / 'audit')
    assert d['low_resolution'] == []

# ---- the review page
def test_the_cards_of_a_blurry_figure_say_so(tmp_path):
    from review import core
    src, (blurry, sharp, icon) = figures_pdf(tmp_path / 'figs.pdf')
    d, _ = audit(src, tmp_path / 'audit')
    wo = {'alt': [{'obj': blurry, 'alt': 'A blurry photo.'}, {'obj': sharp, 'alt': 'A sharp photo.'}]}
    items = {it['id']: it for it in core.build_items(wo, d)}
    assert items[f'alt:{blurry}']['context']['low_ppi'] == 33 and 'low_ppi' not in items[f'alt:{sharp}']['context']
    targets = {t['target']: t for t in core.addable({}, d)['alt']}
    assert targets[blurry]['context']['low_ppi'] == 33 and 'low_ppi' not in targets[sharp]['context']
