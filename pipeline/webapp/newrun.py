"""webapp/newrun.py: a single run started from the home page (#45, home interface): New Run's form, the free estimate
job, "Get a New Estimate", "Try Again" (decided from disk), "Spend" (through webapp/spend.py), and "New Run from the
Saved Reply". Every command is run_api.sh's own; nothing here sends to the AI service except the spend job spend.py made.

    estimate     ESTIMATE=1 [OCR_LANG=…] bash run_api.sh <book> <short name> <run name>     intake, audit, decide.py --dry-run
    spend        AUTO=1 MAX_USD=… MODEL=… [REVIEW=1] [OCR_LANG] bash run_api.sh …           paid (spend.authorize)
    rerun        [REVIEW=1] [OCR_LANG] bash run_api.sh …   free: only when a complete reply is saved (03 §2); a rerun that would
                 reach a new call stops at run_api.sh's y/N question (stdin is empty) and the page says to get a new estimate
    replay       python3 review_workorder.py <run> --replay-to <new folder>, then INTAKE_REUSE=1 REPLY=… REVIEW=1 RUN_DIR=…
                 bash run_api.sh … (free; for a run that can no longer be reviewed)

The short name (runs/<name>/) comes from the book's file name and is unique per sha256: a folder already holding runs
of another book gets "-2", "-3"… (02 M4). The Run Name is the label; any folder or job that already names it is refused.
"""
import os, re, sys, json, datetime, urllib.parse
from lib import costs, dates as D
from review import sessions as S
from . import config, jobs, books as BK, spend as SP

RUN_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
E = None

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def default_run_name(): return f'run-{datetime.datetime.now():%Y-%m-%d-%H%M}'

def clean_stem(file):
    return re.sub(r'[^A-Za-z0-9_-]+', '_', os.path.splitext(os.path.basename(file))[0]).strip('_-') or 'book'

def folder_shas(d):
    """The sha256s of the books whose runs are in runs/<name>/ (each label's intake or record), and whether every label
    could be read."""
    out, all_known = set(), True
    try: labels = [e.path for e in os.scandir(d) if e.is_dir() and not e.name.startswith('.')]
    except OSError: return out, True
    for L in labels:
        sha = ((_load(os.path.join(L, '_intake', 'intake.json')) or {}).get('original') or {}).get('sha256') \
              or ((_load(os.path.join(L, 'record.json')) or {}).get('document') or {}).get('sha256') \
              or ((_load(os.path.join(L, 'review_stop.json')) or {}).get('sha256'))
        if sha: out.add(sha)
        elif os.listdir(L): all_known = False
    return out, all_known

def short_name(s, book, taken_jobs=None):
    """runs/<name>/ for this book: its cleaned file stem, unless that folder holds runs of another sha256 (then -2, -3…)."""
    base = clean_stem(book['path']); n = 1
    taken_jobs = taken_jobs if taken_jobs is not None else {(j['run'].split('/')[0], j.get('book_sha')) for j in jobs.all_jobs(s['jobs']) if j.get('book_sha')}
    while True:
        name = base if n == 1 else f'{base}-{n}'
        d = os.path.join(s['runs'], name)
        others = {sh for nm, sh in taken_jobs if nm == name and sh != book['key']}
        if name not in ('batches',) and not others:
            if not os.path.isdir(d): return name
            shas, known = folder_shas(d)
            if known and shas <= {book['key']}: return name
        n += 1

def run_taken(s, R):
    return os.path.exists(R) or any(j.get('dir') == os.path.abspath(R) for j in jobs.all_jobs(s['jobs']))

def check_untagged(s, setup, book):
    from . import checks
    if book.get('tagged') is False and not checks.untagged_ready(setup or []):
        raise ValueError('Text recognition (OCR) isn\'t set up on this computer, and this book needs it. Whoever looks after the app can install it.')

# ------------------------------------------------------------------ the estimate (free)
def start_estimate(s, setup, key, run_name, ocr_lang, review_first):
    """New Run: the free estimate job. Returns the job; raises ValueError with the reason (plain words)."""
    book = BK.by_key(s, key)
    if not book: raise ValueError('This book\'s file has changed or is gone. Go back to the home page to see the list again.')
    if book['locked']: raise ValueError('This PDF is locked with a password. Add an unlocked copy and start a new run.')
    run_name = str(run_name or '').strip()
    if not RUN_NAME.fullmatch(run_name): raise ValueError('A Run Name starts with a letter or digit and uses only letters, digits, "-" and "_" (at most 64).')
    langs = dict(BK.ocr_choices(BK.installed_langs(s)))
    if ocr_lang not in langs: raise ValueError('Choose an OCR language from the list.')
    m = BK.read_meta(book['path']); book['tagged'] = m.get('tagged')
    check_untagged(s, setup, book)
    name = short_name(s, book)
    R = os.path.join(s['runs'], name, run_name)
    if run_taken(s, R): raise ValueError(f'A run named "{run_name}" already exists for this book. Choose another Run Name.')
    os.makedirs(R)
    env = {'ESTIMATE': '1', 'OCR_LANG': ocr_lang}
    argv = ['bash', 'run_api.sh', book['path'], name, run_name]
    return jobs.create(s['jobs'], 'estimate', f'{name}/{run_name}', argv, config.child_env(s, env), env_set=env, R=R, supersede_waiting=True,
                       what='Get the estimate', book_sha=book['key'], book_name=book['name'], book_file=book['file'], run_name=run_name,
                       review_first=bool(review_first), ocr_name=langs[ocr_lang])

