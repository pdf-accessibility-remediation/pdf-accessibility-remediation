"""test_page_costs.py: what page readings (#49, read_pages.py) cost and how they are shown, under #65 (costs in dollars and an
expected cost): paid money counted at every stage and once, the per-PDF limit on a later attempt, a page reused at no cost, the
"page" history behind the Expected Cost, and "Not Available Yet" until that history exists.

    python -m pytest tests/test_page_costs.py -q

Synthetic files only. read_pages.py runs in this process against a fake OpenRouter (urlopen replaced, the key a dummy).
"""
import json, os, runpy, sys, urllib.request
import pytest
from PIL import Image

from test_figure_requests_run import book, decide, small_audit, HERE   # noqa: F401  (book is a fixture)
from test_decide_allowance import fake, load, MODEL
sys.path.insert(0, HERE)
from lib import costs as C, costhistory as H

# ------------------------------------------------------------------ helpers
def w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, 'w', encoding='utf-8')); return p

def paused(R, usage=0.30, pages=0.20):
    """A run stopped for review after its page readings: run.json and page_reads_run.json, no record yet."""
    w(R / 'run.json', {'model': MODEL, 'usage': {'cost_usd': usage}, 'estimate': {'worst_case_total_usd': 0.60, 'expected': {'usd': 0.25}}})
    w(R / 'page_reads_run.json', {'cost_usd': pages, 'estimate': {'to_read': 2, 'worst_case_usd': 0.40, 'expected': {'none': 'too_few', 'kind': 'page', 'calls': 0, 'books': 0}},
                                  'pages': [{'page': 1, 'cost_usd': 0.1}, {'page': 2, 'cost_usd': 0.1}]})
    return R

def finished(R, total=0.50, usage=0.30, pages=0.20, run=None):
    w(R / 'record.json', {'run': {'model': MODEL, 'usage': {'cost_usd': usage}, **(run or {})}, 'cost_total_usd': total, 'earlier_attempts': [], 'document': {'pages': 10},
                          'page_reads': {'cost_usd': pages, 'pages': [{'page': 1, 'cost_usd': 0.1}, {'page': 2, 'cost_usd': 0.1}]}})
    return R

def audit_with_pages(tmp_path, n=2):
    A = tmp_path / '_audit'; (A / 'page_reads').mkdir(parents=True)
    pages = []
    for i in range(1, n + 1):
        Image.new('RGB', (200, 300), (i, 10, 10)).save(A / 'page_reads' / f'page_{i:04d}.png')
        pages.append({'page': i, 'label': None, 'share': 0.9, 'image': f'page_reads/page_{i:04d}.png'})
    w(A / 'page_reads.json', {'pages': pages}); w(A / 'digest.json', {'source': {'sha256': 'abc'}})
    return A

LAST = {}
def read(A, R, monkeypatch, *args, finish=lambda page: 'stop', cost=0.01, ledger=None):
    """read_pages.py as run_api.sh calls it. Returns the bodies of the AI requests it made."""
    calls = []
    def reply(body, n): return {'choices': [{'message': {'content': 'He mau hua ʻōlelo.'}, 'finish_reason': finish(n)}], 'usage': {'prompt_tokens': 1000, 'completion_tokens': 2500, 'cost': cost}}
    monkeypatch.setattr(urllib.request, 'urlopen', fake(calls, reply))
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
    if ledger is not None: monkeypatch.setenv('COST_HISTORY', str(ledger))
    monkeypatch.setattr(sys, 'argv', ['read_pages.py', str(A), str(R), *args]); monkeypatch.chdir(HERE)
    R.mkdir(parents=True, exist_ok=True)
    LAST['exit'] = None
    try: runpy.run_path(os.path.join(HERE, 'read_pages.py'), run_name='__main__')
    except SystemExit as e: LAST['exit'] = e.code
    return calls

def ledger_rows(p): return [json.loads(l) for l in open(p, encoding='utf-8')] if os.path.exists(p) else []

def page_history(p, calls=12, books=6):
    with open(p, 'w', encoding='utf-8') as f:
        for i in range(calls):
            f.write(json.dumps({'kind': 'page', 'model': MODEL, 'prompt': 'page_reading_v1.md', 'input_est': 1500 + i, 'input_billed': 1500 + i, 'output': 2500 + i, 'images': 1, 'forms': 0,
                                'date': f'2026-11-01T10:00:{i:02d}', 'book': f'b{i % books}', 'pass': str(i), 'attempt': 1}) + '\n')

# ------------------------------------------------------------------ the money
def test_paid_pages_count_while_a_run_waits_for_review(tmp_path):
    a = C.actual(str(paused(tmp_path / 'r')))
    assert a['usd'] == 0.5 and not a['finished'] and a['earlier_usd'] == 0

