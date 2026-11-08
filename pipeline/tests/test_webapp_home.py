"""test_webapp_home.py: the home page (#45, home interface): the book list, display names, "Add a Book" (uploads), the
earlier-runs index and the app bar on every page. No book, no model: synthetic PDFs only.

    python -m pytest tests/test_webapp_home.py -q
"""
import os, io, sys, json, shutil, threading, http.client, hashlib
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import books as BK, home as HM, runs as RN, server as W  # noqa: E402
from test_webapp import setup, settings, get, app, wait, free_port  # noqa: E402,F401  (fixtures)

def pdf_bytes(pages=1, title=None, password=None):
    import pikepdf
    p = pikepdf.new()
    for _ in range(pages): p.add_blank_page()
    if title: p.docinfo['/Title'] = title
    b = io.BytesIO()
    p.save(b, encryption=pikepdf.Encryption(owner='o', user=password) if password else None)
    return b.getvalue()

def S(t, **over): return settings(t, **over)

# ------------------------------------------------------------------ names
@pytest.mark.parametrize('title,file,want', [
    ('Ilokano Reference Grammar', 'ilokano.pdf', 'Ilokano Reference Grammar'),
    ('', 'colonial-legacies.pdf', 'colonial legacies'), ('untitled', 'a_b.pdf', 'a b'),
    ('Microsoft Word - draft3.doc', 'book.pdf', 'book'), ('chapter1.indd', 'book_one.pdf', 'book one'), ('x', 'zz.pdf', 'zz'),
    ('book.pdf', 'real-name.PDF', 'real name')])
def test_display_name(title, file, want):
    assert BK.display_name(title, file) == want

@pytest.mark.parametrize('raw,want', [('a b.pdf', 'a b.pdf'), ('../../etc/passwd.pdf', 'passwd.pdf'), ('.hidden.pdf', 'hidden.pdf'),
    ('x#y|z.pdf', 'x_y_z.pdf'), ('noext', 'noext.pdf'), ('a\u202eb.pdf', 'ab.pdf'), ('c:\\dir\\f.pdf', 'f.pdf'), ('...', None), ('', None),
    ('e\u0301.pdf', '\u00e9.pdf')])
def test_upload_names_are_cleaned(raw, want):
    assert BK.clean_upload_name(raw) == want

def test_long_names_are_cut_to_200_bytes():
    n = BK.clean_upload_name('é' * 300 + '.pdf')
    assert n.endswith('.pdf') and len(n.encode()) <= 200

def test_reading_an_untrusted_pdf_never_raises(tmp_path):
    (tmp_path / 'bad.pdf').write_bytes(b'%PDF-1.4 garbage')
    assert BK.read_meta(str(tmp_path / 'bad.pdf'))['unreadable'] is True
    (tmp_path / 'locked.pdf').write_bytes(pdf_bytes(password='u'))
    m = BK.read_meta(str(tmp_path / 'locked.pdf'))
    assert m['locked'] is True and m['pages'] is None
    (tmp_path / 'ok.pdf').write_bytes(pdf_bytes(3, 'A Title Here'))
    assert BK.read_meta(str(tmp_path / 'ok.pdf')) == {'pages': 3, 'title': 'A Title Here', 'locked': False, 'unreadable': False, 'tagged': False}

# ------------------------------------------------------------------ the list
def test_listing_skips_dot_folders_and_lists_a_content_once(setup):
    """Only "Add a PDF"'s folder is listed (P3, Patrick 2026-11-06); samples/ is still searched for originals by sha256."""
    s = S(setup); sm = setup / 'samples'
    (sm / 'g').mkdir(); (sm / 'g' / 'a.pdf').write_bytes(pdf_bytes(2, 'Book A')); (sm / 'only.pdf').write_bytes(pdf_bytes(1, 'Sample Only'))
    U = setup / 'uploads'; (U / '.incoming').mkdir(parents=True); (U / '.incoming' / 'x.part').write_bytes(pdf_bytes())
    (U / '.hidden').mkdir(); (U / '.hidden' / 'h.pdf').write_bytes(pdf_bytes(1, 'Hidden'))
    (U / 'g').mkdir(); (U / 'g' / 'a.pdf').write_bytes((sm / 'g' / 'a.pdf').read_bytes()); (U / 'copy.pdf').write_bytes((sm / 'g' / 'a.pdf').read_bytes())
    L = BK.listing(s)
    assert [(b['name'], b['group'], b['pages'], b['file']) for b in L] == [('Book A', 'added', 2, 'copy.pdf')]
    assert json.load(open(os.path.join(s['jobs'], 'sha256-cache.json')))[str(U / 'copy.pdf')][2] == L[0]['key']
    assert BK.by_key(s, L[0]['key'])['path'] == str(U / 'copy.pdf') and BK.by_key(s, '../x') is None
    only = BK.hashes(s, [str(sm / 'only.pdf')])[str(sm / 'only.pdf')]
    assert BK.by_key(s, only) is None and RN.find_original(s, only) == str(sm / 'only.pdf')   # never listed, still found

