"""intake.tag_status (#122, page-figure trees; checklist 10.5): a tree of page-sized Figures with a few text elements is
a placeholder, set on coverage, not on element kinds. Synthetic tagged PDFs (no book content)."""
import zlib
import pikepdf
import intake

W, H = 400, 600


def tree_pdf(path, pages=10, figure_pages=10, text_pages=1, extra_kinds=(), figure_size=1.0, wrapped=True):
    """A tagged PDF: on `figure_pages` pages a Figure whose marked content draws a gray image (figure_size of the page,
    inside a form when wrapped, the way the sponsors' trees do), and a P (and extra_kinds) on `text_pages` pages."""
    pdf = pikepdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    img = pdf.make_stream(zlib.compress(bytes([128]) * 100), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=10, Height=10,
                          ColorSpace=pikepdf.Name.DeviceGray, BitsPerComponent=8, Filter=pikepdf.Name.FlateDecode)
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    kids, nums = [], []
    w, h = W * figure_size, H * figure_size
    for n in range(pages):
        pg = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, W, H]))
        arr, body = [], b''
        res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(Im0=img))
        if n < figure_pages:
            draw = f'q {w} 0 0 {h} 0 0 cm /Im0 Do Q'.encode()
            if wrapped:
                form = pdf.make_stream(draw, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, W, H],
                                       Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=img)))
                res.XObject.Fm0 = form; draw = b'/Fm0 Do'
            body += b'/Figure <</MCID 0>> BDC ' + draw + b' EMC '
            arr.append(pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=doc, Pg=pg, K=0)))
        for kind in (('/P',) + tuple(extra_kinds)) if n < text_pages else ():
            body += f'{kind} <</MCID {len(arr)}>> BDC BT /F1 12 Tf 20 20 Td (text) Tj ET EMC '.encode()
            arr.append(pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name(kind), P=doc, Pg=pg, K=len(arr))))
        body += b'/Artifact BMC BT 3 Tr /F1 12 Tf 20 300 Td (invisible OCR text marked as an artifact) Tj ET EMC'
        pg.Resources = res; pg.Contents = pdf.make_stream(body); pg.StructParents = n
        kids += arr; nums += [n, pikepdf.Array(arr)]
        pdf.pages.append(pikepdf.Page(pg))
    doc.K = pikepdf.Array(kids); root.K = pikepdf.Array([doc])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array(nums)))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
    pdf.save(path)
    return path


def status(p):
    with pikepdf.open(p) as pdf: return intake.tag_status(pdf)


def test_a_page_figure_tree_with_a_few_paragraphs_is_a_placeholder(tmp_path):
    st, info = status(tree_pdf(str(tmp_path / 'a.pdf')))
    assert st == 'placeholder' and info['page_figure_tree']['figure_pages'] == 10 and info['page_figure_tree']['text_pages'] == 1


def test_part_and_h5_count_as_text_but_coverage_decides(tmp_path):
    st, info = status(tree_pdf(str(tmp_path / 'a.pdf'), extra_kinds=('/Part', '/H5')))
    assert st == 'placeholder' and info['text_elements'] >= 2


def test_unwrapped_figures_count_too(tmp_path):
    assert status(tree_pdf(str(tmp_path / 'a.pdf'), wrapped=False))[0] == 'placeholder'


def test_a_real_tree_with_some_figures_stays_tagged(tmp_path):
    assert status(tree_pdf(str(tmp_path / 'a.pdf'), figure_pages=3, text_pages=10))[0] == 'tagged'     # text on every page
    assert status(tree_pdf(str(tmp_path / 'b.pdf'), figure_pages=10, text_pages=5))[0] == 'tagged'     # text on half the pages


def test_small_figures_are_not_page_sized(tmp_path):
    assert status(tree_pdf(str(tmp_path / 'a.pdf'), figure_size=0.5))[0] == 'tagged'                 # a quarter of the page each
