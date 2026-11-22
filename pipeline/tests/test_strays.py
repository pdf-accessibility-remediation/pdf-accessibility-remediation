"""#168 (auto-tagged tree names form text as page text): lib/strays.py on tiny made-up PDFs (no book content), and the
repair through apply.py and verify.py. Each case is one shape the auto-tagger leaves (handoff/166-form-text-tag-tree 01
§1.1, review 02 §1): a page kid for a form's run or the next page's run, a kid for nothing, a Figure into a form that draws
only an artifact; and the cases the repair must leave alone (a run nearby that no tag names, a named BDC, a page that
can't be parsed, a form drawn from an annotation only)."""
import os, sys, json, subprocess
import pikepdf
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import strays  # noqa: E402

HELV = dict(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)


def text_ops(mcids, y=700, word='Word'):
    return '\n'.join(f'BT /F1 11 Tf 72 {y - 20 * i} Td /P <</MCID {m}>> BDC ({word}{m}) Tj EMC ET' for i, m in enumerate(mcids))


class Book:
    """pages: [{'content': str, 'form': str or None}]; the page draws its own content, then its form (/Fm0) if any. The
    tree is built with el(): elements under one Document, each with its kids as given."""
    def __init__(self, pages):
        self.pdf = pikepdf.new()
        self.font = self.pdf.make_indirect(pikepdf.Dictionary(**HELV))
        self.forms, self.nums = [], []
        for i, p in enumerate(pages):
            pg = self.pdf.add_blank_page(page_size=(612, 792))
            res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=self.font))
            body = p.get('content', '')
            f = None
            if p.get('form') is not None:
                f = self.pdf.make_stream(p['form'].encode('latin-1'))
                f.Type, f.Subtype, f.BBox = pikepdf.Name.XObject, pikepdf.Name.Form, [0, 0, 612, 792]
                f.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=self.font))
                f.StructParents = 100 + i
                res.XObject = pikepdf.Dictionary(Fm0=f)
                body += '\nq /Fm0 Do Q'
            if p.get('props'): res.Properties = pikepdf.Dictionary(p['props'])
            pg.obj.Resources = res
            pg.obj.Contents = self.pdf.make_stream(body.encode('latin-1'))
            pg.obj.StructParents = i
            self.forms.append(f)
        self.doc = self.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, K=pikepdf.Array()))
        self.st = self.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot, K=pikepdf.Array([self.doc])))
        self.doc.P = self.st
        self.pdf.Root.StructTreeRoot = self.st
        self.arrays = {}

    def el(self, s, page, kids, **extra):
        e = self.pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + s), P=self.doc,
                                                      Pg=self.pdf.pages[page - 1].obj, K=pikepdf.Array(kids), **extra))
        self.doc.K.append(e)
        return e

    def stm(self, page, m):
        return pikepdf.Dictionary(Type=pikepdf.Name.MCR, Stm=self.forms[page - 1], MCID=m)

    def mcr(self, page, m):
        return pikepdf.Dictionary(Type=pikepdf.Name.MCR, Pg=self.pdf.pages[page - 1].obj, MCID=m)

    def index(self, key, m, e):
        a = self.arrays.setdefault(key, [])
        while len(a) <= m: a.append(None)
        a[m] = e

    def save(self, path):
        nums = []
        for key in sorted(self.arrays): nums += [key, self.pdf.make_indirect(pikepdf.Array(self.arrays[key]))]
        self.st.ParentTree = self.pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array(nums)))
        self.st.ParentTreeNextKey = 1000
        self.pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
        self.pdf.save(path)
        return path


def slot(pdf, key, m):
    nums = pdf.Root.StructTreeRoot.ParentTree.Nums
    a = next(nums[j + 1] for j in range(0, len(nums), 2) if int(nums[j]) == key)
    return None if m >= len(a) or a[m] is None else str(a[m].S).lstrip('/')


def kids_of(e):
    k = e.get('/K')
    return [] if k is None else list(k) if isinstance(k, pikepdf.Array) else [k]


