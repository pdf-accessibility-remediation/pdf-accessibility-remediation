"""webapp/newrun.py: a single run started from the home page (#45, home interface): New Run's form, the free estimate
job, "Get a New Estimate", "Try Again" (decided from disk), "Spend" (through webapp/spend.py), and "New Run from the
Saved Reply". Every command is run_api.sh's own; nothing here sends to the AI service except the spend job spend.py made.

    estimate     ESTIMATE=1 ASK_LANG=1 bash run_api.sh <book> <short name> <run name>   intake, audit, decide.py --dry-run; when pages
                 need OCR it stops first for "Language of the Scanned Pages" (D4), then ESTIMATE=1 [OCR_LANG=…] again
    spend        AUTO=1 MAX_USD=… MODEL=… REVIEW=1 [OCR_LANG] bash run_api.sh …           paid (spend.authorize)
    rerun        REVIEW=1 [OCR_LANG] bash run_api.sh …   free: only when a complete reply is saved (03 §2); a rerun that would
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

def folder_shas(d, s=None):
    """The sha256s of the books whose runs are in runs/<name>/ (each label's intake or record, or its own PDF: R17), and
    whether every label could be read."""
    out, all_known = set(), True
    try: labels = [e.path for e in os.scandir(d) if e.is_dir() and not e.name.startswith('.')]
    except OSError: return out, True
    for L in labels:
        sha = ((_load(os.path.join(L, '_intake', 'intake.json')) or {}).get('original') or {}).get('sha256') \
              or ((_load(os.path.join(L, 'record.json')) or {}).get('document') or {}).get('sha256') \
              or ((_load(os.path.join(L, 'review_stop.json')) or {}).get('sha256'))
        if not sha and s is not None:
            from . import runs as RN
            sha = RN.own_sha(s, L)
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
            shas, known = folder_shas(d, s)
            if known and shas <= {book['key']}: return name
        n += 1

def run_taken(s, R):
    return os.path.exists(R) or any(j.get('dir') == os.path.abspath(R) for j in jobs.all_jobs(s['jobs']))

def check_untagged(s, setup, book):
    from . import checks
    if book.get('tagged') is False and not checks.untagged_ready(setup or []):
        raise ValueError('Text recognition (OCR) isn\'t set up on this computer, and this book needs it. Whoever looks after the app can install it.')

# ------------------------------------------------------------------ the PDF a new run takes (R17, Patrick 2026-11-07)
def book_of_run(s, run):
    """"New Run of This PDF": the PDF of an existing run (its own copy, or for a run made before R17 the original found
    by sha256 in samples/ or uploads/), as a book entry {path, key, file, name, locked}, or None."""
    from . import home as HM, runs as RN, names as NM
    R = dict(HM.run_folders(s['runs'])).get(run)
    if not R: return None
    p = RN.own_pdf(R)
    if p: sha, file = RN.own_sha(s, R), os.path.basename(p)
    else:
        rec = _load(os.path.join(R, 'record.json')) or {}
        o = (_load(os.path.join(R, '_intake', 'intake.json')) or {}).get('original') or {}
        sha = (rec.get('document') or {}).get('sha256') or o.get('sha256'); file = (rec.get('document') or {}).get('file') or o.get('file')
        p = RN.find_original(s, sha, file) if sha else None
        if not p: return None
    m = BK.read_meta(p)
    return {'path': p, 'key': sha, 'file': BK.shown_file(file or os.path.basename(p)), 'name': NM.book_name(s, sha, file or os.path.basename(p)),
            'locked': bool(m.get('locked')), 'from_run': run}

def take_pdf(s, book, R):
    """The new run's own PDF: the upload moved into <R>/source/ (rename; it leaves the upload list), or a copy when it
    comes from another run, or when a run made before R17 still reads that very upload (it then stays listed).
    Returns (path, 'moved' | 'copied'); raises ValueError in plain words, moving nothing."""
    from . import trash as TR
    try:
        if book.get('from_run'): return BK.copy_into(s, book['path'], book['key'], R), 'copied'
        with BK._uploads_lock(s['uploads']):
            if not os.path.isfile(book['path']) or BK.sha_file(book['path']) != book['key']:
                raise ValueError('This PDF\'s file has changed or is gone. Go back to the home page to see the list again.')
            if TR.upload_still_needed(s, book['path'], book['key']): return BK.copy_into(s, book['path'], book['key'], R), 'copied'
            return BK.move_into(s, book, R), 'moved'
    except BK.Refused as e: raise ValueError(e.words)

def give_back(s, p, mode, orig):
    """Undo take_pdf when the job can't be made: a moved PDF goes back to the upload list through take_back (under the
    uploads lock, a numbered name when its own is taken: never over a PDF uploaded meanwhile, 18-N1); a copy is removed."""
    try:
        if mode == 'moved': BK.take_back(s, p)
        else: os.remove(p)
        os.rmdir(os.path.dirname(p))
    except OSError: pass

# ------------------------------------------------------------------ the estimate (free)
def start_estimate(s, setup, key, plain, from_run=None):
    """New Run: the free estimate job. `plain`: the Run Name in the person's own words (optional); the folder label is
    derived from it (webapp/names.py label_for) and the plain name is kept by the app only. The run takes its PDF into
    its own folder first (take_pdf, R17). Returns the job; raises ValueError with the reason (plain words)."""
    from . import names as NM
    book = book_of_run(s, from_run) if from_run else BK.by_key(s, key)
    if not book: raise ValueError('This PDF\'s file has changed or is gone. Go back to the home page to see the list again.')
    if book['locked']: raise ValueError('This PDF is locked with a password. Add an unlocked copy and start a new run.')
    plain = NM.clean_name(plain)
    if not plain: raise ValueError('Enter a name for the run.')                      # P10: required, no date fallback
    m = BK.read_meta(book['path']); book['tagged'] = m.get('tagged')
    check_untagged(s, setup, book)
    name = short_name(s, book)
    for _ in range(20):                                  # two requests can fold to the same free label at once (07 L1):
        run_name = NM.label_for(plain, 'run', lambda lab: run_taken(s, os.path.join(s['runs'], name, lab)))
        R = os.path.join(s['runs'], name, run_name)
        try: os.makedirs(R); break                       #   the second derives it again ("_2")
        except FileExistsError: continue
    else: raise ValueError('A run with this name is being started right now. Try again in a moment.')
    try: path, mode = take_pdf(s, book, R)
    except ValueError:
        try: os.rmdir(os.path.join(R, 'source'))
        except OSError: pass
        try: os.rmdir(R)
        except OSError: pass
        raise
    if plain: NM.set_run_name(s, f'{name}/{run_name}', plain)
    env = {'ESTIMATE': '1', 'ASK_LANG': '1'}             # D4: the OCR language is asked only when pages need OCR (webapp/lang.py)
    argv = ['bash', 'run_api.sh', path, name, run_name]
    try:
        return jobs.create(s['jobs'], 'estimate', f'{name}/{run_name}', argv, config.child_env(s, env), env_set=env, R=R, supersede_waiting=True,
                           what='Get the estimate', book_sha=book['key'], book_file=book['file'], pdf=mode)
    except Exception:
        give_back(s, path, mode, book['path'])
        try: os.rmdir(R)
        except OSError: pass
        raise

def answer_language(s, run, R, lang):
    """"Language of the Scanned Pages" answered (D4): the estimate again, with that OCR language (English: unset)."""
    from . import lang as LG
    name = LG.check(s, R, lang)
    ej = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run and j['kind'] == 'estimate']
    if not ej: raise ValueError('This run wasn\'t started from the home page, so its settings aren\'t known here. Start a new run from the home page.')
    e = ej[-1]
    env = LG.env_for(lang)
    keep = {k: e.get(k) for k in ('book_sha', 'book_file')}
    return jobs.create(s['jobs'], 'estimate', run, e['argv'], config.child_env(s, env), env_set=env, R=R, supersede_waiting=True,
                       what=f'Get the estimate ({name})', ocr_name=name, **keep)

def again_estimate(s, run, R):
    """"Get a New Estimate": the same settings as the run's last estimate job (never a form again)."""
    ej = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run and j['kind'] == 'estimate']
    if not ej: raise ValueError('This run wasn\'t started from the home page, so its settings aren\'t known here. Start a new run from the home page.')
    if os.path.isfile(os.path.join(R, 'record.json')): raise ValueError('This run has finished.')
    if os.path.isfile(os.path.join(R, 'workorder.ai.json')): raise ValueError('The AI\'s decisions are waiting for a review: "Open the Review Page".')
    e = ej[-1]
    env = {k: v for k, v in (e.get('env_set') or {}).items() if k in ('ESTIMATE', 'OCR_LANG', 'ASK_LANG')}
    keep = {k: e.get(k) for k in ('book_sha', 'book_name', 'book_file', 'run_name', 'ocr_name')}
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
    env = {k: v for k, v in (e.get('env_set') or {}).items() if k in ('OCR_LANG',)}
    env['REVIEW'] = '1'                                  # every app run stops for review (D2), whatever an older job file says
    keep = {k: e.get(k) for k in ('book_sha', 'book_name', 'book_file', 'run_name', 'ocr_name')}
    return jobs.create(s['jobs'], 'rerun', run, e['argv'], config.child_env(s, env), env_set=env, R=R, what='Try again (the saved reply is reused)', **keep)