# ------------------------------------------------------------------ Add a Book (receive)
def test_receive_names_never_overwrite_and_same_content_is_refused(setup):
    s = S(setup); a, b = pdf_bytes(1, 'One Book'), pdf_bytes(2, 'Two Book')
    x = BK.receive(s, io.BytesIO(a), len(a), 'my book.pdf')
    assert x['file'] == 'my book.pdf' and x['key'] == hashlib.sha256(a).hexdigest()
    side = json.load(open(setup / 'uploads' / 'my book.json'))
    assert side['sha256'] == x['key'] and side['bytes'] == len(a) and side['original_name'] == 'my book.pdf'
    y = BK.receive(s, io.BytesIO(b), len(b), 'my book.pdf')
    assert y['file'] == 'my book-2.pdf' and (setup / 'uploads' / 'my book.pdf').read_bytes() == a
    with pytest.raises(BK.Refused) as e: BK.receive(s, io.BytesIO(a), len(a), 'other.pdf')
    assert e.value.status == 409 and 'already in the list as "One Book"' in e.value.words
    assert not [n for n in os.listdir(setup / 'uploads' / '.incoming')]          # no .part left behind

def test_two_uploads_of_one_content_at_once_land_once(setup):
    s = S(setup); a = pdf_bytes(1, 'Raced'); out = []
    def go(i):
        try: out.append(BK.receive(s, io.BytesIO(a), len(a), f'r{i}.pdf')['file'])
        except BK.Refused as e: out.append(e.status)
    ts = [threading.Thread(target=go, args=(i,)) for i in range(4)]; [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(map(str, out)).count('409') == 3 and len([n for n in os.listdir(setup / 'uploads') if n.endswith('.pdf')]) == 1

def test_receive_refuses_a_non_pdf_a_short_body_a_big_file_and_no_space(setup, monkeypatch):
    s = S(setup, upload_max_mb=1)
    with pytest.raises(BK.Refused) as e: BK.receive(s, io.BytesIO(b'hello there'), 11, 'x.pdf')
    assert e.value.status == 415
    with pytest.raises(BK.Refused) as e: BK.receive(s, io.BytesIO(b'%PDF-1.4'), 100, 'x.pdf')
    assert e.value.status == 400
    with pytest.raises(BK.Refused) as e: BK.receive(s, io.BytesIO(b''), 2 * 1024 * 1024, 'x.pdf')
    assert e.value.status == 413
    monkeypatch.setattr(BK.shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(10, 10, 5))
    with pytest.raises(BK.Refused) as e: BK.receive(s, io.BytesIO(b'%PDF-1.4'), 8, 'x.pdf')
    assert e.value.status == 507 and 'enough space' in e.value.words
    assert not [n for n in os.listdir(setup / 'uploads') if n.endswith('.pdf')]

def test_temporary_names_never_end_in_pdf():
    src = open(os.path.join(HERE, 'webapp', 'books.py'), encoding='utf-8').read()
    assert "secrets.token_hex(8) + '.part'" in src

# ------------------------------------------------------------------ the upload route: four checks, each required
def raw(port, headers, body=b'', send_len=True):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        c.putrequest('POST', '/api/upload', skip_host=True, skip_accept_encoding=True)
        c.putheader('Host', f'127.0.0.1:{port}')
        for k, v in headers.items(): c.putheader(k, v)
        if send_len and 'Content-Length' not in headers: c.putheader('Content-Length', str(len(body)))
        c.endheaders(body)
        r = c.getresponse(); return r.status, json.loads(r.read() or b'{}')
    finally: c.close()

def test_upload_route_checks(app):
    port = app['port']; good = {'Content-Type': 'application/pdf', 'X-Pdfrem-Upload': '1', 'X-Pdfrem-Filename': 'up%20one.pdf'}
    body = pdf_bytes(1, 'Uploaded Book')
    assert raw(port, {**good, 'Content-Type': 'text/plain'}, b'%PDF-1.4 a form post')[0] == 415      # a cross-site form's type
    assert raw(port, {k: v for k, v in good.items() if k != 'X-Pdfrem-Upload'}, body)[0] == 403        # no custom header
    assert raw(port, {**good, 'Origin': 'http://evil.example'}, body)[0] == 403                          # local_request
    assert raw(port, {**good, 'Content-Length': '1e9'}, body, send_len=False)[0] == 411
    assert raw(port, {**good, 'Content-Length': str(2 * 1024 ** 4)}, b'', send_len=False)[0] == 413
    assert raw(port, {**good, 'Transfer-Encoding': 'chunked'}, b'0\r\n\r\n', send_len=False)[0] == 411
    st, d = raw(port, good, body)
    assert st == 201 and d['book']['name'] == 'Uploaded Book' and d['book']['file'] == 'up one.pdf'
    assert (app['t'] / 'uploads' / 'up one.pdf').read_bytes() == body
    st, d = raw(port, good, body)
    assert st == 409 and 'already in the list' in d['error']

# ------------------------------------------------------------------ the home page and the app bar
def test_home_page_lists_books_and_runs(app):
    t = app['t']; (t / 'uploads').mkdir(exist_ok=True); (t / 'uploads' / 's.pdf').write_bytes(pdf_bytes(4, 'Sample Title'))
    st, b, h = get(app['port'], '/')
    page = b.decode()
    assert st == 200 and 'Sample Title' in page and 'Source PDF: s.pdf' in page and 'href="/new?book=' in page
    assert 'aria-label="App"' not in page and '>Home Page<' not in page                # P1: no way home on the home page itself
    assert '<script src="/app/home.js" defer></script>' in page and "script-src 'self'" in h['Content-Security-Policy']
    assert 'My Workspace' in page and '/run/book/r1/' in page and 'None' not in page.replace('None yet', '')
    assert get(app['port'], '/app/home.js')[0] == 200
    st, b, _ = get(app['port'], '/?q=nothing-matches-this')
    assert st == 200 and '0 runs matching' in b.decode()

@pytest.mark.parametrize('path', ['/run/book/r1/', '/run/book/r1/review.md', '/run/old/r0/', '/run/book/r1/download?what=nope'])
def test_every_app_page_has_the_way_home(app, path):
    st, b, _ = get(app['port'], path)
    page = b.decode()
    assert page.count('<nav class="pp-appbar" aria-label="App"><a class="pp-btn" href="/">Home Page</a>') == 1, path

def test_appbar_follows_the_skip_link():
    p = W.with_appbar('<body>' + W.SKIP + '<main>x</main></body>')
    assert p.index(W.SKIP) < p.index('aria-label="App"') < p.index('<main>')
    assert W.with_appbar(p) == p

def test_index_rows_and_cache(setup):
    s = S(setup); R = setup / 'runs' / 'bk' / 'l1'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'bk.pdf', 'sha256': 'a' * 64}, 'run': {'started': '2026-11-01T10:00:00',
                                              'usage': {'cost_usd': 0.25}}, 'cost_total_usd': 0.25}))
    W2 = setup / 'runs' / 'bk' / 'l2'; W2.mkdir(); (W2 / 'workorder.ai.json').write_text('{}')
    E = setup / 'runs' / 'bk' / 'l3'; E.mkdir(); (E / 'run.json').write_text(json.dumps({'started': '2026-11-02T10:00:00', 'estimate': {'worst_case_total_usd': 0.5}}))
    I = setup / 'runs' / 'bk' / 'l4'; (I / '_intake').mkdir(parents=True); (I / '_intake' / 'intake.json').write_text(json.dumps({'status': 'stopped', 'original': {'file': 'bk.pdf'}}))
    (setup / 'runs' / 'deep' / 'x' / 'y').mkdir(parents=True); (setup / 'runs' / 'deep' / 'x' / 'y' / 'record.json').write_text('{}')
    rows = {r['run']: r for r in HM.index(s)['runs']}
    assert set(rows) == {'bk/l1', 'bk/l2', 'bk/l3', 'bk/l4'}
    assert rows['bk/l1']['words'] == 'Not Ready' and rows['bk/l1']['cost'] == 0.25 and rows['bk/l2']['words'] == 'Waiting for Review'
    assert rows['bk/l3']['words'] == 'Estimate Ready' and rows['bk/l4']['words'] == 'Stopped: Needs a Person'
    assert os.path.isfile(os.path.join(s['jobs'], 'home-index.json'))
    (W2 / 'review.json').write_text('{}'); (W2 / 'record.json').write_text(json.dumps({'document': {'file': 'bk.pdf'}}))
    assert {r['run']: r for r in HM.index(s)['runs']}['bk/l2']['words'] == 'Not Ready'      # the cache follows the records

