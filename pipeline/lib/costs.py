"""lib/costs.py: what a paid AI step may cost before it runs, and what it cost after: one place for the pages (the home
page, the run page, the batch page) and, later, for run_api.sh and batch_api.sh. No web code, no network, no writing.

    estimate(R, kind='workorder', limits=None)  → the estimate of the step `kind` in run folder R (schema cost-estimate/1)
    actual(R, rec=)                             → what the run's AI calls cost: {usd, earlier_usd, calls, per_page_usd, original_call}
    batch(Rs, limit, folder=B)                  → the books of a batch added up; `folder` makes the money already spent the whole batch's
    batch_spent(B)                              → every book folder of a batch plus its PDFs moved to the Trash: the one definition of "spent"
    bound(x, limit)                             → a dollar cap for the step: the worst case rounded up to the cent, never above
                                                  the limit (02 M2)
    allowance(kind, forms)                      → a request's normal max tokens (decide.py; every kind has one line here)
    cost_words(a), after_line(R)                → "AI Cost: …" after a run, one wording for the pages and the terminal

The estimate reads the run.json decide.py --dry-run wrote. Two shapes are read: main's (one request: worst_case_total_usd)
and #63's (alt text past 100 images: estimate.passes, book_cap_usd, spent_before_usd, input_margin). `kind` names the paid
step; each kind has a reader for its part of the run folder and says what its fingerprint covers, so a later paid step
adds a reader, not a new page.

Page readings (#49: scanned, mostly Hawaiian pages read whole by read_pages.py) run in the same Spend as the work order,
so the 'workorder' estimate includes them when the estimate job wrote page_reads_estimate.json: their worst case is added
to the book's (ceiling_usd, the per-book and credit checks) and to the fingerprint, and Spend binds them with their own
cap (bounds.PAGE_READS_MAX_USD). MAX_USD and BOOK_MAX_USD stay the work order's own (decide.py's caps).

`expected` (#65, costs in dollars and an expected cost) is what decide.py stored at the estimate (lib/costhistory.py, the figure
people read first). It stays out of the fingerprint, like the credit, and a page never reads the history itself: {usd, low, high,
basis}, or {none: reason} ("Not Available Yet"); an estimate made before it has no such key and no "Expected Cost" line.
"""
import os, json, math, hashlib
from lib import costhistory

SCHEMA = 'cost-estimate/1'
DEFAULT_LIMITS = {'per_call_usd': 2.0, 'per_book_usd': 5.0, 'per_batch_usd': 10.0}  # the one place: decide.py, run_api.sh, batch_api.sh and the app read these
OFFLINE = 'ASSUMED'                                      # decide.py's price_source when OpenRouter could not be reached

def allowance(kind, forms=0):
    """A request's normal max tokens. The cap only checks it: it is never lowered to fit (the run stops before spending).
    The work order has room for the reasoning and a reading per OCR word form (Buddhist used ~37 each)."""
    if kind == 'workorder': return max(48000, 16000 + 45 * forms)
    if kind == 'figure': return 32000
    raise ValueError(f'unknown kind: {kind}')

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
def page_estimate(R):
    """read_pages.py's estimate in run folder R when it has pages to read (the ones read before cost nothing), else None."""
    pr = _load(os.path.join(R, 'page_reads_estimate.json'))
    return pr if isinstance(pr, dict) and isinstance(pr.get('worst_case_usd'), (int, float)) and pr.get('to_read') else None

