"""#166 (steps that skip text drawn inside a form XObject): apply.py's steps on made-up books whose text sits inside one form
per page, as on 741 of the 764 collection books (an auto-tagged OCR layer). No book content. Each step reads or moves the
form's runs as it does page runs, or refuses them with its reason (handoff/166-form-text-tag-tree 01 §4, review 02 §3).
The tag-tree check mode is on (conftest): a wrong kept index stops the test."""
import os, sys, json, subprocess
import pikepdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_strays import Book, text_ops, slot  # noqa: E402
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages  # noqa: E402,F401


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off'),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stderr[-2000:]


def apply_verify(tmp_path, b, wo, name='src.pdf'):
    src = b.save(str(tmp_path / name))
    if callable(wo): wo = wo(src)                     # objects are renumbered on save: the work order names them after it
    w = tmp_path / ('wo-' + name + '.json'); w.write_text(json.dumps(wo))
    out = tmp_path / ('out-' + name)
    run('apply.py', src, w, out); run('verify.py', src, out)
    return src, str(out), json.load(open(str(out) + '.log.json')), json.load(open(str(out) + '.verify.json'))


def five(v):
    return v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0 \
        and not (v.get('fonts') or {}).get('unreadable') and v['tree']['parenttree_missing'] == 0 and v['tree']['parenttree_mismatched'] == 0


def og(e): return f'{e.objgen[0]} {e.objgen[1]}'


def table_wo(**reading):
    """A work order naming the saved file's one Table."""
    def make(src):
        with pikepdf.open(src) as pdf:
            t = next(e for e in pdf.Root.StructTreeRoot.K[0].K if str(e.S) == '/Table')
            return {'tables': [{'obj': og(t), **reading}]}
    return make


def test_a_page_run_and_a_form_run_with_the_same_number_are_told_apart(tmp_path):
    """Stage A: the page draws MCID 3 and its form draws MCID 3; each character carries its own stream."""
    b = Book([{'content': text_ops([3], y=100, word='Page'), 'form': text_ops([3], word='Form')}])
    src = b.save(str(tmp_path / 'x.pdf'))
    with pikepdf.open(src) as p: f = p.pages[0].Resources.XObject['/Fm0']; fnum = f.objgen[0]
    PL = plpages.Pages(src)
    by = {}
    for c in PL.pages[0].chars: by.setdefault(c.get('mcs'), '')
    for c in PL.pages[0].chars: by[c.get('mcs')] += c['text']
    assert by == {None: 'Page3', fnum: 'Form3'}


def test_a_heading_inside_a_form_gets_a_bookmark_and_reads_as_text(tmp_path):
    b = Book([{'form': text_ops([0, 1])}])
    h = b.el('H1', 1, [b.stm(1, 0)]); p = b.el('P', 1, [b.stm(1, 1)]); b.index(100, 0, h); b.index(100, 1, p)
    src, out, log, v = apply_verify(tmp_path, b, {})
    assert log['bookmarks']['built'] and five(v)
    with pikepdf.open(out) as pdf:
        assert str(pdf.Root.Outlines.First.Title) == 'Word0'
    assert not [e for e in v['structure']['empty_tag_examples'] if e['tag'] == 'H1']
    assert v['wcag']['reading_order']['pages_checked'] == 1                     # form runs are in the reading-order check


def test_a_table_inside_a_form_gets_header_cells(tmp_path):
    """Before #166 every cell read as empty (no /Stm kid was read), so no cell could be a header."""
    b = Book([{'form': text_ops([0, 1, 2, 3])}])
    t = b.el('Table', 1, [])
    rows = []
    for r in range(2):
        tr = b.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.TR, P=t, Pg=b.pdf.pages[0].obj, K=pikepdf.Array()))
        for c in range(2):
            m = 2 * r + c
            td = b.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.TD, P=tr, Pg=b.pdf.pages[0].obj, K=pikepdf.Array([b.stm(1, m)])))
            tr.K.append(td); b.index(100, m, td)
        t.K.append(tr); rows.append(tr)
    src, out, log, v = apply_verify(tmp_path, b, table_wo(header_rows=1))
    with pikepdf.open(out) as pdf:
        tt = next(e for e in pdf.Root.StructTreeRoot.K[0].K if str(e.S) == '/Table')
        assert [str(c.S) for r in tt.K for c in r.K] == ['/TH', '/TH', '/TD', '/TD']
    assert five(v) and not log['rejected']


