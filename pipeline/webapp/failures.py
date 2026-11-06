"""webapp/failures.py: why a run stopped, in plain words, and what the person can do (#45, requirement 4; 01 §3.4 as
amended by 03 §9). A table keyed by step (03 §11): each row has its matcher, the source text it matches pinned by a test
against the tool that prints it (tests/test_failures.py), a headline and a meaning in plain words, what the person can
do, and the buttons. A new paid step adds rows, not branches.

    explain(s, R, job) → {code, step, headline, meaning, todo, next: [estimate | retry | dismiss], details} or None

The headline, meaning and todo never quote a tool's words (03 §9): those, and any command, are only in "Details", for
whoever looks after the app, with the step, the exit code, the tool's own error line, the record that holds it, and where
the full log is. No other log lines. Steps come from run_api.sh's own "▶ N/5 …" lines; intake's stops from
_intake/intake.json (status and summary); the AI call's from run.json (error, finish_reason) and its log line.
"""
import os, re, json
from . import jobs, logs

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

# ------------------------------------------------------------------ the context a row looks at
STEP_OF = (('0/5 intake', 'intake'), ('1/5 ', 'audit'), ('2/5 cost estimate', 'estimate'), ('2/5 reuse saved reply', 'call'),
           ('2/5 the earlier', 'call'), ('3/5 ', 'call'), ('review:', 'review'), ('4/5 apply', 'apply'), ('4/5 verify', 'apply'), ('5/5 report', 'apply'))
STEP_WORDS = {'start': 'starting the run', 'intake': 'reading and tagging the PDF (intake)', 'audit': 'auditing the PDF',
              'estimate': 'estimating the cost', 'call': 'the AI call', 'review': 'preparing the review page', 'apply': 'applying, checking or writing the report',
              'batch': 'the batch', 'app': 'the app'}

def context(s, R, job):
    text = jobs.read_log(s['jobs'], job['id'], 0, 4 * 1024 * 1024)[0] if job else ''
    started = [m.group(1) for m in re.finditer(r'^▶ (.+?)\s*$', text, re.M)]
    step = 'start'
    for lab in started:
        for pre, st in STEP_OF:
            if lab.startswith(pre): step = st
    intake = _load(os.path.join(R, '_intake', 'intake.json')) or {}
    run = _load(os.path.join(R, 'run.json')) or {}
    env = (job or {}).get('env_set') or {}
    return {'job': job or {}, 'text': text, 'step': step, 'started': started, 'intake': intake, 'run': run, 'env': env, 'R': R,
            'exit': (job or {}).get('exit'), 'status': (job or {}).get('status')}

def _line(c, pat):
    """The last log line holding pat (a tool's own error line, for "Details")."""
    hits = [l.strip() for l in c['text'].splitlines() if pat in l]
    return hits[-1][:400] if hits else None

def _tb(c):
    """A crash's last line (the exception) and the pipeline file it came from."""
    if 'Traceback (most recent call last)' not in c['text']: return None
    tail = c['text'].split('Traceback (most recent call last)')[-1].strip().splitlines()
    files = re.findall(r'File "([^"]+)", line (\d+)', '\n'.join(tail))
    where = next((f'{os.path.basename(f)}:{n}' for f, n in reversed(files) if '/pipeline/' in f or not f.startswith('/')), None)
    return (tail[-1].strip()[:300] if tail else 'an error') + (f' ({where})' if where else '')

def has(pat): return lambda c: pat in c['text']
def summ(*pats): return lambda c: c['intake'].get('status') in ('stopped', 'failed') and any(str(c['intake'].get('summary') or '').startswith(p) or p in str(c['intake'].get('summary') or '') for p in pats)
def flagged(name): return lambda c: c['intake'].get('status') == 'stopped' and any(name in str(f.get('what') if isinstance(f, dict) else f) for f in c['intake'].get('flags') or [])
def at(step, pred): return lambda c: c['step'] == step and pred(c)

WHOEVER = 'Whoever looks after the app can check it: "Details" says what happened.'

