"""webapp/trash.py: "Move to Trash" (#45 D8, Patrick 2026-11-06): a single run, a whole batch or chosen PDFs in it (from
My Workspace and the batch page), and a PDF added through "Add a PDF" (the PDF list). Nothing is ever deleted outright.

How a move works:
    Every item goes to the macOS Trash (~/.Trash; `trash_dir` from a --config only, for tests) with os.rename, under a
    unique name ("name", "name 2", …): never copied then deleted. Another disk is refused in plain words. Finder's
    "Put Back" doesn't know these items: docs/app.md says to drag one back to the folder the move log names.
    runs/.app/trash-log.json records each move (what, from where, to which name, when, and for a PDF its sha256), under
    runs/.app/trash.lock; the run page reads it to say an original PDF was moved.

Refused, with a plain reason, while anything affected is processing, waiting to start or waiting for a new estimate, has a
review page open, or is between "Finish Review" and its apply (review.json written, no result yet). Each run's record
lock is taken once, in path order, around its move (lib/runlock.py: not re-entrant; it is the last lock in the order).

What stays where it is: the run's job files in runs/.app/jobs (home rows come from folders, so nothing is listed for a
moved run, and its label stays taken in the app); a run's or batch's plain name moves from run-names.json into the log,
so a later run reusing the label from a terminal never shows it; the home page's cache is dropped.

    plan_run / plan_batch / plan_pdf      what a confirmation names, and the refusal if one applies now
    move_run / move_batch / move_pdf      the move (the same checks again, under the locks)
    moved_pdf(s, sha)                     the log's entry for an original PDF moved to the Trash, or None
"""
import os, re, json, errno, fcntl, datetime, contextlib
from lib import runlock, costs, release as REL
from . import jobs, books as BK, names as NM, home as HM

CONFIRM_RUN = 'The remediated PDF, its report and its review go with it.'
CONFIRM_SHIPPED = 'This run was shipped. Its record of what was shipped and who approved it goes with it.'
CONFIRM_USED = 'These runs keep their remediated PDF, report and downloads. What moving the PDF changes for each one is under its name.'
STILL_WORKS = '"Review Again" still works: the run kept its own copy.'
NEEDS_BACK = '"Review Again" will need it back.'
APPLY_NEEDS = 'Applying its reviewed decisions will need it back.'
GO_ON_NEEDS = 'Going on with this run will need it back.'
OTHER_DISK = 'The Trash is on another disk than the app\'s folders, so this can\'t be moved there. Whoever looks after the app can move it by hand.'

class Refused(Exception):
    """Nothing was moved: the reason in plain words."""

def trash_dir(s): return os.path.abspath(os.path.expanduser(s.get('trash_dir') or '~/.Trash'))
def _log_path(s): return os.path.join(s['jobs'], 'trash-log.json')
def now(): return datetime.datetime.now().isoformat(timespec='seconds')

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

@contextlib.contextmanager
def _log_lock(s):
    os.makedirs(s['jobs'], exist_ok=True)
    with open(os.path.join(s['jobs'], 'trash.lock'), 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)

def log(s, entry):
    with _log_lock(s):
        d = _load(_log_path(s)) or []
        d.append({**entry, 'at': now()})
        tmp = _log_path(s) + f'.{os.getpid()}.tmp'
        json.dump(d, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, _log_path(s))

def moved_pdf(s, sha):
    return next((e for e in reversed(_load(_log_path(s)) or []) if e.get('what') == 'pdf' and e.get('sha256') == sha), None)

def _rename(s, src, base):
    """src → the Trash, under base (then "base 2", "base 3"…, before a .pdf or .json extension); returns its name there."""
    T = trash_dir(s); os.makedirs(T, exist_ok=True)
    base = re.sub(r'[/\x00]', '-', base).strip() or 'moved'
    stem, ext = os.path.splitext(base)
    if ext.lower() not in ('.pdf', '.json'): stem, ext = base, ''    # a file keeps its extension: "ilokano 2.pdf" (review 10 L2)
    for n in range(1, 1000):
        name = base if n == 1 else f'{stem} {n}{ext}'
        dst = os.path.join(T, name)
        if os.path.lexists(dst): continue
        try: os.rename(src, dst)
        except OSError as e:
            if e.errno == errno.EXDEV: raise Refused(OTHER_DISK)
            if e.errno in (errno.EEXIST, errno.ENOTEMPTY): continue
            raise
        return name
    raise Refused('The Trash already holds too many items of this name. Empty the Trash, then try again.')

