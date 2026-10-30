"""webapp/jobs.py: the app's jobs, kept on disk only, so a stopped and restarted app loses nothing.

    <jobs>/jobs/<id>.json   kind, run, argv, the child's full environment, status, times, exit, pid/pgid, then, paid
    <jobs>/jobs/<id>.log    the command's own output (the command writes straight into it: no pipe through the app)
    <jobs>/dispatch.lock    flock around every read-modify-write of the job files, so two app servers on one jobs
                            folder count and claim under one lock (max_jobs holds across both)

Status: queued → running → done | failed (exit ≠ 0) | interrupted (the whole process group is gone without an exit
recorded: a reboot, or a kill). A paid job (B) still queued when the app starts goes to needs-spend: a paid call never
starts from a click made before a restart.

Each job runs under webapp/jobrun.py, started in a new session (its own process group), so Ctrl+C on the app does not
reach it. Liveness is the process group: os.killpg(pgid, 0), and a process in that group whose command line is the
wrapper or the job's own script (a reused process-group id is not mistaken for the job).
"""
import os, sys, json, time, fcntl, signal, datetime, subprocess, contextlib
from . import logs, config

ACTIVE = ('queued', 'running')
WRAPPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobrun.py')
PIPELINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def now(): return datetime.datetime.now().isoformat(timespec='seconds')
def folder(J): return os.path.join(J, 'jobs')
def path(J, jid): return os.path.join(folder(J), f'{jid}.json')
def log_path(J, jid): return os.path.join(folder(J), f'{jid}.log')

@contextlib.contextmanager
def locked(J):
    os.makedirs(folder(J), exist_ok=True)
    with open(os.path.join(J, 'dispatch.lock'), 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)

