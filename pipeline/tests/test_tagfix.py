"""lib/tagfix.py (#127, the generated cover page): restoring the /ActualText spans the auto-tagger drops, and the "same
drawing" proof. Synthetic PDFs only (no book content, no Java, no OCR): each 'tagged' file imitates what the tagger
does (an MCID span in place of the source's span, split runs)."""
import re
import pikepdf, pypdfium2 as pdfium
from lib import tagfix as TF


def make(path, content, forms=None, font_extra=None):
    """One page drawing `content` with Helvetica as /F1; forms: {name: (bytes, {sub name: (bytes, …)})} nested."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    if font_extra: font.update(font_extra(pdf))
    font = pdf.make_indirect(font)

    def form(spec):
        data, subs = spec
        res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
        if subs: res.XObject = pikepdf.Dictionary({'/' + k: form(v) for k, v in subs.items()})
        return pdf.make_stream(data, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, 612, 792], Resources=res)
    res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    if forms: res.XObject = pikepdf.Dictionary({'/' + k: form(v) for k, v in forms.items()})
    pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 612, 792], Resources=res,
                                                     Contents=pdf.make_stream(content))))
    pdf.save(path)
    return path


def text(path):
    d = pdfium.PdfDocument(path); t = re.sub(r'\s+', '', d[0].get_textpage().get_text_range()); d.close(); return t


SRC = b'BT /F1 24 Tf 72 700 Td (Japanese ) Tj /Span <</ActualText (N)>> BDC (n) Tj EMC (ow) Tj ET'
TAG = b'BT /F1 24 Tf 72 700 Td /P <</MCID 0>> BDC (Japanese ) Tj EMC /P <</MCID 1>> BDC (n) Tj EMC /P <</MCID 2>> BDC (ow) Tj EMC ET'


def ops(path, form=None):
    with pikepdf.open(path) as p:
        owner = p.pages[0] if form is None else p.pages[0].Resources.XObject[form]
        return [(str(i.operator), [str(x) for x in i.operands]) for i in pikepdf.parse_content_stream(owner)]


def test_restore_puts_the_span_back_and_the_text_matches(tmp_path):
    s = make(str(tmp_path / 's.pdf'), SRC); t = make(str(tmp_path / 't.pdf'), TAG)
    assert text(s) == 'JapaneseNow' and text(t) == 'Japanesenow'          # the tagger's loss, as on the covers
    rep = TF.restore(s, t)
    assert rep['spans'] == 1 and rep['pages'] == {1: 1} and not rep['misfits'] and rep['values'] == {'N': 1}
    assert text(t) == text(s)
    o = ops(t); i = next(k for k, (op, a) in enumerate(o) if op == 'BDC' and a[0] == '/Span')
    assert o[i - 1][0] == 'BDC' and o[i + 1] == ('Tj', ['n']) and o[i + 2][0] == 'EMC' and o[i + 3][0] == 'EMC'   # inside the MCID span


SPLIT = b'BT /F1 24 Tf 72 700 Td /Lbl <</MCID 0>> BDC [(A)] TJ EMC /LBody <</MCID 1>> BDC [-20 (B)] TJ (cd) Tj EMC ET'


def test_restore_finds_a_run_the_tagger_split(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b'BT /F1 24 Tf 72 700 Td [(A) -20 /Span <</ActualText (b)>> BDC (B)] TJ EMC (cd) Tj ET'
             .replace(b'[(A) -20 /Span <</ActualText (b)>> BDC (B)] TJ', b'[(A)] TJ /Span <</ActualText (b)>> BDC [-20 (B)] TJ'))
    t = make(str(tmp_path / 't.pdf'), SPLIT)
    rep = TF.restore(s, t)
    assert rep['spans'] == 1 and not rep['misfits'] and text(t) == text(s) == 'Abcd'


def test_a_span_across_two_of_the_tagger_elements_is_a_misfit(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b'BT /F1 24 Tf 72 700 Td /Span <</ActualText (Ab)>> BDC [(A) -20 (B)] TJ EMC (cd) Tj ET')
    t = make(str(tmp_path / 't.pdf'), SPLIT)
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and 'cross' in rep['misfits'][0][2]                 # the run would cross MCID 0 → MCID 1


def test_restore_in_a_form(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b'q /Fm0 Do Q', forms={'Fm0': (SRC, None)})
    t = make(str(tmp_path / 't.pdf'), b'q /Fm0 Do Q', forms={'Fm0': (TAG, None)})
    rep = TF.restore(s, t)
    assert rep['spans'] == 1 and not rep['misfits'] and text(t) == text(s)
    assert any(op == 'BDC' and a[0] == '/Span' for op, a in ops(t, '/Fm0'))


def test_p1_same_length_other_bytes_is_a_misfit(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b'BT /F1 24 Tf 72 700 Td /Span <</ActualText (X)>> BDC (ab) Tj (cd) Tj EMC ET')
    t = make(str(tmp_path / 't.pdf'), b'BT /F1 24 Tf 72 700 Td /P <</MCID 0>> BDC (xy) Tj (zw) Tj EMC ET')
    before = open(t, 'rb').read()
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and rep['misfits'] and 'glyph bytes differ' in rep['misfits'][0][2]
    assert open(t, 'rb').read() == before                                        # nothing written


def test_p2_two_spans_starting_together_nest_correctly(tmp_path):
    s = make(str(tmp_path / 's.pdf'),
             b'BT /F1 24 Tf 72 700 Td /Span <</ActualText (OUTER)>> BDC /Span <</ActualText (I)>> BDC (a) Tj EMC (b) Tj EMC ET')
    t = make(str(tmp_path / 't.pdf'), b'BT /F1 24 Tf 72 700 Td /P <</MCID 0>> BDC (a) Tj (b) Tj EMC ET')
    rep = TF.restore(s, t)
    assert rep['spans'] == 2 and not rep['misfits']
    seq = [op if op == 'EMC' else ('Tj', a[0]) if op == 'Tj' else ('BDC', a[1]) for op, a in ops(t) if op in ('BDC', 'EMC', 'Tj')]
    assert '"/MCID": 0' in seq[0][1]
    assert '"/ActualText": "OUTER"' in seq[1][1] and '"/ActualText": "I"' in seq[2][1]   # the outer span opens first
    assert seq[3:] == [('Tj', 'a'), 'EMC', ('Tj', 'b'), 'EMC', 'EMC']          # inner closes after a, outer after b, then MCID 0
    assert text(t) == text(s)


def test_p3_quote_operator_is_a_misfit(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b"BT /F1 24 Tf 14 TL 72 700 Td /Span <</ActualText (X)>> BDC (a) Tj (b) ' EMC ET")
    t = make(str(tmp_path / 't.pdf'), b"BT /F1 24 Tf 14 TL 72 700 Td /P <</MCID 0>> BDC (a) Tj (b) ' EMC ET")
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and rep['misfits'] and 'operator' in rep['misfits'][0][2]


def test_span_ending_inside_a_tagger_operator_is_a_misfit(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b'BT /F1 24 Tf 72 700 Td /Span <</ActualText (N)>> BDC (n) Tj EMC (ow) Tj ET')
    t = make(str(tmp_path / 't.pdf'), b'BT /F1 24 Tf 72 700 Td /P <</MCID 0>> BDC (now) Tj EMC ET')
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and 'inside' in rep['misfits'][0][2]


def test_spans_the_tagger_kept_are_not_doubled(tmp_path):
    s = make(str(tmp_path / 's.pdf'), SRC); t = make(str(tmp_path / 't.pdf'), SRC)
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and not rep['misfits']


def test_page_without_actualtext_is_not_read(tmp_path):
    s = make(str(tmp_path / 's.pdf'), b'BT /F1 24 Tf 72 700 Td (plain) Tj ET'); t = make(str(tmp_path / 't.pdf'), b'BT /F1 24 Tf 72 700 Td (plain) Tj ET')
    assert TF.restore(s, t) == {'spans': 0, 'pages': {}, 'values': {}, 'misfits': []}


# ------------------------------------------------------------------ same drawing
def same(tmp_path, a, b, **kw):
    pa = make(str(tmp_path / 'a.pdf'), a, **{k: v[0] for k, v in kw.items()}) if kw else make(str(tmp_path / 'a.pdf'), a)
    pb = make(str(tmp_path / 'b.pdf'), b, **{k: v[1] for k, v in kw.items()}) if kw else make(str(tmp_path / 'b.pdf'), b)
    with pikepdf.open(pa) as A, pikepdf.open(pb) as B:
        return TF.same_drawing(A, B, 1)


def test_split_runs_draw_the_same(tmp_path):
    a = b'BT /F1 12 Tf 72 700 Td [(B ) -3088 (1 )] TJ ET'
    b = b'BT /F1 12 Tf 72 700 Td /Lbl <</MCID 0>> BDC [(B)] TJ EMC /Artifact BMC [( )] TJ EMC /LBody <</MCID 1>> BDC [-3088 (1)] TJ EMC /Artifact BMC [( )] TJ EMC ET'
    assert same(tmp_path, a, b) == (True, True, None)


def test_a_changed_glyph_a_moved_run_or_text_state_is_not_the_same(tmp_path):
    a = b'BT /F1 12 Tf 72 700 Td (abc) Tj ET'
    assert same(tmp_path, a, b'BT /F1 12 Tf 72 700 Td (abd) Tj ET')[0] is False
    assert same(tmp_path, a, b'BT /F1 12 Tf 72 701 Td (abc) Tj ET')[0] is False
    assert same(tmp_path, a, b'BT /F1 12 Tf 2 Tc 72 700 Td (abc) Tj ET')[0] is False
    assert same(tmp_path, a, b'BT /F1 12 Tf 72 700.00001 Td (abc) Tj ET')[0] is True     # equal to four decimals


def test_a_lost_actualtext_is_reported(tmp_path):
    assert same(tmp_path, SRC, TAG) == (True, False, None)


def test_a_changed_font_map_is_not_the_same_drawing(tmp_path):
    a = b'BT /F1 12 Tf 72 700 Td (abc) Tj ET'
    cmap = lambda u: (lambda pdf: {'/ToUnicode': pdf.make_stream(b'/CIDInit /ProcSet findresource begin 12 dict begin begincmap 1 begincodespacerange <00> <FF> endcodespacerange 1 beginbfchar <61> <' + u + b'> endbfchar endcmap end end')})
    pa = make(str(tmp_path / 'a.pdf'), a, font_extra=cmap(b'0061')); pb = make(str(tmp_path / 'b.pdf'), a, font_extra=cmap(b'0041'))
    with pikepdf.open(pa) as A, pikepdf.open(pb) as B:
        assert TF.same_drawing(A, B, 1)[0] is False


def test_p4_a_form_deeper_than_the_limit_is_a_misfit_not_a_pass(tmp_path):
    deep = lambda t: {'F1x': (b'q /G Do Q', {'G': (b'q /H Do Q', {'H': (b'q /K Do Q', {'K': (b'BT /F1 12 Tf 72 700 Td (' + t + b') Tj ET', None)})})})}
    pa = make(str(tmp_path / 'a.pdf'), b'q /F1x Do Q', forms=deep(b'same'))
    pb = make(str(tmp_path / 'b.pdf'), b'q /F1x Do Q', forms=deep(b'diff'))
    with pikepdf.open(pa) as A, pikepdf.open(pb) as B:
        sd, sp, why = TF.same_drawing(A, B, 1)
    assert sd is False and why and 'deeper' in why
    with pikepdf.open(pa) as A, pikepdf.open(pa) as B:
        assert TF.same_drawing(A, B, 1)[2]                          # even identical files: never an unchecked pass


def pattern_pdf(path, text, actualtext=False):
    """The reviewer's probe P (review 04 M1): text inside a tiling pattern used as a fill colour."""
    pdf = pikepdf.new()
    f = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    p = pdf.make_stream(b'BT /F1 40 Tf 10 20 Td (' + text + b') Tj ET', Type=pikepdf.Name.Pattern, PatternType=1, PaintType=1, TilingType=1,
                        BBox=[0, 0, 300, 100], XStep=300, YStep=100, Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=f)))
    pg = pdf.add_blank_page(page_size=(300, 100))
    pg.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=f), Pattern=pikepdf.Dictionary(P0=p),
                                      ColorSpace=pikepdf.Dictionary(CS0=pikepdf.Array([pikepdf.Name.Pattern])))
    span = b'/Span <</ActualText (N)>> BDC BT /F1 12 Tf 10 80 Td (N) Tj ET EMC ' if actualtext else b''
    pg.Contents = pdf.make_stream(span + b'/CS0 cs /P0 scn 10 30 280 60 re f')
    pdf.save(path); return path