def pages_paid(R):
    """What the page readings of an unfinished run have cost so far (page_reads_run.json); report.py moves it into the record."""
    pr = _load(os.path.join(R, 'page_reads_run.json'))
    return (pr.get('cost_usd') or 0) if isinstance(pr, dict) else 0

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
    if spent is None: spent = round(sum((a.get('cost_usd') or 0) + (a.get('worst_usd') or 0) for a in att if isinstance(a, dict)) + pages_paid(R), 6)   # decide.py's sum: a charge not known counts at its worst case
    covered = {'estimate': {k: v for k, v in e.items() if k not in ('credit_available_usd', 'expected')},
               'request': _sha(os.path.join(R, 'request.json')), 'digest': _sha(os.path.join(R, '_audit', 'digest.json')),
               'model': run.get('model'), 'prompt': run.get('prompt_sha256')}
    sheets = (run.get('ocr_words') or {}).get('sheets') if isinstance(run.get('ocr_words'), dict) else None
    pr = page_estimate(R)
    if pr: covered['page_reads'] = {k: v for k, v in pr.items() if k != 'expected'}     # the expected figure stays out, like the credit
    return {'run': run, 'e': e, 'passes': passes, 'per_call': per_call, 'spent_before': spent, 'covered': covered,
            'sheets': sheets if isinstance(sheets, int) else None, 'page_reads': pr}

KINDS = {'workorder': _workorder}

def _expected(x):
    """What decide.py stored at the estimate, with the page readings to come added: {usd, low, high, basis}, {none: reason}, or
    None (an estimate made before #65)."""
    v = x['e'].get('expected')
    return costhistory.with_pages(v, x.get('page_reads')) if isinstance(v, dict) and (v.get('usd') is not None or v.get('none')) else None

def up(x):
    """A dollar figure in a sentence that says "up to": never rounded down."""
    return math.ceil(round(x * 100, 6)) / 100

