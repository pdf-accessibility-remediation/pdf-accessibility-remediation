"""webapp/home.py: the home page (#45, home interface): the books, the runs in progress, every earlier run and batch, each
with its status, date and AI cost, and a button that opens it. Listing a run never changes it.

    index(s)            {'runs': [row …], 'batches': [row …]}, newest first; rows are cached in runs/.app/home-index.json by
                        the run's path and the mtimes of its records (record.json, run.json, workorder.ai.json, review.json,
                        _intake/intake.json, release/*.json), and the app's jobs are laid over them when read (03 §12 L3)
    page(s, q, n)       the home page's HTML (home.js adds Add a Book, New Batch's selection and the live "Runs in Progress")

What is listed: runs/<name>/<label>/ and runs/batches/<label>/<name>/ holding record.json, workorder.ai.json, run.json or
_intake/intake.json; runs/.app and dot-folders are skipped. A row's status uses one vocabulary (03 §12 L5): Not Ready,
Pending Evaluation, Ready, Shipped (each with "· N issues noted"), Waiting for Review, Estimating, Estimate Ready,
Running, Stopped: Needs a Person, Failed, Cleared. A finished run's status is worked out from its glance and release/
(lib/glance.py with_release), without hashing any PDF: the run page does the full check.
"""
import os, json, html, threading, datetime, urllib.parse
from lib import dates as D, costs, release as REL
from . import books as BK, jobs, config

E = html.escape
MARKS = ('record.json', 'run.json', 'workorder.ai.json', 'review.json', os.path.join('_intake', 'intake.json'))
RELEASE = ('checks.json', 'shipped.json', 'cleared.json')
_lock = threading.Lock()

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def _mt(p):
    try: return os.stat(p).st_mtime_ns
    except OSError: return None

def is_run(R):
    return any(os.path.isfile(os.path.join(R, m)) for m in ('record.json', 'run.json', 'workorder.ai.json', os.path.join('_intake', 'intake.json')))

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
        if os.path.isfile(os.path.join(R, 'workorder.ai.json')): name = words = 'Waiting for Review'
        elif intake.get('status') == 'stopped': name, words = 'Stopped', 'Stopped: Needs a Person'
        elif intake.get('status') == 'failed' or runj.get('error') or runj.get('parse_error'): name = words = 'Failed'
        elif isinstance(runj.get('estimate'), dict) and not runj.get('usage'): name = words = 'Estimate Ready'
        else: name, words = 'Stopped', 'Stopped before it finished'
    if not when:
        try: when = datetime.datetime.fromtimestamp(os.path.getmtime(R)).isoformat(timespec='seconds')
        except OSError: when = ''
    a = costs.actual(R)
    parts = run.split('/')
    return {'run': run, 'book': (BK.name_of_sha(s, sha, file) if sha else None) or BK.stem_name(file or parts[-2 if parts[0] != 'batches' else -1]),
            'file': BK.shown_file(file) if file else '', 'status': name, 'words': words, 'when': when,
            'cost': a['usd'], 'reused': a['reused'], 'batch': parts[1] if parts[0] == 'batches' else None, 'finished': bool(rec)}

def index(s):
    """Every run's row (cached by its records' mtimes), newest first, with the app's jobs laid over them, and the batches."""
    cp = os.path.join(s['jobs'], 'home-index.json')
    with _lock: cache = _load(cp) or {}
    rows, fresh, dirty = [], {}, False
    for run, R in run_folders(s['runs']):
        k = key_of(R); c = cache.get(run)
        if c and c.get('key') == k: row = c['row']
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
        if not j: continue
        if j['status'] in jobs.ACTIVE:
            r['status'] = r['words'] = ACTIVE_WORDS.get(j['kind'], 'Running') if j['status'] == 'running' else 'Waiting to Start'
            r['active'] = True
        elif j['status'] == 'needs-spend': r['status'], r['words'] = 'Estimate Ready', 'Waiting: open it and select "Get a New Estimate"'   # 05 M2
        elif j['status'] in ('failed', 'interrupted') and not r['finished'] and r['status'] not in ('Stopped', 'Waiting for Review'):
            r['status'] = r['words'] = 'Failed' if j['status'] == 'failed' else 'Stopped before it finished'

