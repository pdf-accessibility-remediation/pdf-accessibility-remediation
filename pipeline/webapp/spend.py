"""webapp/spend.py: the one gate every "Spend" goes through (#45, 03 §11). Nothing else in the app makes a job that may
send to the AI service, and jobs.create() refuses one that did not come from here (03 §2).

    authorize(s, kind, run, R, fingerprint) → {argv, env_set, extra}, or raises Refused(words)
    current_model_and_prompt()     decide.py's DEFAULT_MODEL and its prompt's sha256[:16], read from its source (never
                                   imported: importing it would read .env and parse arguments)

What a Spend checks, in this order, at the click:
  1. the estimate shown is the estimate on disk now: the fingerprint lib/costs.py made (the estimate without the credit,
     request.json, the digest, the model, the prompt);
  2. decide.py's DEFAULT_MODEL and prompt are still the ones the estimate used, and the model is a Claude model (decide.py
     checks its caps for Claude models only: 02 B6). The job then also gets MODEL=<that model>, so a change while it waits
     in the queue cannot lift the cap;
  3. the estimate fits the limits and the credit (lib/costs.py `blocked`);
  4. the book's file is still the one the estimate was made from (its sha256).
Then the job: AUTO=1, MAX_USD (and BOOK_MAX_USD for #63's shape, BATCH_MAX_USD for a batch) bound to the estimate shown,
the settings copied from the estimate's own job (never from a form again), paid, with the fingerprint and the tick.
Test mode (test_reply_dir / test_batch_from from --config): REPLY= (or FROM=) instead of the call; prices offline are
allowed, a missing saved reply is refused, never sent instead.
"""
import os, re, datetime
from lib import costs
from . import config, jobs, books as BK

class Refused(Exception):
    """A Spend that is refused, in plain words for the page."""

CHANGED = 'The estimate changed since it was shown. Look at the new estimate.'
OUT_OF_DATE = 'The estimate is out of date. Get a new estimate.'

def _decide_source():
    return open(os.path.join(config.PIPELINE, 'decide.py'), encoding='utf-8').read()

def current_model_and_prompt():
    """(DEFAULT_MODEL, the prompt file's sha256[:16] as decide.py computes it), from decide.py's source, or (None, None)."""
    try: src = _decide_source()
    except OSError: return None, None
    m = re.search(r"^DEFAULT_MODEL = '([^']+)'", src, re.M)
    pn = re.search(r"^PROMPT_NAME = '([^']+)'", src, re.M)
    sha = None
    if pn:
        import hashlib
        for d in (os.path.join(config.PIPELINE, 'prompts'), os.path.join(config.ROOT, 'prompts')):   # as DEFAULT_PROMPT finds it
            p = os.path.join(d, pn.group(1))
            if os.path.isfile(p):
                sha = hashlib.sha256(open(p, encoding='utf-8').read().encode()).hexdigest()[:16]; break
    return (m.group(1) if m else None), sha

def last_estimate_job(s, run):
    """The run's newest estimate job that finished: its settings are the ones Spend uses."""
    ej = [j for j in jobs.all_jobs(s['jobs']) if j['run'] == run and j['kind'] == 'estimate' and j['status'] == 'done']   # a single run's (a batch's book: the batch's Spend)
    return ej[-1] if ej else None

def check_estimate(s, R, fingerprint, test, limits):
    """The estimate on disk, after checks 2–4; raises Refused."""
    est = costs.estimate(R, 'workorder', limits)
    if est is None: raise Refused('There is no estimate for this run yet: select "Get a New Estimate".')
    if fingerprint != est['fingerprint']: raise Refused(CHANGED)
    model, prompt = current_model_and_prompt()
    if not est['claude'] or model != est['model'] or not prompt or prompt != est['prompt_sha256']: raise Refused(OUT_OF_DATE)   # fails closed (05 M5)
    b = est['blocked']
    if b and not (test and b['code'] in ('offline', 'no_credit')): raise Refused(b['words'])
    return est

