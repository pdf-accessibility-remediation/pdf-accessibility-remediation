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
from . import config, jobs, logs, books as BK

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
    """A PDF in samples/ or uploads/ whose sha256 is sha (files named `name` are tried first), or None. Dot-folders are
    left out (uploads/.incoming holds unfinished uploads); hashes come from the shared cache (webapp/books.py hashes)."""
    from . import books
    cands = books.pdfs_in(s['samples']) + books.pdfs_in(s['uploads'])
    cands.sort(key=lambda p: (os.path.basename(p) != name, p))
    found = []
    books.hashes(s, cands, stop=lambda p, h: h == sha and not found.append(p))
    return found[0] if found else None

def own_pdf(R):
    """The run's own original PDF (R17: <run>/source/), or None: a run made before R17 finds its original by sha256."""
    return S.own_source(R)

def own_sha(s, R):
    p = own_pdf(R)
    if not p: return None
    from . import books as BK
    return BK.hashes(s, [p]).get(p)

def input_of(R, rec):
    """Where this run's next review reads its PDF from, before any search (shared by pdf_needed and the Trash's per-run
    warning, webapp/trash.py effect): {'kind': 'copy'} its own intake copy; {'kind': 'path', 'path'} the existing file its
    review basis names (for a tagged PDF, the original itself); {'kind': 'lost', 'why'} its own intake result is missing;
    {'kind': 'unknown', 'why'} its record names no sha256; {'kind': 'find', 'sha', 'name'} the original, found by sha256."""
    b = S.basis(R)
    if b and os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json')):
        if os.path.isfile(os.path.join(R, '_intake', 'intake.pdf')): return {'kind': 'copy'}
        inp = b.get('input') or {}
        if inp.get('path') and os.path.isfile(inp['path']): return {'kind': 'path', 'path': inp['path']}
        sha = inp.get('sha256')
        if inp.get('path') and os.path.basename(os.path.dirname(inp['path'])) == '_intake':     # the run's own intake result
            return {'kind': 'lost', 'why': (f'this run\'s input, {inp["path"]} (its intake result, sha256 {(sha or "")[:16]}), is missing: it was made by '
                                            'intake and is not in samples/; the run cannot be reviewed again without it')}
    else:
        if ((rec.get('intake') or {}).get('result') or {}).get('pdf'): return {'kind': 'copy'}
        sha = ((rec.get('workorder') or {}).get('source') or {}).get('sha256') or (rec.get('document') or {}).get('sha256')
    if not sha: return {'kind': 'unknown', 'why': 'This run\'s record doesn\'t say which PDF it was made from, so its original PDF can\'t be found.'}
    return {'kind': 'find', 'sha': sha, 'name': (rec.get('document') or {}).get('file')}

def pdf_needed(s, R, rec):
    """(--pdf path or None, refusal or None) for this run's next review command."""
    i = input_of(R, rec)
    if i['kind'] in ('copy', 'path'): return None, None
    if i['kind'] in ('lost', 'unknown'): return None, i['why']
    sha, name = i['sha'], i['name']
    if own_sha(s, R) == sha: return own_pdf(R), None       # R17: the run's own copy
    p = find_original(s, sha, name)
    if p: return p, None
    if moved_words(s, sha): return None, moved_words(s, sha)
    return None, (f'The book\'s original PDF ({name or "its file"}) wasn\'t found in the folder of original PDFs or of uploads. '
                  'Put a copy of it in one of them, then try again.')

MOVED = ('The original PDF was moved to the Trash. "Review Again" needs it back: drag it from the Trash into the app\'s folder '
         'of added PDFs (where it was), then try again.')
def moved_words(s, sha):
    """The plain sentence for an original PDF a person moved to the Trash (#45 D8), when the app's move log says so."""
    from . import trash as TR
    return MOVED if sha and TR.moved_pdf(s, sha) else None

# ------------------------------------------------------------------ the panel's view of a run
def live_review(s, run):
    """The run's open review page: a work-order review, or the OCR-only page (review_ocr.py --serve)."""
    for j in reversed(jobs.all_jobs(s['jobs'])):
        if j['run'] == run and j['kind'] in jobs.PERSON and j['status'] == 'running': return j
    return None

SEEN_MAX = 500                                          # ids a lighter check reads (the parameter is cut at 40 characters each)
JOB_ID = re.compile(r'[0-9A-Za-z_-]{1,64}')