def test_a_batch_whose_books_all_stopped_is_stopped(setup):
    """A batch is "Estimate Ready" only when a book has an estimate; every book stopped at intake: "Stopped"."""
    s = S(setup)
    for n in ('a', 'b'):
        I = setup / 'runs' / 'batches' / 'bx' / n / '_intake'; I.mkdir(parents=True)
        (I / 'intake.json').write_text(json.dumps({'status': 'stopped', 'original': {'file': f'{n}.pdf'}}))
    assert {b['label']: b for b in HM.index(s)['batches']}['bx']['state'] == 'Stopped'

def test_a_run_waiting_for_a_new_estimate_says_so_on_home(setup):
    """07 L3 (05 M2): a needs-spend run's home row tells the person what to do."""
    from webapp import jobs
    s = settings(setup)
    j = jobs.create(s['jobs'], 'estimate', 'bk/r1', ['true'], {}, R=str(setup / 'runs' / 'bk' / 'r1'))
    jobs.update(s['jobs'], j['id'], status='needs-spend')
    rows = [{'run': 'bk/r1', 'finished': False, 'status': 'Estimate Ready', 'words': 'Estimate Ready'}]
    HM.over(s, rows)
    assert rows[0]['words'] == 'Waiting: open it and select "Get a New Estimate"'