def authorize(s, kind, run, R, fingerprint):
    """A single run's Spend (kind 'workorder'). Returns {argv, env_set, extra} for jobs.create(kind='spend', paid=True)."""
    if kind != 'workorder': raise Refused('This kind of AI step can\'t be sent from here yet.')
    test = bool(s.get('test_reply_dir'))
    L = costs.limits_of(s)
    est = check_estimate(s, R, fingerprint, test, L)
    ej = last_estimate_job(s, run)
    if not ej: raise Refused('There is no estimate for this run yet: select "Get a New Estimate".')
    src = ej['argv'][2] if len(ej['argv']) > 2 else None
    if not src or not os.path.isfile(src) or BK.hashes(s, [src]).get(src) != ej.get('book_sha'):
        raise Refused('This book\'s file has changed or is gone since the estimate. Go back to the home page and start a new run.')
    keep = {k: v for k, v in (ej.get('env_set') or {}).items() if k in ('OCR_LANG',)}
    if ej.get('review_first'): keep['REVIEW'] = '1'
    if test:
        reply = os.path.join(s['test_reply_dir'], f'{ej["argv"][3]}.txt')
        if not os.path.isfile(reply): raise Refused('There is no saved test reply for this book.')
        env = {**keep, 'REPLY': reply, 'INTAKE_REUSE': '1'}
    else:
        env = {**keep, 'AUTO': '1', 'MAX_USD': f'{est["bounds"]["MAX_USD"]:.2f}', 'MODEL': est['model']}
        if est['bounds'].get('BOOK_MAX_USD') is not None: env['BOOK_MAX_USD'] = f'{est["bounds"]["BOOK_MAX_USD"]:.2f}'
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'),
             'shown': {'ceiling_usd': est['ceiling_usd'], 'per_call_ceiling_usd': est['per_call_ceiling_usd'], 'bounds': est['bounds'], 'model': est['model']},
             'test': test, 'review_first': bool(ej.get('review_first')),
             **{k: ej.get(k) for k in ('book_sha', 'book_name', 'book_file', 'run_name')}}
    return {'argv': list(ej['argv']), 'env_set': env, 'extra': extra}

def authorize_batch(s, label, books_list, total, fingerprint):
    """A batch's Spend: books_list is the app's book list file, total the costs.batch() shown (its fingerprint checked by
    the caller against the one shown). Returns {argv, env_set, extra}."""
    test_from = s.get('test_batch_from')
    jobs_n = str(int(s.get('batch_jobs') or 10))            # books in progress at once inside the batch (one place of max_jobs)
    if test_from:
        env = {'AUTO': '1', 'FROM': test_from, 'JOBS': jobs_n}           # FROM: every book runs from a saved reply (REPLY=)
    else:
        model, prompt = current_model_and_prompt()
        models = {b['estimate']['model'] for b in total['books'] if b.get('estimate')}
        prompts = {b['estimate']['prompt_sha256'] for b in total['books'] if b.get('estimate')}
        if not model or models - {model} or not model.startswith('anthropic/') or not prompt or prompts - {prompt}: raise Refused(OUT_OF_DATE)
        if total['blocked']: raise Refused(total['blocked'][0][1]['words'])
        if not total['fits']['batch']: raise Refused(f'This batch could cost more than the limit of ${total["limit_usd"]:.2f} per batch.')
        if total['fits']['credit'] is False: raise Refused('There isn\'t enough credit for this batch.')
        if total['credit_usd'] is None: raise Refused('The credit couldn\'t be checked, so the cost can\'t be compared with it.')
        env = {'AUTO': '1', 'JOBS': jobs_n, 'BATCH_MAX_USD': f'{total["bounds"]["BATCH_MAX_USD"]:.2f}', 'MODEL': model}
        if total['bounds'].get('MAX_USD'): env['MAX_USD'] = f'{total["bounds"]["MAX_USD"]:.2f}'
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'),
             'shown': {'ceiling_usd': total['ceiling_usd'], 'bounds': total['bounds']}, 'test': bool(test_from)}
    return {'argv': ['bash', 'batch_api.sh', label, books_list], 'env_set': env, 'extra': extra}
