"""test_book_limit.py: the three paid steps share the PDF's limit in terminal runs (review 06, M2; Patrick 2026-11-12).

    python -m pytest tests/test_book_limit.py -q

costs.book_spent(R) is what the folder has spent so far; decide.py counts the page readings and the language step still
to come in its book check; read_pages.py and name_languages.py each refuse when the book's spending plus their own
worst case would pass BOOK_MAX_USD. Fake prices, no network.
"""
import json, os, sys
from test_figure_requests_run import book, decide, small_audit, HERE   # noqa: F401  (book is a fixture)
from test_page_costs import audit_with_pages, read, LAST as PLAST, w
import test_name_languages as TN
sys.path.insert(0, HERE)
from lib import costs as C

def test_book_spent_counts_every_paid_step_of_this_folder(tmp_path):
    R = tmp_path / 'r'
    w(R / 'attempts.json', [{'cost_usd': 0.10}, {'worst_usd': 0.05}])
    w(R / 'run.json', {'usage': {'cost_usd': 0.30}})
    w(R / 'page_reads_run.json', {'cost_usd': 0.20})
    w(R / 'language_run.json', {'cost_usd': 0.40})
    assert C.book_spent(str(R)) == 1.05
    w(R / 'run.json', {'usage': {'cost_usd': 0.30}, 'response_from': '/elsewhere/response.json'})      # a reply from elsewhere
    w(R / 'language_run.json', {'cost_usd': 0.40, 'response_from': '/elsewhere/x.language.json'})
    assert C.book_spent(str(R)) == 0.35

def test_decide_counts_the_steps_to_come(book, tmp_path):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    w(R / 'language_estimate.json', {'worst_case_usd': 4.99, 'to_send': 3})
    r = decide(A, R, '--dry-run')
    assert r.returncode == 0 and 'for the language tags (3 AI requests)' in r.stdout and 'more than the limit of $5.00 per PDF' in r.stdout

def test_page_readings_refuse_over_the_books_limit(tmp_path, monkeypatch):
    A = audit_with_pages(tmp_path); R = tmp_path / 'r'
    w(R / 'run.json', {'usage': {'cost_usd': 4.99}})
    calls = read(A, R, monkeypatch, '--model', TN.MODEL)
    assert calls == [] and 'per PDF' in str(PLAST['exit'])
    calls = read(A, R, monkeypatch, '--model', TN.MODEL, '--book-max-usd', '9')
    assert len(calls) == 2

def test_the_language_step_refuses_over_the_books_limit(tmp_path, monkeypatch):
    src, A, R = TN.folders(tmp_path)
    w(R / 'run.json', {'usage': {'cost_usd': 4.999}})
    assert TN.run(src, A, R, monkeypatch) == [] and 'per PDF' in str(TN.LAST['exit'])
    assert len(TN.run(src, A, R, monkeypatch, '--book-max-usd', '6')) == 1
