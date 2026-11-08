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
    page = NR.form_part(s, '', run='bk/First')
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
    page = NR.form_part(s, '', run='batches/Spring/a')                                                              # New Run of This PDF
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
    page = BT.form_part(s, [], saved='Later')
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
    assert get(app['port'], '/batch/Later/')[2].get('Location') == '/?view=batches&open=Later'           # T4: its pop-up on the home page
    page = json.loads(get(app['port'], '/api/form?what=batch&saved=Later')[1])['html']
    assert '<h2 id="dlg-h">New Batch</h2>' in page and page.count('>Remove from Batch</button>') == 3 and 'Save Batch for Later' in page and 'data-cancel>Cancel' in page
    assert jpost(app['port'], '/api/batch/Later/remove', {'book': 'c'}) == (200, {'removed': True})
    assert jpost(app['port'], '/api/batch/Later/remove', {'book': 'b'})[0] == 200
    st, d = jpost(app['port'], '/api/batch/Later/start', {'label': 'Later'})
    assert st == 409 and 'two or more' in d['error']
    assert sorted(b['file'] for b in BK.listing(settings(t))) == ['b.pdf', 'c.pdf']

NO_OCR = [{'id': 'ocrmypdf', 'ok': False}, {'id': 'tesseract', 'ok': False}, {'id': 'tesseract_langs', 'ok': False}]
OCR_OK = [{'id': 'ocrmypdf', 'ok': True}, {'id': 'tesseract', 'ok': True}, {'id': 'tesseract_langs', 'ok': True}]

@pytest.mark.parametrize('tools', [NO_OCR, OCR_OK], ids=['ocr-missing', 'ocr-installed'])
def test_saving_a_batch_never_needs_ocr_and_get_the_estimates_checks_it(setup, tools):
    """PR #88's CI (Patrick, 2026-11-08): "Save Batch for Later" runs nothing, so it saves untagged PDFs whatever is
    installed; "Get the Estimates" (start_saved) is where a missing OCR refuses them, and the batch stays saved. The
    machine's own tools never decide: both cases are given here."""
    s = S(setup); keys = three(setup, s)                                    # synthetic PDFs with no tag tree: untagged
    assert all(BK.read_meta(b['path']).get('tagged') is False for b in BK.listing(s))
    BT.start(s, tools, keys, 'Later', estimate=False)
    assert BT.saved(s, 'Later') and BK.listing(s) == []
    if tools is NO_OCR:
        with pytest.raises(ValueError, match=r"Text recognition \(OCR\) isn't set up on this computer"): BT.start_saved(s, tools, 'Later', 'Later')
        assert BT.saved(s, 'Later') and not jobs.all_jobs(s['jobs'])           # nothing started, still "Save Batch for Later"
    else:
        assert len(BT.start_saved(s, tools, 'Later', 'Later')) == 3 and not BT.saved(s, 'Later')

def test_new_batch_still_checks_ocr_when_it_estimates_at_once(setup):
    s = S(setup); keys = three(setup, s)
    with pytest.raises(ValueError, match=r"Text recognition \(OCR\) isn't set up"): BT.start(s, NO_OCR, keys, 'Now')
    assert sorted(b['file'] for b in BK.listing(s)) == ['a.pdf', 'b.pdf', 'c.pdf']   # nothing moved

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

# ------------------------------------------------------------------ review 18: 18-L1, 18-N1, 18-N3
def test_a_saved_batch_whose_trash_move_is_refused_gives_nothing_back(setup, monkeypatch):
    """18-L1: the PDFs go back to the upload list only once the batch folder has moved; a refused move (the Trash on
    another disk) leaves the batch as it was, its PDFs inside it."""
    s = S(setup); keys = three(setup, s)
    BT.start(s, [], keys, 'Later', estimate=False)
    def refuse(*a, **k): raise TR.Refused('The Trash is on another disk.')
    monkeypatch.setattr(TR, '_rename', refuse)
    with pytest.raises(TR.Refused): TR.move_batch(s, 'Later')
    assert BK.listing(s) == [] and BT.saved(s, 'Later')
    assert all((setup / 'runs' / 'batches' / 'Later' / n / 'source' / f'{n}.pdf').is_file() for n in 'abc')

