"""test_verify_inline.py: verify.py counts an untagged inline image as untagged content, exactly as it counts an untagged
image XObject (the inline-image issue; #93 (improve performance: home and batch pages, first-time "Review Again", and PDF
pipeline step timing), Part 3, handoff 11 §3 and review 12 L2).

    python -m pytest tests/test_verify_inline.py -q

pikepdf names an inline image `INLINE IMAGE`, never `BI`, so verify's check never counted one before. Synthetic PDFs only,
each with a small tag tree (one tagged word per page), veraPDF off. Each placement is tried with an inline image and with
an image XObject in the same place, which must give the same counts:
  1 on the page, untagged: counted once      2 inside marked content with an MCID: not counted
  3 inside /Artifact: not counted            4 in a form drawn untagged on two pages: counted once (a form counts once)
  5 in a form drawn inside tagged content: not counted
  6 in a Type 3 glyph, a tiling pattern or an annotation's appearance: not counted (the text or fill that paints it is,
    and annotations are checked through their OBJR)
  7 an untagged inline image, then untagged text and a path: all three counted (nothing after the image is lost)
  8 through run_api.sh and report.py: the safety check's row and review.md's "Untagged Content" section
  9 in the second stream of a page's /Contents array: counted
  10 in a form drawn from a form inside tagged content: not counted (and counted when the outer form is drawn untagged)
"""
import os, sys, json, shutil, subprocess
import pikepdf
import pytest

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INLINE = b'BI /W 1 /H 1 /BPC 8 /CS /G ID \x80 EI'
TAGGED_WORD = b'/P <</MCID 0>> BDC BT /F1 10 Tf 10 10 Td (x) Tj ET EMC\n'

def image_xobject(pdf):
    return pdf.make_stream(b'\x80', Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=1, Height=1,
                           BitsPerComponent=8, ColorSpace=pikepdf.Name.DeviceGray)

def drawn(kind):
    """The drawing of one image: an inline image, or the image XObject /Im1."""
    return (INLINE if kind == 'inline' else b'/Im1 Do')

