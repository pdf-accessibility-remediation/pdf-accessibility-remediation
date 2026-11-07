"""webapp/batches.py: batches from the home page (#45, requirement 2; 01 §3.2 as amended by 03 §7). batch_api.sh is not
changed: the app runs each book's estimate itself (exactly batch_api.sh's own estimate command), adds them up, and the
batch's Spend runs batch_api.sh, which estimates again (intake and audits reused) and refuses on its own when over.

    start(s, setup, keys, label, ocr_lang)   the book list, the batch's record, one free estimate job per book
    state(s, label)                          {label, phase, books: [{name, book, file, status, href}], totals, spend, …}
    spend(s, label, body)                    the batch job (webapp/spend.py authorize_batch): paid, slots = JOBS
    again(s, label)                          "Run the Unfinished Books Again": new estimates for the books without a result;
                                             the next Spend adds RETRY=1

    runs/.app/batches/<label>.books.txt      one book per line: <short name> <absolute path> (batch_api.sh's book list)
    runs/.app/batches/<label>.json           {label, created, ocr_lang, books: [{name, key, file, book}]}
    estimate job   ESTIMATE=1 RUN_DIR=runs/batches/<label>/<name> [OCR_LANG] bash run_api.sh <book> <name> <label>
    batch job      AUTO=1 JOBS=… BATCH_MAX_USD=… MAX_USD=… MODEL=… [OCR_LANG] [RETRY=1] bash batch_api.sh <label> <books.txt>

A short name is the book's cleaned file stem, unique in the batch ("-2", "-3"… for a second book of the same stem); a
path holding "#" or "|" (the book list's comment and result marks) is refused. Book statuses use the home page's words.
"""
import os, re, json, hashlib, datetime, urllib.parse
from lib import costs
from . import config, jobs, books as BK, newrun as NR, home as HM, logs

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def meta_path(s, label): return os.path.join(s['jobs'], 'batches', f'{label}.json')
def list_path(s, label): return os.path.join(s['jobs'], 'batches', f'{label}.books.txt')
def folder(s, label): return os.path.join(s['runs'], 'batches', label)

def books_of(s, label):
    """[{name, key, file, book}]: the app's record of the batch, else (a batch made from the terminal) its folders."""
    m = _load(meta_path(s, label))
    if m and isinstance(m.get('books'), list): return m['books']
    B = folder(s, label); out = []
    try: names = sorted(e.name for e in os.scandir(B) if e.is_dir() and not e.name.startswith('.'))
    except OSError: names = []
    for n in names:
        R = os.path.join(B, n)
        if not HM.is_run(R): continue
        rec = _load(os.path.join(R, 'record.json')) or {}
        o = (_load(os.path.join(R, '_intake', 'intake.json')) or {}).get('original') or {}
        f = (rec.get('document') or {}).get('file') or o.get('file') or ''
        sha = (rec.get('document') or {}).get('sha256') or o.get('sha256')
        out.append({'name': n, 'key': sha, 'file': f, 'book': (BK.name_of_sha(s, sha, f) if sha else None) or BK.stem_name(f or n)})
    return out

def exists(s, label):
    return os.path.isdir(folder(s, label)) or os.path.isfile(meta_path(s, label))