def test_paid_pages_count_once_after_the_record_is_written(tmp_path):
    R = tmp_path / 'r'; finished(R)
    assert C.actual(str(R))['usd'] == 0.5
    w(R / 'page_reads_run.json', {'cost_usd': 0.20})          # KEEP=1 leaves the working file beside the record: still once
    assert C.actual(str(R))['usd'] == 0.5 and C.actual(str(R))['finished']

def test_a_reapply_record_that_lost_the_pages_still_counts_them(tmp_path):
    R = tmp_path / 'r'; finished(R, total=0.30)
    assert C.actual(str(R))['usd'] == 0.5

def test_a_reapply_keeps_the_pages_in_the_records_total():
    assert 'cost_pages = 0 if prev' not in open(os.path.join(HERE, 'report.py'), encoding='utf-8').read()

def test_the_batch_counts_pages_at_every_stage(tmp_path):
    B = tmp_path / 'batch'; paused(B / 'waiting'); finished(B / 'done')
    assert C.batch_spent(str(B))['usd'] == 1.0
    assert C.batch_spent(str(B))['usd'] == round(C.actual(str(B / 'waiting'))['usd'] + C.actual(str(B / 'done'))['usd'], 6)

def test_the_run_page_words_show_what_was_agreed_for_pages_too(tmp_path):
    a = C.actual(str(paused(tmp_path / 'r')))
    assert a['estimate_usd'] == 1.0 and a['expected_usd'] is None        # "Not Available Yet" was shown, so no figure afterwards
    assert C.cost_words(a) == '$0.50 (max estimated $1.00)'

def test_a_saved_reply_with_no_pages_is_still_reused(tmp_path):
    R = tmp_path / 'r'; w(R / 'run.json', {'response_from': '/x/response.json', 'usage': {'cost_usd': 0.3}})
    a = C.actual(str(R)); assert a['usd'] == 0 and a['reused']

def test_pages_paid_in_this_folder_are_not_a_saved_replys_nothing(tmp_path):
    R = tmp_path / 'r'; w(R / 'run.json', {'response_from': '/x/response.json', 'usage': {'cost_usd': 0.3}}); w(R / 'page_reads_run.json', {'cost_usd': 0.2})
    a = C.actual(str(R)); assert a['usd'] == 0.2 and not a['reused']

def test_a_later_attempt_counts_the_pages_toward_the_pdfs_limit(book, tmp_path):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; w(R / 'page_reads_run.json', {'cost_usd': 0.25})
    assert decide(A, R, '--dry-run').returncode == 0
    assert load(R / 'run.json')['estimate']['spent_before_usd'] == 0.25

def test_an_estimate_with_no_stored_sum_counts_the_pages_too(tmp_path):
    R = tmp_path / 'r'; w(R / '_audit/digest.json', {}); (R / 'request.json').write_text('{}')
    w(R / 'run.json', {'model': MODEL, 'price_source': 'openrouter /models', 'estimate': {'worst_case_total_usd': 0.6, 'input_tokens': 1, 'images': 0}})
    w(R / 'page_reads_run.json', {'cost_usd': 0.25})
    assert C.estimate(str(R))['spent_before_usd'] == 0.25

# ------------------------------------------------------------------ read_pages.py
def test_a_page_read_before_is_not_paid_or_counted_twice(tmp_path, monkeypatch):
    A, R, L = audit_with_pages(tmp_path), tmp_path / 'r', tmp_path / 'ledger.jsonl'
    assert len(read(A, R, monkeypatch, ledger=L, finish=lambda n: 'length' if n == 2 else 'stop')) == 2      # page 2 is cut off: paid, not used
    assert load(R / 'page_reads_run.json')['cost_usd'] == 0.02
    assert len(read(A, R, monkeypatch, ledger=L)) == 1                                                       # page 2 read again
    assert load(R / 'page_reads_run.json')['cost_usd'] == 0.03
    assert len(read(A, R, monkeypatch, ledger=L)) == 0                                                       # all reused: the cut-off's charge is still there
    assert load(R / 'page_reads_run.json')['cost_usd'] == 0.03 and C.pages_paid(str(R)) == 0.03

def test_a_finished_page_teaches_and_a_cut_off_or_reused_one_does_not(tmp_path, monkeypatch):
    A, R, L = audit_with_pages(tmp_path), tmp_path / 'r', tmp_path / 'ledger.jsonl'
    read(A, R, monkeypatch, ledger=L, finish=lambda n: 'length' if n == 2 else 'stop')
    rows = ledger_rows(L); assert [(r['kind'], r['pass'], r['images']) for r in rows] == [('page', '1', 1)] and rows[0]['output'] == 2500 and H._good(rows[0])
    read(A, R, monkeypatch, ledger=L); assert [r['pass'] for r in ledger_rows(L)] == ['1', '2']
    read(A, R, monkeypatch, ledger=L); assert len(ledger_rows(L)) == 2

