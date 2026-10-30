"""webapp/runs.py: a finished run as the panel shows it, and the commands its buttons start. Everything comes from the
run folder (record.json, review.md, reviews/) and the job files; the commands are review_workorder.py's own.

    Review again                  review_workorder.py <run> --reopen [--pdf P] --no-browser --return-to <run page>
    … from session N / the AI     the same with --from N / --from ai (and --discard-open after the person confirms)
    Apply session N               review_workorder.py <run> --apply [--pdf P]
    (before the first review of an unpinned run) review_workorder.py <run> --pin [--pdf P], then the review

--pdf is added only when the run's input is not where the pipeline can find it: a tagged book never pinned (the record
names no path), or a basis whose path no longer holds the file. The original is then found by its sha256 in samples/
and uploads/ (read only; sha256s cached in <jobs>/sha256-cache.json by path, size and mtime).
"""
import os, re, sys, json, urllib.parse
from review import sessions as S
from . import config, jobs, logs

def load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

# ------------------------------------------------------------------ ready to ship, never None or "unknown"
READY_MD = re.compile(r'^\*\*Ready to ship\?\*\* (Yes|No)\s*$')

def ready(R, rec):
    """{'answer': 'Yes' | 'No' | None, 'lines': [...], 'source': ...}: the record's glance, else review.md's Overview, else
    'not recorded for this run'."""
    g = (rec or {}).get('glance')
    if isinstance(g, dict) and isinstance(g.get('ready'), bool):
        return {'answer': 'Yes' if g['ready'] else 'No', 'lines': [f'{x["what"]}: {x["text"]}' for x in g.get('ship') or []], 'source': 'record.json'}
    try: md = open(os.path.join(R, 'review.md'), encoding='utf-8').read().splitlines()
    except OSError: md = []
    for i, l in enumerate(md):
        m = READY_MD.match(l)
        if m:
            lines = []
            for x in md[i + 1:]:
                if not x.startswith('- '): break
                lines.append(x[2:])
            return {'answer': m.group(1), 'lines': lines, 'source': 'review.md'}
    return {'answer': None, 'lines': [], 'source': None, 'text': 'not recorded for this run'}

# ------------------------------------------------------------------ the original, by sha256
def find_original(s, sha, name=None):
    """A PDF in samples/ or uploads/ whose sha256 is sha (files named `name` are tried first), or None."""
    cache_p = os.path.join(s['jobs'], 'sha256-cache.json'); cache = load(cache_p) or {}
    cands = []
    for root in (s['samples'], s['uploads']):
        if not os.path.isdir(root): continue
        for d, _, fs in os.walk(root):
            cands += [os.path.join(d, f) for f in fs if f.lower().endswith('.pdf')]
    cands.sort(key=lambda p: (os.path.basename(p) != name, p))
    found, dirty = None, False
    for p in cands:
        try: st = os.stat(p)
        except OSError: continue
        key = [st.st_size, st.st_mtime_ns]
        c = cache.get(p)
        if not c or c[:2] != key:
            c = key + [S.sha_file(p)]; cache[p] = c; dirty = True
        if c[2] == sha: found = p; break
    if dirty:
        os.makedirs(s['jobs'], exist_ok=True); tmp = cache_p + '.tmp'
        json.dump(cache, open(tmp, 'w'), indent=0); os.replace(tmp, cache_p)
    return found

def pdf_needed(s, R, rec):
    """(--pdf path or None, refusal or None) for this run's next review command."""
    b = S.basis(R)
    if b and os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json')):
        if os.path.isfile(os.path.join(R, '_intake', 'intake.pdf')): return None, None
        inp = b.get('input') or {}
        if inp.get('path') and os.path.isfile(inp['path']): return None, None
        sha = inp.get('sha256')
        if inp.get('path') and os.path.basename(os.path.dirname(inp['path'])) == '_intake':     # the run's own intake result
            return None, (f'this run\'s input, {inp["path"]} (its intake result, sha256 {(sha or "")[:16]}), is missing: it was made by '
                          'intake and is not in samples/; the run cannot be reviewed again without it')
    else:
        if ((rec.get('intake') or {}).get('result') or {}).get('pdf'): return None, None
        sha = ((rec.get('workorder') or {}).get('source') or {}).get('sha256') or (rec.get('document') or {}).get('sha256')
    name = (rec.get('document') or {}).get('file')
    if not sha: return None, 'the record names no input sha256, so the original cannot be looked for'
    p = find_original(s, sha, name)
    if p: return p, None
    return None, (f'the original PDF of this run ({name or "its PDF"}, sha256 {sha[:16]}) is not in {s["samples"]} or {s["uploads"]}: '
                  f'put a copy there, or run the command in a terminal with --pdf <the original>')

