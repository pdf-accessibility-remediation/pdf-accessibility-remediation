"""lib/costs.py: what a paid AI step may cost before it runs, and what it cost after: one place for the pages (the home
page, the run page, the batch page) and, later, for run_api.sh and batch_api.sh. No web code, no network, no writing.

    estimate(R, kind='workorder', limits=None)  → the estimate of the step `kind` in run folder R (schema cost-estimate/1)
    actual(R)                                   → what the run's AI calls cost: {usd, earlier_usd, calls, per_page_usd, original_call}
    batch(Rs, limit)                            → the books of a batch added up
    bound(x, limit)                             → a dollar cap for the step: the worst case rounded up to the cent, never above
                                                  the limit (02 M2)

The estimate reads the run.json decide.py --dry-run wrote. Two shapes are read: main's (one request: worst_case_total_usd)
and #63's (alt text past 100 images: estimate.passes, book_cap_usd, spent_before_usd, input_margin). `kind` names the paid
step; each kind has a reader for its part of the run folder and says what its fingerprint covers, so a later paid step
(#49, AI drafts for hard OCR pages: 'ocr-draft') adds a reader, not a new page.

`expected` is the hook for #65 (dollar-only cost limits): None until #65 fills it from _expected(); the pages show it
only when present ("About $0.25 (usually $0.18–$0.36) · Worst-case estimate $0.62 …").
"""
import os, json, math, hashlib

SCHEMA = 'cost-estimate/1'
DEFAULT_LIMITS = {'per_call_usd': 2.0, 'per_book_usd': 5.0, 'per_batch_usd': 5.0}   # the pipeline's own defaults (decide.py, #63, batch_api.sh)
OFFLINE = 'ASSUMED'                                      # decide.py's price_source when OpenRouter could not be reached

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def _sha(p):
    try:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
        return h.hexdigest()
    except OSError: return None

def limits_of(s=None):
    """The app's `limits` setting over the defaults; numbers only."""
    out = dict(DEFAULT_LIMITS)
    for k, v in ((s or {}).get('limits') or {}).items():
        if k in out and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0: out[k] = float(v)
    return out

def round_up(x):
    """Up to the cent, from a stored value that decide.py rounded to 4 decimals: the stored value plus 0.0001 first, so a
    true 0.62004 stored as 0.6200 gives 0.63, never 0.62 (02 M2)."""
    return math.ceil(round((x + 0.0001) * 100, 6)) / 100

def bound(x, limit):
    """The cap passed to the paid step: round_up(x), never above the limit."""
    return min(round_up(x), limit) if limit is not None else round_up(x)

# ------------------------------------------------------------------ kinds
def _workorder(R):
    """The work-order call (decide.py): run.json's estimate; the fingerprint covers the estimate without the credit,
    request.json's sha256, the digest's sha256, the model and the prompt's sha256."""
    run = _load(os.path.join(R, 'run.json')) or {}
    e = run.get('estimate')
    if not isinstance(e, dict) or 'worst_case_total_usd' not in e: return None
    passes = e.get('passes') if isinstance(e.get('passes'), list) else None
    per_call = max((p.get('worst_case_usd') or 0) for p in passes) if passes else e['worst_case_total_usd']
    att = _load(os.path.join(R, 'attempts.json')) or []
    spent = e.get('spent_before_usd')
    if spent is None: spent = round(sum((a.get('cost_usd') or 0) for a in att if isinstance(a, dict)), 6)
    covered = {'estimate': {k: v for k, v in e.items() if k != 'credit_available_usd'},
               'request': _sha(os.path.join(R, 'request.json')), 'digest': _sha(os.path.join(R, '_audit', 'digest.json')),
               'model': run.get('model'), 'prompt': run.get('prompt_sha256')}
    sheets = (run.get('ocr_words') or {}).get('sheets') if isinstance(run.get('ocr_words'), dict) else None
    return {'run': run, 'e': e, 'passes': passes, 'per_call': per_call, 'spent_before': spent, 'covered': covered,
            'sheets': sheets if isinstance(sheets, int) else None}

KINDS = {'workorder': _workorder}

class NotBuilt(Exception):
    """A kind that is named for a later issue and has no reader yet."""

def _expected(x):
    """#65 (dollar-only cost limits): the expected cost and its range, {usd, low, high, basis}; None until #65 builds it."""
    return None

