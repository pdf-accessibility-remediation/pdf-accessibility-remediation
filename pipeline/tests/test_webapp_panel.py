"""test_webapp_panel.py: the run page's buttons (webapp/runs.py, the POST routes), the review child's --return-to, the
panel added at serve time, and the log lines the panel reads (pinned against the tools that print them).

    python -m pytest tests/test_webapp_panel.py -q

No book, no model. The review page itself is tested on a synthetic run (as test_review_sessions.py does); a real
Review again → Finish → apply is in the real-run tests of the builder report.
"""
import os, sys, json, time, signal, threading, subprocess, urllib.request
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import config, jobs, logs, runs, server as W  # noqa: E402
from review import sessions as S, server as RS  # noqa: E402
from test_webapp import setup, settings, fake, wait, get, free_port, sha, app  # noqa: E402,F401  (fixtures)
from test_review_sessions import run_folder, ALL, digest, ai_order  # noqa: E402,F401
import app as APP  # noqa: E402

def src(rel): return open(os.path.join(HERE, rel), encoding='utf-8').read()

# ------------------------------------------------------------------ the log lines, one assertion each
def test_the_review_page_line_is_what_the_server_prints():
    assert "print(f'review page: {url}" in src('review/server.py') and "url = f'http://localhost:{srv.server_address[1]}/'" in src('review/server.py')
    assert logs.review_url('x\nreview page: http://localhost:8766/\n  open it') == 'http://localhost:8766/'

def test_review_recorded_line():
    assert "print(f'review recorded: " in src('review_workorder.py') and logs.RECORDED == 'review recorded: '

def test_step_lines_of_sessions_run():
    assert "say(f'▶ {what}')" in src('review/sessions.py') and "say(f'  ✓ {what}: {d:.1f}s')" in src('review/sessions.py')

def test_step_lines_of_run_api_stage():
    assert 'echo "▶ $label"' in src('run_api.sh') and 'echo "  ✓ $label: $(fmt "$d")"' in src('run_api.sh')

def test_done_stays_open_and_refused_lines():
    w = src('review_workorder.py')
    assert "print(f'done: {S.label(s[\"id\"])} is the current result in {R}')" in w
    assert "stays open: run the same command again to carry on'" in w and "sys.exit(f'refused: {e}')" in w

def test_steps_are_parsed_as_printed():
    text = ('▶ 0/5 intake: not re-run; applying to the intake result saved before the review stop\n▶ 1/5 audit (no model)\n'
            '  ✓ 1/5 audit (no model): 1m 04.2s\n▶ apply (no model)\n  ✓ apply (no model): 12.3s\n▶ verify (no model)\n')
    assert logs.steps(text) == [
        {'label': '0/5 intake: not re-run; applying to the intake result saved before the review stop', 'state': 'done', 'time': None},
        {'label': '1/5 audit (no model)', 'state': 'done', 'time': '1m 04.2s'}, {'label': 'apply (no model)', 'state': 'done', 'time': '12.3s'},
        {'label': 'verify (no model)', 'state': 'running', 'time': None}]
    assert logs.outcome('▶ apply\nrefused: apply (no model) failed (exit 1): the current result is unchanged') == \
        'refused: apply (no model) failed (exit 1): the current result is unchanged'
    assert logs.outcome('done: session 4 is the current result in /r') == 'done: session 4 is the current result'
    assert logs.outcome('session 3 stays open: run the same command again to carry on') == 'session 3 stays open'

# ------------------------------------------------------------------ --return-to
@pytest.mark.parametrize('url', ['http://127.0.0.1:8760/run/a/b/?after=finish', 'http://localhost:8761/run/x/'])
def test_return_to_accepts_this_computer(url):
    assert RS.check_return_to(url) == url

@pytest.mark.parametrize('url', ['https://127.0.0.1:8760/', 'http://example.com:8760/', 'http://127.0.0.1/', 'http://user@127.0.0.1:8760/',
                                 'javascript:alert(1)', 'http://127.0.0.1.evil.com:8760/', 'http://[::1]:8760/', '//127.0.0.1:8760/'])
def test_return_to_refuses_anything_else(url):
    with pytest.raises(ValueError): RS.check_return_to(url)
    r = subprocess.run([sys.executable, 'review_workorder.py', '/nonexistent', '--serve', '--return-to', url], cwd=HERE, capture_output=True, text=True)
    assert r.returncode != 0 and '--return-to: only http://127.0.0.1' in r.stderr

