"""cost_backtest.py: how good is the expected cost? Each past work-order call is predicted only from calls made before it and
never from its own book, on the committed seed alone (any computer, no runs/ folder needed, no model).

    python3 tools/cost_backtest.py

Prints the share of calls whose actual cost fell in the terminal's range, how close the single figure was, the bias per prompt,
how often no figure is given, and whether any past bill is above its recomputed ceiling. tests/test_costs.py asserts on these.
"""
import os, sys, collections

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import costhistory as H, costs as C

PIN, POUT = 2e-6, 10e-6                  # Sonnet 5.5's prices; the seed's calls were all billed at the listed prices
MODEL = 'anthropic/claude-sonnet-5.5'

def forward(rows=None):
    """[{row, expected, low, high, actual}] per call predicted, and how many calls got no figure because of their size."""
    rows = sorted((r for r in (H.seed_rows() if rows is None else rows) if r['model'] == MODEL and r['kind'] == 'workorder'), key=lambda r: r['date'])
    out, above = [], 0
    for c in rows:
        tr = [t for t in rows if t['date'] < c['date'] and t['book'] != c['book']]
        m = H.learn(tr)
        if not m: continue
        if c['input_est'] > m['max_input']: above += 1; continue
        lo, md, hi = H.predict(m, c['input_est'], C.allowance('workorder', c.get('forms') or 0))
        cost_in = c['input_est'] * m['input_ratio'] * PIN
        out.append({'row': c, 'expected': cost_in + md * POUT, 'low': cost_in + lo * POUT, 'high': cost_in + hi * POUT,
                    'actual': c['input_billed'] * PIN + c['output'] * POUT})
    return out, above

def newest(F):
    last = {}
    for x in F: last[x['row']['book']] = x
    return list(last.values())

def rate(F, test): return sum(1 for x in F if test(x)) / len(F) if F else 0.0
def inside(x): return x['low'] <= x['actual'] <= x['high']
def within(d): return lambda x: abs(x['actual'] / x['expected'] - 1) <= d

def bills_above_ceiling(rows=None):
    """Past calls billed above the ceiling recomputed from today's rule (input estimate × 1.25, the kind's allowance)."""
    bad = []
    for c in (H.seed_rows() if rows is None else rows):
        if c['model'] != MODEL: continue
        mt = C.allowance(c['kind'], c.get('forms') or 0)
        if c['input_billed'] * PIN + c['output'] * POUT > c['input_est'] * PIN * 1.25 + mt * POUT: bad.append(c)
    return bad

def figure_held_out(rows=None):
    """Figure requests, each PDF held out in turn and predicted from the others. Not forward in time: only 6 PDFs exist, so no earlier
    set reaches the 12 calls from 6 PDFs a person's figure needs. The minimum is lowered here for that reason. [{…}], and how many got no figure."""
    rows = sorted((r for r in (H.seed_rows() if rows is None else rows) if r['model'] == MODEL and r['kind'] == 'figure'), key=lambda r: r['date'])
    out, above = [], 0
    for c in rows:
        m = H.learn([t for t in rows if t['book'] != c['book']], min_calls=5, min_books=3)
        if not m: continue
        if c['input_est'] > m['max_input']: above += 1; continue
        lo, md, hi = H.predict(m, c['input_est'], C.allowance('figure'))
        cost_in = c['input_est'] * m['input_ratio'] * PIN
        out.append({'row': c, 'expected': cost_in + md * POUT, 'low': cost_in + lo * POUT, 'high': cost_in + hi * POUT, 'actual': c['input_billed'] * PIN + c['output'] * POUT})
    return out, above

def report():
    F, above = forward(); N = newest(F)
    print(f'{len(F)} calls predicted forward in time, never from their own book · {above} left without a figure (input above the training calls)')
    print(f'in the range: {sum(map(inside, F))}/{len(F)} ({rate(F, inside):.0%}) · newest call per book: {sum(map(inside, N))}/{len(N)} ({rate(N, inside):.0%})')
    for d in (0.25, 0.5):
        print(f'within {d:.0%} of the bill: {rate(F, within(d)):.0%} of calls, {rate(N, within(d)):.0%} of newest-per-book')
    print('bias per prompt (median actual / expected):')
    by = collections.defaultdict(list)
    for x in F: by[x['row'].get('prompt') or 'not recorded'].append(x['actual'] / x['expected'])
    for k in sorted(by): print(f'  {k:22} {len(by[k]):4} calls  {H._median(by[k]):.2f}')
    print(f'past bills above their recomputed ceiling: {len(bills_above_ceiling())}')
    G, none = figure_held_out()
    print(f'figure requests, each PDF held out in turn (not forward in time, minimum lowered: too few PDFs yet): {len(G)} predicted, {none} left without a figure')
    print(f'  in the range: {sum(map(inside, G))}/{len(G)} ({rate(G, inside):.0%}) · within 25% of the bill: {rate(G, within(0.25)):.0%} · within 50%: {rate(G, within(0.5)):.0%}'
          f' · median actual/expected {H._median([x["actual"] / x["expected"] for x in G]):.2f}' if G else '  none')
    by_book = collections.defaultdict(list)
    for x in G: by_book[x['row']['book']].append(x['actual'] / x['expected'])
    print('  per PDF (median actual/expected):', ', '.join(f'{k} {H._median(v):.2f} ({len(v)})' for k, v in sorted(by_book.items())))

if __name__ == '__main__':
    report()