def batches(s, rows):
    """Every batch folder: its books, state, date and cost."""
    BB = os.path.join(s['runs'], 'batches')
    try: labels = sorted(e.name for e in os.scandir(BB) if e.is_dir() and not e.name.startswith('.'))
    except OSError: labels = []
    by = {}
    for r in rows:
        if r['batch']: by.setdefault(r['batch'], []).append(r)
    out = []
    for lb in labels:
        bs = by.get(lb, [])
        B = os.path.join(BB, lb)
        meta = _load(os.path.join(s['jobs'], 'batches', f'{lb}.json')) or {}
        if not bs and not meta: continue
        done = sum(1 for r in bs if r['finished'])
        state = 'Finished' if os.path.isfile(os.path.join(B, 'summary.md')) and done else \
                'Running' if any(r.get('active') for r in bs) or meta.get('running') else \
                'Estimate Ready' if bs and all(r['status'] in ('Estimate Ready', 'Stopped') for r in bs) else 'Stopped'
        when = max((r['when'] for r in bs), default='') or meta.get('created') or ''
        out.append({'label': lb, 'books': len(bs) or len(meta.get('books') or []), 'done': done, 'state': state, 'when': when,
                    'cost': round(sum(r['cost'] or 0 for r in bs), 6)})
    out.sort(key=lambda b: b['when'] or '', reverse=True)
    return out

# ------------------------------------------------------------------ the page
def money(x): return '$0.00' if not x else f'${x:.2f}' if x >= 0.01 else '< $0.01'

def run_href(run): return '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/'

def book_cell(name, file):
    """A book as every page names it: its display name, and under it the one file name the pages show (Q6)."""
    return f'<span class="hm-book">{E(name)}</span>' + (f'<span class="hm-file">Source PDF Filename: {E(file)}</span>' if file else '')

