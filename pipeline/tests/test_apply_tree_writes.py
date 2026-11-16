"""test_apply_tree_writes.py: apply.py keeps its tag-tree index between steps and walks the tree again only after a write
(#93 (improve performance: home and batch pages, first-time "Review Again", and PDF pipeline step timing), Part 3, C2;
review 12 M1 and M3). These rules keep the kept index right.

    python -m pytest tests/test_apply_tree_writes.py -q

Rule 1, read from the code (apply.py and every lib/*.py, whether apply.py imports it directly, through another module or
not at all: review 14 L2): no write of a key the index depends on (/K /P /Pg
/Type /MCID /Stm) except through tree_set(): no attribute assignment (n.K = …), no literal subscript assignment or del
(n['/K'] = …), no .update( naming one of them in a dict literal or as a keyword, no __setattr__ / __setitem__ called by name,
no setattr() naming one. What a rule can't read is left to the check mode: a write with a computed key (n[key] = …;
apply.py has over a hundred such writes on dicts and lists, and the code alone can't tell a pikepdf object from a dict),
and an .update( on an object built elsewhere. The check mode (APPLY_TREE_CHECK=1, always on in pytest and
tools/regression.py) walks again wherever the kept index would be used and stops on any difference.
Rule 2, apply.py: /K is read only through kids(), which returns a Python list, so no /K array is ever changed in place.
Then, on a real apply.py run (runpy, its globals kept): a /MCID written through tree_set() after a kept walk is seen by the
next reindex(), and a /MCID written around it is caught by the check mode, which prints its marker and stops with
TreeIndexStale (a BaseException, so apply.py's `except Exception` handlers can't swallow it).
"""
import os, re, ast, sys, json, runpy, contextlib, io
import pikepdf
import pytest

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = {'K', 'P', 'Pg', 'Type', 'MCID', 'Stm'}
KEYS = {'/' + n for n in NAMES}

def imported_libs():
    src = open(os.path.join(PIPE, 'apply.py'), encoding='utf-8').read()
    mods = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.ImportFrom) and n.module == 'lib': mods |= {a.name for a in n.names}
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith('lib.'): mods.add(n.module.split('.', 1)[1])
    return sorted(os.path.join(PIPE, 'lib', m + '.py') for m in mods)

def const(x): return x.value if isinstance(x, ast.Constant) else None

def rule1_breaches(path):
    tree = ast.parse(open(path, encoding='utf-8').read())
    inside = set()                                       # tree_set's own body may write
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef) and f.name == 'tree_set': inside |= {id(n) for n in ast.walk(f)}
    out = []
    def bad_target(t):
        if isinstance(t, ast.Attribute) and t.attr in NAMES: return True
        if isinstance(t, ast.Subscript) and const(t.slice) in KEYS: return True
        if isinstance(t, (ast.Tuple, ast.List)): return any(bad_target(e) for e in t.elts)
        return False
    for n in ast.walk(tree):
        if id(n) in inside: continue
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            ts = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(bad_target(t) for t in ts): out.append(n.lineno)
        elif isinstance(n, ast.Delete) and any(bad_target(t) for t in n.targets): out.append(n.lineno)
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr in ('__setattr__', '__setitem__', '__delitem__', '__delattr__'): out.append(n.lineno)
            elif isinstance(f, ast.Name) and f.id in ('setattr', 'delattr') and len(n.args) > 1 and const(n.args[1]) in NAMES | KEYS: out.append(n.lineno)
            elif isinstance(f, ast.Attribute) and f.attr == 'update':
                if any(isinstance(a, ast.Dict) and any(const(k) in KEYS | NAMES for k in a.keys) for a in n.args) or any(k.arg in NAMES for k in n.keywords):
                    out.append(n.lineno)
    return out

def all_libs():
    """Every lib/*.py: a module apply.py reaches only through another one (ocrwords.py, workorder_check.py) is scanned
    too, and so is one it may import later (review 14 L2)."""
    import glob
    return sorted(glob.glob(os.path.join(PIPE, 'lib', '*.py')))

def test_rule_1_every_tree_write_goes_through_tree_set():
    libs = all_libs()
    assert set(imported_libs()) <= set(libs) and len(libs) > len(imported_libs())
    for p in [os.path.join(PIPE, 'apply.py')] + libs:
        assert rule1_breaches(p) == [], (os.path.basename(p), rule1_breaches(p))

def test_rule_1_sees_each_write_form():
    """The rule itself, on a snippet holding each form it must refuse (and the ones it leaves to the check mode)."""
    import tempfile
    snippet = '''
n.K = a
n.MCID = 3
n['/Stm'] = s
del n['/Pg']
n.update({'/K': a})
n.update(Type=t)
pikepdf.Object.__setattr__(n, 'P', p)
setattr(n, 'Pg', p)
n[key] = v
def tree_set(n, key, value):
    n[key] = value; n.K = value
'''
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f: f.write(snippet)
    try: assert rule1_breaches(f.name) == [2, 3, 4, 5, 6, 7, 8, 9]      # n[key] = v: the check mode's job
    finally: os.remove(f.name)

