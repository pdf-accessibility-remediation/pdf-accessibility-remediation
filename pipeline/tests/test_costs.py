"""test_costs.py: the expected cost and the money rules of #65 (costs in dollars and an expected cost): lib/costs.py's
allowance, wording and batch sums, lib/costhistory.py's fit, seed and ledger, and the committed seed itself. No model, no network.

    python -m pytest tests/test_costs.py -q
"""
import os, re, json, sys, multiprocessing
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import costs as C, costhistory as H
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import cost_backtest as BT

MODEL = 'anthropic/claude-sonnet-5.5'
def row(book, i=0, input_est=60000, output=9000, kind='workorder', date=None, billed=None, model=MODEL, **kw):
    return {'kind': kind, 'model': model, 'prompt': 'workorder_v10.md', 'input_est': input_est, 'input_billed': billed or input_est, 'output': output, 'images': 3,
            'forms': 0, 'date': date or f'2026-10-{1 + i % 28:02d}T10:00:{i % 60:02d}', 'book': book, **kw}

def history(calls=12, books=6, spread=True):
    """calls from books, with output rising with input and a little spread."""
    out = []
    for i in range(calls):
        k = i % books; s = 1 + 0.05 * (i % 3) if spread else 1
        out.append(row(f'b{k:02d}', i, input_est=40000 + 5000 * k + 100 * i, output=int((6000 + 800 * k) * s)))
    return out

P = dict(price_in=2e-6, price_out=10e-6)
def ask(hist, input_est=60000, max_tokens=48000, ceiling=0.61, kind='workorder', **kw):
    return H.expected([{'kind': kind, 'input_est': input_est, 'max_tokens': max_tokens}], MODEL, ceiling=ceiling, history=hist, **P, **kw)

# ------------------------------------------------------------------ the allowance, the limits
@pytest.mark.parametrize('forms,want', [(0, 48000), (711, 48000), (712, 48040), (2000, 106000)])
def test_the_work_order_allowance_is_todays_rule(forms, want):
    assert C.allowance('workorder', forms) == want

def test_a_figure_request_has_32000_and_later_kinds_are_named():
    assert C.allowance('figure') == 32000
    with pytest.raises(C.NotBuilt): C.allowance('ocr-draft')
    with pytest.raises(ValueError): C.allowance('nonsense')

def test_the_default_limits_are_in_one_place():
    assert C.DEFAULT_LIMITS == {'per_call_usd': 2.0, 'per_book_usd': 5.0, 'per_batch_usd': 10.0}

def test_the_retry_limits_are_the_persons_real_limits():
    assert C.retry_env(C.limits_of({'limits': {'per_call_usd': 3, 'per_book_usd': 7}})) == {'FIGURE_RETRY_MAX_USD': '3.00', 'FIGURE_RETRY_BOOK_MAX_USD': '7.00'}

# ------------------------------------------------------------------ the expected figure
def test_too_little_history_gives_no_figure():
    assert ask(history(11, 6))['none'] == 'too_few'
    assert ask(history(20, 5)) == {'none': 'too_few', 'kind': 'workorder', 'calls': 20, 'books': 5}

def test_the_minimum_of_12_calls_from_6_books_gives_a_figure():
    x = ask(history(12, 6)); assert x['usd'] > 0 and x['low'] <= x['usd'] <= x['high'] and x['basis'] == {'calls': 12, 'books': 6}

def test_a_request_larger_than_any_learned_still_gets_a_figure_and_says_so():
    h = history(30, 6); top = max(r['input_est'] for r in h)
    assert 'beyond' not in ask(h, input_est=top)
    x = ask(h, input_est=top + 1, ceiling=9); assert x['usd'] > 0 and x['beyond'] is True and 'none' not in x
    assert H.terminal_line(x).endswith('; larger than any request learned from, so it may read high')