def test_a_running_head_inside_a_form_is_hidden_inside_it(tmp_path):
    b = Book([{'form': 'BT /F1 9 Tf 72 770 Td /P <</MCID 0>> BDC (RUNNING HEAD) Tj EMC ET\n' + text_ops([1])}])
    rh = b.el('P', 1, [b.stm(1, 0)]); p = b.el('P', 1, [b.stm(1, 1)]); b.index(100, 0, rh); b.index(100, 1, p)
    wo = {'artifacts': {'text_rules': [{'regex': 'RUNNING HEAD', 'band': 'top', 'pages': [1, 1], 'label': 'running head'}]}}
    src, out, log, v = apply_verify(tmp_path, b, wo)
    assert log['applied'].get('artifact: "running head" (inside a form)') == 1 and not log.get('text_rules_refused')
    with pikepdf.open(out) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']
        assert b'/Artifact' in f.read_bytes() and b'/MCID 0' not in f.read_bytes()
        assert len(pdf.Root.StructTreeRoot.K[0].K) == 1 and slot(pdf, 100, 0) is None
    assert five(v) and v['tree']['kids_not_drawn'] == 0


def test_a_running_head_inside_a_form_drawn_on_two_pages_is_refused_not_counted_as_matched(tmp_path):
    form = 'BT /F1 9 Tf 72 770 Td /P <</MCID 0>> BDC (RUNNING HEAD) Tj EMC ET'
    b = Book([{'form': form}, {'content': text_ops([0])}])
    b.pdf.pages[1].obj.Resources.XObject = pikepdf.Dictionary(Fm0=b.forms[0])
    b.pdf.pages[1].obj.Contents = b.pdf.make_stream(text_ops([0]).encode() + b'\nq /Fm0 Do Q')
    rh = b.el('P', 1, [b.stm(1, 0)]); p = b.el('P', 2, [0]); b.index(100, 0, rh); b.index(1, 0, p)
    wo = {'artifacts': {'text_rules': [{'regex': 'RUNNING HEAD', 'band': 'top', 'pages': [1, 1], 'label': 'running head'}]}}
    src, out, log, v = apply_verify(tmp_path, b, wo)
    assert [x['why'] for x in log['text_rules_refused']] == ['the text is drawn inside a form used in more than one place']
    assert not any('artifact' in k for k in log['applied'])
    assert [d['why'] for d in log['deferred'] if 'running head' in d['what']] == [
        "matched text drawn inside a form that can't be changed (listed with each reason)"]     # matched, never counted as hidden


def test_a_merge_moves_a_form_run_with_its_form_index_entry(tmp_path):
    b = Book([{'form': text_ops([0, 1])}])
    lab = b.el('Label', 1, [b.stm(1, 0)]); h = b.el('H1', 1, [b.stm(1, 1)]); b.index(100, 0, lab); b.index(100, 1, h)
    src, out, log, v = apply_verify(tmp_path, b, {'merges': [{'style': 'Label', 'direction': 'next', 'with': ['H1']}]})
    assert log['applied'].get('heading: merged into next') == 1
    with pikepdf.open(out) as pdf: assert slot(pdf, 100, 0) == 'H1' and slot(pdf, 100, 1) == 'H1'
    assert five(v)


def test_a_merge_of_a_run_inside_a_shared_form_is_refused(tmp_path):
    b = Book([{'form': text_ops([0, 1])}, {'content': text_ops([0])}])
    b.pdf.pages[1].obj.Resources.XObject = pikepdf.Dictionary(Fm0=b.forms[0])
    b.pdf.pages[1].obj.Contents = b.pdf.make_stream(text_ops([0], y=100).encode() + b'\nq /Fm0 Do Q')
    lab = b.el('Label', 1, [b.stm(1, 0)]); h = b.el('H1', 1, [b.stm(1, 1)]); p = b.el('P', 2, [0])
    b.index(100, 0, lab); b.index(100, 1, h); b.index(1, 0, p)
    src, out, log, v = apply_verify(tmp_path, b, {'merges': [{'style': 'Label', 'direction': 'next', 'with': ['H1']}]})
    assert [r['why'] for r in log['rejected'] if r['op'].startswith('merge')] == ['the text is drawn inside a form used in more than one place']