# ------------------------------------------------------------------ the panel's view of a run
def live_review(s, run):
    for j in reversed(jobs.all_jobs(s['jobs'])):
        if j['run'] == run and j['kind'] == 'review' and j['status'] == 'running': return j
    return None

def job_view(s, j, with_text=False, offset=0):
    """A job for the page: no environment; its steps, outcome and the last lines of its log."""
    text = jobs.read_log(s['jobs'], j['id'])[0]
    v = {k: j.get(k) for k in ('id', 'kind', 'run', 'status', 'created', 'started', 'ended', 'exit', 'url', 'paid', 'after', 'then_job', 'note', 'what')}
    v.update(position=jobs.position(s['jobs'], j['id']), steps=logs.steps(text), outcome=logs.outcome(text), tail=logs.tail(text),
             command=' '.join(x if x != sys.executable else 'python3' for x in j['argv']))
    if j['kind'] == 'review' and j['status'] == 'running':
        v['past_finish'] = jobs.review_past_finish(jobs.run_dir(j, s['runs']), j.get('started'))
    if j['status'] == 'interrupted' and j['kind'] in ('apply', 'review'):
        v['interrupted'] = after_interrupt(jobs.run_dir(j, s['runs']), j)
    if with_text:
        t, nxt = jobs.read_log(s['jobs'], j['id'], offset); v.update(text=t, next=nxt)
    return v

def after_interrupt(R, j):
    """An interrupted apply or review: what is left, from the run's state on disk, not from the job status (a killed wrapper
    can leave its command to finish alone). {state: apply | done | continue | none, text}."""
    ss = S.sessions(R) if R else []
    since = j.get('started') or ''
    applied = [x for x in ss if x.get('status') == 'applied' and (x.get('applied') or '') >= since]
    if os.path.exists(os.path.join(R, 'reviews', 'promoting.json')):
        return {'state': 'apply', 'text': 'The apply stopped partway (reviews/promoting.json is there). Apply finishes it; it may apply the '
                                          'session again. Earlier results stay in reviews/versions/.'}
    if applied:
        return {'state': 'done', 'text': f'done (the app lost track of the job): {S.label(applied[-1]["id"])} is the current result'}
    u = unapplied(ss)
    if u: return {'state': 'apply', 'text': f'{u["label"].capitalize()} is finished and not applied: Apply applies it.'}
    op = [x for x in ss if x.get('status') == 'open']
    if j['kind'] == 'review' and op: return {'state': 'continue', 'text': f'{S.label(op[-1]["id"]).capitalize()} stays open: Continue review carries on with it.'}
    return {'state': 'none', 'text': 'The run shows no change from this job: start it again.'}

def run_path(run): return os.path.join(*run.split('/'))

def unapplied(ss):
    """The session Apply is offered for: the newest finished-or-applied one, when it is finished and not applied. A
    finished session that a later one replaced (its apply failed, then the person reviewed again) is never offered."""
    done = [x for x in ss if x.get('status') in ('finished', 'applied')]
    if not done or done[-1].get('status') != 'finished': return None
    x = done[-1]
    return {'id': x['id'], 'label': S.label(x['id']), 'finished': x.get('finished')}