def view_context(s, nm=None):
    """One answer's view of the queue (#93, fix 1): the jobs read once (through the request's names snapshot nm), each queued
    job's place in line (1-based, in the jobs folder's order, as jobs.position() and tick() count it: every job, not only
    the ones the answer shows), the running batch and the running counted jobs (what a queued job waits for)."""
    from . import names as NM
    nm = nm or NM.snapshot(s); al = nm.jobs()
    q = [j['id'] for j in al if j['status'] == 'queued']
    return {'nm': nm, 'pos': {jid: i + 1 for i, jid in enumerate(q)},
            'batch': next((x for x in al if x['status'] == 'running' and x['kind'] == 'batch'), None),
            'running': [x for x in al if x['status'] == 'running' and x.get('counted', True)]}

def changing_jobs(al, seen=''):
    """The home page's lighter check (#93, fix 3; review 02 H1): every job whose status can still change (jobs.can_change),
    and every job named in seen (the ids the page last saw in one of those statuses), in the jobs' own order. seen is cut
    at SEEN_MAX × 40 characters before it is split, only its first SEEN_MAX ids are read, each must be job-id characters,
    and an id is only compared with the jobs' own (never joined onto a path)."""
    want = {x for x in str(seen or '')[:SEEN_MAX * 40].split(',')[:SEEN_MAX] if JOB_ID.fullmatch(x)}
    return [j for j in al if jobs.can_change(j) or j['id'] in want]

def job_view(s, j, with_text=False, offset=0, ctx=None):
    """A job for the page: no environment, no log lines and no command (the page shows none: the log stays on disk, at
    `log`); its steps in plain words, the step running now, its title (what happened), and for a failure the reason.
    ctx: the answer's view_context() (the jobs check), so the queue and the names are read once for every job in it."""
    from . import names as NM
    nm = ctx['nm'] if ctx else NM.snapshot(s)
    text = jobs.read_log(s['jobs'], j['id'], job=j if ctx else None)[0]
    R = jobs.run_dir(j, s['runs'])
    v = {k: j.get(k) for k in ('id', 'kind', 'run', 'status', 'created', 'started', 'ended', 'exit', 'url', 'paid', 'after', 'then_job', 'note', 'what', 'first',
                               'book_name', 'run_name')}
    if j['kind'] in ('estimate', 'batch-estimate') and j['status'] == 'failed' and j.get('exit') == 4:
        v['status'] = 'done'                                       # D4: stopped to ask the language (run_api.sh exit 4), not a failure
    if j.get('child'):                                  # Bring Back an Edited PDF: the new run it made, once there is one
        C = os.path.join(s['runs'], *str(j['child']).split('/'))
        v['child_url'] = run_url(s, C) if os.path.isdir(C) else None
    steps = logs.steps(text)
    v.update(position=ctx['pos'].get(j['id']) if ctx else jobs.position(s['jobs'], j['id']), steps=[dict(x, words=logs.plain(x['label'])) for x in steps], outcome=logs.outcome(text),
             log=shown_path(jobs.log_path(s['jobs'], j['id'])))
    if j['kind'] in jobs.PERSON and j['status'] == 'running':      # the OCR-only page has no Finish
        v['past_finish'] = j['kind'] == 'review' and jobs.review_past_finish(R, j.get('started'))
    if j['status'] == 'interrupted' and j['kind'] in ('apply', 'review', 'ocr'):
        v['interrupted'] = after_interrupt(R, j)
    v['step'] = logs.now_step(j['kind'], steps) if j['status'] == 'running' else None
    v['title'] = title(R, j, v); v['action'] = action(j); v['result'] = result(R, j, v)
    if j.get('book_sha'): v['book_name'] = nm.book_name(j['book_sha'], j.get('book_file'))
    elif j['kind'] == 'batch': v['book_name'] = 'Batch ' + nm.shown_run(j['run'])
    v['run_name'] = nm.shown_run(j['run'])
    if j['status'] == 'queued':                                    # what it waits for, by its plain name (Patrick, 2026-11-06)
        if ctx: cur = ctx['batch'] or next((x for x in ctx['running'] if jobs.related(x['run'], j['run'])), None)
        else:
            al = nm.jobs()                                         # a batch runs alone (D1): a run waits for it by name;
            cur = next((x for x in al if x['status'] == 'running' and x['kind'] == 'batch'), None) or \
                  next((x for x in al if x['status'] == 'running' and x.get('counted', True) and jobs.related(x['run'], j['run'])), None)
        if cur: v['waiting_for'] = ('the batch ' if cur['kind'] == 'batch' or cur['run'].startswith('batches/') else 'the run ') + \
                                   f'"{nm.shown_run(cur["run"])}"'      #   else its place in line (3 runs at once)
    ds = designed_stop(j)                                          # U4: a designed stop is never Failed
    if ds: v['status'] = 'done' if ds == 'asked' else 'stopped'
    v['reason'] = reason(v) if v['status'] in ('failed', 'interrupted') else None
    v['detail'] = {'exit': j.get('exit'), 'log': v.get('log')} if v['status'] in ('failed', 'interrupted') else None   # folded "Details" only
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
    return shown(j.get('what') or {'apply': 'Apply', 'review': 'Review', 'pin': 'Pin', 'ocr': 'Review OCR Text', 'estimate': 'Get the estimate',
                                    'spend': 'Start remediation: the AI request', 'rerun': 'Try again', 'batch': 'Run the batch'}.get(j['kind'], j['kind']))

