"""test_own_pdf.py: each new run carries its own original PDF (R17, #45 home interface, Patrick 2026-11-07). A new run
moves its PDF from the upload list into <run>/source/ (or copies it: "New Run of This PDF", or when a run made before R17
still reads that very upload); every later step uses that copy; Move to Trash takes it along; runs made before R17 keep
finding their original by sha256. Synthetic PDFs only, no model, no paid call.

    python -m pytest tests/test_own_pdf.py -q
"""
import os, sys, json, hashlib
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from lib import costs  # noqa: E402
from webapp import books as BK, newrun as NR, runs as RN, jobs, home as HM, trash as TR, spend as SP, names as NM  # noqa: E402
from test_webapp import setup, settings, app  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402
from test_spend import run_folder  # noqa: E402

def S(t): return settings(t, trash_dir=str(t / 'Trash'))

def upload(t, s, name='bk.pdf', title='A Book'):
    (t / 'uploads' / name).write_bytes(pdf_bytes(2, title))
    (t / 'uploads' / (name[:-4] + '.json')).write_text(json.dumps({'original_name': name}))
    return next(b for b in BK.listing(s) if b['file'] == name)

def test_a_new_run_takes_its_pdf_and_every_step_uses_it(setup):
    s = S(setup); b = upload(setup, s)
    NM.set_book_name(s, b['key'], 'My Book')
    j = NR.start_estimate(s, [], b['key'], 'First')
    R = setup / 'runs' / 'bk' / 'First'
    own = R / 'source' / 'bk.pdf'
    assert own.is_file() and not (setup / 'uploads' / 'bk.pdf').exists() and (R / 'source' / 'bk.json').is_file()   # moved, with its note
    assert j['argv'][2] == str(own) and j['pdf'] == 'moved' and BK.listing(s) == []                                 # the upload list is empty
    assert hashlib.sha256(own.read_bytes()).hexdigest() == b['key'] and RN.own_pdf(str(R)) == str(own)
    assert RN.book_of(s, 'bk/First', str(R))[0] == 'My Book'                                                        # the name travels (sha256)
    row = {r['run']: r for r in HM.index(s)['runs']}['bk/First']
    assert row['sha'] == b['key'] and HM.group_of(row) == 'processing'                                              # its job is queued
    jobs.update(s['jobs'], j['id'], status='failed', exit=1)                                                       # the estimate fails early:
    row = {r['run']: r for r in HM.index(s)['runs']}['bk/First']
    assert row['status'] == 'Failed' and own.is_file()                                                              #   the run keeps its PDF
    again = NR.again_estimate(s, 'bk/First', str(R))                                                                #   and Try Again uses it
    assert again['argv'][2] == str(own)

def test_the_paid_rule_holds_after_the_move(setup):
    """The estimate is made from the run's own copy, so "Start Remediation" binds that same file (sha256 checked)."""
    s = S(setup); b = upload(setup, s)
    j = NR.start_estimate(s, [], b['key'], 'First')
    R = run_folder(setup, name='bk', label='First')
    jobs.update(s['jobs'], j['id'], status='done')
    est = costs.estimate(str(R), limits=costs.limits_of(s))
    a = SP.authorize(s, 'workorder', 'bk/First', str(R), est['fingerprint'])
    assert a['argv'][2] == str(R / 'source' / 'bk.pdf') and a['extra']['book_sha'] == b['key']
    (R / 'source' / 'bk.pdf').write_bytes(pdf_bytes(3, 'Changed'))                                                 # a different file there: refused
    with pytest.raises(SP.Refused, match='changed or is gone'): SP.authorize(s, 'workorder', 'bk/First', str(R), est['fingerprint'])

