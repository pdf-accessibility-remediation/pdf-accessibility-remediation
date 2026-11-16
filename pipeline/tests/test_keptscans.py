"""Review 06 H2: page scans intake kept as figures (#128) are marked in the digest, and the executor refuses alt text on them
that copies the page's text (lib/keptscans.py, apply.py op_alt). Synthetic PDFs and alt texts only; no model call."""
import os, sys, json, hashlib, runpy, io, contextlib
import pikepdf, pytest
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import keptscans as K  # noqa: E402

LINE = 'The harvest festival was held each autumn in the village square, where families gathered to share food.'


def test_a_copied_line_is_refused_and_a_description_is_not():
    page = LINE + ' The elders spoke first, then the children sang.'
    assert K.copied_text('Page of text: ' + LINE[:60], page).startswith('it repeats')
    assert K.copied_text('A photograph of a crowded village square with long tables of food under paper lanterns.', page) is None
    assert K.copied_text('A page of printed text about a harvest festival.', page) is None    # names the page: no copy


def test_the_shared_run_limit_white_space_and_case():
    page = 'abcdefghij klmnopqrstuvwxyz'
    assert K.copied_text('x abcde fghijklmnopqrst y', page)                     # 20 shared letters, spaces ignored on both sides
    assert K.copied_text('x abcdefghijklmnopqrs y', page) is None               # 19: under the limit
    assert K.copied_text('ABCDEFGHIJKLMNOPQRST', page)                           # letter case ignored by default
    assert K.copied_text('ABCDEFGHIJKLMNOPQRST', page, fold=False) is None       # as written: the copy in capitals passes


def test_a_long_caption_quoted_in_the_alt_is_refused():
    """The accepted side effect (Patrick's decision 2): alt text quoting a caption of 20+ characters is refused."""
    page = 'Plate 2. A grey field at the edge of the village, photographed in the early morning.'
    assert K.copied_text('Plate 2. A grey field at the edge of the village: a wide, empty field under a pale sky.', page)
    assert K.copied_text('Plate 2: a wide, empty field under a pale sky.', page) is None


def test_cjk_the_layer_lacks():
    assert K.copied_text('A page headed 春天的山上開滿了紅色花朵 in large type.', 'Page 14 Spring') .startswith('it holds 12 Chinese')
    assert K.copied_text('A page headed 春天的山上 in large type.', 'Page 14 Spring') is None                 # 5: under the limit
    assert K.copied_text('A title in Chinese, 春天的山上開, beside a map.', 'Map 春天的山上開 of the hills') is None   # in the layer
    assert K.copied_text('はるのやまにはなが', '') .startswith('it holds 9')                                  # kana count too


def scan_pdf(path, text):
    """One page: a full-page image tagged Figure (MCID 0) and invisible OCR text in a P (MCID 1), like an OCR'd scan."""
    pdf = pikepdf.new()
    img = pikepdf.Stream(pdf, b'\x80' * 16, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=4, Height=4,
                         ColorSpace=pikepdf.Name.DeviceGray, BitsPerComponent=8)
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    c = (b'/Figure <</MCID 0>> BDC q 612 0 0 792 0 0 cm /Im0 Do Q EMC\n/P <</MCID 1>> BDC BT 3 Tr /F1 10 Tf 72 700 Td ('
         + text.encode('latin-1') + b') Tj ET EMC\n')
    pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 612, 792], StructParents=0,
                                                     Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(Im0=img)),
                                                     Contents=pdf.make_stream(c))))
    pg = pdf.pages[0].obj
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    fig = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=doc, Pg=pg, K=0))
    para = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg, K=1))
    doc.K = pikepdf.Array([fig, para]); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=[0, pikepdf.Array([fig, para])]))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path, deterministic_id=True)
    with pikepdf.open(path) as p:                    # the object number as saved
        f = p.Root.StructTreeRoot.K.K[0]
        return f'{f.objgen[0]} {f.objgen[1]}'


def run_apply(tmp_path, monkeypatch, alt, why='', kept=True, sha_ok=True):
    d = tmp_path / '_intake'; d.mkdir(exist_ok=True); src = str(d / 'intake.pdf')
    ref = scan_pdf(src, LINE)
    sha = hashlib.sha256(open(src, 'rb').read()).hexdigest() if sha_ok else '0' * 64
    (d / 'intake.json').write_text(json.dumps({'result': {'pdf': 'intake.pdf', 'sha256': sha}, 'page_scans': {'kept_as_figure': {'1': 0.05} if kept else {}}}))
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'schema': 'workorder/0.2', 'alt': [{'obj': ref, 'alt': alt, 'why': why}]}))
    monkeypatch.setenv('VERAPDF', 'off')
    monkeypatch.setattr(sys, 'argv', ['apply.py', src, str(wo), str(tmp_path / 'out.pdf')])
    monkeypatch.syspath_prepend(PIPE)
    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(os.path.join(PIPE, 'apply.py'), run_name='__main__')
    log = json.load(open(str(tmp_path / 'out.pdf') + '.log.json'))
    with pikepdf.open(str(tmp_path / 'out.pdf')) as p:
        a = next((str(n.get('/Alt')) for n in [p.get_object(tuple(int(x) for x in ref.split()))] if '/Alt' in n), None)
    return log, a