def _drop_home_cache(s):
    try: os.remove(os.path.join(s['jobs'], 'home-index.json'))
    except OSError: pass

def _drop_name(s, kind, key):
    """A run's or batch's plain name out of run-names.json; returned for the log."""
    with NM.locked(s):
        d = NM._load(NM._p(s, 'run-names.json'))
        e = (d.get(kind) or {}).pop(key, None)
        if e is not None: NM._save(NM._p(s, 'run-names.json'), d)
    return (e or {}).get('name')

# ------------------------------------------------------------------ what blocks a move
def why_busy(s, run, R):
    """The plain reason this run can't be moved now, or None."""
    if R and jobs.lock_holder(R): return 'A review page is open for it. Close the review first.'
    for j in jobs.all_jobs(s['jobs']):
        if not jobs.related(j['run'], run): continue
        if j['status'] == 'running' and j['kind'] in jobs.PERSON: return 'A review page is open for it. Close the review first.'
        if j['status'] == 'running': return 'It is being processed right now. Try again when it stops.'
        if j['status'] == 'queued': return 'It is waiting to start. Try again when it has run, or once it is stopped.'
        if j['status'] == 'needs-spend': return 'It is waiting for a new estimate. Select "Dismiss" on its page first.'
    if R and os.path.isfile(os.path.join(R, 'review.json')) and not os.path.isfile(os.path.join(R, 'record.json')):
        return 'Its review was just finished and its decisions are about to be applied. Try again when the apply is done.'
    return None

def _shipped(R):
    try: return bool(REL.load(R)['shipped'])
    except (OSError, ValueError, KeyError): return False

@contextlib.contextmanager
def _locks(Rs):
    with contextlib.ExitStack() as st:
        for R in sorted({os.path.realpath(R) for R in Rs}):
            try: st.enter_context(runlock.record_lock(R, runlock.REQUEST_WAIT))
            except runlock.Busy: raise Refused(runlock.BUSY)
        yield

def _run_dir(s, run):
    """A run folder the home page lists: under the runs folder, no part starting with "." (runs/.app is the app's own),
    holding a run's own files (HM.is_run); else Refused."""
    parts = run.split('/')
    if any(not x or x.startswith('.') for x in parts): raise Refused('There is no such run.')
    R = os.path.realpath(os.path.join(s['runs'], *parts))
    if not R.startswith(os.path.realpath(s['runs']) + os.sep) or not os.path.isdir(R) or not HM.is_run(R): raise Refused('There is no such run.')
    return R

# ------------------------------------------------------------------ a single run
def plan_run(s, run):
    p = run.split('/')
    if len(p) != 2 or p[0] == 'batches': raise Refused('There is no such run.')
    R = _run_dir(s, run)
    row = HM.row_of(s, run, R)
    return {'what': 'run', 'run': run, 'name': NM.shown_run(s, run), 'pdf': NM.book_name(s, row.get('sha'), row.get('file')) if row.get('sha') else row['book'],
            'file': row.get('file'), 'shipped': _shipped(R), 'words': [CONFIRM_RUN] + ([CONFIRM_SHIPPED] if _shipped(R) else []),
            'refused': why_busy(s, run, R)}

def move_run(s, run):
    pl = plan_run(s, run)
    if pl['refused']: raise Refused(pl['refused'])
    R = _run_dir(s, run)
    with _locks([R]):
        why = why_busy(s, run, R)
        if why: raise Refused(why)
        name = _rename(s, R, f'{run.split("/")[0]} - {run.split("/")[1]}')
    plain = _drop_name(s, 'runs', run)
    log(s, {'what': 'run', 'run': run, 'from': R, 'to': os.path.join(trash_dir(s), name), 'name': plain, 'shipped': pl['shipped']})
    _drop_home_cache(s)
    return {'moved': name}

# ------------------------------------------------------------------ a batch, whole or in part
def _batch(s, label):
    from . import batches as BT
    if not label or label.startswith('.') or '/' in label: raise Refused('There is no such batch.')
    B = os.path.realpath(BT.folder(s, label))
    if not B.startswith(os.path.realpath(os.path.join(s['runs'], 'batches')) + os.sep) or not os.path.isdir(B): raise Refused('There is no such batch.')
    return B