def page(s, q='', n=25, test=False, added=None, bn=25):
    try: n = max(25, min(int(n), 100000))
    except (TypeError, ValueError): n = 25
    try: bn = max(25, min(int(bn), 100000))
    except (TypeError, ValueError): bn = 25
    q = (q or '').strip()[:200]
    idx = index(s)
    bk = BK.listing(s)
    B = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>PDF Remediation</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>',
         '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a>', appbar(current=True),
         '<header><h1>PDF Remediation</h1></header><main id="main" tabindex="-1">']
    if test: B.append('<p class="pp pp-bar">Test: saved replies, no AI call.</p>')
    B.append('<section class="pp" aria-labelledby="hm-act-h"><h2 id="hm-act-h">Runs in Progress</h2><div id="hm-active"><p>Loading…</p></div>'
             '<div id="hm-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div></section>')
    # the books
    B.append('<section class="pp" aria-labelledby="hm-books-h"><h2 id="hm-books-h">Books</h2>'
             '<form id="hm-add" class="hm-add"><label for="hm-file">Add a Book</label> <input type="file" id="hm-file" accept="application/pdf,.pdf"> '
             '<button type="submit" id="hm-add-b">Add the Book</button><span class="pp-note"> The PDF is copied into the app\'s folder of added books; '
             'the file you choose is not changed.</span></form><div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>')
    ab = next((b for b in bk if b['key'] == added), None) if added else None
    if ab: B.append(f'<p id="hm-added" hidden>Added "{E(ab["name"])}" to "Added Books."</p>')
    B.append('<form id="hm-batch" method="get" action="/new-batch">')
    for group, title in (('sample', 'Sample Books'), ('added', 'Added Books')):
        rows = [b for b in bk if b['group'] == group]
        B.append(f'<h3 id="hm-{group}-h">{title} ({len(rows)})</h3>')
        if not rows:
            B.append('<p>None yet. "Add a Book" adds one.</p>' if group == 'added' else '<p>None.</p>'); continue
        B.append(f'<div class="pp-tw" tabindex="0" role="region" aria-labelledby="hm-{group}-h"><table class="hm-t"><thead><tr>'
                 '<th scope="col">Select</th><th scope="col">Book</th><th scope="col">Pages</th><th scope="col">Size</th><th scope="col">Action</th></tr></thead><tbody>')
        for i, b in enumerate(rows):
            cid = f'hm-sel-{group}-{i}'
            note = ' <span class="pp-note">Locked with a password: add an unlocked copy.</span>' if b['locked'] else \
                   ' <span class="pp-note">This PDF couldn\'t be read.</span>' if b['unreadable'] else ''
            act = '' if b['locked'] else f'<a class="pp-btn" href="/new?book={E(b["key"])}" aria-describedby="{cid}-n">New Run</a>'
            sel = '' if b['locked'] else f'<input type="checkbox" name="book" value="{E(b["key"])}" id="{cid}" aria-labelledby="{cid}-n">'
            B.append(f'<tr><td>{sel}</td><th scope="row" id="{cid}-n">{book_cell(b["name"], b["file"])}{note}</th>'
                     f'<td>{b["pages"] if b["pages"] is not None else "not counted"}</td><td class="pp-nw">{E(BK.size_words(b["size"]))}</td><td>{act}</td></tr>')
        B.append('</tbody></table></div>')
    B.append('<div class="pp-row"><button type="submit" id="hm-batch-b">New Batch with the Selected Books</button>'
             '<span class="pp-note" id="hm-batch-n">Select two or more books first.</span></div></form></section>')
    # earlier runs
    rows = idx['runs']
    if q:
        ql = q.casefold()
        rows = [r for r in rows if ql in (r['book'] or '').casefold() or ql in (r['file'] or '').casefold() or ql in r['run'].casefold()]
    B.append(f'<section class="pp" aria-labelledby="hm-runs-h"><h2 id="hm-runs-h">Earlier Runs</h2>'
             f'<form method="get" action="/" class="hm-search" role="search"><label for="hm-q">Search by Book or Run Name</label> '
             f'<input type="search" id="hm-q" name="q" value="{E(q)}"> <button type="submit">Search</button>'
             + (' <a href="/">Show All</a>' if q else '') + '</form>')
    shown = rows[:n]
    B.append(f'<p class="pp-note">{len(rows)} run{"" if len(rows) == 1 else "s"}' + (f' matching "{E(q)}"' if q else '') +
             (f'; the newest {len(shown)} are shown.' if len(shown) < len(rows) else '.') + '</p>')
    if shown:
        B.append('<div class="pp-tw" tabindex="0" role="region" aria-label="Earlier Runs Table"><table class="hm-t"><thead><tr><th scope="col">Book</th>'
                 '<th scope="col">Run Name</th><th scope="col">Status</th><th scope="col">Date</th><th scope="col">AI Cost</th><th scope="col">Action</th></tr></thead><tbody>')
        for r in shown:
            label = r['run'].split('/')[-1] if not r['batch'] else r['run'].split('/')[1]
            B.append(f'<tr><th scope="row">{book_cell(r["book"], r["file"])}</th><td>{E(label)}' + (' <span class="pp-note">(batch)</span>' if r['batch'] else '') +
                     f'</td><td>{E(r["words"])}</td><td class="pp-nw">{E(D.day(r["when"]) if r["when"] else "date not recorded")}</td>'
                     f'<td>{E(money(r["cost"]))}' + (' <span class="pp-note">(saved reply)</span>' if r['reused'] else '') +
                     f'</td><td><a class="pp-btn" href="{E(run_href(r["run"]))}">Open</a></td></tr>')
        B.append('</tbody></table></div>')
    if len(rows) > n:
        B.append(f'<p><a class="pp-btn" href="/?{E(urllib.parse.urlencode({**({"q": q} if q else {}), "n": n + 25, "bn": bn}))}#hm-more" id="hm-more">Show More Runs</a></p>')
    B.append('</section>')
    # batches
    bs = idx['batches']
    B.append(f'<section class="pp" aria-labelledby="hm-b-h"><h2 id="hm-b-h">Batches ({len(bs)})</h2>')
    if bs:
        B.append('<div class="pp-tw" tabindex="0" role="region" aria-label="Batches Table"><table class="hm-t"><thead><tr><th scope="col">Batch Name</th>'
                 '<th scope="col">Books</th><th scope="col">State</th><th scope="col">Date</th><th scope="col">AI Cost</th><th scope="col">Action</th></tr></thead><tbody>')
        for b in bs[:bn]:
            B.append(f'<tr><th scope="row">{E(b["label"])}</th><td>{b["done"]} of {b["books"]} finished</td><td>{E(b["state"])}</td>'
                     f'<td class="pp-nw">{E(D.day(b["when"]) if b["when"] else "date not recorded")}</td><td>{E(money(b["cost"]))}</td>'
                     f'<td><a class="pp-btn" href="/batch/{E(urllib.parse.quote(b["label"], safe=""))}/">Open</a></td></tr>')
        B.append('</tbody></table></div>')
        if len(bs) > bn: B.append(f'<p class="pp-note">The newest {bn} of {len(bs)} batches are shown.</p><p><a class="pp-btn" id="hm-bmore" '
                                  f'href="/?{E(urllib.parse.urlencode({**({"q": q} if q else {}), "n": n, "bn": bn + 25}))}#hm-bmore">Show More Batches</a></p>')
    else: B.append('<p>None yet.</p>')
    B.append('</section></main><script src="/app/home.js" defer></script></body></html>')
    return '\n'.join(B)

def appbar(current=False):
    """The app bar every page the app serves carries, right after the skip link: the way home."""
    return ('<nav class="pp-appbar" aria-label="App"><a href="/"' + (' aria-current="page"' if current else '') + '>Home</a></nav>')