def test_a_figure_for_a_much_larger_request_keeps_to_both_limits():
    h = history(30, 6)
    x = ask(h, input_est=5_000_000, max_tokens=48000, ceiling=11); assert x['usd'] <= 11 and x['high'] <= 11
    m = H.learn(sorted(h, key=lambda r: r['date'])); assert max(H.predict(m, 5_000_000, 48000)) == 48000

def test_the_note_for_a_larger_request_is_one_wording_for_a_pdf_and_a_batch():
    x = {'usd': 1.0, 'low': 0.8, 'high': 1.2, 'basis': {'calls': 80, 'books': 30}, 'beyond': True}
    assert H.beyond_note(x) in H.terminal_line(x) and H.beyond_note({'usd': 1.0}) == ''
    sh = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'batch_api.sh'), encoding='utf-8').read()
    assert 'costhistory.beyond_note(x)' in sh

def test_the_terminal_names_the_thinner_of_two_histories():
    wo, fig = history(40, 8), [dict(r, kind='figure') for r in history(19, 6)]
    q = [{'kind': 'workorder', 'input_est': 60000, 'max_tokens': 48000}, {'kind': 'figure', 'input_est': 60000, 'max_tokens': 32000}]
    assert H.expected(q, MODEL, ceiling=9, history=wo + fig, **P)['basis'] == {'calls': 19, 'books': 6}

def test_a_cut_off_in_the_folder_gives_no_figure():
    assert ask(history(30, 6), cut_off=True) == {'none': 'cut_off'}

def test_the_figure_never_passes_the_ceiling_or_the_allowance():
    x = ask(history(30, 6), ceiling=0.05); assert x['usd'] == 0.05 and x['high'] == 0.05 and x['low'] <= 0.05
    h = history(30, 6, spread=False); top = max(r['input_est'] for r in h)
    m = H.learn(sorted(h, key=lambda r: r['date']))
    assert max(H.predict(m, top, 100)) == 100
    assert ask(h, input_est=top, max_tokens=100, ceiling=9)['usd'] == pytest.approx(top * m['input_ratio'] * 2e-6 + 100 * 10e-6, abs=1e-4)

def test_a_multi_request_book_adds_its_requests_and_needs_both_kinds():
    wo, fig = history(30, 6), [dict(r, kind='figure') for r in history(30, 6)]
    q = [{'kind': 'workorder', 'input_est': 60000, 'max_tokens': 48000}, {'kind': 'figure', 'input_est': 60000, 'max_tokens': 32000}]
    both = H.expected(q, MODEL, ceiling=9, history=wo + fig, **P)
    assert both['usd'] == pytest.approx(2 * ask(wo, ceiling=9)['usd'], abs=1e-3)
    assert H.expected(q, MODEL, ceiling=9, history=wo, **P)['none'] == 'too_few'

def test_models_and_kinds_are_learned_apart():
    h = history(30, 6)
    assert H.expected([{'kind': 'workorder', 'input_est': 60000, 'max_tokens': 48000}], 'anthropic/other', ceiling=9, history=h, **P)['none'] == 'too_few'

def test_only_the_last_80_calls_are_learned_from():
    assert H.learn(sorted(history(200, 8), key=lambda r: r['date']))['calls'] == 80

def test_the_terminal_line_names_the_range_and_why_none():
    assert H.terminal_line({'usd': .31, 'low': .22, 'high': .43, 'basis': {'calls': 80, 'books': 29}}) == 'Expected Cost: $0.31 (usually $0.22–$0.43), from the last 80 calls (29 PDFs)'
    assert H.terminal_line({'none': 'too_few', 'calls': 5, 'books': 1}) == 'Expected Cost: Not Available Yet (5 past calls of this kind, from 1 PDF; needs 12 from 6)'

# ------------------------------------------------------------------ seed + ledger: each call once, each book once
def ledger(tmp_path, *rows, raw=''):
    p = tmp_path / '.cost-history.jsonl'; p.write_text(''.join(json.dumps(r) + '\n' for r in rows) + raw, encoding='utf-8'); return str(p)
