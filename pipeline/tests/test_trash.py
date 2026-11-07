"""test_trash.py: "Move to Trash" (#45 D8, webapp/trash.py): a run, a batch whole or in part, a PDF added through "Add a
PDF". Everything goes to a Trash folder of the test's own (trash_dir), by rename, logged; a refused move moves nothing;
a partial batch move rewrites the batch's book list and keeps the spend shown; a run whose original PDF was moved says
so and refuses "Review Again" in plain words. No book, no model.

    python -m pytest tests/test_trash.py -q
"""
import os, sys, json, errno
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import trash as TR, jobs, books as BK, batches as BT, names as NM, runs as RN  # noqa: E402
from test_webapp import setup, settings, get, app  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402

def S(t): return settings(t, trash_dir=str(t / 'Trash'))

def finished_run(t, name='bk', label='r1', sha='a' * 64, cost=0.25, shipped=False):
    R = t / 'runs' / name / label; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': f'{name}.pdf', 'sha256': sha}, 'run': {'started': '2026-11-01T10:00:00',
                                              'usage': {'cost_usd': cost}}, 'cost_total_usd': cost}))
    (R / 'bk_remediated.pdf').write_bytes(b'%PDF-1.7 result')
    if shipped:
        (R / 'release').mkdir(); (R / 'release' / 'shipped.json').write_text(json.dumps([{'n': 1, 'shipped': '2026-11-02T10:00:00'}]))
    return R

def test_a_run_goes_to_the_trash_and_is_logged(setup):
    s = S(setup); R = finished_run(setup)
    NM.set_run_name(s, 'bk/r1', 'Spring pass')
    p = TR.plan_run(s, 'bk/r1')
    assert p['name'] == 'Spring pass' and p['words'] == [TR.CONFIRM_RUN] and not p['refused']
    r = TR.move_run(s, 'bk/r1')
    assert not R.exists() and (setup / 'Trash' / 'bk - r1' / 'bk_remediated.pdf').read_bytes() == b'%PDF-1.7 result'
    log = json.load(open(os.path.join(s['jobs'], 'trash-log.json')))
    assert log[-1]['what'] == 'run' and log[-1]['name'] == 'Spring pass' and log[-1]['to'].endswith('bk - r1')
    assert NM.run_name(s, 'bk/r1') is None                                       # the plain name moved into the log
    R2 = finished_run(setup); TR.move_run(s, 'bk/r1')
    assert not R2.exists() and (setup / 'Trash' / 'bk - r1 2').is_dir()         # a name taken in the Trash: "… 2"

def test_a_shipped_run_is_warned_about(setup):
    s = S(setup); finished_run(setup, shipped=True)
    assert TR.plan_run(s, 'bk/r1')['words'] == [TR.CONFIRM_RUN, TR.CONFIRM_SHIPPED]

@pytest.mark.parametrize('state', ['queued', 'running', 'needs-spend', 'finish-gap'])
def test_a_refused_move_moves_nothing(setup, state):
    s = S(setup); R = finished_run(setup)
    if state == 'finish-gap': (R / 'record.json').unlink(); (R / 'workorder.ai.json').write_text('{}'); (R / 'review.json').write_text('{}')
    else:
        j = jobs.create(s['jobs'], 'apply', 'bk/r1', ['true'], {}, R=str(R)); jobs.update(s['jobs'], j['id'], status=state)
    before = sorted(os.listdir(R))
    with pytest.raises(TR.Refused): TR.move_run(s, 'bk/r1')
    assert sorted(os.listdir(R)) == before and not (setup / 'Trash').exists() and not os.path.exists(os.path.join(s['jobs'], 'trash-log.json'))

def test_another_disk_is_refused(setup, monkeypatch):
    s = S(setup); R = finished_run(setup)
    def exdev(a, b): raise OSError(errno.EXDEV, 'cross-device')
    monkeypatch.setattr(TR.os, 'rename', exdev)
    with pytest.raises(TR.Refused, match='another disk'): TR.move_run(s, 'bk/r1')
    assert R.exists()

