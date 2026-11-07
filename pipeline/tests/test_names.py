"""test_names.py: the names people see (#45, home interface; Patrick, 2026-11-06): book names kept by the app
(runs/.app/book-names.json), the automatic cleanup, renaming and its effect on every page at once, and plain run names
whose folder label is derived. No book, no model.

    python -m pytest tests/test_names.py -q
"""
import os, sys, json
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import names as NM, books as BK, home as HM, newrun as NR, runs as RN, jobs  # noqa: E402
from test_webapp import setup, settings, get, app  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402

@pytest.mark.parametrize('title,file,want', [
    ('_no template_Da Kine Talk: From Pidgin', 'dakine.pdf', 'Da Kine Talk: From Pidgin'),
    ('Bikol Text copy', 'bikol.pdf', 'Bikol Text'), ('Bikol Text Copy 2', 'bikol.pdf', 'Bikol Text'),
    ('Bikol Text copy without INDEX', 'bikol.pdf', 'Bikol Text copy without INDEX'),      # left for a person
    ('_x_', 'my_book.pdf', 'my book'), ('', 'colonial-legacies.pdf', 'colonial legacies'),
    ('Ilokano Reference Grammar', 'ilokano.pdf', 'Ilokano Reference Grammar')])
def test_auto_name_is_conservative(title, file, want):
    assert NM.auto_name(title, file) == want

def test_a_person_names_a_book_and_every_page_follows(setup):
    s = settings(setup)
    (setup / 'samples' / 'bk.pdf').write_bytes(pdf_bytes(2, '_draft_A Good Book copy'))
    b = BK.listing(s)[0]
    assert b['name'] == 'A Good Book' and b['file'] == 'bk.pdf'
    R = setup / 'runs' / 'bk' / 'r1'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'bk.pdf', 'sha256': b['key']}, 'run': {'started': '2026-11-01T10:00:00'}}))
    assert {r['run']: r for r in HM.index(s)['runs']}['bk/r1']['book'] == 'A Good Book'
    assert os.path.isfile(os.path.join(s['jobs'], 'home-index.json'))
    NM.set_book_name(s, b['key'], '  The  Good‮ Book ')
    assert not os.path.exists(os.path.join(s['jobs'], 'home-index.json'))        # the cache is built again
    assert BK.listing(s)[0]['name'] == 'The Good Book' and {r['run']: r for r in HM.index(s)['runs']}['bk/r1']['book'] == 'The Good Book'
    NM.set_book_name(s, b['key'], 'Third Name')
    e = json.load(open(os.path.join(s['jobs'], 'book-names.json')))[b['key']]
    assert e['name'] == 'Third Name' and [h['name'] for h in e['history']] == ['The Good Book']
    assert 'Third Name' not in (R / 'record.json').read_text()                   # never in the run's archive
    with pytest.raises(ValueError): NM.set_book_name(s, b['key'], '   ')
    with pytest.raises(ValueError): NM.set_book_name(s, '../x', 'A')

def test_a_run_page_shows_the_new_name_not_the_jobs_snapshot(setup):
    s = settings(setup)
    sha = 'a' * 64
    R = setup / 'runs' / 'bk' / 'r2'; R.mkdir(parents=True)
    jobs.create(s['jobs'], 'estimate', 'bk/r2', ['true'], {}, R=str(R), book_sha=sha, book_name='Old Snapshot', book_file='bk.pdf')
    NM.set_book_name(s, sha, 'New Name')
    assert RN.book_of(s, 'bk/r2', str(R))[0] == 'New Name'

@pytest.mark.parametrize('plain,want', [('First pass, March', 'First-pass-March'), ('Café ëxample', 'Cafe-example'),
                                        ('  ', None), ('日本語', None), ('-x-', 'x'), ('a' * 100, 'a' * 64)])
def test_labels_are_derived(plain, want):
    lab = NM.label_for(NM.clean_name(plain), 'run', lambda l: False)
    assert NM.LABEL.fullmatch(lab) and (lab == want if want else lab.startswith('run-20'))

def test_a_taken_label_gets_underscore_2(setup):
    taken = {'x', 'x_2'}
    assert NM.label_for('x', 'run', taken.__contains__) == 'x_3'
    assert NM.label_for('a' * 64, 'run', {'a' * 64}.__contains__) == 'a' * 62 + '_2'

def test_new_run_takes_a_plain_name(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng'])
    s = settings(setup)
    (setup / 'samples' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book'))
    key = BK.listing(s)[0]['key']
    j = NR.start_estimate(s, [], key, 'First pass, March', 'eng', True)
    k = NR.start_estimate(s, [], key, 'First pass March', 'eng', True)        # folds to the same label
    assert j['run'] == 'bk/First-pass-March' and k['run'] == 'bk/First-pass-March_2'
    assert 'First pass, March' not in json.dumps({x: j[x] for x in ('run', 'argv', 'dir', 'env_set')})
    assert NM.shown_run(s, j['run']) == 'First pass, March' and NM.shown_run(s, k['run']) == 'First pass March'
    v = RN.job_view(s, jobs.load(s['jobs'], j['id']))
    assert v['run_name'] == 'First pass, March' and v['book_name'] == 'A Book'

def test_home_search_matches_both_names(app):
    from webapp import config
    t = app['t']; s = config.load(str(t / 'app.json'), environ={})
    R = t / 'runs' / 'bk' / 'lbl-x'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'bk.pdf'}, 'run': {'started': '2026-11-01T10:00:00'}}))
    NM.set_run_name(s, 'bk/lbl-x', 'Spring pass')
    for q in ('Spring', 'lbl-x'):
        page = get(app['port'], f'/?q={q}')[1].decode()
        assert '1 run matching' in page and 'Spring pass' in page, q
