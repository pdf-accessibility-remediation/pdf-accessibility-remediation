"""test_webapp_handedit.py: Bring Back an Edited PDF in the app (webapp/runs.py start_bring_back, the bring-back route, the
panel), the run state's uploads and hand edits, and downloads of the current version logged as exports (#62).

    python -m pytest tests/test_webapp_handedit.py -q

No book, no model: the job is queued and checked, never run (tests/test_handedit.py runs handedit.py itself).
"""
import os, sys, json, socket, hashlib, http.client, urllib.parse
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import jobs, runs  # noqa: E402
from test_webapp import setup, settings, get, app, wait  # noqa: E402,F401  (fixtures)
from test_webapp_panel import post  # noqa: E402
from test_webapp_checks import mapp, req  # noqa: E402,F401

def src(rel): return open(os.path.join(HERE, rel), encoding='utf-8').read()
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def finished_run(t):
    """runs/book/r1: a finished run whose PDF is the one its record describes."""
    R = t / 'runs' / 'book' / 'r1'; R.mkdir(parents=True, exist_ok=True)
    (R / 'book_remediated.pdf').write_bytes(b'%PDF-1.7 result')
    (R / 'record.json').write_text(json.dumps({'document': {'output': 'book_remediated.pdf', 'output_sha256': sha(R / 'book_remediated.pdf')}}))
    return R

def upload(t, name='edited.pdf', data=b'%PDF-1.7 edited'):
    (t / 'uploads').mkdir(exist_ok=True); (t / 'uploads' / name).write_bytes(data); return t / 'uploads' / name

# ------------------------------------------------------------------ start_bring_back
def test_bring_back_queues_handedit_import_as_a_new_run(setup):
    s = settings(setup); R = finished_run(setup); f = upload(setup)
    j = runs.start_bring_back(s, 'book/r1', str(R), 'edited.pdf', ' Pat ', 'replaced the photo on PDF 12')
    assert j['kind'] == 'bring_back' and j['what'] == 'Bring Back an Edited PDF' and j['status'] == 'queued'
    label = j['argv'][-1]
    assert j['argv'][1:] == ['handedit.py', 'import', str(R), str(f), '--by', 'Pat', '--note', 'replaced the photo on PDF 12', '--label', label]
    assert label.startswith('handedit-') and j['child'] == f'book/{label}'
    assert 'DECIDE' not in j['env'] and 'REVIEW' not in j['env']                # handedit.py sets them for run_api.sh itself
    v = runs.job_view(s, jobs.update(s['jobs'], j['id'], status='done', ended='2026-11-09T10:00:00'))
    assert v['title'] == f'Bring Back an Edited PDF → brought back as {label} (10:00 AM)' and v['child_url'] is None
    (setup / 'runs' / 'book' / label).mkdir()
    assert runs.job_view(s, jobs.load(s['jobs'], j['id']))['child_url'] == f'/run/book/{label}/'

def test_the_label_never_reuses_a_folder(setup, monkeypatch):
    s = settings(setup); R = finished_run(setup); upload(setup)
    import datetime as DT
    class Fixed(DT.datetime):
        @classmethod
        def now(cls, tz=None): return cls(2026, 11, 9, 10, 0)
    monkeypatch.setattr(runs.datetime, 'datetime', Fixed)
    (setup / 'runs' / 'book' / 'handedit-20261109-1000').mkdir()
    j = runs.start_bring_back(s, 'book/r1', str(R), 'edited.pdf', 'Pat', 'n')
    assert j['argv'][-1] == 'handedit-20261109-1000-2'

@pytest.mark.parametrize('name, by, note, words', [
    ('gone.pdf', 'Pat', 'n', 'is not in the uploads folder'),
    ('../edited.pdf', 'Pat', 'n', 'is not in the uploads folder'),
    ('edited.txt', 'Pat', 'n', 'Choose the edited PDF'),
    (None, 'Pat', 'n', 'Choose the edited PDF'),
    ('edited.pdf', '', 'n', 'Say who edited the PDF'),
    ('edited.pdf', 'Pat', '  ', 'Say what was changed'),
    ('edited.pdf', 'Pat', 'a\nb', 'in one line'),
    ('edited.pdf', 'Pat', 'x' * 201, 'in one line')])
