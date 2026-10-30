"""test_webapp_panel.py: the run page's buttons (webapp/runs.py, the POST routes), the review child's --return-to, the
panel added at serve time, and the log lines the panel reads (pinned against the tools that print them).

    python -m pytest tests/test_webapp_panel.py -q

No book, no model. The review page itself is tested on a synthetic run (as test_review_sessions.py does); a real
Review again → Finish → apply is in the real-run tests of the builder report.
"""
import os, sys, json, time, signal, threading, subprocess, urllib.request, urllib.parse
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
    (app['R'] / 'review.html').write_text(PAGE); (app['R'] / 'reviews' / 'versions' / '001' / 'review.html').write_text(PAGE)
    h = base64.b64encode(hashlib.sha256(INLINE.encode()).digest()).decode()
    for path, method in (('/run/book/r1/', 'GET'), ('/run/book/r1/reviews/versions/001/review.html', 'GET'), ('/run/book/r1/review.md', 'GET'), ('/app/panel.js', 'GET'),
                         ('/batch/b1/', 'GET'), ('/api/ping', 'GET'), ('/api/run/book/r1', 'GET'), ('/run/nope/', 'GET'), ('/run/book/r1', 'GET'),
                         ('/api/run/book/r1/apply', 'POST')):
        st, b, hd = get(app['port'], path, method=method, headers={'Content-Type': 'application/json'} if method == 'POST' else None,
                        body='{}' if method == 'POST' else None)
        assert hd.get('X-Frame-Options') == 'DENY' and "frame-ancestors 'none'" in hd.get('Content-Security-Policy', ''), (path, hd)
        if path in ('/run/book/r1/', '/run/book/r1/reviews/versions/001/review.html'):
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

# ------------------------------------------------------------------ reviews 06 and 07
def test_the_newest_finished_session_with_a_later_one_open(app):
    """Pinned as it is (review 06): the newest finished session is still the one Apply would take while a later session
    is open; the panel hides the button while a session is open, and the route accepts it."""
    port, R = app['port'], str(app['R'])
    ses(R, '001', 'applied'); ses(R, '002', 'finished', finished='2026-10-29T10:00:00'); ses(R, '003', 'open')
    os.makedirs(os.path.join(R, 'reviews', '_audit')); os.makedirs(os.path.join(R, '_intake'))      # pinned, with its input: no --pdf needed
    open(os.path.join(R, 'reviews', '_audit', 'digest.json'), 'w').write('{}'); open(os.path.join(R, 'reviews', 'basis.json'), 'w').write('{"input": {}}')
    open(os.path.join(R, '_intake', 'intake.pdf'), 'wb').write(b'%PDF')
    d = json.loads(get(port, '/api/run/book/r1')[1])
    assert d['unapplied']['id'] == '002' and d['open']['id'] == '003'
    assert "if (s.unapplied && !s.open) h += '<button type=\"button\" id=\"pp-apply\"" in src('webapp/panel.js')
    st, b = post(port, '/api/run/book/r1/apply')
    assert st == 202 and b['job']['kind'] == 'apply' and b['job']['what'] == 'Apply session 2'

def test_a_run_whose_name_needs_encoding_is_served(app):
    R = app['t'] / 'runs' / 'odd name#1' / 'r?x'; R.mkdir(parents=True); (R / 'record.json').write_text('{}'); (R / 'review.md').write_text('# x')
    st, b, _ = get(app['port'], '/run/odd%20name%231/r%3Fx/')
    assert st == 200 and 'data-run="odd name#1/r?x"' in b.decode()
    assert json.loads(get(app['port'], '/api/run/odd%20name%231/r%3Fx')[1])['run'] == 'odd name#1/r?x'

@pytest.mark.parametrize('q', ['²', '٣', '99999999999999999999', '-1', '0', 'x'])
def test_odd_numbers_in_the_query_never_break_a_route(app, q):
    assert get(app['port'], '/api/jobs?limit=' + urllib.parse.quote(q))[0] == 200
    j = jobs.create(str(app['t'] / 'runs' / '.app'), 'apply', 'q/r', [sys.executable, '-c', 'pass'], {}, counted=True)
    jobs.update(str(app['t'] / 'runs' / '.app'), j['id'], status='done')
    assert get(app['port'], f'/api/job/{j["id"]}?from=' + urllib.parse.quote(q))[0] == 200