def seed(tmp_path, *rows):
    p = tmp_path / 'seed.json'; p.write_text(json.dumps({'format': 'cost-seed/1', 'rows': list(rows)}), encoding='utf-8'); return str(p)

def test_a_call_in_both_seed_and_ledger_counts_once(tmp_path):
    """Rebuilding the seed after the ledger recorded a call must not double it: no book id is needed to see it is the same call."""
    a = row('b01', 1); got = H.rows(ledger(tmp_path, dict(a, book='ab12cd34ab12cd34', **{'pass': '1', 'attempt': 1})), seed(tmp_path, a))
    assert len(got) == 1

def test_a_book_in_both_counts_as_one_book_through_the_local_labels(tmp_path):
    a = row('b01', 1)
    new = dict(row('ab12cd34ab12cd34', 2, output=9100), **{'pass': '1', 'attempt': 1})
    L = ledger(tmp_path, new); S = seed(tmp_path, a)
    assert {r['book'] for r in H.rows(L, S)} == {'b01', 'ab12cd34ab12cd34'}      # no labels file (another computer): two
    (tmp_path / H.LABELS_NAME).write_text(json.dumps({'ab12cd34ab12cd34': 'b01'}))
    assert {r['book'] for r in H.rows(L, S)} == {'b01'} and len(H.rows(L, S)) == 2

def test_the_ledger_key_drops_a_duplicate_line(tmp_path):
    r = dict(row('x', 1), **{'pass': '2', 'attempt': 1})
    assert len(H.rows(ledger(tmp_path, r, r, dict(r, attempt=2, output=9001)), seed(tmp_path))) == 2

def test_a_malformed_or_half_written_line_is_skipped(tmp_path):
    r = row('x', 1)
    assert len(H.rows(ledger(tmp_path, r, raw='{"kind": "workorder", "mod\nnot json\n{}\n[1]\n'), seed(tmp_path))) == 1

def test_no_ledger_is_the_seed_alone(tmp_path):
    S = seed(tmp_path, row('b01', 1))
    assert len(H.rows(str(tmp_path / 'absent.jsonl'), S)) == 1 and len(H.rows('', S)) == 1

def seed_run(R, started):
    R.mkdir(parents=True); (R / '_intake').mkdir()
    (R / '_intake' / 'intake.json').write_text(json.dumps({'original': {'sha256': 'a' * 64}}))
    (R / 'run.json').write_text(json.dumps({'model': MODEL, 'started': started, 'usage': {'cost_usd': 1, 'prompt_tokens': 1234, 'completion_tokens': 567}, 'finish_reason': 'stop', 'estimate': {'input_tokens': 2000, 'images': 1}}))

def test_a_rebuilt_seed_takes_only_calls_in_the_seed_or_the_ledger(tmp_path):
    """review 08 L1: a folder with a paid-looking call and an original on record isn't proof the call was real."""
    import cost_seed
    seed_run(tmp_path / 'fake', '2026-11-09T10:00:00')
    rows, dropped, unproved = cost_seed.collect(str(tmp_path)); assert rows == [] and unproved == 1 and dropped == 0
    H.append({'kind': 'workorder', 'model': MODEL, 'prompt': 'p', 'input_est': 2000, 'input_billed': 1234, 'output': 567, 'images': 1, 'forms': 0, 'date': '2026-11-09T10:00:00', 'book': 'x', 'pass': '1', 'attempt': 1})
    rows, dropped, unproved = cost_seed.collect(str(tmp_path)); assert len(rows) == 1 and unproved == 0     # conftest's own ledger for this test

