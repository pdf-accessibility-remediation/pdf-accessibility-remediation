"""test_review_draft.py: the review page's Build a Draft PDF (issue #57), on test_synthetic.py's three-page figure PDF.

    python -m pytest tests/test_review_draft.py -q

core.draft_pdf (the same check as Finish, then apply.py with APPLY_DRAFT=1) and the server's /draft, /draft.pdf: the
draft has the reviewer's changes and the draft mark, a build that fails leaves no file, nothing in the run folder is
written but the auto-saved draft, and the draft's folder is gone once the server stops. No model; veraPDF is off.
"""
import os, re, sys, json, time, glob, hashlib, tempfile, threading, subprocess, urllib.request
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

# ------------------------------------------------------------------ the server's listen queue (a bug found on dwellings' review page)
def test_a_burst_of_connections_is_never_refused():
    """A page full of cards asks for many images at once while PDFium holds the accept loop up; the default queue of 5
    overflowed and the browser got reset connections: broken thumbnails until something asked again."""
    import http.server, concurrent.futures as C
    assert server.Server.request_queue_size >= 128
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self): self.send_response(200); self.send_header('Content-Length', '2'); self.end_headers(); self.wfile.write(b'ok')
    srv = server.Server(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    def get(_):
        with urllib.request.urlopen(f'http://127.0.0.1:{srv.server_address[1]}/', timeout=30) as r: return r.status
    try:
        with C.ThreadPoolExecutor(40) as ex: assert set(ex.map(get, range(400))) == {200}
    finally: srv.shutdown(); srv.server_close()

# ------------------------------------------------------------------ 15: the review page in one step (#93, Patrick 2026-11-11)

def test_the_review_page_is_drawn_while_it_is_read_with_what_it_used_to_ask_for(R):
    """The review page's script (with its data) is read in the head and only defines; the call at the end of the body draws
    the page. The line beside Finish (the check of the saved choices), the draft line and the first OCR pages' text come
    with the page: the check is exactly what /keep answers for the same choices."""
    p = open(os.path.join(PIPE, 'review', 'page.html'), encoding='utf-8').read()
    head = p.split('</head>')[0]
    assert p.index('<script>\n') < p.index('function bootReview() {') < p.index('</head>') < p.index('<body>') < p.index('<script>bootReview()</script>') < p.index('</body>')
    assert p.count('<script>') == 2 and '/*REVIEW_DATA*/null' in head
    assert "if (DATA.check && !(state.saved_at && state.saved_at !== (srv.saved_at || ''))) { gotCheck(DATA.check, state.saved_at); refreshMoves(DATA.check.move_previews); }" in p
    assert p.count("box(src, 220)") == 1 and "box('_audit/' + c.figure, 220)" in p and "const SIZES = DATA.img_sizes || {};" in p
    assert "if (DATA.draft) firstDraft(DATA.draft); else fetch('/draft')" in p and "(OCR_TEXT[p.page] != null ? esc(OCR_TEXT[p.page]) : 'Loading the text…')" in p
    port, t = start(R)
    try:
        assert call(port, '/keep', BODY)[0] == 200                                         # some saved choices on disk…
    finally:
        assert call(port, '/finish', FINISH)[0] == 200; t.join(10)
    port, t = start(R)                                                                  # …which a new page starts from
    try:
        page = call(port, '/')[1].decode('utf-8')
        data = json.loads(re.search(r'const DATA = (\{.*?\});\n', page, re.S).group(1))
        assert data['draft'] == {'state': 'idle'} and data['ocr_text'] == {}
        keep = json.loads(call(port, '/keep', dict(BODY, saved_at=data['saved']['saved_at']))[1])
        assert data['check'] == {k: keep[k] for k in ('problems', 'gaps', 'move_previews')}
        from PIL import Image                                                           # each image's box, set before it arrives
        assert {f'review_pages/page_{n:03d}.png' for n in (1, 2, 3)} <= set(data['img_sizes'])
        for k, wh in data['img_sizes'].items():
            f = os.path.join(str(R), *k.split('/'))
            if os.path.exists(f): assert list(Image.open(f).size) == wh, k
            else: assert k.startswith('review_pages/') and wh[0] > 0 and wh[1] > 0, k   # not rendered yet: the PDF page's size
    finally:
        call(port, '/finish', FINISH); t.join(10)


def test_a_note_holding_markup_never_ends_or_hides_the_pages_script(R):
    """review 16 M2: the page's data is written into its script with <, > and & as \\u escapes, so a saved Session Note
    holding "<!--" and then "<script" (or "</script>") can't make the browser read the rest of the page as script (the page
    would load blank, every time). The note still reaches the page exactly as written."""
    note = 'The <!-- comment and the <script> tag in chapter 3 are code samples; so is </script> & more.'
    core.save(str(R / 'review_decisions.json'), dict(BODY, session_name='<!--<script>', session_notes=note, saved_at='2026-11-11T10:00:00Z'))
    port, t = start(R)
    try:
        page = call(port, '/')[1].decode('utf-8')
    finally:
        call(port, '/finish', FINISH); t.join(10)
    head = page.split('</head>')[0]
    s = head.index('<script>\n') + len('<script>\n'); script = head[s:head.index('</script>', s)]
    assert 'const DATA = {' in script and 'function bootReview() {' in script            # the whole script, ended by its own tag
    assert '<!--' not in script and '<script' not in script and '</script' not in script
    raw = re.search(r'const DATA = (\{.*?\});\n', script, re.S).group(1)
    assert not set('<>&') & set(raw) and '\\u003c!--\\u003cscript\\u003e' in raw                # all three escaped in the data
    data = json.loads(raw)
    assert data['saved']['session_notes'] == note and data['saved']['session_name'] == '<!--<script>'
    assert page.index('<body>') < page.index('<script>bootReview()</script>') < page.index('</body>')


@pytest.mark.parametrize('bad', ['one page', 'the whole PDF'])
def test_a_page_whose_size_cant_be_read_leaves_the_others_their_sizes(R, monkeypatch, bad):
    """review 18 L2 (b19efdf, review 16 L1): image sizes are read page by page. A rendered page image is measured from its
    file, without the PDF; a page not rendered yet from its PDF page's size, each in its own try. One page whose size
    pdfium can't read leaves the others theirs; a PDF that can't be opened leaves the rendered images theirs."""
    import pypdfium2 as pdfium
    from PIL import Image
    real = pdfium.PdfDocument
    class Doc(real):
        def __init__(self, *a, **k):
            if bad == 'the whole PDF': raise pdfium.PdfiumError('cannot open')
            super().__init__(*a, **k)
        def get_page_size(self, i):
            if i == 1: raise pdfium.PdfiumError('cannot read page 2')
            return super().get_page_size(i)
    monkeypatch.setattr(pdfium, 'PdfDocument', Doc)
    pages = R / 'review_pages'; pages.mkdir(exist_ok=True)
    for f in pages.glob('page_*.png'): f.unlink()
    Image.new('RGB', (50, 60), 'white').save(pages / 'page_001.png')                  # page 1 rendered already
    port, t = start(R)
    try:
        page = call(port, '/')[1].decode('utf-8')
    finally:
        call(port, '/finish', FINISH); t.join(10)
    sizes = json.loads(re.search(r'const DATA = (\{.*?\});\n', page, re.S).group(1))['img_sizes']
    assert sizes['review_pages/page_001.png'] == [50, 60]                              # from its file
    assert 'review_pages/page_002.png' not in sizes                                     # its card grows when the image comes
    if bad == 'one page': assert sizes['review_pages/page_003.png'][0] > 0 and sizes['review_pages/page_003.png'][1] > 0
    else: assert 'review_pages/page_003.png' not in sizes