def shown(t):
    """A job line as the panel shows it, formatted when shown (so jobs recorded before the rule read the same): a session
    is "Session N", and the OCR button is "Review OCR Text" (it names the button; "OCR text" for the text itself stays)."""
    t = re.sub(r'\bsession (\d+)', r'Session \1', str(t)).replace('the AI call', 'the AI request')   # a job recorded before the wording changed
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
    if st == 'superseded': return ('dismissed' if j.get('note') == 'dismissed' else 'replaced by a new estimate') + when
    if j['kind'] in ('estimate', 'batch-estimate') and j['status'] == 'failed' and j.get('exit') == 4:
        return 'stopped to ask the language of the scanned pages' + when
    if designed_stop(j) == 'stopped': return 'stopped for a person (see why on this page)' + when
    if st == 'failed': return 'failed' + when
    if j['kind'] in ('estimate', 'batch-estimate') and st == 'done': return 'estimate ready' + when
    if j['kind'] in ('spend', 'rerun', 'replay') and st == 'done':
        return ('stopped for review' if R and os.path.isfile(os.path.join(R, 'workorder.ai.json')) and not os.path.isfile(os.path.join(R, 'record.json'))
                else 'finished') + when
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
        tj = j.get('then_job') or ''
        after = '; its apply started' if re.fullmatch(r'\d{8}-\d{6}-\d+-apply', tj) else '; its apply couldn\'t start' if tj == 'refused' else \
                ', applied next' if j.get('auto_apply') and tj in ('', 'starting') else ', not applied yet'          # D3
        return f'review finished ({(rv or {}).get("reviewer") or "reviewer not recorded"}{", " + at if at else ""}){after}' \
            if rv else 'closed without "Finish Review"' + when
    m = SESSION_IN.search(out if out else (v.get('interrupted') or {}).get('text', ''))
    if not m and j.get('first') and j['kind'] == 'apply' and R and os.path.isfile(os.path.join(R, 'record.json')): m = SESSION_IN.search('session 1')
    if not m: return 'done' + when
    sid = f'{int(m.group(1)):03d}'
    who = ((S.session(R, sid) or {}).get('reviewer') if R else None) or 'reviewer not recorded'
    done = 'left open' if out.endswith('stays open') else 'applied'
    return shown(f'{S.label(sid)} {done} (' + (f'{who}, {at}' if done == 'applied' else at or 'time not recorded') + ')')

STOP_KINDS = ('estimate', 'batch-estimate', 'spend', 'rerun', 'replay')
def designed_stop(j):
    """A job that ended by design, not by an error (U4, Patrick 2026-11-07): 'asked' (run_api.sh exit 4: stopped to ask the
    language of the scanned pages) or 'stopped' (exit 3: intake stopped the PDF for a person, e.g. no page to tag, a
    password, PDF 2.0); None otherwise. Never shown or counted as Failed."""
    if j.get('status') != 'failed' or j.get('kind') not in STOP_KINDS: return None
    return {4: 'asked', 3: 'stopped'}.get(j.get('exit')) if j['kind'] in ('estimate', 'batch-estimate') or j.get('exit') == 3 else None

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
    if out.startswith('refused: '):                          # the tool's own words, without its exit code (under "Details", U4)
        x = re.sub(r'\s*\(exit \d+\)', '', out[len('refused: '):]); return x[:1].upper() + x[1:]
    return 'The command ended with an error.'          # its exit code and log are under "Details" (U4)

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
        return {'state': 'apply', 'text': 'The apply stopped partway. "Try Again" finishes it; it may apply the '
                                          'session again. Previous results stay in reviews/versions/.'}
    if applied:
        return {'state': 'done', 'text': f'done (the app lost track of the job): {S.label(applied[-1]["id"])} is the current result'}
    u = unapplied(R)
    if u: return {'state': 'apply', 'text': f'{u["label"].capitalize()} is finished and not applied: "Try Again" applies it.'}
    op = [x for x in ss if x.get('status') == 'open']
    if j['kind'] == 'review' and op: return {'state': 'continue', 'text': f'{S.label(op[-1]["id"]).capitalize()} stays open: Continue review carries on with it.'}
    return {'state': 'none', 'text': 'The run shows no change from this job: start it again.'}