def test_text_in_a_tiling_pattern_is_a_misfit_not_a_pass(tmp_path):
    a, b = pattern_pdf(str(tmp_path / 'a.pdf'), b'Hello'), pattern_pdf(str(tmp_path / 'b.pdf'), b'Hallo')
    with pikepdf.open(a) as pa, pikepdf.open(b) as pb:
        same_, props, why = TF.same_drawing(pa, pb, 1)
    assert same_ is False and props is False and 'tiling pattern' in why
    s, t = pattern_pdf(str(tmp_path / 's.pdf'), b'Hello', actualtext=True), pattern_pdf(str(tmp_path / 't.pdf'), b'Hello')
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and rep['misfits'] and 'tiling pattern' in rep['misfits'][0][2]


def test_a_tiling_patterns_path_or_colour_change_is_seen():
    """Review 06 M3 (probe Q): a tiling pattern that fills with another grey, or draws another path, is not the same drawing;
    the same pattern again is."""
    def build(pat, name='P1'):
        pdf = pikepdf.new()
        st = pdf.make_stream(pat, PatternType=1, PaintType=1, TilingType=1, BBox=[0, 0, 50, 50], XStep=50, YStep=50, Resources=pikepdf.Dictionary())
        pg = pdf.add_blank_page(page_size=(300, 100))
        pg.Resources = pikepdf.Dictionary(Pattern=pikepdf.Dictionary({'/' + name: st}))
        pg.Contents = pdf.make_stream(b'/Pattern cs /' + name.encode() + b' scn 10 10 200 80 re f\n')
        return pdf
    base = build(b'0.2 g 0 0 20 20 re f\n')
    for other, same_ in ((build(b'0.9 g 0 0 20 20 re f\n'), False), (build(b'0.2 g 0 0 30 20 re f\n'), False), (build(b'0.2 g 0 0 20 20 re f\n'), True)):
        assert TF.same_drawing(base, other, 1)[0] is same_