def estimate(R, kind='workorder', limits=None):
    """The estimate of the paid step `kind` in run folder R, or None when there is none yet. limits: limits_of(settings)."""
    if kind == 'ocr-draft': raise NotBuilt('the OCR-draft estimate comes with #49 (AI drafts for hard OCR pages)')
    if kind not in KINDS: raise ValueError(f'unknown kind: {kind}')
    x = KINDS[kind](R)
    if x is None: return None
    L = limits or limits_of()
    run, e = x['run'], x['e']
    model = run.get('model') or ''
    claude = model.startswith('anthropic/')
    prices = bool(run.get('price_source')) and not str(run.get('price_source')).startswith(OFFLINE)
    total = float(e['worst_case_total_usd'])
    credit = e.get('credit_available_usd')
    book_cap = e.get('book_cap_usd')
    per_book = min(L['per_book_usd'], book_cap) if book_cap is not None else L['per_book_usd']
    fits = {'per_call': x['per_call'] <= L['per_call_usd'] if claude else None,
            'per_book': (total + x['spent_before']) <= per_book if claude else None,
            'credit': None if credit is None else total <= credit}
    blocked = None
    if not claude: blocked = {'code': 'model', 'words': 'The AI model set for the app isn\'t one whose cost the app can check, so it can\'t be sent from here.'}
    elif not prices: blocked = {'code': 'offline', 'words': 'Prices and credit couldn\'t be checked, so the cost isn\'t known yet.'}
    elif fits['per_call'] is False: blocked = {'code': 'per_call', 'words': f'This run could cost more than the limit of ${L["per_call_usd"]:.2f} per AI call.'}
    elif fits['per_book'] is False: blocked = {'code': 'per_book', 'words': f'This book could cost more than the limit of ${per_book:.2f} per book.'}
    elif fits['credit'] is False: blocked = {'code': 'credit', 'words': 'There isn\'t enough credit for this run.'}
    elif credit is None: blocked = {'code': 'no_credit', 'words': 'The credit couldn\'t be checked, so the cost can\'t be compared with it.'}
    fp = hashlib.sha256(json.dumps(x['covered'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {'schema': SCHEMA, 'kind': kind, 'model': model, 'claude': claude, 'prices_checked': prices, 'prompt_sha256': run.get('prompt_sha256'),
            'requests': len(x['passes']) if x['passes'] else int(e.get('requests') or 1), 'images': int(e.get('images') or 0),
            'sheets': x['sheets'], 'input_tokens': e.get('input_tokens'),
            'ceiling_usd': total, 'per_call_ceiling_usd': x['per_call'], 'spent_before_usd': x['spent_before'],
            'limits': {'per_call_usd': L['per_call_usd'], 'per_book_usd': per_book if book_cap is not None else None},
            'credit_usd': credit, 'fits': fits, 'blocked': blocked, 'expected': _expected(x), 'fingerprint': fp,
            'bounds': {'MAX_USD': bound(x['per_call'], L['per_call_usd']),
                       'BOOK_MAX_USD': bound(total + x['spent_before'], per_book) if book_cap is not None else None}}

# ------------------------------------------------------------------ after the run
def actual(R):
    """What the run's AI calls cost: the record's (with earlier cut-off attempts), else run.json's and attempts.json's for
    a run that has not finished. A reused reply costs nothing new: its original call's cost is reported apart."""
    rec = _load(os.path.join(R, 'record.json'))
    if rec:
        run = rec.get('run') or {}
        reused = bool(run.get('response_from'))
        earlier = sum((a.get('cost_usd') or 0) for a in rec.get('earlier_attempts') or [] if isinstance(a, dict))
        this = 0.0 if reused else ((run.get('usage') or {}).get('cost_usd') or 0.0)
        if not reused and isinstance(rec.get('cost_total_usd'), (int, float)): this = rec['cost_total_usd'] - earlier   # report.py's sum
        try:
            from lib import origin
            ai = origin.summary(rec)
        except Exception: ai = {}
        pages = (rec.get('document') or {}).get('pages')
        return {'usd': round(this + earlier, 6), 'earlier_usd': round(earlier, 6), 'calls': (0 if reused else 1) + len(rec.get('earlier_attempts') or []),
                'per_page_usd': round((this + earlier) / pages, 6) if pages and (this + earlier) else None, 'reused': reused,
                'original_call': {'usd': ai.get('cost_usd'), 'date': ai.get('date')} if reused else None, 'finished': True,
                'estimate_usd': ((run.get('estimate') or {}).get('worst_case_total_usd'))}
    run = _load(os.path.join(R, 'run.json')) or {}
    reused = bool(run.get('response_from'))
    this = 0.0 if reused else ((run.get('usage') or {}).get('cost_usd') or 0.0)
    earlier = sum((a.get('cost_usd') or 0) for a in _load(os.path.join(R, 'attempts.json')) or [] if isinstance(a, dict))
    return {'usd': round(this + earlier, 6), 'earlier_usd': round(earlier, 6), 'calls': (1 if this else 0) + len(_load(os.path.join(R, 'attempts.json')) or []),
            'per_page_usd': None, 'reused': reused, 'original_call': None, 'finished': False,
            'estimate_usd': ((run.get('estimate') or {}).get('worst_case_total_usd'))}

def batch(Rs, limit=None, limits=None):
    """The books of a batch added up: the worst case of every book still to send (one with a complete saved reply adds
    nothing), what was spent so far, and whether the total fits the batch limit and the credit."""
    L = limits or limits_of()
    lim = L['per_batch_usd'] if limit is None else limit
    books, ceiling, spent, credit, per_call, blocked = [], 0.0, 0.0, None, 0.0, []
    for R in Rs:
        a = actual(R); spent += a['usd']
        if os.path.isfile(os.path.join(R, 'record.json')) or (os.path.isfile(os.path.join(R, 'workorder.json')) and os.path.isfile(os.path.join(R, 'response.json'))):
            books.append({'R': R, 'estimate': None, 'adds_usd': 0.0}); continue
        e = estimate(R, limits=L)
        if e:
            ceiling += e['ceiling_usd']; per_call = max(per_call, e['per_call_ceiling_usd'])
            if e['credit_usd'] is not None: credit = e['credit_usd'] if credit is None else min(credit, e['credit_usd'])
            if e['blocked'] and e['blocked']['code'] not in ('credit', 'no_credit'): blocked.append((R, e['blocked']))
        books.append({'R': R, 'estimate': e, 'adds_usd': e['ceiling_usd'] if e else None})
    return {'schema': SCHEMA, 'books': books, 'ceiling_usd': round(ceiling, 4), 'per_call_ceiling_usd': per_call, 'expected': None,
            'spent_usd': round(spent, 6), 'credit_usd': credit, 'limit_usd': lim,
            'fits': {'batch': ceiling <= lim, 'credit': None if credit is None else ceiling <= credit},
            'blocked': blocked,
            'bounds': {'MAX_USD': bound(per_call, L['per_call_usd']) if per_call else None, 'BATCH_MAX_USD': bound(ceiling, lim)}}