def test_from_intake_reads_the_record_only_for_its_own_result(tmp_path):
    d = tmp_path / '_intake'; d.mkdir(); src = str(d / 'intake.pdf'); scan_pdf(src, LINE)
    sha = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    (d / 'intake.json').write_text(json.dumps({'result': {'sha256': sha}, 'page_scans': {'kept_as_figure': {'3': 0.02}},
                                               'ocr': {'scan_images_kept_as_figure': {'7': 0.3}}}))
    assert K.from_intake(src) == {3: 0.02, 7: 0.3}
    (d / 'intake.json').write_text(json.dumps({'result': {'sha256': '0' * 64}, 'page_scans': {'kept_as_figure': {'3': 0.02}}}))
    assert K.from_intake(src) == {}                                             # another file: nothing
    other = tmp_path / 'book.pdf'; other.write_bytes(open(src, 'rb').read())
    assert K.from_intake(str(other)) == {}                                      # not intake's result


def test_apply_refuses_copied_alt_on_a_kept_scan(tmp_path, monkeypatch):
    log, alt = run_apply(tmp_path, monkeypatch, 'A page of text: ' + LINE)
    assert alt is None and log['alt_refused_copied_text'][0]['page'] == 1 and 'repeats' in log['alt_refused_copied_text'][0]['why']
    assert any(r['op'].startswith('alt ') and 'left without alt text' in r['why'] for r in log['rejected'])


def test_apply_writes_a_description_on_a_kept_scan(tmp_path, monkeypatch):
    log, alt = run_apply(tmp_path, monkeypatch, 'A photograph of a village square with long tables of food.')
    assert alt == 'A photograph of a village square with long tables of food.' and not log.get('alt_refused_copied_text')


@pytest.mark.parametrize('kw', [{'kept': False}, {'sha_ok': False}, {'why': 'added by Kim in review'}])
def test_the_guard_applies_only_to_kept_scans_and_never_to_a_persons_addition(tmp_path, monkeypatch, kw):
    log, alt = run_apply(tmp_path, monkeypatch, 'A page of text: ' + LINE, **kw)
    assert alt == 'A page of text: ' + LINE and not log.get('alt_refused_copied_text')


def test_the_marker_reaches_both_requests():
    """The audit's kept_by_picture_test stays on the figure entry in the figure request's data, and both image labels name it."""
    from lib import figpasses as FP
    f = {'obj': '12 0', 'page': 5, 'label': '5', 'area_pct': 98.0, 'image': 'figures/p005_12.png', 'kept_by_picture_test': {'ink_outside_text': 0.04}}
    digest = {'figures': [f], 'source': {'pages': 9}, 'text_quality': {}, 'page_map': []}
    data = FP.context(digest, None, [f], {}, [])
    assert data['figures'][0]['kept_by_picture_test'] == {'ink_outside_text': 0.04}
    assert 'kept as a picture' in FP.label(f) and 'kept as a picture' not in FP.label({**f, 'kept_by_picture_test': None})
    src = open(os.path.join(PIPE, 'decide.py'), encoding='utf-8').read()
    assert src.count("' A page scan kept as a picture (kept_by_picture_test)") == 1   # the first request's label: the same words


def test_the_audit_marks_a_kept_page_scan(tmp_path):
    import subprocess
    d = tmp_path / '_intake'; d.mkdir(); src = str(d / 'intake.pdf'); scan_pdf(src, LINE)
    sha = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    for kept, want in (({'1': 0.05}, {'ink_outside_text': 0.05}), ({}, None)):
        (d / 'intake.json').write_text(json.dumps({'result': {'sha256': sha}, 'page_scans': {'kept_as_figure': kept}}))
        out = tmp_path / ('a' + str(bool(kept)))
        r = subprocess.run([sys.executable, os.path.join(PIPE, 'audit.py'), src, str(out)], env={**os.environ, 'VERAPDF': 'off'}, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        dg = json.load(open(out / 'digest.json'))
        assert [f.get('kept_by_picture_test') for f in dg['figures']] == [want]
        assert ('kept_page_scans_format' in dg) == bool(kept)                  # no new key in a digest without kept scans