def test_give_back_never_replaces_a_pdf_uploaded_meanwhile(setup):
    """18-N1: a moved PDF put back when its job can't be made goes through take_back: a numbered name when its own is taken."""
    s = S(setup); b = upload(setup, s)
    R = setup / 'runs' / 'bk' / 'x'; R.mkdir(parents=True)
    p, mode = NR.take_pdf(s, b, str(R))
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'Another'))                                           # uploaded meanwhile
    other = (setup / 'uploads' / 'bk.pdf').read_bytes()
    NR.give_back(s, p, mode, b['path'])
    assert (setup / 'uploads' / 'bk.pdf').read_bytes() == other and (setup / 'uploads' / 'bk-2.pdf').is_file()

def test_a_batch_whose_record_cant_be_written_undoes_the_moves(setup, monkeypatch):
    """18-N3: the batch record is written inside the rollback: when it fails, the PDFs go back and no batch is left."""
    s = S(setup); keys = three(setup, s)
    def boom(*a): raise OSError(28, 'No space left on device')
    monkeypatch.setattr(BT, '_write_meta', boom)
    with pytest.raises(OSError): BT.start(s, [], keys, 'Full')
    monkeypatch.undo()
    assert sorted(b['file'] for b in BK.listing(s)) == ['a.pdf', 'b.pdf', 'c.pdf']
    assert not (setup / 'runs' / 'batches' / 'Full').exists() and not os.path.exists(BT.list_path(s, 'Full')) and not os.path.exists(BT.meta_path(s, 'Full'))

# ------------------------------------------------------------------ T2 (the batch dashboard's "⋯") and T4 (the pop-ups)
def test_a_batch_pdfs_menu_edit_name_and_new_run(app):
    """T2: each dashboard row has a "⋯" menu (Edit Name, New Run of This PDF). Edit Name sets the PDF's display name by
    sha256 (shown wherever that file is named), never a folder, file or run name; New Run of This PDF opens New Run's pop-up."""
    from test_webapp import get
    from test_webapp_home import jpost
    t = app['t']; s = settings(t); (t / 'uploads').mkdir(exist_ok=True)
    for n in ('a', 'b'): (t / 'uploads' / f'{n}.pdf').write_bytes(pdf_bytes(1, f'Book {n}'))
    keys = {b['file']: b['key'] for b in BK.listing(s)}
    BT.start(s, [], list(keys.values()), 'Spring', estimate=False)
    assert jpost(app['port'], '/api/rename/batch-pdf', {'label': 'Spring', 'book': 'a', 'name': 'Annals, vol. 1'}) == (200, {'name': 'Annals, vol. 1'})
    assert NM.book_name(s, keys['a.pdf'], 'a.pdf') == 'Annals, vol. 1' and (t / 'runs' / 'batches' / 'Spring' / 'a' / 'source' / 'a.pdf').is_file()
    assert NM.run_name(s, 'batches/Spring/a') is None and [x['name'] for x in BT.books_of(s, 'Spring')] == ['a', 'b']
    assert jpost(app['port'], '/api/rename/batch-pdf', {'label': 'Spring', 'book': 'zz', 'name': 'x'})[0] == 409
    assert jpost(app['port'], '/api/rename/batch-pdf', {'label': '../x', 'book': 'a', 'name': 'x'})[0] == 409
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert 'data-edit="batchpdf"' in js and '>New Run of This PDF</button>' in js and 'aria-haspopup="menu"' in js and "'More Actions for ' + esc(r.book)" in js
    assert 'New Run of This PDF</a>' not in js                                                                   # the old button is gone
    f = json.loads(get(app['port'], '/api/form?what=run&run=' + 'batches/Spring/a')[1])['html']                 # New Run of This PDF
    assert '<h2 id="dlg-h">New Run</h2>' in f and 'name="run" value="batches/Spring/a"' in f and 'Annals, vol. 1' in f