@pytest.mark.parametrize('row,g', [({'status': 'Estimate Ready'}, 'not-started'), ({'status': 'Running', 'active': True}, 'processing'),
                                   ({'status': 'Waiting to Start', 'active': True}, 'processing'), ({'status': 'Waiting for Review'}, 'in-progress'),
                                   ({'status': 'Stopped'}, 'in-progress'), ({'status': 'Stopped before it finished'}, 'in-progress'),
                                   ({'status': 'Not Ready'}, 'in-progress'), ({'status': 'Pending Evaluation'}, 'in-progress'),
                                   ({'status': 'Ready'}, 'done'), ({'status': 'Shipped'}, 'done'), ({'status': 'Failed'}, 'failed')])
def test_status_groups(row, g):
    """D6 (Patrick, 2026-11-06): Done is Ready or Shipped only; an interrupted run is In Progress, not Failed."""
    assert HM.group_of(row) == g

def test_workspace_switch_filter_and_pills(app):
    t = app['t']; s = S(t)
    page = get(app['port'], '/')[1].decode()
    assert 'My Workspace' in page and 'aria-pressed="true">Single Runs' in page and 'Date Created' in page
    assert 'class="hm-pill hm-g-' in page and 'Source PDF Filename' not in page
    assert 'Sample Books' not in page and 'Earlier Runs' not in page
    page = get(app['port'], '/?view=batches')[1].decode()
    assert 'aria-pressed="true">Batches' in page and 'Batch Name' in page
    page = get(app['port'], '/?group=done')[1].decode()
    assert '0 runs, Done.' in page

def test_run_page_header_is_the_apps(app):
    """P7: review.html's own header (a file name, the prompt, the model, the run label) is replaced as served; the file
    on disk is unchanged."""
    t = app['t']; R = t / 'runs' / 'book' / 'r1'
    (R / 'review.html').write_text('<!doctype html><title>Review: book.pdf</title><body><header class="top"><h1>Review: book.pdf</h1>'
                                   '<div class="meta">run book/r1 · 12 pages · model anthropic/x · prompt workorder_v10.md</div></header><main>m</main></body>')
    before = (R / 'review.html').read_bytes()
    page = get(app['port'], '/run/book/r1/')[1].decode()
    assert 'Review: book.pdf' not in page and 'workorder_v10' not in page and 'anthropic/x' not in page
    assert 'class="top pp-head"' in page and '12 pages' in page and 'Run Name: r1' in page
    assert (R / 'review.html').read_bytes() == before

# ------------------------------------------------------------------ Patrick's test, 2026-11-07: Q1, Q3, Q4
def jpost(port, path, body):
    st, b, _ = get(port, path, method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps(body))
    return st, json.loads(b or b'{}')

