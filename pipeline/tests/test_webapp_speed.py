"""test_webapp_speed.py: #93 (improve performance: home and batch pages, first-time "Review Again", and PDF pipeline step
timing), Part 1. The jobs check builds the queue once per answer (fix 1); a page reads each names file and each job file
once (fix 2, review 02 L8: the batch PDF's page too); the home page's lighter check (fix 3, with review 02 H1: every
status that can still change); the batch dashboard never opens a PDF for page labels it doesn't use (§2.5). Synthetic
folders only: no book, no model, no running job (the server is started in this process without its dispatcher).

    python -m pytest tests/test_webapp_speed.py -q
"""
import os, sys, json, builtins, threading, contextlib, collections, urllib.parse
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import jobs, runs as RN, home as HM, batches as BT, books as BK, names as NM, server as W  # noqa: E402
from test_webapp import setup, settings, get  # noqa: E402,F401  (fixtures)
from test_webapp_home import pdf_bytes  # noqa: E402

def mk(s, n, kind, run, status, **kw):
    """A job file written by hand (no process: pid and pgid null), its id ordered by n."""
    jid = f'20261110-09{n:04d}-000000-{kind}'
    j = {'id': jid, 'kind': kind, 'run': run, 'dir': None, 'argv': ['true'], 'env': {}, 'env_set': {}, 'counted': True, 'then': None,
         'paid': False, 'status': status, 'created': f'2026-11-10T09:{n // 60 % 60:02d}:{n % 60:02d}', 'started': None, 'ended': None,
         'exit': None, 'pid': None, 'pgid': None, 'log': f'{jid}.log'}
    j.update(kw)
    os.makedirs(jobs.folder(s['jobs']), exist_ok=True)
    jobs.save(s['jobs'], j); open(jobs.log_path(s['jobs'], jid), 'w').close()
    return j

def setj(s, j, **kw):
    j = jobs.load(s['jobs'], j['id']); j.update(kw); jobs.save(s['jobs'], j); return j

@contextlib.contextmanager
def served(s):
    """The app's own HTTP server in this process, without the dispatcher and without recover(): nothing starts."""
    srv = W.make(s, [], 'test')
    threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()
    try: yield srv.server_address[1]
    finally: srv.shutdown(); srv.server_close()

def jget(port, path):
    st, b, _ = get(port, path); assert st == 200, (path, st, b[:300]); return json.loads(b)

# ------------------------------------------------------------------ fix 1: the queue, once per answer
def queue_jobs(s, batch):
    js = [mk(s, 1, 'estimate', 'a/r1', 'done', exit=0),
          mk(s, 2, 'batch', 'batches/b1', 'running') if batch else mk(s, 2, 'spend', 'a/r2', 'running', paid=True),
          mk(s, 3, 'apply', 'a/r2', 'queued'), mk(s, 4, 'batch-estimate', 'batches/b1/x', 'queued'),
          mk(s, 5, 'spend', 'a/r3', 'needs-spend', paid=True), mk(s, 6, 'estimate', 'a/r4', 'interrupted'),
          mk(s, 7, 'spend', 'a/r5', 'superseded', paid=True, note='dismissed'), mk(s, 8, 'spend', 'a/r6', 'failed', exit=1, paid=True),
          mk(s, 9, 'rerun', 'a/r7', 'queued'), mk(s, 10, 'review', 'a/r8', 'running', counted=False, url='http://localhost:8765/')]
    return js

@pytest.mark.parametrize('batch', [True, False])
def test_shared_queue_views_equal_views_made_one_at_a_time(setup, batch):
    s = settings(setup); queue_jobs(s, batch)
    al = jobs.all_jobs(s["jobs"]); ctx = RN.view_context(s)
    for j in al: assert RN.job_view(s, j, ctx=ctx) == RN.job_view(s, j), j['id']
    by = {j['id']: RN.job_view(s, j, ctx=ctx) for j in al}
    q = [j['id'] for j in al if j['status'] == 'queued']
    assert [by[i]['position'] for i in q] == [1, 2, 3]                            # oldest first
    assert all(by[j['id']]['position'] is None for j in al if j['status'] != 'queued')
    w = {by[i]['id'][-8:]: by[i].get('waiting_for') for i in q}
    if batch: assert set(w.values()) == {'the batch "b1"'}                         # a batch runs alone: everything waits for it
    else: assert by[q[0]]['waiting_for'] == 'the run "r2"' and by[q[1]].get('waiting_for') is None and by[q[2]].get('waiting_for') is None

