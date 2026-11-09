"""webapp/config.py: the app's settings, from one place, and the environment its children get.

Layers, later wins:  webapp/settings.json (committed, neutral) < webapp/settings.local.json (git-ignored, this machine:
VERAPDF, the Java path) < --config FILE < an exported VERAPDF. Relative paths are relative to pipeline/.

    host, port         where the app listens. Only a loopback address is accepted until the app has logins.
    runs, samples, uploads, jobs   the folders (jobs: the queue, logs and the dispatch lock)
    max_jobs           (3) single runs at once; a batch runs alone (nothing else counted starts while it runs: D1)
    batch_jobs         books of a batch in progress at once (batch_api.sh's JOBS, 10)
    max_books_per_batch   the most books New Batch accepts (the app only: batch_api.sh in a terminal has no cap)
    upload_max_mb      "Add a Book": the largest PDF accepted, in MB (default 1024)
    limits             dollars: per_call_usd (one AI call), per_book_usd (a book, #63), per_batch_usd (a batch); what the
                       pages compare estimates with, and the most a Spend may bind (lib/costs.py)
    tools              VERAPDF (path to the launcher) and path_prepend (folders put first on the children's PATH: Java)
    test_reply_dir     tests only, and only from --config: never from a committed or local settings file. Spend then runs
                       REPLY=<test_reply_dir>/<name>.txt instead of a paid call, and every page says "Test"
    test_batch_from    tests only, from --config only: a batch's Spend runs FROM=<label> (saved replies) instead of paid calls
    trash_dir          tests only, from --config only: where "Move to Trash" moves things instead of ~/.Trash (webapp/trash.py)

The app never runs with veraPDF off: VERAPDF=off is refused from any source.
"""
import os, sys, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))           # pipeline/webapp/
PIPELINE = os.path.dirname(HERE)                             # pipeline/
ROOT = os.path.dirname(PIPELINE)                             # the repo
FOLDERS = ('runs', 'samples', 'uploads', 'jobs')
# what a child inherits from the app's own environment (RUNS_DIR is always the app's runs folder); everything else (MODEL, REPLY, FROM, KEEP, RUN_DIR,
# INTAKE, OCR, FORCE_OCR, MAX_TOKENS, VERAPDF=off, …) is dropped, and a job adds only its own whitelisted variables
BASE_ENV = ('PATH', 'HOME', 'LANG', 'TMPDIR', 'USER', 'LOGNAME', 'SHELL')
JOB_ENV = ('REVIEW', 'AUTO', 'ESTIMATE', 'OCR_LANG', 'RUN_DIR', 'INTAKE_REUSE', 'REPLY', 'MAX_USD', 'INTAKE', 'OUT',
           'JOBS', 'BATCH_MAX_USD', 'BOOK_MAX_USD', 'RETRY', 'MODEL', 'FROM',    # #45: batches, the caps, the estimate's model
           'SUMMARY_ONLY', 'ASK_LANG',                                         # round 4: the batch summary rebuild (D3, D8), the language question (D4)
           'PAGE_READS', 'PAGE_READS_MAX_USD')                                 # #49: page readings, set by Spend from the estimate shown
# MODEL only as an anthropic/ id (the one the estimate used: 03 §5); FROM only in test mode (test_batch_from, --config);
# never FORCE_OCR (Q7: no "OCR Every Page Instead" in the app)

def entry(folder, name):
    """The path of folder's entry called `name`, taken from the folder's own listing, or None. A name from a request is
    never joined onto a path: it only picks one of the names that are already on disk."""
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.name == name: return e.path
    except OSError: pass
    return None

class Bad(Exception):
    """The settings cannot be used: the app does not start."""

def _read(path, required=False):
    if not os.path.exists(path):
        if required: raise Bad(f'no settings file: {path}')
        return {}
    try: d = json.load(open(path, encoding='utf-8'))
    except ValueError as e: raise Bad(f'{path} is not valid JSON: {e}')
    if not isinstance(d, dict): raise Bad(f'{path} is not a JSON object')
    return d

def _merge(a, b):
    out = dict(a)
    for k, v in b.items(): out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out