# ------------------------------------------------------------------ Spend
def start_spend(s, run, R, body):
    try: a = SP.authorize(s, str(body.get('kind') or 'workorder'), run, R, str(body.get('fingerprint') or ''))
    except SP.Refused as e: raise ValueError(str(e))
    return jobs.create(s['jobs'], 'spend', run, a['argv'], config.child_env(s, a['env_set']), env_set=a['env_set'], R=R, paid=True,
                       what='Start remediation: the AI call' + (' (test: a saved reply)' if a['extra']['test'] else ''), **a['extra'])

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
    src = RN.own_pdf(R) if RN.own_sha(s, R) == doc.get('sha256') else RN.find_original(s, doc.get('sha256'), doc.get('file'))
    if not src: raise ValueError('The book\'s original PDF wasn\'t found in the folder of original PDFs or of added books.')
    parent = os.path.dirname(R) if not run.startswith('batches/') else os.path.join(s['runs'], short_name(s, {'path': src, 'key': doc.get('sha256')}))   # 05 L2
    name = os.path.basename(parent)
    D_ = os.path.join(parent, label)
    if run_taken(s, D_) or os.path.exists(D_.rstrip(os.sep) + '.reply.txt'): raise ValueError(f'A run named "{label}" already exists for this book. Choose another Run Name.')
    os.makedirs(D_)
    try: src = BK.copy_into(s, src, doc.get('sha256'), D_)   # R17: the new run carries its own copy (replay_to allows source/)
    except BK.Refused as e:
        import shutil; shutil.rmtree(D_, ignore_errors=True); raise ValueError(e.words)
    reply = D_.rstrip(os.sep) + '.reply.txt'
    env = {'INTAKE_REUSE': '1', 'REPLY': reply, 'REVIEW': '1', 'RUN_DIR': D_}
    nxt = {'kind': 'replay', 'argv': ['bash', 'run_api.sh', src, name, label], 'env': config.child_env(s, env), 'env_set': env,
           'extra': {'what': 'Run the book from the saved reply', 'run_name': label, 'book_sha': doc.get('sha256'), 'book_file': doc.get('file'),
                     'book_name': BK.name_of_sha(s, doc.get('sha256'), doc.get('file'))}}
    return jobs.create(s['jobs'], 'replay-copy', f'{name}/{label}', [sys.executable, 'review_workorder.py', R, '--replay-to', D_],
                       config.child_env(s), R=D_, then=nxt, what='Copy the saved reply and the intake result', run_name=label,
                       book_sha=doc.get('sha256'), book_file=doc.get('file'), book_name=BK.name_of_sha(s, doc.get('sha256'), doc.get('file')))

