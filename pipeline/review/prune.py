"""review/prune.py: "Remove Older PDFs" (issue #38, stage 3; Patrick's decision on storage). Frees space by deleting the
PDFs of earlier versions that were never evaluated or shipped. Their records and decisions are kept. The AI's own version
is always kept.

    plan(R, sha=…)                     [{id, label, applied, bytes, sha256, path}]: what would be removed (a dry run)
    remove(R, shown, by, wait=…)       remove exactly what plan() gives now, if it is what the person was shown

Never removed:
  - the current version (it is not under reviews/versions/);
  - the AI's own version, reviews/versions/ai: the result before any review, the evidence of what the AI did (review 18 K9);
  - any version with an evaluation result on its PDF's hash (release/checks.json), or a shipment of it (release/shipped.json,
    withdrawn or not).
Only the PDF goes. The version's record.json, review.md and review.html, and the session's work order
(reviews/sessions/NNN.json and NNN.workorder.json), always stay. release/removed.json records each removal, and the
version's review.html says so whenever it is built (report_html, from that file). The deletion is permanent.

Locks in the stated order (lib/runlock.py): reviews/.lock (refuses, never waits), then the record lock. Refused while a
promotion or a re-apply is under way. The PDFs are hashed again under the lock, and nothing is removed if the list is not
the one shown.
"""
import os, datetime
from lib import release as REL, runlock
from . import sessions as S
from .ocr import put_json

LIST_CHANGED = 'The list of older PDFs changed since it was shown. Look at it again, then remove them.'
REVIEW_OPEN = 'A review of this book is open or being applied. Try again once it is closed.'
BEING_MADE = 'A new version of this book is being made. Try again once it is done.'

def _label(vid): return f'Session {int(vid)}' if str(vid).isdigit() else f'version {vid}'

def plan(R, sha=REL.sha_file):
    """The earlier versions whose PDF would be removed now, oldest first. sha: how a PDF is hashed (the app passes its
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

def remove(R, shown, by, wait=runlock.COMMAND_WAIT, say=print):
    """Remove the PDFs plan() gives now, if their hashes are exactly `shown` (what the person saw). Returns what was removed."""
    from review.core import clean_text
    R = os.path.abspath(R)
    by = clean_text(by or '', one_line=True)[:80]
    if not by: raise S.Refused('Enter your name in "Removed By".')
    try: lk = S.Lock(R, 'remove older pdfs')                     # reviews/.lock first: it refuses, never waits
    except S.Refused: raise S.Refused(REVIEW_OPEN)
    try:
        with runlock.record_lock(R, wait):
            p = S.P(R)
            if os.path.exists(p['promoting']) or os.path.isdir(p['work']): raise S.Refused(BEING_MADE)
            items = plan(R)                                       # hashed afresh, under the lock
            if not items or sorted(x['sha256'] for x in items) != sorted(shown or []): raise S.Refused(LIST_CHANGED)
            log = REL.removed(R); now = datetime.datetime.now().isoformat(timespec='seconds')
            for x in items:
                os.remove(x['path'])
                log.append({'version': x['id'], 'sha256': x['sha256'], 'bytes': x['bytes'], 'by': by, 'removed': now})
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
