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
import os, re, sys, json, signal, hashlib, datetime, urllib.parse
from review import sessions as S
from lib import dates as D, release as REL
from . import config, jobs, logs

def load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

# ------------------------------------------------------------------ ready to ship, never None or "unknown"
READY_MD = re.compile(r'^\*\*Ready to ship\?\*\*(?: (Yes|No))?\s*$', re.I)   # older runs: "… Yes|No"; from 2026-11 the label alone
STATUS_MD = re.compile(r'^\*\*Status:\*\* (.*?)\s*$')

def ready(R, rec):
    """{'answer': 'Yes' | 'No' | None, 'lines': [...], 'source': ...}: the record's glance, else review.md's Overview, else
    'not recorded for this run'."""
    g = (rec or {}).get('glance')
    if isinstance(g, dict) and isinstance(g.get('ship'), list):
        try:                                   # never a stored `ready`: the PAC and screen-reader lines, ready and the status are
            from lib import glance as G                       # worked out now from release/ (cheap: no PDF is opened)
            from . import manualpage                               # as the evaluation page reads it: a changed file is never Ready (K1)
            g = manualpage.app_glance(R, rec, g) if R and os.path.isdir(R) else G.with_release(g, rec, REL.load(R, rec))
        except (ValueError, KeyError, TypeError, OSError):      # release/ unreadable: never Ready, and never says so (J2)
            g = dict(g, ready=False, status={'name': 'Not Ready', 'text': 'Not Ready (the evaluation records could not be read)',
                                             'current': {'name': 'Not Ready', 'issues': 0}})   # the Ship gate reads it too (L3)
        return {'answer': 'Yes' if g['ready'] else 'No', 'lines': [f'{x["what"]}: {x["text"]}' for x in g.get('ship') or []],
                'status': (g.get('status') or {}).get('text'), 'current': ((g.get('status') or {}).get('current') or {}).get('name') or 'Not Ready',
                'source': 'record.json'}                     # current: the current version's own status (the Ship gate, stage 4; L3)
    try: md = open(os.path.join(R, 'review.md'), encoding='utf-8').read().splitlines()
    except OSError: md = []
    for i, l in enumerate(md):
        m = READY_MD.match(l)
        if m:
            lines = []
            for x in md[i + 1:]:
                if not x.startswith('- '): break
                lines.append(x[2:].removeprefix('✓ '))
            st = next((s.group(1) for x in reversed(md[:i]) if (s := STATUS_MD.match(x))), None)
            # no Yes/No after the label: the status line above it says (Yes only when the status is Ready, as glance's `ready`)
            ans = m.group(1) or ('Yes' if st and st.split(' · ')[0] == 'Ready' else 'No' if st else None)
            return {'answer': ans, 'lines': lines, 'status': st, 'source': 'review.md'}
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
    v = {k: j.get(k) for k in ('id', 'kind', 'run', 'status', 'created', 'started', 'ended', 'exit', 'url', 'paid', 'after', 'then_job', 'note', 'what', 'first')}
    if j.get('child'):                                  # Bring Back an Edited PDF: the new run it made, once there is one
        C = os.path.join(s['runs'], *str(j['child']).split('/'))
        v['child_url'] = run_url(s, C) if os.path.isdir(C) else None
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
    return shown(j.get('what') or {'apply': 'Apply', 'review': 'Review', 'pin': 'Pin', 'ocr': 'Review OCR Text'}.get(j['kind'], j['kind']))

def shown(t):
    """A job line as the panel shows it, formatted when shown (so jobs recorded before the rule read the same): a session
    is "Session N", and the OCR button is "Review OCR Text" (it names the button; "OCR text" for the text itself stays)."""
    t = re.sub(r'\bsession (\d+)', r'Session \1', str(t))
    return t.replace('Review OCR text', 'Review OCR Text')

def ocr_recorded(R, since=''):
    """The OCR verdict recorded since a time (a job's start), for its outcome line: "approved (Kim, 19:30)"; None."""
    v = (((load(os.path.join(R, '_intake', 'intake.json')) or {}).get('review') or {}).get('ocr_text_approved')) if R else None
    if not isinstance(v, dict) or (v.get('recorded') or '') < (since or ''): return None
    return f'{v.get("verdict")} ({v.get("reviewer")}, {D.clock(v.get("recorded"))})'