def test_new_run_of_this_pdf_copies_it(setup):
    s = S(setup); b = upload(setup, s)
    NR.start_estimate(s, [], b['key'], 'First')
    page = NR.form_page(s, '', run='bk/First')
    assert 'name="run" value="bk/First"' in page and 'Source PDF: bk.pdf' in page
    j = NR.start_estimate(s, [], '', 'Second', from_run='bk/First')
    one, two = setup / 'runs' / 'bk' / 'First' / 'source' / 'bk.pdf', setup / 'runs' / 'bk' / 'Second' / 'source' / 'bk.pdf'
    assert j['pdf'] == 'copied' and one.read_bytes() == two.read_bytes() and j['argv'][2] == str(two)
    assert not [f for f in os.listdir(two.parent) if f.startswith('.')]                                            # no temporary file left

def test_a_move_that_fails_moves_nothing(setup, monkeypatch):
    s = S(setup); b = upload(setup, s)
    real = os.rename
    def refuse(a, c):
        if str(a).endswith('bk.pdf'): raise OSError(18, 'Invalid cross-device link')
        return real(a, c)
    monkeypatch.setattr(os, 'rename', refuse)
    with pytest.raises(ValueError, match='couldn\'t be moved into the run\'s folder .*nothing was moved'): NR.start_estimate(s, [], b['key'], 'First')
    assert (setup / 'uploads' / 'bk.pdf').is_file() and not (setup / 'runs' / 'bk' / 'First').exists() and not jobs.all_jobs(s['jobs'])

def test_an_older_run_still_reading_the_upload_gets_it_kept(setup):
    """A run made before R17 whose estimate names the upload (or whose review reads it) keeps it: the new run gets a copy."""
    s = S(setup); b = upload(setup, s)
    old = setup / 'runs' / 'bk' / 'old'; old.mkdir(parents=True)
    e = jobs.create(s['jobs'], 'estimate', 'bk/old', ['bash', 'run_api.sh', b['path'], 'bk', 'old'], {}, R=str(old), book_sha=b['key'])
    jobs.update(s['jobs'], e['id'], status='done')
    assert TR.upload_still_needed(s, b['path'], b['key']) == 'bk/old'
    j = NR.start_estimate(s, [], b['key'], 'New')
    assert j['pdf'] == 'copied' and (setup / 'uploads' / 'bk.pdf').is_file() and [x['key'] for x in BK.listing(s)] == [b['key']]

def test_an_older_finished_run_still_finds_its_original_by_sha(setup):
    s = S(setup)
    src = setup / 'samples' / 'bk.pdf'; src.write_bytes(pdf_bytes(1, 'Old'))
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    R = setup / 'runs' / 'bk' / 'old'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'bk.pdf', 'sha256': sha}}))
    assert RN.own_pdf(str(R)) is None and RN.pdf_needed(s, str(R), json.loads((R / 'record.json').read_text())) == (str(src), None)

def test_a_run_moved_to_the_trash_takes_its_pdf(setup):
    s = S(setup); b = upload(setup, s)
    j = NR.start_estimate(s, [], b['key'], 'First'); jobs.update(s['jobs'], j['id'], status='failed', exit=1)
    p = TR.plan_run(s, 'bk/First')
    assert TR.CONFIRM_OWN in p['words'] and not p['refused']
    TR.move_run(s, 'bk/First')
    assert (setup / 'Trash' / 'bk - First' / 'source' / 'bk.pdf').is_file() and not (setup / 'runs' / 'bk' / 'First').exists()
    assert BK.listing(s) == []                                                                                      # nothing back in the upload list

def test_the_upload_lists_trash_warns_only_about_older_runs(setup):
    """R17: a run carrying its own PDF isn't listed when the same content is uploaded again and moved to the Trash."""
    s = S(setup); b = upload(setup, s)
    NR.start_estimate(s, [], b['key'], 'First')
    b2 = upload(setup, s)                                                                                           # the same content again
    assert b2['key'] == b['key'] and TR.plan_pdf(s, b2['key'])['runs'] == []

def test_replay_allows_the_new_runs_own_pdf():
    from review import sessions as SS
    import inspect
    assert "[f for f in os.listdir(D) if f != 'source']" in inspect.getsource(SS.replay_to)

