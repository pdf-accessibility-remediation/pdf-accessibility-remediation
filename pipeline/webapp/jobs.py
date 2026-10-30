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

def load(J, jid):
    try: return json.load(open(path(J, jid), encoding='utf-8'))
    except (OSError, ValueError): return None

def save(J, job):
    p = path(J, job['id']); tmp = p + '.tmp'
    json.dump(job, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, p)

def all_jobs(J):
    if not os.path.isdir(folder(J)): return []
    return [j for j in (load(J, n[:-5]) for n in sorted(os.listdir(folder(J))) if n.endswith('.json')) if j]

def update(J, jid, **kw):
    with locked(J):
        job = load(J, jid)
        if job is None: return None
        job.update(kw); save(J, job); return job

# ------------------------------------------------------------------ liveness
def _marks(job):
    m = ['webapp/jobrun.py']
    for a in job['argv'][:3]:
        if a.endswith(('.py', '.sh')): m.append(os.path.basename(a))
    return m

def group_alive(job):
    pg = job.get('pgid')
    if not pg: return False
    try: os.killpg(pg, 0)
    except ProcessLookupError: return False
    except PermissionError: pass
    try: out = subprocess.run(['ps', '-A', '-o', 'pgid=,command='], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired): return True                # cannot tell: never call a live job interrupted
    marks = _marks(job)
    for line in out.splitlines():
        g, _, cmd = line.strip().partition(' ')
        if g == str(pg) and any(m in cmd for m in marks): return True
    return False

# ------------------------------------------------------------------ the run's own state
def review_past_finish(R, since=None):
    """A review child is past Finish (it records the session, then applies): never signal it from then on. From disk only:
    the review's review.json (written when Finish is accepted), the work or promotion folder of a re-apply, or a session
    finished since the job started."""
    rv = os.path.join(R, 'reviews')
    if any(os.path.exists(os.path.join(rv, n)) for n in ('review.json', 'work', 'promoting.json')): return True
    if not os.path.exists(os.path.join(R, 'record.json')) and os.path.exists(os.path.join(R, 'review.json')): return True   # a first review
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
        job = {'id': jid, 'kind': kind, 'run': run, 'argv': list(argv), 'env': env, 'env_set': env_set or {}, 'counted': counted,
               'then': then, 'paid': paid, 'status': 'queued', 'created': now(), 'started': None, 'ended': None, 'exit': None,
               'pid': None, 'pgid': None, 'log': os.path.basename(log_path(J, jid)), **extra}
        save(J, job)
        return job

def counts(job, runs):
    """A running job takes one of max_jobs: work jobs always, a review job once it is past Finish (it is applying)."""
    if job.get('counted'): return True
    return job['kind'] == 'review' and review_past_finish(os.path.join(runs, job['run']), job.get('started'))

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
            if j['status'] == 'running' and not j.get('ended') and not group_alive(j):
                j.update(status='interrupted', ended=now()); save(J, j)
            if j['status'] == 'done' and j.get('then') and not j.get('then_job'):
                t = j['then']
                nxt = {'id': f'{datetime.datetime.now():%Y%m%d-%H%M%S-%f}-{t["kind"]}', 'kind': t['kind'], 'run': j['run'], 'argv': t['argv'],
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
    """(text, next offset) from byte offset; whole lines only while the job may still write."""
    try:
        with open(log_path(J, jid), 'rb') as f:
            f.seek(max(0, int(offset))); b = f.read(limit)
    except OSError: return '', offset
    job = load(J, jid) or {}
    if job.get('status') in ACTIVE and b and not b.endswith(b'\n'):
        cut = b.rfind(b'\n'); b = b[:cut + 1] if cut >= 0 else b''
    return b.decode('utf-8', 'replace'), int(offset) + len(b)

def interrupt(J, jid):
    """Ctrl+C (SIGINT) to a job's process group, as the terminal's Ctrl+C. The caller decides whether that is allowed."""
    job = load(J, jid)
    if not job or job['status'] != 'running' or not group_alive(job): return False
    try: os.killpg(job['pgid'], signal.SIGINT); return True
    except OSError: return False