def build(path, pages, kind, forms=None, extra=None):
    """pages: each a content stream (bytes) or a list of streams (a /Contents array); the first stream of each page starts
    with one tagged word (MCID 0). forms: {name: content}, drawn with `/<name> Do`. extra(pdf, page_dicts, res): more."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    xo = pikepdf.Dictionary(Im1=image_xobject(pdf))
    for name, content in (forms or {}).items():
        xo['/' + name] = pdf.make_stream(content, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, 300, 300],
                                   Resources=pikepdf.Dictionary(XObject=xo))   # forms may draw forms (and /Im1)
    res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=xo)
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root, K=pikepdf.Array()))
    nums = pikepdf.Array(); kids = []
    for i, content in enumerate(pages):
        streams = content if isinstance(content, list) else [content]
        streams = [TAGGED_WORD + streams[0]] + streams[1:]
        cs = [pdf.make_stream(s) for s in streams]
        pg = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 300, 300], Resources=res, StructParents=i,
                                Contents=cs[0] if len(cs) == 1 else pikepdf.Array(cs))
        pdf.pages.append(pikepdf.Page(pg))
        po = pdf.pages[-1].obj
        p = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=po, K=0))
        kids.append(p); nums.extend([i, pikepdf.Array([p])])
    doc.K = pikepdf.Array(kids); root.K = doc; root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=nums))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    if extra: extra(pdf, [p.obj for p in pdf.pages], res)
    pdf.save(path, deterministic_id=True)
    return path

def untagged(path):
    """verify.py on the PDF against itself: its untagged-objects block."""
    b = str(path) + '.out.pdf'; shutil.copyfile(path, b)
    r = subprocess.run([sys.executable, os.path.join(PIPE, 'verify.py'), str(path), b], env=dict(os.environ, VERAPDF='off'),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return json.load(open(b + '.verify.json', encoding='utf-8'))['untagged_objects']

KINDS = ['inline', 'xobject']

@pytest.mark.parametrize('kind', KINDS)
def test_1_an_untagged_image_on_the_page_counts_once(tmp_path, kind):
    u = untagged(build(tmp_path / 'a.pdf', [b'q 10 0 0 10 50 50 cm ' + drawn(kind) + b' Q\n'], kind))
    assert u['total'] == 1 and u['by_kind'] == {'image': 1} and u['top_pages'] == [[1, {'image': 1}]]

@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('wrap', [b'/Figure <</MCID 1>> BDC ', b'/Artifact BMC '])
def test_2_3_a_tagged_or_decorative_image_is_not_counted(tmp_path, kind, wrap):
    u = untagged(build(tmp_path / 'a.pdf', [wrap + b'q 10 0 0 10 50 50 cm ' + drawn(kind) + b' Q EMC\n'], kind))
    assert u['total'] == 0 and u['by_kind'] == {}

@pytest.mark.parametrize('kind', KINDS)
def test_4_a_form_drawn_untagged_on_two_pages_counts_once(tmp_path, kind):
    form = {'Fm1': b'q 10 0 0 10 50 50 cm ' + drawn(kind) + b' Q'}
    u = untagged(build(tmp_path / 'a.pdf', [b'/Fm1 Do\n', b'/Fm1 Do\n'], kind, forms=form))
    assert u['total'] == 1 and u['by_kind'] == {'image': 1}

@pytest.mark.parametrize('kind', KINDS)
def test_5_a_form_drawn_inside_tagged_content_is_not_counted(tmp_path, kind):
    form = {'Fm1': b'q 10 0 0 10 50 50 cm ' + drawn(kind) + b' Q'}
    u = untagged(build(tmp_path / 'a.pdf', [b'/Figure <</MCID 1>> BDC /Fm1 Do EMC\n'], kind, forms=form))
    assert u['total'] == 0

def type3(kind):
    def extra(pdf, pages, res):
        glyph = pdf.make_stream(b'1000 0 d0 q 1000 0 0 1000 0 0 cm ' + drawn(kind) + b' Q')
        f = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type3, FontBBox=[0, 0, 1000, 1000],
                               FontMatrix=[0.001, 0, 0, 0.001, 0, 0], CharProcs=pikepdf.Dictionary(a=glyph),
                               Encoding=pikepdf.Dictionary(Type=pikepdf.Name.Encoding, Differences=[97, pikepdf.Name.a]),
                               FirstChar=97, LastChar=97, Widths=[1000], Resources=pikepdf.Dictionary(XObject=res.XObject))
        res.Font.T3 = pdf.make_indirect(f)
    return extra

def pattern(kind):
    def extra(pdf, pages, res):
        p = pdf.make_stream(b'q 10 0 0 10 0 0 cm ' + drawn(kind) + b' Q', PatternType=1, PaintType=1, TilingType=1,
                            BBox=[0, 0, 10, 10], XStep=10, YStep=10, Resources=pikepdf.Dictionary(XObject=res.XObject))
        res.Pattern = pikepdf.Dictionary(P0=p)
    return extra

def annotation(kind):
    def extra(pdf, pages, res):
        ap = pdf.make_stream(b'q 10 0 0 10 0 0 cm ' + drawn(kind) + b' Q', Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form,
                             BBox=[0, 0, 50, 50], Resources=pikepdf.Dictionary(XObject=res.XObject))
        a = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Square, Rect=[0, 0, 50, 50],
                                                 AP=pikepdf.Dictionary(N=ap), Contents=pikepdf.String('a box'), P=pages[0]))
        pages[0].Annots = pikepdf.Array([a])
    return extra

@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('where,content,expect', [
    (type3, b'BT /T3 12 Tf 50 50 Td (a) Tj ET\n', {'text': 1}),               # the glyph's painting is the text shown
    (pattern, b'/Pattern cs /P0 scn 20 20 50 50 re f\n', {'path': 1}),         # the pattern's painting is the fill
    (annotation, b'', {})])                                                     # an annotation is not page content
def test_6_type3_glyphs_patterns_and_appearances_are_not_walked(tmp_path, kind, where, content, expect):
    u = untagged(build(tmp_path / 'a.pdf', [content], kind, extra=where(kind)))
    assert u['by_kind'] == expect

def test_7_nothing_after_an_inline_image_is_lost(tmp_path):
    u = untagged(build(tmp_path / 'a.pdf', [b'q 10 0 0 10 50 50 cm ' + INLINE + b' Q BT /F1 10 Tf 100 100 Td (y) Tj ET 0 0 m 10 10 l S\n'], 'inline'))
    assert u['by_kind'] == {'image': 1, 'text': 1, 'path': 1}

@pytest.mark.parametrize('kind', KINDS)
def test_9_the_second_stream_of_a_contents_array_counts(tmp_path, kind):
    u = untagged(build(tmp_path / 'a.pdf', [[b'BT /F1 10 Tf 40 40 Td (z) Tj ET\n'.replace(b'BT', b'/Artifact BMC BT').replace(b'ET\n', b'ET EMC\n'),
                                             b'q 10 0 0 10 50 50 cm ' + drawn(kind) + b' Q\n']], kind))
    assert u['by_kind'] == {'image': 1}

@pytest.mark.parametrize('kind', KINDS)
def test_10_a_form_inside_a_form_follows_the_outer_state(tmp_path, kind):
    forms = {'Fin': b'q 10 0 0 10 50 50 cm ' + drawn(kind) + b' Q', 'Fout': b'/Fin Do'}
    assert untagged(build(tmp_path / 'a.pdf', [b'/Figure <</MCID 1>> BDC /Fout Do EMC\n'], kind, forms=forms))['total'] == 0
    assert untagged(build(tmp_path / 'b.pdf', [b'/Fout Do\n'], kind, forms=forms))['by_kind'] == {'image': 1}

def test_8_review_md_names_the_untagged_inline_image(tmp_path):
    """run_api.sh end to end with no AI request (DECIDE=none, intake off, veraPDF off): the safety check's row and
    review.md's "Untagged Content" section: one object, in the singular, and content reused on several pages named
    in plain words (review 14 N1)."""
    src = build(tmp_path / 'book.pdf', [b'q 10 0 0 10 50 50 cm ' + INLINE + b' Q\n'], 'inline')
    R = tmp_path / 'run'
    env = dict(os.environ, VERAPDF='off', OPENROUTER_API_KEY='test-not-a-key', HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9',
               PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), RUN_DIR=str(R), INTAKE='off', DECIDE='none')
    for k in ('REPLY', 'REVIEW', 'KEEP', 'AUTO', 'ESTIMATE', 'INTAKE_REUSE'): env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', str(src), 'book', 'x'], cwd=PIPE, env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    md = (R / 'review.md').read_text(encoding='utf-8')
    row = next(l for l in md.splitlines() if l.startswith('| All content tagged or marked as decoration |'))
    assert '| **CHECK** |' in row and '1 untagged object (1 image)' in row and '1 untagged objects' not in row, row
    assert '### 2. Untagged Content (1 object)' in md and ': 1 image' in md and '(1 objects)' not in md
    assert '(content reused on several pages counts once)' in md and 'form XObject' not in md
