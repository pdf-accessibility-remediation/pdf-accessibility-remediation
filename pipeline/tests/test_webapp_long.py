"""M6 (review 04): the long-book note on the run page and "(long book)" on a batch row, for a book over intake's
TAGGER_LONG pages (it tags alone and can take over an hour). Synthetic PDFs only."""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import intake  # noqa: E402
from webapp import books as BK, runs as RN, server as W, newrun as NR  # noqa: E402
from test_webapp import setup, settings  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402


def test_the_threshold_is_intakes():
    assert RN.LONG_BOOK == intake.TAGGER_LONG


def test_the_note_on_the_run_page(setup):
    s = settings(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(3, 'A Book'))
    key = BK.listing(s)[0]['key']
    NR.start_estimate(s, [], key, 'First'); R = setup / 'runs' / 'bk' / 'First'
    assert RN.long_book(s, 'bk/First', str(R)) is None                        # 3 pages: no note
    assert 'pp-hd-long' not in W.app_header(s, 'bk/First', str(R))
    cp = os.path.join(s['jobs'], 'books-cache.json'); cache = json.load(open(cp)); cache[key]['pages'] = 1467; json.dump(cache, open(cp, 'w'))
    assert RN.long_book(s, 'bk/First', str(R)) == 1467                        # before intake: the count read at upload
    h = W.app_header(s, 'bk/First', str(R))
    assert 'This is a long book (1,467 pages). Processing can take over an hour.' in h
    (R / '_intake').mkdir(parents=True, exist_ok=True); (R / '_intake' / 'intake.json').write_text(json.dumps({'original': {'pages': 1000}}))
    assert RN.long_book(s, 'bk/First', str(R)) is None                        # intake's count wins; exactly 1,000 is not long
    (R / '_intake' / 'intake.json').write_text(json.dumps({'original': {'pages': 1001}}))
    assert RN.long_book(s, 'bk/First', str(R)) == 1001
    (R / 'record.json').write_text('{}')                                       # finished: no note
    assert RN.long_book(s, 'bk/First', str(R)) is None


def test_long_book_on_a_batch_row():
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "(r.long && !x ? ' <span class=\"pp-note\">(long book)</span>' : '')" in js