def result(R, j, v):
    """What came of a job that has ended, in sentence case: "session 3 applied (Kim, 18:19)"; None while it is active."""
    st, out = j['status'], v.get('outcome') or ''
    at = D.clock(j.get('ended')) if D.parse(j.get('ended')) else ''
    when = f' ({at})' if at else ''
    lost = st == 'interrupted' and (v.get('interrupted') or {}).get('state') == 'done'
    if st in ('queued', 'running', 'needs-spend'): return None
    if st == 'failed': return 'failed' + when
    if st == 'interrupted' and not lost: return 'stopped without finishing' + when
    if j['kind'] == 'pin': return 'pinned' + when
    if j['kind'] == 'bring_back':                      # the new run waits for its review (or was applied since)
        lab = str(j.get('child') or '').split('/')[-1] or 'a new run'
        return f'brought back as {lab}' + when
    if j['kind'] == 'discard': return 'discarded' + when
    if j['kind'] == 'ocr':
        got = ocr_recorded(R, j.get('started'))
        return 'closed' + when + (f'; OCR verdict recorded: {got}' if got else '; no verdict recorded')
    if j.get('first') and j['kind'] == 'review':          # a waiting run's first review: Finish writes review.json
        rv = load(os.path.join(R, 'review.json')) if R else None
        return f'review finished ({(rv or {}).get("reviewer") or "reviewer not recorded"}{", " + at if at else ""}), not applied yet' \
            if rv else 'closed without "Finish Review"' + when
    m = SESSION_IN.search(out if out else (v.get('interrupted') or {}).get('text', ''))
    if not m and j.get('first') and j['kind'] == 'apply' and R and os.path.isfile(os.path.join(R, 'record.json')): m = SESSION_IN.search('session 1')
    if not m: return 'done' + when
    sid = f'{int(m.group(1)):03d}'
    who = ((S.session(R, sid) or {}).get('reviewer') if R else None) or 'reviewer not recorded'
    done = 'left open' if out.endswith('stays open') else 'applied'
    return shown(f'{S.label(sid)} {done} (' + (f'{who}, {at}' if done == 'applied' else at or 'time not recorded') + ')')

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
        return {'state': 'none', 'text': 'The OCR Text Review page was closed without "Close Without a Verdict"' + (f'; the verdict recorded is kept: {got}.' if got else '; no verdict was recorded.')}
    ss = S.sessions(R) if R else []
    since = j.get('started') or ''
    applied = [x for x in ss if x.get('status') == 'applied' and (x.get('applied') or '') >= since]
    if os.path.exists(os.path.join(R, 'reviews', 'promoting.json')):
        return {'state': 'apply', 'text': 'The apply stopped partway (reviews/promoting.json is there). Apply finishes it; it may apply the '
                                          'session again. Previous results stay in reviews/versions/.'}
    if applied:
        return {'state': 'done', 'text': f'done (the app lost track of the job): {S.label(applied[-1]["id"])} is the current result'}
    u = unapplied(R)
    if u: return {'state': 'apply', 'text': f'{u["label"].capitalize()} is finished and not applied: Apply applies it.'}
    op = [x for x in ss if x.get('status') == 'open']
    if j['kind'] == 'review' and op: return {'state': 'continue', 'text': f'{S.label(op[-1]["id"]).capitalize()} stays open: Continue review carries on with it.'}
    return {'state': 'none', 'text': 'The run shows no change from this job: start it again.'}

def run_path(run): return os.path.join(*run.split('/'))

# ------------------------------------------------------------------ a PDF edited by hand (handedit.py, docs/hand-edits.md)
def run_url(s, P):
    """The app's page of a run folder under the runs folder, or None (outside it)."""
    rel = os.path.relpath(os.path.abspath(P), os.path.abspath(s['runs']))
    if rel == '.' or rel.startswith('..'): return None
    return '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in rel.split(os.sep)) + '/'

def hand_edits(s, R, rec):
    """The runs made from edited copies of this one (its hand_edits.json children), and the run this one was made from (its
    hand_edit), each with its page; None for a run with neither."""
    kids = []
    busy = {str(j.get('child')) for j in jobs.all_jobs(s['jobs']) if j['kind'] == 'bring_back' and j['status'] in ('queued', 'running')}
    for c in (load(os.path.join(R, 'hand_edits.json')) or {}).get('children') or []:
        P = c.get('run') or ''
        rel = os.path.relpath(os.path.abspath(P), os.path.abspath(s['runs'])).replace(os.sep, '/') if P else ''
        if not P or not os.path.isdir(P): st = 'removed'
        elif os.path.isfile(os.path.join(P, 'record.json')): st = 'finished'
        elif waiting(P): st = 'waiting for its review'
        elif rel in busy: st = 'being prepared'
        else: st = 'not started'                       # brought back with --no-run, or its job failed or was stopped
        to = (load(os.path.join(P, '_handedit', 'hand_edit.json')) or {}).get('to') if st == 'not started' else None
        kids.append({'label': os.path.basename(os.path.normpath(P)) or 'run not recorded', 'when': c.get('when'), 'by': c.get('by'),
                     'note': c.get('note'), 'state': st, 'url': run_url(s, P) if st in ('finished', 'waiting for its review') else None,
                     'startable': st == 'not started' and to == 'review'})
    he = rec.get('hand_edit') or load(os.path.join(R, '_handedit', 'hand_edit.json'))
    parent = None
    if isinstance(he, dict) and (he.get('parent') or {}).get('run'):
        P = he['parent']['run']
        parent = {'label': '/'.join(os.path.normpath(P).split(os.sep)[-2:]), 'url': run_url(s, P) if os.path.isdir(P) else None}
    return {'children': kids, 'parent': parent} if kids or parent else None

