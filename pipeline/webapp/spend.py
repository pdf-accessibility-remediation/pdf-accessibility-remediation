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
  4. the book's file is still the one the estimate was made from (its sha256); after a person moved it to the Trash and
     uploaded it again, under any name, the copy found by its content (uploaded_again, #93) is sent instead.
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

def current_language_prompt():
    """The language step's prompt sha256[:16] as name_languages.py computes it (issue 118), or None."""
    try: src = open(os.path.join(config.PIPELINE, 'name_languages.py'), encoding='utf-8').read()
    except OSError: return None
    pn = re.search(r"^PROMPT_NAME = '([^']+)'", src, re.M)
    if not pn: return None
    import hashlib
    for d in (os.path.join(config.PIPELINE, 'prompts'), os.path.join(config.ROOT, 'prompts')):
        p = os.path.join(d, pn.group(1))
        if os.path.isfile(p): return hashlib.sha256(open(p, encoding='utf-8').read().encode()).hexdigest()[:16]
    return None

def language_env(est):
    """The language step as the estimate showed it (issue 118): its cap and model when it was in the estimate, else off, so a
    job never sends what the person was not shown (config.child_env keeps it off otherwise)."""
    lg = est.get('language') if isinstance(est, dict) else None
    if not lg or est['bounds'].get('LANGUAGE_MAX_USD') is None:                    # config.child_env: off unless set here
        # #123: every word form decided by the reading printed beside it: the step runs with a $0 cap, so it sends nothing
        # (any form it would send is refused); never when the estimate left the language step out
        if isinstance(est, dict) and est.get('language_local') and not any((x or {}).get('kind') == 'language' for x in est.get('left_out') or []):
            return {'LANG_TAGS': 'on', 'LANGUAGE_MAX_USD': '0.00'}
        return {}
    return {'LANG_TAGS': 'on', 'LANGUAGE_MAX_USD': f'{est["bounds"]["LANGUAGE_MAX_USD"]:.2f}', 'LANGUAGE_MODEL': lg['model']}

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
    lg = est.get('language')
    if lg and (not str(lg.get('model') or '').startswith('anthropic/') or lg.get('prompt_sha256') != current_language_prompt()): raise Refused(OUT_OF_DATE)
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

MOVED = 'This PDF was moved to the Trash. To continue, upload the same PDF again with "Choose PDFs" on the home page, then try again.'

def _sha_now(p):
    """The file's sha256 read now, never from the shared cache (a copy found again is checked afresh before it is used)."""
    import hashlib
    h = hashlib.sha256()
    try:
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    except OSError: return None
    return h.hexdigest()

def uploaded_again(s, ej):
    """An estimate job's PDF that a person moved to the Trash (#45 D8) and uploaded again, under any file name (#93, review
    09 M1): the copy found by its content in samples/ or uploads/, its sha256 checked afresh, or None (the job's own file is
    still there, it was not moved by the app, or no copy is back). Its content is the estimate's, byte for byte, and the
    estimate's fingerprint covers only the run folder's files (lib/costs.py), so the estimate stays valid for it."""
    src = ej['argv'][2] if len(ej.get('argv') or []) > 2 else None
    sha = ej.get('book_sha')
    if not src or not sha or os.path.isfile(src): return None
    from . import runs as RN
    if not RN.moved_words(s, sha): return None
    p = RN.find_original(s, sha, os.path.basename(src))
    return p if p and _sha_now(p) == sha else None

def authorize(s, kind, run, R, fingerprint):
    """A single run's Spend (kind 'workorder'), or "Ask the AI Again" for a run held at its review stop (kind 'retry',
    #151). Returns {argv, env_set, extra} for jobs.create(kind='spend' or 'ai-retry', paid=True)."""
    if kind == 'retry': return authorize_retry(s, run, R, fingerprint)
    if kind != 'workorder': raise Refused('This kind of AI step can\'t be sent from here yet.')
    test = bool(s.get('test_reply_dir'))
    L = costs.limits_of(s)
    est = check_estimate(s, R, fingerprint, test, L)
    ej = last_estimate_job(s, run)
    if not ej: raise Refused('There is no estimate for this run yet: select "Get a New Estimate".')
    argv = list(ej['argv'])
    src = argv[2] if len(argv) > 2 else None
    if not src or not os.path.isfile(src) or BK.hashes(s, [src]).get(src) != ej.get('book_sha'):
        back = uploaded_again(s, ej)                         # moved to the Trash, then uploaded again: the copy is used
        if back: argv[2] = back
        else:
            from . import runs as RN
            if RN.moved_words(s, ej.get('book_sha')) and not (src and os.path.isfile(src)): raise Refused(MOVED)   # D8: no copy back yet
            raise Refused('This PDF\'s file has changed or is gone since the estimate. Go back to the home page and start a new run.')
    keep = {k: v for k, v in (ej.get('env_set') or {}).items() if k in ('OCR_LANG', 'REOCR', 'KEEP_CJK_PAGES')}   # #121, review 06: the intake it was estimated on
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
        env.update(language_env(est))                       # #118: the language step only as the estimate showed it
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'),
             'shown': {'ceiling_usd': est['ceiling_usd'], 'per_call_ceiling_usd': est['per_call_ceiling_usd'], 'expected_usd': (est['expected'] or {}).get('usd'),
                       'bounds': est['bounds'], 'model': est['model']},
             'test': test,
             **{k: ej.get(k) for k in ('book_sha', 'book_name', 'book_file', 'run_name')}}
    return {'argv': argv, 'env_set': env, 'extra': extra}

