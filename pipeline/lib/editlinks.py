"""lib/editlinks.py: the link between a run and the runs made from hand-edited copies of it (handedit.py import, #62), as
the app's run page and the offline dashboards (review.html, summary.html: #98) both show it. Standard library only.

    from lib import editlinks
    kids = editlinks.copies(R)            # [{'label', 'run', 'when', 'by', 'note', 'to', 'state'}] from R/hand_edits.json
    par  = editlinks.parent(R, rec)       # {'run', 'label', 'state'} from record.json hand_edit (or _handedit/), else None
    href = editlinks.rel_page(R, P)       # "../handedit-x/review.html": P's review.html from R's folder, None without one

A copy's state: "removed" (its folder is gone), "finished" (record.json), "waiting for its review" (run_api.sh stopped
with REVIEW=1: the decisions kept, nothing applied) or "not started" (brought back with --no-run, or its run failed or was
stopped). The app adds "being prepared" from its own jobs (webapp/runs.py hand_edits). The folders are the absolute paths
handedit.py recorded; a runs folder moved since reads as "removed".
"""
import os, json

WORDS = {'finished': ('Finished.', 'finished'),             # each state as a sentence (review.html) and inline (summary.html)
         'waiting for its review': ('Waiting for its review (no dashboard yet).', 'waiting for its review'),
         'not started': ('Not started (no dashboard yet).', 'not started'),
         'removed': ('Its folder is no longer there.', 'its folder is no longer there')}

def words(st, inline=False):
    w = WORDS.get(st)
    return (w[1] if inline else w[0]) if w else st

def _path(v): return v if isinstance(v, str) and v else None   # a hand-edited or damaged file: anything else is no folder

def _load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None

def waiting(R):
    """A run run_api.sh stopped for its first review (REVIEW=1): the AI's decisions kept, nothing applied, no record yet."""
    return not os.path.isfile(os.path.join(R, 'record.json')) and os.path.isfile(os.path.join(R, 'workorder.ai.json'))

def state(P):
    if not P or not os.path.isdir(P): return 'removed'
    if os.path.isfile(os.path.join(P, 'record.json')): return 'finished'
    if waiting(P): return 'waiting for its review'
    return 'not started'

def copies(R):
    """The runs made from edited copies of R, in the order they were brought back (hand_edits.json `children`)."""
    d = _load(os.path.join(R, 'hand_edits.json'))
    out = []
    for c in (d.get('children') if isinstance(d, dict) else None) or []:
        if not isinstance(c, dict): continue
        P = _path(c.get('run'))
        out.append({'label': os.path.basename(os.path.normpath(P)) if P else 'run not recorded', 'run': P,
                    'when': c.get('when'), 'by': c.get('by'), 'note': c.get('note'), 'to': c.get('to'), 'state': state(P)})
    return out

def parent(R, rec=None):
    """The run this one was made from (record.json `hand_edit`, else _handedit/hand_edit.json before the first record), or None."""
    he = (rec or {}).get('hand_edit') or _load(os.path.join(R, '_handedit', 'hand_edit.json'))
    par = he.get('parent') if isinstance(he, dict) else None
    P = _path(par.get('run')) if isinstance(par, dict) else None
    if not P: return None
    return {'run': P, 'label': '/'.join(os.path.normpath(P).split(os.sep)[-2:]), 'state': state(P)}

def rel_page(R, P, name='review.html'):
    """P's review.html as a link relative to R's folder (offline and in the app alike), or None when it has none."""
    if not P or not os.path.isfile(os.path.join(P, name)): return None
    return os.path.relpath(os.path.join(os.path.abspath(P), name), os.path.abspath(R)).replace(os.sep, '/')