def resume_bring_back(s, run, R, label):
    """Start, for an edited copy brought back but never run (handedit.py import --no-run, or a job that failed or was stopped):
    the same import again, which carries on in its folder (same file, same mode). Only a review child: a paid run stays a
    terminal command. The label must be one of this run's children; it is never used as a path on its own."""
    rec = load(os.path.join(R, 'record.json'))
    if not rec: raise ValueError('This run is not finished.')
    kid = next((c for c in (hand_edits(s, R, rec) or {}).get('children') or [] if c['label'] == label), None)
    if not kid: raise ValueError('No edited copy of this run has that name.')
    if kid['state'] != 'not started': raise ValueError(f'"{label}" is {kid["state"]}: there is nothing to start.')
    P = next(c.get('run') for c in (load(os.path.join(R, 'hand_edits.json')) or {}).get('children') or []
             if os.path.basename(os.path.normpath(c.get('run') or '')) == label)
    he = load(os.path.join(P, '_handedit', 'hand_edit.json')) or {}
    if he.get('to') != 'review':
        raise ValueError(f'"{label}" was brought back for the full pipeline (a paid AI call): start it in a terminal with handedit.py.')
    f = os.path.join(P, '_handedit', (he.get('edited') or {}).get('file') or '')
    if not os.path.isfile(f): raise ValueError(f'The edited PDF of "{label}" is missing from its folder: bring it back again.')
    argv = [sys.executable, 'handedit.py', 'import', R, f, '--by', he.get('by') or '', '--note', he.get('note') or '', '--label', label]
    return jobs.create(s['jobs'], 'bring_back', run, argv, config.child_env(s), R=R, what='Bring Back an Edited PDF',
                       child=os.path.relpath(P, s['runs']).replace(os.sep, '/'))

def start_bring_back(s, run, R, name, by, note):
    """Bring Back an Edited PDF: handedit.py import of a PDF in the uploads folder, as a new run beside this one that stops for
    its review (no AI call, $0; a paid run stays a terminal command). Refused, with words for the dialog, before anything runs."""
    rec = load(os.path.join(R, 'record.json'))
    if not rec: raise ValueError('This run is not finished: bring an edited PDF back to a finished run.')
    from . import manualpage as MP
    ds = MP.disk_state(R, rec)
    if ds['missing']: raise ValueError('This run\'s remediated PDF is missing, so an edited copy can\'t be compared with it.')
    if ds['same'] is False:
        raise ValueError('This run\'s own PDF was changed after the run made it. Bring back an edited copy instead, and keep the run\'s PDF as it was made.')
    for v, what in ((by, 'who edited the PDF'), (note, 'what was changed')):
        if not isinstance(v, str) or not v.strip(): raise ValueError(f'Say {what}.')
        if '\n' in v.strip() or len(v.strip()) > 200: raise ValueError(f'Say {what} in one line of at most 200 characters.')
    if not isinstance(name, str) or not name.lower().endswith('.pdf'): raise ValueError('Choose the edited PDF from the uploads folder.')
    p = config.entry(s['uploads'], name) if s.get('uploads') else None   # a name from the uploads listing only, never a path
    if not p or not os.path.isfile(p): raise ValueError(f'"{name}" is not in the uploads folder: save it there, then try again.')
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    if h.hexdigest() == (ds['sha'] or (rec.get('document') or {}).get('output_sha256')):
        raise ValueError(f'"{name}" is the same file as this run\'s result: nothing was edited.')
    import handedit as HE
    base = 'handedit-' + datetime.datetime.now().strftime('%Y%m%d-%H%M'); label, n = base, 1
    while os.path.exists(HE.child_dir(R, rec, label)[0]): n += 1; label = f'{base}-{n}'
    C = HE.child_dir(R, rec, label)[0]
    argv = [sys.executable, 'handedit.py', 'import', R, p, '--by', by.strip(), '--note', note.strip(), '--label', label]
    return jobs.create(s['jobs'], 'bring_back', run, argv, config.child_env(s), R=R, what='Bring Back an Edited PDF',
                       child=os.path.relpath(C, s['runs']).replace(os.sep, '/'))