# ------------------------------------------------------------------ "Ask the AI Again" (#151: a run held at its review stop)
# run_api.sh's AI_RETRY=1 sends the next unfinished part (lib/aistatus.py retry_parts: the page readings first, else the
# language step); its stop wrote that part's estimate (or the app's "Get a New Estimate" did). The click is checked
# against that estimate as it was shown (retry_fingerprint), the limits, the credit and, for a batch's PDF, what is left
# of the batch's limit; the job is then bound to the "Max Estimated Cost" shown.
RETRY_FILES = {'pages': 'page_reads_retry_estimate.json', 'language': 'language_retry_estimate.json'}
TEST_MODE = 'This isn\'t available in test mode.'
NO_RETRY_ESTIMATE = 'There is no estimate for asking the AI again yet. Select "Get a New Estimate".'
RETRY_CHANGED = 'The estimate changed since it was shown. Select "Get a New Estimate" and look at the new cost.'
NOTHING_TO_RETRY = 'Nothing that the AI can be asked again is missing in this run.'

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def retry_fingerprint(R, part):
    """sha256 over the part's retry estimate file, language_run.json and page_reads_run.json (a missing file counts as
    missing): what the card showed, so the job sends only that."""
    import hashlib
    h = hashlib.sha256(f'{part}\0'.encode())
    for f in (RETRY_FILES.get(part) or '-', 'language_run.json', 'page_reads_run.json'):
        try: b = open(os.path.join(R, f), 'rb').read()
        except OSError: b = b'\0missing'
        h.update(f.encode() + b'\0' + b + b'\0')
    return h.hexdigest()

def retry_estimate(R, part):
    """The part's retry estimate (a dict), or None."""
    d = _load(os.path.join(R, RETRY_FILES[part])) if part in RETRY_FILES else None
    return d if isinstance(d, dict) else None

def retry_refusal(R):
    """Why this run can't be asked again, as run_api.sh refuses it (in plain words), or None."""
    if not os.path.isfile(os.path.join(R, 'workorder.ai.json')) or os.path.isfile(os.path.join(R, 'record.json')):
        return 'This run isn\'t waiting for its review, so there is nothing to ask the AI again.'
    if os.path.isfile(os.path.join(R, 'review.json')): return 'The review is finished: its decisions are being applied.'
    if os.path.isfile(os.path.join(R, 'review_decisions.json')): return 'A review of this run was started, so the AI can\'t be asked again.'
    if os.path.isfile(os.path.join(R, 'ai_override.json')): return 'The review was opened without the missing suggestions, so the AI can\'t be asked again.'
    return None

def retry_check(s, run, R, worst, per_call):
    """The limits, the batch's limit and the credit for a retry costing up to `worst` (one request up to `per_call`);
    raises Refused."""
    L = costs.limits_of(s)
    if per_call > L['per_call_usd']:
        raise Refused(f'One AI request could cost up to ${costs.up(per_call):.2f}, more than the limit of ${L["per_call_usd"]:.2f} per AI request.')
    spent = costs.book_spent(R)
    if spent + worst > L['per_book_usd']:
        raise Refused(f'This PDF could cost up to ${costs.up(spent + worst):.2f}' + (f', including ${spent:.2f} already spent' if spent else '')
                      + f', more than the limit of ${L["per_book_usd"]:.2f} per PDF.')
    p_ = run.split('/')
    if p_[0] == 'batches' and len(p_) == 3:                  # a batch's PDF: what is left of the batch's limit
        left = L['per_batch_usd'] - costs.batch_spent(os.path.dirname(R))['usd']
        if worst > left:
            raise Refused(f'Asking the AI again could cost up to ${costs.up(worst):.2f}, more than the ${max(0.0, int(left * 100) / 100):.2f} left '
                          f'within this batch\'s limit of ${L["per_batch_usd"]:.2f}.')
    credit = credit_read(s)                                  # a fresh "Check Credit Again" read, else one now (free: nothing of the book is sent)
    if credit is None: credit = check_credit(s).get('usd')
    if credit is None: raise Refused(credit_words(s))
    if worst > credit: raise Refused(f'Asking the AI again could cost up to ${costs.up(worst):.2f}, more than the ${credit:.2f} of credit left.')
    return L