def test_the_pdf_section_and_its_menus(app):
    """Q1, Q3, Q4: the drop zone (several PDFs, "Choose PDFs" the keyboard path), "Upload a PDF", the narrow Select column,
    "Create a New Batch", and a "⋯" menu button per row (Edit Name, Move to Trash) in place of the row's own buttons."""
    t = app['t']; (t / 'uploads').mkdir(exist_ok=True)
    for n in ('a', 'b'): (t / 'uploads' / f'{n}.pdf').write_bytes(pdf_bytes(1, f'Book {n.upper()}'))
    page = get(app['port'], '/')[1].decode()
    assert '<h2 id="hm-books-h">Upload a PDF</h2>' in page and 'id="hm-drop"' in page and '>Choose PDFs</button> <span>or drop PDFs here</span>' in page
    assert 'A copy goes into the app\'s folder; the file you choose is not changed.' in page and 'accept="application/pdf,.pdf" multiple hidden' in page
    assert 'Create a New Batch</button>' in page and 'Select two or more PDFs first.' in page and '<th scope="col" class="hm-sel">Select</th>' in page
    assert 'Edit the Name' not in page and 'New Batch with' not in page and '>Move to Trash</button></td>' not in page
    assert page.count('aria-haspopup="menu" aria-expanded="false"') >= 3 and 'aria-label="More Actions for Book A"' in page
    assert 'role="menuitem" tabindex="-1" data-edit="pdf"' in page and 'class="hm-danger" data-trash="pdf"' in page
    assert 'data-edit="run" data-run="book/r1"' in page and 'class="hm-danger" data-trash="run" data-run="book/r1"' in page
    bp = get(app['port'], '/?view=batches')[1].decode()
    assert 'data-edit="batch" data-label="b1"' in bp and 'class="hm-danger" data-trash="batch" data-label="b1"' in bp
    keys = {b['name']: b['key'] for b in BK.listing(S(t))}
    page = get(app['port'], '/?added=' + keys['Book B'])[1].decode()                 # just added: first, highlighted, its name box opens
    assert page.index('Book B') < page.index('Book A') and page.count('data-new="1"') == 1 and 'Added "Book B".' in page
    assert get(app['port'], '/book?key=' + keys['Book A'])[2].get('Location') == '/'   # the name page went away

def test_edit_name_for_runs_and_batches_changes_only_the_shown_name(app):
    """Q4: My Workspace's Edit Name sets the plain name, never the folder; a batch's PDF is named by its batch."""
    from webapp import names as NM
    t = app['t']; s = S(t)
    assert jpost(app['port'], '/api/rename/run', {'run': 'book/r1', 'name': '  Spring  check '}) == (200, {'name': 'Spring check'})
    assert NM.run_name(s, 'book/r1') == 'Spring check' and (t / 'runs' / 'book' / 'r1').is_dir()
    assert 'Spring check' in get(app['port'], '/')[1].decode()
    assert jpost(app['port'], '/api/rename/batch', {'label': 'b1', 'name': 'First batch'}) == (200, {'name': 'First batch'})
    assert NM.batch_name(s, 'b1') == 'First batch' and (t / 'runs' / 'batches' / 'b1').is_dir()
    assert jpost(app['port'], '/api/rename/run', {'run': 'batches/b1/x', 'name': 'x'})[0] == 409    # named by its batch
    assert jpost(app['port'], '/api/rename/run', {'run': '../etc', 'name': 'x'})[0] == 409
    assert jpost(app['port'], '/api/rename/batch', {'label': 'nope', 'name': 'x'})[0] == 409
    assert jpost(app['port'], '/api/rename/run', {'run': 'book/r1', 'name': '   '}) == (409, {'error': 'Type a name first.'})

def test_an_upload_says_when_the_pdf_is_locked(app):
    good = {'Content-Type': 'application/pdf', 'X-Pdfrem-Upload': '1', 'X-Pdfrem-Filename': 'locked.pdf'}
    st, d = raw(app['port'], good, pdf_bytes(1, 'Locked', password='pw'))
    assert st == 201 and d['book']['locked'] is True and d['book']['unreadable'] is False

def test_home_js_menu_and_drop_zone():
    js = open(os.path.join(HERE, 'webapp', 'home.js'), encoding='utf-8').read()
    for x in ("e.key === 'Escape') { e.preventDefault(); closeMenu(true); }", "else if (e.key === 'Tab') closeMenu(false);",
              "['dragover', 'drop'].forEach(k => addEventListener(k,", "if (e.key === 'Enter' && e.target === input) { e.preventDefault(); save(); }",
              "fresh.forEach((tr, i) => edit(tr.querySelector('[data-edit]'), !notes.length && i === 0));"):
        assert x in js, x
    tj = open(os.path.join(HERE, 'webapp', 'trash.js'), encoding='utf-8').read()
    assert "if (m) b = m.querySelector('.hm-more');" in tj                          # the dialog gives focus back to "⋯"
