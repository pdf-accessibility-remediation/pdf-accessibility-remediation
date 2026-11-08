"""webapp/home.py: the home page (#45, home interface): the books, the runs in progress, every earlier run and batch, each
with its status, date and AI cost, and a button that opens it. Listing a run never changes it.

    index(s)            {'runs': [row …], 'batches': [row …]}, newest first; rows are cached in runs/.app/home-index.json by
                        the run's path and the mtimes of its records (record.json, run.json, workorder.ai.json, review.json,
                        _intake/intake.json, release/*.json), and the app's jobs are laid over them when read (03 §12 L3)
    page(s, q, n)       the home page's HTML (home.js adds the drop zone, the "⋯" menus, Edit Name, Create a New Batch's selection and the live "Runs in Progress")

What is listed: runs/<name>/<label>/ and runs/batches/<label>/<name>/ holding record.json, workorder.ai.json, run.json,
_intake/intake.json or _intake/languages.json; runs/.app and dot-folders are skipped. A row's status uses one vocabulary (03 §12 L5): Not Ready,
Pending Evaluation, Ready, Shipped (each with "· N issues noted"), Waiting for Review, Estimating, Estimate Ready,
Running, Stopped: Needs a Person, Failed, Cleared. A finished run's status is worked out from its glance and release/
(lib/glance.py with_release), without hashing any PDF: the run page does the full check.
"""
import os, json, html, hashlib, threading, datetime, urllib.parse
from lib import dates as D, costs, release as REL
from . import books as BK, jobs, config, lang as LG

E = html.escape
MARKS = ('record.json', 'run.json', 'workorder.ai.json', 'review.json', os.path.join('_intake', 'intake.json'), os.path.join('_intake', 'languages.json'))
RELEASE = ('checks.json', 'shipped.json', 'cleared.json')
_lock = threading.Lock()

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def _mt(p):
    try: return os.stat(p).st_mtime_ns
    except OSError: return None

def has_source(R):
    """A run folder holding only its own PDF (R17): just started, or saved in a batch for later, or its estimate failed
    before intake wrote anything. It is a run, so its PDF is never hidden."""
    try: return any(f.lower().endswith('.pdf') for f in os.listdir(os.path.join(R, 'source')))
    except OSError: return False

def is_run(R):
    return any(os.path.isfile(os.path.join(R, m)) for m in ('record.json', 'run.json', 'workorder.ai.json', os.path.join('_intake', 'intake.json'),
                                                          os.path.join('_intake', 'languages.json'))) or has_source(R)   # D4; R17

def run_folders(runs):
    """[(run name, folder)] of every run folder: runs/<name>/<label>/ and runs/batches/<label>/<name>/."""
    out = []
    def subdirs(d):
        try: return sorted(e.name for e in os.scandir(d) if e.is_dir(follow_symlinks=False) and not e.name.startswith('.'))
        except OSError: return []
    for a in subdirs(runs):
        for b in subdirs(os.path.join(runs, a)):
            R = os.path.join(runs, a, b)
            if a == 'batches':
                for c in subdirs(R):
                    if is_run(os.path.join(R, c)): out.append((f'batches/{b}/{c}', os.path.join(R, c)))
            elif is_run(R): out.append((f'{a}/{b}', R))
    return out

def key_of(R):
    return [_mt(os.path.join(R, m)) for m in MARKS] + [_mt(os.path.join(R, 'release', f)) for f in RELEASE]

def _status_of_record(R, rec):
    """A finished run's status words, from its glance and release/ (no PDF hashed)."""
    cl = _load(os.path.join(R, 'release', 'cleared.json'))
    if isinstance(cl, dict) and cl.get('state') in ('planned', 'done'):
        n = cl.get('shipment')
        return 'Cleared', f'Cleared on {D.day(cl.get("cleared") or cl.get("planned"))}' + (f' · shipped as Shipment {n}' if n else '')
    g = rec.get('glance')
    if isinstance(g, dict) and isinstance(g.get('ship'), list):
        try:
            from lib import glance as G
            st = G.with_release(g, rec, REL.load(R, rec)).get('status') or {}
            return st.get('name') or REL.NOT_READY, REL.with_issues(st.get('name') or REL.NOT_READY, st.get('issues') or 0)
        except Exception: pass
    return REL.NOT_READY, REL.NOT_READY

