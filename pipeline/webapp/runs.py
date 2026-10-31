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
import os, re, sys, json, signal, urllib.parse
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
    if not sha: return None, 'This run\'s record doesn\'t say which PDF it was made from, so its original PDF can\'t be found.'
    p = find_original(s, sha, name)
    if p: return p, None
    return None, (f'The book\'s original PDF ({name or "its file"}) wasn\'t found in the folder of original PDFs or of uploads. '
                  'Put a copy of it in one of them, then try again.')

# ------------------------------------------------------------------ the panel's view of a run
def live_review(s, run):
    """The run's open review page: a work-order review, or the OCR-only page (review_ocr.py --serve)."""
    for j in reversed(jobs.all_jobs(s['jobs'])):
        if j['run'] == run and j['kind'] in jobs.PERSON and j['status'] == 'running': return j
    return None

def job_view(s, j, with_text=False, offset=0):
    """A job for the page: no environment, no log lines and no command (the page shows none: the log stays on disk, at
    `log`); its steps in plain words, the step running now, its title (what happened), and for a failure the reason."""
    text = jobs.read_log(s['jobs'], j['id'])[0]
    R = jobs.run_dir(j, s['runs'])
    v = {k: j.get(k) for k in ('id', 'kind', 'run', 'status', 'created', 'started', 'ended', 'exit', 'url', 'paid', 'after', 'then_job', 'note', 'what')}
    steps = logs.steps(text)
    v.update(position=jobs.position(s['jobs'], j['id']), steps=[dict(x, words=logs.plain(x['label'])) for x in steps], outcome=logs.outcome(text),
             log=shown_path(jobs.log_path(s['jobs'], j['id'])))
    if j['kind'] in jobs.PERSON and j['status'] == 'running':      # the OCR-only page has no Finish
        v['past_finish'] = j['kind'] == 'review' and jobs.review_past_finish(R, j.get('started'))
    if j['status'] == 'interrupted' and j['kind'] in ('apply', 'review', 'ocr'):
        v['interrupted'] = after_interrupt(R, j)
    v['step'] = logs.now_step(j['kind'], steps) if j['status'] == 'running' else None
    v['title'] = title(R, j, v); v['action'] = action(j); v['result'] = result(R, j, v)
    v['reason'] = reason(v) if j['status'] in ('failed', 'interrupted') else None
    if with_text:
        t, nxt = jobs.read_log(s['jobs'], j['id'], offset); v.update(text=t, next=nxt)
    return v

def shown_path(p):
    """A file's path as a person reads it: from the repo root (runs/.app/jobs/…) when it is inside it, else absolute."""
    p = os.path.abspath(p)
    return os.path.relpath(p, config.ROOT) if p.startswith(config.ROOT + os.sep) else p

SESSION_IN = re.compile(r'session (\d+)')

def action(j):
    """The job's action, as it was asked for: "Review again from session 2"."""
    return j.get('what') or {'apply': 'Apply', 'review': 'Review', 'pin': 'Pin', 'ocr': 'Review OCR text'}.get(j['kind'], j['kind'])

def ocr_recorded(R, since=''):
    """The OCR verdict recorded since a time (a job's start), for its outcome line: "approved (Kim, 19:30)"; None."""
    v = (((load(os.path.join(R, '_intake', 'intake.json')) or {}).get('review') or {}).get('ocr_text_approved')) if R else None
    if not isinstance(v, dict) or (v.get('recorded') or '') < (since or ''): return None
    return f'{v.get("verdict")} ({v.get("reviewer")}, {(v.get("recorded") or "")[11:16] or "time not recorded"})'