def test_core_save_never_leaves_a_cut_short_file(tmp_path):
    from review import core
    p = str(tmp_path / 'review.json'); core.save(p, {'a': 1}); core.save(p, {'a': 2})
    assert json.load(open(p)) == {'a': 2} and os.listdir(tmp_path) == ['review.json']

CTRL_C_AT_FINISH = r'''
import sys, os, time, json, threading, signal
sys.path.insert(0, sys.argv[1]); R, port = sys.argv[2], int(sys.argv[3])
from review import core, server
real = core.finish
def slow(*a, **k):
    print('finish started', flush=True); time.sleep(1.5); return real(*a, **k)
core.finish = slow
v = server.serve(R, '2026-10-29', port, open_browser=False)
print('RESULT', 'recorded' if v else 'none', flush=True)
'''

def test_ctrl_c_during_finish_waits_for_the_record(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    from review import core
    p = S.P(R)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS, 'add_kinds': core.ADD_KINDS,
                        'items': core.build_items(ai, dg), 'addable': core.addable(ai, dg), 'session': {'key': 'abc:002', 'id': '002', 'reopened': True}})
    S.save(os.path.join(p['dir'], 'workorder.ai.json'), ai)
    port = free_port(); script = tmp_path / 'c.py'; script.write_text(CTRL_C_AT_FINISH)
    pr = subprocess.Popen([sys.executable, str(script), HERE, p['dir'], str(port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert wait(lambda: get(port, '/')[0] == 200, 20)
    body = json.dumps({'reviewer': 'Kim', 'decisions': ALL, 'additions': [], 'gaps_ack': {'figures_without_alt': 'later', 'h1': 'later'}})
    th = threading.Thread(target=lambda: get(port, '/finish', method='POST', headers={'Content-Type': 'application/json'}, body=body), daemon=True); th.start()
    time.sleep(0.6); pr.send_signal(signal.SIGINT)                                   # Ctrl+C while core.finish is running
    out = pr.communicate(timeout=30)[0]
    assert 'finish started' in out and 'review is recorded' in out and 'RESULT recorded' in out, out
    assert json.load(open(os.path.join(p['dir'], 'review.json')))['reviewer'] == 'Kim'          # whole, not cut short

def test_ctrl_c_before_finish_still_stops(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    from review import core
    p = S.P(R)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS, 'add_kinds': core.ADD_KINDS,
                        'items': core.build_items(ai, dg), 'addable': core.addable(ai, dg), 'session': {'key': 'abc:002', 'id': '002', 'reopened': True}})
    S.save(os.path.join(p['dir'], 'workorder.ai.json'), ai)
    port = free_port(); script = tmp_path / 'c.py'; script.write_text(CTRL_C_AT_FINISH)
    pr = subprocess.Popen([sys.executable, str(script), HERE, p['dir'], str(port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert wait(lambda: get(port, '/')[0] == 200, 20)
    st, b, _ = get(port, '/finish', method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps({'reviewer': 'Kim', 'decisions': {}, 'additions': []}))
    b = json.loads(b)
    assert st == 200 and b['finished'] is False and b['needs'] == 'unreviewed'          # not finished, before core.finish: Ctrl+C must not wait
    pr.send_signal(signal.SIGINT)
    out = pr.communicate(timeout=10)[0]
    assert 'stopped: the review is not finished' in out and 'RESULT none' in out, out

# ------------------------------------------------------------------ Patrick's pass on the run page
def test_steps_in_plain_words():
    assert logs.plain('apply (no model)') == 'applying the reviewed decisions' and logs.plain('verify (no model)') == 'checking the result'
    assert logs.plain('report') == 'writing the report' and logs.plain('1/5 audit (no model)') == 'auditing the PDF'
    steps = logs.steps('▶ apply (no model)\n  ✓ apply (no model): 12.0s\n▶ verify (no model)\n')
    assert logs.now_step('review', steps) == {'words': 'checking the result', 'n': 2, 'total': 3}
    assert logs.now_step('pin', []) == {'words': 're-auditing the run to pin it (free)', 'n': 1, 'total': 1}
    assert logs.now_step('apply', logs.steps('▶ apply (no model)\n  ✓ apply (no model): 1.0s\n')) is None

def test_job_titles_say_what_happened(tmp_path):
    R = str(tmp_path); ses(R, '003', 'applied', reviewer='sss')
    v = {'outcome': 'done: session 3 is the current result'}
    j = {'kind': 'review', 'what': 'Review again from session 2', 'status': 'done', 'ended': '2026-10-29T18:19:44'}
    assert runs.title(R, j, v) == 'Review again from session 2 → session 3 applied (sss, 18:19)'
    assert runs.title(R, dict(j, status='running'), {}) == 'Review again from session 2'
    assert runs.title(R, dict(j, status='failed'), {}) == 'Review again from session 2 → failed (18:19)'
    assert runs.title(R, j, {'outcome': 'session 4 stays open'}) == 'Review again from session 2 → session 4 left open (18:19)'
    assert runs.title(R, dict(j, kind='pin', what='Pin the run'), {}) == 'Pin the run → pinned (18:19)'
    lost = {'interrupted': {'state': 'done', 'text': 'done (the app lost track of the job): session 3 is the current result'}}
    assert runs.title(R, dict(j, kind='apply', what='Apply session 3', status='interrupted'), lost) == 'Apply session 3 → session 3 applied (sss, 18:19)'
    assert runs.reason({'status': 'failed', 'outcome': 'refused: apply (no model) failed (exit 1): the current result is unchanged', 'exit': 1}) == \
        'Apply (no model) failed (exit 1): the current result is unchanged'
    assert runs.reason({'status': 'failed', 'outcome': None, 'exit': 2}) == 'The command ended with an error (exit 2).'

def test_the_page_shows_no_log_or_command_and_every_job(app):
    s = config.load(str(app['t'] / 'app.json'), environ={})
    for i in range(12):
        j = jobs.create(s['jobs'], 'apply', 'book/r1', [sys.executable, '-c', 'pass'], {}, counted=True, what=f'Apply {i}')
        jobs.update(s['jobs'], j['id'], status='failed' if i == 11 else 'done', ended='2026-10-29T10:00:00', exit=1 if i == 11 else 0)
    d = json.loads(get(app['port'], '/api/run/book/r1')[1])
    assert len(d['jobs']) == 12                                                               # none drop off
    v = d['jobs'][-1]
    assert 'tail' not in v and 'command' not in v and v['log'] == os.path.join(s['jobs'], 'jobs', v['id'] + '.log')   # outside the repo: absolute
    assert runs.shown_path(os.path.join(config.ROOT, 'runs', '.app', 'jobs', 'x.log')) == os.path.join('runs', '.app', 'jobs', 'x.log')
    assert v['reason'] == 'The command ended with an error (exit 1).' and v['title'] == 'Apply 11 → failed (10:00)'
    js = src('webapp/panel.js')
    assert 'Log and command' not in js and 'The same from a terminal' not in js and 'Previous Jobs (' in js and 'Its log is saved in' in js
    assert 'Earlier jobs' not in js and v['action'] == 'Apply 11' and v['result'] == 'failed (10:00)'
    assert 'aria-hidden="true"></span>' in js and 'pp-spin' in js
    assert 'prefers-reduced-motion: reduce) { .pp .pp-spin { animation: none; } }' in src('webapp/panel.css')

def test_every_report_has_a_way_back(app):
    port, R = app['port'], app['R']
    (R / 'reviews' / 'versions' / '001' / 'review.html').write_text(PAGE)
    st, b, hd = get(port, '/run/book/r1/reviews/versions/001/review.html')
    page = b.decode()
    assert st == 200 and '<div id="pdfrem-version" data-run="book/r1" data-session="001">' in page and '/app/panel.js' in page
    assert page.index('</header>') < page.index('pdfrem-version') and 'pdfrem-panel' not in page
    js = src('webapp/panel.js')
    assert "You\\'re viewing" in js and 'Back to the Current Result' in js and 'Review Again from This Session' in js
    st, b, hd = get(port, '/run/book/r1/review.md')
    assert st == 200 and hd['Content-Type'].startswith('text/html') and '<a href="/run/book/r1/">Back to the Run Page</a>' in b.decode()
    assert '<pre class="pp-md"># Review</pre>' in b.decode() and 'href="review.md?raw=1"' in b.decode()
    st, b, hd = get(port, '/run/book/r1/review.md?raw=1')
    assert hd['Content-Type'].startswith('text/plain') and b == b'# Review'
    st, b, hd = get(port, '/run/book/r1/reviews/versions/001/review.md')
    assert 'A Previous Result (Session 1)' in b.decode() and '<a href="review.html">This Previous Result' in b.decode()
    assert get(port, '/run/book/r1/review.html')[2].get('Location') == '/run/book/r1/'

def test_review_again_names_where_it_starts(setup):
    s = settings(setup)
    R = setup / 'runs' / 'b' / 'r'; (R / 'reviews' / '_audit').mkdir(parents=True); (R / '_intake').mkdir()
    (R / 'record.json').write_text('{}'); (R / 'reviews' / 'basis.json').write_text('{"input": {}}'); (R / 'reviews' / '_audit' / 'digest.json').write_text('{}')
    (R / '_intake' / 'intake.pdf').write_bytes(b'%PDF')
    ses(str(R), '001', 'applied'); ses(str(R), '002', 'applied')
    assert runs.start_review(s, 'b/r', str(R), 8760)['what'] == 'Review again from session 2'

# ------------------------------------------------------------------ Patrick's second pass
def test_a_second_start_refuses_an_app_running_other_code(setup):
    """A running app with the same settings but other code (started before the code changed) is refused, not opened."""
    import http.server
    s = settings(setup)
    port = json.loads((setup / 'app.json').read_text())['port']
    class P(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            b = json.dumps({'app': 'pdfrem', 'root': config.ROOT, 'settings': s['sha'], 'code': 'older'}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    srv = http.server.HTTPServer(('127.0.0.1', port), P); threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        env = {k: v for k, v in os.environ.items() if k != 'VERAPDF'}
        r = subprocess.run([sys.executable, 'app.py', '--config', str(setup / 'app.json'), '--no-browser'], cwd=HERE, env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode != 0 and 'the running app is older than the code on disk: stop it and start again' in r.stderr
    finally: srv.shutdown()

def test_the_panel_files_are_read_once_at_start(setup, monkeypatch):
    s = settings(setup)
    js = setup / 'panel.js'; js.write_text('/* v1 */')
    monkeypatch.setitem(W.STATIC, 'panel.js', str(js))
    srv = W.make(dict(s, port=free_port()), [], code='c0ffee')
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        assert get(port, '/app/panel.js')[1] == b'/* v1 */'
        js.write_text('/* v2, written while the app runs */')
        assert get(port, '/app/panel.js')[1] == b'/* v1 */'                                  # the pages keep matching the running code
        assert json.loads(get(port, '/api/ping')[1])['code'] == 'c0ffee'
    finally: srv.shutdown(); srv.server_close()

def test_code_fingerprint_covers_the_app_code():
    a = config.code_fingerprint()
    assert len(a) == 16 and a == config.code_fingerprint()
    assert set(config.CODE) == {'app.py', 'webapp', 'review', 'lib/titles.py', 'lib/glance.py'}

def test_panel_and_review_page_details():
    js, css, page = src('webapp/panel.js'), src('webapp/panel.css'), src('review/page.html')
    assert "'Waiting for you: the review page is open'" in js and 'Ready to ship?</b>' not in js            # the report's card says it
    assert '[tabindex="-1"]:not(.hit):focus, [tabindex="-1"]:not(.hit):focus-visible { outline: none; }' in css   # any app page, not .hit
    assert '.pp summary { cursor: pointer; font-size: 15px; color: var(--ink); }' in css
    assert 'placeholder="Your name"' in page and '<h1 id="title">Work Order Review</h1>' in page and 'Back to the Run Page' in page
    assert ": done' + (s.time ? ', ' + esc(s.time) : '') : j.status === 'running' ? '' : ': did not finish'" in js   # no ": running"
    assert 'html { scroll-padding-top' not in page and 'main [id] { scroll-margin-top: calc(var(--top, 0px) + 8px); }' in page

def test_the_report_review_section(tmp_path):
    import report_html as H
    ss = [{'id': '001', 'from': 'ai', 'status': 'applied', 'reviewer': 'Kim', 'date': '2026-10-28', 'carried': 0, 'since_start': 4, 'changes': 2,
           'counts': {'approved': 5, 'changed': 2, 'rejected': 1, 'accepted_unreviewed': 3}},
          {'id': '002', 'from': '001', 'status': 'applied', 'reviewer': 'sss', 'date': '2026-10-29', 'carried': 3, 'since_start': 1, 'changes': 2,
           'counts': {'approved': 9, 'rejected': 0, 'accepted_unreviewed': 2}}]
    rec = {'review': {'session': '002', 'sessions': ss, 'run': '../runs/b/r', 'decisions': [{'id': 'x', 'kind': 'retype', 'label': 'A', 'page': 2, 'status': 'approved'}]}}
    out = ''.join(H.review_card(str(tmp_path), rec))
    assert '<p><strong>Session 2</strong> · sss · 2026-10-29 · 9 approved · 0 rejected · 2 accepted without review</p>' in out
    assert out.count('<td class="nowrap">2 <strong>(current)</strong></td>') == 1 and '<td class="nowrap">3 from session 1</td>' in out
    assert '<td class="nowrap">none</td>' in out and '<td class="nowrap">session 1</td>' in out                # From and Carried never wrap
    assert '<details class="fold"><summary>Previous Sessions (1)</summary>' in out and '<td class="nowrap">2026-10-28</td>' in out
    assert out.index('Previous Sessions (1)') < out.index('<td class="nowrap">1</td>')                     # session 1 only inside the fold
    assert 'From a terminal' not in out and 'review_workorder.py' not in out and 'Earlier sessions' not in out
    assert '<h2 id="rev-h">Review of the AI\'s Decisions</h2>' in out and '<summary>Approved: 1</summary>' in out
    assert '<th scope="col">Changed in the Session</th>' in out and '<th scope="col">Status, Set In</th>' in out
    assert 'accepted unreviewed' not in out and 'carried:' not in out
    assert H.counts_text({'approved': 1, 'accepted_unreviewed': 2}) == '1 approved, 2 accepted without review'
    assert 'details.fold summary { cursor: pointer; color: var(--ink); font-size: 15px; }' in H.CSS and '.strip:focus-visible' in H.CSS
    assert '[tabindex="-1"]:focus { outline: none; }' in H.CSS
    assert S.summary_text({'id': '001', 'review': {'counts': {'accepted_unreviewed': 4}, 'changes': []}}).startswith('Session 1 (summary only): 4 accepted without review')

# ------------------------------------------------------------------ Patrick's third pass: capitalization
@pytest.mark.parametrize('s,want', [
    ("Review of the AI's decisions", "Review of the AI's Decisions"), ('Ready to ship? No', 'Ready to Ship? No'),
    ('Current result: session 5', 'Current Result: Session 5'), ('veraPDF (WCAG rules)', 'veraPDF (WCAG Rules)'),
    ('Previous jobs (2)', 'Previous Jobs (2)'), ('Review again from session 4', 'Review Again from Session 4'),
    ("Start over from the AI's decisions", "Start Over from the AI's Decisions"), ('review.md of a run', 'review.md of a Run'),
    ('H1 and title', 'H1 and Title'), ('a word to', 'A Word To'), ('Pages with something listed (4)', 'Pages with Something Listed (4)')])
def test_title_case(s, want):
    from lib.titles import title_case
    assert title_case(s) == want

def test_the_same_title_case_rule_in_the_pages():
    """panel.js and page.html carry the same small-word list and skip rules as lib/titles.py."""
    from lib.titles import SMALL
    for f in ('webapp/panel.js', 'review/page.html'):
        t = src(f)
        assert "const SMALL = new Set(['a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'by', 'from', 'with']);" in t
        assert "/[./_@\\d]/.test(core)" in t and 'edge = /[:?—]$/.test(x);' in t
    assert SMALL == {'a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'by', 'from', 'with'}

def test_a_job_card_and_its_one_line_forms():
    js = src('webapp/panel.js')
    assert "esc(tc(j.action || j.title))" in js                                   # card heading: the action, Title Case
    assert "return /^(done|pinned|discarded)\\b/.test(r) ? cap(r) : 'Done: ' + r;" in js   # status line: "Done: session 5 applied (…)"
    assert "<b>Last Job:</b> ' + esc(cap(last.title))" in js and "'<li>' + esc(cap(j.title))" in js

# ------------------------------------------------------------------ Patrick's fourth pass
def test_discard_open_marks_the_session_abandoned_and_keeps_it(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    with pytest.raises(S.Refused, match='no session is open'): S.discard_open(R)
    S.save_session(R, {'id': '002', 'status': 'open', 'started': '2026-10-29T10:00:00'})
    S.save(S.P(R)['draft'], {'reviewer': 'Kim', 'decisions': {'x': {'status': 'approved'}}})
    before = sha(os.path.join(R, 'record.json'))
    assert S.discard_open(R, say=lambda *a: None) == ['002']
    s = S.session(R, '002')
    assert s['status'] == 'abandoned' and s['abandoned'] and s['draft']['decisions'] == {'x': {'status': 'approved'}}   # kept, not deleted
    assert not os.path.exists(S.P(R)['draft']) and sha(os.path.join(R, 'record.json')) == before                       # the result is unchanged

def test_discard_open_from_the_command_line(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    S.save_session(R, {'id': '002', 'status': 'open', 'started': '2026-10-29T10:00:00'})
    r = subprocess.run([sys.executable, 'review_workorder.py', R, '--discard-open'], cwd=HERE, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and 'discarded: session 2' in r.stdout and 'is unchanged' in r.stdout and S.session(R, '002')['status'] == 'abandoned'
    r = subprocess.run([sys.executable, 'review_workorder.py', R, '--discard-open'], cwd=HERE, capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and 'refused: no session is open' in r.stderr

def test_the_discard_route(app):
    port, t, R = app['port'], app['t'], app['R']
    s = config.load(str(t / 'app.json'), environ={})
    st, b = post(port, '/api/run/book/r1/discard')
    assert st == 409 and b['error'] == 'no session is open'
    ses(str(R), '002', 'open', started='2026-10-29T10:00:00')
    j = fake(t, s, 'book/r1', 30); jobs.update(s['jobs'], j['id'], kind='review', counted=False)          # its review page is open
    assert wait(lambda: (jobs.load(s['jobs'], j['id']) or {}).get('child_pid'), 20)
    st, b = post(port, '/api/run/book/r1/discard')
    assert st == 409 and b['error'] == 'the review page is open: press Stop Reviewing first, then Discard'
    (R / 'reviews' / 'review.json').write_text('{}')                                                       # past Finish
    st, b = post(port, '/api/run/book/r1/discard')
    assert st == 409 and 'past Finish' in b['error']
    os.killpg(jobs.load(s['jobs'], j['id'])['pgid'], signal.SIGKILL); (R / 'reviews' / 'review.json').unlink()
    assert wait(lambda: jobs.load(s['jobs'], j['id'])['status'] != 'running', 20)
    st, b = post(port, '/api/run/book/r1/discard')
    assert st == 202 and b['job']['kind'] == 'discard' and b['job']['what'] == 'Discard session 2'
    assert jobs.load(s['jobs'], b['job']['id'])['argv'][1:] == ['review_workorder.py', str(R), '--discard-open']

def test_fourth_pass_details():
    import report_html as H
    js, css = src('webapp/panel.js'), src('webapp/panel.css')
    assert 'Its choices are kept in Session History as abandoned; the current result (' in js and "esc(tc('Discard ' + s.open.label))" in js
    assert "'The review page is closed. ' + open + ' stays open: press Continue Review to carry on.'" in js
    assert "if (!miss.length) return '';" in js and 'previous result' in js and 'earlier result' not in js
    assert 'body:has(#pdfrem-version) .replaced { display: none; }' in css and '#pp-vreview { margin-left: 12px; }' in css
    rec = {'review': {'session': '001', 'sessions': [{'id': '001', 'from': 'ai', 'status': 'applied', 'reviewer': 'K', 'date': '2026-10-29',
           'counts': {'approved': 1}}], 'decisions': [{'id': 'x', 'kind': 'retype', 'label': 'A', 'page': 2, 'status': 'approved'}]}}
    out = ''.join(H.review_card('/tmp', rec))
    assert '<hr class="thin"><h3 class="rev-sub">Decisions in This Session</h3>' in out and '<p>1 approved</p>' not in out

# ------------------------------------------------------------------ Patrick's fifth pass
def test_messages_can_be_dismissed_and_are_neutral():
    js, css = src('webapp/panel.js'), src('webapp/panel.css')
    assert '<button type="button" class="pp-x" data-act="dismiss" aria-label="Dismiss message">' in js and '<span aria-hidden="true">×</span></button>' in js
    assert "if (act === 'dismiss') { msg(''); $('pp-h').focus(); return; }" in js                     # focus to the Run Actions heading
    assert js.index("if (act === 'dismiss')") < js.index("msg('');                                                       // any other panel button")
    assert '<div id="pp-msg" class="pp-msg" tabindex="-1" hidden></div>' in js and '<p id="pp-msg"' not in js
    assert '#pdfrem-panel > .pp {' not in css and 'border-left: 6px solid var(--accent)' not in css     # Run Actions: the thin border only
    assert '.pp .pp-msg.pp-okmsg { border: 1px solid var(--line); background: var(--panel); }' in css  # a message: neutral
    assert '.pp .pp-msg { border-left: 4px solid var(--reject);' in css                                # an error keeps its red
    assert '.pp .pp-warn { border-left: 4px solid var(--change);' in css                               # Setup keeps its orange
    assert '.pp .pp-msg:not([hidden]) { display: flex;' in css                                         # hidden still hides it

# ------------------------------------------------------------------ the VoiceOver pass in Safari
def test_no_dismiss_or_close_button_has_an_unlabeled_glyph():
    import re
    for f in ('webapp/panel.js', 'review/page.html', 'webapp/server.py', 'report_html.py'):
        t = src(f)
        for m in re.finditer(r'<button[^>]*>(.*?)</button>', t):
            if '×' in m.group(1):                                                     # the glyph, if any, only inside aria-hidden
                assert 'aria-label="' in m.group(0) and re.fullmatch(r'<span aria-hidden="true">×</span>', m.group(1)), (f, m.group(0))
    assert "aria-label=\"Dismiss message\">' +\n                       '<span aria-hidden=\"true\">×</span></button>'" in src('webapp/panel.js')
    assert 'aria-label="Close Sections"><span aria-hidden="true">×</span></button>' in src('review/page.html')

def test_in_page_link_targets_take_focus():
    import report_html as H
    assert '<main id="main" tabindex="-1">' in src('report_html.py') and src('report_html.py').count('<main id="main" tabindex="-1">') == 2
    assert "el.setAttribute('tabindex', '-1'); el.classList.add('hit'); el.scrollIntoView({block: 'center'}); el.focus({preventScroll: true});" in src('report_html.py')
    js, page, srv = src('webapp/panel.js'), src('review/page.html'), src('webapp/server.py')
    assert "if (!t.hasAttribute('tabindex')) t.setAttribute('tabindex', '-1');\n  t.scrollIntoView(); t.focus({ preventScroll: true });" in js
    assert 'if (e.defaultPrevented || e.button) return;' in js                            # review.html's own handler goes first
    assert "goTo(document.querySelector(a.getAttribute('href')));" in page and "goTo(document.getElementById('card-' + t.id));" in page
    assert '[tabindex="-1"]:focus, [tabindex="-1"]:focus-visible { outline: none; }' in page
    assert srv.count('<main id="main" tabindex="-1">') == 2 and '<script src="/app/panel.js" defer></script></body></html>' in srv

def test_finish_not_yet_is_200_with_needs(tmp_path):
    R, rec, ai, dg = run_folder(tmp_path)
    from review import core
    p = S.P(R)
    S.save(p['items'], {'book': 'book.pdf', 'run': 'run', 'pages': 5, 'pdf': '', 'groups': core.GROUPS, 'levels': core.LEVELS, 'add_kinds': core.ADD_KINDS,
                        'items': core.build_items(ai, dg), 'addable': core.addable(ai, dg), 'session': {'key': 'abc:002', 'id': '002', 'reopened': True}})
    S.save(os.path.join(p['dir'], 'workorder.ai.json'), ai)
    port = free_port()
    th = threading.Thread(target=lambda: RS.serve(p['dir'], '2026-10-30', port, open_browser=False), daemon=True); th.start()
    assert wait(lambda: get(port, '/')[0] == 200, 10)
    def fin(body):
        st, b, _ = get(port, '/finish', method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps(body)); return st, json.loads(b)
    st, b = fin({'reviewer': 'Kim', 'decisions': {}, 'additions': []})
    assert st == 200 and b['finished'] is False and b['needs'] == 'unreviewed' and b['unreviewed']
    st, b = fin({'reviewer': 'Kim', 'decisions': ALL, 'additions': []})
    assert st == 200 and b['finished'] is False and b['needs'] == 'gaps' and b['gaps']
    st, b = fin({'reviewer': 'Kim', 'decisions': ALL, 'additions': [], 'gaps_ack': {g['id']: 'later' for g in b['gaps']}})
    assert st == 200 and b['finished'] is True
    th.join(5)
    page = src('review/page.html')
    assert "if (s === 200 && b.needs === 'unreviewed')" in page and "if (s === 200 && b.needs === 'gaps')" in page and 's === 409' not in page
    assert '<h2 id="gapTitle" tabindex="-1">' in page and "document.getElementById('gapTitle').focus();" in page
    assert 'aria-describedby="gapCtx"' in page and 'id="gapErr" role="alert"' in page

# ------------------------------------------------------------------ review 08
def test_the_landing_highlight_keeps_its_outline_and_the_page_map_is_unchanged():
    import re, report_html as H
    css = src('webapp/panel.css')
    assert '.hit, .hit:focus { outline: 2px solid var(--accent); outline-offset: 1px; }' in H.CSS          # 2 px, kept while focused
    # nothing in either stylesheet removes .hit's outline: every no-outline rule for script-focused targets excludes .hit
    for sheet in (H.CSS, css):
        for rule in re.findall(r'[^{}]*\[tabindex="-1"\][^{}]*\{[^}]*outline:\s*none[^}]*\}', sheet):
            sel = rule.split('{')[0]
            assert ':not(.hit)' in sel or sheet is H.CSS, rule                                                 # panel.css: must exclude .hit
    # in the report the no-outline rule comes before .hit, so .hit:focus wins there too (equal specificity, later rule)
    assert H.CSS.index('[tabindex="-1"]:focus { outline: none; }') < H.CSS.index('.hit, .hit:focus {')
    # the page map is exactly as it was: its own rules, and land() never marks a cell
    for rule in ('.cell.active { outline: 2px dotted var(--ink); outline-offset: 1px; }', '.cell.pinned { outline: 2px solid var(--accent); outline-offset: 2px; }',
                 '.strip:focus { outline: none; } .strip:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }'):
        assert rule in H.CSS
    assert "if (el.classList.contains('cell')) { clearHit(); goPage(el); } else land(el);" in src('report_html.py')

@pytest.mark.parametrize('flag', [['--apply'], ['--pin'], ['--sessions'], ['--replay-to', '/tmp/x']])
def test_discard_open_is_refused_with_another_action(tmp_path, flag):
    R, rec, ai, dg = run_folder(tmp_path)
    S.save_session(R, {'id': '002', 'status': 'open', 'started': '2026-10-30T10:00:00'})
    r = subprocess.run([sys.executable, 'review_workorder.py', R, '--discard-open'] + flag, cwd=HERE, capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and f'--discard-open goes on its own (or with --reopen --from), not with {flag[0]}' in r.stderr
    assert S.session(R, '002')['status'] == 'open'                                       # nothing was done

def test_review_08_small_items():
    import report_html as H
    assert "try { id = decodeURIComponent(a.getAttribute('href').slice(1)); } catch (err) { return; }" in src('webapp/panel.js')
    rec = {'review': {'session': '001', 'sessions': [{'id': '001', 'from': 'ai', 'status': 'applied', 'reviewer': 'K', 'date': '2026-10-30'}]}}
    out = ''.join(H.review_card('/tmp', rec))
    assert '<p><strong>Session 1</strong> · K · 2026-10-30 · counts not recorded</p>' in out and '0 approved' not in out

# ------------------------------------------------------------------ CodeQL on PR #46
def test_csp_finds_a_script_closed_with_a_space_and_never_hangs():
    import base64, hashlib, time
    body = '\nif (a < b && c > d) { x = "</p>"; }\n'
    h = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    assert W.csp(f'<p>x</p><script>{body}</script >tail') == f"frame-ancestors 'none'; script-src 'self' 'sha256-{h}'"   # "</script >"
    assert W.csp(f'<SCRIPT>{body}</SCRIPT>') == f"frame-ancestors 'none'; script-src 'self' 'sha256-{h}'"
    assert W.csp('<script type="application/json">{}</script><script src="/app/panel.js"></script>') == "frame-ancestors 'none'; script-src 'self'"
    t = time.time(); W.csp('<script ' * 50000); W.csp('<body ' * 50000); W.with_panel('<body ' * 50000, 'r')
    assert time.time() - t < 2                                                               # linear: no polynomial regex left

def test_after_body_finds_the_tag_without_a_regex():
    assert W.after_body('<html><BODY class="x">t', '[B]') == '<html><BODY class="x">[B]t'
    assert W.after_body('<html>no body', '[B]') == '[B]<html>no body'
    assert 're.search(r\'<body' not in src('webapp/server.py') and 'SCRIPT = re.compile' not in src('webapp/server.py')

def test_paths_are_checked_where_they_are_used(setup):
    s = settings(setup)
    os.makedirs(os.path.join(s['jobs'], 'jobs'), exist_ok=True)
    open(os.path.join(s['jobs'], 'secret.json'), 'w').write('{"x": 1}')
    assert jobs.load(s['jobs'], '../secret') is None and jobs.read_log(s['jobs'], '../secret') == ('', 0)
    srv = src('webapp/server.py')
    for line in ("rp = os.path.realpath(p)                     # only files inside the runs folder",
                 "if not rp.startswith(RUNS + os.sep) or not os.path.isfile(rp)",
                 "if not B.startswith(BB + os.sep)", "if p.startswith(base + os.sep) and os.path.isfile(p): out[n] = p",
                 "if rec.startswith(base + os.sep):"):
        assert line in srv, line
    assert "if not p.startswith(os.path.realpath(folder(J)) + os.sep): return None" in src('webapp/jobs.py')