def row_of(s, run, R):
    """One run's row (without the jobs laid over it)."""
    rec = _load(os.path.join(R, 'record.json'))
    intake = _load(os.path.join(R, '_intake', 'intake.json')) or {}
    runj = _load(os.path.join(R, 'run.json')) or {}
    if rec:
        doc = rec.get('document') or {}
        file, sha = doc.get('file') or '', doc.get('sha256')
        name, words = _status_of_record(R, rec)
        when = (rec.get('run') or {}).get('started') or rec.get('generated') or ''
    else:
        o = intake.get('original') or {}
        stop = _load(os.path.join(R, 'review_stop.json')) or {}
        file, sha = o.get('file') or os.path.basename(stop.get('src') or '') or (runj.get('source') or {}).get('file') or '', o.get('sha256') or (runj.get('source') or {}).get('sha256')
        if not sha and has_source(R):                       # R17: its own PDF says which book it is
            from . import runs as RN
            p = RN.own_pdf(R); sha = RN.own_sha(s, R); file = file or os.path.basename(p)
        when = runj.get('started') or intake.get('written') or ''
        if os.path.isfile(os.path.join(R, 'workorder.ai.json')):
            name = words = 'Waiting to Start' if os.path.isfile(os.path.join(R, 'review.json')) else 'Waiting for Review'   # reviewed: its apply comes next (D3)
        elif LG.asks(R): name = words = 'Waiting for a Language'                 # D4 (a 'first' one is checked against the jobs in over())
        elif intake.get('status') == 'stopped': name, words = 'Stopped', 'Stopped: Needs a Person'
        elif intake.get('status') == 'failed' or runj.get('error') or runj.get('parse_error'): name = words = 'Failed'
        elif isinstance(runj.get('estimate'), dict) and not runj.get('usage'): name = words = 'Estimate Ready'
        elif not intake and not runj and has_source(R): name = words = 'Not Started'   # R17: only its own PDF so far
        else: name, words = 'Stopped', 'Stopped before it finished'
    if not when:
        try: when = datetime.datetime.fromtimestamp(os.path.getmtime(R)).isoformat(timespec='seconds')
        except OSError: when = ''
    a = costs.actual(R)
    parts = run.split('/')
    pages = ((rec or {}).get('document') or {}).get('pages') or (intake.get('original') or {}).get('pages')
    if not pages and sha: pages = (_load(os.path.join(s['jobs'], 'books-cache.json')) or {}).get(sha, {}).get('pages')
    return {'run': run, 'lang_kind': None if rec else LG.asks(R), 'sha': sha, 'book': (BK.name_of_sha(s, sha, file) if sha else None) or BK.stem_name(file or parts[-2 if parts[0] != 'batches' else -1]),
            'file': BK.shown_file(file) if file else '', 'status': name, 'words': words, 'when': when,
            'cost': a['usd'], 'reused': a['reused'], 'batch': parts[1] if parts[0] == 'batches' else None, 'finished': bool(rec),
            'pages': pages if isinstance(pages, int) else None}

def index(s):
    """Every run's row (cached by its records' mtimes), newest first, with the app's jobs laid over them, and the batches."""
    cp = os.path.join(s['jobs'], 'home-index.json')
    with _lock: cache = _load(cp) or {}
    rows, fresh, dirty = [], {}, False
    for run, R in run_folders(s['runs']):
        k = key_of(R); c = cache.get(run)
        if c and c.get('key') == k and 'pages' in c['row']: row = c['row']   # a row cached before Q5 has no pages: drawn again
        else:
            try: row = row_of(s, run, R)
            except Exception: continue                      # an unreadable folder is left out, never fails the page
            dirty = True
        fresh[run] = {'key': k, 'row': row}; rows.append(dict(row))
    if dirty or set(fresh) != set(cache):
        with _lock:
            tmp = cp + f'.{os.getpid()}.tmp'
            os.makedirs(os.path.dirname(cp), exist_ok=True); json.dump(fresh, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False); os.replace(tmp, cp)
    over(s, rows)
    from . import names as NM
    for r in rows:                                          # names resolved now: a rename shows at once (Patrick, 2026-11-06)
        if r.get('sha'): r['book'] = NM.book_name(s, r['sha'], r.get('file'))
        r['name'] = NM.shown_run(s, r['run'])
    rows.sort(key=lambda r: r['when'] or '', reverse=True)
    return {'runs': rows, 'batches': batches(s, rows)}