def kana_page(path, content):
    """Review 09 H-A: "Ka", a 4 × 4 image standing for the letter ā, "na"; the image carries ActualText (ā) in the source."""
    pdf = pikepdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                                                Encoding=pikepdf.Name.WinAnsiEncoding))
    img = pikepdf.Stream(pdf, b'\x00' * 16, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=4, Height=4,
                         ColorSpace=pikepdf.Name.DeviceGray, BitsPerComponent=8)
    pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 612, 792],
                                                     Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(Im1=img)),
                                                     Contents=pdf.make_stream(content))))
    pdf.save(path)
    return path


A_MACRON = b'/Span <</ActualText <FEFF0101>>> BDC q 8 0 0 12 98 700 cm /Im1 Do Q EMC'
KANA_SRC = b'BT /F1 12 Tf 72 700 Td (Ka) Tj ET ' + A_MACRON + b' BT /F1 12 Tf 108 700 Td (na) Tj ET'
KANA_TAG = (b'/P <</MCID 0>> BDC BT /F1 12 Tf 72 700 Td (Ka) Tj ET EMC /Figure <</MCID 1>> BDC q 8 0 0 12 98 700 cm /Im1 Do Q EMC '
            b'/P <</MCID 2>> BDC BT /F1 12 Tf 108 700 Td (na) Tj ET EMC')