def form_book(tmp_path, same_element=False):
    """Page 1's text sits in its form (MCIDs 0, 1); a P names them by /Stm. A stray page kid 1 sits on that P (same_element)
    or on a second P that the page index also names (another element)."""
    b = Book([{'form': text_ops([0, 1])}])
    p = b.el('P', 1, [b.stm(1, 0), b.stm(1, 1)])
    b.index(100, 0, p); b.index(100, 1, p)
    if same_element: p.K.append(1); b.index(0, 1, p)
    else:
        q = b.el('P', 1, [1]); b.index(0, 1, q)
    return b.save(str(tmp_path / 'form.pdf'))


def test_page_kid_for_a_form_run_named_by_another_element(tmp_path):
    with pikepdf.open(form_book(tmp_path)) as pdf:
        rec = strays.repair(pdf, empties='leave')
        assert rec['removed']['page_kids'] == 1 and rec['removed']['slots_cleared'] == 1 and rec['kept'] == 0
        assert slot(pdf, 0, 1) is None and slot(pdf, 100, 1) == 'P'          # the page slot cleared, the form's kept
        assert len(rec['emptied']) == 1                                          # the second P has nothing left
        assert strays.counts(pdf) == {'kids_not_drawn': 0, 'kids_not_drawn_pages': [], 'runs_named_twice': 0, 'runs_named_twice_pages': []}


def test_page_kid_duplicating_the_same_elements_stm_kid(tmp_path):
    with pikepdf.open(form_book(tmp_path, same_element=True)) as pdf:
        rec = strays.repair(pdf)
        p = pdf.Root.StructTreeRoot.K[0].K[0]
        assert rec['removed']['page_kids'] == 1 and not rec['emptied']
        assert [int(k.MCID) for k in kids_of(p)] == [0, 1] and all('/Stm' in k for k in kids_of(p))


def test_cross_page_kid_whose_run_the_next_page_holds(tmp_path):
    """bringing's shape: a P on page 2 names MCID 5, which only page 1 draws and page 1's own P names."""
    b = Book([{'content': text_ops([4, 5])}, {'content': text_ops([0, 1])}])
    a = b.el('P', 1, [4, 5]); b.index(0, 4, a); b.index(0, 5, a)
    c = b.el('P', 2, [0, 5, 1]); b.index(1, 0, c); b.index(1, 1, c); b.index(1, 5, c)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        rec = strays.repair(pdf)
        assert rec['removed']['page_kids'] == 1 and rec['removed']['slots_cleared'] == 1
        assert [int(k) for k in kids_of(pdf.Root.StructTreeRoot.K[0].K[1])] == [0, 1]


def test_kid_drawn_nowhere_and_kid_with_a_free_run_nearby(tmp_path):
    """MCID 9 is drawn nowhere: removed. MCID 7 is drawn on page 2 and no tag names it there: the kid on page 1 may be its
    only pointer, so it stays, listed."""
    b = Book([{'content': text_ops([0])}, {'content': text_ops([7])}])
    a = b.el('P', 1, [0, 9, 7]); b.index(0, 0, a); b.index(0, 9, a); b.index(0, 7, a)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        rec = strays.repair(pdf)
        assert rec['removed']['page_kids'] == 1 and rec['kept'] == 1
        assert rec['kept_listed'][0]['mcid'] == 7 and 'no tag names' in rec['kept_listed'][0]['why']
        assert [int(k) for k in kids_of(pdf.Root.StructTreeRoot.K[0].K[0])] == [0, 7]
        assert strays.counts(pdf)['kids_not_drawn'] == 1


def test_figure_into_a_form_that_draws_only_an_artifact(tmp_path):
    """Fault 3: a Figure per page names MCID 0 of a form whose image the tagger marked /Artifact. intake removes the
    Figures (empties='remove'); apply leaves them to fix_empty_tags (empties='leave')."""
    for mode in ('remove', 'leave'):
        b = Book([{'content': text_ops([0]), 'form': 'q /Artifact BMC 0 0 m 10 10 l S EMC Q'}])
        t = b.el('P', 1, [0]); b.index(0, 0, t)
        f = b.el('Figure', 1, [b.stm(1, 0)]); b.index(100, 0, f)
        with pikepdf.open(b.save(str(tmp_path / f'{mode}.pdf'))) as pdf:
            rec = strays.repair(pdf, empties=mode)
            assert rec['removed']['stm_kids'] == 1 and slot(pdf, 100, 0) is None
            doc = pdf.Root.StructTreeRoot.K[0]
            if mode == 'remove': assert rec['removed']['elements'] == 1 and [str(e.S) for e in kids_of(doc)] == ['/P']
            else: assert len(rec['emptied']) == 1 and len(kids_of(doc)) == 2