def authorize_retry(s, run, R, fingerprint):
    """"Ask the AI Again" (#151): AI_RETRY=1 AUTO=1 bash run_api.sh, in the run's folder (RUN_DIR) with the settings it
    stopped with (review_stop.json), its part's limit bound to the estimate shown and BOOK_MAX_USD to the per-PDF limit."""
    if s.get('test_reply_dir') or s.get('test_batch_from'): raise Refused(TEST_MODE)
    why = retry_refusal(R)
    if why: raise Refused(why)
    from lib import aistatus
    st = aistatus.status(R); part = aistatus.retry_parts(st)
    if not st['held'] or not part: raise Refused(NOTHING_TO_RETRY)
    est = retry_estimate(R, part)
    if est is None: raise Refused(NO_RETRY_ESTIMATE)
    if fingerprint != retry_fingerprint(R, part): raise Refused(RETRY_CHANGED)
    if isinstance(est.get('refused'), dict): raise Refused(est['refused'].get('words') or 'Asking the AI again was left out for its cost.')
    if not int(est.get('to_read' if part == 'pages' else 'to_send') or 0): raise Refused(NO_RETRY_ESTIMATE)
    model = str(est.get('model') or '')
    if not model.startswith('anthropic/'):
        raise Refused('The AI model set for the app isn\'t one whose cost the app can check, so it can\'t be sent from here.')
    if part == 'language' and est.get('prompt_sha256') != current_language_prompt(): raise Refused(OUT_OF_DATE)
    worst = float(est.get('worst_case_usd') or 0)
    per_call = float(est.get('per_page_worst_usd' if part == 'pages' else 'per_call_worst_usd') or 0)
    L = retry_check(s, run, R, worst, per_call)
    from . import runs as RN
    src, why = RN.first_original(s, R)
    if why: raise Refused(why.replace('Applying the reviewed decisions requires', 'Asking the AI again requires'))
    stop = _load(os.path.join(R, 'review_stop.json')) or {}
    se = stop.get('env') if isinstance(stop.get('env'), dict) else {}
    cap = f'{costs.round_up(worst):.2f}'
    env = {'RUN_DIR': R, **{k: str(v) for k, v in se.items() if k in ('OCR_LANG', 'INTAKE_REUSE', 'INTAKE', 'OUT') and v},
           'AI_RETRY': '1', 'AUTO': '1', 'BOOK_MAX_USD': f'{L["per_book_usd"]:.2f}'}
    other = se.get('LANGUAGE_MODEL' if part == 'pages' else 'MODEL')   # the other step's model, as the run had it (Claude only)
    if part == 'pages':
        env.update(MODEL=model, PAGE_READS_MAX_USD=cap)
        if str(other or '').startswith('anthropic/'): env['LANGUAGE_MODEL'] = other
    else:
        env.update(LANGUAGE_MODEL=model, LANGUAGE_MAX_USD=cap)
        if str(other or '').startswith('anthropic/'): env['MODEL'] = other
    name_, label_ = stop.get('name') or os.path.basename(os.path.dirname(R)), os.path.basename(R)
    p_ = run.split('/')
    if p_[0] == 'batches' and len(p_) == 3: name_, label_ = p_[2], p_[1]          # a batch's PDF: runs/batches/<label>/<name>
    x = est.get('expected') if isinstance(est.get('expected'), dict) else {}
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'), 'part': part,
             'shown': {'part': part, 'ceiling_usd': worst, 'max_usd': costs.round_up(worst), 'expected_usd': x.get('usd'), 'model': model}, 'test': False}
    return {'argv': ['bash', 'run_api.sh', src, name_, label_], 'env_set': env, 'extra': extra}

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
        if total['bounds'].get('LANGUAGE_MAX_USD'):              # #118: each book's language step held to the largest's cap
            env.update(LANG_TAGS='on', LANGUAGE_MAX_USD=f'{total["bounds"]["LANGUAGE_MAX_USD"]:.2f}')
        elif total.get('language_local'):                       # #123: only forms decided by a printed reading: the step, sending nothing
            env.update(LANG_TAGS='on', LANGUAGE_MAX_USD='0.00')
    env['REVIEW'] = '1'                                    # every book stops for review (D2a, Patrick 2026-11-06)
    x = total.get('expected') or {}                         # a figure only when every PDF to send has one: a part of them would mislead after the run
    extra = {'fingerprint': fingerprint, 'started_by_click': datetime.datetime.now().isoformat(timespec='seconds'),
             'shown': {'ceiling_usd': total['ceiling_usd'], 'bounds': total['bounds'], 'expected_usd': x.get('usd') if x.get('books') == x.get('of') else None,
                       'spent_usd': total['spent_usd'], 'retry_usd': total['retry_usd']}, 'test': bool(test_from)}
    return {'argv': ['bash', 'batch_api.sh', label, books_list], 'env_set': env, 'extra': extra}