# ------------------------------------------------------------------ New Batch
def start(s, setup, keys, label, ocr_lang):
    label = str(label or '').strip()
    if not NR.RUN_NAME.fullmatch(label): raise ValueError('A Batch Name starts with a letter or digit and uses only letters, digits, "-" and "_" (at most 64).')
    if exists(s, label) or any(jobs.related(j['run'], f'batches/{label}') for j in jobs.all_jobs(s['jobs'])):
        raise ValueError(f'A batch named "{label}" already exists. Choose another Batch Name.')
    langs = dict(BK.ocr_choices(BK.installed_langs(s)))
    if ocr_lang not in langs: raise ValueError('Choose an OCR language from the list.')
    keys = [k for k in dict.fromkeys(keys or []) if isinstance(k, str)]
    if len(keys) < 2: raise ValueError('Select two or more books for a batch.')
    bs, taken = [], set()
    for k in keys:
        b = BK.by_key(s, k)
        if not b: raise ValueError('A selected book\'s file has changed or is gone. Go back to the home page to see the list again.')
        if b['locked']: raise ValueError(f'"{b["name"]}" is locked with a password: add an unlocked copy, or leave it out.')
        if re.search(r'[#|\t\r\n]', b['path']) or b['path'] != b['path'].strip(): raise ValueError(f'"{b["name"]}" has a file name a batch can\'t use: add it again from the home page.')
        b['tagged'] = BK.read_meta(b['path']).get('tagged')
        NR.check_untagged(s, setup, b)
        base, n = NR.clean_stem(b['path']), 1
        while (base if n == 1 else f'{base}-{n}') in taken: n += 1
        name = base if n == 1 else f'{base}-{n}'; taken.add(name)
        bs.append({'name': name, 'key': b['key'], 'file': b['file'], 'book': b['name'], 'path': b['path']})
    os.makedirs(os.path.join(s['jobs'], 'batches'), exist_ok=True)
    with open(list_path(s, label), 'x', encoding='utf-8') as f:
        f.write(f'# batch {label}, made by the app {datetime.datetime.now().isoformat(timespec="seconds")}: <short name> <absolute path>\n')
        for b in bs: f.write(f'{b["name"]} {b["path"]}\n')
    json.dump({'label': label, 'created': datetime.datetime.now().isoformat(timespec='seconds'), 'ocr_lang': ocr_lang, 'ocr_name': langs[ocr_lang],
               'books': [{k: b[k] for k in ('name', 'key', 'file', 'book')} for b in bs]},
              open(meta_path(s, label), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for b in bs: os.makedirs(os.path.join(folder(s, label), b['name']))
    return [estimate_job(s, label, b, ocr_lang) for b in bs]

def estimate_job(s, label, b, ocr_lang):
    R = os.path.join(folder(s, label), b['name'])
    env = {'ESTIMATE': '1', 'RUN_DIR': R, 'OCR_LANG': ocr_lang}
    path = b.get('path') or next((x.split(' ', 1)[1].rstrip('\n') for x in open(list_path(s, label), encoding='utf-8')
                                  if not x.startswith('#') and x.split(' ', 1)[0] == b['name']), None)
    return jobs.create(s['jobs'], 'batch-estimate', f'batches/{label}/{b["name"]}', ['bash', 'run_api.sh', path, b['name'], label],
                       config.child_env(s, env), env_set=env, R=R, supersede_waiting=True, what='Get the estimate',
                       book_sha=b['key'], book_name=b['book'], book_file=b['file'], run_name=label)

# ------------------------------------------------------------------ the batch's state
def _book_status(s, label, b, R, jl, batch_job):
    """A book's status in the home page's words, from disk and the jobs."""
    if HM.is_run(R):
        row = HM.row_of(s, f'batches/{label}/{b["name"]}', R)
        HM.over(s, [row])
    else: row = {'status': 'Waiting', 'words': 'Waiting', 'finished': False}
    mine = [j for j in jl if j['run'] == f'batches/{label}/{b["name"]}']
    if mine and mine[-1]['status'] in jobs.ACTIVE:
        row['words'] = 'Estimating' if mine[-1]['status'] == 'running' else 'Waiting to Start'
    elif batch_job and batch_job['status'] == 'running' and not row['finished']:
        lp = os.path.join(folder(s, label), f'{b["name"]}.log')
        try: st = logs.now_step('apply', logs.steps(open(lp, encoding='utf-8', errors='replace').read()))
        except OSError: st = None
        row['words'] = 'Running' + (f': {st["words"]}' if st else '') if os.path.exists(lp) or st else row['words']
    elif mine and mine[-1]['status'] in ('failed', 'interrupted') and not row['finished']:
        it = (_load(os.path.join(R, '_intake', 'intake.json')) or {}).get('status')
        row['words'] = 'Stopped: Needs a Person' if it == 'stopped' else 'Failed'
    return row

def fingerprint(total):
    return hashlib.sha256(json.dumps([[b['R'], (b['estimate'] or {}).get('fingerprint'), b['adds_usd']] for b in total['books']],
                                     sort_keys=True).encode()).hexdigest()

def state(s, label):
    bs = books_of(s, label)
    jl = jobs.all_jobs(s['jobs'])
    bj = [j for j in jl if j['run'] == f'batches/{label}' and j['kind'] == 'batch']
    batch_job = bj[-1] if bj else None
    B = folder(s, label)
    out, Rs, flagged, missing, est_active = [], [], [], [], False
    for b in bs:
        R = os.path.join(B, b['name'])
        row = _book_status(s, label, b, R, jl, batch_job)
        stopped = (_load(os.path.join(R, '_intake', 'intake.json')) or {}).get('status') == 'stopped'
        mine = [j for j in jl if j['run'] == f'batches/{label}/{b["name"]}']
        if mine and mine[-1]['status'] in jobs.ACTIVE: est_active = True
        if stopped and not row['finished']: flagged.append(b['name'])
        elif not row['finished']:
            Rs.append(R)
            if not costs.estimate(R) and not (os.path.isfile(os.path.join(R, 'workorder.json')) and os.path.isfile(os.path.join(R, 'response.json'))):
                missing.append(b['name'])
        out.append({'name': b['name'], 'book': b['book'], 'file': BK.shown_file(b.get('file') or ''), 'status': row['words'], 'finished': row['finished'],
                    'href': HM.run_href(f'batches/{label}/{b["name"]}'), 'cost': row.get('cost') or 0})
    total = costs.batch(Rs, limits=costs.limits_of(s))
    spent = round(sum(x['cost'] or 0 for x in out if x['finished']) + total['spent_usd'], 6)
    active = batch_job and batch_job['status'] in jobs.ACTIVE
    needs = batch_job and batch_job['status'] == 'needs-spend'
    finished = sum(1 for x in out if x['finished'])
    summary = os.path.isfile(os.path.join(B, 'summary.html'))
    phase = ('estimating' if est_active else 'running' if active else 'needs-spend' if needs else
             'finished' if finished == len(out) and out else
             'stopped' if batch_job and batch_job['status'] in ('failed', 'interrupted', 'done') else
             'missing' if missing else 'ready' if Rs else 'stopped')
    test = bool(s.get('test_batch_from'))
    spend = None
    if phase == 'ready':
        why = None
        if not test:
            if total['blocked']: why = total['blocked'][0][1]['words']
            elif not total['fits']['batch']: why = f'This batch could cost more than the limit of ${total["limit_usd"]:.2f} per batch.'
            elif total['fits']['credit'] is False: why = 'There isn\'t enough credit for this batch.'
            elif total['credit_usd'] is None: why = 'The credit couldn\'t be checked, so the cost can\'t be compared with it.'
        spend = {'ok': not why, 'why': why}
    meta = _load(meta_path(s, label)) or {}
    return {'label': label, 'phase': phase, 'books': out, 'flagged': flagged, 'missing': missing, 'test': test,
            'from_app': bool(meta), 'ocr_name': meta.get('ocr_name'),
            'totals': {'ceiling_usd': total['ceiling_usd'], 'limit_usd': total['limit_usd'], 'credit_usd': total['credit_usd'],
                       'spent_usd': spent, 'books_to_send': len(Rs), 'finished': finished, 'expected': total['expected'],
                       'shown_ceiling_usd': ((batch_job or {}).get('shown') or {}).get('ceiling_usd')},
            'fingerprint': fingerprint(total), 'spend': spend, 'summary': summary,
            'again': bool(meta) and phase in ('stopped', 'finished') and finished < len(out) - 0,
            'job': ({k: batch_job.get(k) for k in ('id', 'status', 'exit', 'started', 'ended')} if batch_job else None)}

# ------------------------------------------------------------------ Spend, and again
def spend(s, label, body):
    from . import spend as SP
    st = state(s, label)
    if st['phase'] != 'ready': raise ValueError('This batch isn\'t ready to send: reload the page.')
    if str(body.get('fingerprint') or '') != st['fingerprint']: raise ValueError(SP.CHANGED)
    Rs = [os.path.join(folder(s, label), b['name']) for b in st['books'] if not b['finished'] and b['name'] not in st['flagged']]
    total = costs.batch(Rs, limits=costs.limits_of(s))
    try: a = SP.authorize_batch(s, label, list_path(s, label), total, st['fingerprint'], body.get('no_personal_information'))
    except SP.Refused as e: raise ValueError(str(e))
    env = dict(a['env_set'])
    meta = _load(meta_path(s, label)) or {}
    if meta.get('ocr_lang'): env['OCR_LANG'] = meta['ocr_lang']
    if any(b['finished'] for b in st['books']) or os.path.isfile(os.path.join(folder(s, label), 'summary.md')): env['RETRY'] = '1'
    extra = dict(a['extra']); slots = extra.pop('slots')
    return jobs.create(s['jobs'], 'batch', f'batches/{label}', a['argv'], config.child_env(s, env), env_set=env, R=folder(s, label), paid=True, slots=slots,
                       what='Run the batch' + (' (test: saved replies)' if extra['test'] else ''), run_name=label, book_name=f'Batch {label}', **extra)

def again(s, label):
    """"Run the Unfinished Books Again": a new free estimate for every book without a result."""
    meta = _load(meta_path(s, label))
    if not meta: raise ValueError('This batch wasn\'t made from the home page, so its settings aren\'t known here.')
    todo = [b for b in meta['books'] if not os.path.isfile(os.path.join(folder(s, label), b['name'], 'record.json'))]
    if not todo: raise ValueError('Every book in this batch has finished.')
    return [estimate_job(s, label, b, meta.get('ocr_lang') or 'eng') for b in todo]

# ------------------------------------------------------------------ pages
def form_page(s, keys):
    import html
    E = html.escape
    keys = [k for k in dict.fromkeys(keys) if isinstance(k, str)]
    bs = [b for b in (BK.by_key(s, k) for k in keys) if b]
    langs = BK.ocr_choices(BK.installed_langs(s))
    opts = ''.join(f'<option value="{E(v)}"' + (' selected' if v == 'eng' else '') + f'>{E(n)}</option>' for v, n in langs)
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>New Batch</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a><header><h1>New Batch</h1></header><main id="main" tabindex="-1">')
    if len(bs) < 2:
        return head + '<div class="pp"><p>Select two or more books on the home page first.</p><p><a class="pp-btn" href="/">Back to the Home Page</a></p></div></main></body></html>'
    items = ''.join(f'<li>{HM.book_cell(b["name"], b["file"])}<input type="hidden" name="books" value="{E(b["key"])}"></li>' for b in bs)
    return head + (f'<form class="pp hm-form" id="hm-newbatch" data-api="/api/batch/new"><h2>Books ({len(bs)})</h2><ul class="hm-active">{items}</ul>'
        '<div class="mc-field"><label for="nb-name">Batch Name</label>'
        f'<input type="text" id="nb-name" name="label" value="batch-{datetime.datetime.now():%Y-%m-%d-%H%M}" required maxlength="64" aria-describedby="nb-name-h">'
        '<p class="mc-help" id="nb-name-h">Letters, digits, "-" and "_". It names this batch in the list of batches.</p></div>'
        f'<div class="mc-field"><label for="nb-lang">OCR Language</label><select id="nb-lang" name="ocr_lang" aria-describedby="nb-lang-h">{opts}</select>'
        '<p class="mc-help" id="nb-lang-h">Used for every book\'s pages that need OCR (scanned pages). It is never guessed.</p></div>'
        '<p class="mc-help">Books in a batch are applied without a review first. Review each one afterwards from its page.</p>'
        '<p class="mc-help">"Get the Estimates" prepares every book and works out what the batch could cost. It is free: nothing is sent to the AI '
        'until you select "Spend" on the batch page.</p><div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>'
        '<div class="pp-row"><button type="submit" class="pp-primary">Get the Estimates</button><a class="pp-btn" href="/">Cancel</a></div>'
        '</form></main><script src="/app/home.js" defer></script></body></html>')

def nav(s, label, current=None):
    """The side column (03 §7, 01 §3.2): the batch's books, each with its status in words; the current book marked. It is
    added at serve time; batch.js keeps the statuses current, collapses the column and opens it as a list on a narrow screen."""
    import html
    E = html.escape
    st = state(s, label)
    items = ''.join(f'<li><a href="{E(b["href"])}"' + (' aria-current="page"' if b['name'] == current else '') +
                    f' data-book="{E(b["name"])}"><span class="bn-name">{E(b["book"])}</span><span class="hm-file">Source PDF Filename: {E(b["file"])}</span>'
                    f'<span class="bn-st">{E(b["status"])}</span></a></li>' for b in st['books'])
    n = len(st['books'])
    return (f'<nav class="bn" id="pp-bnav" aria-label="Books in This Batch" data-label="{E(label)}">'
            f'<button type="button" class="bn-toggle" id="bn-toggle" aria-expanded="true" aria-controls="bn-list">Hide the Book List</button>'
            f'<div id="bn-list"><p class="bn-h"><a href="/batch/{E(urllib.parse.quote(label, safe=""))}/"' + (' aria-current="page"' if current is None else '') +
            f'>Batch {E(label)}</a> <span class="pp-note">({n} book{"" if n == 1 else "s"})</span></p><ul>{items}</ul></div></nav>')

def page(s, label):
    import html
    E = html.escape
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Batch {E(label)}</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a>' + HM.appbar() + nav(s, label) +
            f'<header><h1>Batch {E(label)}</h1></header><main id="main" tabindex="-1"><section class="pp" id="bt-panel" data-label="{E(label)}" aria-labelledby="bt-h">'
            '<h2 id="bt-h" tabindex="-1">This Batch</h2><div id="bt-body"><p>Loading…</p></div><div id="pp-msg" class="pp-msg" tabindex="-1" hidden></div>'
            '<div id="pp-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div></section></main>'
            '<script src="/app/batch.js" defer></script></body></html>')

def with_nav(page, s, label, current):
    """A book's run page inside a batch: the side column after the app bar (after the skip link when there is none)."""
    from . import server as W
    n = nav(s, label, current)
    if W.APPBAR_MARK in page:
        i = page.find('</nav>', page.find(W.APPBAR_MARK))
        page = page[:i + 6] + n + page[i + 6:]
    elif W.SKIP in page: page = page.replace(W.SKIP, W.SKIP + W.HM.appbar() + n, 1)
    else: page = W.after_body(page, W.HM.appbar() + n)
    i = page.rfind('</body>'); js = '<script src="/app/batch.js" defer></script>\n'
    return page[:i] + js + page[i:] if i >= 0 else page + js