def test_rule_2_k_is_read_only_through_kids():
    tree = ast.parse(open(os.path.join(PIPE, 'apply.py'), encoding='utf-8').read())
    allowed = set()
    for f in ast.walk(tree):
        if isinstance(f, ast.FunctionDef) and f.name in ('kids', 'tree_set'): allowed |= {id(n) for n in ast.walk(f)}
    bad = []
    for n in ast.walk(tree):
        if id(n) in allowed: continue
        if isinstance(n, ast.Attribute) and n.attr == 'K': bad.append(n.lineno)
        elif isinstance(n, ast.Subscript) and const(n.slice) == '/K': bad.append(n.lineno)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'get' and n.args and const(n.args[0]) == '/K': bad.append(n.lineno)
    assert bad == [], bad

# ------------------------------------------------------------------ a real apply.py run, its globals kept
def tree_pdf(path):
    """One page, two paragraphs: one owns MCID 0 through an MCR, one MCID 1 as a plain number."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    c = b'/P <</MCID 0>> BDC BT /F1 12 Tf 72 700 Td (First paragraph.) Tj ET EMC\n/P <</MCID 1>> BDC BT /F1 12 Tf 72 680 Td (Second one.) Tj ET EMC\n'
    pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 612, 792], StructParents=0,
                                                     Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)), Contents=pdf.make_stream(c))))
    pg = pdf.pages[0].obj
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    p1 = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg,
                                              K=pikepdf.Array([pikepdf.Dictionary(Type=pikepdf.Name.MCR, Pg=pg, MCID=0)])))
    p2 = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg, K=1))
    doc.K = pikepdf.Array([p1, p2]); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=[0, pikepdf.Array([p1, p2])]))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path, deterministic_id=True)
    return path

@pytest.fixture
def applied(tmp_path, monkeypatch):
    """apply.py run in this process on tree_pdf with an empty work order; its globals afterwards."""
    src = tree_pdf(str(tmp_path / 'b.pdf')); wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'schema': 'workorder/0.2'}))
    monkeypatch.setenv('APPLY_TREE_CHECK', '1')
    monkeypatch.setenv('APPLY_TREE_STALE_LOG', str(tmp_path / 'own-stale.log'))   # this test's stops are its own
    monkeypatch.setenv('VERAPDF', 'off')
    monkeypatch.setattr(sys, 'argv', ['apply.py', src, str(wo), str(tmp_path / 'out.pdf')])
    monkeypatch.syspath_prepend(PIPE)
    with contextlib.redirect_stdout(io.StringIO()):
        g = runpy.run_path(os.path.join(PIPE, 'apply.py'), run_name='__main__')
    return g['reindex'].__globals__, tmp_path            # the live globals (run_path hands back a copy)

def mcr_of(g):
    for n, _ in g['all_elems']():
        for k in g['kids'](n):
            if g['is_mcr'](k): return n, k
    raise AssertionError('no MCR in the test tree')

def test_an_mcid_written_through_tree_set_is_seen_by_the_next_reindex(applied):
    g, _ = applied
    g['reindex'](); g['reindex']()                      # the second call uses the kept index (and checks it)
    el, ref = mcr_of(g)
    pno = next(p for (p, m), o in g['owner'].items() if o.objgen == el.objgen)
    v = g['TREE_V']; g['tree_set'](ref, '/MCID', 7); assert g['TREE_V'] == v + 1
    g['reindex']()
    assert g['owner'][(pno, 7)].objgen == el.objgen and (pno, 0) not in g['owner']

def test_a_write_around_tree_set_is_stopped_by_the_check_mode(applied, capsys):
    g, tmp = applied
    g['reindex'](); el, ref = mcr_of(g)
    ref['/MCID'] = 9                                       # not through tree_set: the kept index is now wrong
    with pytest.raises(BaseException) as e: g['reindex']()
    assert type(e.value).__name__ == 'TreeIndexStale' and not isinstance(e.value, Exception)
    err = capsys.readouterr().err
    assert re.search(r'^TREE INDEX STALE: the kept tag-tree index differs from a new walk, used by ', err, re.M), err
    assert 'TREE INDEX STALE:' in (tmp / 'own-stale.log').read_text()

def test_all_elems_hands_out_a_copy(applied):
    g, _ = applied
    a = g['all_elems'](); a.clear()
    assert g['all_elems']()

def test_run_apply_fails_loudly_on_the_marker(tmp_path, monkeypatch):
    """review/core.py's run_apply (the trial run and the draft): a check-mode stop is raised, never a soft result."""
    from review import core
    stub = tmp_path / 'apply.py'
    stub.write_text("import sys\nprint('TREE INDEX STALE: the kept list of tag-tree elements differs from a new walk, used by x', file=sys.stderr)\nsys.exit(1)\n")
    monkeypatch.setattr(core, 'HERE', str(tmp_path)); (tmp_path / 'o').mkdir()
    with pytest.raises(core.TreeIndexStale):
        core.run_apply('in.pdf', {'schema': 'workorder/0.2'}, str(tmp_path / 'o' / 'out.pdf'), env=dict(os.environ, APPLY_TREE_CHECK='1'))
    code, log = core.run_apply('in.pdf', {'schema': 'workorder/0.2'}, str(tmp_path / 'o' / 'out.pdf'), env=dict(os.environ, APPLY_TREE_CHECK=''))
    assert code == 1 and log is None                       # production: as before, the caller words it
