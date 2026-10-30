"""test_webapp.py: the app's settings, setup check, jobs and server (webapp/, app.py). No book, no model.

    python -m pytest tests/test_webapp.py -q

veraPDF is a stub script given through --config (it answers --version as veraPDF does, so vera.py --check passes): the
same on this machine and on CI, which has no veraPDF. Nothing here skips the app's setup check. Java must be on PATH or
in webapp/settings.local.json, as for the app itself. Every job runs a small script in the test's own folder.
"""
import os, sys, json, time, signal, socket, hashlib, subprocess, http.client
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import config, checks, jobs  # noqa: E402

FAKEJOB = '''import sys, os, time, json
out, secs = sys.argv[1], float(sys.argv[2])
with open(out, 'a') as f: f.write(f"start {time.time():.3f} {sys.argv[3] if len(sys.argv) > 3 else ''}\\n")
print("▶ step one", flush=True); time.sleep(secs)
with open(out, 'a') as f: f.write(f"end {time.time():.3f} {sys.argv[3] if len(sys.argv) > 3 else ''}\\n")
sys.exit(int(os.environ.get('REVIEW', '0') == 'fail') * 3)
'''
ENVDUMP = 'import os, sys, json; json.dump(dict(os.environ), open(sys.argv[1], "w"))\n'

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def free_port():
    with socket.socket() as k: k.bind(('127.0.0.1', 0)); return k.getsockname()[1]

def stub_vera(d, answer='veraPDF 1.30.3'):
    p = os.path.join(d, 'verapdf'); open(p, 'w').write(f'#!/bin/sh\nif [ "$1" = "--version" ]; then echo "{answer}"; exit 0; fi\nexit 1\n'); os.chmod(p, 0o755)
    return p

@pytest.fixture
def setup(tmp_path):
    """Folders, a stub veraPDF, the fake job script and a --config file."""
    for d in ('runs', 'samples', 'bin'): (tmp_path / d).mkdir()
    (tmp_path / 'bin' / 'fakejob.py').write_text(FAKEJOB); (tmp_path / 'bin' / 'envdump.py').write_text(ENVDUMP)
    cfg = {'runs': str(tmp_path / 'runs'), 'samples': str(tmp_path / 'samples'), 'uploads': str(tmp_path / 'uploads'),
           'jobs': str(tmp_path / 'runs' / '.app'), 'port': free_port(), 'max_jobs': 2, 'tools': {'VERAPDF': stub_vera(str(tmp_path / 'bin'))}}
    (tmp_path / 'app.json').write_text(json.dumps(cfg))
    return tmp_path

def settings(t, **over):
    c = json.loads((t / 'app.json').read_text()); c.update(over); (t / 'app.json').write_text(json.dumps(c))
    return config.load(str(t / 'app.json'), environ={})

# ------------------------------------------------------------------ settings
def base_dir(t, local=None):
    b = t / 'base'; b.mkdir(exist_ok=True)
    (b / 'settings.json').write_text(json.dumps({'host': '127.0.0.1', 'port': 8760, 'runs': str(t / 'runs'), 'samples': str(t / 'samples'),
                                                 'uploads': str(t / 'u'), 'jobs': str(t / 'j'), 'max_jobs': 2, 'tools': {'VERAPDF': '', 'path_prepend': []}}))
    if local is not None: (b / 'settings.local.json').write_text(json.dumps(local))
    return str(b)

def test_settings_layers_later_wins(setup):
    t = setup; b = base_dir(t, {'max_jobs': 3, 'tools': {'VERAPDF': '/a/verapdf', 'path_prepend': ['/java']}})
    (t / 'c.json').write_text(json.dumps({'max_jobs': 4}))
    s = config.load(None, base=b, environ={})
    assert s['max_jobs'] == 3 and s['tools'] == {'VERAPDF': '/a/verapdf', 'path_prepend': ['/java']}
    s = config.load(str(t / 'c.json'), base=b, environ={})
    assert s['max_jobs'] == 4 and s['tools']['VERAPDF'] == '/a/verapdf'
    s = config.load(str(t / 'c.json'), base=b, environ={'VERAPDF': '/b/verapdf'})
    assert s['tools']['VERAPDF'] == '/b/verapdf'                                  # an exported VERAPDF wins over every file
    assert config.fingerprint(dict(s, port=9999)) == s['sha']                    # the port is not part of "the same app"