# ------------------------------------------------------------------ the New Run page
def form_part(s, key, run=None):
    """New Run's pop-up (T4, Patrick 2026-11-07): its heading, the PDF and the form, for webapp/shared.js to put in a dialog
    on the page it was opened from; run: "New Run of This PDF" (R17), the new run gets a copy of that run's PDF.
    "Get the Estimate" starts only the free estimate (the paid step stays "Start Remediation" on the run page)."""
    import html
    E = html.escape
    book = book_of_run(s, run) if run else BK.by_key(s, key)
    head = '<h2 id="dlg-h">New Run</h2>'
    if not book:
        return head + ('<p>This PDF\'s file has changed or is gone. Reload the page.</p>'
                       '<div class="pp-row"><button type="button" data-cancel>Close</button></div>')
    what = ''                                            # U1 (Patrick, 2026-11-07): "New Run of This PDF" says what it does
    if run and run.startswith('batches/'): what = '<p class="mc-help nr-what">This makes a separate single run with its own copy of this PDF. The batch and its run are not changed.</p>'
    elif run: what = '<p class="mc-help nr-what">This makes a separate run with its own copy of this PDF. The run it comes from is not changed.</p>'
    return head + (f'<p class="mc-book"><span class="hm-book">{E(book["name"])}</span><span class="hm-file">Source PDF: {E(book["file"])}</span></p>{what}'
        '<form class="hm-form" data-api="/api/new/estimate" novalidate>'
        + (f'<input type="hidden" name="run" value="{E(run)}">' if run else f'<input type="hidden" name="book" value="{E(book["key"])}">') +
        '<div class="mc-field"><label for="nr-name">Run Name</label>'
        '<input type="text" id="nr-name" name="run_name" maxlength="120" required data-field="name" aria-describedby="nr-name-e">'
        '<p class="pp-warn-t pp-field-e" id="nr-name-e" hidden></p></div>'
        '<p class="mc-help">"Get the Estimate" prepares the PDF and works out what the AI call could cost. It is free: nothing is sent to the AI '
        'until you select "Start Remediation" on the next page.</p>'
        '<div class="pp-msg dlg-msg" tabindex="-1" hidden></div>'
        '<div class="pp-row"><button type="submit" class="pp-primary">Get the Estimate</button><button type="button" data-cancel>Cancel</button></div>'
        '</form>')