# ------------------------------------------------------------------ the table, in the order rows are tried (first match wins)
# (code, step, matcher, (source file, pinned text) or None, headline, meaning, todo, next buttons, details' command or None)
ROWS = [
    # --- the run was interrupted (job status): what is left is read from disk
    ('I2', 'interrupted', lambda c: c['status'] == 'interrupted' and c['step'] == 'call' and not os.path.exists(os.path.join(c['R'], 'response.json')), None,
     'The run stopped during the AI call.', 'The computer restarted or the run was stopped while the AI call was being made. It isn\'t known whether the call was charged.',
     'Whoever looks after the app can check the AI service\'s activity page. To go on, get a new estimate, then select "Spend" again.', ['estimate'], None),
    ('I3', 'interrupted', lambda c: c['status'] == 'interrupted' and os.path.exists(os.path.join(c['R'], 'response.json')), None,
     'The run stopped before it finished.', 'The computer restarted or the run was stopped. The AI\'s reply is saved, so going on costs nothing.',
     'Select "Try Again": the saved reply is used again.', ['retry'], None),
    ('I1', 'interrupted', lambda c: c['status'] == 'interrupted', None,
     'The run stopped before it finished.', 'The computer restarted or the run was stopped before the AI call. Nothing was sent.',
     'Select "Try Again": the steps already done are reused.', ['retry'], None),
    # --- run_api.sh before the pipeline (log only)
    ('B7', 'start', has('MAX_USD must be a number of dollars'), ('run_api.sh', 'MAX_USD must be a number of dollars'),
     'The app sent a cost limit the run couldn\'t read.', 'Nothing was sent to the AI service.', WHOEVER, [], None),
    ('B1', 'start', has('no such PDF: '), ('run_api.sh', 'no such PDF: '),
     'The book\'s file couldn\'t be found.', 'The PDF this run was started from is no longer where it was. Nothing was sent.',
     'Add the book again from the home page, then start a new run.', [], None),
    ('B2', 'start', lambda c: 'missing Python libraries' in c['text'] or 'veraPDF is needed for the WCAG checks' in c['text'],
     ('run_api.sh', 'veraPDF is needed for the WCAG checks'), 'The app\'s tools are not set up.', 'A tool every run needs is missing. Nothing was sent.', WHOEVER, [], None),
    ('B3', 'start', has('already holds a finished run'), ('run_api.sh', 'already holds a finished run'),
     'This run has already finished.', 'Its result is on its run page.', 'Open the run from the home page.', [], None),
    ('B4', 'start', has('is waiting for a review. Finish it first'), ('run_api.sh', 'is waiting for a review. Finish it first'),
     'The AI\'s decisions are waiting for a review.', 'Nothing has been applied yet.', 'Reload this page: it offers "Open the Review Page."', [], None),
    ('B5', 'intake', has('is not the original this run\'s intake was made from'), ('run_api.sh', 'is not the original this run\'s intake was made from'),
     'This isn\'t the same file the run started with.', 'The book\'s file changed since the run started, so the AI\'s decisions may not fit it.',
     'Start a new run of the book from the home page.', [], None),
    # --- intake (_intake/intake.json: status and summary)
    ('C1', 'intake', summ('the PDF needs a password to open'), ('intake.py', 'the PDF needs a password to open'),
     'This PDF is locked with a password.', 'The app can\'t read a locked PDF. Nothing was sent to the AI service.',
     'Add an unlocked copy from the home page and start a new run with it.', [], None),
    ('C2', 'intake', lambda c: flagged('Not supported yet')(c) or 'audit: stopped: ' in c['text'], ('lib/support.py', "print(f'{step}: stopped: {why}'"),
     'This PDF uses a format the app can\'t fix yet.', 'It is a PDF 2.0 file, or its tags use a newer scheme. Nothing was sent to the AI service.',
     'A person remediates this book by hand.', [], None),
    ('C3', 'intake', summ('no page has text or a page image'), ('intake.py', 'no page has text or a page image'),
     'No page has text or a page image.', 'There is nothing on the pages to tag. Nothing was sent to the AI service.',
     'Check that this is the right file.', [], None),
    ('C4', 'intake', summ('text layer unusable'), ('intake.py', 'text layer unusable'),
     'The PDF\'s text doesn\'t match what\'s printed on its pages.', 'Its hidden text layer is too far from the printed words to use. Nothing was sent to the AI service.',
     'A person compares a few pages with the original and decides. Whoever looks after the app can also run the book with every page recognized again (the command is in "Details").',
     [], 'FORCE_OCR=1 OCR_LANG=<language> bash run_api.sh <the book> <name> <run name>'),
    ('C5', 'intake', summ('CJK text on pages to be OCR'), ('intake.py', "CJK text on pages to be OCR\\'d"),
     'Pages that need OCR have Chinese, Japanese or Korean text.', 'The OCR language is never guessed, so the run stopped before reading those pages. Nothing was sent.',
     'Start a new run of the book from the home page and choose its language under "OCR Language."', [], None),
    ('C6', 'intake', summ('the PDF could not be opened'), ('intake.py', 'the PDF could not be opened'),
     'This PDF couldn\'t be opened.', 'The file may be damaged. Nothing was sent to the AI service.', 'Add another copy of the book from the home page.', [], None),
    ('C7', 'intake', lambda c: summ('is not installed', 'is needed for auto-tagging', 'OCRmyPDF 17 or later is needed')(c), ('intake.py', 'OCRmyPDF 17 or later is needed'),
     'A tool the app needs for OCR is missing.', 'Text recognition or tagging can\'t run on this computer. Nothing was sent.', WHOEVER, [], None),
    ('C8', 'intake', lambda c: summ('changed pages', 'changed page', 'changed a page', 'lost ')(c), ('intake.py', 'changed pages it should not have'),
     'A safety check stopped the run.', 'A step would have changed how the pages look or read, so nothing was kept and nothing was sent.', WHOEVER, [], None),
    ('C9', 'intake', summ('OCRmyPDF failed', 'auto-tagging failed', 'auto-tagging produced no tag tree'), ('intake.py', 'auto-tagging failed: '),
     'Text recognition or tagging failed.', 'A tool stopped while reading or tagging the PDF. Nothing was sent to the AI service.',
     'Select "Try Again." If it stops again, whoever looks after the app can check it.', ['retry'], None),
    ('C10', 'intake', lambda c: c['step'] == 'intake' and c['intake'].get('status') not in ('stopped', 'failed', 'done', 'skipped'), None,
     'The run stopped with an error while reading the PDF.', 'Nothing was sent to the AI service.', 'Select "Try Again." If it stops again, whoever looks after the app can check it.', ['retry'], None),
    # --- the audit
    ('D2', 'audit', has('untagged PDF: this pipeline repairs an existing tag tree'), ('audit.py', 'untagged PDF: this pipeline repairs an existing tag tree'),
     'This PDF has no tags to repair.', 'The run was made without its intake step. Nothing was sent.', WHOEVER, [], None),
    ('D3', 'audit', lambda c: c['step'] == 'audit', None,
     'The run stopped with an error while checking the PDF.', 'Nothing was sent to the AI service.', 'Select "Try Again." If it stops again, whoever looks after the app can check it.', ['retry'], None),
    # --- the estimate (decide.py --dry-run)
    ('E1', 'estimate', lambda c: c['step'] == 'estimate' and ('prompt not found' in c['text'] or 'even when reduced' in c['text']), ('decide.py', 'even when reduced'),
     'The request to the AI couldn\'t be built.', 'Nothing was sent.', WHOEVER, [], None),
    ('E2', 'estimate', lambda c: c['step'] in ('estimate', 'call') and re.search(r'refusing: (model "|\S+ cannot take images|\S+ writes at most|the request needs about)', c['text']),
     ('decide.py', 'refusing: the request needs about'), 'The AI model can\'t take this book.', 'The book is too large for the model, or the model is not available. Nothing was sent.', WHOEVER, [], None),
    ('B6', 'call', lambda c: c['job'].get('kind') in ('rerun', 'replay') and not ({'AUTO', 'ESTIMATE', 'REPLY'} & set(c['env'])) and c['started'] and c['started'][-1].startswith('2/5 cost estimate'),
     ('run_api.sh', 'stage "2/5 cost estimate (no model)"'), 'A new AI call is needed.', 'The saved reply could not be used, so the run stopped before sending anything.',
     'Get a new estimate first, then select "Spend."', ['estimate'], None),
    ('E9', 'estimate', lambda c: c['step'] == 'estimate', None,
     'The cost estimate stopped with an error.', 'Nothing was sent to the AI service.', 'Select "Get a New Estimate." If it stops again, whoever looks after the app can check it.', ['estimate'], None),
    # --- the paid call (decide.py; run.json error, finish_reason)
    ('F0', 'call', has('could not reach OpenRouter to look up the model'), ('decide.py', 'could not reach OpenRouter to look up the model'),
     'The connection to the AI service failed before anything was sent.', 'Nothing was charged.', 'When this computer is online again, select "Get a New Estimate," then "Spend."', ['estimate'], None),
    ('F1', 'call', lambda c: re.search(r'refusing: worst-case \$[\d.]+ is over the \$[\d.]+ cap', c['text']), ('decide.py', "refusing: worst-case ${est_in + worst_out:.2f} is over the ${args.max_usd:.2f} cap"),
     'The cost went over the limit after the estimate, so nothing was sent.', 'Prices or the request changed since the estimate, and the run kept to the amount you agreed to.',
     'Select "Get a New Estimate" to see the new cost.', ['estimate'], None),
    ('F2', 'call', lambda c: re.search(r'refusing: \$[\d.]+ credit available', c['text']), ('decide.py', 'credit available, worst case is'),
     'There isn\'t enough credit, so nothing was sent.', 'The AI service\'s credit is lower than the most this run could cost.',
     'Whoever looks after the app adds credit; then select "Get a New Estimate."', ['estimate'], None),
    ('F3', 'call', has('no OPENROUTER_API_KEY'), ('decide.py', 'no OPENROUTER_API_KEY: put it in'),
     'The app has no key for the AI service.', 'Nothing was sent.', WHOEVER, [], None),
    ('F4', 'call', lambda c: 'accepts our "don\'t keep or train on the data" setting' in c['text'] or 'rejected the temperature setting' in c['text'],
     ('decide.py', 'rejected the temperature setting'), 'The AI service refused the request.', 'Nothing was charged.', WHOEVER, [], None),
    ('F5a', 'call', lambda c: str((c['run'].get('error') or {}).get('code')) == '429', ('decide.py', "if str(code) == '429':"),
     'The AI service is busy.', 'It asked the app to wait. Whether anything was charged is in "Details."',
     'Wait a few minutes, then select "Get a New Estimate" and "Spend" again.', ['estimate'], None),
    ('F5', 'call', lambda c: bool(c['run'].get('error')), ('decide.py', "run['error'] = {'code': code, 'message': (message or '')[:500]}"),
     'The AI service refused or failed the request.', 'Whether anything was charged is in "Details."', 'Whoever looks after the app can check it ("Details"); then select "Get a New Estimate."', ['estimate'], None),
    ('F7', 'call', lambda c: c['step'] == 'call' and re.search(r'URLError|TimeoutError|timed out|ConnectionResetError|RemoteDisconnected|IncompleteRead', c['text']), None,
     'The connection to the AI service was lost during the call.', 'It isn\'t known whether the call was charged.',
     'Whoever looks after the app can check the AI service\'s activity page. Then select "Get a New Estimate" and "Spend."', ['estimate'], None),
    ('F8', 'call', lambda c: c['run'].get('finish_reason') == 'length', ('decide.py', 'the reply was cut off at'),
     'The AI\'s answer was cut off.', 'It was too long to finish. Its cost is kept on record.',
     'Select "Get a New Estimate" and "Spend" to make a new call; whoever looks after the app may raise the answer\'s length limit first.', ['estimate'], None),
    ('F9', 'call', lambda c: 'could not parse a JSON work order' in c['text'] or 'the last one, the model\'s final answer, could not be read' in c['text'],
     ('decide.py', 'could not parse a JSON work order from reply.txt'), 'The AI\'s answer couldn\'t be read.', 'Its cost is kept on record.',
     'Select "Try Again": the saved answer is read again first, free; a new call needs a new estimate.', ['retry'], None),
    ('F99', 'call', lambda c: c['step'] == 'call', None,
     'The AI call stopped with an error.', 'Whether anything was charged is in "Details" if the service reported it.', WHOEVER + ' Then select "Try Again."', ['retry'], None),
    # --- the review stop
    ('G1', 'review', lambda c: c['step'] == 'review', None,
     'The review page couldn\'t be prepared.', 'The AI\'s reply is saved, so going on costs nothing.', 'Select "Try Again."', ['retry'], None),
    # --- apply, verify, report
    ('H1', 'apply', has('work order was written for a different file'), ('apply.py', 'work order was written for a different file'),
     'The AI\'s decisions were made for a different file.', 'Nothing was applied.', 'Start a new run of the book from the home page.', [], None),
    ('H2', 'apply', lambda c: c['step'] == 'apply', None,
     'The run stopped while applying the decisions, checking the result or writing the report.', 'The AI\'s reply is saved, so going on costs nothing.',
     'Select "Try Again." If it stops again, whoever looks after the app can check it.', ['retry'], None),
    # --- the app
    ('J1', 'app', lambda c: c['exit'] == 127, ('webapp/jobrun.py', "log.write(f'could not start: {e}\\n'.encode())"),
     'The app couldn\'t start this step.', 'Nothing was sent.', 'Select "Try Again." If it happens again, whoever looks after the app can check it.', ['retry'], None),
]

