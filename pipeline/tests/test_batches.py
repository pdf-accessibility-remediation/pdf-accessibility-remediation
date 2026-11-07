"""test_batches.py: batches from the home page (#45, webapp/batches.py, batch.js's markup): the book list batch_api.sh reads,
names unique per book, one free estimate job per book, the batch's state and Spend (test mode: FROM=, no paid call), the
side column, and the Home links on the review page (stage 5). No book, no model.

    python -m pytest tests/test_batches.py -q
"""
import os, sys, json, hashlib
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import batches as BT, jobs, books as BK  # noqa: E402
from test_webapp import setup, settings  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402
from test_spend import run_folder  # noqa: E402

def books(t, names):
    for n in names: (t / 'uploads' / n).write_bytes(pdf_bytes(1, None) + n.encode())

@pytest.fixture
def two(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng'])
    (setup / 'uploads' / 'a').mkdir(); (setup / 'uploads' / 'b').mkdir()
    (setup / 'uploads' / 'a' / 'Book One.pdf').write_bytes(pdf_bytes(1) + b'a'); (setup / 'uploads' / 'b' / 'Book One.pdf').write_bytes(pdf_bytes(2) + b'b')
    (setup / 'uploads' / 'two.pdf').write_bytes(pdf_bytes(3) + b'c')
    return setup

def test_start_writes_the_book_list_and_one_estimate_per_book(two):
    s = settings(two, test_batch_from='v8-p7a')
    keys = [b['key'] for b in BK.listing(s)]
    js = BT.start(s, [], keys, 'b1', 'eng')
    lines = [l.rstrip('\n') for l in open(BT.list_path(s, 'b1'), encoding='utf-8') if not l.startswith('#')]
    names = [l.split(' ', 1)[0] for l in lines]
    assert sorted(names) == ['Book_One', 'Book_One-2', 'two'] and all(os.path.isabs(l.split(' ', 1)[1]) for l in lines)   # unique, absolute
    assert [j['kind'] for j in js] == ['batch-estimate'] * 3 and all(j['env_set']['ESTIMATE'] == '1' and j['env_set']['RUN_DIR'].endswith(j['run'].split('/')[-1]) for j in js)
    assert all(j['argv'][1:2] == ['run_api.sh'] and j['argv'][4] == 'b1' and 'AUTO' not in j['env'] for j in js)    # batch_api.sh's own estimate command
    assert json.load(open(BT.meta_path(s, 'b1')))['ocr_lang'] == 'eng'
    j2 = BT.start(s, [], keys, 'b1', 'eng')                                 # a name that is taken: "_2" (never "-2")
    assert j2[0]['run'].startswith('batches/b1_2/') and j2[0]['argv'][4] == 'b1_2'
    with pytest.raises(ValueError, match='two or more'): BT.start(s, [], keys[:1], 'b2', 'eng')
    with pytest.raises(ValueError, match='Enter a name'): BT.start(s, [], keys, '   ', 'eng')         # P10: required

def test_plain_batch_names_and_the_cap(two):
    """Patrick, 2026-11-06: staff type a plain name; the label is derived and the plain name is the app's only. Two names
    that fold to the same label get "_2". New Batch refuses more than max_books_per_batch."""
    from webapp import names as NM
    s = settings(two, test_batch_from='v8-p7a')
    keys = [b['key'] for b in BK.listing(s)]
    a = BT.start(s, [], keys, 'Café books, spring!', 'eng')[0]['run'].split('/')[1]
    b = BT.start(s, [], keys, 'Cafe books spring', 'eng')[0]['run'].split('/')[1]
    assert a == 'Cafe-books-spring' and b == 'Cafe-books-spring_2'
    assert NM.batch_name(s, a) == 'Café books, spring!' and NM.batch_name(s, b) == 'Cafe books spring'
    assert 'Café' not in open(BT.list_path(s, a), encoding='utf-8').read()                  # never in a path or a command
    c = BT.start(s, [], keys, '日本語', 'eng')[0]['run'].split('/')[1]
    assert c.startswith('batch-20') and NM.batch_name(s, c) == '日本語'                     # nothing left: the date
    s2 = settings(two, max_books_per_batch=2)
    with pytest.raises(ValueError, match='A batch can hold up to 2 PDFs. Split them into two batches.'): BT.start(s2, [], keys, 'x', 'eng')

def test_a_path_with_list_marks_is_refused(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng'])
    (setup / 'uploads' / 'x#1.pdf').write_bytes(pdf_bytes(1) + b'1'); (setup / 'uploads' / 'y.pdf').write_bytes(pdf_bytes(1) + b'2')
    s = settings(setup)
    with pytest.raises(ValueError, match='file name a batch'): BT.start(s, [], [b['key'] for b in BK.listing(s)], 'b1', 'eng')

def ready_batch(t, s):
    """A batch whose two books have their estimates (synthetic run.json), as the app's estimate jobs leave them."""
    keys = [b['key'] for b in BK.listing(s)][:2]
    js = BT.start(s, [], keys, 'bb', 'eng')
    for j in js:
        jobs.update(s['jobs'], j['id'], status='done', exit=0)
        name = j['run'].split('/')[-1]
        R = run_folder(t, name='batches', label=f'bb/{name}', worst=0.6)
    return keys

def test_state_and_test_mode_spend(two):
    s = settings(two, test_batch_from='v8-p7a')
    ready_batch(two, s)
    st = BT.state(s, 'bb')
    assert st['phase'] == 'ready' and st['spend'] == {'ok': True, 'why': None} and st['totals']['ceiling_usd'] == 1.2 and st['test']
    assert [b['status'] for b in st['books']] == ['Estimate Ready'] * 2 and sorted(b['file'] for b in st['books']) == ['Book One.pdf', 'two.pdf']
    with pytest.raises(ValueError, match='changed since'): BT.spend(s, 'bb', {'fingerprint': 'x'})
    j = BT.spend(s, 'bb', {'fingerprint': st['fingerprint']})
    assert j['kind'] == 'batch' and j['paid'] and j['run'] == 'batches/bb' and 'slots' not in j
    assert j['env_set'] == {'AUTO': '1', 'FROM': 'v8-p7a', 'JOBS': '10', 'OCR_LANG': 'eng'} and j['argv'] == ['bash', 'batch_api.sh', 'bb', BT.list_path(s, 'bb')]

def test_real_spend_binds_the_total_and_each_call(two):
    s = settings(two)
    ready_batch(two, s)
    st = BT.state(s, 'bb')
    j = BT.spend(s, 'bb', {'fingerprint': st['fingerprint']})
    e = j['env_set']
    assert e['BATCH_MAX_USD'] == '1.21' and e['MAX_USD'] == '0.61' and e['MODEL'].startswith('anthropic/') and 'FROM' not in e

def test_over_the_batch_limit_shows_no_spend(two):
    s = settings(two, limits={'per_batch_usd': 1.0})
    ready_batch(two, s)
    st = BT.state(s, 'bb')
    assert st['spend']['ok'] is False and 'limit of $1.00 per batch' in st['spend']['why']
    with pytest.raises(ValueError): BT.spend(s, 'bb', {'fingerprint': st['fingerprint']})

def test_side_column_markup(two):
    s = settings(two, test_batch_from='v8-p7a')
    ready_batch(two, s)
    n = BT.nav(s, 'bb', current='Book_One')
    assert n.startswith('<nav class="bn" id="pp-bnav" aria-label="PDFs in This Batch"') and 'aria-expanded="true"' in BT.toggle(2) and 'aria-controls="bn-list"' in BT.toggle(2)
    assert n.count('aria-current="page"') == 1 and 'href="/run/batches/bb/Book_One/" aria-current="page"' in n and 'Source PDF: Book One.pdf' in n
    assert 'Estimate Ready' in n
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "matchMedia('(max-width: 48em)')" in js and "setAttribute('aria-expanded'" in js and 'Show the Book List (' in js

def test_again_estimates_only_the_unfinished(two):
    s = settings(two, test_batch_from='v8-p7a')
    ready_batch(two, s)
    (two / 'runs' / 'batches' / 'bb' / 'Book_One' / 'record.json').write_text('{}')
    js = BT.again(s, 'bb')
    assert [j['run'] for j in js] == ['batches/bb/two'] and js[0]['kind'] == 'batch-estimate'

def test_the_review_page_links_home():
    p = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert "a.textContent = 'Home Page'" in p and "new URL(RETURN_TO).origin" in p and p.count('homeLink(') == 3     # the review page and the OCR-only page

def test_the_forms_send_what_the_routes_read(two):
    """New Run's form sends `book` (one key), New Batch's `books` (a list): home.js turns only a field named "books" into a
    list (a batch-only rule once broke New Run, caught in the paid test P1)."""
    from webapp import newrun as NR
    s = settings(two)
    key = BK.listing(s)[0]['key']
    assert f'name="book" value="{key}"' in NR.form_page(s, key)
    keys = [b['key'] for b in BK.listing(s)]
    assert all(f'name="books" value="{k}"' in BT.form_page(s, keys) for k in keys)
    js = open(os.path.join(HERE, 'webapp', 'home.js'), encoding='utf-8').read()
    assert "if (x.name === 'books')" in js and "x.name === 'book')" not in js

def test_a_tab_or_return_in_a_path_is_refused(setup, monkeypatch):
    """05 L1: batch_api.sh's books.tsv is tab-separated."""
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng'])
    (setup / 'uploads' / 'x\ty.pdf').write_bytes(pdf_bytes(1) + b'1'); (setup / 'uploads' / 'z.pdf').write_bytes(pdf_bytes(1) + b'2')
    s = settings(setup)
    with pytest.raises(ValueError, match='file name a batch'): BT.start(s, [], [b['key'] for b in BK.listing(s)], 'b1', 'eng')