def test_bring_back_refuses_with_words_for_the_dialog(setup, name, by, note, words):
    s = settings(setup); R = finished_run(setup); upload(setup)
    with pytest.raises(ValueError, match=words): runs.start_bring_back(s, 'book/r1', str(R), name, by, note)
    assert jobs.all_jobs(s['jobs']) == []

def test_bring_back_refuses_the_same_file_and_a_run_whose_pdf_changed(setup):
    s = settings(setup); R = finished_run(setup)
    upload(setup, 'same.pdf', (R / 'book_remediated.pdf').read_bytes())
    with pytest.raises(ValueError, match='same file as this run'): runs.start_bring_back(s, 'book/r1', str(R), 'same.pdf', 'Pat', 'n')
    upload(setup); (R / 'book_remediated.pdf').write_bytes(b'%PDF-1.7 edited in place')
    with pytest.raises(ValueError, match='was changed after the run made it'): runs.start_bring_back(s, 'book/r1', str(R), 'edited.pdf', 'Pat', 'n')
    (R / 'record.json').unlink()
    with pytest.raises(ValueError, match='not finished'): runs.start_bring_back(s, 'book/r1', str(R), 'edited.pdf', 'Pat', 'n')

def test_a_refusal_from_handedit_is_the_job_cards_reason(setup):
    assert "print(msg if msg == __doc__ else f'refused: {msg}', file=sys.stderr)" in src('handedit.py')
    v = {'status': 'failed', 'outcome': 'refused: the edited PDF is not supported yet: PDF 2.0', 'exit': 3}
    assert runs.reason(v) == 'The edited PDF is not supported yet: PDF 2.0'

# ------------------------------------------------------------------ the run state
def child(t, R, label, to='review', state='not started'):
    """An edited copy of R, as handedit.py import leaves it: its _handedit/ only (not started), stopped for review, or finished."""
    C = t / 'runs' / 'book' / label; (C / '_handedit').mkdir(parents=True)
    (C / '_handedit' / 'edited.pdf').write_bytes(b'%PDF-1.7 edited ' + label.encode())
    (C / '_handedit' / 'hand_edit.json').write_text(json.dumps({'to': to, 'by': 'Pat', 'note': 'new photo', 'edited': {'file': 'edited.pdf'},
                                                                'parent': {'run': str(R)}}))
    if state == 'waiting': (C / 'workorder.ai.json').write_text('{}')
    if state == 'finished': (C / 'record.json').write_text(json.dumps({'hand_edit': {'parent': {'run': str(R)}}}))
    hp = R / 'hand_edits.json'; d = json.loads(hp.read_text()) if hp.exists() else {'exports': [], 'children': []}
    d['children'].append({'when': '2026-11-09T10:00:00', 'run': str(C), 'by': 'Pat', 'note': 'new photo'}); hp.write_text(json.dumps(d))
    return C

def test_each_edited_copy_says_its_state_and_only_real_runs_are_linked(setup):
    s = settings(setup); R = finished_run(setup)
    assert runs.hand_edits(s, str(R), {}) is None
    child(setup, R, 'done', state='finished'); child(setup, R, 'wait', state='waiting'); child(setup, R, 'cold'); child(setup, R, 'paid', to='pipeline')
    d = json.loads((R / 'hand_edits.json').read_text())
    d['children'].append({'when': '2026-11-08T10:00:00', 'run': str(setup / 'runs' / 'book' / 'gone'), 'by': 'Kim', 'note': 'old'})
    (R / 'hand_edits.json').write_text(json.dumps(d))
    he = runs.hand_edits(s, str(R), {})
    assert he['parent'] is None and [(c['label'], c['state'], c['url'], c['startable']) for c in he['children']] == [
        ('done', 'finished', '/run/book/done/', False), ('wait', 'waiting for its review', '/run/book/wait/', False),
        ('cold', 'not started', None, True), ('paid', 'not started', None, False), ('gone', 'removed', None, False)]
    j = runs.resume_bring_back(s, 'book/r1', str(R), 'cold')                      # being prepared while its job is queued
    assert next(c for c in runs.hand_edits(s, str(R), {})['children'] if c['label'] == 'cold')['state'] == 'being prepared'
    assert runs.hand_edits(s, str(setup / 'runs' / 'book' / 'done'), {'hand_edit': {'parent': {'run': str(R)}}})['parent'] == {
        'label': 'book/r1', 'url': '/run/book/r1/'}