def test_positions_count_queued_jobs_older_than_the_window(setup):
    """Review 02 L4: the queue is built from every job before ?limit= picks the newest: a newer queued job counts an older
    one the answer doesn't show."""
    s = settings(setup)
    q1 = mk(s, 1, 'estimate', 'a/r1', 'queued'); mk(s, 2, 'estimate', 'a/r2', 'done', exit=0); mk(s, 3, 'estimate', 'a/r3', 'done', exit=0)
    q4 = mk(s, 4, 'estimate', 'a/r4', 'queued'); q5 = mk(s, 5, 'estimate', 'a/r5', 'queued')
    with served(s) as port:
        got = jget(port, '/api/jobs?limit=2')
    assert [(v['id'], v['position']) for v in got] == [(q5['id'], 3), (q4['id'], 2)]
    assert jobs.position(s['jobs'], q4['id']) == 2 and jobs.position(s['jobs'], q1['id']) == 1

def test_read_log_takes_the_listed_job(setup):
    s = settings(setup); j = mk(s, 1, 'estimate', 'a/r1', 'running')
    open(jobs.log_path(s['jobs'], j['id']), 'w').write('▶ one\nhalf a li')
    assert jobs.read_log(s['jobs'], j['id']) == jobs.read_log(s['jobs'], j['id'], job=j) == ('▶ one\n', 8)
    assert jobs.read_log(s['jobs'], j['id'], job=dict(j, status='done'))[0] == '▶ one\nhalf a li'   # an ended job: every byte

# ------------------------------------------------------------------ fix 2: each names file and each job file read once
def runs_fixture(setup, s):
    """Two uploaded PDFs (one titled), two single runs, an app batch of two finished PDFs, a saved batch, three jobs (one
    queued), names for one book, one run and one batch, and books-cache.json complete (nothing written while counting)."""
    U = setup / 'uploads'
    (U / 'u1.pdf').write_bytes(pdf_bytes(2, 'Book One Title')); (U / 'u2.pdf').write_bytes(pdf_bytes(3))
    L = BK.listing(s); sha = {b['file']: b['key'] for b in L}
    runs = setup / 'runs'
    for lab, f in (('l1', 'u1.pdf'), ('l2', 'u2.pdf')):
        R = runs / 'bk' / lab; R.mkdir(parents=True)
        (R / 'record.json').write_text(json.dumps({'document': {'file': f, 'sha256': sha[f], 'pages': 2}, 'run': {'started': f'2026-11-0{1 + (lab == "l2")}T10:00:00'}}))
    B = runs / 'batches' / 'b1'
    for n, f in (('x', 'u1.pdf'), ('y', 'u2.pdf')):
        (B / n).mkdir(parents=True)
        (B / n / 'record.json').write_text(json.dumps({'document': {'file': f, 'sha256': sha[f], 'pages': 2, 'output': f'{n}_remediated.pdf'},
                                                      'run': {'started': '2026-11-03T10:00:00'}}))
        (B / n / 'review.html').write_text('<!doctype html><html><head><title>t</title></head><body><a class="skip" href="#main">Skip</a>'
                                           '<header class="top"><h1>t</h1>· 2 pages ·</header><main id="main">m</main></body></html>')
    (runs / 'batches' / 'sv' / 'z' / 'source').mkdir(parents=True); (runs / 'batches' / 'sv' / 'z' / 'source' / 'u2.pdf').write_bytes(pdf_bytes(3))
    A = setup / 'runs' / '.app' / 'batches'; A.mkdir(parents=True, exist_ok=True)
    (A / 'b1.json').write_text(json.dumps({'label': 'b1', 'created': '2026-11-03T09:00:00', 'langs': {},
                                           'books': [{'name': 'x', 'key': sha['u1.pdf'], 'file': 'u1.pdf', 'book': 'x'},
                                                     {'name': 'y', 'key': sha['u2.pdf'], 'file': 'u2.pdf', 'book': 'y'}]}))
    (A / 'sv.json').write_text(json.dumps({'label': 'sv', 'created': '2026-11-04T09:00:00', 'langs': {}, 'saved': True,
                                           'books': [{'name': 'z', 'key': sha['u2.pdf'], 'file': 'u2.pdf', 'book': 'z'}]}))
    NM.set_book_name(s, sha['u1.pdf'], 'A Person\'s Name'); NM.set_run_name(s, 'bk/l1', 'First Run'); NM.set_run_name(s, 'b1', 'Batch One', kind='batches')
    mk(s, 1, 'spend', 'bk/l1', 'done', exit=0, book_sha=sha['u1.pdf'], book_file='u1.pdf')
    mk(s, 2, 'batch-estimate', 'batches/b1/x', 'done', exit=0, book_sha=sha['u1.pdf'], book_file='u1.pdf')
    mk(s, 3, 'estimate', 'bk/l2', 'queued', book_sha=sha['u2.pdf'], book_file='u2.pdf')
    HM.index(s)                                          # the home list's cache, as the app keeps it warm
    return sha