def test_a_table_title_row_inside_a_shared_form_stays_with_the_reason(tmp_path):
    """review 02 item 5, never half-applied: a title row's text would move to the table's Caption, but its form is drawn
    on two pages, so its form index entry can't follow: the reading is rejected and nothing moves."""
    b = Book([{'form': text_ops([0, 1, 2])}, {'content': text_ops([0], y=100)}])
    b.pdf.pages[1].obj.Resources.XObject = pikepdf.Dictionary(Fm0=b.forms[0])
    b.pdf.pages[1].obj.Contents = b.pdf.make_stream(text_ops([0], y=100).encode() + b'\nq /Fm0 Do Q')
    t = b.el('Table', 1, []); p = b.el('P', 2, [0]); b.index(1, 0, p)
    for r, ms in enumerate([[0], [1, 2]]):
        tr = b.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.TR, P=t, Pg=b.pdf.pages[0].obj, K=pikepdf.Array()))
        for m in ms:
            td = b.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.TD, P=tr, Pg=b.pdf.pages[0].obj,
                                                        K=pikepdf.Array([b.stm(1, m)]), A=pikepdf.Dictionary(O=pikepdf.Name('/Table'), ColSpan=2) if len(ms) == 1 else pikepdf.Dictionary()))
            if len(ms) == 1: del td['/A']; td.A = pikepdf.Dictionary(O=pikepdf.Name('/Table'), ColSpan=2)
            tr.K.append(td); b.index(100, m, td)
        t.K.append(tr)
    src, out, log, v = apply_verify(tmp_path, b, table_wo(title_rows=1))
    assert [r['why'] for r in log['rejected'] if r['op'].startswith('tables')] == ['a title or note row stays in the table: the text is drawn inside a form used in more than one place']
    with pikepdf.open(out) as pdf: assert slot(pdf, 100, 0) == 'TD'



def test_a_running_head_half_in_a_shared_form_is_held_whole(tmp_path):
    """Review 04 M4: "RUNNING" in the page's content and "HEAD" in a form drawn on two pages, on one line. The form's half
    can't be hidden, so the page's half is held too, with the reason: never half hidden."""
    form = 'BT /F1 9 Tf 150 770 Td /P <</MCID 0>> BDC (HEAD) Tj EMC ET'
    page1 = 'BT /F1 9 Tf 72 770 Td /P <</MCID 0>> BDC (RUNNING) Tj EMC ET\n' + text_ops([1])
    b = Book([{'content': page1, 'form': form}, {'content': text_ops([0])}])
    b.pdf.pages[1].obj.Resources.XObject = pikepdf.Dictionary(Fm0=b.forms[0])
    b.pdf.pages[1].obj.Contents = b.pdf.make_stream(text_ops([0], y=100).encode() + b'\nq /Fm0 Do Q')
    r1 = b.el('P', 1, [0]); r2 = b.el('P', 1, [b.stm(1, 0)]); body = b.el('P', 1, [1]); p2 = b.el('P', 2, [0])
    b.index(0, 0, r1); b.index(100, 0, r2); b.index(0, 1, body); b.index(1, 0, p2)
    wo = {'artifacts': {'text_rules': [{'regex': 'RUNNING|HEAD', 'band': 'top', 'pages': [1, 1], 'label': 'running head'}]}}
    src, out, log, v = apply_verify(tmp_path, b, wo)
    assert not any('artifact' in k for k in log['applied'])
    held = [g for g in log['text_rule_guard'] if g.get('why')]
    assert held and held[0]['text'] == 'RUNNING' and "form that can't be changed" in held[0]['why'], log['text_rule_guard']
