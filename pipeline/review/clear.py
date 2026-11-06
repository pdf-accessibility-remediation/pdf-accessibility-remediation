"""review/clear.py: "Clear This Book's Files" (#45, requirement 6; 03 §10, Patrick's decisions of 2026-11-05). Optional:
offered on the run page only once its gate is open, never prompted, counted or suggested anywhere else. A shipped book
that is never cleared stays a full run.

    gate(R, rec=None, sha=REL.sha_file)     {ok, why, shipment, sha, files, bytes}: may this book be cleared now
    plan(R, ship_sha, sha=REL.sha_file)     [{path (relative), bytes, sha256, what}]: the files clearing deletes
    clear(R, by, confirm, busy=None, wait=…) the deletion, recorded in release/cleared.json (planned, then done)

What is deleted, by an allow-list of file types at named paths (never a whole folder):
  - the run folder's finished PDF (record.json document.output), only when its sha256 is a live shipment's;
  - _intake/intake.pdf;
  - every reviews/versions/*/ PDF, the AI's own version (ai) and versions with evaluation results included: after shipping,
    the AI's decisions (workorder.ai.json) and the records are the evidence; the PDF is a by-product (Patrick, 2026-11-05;
    "Clean Up Space" before shipping still keeps versions/ai: review/prune.py, K9);
  - figure crops and page images (.png, .jpg, .jpeg) under _audit/ and reviews/_audit/.
What is kept: every .json, .md, .html and .csv file (records are never written under _audit/ or reviews/_audit/, and
never as images: docs/files.md); all of release/shipped/NNN/; the original in samples/ or uploads/ (never touched).

The gate: the book is Shipped (its current PDF, hashed now, is a live shipment's); that version's record ZIP was downloaded
in full (release/downloads.json, written by the app after the ZIP's last byte); the shipped copy in release/shipped/NNN/
still has the shipment's hash; nothing is in progress (reviews/.lock free, no promotion or re-apply, no open session, no
finished session waiting to be applied, no job of the app: `busy`); not cleared already. Every condition is read again
under the locks, in review/prune.py's order: reviews/.lock (refuses, never waits), then the record lock.

release/cleared.json: {schema, state: planned | done, by, planned, cleared, shipment, sha256, files: [{path, bytes, sha256,
what}], kept_changed: [...], freed_bytes, code}. It is written as `planned` before anything is deleted; a clear that
stopped partway is finished by running it again: each planned file still there is hashed and deleted only when it
matches the plan. After clearing the book is read only (review/sessions.py not_cleared): Review Again, Apply, an OCR
verdict, the evaluation's Record, Ship and Clean Up Space are refused; withdrawing a shipment still works.
"""
import os, datetime
from lib import release as REL, runlock
from . import sessions as S
from .ocr import put_json

SCHEMA = 'cleared/1'
CONFIRM = 'CLEAR'
IMAGES = ('.png', '.jpg', '.jpeg')
WHAT = {'output': 'The working copy of the finished PDF (the same file as the shipped copy)', 'intake': 'The prepared PDF the run worked on',
        'version': 'The PDFs of the earlier versions, the AI\'s own version included', 'images': 'Figure crops and page images made for the AI and the review'}

def _p(R): return os.path.join(R, 'release', 'cleared.json')
def downloads(R):
    try: d = REL._json(os.path.join(R, 'release', 'downloads.json'), [])
    except (OSError, ValueError): return []
    return d if isinstance(d, list) else []

def _inside(R, p):
    r = os.path.realpath(R); q = os.path.realpath(p)
    return q.startswith(r + os.sep) and os.path.isfile(p) and not os.path.islink(p)

def plan(R, ship_sha, sha=REL.sha_file, rec=None):
    """The files clearing deletes now, each with its size and hash; the finished PDF only when its hash is ship_sha."""
    R = os.path.abspath(R); rec = rec if rec is not None else (S.load(os.path.join(R, 'record.json')) or {})
    out = []
    def add(p, what, need=None):
        if not _inside(R, p): return
        h = sha(p)
        if need and h != need: return
        out.append({'path': os.path.relpath(p, R), 'bytes': os.path.getsize(p), 'sha256': h, 'what': what})
    name = (rec.get('document') or {}).get('output')
    from webapp.downloads import plain_name
    if plain_name(name): add(os.path.join(R, name), 'output', need=ship_sha)
    add(os.path.join(R, '_intake', 'intake.pdf'), 'intake')
    V = S.P(R)['versions']
    try: vs = sorted(e.name for e in os.scandir(V) if e.is_dir() and not e.name.startswith('.'))
    except OSError: vs = []
    for v in vs:
        d = os.path.join(V, v)
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.pdf'): add(os.path.join(d, f), 'version')
    for A in (os.path.join(R, '_audit'), S.P(R)['audit']):
        if not os.path.isdir(A): continue
        for d, subs, fs in os.walk(A):
            subs.sort()
            for f in sorted(fs):
                if f.lower().endswith(IMAGES): add(os.path.join(d, f), 'images')
    return out