def result(R, j, v):
    """What came of a job that has ended, in sentence case: "session 3 applied (Kim, 18:19)"; None while it is active."""
    st, out = j['status'], v.get('outcome') or ''
    at = (j.get('ended') or '')[11:16]
    when = f' ({at})' if at else ''
    lost = st == 'interrupted' and (v.get('interrupted') or {}).get('state') == 'done'
    if st in ('queued', 'running', 'needs-spend'): return None
    if st == 'failed': return 'failed' + when
    if st == 'interrupted' and not lost: return 'stopped without finishing' + when
    if j['kind'] == 'pin': return 'pinned' + when
    if j['kind'] == 'discard': return 'discarded' + when
    if j['kind'] == 'ocr':
        got = ocr_recorded(R, j.get('started'))
        return 'closed' + when + (f'; OCR verdict recorded: {got}' if got else '; no verdict recorded')
    m = SESSION_IN.search(out if out else (v.get('interrupted') or {}).get('text', ''))
    if not m: return 'done' + when
    sid = f'{int(m.group(1)):03d}'
    who = ((S.session(R, sid) or {}).get('reviewer') if R else None) or 'reviewer not recorded'
    done = 'left open' if out.endswith('stays open') else 'applied'
    return f'{S.label(sid)} {done} (' + (f'{who}, {at}' if done == 'applied' else at or 'time not recorded') + ')'

def title(R, j, v):
    """What the job did, in one line (sentence case, for "Last Job:" and Previous Jobs):
    "Review again from session 2 → session 3 applied (Kim, 18:19)". A job card shows the two halves apart."""
    r = result(R, j, v)
    return action(j) + (f' → {r}' if r else '')

def reason(v):
    """A failed or interrupted job's reason, in the tool's own words where it gave one, never log lines."""
    if v.get('interrupted'): return v['interrupted']['text']
    if v['status'] == 'interrupted': return 'The job stopped without finishing (the computer restarted, or the job was stopped).'
    out = v.get('outcome') or ''
    if S.FALLBACK.split('.')[0] in out: return S.FALLBACK_PAGE     # the pin refused: the command stays in the job's log
    if out.startswith('refused: '): return out[len('refused: '):][:1].upper() + out[len('refused: ') + 1:]
    return f'The command ended with an error (exit {v.get("exit")}).'

def after_interrupt(R, j):
    """An interrupted apply or review: what is left, from the run's state on disk, not from the job status (a killed wrapper
    can leave its command to finish alone). {state: apply | done | continue | none, text}."""
    if j['kind'] == 'ocr':                             # nothing to finish: a verdict is written whole or not at all
        got = ocr_recorded(R, j.get('started'))
        return {'state': 'none', 'text': 'The OCR review page closed without Close' + (f'; the verdict recorded is kept: {got}.' if got else '; no verdict was recorded.')}
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
        if x.get('status') == 'open': r.update(S.name_notes(load(S.P(R)['draft']), x['id']))   # the open session: as last saved
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
        'ocr': ocr_state(R),
        'lock': {'pid': h[0], 'what': h[1], 'since': h[2], 'words': jobs.lock_words(h[1], h[2])} if h else None,
        'live_review': job_view(s, live) if live else None,
        'jobs': [job_view(s, j) for j in rj],               # every job of the run: the page folds the earlier ones, none drop off
        'commands': {'reopen': f'python3 review_workorder.py {rel} --reopen', 'sessions': f'python3 review_workorder.py {rel} --sessions'},
        'batch': run.split('/')[1] if run.startswith('batches/') and len(run.split('/')) == 3 and
                 os.path.isfile(os.path.join(os.path.dirname(R), 'summary.html')) else None,
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
    ss = S.sessions(R); op = [x for x in ss if x.get('status') == 'open']; done = [x for x in ss if x.get('status') in ('finished', 'applied')]
    what = ('Review again from the AI\'s decisions' if src == 'ai' else f'Review again from {S.label(f"{int(src):03d}")}' if src else
            f'Continue review ({S.label(op[-1]["id"]).capitalize()})' if op else f'Review again from {S.label(done[-1]["id"])}' if done else
            'Review again from the AI\'s decisions')
    review = {'kind': 'review', 'argv': argv, 'env': config.child_env(s), 'counted': False, 'extra': {'what': what, 'app_pid': app_pid}}
    pinned = S.basis(R) and os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json'))
    if pinned:
        return jobs.create(s['jobs'], 'review', run, argv, review['env'], counted=False, R=R, what=what, app_pid=app_pid)
    return jobs.create(s['jobs'], 'pin', run, py + ['--pin'] + (['--pdf', pdf] if pdf else []), config.child_env(s), R=R, then=review,
                       what='Pin the run (a free re-audit), then ' + what[0].lower() + what[1:])