def test_start_runs_the_same_import_again_for_a_copy_never_run(setup):
    s = settings(setup); R = finished_run(setup); C = child(setup, R, 'cold')
    j = runs.resume_bring_back(s, 'book/r1', str(R), 'cold')
    assert j['kind'] == 'bring_back' and j['child'] == 'book/cold' and j['argv'][1:] == [
        'handedit.py', 'import', str(R), str(C / '_handedit' / 'edited.pdf'), '--by', 'Pat', '--note', 'new photo', '--label', 'cold']

@pytest.mark.parametrize('label, state, to, words', [('paid', 'not started', 'pipeline', 'full pipeline'), ('wait', 'waiting', 'review', 'nothing to start'),
                                                      ('nope', None, None, 'No edited copy')])
def test_start_is_refused_for_a_paid_copy_one_already_run_and_an_unknown_name(setup, label, state, to, words):
    s = settings(setup); R = finished_run(setup)
    if state: child(setup, R, label, to=to, state=state)
    with pytest.raises(ValueError, match=words): runs.resume_bring_back(s, 'book/r1', str(R), label)

# ------------------------------------------------------------------ the route and the panel
def test_the_bring_back_route(app):
    port, t, R = app['port'], app['t'], app['R']
    rec = json.loads((R / 'record.json').read_text()); rec['document']['output_sha256'] = sha(R / 'book_remediated.pdf')
    (R / 'record.json').write_text(json.dumps(rec))
    st, b = post(port, '/api/run/book/r1/bring-back', {'file': 'edited.pdf', 'by': 'Pat', 'note': 'n'})
    assert st == 409 and 'is not in the uploads folder' in b['error']
    upload(t)
    st, b = post(port, '/api/run/book/r1/bring-back', {'file': 'edited.pdf', 'by': 'Pat', 'note': 'n'})
    assert st == 202 and b['job']['kind'] == 'bring_back'
    st, b = post(port, '/api/run/book/r1/bring-back', {'file': 'edited.pdf', 'by': 'Pat', 'note': 'n'})
    assert st == 409 and 'already' in b['error']                                    # one job per run

def test_the_panel_has_the_button_the_dialog_and_the_links():
    p = src('webapp/panel.js')
    assert 'data-act="bring-back"' in p and "api(API + '/bring-back', { file:" in p
    assert '<label for="pp-bring-by">Edited By</label>' in p and 'autocomplete="name"' in p and 'role="alert"' in p
    assert 'uncheck "Recognize scanned text."' in p and 'no AI call, no cost. This run is not changed.' in p
    assert '<input type="file" id="pp-bring-file" accept="application/pdf,.pdf">' in p and "'Uploading… '" in p and 'xhr.abort()' in p
    assert 'uploads folder' not in p                                                 # the person never sees a folder (app.md)
    assert 'data-act="bring-start"' in p and '{ resume: b.dataset.label }' in p
    assert 'Open the Edited Run' in p and "tc('Edited copies')" in p and 'Made from an edited copy of run ' in p

# ------------------------------------------------------------------ a download of the current version, logged as an export
def test_a_current_pdf_download_is_logged_as_an_export(mapp):
    port, R = mapp['port'], mapp['R']
    RUN = 'batches/d1/sample'
    st, body, h = req(port, 'GET', f'/run/{RUN}/download?what=pdf&v=current')
    assert st == 200
    ex = json.load(open(os.path.join(R, 'hand_edits.json')))['exports']
    assert len(ex) == 1 and ex[0]['via'] == 'app download' and ex[0]['by'] is None and ex[0]['base'] == 'output'
    assert ex[0]['sha256'] == sha(os.path.join(R, 'sample_remediated.pdf'))
    assert req(port, 'GET', f'/run/{RUN}/download?what=record&v=current')[0] == 200
    assert len(json.load(open(os.path.join(R, 'hand_edits.json')))['exports']) == 1      # the record ZIP is not an export