@pytest.mark.parametrize('where', ['settings', 'local', 'config', 'environ'])
def test_verapdf_off_is_refused_from_any_source(setup, where):
    t = setup; b = base_dir(t, {'tools': {'VERAPDF': 'off'}} if where == 'local' else None)
    if where == 'settings':
        d = json.loads(open(os.path.join(b, 'settings.json')).read()); d['tools']['VERAPDF'] = 'off'; open(os.path.join(b, 'settings.json'), 'w').write(json.dumps(d))
    (t / 'c.json').write_text(json.dumps({'tools': {'VERAPDF': 'OFF'}} if where == 'config' else {}))
    with pytest.raises(config.Bad, match='VERAPDF=off'):
        config.load(str(t / 'c.json'), base=b, environ={'VERAPDF': 'off'} if where == 'environ' else {})

def test_test_reply_dir_only_from_config(setup):
    t = setup
    with pytest.raises(config.Bad, match='test_reply_dir'): config.load(None, base=base_dir(t, {'test_reply_dir': str(t)}), environ={})
    (t / 'c.json').write_text(json.dumps({'test_reply_dir': str(t)}))
    assert config.load(str(t / 'c.json'), base=base_dir(t, {}), environ={})['test_reply_dir'] == str(t)

def test_host_and_folders_are_checked(setup):
    t = setup
    for host in ('0.0.0.0', '192.168.1.5', '127.0.0.2', 'localhost'):
        with pytest.raises(config.Bad, match='127.0.0.1 only'): settings(t, host=host)
    with pytest.raises(config.Bad, match='runs folder does not exist'): settings(t, host='127.0.0.1', runs=str(t / 'nope'))

def test_child_env_is_clean(setup):
    s = settings(setup)
    dirty = {'PATH': '/usr/bin:/bin', 'HOME': '/h', 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8', 'TMPDIR': '/t', 'MODEL': 'openai/gpt-5',
             'REPLY': 'r.txt', 'FROM': 'v8-g1', 'KEEP': '1', 'RUNS_DIR': '/x', 'RUN_DIR': '/y', 'INTAKE': 'off', 'OCR': 'off', 'FORCE_OCR': '1',
             'MAX_TOKENS': '9', 'VERAPDF': 'off', 'OPENROUTER_API_KEY': 'sk-secret', 'AUTO': '1', 'PYTHONPATH': '/p'}
    env = config.child_env(s, {'REVIEW': '1'}, environ=dirty)
    assert set(env) == {'PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR', 'VERAPDF', 'PYTHONUNBUFFERED', 'REVIEW'}
    assert env['VERAPDF'] == s['tools']['VERAPDF'] and env['PATH'].split(os.pathsep)[0] == os.path.dirname(sys.executable)
    with pytest.raises(ValueError): config.child_env(s, {'MODEL': 'x'}, environ=dirty)

# ------------------------------------------------------------------ setup check
def test_setup_check_needs_a_verapdf_version_line(setup):
    s = settings(setup)
    v = {x['id']: x for x in checks.check(s)}['verapdf']
    assert v['ok'] and v['detail'] == 'veraPDF 1.30.3' and v['required']
    s = settings(setup, tools={'VERAPDF': stub_vera(str(setup), answer='something else')})
    v = {x['id']: x for x in checks.check(s)}['verapdf']
    assert not v['ok'] and 'install.sh' in v['fix']

# ------------------------------------------------------------------ jobs
def fake(t, s, run, secs=0.5, tag='', **kw):
    out = str(t / 'times.txt')
    return jobs.create(s['jobs'], 'apply', run, [sys.executable, str(t / 'bin' / 'fakejob.py'), out, str(secs), tag], config.child_env(s, kw.pop('env_set', None)), **kw)