def _read(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def load(J, jid):
    """A job by id. The file is picked from the jobs folder's own listing (an id from a request is never joined onto a
    path), so the job and its id come from the disk."""
    p = config.entry(folder(J), f'{jid}.json')
    return _read(p) if p else None

def save(J, job):
    p = path(J, job['id']); tmp = p + '.tmp'
    json.dump(job, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, p)

def all_jobs(J):
    F = folder(J)
    if not os.path.isdir(F): return []
    return [j for j in (_read(os.path.join(F, n)) for n in sorted(os.listdir(F)) if n.endswith('.json')) if j]

def update(J, jid, **kw):
    with locked(J):
        job = load(J, jid)
        if job is None: return None
        job.update(kw); save(J, job); return job

# ------------------------------------------------------------------ liveness
def _marks(J, job):
    """What a process of this job has in its command line, each a tuple of parts that must all be there: the wrapper
    with its jobs folder and job id; the command's script with the run folder (when the command names it)."""
    m = [(f'webapp/jobrun.py {J} {job["id"]}',)]
    for a in job['argv'][:3]:
        if a.endswith(('.py', '.sh')): m.append((os.path.basename(a), job['dir']) if job.get('dir') and job['dir'] in job['argv'] else (os.path.basename(a),))
    return m

def group_alive(J, job):
    pg = job.get('pgid')
    if not pg: return False
    try: os.killpg(pg, 0)
    except ProcessLookupError: return False
    except PermissionError: pass
    try: out = subprocess.run(['ps', '-A', '-ww', '-o', 'pgid=,command='], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired): return True                # cannot tell: never call a live job interrupted
    marks = _marks(J, job)
    for line in out.splitlines():
        g, _, cmd = line.strip().partition(' ')
        if g == str(pg) and any(all(p in cmd for p in m) for m in marks): return True
    return False

# ------------------------------------------------------------------ the run's own state
def _at(since):
    try: return datetime.datetime.fromisoformat(since).timestamp() if since else None
    except ValueError: return None

def review_past_finish(R, since=None):
    """A review child is past Finish (it records the session, then applies): never signal it from then on. From disk only,
    and only what appeared since the job started (a failed apply leaves reviews/work/ behind; an old review.json is not
    this review's Finish): the review's review.json (written when Finish is accepted), the work folder or promotion
    marker of a re-apply, or a session finished since then."""
    if not R: return True                               # the run is not known: never signal
    t = _at(since)
    def new(p):
        try: return os.path.exists(p) and (t is None or os.path.getmtime(p) >= t)
        except OSError: return False
    rv = os.path.join(R, 'reviews')
    if any(new(os.path.join(rv, n)) for n in ('review.json', 'work', 'promoting.json')): return True
    if not os.path.exists(os.path.join(R, 'record.json')) and new(os.path.join(R, 'review.json')): return True   # a first review
    sd = os.path.join(rv, 'sessions')
    if os.path.isdir(sd):
        ns = sorted(n for n in os.listdir(sd) if n[:3].isdigit() and n.endswith('.json') and not n.endswith('.workorder.json'))
        if ns:
            try: s = json.load(open(os.path.join(sd, ns[-1]), encoding='utf-8'))
            except (OSError, ValueError): s = {}
            if s.get('status') in ('finished', 'applied') and (since is None or (s.get('finished') or '') >= since): return True
    return False

def lock_holder(R):
    """reviews/.lock held by a live process: (pid, what, since); else None (a lock left by an ended process is not held)."""
    p = os.path.join(R, 'reviews', '.lock')
    try: d = json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None
    try: os.kill(int(d.get('pid')), 0)
    except ProcessLookupError: return None
    except PermissionError: pass
    except (TypeError, ValueError): return None
    return d.get('pid'), d.get('what'), d.get('since')

def busy(J, run, R):
    """Why nothing new may start for this run now, or None."""
    h = lock_holder(R)
    if h: return f'another review of this run is running (process {h[0]}, {h[1]}, since {h[2]})'
    for j in all_jobs(J):
        if j['run'] == run and j['status'] in ACTIVE + ('needs-spend',):
            return f'a job for this run is already {"waiting" if j["status"] != "running" else "running"}: {j["kind"]}, since {j.get("started") or j["created"]}'
    return None

# ------------------------------------------------------------------ queue
def create(J, kind, run, argv, env, env_set=None, counted=True, then=None, paid=False, R=None, **extra):
    """A queued job, refused (ValueError with the reason) when the run is busy. env is the child's whole environment
    (config.child_env); env_set the variables the job itself set."""
    with locked(J):
        if R is not None:
            why = busy(J, run, R)
            if why: raise ValueError(why)
        jid = f'{datetime.datetime.now():%Y%m%d-%H%M%S-%f}-{kind}'
        job = {'id': jid, 'kind': kind, 'run': run, 'dir': os.path.abspath(R) if R is not None else None, 'argv': list(argv), 'env': env,
               'env_set': env_set or {}, 'counted': counted, 'then': then, 'paid': paid, 'status': 'queued', 'created': now(), 'started': None,
               'ended': None, 'exit': None, 'pid': None, 'pgid': None, 'log': os.path.basename(log_path(J, jid)), **extra}
        save(J, job)
        return job

def run_dir(job, runs=None):
    return job.get('dir') or (os.path.join(runs, *job['run'].split('/')) if runs else None)

def counts(job, runs):
    """A running job takes one of max_jobs: work jobs always, a review job once it is past Finish (it is applying)."""
    if job.get('counted'): return True
    return job['kind'] == 'review' and review_past_finish(run_dir(job, runs), job.get('started'))

def _start(J, job):
    lp = log_path(J, job['id'])
    open(lp, 'ab').close()
    p = subprocess.Popen([sys.executable, WRAPPER, J, job['id']], cwd=PIPELINE, env=job['env'], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    job.update(status='running', started=now(), pid=p.pid, pgid=p.pid); save(J, job)

def tick(J, s):
    """One pass of the dispatcher: mark ended and interrupted jobs, queue each finished job's `then`, start queued jobs
    oldest first while max_jobs allows (one job at a time per run). Reads and writes only the job files."""
    with locked(J):
        jobs = all_jobs(J)
        for j in jobs:
            if j['status'] == 'running' and not j.get('ended') and not group_alive(J, j):
                j.update(status='interrupted', ended=now()); save(J, j)
            if j['kind'] == 'review' and j['status'] == 'running' and not j.get('url'):       # the review page is up: keep its URL
                u = logs.review_url(read_log(J, j['id'])[0])
                if u: j['url'] = u; save(J, j)
            if j['status'] == 'done' and j.get('then') and not j.get('then_job'):
                t = j['then']
                nxt = {'id': f'{datetime.datetime.now():%Y%m%d-%H%M%S-%f}-{t["kind"]}', 'kind': t['kind'], 'run': j['run'], 'dir': j.get('dir'), 'argv': t['argv'],
                       'env': t['env'], 'env_set': t.get('env_set') or {}, 'counted': t.get('counted', True), 'then': t.get('then'),
                       'paid': t.get('paid', False), 'status': 'queued', 'created': now(), 'started': None, 'ended': None, 'exit': None,
                       'pid': None, 'pgid': None, 'after': j['id'], **(t.get('extra') or {})}
                nxt['log'] = os.path.basename(log_path(J, nxt['id']))
                save(J, nxt); j['then_job'] = nxt['id']; save(J, j); jobs.append(nxt)
        running = [j for j in jobs if j['status'] == 'running']
        n = sum(1 for j in running if counts(j, s['runs']))
        busy_runs = {j['run'] for j in running}
        for j in sorted((j for j in jobs if j['status'] == 'queued'), key=lambda j: j['id']):
            if j['run'] in busy_runs: continue
            if j.get('counted', True):
                if n >= s['max_jobs']: continue
                n += 1
            _start(J, j); busy_runs.add(j['run'])

def recover(J):
    """At app start: a paid job still queued needs its Spend click again."""
    with locked(J):
        for j in all_jobs(J):
            if j['status'] == 'queued' and j.get('paid'):
                j.update(status='needs-spend', note='the app was restarted before this paid job started: Spend again on a fresh estimate'); save(J, j)

def position(J, jid):
    """1-based place in line among queued jobs, or None."""
    q = [j['id'] for j in all_jobs(J) if j['status'] == 'queued']
    return q.index(jid) + 1 if jid in q else None

def read_log(J, jid, offset=0, limit=256 * 1024):
    """(text, next offset) from byte offset; whole lines only while the job may still write. jid is a loaded job's own id
    (from the disk, never from a request: /api/job/<id> finds the job with load() first)."""
    lp = os.path.realpath(log_path(J, jid))
    if not lp.startswith(os.path.realpath(folder(J)) + os.sep): return '', offset
    try:
        with open(lp, 'rb') as f:
            f.seek(max(0, int(offset))); b = f.read(limit)
    except OSError: return '', offset
    job = load(J, jid) or {}
    if job.get('status') in ACTIVE and b and not b.endswith(b'\n'):
        cut = b.rfind(b'\n'); b = b[:cut + 1] if cut >= 0 else b''
    try: b.decode('utf-8')
    except UnicodeDecodeError as e:                     # a character cut at the read limit: leave it for the next read
        if e.start >= len(b) - 3: b = b[:e.start]
    return b.decode('utf-8', 'replace'), int(offset) + len(b)

def interrupt(J, jid, runs=None):
    """Ctrl+C (SIGINT) to a job's process group, as the terminal's Ctrl+C. (True, None), or (False, why). A review job
    past Finish is never signalled (it is recording its session or applying it); the check is here, so no caller can
    skip it."""
    job = load(J, jid)
    if not job or job['status'] != 'running' or not group_alive(J, job): return False, 'the job is not running'
    if job['kind'] == 'review' and review_past_finish(run_dir(job, runs), job.get('started')):
        return False, 'this review is past Finish and is being applied: it cannot be stopped now'
    try: os.killpg(job['pgid'], signal.SIGINT); return True, None
    except OSError as e: return False, f'the job could not be reached ({e})'