def plan_batch(s, label, names=None):
    from . import batches as BT
    B = _batch(s, label)
    st = BT.state(s, label)
    books = {b['name']: b for b in st['books']}
    pick = list(dict.fromkeys(names)) if names is not None else list(books)   # [] is nothing selected, never the whole batch
    if not pick: raise Refused('Select one or more PDFs first.')
    bad = [n for n in pick if n not in books]
    if bad: raise Refused('A selected PDF is no longer in this batch. Reload the page.')
    shipped = [books[n]['book'] for n in pick if _shipped(os.path.join(B, n))]
    whole = set(pick) == set(books)
    why = next((w for w in (why_busy(s, f'batches/{label}', None),) if w), None) or \
          next((f'"{books[n]["book"]}": ' + w[0].lower() + w[1:] for n in pick for w in [why_busy(s, f'batches/{label}/{n}', os.path.join(B, n))] if w), None)
    return {'what': 'batch', 'label': label, 'name': NM.shown_run(s, f'batches/{label}'), 'whole': whole,
            'pdfs': [{'name': n, 'pdf': books[n]['book'], 'file': books[n]['file']} for n in pick],
            'words': (['Each one\'s remediated PDF, report and review go with it.' + (' The batch\'s dashboard goes too.' if whole else '')]
                      + ([f'{len(shipped)} of them {"was" if len(shipped) == 1 else "were"} shipped. The record of what was shipped and who approved it goes with '
                          + ('it.' if len(shipped) == 1 else 'them.')] if shipped else [])),
            'shipped': shipped, 'refused': why}

def move_batch(s, label, names=None):
    from . import batches as BT
    pl = plan_batch(s, label, names)
    if pl['refused']: raise Refused(pl['refused'])
    B = _batch(s, label)
    picked = [x['name'] for x in pl['pdfs']]
    if pl['whole']:
        with _locks([os.path.join(B, n) for n in picked if os.path.isdir(os.path.join(B, n))]):
            why = plan_batch(s, label, names)['refused']
            if why: raise Refused(why)
            cost = sum(costs.actual(os.path.join(B, n))['usd'] or 0 for n in picked)
            name = _rename(s, B, f'batch - {label}')
        plain = _drop_name(s, 'batches', label)
        log(s, {'what': 'batch', 'label': label, 'from': B, 'to': os.path.join(trash_dir(s), name), 'name': plain, 'pdfs': picked, 'cost_usd': round(cost, 6)})
        _drop_home_cache(s)
        return {'moved': name, 'whole': True}
    # All or nothing (review 10 H1): every picked PDF's record lock up front (sorted, folders that exist), every check
    # again under them, then the moves. A picked PDF with no folder (its estimate failed before run_api.sh made one) has
    # nothing to move: it is only taken out of the batch. Whatever stops the moves, the PDFs already moved are always
    # taken out of the batch and logged (finally), so nothing in the Trash stays on its to-do list.
    have = [n for n in sorted(picked) if os.path.isdir(os.path.join(B, n))]
    absent = [n for n in sorted(picked) if n not in have]
    moved, done = [], False
    try:
        with _locks([os.path.join(B, n) for n in have]):
            why = why_busy(s, f'batches/{label}', None) or next((w for n in picked for w in [why_busy(s, f'batches/{label}/{n}', os.path.join(B, n))] if w), None)
            if why: raise Refused(why)
            for n in have:
                R = os.path.join(B, n)
                cost = costs.actual(R)['usd'] or 0
                name = _rename(s, R, f'batch - {label} - {n}')
                dst = os.path.join(trash_dir(s), name)
                moved.append({'name': n, 'to': dst, 'cost_usd': round(cost, 6)})
                side = os.path.join(dst, '_batch-files'); os.makedirs(side, exist_ok=True)
                for f in sorted(os.listdir(B)):                     # its files in the batch folder go with it
                    if f in (f'{n}.reply.txt', f'{n}.reply.txt.meta.json', f'{n}.log', f'{n}.estimate.log'):
                        os.rename(os.path.join(B, f), os.path.join(side, f))
            done = True
    finally:
        gone = [m['name'] for m in moved] + (absent if done else [])
        if gone:
            BT.forget_books(s, label, gone, moved)
            for m in moved: log(s, {'what': 'batch-pdf', 'label': label, 'pdf': m['name'], 'from': os.path.join(B, m['name']), 'to': m['to'], 'cost_usd': m['cost_usd']})
            for n in (absent if done else []): log(s, {'what': 'batch-pdf', 'label': label, 'pdf': n, 'from': None, 'to': None, 'note': 'no folder: taken out of the batch only'})
            _drop_home_cache(s)
    return {'moved': [m['name'] for m in moved], 'forgotten': absent, 'whole': False}