def gate(R, rec=None, sha=REL.sha_file, busy=None):
    """{ok, why, shipment, sha}: every condition but the locks. busy: the app's own check (a job of this run), or None."""
    R = os.path.abspath(R)
    c = REL.cleared(R)
    if c and c.get('state') == 'done': return {'ok': False, 'why': 'This book\'s files were cleared already.', 'shipment': c.get('shipment')}
    if busy:
        why = busy()
        if why: return {'ok': False, 'why': why, 'shipment': (c or {}).get('shipment')}
    rec = rec if rec is not None else (S.load(os.path.join(R, 'record.json')) or {})
    rel = REL.load(R, rec)
    out = (rec.get('document') or {}).get('output')
    p = os.path.join(R, out) if out else None
    if c and c.get('state') == 'planned':                      # finishing a clear that stopped partway
        return {'ok': True, 'why': None, 'shipment': c.get('shipment'), 'sha': c.get('sha256'), 'resume': True}
    cur = sha(p) if p and os.path.isfile(p) else None
    live = [s for s in REL.live_shipments(rel) if REL.sha_of(s) == cur] if cur else []
    if not live: return {'ok': False, 'why': 'Only a shipped book can be cleared: the current version is not a shipped one.'}
    s = live[-1]; n = s.get('n')
    from webapp.downloads import _shipped_dir
    d = _shipped_dir(R, s); f = (s.get('pdf') or {}).get('file')
    if not d or not f or not os.path.isfile(os.path.join(d, f)) or sha(os.path.join(d, f)) != cur:
        return {'ok': False, 'why': 'The shipped copy kept with this book has changed or is missing, so its files are not cleared.', 'shipment': n}
    if not any(x.get('what') == 'record' and x.get('sha256') == cur and x.get('complete') for x in downloads(R)):
        return {'ok': False, 'why': 'Download the record (ZIP) of the shipped version first.', 'shipment': n, 'sha': cur}
    p_ = S.P(R)
    if os.path.exists(p_['promoting']) or os.path.isdir(p_['work']): return {'ok': False, 'why': 'A new version of this book is being made.', 'shipment': n}
    if any(x.get('status') == 'open' for x in S.sessions(R)): return {'ok': False, 'why': 'A review session of this book is open: discard it or finish it first.', 'shipment': n}
    if S.newer(R, rec)['finished']: return {'ok': False, 'why': 'A finished review session is waiting to be applied.', 'shipment': n}
    return {'ok': True, 'why': None, 'shipment': n, 'sha': cur}

def summary(items):
    """What goes, in words and sizes, by kind (the dialog's list)."""
    out = {}
    for x in items:
        k = out.setdefault(x['what'], {'what': WHAT[x['what']], 'files': 0, 'bytes': 0}); k['files'] += 1; k['bytes'] += x['bytes']
    return [out[k] for k in ('output', 'intake', 'version', 'images') if k in out]

def clear(R, by, confirm, busy=None, wait=runlock.COMMAND_WAIT, now=None):
    """Clear the book's files. Raises S.Refused with the reason. Returns the cleared record."""
    from review.core import clean_text
    R = os.path.abspath(R)
    by = clean_text(by or '', one_line=True)[:80]
    if not by: raise S.Refused('Enter your name in "Your Name."')
    if str(confirm or '').strip() != CONFIRM: raise S.Refused(f'Type {CONFIRM} to confirm.')
    try: lk = S.Lock(R, 'clear')                             # reviews/.lock first: it refuses, never waits
    except S.Refused: raise S.Refused('A review of this book is open or being applied. Try again once it is closed.')
    try:
        with runlock.record_lock(R, wait):
            g = gate(R, busy=busy)
            if not g['ok']: raise S.Refused(g['why'])
            at = now or datetime.datetime.now().isoformat(timespec='seconds')
            os.makedirs(os.path.join(R, 'release'), exist_ok=True)
            if g.get('resume'):
                c = REL.cleared(R)
                items, kept = [], []
                for x in c.get('files') or []:
                    p = os.path.join(R, x['path'])
                    if not _inside(R, p): continue                       # already deleted
                    if REL.sha_file(p) == x['sha256']: items.append(x)
                    else: kept.append(x['path'])
            else:
                items, kept = plan(R, g['sha']), []
                c = {'schema': SCHEMA, 'state': 'planned', 'by': by, 'planned': at, 'shipment': g['shipment'], 'sha256': g['sha'],
                     'files': items}
                put_json(_p(R), c)                                        # before anything is deleted
            for x in items: os.remove(os.path.join(R, x['path']))
            from review.manual import code
            c.update(state='done', cleared=at, kept_changed=sorted(set((c.get('kept_changed') or []) + kept)),
                     freed_bytes=sum(x['bytes'] for x in c.get('files') or []) - sum(x['bytes'] for x in c.get('files') or [] if x['path'] in kept),
                     code=code(), **({'finished_by': by} if g.get('resume') else {}))
            put_json(_p(R), c)
            return c
    except runlock.Busy as e: raise S.Refused(str(e))
    finally: lk.release()