def run_path(run): return os.path.join(*run.split('/'))

# ------------------------------------------------------------------ a PDF edited by hand (handedit.py, docs/hand-edits.md)
def edited_dir(s):
    """Where Bring Back an Edited PDF keeps its uploads: the uploads folder's .edited/, a dot-folder, so an edited copy is
    never listed as a book to remediate, searched as an original or offered by the Trash (webapp/books.py pdfs_in)."""
    return os.path.join(s['uploads'], '.edited')

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
    if REL.cleared(R): raise ValueError('This book\'s working files were cleared, so an edited copy can\'t be compared with its result.')
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
    if REL.cleared(R): raise ValueError('This book\'s working files were cleared, so an edited copy can\'t be compared with its result.')
    from . import manualpage as MP
    ds = MP.disk_state(R, rec)
    if ds['missing']: raise ValueError('This run\'s remediated PDF is missing, so an edited copy can\'t be compared with it.')
    if ds['same'] is False:
        raise ValueError('This run\'s own PDF was changed after the run made it. Bring back an edited copy instead, and keep the run\'s PDF as it was made.')
    for v, what in ((by, 'who edited the PDF'), (note, 'what was changed')):
        if not isinstance(v, str) or not v.strip(): raise ValueError(f'Say {what}.')
        if '\n' in v.strip() or len(v.strip()) > 200: raise ValueError(f'Say {what} in one line of at most 200 characters.')
    if not isinstance(name, str) or not name.lower().endswith('.pdf'): raise ValueError('Choose the edited PDF from the uploads folder.')
    p = config.entry(edited_dir(s), name) if s.get('uploads') else None   # a name from the folder's listing only, never a path
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

def cleared_view(R):
    """A cleared book's note for the panel: when, by whom, the shipment, the space freed; or None."""
    c = REL.cleared(R)
    if not c: return None
    return {'state': c.get('state'), 'day': D.day(c.get('cleared') or c.get('planned')), 'by': c.get('by'), 'shipment': c.get('shipment'),
            'mb': round((c.get('freed_bytes') or 0) / 1e6, 1)}

def clear_offer(s, run, R, rec):
    """"Clear This Book's Files" (#45, review/clear.py): offered only when its gate is open (never prompted elsewhere), with
    what goes and what stays in words and sizes. Hashes come from the app's display cache; the clear itself hashes afresh."""
    from review import clear as CL
    from . import manualpage
    try:
        g = CL.gate(R, rec, sha=manualpage.disk_sha, busy=lambda: jobs.busy(s['jobs'], run, R))
        if not g['ok']: return None
        items = CL.plan(R, g['sha'], sha=manualpage.disk_sha, rec=rec) if not g.get('resume') else (REL.cleared(R) or {}).get('files') or []
    except (OSError, ValueError, KeyError, TypeError): return None
    return {'shipment': g['shipment'], 'resume': bool(g.get('resume')), 'confirm': CL.CONFIRM,
            'goes': [{'what': x['what'], 'files': x['files'], 'size': f'{x["bytes"] / 1e6:.1f} MB'} for x in CL.summary(items)],
            'size': f'{sum(x["bytes"] for x in items) / 1e6:.1f} MB'}

