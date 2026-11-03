"""test_review_draft.py: the review page's Build a Draft PDF (issue #57), on test_synthetic.py's three-page figure PDF.

    python -m pytest tests/test_review_draft.py -q

core.draft_pdf (the same check as Finish, then apply.py with APPLY_DRAFT=1) and the server's /draft, /draft.pdf: the
draft has the reviewer's changes and the draft mark, a build that fails leaves no file, nothing in the run folder is
written but the auto-saved draft, and the draft's folder is gone once the server stops. No model; veraPDF is off.
"""
import os, sys, json, time, glob, hashlib, tempfile, threading, subprocess, urllib.request
import pikepdf
import pytest

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_synthetic import figure_pdf, run  # noqa: E402
from test_review_sessions import free_port  # noqa: E402
from review import core, server  # noqa: E402

ALT = 'alt:16 0'                                       # the figure's alt card (figure_pdf's Figure is object 16)

@pytest.fixture
def R(tmp_path, monkeypatch):
    """A run folder in the state a REVIEW=1 stop leaves: the audit, the AI's order (one alt) and review_items.json."""
    monkeypatch.setenv('REVIEW_DRYRUN', 'off'); monkeypatch.setenv('VERAPDF', 'off')
    src = figure_pdf(tmp_path / 'book.pdf')
    R = tmp_path / 'run'; R.mkdir()
    run('audit.py', src, R / '_audit')
    sha = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    ai = {'schema': 'workorder/0.1', 'source': {'sha256': sha}, 'alt': [{'obj': '16 0', 'alt': 'A blue box'}]}
    core.save(str(R / 'workorder.ai.json'), ai)
    core.prepare(str(R), str(src))
    return R

def figure_alt(path):
    with pikepdf.open(path) as p:
        return [str(e.Alt) for e in p.objects if isinstance(e, pikepdf.Dictionary) and e.get('/S') == '/Figure' and '/Alt' in e]

def draft_of(R, decisions, out):
    data = core.load(str(R / 'review_items.json')); ai = core.load(str(R / 'workorder.ai.json'))
    wo = core.apply_decisions(ai, data['items'], decisions)
    return core.draft_pdf(str(R), data['pdf'], ai, wo, str(out), items=data['items'], decisions=decisions)

def listing(R):
    return sorted((os.path.relpath(os.path.join(d, n), R), os.path.getmtime(os.path.join(d, n))) for d, _, ns in os.walk(R) for n in ns)

def test_a_changed_alt_is_in_the_draft_and_the_draft_is_marked(R, tmp_path):
    before = listing(R)
    out = tmp_path / 'd' / 'draft.pdf'; out.parent.mkdir()
    res = draft_of(R, {ALT: {'status': 'changed', 'value': 'A red square'}}, out)
    assert figure_alt(out) == ['A red square'] and res['dropped'] == 0 and res['bytes'] == os.path.getsize(out)
    with pikepdf.open(out) as p: assert 'Not final' in str(p.docinfo['/RemediationDraft'])
    assert listing(R) == before                                                  # nothing in the run folder is written
    plain = tmp_path / 'plain.pdf'                                               # the mark is the draft's alone
    run('apply.py', core.load(str(R / 'review_items.json'))['pdf'], R / 'workorder.ai.json', plain)
    with pikepdf.open(plain) as p: assert '/RemediationDraft' not in p.docinfo

def test_a_choice_the_check_drops_is_left_out_of_the_draft(R, tmp_path):
    res = draft_of(R, {ALT: {'status': 'changed', 'value': '   '}}, tmp_path / 'draft.pdf')
    assert res['dropped'] == 1
    assert figure_alt(tmp_path / 'draft.pdf') == ['A blue box']                 # dropped: the original's alt stays, as at Finish

def test_a_draft_that_cannot_be_built_leaves_no_file(R, tmp_path):
    out = tmp_path / 'draft.pdf'
    data = core.load(str(R / 'review_items.json')); ai = core.load(str(R / 'workorder.ai.json'))
    out.write_bytes(b'an older draft')
    with pytest.raises(ValueError, match='changed since the review started'):    # another file than the order was written for
        core.draft_pdf(str(R), data['pdf'], dict(ai, source={'sha256': '0' * 64}), ai, str(out))
    junk = tmp_path / 'junk.pdf'; junk.write_bytes(b'not a PDF')                # the executor stops
    sha = hashlib.sha256(b'not a PDF').hexdigest()
    with pytest.raises(ValueError, match='could not be built'):
        core.draft_pdf(str(R), str(junk), dict(ai, source={'sha256': sha}), dict(ai, source={'sha256': sha}), str(out))
    assert not out.exists() and not os.path.exists(str(out) + '.log.json')

def call(port, path, body=None):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e: return e.code, e.read(), dict(e.headers)