def wait(pred, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        if pred(): return True
        time.sleep(0.1)
    return False

def test_job_runs_writes_its_log_and_exit(setup):
    s = settings(setup)
    j = fake(setup, s, 'a/r', 0.1, env_set={'REVIEW': 'fail'})
    jobs.tick(s['jobs'], s)
    assert wait(lambda: jobs.load(s['jobs'], j['id'])['status'] == 'failed')
    j = jobs.load(s['jobs'], j['id'])
    assert j['exit'] == 3 and j['ended'] and j['child_pid']
    text, nxt = jobs.read_log(s['jobs'], j['id'])
    assert text.startswith(f'job {j["id"]}: ') and '▶ step one\n' in text and nxt == len(text.encode())
    assert jobs.read_log(s['jobs'], j['id'], nxt) == ('', nxt)

def test_the_child_gets_exactly_the_recorded_environment(setup, monkeypatch):
    for k, v in {'MODEL': 'openai/gpt-5', 'REPLY': 'x', 'VERAPDF': 'off', 'OPENROUTER_API_KEY': 'sk-secret'}.items(): monkeypatch.setenv(k, v)
    s = settings(setup)
    out = str(setup / 'env.json')
    j = jobs.create(s['jobs'], 'apply', 'a/r', [sys.executable, str(setup / 'bin' / 'envdump.py'), out], config.child_env(s, {'OCR_LANG': 'eng'}), env_set={'OCR_LANG': 'eng'})
    jobs.tick(s['jobs'], s)
    assert wait(lambda: jobs.load(s['jobs'], j['id'])['status'] == 'done')
    got = json.load(open(out)); rec = jobs.load(s['jobs'], j['id'])['env']
    assert {k: v for k, v in got.items() if k != '__CF_USER_TEXT_ENCODING'} == rec      # macOS adds that one to every process
    assert not {'MODEL', 'REPLY', 'OPENROUTER_API_KEY'} & set(got) and got['VERAPDF'] == s['tools']['VERAPDF'] and got['OCR_LANG'] == 'eng'

def test_one_job_per_run_and_a_held_lock_refuse(setup):
    s = settings(setup)
    R = setup / 'runs' / 'a' / 'r'; (R / 'reviews').mkdir(parents=True)
    fake(setup, s, 'a/r', R=str(R))
    with pytest.raises(ValueError, match='already waiting: apply'): fake(setup, s, 'a/r', R=str(R))
    R2 = setup / 'runs' / 'b' / 'r'; (R2 / 'reviews').mkdir(parents=True)
    (R2 / 'reviews' / '.lock').write_text(json.dumps({'pid': os.getpid(), 'since': 'x', 'what': 'reopen'}))
    with pytest.raises(ValueError, match=f'another review of this run is running \\(process {os.getpid()}, reopen'): fake(setup, s, 'b/r', R=str(R2))
    p = subprocess.Popen([sys.executable, '-c', 'pass']); p.wait()                        # a lock left by an ended process
    (R2 / 'reviews' / '.lock').write_text(json.dumps({'pid': p.pid, 'since': 'x', 'what': 'reopen'}))
    assert fake(setup, s, 'b/r', R=str(R2))['status'] == 'queued'

def test_max_jobs_holds_across_two_dispatchers(setup):
    s = settings(setup, max_jobs=2)
    ids = [fake(setup, s, f'run{i}/x', 0.6, tag=str(i))['id'] for i in range(8)]
    loop = ('import sys, time; sys.path.insert(0, sys.argv[1]); from webapp import config, jobs\n'
            's = config.load(sys.argv[2], environ={})\nend = time.time() + 12\n'
            'while time.time() < end and any(j["status"] in ("queued", "running") for j in jobs.all_jobs(s["jobs"])):\n'
            '    jobs.tick(s["jobs"], s)\n')
    ps = [subprocess.Popen([sys.executable, '-c', loop, HERE, str(setup / 'app.json')], env=dict(os.environ, VERAPDF=s['tools']['VERAPDF'])) for _ in range(2)]
    for p in ps: p.wait(timeout=60)
    assert all(jobs.load(s['jobs'], i)['status'] == 'done' for i in ids)
    ev = sorted((float(t), k) for k, t, _ in (l.split() for l in open(setup / 'times.txt')))
    live = peak = 0
    for _, k in ev: live += 1 if k == 'start' else -1; peak = max(peak, live)
    assert peak == 2
    starts = [int(l.split()[2]) for l in open(setup / 'times.txt') if l.startswith('start')]
    assert set(starts[:2]) == {0, 1} and set(starts[2:4]) == {2, 3}                     # oldest first (a pair starts together)

def test_liveness_is_the_process_group(setup):
    s = settings(setup)
    j = fake(setup, s, 'a/r', 30)
    jobs.tick(s['jobs'], s)
    assert wait(lambda: (jobs.load(s['jobs'], j['id']) or {}).get('child_pid'))
    j = jobs.load(s['jobs'], j['id'])
    os.kill(j['pid'], signal.SIGKILL); time.sleep(0.3)                                   # the wrapper is gone, its child is not
    jobs.tick(s['jobs'], s)
    assert jobs.load(s['jobs'], j['id'])['status'] == 'running'
    os.killpg(j['pgid'], signal.SIGKILL); time.sleep(0.3)
    jobs.tick(s['jobs'], s)
    assert jobs.load(s['jobs'], j['id'])['status'] == 'interrupted'

def test_a_reused_group_id_is_not_mistaken_for_the_job(setup):
    s = settings(setup)
    j = fake(setup, s, 'a/r')
    jobs.update(s['jobs'], j['id'], status='running', pid=os.getpid(), pgid=os.getpgrp(), started='x')   # pytest's own group: alive, not the job
    jobs.tick(s['jobs'], s)
    assert jobs.load(s['jobs'], j['id'])['status'] == 'interrupted'

def test_ctrl_c_reaches_the_command_and_the_wrapper_records_it(setup):
    s = settings(setup)
    j = fake(setup, s, 'a/r', 30)
    jobs.tick(s['jobs'], s)
    assert wait(lambda: (jobs.load(s['jobs'], j['id']) or {}).get('child_pid'))
    assert jobs.interrupt(s['jobs'], j['id'])
    assert wait(lambda: jobs.load(s['jobs'], j['id'])['status'] == 'failed')
    j = jobs.load(s['jobs'], j['id'])
    assert j['exit'] in (-signal.SIGINT, 1, 130) and j['ended']                          # the command got KeyboardInterrupt
    assert 'KeyboardInterrupt' in jobs.read_log(s['jobs'], j['id'])[0]

def test_then_and_restart(setup):
    s = settings(setup)
    nxt = {'kind': 'review', 'argv': [sys.executable, str(setup / 'bin' / 'fakejob.py'), str(setup / 'times.txt'), '0', 'then'], 'env': config.child_env(s), 'counted': False}
    j = fake(setup, s, 'a/r', 0.1, then=nxt)
    paid = fake(setup, s, 'b/r', paid=True); free = fake(setup, s, 'c/r')
    jobs.recover(s['jobs'])                                                              # what the app does at start
    assert jobs.load(s['jobs'], paid['id'])['status'] == 'needs-spend' and jobs.load(s['jobs'], free['id'])['status'] == 'queued'
    assert wait(lambda: (jobs.tick(s['jobs'], s), jobs.load(s['jobs'], j['id']).get('then_job'))[1])
    t = jobs.load(s['jobs'], jobs.load(s['jobs'], j['id'])['then_job'])
    assert t['kind'] == 'review' and t['run'] == 'a/r' and t['after'] == j['id']
    assert wait(lambda: (jobs.tick(s['jobs'], s), jobs.load(s['jobs'], t['id'])['status'] == 'done')[1])

# ------------------------------------------------------------------ the server
@pytest.fixture
def app(setup):
    """The app started as a person starts it, on a folder with a finished run, a batch, a run with no review.html, and a
    symlink out of the runs folder."""
    t = setup; runs = t / 'runs'
    R = runs / 'book' / 'r1'; (R / 'reviews' / 'versions' / '001').mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'output': 'book_remediated.pdf'}}))
    (R / 'review.html').write_text('<!doctype html><title>r1</title><a href="review.md">review.md</a>')
    (R / 'review.md').write_text('# Review'); (R / 'book_remediated.pdf').write_bytes(b'%PDF-1.7 result'); (R / 'secret.txt').write_text('no')
    (R / 'reviews' / 'basis.json').write_text('{}')
    V = R / 'reviews' / 'versions' / '001'; (V / 'record.json').write_text(json.dumps({'document': {'output': 'book_remediated.pdf'}})); (V / 'review.md').write_text('old')
    N = runs / 'old' / 'r0'; N.mkdir(parents=True); (N / 'record.json').write_text('{}'); (N / 'review.md').write_text('# Old')
    B = runs / 'batches' / 'b1'; (B / 'x').mkdir(parents=True); (B / 'summary.html').write_text('<a href="x/review.html">x</a>'); (B / 'x' / 'record.json').write_text('{}')
    out = t / 'outside'; out.mkdir(); (out / 'record.json').write_text('{}'); (out / 'review.html').write_text('outside'); os.symlink(out, runs / 'link')
    (t / '.env').write_text('OPENROUTER_API_KEY=sk-secret')
    port = json.loads((t / 'app.json').read_text())['port']
    env = {k: v for k, v in os.environ.items() if k != 'VERAPDF'}
    p = subprocess.Popen([sys.executable, 'app.py', '--config', str(t / 'app.json'), '--no-browser'], cwd=HERE, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ok = wait(lambda: p.poll() is not None or get(port, '/api/ping')[0] == 200, 60)
    if p.poll() is not None or not ok: pytest.fail(p.stdout.read())
    yield {'port': port, 't': t, 'R': R, 'env': env}
    p.send_signal(signal.SIGINT)
    try: p.wait(timeout=10)
    except subprocess.TimeoutExpired: p.kill()

def get(port, path, host=None, method='GET', headers=None, body=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        c.putheader('Host', host or f'127.0.0.1:{port}')
        for k, v in (headers or {}).items(): c.putheader(k, v)
        if body is not None: c.putheader('Content-Length', str(len(body)))
        c.endheaders(body.encode() if body is not None else None)
        r = c.getresponse(); return r.status, r.read(), dict(r.getheaders())
    except OSError: return None, b'', {}
    finally: c.close()

def test_the_run_page_is_review_html_as_on_disk(app):
    before = sha(app['R'] / 'review.html')
    st, b, h = get(app['port'], '/run/book/r1/')
    assert st == 200 and b == (app['R'] / 'review.html').read_bytes() and h['Content-Type'].startswith('text/html')
    assert sha(app['R'] / 'review.html') == before
    assert get(app['port'], '/run/book/r1')[2].get('Location') == '/run/book/r1/'

@pytest.mark.parametrize('path,code', [
    ('/run/book/r1/review.md', 200), ('/run/book/r1/book_remediated.pdf', 200), ('/run/book/r1/reviews/versions/001/review.md', 200),
    ('/run/book/r1/secret.txt', 404), ('/run/book/r1/record.json', 404), ('/run/book/r1/reviews/basis.json', 404),
    ('/run/book/r1/reviews/versions/001/record.json', 404), ('/run/../.env', 404), ('/run/book/..%2f..%2f.env', 404),
    ('/run/book/%2e%2e/book/r1/', 404), ('/run/%2e%2e/.env', 404), ('/run/book/r1/%2e%2e%2fsecret.txt', 404), ('/run/link/', 404),
    ('/run/.app/jobs/', 404), ('/run/book/r1/..\\secret.txt', 404), ('/.env', 404), ('/run/book/r1/ocr', 404)])
def test_only_listed_files_inside_runs_are_served(app, path, code):
    assert get(app['port'], path)[0] == code

def test_requests_must_come_from_the_app(app):
    assert get(app['port'], '/api/ping', host='evil.example:80')[0] == 403
    assert get(app['port'], '/api/ping', host=f'localhost:{app["port"]}')[0] == 200
    js = {'Content-Type': 'application/json'}
    assert get(app['port'], '/api/x', method='POST', headers={**js, 'Origin': 'http://evil.example'}, body='{}')[0] == 403
    assert get(app['port'], '/api/x', method='POST', headers={'Content-Type': 'text/plain'}, body='{}')[0] == 415

def test_batch_route_and_a_run_with_no_dashboard(app):
    st, b, _ = get(app['port'], '/batch/b1/')
    assert st == 200 and b'x/review.html' in b
    assert get(app['port'], '/batch/b1/x/review.html')[2].get('Location') == '/run/batches/b1/x/'
    assert get(app['port'], '/run/batches/b1/summary.html')[2].get('Location') == '/batch/b1/'
    st, b, _ = get(app['port'], '/run/old/r0/')
    assert st == 200 and b'has no dashboard' in b and b'href="review.md"' in b and b'None' not in b and b'unknown' not in b

def test_ping_jobs_and_a_second_start(app):
    st, b, _ = get(app['port'], '/api/ping')
    assert st == 200 and json.loads(b)['root'] == os.path.dirname(HERE)
    assert json.loads(get(app['port'], '/api/setup')[1])[1]['detail'] == 'veraPDF 1.30.3'
    assert json.loads(get(app['port'], '/api/run/book/r1')[1])['review_html'] is True
    cfg = str(app['t'] / 'app.json')
    r = subprocess.run([sys.executable, 'app.py', '--config', cfg, '--no-browser'], cwd=HERE, env=app['env'], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and 'already running' in r.stdout
    other = app['t'] / 'other.json'; d = json.loads(open(cfg).read()); d['max_jobs'] = 5; other.write_text(json.dumps(d))
    r = subprocess.run([sys.executable, 'app.py', '--config', str(other), '--no-browser'], cwd=HERE, env=app['env'], capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and 'other settings' in r.stderr

def test_the_app_refuses_to_start_without_verapdf(setup):
    env = {k: v for k, v in os.environ.items() if k != 'VERAPDF'}
    r = subprocess.run([sys.executable, 'app.py', '--config', str(setup / 'app.json'), '--no-browser'], cwd=HERE, env=dict(env, VERAPDF='off'),
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and 'VERAPDF=off' in r.stderr
    settings(setup, tools={'VERAPDF': stub_vera(str(setup), answer='nope')})
    r = subprocess.run([sys.executable, 'app.py', '--config', str(setup / 'app.json'), '--no-browser'], cwd=HERE, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and 'veraPDF missing' in r.stderr