ACTIVE_WORDS = {'estimate': 'Estimating', 'spend': 'Running', 'rerun': 'Running', 'replay': 'Running', 'apply': 'Running',
                'review': 'Waiting for Review', 'pin': 'Running', 'ocr': 'Waiting for Review', 'discard': 'Running', 'batch': 'Running'}

def over(s, rows):
    """The app's jobs laid over the rows: a run with a job queued or running says so; a job's failure the record cannot
    show (an estimate that stopped) says Failed."""
    last = {}
    for j in jobs.all_jobs(s['jobs']): last[j['run']] = j
    for r in rows:
        j = last.get(r['run'])
        if r['status'] == 'Waiting to Start' and not r['finished'] and not (j and j['status'] in jobs.ACTIVE):   # reviewed, not applied
            if not (j and j['kind'] == 'review' and j.get('auto_apply') and j.get('then_job') in (None, 'starting')):
                r['status'], r['words'] = 'Reviewed', ('Reviewed: The Apply Couldn\'t Start' if j and j.get('then_job') == 'refused' else 'Reviewed, Not Applied')
        if not j: continue
        if j['status'] in jobs.ACTIVE:
            r['status'] = r['words'] = ACTIVE_WORDS.get(j['kind'], 'Running') if j['status'] == 'running' else 'Waiting to Start'
            r['active'] = True
        elif j['status'] == 'needs-spend': r['status'], r['words'] = 'Estimate Ready', 'Waiting: open it and select "Get a New Estimate"'   # 05 M2
        elif j['status'] in ('failed', 'interrupted') and not r['finished'] and r['status'] not in ('Stopped', 'Waiting for Review') \
                and not (r['status'] == 'Waiting for a Language' and (r.get('lang_kind') == 'cjk' or LG.stopped_to_ask(j))):   # a later failure shows
            r['status'] = r['words'] = 'Failed' if j['status'] == 'failed' else 'Stopped before it finished'

GROUPS = (('not-started', 'Not Started'), ('processing', 'Processing'), ('in-progress', 'In Progress'), ('done', 'Done'), ('failed', 'Failed'))
GROUP_NAMES = dict(GROUPS)

def group_of(r):
    """A run's status group on the home page (D6, Patrick 2026-11-06): Not Started (an estimate, nothing paid), Processing
    (a job running or waiting to start), In Progress (waiting for a person, stopped, interrupted, Not Ready, Pending
    Evaluation), Done (Ready or Shipped only), Failed (the last job ended with an error). The exact status is shown beside it."""
    st = r.get('status') or ''
    if r.get('active') or st == 'Waiting to Start': return 'processing'
    if st == 'Failed': return 'failed'
    if st in ('Ready', 'Shipped', 'Cleared'): return 'done'
    if st in ('Estimate Ready', 'Not Started'): return 'not-started'
    return 'in-progress'

def pages_words(n, missing=0):
    """A Pages cell: "321", "not counted", or a batch's total with the PDFs it leaves out said ("1,195 (1 PDF not counted)")."""
    if not n: return 'not counted'
    return f'{n:,}' + (f' ({missing} PDF{"" if missing == 1 else "s"} not counted)' if missing else '')

def pill(g, words=None):
    """The group's pill (its name in words: color is never the only signal), and the exact status beside it."""
    name = GROUP_NAMES[g]
    return f'<span class="hm-pill hm-g-{g}">{E(name)}</span>' + (f' <span class="hm-st">{E(words)}</span>' if words and words != name else '')