def ocr_state(R):
    """{needed, verdict, recorded} for the panel: Review OCR Text is offered when needed; `recorded` changing tells the run
    page that its report is older than the verdict. None when the run has no intake."""
    intake = load(os.path.join(R, '_intake', 'intake.json'))
    if not intake: return None
    from review import ocr as O
    v = (intake.get('review') or {}).get('ocr_text_approved')
    return {'needed': O.needed(intake), 'verdict': v.get('verdict') if isinstance(v, dict) else None,
            'recorded': v.get('recorded') if isinstance(v, dict) else None}

def start_ocr(s, run, R, port, app_pid=None):
    """Queue Review OCR text: the OCR-only page (review_ocr.py --serve), which waits on a person, so it is not counted in
    max_jobs. Refused when the book needs no OCR approval, or when the run has no intake.pdf and no original is found."""
    st = ocr_state(R)
    if not st or not st['needed']: raise ValueError('This book has no OCR text that needs approval.')
    rec = load(os.path.join(R, 'record.json')) or {}
    argv = [sys.executable, 'review_ocr.py', R, '--serve', '--no-browser', '--return-to',
            f'http://127.0.0.1:{port}/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/']
    if not os.path.isfile(os.path.join(R, '_intake', 'intake.pdf')):
        doc = rec.get('document') or {}
        pdf = find_original(s, doc.get('sha256'), doc.get('file'))
        if not pdf: raise ValueError(f'The book\'s original PDF ({doc.get("file") or "its file"}) wasn\'t found in the folder of original PDFs, '
                                     'so its pages can\'t be shown.')
        argv += ['--pdf', pdf]
    return jobs.create(s['jobs'], 'ocr', run, argv, config.child_env(s), counted=False, R=R, what='Review OCR text', app_pid=app_pid)

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

def start_discard(s, run, R):
    """Discard Session N: the open session marked abandoned (review_workorder.py --discard-open on its own; nothing
    deleted, the current result unchanged). Refused while its review page is open (Stop it first) or past Finish."""
    j = live_review(s, run)
    if j:
        if jobs.review_past_finish(jobs.run_dir(j, s['runs']), j.get('started')):
            raise ValueError('This review is past "Finish Review" and is being applied: it can\'t be discarded now.')
        op = [x for x in S.sessions(R) if x.get('status') == 'open']
        raise ValueError('The review page is open: press "Stop Reviewing" first, then "' + (f'Discard {S.label(op[-1]["id"]).capitalize()}' if op else 'Discard') + '".')
    op = [x for x in S.sessions(R) if x.get('status') == 'open']
    if not op: raise ValueError('no session is open')
    argv = [sys.executable, 'review_workorder.py', R, '--discard-open']
    return jobs.create(s['jobs'], 'discard', run, argv, config.child_env(s), R=R, what=f'Discard {S.label(op[-1]["id"])}')

def stop_review(s, run, R):
    """Stop reviewing: Ctrl+C to the live review child, only while it is before Finish (decided from disk)."""
    j = live_review(s, run)
    if not j: raise ValueError('no review page is open for this run')
    ok, why = jobs.interrupt(s['jobs'], j['id'], s['runs'])
    if not ok: raise ValueError(why)
    return j

STOPPABLE = ('reopen', 'ocr review')                   # lock holders that serve a review page (Ctrl+C closes it, nothing lost)

def stop_other(s, run, R):
    """Stop the Other Review: Ctrl+C to the review process holding reviews/.lock that the app did not start (a terminal's
    review_workorder.py --reopen or review_ocr.py --serve), as Stop does for the app's own; refused past Finish, for an
    apply or a discard, and when the app's own job holds it (its card has Stop)."""
    if live_review(s, run): raise ValueError('This review was started here: use "Stop Reviewing" on its card.')
    h = jobs.lock_holder(R)                            # alive and a review process (review/sessions.py review_process)
    if not h: raise ValueError('No other review of this run is open now.')
    pid, what, since = h
    if what not in STOPPABLE: raise ValueError(jobs.lock_words(what, since))
    if jobs.review_past_finish(R, since): raise ValueError('This review is past "Finish Review" and is being applied: it can\'t be stopped now.')
    try: os.kill(int(pid), signal.SIGINT)
    except OSError: raise ValueError('The other review could not be reached; it may have just ended.')
    return {'pid': pid, 'what': what}