def replay_offer(s, run, R):
    """"New Run from the Saved Reply" (decided 2026-10-28) is offered once a review of this run was refused because the
    run can no longer be reviewed (review/sessions.py FALLBACK), and the run has a saved reply and is not cleared."""
    rj = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run and j['kind'] in ('pin', 'review')]
    if not rj or rj[-1]['status'] != 'failed': return None
    if S.FALLBACK.split('.')[0] not in (logs.outcome(jobs.read_log(s['jobs'], rj[-1]['id'])[0]) or ''): return None
    if REL.cleared(R) or not (load(os.path.join(R, 'record.json')) or {}).get('raw_reply'): return None
    import datetime
    return {'label': f'replay-{datetime.datetime.now():%Y-%m-%d-%H%M}'}

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
    from lib import costs
    out = {
        'run': run, 'mode': 'finished', 'run_name': __import__('webapp.names', fromlist=['x']).shown_run(s, run), 'file': BK.shown_file((rec.get('document') or {}).get('file') or ''), 'cost': costs.actual(R),
        'cleared': cleared_view(R), 'clear': clear_offer(s, run, R, rec), 'replay': replay_offer(s, run, R),
        'title': (rec.get('document') or {}).get('file') or run, 'review_html': os.path.isfile(os.path.join(R, 'review.html')),
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
    sha = (rec.get('document') or {}).get('sha256')                  # D8: its original PDF moved to the Trash
    if sha and moved_words(s, sha) and not find_original(s, sha, (rec.get('document') or {}).get('file')):
        need = pdf_needed(s, R, rec)[1]
        out['pdf_moved'] = {'text': 'The original PDF was moved to the Trash.' + (' "Review Again" needs it back: drag it from the Trash into the app\'s folder of added PDFs (where it was).'
                                     if need else ' "Review Again" still works: it uses the copy the app made when it prepared the PDF.')}
    if out['batch']: out['batch_name'] = __import__('webapp.names', fromlist=['x']).shown_run(s, f'batches/{out["batch"]}')   # 07 L4
    return out

# ------------------------------------------------------------------ a run started from the home page, before any result (#45)
PENDING_MARKS = ('run.json', os.path.join('_intake', 'intake.json'), os.path.join('_intake', 'languages.json'), os.path.join('_audit', 'digest.json'))

def pending(s, R, nm=None):
    """A run folder with no result yet and not stopped for its review: estimating, estimate ready, running, stopped or
    failed. It holds one of run_api.sh's own files, or an app job names it (a run queued a moment ago is an empty folder).
    nm: the request's names snapshot (its job list: the page's path checks each parent folder, #93)."""
    if os.path.isfile(os.path.join(R, 'record.json')) or waiting(R): return False
    if any(os.path.exists(os.path.join(R, m)) for m in PENDING_MARKS): return True
    R = os.path.abspath(R)
    return any(j.get('dir') == R and j['kind'] not in ('batch', 'summary') for j in (nm.jobs() if nm else jobs.all_jobs(s['jobs'])))   # a batch's own jobs name its folder

def book_of(s, run, R, js=None, nm=None):
    """(display name, file name) of a run's book: from the app's job, else intake's record or the estimate's source.
    js: the run's jobs; nm: the request's names snapshot (its job list too)."""
    from . import books as BK
    if js is None: js = [j for j in (nm.jobs() if nm else jobs.all_jobs(s['jobs'])) if j['run'] == run]
    for j in reversed(js):
        if j.get('book_sha') or j.get('book_name'):                 # resolved now: a rename shows at once (not the job's snapshot)
            return (BK.name_of_sha(s, j.get('book_sha'), j.get('book_file'), nm) if j.get('book_sha') else j['book_name']), BK.shown_file(j.get('book_file') or '')
    o = (load(os.path.join(R, '_intake', 'intake.json')) or {}).get('original') or (load(os.path.join(R, 'record.json')) or {}).get('document') \
        or (load(os.path.join(R, 'run.json')) or {}).get('source') or {}
    f = BK.shown_file(o.get('file') or '')
    return (BK.name_of_sha(s, o.get('sha256'), f, nm) if o.get('sha256') else None) or BK.stem_name(f or run.split('/')[-1]), f

MODEL_NAMES = {'gpt-4o': 'GPT-4o', 'gpt-4o-mini': 'GPT-4o mini', 'gpt-4.1': 'GPT-4.1', 'gpt-4.1-mini': 'GPT-4.1 mini',
               'o3': 'OpenAI o3', 'o3-mini': 'OpenAI o3-mini', 'o4-mini': 'OpenAI o4-mini'}   # names the rule below reads badly (V2)

def model_words(m):
    """A model's display name from its id: "anthropic/claude-sonnet-5.5" → "Claude Sonnet 5.5" (no provider, no id): the
    table above for names the rule reads badly, else each part capitalized. A new model's name is checked when it is
    adopted (docs/app.md)."""
    if not m: return None
    k = str(m).split('/')[-1].split(':')[0]
    if k in MODEL_NAMES: return MODEL_NAMES[k]
    w = k.replace('_', '-').split('-')
    up = {'gpt': 'GPT', 'ai': 'AI', 'xl': 'XL'}
    return ' '.join(up.get(x.lower(), x if x[:1].isdigit() else x[:1].upper() + x[1:]) for x in w if x)

def details(s, run, R, pages=None, nm=None):
    """The run page header's line (Patrick's test, 2026-11-07, Q6, R5): "mm · 321 pages · Run on November 6, 2026,
    at 9:29 PM · AI Model: Claude Sonnet 5.5 · AI Cost: $0.27 (expected $0.31, max estimated $0.67)", in plain words; a part with nothing
    recorded is left out, and "AI" and "AI Cost" only once an AI reply exists (a saved one: "AI Cost: none (a saved reply
    was used)"). The model is the original call's (lib/origin.py), never an id or a file name."""
    from lib import dates as D, costs, origin
    from . import names as NM
    rec = load(os.path.join(R, 'record.json')); runj = load(os.path.join(R, 'run.json')) or {}
    if not pages:
        pages = ((rec or {}).get('document') or {}).get('pages') or ((load(os.path.join(R, '_intake', 'intake.json')) or {}).get('original') or {}).get('pages')
    try: pages = int(str(pages).replace(',', '')) if pages else None
    except ValueError: pages = None
    when = ((rec or {}).get('run') or {}).get('started') or runj.get('started')
    out = [(nm or NM.snapshot(s)).shown_run(run)] + ([f'{pages:,} page{"" if pages == 1 else "s"}'] if pages else []) + \
          ([f'Run on {D.when(when)}'] if when and D.parse(when) else [])
    called = bool(rec) or os.path.isfile(os.path.join(R, 'workorder.ai.json')) or bool(runj.get('usage') or runj.get('response_from'))
    if called:
        model = (origin.summary(rec).get('model') if rec else None) or ((rec or {}).get('run') or {}).get('model') or runj.get('model')
        if model_words(model): out.append(f'AI Model: {model_words(model)}')
        c = costs.actual(R)
        r_ = (rec or {}).get('run') or runj
        if c['reused']: out.append('AI Cost: none (a saved reply was used)')   # L1 (review 15): labels in Title Case
        elif c.get('no_model') and not c['usd']: out.append('AI Cost: ' + costs.NO_MODEL_WORDS)   # a PDF edited by hand: never "$0.00"
        elif (rec or {}).get('cost_total_usd') is None and (r_.get('usage') or {}).get('cost_usd') is None and not c['usd']:
            out.append('AI Cost: not recorded')                # never a "$0.00" that was not measured
        else: out.append('AI Cost: ' + costs.cost_words(c))    # one wording with the batch page and the terminal
    return out

def sent_words(est):
    """What leaves the computer with the AI call, in words (02 M9): the parts counted from the estimate, a zero part left out."""
    figs = max(0, (est.get('images') or 0) - (est.get('sheets') or 0)); sh = est.get('sheets') or 0
    parts = ['the book\'s structure and much of its text']
    if figs: parts.append(f'{figs} figure image{"" if figs == 1 else "s"}')
    if sh: parts.append(f'{sh} image{"" if sh == 1 else "s"} of hard-to-read scanned words')
    return 'Sent to the AI (Claude, through OpenRouter): ' + (', '.join(parts[:-1]) + (',' if len(parts) > 2 else '') + ' and ' + parts[-1] if len(parts) > 1 else parts[0]) + '.'

def pending_state(s, run, R):
    """The run page's view of a run started from the home page before its result: the estimate, Spend, the jobs, and what
    "Try Again" does (decided from disk)."""
    from lib import costs
    from . import newrun, failures, names as NM
    js = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run]
    name, file = book_of(s, run, R, js)
    from . import spend as SP
    try: est = costs.estimate(R, 'workorder', costs.limits_of(s), credit_read=SP.credit_read(s))   # U8
    except Exception: est = None
    test = bool(s.get('test_reply_dir'))
    active = [j for j in js if j['status'] in jobs.ACTIVE]
    needs = [j for j in js if j['status'] == 'needs-spend']
    retry = newrun.retry_kind(R)
    fail = None if active else failures.explain(s, R, js[-1] if js else None)
    from . import lang as LG
    lq = None if active else LG.question(s, R, js)                 # D4: "Language of the Scanned Pages"
    phase = 'active' if active else 'needs-spend' if needs else 'language' if lq else 'stopped' if fail else 'saved-reply' if retry == 'rerun' else 'estimate' if est else 'new'
    from_app = any(j['kind'] == 'estimate' for j in js)
    batch = run.split('/')[1] if run.startswith('batches/') and len(run.split('/')) == 3 else None
    if phase != 'active' and batch: phase = 'batch'            # a batch's book: its Spend is the batch's, on the batch page
    elif phase != 'active' and not from_app: phase = 'outside'  # made from the terminal: its settings aren't known here
    spend = None
    if phase == 'estimate' and est:
        b = est['blocked']
        ok = not b or (test and b['code'] in ('offline', 'no_credit'))
        spend = {'ok': ok, 'why': None if ok else (SP.credit_words(s) if b['code'] == 'no_credit' else b['words']), 'code': None if ok else b['code']}
    if lq: fail = None
    return {'run': run, 'mode': 'pending', 'title': name, 'file': file, 'run_name': NM.shown_run(s, run), 'phase': phase, 'language': lq,
            'estimate': est, 'sent': sent_words(est) if est else None, 'spend': spend, 'retry': retry, 'failure': fail, 'test': test,
            'from_app': from_app, 'batch': batch, 'batch_name': NM.shown_run(s, f'batches/{batch}') if batch else None,
            'jobs': [job_view(s, j) for j in js]}

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
    if own_sha(s, R) == sha: return own_pdf(R), None       # R17: the run's own copy
    p = find_original(s, sha, name)
    if p: return p, None
    if moved_words(s, sha): return None, moved_words(s, sha).replace('"Review Again" needs', 'Applying the reviewed decisions needs')
    return None, (f'The book\'s original PDF ({name or "its file"}) wasn\'t found in the folder of original PDFs or of uploads. '
                  'Put a copy of it in one of them, then try again.')

