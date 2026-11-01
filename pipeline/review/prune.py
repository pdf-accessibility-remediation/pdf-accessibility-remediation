"""review/prune.py: "Clean Up Space" (issue #38, stage 3; Patrick's decisions on storage, 2026-10-31 and 2026-11-01).
Deletes the PDF files of the previous versions a person selects, to free up space. Their records and decisions stay; the
AI's own version is always kept.

    plan(R, sha=…)                     [{id, label, applied, bytes, sha256, path}]: the versions that may be removed
    remove(R, chosen, by, wait=…)      remove exactly the chosen ones [{id, sha256}], if each is still in plan() with the
                                       hash the person was shown; nothing is removed unless chosen

Never removed:
  - the current version (it is not under reviews/versions/);
  - the AI's own version, reviews/versions/ai: the result before any review, the evidence of what the AI did (review 18 K9);
  - any version with an evaluation result on its PDF's hash (release/checks.json), or a shipment of it (release/shipped.json,
    withdrawn or not).
Only the PDF goes. The version's record.json, review.md and review.html, and the session's work order
(reviews/sessions/NNN.json and NNN.workorder.json), always stay. release/removed.json records each removal, and the
version's review.html says so whenever it is built (report_html, from that file). The deletion is permanent.

Locks in the stated order (lib/runlock.py): reviews/.lock (refuses, never waits), then the record lock. Refused while a
promotion or a re-apply is under way. The PDFs are hashed again under the lock, and nothing is removed if any chosen
version is no longer offered, or its PDF is not the one shown.
"""
import os, datetime
from lib import release as REL, runlock
from . import sessions as S
from .ocr import put_json

LIST_CHANGED = 'The previous versions changed since they were shown, so nothing was removed. Open "Clean Up Space" again and choose again.'
NONE_CHOSEN = 'Select at least one PDF to remove.'
REVIEW_OPEN = 'A review of this book is open or being applied. Try again once it is closed.'
BEING_MADE = 'A new version of this book is being made. Try again once it is done.'

def _label(vid): return f'Session {int(vid)}' if str(vid).isdigit() else f'version {vid}'

def plan(R, sha=REL.sha_file):
    """The previous versions whose PDF may be removed now (the ones the dialog offers), oldest first. sha: how a PDF is hashed (the app passes its
    cached display hash; remove() always hashes afresh)."""
    R = os.path.abspath(R)
    rel = REL.load(R)
    keep = {REL.sha_of(c) for s in REL.SECTIONS for c in rel['checks'].get(s) or []} | {REL.sha_of(s) for s in rel.get('shipped') or []}
    keep.discard(None)
    V = S.P(R)['versions']; base = os.path.realpath(V) + os.sep
    try: names = sorted((e.name for e in os.scandir(V) if e.is_dir() and not e.name.startswith('.')), key=lambda n: (S.sid_n(n), n))
    except OSError: return []
    out = []
    for n in names:
        if n == 'ai': continue                                    # the AI's own version is always kept (K9)
        d = os.path.realpath(os.path.join(V, n))
        if not d.startswith(base): continue
        vrec = S.load(os.path.join(d, 'record.json')) or {}
        name = (vrec.get('document') or {}).get('output')
        p = os.path.join(d, name) if name else None
        if not p or os.path.dirname(os.path.realpath(p)) != d or not os.path.isfile(p): continue
        h = sha(p)
        if h in keep: continue
        ses = S.session(R, n) or {}
        out.append({'id': n, 'label': _label(n), 'applied': ses.get('applied') or vrec.get('written'), 'bytes': os.path.getsize(p),
                    'sha256': h, 'path': p})
    return out

def chosen_of(chosen):
    """The person's choice as {id: sha256}; a version named twice with two hashes is refused."""
    out = {}
    for c in chosen or []:
        vid, h = (str(c.get('id') or ''), str(c.get('sha256') or '')) if isinstance(c, dict) else ('', '')
        if not vid or not h or out.get(vid, h) != h: raise S.Refused(LIST_CHANGED)
        out[vid] = h
    return out

def remove(R, chosen, by, wait=runlock.COMMAND_WAIT, say=print):
    """Remove the PDFs of the chosen versions [{id, sha256}] (what the person selected, with the hash they were shown), if
    each is still offered by plan() with that hash, hashed afresh under the locks. Returns what was removed."""
    from review.core import clean_text
    R = os.path.abspath(R)
    want = chosen_of(chosen)
    if not want: raise S.Refused(NONE_CHOSEN)
    by = clean_text(by or '', one_line=True)[:80]
    if not by: raise S.Refused('Enter your name in "Removed By."')
    try: lk = S.Lock(R, 'clean up space')                     # reviews/.lock first: it refuses, never waits
    except S.Refused: raise S.Refused(REVIEW_OPEN)
    try:
        with runlock.record_lock(R, wait):
            p = S.P(R)
            if os.path.exists(p['promoting']) or os.path.isdir(p['work']): raise S.Refused(BEING_MADE)
            now = {x['id']: x for x in plan(R)}                   # hashed afresh, under the lock
            if any(vid not in now or now[vid]['sha256'] != h for vid, h in want.items()): raise S.Refused(LIST_CHANGED)
            items = [now[vid] for vid in now if vid in want]      # oldest first; only what was chosen
            log = REL.removed(R); at = datetime.datetime.now().isoformat(timespec='seconds')
            for x in items:
                os.remove(x['path'])
                log.append({'version': x['id'], 'sha256': x['sha256'], 'bytes': x['bytes'], 'by': by, 'removed': at})
            os.makedirs(os.path.join(R, 'release'), exist_ok=True)
            put_json(os.path.join(R, 'release', 'removed.json'), log)
    except runlock.Busy as e: raise S.Refused(str(e))
    finally: lk.release()
    for x in items:                                               # each version's own page, with its note (outside the locks)
        try: _rebuild_version_page(R, x['id'])
        except Exception as e: say(f'note: the page of {x["label"]} was not rebuilt ({type(e).__name__}: {e})')
    return items

def _rebuild_version_page(R, vid):
    """The removed version's review.html, built again with its "replaced by" banner and the removal note."""
    rec = S.load(os.path.join(R, 'record.json')) or {}
    later = sorted((x['id'] for x in S.sessions(R) if x.get('status') == 'applied' and S.sid_n(x['id']) > S.sid_n(vid)), key=S.sid_n)
    S.replaced_banner(os.path.join(S.P(R)['versions'], vid), vid, later[0] if later else S.current_id(rec), R)