def test_empty_element_with_actualtext_is_kept_in_intake(tmp_path):
    """sands' shape: the Span's only kid points at nothing; the Span carries ActualText, so it stays (listed by apply's
    fix_empty_tags), even with empties='remove'."""
    b = Book([{'content': text_ops([0])}])
    p = b.el('P', 1, [0]); b.index(0, 0, p)
    s = b.el('Span', 1, [3], ActualText=pikepdf.String('x')); b.index(0, 3, s)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        rec = strays.repair(pdf, empties='remove')
        assert rec['removed']['page_kids'] == 1 and rec['removed']['elements'] == 0 and len(rec['emptied']) == 1
        assert len(kids_of(pdf.Root.StructTreeRoot.K[0])) == 2


def test_named_properties_are_drawn(tmp_path):
    """hawaii3's shape: /P /MC0 BDC, the MCID in the page's /Properties: the kid is drawn and stays."""
    content = 'BT /F1 11 Tf 72 700 Td /P /MC0 BDC (Named) Tj EMC ET'
    b = Book([{'content': content, 'props': {'/MC0': pikepdf.Dictionary(MCID=4)}}])
    p = b.el('P', 1, [4]); b.index(0, 4, p)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        assert strays.find(pdf)['strays'] == [] and strays.repair(pdf)['removed']['page_kids'] == 0


def test_page_that_fails_to_parse_is_left_alone(tmp_path):
    b = Book([{'content': text_ops([0])}])
    bad = b.pdf.make_stream(b'not deflate data'); bad.Filter = pikepdf.Name.FlateDecode
    b.pdf.pages[0].obj.Contents = bad                                     # the page's content can't be read at all
    p = b.el('P', 1, [0, 3]); b.index(0, 0, p)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        F = strays.find(pdf)
        assert F['strays'] == [] and F['skipped'].get("its page's content could not be read") == 2
        assert strays.repair(pdf)['removed']['page_kids'] == 0


def test_stm_kid_into_a_form_drawn_only_by_an_annotation_is_kept(tmp_path):
    """An /Stm kid is judged by the form's own content: a form an annotation's appearance draws (no page draws it) holds
    MCID 0, so its kid stays."""
    b = Book([{'content': text_ops([0])}])
    f = b.pdf.make_stream(b'BT /F1 9 Tf 2 2 Td /P <</MCID 0>> BDC (Note) Tj EMC ET')
    f.Type, f.Subtype, f.BBox = pikepdf.Name.XObject, pikepdf.Name.Form, [0, 0, 50, 20]
    f.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=b.font)); f.StructParents = 200
    b.pdf.pages[0].obj.Annots = pikepdf.Array([b.pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Widget, Rect=[0, 0, 50, 20], AP=pikepdf.Dictionary(N=f)))])
    p = b.el('P', 1, [0]); b.index(0, 0, p)
    n = b.el('Form', 1, [pikepdf.Dictionary(Type=pikepdf.Name.MCR, Stm=f, MCID=0)]); b.index(200, 0, n)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        assert strays.find(pdf)['strays'] == [] and strays.repair(pdf)['removed']['stm_kids'] == 0


def test_runs_named_twice_counted(tmp_path):
    b = Book([{'content': text_ops([0])}])
    p = b.el('P', 1, [0]); q = b.el('P', 1, [b.mcr(1, 0)]); b.index(0, 0, p)
    with pikepdf.open(b.save(str(tmp_path / 'x.pdf'))) as pdf:
        c = strays.counts(pdf)
        assert c['runs_named_twice'] == 1 and c['runs_named_twice_pages'] == [1] and c['kids_not_drawn'] == 0


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off'),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stderr[-2000:]