# ------------------------------------------------------------------ batches (R17) and "Save Batch for Later" (S7)
from webapp import batches as BT  # noqa: E402

def three(t, s):
    for n in ('a', 'b', 'c'): upload(t, s, f'{n}.pdf', f'Book {n}')
    return [b['key'] for b in BK.listing(s)]

def test_a_batch_moves_each_pdf_into_its_book_folder(setup):
    s = S(setup); keys = three(setup, s)
    js = BT.start(s, [], keys, 'Spring')
    B = setup / 'runs' / 'batches' / 'Spring'
    assert BK.listing(s) == [] and all((B / n / 'source' / f'{n}.pdf').is_file() for n in 'abc')
    lines = [l for l in open(BT.list_path(s, 'Spring'), encoding='utf-8') if not l.startswith('#')]
    assert sorted(l.split(' ', 1)[1].strip() for l in lines) == sorted(str(B / n / 'source' / f'{n}.pdf') for n in 'abc')
    assert sorted(j['argv'][2] for j in js) == sorted(str(B / n / 'source' / f'{n}.pdf') for n in 'abc')
    page = NR.form_page(s, '', run='batches/Spring/a')                                                              # New Run of This PDF
    assert 'Source PDF: a.pdf' in page

def test_a_batch_that_cannot_move_one_pdf_moves_none(setup, monkeypatch):
    s = S(setup); keys = three(setup, s)
    real = os.rename
    def refuse(a, c):
        if str(a).endswith('c.pdf'): raise OSError(18, 'Invalid cross-device link')
        return real(a, c)
    monkeypatch.setattr(os, 'rename', refuse)
    with pytest.raises(ValueError, match='nothing was moved'): BT.start(s, [], keys, 'Spring')
    monkeypatch.undo()
    assert sorted(b['file'] for b in BK.listing(s)) == ['a.pdf', 'b.pdf', 'c.pdf'] and (setup / 'uploads' / 'a.json').is_file()
    assert not (setup / 'runs' / 'batches' / 'Spring').exists() and not os.path.exists(BT.list_path(s, 'Spring')) and not jobs.all_jobs(s['jobs'])

def test_save_reopen_remove_then_estimate(setup):
    """S7: "Save Batch for Later" keeps the batch with its PDFs (moved in, out of the upload list) and no estimate; it is a
    Not Started batch in My Workspace; its page is the form again; "Remove from Batch" puts a PDF back; "Get the Estimates"
    starts it, with the name as the form has it then."""
    s = S(setup); keys = three(setup, s)
    assert BT.start(s, [], keys, 'Later', estimate=False) == []
    assert BK.listing(s) == [] and BT.saved(s, 'Later') and not jobs.all_jobs(s['jobs'])
    b = {x['label']: x for x in HM.index(s)['batches']}['Later']
    assert b['group'] == 'not-started' and b['state'] == 'Not Started'
    page = BT.form_page(s, [], saved='Later')
    assert 'value="Later"' in page and page.count('Remove from Batch</button>') == 3 and 'data-api="/api/batch/Later/start"' in page
    back = BT.remove_saved(s, 'Later', 'c')
    assert back == str(setup / 'uploads' / 'c.pdf') and [x['file'] for x in BK.listing(s)] == ['c.pdf'] and (setup / 'uploads' / 'c.json').is_file()
    assert not (setup / 'runs' / 'batches' / 'Later' / 'c').exists() and [x['name'] for x in BT.books_of(s, 'Later')] == ['a', 'b']
    BT.save_name(s, 'Later', 'Spring backlist')
    js = BT.start_saved(s, [], 'Later', 'Spring backlist, part 1')
    assert len(js) == 2 and not BT.saved(s, 'Later') and NM.batch_name(s, 'Later') == 'Spring backlist, part 1'
    with pytest.raises(ValueError, match='has started'): BT.remove_saved(s, 'Later', 'a')