def estimate(R, kind='workorder', limits=None, credit_read=None):
    """The estimate of the paid step `kind` in run folder R, or None when there is none yet. limits: limits_of(settings).
    credit_read: a fresher credit read ("Check Credit Again", U8) used when the estimate's own couldn't be read; the same checks
    apply to it, and the fingerprint never covers the credit."""
    if kind not in KINDS: raise ValueError(f'unknown kind: {kind}')
    x = KINDS[kind](R)
    if x is None: return None
    L = limits or limits_of()
    run, e = x['run'], x['e']
    model = run.get('model') or ''
    claude = model.startswith('anthropic/')
    prices = bool(run.get('price_source')) and not str(run.get('price_source')).startswith(OFFLINE)
    wo_total = float(e['worst_case_total_usd'])                 # the work order's own: decide.py's caps bind it
    pr = x.get('page_reads')
    pr_total = float(pr['worst_case_usd']) if pr else 0.0
    total = wo_total + pr_total
    credit = e.get('credit_available_usd')
    if credit is None and credit_read is not None: credit = credit_read
    book_cap = e.get('book_cap_usd')                     # present on #63's shape; the app's own limit is the one that binds (Spend passes it as BOOK_MAX_USD)
    per_book = L['per_book_usd']
    per_call = max(x['per_call'], float(pr.get('per_page_worst_usd') or 0) if pr else 0)
    fits = {'per_call': per_call <= L['per_call_usd'] if claude else None,
            'per_book': (total + x['spent_before']) <= per_book if claude else None,
            'credit': None if credit is None else total <= credit}
    blocked = None
    if not claude: blocked = {'code': 'model', 'words': 'The AI model set for the app isn\'t one whose cost the app can check, so it can\'t be sent from here.'}
    elif not prices: blocked = {'code': 'offline', 'words': 'Prices and credit couldn\'t be checked, so the cost isn\'t known yet.'}
    elif fits['per_call'] is False: blocked = {'code': 'per_call', 'words': f'This run could cost up to ${up(x["per_call"]):.2f}, more than the limit of ${L["per_call_usd"]:.2f} per AI request.'}
    elif fits['per_book'] is False: blocked = {'code': 'per_book', 'words': f'This PDF could cost up to ${up(total + x["spent_before"]):.2f}'
                                               + (f', including ${x["spent_before"]:.2f} already spent' if x['spent_before'] else '') + f', more than the limit of ${per_book:.2f} per PDF.'}
    elif fits['credit'] is False: blocked = {'code': 'credit', 'words': f'This run could cost up to ${up(total):.2f}, more than the ${credit:.2f} of credit left.'}
    elif credit is None: blocked = {'code': 'no_credit', 'words': 'The credit couldn\'t be checked, so the cost can\'t be compared with it.'}
    fp = hashlib.sha256(json.dumps(x['covered'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {'schema': SCHEMA, 'kind': kind, 'model': model, 'claude': claude, 'prices_checked': prices, 'prompt_sha256': run.get('prompt_sha256'),
            'requests': (len(x['passes']) if x['passes'] else int(e.get('requests') or 1)) + (int(pr['to_read']) if pr else 0), 'images': int(e.get('images') or 0),
            'sheets': x['sheets'], 'input_tokens': e.get('input_tokens'),
            'ceiling_usd': round(total, 4), 'per_call_ceiling_usd': x['per_call'], 'spent_before_usd': x['spent_before'],
            'page_reads': {'pages': int(pr['to_read']), 'ceiling_usd': pr_total} if pr else None,
            'limits': {'per_call_usd': L['per_call_usd'], 'per_book_usd': per_book if book_cap is not None else None},
            'credit_usd': credit, 'fits': fits, 'blocked': blocked, 'expected': _expected(x), 'fingerprint': fp,
            'bounds': {'MAX_USD': bound(x['per_call'], L['per_call_usd']),
                       'BOOK_MAX_USD': bound(wo_total + x['spent_before'], per_book) if book_cap is not None else None,
                       **({'PAGE_READS_MAX_USD': bound(pr_total, per_book)} if pr else {})}}

# ------------------------------------------------------------------ after the run
def _retry_usd(run):
    """What the doubled retries of figure requests cut off cost (figure_passes.cut_off_retries)."""
    fp = run.get('figure_passes') if isinstance(run.get('figure_passes'), dict) else {}
    return round(sum((x.get('cost_usd') or 0) for x in fp.get('cut_off_retries') or [] if isinstance(x, dict)), 6)

def _expected_usd(run, pr=None):
    """The expected figure that was shown. pr: the page readings' estimate, when they were read."""
    x = costhistory.with_pages((run.get('estimate') or {}).get('expected'), pr)
    return x.get('usd') if isinstance(x, dict) else None

def _estimate_usd(run, pr=None):
    """The Max Estimated Cost that was shown: the work order's and figure requests', with the pages that were to be read."""
    c = (run.get('estimate') or {}).get('worst_case_total_usd')
    return round(c + (pr.get('worst_case_usd') or 0), 4) if c is not None and isinstance(pr, dict) and pr.get('to_read') else c

def _page_money(pr):
    """(paid, requests paid for, the estimate shown) of the page readings: the record's page_reads or page_reads_run.json. cost_usd
    is the step's running total, and a page read before keeps its one charge, so this counts every page once."""
    if not isinstance(pr, dict): return 0.0, 0, None
    return round(pr.get('cost_usd') or 0, 6), sum(1 for p in pr.get('pages') or [] if isinstance(p, dict) and p.get('cost_usd')), pr.get('estimate')

_READ = object()                                   # actual()'s rec when the caller didn't read it

def actual(R, rec=_READ):
    """What the run's AI calls cost: the record's (with earlier cut-off attempts), else run.json's and attempts.json's for
    a run that has not finished. A reply reused from elsewhere costs nothing new: its original call's cost is reported apart. A
    reply this folder paid for and read again is different (run.own_reply, decided by decide.py when it reads it): that money was
    spent on this run, so it counts like any other. Page readings (#49) are this folder's own money at every stage: from
    page_reads_run.json until report.py moves them into the record, then from the record, once. retry_usd: the
    part that retried a figure request cut off; expected_usd and estimate_usd: what was shown before it was sent. no_model:
    run.no_model, set for a run with no AI request at all (decide.py --no-model: a PDF edited by hand), whose calls are 0.
    rec: record.json as the caller already read it (None: there is none), so a page reads it once (#93); never changed here."""
    if rec is _READ: rec = _load(os.path.join(R, 'record.json'))
    if rec:
        run = rec.get('run') or {}
        nm = run.get('no_model') or None
        own = bool(run.get('own_reply'))
        saved = bool(run.get('response_from')) and not own
        pages, page_calls, pr = _page_money(rec.get('page_reads'))
        reused = saved and not pages
        earlier = sum((a.get('cost_usd') or 0) for a in rec.get('earlier_attempts') or [] if isinstance(a, dict))
        this = pages + (0.0 if saved else ((run.get('usage') or {}).get('cost_usd') or 0.0))
        if not saved and not own and isinstance(rec.get('cost_total_usd'), (int, float)): this = max(rec['cost_total_usd'] - earlier, this)   # report.py's sum; a re-apply's record from before the page readings were kept in it has less
        try:
            from lib import origin
            ai = origin.summary(rec)
        except Exception: ai = {}
        doc_pages = (rec.get('document') or {}).get('pages')
        return {'usd': round(this + earlier, 6), 'earlier_usd': round(earlier, 6), 'calls': (0 if saved or nm else len(run.get('passes') or []) or 1) + len(rec.get('earlier_attempts') or []) + page_calls,
                'per_page_usd': round((this + earlier) / doc_pages, 6) if doc_pages and (this + earlier) else None, 'reused': reused,
                'original_call': {'usd': ai.get('cost_usd'), 'date': ai.get('date')} if reused else None, 'finished': True,
                'estimate_usd': _estimate_usd(run, pr),
                'expected_usd': None if reused else _expected_usd(run, pr), 'retry_usd': 0.0 if saved else _retry_usd(run), 'no_model': nm}
    run = _load(os.path.join(R, 'run.json')) or {}
    saved = bool(run.get('response_from')) and not run.get('own_reply')
    pages, page_calls, pr = _page_money(_load(os.path.join(R, 'page_reads_run.json')))
    reused = saved and not pages
    decided = 0.0 if saved else ((run.get('usage') or {}).get('cost_usd') or 0.0)
    this = decided + pages
    earlier = sum((a.get('cost_usd') or 0) for a in _load(os.path.join(R, 'attempts.json')) or [] if isinstance(a, dict))
    return {'usd': round(this + earlier, 6), 'earlier_usd': round(earlier, 6), 'calls': (len(run.get('passes') or []) or (1 if decided else 0)) + len(_load(os.path.join(R, 'attempts.json')) or []) + page_calls,
            'per_page_usd': None, 'reused': reused, 'original_call': None, 'finished': False,
            'estimate_usd': _estimate_usd(run, pr),
            'expected_usd': None if reused else _expected_usd(run, pr), 'retry_usd': 0.0 if saved else _retry_usd(run),
            'no_model': run.get('no_model') or None}

NO_MODEL_WORDS = 'none (no AI request: a PDF edited by hand)'   # "AI Cost: …" for a run with no AI request at all

def cost_words(a, so_far=False):
    """The words after "AI Cost:" or "Total Cost:", one source for the run page, the batch page and the terminal. a: {usd,
    earlier_usd, retry_usd, expected_usd, estimate_usd}. "Max Estimated Cost" describes what was shown before sending, so when
    a previous attempt or a doubled retry was paid for the total is shown as an addition and says what the maximum leaves out."""
    total = round(a.get('usd') or 0, 2)
    retry = min(round(a.get('retry_usd') or 0, 2), total); prev = min(round(a.get('earlier_usd') or 0, 2), round(total - retry, 2))   # never a part larger than the whole, so none is negative
    ceiling, exp = a.get('estimate_usd'), a.get('expected_usd')
    amount = f'${total:.2f}' + (' so far' if so_far else '')
    if prev or retry:
        new = round(total - prev - retry, 2)                 # nothing spent yet by this send (a batch sent again): no "$0.00 +"
        parts = ([f'${new:.2f}'] if new else []) + ([f'${prev:.2f} for previous attempts'] if prev else []) + ([f'${retry:.2f} to retry an answer that was cut off'] if retry else [])
        s = f'{amount} ({" + ".join(parts)})'
        if retry and not prev and exp is not None: s += f' · Expected: ${exp:.2f}'
        left_out = ' or '.join((['previous attempts'] if prev else []) + (['the retry'] if retry else []))
        return s + (f' · Max Estimated Cost: ${ceiling:.2f}, not including {left_out}' if ceiling else '')
    shown = ([f'expected ${exp:.2f}'] if exp is not None else []) + ([f'max estimated ${ceiling:.2f}'] if ceiling else [])
    return amount + (f' ({", ".join(shown)})' if shown else '')

def after_line(R):
    """The terminal's line after a run, in the run page's words."""
    a = actual(R)
    if a.get('no_model') and not a['usd']: return 'AI Cost: ' + NO_MODEL_WORDS
    return 'AI Cost: none (a saved reply was used)' if a['reused'] else 'AI Cost: ' + cost_words(a)

def still_trashed(B):
    """The entries of a batch's trashed.json whose PDF is still in the Trash. One dragged back has its folder here again, and that
    folder counts it. The one filter behind the batch's spent money, its page and summary.md."""
    try: here = {e.name for e in os.scandir(B) if e.is_dir()}
    except OSError: here = set()
    return [x for x in _load(os.path.join(B, 'trashed.json')) or [] if isinstance(x, dict) and x.get('name') not in here]

def batch_spent(B, rd=None):
    """What the whole batch has spent: every book folder in it, whatever its state (waiting for review, finished, stopped), and
    the PDFs moved to the Trash (their folders are gone; trashed.json keeps their cost). The one definition behind the batch
    limit, the page's "Total Cost" and batch_api.sh's check. {usd, earlier_usd, retry_usd, trashed_usd}. rd: a page's JSON
    reader (path → data or None), so each record is read once per page (#93)."""
    usd = earlier = retry = 0.0
    try: dirs = sorted(e.path for e in os.scandir(B) if e.is_dir() and not e.name.startswith('.'))
    except OSError: dirs = []
    for R in dirs:
        a = actual(R, rd(os.path.join(R, 'record.json'))) if rd else actual(R); usd += a['usd']; earlier += a['earlier_usd']; retry += a['retry_usd']
    trashed = sum((x.get('cost_usd') or 0) for x in still_trashed(B))
    return {'usd': round(usd + trashed, 6), 'earlier_usd': round(earlier, 6), 'retry_usd': round(retry, 6), 'trashed_usd': round(trashed, 6)}

def shown_words(B, shown, so_far=False, rd=None):
    """The batch's total, in the page's words. shown: what was agreed before this send ({ceiling_usd, expected_usd, spent_usd, retry_usd}).
    rd: as batch_spent()."""
    sp = batch_spent(B, rd)
    return cost_words({'usd': sp['usd'], 'earlier_usd': shown.get('spent_usd') or 0, 'retry_usd': max(0, sp['retry_usd'] - (shown.get('retry_usd') or 0)),
                       'expected_usd': shown.get('expected_usd'), 'estimate_usd': shown.get('ceiling_usd')}, so_far=so_far)

def progress_words(B, name):
    """What batch_api.sh prints after each PDF: its cost and the batch's running total."""
    shown = _load(os.path.join(B, '.shown.json')) or {}
    return f' · AI Cost: ${actual(os.path.join(B, name))["usd"]:.2f} · Total Cost: {shown_words(B, shown, so_far=True)}'

def retry_env(L):
    """The limits a doubled figure-request retry may use: the person's real ones, for that retry only. The first send of every
    request stays bound to the estimate shown (MAX_USD, BOOK_MAX_USD)."""
    return {'FIGURE_RETRY_MAX_USD': f'{L["per_call_usd"]:.2f}', 'FIGURE_RETRY_BOOK_MAX_USD': f'{L["per_book_usd"]:.2f}'}

WORDS = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine'}
def batch_advice(fit_n):
    """What a person can do about a batch over its limit. fit_n counts the smallest PDFs first, so the sentence says the smallest."""
    who = '' if not fit_n else 'Only the smallest PDF in this batch' if fit_n == 1 else f'Only the {WORDS.get(fit_n, fit_n)} smallest PDFs in this batch'
    return 'The app administrator can raise the limit or you can start a batch with fewer PDFs.' + (f' {who} would fit within the current limit.' if who else '')

def batch_over_words(total):
    """Why a batch over its limit is refused: the most it could cost (with what it already spent) and the limit named."""
    return (f'This batch could cost up to ${up(total["could_cost_usd"]):.2f}' + (f', including ${total["spent_usd"]:.2f} already spent' if total['spent_usd'] else '')
            + f', more than the limit of ${total["limit_usd"]:.2f} per batch.')

def batch(Rs, limit=None, limits=None, credit_read=None, folder=None, rd=None):
    """The books of a batch added up: the worst case of every book still to send (one with a complete saved reply adds
    nothing), what was spent so far, and whether spent + worst case fits the batch limit, and the worst case the credit.
    folder: the batch's folder, so "spent" is the whole batch's (batch_spent), not only these books'. rd: as batch_spent()."""
    L = limits or limits_of()
    lim = L['per_batch_usd'] if limit is None else limit
    books, ceiling, credit, per_call, blocked = [], 0.0, None, 0.0, []
    requests, per_book, pr_book = 0, None, None          # every AI request of the books to send, and the largest book's bounds (#63's shape, #49's page readings)
    exp_usd, exp_n, exp_of, exp_seen, adds = 0.0, 0, 0, False, []
    for R in Rs:
        if os.path.isfile(os.path.join(R, 'record.json')) or (os.path.isfile(os.path.join(R, 'workorder.json')) and os.path.isfile(os.path.join(R, 'response.json'))):
            books.append({'R': R, 'estimate': None, 'adds_usd': 0.0}); continue
        e = estimate(R, limits=L, credit_read=credit_read)
        if e:
            ceiling += e['ceiling_usd']; per_call = max(per_call, e['per_call_ceiling_usd']); requests += e['requests']; adds.append(e['ceiling_usd'])
            if e['bounds']['BOOK_MAX_USD'] is not None: per_book = max(per_book or 0, e['bounds']['BOOK_MAX_USD'])
            if e['bounds'].get('PAGE_READS_MAX_USD') is not None: pr_book = max(pr_book or 0, e['bounds']['PAGE_READS_MAX_USD'])
            if e['credit_usd'] is not None: credit = e['credit_usd'] if credit is None else min(credit, e['credit_usd'])
            if e['blocked'] and e['blocked']['code'] not in ('credit', 'no_credit'): blocked.append((R, e['blocked']))
            x = e['expected']; exp_of += 1
            if x is not None: exp_seen = True
            if x is not None and x.get('usd') is not None: exp_usd += x['usd']; exp_n += 1
        books.append({'R': R, 'estimate': e, 'adds_usd': e['ceiling_usd'] if e else None})
    sp = batch_spent(folder, rd) if folder else {'usd': round(sum(actual(R)['usd'] for R in Rs), 6), 'retry_usd': round(sum(actual(R)['retry_usd'] for R in Rs), 6)}
    spent = sp['usd']; could = spent + ceiling
    room, fit_n = lim - spent, 0
    for c in sorted(adds):
        if c > room: break
        room -= c; fit_n += 1
    return {'schema': SCHEMA, 'books': books, 'ceiling_usd': round(ceiling, 4), 'per_call_ceiling_usd': per_call,
            'expected': {'usd': round(exp_usd, 4) if exp_n else None, 'books': exp_n, 'of': exp_of} if exp_seen else None, 'requests': requests,
            'spent_usd': round(spent, 6), 'retry_usd': sp['retry_usd'], 'could_cost_usd': round(could, 6), 'fit_n': fit_n, 'credit_usd': credit, 'limit_usd': lim,
            'fits': {'batch': could <= lim, 'credit': None if credit is None else ceiling <= credit},
            'blocked': blocked,
            'bounds': {'MAX_USD': bound(per_call, L['per_call_usd']) if per_call else None, 'BATCH_MAX_USD': bound(could, lim),
                       **({'BOOK_MAX_USD': per_book} if per_book is not None else {}),
                       **({'PAGE_READS_MAX_USD': pr_book} if pr_book is not None else {})}}