def test_apply_repairs_and_verify_counts_nothing_left(tmp_path):
    """Through apply.py and verify.py: the stray kid and its slot go, the emptied P goes in fix_empty_tags, the Figure's
    alt text is refused (it pointed at nothing), and verify finds no reference to nothing and no stale index entry."""
    b = Book([{'form': text_ops([0, 1]) + '\nq /Artifact BMC 0 0 m 10 10 l S EMC Q'}])
    p = b.el('P', 1, [b.stm(1, 0), b.stm(1, 1)]); b.index(100, 0, p); b.index(100, 1, p)
    q = b.el('P', 1, [1]); b.index(0, 1, q)
    f = b.el('Figure', 1, [b.stm(1, 5)])
    src = b.save(str(tmp_path / 'src.pdf'))
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'alt': [{'obj': f'{f.objgen[0]} {f.objgen[1]}', 'alt': 'A picture'}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, wo, out); run('verify.py', src, out)
    log = json.load(open(str(out) + '.log.json')); v = json.load(open(str(out) + '.verify.json'))
    assert log['strays']['removed'] == {'page_kids': 1, 'stm_kids': 1, 'slots_cleared': 1, 'elements': 0}
    assert any('the figure holds nothing' in r['why'] for r in log['rejected'])
    assert len(log['empty_tags']['removed']) == 2 and not log['empty_tags']['kept']
    assert v['tree']['kids_not_drawn'] == 0 and v['tree']['runs_named_twice'] == 0 and v['index']['stale_entries'] == 0


def test_runs_named_twice_lead_what_needs_a_person_without_blocking():
    """Review 02 item 8: text two tags name, left after the repair, is listed first among rank 1 ("What Needs a Person"),
    never as a safety check; references to nothing alone stay an ordinary CHECK row."""
    from lib import glance as G
    safe = [f'| {n} | OK | x |' for n, _ in G.SAFETY]
    def md(row): return '\n'.join(['# Remediation Review: b.pdf', '', '## Automated Checks', '', '| Check | Result | Detail |', '|---|---|---|']
                                  + safe + [f'| Tag tree consistent | **CHECK** | {row} |', ''])
    g = G.glance({'verify': {'tree': {'runs_named_twice': 2, 'runs_named_twice_pages': [4, 9], 'kids_not_drawn': 0}}},
                 md('0 missing · 0 mismatched · 2 text runs named by two tags (PDF 4, PDF 9)'))
    lead = [x for x in g['issues'] if x['rank'] == 1]                    # 'lead' only orders: first among rank 1
    assert g['safety_ok'] and lead and lead[0]['rank'] == 1 and lead[0]['pages'] == [4, 9] and 'named by two tags' in lead[0]['text']
    g = G.glance({'verify': {'tree': {'runs_named_twice': 0, 'kids_not_drawn': 3}}}, md('0 missing · 0 mismatched · 3 references to text not drawn there'))
    assert g['safety_ok'] and not [x for x in g['issues'] if 'named by two tags' in x['text'] and x['rank'] == 1]
    assert [x['rank'] for x in g['issues'] if 'Tag tree consistent' in x['text']] == [2]


def test_a_named_bdc_is_tagged_content_everywhere(tmp_path):
    """Review 04 H1 (hawaii3's three runs): a run whose BDC names its properties (/P /MC0 BDC) is tagged content for every
    reader: not untagged characters, not an untagged object, and its ParentTree entry is not stale."""
    content = 'BT /F1 11 Tf 72 700 Td /P /MC0 BDC (Named) Tj EMC ET\n' + text_ops([1], y=650)
    b = Book([{'content': content, 'props': {'/MC0': pikepdf.Dictionary(MCID=0)}}])
    p = b.el('P', 1, [0]); q = b.el('P', 1, [1]); b.index(0, 0, p); b.index(0, 1, q)
    src = b.save(str(tmp_path / 'src.pdf'))
    wo = tmp_path / 'wo.json'; wo.write_text('{}')
    out = tmp_path / 'out.pdf'
    run('apply.py', src, wo, out); run('verify.py', src, out)
    v = json.load(open(str(out) + '.verify.json'))
    assert v['untagged_chars'] == 0 and not (v.get('untagged_objects') or {}).get('total'), (v['untagged_chars'], v.get('untagged_objects'))
    assert v['index']['stale_entries'] == 0 and v['tree']['content_mcids_not_in_tree'] == 0