def test_a_rebuilt_seed_has_one_row_per_finished_call_like_the_ledger():
    """review 06 L3: a request's usage is the sum of its calls. A cut-off is left out; each call that finished is a row of its own."""
    import cost_seed
    U = lambda out: {'prompt_tokens': 100, 'completion_tokens': out}
    base = {'usage': {'cost_usd': 1, 'prompt_tokens': 200, 'completion_tokens': 99999}, 'finish_reason': None}
    run = {'model': MODEL, 'started': '2026-11-08T10:00:00', 'passes': [
               {'pass': '2', **base, 'calls': [{'finish_reason': 'length', 'usage': U(32000)}, {'finish_reason': 'stop', 'usage': U(40000), 'doubled': True}]},
               {'pass': '3', **base, 'calls': [{'finish_reason': 'stop', 'usage': U(500)}, {'finish_reason': 'stop', 'usage': U(600)}]},
               {'pass': '4', **base, 'calls': [{'finish_reason': 'length', 'usage': U(32000)}]},
               {'pass': '5', **base, 'finish_reason': 'stop', 'calls': [{'finish_reason': 'stop'}]}],
           'estimate': {'passes': [{'pass': str(i), 'input_tokens': 5000, 'images': 3} for i in range(2, 6)]}}
    rows = cost_seed.calls_of(run, 'x')
    assert [r['output'] for r in rows] == [40000, 500, 600, 99999] and all(r['input_est'] == 5000 and r['kind'] == 'figure' for r in rows)   # the last: an older record, no per-call usage

def test_the_committed_seed_alone_gives_a_figure():
    x = H.expected([{'kind': 'workorder', 'input_est': 60000, 'max_tokens': 48000}], MODEL, ceiling=0.61, history=H.seed_rows(), **P)
    assert 0.05 < x['usd'] < 0.61 and x['basis']['calls'] == 80

def test_append_makes_the_folder_and_writes_one_line(tmp_path):
    p = tmp_path / 'new' / 'x.jsonl'
    assert H.append({'a': 1}, str(p)) and H.append({'a': 2}, str(p)) and p.read_text().count('\n') == 2

def test_append_never_raises(tmp_path, capsys):
    (tmp_path / 'file').write_text('x'); H._warned = False
    assert H.append({'a': 1}, str(tmp_path / 'file' / 'y.jsonl')) is False and H.append({'a': 2}, str(tmp_path / 'file' / 'y.jsonl')) is False
    assert capsys.readouterr().err.count('could not be written') == 1
    H._warned = False

def _writer(a):
    for i in range(200): H.append({'w': a[1], 'i': i, 'pad': 'x' * 200}, a[0])

def test_parallel_appends_do_not_mix_lines(tmp_path):
    p = str(tmp_path / 'p.jsonl')
    with multiprocessing.get_context('fork').Pool(4) as pool: pool.map(_writer, [(p, n) for n in range(4)])
    lines = open(p).read().splitlines(); assert len(lines) == 800 and all(json.loads(l)['pad'] for l in lines)

def test_the_ledger_path_order():
    assert H.ledger_path({'COST_HISTORY': '/a/b', 'RUNS_DIR': '/r'}) == '/a/b' and H.ledger_path({'RUNS_DIR': '/r'}) == '/r/.cost-history.jsonl' and H.ledger_path({}) is None

def test_two_untagged_books_with_the_same_digest_name_get_different_ids(tmp_path):
    ids = []
    for n, sha in (('a', 'a' * 64), ('b', 'b' * 64)):
        R = tmp_path / n / '_intake'; R.mkdir(parents=True); (R / 'intake.json').write_text(json.dumps({'original': {'sha256': sha}}))
        ids.append(H.book_id(str(R.parent), {'source': {'file': 'intake.pdf', 'sha256': 'c' * 64}}))
    assert ids[0] != ids[1] and H.book_id(str(tmp_path / 'none'), {'source': {'sha256': 'c' * 64}}) not in ids

# ------------------------------------------------------------------ the committed seed
LABEL = re.compile(r'^b\d{2,}$')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')
def test_the_committed_seed_holds_only_the_listed_fields():
    d = json.load(open(H.SEED, encoding='utf-8'))
    assert set(d) == {'format', 'rows'} and len(d['rows']) > 200
    for r in d['rows']:
        assert set(r) == set(H.SEED_KEYS)
        assert r['kind'] in ('workorder', 'figure') and re.fullmatch(r'[a-z0-9-]+/[a-z0-9.\-]+', r['model'])
        assert re.fullmatch(r'(workorder_v\d+|figures_v\d+)\.md', r['prompt']) and DATE.match(r['date']) and LABEL.match(r['book'])
        assert all(isinstance(r[k], int) and not isinstance(r[k], bool) and r[k] >= 0 for k in ('input_est', 'input_billed', 'output', 'images', 'forms'))