class Opens:
    """Every builtins.open while on, by kind: the three names files, each job file, each job log."""
    def __init__(self, s): self.J = os.path.realpath(jobs.folder(s['jobs'])); self.c = collections.Counter(); self.on = False
    def kind(self, p):
        p = os.path.realpath(str(p)); b = os.path.basename(p)
        if b in ('book-names.json', 'run-names.json', 'books-cache.json'): return b
        if os.path.dirname(p) == self.J: return 'job ' + b
        return None
    @contextlib.contextmanager
    def counting(self, monkeypatch):
        real = builtins.open
        def op(f, *a, **k):
            if self.on and isinstance(f, (str, bytes, os.PathLike)):
                k_ = self.kind(f)
                if k_: self.c[k_] += 1
            return real(f, *a, **k)
        monkeypatch.setattr(builtins, 'open', op)
        try: yield self
        finally: monkeypatch.setattr(builtins, 'open', real)
    def during(self, f):
        self.c.clear(); self.on = True
        try: f()
        finally: self.on = False
        return dict(self.c)

NAMES = ('book-names.json', 'run-names.json', 'books-cache.json')

@pytest.mark.parametrize('path,names', [('/', NAMES), ('/?view=batches', NAMES), ('/batch/b1/', NAMES), ('/api/batch/b1', ('book-names.json', 'books-cache.json')),
                                        ('/api/jobs?limit=200', NAMES), ('/api/jobs?active=1', NAMES), ('/run/batches/b1/x/', NAMES),
                                        ('/api/run/batches/b1/x', ('book-names.json', 'run-names.json')), ('/run/bk/l2/', NAMES), ('/api/run/bk/l2', NAMES)])   # the run page with its panel's first answer, and the panel's own request (#93)
def test_a_page_reads_each_names_file_and_each_job_file_once(setup, monkeypatch, path, names):
    """Review 02 L4, L8: exactly one open of each names file the page needs, and of each job file it reads (two runs, three
    jobs, a queued one, a saved batch; one row would hide per-row reads). The batch PDF's page includes its run header.
    The files each page needs were measured on the code before #93 (each opened 2 to 7 times on this fixture, every job
    file 3 to 7 times)."""
    s = settings(setup); runs_fixture(setup, s)
    op = Opens(s)
    with served(s) as port, op.counting(monkeypatch):
        st = []
        c = op.during(lambda: st.append(get(port, path)[0]))
    assert st == [200], st
    for n in NAMES: assert c.get(n, 0) == (1 if n in names else 0), (n, c)
    jf = {k: v for k, v in c.items() if k.startswith('job ') and k.endswith('.json')}
    assert jf and set(jf.values()) == {1}, jf                                     # each job file once
    assert len(jf) == len(jobs.all_jobs(s['jobs']))