def waiting_title(run, R):
    """A waiting run's heading: the original's file name (intake's record, else the path kept at the stop), else the run."""
    o = (load(os.path.join(R, '_intake', 'intake.json')) or {}).get('original') or {}
    from . import books as BK
    return BK.shown_file(o.get('file') or os.path.basename((load(os.path.join(R, 'review_stop.json')) or {}).get('src') or '') or run)

def waiting_state(s, run, R):
    """The panel's view of a waiting run: whether its review is finished (review.json), and its jobs. No result, no
    sessions and no evaluation yet: those come with the first apply."""
    rv = load(os.path.join(R, 'review.json')) or {}
    live = live_review(s, run)
    name, file = book_of(s, run, R)
    al = jobs.all_jobs(s['jobs'])                        # in the order they were made (job ids are timestamps)
    rj = [j for j in al if j['run'] == run and j['kind'] == 'review' and j.get('first')]
    last = rj[-1] if rj else {}
    auto = None                                          # D3: what became of the apply "Finish Review" starts
    if rv and last.get('auto_apply'):
        tj = last.get('then_job')
        # The newest first apply made after this review (review 12 L3): "Try Again" makes a new one, and the page follows
        # it (the spinner while it is queued or running, the card with its own reason if it fails), never the first one's.
        aj = next((j for j in reversed(al) if j['run'] == run and j['kind'] == 'apply' and j.get('first') and j['id'] > last['id']), None)
        if aj and aj['status'] in ('failed', 'interrupted'):           # review 10 M1: the apply ended without a result
            v = job_view(s, aj)
            auto = {'state': 'failed', 'why': v.get('reason') or 'The apply stopped before it finished.', 'job': aj['id']}
        elif not aj and tj == 'refused': auto = {'state': 'refused', 'why': last.get('then_why')}
        else: auto = {'state': 'starting'}
    return {'run': run, 'mode': 'waiting', 'title': waiting_title(run, R), 'book': name, 'file': file,
            'waiting': {'reviewed': bool(rv), 'reviewer': rv.get('reviewer'), 'date': rv.get('date'), 'auto': auto,
                        'prepared': os.path.isfile(os.path.join(R, 'review_items.json'))},
            'live_review': job_view(s, live) if live else None,
            'jobs': [job_view(s, j) for j in al if j['run'] == run]}