def batches(s, rows):
    """Every batch folder: its books, state, group, date and cost."""
    BB = os.path.join(s['runs'], 'batches')
    try: labels = sorted(e.name for e in os.scandir(BB) if e.is_dir() and not e.name.startswith('.'))
    except OSError: labels = []
    by = {}
    for r in rows:
        if r['batch']: by.setdefault(r['batch'], []).append(r)
    last = {}
    for j in jobs.all_jobs(s['jobs']):
        if j['kind'] == 'batch': last[j['run']] = j
    out = []
    from . import names as NM
    for lb in labels:
        bs = by.get(lb, [])
        B = os.path.join(BB, lb)
        meta = _load(os.path.join(s['jobs'], 'batches', f'{lb}.json')) or {}
        if not bs and not meta: continue
        done = sum(1 for r in bs if r['finished'])
        lj = last.get(f'batches/{lb}')
        gs = [group_of(r) for r in bs]
        g = 'processing' if (lj and lj['status'] in jobs.ACTIVE) or 'processing' in gs else \
            'failed' if lj and lj['status'] == 'failed' else \
            'done' if gs and all(x == 'done' for x in gs) else \
            'not-started' if not lj and all(x == 'not-started' for x in gs) else 'in-progress'
        n_done = sum(1 for x in gs if x == 'done')
        state = {'processing': 'Running', 'failed': 'The batch stopped with a problem', 'done': f'All {len(bs)} Ready or Shipped',
                 'not-started': 'Estimate Ready' if bs and all(r['status'] == 'Estimate Ready' for r in bs) else 'Not Started',
                 'in-progress': 'Stopped' if bs and all(r['status'] == 'Stopped' for r in bs) else f'{n_done} of {len(bs)} Ready or Shipped'}[g]
        when = meta.get('created') or min((r['when'] for r in bs if r['when']), default='') or ''
        n_books = len(bs) or len(meta.get('books') or [])
        known = [r['pages'] for r in bs if r.get('pages')]
        out.append({'label': lb, 'name': NM.batch_name(s, lb) or lb, 'books': n_books, 'done': done, 'state': state,
                    'group': g, 'when': when, 'cost': round(sum(r['cost'] or 0 for r in bs), 6),
                    'pages': sum(known) if known else None, 'pages_missing': n_books - len(known)})
    out.sort(key=lambda b: b['when'] or '', reverse=True)
    return out

# ------------------------------------------------------------------ the page
def run_href(run): return '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/'

def menu(mid, name, items):
    """A row's "⋯" menu (Patrick's test, 2026-11-07, Q4): a real menu button (aria-haspopup, aria-expanded, named "More
    Actions for <name>"); home.js gives it arrow keys, Esc (focus back on the button), Tab and a click outside to close.
    Each item is a button with its data- attributes (trash.js and home.js act on them); "Move to Trash" is drawn red."""
    def attrs(d): return ''.join(f' {k}="{E(str(v))}"' for k, v in d.items())
    return (f'<span class="hm-menu"><button type="button" class="hm-more" aria-haspopup="menu" aria-expanded="false" aria-controls="{mid}" '
            f'aria-label="More Actions for {E(name)}"><span aria-hidden="true">⋯</span></button>'
            f'<span class="hm-mlist" role="menu" id="{mid}" aria-label="More Actions for {E(name)}" hidden>' +
            ''.join(f'<button type="button" role="menuitem" tabindex="-1"' + (' class="hm-danger"' if 'data-trash' in d else '') + f'{attrs(d)}>{E(w)}</button>'
                    for w, d in items) + '</span></span>')

def book_cell(name, file):
    """A PDF as every page names it: its display name, and under it the one file name the pages show (Q6)."""
    return f'<span class="hm-book">{E(name)}</span>' + (f'<span class="hm-file">Source PDF: {E(file)}</span>' if file else '')

def qs(**kw): return '/?' + urllib.parse.urlencode({k: v for k, v in kw.items() if v not in (None, '', 25)})