# ------------------------------------------------------------------ the backtest, on the committed seed
def test_the_backtest_holds_forward_in_time():
    F = BT.forward(); N = BT.newest(F)
    assert len(F) >= 200 and BT.rate(F, BT.inside) >= 0.80 and BT.rate(N, BT.inside) >= 0.80
    assert BT.rate(F, BT.within(0.25)) >= 0.80 and BT.rate(N, BT.within(0.25)) >= 0.70 and BT.rate(F, BT.within(0.5)) >= 0.95
    assert all(x['expected'] > 0 for x in F)

def test_nothing_is_left_out_of_the_backtest_for_its_size():
    F = BT.forward(); big = [x for x in F if x['beyond']]
    assert big and BT.rate(big, BT.inside) >= 0.7 and all(x['ratio'] > 1 for x in big)
    assert len(BT.figure_held_out()) == len([x for x in H.seed_rows() if x['kind'] == 'figure' and x['model'] == MODEL])

def test_the_seed_holds_the_figure_request_baseline():
    r = [x for x in H.seed_rows() if x['kind'] == 'figure' and x['model'] == MODEL]
    assert len(r) >= H.MIN_CALLS and len({x['book'] for x in r}) >= H.MIN_BOOKS

def test_figure_requests_hold_out_each_pdf():
    G = BT.figure_held_out()
    assert len(G) == len([x for x in H.seed_rows() if x['kind'] == 'figure' and x['model'] == MODEL]) and BT.rate(G, BT.inside) >= 0.7

def test_no_past_bill_is_above_its_recomputed_ceiling():
    assert BT.bills_above_ceiling() == []

# ------------------------------------------------------------------ the estimate on a run folder
def folder(t, name='r', worst=0.62, extra=None, attempts=None):
    R = t / name; R.mkdir(parents=True, exist_ok=True)
    (R / 'run.json').write_text(json.dumps({'model': MODEL, 'price_source': 'openrouter /models', 'prompt_sha256': 'p' * 16,
                                            'estimate': {'input_tokens': 20000, 'images': 2, 'worst_case_total_usd': worst, 'credit_available_usd': 20.0, **(extra or {})}}))
    if attempts is not None: (R / 'attempts.json').write_text(json.dumps(attempts))
    return R

def test_expected_stays_out_of_the_fingerprint(tmp_path):
    a = C.estimate(str(folder(tmp_path, 'a')));
    (tmp_path / 'a' / 'run.json').write_text(json.dumps({**json.load(open(tmp_path / 'a' / 'run.json')),
        'estimate': {**json.load(open(tmp_path / 'a' / 'run.json'))['estimate'], 'expected': {'usd': .3, 'low': .2, 'high': .4}}}))
    b = C.estimate(str(tmp_path / 'a')); assert b['fingerprint'] == a['fingerprint'] and b['expected']['usd'] == .3

def test_an_estimate_made_before_this_change_has_no_expected(tmp_path):
    assert C.estimate(str(folder(tmp_path)))['expected'] is None

def test_not_available_is_kept_as_it_is(tmp_path):
    assert C.estimate(str(folder(tmp_path, extra={'expected': {'none': 'too_few'}})))['expected'] == {'none': 'too_few'}

