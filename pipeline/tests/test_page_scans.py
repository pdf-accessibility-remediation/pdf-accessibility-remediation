"""intake.artifact_page_scans (#128, whole-page figures; checklist 5.1): a Figure that is only the whole-page scan image
becomes decoration, also inside the form the sponsors' scans wrap each page in, and on pages with an existing OCR layer
only when the page is a page of text (scan_page_is_text). Synthetic tagged PDFs (no book content, no Java, no OCR): each
imitates the tagger's output, a Figure around the scan image and the invisible OCR text tagged as a paragraph."""
import zlib
import pikepdf
import intake

W, H = 612, 792


def scan_pdf(path, ink=0, wrapped=True, pages=1, share_form=False, depth=1, figure_kids=1):
    """Pages each with a full-page gray image (value `ink`: 255 white, 0 black) under invisible text, tagged as the tagger
    does. wrapped: the image and text sit in a form (the form numbers its marked content through /StructParents);
    depth: forms nested this deep; share_form: every page draws the same form."""
    pdf = pikepdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    w, h = 61, 79
    img = pdf.make_stream(zlib.compress(bytes([ink]) * (w * h)), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=w, Height=h,
                          ColorSpace=pikepdf.Name.DeviceGray, BitsPerComponent=8, Filter=pikepdf.Name.FlateDecode)
    body = (f'q {W} 0 0 {H} 0 0 cm /Figure <</MCID 0>> BDC /Im0 Do EMC Q '
            '/P <</MCID 1>> BDC BT 3 Tr /F1 12 Tf 72 700 Td (A line of invisible OCR text on the page) Tj ET EMC').encode()
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    nums, kids, shared = [], [], None
    for n in range(pages):
        pg_dict = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, W, H])
        pg_obj = pdf.make_indirect(pg_dict)
        fig = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=doc, Pg=pg_obj,
                                                   K=0 if figure_kids == 1 else pikepdf.Array([0, 2])))
        par = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg_obj, K=1))
        kids += [fig, par]
        res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(Im0=img))
        if wrapped:
            if share_form and shared is not None: form = shared
            else:
                form = pdf.make_stream(body, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, W, H], Resources=res,
                                       StructParents=len(nums) // 2)
                for _ in range(depth - 1):              # wrap it again: Fm0 > Fm0 > …
                    form = pdf.make_stream(b'/Fm0 Do', Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, W, H],
                                           Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm0=form)))
                shared = form
            pg_dict.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm0=form))
            pg_obj.Resources = pg_dict.Resources; pg_obj.Contents = pdf.make_stream(b'q /Fm0 Do Q')
        else:
            pg_obj.Resources = res; pg_obj.Contents = pdf.make_stream(body); pg_obj.StructParents = len(nums) // 2
        nums += [len(nums) // 2, pikepdf.Array([fig, par])]
        pdf.pages.append(pikepdf.Page(pg_obj))
    doc.K = pikepdf.Array(kids); root.K = pikepdf.Array([doc])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array(nums)))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
    pdf.save(path)
    return path


def figures(path):
    st, info = intake.tag_status(pikepdf.open(path))
    return info['elements'].get('/Figure', 0)


def test_wrapped_text_page_scan_becomes_decoration(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=255)
    out = intake.artifact_page_scans(p, [1], picture_test=[1])
    assert out['pages'] == [1] and out['measured'] == {1: 0.0} and not out['misfits']
    with pikepdf.open(p) as pdf:
        form = pdf.pages[0].Resources.XObject.Fm0
        assert b'/Artifact' in form.read_bytes() and b'/Figure' not in form.read_bytes()
    assert figures(p) == 0


def test_unwrapped_page_works_too(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=255, wrapped=False)
    assert intake.artifact_page_scans(p, [1], picture_test=[1])['pages'] == [1] and figures(p) == 0


def test_a_picture_page_keeps_its_figure(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=0)                    # a black page: all its ink lies outside the text
    out = intake.artifact_page_scans(p, [1], picture_test=[1])
    assert out['pages'] == [] and out['kept'][1] > intake.SCAN_TEXT_INK and figures(p) == 1


def test_pages_intake_ocrd_are_not_picture_tested(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=0)                    # as before #128: OCR'd pages lose the scan Figure
    out = intake.artifact_page_scans(p, [1])
    assert out['pages'] == [1] and out['measured'] == {} and figures(p) == 0


def test_a_shared_form_is_a_misfit(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=255, pages=2, share_form=True)
    out = intake.artifact_page_scans(p, [1, 2], picture_test=[1, 2])
    assert out['pages'] == [] and [m[0] for m in out['misfits']] == [1, 2] and 'another page' in out['misfits'][0][1]


def test_a_form_deeper_than_the_limit_is_a_misfit(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=255, depth=5)
    out = intake.artifact_page_scans(p, [1], picture_test=[1])
    assert out['pages'] == [] and out['misfits'] and 'deeper' in out['misfits'][0][1]


def test_a_figure_holding_more_than_the_image_is_left(tmp_path):
    p = scan_pdf(str(tmp_path / 'a.pdf'), ink=255, figure_kids=2)
    assert intake.artifact_page_scans(p, [1], picture_test=[1])['pages'] == [] and figures(p) == 1


def test_the_ink_rule(tmp_path):
    import pypdfium2 as pdfium
    white, black = scan_pdf(str(tmp_path / 'w.pdf'), ink=255), scan_pdf(str(tmp_path / 'b.pdf'), ink=0)
    assert intake.scan_page_is_text(pdfium.PdfDocument(white), 1) == (True, 0.0)
    is_text, share = intake.scan_page_is_text(pdfium.PdfDocument(black), 1)
    assert is_text is False and share > 0.9                        # the text box is masked out; the rest is ink


def test_compare_only_reads_the_pages_asked_for(tmp_path):
    def two(path, second):
        pdf = pikepdf.new()
        font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
        for t in (b'same text', second):
            pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 300, 300],
                             Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
                             Contents=pdf.make_stream(b'BT /F1 12 Tf 20 200 Td (' + t + b') Tj ET'))))
        pdf.save(path); return path
    a, b = two(str(tmp_path / 'a.pdf'), b'page two'), two(str(tmp_path / 'b.pdf'), b'page 2!!')
    assert intake.compare(a, b, near=True)['text'] == [2]
    assert intake.compare(a, b, near=True, only={1})['text'] == [] and intake.compare(a, b, near=True, only={2})['text'] == [2]