def start_first_review(s, run, R, port, app_pid=None):
    """Open the Review Page for a waiting run: review_workorder.py <run> --serve, as the terminal's step 1."""
    if os.path.isfile(os.path.join(R, 'review.json')): raise ValueError('The review is finished: its decisions are being applied.')
    if not os.path.isfile(os.path.join(R, 'review_items.json')):
        raise ValueError('The review page was not prepared when this run stopped, so it can\'t be opened. Run the book again.')
    back = f'http://127.0.0.1:{port}/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/?after=finish'
    argv = [sys.executable, 'review_workorder.py', R, '--serve', '--no-browser', '--return-to', back]
    return jobs.create(s['jobs'], 'review', run, argv, config.child_env(s), counted=False, R=R, what='Review the edited PDF' if S.no_model(R) else 'Review the AI\'s decisions',
                       app_pid=app_pid, first=True, auto_apply=True)

def auto_apply(s):
    """"Finish Review" applies at once (D3, Patrick 2026-11-06): after each dispatcher pass, a first review that has ended
    with a review.json written since it started gets its apply (start_first_apply: the original is looked up now, never a
    path kept from when the review opened). Only review jobs made with auto_apply (from this change on): an older review
    finished before it is never applied by itself. The claim is made under the jobs lock, so two app servers never
    both apply; the job records the apply's id, or why it could not start (then_why, shown with "Try Again")."""
    J = s['jobs']
    for j in jobs.all_jobs(J):
        if j['kind'] != 'review' or not j.get('auto_apply') or j['status'] in jobs.ACTIVE or j.get('then_job'): continue
        R = j.get('dir') or os.path.join(s['runs'], *j['run'].split('/'))
        rv = os.path.join(R, 'review.json')
        with jobs.locked(J):
            cur = jobs.load(J, j['id']) or {}
            if cur.get('then_job'): continue
            if os.path.isfile(os.path.join(R, 'record.json')): cur['then_job'] = 'applied'
            elif not (os.path.isfile(rv) and os.path.getmtime(rv) >= (jobs._at(j.get('started')) or 0) - 1): cur['then_job'] = 'not-finished'
            else: cur['then_job'] = 'starting'
            jobs.save(J, cur)
        if cur['then_job'] != 'starting': continue
        try: a = start_first_apply(s, j['run'], R)
        except ValueError as e: jobs.update(J, j['id'], then_job='refused', then_why=str(e)); continue
        except Exception as e:                                   # review 10 L1: never left at 'starting'
            jobs.update(J, j['id'], then_job='refused', then_why=f'The apply couldn\'t start because of a problem in the app ({type(e).__name__}). Try again.'); continue
        jobs.update(J, j['id'], then_job=a['id'])