def test_the_side_list_reads_each_names_file_once(setup, monkeypatch):
    s = settings(setup); runs_fixture(setup, s)
    op = Opens(s)
    with op.counting(monkeypatch):
        c = op.during(lambda: BT.with_nav('<!doctype html><html><body><a class="skip" href="#main">Skip</a></body></html>', s, 'b1', 'x'))
    assert all(c.get(n, 0) <= 1 for n in NAMES) and set(v for k, v in c.items() if k.startswith('job ') and k.endswith('.json')) == {1}, c

def test_a_listing_that_writes_a_title_is_seen_by_the_rows_after_it(setup):
    """Review 02 M1: books-cache.json is read once per page, so a Title the listing writes into it in that same request
    (a cache that was lost or reset) reaches the rows drawn after it, as when every row read the file again."""
    s = settings(setup); U = setup / 'uploads'
    (U / 'a0.pdf').write_bytes(pdf_bytes(1)); (U / 'a1.pdf').write_bytes(pdf_bytes(2, 'The Written Title'))
    sha = {b['file']: b['key'] for b in BK.listing(s)}
    os.remove(os.path.join(s['jobs'], 'books-cache.json'))                        # lost: the next listing writes it again
    R = setup / 'runs' / 'bk' / 'l1'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'a1.pdf', 'sha256': sha['a1.pdf']}, 'run': {'started': '2026-11-01T10:00:00'}}))
    h = HM.page(s)                                       # a0 (no Title) makes the snapshot read the cache before a1's Title is written
    assert '<span class="hm-run">l1</span><span class="hm-book">The Written Title</span>' in h, h   # the run's own row (review 04 L-A)
    nm = NM.snapshot(s); assert nm.book_name(sha['a1.pdf'], 'a1.pdf') == 'The Written Title' == NM.book_name(s, sha['a1.pdf'], 'a1.pdf')

def test_a_snapshot_answers_as_the_module_functions(setup):
    s = settings(setup); runs_fixture(setup, s); nm = NM.snapshot(s)
    for sha in [None, 'f' * 64] + [json.load(open(setup / 'runs' / 'bk' / l / 'record.json'))['document']['sha256'] for l in ('l1', 'l2')]:
        for t in (None, 'Some Real Title', ''):
            assert nm.book_name(sha, 'u9.pdf', t) == NM.book_name(s, sha, 'u9.pdf', t)
    for r in ('bk/l1', 'bk/l2', 'batches/b1', 'batches/b1/x', 'batches/sv/z', 'x'):
        assert nm.shown_run(r) == NM.shown_run(s, r) and nm.run_name(r) == NM.run_name(s, r)
    assert nm.batch_name('b1') == NM.batch_name(s, 'b1') == 'Batch One'

def test_snapshots_are_never_kept(setup):
    """A snapshot lives for one request: never stored in the settings or in a module (a rename shows on the next page)."""
    s = settings(setup); runs_fixture(setup, s)
    before = dict(s); HM.page(s); BT.state(s, 'b1'); assert s == before
    NM.set_run_name(s, 'bk/l1', 'Renamed Run')
    assert 'Renamed Run' in HM.page(s)
    assert not any(isinstance(v, NM.Snapshot) for m in (NM, HM, BT, RN, BK, W) for v in vars(m).values())

