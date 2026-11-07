"""webapp/home.py: the home page (#45, home interface): the books, the runs in progress, every earlier run and batch, each
with its status, date and AI cost, and a button that opens it. Listing a run never changes it.

    index(s)            {'runs': [row …], 'batches': [row …]}, newest first; rows are cached in runs/.app/home-index.json by
                        the run's path and the mtimes of its records (record.json, run.json, workorder.ai.json, review.json,
                        _intake/intake.json, release/*.json), and the app's jobs are laid over them when read (03 §12 L3)
    page(s, q, n)       the home page's HTML (home.js adds Add a Book, New Batch's selection and the live "Runs in Progress")

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

def is_run(R):
    return any(os.path.isfile(os.path.join(R, m)) for m in ('record.json', 'run.json', 'workorder.ai.json', os.path.join('_intake', 'intake.json'),
                                                          os.path.join('_intake', 'languages.json')))   # D4: stopped to ask its language

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
        when = runj.get('started') or intake.get('written') or ''
        if os.path.isfile(os.path.join(R, 'workorder.ai.json')):
            name = words = 'Waiting to Start' if os.path.isfile(os.path.join(R, 'review.json')) else 'Waiting for Review'   # reviewed: its apply comes next (D3)
        elif LG.asks(R): name = words = 'Waiting for a Language'                 # D4 (a 'first' one is checked against the jobs in over())
        elif intake.get('status') == 'stopped': name, words = 'Stopped', 'Stopped: Needs a Person'
        elif intake.get('status') == 'failed' or runj.get('error') or runj.get('parse_error'): name = words = 'Failed'
        elif isinstance(runj.get('estimate'), dict) and not runj.get('usage'): name = words = 'Estimate Ready'
        else: name, words = 'Stopped', 'Stopped before it finished'
    if not when:
        try: when = datetime.datetime.fromtimestamp(os.path.getmtime(R)).isoformat(timespec='seconds')
        except OSError: when = ''
    a = costs.actual(R)
    parts = run.split('/')
    return {'run': run, 'lang_kind': None if rec else LG.asks(R), 'sha': sha, 'book': (BK.name_of_sha(s, sha, file) if sha else None) or BK.stem_name(file or parts[-2 if parts[0] != 'batches' else -1]),
            'file': BK.shown_file(file) if file else '', 'status': name, 'words': words, 'when': when,
            'cost': a['usd'], 'reused': a['reused'], 'batch': parts[1] if parts[0] == 'batches' else None, 'finished': bool(rec)}

def index(s):
    """Every run's row (cached by its records' mtimes), newest first, with the app's jobs laid over them, and the batches."""
    cp = os.path.join(s['jobs'], 'home-index.json')
    with _lock: cache = _load(cp) or {}
    rows, fresh, dirty = [], {}, False
    for run, R in run_folders(s['runs']):
        k = key_of(R); c = cache.get(run)
        if c and c.get('key') == k and 'lang_kind' in c['row']: row = c['row']
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
    if st == 'Estimate Ready': return 'not-started'
    return 'in-progress'

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
        out.append({'label': lb, 'name': NM.batch_name(s, lb) or lb, 'books': len(bs) or len(meta.get('books') or []), 'done': done, 'state': state,
                    'group': g, 'when': when, 'cost': round(sum(r['cost'] or 0 for r in bs), 6)})
    out.sort(key=lambda b: b['when'] or '', reverse=True)
    return out

# ------------------------------------------------------------------ the page
def money(x): return '$0.00' if not x else f'${x:.2f}' if x >= 0.01 else '< $0.01'

