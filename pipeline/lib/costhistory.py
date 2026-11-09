"""lib/costhistory.py: what an AI call is expected to cost, learned from past calls (#65, costs in dollars and an expected cost).
Local arithmetic on token counts: no network, no book content. It is the only module that writes the history.

    rows()                                      the seed plus the local ledger, each call once
    expected(requests, model, prices, ceiling)  {usd, low, high, basis}, or {none: <reason>}
    append(row)                                 one finished call added to the ledger (never raises)
    book_id(run_dir, digest)                    a short id from the original PDF's sha256

Where the history lives
    lib/cost_seed.json             committed, numbers only: built once from past records by tools/cost_seed.py. So a computer
                                   with no history still has a figure. Books are plain labels (b01, b02, …).
    <runs>/.cost-history.jsonl     local, one line per finished paid call (COST_HISTORY, else RUNS_DIR). Survives the removal
                                   of any run folder, never committed. Books are short ids made from the original's sha256.
    <runs>/.cost-book-labels.json  local, written by tools/cost_seed.py: {sha-based id: seed label}.

One call, one row; one book, one book:
  - the same call in seed and ledger (the seed rebuilt after the ledger recorded it) is one row: a ledger row is dropped when a
    seed row has the same date, input estimate, billed input and output;
  - inside the ledger the key is (book, started, pass, attempt);
  - a book in both counts as one book: the local labels file turns its ledger id into its seed label before anything is
    counted or fitted. On a computer without that file (the seed's ids are deliberately not linkable to a PDF) a seed book
    run again there counts as one more book.

The rule (handoff/cost-estimates/01, §3.5). Per model and kind, the last 80 calls: predicted output tokens from
log(output) = a + b log(input estimate), each book weighing the same; the range is the 5th to 95th percentile of actual/predicted
with each ratio from a fit that left that book out. Output tokens are what it learns, so a price change needs no new history.
It never decides anything: limits and credit are checked against the ceiling. No figure ("Not Available Yet") for fewer than
12 calls from 6 books, for an input above the largest of its training calls, or after a cut-off in the same folder. A predicted
output never passes the request's allowance and the figure never passes the ceiling.
"""
import os, sys, json, math, hashlib, collections

SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cost_seed.json')
LEDGER_NAME, LABELS_NAME = '.cost-history.jsonl', '.cost-book-labels.json'
WINDOW, MIN_CALLS, MIN_BOOKS = 80, 12, 6
LOW, HIGH = 0.05, 0.95
SEED_KEYS = ('kind', 'model', 'prompt', 'input_est', 'input_billed', 'output', 'images', 'forms', 'date', 'book')

def ledger_path(environ=None):
    """COST_HISTORY, else <RUNS_DIR>/.cost-history.jsonl, else None (decide.py called directly: nothing is written)."""
    e = os.environ if environ is None else environ
    if e.get('COST_HISTORY'): return e['COST_HISTORY']
    return os.path.join(e['RUNS_DIR'], LEDGER_NAME) if e.get('RUNS_DIR') else None

def _labels(ledger):
    try: d = json.load(open(os.path.join(os.path.dirname(ledger), LABELS_NAME), encoding='utf-8'))
    except (OSError, ValueError, TypeError): return {}
    return d if isinstance(d, dict) else {}

def _good(r):
    """A row usable for learning: the fields it needs, as numbers above zero."""
    if not isinstance(r, dict): return False
    if not all(isinstance(r.get(k), str) and r[k] for k in ('kind', 'model', 'date', 'book')): return False
    return all(isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool) and r[k] > 0 for k in ('input_est', 'input_billed', 'output'))

def seed_rows(path=SEED):
    try: d = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError): return []
    return [r for r in (d.get('rows') if isinstance(d, dict) else None) or [] if _good(r)]

def _call_key(r): return (r['date'], r['input_est'], r['input_billed'], r['output'])

def rows(ledger=None, seed=SEED):
    """The seed plus the ledger (ledger: a path; default: ledger_path()). A malformed line is skipped, so a line another
    process is writing or a damaged one can't stop an estimate; a missing file is the seed alone."""
    out = seed_rows(seed)
    ledger = ledger_path() if ledger is None else ledger
    if not ledger: return out
    known, seen, labels = {_call_key(r) for r in out}, set(), _labels(ledger)
    try:
        with open(ledger, encoding='utf-8', errors='replace') as f: lines = f.readlines()
    except OSError: return out
    for line in lines:
        try: r = json.loads(line)
        except ValueError: continue
        if not _good(r): continue
        r['book'] = labels.get(r['book'], r['book'])
        k = (r['book'], r['date'], str(r.get('pass')), r.get('attempt'))
        if k in seen or _call_key(r) in known: continue
        seen.add(k); out.append(r)
    return out

# ------------------------------------------------------------------ the fit
def _line(tr):
    """(a, b) of log(output) = a + b·log(input, thousands), each book weighing the same (a small ridge keeps it solvable)."""
    n = collections.Counter(r['book'] for r in tr)
    s0 = sxy = sx = sy = sxx = 0.0
    for r in tr:
        w = 1 / n[r['book']]; x = math.log(r['input_est'] / 1000); y = math.log(r['output'])
        s0 += w; sx += w * x; sy += w * y; sxx += w * x * x; sxy += w * x * y
    s0 += 1e-6; sxx += 1e-6
    det = s0 * sxx - sx * sx
    return (sy * sxx - sx * sxy) / det, (s0 * sxy - sx * sy) / det