def test_a_batch_request_asks_tesseract_for_its_languages_at_most_once(setup, monkeypatch):
    """Review 04 M-A: a batch of estimated, not-started books (each unfinished and idle) asked `tesseract --list-langs`
    twice per book on every page and poll; now once per request when a book asks its language, and not at all when none
    does."""
    from webapp import checks
    s = settings(setup)
    def book(label, n, cjk=False):
        R = setup / 'runs' / 'batches' / label / n; (R / '_intake').mkdir(parents=True)
        ij = {'status': 'stopped', 'flags': [{'what': 'OCR language needed', 'pages': [2]}], 'plan': {'ocr_pages': [2]}} if cjk else {'status': 'done'}
        (R / '_intake' / 'intake.json').write_text(json.dumps(dict(ij, original={'file': f'{n}.pdf', 'sha256': n[0] * 64})))
        (R / 'run.json').write_text(json.dumps({'estimate': {'worst_case_total_usd': 0.5}, 'started': '2026-11-05T10:00:00'}))
    for n in ('a', 'b', 'c'): book('est', n); book('est2', n)
    book('est', 'd', cjk=True)                                        # one book asks its language (intake's CJK stop)
    asked = []; real = checks._run
    monkeypatch.setattr(checks, '_run', lambda argv, *a, **k: (asked.append(argv), real(argv, *a, **k))[1] if argv[0] == 'tesseract' else real(argv, *a, **k))
    with served(s) as port:
        for path in ('/batch/est/', '/api/batch/est', '/run/batches/est/a/'):
            asked.clear(); assert get(port, path)[0] == 200
            assert len(asked) == 1, (path, len(asked))                # was 2 per book: 8
        for path in ('/batch/est2/', '/api/batch/est2'):
            asked.clear(); assert get(port, path)[0] == 200
            assert asked == [], path                                  # no book asks a language: never asked
    st = BT.state(s, 'est')
    assert [b['language'] is not None for b in st['books']] == [False, False, False, True]

# ------------------------------------------------------------------ fix 3: the home page's lighter check (H1)
CAN_CHANGE = ('queued', 'running', 'needs-spend', 'interrupted')

class Page:
    """home.js poll() in Python: today's (?limit=200) or the lighter check (?active=1&seen=<ids last seen in a status that
    can still change>), with the same seen map and the same announcement rule."""
    def __init__(self, port, light): self.port, self.light, self.seen, self.primed = port, light, {}, False
    def poll(self):
        if self.light: path = '/api/jobs?active=1&seen=' + ','.join(i for i, k in self.seen.items() if k in CAN_CHANGE)
        else: path = '/api/jobs?limit=200'
        js = jget(self.port, path); said = []
        for j in js:
            k, was = j['status'], self.seen.get(j['id']); self.seen[j['id']] = k
            if self.primed and was and was != k and k not in ('queued', 'running'): said.append((j['id'], k))
        self.primed = True
        return said, [j['id'] for j in js if j['status'] in ('queued', 'running')]

def test_the_lighter_check_announces_what_todays_check_announces(setup):
    """Review 02 H1: queued→done, running→failed, needs-spend→superseded (Dismiss), interrupted→done, interrupted→running→done,
    and a needs-spend job that appears after the first check: each is announced exactly as the full list announces it,
    and "Runs in Progress" lists the same jobs in the same order."""
    s = settings(setup)
    old = mk(s, 1, 'spend', 'a/r0', 'done', exit=0, paid=True)
    A = mk(s, 2, 'estimate', 'a/r1', 'queued'); B = mk(s, 3, 'spend', 'a/r2', 'running', paid=True)
    C = mk(s, 4, 'spend', 'a/r3', 'needs-spend', paid=True); D = mk(s, 5, 'apply', 'a/r4', 'interrupted', ended='2026-11-10T09:00:00', pgid=4242)
    E = mk(s, 6, 'apply', 'a/r5', 'interrupted', ended='2026-11-10T09:00:00', pgid=4243)   # may be alive after all: no exit, a group
    mk(s, 8, 'estimate', 'a/r8', 'interrupted', ended='2026-11-10T09:00:00')                 # interrupted for good (no process group)
    mk(s, 9, 'apply', 'a/r9', 'interrupted', ended='2026-11-10T09:00:00', exit=1, pgid=4244)   # and with an exit recorded
    with served(s) as port:
        full, light = Page(port, False), Page(port, True)
        steps = [lambda: None,
                 lambda: (setj(s, A, status='done', exit=0, ended='2026-11-10T10:00:00'), setj(s, B, status='failed', exit=1, ended='2026-11-10T10:00:00')),
                 lambda: (setj(s, C, status='superseded', note='dismissed', superseded_by='dismissed', ended='2026-11-10T10:01:00'),
                          setj(s, D, status='done', exit=0, ended='2026-11-10T10:01:00'), setj(s, E, status='running', ended=None)),
                 lambda: (setj(s, E, status='done', exit=0, ended='2026-11-10T10:02:00'), mk(s, 10, 'spend', 'a/r6', 'needs-spend', paid=True)),
                 lambda: setj(s, jobs.all_jobs(s['jobs'])[-1], status='superseded', note='dismissed', ended='2026-11-10T10:03:00')]
        got = []
        for f in steps:
            f(); a, b = full.poll(), light.poll()
            assert a == b, (a, b)
            got.append(a[0])
    G = jobs.all_jobs(s['jobs'])[-1]['id']
    assert got == [[], [(B['id'], 'failed'), (A['id'], 'done')], [(D['id'], 'done'), (C['id'], 'superseded')],
                   [(E['id'], 'done')], [(G, 'superseded')]]                       # newest first, as the answer lists them
    assert old['id'] not in [x for st in got for x, _ in st]