def test_the_pop_ups(app):
    """T4: New Run and New Batch are pop-ups: their contents from /api/form (a heading, the fields, "Cancel"); the old pages
    go home; the dialog is a native <dialog> (Tab stays inside), Esc and Cancel close it and give focus back."""
    from test_webapp import get
    t = app['t']; s = settings(t); (t / 'uploads').mkdir(exist_ok=True)
    for n in ('a', 'b'): (t / 'uploads' / f'{n}.pdf').write_bytes(pdf_bytes(1, f'Book {n}'))
    keys = [b['key'] for b in BK.listing(s)]
    r = json.loads(get(app['port'], '/api/form?what=run&book=' + keys[0])[1])['html']
    assert '<h2 id="dlg-h">New Run</h2>' in r and 'aria-describedby="nr-name-e"' in r and '>Get the Estimate</button><button type="button" data-cancel>Cancel</button>' in r
    b = json.loads(get(app['port'], '/api/form?what=batch&book=' + keys[0] + '&book=' + keys[1])[1])['html']
    assert '<h2 id="dlg-h">New Batch</h2>' in b and 'data-api="/api/batch/new-later"' in b and 'data-cancel>Cancel' in b
    assert get(app['port'], '/api/form?what=nope')[0] == 404
    js = open(os.path.join(HERE, 'webapp', 'shared.js'), encoding='utf-8').read()
    for x in ("dlg.showModal()", "dlg.setAttribute('aria-labelledby', 'dlg-h')", "dlg.addEventListener('cancel', e => { e.preventDefault(); closeDialog(); });",
              "if (o && document.body.contains(o) && !o.closest('[hidden]')) o.focus({ preventScroll: true });", "if (o && !document.body.contains(o) && o.id) o = $(o.id);", "nameIn.setAttribute('aria-invalid', 'true')"):
        assert x in js, x
    home = get(app['port'], '/')[1].decode()
    assert '<script src="/app/shared.js" defer></script><script src="/app/home.js" defer></script>' in home and get(app['port'], '/app/shared.js')[0] == 200

# ------------------------------------------------------------------ U1, U2, U5, U6, U7
def test_new_run_of_this_pdf_says_what_it_does(setup):
    s = S(setup); keys = three(setup, s)
    BT.start(s, [], keys, 'Spring', estimate=False)
    f = NR.form_part(s, '', run='batches/Spring/a')
    assert 'This makes a separate single run with its own copy of this PDF. The batch and its run are not changed.' in f
    b = upload(setup, s, 'solo.pdf', 'Solo'); NR.start_estimate(s, [], b['key'], 'First')
    assert 'The run it comes from is not changed.' in NR.form_part(s, '', run='solo/First')
    assert 'separate' not in NR.form_part(s, upload(setup, s, 'new.pdf', 'New')['key'])      # a plain New Run says nothing more

def test_one_spinner_no_scroll_behind_pop_ups_and_equal_buttons():
    css = open(os.path.join(HERE, 'webapp', 'panel.css'), encoding='utf-8').read()
    js = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "'<span class=\"pp-spin\" aria-hidden=\"true\"></span>Applying the reviewed decisions. This page follows each step.'" not in js   # U5
    assert 'html:has(dialog[open]) { overflow: hidden; }' in css                                                  # U6
    assert '.pp-appbar .pp-btn { display: inline-flex;' in css and 'height: 34px;' in css                          # U7
    t3 = css[css.index('/* ---- T3 as revised by U2'):css.index('/* ---- end of T3 */')]                         # U2: gaps back between the three
    assert '#main > section.ship, #main > #pdfrem-checks > .pp-checks {\n  margin-top: 0' not in t3 and 'border-top-width: 0' in t3