# ------------------------------------------------------------------ a PDF added through "Add a PDF"
def runs_using(s, sha):
    """Every run (single or in a batch) made from this content: [{run, name, date, status, R}]: a run whose records name
    it, and a run the app started from it that has no record yet (its jobs name it: an estimate in progress)."""
    rows = {r['run']: r for r in HM.index(s)['runs']}
    first = {}
    for j in jobs.all_jobs(s['jobs']):
        if j.get('book_sha') == sha and j['kind'] != 'batch': first.setdefault(j['run'], j.get('created'))
    out = []
    for run in sorted({r for r, x in rows.items() if x.get('sha') == sha} | set(first)):
        r = rows.get(run) or {'run': run, 'when': first.get(run), 'words': 'Not started'}
        out.append({'run': run, 'name': NM.shown_run(s, run) if run.startswith('batches/') else r.get('name') or NM.shown_run(s, run),
                    'date': r.get('when'), 'status': r.get('words'), 'R': os.path.join(s['runs'], *run.split('/'))})
    return out

def _other_copy(s, sha, path):
    """Another file with the same content in samples/ or uploads/ (the app finds an original by sha256)."""
    others = [p for p in BK.pdfs_in(s['samples']) + BK.pdfs_in(s['uploads']) if os.path.realpath(p) != os.path.realpath(path)]
    return any(h == sha for h in BK.hashes(s, others).values())

def effect(s, u, sha, path):
    """What moving this PDF changes for one run, in a sentence (Patrick, 2026-11-07: never claim "Review Again" fails for
    a run that kept its own copy): a finished run needs the original only when it has no intake copy (runs.pdf_needed);
    a run waiting for its first apply always needs one; a run before its result needs the very file it was started from."""
    from . import runs as RN
    R = u['R']
    rec = RN.load(os.path.join(R, 'record.json'))
    if rec:
        p, why = RN.pdf_needed(s, R, rec)
        if not p and not why: return STILL_WORKS
        return STILL_WORKS.replace('the run kept its own copy', 'another copy of the PDF is in the app\'s folders') if _other_copy(s, sha, path) else NEEDS_BACK
    if RN.waiting(R): return APPLY_NEEDS if not _other_copy(s, sha, path) else STILL_WORKS.replace('"Review Again" still works: the run kept its own copy',
                                                                                                   'Applying its reviewed decisions still works: another copy of the PDF is in the app\'s folders')
    return GO_ON_NEEDS

def jobs_reading(s, path):
    """A running or queued job whose command names this file (an estimate, a run or a batch reading it), or None."""
    return next((j for j in jobs.all_jobs(s['jobs']) if j['status'] in jobs.ACTIVE and any(jobs.path_in(a, path) for a in j.get('argv') or [])), None)

def plan_pdf(s, key):
    b = BK.by_key(s, key)
    if not b: raise Refused('This PDF\'s file has changed or is gone. Reload the page.')
    U = os.path.realpath(s['uploads'])
    if not os.path.realpath(b['path']).startswith(U + os.sep): raise Refused('Only a PDF added through "Add a PDF" can be moved from here.')
    used = runs_using(s, key)
    why = next((f'The run "{u["name"]}": ' + w[0].lower() + w[1:] for u in used for w in [why_busy(s, u['run'], u['R'])] if w), None) or \
          ('It is being read by a job right now. Try again when the job has stopped.' if jobs_reading(s, b['path']) else None)
    from lib import dates as D
    return {'what': 'pdf', 'key': key, 'pdf': b['name'], 'file': b['file'],
            'runs': [{'name': u['name'], 'date': D.day(u['date']) if u['date'] else 'date not recorded', 'status': u['status'],
                      'effect': effect(s, u, key, b['path'])} for u in used],
            'words': [CONFIRM_USED] if used else [], 'refused': why}

def move_pdf(s, key):
    pl = plan_pdf(s, key)
    if pl['refused']: raise Refused(pl['refused'])
    b = BK.by_key(s, key)
    with BK._uploads_lock(s['uploads']):
        why = plan_pdf(s, key)['refused']
        if why: raise Refused(why)
        name = _rename(s, b['path'], os.path.basename(b['path']))
        note = b['path'][:-4] + '.json'                     # its note from "Add a PDF" goes with it
        noted = _rename(s, note, name[:-4] + '.json' if name.lower().endswith('.pdf') else name + '.json') if os.path.isfile(note) else None
    log(s, {'what': 'pdf', 'sha256': key, 'file': os.path.basename(b['path']), 'from': b['path'], 'to': os.path.join(trash_dir(s), name),
            'note_to': os.path.join(trash_dir(s), noted) if noted else None,
            'runs': [r['name'] for r in pl['runs']]})
    _drop_home_cache(s)
    return {'moved': name}