def test_the_lighter_answer(setup):
    """Its views equal the full list's, newest first; a done job not in seen is left out, and so is an interrupted job that
    can't change any more (an exit recorded, or no process group: review 04 L-B) unless seen names it; seen is checked (job-id
    characters, duplicates once, unknown ids ignored, at most 500 ids, the parameter cut at 500 × 40 characters before it
    is split); ?active=1 wins over ?limit=."""
    s = settings(setup)
    d1 = mk(s, 1, 'estimate', 'a/r1', 'done', exit=0); d2 = mk(s, 2, 'estimate', 'a/r2', 'failed', exit=1)
    q = mk(s, 3, 'estimate', 'a/r3', 'queued'); r = mk(s, 4, 'spend', 'a/r4', 'running', paid=True)
    n = mk(s, 5, 'spend', 'a/r5', 'needs-spend', paid=True); i = mk(s, 6, 'estimate', 'a/r6', 'interrupted', pgid=4242)
    gone = mk(s, 7, 'estimate', 'a/r7', 'interrupted'); ended = mk(s, 8, 'estimate', 'a/r8', 'interrupted', exit=1, pgid=4243)   # can't change (L-B)
    ids = lambda js: [j['id'] for j in js]
    with served(s) as port:
        full = {v['id']: v for v in jget(port, '/api/jobs?limit=200')}
        assert jget(port, '/api/jobs?active=1') == [full[x] for x in (i['id'], n['id'], r['id'], q['id'])]          # newest first
        assert ids(jget(port, f'/api/jobs?active=1&seen={gone["id"]},{ended["id"]}')) == [ended['id'], gone['id'], i['id'], n['id'], r['id'], q['id']]
        assert ids(jget(port, '/api/jobs?active=1&seen=' + d1['id'])) == [i['id'], n['id'], r['id'], q['id'], d1['id']]
        assert ids(jget(port, '/api/jobs?active=1&limit=1')) == [i['id'], n['id'], r['id'], q['id']]                # active wins
        bad = ','.join(['../x', '<b>', 'a b', 'x' * 65, '20991231-000000-000000-nope', d2['id'], d2['id']])
        assert ids(jget(port, '/api/jobs?active=1&seen=' + urllib.parse.quote(bad, safe=','))) == [i['id'], n['id'], r['id'], q['id'], d2['id']]
        many = ['20261110-000000-%06d-x' % k for k in range(600)]
        assert d1['id'] not in ids(jget(port, '/api/jobs?active=1&seen=' + ','.join(many[:500] + [d1['id']])))      # the first 500 ids
        assert d1['id'] in ids(jget(port, '/api/jobs?active=1&seen=' + ','.join(many[:10] + [d1['id']])))
        long_ = 'y' * (500 * 40) + ',' + d1['id']
        assert d1['id'] not in ids(jget(port, '/api/jobs?active=1&seen=' + long_))                                 # cut before the split
        assert jget(port, '/api/jobs?limit=200') == list(full.values())                                             # ?limit= as it was

