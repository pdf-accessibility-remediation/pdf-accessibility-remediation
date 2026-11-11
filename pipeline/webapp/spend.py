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
Then the job: AUTO=1, MAX_USD, BOOK_MAX_USD (BATCH_MAX_USD for a batch) bound to the estimate shown, PAGE_READS=1 with
PAGE_READS_MAX_USD when the estimate included page readings (#49), and the person's real limits for
a figure request's doubled retry only (FIGURE_RETRY_MAX_USD, FIGURE_RETRY_BOOK_MAX_USD; docs/options.md),
the settings copied from the estimate's own job (never from a form again), paid, with the estimate's fingerprint.
Test mode (test_reply_dir / test_batch_from from --config): REPLY= (or FROM=) instead of the call; prices offline are
allowed, a missing saved reply is refused, never sent instead.
"""
import os, re, json, time, datetime
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
    est = costs.estimate(R, 'workorder', limits, credit_read=credit_read(s))   # U8: a fresh "Check Credit Again" read counts
    if est is None: raise Refused('There is no estimate for this run yet: select "Get a New Estimate".')
    if fingerprint != est['fingerprint']: raise Refused(CHANGED)
    model, prompt = current_model_and_prompt()
    if not est['claude'] or model != est['model'] or not prompt or prompt != est['prompt_sha256']: raise Refused(OUT_OF_DATE)   # fails closed (05 M5)
    b = est['blocked']
    if b and not (test and b['code'] in ('offline', 'no_credit')): raise Refused(b['words'])
    return est

# ------------------------------------------------------------------ "Check Credit Again" (U8, Patrick 2026-11-07)
CREDIT_FRESH = 600                                           # a credit read counts for 10 minutes
CREDIT_WHY = {
    None: 'The credit couldn\'t be checked when the estimate was made. Select "Check Credit Again".',
    'no_key': 'The app has no OpenRouter key, so the credit can\'t be checked. Whoever looks after the app can add it, then select "Check Credit Again".',
    'refused': 'OpenRouter refused the app\'s key, so the credit can\'t be checked (the key may have been revoked or replaced). '
               'Whoever looks after the app can check the key, then select "Check Credit Again".',
    'unreachable': 'OpenRouter couldn\'t be reached. Check this computer\'s connection, then select "Check Credit Again".',
    'error': 'OpenRouter didn\'t give the credit. Select "Check Credit Again" in a moment.'}

def _credit_p(s): return os.path.join(s['jobs'], 'credit.json')

def credit_now(s):
    """The last credit read by "Check Credit Again": {usd, why, at}, or {} (none, or older than CREDIT_FRESH)."""
    try: d = json.load(open(_credit_p(s), encoding='utf-8'))
    except (OSError, ValueError): return {}
    try: age = time.time() - float(d.get('t') or 0)
    except (TypeError, ValueError): return {}
    return d if 0 <= age <= CREDIT_FRESH else {}

def credit_read(s):
    """A fresh read's dollars for the checks, or None (the estimates' own credit is used as before)."""
    v = credit_now(s).get('usd')
    return float(v) if isinstance(v, (int, float)) else None

def check_credit(s):
    """"Check Credit Again": read the credit now (no book content is sent, nothing is paid), keep it for CREDIT_FRESH."""
    from . import credit as CR
    usd, why = CR.check()                                    # stored as it is, test mode too (21-L1): a failed read is no
                                                             #   credit (test mode lets that through), never $0.00
    d = {'usd': round(usd, 4) if usd is not None else None, 'why': why, 'at': datetime.datetime.now().isoformat(timespec='seconds'), 't': time.time()}
    os.makedirs(s['jobs'], exist_ok=True)
    tmp = _credit_p(s) + '.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8')); os.replace(tmp, _credit_p(s))
    return d

def credit_words(s):
    """Why the credit isn't known, in plain words, for the run and batch pages."""
    d = credit_now(s)
    return CREDIT_WHY.get(d.get('why'), CREDIT_WHY['error']) if d else CREDIT_WHY[None]

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
        from . import runs as RN
        if RN.moved_words(s, ej.get('book_sha')) and not (src and os.path.isfile(src)):   # D8: a person moved it to the Trash
            raise Refused('This PDF was moved to the Trash. To continue, upload the same PDF again with "Choose PDFs" on the home page, then try again.')
        raise Refused('This PDF\'s file has changed or is gone since the estimate. Go back to the home page and start a new run.')
    keep = {k: v for k, v in (ej.get('env_set') or {}).items() if k in ('OCR_LANG',)}
    keep['REVIEW'] = '1'                                     # every app run stops for review (D2, Patrick 2026-11-06), whatever an older job file says
    if test:
        reply = os.path.join(s['test_reply_dir'], f'{ej["argv"][3]}.txt')
        if not os.path.isfile(reply): raise Refused('There is no saved test reply for this book.')
        env = {**keep, 'REPLY': reply, 'INTAKE_REUSE': '1'}
    else:
        env = {**keep, 'AUTO': '1', 'MAX_USD': f'{est["bounds"]["MAX_USD"]:.2f}', 'MODEL': est['model']}
        if est['bounds'].get('BOOK_MAX_USD') is not None: env['BOOK_MAX_USD'] = f'{est["bounds"]["BOOK_MAX_USD"]:.2f}'
        env.update(costs.retry_env(L))
        if est['bounds'].get('PAGE_READS_MAX_USD') is not None:   # #49: the pages read whole, as the estimate showed them
            env.update(PAGE_READS='1', PAGE_READS_MAX_USD=f'{est["bounds"]["PAGE_READS_MAX_USD"]:.2f}')
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'),
             'shown': {'ceiling_usd': est['ceiling_usd'], 'per_call_ceiling_usd': est['per_call_ceiling_usd'], 'expected_usd': (est['expected'] or {}).get('usd'),
                       'bounds': est['bounds'], 'model': est['model']},
             'test': test,
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
        if not total['fits']['batch']: raise Refused(costs.batch_over_words(total))
        if total['fits']['credit'] is False: raise Refused(f'This batch could cost up to ${costs.up(total["ceiling_usd"]):.2f}, more than the ${total["credit_usd"]:.2f} of credit left.')
        if total['credit_usd'] is None: raise Refused('The credit couldn\'t be checked, so the cost can\'t be compared with it.')
        env = {'AUTO': '1', 'JOBS': jobs_n, 'BATCH_MAX_USD': f'{total["bounds"]["BATCH_MAX_USD"]:.2f}', 'MODEL': model}
        if total['bounds'].get('MAX_USD'): env['MAX_USD'] = f'{total["bounds"]["MAX_USD"]:.2f}'
        if total['bounds'].get('BOOK_MAX_USD'): env['BOOK_MAX_USD'] = f'{total["bounds"]["BOOK_MAX_USD"]:.2f}'   # the largest book's total (#63): decide.py holds each book to it
        env.update(costs.retry_env(costs.limits_of(s)))
        if total['bounds'].get('PAGE_READS_MAX_USD'):            # #49: some books have pages read whole; each is held to the largest's cap
            env.update(PAGE_READS='1', PAGE_READS_MAX_USD=f'{total["bounds"]["PAGE_READS_MAX_USD"]:.2f}')
    env['REVIEW'] = '1'                                    # every book stops for review (D2a, Patrick 2026-11-06)
    x = total.get('expected') or {}                         # a figure only when every PDF to send has one: a part of them would mislead after the run
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'),
             'shown': {'ceiling_usd': total['ceiling_usd'], 'bounds': total['bounds'], 'expected_usd': x.get('usd') if x.get('books') == x.get('of') else None,
                       'spent_usd': total['spent_usd'], 'retry_usd': total['retry_usd']}, 'test': bool(test_from)}
    return {'argv': ['bash', 'batch_api.sh', label, books_list], 'env_set': env, 'extra': extra}