def start_first_apply(s, run, R):
    """Apply for a waiting run, after Finish Review: run_api.sh's second call (the same command the terminal is told to
    run), in this run's folder (RUN_DIR) with the settings it stopped with (review_stop.json)."""
    if not os.path.isfile(os.path.join(R, 'review.json')): raise ValueError('Finish the review first: "Open the Review Page", then "Finish Review".')
    src, why = first_original(s, R)
    if why: raise ValueError(why)
    stop = load(os.path.join(R, 'review_stop.json')) or {}
    env = {'RUN_DIR': R, **{k: v for k, v in (stop.get('env') or {}).items() if k in ('OCR_LANG', 'INTAKE_REUSE', 'INTAKE', 'OUT') and v}}
    name_, label_ = stop.get('name') or os.path.basename(os.path.dirname(R)), os.path.basename(R)
    p_ = run.split('/')
    if p_[0] == 'batches' and len(p_) == 3: name_, label_ = p_[2], p_[1]          # a batch's book: runs/batches/<label>/<name>
    argv = ['bash', 'run_api.sh', src, name_, label_]
    then = None
    if p_[0] == 'batches' and len(p_) == 3:                  # a batch's book (D2a): its batch's summary is written again after
        then = {'kind': 'summary', 'argv': ['bash', 'batch_api.sh', p_[1]], 'env': config.child_env(s, {'SUMMARY_ONLY': '1'}),
                'env_set': {'SUMMARY_ONLY': '1'}, 'counted': False, 'extra': {'what': 'Write the batch summary again'}}
    return jobs.create(s['jobs'], 'apply', run, argv, config.child_env(s, env), env_set=env, R=R, what='Apply session 1', first=True, then=then)

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