def test_a_log_that_cannot_be_written_never_stops_the_download(mapp):
    port, R = mapp['port'], mapp['R']
    os.mkdir(os.path.join(R, 'hand_edits.json'))                                        # a folder where the log would go
    assert req(port, 'GET', '/run/batches/d1/sample/download?what=pdf&v=current')[0] == 200

# ------------------------------------------------------------------ the upload (POST /api/run/<run>/upload, raw PDF bytes)
def put(port, path, data, name='edited.pdf', ctype='application/pdf', length=None, origin=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
    try:
        c.putrequest('POST', path, skip_host=True, skip_accept_encoding=True)
        c.putheader('Host', f'127.0.0.1:{port}'); c.putheader('Content-Type', ctype)
        c.putheader('Content-Length', str(len(data)) if length is None else length)
        if name is not None: c.putheader('X-File-Name', urllib.parse.quote(name))
        if origin: c.putheader('Origin', origin)
        c.endheaders(data)
        r = c.getresponse(); return r.status, json.loads(r.read() or b'{}')
    except OSError: return None, {}
    finally: c.close()

def test_an_uploaded_pdf_is_saved_under_a_clean_name_and_never_replaces_another(app):
    port, t = app['port'], app['t']; U = t / 'uploads'
    st, b = put(port, '/api/run/book/r1/upload', b'%PDF-1.7 one', 'edited.pdf')
    assert st == 200 and b == {'file': 'edited.pdf', 'sha256': hashlib.sha256(b'%PDF-1.7 one').hexdigest(), 'size': 12}
    assert (U / 'edited.pdf').read_bytes() == b'%PDF-1.7 one'
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7 one', 'edited.pdf')[1]['file'] == 'edited.pdf'    # the same file: its name
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7 two', 'edited.pdf')[1]['file'] == 'edited-2.pdf'  # another: a new name
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7 x', '../../x\x01y')[1]['file'] == 'x_y.pdf'
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7 z', '.hidden.PDF')[1]['file'] == 'hidden.pdf'
    assert sorted(os.listdir(U)) == ['edited-2.pdf', 'edited.pdf', 'hidden.pdf', 'x_y.pdf']   # no .part file left

def test_an_upload_is_refused_before_anything_is_kept(app):
    port, t = app['port'], app['t']
    assert put(port, '/api/run/book/r1/upload', b'not a pdf at all')[0] == 400
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7', ctype='application/json')[0] == 415
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7', length='12a')[0] == 411
    assert put(port, '/api/run/book/r1/upload', b'%PDF-1.7', origin='http://evil.example')[0] == 403
    assert put(port, '/api/run/book/nope/upload', b'%PDF-1.7')[0] == 404
    st, b = put(port, '/api/run/book/r1/upload', b'%PDF-1.7', length=str(600 * 1_000_000))
    assert st == 413 and b['error'] == 'The PDF is larger than the app accepts (500 MB).'
    sk = socket.create_connection(('127.0.0.1', port))                             # Cancel: the body stops before its length
    sk.sendall(f'POST /api/run/book/r1/upload HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/pdf\r\n'
               f'Content-Length: 100000\r\nX-File-Name: half.pdf\r\n\r\n'.encode() + b'%PDF-1.7 half'); sk.close()
    parts = lambda: [f for f in (os.listdir(t / 'uploads') if (t / 'uploads').exists() else []) if f.endswith('.part') or f == 'half.pdf']
    assert wait(lambda: parts() == [], 10), parts()

def test_upload_then_bring_back_queues_the_import_of_that_file(app):
    port, t, R = app['port'], app['t'], app['R']
    rec = json.loads((R / 'record.json').read_text()); rec['document']['output_sha256'] = sha(R / 'book_remediated.pdf')
    (R / 'record.json').write_text(json.dumps(rec))
    st, u = put(port, '/api/run/book/r1/upload', b'%PDF-1.7 edited', 'My edit.pdf')
    st, b = post(port, '/api/run/book/r1/bring-back', {'file': u['file'], 'by': 'Pat', 'note': 'new photo'})
    assert st == 202
    j = jobs.load(str(t / 'runs' / '.app'), b['job']['id'])
    assert j['argv'][4] == str(t / 'uploads' / 'My edit.pdf')