def run_href(run): return '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/'

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
    # the PDFs added through "Add a PDF" (samples/ is never listed: P3)
    B.append('<section class="pp hm-card hm-c-pdfs" aria-labelledby="hm-books-h"><h2 id="hm-books-h">PDFs</h2>'
             '<form id="hm-add" class="hm-add"><label for="hm-file">Add a PDF</label> <input type="file" id="hm-file" accept="application/pdf,.pdf"> '
             '<button type="submit" id="hm-add-b">Add the PDF</button><span class="pp-note">The PDF is copied into the app\'s folder of added PDFs; '
             'the file you choose is not changed.</span></form><div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>')
    ab = next((b for b in bk if b['key'] == (added or renamed)), None) if (added or renamed) else None
    if ab: B.append(f'<p id="hm-added" hidden>' + (f'Added "{E(ab["name"])}".' if added else f'The PDF is now named "{E(ab["name"])}".') + '</p>')
    elif trashed: B.append('<p id="hm-added" hidden>Moved to the Trash. Nothing was deleted: to put it back, drag it from the Trash to where it was.</p>')
    B.append('<form id="hm-batch" method="get" action="/new-batch">')
    if not bk: B.append('<p>None yet. "Add a PDF" adds one.</p>')
    else:
        B.append(f'<div class="pp-tw" tabindex="0" role="region" aria-labelledby="hm-books-h"><table class="hm-t"><thead><tr>'
                 '<th scope="col">Select</th><th scope="col">PDF</th><th scope="col">Pages</th><th scope="col">Size</th><th scope="col">Action</th></tr></thead><tbody>')
        for i, b in enumerate(bk):
            cid = f'hm-sel-{i}'
            note = ' <span class="pp-note">Locked with a password: add an unlocked copy.</span>' if b['locked'] else \
                   ' <span class="pp-note">This PDF couldn\'t be read.</span>' if b['unreadable'] else ''
            act = ('' if b['locked'] else f'<a class="pp-btn" href="/new?book={E(b["key"])}" aria-describedby="{cid}-n">New Run</a> ') + \
                  f'<a class="pp-btn" href="/book?key={E(b["key"])}" aria-describedby="{cid}-n">Edit the Name</a> ' + \
                  f'<button type="button" data-trash="pdf" data-key="{E(b["key"])}" aria-describedby="{cid}-n">Move to Trash</button>'
            sel = '' if b['locked'] else f'<input type="checkbox" name="book" value="{E(b["key"])}" id="{cid}" aria-labelledby="{cid}-n">'
            B.append(f'<tr><td>{sel}</td><th scope="row" id="{cid}-n">{book_cell(b["name"], b["file"])}{note}</th>'
                     f'<td>{b["pages"] if b["pages"] is not None else "not counted"}</td><td class="pp-nw">{E(BK.size_words(b["size"]))}</td><td>{act}</td></tr>')
        B.append('</tbody></table></div>')
        B.append('<div class="pp-row"><button type="submit" id="hm-batch-b">New Batch with the Selected PDFs</button>'
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
                 '<th scope="col">Status</th><th scope="col">Date Created</th><th scope="col">AI Cost</th><th scope="col">Action</th></tr></thead><tbody>')
        for r in shown:
            label = r.get('name') or r['run'].split('/')[-1]
            rid = 'hm-r-' + hashlib.sha1(r['run'].encode()).hexdigest()[:10]
            B.append(f'<tr><th scope="row" id="{rid}"><span class="hm-run">{E(label)}</span>{book_cell(r["book"], r["file"])}</th><td>{pill(r["group"], r["words"])}</td>'
                     f'<td class="pp-nw">{E(D.day(r["when"]) if r["when"] else "date not recorded")}</td>'
                     f'<td>{E(money(r["cost"]))}' + (' <span class="pp-note">(saved reply)</span>' if r['reused'] else '') +
                     f'</td><td><a class="pp-btn" href="{E(run_href(r["run"]))}" aria-describedby="{rid}">Open</a> '
                     f'<button type="button" data-trash="run" data-run="{E(r["run"])}" aria-describedby="{rid}">Move to Trash</button></td></tr>')
        B.append('</tbody></table></div>')
    elif shown:
        B.append('<div class="pp-tw" tabindex="0" role="region" aria-label="Batches Table"><table class="hm-t"><thead><tr><th scope="col">Batch Name</th>'
                 '<th scope="col">PDFs</th><th scope="col">Status</th><th scope="col">Date Created</th><th scope="col">AI Cost</th><th scope="col">Action</th></tr></thead><tbody>')
        for b in shown:
            bid = 'hm-b-' + hashlib.sha1(b['label'].encode()).hexdigest()[:10]
            B.append(f'<tr><th scope="row" id="{bid}"><span class="hm-run">{E(b["name"])}</span></th><td>{b["done"]} of {b["books"]} PDFs finished</td><td>{pill(b["group"], b["state"])}</td>'
                     f'<td class="pp-nw">{E(D.day(b["when"]) if b["when"] else "date not recorded")}</td><td>{E(money(b["cost"]))}</td>'
                     f'<td><a class="pp-btn" href="/batch/{E(urllib.parse.quote(b["label"], safe=""))}/" aria-describedby="{bid}">Open</a> '
                     f'<button type="button" data-trash="batch" data-label="{E(b["label"])}" aria-describedby="{bid}">Move to Trash</button></td></tr>')
        B.append('</tbody></table></div>')
    if len(items) > lim:
        more = qs(view=view if view != 'runs' else None, q=q, group=group, n=n + 25 if view == 'runs' else n, bn=bn + 25 if view == 'batches' else bn)
        B.append(f'<p><a class="pp-btn" href="{E(more)}#hm-more" id="hm-more">Show More {"Runs" if view == "runs" else "Batches"}</a></p>')
    B.append('</section></main><script src="/app/home.js" defer></script><script src="/app/trash.js" defer></script></body></html>')
    return '\n'.join(B)

def name_page(s, key, added=False):
    """A PDF's name (Patrick, 2026-11-06): shown after "Add a PDF" with the automatic name prefilled, and from the home
    page's "Edit the Name". The name is the app's only (webapp/names.py); "Source PDF:" stays under it. P9: no
    explanatory sentences, one button."""
    b = BK.by_key(s, key)
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>PDF Name</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a>' + appbar())
    if not b:
        return head + ('<header><h1>PDF Name</h1></header><main id="main" tabindex="-1"><div class="pp"><p>This PDF\'s file has changed or is gone.</p>'
                       '</div></main></body></html>')
    return head + (f'<header><h1>PDF Name</h1><p class="mc-book">{book_cell(b["name"], b["file"])}</p></header><main id="main" tabindex="-1">'
        '<form class="pp hm-form" id="hm-bookname" data-api="/api/book/name">'
        f'<input type="hidden" name="key" value="{E(b["key"])}">'
        '<div class="mc-field"><label for="bk-name">PDF Name</label>'
        f'<input type="text" id="bk-name" name="name" value="{E(b["name"])}" required maxlength="120"></div>'
        '<div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>'
        '<div class="pp-row"><button type="submit" class="pp-primary">Save Name</button></div></form></main>'
        '<script src="/app/home.js" defer></script></body></html>')

def appbar(current=False, extra=''):
    """The app bar on every page the app serves except the home page itself (P1), right after the skip link: "Home Page"
    as a button (P5), and on run and batch pages the book list's own button beside it (`extra`)."""
    return ('<nav class="pp-appbar" aria-label="App"><a class="pp-btn" href="/">Home Page</a>' + extra + '</nav>')