def test_home_js_sends_the_ids_it_last_saw_in_a_status_that_can_change():
    t = open(os.path.join(HERE, 'webapp', 'home.js'), encoding='utf-8').read()
    assert "fetch('/api/jobs?active=1&seen=' + " in t and "'/api/jobs?limit=200'" not in t
    assert "const CAN_CHANGE = ['queued', 'running', 'needs-spend', 'interrupted'];" in t

# ------------------------------------------------------------------ §2.5: the dashboard reads no page labels
def test_glance_without_labels_equals_glance_with_them(tmp_path, monkeypatch):
    import report_html as H
    from test_evaluation import make_run
    from review import manual as M
    for i, sec in enumerate((True, False, None)):
        R = make_run(tmp_path / str(i), bool(sec))
        if sec is None: M.refresh(R, say=lambda *a: None)                         # the current glance schema
        rec = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
        assert H.glance_of(R, rec, H.labels_of(R, rec)) == H.glance_of(R, rec), i

def test_the_batch_dashboard_never_opens_a_pdf_for_labels(setup, monkeypatch):
    import report_html as H
    s = settings(setup); runs_fixture(setup, s)
    monkeypatch.setattr(H, 'labels_of', lambda *a: (_ for _ in ()).throw(AssertionError('labels_of called')))
    seen = []
    monkeypatch.setattr(H, 'glance_of', lambda R, rec=None, labels=None: seen.append(labels) or (_ for _ in ()).throw(KeyError('x')))
    BT._DASH.clear(); BT.state(s, 'b1')
    assert seen == [None, None]

# ------------------------------------------------------------------ review 09, 12a: a book's page skips the dashboard
def test_a_book_page_in_a_batch_and_its_poll_never_build_the_dashboard(setup, monkeypatch):
    """The side list shows only the books' statuses: a book's page in a batch, and batch.js's poll on it (?nav=1), never
    build the batch dashboard (for an older batch, a pikepdf open of every finished PDF on the first open after a start).
    The batch page and its own poll still do, and the side list is the same either way."""
    s = settings(setup); runs_fixture(setup, s)
    calls = []; real = BT.dashboard
    monkeypatch.setattr(BT, 'dashboard', lambda *a, **k: (calls.append(a[1]), real(*a, **k))[1])
    BT._DASH.clear()
    with served(s) as port:
        for path in ('/run/batches/b1/x/', '/api/batch/b1?nav=1'):
            calls.clear(); assert get(port, path)[0] == 200, path
            assert calls == [], path
        light, full = jget(port, '/api/batch/b1?nav=1'), jget(port, '/api/batch/b1')
        page = get(port, '/run/batches/b1/x/')[1].decode('utf-8')
        for path in ('/batch/b1/', '/api/batch/b1'):
            calls.clear(); assert get(port, path)[0] == 200, path
            assert calls == ['b1'], path
    assert light['dashboard'] is None and full['dashboard'] and {k: v for k, v in full.items() if k != 'dashboard'} == {k: v for k, v in light.items() if k != 'dashboard'}
    assert BT.nav(s, 'b1', 'x', st=BT.state(s, 'b1', with_dashboard=False)) == BT.nav(s, 'b1', 'x', st=BT.state(s, 'b1'))
    assert 'aria-label="PDFs in This Batch"' in page and 'aria-current="page"' in page

def test_batch_js_asks_the_light_answer_on_a_book_page_only():
    t = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "API = '/api/batch/' + encodeURIComponent(LABEL)" in t and "POLL = API + ($('bt-panel') ? '' : '?nav=1')" in t
    assert 'await api(POLL)' in t and 'await api(API)' not in t