def again_estimate(s, run, R):
    """"Get a New Estimate": the same settings as the run's last estimate job (never a form again)."""
    ej = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run and j['kind'] == 'estimate']
    if not ej: raise ValueError('This run wasn\'t started from the home page, so its settings aren\'t known here. Start a new run from the home page.')
    if os.path.isfile(os.path.join(R, 'record.json')): raise ValueError('This run has finished.')
    if os.path.isfile(os.path.join(R, 'workorder.ai.json')): raise ValueError('The AI\'s decisions are waiting for a review: "Open the Review Page."')
    e = ej[-1]
    env = {k: v for k, v in (e.get('env_set') or {}).items() if k in ('ESTIMATE', 'OCR_LANG')}
    keep = {k: e.get(k) for k in ('book_sha', 'book_name', 'book_file', 'run_name', 'review_first', 'ocr_name')}
    return jobs.create(s['jobs'], 'estimate', run, e['argv'], config.child_env(s, env), env_set=env, R=R, supersede_waiting=True,
                       what='Get a new estimate', **keep)

# ------------------------------------------------------------------ Try Again, decided from disk (03 §2)
def retry_kind(R):
    """What "Try Again" does for an unfinished run: 'rerun' (free: a complete reply is saved), 'apply' (the review stop),
    'estimate' (everything else: a new estimate, then Spend), or None (finished)."""
    if os.path.isfile(os.path.join(R, 'record.json')): return None
    if os.path.isfile(os.path.join(R, 'workorder.ai.json')): return 'apply'
    if os.path.isfile(os.path.join(R, 'workorder.json')) and os.path.isfile(os.path.join(R, 'response.json')): return 'rerun'
    run = _load(os.path.join(R, 'run.json')) or {}
    if (os.path.isfile(os.path.join(R, 'response.json')) and (run.get('usage') or {}).get('cost_usd') and run.get('finish_reason') not in (None, 'length')
            and not run.get('error') and not run.get('response_from')): return 'rerun'
    return 'estimate'

def start_rerun(s, run, R):
    """"Try Again" when a complete reply is saved: run_api.sh again, free (no AUTO, no ESTIMATE)."""
    if retry_kind(R) != 'rerun': raise ValueError('A new AI call is needed. Get a new estimate first.')
    ej = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run and j['kind'] in ('estimate', 'spend', 'rerun')]
    if not ej: raise ValueError('This run wasn\'t started from the home page, so its settings aren\'t known here.')
    e = ej[-1]
    env = {k: v for k, v in (e.get('env_set') or {}).items() if k in ('OCR_LANG', 'REVIEW')}
    if e['kind'] == 'estimate' and e.get('review_first'): env['REVIEW'] = '1'
    keep = {k: e.get(k) for k in ('book_sha', 'book_name', 'book_file', 'run_name', 'review_first', 'ocr_name')}
    return jobs.create(s['jobs'], 'rerun', run, e['argv'], config.child_env(s, env), env_set=env, R=R, what='Try again (the saved reply is reused)', **keep)

# ------------------------------------------------------------------ Spend
def start_spend(s, run, R, body):
    try: a = SP.authorize(s, str(body.get('kind') or 'workorder'), run, R, str(body.get('fingerprint') or ''), body.get('no_personal_information'))
    except SP.Refused as e: raise ValueError(str(e))
    return jobs.create(s['jobs'], 'spend', run, a['argv'], config.child_env(s, a['env_set']), env_set=a['env_set'], R=R, paid=True,
                       what='Spend: the AI call' + (' (test: a saved reply)' if a['extra']['test'] else ''), **a['extra'])