@pytest.mark.parametrize('kw,code,words', [
    ({'worst': 2.4, 'extra': {}}, 'per_call', 'This run could cost up to $2.40, more than the limit of $2.00 per AI request.'),
    ({'worst': 5.9, 'extra': {'passes': [{'pass': '1', 'worst_case_usd': 0.9}], 'book_cap_usd': 5}}, 'per_book', 'This PDF could cost up to $5.90, more than the limit of $5.00 per PDF.'),
    ({'worst': 4.6, 'extra': {'passes': [{'pass': '1', 'worst_case_usd': 0.9}], 'book_cap_usd': 5, 'spent_before_usd': 0.6}}, 'per_book', 'This PDF could cost up to $5.20, including $0.60 already spent, more than the limit of $5.00 per PDF.'),
    ({'worst': 0.67, 'extra': {'credit_available_usd': 0.4}}, 'credit', 'This run could cost up to $0.67, more than the $0.40 of credit left.')])
def test_refusals_name_what_it_could_cost_and_the_limit(tmp_path, kw, code, words):
    b = C.estimate(str(folder(tmp_path, **kw)))['blocked']; assert b['code'] == code and b['words'] == words

# ------------------------------------------------------------------ after a run: one wording
@pytest.mark.parametrize('a,want', [
    ({'usd': .27, 'expected_usd': .31, 'estimate_usd': .67}, '$0.27 (expected $0.31, max estimated $0.67)'),
    ({'usd': .27, 'estimate_usd': .61}, '$0.27 (max estimated $0.61)'),
    ({'usd': .6, 'earlier_usd': .29, 'expected_usd': .31, 'estimate_usd': .67}, '$0.60 ($0.31 + $0.29 for previous attempts) · Max Estimated Cost: $0.67, not including previous attempts'),
    ({'usd': 3.4, 'retry_usd': .5, 'estimate_usd': 3.13}, '$3.40 ($2.90 + $0.50 to retry an answer that was cut off) · Max Estimated Cost: $3.13, not including the retry'),
    ({'usd': 3.4, 'retry_usd': .5, 'expected_usd': .31, 'estimate_usd': 3.13}, '$3.40 ($2.90 + $0.50 to retry an answer that was cut off) · Expected: $0.31 · Max Estimated Cost: $3.13, not including the retry'),
    ({'usd': 3.7, 'earlier_usd': .3, 'retry_usd': .5, 'expected_usd': .31, 'estimate_usd': 3.13}, '$3.70 ($2.90 + $0.30 for previous attempts + $0.50 to retry an answer that was cut off) · Max Estimated Cost: $3.13, not including previous attempts or the retry'),
    ({'usd': 3.8, 'earlier_usd': 3.8, 'estimate_usd': .67}, '$3.80 ($3.80 for previous attempts) · Max Estimated Cost: $0.67, not including previous attempts'),
    ({'usd': .27}, '$0.27')])
def test_the_after_run_words(a, want):
    assert C.cost_words(a) == want

def test_so_far_comes_right_after_the_amount():
    assert C.cost_words({'usd': 1.2, 'expected_usd': 4.1, 'estimate_usd': 8.8}, so_far=True) == '$1.20 so far (expected $4.10, max estimated $8.80)'

def test_the_addition_never_loses_a_cent_to_rounding():
    s = C.cost_words({'usd': 0.605, 'earlier_usd': 0.295, 'estimate_usd': 1}); m = re.match(r'\$([\d.]+) \(\$([\d.]+) \+ \$([\d.]+) ', s)
    assert float(m[1]) == pytest.approx(float(m[2]) + float(m[3]))

def test_actual_reports_the_retry_and_the_expected_figure_shown(tmp_path):
    R = folder(tmp_path, extra={'expected': {'usd': .31}})
    run = json.load(open(R / 'run.json')); run.update(usage={'cost_usd': 3.4}, figure_passes={'cut_off_retries': [{'pass': '2', 'max_tokens': 64000, 'cost_usd': .5, 'outcome': 'done'}]})
    (R / 'run.json').write_text(json.dumps(run))
    a = C.actual(str(R)); assert a['retry_usd'] == .5 and a['expected_usd'] == .31 and C.after_line(str(R)).startswith('AI Cost: $3.40 ($2.90 + $0.50 to retry')