def start(R):
    port = free_port(); out = {}
    t = threading.Thread(target=lambda: out.update(v=server.serve(str(R), '2026-11-02', port, open_browser=False)), daemon=True)
    t.start()
    for _ in range(100):
        try:
            if call(port, '/draft')[0] == 200: break
        except OSError: time.sleep(0.1)
    return port, t

def built(port, body):
    """POST /draft, then GET /draft until it is no longer building."""
    assert call(port, '/draft', body)[0] == 202
    for _ in range(600):
        d = json.loads(call(port, '/draft')[1])
        if d['state'] != 'building': return d
        time.sleep(0.1)

def drafts(): return set(glob.glob(os.path.join(tempfile.gettempdir(), server.DRAFT_PREFIX + '*')))

BODY = {'reviewer': 'Kim', 'decisions': {ALT: {'status': 'changed', 'value': 'A red square'}}, 'additions': []}
FINISH = dict(BODY, gaps_ack={'h1': 'later', 'figures_without_alt': 'later'}, accept_unreviewed=True)

def test_the_server_builds_serves_and_removes_the_draft(R):
    had = drafts()
    port, t = start(R)
    assert call(port, '/draft.pdf')[0] == 404                                    # nothing built yet
    assert json.loads(call(port, '/draft')[1])['state'] == 'idle'
    st, b, _ = call(port, '/draft', BODY)
    assert st == 202 and json.loads(b)['state'] == 'building'
    for _ in range(600):
        d = json.loads(call(port, '/draft')[1])
        if d['state'] != 'building': break
        time.sleep(0.1)
    assert d['state'] == 'ready' and d['result']['dropped'] == 0 and d['seconds'] >= 0, d
    assert d['result']['problems'] == {'fields': [], 'conflicts': [], 'unplaced': []}
    st, pdf, hd = call(port, '/draft.pdf?x=../../review_items.json')             # the query never picks the file
    assert st == 200 and pdf.startswith(b'%PDF') and hd['Content-Disposition'] == 'attachment; filename="book_draft.pdf"'
    assert core.load(str(R / 'review_decisions.json'))['decisions'] == BODY['decisions']   # kept, as auto-save does
    assert call(port, '/finish', FINISH)[0] == 200
    t.join(10); assert not t.is_alive() and drafts() <= had                      # the server stopped, and the draft went with it

def test_one_build_at_a_time_and_finish_does_not_wait_for_it(R, monkeypatch):
    go = threading.Event()
    def slow(*a, **k): go.wait(30); raise ValueError('stopped')
    monkeypatch.setattr(core, 'draft_pdf', slow)
    had = drafts()
    port, t = start(R)
    try:
        assert call(port, '/draft', BODY)[0] == 202
        st, b, _ = call(port, '/draft', BODY)
        assert st == 409 and 'already' in json.loads(b)['error']
        assert call(port, '/finish', FINISH)[0] == 200
        t.join(10); assert not t.is_alive() and drafts() <= had                  # stopped while the draft was still building
    finally: go.set()

def test_a_dead_servers_draft_folder_is_swept(tmp_path):
    dead = tempfile.mkdtemp(prefix=server.DRAFT_PREFIX); live = tempfile.mkdtemp(prefix=server.DRAFT_PREFIX)
    p = subprocess.Popen([sys.executable, '-c', 'pass']); p.wait()                # a pid that has ended
    open(os.path.join(dead, 'pid'), 'w').write(str(p.pid)); open(os.path.join(live, 'pid'), 'w').write(str(os.getpid()))
    try:
        server.sweep_drafts()
        assert not os.path.exists(dead) and os.path.isdir(live)
    finally:
        import shutil; shutil.rmtree(live, ignore_errors=True); shutil.rmtree(dead, ignore_errors=True)

def test_the_draft_name():
    assert server.draft_name('Clans of Hawaii.pdf') == 'Clans of Hawaii_draft.pdf'
    assert server.draft_name('a"b\r\n.pdf') == 'a_b_draft.pdf' and server.draft_name('') == 'book_draft.pdf'

def test_a_choice_left_out_is_worded_as_on_its_card(R):
    """The draft's list is the check's verdict on the cards (core.problems): the same fix, the same card, the same origin."""
    port, t = start(R)
    d = built(port, dict(BODY, decisions={ALT: {'status': 'changed', 'value': '   '}}))
    assert d['state'] == 'ready' and d['result']['dropped'] == 1, d
    assert d['result']['problems']['fields'] == [{'card': ALT, 'why': 'not a figure or empty alt',
                                                  'fix': core.fix('not a figure or empty alt', 3), 'origin': 'review'}]
    assert call(port, '/finish', FINISH)[0] == 200                                # a valid choice again: Finish closes it
    t.join(10); assert not t.is_alive()