# ------------------------------------------------------------------ New Run from the Saved Reply (decided 2026-10-28)
def start_replay(s, run, R, label):
    """A new run of the same book from this run's saved reply (free), for a run that can no longer be reviewed: the
    intake result and the reply are copied (review_workorder.py --replay-to), then run_api.sh with INTAKE_REUSE=1 REPLY=…
    REVIEW=1 in the new folder. The original PDF is found by its sha256."""
    from lib import release as REL
    if REL.cleared(R): raise ValueError('This book\'s working files were cleared, so its saved reply can\'t be used again.')
    rec = _load(os.path.join(R, 'record.json')) or {}
    if not rec.get('raw_reply'): raise ValueError('This run has no saved AI reply.')
    label = str(label or '').strip()
    if not RUN_NAME.fullmatch(label): raise ValueError('A Run Name starts with a letter or digit and uses only letters, digits, "-" and "_" (at most 64).')
    from . import runs as RN
    doc = rec.get('document') or {}
    src = RN.find_original(s, doc.get('sha256'), doc.get('file'))
    if not src: raise ValueError('The book\'s original PDF wasn\'t found in the folder of original PDFs or of added books.')
    parent = os.path.dirname(R) if not run.startswith('batches/') else os.path.join(s['runs'], clean_stem(src))
    name = os.path.basename(parent)
    D_ = os.path.join(parent, label)
    if run_taken(s, D_) or os.path.exists(D_.rstrip(os.sep) + '.reply.txt'): raise ValueError(f'A run named "{label}" already exists for this book. Choose another Run Name.')
    os.makedirs(D_)
    reply = D_.rstrip(os.sep) + '.reply.txt'
    env = {'INTAKE_REUSE': '1', 'REPLY': reply, 'REVIEW': '1', 'RUN_DIR': D_}
    nxt = {'kind': 'replay', 'argv': ['bash', 'run_api.sh', src, name, label], 'env': config.child_env(s, env), 'env_set': env,
           'extra': {'what': 'Run the book from the saved reply', 'run_name': label, 'book_sha': doc.get('sha256'), 'book_file': doc.get('file'),
                     'book_name': BK.name_of_sha(s, doc.get('sha256'), doc.get('file')), 'review_first': True}}
    return jobs.create(s['jobs'], 'replay-copy', f'{name}/{label}', [sys.executable, 'review_workorder.py', R, '--replay-to', D_],
                       config.child_env(s), R=D_, then=nxt, what='Copy the saved reply and the intake result', run_name=label,
                       book_sha=doc.get('sha256'), book_file=doc.get('file'), book_name=BK.name_of_sha(s, doc.get('sha256'), doc.get('file')))

# ------------------------------------------------------------------ the New Run page
def form_page(s, key):
    import html
    E = html.escape
    from . import home as HM
    book = BK.by_key(s, key)
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>New Run</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page hm-page"><a class="skip" href="#main">Skip to the content</a>')
    if not book:
        return head + ('<header><h1>New Run</h1></header><main id="main" tabindex="-1"><div class="pp"><p>This book\'s file has changed or is gone.</p>'
                       '<p><a class="pp-btn" href="/">Back to the Home Page</a></p></div></main></body></html>')
    langs = BK.ocr_choices(BK.installed_langs(s))
    opts = ''.join(f'<option value="{E(v)}"' + (' selected' if v == 'eng' else '') + f'>{E(n)}</option>' for v, n in langs)
    return head + (f'<header><h1>New Run</h1><p class="mc-book">{HM.book_cell(book["name"], book["file"])}</p></header>'
        '<main id="main" tabindex="-1"><form class="pp hm-form" id="hm-newrun" data-api="/api/new/estimate">'
        f'<input type="hidden" name="book" value="{E(book["key"])}">'
        '<div class="mc-field"><label for="nr-name">Run Name</label>'
        f'<input type="text" id="nr-name" name="run_name" value="{E(default_run_name())}" required maxlength="64" pattern="[A-Za-z0-9][A-Za-z0-9_\\-]{{0,63}}" aria-describedby="nr-name-h">'
        '<p class="mc-help" id="nr-name-h">Letters, digits, "-" and "_". It names this run in the list of earlier runs.</p></div>'
        '<div class="mc-field"><label for="nr-lang">OCR Language</label>'
        f'<select id="nr-lang" name="ocr_lang" aria-describedby="nr-lang-h">{opts}</select>'
        '<p class="mc-help" id="nr-lang-h">Used only for pages that need OCR (scanned pages). Choose the book\'s language; it is never guessed.</p></div>'
        '<div class="mc-field"><label class="hm-check"><input type="checkbox" id="nr-review" name="review_first" checked> Review First</label>'
        '<p class="mc-help">The run stops after the AI\'s decisions, so a person can review them before anything is applied.</p></div>'
        '<p class="mc-help">"Get the Estimate" prepares the book and works out what the AI call could cost. It is free: nothing is sent to the AI '
        'until you select "Spend" on the next page.</p>'
        '<div id="hm-msg" class="pp-msg" tabindex="-1" hidden></div>'
        '<div class="pp-row"><button type="submit" class="pp-primary">Get the Estimate</button><a class="pp-btn" href="/">Cancel</a></div>'
        '</form></main><script src="/app/home.js" defer></script></body></html>')