def page(s, q='', n=25, test=False, added=None, bn=25, renamed=None, view='runs', group='', trashed=False):
    try: n = max(25, min(int(n), 100000))
    except (TypeError, ValueError): n = 25
    try: bn = max(25, min(int(bn), 100000))
    except (TypeError, ValueError): bn = 25
    q = (q or '').strip()[:200]
    view = 'batches' if view == 'batches' else 'runs'
    group = group if group in GROUP_NAMES else ''
    bk = BK.listing(s)                                      # first: it reads each PDF's Title, which the rows' names use
    idx = index(s)
    active = any(j['status'] in jobs.ACTIVE for j in jobs.all_jobs(s['jobs']))
    B = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>PDF Accessibility Remediation</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>',
         '<body class="pp-page hm-page" data-home="1"><a class="skip" href="#main">Skip to the content</a>',
         '<header><h1>PDF Accessibility Remediation</h1></header><main id="main" tabindex="-1">']
    if test: B.append('<p class="pp pp-bar">Test: saved replies, no AI call.</p>')
    B.append('<section class="pp hm-card hm-c-act" id="hm-act-sec" aria-labelledby="hm-act-h"' + ('' if active else ' hidden') +
             '><h2 id="hm-act-h">Runs in Progress</h2><div id="hm-active"><p>Loading…</p></div></section>'
             '<div id="hm-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div>')
    # the PDFs added through the drop zone (samples/ is never listed: P3). Patrick's test, 2026-11-07 (Q1, Q3, Q4): one
    # drop zone for several PDFs; a new PDF comes first, highlighted, with its name box open (home.js); Edit Name in place.
    new = [k for k in (added or '').split(',') if k] if added else []
    bk = sorted(bk, key=lambda b: b['key'] not in new)      # the PDFs just added first, in the list's own order otherwise
    B.append('<section class="pp hm-card hm-c-pdfs" aria-labelledby="hm-books-h"><h2 id="hm-books-h">Upload a PDF</h2>'
             '<div class="hm-drop" id="hm-drop"><svg class="hm-drop-i" aria-hidden="true" focusable="false" viewBox="0 0 24 24" width="28" height="28">'
             '<path d="M12 16V4m0 0-5 5m5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg><div class="hm-drop-t"><div class="hm-drop-r">'
             '<button type="button" id="hm-choose" class="pp-primary">Choose PDFs</button> <span>or Drop PDFs here</span></div>'
             '<p class="pp-note" id="hm-drop-n">A copy goes into the app\'s folder; the file you choose is not changed.</p></div>'
             '<input type="file" id="hm-file" accept="application/pdf,.pdf" multiple hidden tabindex="-1" aria-hidden="true"></div>'
             '<div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>')
    ab = [b for b in bk if b['key'] in new]
    if ab: B.append('<p id="hm-added" hidden>' + (f'Added "{E(ab[0]["name"])}"' if len(ab) == 1 else f'Added {len(ab)} PDFs') + '</p>')   # R7
    elif renamed and next((b for b in bk if b['key'] == renamed), None):
        B.append(f'<p id="hm-added" hidden>The PDF is now named "{E(next(b for b in bk if b["key"] == renamed)["name"])}".</p>')
    elif trashed: B.append('<p id="hm-added" hidden>Moved to the Trash. Nothing was deleted: to put it back, drag it from the Trash to where it was.</p>')
    B.append('<form id="hm-batch" method="get" action="/new-batch">')
    if not bk: B.append('<p>None yet. "Choose PDFs" adds one.</p>')
    else:
        B.append(f'<div class="pp-tw" tabindex="0" role="region" aria-labelledby="hm-books-h"><table class="hm-t hm-pdfs"><thead><tr>'
                 '<th scope="col" class="hm-sel">Select</th><th scope="col">PDF</th><th scope="col">Pages</th><th scope="col">Size</th><th scope="col">Action</th></tr></thead><tbody>')
        for i, b in enumerate(bk):
            cid = f'hm-sel-{i}'
            note = ' <span class="pp-note">Locked with a password: add an unlocked copy.</span>' if b['locked'] else \
                   ' <span class="pp-note">This PDF couldn\'t be read.</span>' if b['unreadable'] else ''
            act = ('' if b['locked'] else f'<a class="pp-btn" href="/new?book={E(b["key"])}" aria-describedby="{cid}-n">New Run</a> ') + \
                  menu(f'{cid}-m', b['name'], [('Edit Name', {'data-edit': 'pdf', 'data-key': b['key']}),
                                               ('Move to Trash', {'data-trash': 'pdf', 'data-key': b['key']})])
            sel = '' if b['locked'] else f'<input type="checkbox" name="book" value="{E(b["key"])}" id="{cid}" aria-labelledby="{cid}-n">'
            B.append(f'<tr' + (' class="hm-new" data-new="1"' if b['key'] in new else '') + f'><td class="hm-sel">{sel}</td><th scope="row" id="{cid}-n">'
                     f'{book_cell(b["name"], b["file"])}{note}</th>'
                     f'<td>{b["pages"] if b["pages"] is not None else "not counted"}</td><td class="pp-nw">{E(BK.size_words(b["size"]))}</td><td class="hm-acts">{act}</td></tr>')
        B.append('</tbody></table></div>')
        B.append('<div class="pp-row"><button type="submit" id="hm-batch-b">Create a New Batch</button>'
                 '<span class="pp-note" id="hm-batch-n">Select two or more PDFs first.</span></div>')
    B.append('</form></section>')
    # My Workspace: single runs or batches, searched and filtered by status group
    ql = q.casefold()
    runs_ = [r for r in idx['runs'] if not r['batch']]
    if q: runs_ = [r for r in runs_ if ql in (r['book'] or '').casefold() or ql in (r['file'] or '').casefold() or ql in r['run'].casefold()
                   or ql in (r.get('name') or '').casefold()]                     # the plain name and the label both match
    bs = idx['batches']
    if q: bs = [b for b in bs if ql in b['label'].casefold() or ql in b['name'].casefold()]   # both names match
    for r in runs_: r['group'] = group_of(r)
    items = runs_ if view == 'runs' else bs
    counts = {g: sum(1 for x in items if x['group'] == g) for g in GROUP_NAMES}
    if group: items = [x for x in items if x['group'] == group]
    B.append('<section class="pp hm-card hm-c-ws" aria-labelledby="hm-runs-h"><h2 id="hm-runs-h">My Workspace</h2>'
             '<form method="get" action="/" class="hm-ws" role="search" aria-label="My Workspace">'
             f'<input type="hidden" name="group" value="{E(group)}">'
             '<div class="hm-switch" role="group" aria-label="Show">' +
             ''.join(f'<button type="submit" name="view" value="{v}" aria-pressed="{"true" if view == v else "false"}">{w}</button>'
                     for v, w in (('runs', 'Single Runs'), ('batches', 'Batches'))) + '</div>'
             f'<div class="hm-search"><label for="hm-q">Search by {"PDF or Run Name" if view == "runs" else "Batch Name"}</label> '
             f'<input type="search" id="hm-q" name="q" value="{E(q)}"> <button type="submit" name="view" value="{view}">Search</button></div></form>'
             '<div class="hm-filter" role="group" aria-label="Filter by Status">' +
             f'<a class="pp-btn" href="{E(qs(view=view if view != "runs" else None, q=q))}" aria-current="{"true" if not group else "false"}">All ({sum(counts.values())})</a>' +
             ''.join(f'<a class="pp-btn hm-f hm-f-{g}" href="{E(qs(view=view if view != "runs" else None, q=q, group=g))}" aria-current="{"true" if group == g else "false"}">'
                     f'{E(w)} ({counts[g]})</a>' for g, w in GROUPS) + '</div>')
    what = 'run' if view == 'runs' else 'batch'
    plural = lambda k: f'{k} {what}' + ('' if k == 1 else 'es' if what == 'batch' else 's')
    lim = n if view == 'runs' else bn
    shown = items[:lim]
    B.append(f'<p class="pp-note">{plural(len(items))}' + (f' matching "{E(q)}"' if q else '') + (f', {GROUP_NAMES[group]}' if group else '') +
             (f'; the newest {len(shown)} are shown.' if len(shown) < len(items) else '.') + '</p>')
    if shown and view == 'runs':
        B.append('<div class="pp-tw" tabindex="0" role="region" aria-label="Single Runs Table"><table class="hm-t"><thead><tr><th scope="col">Run</th>'
                 '<th scope="col">Status</th><th scope="col">Pages</th><th scope="col">Date Created</th><th scope="col">Action</th></tr></thead><tbody>')
        for r in shown:                                     # Q5 (Patrick's test, 2026-11-07): the pill alone; Pages; no AI Cost (it is on the run page)
            label = r.get('name') or r['run'].split('/')[-1]
            rid = 'hm-r-' + hashlib.sha1(r['run'].encode()).hexdigest()[:10]
            B.append(f'<tr><th scope="row" id="{rid}"><span class="hm-run">{E(label)}</span>{book_cell(r["book"], r["file"])}</th><td>{pill(r["group"])}</td>'
                     f'<td>{E(pages_words(r.get("pages")))}</td><td class="pp-nw">{E(D.day(r["when"]) if r["when"] else "date not recorded")}</td>'
                     f'<td class="hm-acts"><a class="pp-btn" href="{E(run_href(r["run"]))}" aria-describedby="{rid}">Open</a> ' +
                     menu(f'{rid}-m', label, [('New Run of This PDF', {'data-href': '/new?run=' + urllib.parse.quote(r['run'])}), ('Edit Name', {'data-edit': 'run', 'data-run': r['run']}),
                                              ('Move to Trash', {'data-trash': 'run', 'data-run': r['run']})]) +
                     '</td></tr>')
        B.append('</tbody></table></div>')
    elif shown:
        B.append('<div class="pp-tw" tabindex="0" role="region" aria-label="Batches Table"><table class="hm-t"><thead><tr><th scope="col">Batch Name</th>'
                 '<th scope="col">Status</th><th scope="col">Pages</th><th scope="col">Date Created</th><th scope="col">Action</th></tr></thead><tbody>')
        for b in shown:
            bid = 'hm-b-' + hashlib.sha1(b['label'].encode()).hexdigest()[:10]
            B.append(f'<tr><th scope="row" id="{bid}"><span class="hm-run">{E(b["name"])}</span></th><td>{pill(b["group"], b["state"])}</td>'
                     f'<td>{E(pages_words(b.get("pages"), b.get("pages_missing") or 0))}</td><td class="pp-nw">{E(D.day(b["when"]) if b["when"] else "date not recorded")}</td>'
                     f'<td class="hm-acts"><a class="pp-btn" href="/batch/{E(urllib.parse.quote(b["label"], safe=""))}/" aria-describedby="{bid}">Open</a> ' +
                     menu(f'{bid}-m', b['name'], [('Edit Name', {'data-edit': 'batch', 'data-label': b['label']}), ('Move to Trash', {'data-trash': 'batch', 'data-label': b['label']})]) +
                     '</td></tr>')
        B.append('</tbody></table></div>')
    if len(items) > lim:
        more = qs(view=view if view != 'runs' else None, q=q, group=group, n=n + 25 if view == 'runs' else n, bn=bn + 25 if view == 'batches' else bn)
        B.append(f'<p><a class="pp-btn" href="{E(more)}#hm-more" id="hm-more">Show More {"Runs" if view == "runs" else "Batches"}</a></p>')
    B.append('</section></main><script src="/app/home.js" defer></script><script src="/app/trash.js" defer></script></body></html>')
    return '\n'.join(B)

def title_row(h1, extra=''):
    """A page's name with "Home Page" (and `extra`: the PDF list's button) right beside it, on the same line (R4, Patrick's
    test 2026-11-07); the bar is the app bar's own nav, so with_appbar adds none. h1: the heading's escaped text."""
    return f'<div class="pp-hd-top"><h1>{h1}</h1>{appbar(extra=extra)}</div>'

def appbar(current=False, extra=''):
    """The app bar on every page the app serves except the home page itself (P1), right after the skip link: "Home Page"
    as a button (P5), and on run and batch pages the book list's own button beside it (`extra`)."""
    return ('<nav class="pp-appbar" aria-label="App"><a class="pp-btn" href="/">Home Page</a>' + extra + '</nav>')