def batch(setup, s):
    for n in ('a', 'b', 'c'): (setup / 'uploads' / f'{n}.pdf').write_bytes(pdf_bytes(1, f'Book {n}'))
    js = BT.start(s, [], [b['key'] for b in BK.listing(s)], 'Spring')
    for j in js: jobs.update(s['jobs'], j['id'], status='done')
    B = setup / 'runs' / 'batches' / 'Spring'
    for n, c in (('a', 0.10), ('b', 0.20)):
        (B / n / 'record.json').write_text(json.dumps({'document': {'file': f'{n}.pdf'}, 'run': {'usage': {'cost_usd': c}}, 'cost_total_usd': c}))
    (B / 'b.log').write_text('log'); (B / 'summary.md').write_text('# Batch Spring')
    return B

def test_part_of_a_batch_goes_and_its_spend_stays_shown(setup):
    s = S(setup); B = batch(setup, s)
    p = TR.plan_batch(s, 'Spring', ['b'])
    assert not p['whole'] and [x['name'] for x in p['pdfs']] == ['b'] and not p['refused']
    TR.move_batch(s, 'Spring', ['b'])
    assert not (B / 'b').exists() and (setup / 'Trash' / 'batch - Spring - b' / '_batch-files' / 'b.log').read_text() == 'log'
    assert [l.split(' ', 1)[0] for l in open(BT.list_path(s, 'Spring')) if not l.startswith('#')] == ['a', 'c']   # never sent again
    assert [b['name'] for b in json.load(open(BT.meta_path(s, 'Spring')))['books']] == ['a', 'c']
    assert json.load(open(B / 'trashed.json'))[0]['cost_usd'] == 0.2
    st = BT.state(s, 'Spring')
    assert [b['name'] for b in st['books']] == ['a', 'c'] and st['trashed'] == {'n': 1, 'cost_usd': 0.2}
    assert any(j['kind'] == 'summary' and j['argv'] == ['bash', 'batch_api.sh', 'Spring'] for j in jobs.all_jobs(s['jobs']))   # summary.md again
    assert TR.plan_batch(s, 'Spring', ['a'])['refused'].startswith('It is waiting to start')      # its summary job still queued
    for j in jobs.all_jobs(s['jobs']):
        if j['kind'] == 'summary': jobs.update(s['jobs'], j['id'], status='done')   # as the dispatcher would run it
    p = TR.plan_batch(s, 'Spring', ['a', 'c'])
    assert p['whole']                                                         # every PDF left: the batch itself goes
    TR.move_batch(s, 'Spring', ['a', 'c'])
    assert not B.exists() and (setup / 'Trash' / 'batch - Spring' / 'trashed.json').exists()

def test_a_batch_that_runs_is_refused(setup):
    s = S(setup); B = batch(setup, s)
    j = jobs.create(s['jobs'], 'batch', 'batches/Spring', ['true'], {}, R=str(B), paid=True, fingerprint='f'); jobs.update(s['jobs'], j['id'], status='running')
    with pytest.raises(TR.Refused, match='processed right now'): TR.move_batch(s, 'Spring', ['a'])
    assert (B / 'a').exists()

