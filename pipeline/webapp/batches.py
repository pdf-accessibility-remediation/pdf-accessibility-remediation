"""webapp/batches.py: batches from the home page (#45, requirement 2; 01 §3.2 as amended by 03 §7). batch_api.sh is not
changed: the app runs each book's estimate itself (exactly batch_api.sh's own estimate command), adds them up, and the
batch's Spend runs batch_api.sh, which estimates again (intake and audits reused) and refuses on its own when over.

    start(s, setup, keys, label)   the book list, the batch's record, one free estimate job per book (ASK_LANG=1: D4)
    state(s, label)                          {label, phase, books: [{name, book, file, status, href}], totals, spend, …}
    spend(s, label, body)                    the batch job (webapp/spend.py authorize_batch): paid; one place of max_jobs,
                                             JOBS (batch_jobs) of its books in progress at once
    again(s, label)                          "Run the Unfinished Books Again": new estimates for the books without a result;
                                             the next Spend adds RETRY=1

    runs/.app/batches/<label>.books.txt      one book per line: <short name> <absolute path> (batch_api.sh's book list)
    runs/.app/batches/<label>.json           {label, created, langs: {name: OCR language answered}, books: [{name, key, file, book}]}
                                             (a batch made before D4 has one ocr_lang for every book instead)
    estimate job   ESTIMATE=1 RUN_DIR=runs/batches/<label>/<name> [OCR_LANG] bash run_api.sh <book> <name> <label>
    batch job      AUTO=1 JOBS=… BATCH_MAX_USD=… MAX_USD=… MODEL=… [OCR_LANG] [RETRY=1] bash batch_api.sh <label> <books.txt>

A short name is the book's cleaned file stem, unique in the batch ("-2", "-3"… for a second book of the same stem); a
path holding "#" or "|" (the book list's comment and result marks) is refused. Book statuses use the home page's words.
"""
import os, re, json, hashlib, datetime, urllib.parse
from lib import costs
from . import config, jobs, books as BK, newrun as NR, home as HM, logs, lang as LG

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
    return os.path.isdir(folder(s, label)) or os.path.isfile(meta_path(s, label)) or os.path.isfile(list_path(s, label))