def load(config=None, base=HERE, environ=None):
    """The merged settings, checked, with absolute folders. Raises Bad with the reason."""
    environ = os.environ if environ is None else environ
    files = [os.path.join(base, 'settings.json'), os.path.join(base, 'settings.local.json')]
    if config and os.path.realpath(config) in {os.path.realpath(f) for f in files}:
        raise Bad(f'--config {config} is one of the settings files the app always reads: give a file of your own')
    layers = [('webapp/settings.json', _read(files[0], required=True), False), ('webapp/settings.local.json', _read(files[1]), False)]
    if config: layers.append((config, _read(os.path.abspath(config), required=True), True))
    s = {}
    for name, d, given in layers:
        for k in ('test_reply_dir', 'test_batch_from', 'trash_dir'):
            if k in d and not given: raise Bad(f'{k} is set in {name}: it may only come from --config')
        if str((d.get('tools') or {}).get('VERAPDF', '')).strip().lower() == 'off': raise Bad(f'{name} sets VERAPDF=off: the app always runs veraPDF')
        s = _merge(s, d)
    if 'VERAPDF' in environ:
        if environ['VERAPDF'].strip().lower() == 'off': raise Bad('VERAPDF=off is exported: the app always runs veraPDF (unset it, or export the launcher path)')
        s.setdefault('tools', {})['VERAPDF'] = environ['VERAPDF']
    if s.get('host') != '127.0.0.1':                         # the pages check Host against 127.0.0.1 / localhost
        raise Bad(f'host {s.get("host")!r}: the app has no logins yet, so it listens on 127.0.0.1 only')
    for k in ('port', 'max_jobs'):
        if not isinstance(s.get(k), int) or isinstance(s.get(k), bool) or s[k] < 1: raise Bad(f'{k} must be a whole number above 0: {s.get(k)!r}')
    for k, dflt in (('batch_jobs', 10), ('upload_max_mb', 1024), ('max_books_per_batch', 50)):
        s.setdefault(k, dflt)
        if not isinstance(s[k], int) or isinstance(s[k], bool) or s[k] < 1: raise Bad(f'{k} must be a whole number above 0: {s[k]!r}')
    lim = s.setdefault('limits', {})
    if not isinstance(lim, dict): raise Bad('limits must be an object: {"per_call_usd": 2, "per_book_usd": 5, "per_batch_usd": 5}')
    for k, v in lim.items():
        if k not in ('per_call_usd', 'per_book_usd', 'per_batch_usd'): raise Bad(f'limits: unknown key {k!r}')
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 < v <= 100: raise Bad(f'limits.{k} must be a number of dollars above 0 and at most 100: {v!r}')
    for k in FOLDERS:
        if not isinstance(s.get(k), str) or not s[k]: raise Bad(f'{k} must name a folder')
        s[k] = os.path.normpath(os.path.join(PIPELINE, os.path.expanduser(s[k])))
    if not os.path.isdir(s['runs']): raise Bad(f'the runs folder does not exist: {s["runs"]}')
    if not os.path.isdir(s['samples']): raise Bad(f'the samples folder does not exist: {s["samples"]}')
    t = s.setdefault('tools', {})
    t['VERAPDF'] = os.path.expanduser(str(t.get('VERAPDF') or ''))
    t['path_prepend'] = [os.path.expanduser(p) for p in t.get('path_prepend') or []]
    if s.get('trash_dir'): s['trash_dir'] = os.path.normpath(os.path.join(PIPELINE, os.path.expanduser(s['trash_dir'])))
    if s.get('test_reply_dir'): s['test_reply_dir'] = os.path.normpath(os.path.join(PIPELINE, os.path.expanduser(s['test_reply_dir'])))   # as the folders
    s['sha'] = fingerprint(s)
    return s

CODE = ('app.py', 'webapp', 'review', 'lib/titles.py', 'lib/glance.py')   # what the running app is made of (its pages included)

def code_fingerprint():
    """The app's code on disk now: sha256 over app.py, every .py/.js/.css/.html file in webapp/ and review/, and the lib/
    modules they import for what the pages show (titles.py, glance.py). A running
    app keeps the one it started with, so a second start can tell that the code changed under it."""
    h = hashlib.sha256()
    for c in CODE:
        p = os.path.join(PIPELINE, c)
        files = [p] if os.path.isfile(p) else sorted(os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs
                                                     if f.endswith(('.py', '.js', '.css', '.html')) and '__pycache__' not in d)
        for f in files:
            h.update(os.path.relpath(f, PIPELINE).encode() + b'\0' + open(f, 'rb').read() + b'\0')
    return h.hexdigest()[:16]

def fingerprint(s):
    """Same folders and tools = the same app (the port is left out: --port starts a second server on purpose)."""
    return hashlib.sha256(json.dumps({k: v for k, v in s.items() if k not in ('port', 'sha')}, sort_keys=True).encode()).hexdigest()[:16]

def child_env(s, job_env=None, environ=None):
    """A child's whole environment: the base variables, PATH with the venv's bin/ and the settings' folders first,
    VERAPDF from the settings, and the job's own whitelisted variables. Nothing else from the app's environment."""
    environ = os.environ if environ is None else environ
    env = {k: environ[k] for k in BASE_ENV if k in environ}
    env.update({k: v for k, v in environ.items() if k.startswith('LC_')})
    env['PATH'] = os.pathsep.join([os.path.dirname(sys.executable)] + s['tools']['path_prepend'] + [environ.get('PATH', '/usr/bin:/bin')])
    if s['tools']['VERAPDF']: env['VERAPDF'] = s['tools']['VERAPDF']
    env['PYTHONUNBUFFERED'] = '1'                            # the log fills as the tools print
    env['RUNS_DIR'] = os.path.abspath(s['runs'])             # run_api.sh and batch_api.sh write where the app reads (a --config's own runs folder too)
    # page readings (#49): an estimate prices them (page_reads_estimate.json, in lib/costs.py's total); only a Spend that
    # showed them sends them (PAGE_READS=1 and PAGE_READS_MAX_USD from spend.py); every other job reads no pages
    env['PAGE_READS'] = '1' if 'ESTIMATE' in (job_env or {}) else 'off'
    for k, v in (job_env or {}).items():
        if k not in JOB_ENV: raise ValueError(f'{k} is not a variable a job may set')
        if k == 'MODEL' and not str(v).startswith('anthropic/'): raise ValueError(f'MODEL {v!r}: the app sends only to a Claude model whose cost it can check')
        if k == 'FROM' and not s.get('test_batch_from'): raise ValueError('FROM is for test mode only (test_batch_from, from --config)')
        env[k] = str(v)
    return env