def test_the_page_history_does_not_touch_the_other_kinds(tmp_path):
    L = tmp_path / 'ledger.jsonl'; page_history(L)
    rows = H.rows(str(L), seed=str(tmp_path / 'no-seed.json'))
    assert H.expected([{'kind': 'workorder', 'input_est': 20000, 'max_tokens': 48000}], MODEL, 2e-6, 1e-5, 1.0, history=rows)['none'] == 'too_few'

def test_a_page_and_a_work_order_started_in_the_same_second_both_count(tmp_path):
    L = tmp_path / 'ledger.jsonl'
    same = {'model': MODEL, 'input_est': 20000, 'input_billed': 20000, 'output': 3000, 'images': 1, 'forms': 0,
            'date': '2026-11-01T10:00:00', 'book': 'b1', 'pass': '1', 'attempt': 1}
    with open(L, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'kind': 'workorder', 'prompt': 'workorder_v10.md', **same}) + '\n')
        f.write(json.dumps({'kind': 'page', 'prompt': 'page_reading_v1.md', **same}) + '\n')
    rows = H.rows(str(L), seed=str(tmp_path / 'no-seed.json'))
    assert sorted(r['kind'] for r in rows) == ['page', 'workorder']

def test_no_history_means_not_available_yet(tmp_path, monkeypatch):
    A, R, L = audit_with_pages(tmp_path), tmp_path / 'r', tmp_path / 'ledger.jsonl'
    assert read(A, R, monkeypatch, '--dry-run', ledger=L) == []
    e = load(R / 'page_reads_estimate.json')['expected']
    assert e == {'none': 'too_few', 'kind': 'page', 'calls': 0, 'books': 0}

def test_enough_history_gives_a_figure(tmp_path, monkeypatch):
    A, R, L = audit_with_pages(tmp_path), tmp_path / 'r', tmp_path / 'ledger.jsonl'; page_history(L)
    read(A, R, monkeypatch, '--dry-run', ledger=L)
    e = load(R / 'page_reads_estimate.json'); assert e['expected']['usd'] > 0 and e['expected']['usd'] <= e['worst_case_usd'] and e['expected']['basis'] == {'calls': 12, 'books': 6}

def test_a_cut_off_page_in_the_folder_means_no_figure(tmp_path, monkeypatch):
    A, R, L = audit_with_pages(tmp_path), tmp_path / 'r', tmp_path / 'ledger.jsonl'; page_history(L)
    read(A, R, monkeypatch, ledger=L, finish=lambda n: 'length' if n == 2 else 'stop')
    read(A, R, monkeypatch, '--dry-run', ledger=L)
    assert load(R / 'page_reads_estimate.json')['expected'] == {'none': 'cut_off'}

def test_the_terminal_says_ai_request_and_limit(tmp_path, monkeypatch, capsys):
    A, R, L = audit_with_pages(tmp_path), tmp_path / 'r', tmp_path / 'ledger.jsonl'
    read(A, R, monkeypatch, '--dry-run', ledger=L); out = capsys.readouterr().out
    assert 'Expected Cost: Not Available Yet (0 past page readings, from 0 PDFs; needs 12 from 6)' in out and 'Max Estimated Cost: $' in out
    assert not any(w_ in out for w_ in ('worst case', ' cap ', ' call'))
    read(A, R, monkeypatch, '--max-usd', '0.0001', ledger=L)
    assert LAST['exit'].startswith('refusing before any AI request: the page readings could cost up to $') and 'more than the limit of $0.00. To run it, raise the limit for this run: PAGE_READS_MAX_USD=' in LAST['exit']

# ------------------------------------------------------------------ the figure shown
X = {'usd': 0.30, 'low': 0.20, 'high': 0.45, 'basis': {'calls': 80, 'books': 29}}
P = {'usd': 0.10, 'low': 0.08, 'high': 0.15, 'basis': {'calls': 12, 'books': 6}}

def test_with_pages_adds_both_and_names_the_thinner_history():
    assert H.with_pages(X, {'to_read': 3, 'expected': P}) == {'usd': 0.4, 'low': 0.28, 'high': 0.6, 'basis': {'calls': 12, 'books': 6}}

@pytest.mark.parametrize('pr', [None, {}, {'to_read': 0, 'expected': {'none': 'too_few'}}])
def test_with_no_pages_to_read_the_figure_is_unchanged(pr):
    assert H.with_pages(X, pr) == X

