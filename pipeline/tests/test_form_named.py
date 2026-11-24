"""Review 06 §2 and S1 (#166, steps that skip form text): a form XObject whose marked content names its property list
(/Span /MC0 BDC, the dictionary in the form's own /Resources /Properties) is read like one that writes it inline. Its words
are placed by the finder, its runs pass apply's form checks and are tagged, a band rule hides its running head, verify reads
them as form runs, and lib/mcsplit counts them. Made-up words on tiny PDFs (tests/langpdf.build_in_form(named=True)); no
book has this shape yet (review 06 §2). veraPDF off; the tag-tree check mode on (conftest)."""
import os, sys, json
import pikepdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
from test_language_forms import run, wo_of, spans, form_index, clean, THREE, WHOLE, OCR, PHRASE, LONG, INRUN, INRUN_WO  # noqa: E402
from test_strays import Book, text_ops, slot  # noqa: E402
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, langcands, langjoin, mcsplit, tagfix  # noqa: F401,E402


def apply_verify(tmp_path, lines, wo, name='src.pdf', **build):
    src = langpdf.build_in_form(str(tmp_path / name), lines, named=True, **build)
    p = tmp_path / ('wo-' + name + '.json'); p.write_text(json.dumps(wo))
    out = str(tmp_path / ('out-' + name))
    run('apply.py', src, p, out); run('verify.py', src, out)
    return src, out, json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))


def marks(path):
    """{MCID: its properties as text}, inline or named, for every run of the page's form (tagfix.bdc_props)."""
    with pikepdf.open(path) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']; out = {}
        for x in pikepdf.parse_content_stream(f, 'BDC'):
            p = tagfix.bdc_props(x.operands, f.get('/Resources'))
            if p is not None and '/MCID' in p: out[int(p.MCID)] = {str(k): str(v) for k, v in p.items()}
        return out


def test_the_builder_names_every_property_list(tmp_path):
    src = langpdf.build_in_form(str(tmp_path / 'f.pdf'), THREE, named=True)
    with pikepdf.open(src) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']
        assert b'/MCID' not in f.read_bytes() and tagfix.names_props(f.read_bytes())
        assert tagfix.form_mcids(f) == {0, 1, 2} and tagfix.form_has_mcids(f)


def test_without_a_named_bdc_the_byte_search_is_unchanged(tmp_path):
    """A form with inline dictionaries only: form_mcids is exactly the byte search (#167), and no parse is needed."""
    src = langpdf.build_in_form(str(tmp_path / 'f.pdf'), THREE)
    with pikepdf.open(src) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']; data = f.read_bytes()
        assert not tagfix.names_props(data)
        assert tagfix.form_mcids(f) == set(map(int, tagfix.MCID_RX.findall(data))) == {0, 1, 2}


def test_the_finder_places_a_word_across_two_named_runs_in_a_form(tmp_path):
    src = langpdf.build_in_form(str(tmp_path / 'f.pdf'), LONG, named=True)
    with pikepdf.open(src) as pdf:
        assert len(langjoin.single_use_forms(pdf).get(1, [])) == 1
        c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf)
    ps = [p for p in c['places'] if p['form'] == 'velunka']
    assert len(ps) == 1 and [s[0] for s in ps[0]['segments']] == [0, 1], c['places']
    assert not any(u['form'] == 'velunka' for u in c['unplaced'])


def test_a_whole_named_run_in_a_form_is_tagged_and_its_marks_lose_their_lang(tmp_path):
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE))
    assert spans(out) == [('haw', [1], 'P', ['stm'])], log['language_parts']
    m = marks(out)
    assert '/Lang' not in m[1] and m[0]['/Lang'] == 'en-US' and m[2]['/Lang'] == 'en-US'
    assert form_index(out)[1] == 'Span'
    assert v['language']['all_match'] and v['language']['spans_written'] == 1 and clean(v), v['language']   # read as a form run


def test_a_place_inside_a_named_run_is_split_inside_the_form(tmp_path):
    src, out, log, v = apply_verify(tmp_path, INRUN, wo_of(INRUN_WO))
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'haw' and sp[0][3] == ['stm'] and sp[0][1][0] >= 2, sp
    m = marks(out)
    assert sp[0][1][0] in m and '/Lang' not in m[sp[0][1][0]] and len(m) == 4
    assert v['language']['all_match'] and clean(v), v['language']


def test_a_phrase_across_three_named_runs_in_a_form_is_one_span(tmp_path):
    src, out, log, v = apply_verify(tmp_path, OCR, wo_of(PHRASE))
    assert log['language_parts']['phrases'] == 1 and not log['language_parts']['refused'], log['language_parts']
    assert spans(out) == [('haw', [1, 2, 3], 'P', ['stm', 'stm', 'stm'])]
    m = marks(out)
    assert all('/Lang' not in m[k] for k in (1, 2, 3)) and m[0]['/Lang'] == 'en-US'
    assert v['language']['all_match'] and clean(v), v['language']


def test_a_running_head_in_a_named_form_run_is_hidden_inside_it(tmp_path):
    b = Book([{'form': 'BT /F1 9 Tf 72 770 Td /P /MC0 BDC (RUNNING HEAD) Tj EMC ET\n' + text_ops([1])}])
    b.forms[0].Resources.Properties = pikepdf.Dictionary(MC0=pikepdf.Dictionary(MCID=0))
    rh = b.el('P', 1, [b.stm(1, 0)]); p = b.el('P', 1, [b.stm(1, 1)]); b.index(100, 0, rh); b.index(100, 1, p)
    src = b.save(str(tmp_path / 'src.pdf'))
    w = tmp_path / 'wo.json'
    w.write_text(json.dumps({'artifacts': {'text_rules': [{'regex': 'RUNNING HEAD', 'band': 'top', 'pages': [1, 1], 'label': 'running head'}]}}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, w, out); run('verify.py', src, out)
    log = json.load(open(str(out) + '.log.json')); v = json.load(open(str(out) + '.verify.json'))
    assert log['applied'].get('artifact: "running head" (inside a form)') == 1 and not log.get('text_rules_refused'), log['applied']
    with pikepdf.open(out) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']
        assert b'/Artifact' in f.read_bytes() and len(pdf.Root.StructTreeRoot.K[0].K) == 1 and slot(pdf, 100, 0) is None
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0
    assert v['tree']['kids_not_drawn'] == 0


def test_mcsplit_counts_named_runs_through_the_streams_resources(tmp_path):
    """S1: with the form's resources, count_all, drawn_mcids and find_run see the named runs; without them (None), only
    inline dictionaries count, as before."""
    src = langpdf.build_in_form(str(tmp_path / 'f.pdf'), THREE, named=True)
    with pikepdf.open(src) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']; res = f.Resources
        ins = list(pikepdf.parse_content_stream(f))
        assert mcsplit.count_all(ins, res.Font, {}, res=res) == {0: 4, 1: 8, 2: 5}
        assert mcsplit.drawn_mcids(ins, res) == {0, 1, 2} and mcsplit.find_run(ins, 1, res) is not None
        assert mcsplit.count_all(ins, res.Font, {}) == {} and mcsplit.drawn_mcids(ins) == set() and mcsplit.find_run(ins, 1) is None