# ------------------------------------------------------------------ the batch: spent, expected
def test_batch_spent_counts_every_folder_and_the_trash(tmp_path):
    a = folder(tmp_path, 'a', attempts=[{'cost_usd': .2}])                       # to send, with a paid previous attempt
    b = folder(tmp_path, 'b'); (b / 'workorder.ai.json').write_text('{}')
    run = json.load(open(b / 'run.json')); run['usage'] = {'cost_usd': .3}; (b / 'run.json').write_text(json.dumps(run))    # waiting for review
    c = tmp_path / 'c'; c.mkdir(); (c / 'record.json').write_text(json.dumps({'run': {'usage': {'cost_usd': .4}}, 'cost_total_usd': .4, 'document': {}}))   # finished
    (tmp_path / '.hidden').mkdir(); (tmp_path / 'trashed.json').write_text(json.dumps([{'name': 'd', 'cost_usd': .1}]))
    assert C.batch_spent(str(tmp_path)) == {'usd': pytest.approx(1.0), 'earlier_usd': pytest.approx(.2), 'retry_usd': 0, 'trashed_usd': .1}
    t = C.batch([str(a)], limit=1.5, folder=str(tmp_path))
    assert t['spent_usd'] == pytest.approx(1.0) and t['ceiling_usd'] == .62 and t['could_cost_usd'] == pytest.approx(1.62) and t['fits']['batch'] is False
    assert t['bounds']['BATCH_MAX_USD'] == 1.5
    t = C.batch([str(a)], limit=9, folder=str(tmp_path)); assert t['fits']['batch'] and t['bounds']['BATCH_MAX_USD'] == pytest.approx(1.63)

def test_the_batch_refusal_says_when_spent_money_is_part_of_it(tmp_path):
    a = folder(tmp_path, 'a', worst=9.0, attempts=[{'cost_usd': 1.2}])
    t = C.batch([str(a)], limit=10, folder=str(tmp_path))
    assert C.batch_over_words(t) == 'This batch could cost up to $10.20, including $1.20 already spent, more than the limit of $10.00 per batch.'
    t = C.batch([str(folder(tmp_path / 'x', 'a', worst=33.1))], limit=10)
    assert C.batch_over_words(t) == 'This batch could cost up to $33.10, more than the limit of $10.00 per batch.'

def test_a_batch_adds_up_its_expected_figures_and_counts_the_rest(tmp_path):
    a = folder(tmp_path, 'a', extra={'expected': {'usd': .3, 'low': .2, 'high': .4}}); b = folder(tmp_path, 'b', extra={'expected': {'usd': .4, 'low': .3, 'high': .5}})
    c = folder(tmp_path, 'c', extra={'expected': {'none': 'too_few'}})
    assert C.batch([str(a), str(b)])['expected'] == {'usd': .7, 'books': 2, 'of': 2}
    assert C.batch([str(a), str(b), str(c)])['expected'] == {'usd': .7, 'books': 2, 'of': 3}
    assert C.batch([str(c)])['expected'] == {'usd': None, 'books': 0, 'of': 1}
    assert C.batch([str(folder(tmp_path, 'old'))])['expected'] is None           # no estimate has the key: no "Expected Cost" line

def test_fit_n_counts_how_many_of_these_would_fit(tmp_path):
    Rs = [str(folder(tmp_path, n, worst=w)) for n, w in (('a', 4.0), ('b', 3.0), ('c', 5.0), ('d', 3.5))]
    assert C.batch(Rs, limit=10)['fit_n'] == 2

@pytest.mark.parametrize('n,want', [
    (0, 'The app administrator can raise the limit or you can start a batch with fewer PDFs.'),
    (1, 'The app administrator can raise the limit or you can start a batch with fewer PDFs. Only the smallest PDF in this batch would fit within the current limit.'),
    (2, 'The app administrator can raise the limit or you can start a batch with fewer PDFs. Only the two smallest PDFs in this batch would fit within the current limit.'),
    (9, 'The app administrator can raise the limit or you can start a batch with fewer PDFs. Only the nine smallest PDFs in this batch would fit within the current limit.'),
    (10, 'The app administrator can raise the limit or you can start a batch with fewer PDFs. Only the 10 smallest PDFs in this batch would fit within the current limit.')])
