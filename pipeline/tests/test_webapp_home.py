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
    s = S(setup); sm = setup / 'samples'
    (sm / 'g').mkdir(); (sm / 'g' / 'a.pdf').write_bytes(pdf_bytes(2, 'Book A'))
    (sm / '.hidden').mkdir(); (sm / '.hidden' / 'h.pdf').write_bytes(pdf_bytes(1, 'Hidden'))
    U = setup / 'uploads'; (U / '.incoming').mkdir(parents=True); (U / '.incoming' / 'x.part').write_bytes(pdf_bytes())
    (U / 'copy.pdf').write_bytes((sm / 'g' / 'a.pdf').read_bytes())
    L = BK.listing(s)
    assert [(b['name'], b['group'], b['pages']) for b in L] == [('Book A', 'sample', 2)]
    assert json.load(open(os.path.join(s['jobs'], 'sha256-cache.json')))[str(sm / 'g' / 'a.pdf')][2] == L[0]['key']
    assert BK.by_key(s, L[0]['key'])['path'] == str(sm / 'g' / 'a.pdf') and BK.by_key(s, '../x') is None
    assert RN.find_original(s, L[0]['key']) == str(sm / 'g' / 'a.pdf')          # find_original shares the cache

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
    t = app['t']; (t / 'samples' / 's.pdf').write_bytes(pdf_bytes(4, 'Sample Title'))
    st, b, h = get(app['port'], '/')
    page = b.decode()
    assert st == 200 and 'Sample Title' in page and 'Source PDF Filename: s.pdf' in page and 'href="/new?book=' in page
    assert page.count('aria-label="App"') == 1 and 'aria-current="page"' in page
    assert '<script src="/app/home.js" defer></script>' in page and "script-src 'self'" in h['Content-Security-Policy']
    assert 'Earlier Runs' in page and '/run/book/r1/' in page and 'None' not in page.replace('None yet', '')
    assert get(app['port'], '/app/home.js')[0] == 200
    st, b, _ = get(app['port'], '/?q=nothing-matches-this')
    assert st == 200 and '0 runs matching' in b.decode()

@pytest.mark.parametrize('path', ['/run/book/r1/', '/run/book/r1/review.md', '/run/old/r0/', '/run/book/r1/download?what=nope'])
def test_every_app_page_has_the_way_home(app, path):
    st, b, _ = get(app['port'], path)
    page = b.decode()
    assert page.count('<nav class="pp-appbar" aria-label="App"><a href="/">Home</a></nav>') == 1, path

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