def test_pages_without_a_figure_mean_no_figure():
    why = {'none': 'too_few', 'kind': 'page', 'calls': 3, 'books': 1}
    assert H.with_pages(X, {'to_read': 3, 'expected': why}) == why
    assert H.with_pages(X, {'to_read': 3})['none'] == 'no_page_figure'
    assert H.with_pages({'none': 'cut_off'}, {'to_read': 3, 'expected': P}) == {'none': 'cut_off'}

def test_the_terminal_names_page_readings():
    assert H.terminal_line({'none': 'too_few', 'kind': 'page', 'calls': 1, 'books': 1}) == 'Expected Cost: Not Available Yet (1 past page reading, from 1 PDF; needs 12 from 6)'
    assert H.terminal_line({'none': 'no_page_figure'}) == 'Expected Cost: Not Available Yet'

def run_with_pages(R, expected, page_expected, **pr):
    w(R / '_audit/digest.json', {}); (R / 'request.json').write_text('{}')
    w(R / 'run.json', {'model': MODEL, 'prompt_sha256': 'p', 'price_source': 'openrouter /models',
                       'estimate': {'worst_case_total_usd': 0.60, 'input_tokens': 20000, 'images': 0, 'book_cap_usd': 5.0, 'credit_available_usd': 9.0, 'expected': expected}})
    w(R / 'page_reads_estimate.json', {'model': MODEL, 'to_read': 5, 'worst_case_usd': 0.40, 'per_page_worst_usd': 0.08, **({'expected': page_expected} if page_expected else {}), **pr})
    return R

def test_a_pdf_with_pages_to_read_shows_not_available_yet(tmp_path):
    e = C.estimate(str(run_with_pages(tmp_path / 'r', X, {'none': 'too_few', 'kind': 'page', 'calls': 0, 'books': 0})))
    assert e['expected']['none'] == 'too_few' and e['ceiling_usd'] == 1.0 and e['requests'] == 6      # the maximum still includes them

def test_with_history_the_expected_figure_includes_the_pages(tmp_path):
    e = C.estimate(str(run_with_pages(tmp_path / 'r', X, P)))
    assert e['expected']['usd'] == 0.4 and e['ceiling_usd'] == 1.0

def test_the_page_figure_stays_out_of_the_fingerprint(tmp_path):
    a = C.estimate(str(run_with_pages(tmp_path / 'a', X, P)))['fingerprint']
    assert a == C.estimate(str(run_with_pages(tmp_path / 'a', X, {'none': 'too_few', 'kind': 'page', 'calls': 0, 'books': 0})))['fingerprint']

def test_a_batch_with_a_pdf_lacking_a_figure_says_so(tmp_path):
    a = run_with_pages(tmp_path / 'a', X, P); b = run_with_pages(tmp_path / 'b', X, {'none': 'too_few', 'kind': 'page', 'calls': 0, 'books': 0})
    t = C.batch([str(a), str(b)])
    assert t['expected'] == {'usd': 0.4, 'books': 1, 'of': 2} and t['ceiling_usd'] == 2.0 and t['bounds']['PAGE_READS_MAX_USD'] == 0.41

def test_decides_terminal_lines_include_the_pages(book, tmp_path):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    w(R / 'page_reads_estimate.json', {'model': MODEL, 'to_read': 5, 'worst_case_usd': 0.40, 'expected': {'none': 'too_few', 'kind': 'page', 'calls': 0, 'books': 0}})
    out = decide(A, R, '--dry-run').stdout
    assert 'Expected Cost: Not Available Yet (0 past page readings, from 0 PDFs; needs 12 from 6)' in out
    assert ' for 6 AI requests, including $0.40 for 5 Hawaiian pages to be read by the AI · Limits:' in out
    e = load(R / 'run.json')['estimate']                     # the work order's own figures stay stored: decide.py's limits bind those
    assert f"Max Estimated Cost: ${e['worst_case_total_usd'] + 0.4:.2f} for 6 AI requests" in out and e['expected'].get('kind') != 'page'

def test_the_run_page_names_the_pages_on_the_max_line_only():
    js = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read().split('function costLines')[1].split('const NEXT')[0]
    assert "', including ' + usd(e.page_reads.ceiling_usd) + ' for ' + e.page_reads.pages + ' Hawaiian page'" in js and '<b>' not in js
    assert js.index("'Max Estimated Cost: '") < js.index("', including '") < js.index('Counted Toward')

def test_run_api_prices_the_pages_before_the_cost_lines():
    sh = open(os.path.join(HERE, 'run_api.sh'), encoding='utf-8').read()
    assert sh.index('read_pages.py "$A" "$R" --dry-run') < sh.index('stage "2/5 cost estimate (no model)"')

def test_the_batch_gate_counts_the_pages():
    sh = open(os.path.join(HERE, 'batch_api.sh'), encoding='utf-8').read()
    assert "costs.page_estimate(R)" in sh and "costs.pages_paid(R)" in sh and "with_pages" in sh