def prune_plan(R):
    """"Clean Up Space": the previous versions whose PDF may be removed (review/prune.py plan, hashed through the app's
    display cache), or None when there are none. Sizes in words; each chosen version's hash goes back with the POST, so a
    changed one is refused."""
    from review import prune
    from . import manualpage
    try: items = prune.plan(R, sha=manualpage.disk_sha)
    except (OSError, ValueError): return None
    if not items: return None
    from lib import dates as D, release as REL
    mb = lambda n: f'{n / 1e6:.1f} MB'
    return {'versions': [{'id': x['id'], 'sha256': x['sha256'], 'label': x['label'] + (f', applied on {D.day(x["applied"])}' if x.get('applied') else ''),
                          'size': mb(x['bytes']), 'bytes': x['bytes']} for x in items]}

def manual_strip(R, rec):
    """The Manual Checks strip after "Ready to Ship?" (webapp/manualpage.py strip()); None for a run it cannot read."""
    from . import manualpage
    try: return manualpage.strip(R, rec)
    except (OSError, ValueError, KeyError, TypeError): return None

def unapplied(R, rec=None):
    """The session Apply is offered for (review/sessions.py newer(), the rule the manual checks' refusal shares): the
    newest finished session newer than the current result, when no applied one is newer. A finished session that a later
    one replaced (its apply failed, then the person reviewed again) is never offered."""
    x = S.newer(R, rec)['finished']
    return {'id': x['id'], 'label': S.label(x['id']), 'finished': x.get('finished')} if x else None