def state(s, run, R):
    rec = load(os.path.join(R, 'record.json')) or {}
    ss = S.sessions(R); cur = S.current_id(rec)
    vers = S.P(R)['versions']
    rows = []
    for x in ss:
        r = S.summary_row(x)
        v = os.path.join(vers, x['id'])
        rows.append({**r, 'current': x['id'] == cur, 'from_label': S.from_label(r['from']), 'label': S.label(x['id']),
                     'result': (f'reviews/versions/{x["id"]}/' + ('review.html' if os.path.isfile(os.path.join(v, 'review.html')) else 'review.md'))
                               if os.path.isdir(v) and x['id'] != cur else None})
    ai_v = os.path.join(vers, 'ai')
    op = [x for x in ss if x.get('status') == 'open']
    done =[x for x in ss if x.get('status') in ('finished', 'applied')]
    rj = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run]
    live = live_review(s, run)
    h = jobs.lock_holder(R)
    rel = os.path.relpath(R, config.PIPELINE)
    return {
        'run': run, 'title': (rec.get('document') or {}).get('file') or run, 'review_html': os.path.isfile(os.path.join(R, 'review.html')),
        'review_md': os.path.isfile(os.path.join(R, 'review.md')), 'ready': ready(R, rec),
        'current': {'id': cur, 'label': S.label(cur)}, 'pending': (rec.get('review') or {}).get('pending'),
        'pinned': bool(S.basis(R)) and os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json')),
        'legacy_review': bool((rec.get('review') or {}).get('workorder')) and not ss,
        'sessions': rows, 'ai_result': 'reviews/versions/ai/' + ('review.html' if os.path.isfile(os.path.join(ai_v, 'review.html')) else 'review.md') if os.path.isdir(ai_v) and cur != 'ai' else None,
        'open': {'id': op[-1]['id'], 'label': S.label(op[-1]['id']), 'started': op[-1].get('started')} if op else None,
        'latest': {'id': done[-1]['id'], 'label': S.label(done[-1]['id'])} if done else None,
        'unapplied': unapplied(ss),
        'lock': {'pid': h[0], 'what': h[1], 'since': h[2]} if h else None,
        'live_review': job_view(s, live) if live else None,
        'jobs': [job_view(s, j) for j in rj[-8:]],
        'commands': {'reopen': f'python3 review_workorder.py {rel} --reopen', 'sessions': f'python3 review_workorder.py {rel} --sessions'},
    }

# ------------------------------------------------------------------ starting jobs
def start_review(s, run, R, port, src=None, discard_open=False, app_pid=None):
    """Queue Review again (with a pin first when the run has no basis yet). Returns the first job; raises ValueError."""
    rec = load(os.path.join(R, 'record.json')) or {}
    pdf, why = pdf_needed(s, R, rec)
    if why: raise ValueError(why)
    if src not in (None, 'ai') and not re.fullmatch(r'\d{1,3}', str(src)): raise ValueError(f'no such session: {src}')
    back = f'http://127.0.0.1:{port}/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/?after=finish'
    py = [sys.executable, 'review_workorder.py', R]
    argv = py + ['--reopen'] + (['--from', str(src)] if src else []) + (['--discard-open'] if discard_open else []) + \
           (['--pdf', pdf] if pdf else []) + ['--no-browser', '--return-to', back]
    what = ('Review again from the AI\'s decisions' if src == 'ai' else f'Review again from {S.label(f"{int(src):03d}")}' if src else 'Review again')
    review = {'kind': 'review', 'argv': argv, 'env': config.child_env(s), 'counted': False, 'extra': {'what': what, 'app_pid': app_pid}}
    pinned = S.basis(R) and os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json'))
    if pinned:
        return jobs.create(s['jobs'], 'review', run, argv, review['env'], counted=False, R=R, what=what, app_pid=app_pid)
    return jobs.create(s['jobs'], 'pin', run, py + ['--pin'] + (['--pdf', pdf] if pdf else []), config.child_env(s), R=R, then=review,
                       what='Pin the run (a free re-audit), then ' + what[0].lower() + what[1:])

def start_apply(s, run, R):
    rec = load(os.path.join(R, 'record.json')) or {}
    ss = S.sessions(R); u = unapplied(ss)
    if not u:
        fin = [x for x in ss if x.get('status') == 'finished']
        if not fin: raise ValueError('no finished session is waiting to be applied')
        newer = [x for x in ss if x.get('status') == 'applied' and S.sid_n(x['id']) > S.sid_n(fin[-1]['id'])]
        raise ValueError(f'{S.label(fin[-1]["id"])} was replaced by {S.label(newer[-1]["id"]) if newer else "a later session"}: '
                         'Apply is offered only for the newest session')
    pdf, why = pdf_needed(s, R, rec)
    if why: raise ValueError(why)
    argv = [sys.executable, 'review_workorder.py', R, '--apply'] + (['--pdf', pdf] if pdf else [])
    return jobs.create(s['jobs'], 'apply', run, argv, config.child_env(s), R=R, what=f'Apply {u["label"]}')

def stop_review(s, run, R):
    """Stop reviewing: Ctrl+C to the live review child, only while it is before Finish (decided from disk)."""
    j = live_review(s, run)
    if not j: raise ValueError('no review page is open for this run')
    ok, why = jobs.interrupt(s['jobs'], j['id'], s['runs'])
    if not ok: raise ValueError(why)
    return j