def test_the_review_page_gets_return_to(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    from review import core
    p = S.P(R)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS, 'add_kinds': core.ADD_KINDS,
                        'items': core.build_items(ai, dg), 'addable': core.addable(ai, dg), 'session': {'key': 'abc:002', 'id': '002', 'reopened': True}})
    S.save(os.path.join(p['dir'], 'workorder.ai.json'), ai)
    port = free_port(); back = 'http://127.0.0.1:8760/run/book/r1/?after=finish'
    t = threading.Thread(target=lambda: RS.serve(p['dir'], '2026-10-29', port, open_browser=False, return_to=back), daemon=True); t.start()
    assert wait(lambda: get(port, '/')[0] == 200, 10)
    page = get(port, '/')[1].decode()
    assert '"return_to": "http://127.0.0.1:8760/run/book/r1/?after=finish"' in page and 'id="back"' in page and 'location.assign(RETURN_TO)' in page
    r = urllib.request.Request(f'http://127.0.0.1:{port}/finish', data=json.dumps({'reviewer': 'Kim', 'decisions': ALL, 'additions': [],
                               'gaps_ack': {'figures_without_alt': 'later', 'h1': 'later'}}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(r) as x: assert json.load(x)['finished']
    t.join(5)

# ------------------------------------------------------------------ ready to ship, never None or "unknown"
def test_ready_comes_from_the_glance_then_review_md_then_says_not_recorded(tmp_path):
    R = str(tmp_path)
    g = {'glance': {'ready': False, 'ship': [{'what': 'Safety checks', 'text': 'OK'}]}}
    assert runs.ready(R, g) == {'answer': 'No', 'lines': ['Safety checks: OK'], 'source': 'record.json'}
    (tmp_path / 'review.md').write_text('## Overview\n\n**Ready to ship?** Yes\n- Safety checks: OK\n- PAC: not run\n\nmore\n')
    assert runs.ready(R, {}) == {'answer': 'Yes', 'lines': ['Safety checks: OK', 'PAC: not run'], 'source': 'review.md'}
    (tmp_path / 'review.md').write_text('# an old review.md\n')
    assert runs.ready(R, {})['text'] == 'not recorded for this run' and runs.ready(R, {})['answer'] is None

# ------------------------------------------------------------------ the original, by sha256
def test_the_original_is_found_by_sha256_and_never_written(setup):
    s = settings(setup)
    a = setup / 'samples' / 'g' / 'other.pdf'; a.parent.mkdir(); a.write_bytes(b'%PDF other')
    b = setup / 'samples' / 'g' / 'book.pdf'; b.write_bytes(b'%PDF the book'); before = (b.stat().st_mtime_ns, sha(b))
    assert runs.find_original(s, sha(b), 'book.pdf') == str(b)
    assert json.load(open(setup / 'runs' / '.app' / 'sha256-cache.json'))[str(b)][2] == sha(b)
    assert runs.find_original(s, '0' * 64) is None
    assert (b.stat().st_mtime_ns, sha(b)) == before
    R = setup / 'runs' / 'book' / 'r1'; R.mkdir(parents=True)
    rec = {'document': {'file': 'book.pdf', 'sha256': sha(b)}, 'workorder': {'source': {'sha256': sha(b)}}}
    assert runs.pdf_needed(s, str(R), rec) == (str(b), None)                    # unpinned, tagged: --pdf
    rec['workorder']['source']['sha256'] = 'f' * 64
    p, why = runs.pdf_needed(s, str(R), rec)
    assert p is None and 'book.pdf' in why and 'ffffffffffffffff' in why and 'not in' in why
    assert runs.pdf_needed(s, str(R), {'intake': {'result': {'pdf': 'intake.pdf'}}}) == (None, None)

# ------------------------------------------------------------------ past Finish, from disk
START = '2026-10-29T10:00:00'
OLD, NEW = time.mktime((2026, 10, 29, 9, 0, 0, 0, 0, -1)), time.mktime((2026, 10, 29, 10, 0, 5, 0, 0, -1))   # before / after START

def marker(tmp_path, name, where, when):
    """A run folder with one Finish marker, its mtime set to `when`."""
    F = tmp_path / f'{name}-{int(when)}'; (F / 'reviews').mkdir(parents=True)
    if where != 'first': (F / 'record.json').write_text('{}')
    p = (F / 'review.json') if where == 'first' else (F / 'reviews' / name)
    p.mkdir() if name == 'work' else p.write_text('{}')
    os.utime(p, (when, when)); return str(F)

@pytest.mark.parametrize('name,where', [('review.json', 'reviews'), ('work', 'reviews'), ('promoting.json', 'reviews'), ('review.json', 'first')])
def test_a_finish_marker_counts_only_from_the_job_start(tmp_path, name, where):
    assert jobs.review_past_finish(marker(tmp_path, name, where, NEW), START)              # this review's Finish
    assert not jobs.review_past_finish(marker(tmp_path, name, where, OLD), START)          # stale: a failed apply's work/, an old review.json

def test_a_session_finished_since_the_job_start(tmp_path):
    R = tmp_path / 'r'; (R / 'reviews' / 'sessions').mkdir(parents=True); (R / 'record.json').write_text('{}')
    assert not jobs.review_past_finish(str(R), START)
    (R / 'reviews' / 'sessions' / '003.json').write_text(json.dumps({'id': '003', 'status': 'open'}))
    assert not jobs.review_past_finish(str(R), START)
    (R / 'reviews' / 'sessions' / '003.json').write_text(json.dumps({'id': '003', 'status': 'finished', 'finished': '2026-10-29T10:05:00'}))
    assert jobs.review_past_finish(str(R), START) and not jobs.review_past_finish(str(R), '2026-10-29T11:00:00')
    (R / 'reviews' / 'sessions' / '003.json').write_text(json.dumps({'id': '003', 'status': 'finished', 'finished': '2026-10-29T09:05:00'}))
    assert not jobs.review_past_finish(str(R), START)                                       # finished before this job started

def test_interrupt_itself_refuses_a_review_past_finish(setup):
    s = settings(setup)
    R = setup / 'runs' / 'a' / 'r'; (R / 'reviews').mkdir(parents=True)
    j = fake(setup, s, 'a/r', 30, R=str(R)); jobs.update(s['jobs'], j['id'], kind='review', counted=False)
    jobs.tick(s['jobs'], s)
    assert wait(lambda: (jobs.load(s['jobs'], j['id']) or {}).get('child_pid'))
    (R / 'reviews' / 'work').mkdir()                                                       # the re-apply has started
    assert jobs.interrupt(s['jobs'], j['id'], s['runs']) == (False, 'this review is past Finish and is being applied: it cannot be stopped now')
    assert jobs.counts(jobs.load(s['jobs'], j['id']), s['runs'])                           # and it takes a place in max_jobs now
    os.utime(R / 'reviews' / 'work', (OLD, OLD))                                           # the same folder, stale: a failed apply's
    assert not jobs.counts(jobs.load(s['jobs'], j['id']), s['runs'])
    assert jobs.interrupt(s['jobs'], j['id'], s['runs']) == (True, None)
    assert wait(lambda: jobs.load(s['jobs'], j['id'])['status'] == 'failed')

def test_liveness_marks_name_the_job(setup):
    s = settings(setup)
    Ra, Rb = setup / 'runs' / 'a' / 'r', setup / 'runs' / 'b' / 'r'; Ra.mkdir(parents=True); Rb.mkdir(parents=True)
    out = str(setup / 'times.txt')
    a = jobs.create(s['jobs'], 'apply', 'a/r', [sys.executable, str(setup / 'bin' / 'fakejob.py'), out, '30', str(Ra)], config.child_env(s), R=str(Ra))
    jobs.tick(s['jobs'], s)
    assert wait(lambda: (jobs.load(s['jobs'], a['id']) or {}).get('child_pid'))
    b = jobs.create(s['jobs'], 'apply', 'b/r', [sys.executable, str(setup / 'bin' / 'fakejob.py'), out, '30', str(Rb)], config.child_env(s), R=str(Rb))
    pg = jobs.load(s['jobs'], a['id'])['pgid']
    jobs.update(s['jobs'], b['id'], status='running', pid=pg, pgid=pg, started=jobs.now())   # a dead job whose group id is now another job's
    assert jobs.group_alive(s['jobs'], jobs.load(s['jobs'], a['id'])) and not jobs.group_alive(s['jobs'], jobs.load(s['jobs'], b['id']))
    os.killpg(pg, signal.SIGKILL)

def test_an_interrupted_job_says_what_is_left_from_disk(tmp_path):
    R = tmp_path / 'r'; (R / 'reviews' / 'sessions').mkdir(parents=True)
    j = {'kind': 'apply', 'started': START}
    def ses(**kw): (R / 'reviews' / 'sessions' / '002.json').write_text(json.dumps({'id': '002', **kw}))
    assert runs.after_interrupt(str(R), j)['state'] == 'none'
    ses(status='finished', finished='2026-10-29T09:59:00')
    assert runs.after_interrupt(str(R), j) == {'state': 'apply', 'text': 'Session 2 is finished and not applied: Apply applies it.'}
    ses(status='applied', applied='2026-10-29T10:03:00')                                    # the orphan finished alone
    assert runs.after_interrupt(str(R), j) == {'state': 'done', 'text': 'done (the app lost track of the job): session 2 is the current result'}
    ses(status='applied', applied='2026-10-29T09:00:00')                                    # applied before this job: not its doing
    assert runs.after_interrupt(str(R), j)['state'] == 'none'
    (R / 'reviews' / 'promoting.json').write_text('{}')
    t = runs.after_interrupt(str(R), j)
    assert t['state'] == 'apply' and 'Apply finishes it; it may apply the session again' in t['text'] and 'completes the promotion' not in t['text']
    (R / 'reviews' / 'promoting.json').unlink(); ses(status='open')
    assert runs.after_interrupt(str(R), {'kind': 'review', 'started': START})['state'] == 'continue'

def test_read_log_never_cuts_a_character(setup):
    s = settings(setup); j = fake(setup, s, 'a/r'); jobs.update(s['jobs'], j['id'], status='done')
    open(jobs.log_path(s['jobs'], j['id']), 'wb').write('ab ✓ cd\n'.encode())             # ✓ is 3 bytes, at offsets 3–5
    t, n = jobs.read_log(s['jobs'], j['id'], 0, limit=5)
    assert (t, n) == ('ab ', 3) and jobs.read_log(s['jobs'], j['id'], n)[0] == '✓ cd\n'

def test_config_may_not_be_a_settings_file(setup):
    from webapp import config as C
    for f in ('settings.json', 'settings.local.json'):
        p = os.path.join(C.HERE, f)
        if not os.path.exists(p): continue
        with pytest.raises(C.Bad, match='one of the settings files'): C.load(p, environ={})
    with pytest.raises(C.Bad, match='one of the settings files'): C.load(os.path.join(C.HERE, '..', 'webapp', 'settings.json'), environ={})

def test_shutdown_signals_only_its_own_reviews_before_finish(setup, monkeypatch):
    s = settings(setup)
    for n in ('mine', 'other', 'applying'): (setup / 'runs' / n / 'r' / 'reviews').mkdir(parents=True)
    ids = {}
    for n, pid in (('mine', os.getpid()), ('other', 1), ('applying', os.getpid())):
        j = fake(setup, s, f'{n}/r', 30); jobs.update(s['jobs'], j['id'], kind='review', counted=False, app_pid=pid); ids[n] = j['id']
    jobs.tick(s['jobs'], s)
    assert wait(lambda: all((jobs.load(s['jobs'], i) or {}).get('child_pid') for i in ids.values()))
    (setup / 'runs' / 'applying' / 'r' / 'reviews' / 'review.json').write_text('{}')      # its Finish, after the job started
    APP.close_reviews(s)
    assert wait(lambda: jobs.load(s['jobs'], ids['mine'])['status'] == 'failed')
    time.sleep(0.5)
    assert jobs.load(s['jobs'], ids['other'])['status'] == 'running' and jobs.load(s['jobs'], ids['applying'])['status'] == 'running'
    for n in ('other', 'applying'): os.killpg(jobs.load(s['jobs'], ids[n])['pgid'], signal.SIGKILL)

# ------------------------------------------------------------------ the routes
def post(port, path, body=None, origin=None):
    h = {'Content-Type': 'application/json', **({'Origin': origin} if origin else {})}
    st, b, _ = get(port, path, method='POST', headers=h, body=json.dumps(body or {}))
    return st, json.loads(b or b'{}')

def test_the_run_page_has_the_panel_and_the_file_is_unchanged(app):
    disk = (app['R'] / 'review.html').read_text(); before = sha(app['R'] / 'review.html')
    st, b, _ = get(app['port'], '/run/book/r1/'); page = b.decode()
    assert st == 200 and '<div id="pdfrem-panel" data-run="book/r1" data-current="ai">' in page and '<script src="/app/panel.js" defer>' in page
    assert '<link rel="stylesheet" href="/app/panel.css">' in page and '<title>r1</title>' in page and 'review.md</a>' in page
    assert sha(app['R'] / 'review.html') == before and 'pdfrem-panel' not in disk
    for f in ('panel.js', 'panel.css', 'palette.css'): assert get(app['port'], '/app/' + f)[0] == 200
    assert get(app['port'], '/app/settings.json')[0] == 404 and get(app['port'], '/app/../app.py')[0] == 404
    st, b, _ = get(app['port'], '/run/old/r0/')
    assert b'pdfrem-panel' in b and b'has no dashboard' in b and b'/app/palette.css' in b

def test_run_state(app):
    st, b, _ = get(app['port'], '/api/run/book/r1'); d = json.loads(b)
    assert st == 200 and d['current'] == {'id': 'ai', 'label': 'the result applied without review'} and d['sessions'] == [] and d['pinned'] is False
    assert d['ready']['text'] == 'not recorded for this run' and d['commands']['reopen'].endswith('--reopen')
    assert 'None' not in json.dumps(d['ready'])

def test_review_needs_the_original_and_then_queues_a_pin_and_the_review(app):
    port, t, R = app['port'], app['t'], app['R']
    rec = json.loads((R / 'record.json').read_text()); rec['document'].update(file='book.pdf', sha256='a' * 64)
    rec['workorder'] = {'source': {'sha256': 'a' * 64}}; (R / 'record.json').write_text(json.dumps(rec))
    st, b = post(port, '/api/run/book/r1/review')
    assert st == 409 and 'book.pdf' in b['error'] and 'aaaaaaaaaaaaaaaa' in b['error']
    orig = t / 'samples' / 'book.pdf'; orig.write_bytes(b'%PDF the book')
    rec['workorder']['source']['sha256'] = rec['document']['sha256'] = sha(orig); (R / 'record.json').write_text(json.dumps(rec))
    st, b = post(port, '/api/run/book/r1/review', {'from': 'ai'})
    assert st == 202 and b['job']['kind'] == 'pin'
    j = jobs.load(str(t / 'runs' / '.app'), b['job']['id'])
    assert j['argv'][1:] == ['review_workorder.py', str(R), '--pin', '--pdf', str(orig)]
    nxt = j['then']['argv']
    assert nxt[1:] == ['review_workorder.py', str(R), '--reopen', '--from', 'ai', '--pdf', str(orig), '--no-browser', '--return-to',
                       f'http://127.0.0.1:{port}/run/book/r1/?after=finish'] and j['then']['counted'] is False
    assert set(j['env']) <= set(config.BASE_ENV) | {'VERAPDF', 'PYTHONUNBUFFERED', 'LC_ALL', 'LC_CTYPE'}
    st, b = post(port, '/api/run/book/r1/review')
    assert st == 409 and 'already' in b['error']
    assert wait(lambda: jobs.load(str(t / 'runs' / '.app'), j['id'])['status'] in ('failed', 'done'), 60)
    assert jobs.load(str(t / 'runs' / '.app'), j['id'])['status'] == 'failed'        # the synthetic record cannot be pinned: refused, nothing kept
    assert 'refused: ' in json.loads(get(port, '/api/job/' + j['id'])[1])['outcome']
    assert not jobs.load(str(t / 'runs' / '.app'), j['id']).get('then_job')          # a failed pin starts no review

def test_apply_and_stop_refuse_with_a_reason(app):
    port, t = app['port'], app['t']
    st, b = post(port, '/api/run/book/r1/apply')
    assert st == 409 and b['error'] == 'no finished session is waiting to be applied'
    st, b = post(port, '/api/run/book/r1/stop')
    assert st == 409 and b['error'] == 'no review page is open for this run'
    assert post(port, '/api/run/book/r1/review', origin='http://evil.example')[0] == 403
    assert post(port, '/api/run/book/r1/nope')[0] == 404 and post(port, '/api/run/book/%2e%2e/review')[0] == 404

def test_stop_only_before_finish(app):
    port, t, R = app['port'], app['t'], app['R']
    s = config.load(str(t / 'app.json'), environ={})
    j = fake(t, s, 'book/r1', 30); jobs.update(s['jobs'], j['id'], kind='review', counted=False)
    assert wait(lambda: (jobs.load(s['jobs'], j['id']) or {}).get('child_pid'), 20)          # the app's dispatcher started it
    (R / 'reviews' / 'review.json').write_text('{}')                                          # Finish accepted
    st, b = post(port, '/api/run/book/r1/stop')
    assert st == 409 and 'past Finish' in b['error'] and jobs.load(s['jobs'], j['id'])['status'] == 'running'
    (R / 'reviews' / 'review.json').unlink()
    st, b = post(port, '/api/run/book/r1/stop')
    assert st == 200 and wait(lambda: jobs.load(s['jobs'], j['id'])['status'] == 'failed')

# ------------------------------------------------------------------ review 05
def ses(R, sid, status, **kw):
    os.makedirs(os.path.join(R, 'reviews', 'sessions'), exist_ok=True)
    json.dump({'id': sid, 'status': status, **kw}, open(os.path.join(R, 'reviews', 'sessions', f'{sid}.json'), 'w'))

def test_apply_is_offered_only_for_the_newest_session(app):
    port, R = app['port'], str(app['R'])
    ses(R, '001', 'applied'); ses(R, '002', 'finished', finished='2026-10-29T10:00:00')
    assert json.loads(get(port, '/api/run/book/r1')[1])['unapplied']['id'] == '002'               # the newest: offered
    ses(R, '003', 'applied', applied='2026-10-29T11:00:00')                                       # 002's apply failed, 003 replaced it
    d = json.loads(get(port, '/api/run/book/r1')[1])
    assert d['unapplied'] is None and d['latest']['id'] == '003'
    st, b = post(port, '/api/run/book/r1/apply')
    assert st == 409 and b['error'] == 'session 2 was replaced by session 3: Apply is offered only for the newest session'
    ses(R, '004', 'open')                                                                          # an open session changes nothing
    assert runs.unapplied(S.sessions(R)) is None
    assert runs.after_interrupt(R, {'kind': 'apply', 'started': '2026-10-29T12:00:00'})['state'] != 'apply'

INLINE = 'document.title = "x";'
PAGE = (f'<!doctype html><html><head><title>r1</title></head><body><a class="skip" href="#main">Skip to the content</a>\n'
        f'<header class="top"><h1>Review: book.pdf</h1></header><main id="main"><a href="javascript:alert(1)">x</a>'
        f'<script type="application/json" id="mentions">{{"1": []}}</script></main>\n<script>{INLINE}</script>\n</body></html>\n')

def test_csp_hashes_the_one_inline_script():
    import base64, hashlib
    h = base64.b64encode(hashlib.sha256(INLINE.encode()).digest()).decode()
    assert W.csp(PAGE) == f"frame-ancestors 'none'; script-src 'self' 'sha256-{h}'"
    assert W.csp(PAGE.replace('</main>', f'<script>{INLINE}</script></main>')) == "frame-ancestors 'none'; script-src 'self'"   # two: none allowed
    assert W.csp('<p>no script</p><script src="/app/panel.js"></script>') == "frame-ancestors 'none'; script-src 'self'"

def test_every_response_refuses_framing_and_run_pages_get_the_script_policy(app):
    import base64, hashlib
    (app['R'] / 'review.html').write_text(PAGE)
    h = base64.b64encode(hashlib.sha256(INLINE.encode()).digest()).decode()
    for path, method in (('/run/book/r1/', 'GET'), ('/run/book/r1/review.html', 'GET'), ('/run/book/r1/review.md', 'GET'), ('/app/panel.js', 'GET'),
                         ('/batch/b1/', 'GET'), ('/api/ping', 'GET'), ('/api/run/book/r1', 'GET'), ('/run/nope/', 'GET'), ('/run/book/r1', 'GET'),
                         ('/api/run/book/r1/apply', 'POST')):
        st, b, hd = get(app['port'], path, method=method, headers={'Content-Type': 'application/json'} if method == 'POST' else None,
                        body='{}' if method == 'POST' else None)
        assert hd.get('X-Frame-Options') == 'DENY' and "frame-ancestors 'none'" in hd.get('Content-Security-Policy', ''), (path, hd)
        if path in ('/run/book/r1/', '/run/book/r1/review.html'):
            assert hd['Content-Security-Policy'] == f"frame-ancestors 'none'; script-src 'self' 'sha256-{h}'", path
    st, b, hd = get(app['port'], '/run/book/r1/')
    page = b.decode()
    assert page.index('</header>') < page.index('id="pdfrem-panel"') < page.index('<main id="main">')    # the panel's h2 follows the h1
    assert 'data-current="ai"' in page and f'<script>{INLINE}</script>' in page                        # the inline script unchanged, so its hash holds
    st, b, hd = get(app['port'], '/run/old/r0/')
    assert hd['Content-Security-Policy'] == "frame-ancestors 'none'; script-src 'self'" and b.decode().index('</header>') < b.decode().index('pdfrem-panel')

def test_the_review_page_refuses_framing(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    from review import core
    p = S.P(R)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS, 'add_kinds': core.ADD_KINDS,
                        'items': core.build_items(ai, dg), 'addable': core.addable(ai, dg), 'session': {'key': 'abc:002', 'id': '002', 'reopened': True}})
    S.save(os.path.join(p['dir'], 'workorder.ai.json'), ai)
    port = free_port()
    threading.Thread(target=lambda: RS.serve(p['dir'], '2026-10-29', port, open_browser=False), daemon=True).start()
    assert wait(lambda: get(port, '/')[0] == 200, 10)
    for path in ('/', '/nope'):
        hd = get(port, path)[2]
        assert hd.get('X-Frame-Options') == 'DENY' and hd.get('Content-Security-Policy') == "frame-ancestors 'none'"
    r = urllib.request.Request(f'http://127.0.0.1:{port}/finish', data=json.dumps({'reviewer': 'Kim', 'decisions': ALL, 'additions': [],
                               'gaps_ack': {'figures_without_alt': 'later', 'h1': 'later'}}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(r) as x: assert json.load(x)['finished']

def test_the_return_to_url_is_percent_encoded(setup):
    s = settings(setup)
    R = setup / 'runs' / 'odd name#1' / 'r?x'; (R / 'reviews' / '_audit').mkdir(parents=True); (R / '_intake').mkdir()
    (R / 'record.json').write_text('{}'); (R / 'reviews' / 'basis.json').write_text('{"input": {}}'); (R / 'reviews' / '_audit' / 'digest.json').write_text('{}')
    (R / '_intake' / 'intake.pdf').write_bytes(b'%PDF')
    j = runs.start_review(s, 'odd name#1/r?x', str(R), 8760)
    assert j['argv'][-1] == 'http://127.0.0.1:8760/run/odd%20name%231/r%3Fx/?after=finish'
    RS.check_return_to(j['argv'][-1])

def test_a_missing_intake_result_is_named(setup):
    s = settings(setup)
    R = setup / 'runs' / 'u' / 'r'; (R / 'reviews' / '_audit').mkdir(parents=True); (R / 'reviews' / '_audit' / 'digest.json').write_text('{}')
    gone = str(R / '_intake' / 'intake.pdf')
    (R / 'reviews' / 'basis.json').write_text(json.dumps({'input': {'path': gone, 'sha256': 'b' * 64}}))
    p, why = runs.pdf_needed(s, str(R), {'document': {'file': 'book.pdf'}})
    assert p is None and gone in why and 'intake result' in why and 'original PDF' not in why

def test_api_jobs_has_a_limit(app):
    s = config.load(str(app['t'] / 'app.json'), environ={})
    ids = [jobs.create(s['jobs'], 'apply', f'x{i}/r', [sys.executable, '-c', 'pass'], {}, counted=True)['id'] for i in range(3)]
    for i in ids: jobs.update(s['jobs'], i, status='done')
    got = json.loads(get(app['port'], '/api/jobs?limit=2')[1])
    assert [j['id'] for j in got] == ids[::-1][:2]
