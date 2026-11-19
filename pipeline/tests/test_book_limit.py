import pytest
"""test_book_limit.py: the three paid steps share the PDF's limit in terminal runs (review 06, M2; Patrick 2026-11-12).

    python -m pytest tests/test_book_limit.py -q

costs.book_spent(R) is what the folder has spent so far; decide.py counts the page readings and the language step still
to come in its book check; read_pages.py and name_languages.py each refuse when the book's spending plus their own
worst case would pass BOOK_MAX_USD. An optional step (page readings, language tags) counts only when it fits with the
work order, and is otherwise the one left out (review 08, H1). Fake prices, no network.
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
    w(R / 'language_estimate.json', {'worst_case_usd': 0.10, 'to_send': 3})
    r = decide(A, R, '--dry-run')
    assert r.returncode == 0 and 'for the language tags (3 AI requests)' in r.stdout and 'left out' not in r.stdout

# ------------------------------------------------------------------ review 08, H1: an optional step never stops the work order
def real_run_passed_the_book_check(r):
    """decide.py's real run, offline: it gets past every limit and stops at the network, never at the PDF's limit."""
    out = r.stdout + r.stderr
    return 'refusing before any request' not in out and 'more than the limit of $5.00 per PDF' not in out

def test_a_language_step_over_its_own_cap_never_counts(book, tmp_path, monkeypatch):
    """$4.50 of language tags, over LANGUAGE_MAX_USD $4. #159: the step no longer refuses itself for its own cost: it holds
    back what doesn't fit (here everything) and sends nothing. An older estimate marked `cap` still never counts, and
    decide.py runs."""
    src, A2, R2 = TN.folders(tmp_path)
    assert TN.run(src, A2, R2, monkeypatch, '--dry-run', '--max-usd', '0.0001') == []
    e = json.load(open(R2 / 'language_estimate.json'))
    assert C.refused(str(R2), 'language') is None and e['to_send'] == 0 and e['held_back'] == e['forms'] and e['held_back_limit']['which'] == 'step'
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    w(R / 'language_estimate.json', {'worst_case_usd': 4.50, 'to_send': 3, 'refused': {'why': 'cap', 'words': 'over its limit'}})
    r = decide(A, R, '--dry-run')
    assert r.returncode == 0 and 'language tags' not in r.stdout and 'more than the limit of $5.00 per PDF' not in r.stdout
    assert real_run_passed_the_book_check(decide(A, R))

def test_a_language_step_that_fits_its_cap_but_not_the_book_is_the_one_left_out(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    w(R / 'language_estimate.json', {'worst_case_usd': 4.99, 'to_send': 3})
    r = decide(A, R, '--dry-run', '--book-max-usd', '5')                                # the $5 this was written for
    assert r.returncode == 0 and 'Language tags from the AI are left out of this run' in r.stdout and 'BOOK_MAX_USD=' in r.stdout
    assert C.refused(str(R), 'language')['why'] == 'book' and C.language_estimate(str(R)) is None
    assert real_run_passed_the_book_check(decide(A, R))
    r = decide(A, R, '--dry-run', '--book-max-usd', '9')                  # a higher limit: counted again
    assert 'for the language tags (3 AI requests)' in r.stdout and C.refused(str(R), 'language') is None
    # name_languages.py then refuses itself, with decide.py's reason, through run_api.sh's order: its dry run, decide.py's
    # mark, the work order's call, its dry run again before the question (which must not lift the mark), the real step
    src, A2, R2 = TN.folders(tmp_path)
    TN.run(src, A2, R2, monkeypatch, '--dry-run')
    C.mark_refused(str(R2), 'language', 'book', 'The language step is left out of this run: with it, this PDF could cost up to $5.62.')
    w0 = C._load(str(R2 / 'language_estimate.json'))['worst_case_usd']
    (R2 / 'workorder.json').write_text(json.dumps({'document': {'lang': 'en', 'title': 'A much longer title the work order set between the two dry runs'}}))
    TN.run(src, A2, R2, monkeypatch, '--dry-run')
    assert C._load(str(R2 / 'language_estimate.json'))['worst_case_usd'] != w0       # the title moved the worst case (review 10, M1)
    assert C.refused(str(R2), 'language')['why'] == 'book'                  # kept by a dry run of the same step
    (R2 / 'response.json').write_text('{}')                                 # the work order has run
    assert TN.run(src, A2, R2, monkeypatch, '--dry-run') == [] and 'left out of this run' in str(TN.LAST['exit'])
    assert TN.run(src, A2, R2, monkeypatch) == [] and 'left out of this run' in str(TN.LAST['exit'])

def test_fit_optional_keeps_the_page_readings_first():
    pr, le = {'worst_case_usd': 1.0}, {'worst_case_usd': 2.0}
    kept, out = C.fit_optional(0.5, 2.0, [('page_reads', pr), ('language', le)], 5.0)
    assert list(kept) == ['page_reads'] and [x['kind'] for x in out] == ['language'] and out[0]['could_usd'] == 5.5
    assert C.fit_optional(0.5, 2.0, [('page_reads', pr), ('language', le)], None)[0] == {'page_reads': pr, 'language': le}
    assert C.fit_optional(0, 6.0, [('language', le)], 5.0)[1][0]['kind'] == 'language'         # the work order alone over: it is decide.py's own refusal

def test_page_readings_refuse_over_the_books_limit(tmp_path, monkeypatch):
    A = audit_with_pages(tmp_path); R = tmp_path / 'r'
    w(R / 'run.json', {'usage': {'cost_usd': 4.99}})
    calls = read(A, R, monkeypatch, '--model', TN.MODEL)
    assert calls == [] and 'per PDF' in str(PLAST['exit'])
    calls = read(A, R, monkeypatch, '--model', TN.MODEL, '--book-max-usd', '9')
    assert len(calls) == 2

def test_the_language_step_fills_only_the_room_left_in_the_books_limit(tmp_path, monkeypatch):
    """#159, review 29 M4 (was: the step refuses over the PDF's limit): $4.999 spent of $5 leaves no room, so every form is
    held back (the PDF's limit named as the reason) and nothing is sent; with $6 the request is sent."""
    src, A, R = TN.folders(tmp_path)
    w(R / 'run.json', {'usage': {'cost_usd': 4.999}})
    assert TN.run(src, A, R, monkeypatch, '--book-max-usd', '5') == [] and TN.LAST['exit'] is None
    lr = json.load(open(R / 'language_run.json'))
    assert lr['held_back_count'] == 3 and lr['held_back_limit']['which'] == 'book' and not lr['requests']
    assert len(TN.run(src, A, R, monkeypatch, '--book-max-usd', '6')) == 1

def test_page_readings_left_out_stay_left_out_through_the_second_dry_run(tmp_path, monkeypatch):
    """review 08, H1: run_api.sh dry-runs read_pages.py again before its question; decide.py's "left out" survives it, and
    once the work order has run the step stops with that reason."""
    A = audit_with_pages(tmp_path); R = tmp_path / 'r'
    read(A, R, monkeypatch, '--model', TN.MODEL, '--dry-run')
    C.mark_refused(str(R), 'page_reads', 'book', 'The AI reading of scanned Hawaiian pages is left out of this run: with it, this PDF could cost up to $5.40.')
    read(A, R, monkeypatch, '--model', TN.MODEL, '--dry-run')
    assert C.refused(str(R), 'page_reads')['why'] == 'book' and C.page_estimate(str(R)) is None
    (R / 'response.json').write_text('{}')
    assert read(A, R, monkeypatch, '--model', TN.MODEL, '--dry-run') == [] and 'left out of this run' in str(PLAST['exit'])
    assert read(A, R, monkeypatch, '--model', TN.MODEL) == [] and 'left out of this run' in str(PLAST['exit'])

def test_the_left_out_words_are_the_panels_with_no_names_in_quotes():
    """review 12, L1: no quoted names that appear on no screen, and no "app's settings" (a file, not a screen)."""
    le = {'worst_case_usd': 1.5}; pr = {'worst_case_usd': 1.0}
    out = {x['kind']: x['words'] for x in C.fit_optional(0, 4.5, [('page_reads', pr), ('language', le)], 5.0)[1]}
    assert out['page_reads'].startswith('The AI reading of Hawaiian pages is left out of this run: ')
    assert out['page_reads'].endswith('To include it, the app administrator can raise the limit per PDF.')
    assert out['language'].startswith('Language tags from the AI are left out of this run: ')
    assert out['language'].endswith('The PDF is processed without language tags from the AI. To include them, the app administrator can raise the limit per PDF.')
    assert not any('"' in w or 'settings' in w for w in out.values())

@pytest.fixture(autouse=True)
def _limits(limits_of_2026_11):
    """These scenarios were written for $5 per PDF and $4 for the language step (conftest.py)."""