def test_spoken_text_on_an_image_dropped_by_the_tagger_is_listed_never_passed(tmp_path):
    """Review 09 H-A: the tagger drops the span around the image (as OpenDataLoader does); the restore can't place it by its
    glyph bytes (it has none), so it is a misfit, and the whole-file check lists the value as missing."""
    s = kana_page(str(tmp_path / 's.pdf'), KANA_SRC); t = kana_page(str(tmp_path / 't.pdf'), KANA_TAG)
    rep = TF.restore(s, t)
    assert rep['spans'] == 0 and len(rep['misfits']) == 1 and rep['misfits'][0][0] == 1 and 'image or a drawing' in rep['misfits'][0][2]
    assert TF.lost_values(s, t) == {1: ['ā']}
    kept = kana_page(str(tmp_path / 'k.pdf'), KANA_TAG.replace(b'/Figure <</MCID 1>> BDC q', b'/Figure <</MCID 1>> BDC ' + A_MACRON.split(b' q ')[0] + b' q')
                     .replace(b'Do Q EMC /P <</MCID 2>>', b'Do Q EMC EMC /P <</MCID 2>>'))
    assert not TF.restore(s, kept)['misfits'] and TF.lost_values(s, kept) == {}     # the tagger kept it: nothing listed


def test_the_whole_file_check_is_quiet_after_a_glyph_restore(tmp_path):
    s = make(str(tmp_path / 's.pdf'), SRC); t = make(str(tmp_path / 't.pdf'), TAG)
    assert TF.lost_values(s, t) == {1: ['N']}                                   # before the restore: missing
    TF.restore(s, t)
    assert TF.lost_values(s, t) == {}                                           # put back: nothing missing