def _details(s, c, row):
    d = {'step': STEP_WORDS.get(c['step'], c['step']), 'exit': c['exit'], 'log': jobs.log_path(s['jobs'], c['job']['id']) if c['job'] else None}
    from . import runs as RN
    if d['log']: d['log'] = RN.shown_path(d['log'])
    line = None
    if c['intake'].get('status') in ('stopped', 'failed') and c['step'] in ('intake', 'start'):
        line, d['record'] = c['intake'].get('summary'), os.path.join(os.path.basename(c['R']), '_intake', 'intake.json')
    elif c['run'].get('error'):
        er = c['run']['error']; line = f'OpenRouter error {er.get("code")}: {er.get("message")}'
        cost = (c['run'].get('usage') or {}).get('cost_usd'); line += f' (cost reported: ${cost:.4f})' if cost else ' (no cost reported)'
        d['record'] = os.path.join(os.path.basename(c['R']), 'run.json')
    if not line and row and row[3]: line = _line(c, row[3][1].split('{')[0].strip()[:40])
    if not line: line = _tb(c) or next((l.strip() for l in reversed(c['text'].splitlines()) if l.strip() and not l.startswith(('  ✓', '▶', 'job '))), None)
    d['line'] = (line or '')[:400] or None
    if row and row[8]: d['command'] = row[8]
    return d

def explain(s, R, job):
    """The failure of a run's last job (failed or interrupted), or of intake when the run stopped there, or None."""
    if not job or job.get('status') not in ('failed', 'interrupted'):
        it = _load(os.path.join(R, '_intake', 'intake.json')) or {}
        if it.get('status') not in ('stopped', 'failed') or os.path.isfile(os.path.join(R, 'run.json')): return None
    c = context(s, R, job)
    for row in ROWS:
        try: hit = row[2](c)
        except Exception: hit = False
        if hit:
            return {'code': row[0], 'step': row[1], 'headline': row[4].rstrip('.'), 'meaning': row[5], 'todo': row[6], 'next': list(row[7]),
                    'details': _details(s, c, row)}
    return {'code': 'X', 'step': c['step'], 'headline': 'The run stopped with an error', 'meaning': None,
            'todo': 'Select "Try Again." If it stops again, whoever looks after the app can check it.', 'next': ['retry'], 'details': _details(s, c, None)}