def test_the_advice_on_a_batch_over_its_limit(n, want):
    assert C.batch_advice(n) == want

@pytest.mark.parametrize('a', [{'usd': 0, 'earlier_usd': .3}, {'usd': .2, 'earlier_usd': .3, 'retry_usd': .3, 'estimate_usd': 1}, {'usd': .1, 'retry_usd': .5}])
def test_no_part_of_the_addition_is_ever_negative(a):
    assert '-' not in C.cost_words(a).replace(' - ', '') and '$-' not in C.cost_words(a)

def spent_money(R, usd, retry=0.0, **extra):
    R.mkdir(parents=True, exist_ok=True)
    (R / 'run.json').write_text(json.dumps({'usage': {'cost_usd': usd}, 'figure_passes': {'cut_off_retries': [{'pass': '2', 'cost_usd': retry}] if retry else []}, **extra}))

def test_a_batch_sent_again_keeps_an_earlier_retry_with_the_previous_money(tmp_path):
    """shown.retry_usd is what was retried before this send: only what this send retried is named as a retry."""
    spent_money(tmp_path / 'a', 1.0, retry=0.2); spent_money(tmp_path / 'b', 0.9, retry=0.25)
    shown = {'ceiling_usd': 2.0, 'spent_usd': 1.0, 'retry_usd': 0.2}
    assert C.shown_words(str(tmp_path), shown) == '$1.90 ($0.65 + $1.00 for previous attempts + $0.25 to retry an answer that was cut off) · Max Estimated Cost: $2.00, not including previous attempts or the retry'

def test_a_reply_read_again_in_its_own_folder_stays_spent_before_and_after(tmp_path):
    """review 04 H1: the money is the same on both sides of the reuse, and the total never goes negative."""
    R = tmp_path / 'a'; spent_money(R, 0.3); shown = {'ceiling_usd': 0.67, 'spent_usd': C.batch_spent(str(tmp_path))['usd'], 'retry_usd': 0}
    assert shown['spent_usd'] == 0.3
    spent_money(R, 0.3, response_from=str(R / 'response.json'), own_reply=True)
    assert C.batch_spent(str(tmp_path))['usd'] == 0.3 and C.shown_words(str(tmp_path), shown) == '$0.30 ($0.30 for previous attempts) · Max Estimated Cost: $0.67, not including previous attempts'

def test_a_finished_run_read_again_in_its_own_folder_counts_its_usage(tmp_path):
    (tmp_path / 'record.json').write_text(json.dumps({'run': {'usage': {'cost_usd': 0.3}, 'response_from': 'x/response.json', 'own_reply': True, 'estimate': {'worst_case_total_usd': 0.67}}, 'cost_total_usd': 0.3, 'document': {}, 'earlier_attempts': []}))
    a = C.actual(str(tmp_path)); assert a['usd'] == 0.3 and a['reused'] is False and a['finished']

def test_a_reply_from_elsewhere_still_costs_nothing_here(tmp_path):
    (tmp_path / 'record.json').write_text(json.dumps({'run': {'usage': {'cost_usd': 0.3}, 'response_from': 'x/response.json'}, 'cost_total_usd': 0, 'document': {}, 'earlier_attempts': []}))
    a = C.actual(str(tmp_path)); assert a['usd'] == 0 and a['reused'] is True

def test_a_pdf_dragged_back_from_the_trash_counts_once(tmp_path):
    spent_money(tmp_path / 'back', 0.3); (tmp_path / 'trashed.json').write_text(json.dumps([{'name': 'back', 'cost_usd': 0.3}, {'name': 'gone', 'cost_usd': 0.1}]))
    assert C.batch_spent(str(tmp_path)) == {'usd': pytest.approx(0.4), 'earlier_usd': 0, 'retry_usd': 0, 'trashed_usd': 0.1}