def _quantile(pairs, p):
    """The p-quantile of [(value, book)], each book weighing the same."""
    n = collections.Counter(b for _, b in pairs); acc = 0.0
    ordered = sorted(pairs)
    for v, b in ordered:
        acc += 1 / n[b] / len(n)
        if acc >= p: return v
    return ordered[-1][0]

def _median(v):
    v = sorted(v); m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2

def _ask(a, b, input_est): return math.exp(a + b * math.log(input_est / 1000))

def learn(train, min_calls=MIN_CALLS, min_books=MIN_BOOKS):
    """What these calls teach, or None when they are too few. train: rows, oldest first (the window is cut here)."""
    tr = train[-WINDOW:]
    books = {r['book'] for r in tr}
    if len(tr) < min_calls or len(books) < min_books: return None
    a, b = _line(tr); ratios = []
    for bk in books:
        rest = [r for r in tr if r['book'] != bk]
        if len({r['book'] for r in rest}) < 2: continue
        a_, b_ = _line(rest)
        ratios += [(r['output'] / _ask(a_, b_, r['input_est']), bk) for r in tr if r['book'] == bk]
    return {'a': a, 'b': b, 'lo': _quantile(ratios, LOW), 'md': _quantile(ratios, 0.5), 'hi': _quantile(ratios, HIGH),
            'input_ratio': _median([r['input_billed'] / r['input_est'] for r in tr]),
            'max_input': max(r['input_est'] for r in tr), 'calls': len(tr), 'books': len(books)}

def predict(m, input_est, max_tokens):
    """(low, expected, high) output tokens: never past the request's allowance."""
    p = _ask(m['a'], m['b'], input_est)
    return tuple(min(p * m[k], max_tokens) for k in ('lo', 'md', 'hi'))

def expected(requests, model, price_in, price_out, ceiling, cut_off=False, history=None):
    """requests: [{kind, input_est, max_tokens}]. Returns {usd, low, high, basis: {calls, books}}, or {none: reason, …} with the
    reason a person could be told: too_few (calls and books so far), above_history, cut_off."""
    if cut_off: return {'none': 'cut_off'}
    history = rows() if history is None else history
    usd = low = high = 0.0; basis, learned = None, {}
    for q in requests:
        k = q['kind']
        if k not in learned:
            all_ = sorted((r for r in history if r['model'] == model and r['kind'] == k), key=lambda r: r['date'])
            learned[k] = (learn(all_), all_)
        m, all_ = learned[k]
        if m is None:
            return {'none': 'too_few', 'kind': k, 'calls': len(all_), 'books': len({r['book'] for r in all_})}
        if q['input_est'] > m['max_input']: return {'none': 'above_history', 'kind': k}
        lo, md, hi = predict(m, q['input_est'], q['max_tokens'])
        cost_in = q['input_est'] * m['input_ratio'] * price_in
        usd += cost_in + md * price_out; low += cost_in + lo * price_out; high += cost_in + hi * price_out
        basis = basis or {'calls': m['calls'], 'books': m['books']}
    usd, high = min(usd, ceiling), min(high, ceiling)
    return {'usd': round(usd, 4), 'low': round(min(low, usd), 4), 'high': round(max(high, usd), 4), 'basis': basis}

def terminal_line(x):
    """The terminal's "Expected Cost" line (the pages show the figure only, and no reason)."""
    if x.get('usd') is not None:
        b = x.get('basis') or {}
        return (f'Expected Cost: ${x["usd"]:.2f} (usually ${x["low"]:.2f}–${x["high"]:.2f})'
                + (f', from the last {b["calls"]} calls ({b["books"]} PDFs)' if b.get('calls') else ''))
    why = {'cut_off': 'an AI answer was cut off in this folder, so past runs say little about the next one',
           'above_history': 'larger than any PDF it has learned from',
           'too_few': f'{x.get("calls", 0)} past call{"" if x.get("calls") == 1 else "s"} of this kind, from {x.get("books", 0)} PDF{"" if x.get("books") == 1 else "s"}; needs {MIN_CALLS} from {MIN_BOOKS}'}
    return 'Expected Cost: Not Available Yet' + (f' ({why[x["none"]]})' if x.get('none') in why else '')

# ------------------------------------------------------------------ the ledger
_warned = False
def append(row, path=None):
    """One line, one os.write on an O_APPEND descriptor, so books running at once can't mix their lines. A paid run is never
    stopped by this: any error is swallowed and reported once. Returns True when written."""
    global _warned
    try:
        path = ledger_path() if path is None else path
        if not path: return False
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        data = (json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try: os.write(fd, data)
        finally: os.close(fd)
        return True
    except Exception as e:
        if not _warned: print(f'note: the cost history could not be written ({type(e).__name__}); the run goes on', file=sys.stderr)
        _warned = True
        return False

def book_id(run_dir, digest):
    """A short id from the original PDF's sha256 (never the digest's file name: it is intake.pdf for every untagged book)."""
    sha = None
    try: sha = (json.load(open(os.path.join(run_dir, '_intake', 'intake.json'), encoding='utf-8')).get('original') or {}).get('sha256')
    except (OSError, ValueError, AttributeError): pass
    sha = sha or ((digest or {}).get('source') or {}).get('sha256') or 'unknown'
    return hashlib.sha256(sha.encode()).hexdigest()[:16]