def test_a_pdf_used_by_runs_goes_and_the_run_says_so(setup):
    s = S(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book')); key = BK.listing(s)[0]['key']
    R = finished_run(setup, sha=key)                                            # a tagged run: no intake copy, so it needs the original
    p = TR.plan_pdf(s, key)
    assert [r['name'] for r in p['runs']] == ['r1'] and p['words'] == [TR.CONFIRM_USED] and not p['refused']
    assert p['runs'][0]['effect'] == TR.NEEDS_BACK                              # no copy of its own: it needs the original
    TR.move_pdf(s, key)
    assert not (setup / 'uploads' / 'bk.pdf').exists() and (setup / 'Trash' / 'bk.pdf').exists() and BK.by_key(s, key) is None
    assert TR.moved_pdf(s, key)['runs'] == ['r1']
    st = RN.state(s, 'bk/r1', str(R))
    assert st['pdf_moved']['text'].startswith('The original PDF was moved to the Trash. "Review Again" needs it back')
    with pytest.raises(ValueError, match='moved to the Trash'): RN.start_review(s, 'bk/r1', str(R), 8123)
    os.rename(setup / 'Trash' / 'bk.pdf', setup / 'uploads' / 'bk.pdf')       # put back by hand: found again
    assert 'pdf_moved' not in RN.state(s, 'bk/r1', str(R))

def test_a_pdf_whose_run_is_busy_is_refused(setup):
    s = S(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book')); key = BK.listing(s)[0]['key']
    R = finished_run(setup, sha=key)
    j = jobs.create(s['jobs'], 'estimate', 'bk/r1', ['true'], {}, R=str(R)); jobs.update(s['jobs'], j['id'], status='running')
    with pytest.raises(TR.Refused, match='processed right now'): TR.move_pdf(s, key)
    assert (setup / 'uploads' / 'bk.pdf').exists()

def test_the_routes(app):
    from test_webapp_panel import post
    t = app['t']; c = json.loads((t / 'app.json').read_text()); c['trash_dir'] = str(t / 'Trash'); (t / 'app.json').write_text(json.dumps(c))
    st, b = post(app['port'], '/api/trash/plan', {'what': 'run', 'run': 'old/r0'})
    assert st == 200 and b['what'] == 'run' and b['words'] == [TR.CONFIRM_RUN]
    for bad in ('../x', '.app/jobs', 'old/../.app', 'old'):                       # never the app's own folders, never outside
        assert post(app['port'], '/api/trash/plan', {'what': 'run', 'run': bad})[0] == 409, bad
        assert post(app['port'], '/api/trash/move', {'what': 'run', 'run': bad})[0] == 409, bad
    assert (t / 'runs' / '.app').is_dir() and not (t / 'Trash').exists()
    st, _ = post(app['port'], '/api/trash/move', {'what': 'run', 'run': 'old/r0'}, origin='http://evil.example')
    assert st == 403 and (t / 'runs' / 'old' / 'r0').is_dir()                    # another site's page: refused, nothing moved
    page = get(app['port'], '/')[1].decode()
    assert 'data-trash="run"' in page and '/app/trash.js' in page

def test_a_pdf_an_estimate_is_reading_is_refused(setup):
    """Found in the browser check: a run with no record yet (its estimate just started) is known only from its job; the
    move is refused while any job's command names the file."""
    s = S(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book')); b = BK.listing(s)[0]
    R = setup / 'runs' / 'batches' / 'B1' / 'bk'; R.mkdir(parents=True)
    j = jobs.create(s['jobs'], 'batch-estimate', 'batches/B1/bk', ['bash', 'run_api.sh', b['path'], 'bk', 'B1'], {}, R=str(R), book_sha=b['key'])
    p = TR.plan_pdf(s, b['key'])
    assert [r['name'] for r in p['runs']] == ['B1'] and 'waiting to start' in p['refused']
    jobs.update(s['jobs'], j['id'], status='done')
    k = jobs.create(s['jobs'], 'estimate', 'other/x', ['bash', 'run_api.sh', b['path'], 'other', 'x'], {}, R=str(setup / 'runs' / 'other' / 'x'))
    assert 'being read by a job' in TR.plan_pdf(s, b['key'])['refused']
    with pytest.raises(TR.Refused): TR.move_pdf(s, b['key'])
    assert (setup / 'uploads' / 'bk.pdf').exists()

def test_a_batch_summary_job_never_makes_the_batch_folder_a_run(setup):
    """Found in the browser check: the summary job after a partial move named the batch folder, so runs.pending() took the
    batch for a run and its PDFs' pages were not found."""
    s = S(setup); B = batch(setup, s)
    TR.move_batch(s, 'Spring', ['b'])
    assert not RN.pending(s, str(B))

def test_a_pdfs_note_goes_with_it(setup):
    s = S(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book')); (setup / 'uploads' / 'bk.json').write_text('{"name": "bk.pdf"}')
    key = BK.listing(s)[0]['key']
    TR.move_pdf(s, key)
    assert (setup / 'Trash' / 'bk.json').exists() and not (setup / 'uploads' / 'bk.json').exists()

def _listed(s):
    return [l.split(' ', 1)[0] for l in open(BT.list_path(s, 'Spring')) if not l.startswith('#')]

def test_a_partial_move_refused_under_the_locks_moves_nothing(setup, monkeypatch):
    """Review 10 H1: c is free when the plan is shown, then a job is queued for it; the check under the locks refuses
    before anything moves, so the book list, the record and the Trash all still agree."""
    s = S(setup); B = batch(setup, s)
    real = TR._locks
    def racing(Rs):
        j = jobs.create(s['jobs'], 'batch-estimate', 'batches/Spring/c', ['true'], {}, R=str(B / 'c'))
        return real(Rs)
    monkeypatch.setattr(TR, '_locks', racing)
    with pytest.raises(TR.Refused, match='waiting to start'): TR.move_batch(s, 'Spring', ['a', 'c'])
    assert (B / 'a').is_dir() and not (setup / 'Trash').exists() and _listed(s) == ['a', 'b', 'c'] and not (B / 'trashed.json').exists()
    assert [b['name'] for b in json.load(open(BT.meta_path(s, 'Spring')))['books']] == ['a', 'b', 'c']

def test_a_partial_move_that_errors_halfway_forgets_what_it_moved(setup, monkeypatch):
    """Review 10 H1: an error after the first PDF moved: that PDF is out of the batch (book list, record,
    trashed.json, the log), so "Run the Unfinished PDFs Again" never queues it."""
    s = S(setup); B = batch(setup, s)
    real, n = TR._rename, []
    def failing(s_, src, base):
        n.append(base)
        if len(n) == 2: raise OSError('disk trouble')
        return real(s_, src, base)
    monkeypatch.setattr(TR, '_rename', failing)
    with pytest.raises(OSError): TR.move_batch(s, 'Spring', ['a', 'c'])
    assert (setup / 'Trash' / 'batch - Spring - a').is_dir() and (B / 'c').is_dir()
    assert _listed(s) == ['b', 'c'] and [b['name'] for b in json.load(open(BT.meta_path(s, 'Spring')))['books']] == ['b', 'c']
    assert [x['name'] for x in json.load(open(B / 'trashed.json'))] == ['a']
    assert json.load(open(os.path.join(s['jobs'], 'trash-log.json')))[-1]['pdf'] == 'a'
    for j in jobs.all_jobs(s['jobs']):
        if j['kind'] == 'summary': jobs.update(s['jobs'], j['id'], status='done')   # as the dispatcher would run it
    assert all(j['run'] != 'batches/Spring/a' for j in BT.again(s, 'Spring'))

def test_a_picked_pdf_with_no_folder_is_only_forgotten(setup):
    import shutil
    s = S(setup); B = batch(setup, s)
    shutil.rmtree(B / 'c')                                                      # its estimate failed before a folder was made
    r = TR.move_batch(s, 'Spring', ['a', 'c'])
    assert r['moved'] == ['a'] and r['forgotten'] == ['c']
    assert _listed(s) == ['b'] and [b['name'] for b in json.load(open(BT.meta_path(s, 'Spring')))['books']] == ['b']
    assert [x['name'] for x in json.load(open(B / 'trashed.json'))] == ['a']                 # only what is in the Trash
    assert sorted(os.listdir(setup / 'Trash')) == ['batch - Spring - a']

def test_nothing_selected_is_never_the_whole_batch(setup):
    s = S(setup); batch(setup, s)
    with pytest.raises(TR.Refused, match='Select one or more'): TR.plan_batch(s, 'Spring', [])

def test_a_second_pdf_of_the_same_name_keeps_its_extension(setup):
    """Review 10 L2: "ilokano 2.pdf" and "ilokano 2.json", never "ilokano.pdf 2"."""
    s = S(setup); (setup / 'Trash').mkdir(); (setup / 'Trash' / 'bk.pdf').write_bytes(b'x'); (setup / 'Trash' / 'bk.json').write_text('{}')
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book')); (setup / 'uploads' / 'bk.json').write_text('{}')
    TR.move_pdf(s, BK.listing(s)[0]['key'])
    assert (setup / 'Trash' / 'bk 2.pdf').exists() and (setup / 'Trash' / 'bk 2.json').exists()


def test_the_warning_says_per_run_whether_review_again_still_works(setup):
    """Patrick, 2026-11-07: a run whose intake kept its own copy still reviews again; never claim it doesn't."""
    s = S(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book')); key = BK.listing(s)[0]['key']
    finished_run(setup, label='tagged', sha=key)
    own = finished_run(setup, label='untagged', sha=key)
    rec = json.loads((own / 'record.json').read_text()); rec['intake'] = {'result': {'pdf': 'intake.pdf'}}; (own / 'record.json').write_text(json.dumps(rec))
    eff = {r['name']: r['effect'] for r in TR.plan_pdf(s, key)['runs']}
    assert eff == {'tagged': TR.NEEDS_BACK, 'untagged': TR.STILL_WORKS}
    (setup / 'samples' / 'copy.pdf').write_bytes((setup / 'uploads' / 'bk.pdf').read_bytes())   # another copy: found by sha256
    assert 'still works' in {r['name']: r['effect'] for r in TR.plan_pdf(s, key)['runs']}['tagged']