def test_a_saved_batch_moved_to_the_trash_gives_its_pdfs_back(setup):
    s = S(setup); keys = three(setup, s)
    BT.start(s, [], keys, 'Later', estimate=False)
    p = TR.plan_batch(s, 'Later')
    assert p['saved'] and p['words'] == [TR.SAVED_BACK] and not p['refused']
    TR.move_batch(s, 'Later')
    assert sorted(b['file'] for b in BK.listing(s)) == ['a.pdf', 'b.pdf', 'c.pdf'] and (setup / 'Trash' / 'batch - Later').is_dir()
    assert not [f for d, _, fs in os.walk(setup / 'Trash') for f in fs if f.endswith('.pdf')]                       # no PDF in the Trash

def test_the_saved_batch_routes(app):
    """S7 through the app: save, the batch's page is the form, remove, then "Get the Estimates" refuses one PDF alone."""
    from test_webapp import get
    from test_webapp_home import jpost
    t = app['t']; (t / 'uploads').mkdir(exist_ok=True)
    for n in ('a', 'b', 'c'): (t / 'uploads' / f'{n}.pdf').write_bytes(pdf_bytes(1, f'Book {n}'))
    keys = [b['key'] for b in BK.listing(settings(t))]
    assert jpost(app['port'], '/api/batch/new-later', {'books': keys, 'label': 'Later'}) == (202, {'location': '/?view=batches'})
    page = get(app['port'], '/batch/Later/')[1].decode()
    assert '<h1>New Batch</h1>' in page and page.count('>Remove from Batch</button>') == 3 and 'Save Batch for Later' in page
    assert jpost(app['port'], '/api/batch/Later/remove', {'book': 'c'}) == (200, {'removed': True})
    assert jpost(app['port'], '/api/batch/Later/remove', {'book': 'b'})[0] == 200
    st, d = jpost(app['port'], '/api/batch/Later/start', {'label': 'Later'})
    assert st == 409 and 'two or more' in d['error']
    assert sorted(b['file'] for b in BK.listing(settings(t))) == ['b.pdf', 'c.pdf']

def test_a_trashed_older_run_or_batch_no_longer_keeps_the_upload(setup):
    """A run made before R17 that was moved to the Trash (its job files stay, its folder is gone), or a batch moved to the
    Trash (its book list stays), needs nothing: the new run moves the upload."""
    s = S(setup); b = upload(setup, s)
    old = setup / 'runs' / 'bk' / 'old'; old.mkdir(parents=True); (old / 'run.json').write_text('{}')
    e = jobs.create(s['jobs'], 'estimate', 'bk/old', ['bash', 'run_api.sh', b['path'], 'bk', 'old'], {}, R=str(old), book_sha=b['key'])
    jobs.update(s['jobs'], e['id'], status='done')
    os.makedirs(os.path.join(s['jobs'], 'batches'), exist_ok=True)
    open(BT.list_path(s, 'gone'), 'w').write(f'# batch gone\nbk {b["path"]}\n')
    assert TR.upload_still_needed(s, b['path'], b['key']) == 'bk/old'
    TR.move_run(s, 'bk/old')
    assert TR.upload_still_needed(s, b['path'], b['key']) is None
    assert NR.start_estimate(s, [], b['key'], 'New')['pdf'] == 'moved'

def test_a_copy_taken_back_is_removed_not_listed_twice(setup):
    s = S(setup); keys = three(setup, s)
    old = setup / 'runs' / 'a' / 'old'; old.mkdir(parents=True)
    e = jobs.create(s['jobs'], 'estimate', 'a/old', ['bash', 'run_api.sh', str(setup / 'uploads' / 'a.pdf'), 'a', 'old'], {}, R=str(old))
    jobs.update(s['jobs'], e['id'], status='done')
    BT.start(s, [], keys, 'Later', estimate=False)                                                                  # a.pdf: copied (still needed)
    assert [x['file'] for x in BK.listing(s)] == ['a.pdf']
    assert BT.remove_saved(s, 'Later', 'a') is None and sorted(f for f in os.listdir(setup / 'uploads') if not f.startswith('.')) == ['a.json', 'a.pdf']