# ------------------------------------------------------------------ New Batch
def start(s, setup, keys, plain):
    """New Batch. `plain`: the Batch Name in the person's own words (optional); the folder label is derived from it
    (webapp/names.py label_for), and the plain name is kept by the app only."""
    from . import names as NM
    plain = NM.clean_name(plain)
    if not plain: raise ValueError('Enter a name for the batch.')                    # P10: required
    keys = [k for k in dict.fromkeys(keys or []) if isinstance(k, str)]
    if len(keys) < 2: raise ValueError('Select two or more PDFs for a batch.')
    cap = int(s.get('max_books_per_batch') or 50)
    if len(keys) > cap: raise ValueError(f'A batch can hold up to {cap} PDFs. Split them into two batches.')
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
    for _ in range(20):                                  # two requests can fold to the same free label at once (07 L1):
        js_ = jobs.all_jobs(s['jobs'])                   #   the second derives it again ("_2")
        label = NM.label_for(plain, 'batch', lambda lab: exists(s, lab) or any(jobs.related(j['run'], f'batches/{lab}') for j in js_))
        try: f = open(list_path(s, label), 'x', encoding='utf-8'); break
        except FileExistsError: continue
    else: raise ValueError('A batch with this name is being started right now. Try again in a moment.')
    with f:
        f.write(f'# batch {label}, made by the app {datetime.datetime.now().isoformat(timespec="seconds")}: <short name> <absolute path>\n')
        for b in bs: f.write(f'{b["name"]} {b["path"]}\n')
    json.dump({'label': label, 'created': datetime.datetime.now().isoformat(timespec='seconds'), 'langs': {},
               'books': [{k: b[k] for k in ('name', 'key', 'file', 'book')} for b in bs]},
              open(meta_path(s, label), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for b in bs: os.makedirs(os.path.join(folder(s, label), b['name']))
    if plain: NM.set_run_name(s, label, plain, kind='batches')
    return [estimate_job(s, label, b) for b in bs]

def estimate_job(s, label, b):
    """A PDF's free estimate in a batch: ASK_LANG=1 until a person gave its OCR language on its row (D4), then that language
    (English: unset, intake's default), kept in the batch's record (langs) and, for batch_api.sh, in ocr_langs.tsv."""
    from . import lang as LG
    R = os.path.join(folder(s, label), b['name'])
    meta = _load(meta_path(s, label)) or {}
    lang = (meta.get('langs') or {}).get(b['name'])
    env = {**(LG.env_for(lang) if lang else {'ESTIMATE': '1', 'OCR_LANG': meta['ocr_lang']} if meta.get('ocr_lang')   # a batch made before D4
              else {'ESTIMATE': '1', 'ASK_LANG': '1'}), 'RUN_DIR': R}
    path = b.get('path') or next((x.split(' ', 1)[1].rstrip('\n') for x in open(list_path(s, label), encoding='utf-8')
                                  if not x.startswith('#') and x.split(' ', 1)[0] == b['name']), None)
    return jobs.create(s['jobs'], 'batch-estimate', f'batches/{label}/{b["name"]}', ['bash', 'run_api.sh', path, b['name'], label],
                       config.child_env(s, env), env_set=env, R=R, supersede_waiting=True, what='Get the estimate',
                       book_sha=b['key'], book_file=b['file'])

# ------------------------------------------------------------------ the batch's state
def _book_status(s, label, b, R, jl, batch_job):
    """A book's status in the home page's words, from disk and the jobs."""
    if HM.is_run(R):
        row = HM.row_of(s, f'batches/{label}/{b["name"]}', R)
        HM.over(s, [row])
    else: row = {'status': 'Waiting', 'words': 'Waiting', 'finished': False}
    mine = [j for j in jl if j['run'] == f'batches/{label}/{b["name"]}']
    if mine and mine[-1]['status'] in jobs.ACTIVE:
        k = mine[-1]['kind']
        row['words'] = 'Waiting to Start' if mine[-1]['status'] == 'queued' else 'Applying the Reviewed Decisions' if k == 'apply' else \
                       'Waiting for Review' if k == 'review' else 'Writing the Batch Summary' if k == 'summary' else 'Estimating'
    elif batch_job and batch_job['status'] == 'running' and not row['finished']:
        lp = os.path.join(folder(s, label), f'{b["name"]}.log')
        try: st = logs.now_step('apply', logs.steps(open(lp, encoding='utf-8', errors='replace').read()))
        except OSError: st = None
        row['words'] = 'Running' + (f': {st["words"]}' if st else '') if os.path.exists(lp) or st else row['words']
    elif not row["finished"] and LG.question(s, R, mine):     # D4: its language is asked on its row
        row['status'] = row['words'] = 'Waiting for a Language'
    elif mine and mine[-1]['status'] in ('failed', 'interrupted') and not row['finished']:
        it = (_load(os.path.join(R, '_intake', 'intake.json')) or {}).get('status')
        row['words'] = 'Stopped: Needs a Person' if it == 'stopped' else 'Failed'
    return row

_DASH = {}
def dashboard(s, label, out):
    """The batch dashboard drawn in the batch page (P8): report_html's own rows (summary_rows, one source with summary.html),
    cached per book by its records' mtimes. A book not applied yet (waiting for review or a language, running, stopped)
    has no result columns: blank, never 0 or OK (Patrick, 2026-11-06)."""
    import report_html
    B = folder(s, label)
    rows = []
    for b in out:
        R = os.path.join(B, b['name'])
        r = None
        if b['finished']:
            k = (R, tuple(HM.key_of(R)))
            r = _DASH.get(k)
            if r is None:
                try:
                    rec = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
                    g = report_html.glance_of(R, rec, report_html.labels_of(R, rec)); vg = g['verapdf']
                    r = {'needs': g['needs_person']['total'], 'ai': g['ai_decisions']['count'], 'safety': report_html.safety_state(g),
                         'vb': vg.get('before_rules'), 'va': vg.get('after_rules'), 'new': len(vg.get('newly_failing') or []),
                         'cost': b.get('cost') or 0, 'pages': (rec.get('document') or {}).get('pages'), 'reviewed': bool(g['ship'][0]['ok'])}
                except (OSError, ValueError, KeyError, TypeError, IndexError): r = None
                _DASH[k] = r
        rows.append({'name': b['name'], 'book': b['book'], 'file': b['file'], 'status': b['status'], 'tone': b.get('tone'), 'href': b['href'], 'result': r})
    rows.sort(key=lambda x: (x['result'] is None, -((x['result'] or {}).get('needs') or 0)))
    return rows

def fingerprint(total):
    return hashlib.sha256(json.dumps([[b['R'], (b['estimate'] or {}).get('fingerprint'), b['adds_usd']] for b in total['books']],
                                     sort_keys=True).encode()).hexdigest()

def state(s, label):
    bs = books_of(s, label)
    jl = jobs.all_jobs(s['jobs'])
    bj = [j for j in jl if j['run'] == f'batches/{label}' and j['kind'] == 'batch']
    batch_job = bj[-1] if bj else None
    B = folder(s, label)
    out, Rs, flagged, missing, est_active, reviewing, asking = [], [], [], [], False, [], []
    for b in bs:
        R = os.path.join(B, b['name'])
        row = _book_status(s, label, b, R, jl, batch_job)
        stopped = (_load(os.path.join(R, '_intake', 'intake.json')) or {}).get('status') == 'stopped'
        mine = [j for j in jl if j['run'] == f'batches/{label}/{b["name"]}']
        if mine and mine[-1]['status'] in jobs.ACTIVE and mine[-1]['kind'] == 'batch-estimate': est_active = True
        q = None if row['finished'] or (mine and mine[-1]['status'] in jobs.ACTIVE) else LG.question(s, R, mine)
        if os.path.isfile(os.path.join(R, 'workorder.ai.json')) and not row['finished']: reviewing.append(b['name'])   # D2a: never sent again
        elif q: asking.append(b['name'])                                         # D4: waits for its language
        elif stopped and not row['finished']: flagged.append(b['name'])
        elif not row['finished']:
            Rs.append(R)
            if not costs.estimate(R) and not (os.path.isfile(os.path.join(R, 'workorder.json')) and os.path.isfile(os.path.join(R, 'response.json'))):
                missing.append(b['name'])
        from . import names as NM
        out.append({'name': b['name'], 'book': NM.book_name(s, b.get('key'), b.get('file') or '') if b.get('key') else b.get('book'), 'file': BK.shown_file(b.get('file') or ''), 'status': row['words'], 'finished': row['finished'],
                    'tone': tone(row, R), 'language': q,
                    'href': HM.run_href(f'batches/{label}/{b["name"]}'), 'cost': row.get('cost') or 0})
    total = costs.batch(Rs, limits=costs.limits_of(s))
    spent = round(sum(x['cost'] or 0 for x in out if x['finished']) + total['spent_usd'], 6)
    active = batch_job and batch_job['status'] in jobs.ACTIVE
    needs = batch_job and batch_job['status'] == 'needs-spend'
    finished = sum(1 for x in out if x['finished'])
    summary = os.path.isfile(os.path.join(B, 'summary.html'))
    phase = ('estimating' if est_active else 'running' if active else 'needs-spend' if needs else
             'language' if asking else
             'finished' if finished == len(out) and out else
             'review' if reviewing and finished + len(reviewing) + len(flagged) == len(out) else
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
    return {'label': label, 'phase': phase, 'books': out, 'flagged': flagged, 'missing': missing, 'test': test, 'reviewing': reviewing, 'asking': asking,
            'from_app': bool(meta), 'ocr_name': meta.get('ocr_name'),   # a batch made before D4: its one OCR language
            'trashed': {'n': len(trashed(s, label)), 'cost_usd': round(sum(x.get('cost_usd') or 0 for x in trashed(s, label)), 6)},
            'totals': {'ceiling_usd': total['ceiling_usd'], 'limit_usd': total['limit_usd'], 'credit_usd': total['credit_usd'],
                       'spent_usd': spent, 'books_to_send': len(Rs), 'finished': finished, 'expected': total['expected'],
                       'shown_ceiling_usd': ((batch_job or {}).get('shown') or {}).get('ceiling_usd')},
            'fingerprint': fingerprint(total), 'spend': spend, 'summary': summary, 'dashboard': dashboard(s, label, out),
            'again': bool(meta) and phase in ('stopped', 'finished') and finished + len(reviewing) < len(out),
            'job': ({k: batch_job.get(k) for k in ('id', 'status', 'exit', 'started', 'ended')} if batch_job else None)}

# ------------------------------------------------------------------ Spend, and again
def spend(s, label, body):
    from . import spend as SP
    st = state(s, label)
    if st['phase'] != 'ready': raise ValueError('This batch isn\'t ready to send: reload the page.')
    if str(body.get('fingerprint') or '') != st['fingerprint']: raise ValueError(SP.CHANGED)
    Rs = [os.path.join(folder(s, label), b['name']) for b in st['books'] if not b['finished'] and b['name'] not in st['flagged']]
    total = costs.batch(Rs, limits=costs.limits_of(s))
    try: a = SP.authorize_batch(s, label, list_path(s, label), total, st['fingerprint'])
    except SP.Refused as e: raise ValueError(str(e))
    env = dict(a['env_set'])
    meta = _load(meta_path(s, label)) or {}
    if meta.get('ocr_lang'): env['OCR_LANG'] = meta['ocr_lang']              # a batch made before D4: one language for every PDF
    if any(b['finished'] for b in st['books']) or os.path.isfile(os.path.join(folder(s, label), 'summary.md')): env['RETRY'] = '1'
    extra = dict(a['extra'])
    return jobs.create(s['jobs'], 'batch', f'batches/{label}', a['argv'], config.child_env(s, env), env_set=env, R=folder(s, label), paid=True,
                       what='Run the batch' + (' (test: saved replies)' if extra['test'] else ''), **extra)

def again(s, label):
    """"Run the Unfinished Books Again": a new free estimate for every book without a result."""
    meta = _load(meta_path(s, label))
    if not meta: raise ValueError('This batch wasn\'t made from the home page, so its settings aren\'t known here.')
    todo = [b for b in meta['books'] if not os.path.isfile(os.path.join(folder(s, label), b['name'], 'record.json'))]
    if not todo: raise ValueError('Every book in this batch has finished.')
    return [estimate_job(s, label, b) for b in todo]

def forget_books(s, label, names, moved):
    """PDFs moved to the Trash from a batch (#45 D8, webapp/trash.py): out of the app's book list (so a later "Run the
    Unfinished PDFs Again" or RETRY never sends them: a paid call for a PDF in the Trash), the batch's record, its
    ocr_langs.tsv; into the batch folder's trashed.json with their AI cost (summary.md's line and "Total Cost:"); then
    summary.md and summary.html written again from the PDFs left (batch_api.sh SUMMARY_ONLY=1, a job of its own). Any
    estimate of the batch is stale from now on: its fingerprint covers the PDFs it was made for."""
    import fcntl
    gone = set(names)
    lp = list_path(s, label)
    if os.path.isfile(lp):
        keep = [l for l in open(lp, encoding='utf-8') if l.startswith('#') or l.split(' ', 1)[0] not in gone]
        tmp = lp + '.tmp'; open(tmp, 'w', encoding='utf-8').writelines(keep); os.replace(tmp, lp)
    mp = meta_path(s, label)
    if os.path.isfile(mp):
        with open(mp + '.lock', 'a') as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            meta = _load(mp) or {}
            meta['books'] = [b for b in meta.get('books') or [] if b.get('name') not in gone]
            meta['langs'] = {k: v for k, v in (meta.get('langs') or {}).items() if k not in gone}
            tmp = mp + '.tmp'; json.dump(meta, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, mp)
    B = folder(s, label)
    ol = os.path.join(B, 'ocr_langs.tsv')
    if os.path.isfile(ol):
        keep = [l for l in open(ol, encoding='utf-8') if l.startswith('#') or l.split('\t', 1)[0] not in gone]
        tmp = ol + '.tmp'; open(tmp, 'w', encoding='utf-8').writelines(keep); os.replace(tmp, ol)
    tp = os.path.join(B, 'trashed.json')
    d = (_load(tp) or []) + [{'name': m['name'], 'cost_usd': m['cost_usd'], 'moved': datetime.datetime.now().isoformat(timespec='seconds')} for m in moved]
    tmp = tp + '.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), indent=1); os.replace(tmp, tp)
    if os.path.isfile(os.path.join(B, 'summary.md')) or os.path.isfile(os.path.join(B, 'summary.html')):
        try:
            jobs.create(s['jobs'], 'summary', f'batches/{label}', ['bash', 'batch_api.sh', label], config.child_env(s, {'SUMMARY_ONLY': '1'}),
                        env_set={'SUMMARY_ONLY': '1'}, counted=False, R=B, what='Write the batch summary again')
        except ValueError:                                  # a job of the batch was queued meanwhile (review 12 N3): the files
            pass                                            # wait for the next batch run, book apply or move (the batch page
                                                            # reads the folders live); everything above is already right

def trashed(s, label):
    """[{name, cost_usd, moved}]: PDFs of this batch moved to the Trash (the batch folder's trashed.json)."""
    return _load(os.path.join(folder(s, label), 'trashed.json')) or []

def answer_language(s, label, name, lang):
    """A PDF's "Language of the Scanned Pages" answered on the batch page (D4): kept in the batch's record and, when it is
    not English, in the batch folder's ocr_langs.tsv (batch_api.sh gives that PDF its own OCR_LANG); then its estimate again."""
    from . import lang as LG
    import fcntl
    meta = _load(meta_path(s, label))
    if not meta: raise ValueError('This batch wasn\'t made from the home page, so its settings aren\'t known here.')
    b = next((x for x in meta.get('books') or [] if x['name'] == name), None)
    if not b: raise ValueError('There is no such PDF in this batch.')
    LG.check(s, os.path.join(folder(s, label), name), lang)
    with open(meta_path(s, label) + '.lock', 'a') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        meta = _load(meta_path(s, label)) or meta
        meta.setdefault('langs', {})[name] = lang
        tmp = meta_path(s, label) + '.tmp'; json.dump(meta, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); os.replace(tmp, meta_path(s, label))
        rows = ''.join(f'{n}\t{l}\n' for n, l in sorted(meta['langs'].items()) if l != 'eng')
        p = os.path.join(folder(s, label), 'ocr_langs.tsv'); tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8').write('# <short name> <TAB> <OCR_LANG>: written by the app (Language of the Scanned Pages)\n' + rows); os.replace(tmp, p)
    return estimate_job(s, label, b)

# ------------------------------------------------------------------ pages
def form_page(s, keys):
    import html
    E = html.escape
    keys = [k for k in dict.fromkeys(keys) if isinstance(k, str)]
    bs = [b for b in (BK.by_key(s, k) for k in keys) if b]
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>New Batch</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a><header><h1>New Batch</h1></header><main id="main" tabindex="-1">')
    if len(bs) < 2:
        return head + '<div class="pp"><p>Select two or more PDFs on the home page first.</p></div></main></body></html>'
    items = ''.join(f'<li>{HM.book_cell(b["name"], b["file"])}<input type="hidden" name="books" value="{E(b["key"])}"></li>' for b in bs)
    return head + (f'<form class="pp hm-form" id="hm-newbatch" data-api="/api/batch/new"><h2>PDFs ({len(bs)})</h2><ul class="hm-active">{items}</ul>'
        '<div class="mc-field"><label for="nb-name">Batch Name</label>'
        '<input type="text" id="nb-name" name="label" maxlength="120" required aria-describedby="nb-name-h">'
        '<p class="mc-help" id="nb-name-h">In your own words, for example "Press backlist, spring". It names this batch in My Workspace.</p></div>'
        '<p class="mc-help">"Get the Estimates" prepares every PDF and works out what the batch could cost. It is free: nothing is sent to the AI '
        'until you select "Start Remediation" on the batch page.</p><div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>'
        '<div class="pp-row"><button type="submit" class="pp-primary">Get the Estimates</button></div>'
        '</form></main><script src="/app/home.js" defer></script></body></html>')

def tone(row, R):
    """A book's state in the side list's left border (P15, Patrick 2026-11-06), always with its status in words beside it:
    processing (grey, with a spinner), new (grey: its review not opened yet), review (blue: the review opened, choices
    saved or finished, up to Pending Evaluation), person (yellow: stopped for a person), done (green: Ready or Shipped),
    failed (red: the last job failed)."""
    st, w = row.get('status') or '', row.get('words') or ''
    if row.get('active') or w in ('Estimating', 'Waiting to Start') or w.startswith('Running') or w.startswith('Applying'): return 'processing'
    if st == 'Failed' or w == 'Failed': return 'failed'
    if st in ('Ready', 'Shipped', 'Cleared'): return 'done'
    if w.startswith('Stopped') or w.startswith('Waiting for a Language'): return 'person'
    opened = any(os.path.exists(os.path.join(R, *x)) for x in (('review.json',), ('review_decisions.json',), ('record.json',),
                                                                 ('reviews', 'review_decisions.json'), ('reviews', 'sessions')))
    if os.path.exists(os.path.join(R, 'record.json')):
        rec = _load(os.path.join(R, 'record.json')) or {}
        ship = (rec.get('glance') or {}).get('ship') or []
        opened = bool(ship and ship[0].get('ok')) or os.path.isdir(os.path.join(R, 'reviews', 'sessions'))
    return 'review' if opened else 'new'

def body_class(page, closed):
    """The side list's layout written into the page's <body> (D7): bn-on, and bn-closed or bn-auto (no choice made yet)."""
    add = 'bn-on ' + ('bn-auto' if closed is None else 'bn-closed' if closed else 'bn-open')
    i = page.lower().find('<body'); j = page.find('>', i) if i >= 0 else -1
    if j < 0: return page
    tag = page[i:j]
    m = re.search(r'class="([^"]*)"', tag)
    new = tag[:m.start(1)] + m.group(1) + ' ' + add + tag[m.end(1):] if m else tag + f' class="{add}"'
    return page[:i] + new + page[j:]

def toggle(n, open_=True):
    """The side list's button, beside "Home Page" in the app bar (P5; in the header from Patrick's test, 2026-11-07)."""
    return (f'<button type="button" class="pp-btn bn-toggle" id="bn-toggle" aria-expanded="{"true" if open_ else "false"}" aria-controls="bn-list">'
            + ('Hide the PDF List' if open_ else f'Show the PDF List ({n})') + '</button>')

def item(b, current):
    import html
    E = html.escape
    spin = '<span class="bn-spin" role="img" aria-label="Processing"></span>' if b.get('tone') == 'processing' else ''
    return (f'<li><a class="bn-t-{E(b.get("tone") or "new")}" href="{E(b["href"])}"' + (' aria-current="page"' if b['name'] == current else '') +
            f' data-book="{E(b["name"])}"><span class="bn-name">{E(b["book"])}</span><span class="hm-file">Source PDF: {E(b["file"])}</span>'
            f'<span class="bn-st">{E(b["status"])}</span>{spin}</a></li>')

def nav(s, label, current=None, st=None, closed=None):
    """The side column (03 §7, 01 §3.2): the batch's PDFs, each with its status in words and its state in its left border
    (P15); the current one marked by its background and bold name. It is added at serve time; batch.js keeps the statuses
    current, and the button that hides it sits in the app bar (toggle())."""
    import html
    E = html.escape
    from . import names as NM
    st = st or state(s, label)
    items = ''.join(item(b, current) for b in st['books'])
    n = len(st['books'])
    return (f'<nav class="bn{" closed" if closed else ""}" id="pp-bnav" aria-label="PDFs in This Batch" data-label="{E(label)}">'
            f'<div id="bn-list"><p class="bn-h"><a href="/batch/{E(urllib.parse.quote(label, safe=""))}/"' + (' aria-current="page"' if current is None else '') +
            f'>Batch: {E(NM.shown_run(s, "batches/" + label))}</a> <span class="pp-note">({n} PDF{"" if n == 1 else "s"})</span></p><ul>{items}</ul></div></nav>')

def page(s, label, closed=None):
    import html
    from . import names as NM
    E = html.escape
    st = state(s, label)
    return body_class('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Batch: {E(NM.shown_run(s, "batches/" + label))}</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a>' + nav(s, label, st=st, closed=closed) +
            f'<header class="top pp-head pp-hd"><div class="pp-hd-main"><h1>Batch: {E(NM.shown_run(s, "batches/" + label))}</h1></div>'
            + HM.appbar(extra=toggle(len(st['books']), not closed)) + '</header><main id="main" tabindex="-1"><section class="pp" id="bt-panel" data-label="{E(label)}" aria-labelledby="bt-h">'
            '<h2 id="bt-h" tabindex="-1">This Batch</h2><div id="bt-body"><p>Loading…</p></div><div id="pp-msg" class="pp-msg" tabindex="-1" hidden></div>'
            '<div id="pp-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div></section></main>'
            '<script src="/app/batch.js" defer></script><script src="/app/trash.js" defer></script></body></html>', closed)

def with_nav(page, s, label, current, closed=None):
    """A book's run page inside a batch: the side list's button beside "Home Page" in the app bar (inside the run page's
    header: Patrick's test 2026-11-07, Q6), and the side column right after the skip link, laid out by the server (D7)."""
    from . import server as W
    st = state(s, label)
    bar = HM.appbar(extra=toggle(len(st['books']), not closed)); side = nav(s, label, current, st=st, closed=closed)
    page = body_class(page, closed)
    if W.APPBAR_MARK in page:
        a = page.rfind('<nav', 0, page.find(W.APPBAR_MARK)); i = page.find('</nav>', a)
        page = page[:a] + bar + page[i + 6:]
    else: side = bar + side                                 # a page with no app bar of its own: the bar comes first
    if W.SKIP in page: page = page.replace(W.SKIP, W.SKIP + side, 1)
    else: page = W.after_body(page, side)
    i = page.rfind('</body>'); js = '<script src="/app/batch.js" defer></script>\n'
    return page[:i] + js + page[i:] if i >= 0 else page + js