def state(s, run, R):
    rec = load(os.path.join(R, 'record.json')) or {}
    ss = S.sessions(R); cur = S.current_id(rec)
    vers = S.P(R)['versions']
    gone = {str(x.get('version')) for x in REL.removed(R)}              # "Clean Up Space" took their PDF: the row stays, marked
    rows, nm = [], S.no_model(R)                       # no AI call (a PDF edited by hand): "the beginning", never "the AI's"
    for x in ss:
        r = S.summary_row(x)
        if x.get('status') == 'open': r.update(S.name_notes(load(S.P(R)['draft']), x['id']))   # the open session: as last saved
        v = os.path.join(vers, x['id'])
        rows.append({**r, 'current': x['id'] == cur, 'from_label': S.from_label(r['from'], nm), 'label': S.label(x['id']), 'pdf_removed': x['id'] in gone,
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
        'unapplied': unapplied(R, rec),
        'ocr': ocr_state(R),
        'manual': manual_strip(R, rec),
        'prune': prune_plan(R),
        'hand_edits': hand_edits(s, R, rec), 'no_model': nm,
        'lock': {'pid': h[0], 'what': h[1], 'since': h[2], 'words': jobs.lock_words(h[1], h[2])} if h else None,
        'live_review': job_view(s, live) if live else None,
        'jobs': [job_view(s, j) for j in rj],               # every job of the run: the page folds the earlier ones, none drop off
        'commands': {'reopen': f'python3 review_workorder.py {rel} --reopen', 'sessions': f'python3 review_workorder.py {rel} --sessions'},
        'batch': run.split('/')[1] if run.startswith('batches/') and len(run.split('/')) == 3 and
                 os.path.isfile(os.path.join(os.path.dirname(R), 'summary.html')) else None,
    }

# ------------------------------------------------------------------ a run stopped for its first review (REVIEW=1)
def waiting(R):
    """A run run_api.sh stopped for its first review (REVIEW=1): the AI's decisions kept, nothing applied, no record yet."""
    return not os.path.isfile(os.path.join(R, 'record.json')) and os.path.isfile(os.path.join(R, 'workorder.ai.json'))

def first_original(s, R):
    """(the original PDF, None) for a waiting run's first apply, or (None, refusal). The path run_api.sh kept at the stop
    (review_stop.json) when it still holds the same file; else the file with the same sha256 in samples/ or uploads/."""
    intake = load(os.path.join(R, '_intake', 'intake.json')) or {}
    o = intake.get('original') or {}
    sha, name = o.get('sha256'), o.get('file')
    if not sha:                                          # intake off: the audit was made from the original itself
        src = ((load(os.path.join(R, '_audit', 'digest.json')) or {}).get('source') or {})
        sha, name = src.get('sha256'), src.get('file')
    if not sha: return None, 'This run doesn\'t say which PDF it was made from, so its original PDF can\'t be found.'
    p = (load(os.path.join(R, 'review_stop.json')) or {}).get('src')
    if p and os.path.isfile(p) and S.sha_file(p) == sha: return p, None
    p = find_original(s, sha, name)
    if p: return p, None
    return None, (f'The book\'s original PDF ({name or "its file"}) wasn\'t found in the folder of original PDFs or of uploads. '
                  'Put a copy of it in one of them, then try again.')

def waiting_title(run, R):
    """A waiting run's heading: the original's file name (intake's record, else the path kept at the stop), else the run."""
    o = (load(os.path.join(R, '_intake', 'intake.json')) or {}).get('original') or {}
    return o.get('file') or os.path.basename((load(os.path.join(R, 'review_stop.json')) or {}).get('src') or '') or run

def waiting_state(s, run, R):
    """The panel's view of a waiting run: whether its review is finished (review.json), and its jobs. No result, no
    sessions and no evaluation yet: those come with the first apply."""
    rv = load(os.path.join(R, 'review.json')) or {}
    live = live_review(s, run)
    return {'run': run, 'title': waiting_title(run, R),
            'waiting': {'reviewed': bool(rv), 'reviewer': rv.get('reviewer'), 'date': rv.get('date'),
                        'prepared': os.path.isfile(os.path.join(R, 'review_items.json'))},
            'live_review': job_view(s, live) if live else None,
            'jobs': [job_view(s, j) for j in jobs.all_jobs(s['jobs']) if j['run'] == run]}

def start_first_review(s, run, R, port, app_pid=None):
    """Open the Review Page for a waiting run: review_workorder.py <run> --serve, as the terminal's step 1."""
    if os.path.isfile(os.path.join(R, 'review.json')): raise ValueError('The review is finished: "Apply" applies it.')
    if not os.path.isfile(os.path.join(R, 'review_items.json')):
        raise ValueError('The review page was not prepared when this run stopped, so it can\'t be opened. Run the book again.')
    back = f'http://127.0.0.1:{port}/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/?after=finish'
    argv = [sys.executable, 'review_workorder.py', R, '--serve', '--no-browser', '--return-to', back]
    return jobs.create(s['jobs'], 'review', run, argv, config.child_env(s), counted=False, R=R, what='Review the edited PDF' if S.no_model(R) else 'Review the AI\'s decisions',
                       app_pid=app_pid, first=True)

def start_first_apply(s, run, R):
    """Apply for a waiting run, after Finish Review: run_api.sh's second call (the same command the terminal is told to
    run), in this run's folder (RUN_DIR) with the settings it stopped with (review_stop.json)."""
    if not os.path.isfile(os.path.join(R, 'review.json')): raise ValueError('Finish the review first: "Open the Review Page," then "Finish Review."')
    src, why = first_original(s, R)
    if why: raise ValueError(why)
    stop = load(os.path.join(R, 'review_stop.json')) or {}
    env = {'RUN_DIR': R, **{k: v for k, v in (stop.get('env') or {}).items() if k in ('OCR_LANG', 'INTAKE_REUSE', 'INTAKE', 'OUT') and v}}
    argv = ['bash', 'run_api.sh', src, stop.get('name') or os.path.basename(os.path.dirname(R)), os.path.basename(R)]
    return jobs.create(s['jobs'], 'apply', run, argv, config.child_env(s, env), env_set=env, R=R, what='Apply session 1', first=True)

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
    start = 'the beginning' if S.no_model(R) else 'the AI\'s decisions'   # no AI call: a PDF edited by hand
    what = (f'Review again from {start}' if src == 'ai' else f'Review again from {S.label(f"{int(src):03d}")}' if src else
            f'Continue review ({S.label(op[-1]["id"]).capitalize()})' if op else f'Review again from {S.label(done[-1]["id"])}' if done else
            f'Review again from {start}')
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
    """Queue Review OCR Text: the OCR-only page (review_ocr.py --serve), which waits on a person, so it is not counted in
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
    return jobs.create(s['jobs'], 'ocr', run, argv, config.child_env(s), counted=False, R=R, what='Review OCR Text', app_pid=app_pid)

def start_apply(s, run, R):
    rec = load(os.path.join(R, 'record.json')) or {}
    ss = S.sessions(R); u = unapplied(R, rec)
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
        raise ValueError('The review page is open: select "Stop Reviewing" first, then "' + (f'Discard {S.label(op[-1]["id"]).capitalize()}' if op else 'Discard') + '."')
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
