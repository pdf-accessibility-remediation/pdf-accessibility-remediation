"""test_clear.py: "Clear This Book's Files" (#45, review/clear.py; 03 §10) on synthetic shipped runs only: the gate, each
condition alone; exactly the listed files deleted (PDFs and images at named places, versions/ai's PDF included), every
record kept; release/cleared.json planned → done; a clear that stopped partway finished by re-hashing; every change
refused afterwards in the pipeline layer; the shipped copy still downloads (02 B2); the download record. No book, no model.

    python -m pytest tests/test_clear.py -q
"""
import os, sys, json, hashlib, io
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from review import clear as CL, sessions as S, prune, manual as M, ocr as O  # noqa: E402
from lib import release as REL  # noqa: E402
from webapp import downloads as DL  # noqa: E402

def sha(b): return hashlib.sha256(b).hexdigest()

def shipped_run(t, downloaded=True, shipped=True):
    R = t / 'runs' / 'bk' / 'r1'
    pdf = b'%PDF-1.7 the shipped result'
    for d in ('release/shipped/001', 'reviews/versions/ai', 'reviews/versions/001', 'reviews/_audit/ocr_words', 'reviews/sessions', '_intake', '_audit/figs'):
        (R / d).mkdir(parents=True, exist_ok=True)
    (R / 'bk_remediated.pdf').write_bytes(pdf)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'bk.pdf', 'output': 'bk_remediated.pdf', 'output_sha256': sha(pdf), 'pages': 3},
                                              'run': {'started': '2026-11-01T10:00:00'}, 'review': {'session': '001'}}))
    for f, b in (('review.md', b'# r'), ('review.html', b'<html></html>'), ('han_review.csv', b'a,b'), ('workorder.ai.json', b'{}'),
                 ('reviews/versions/ai/bk_remediated.pdf', b'%PDF ai'), ('reviews/versions/ai/record.json', b'{"document": {"output": "bk_remediated.pdf"}}'),
                 ('reviews/versions/001/bk_remediated.pdf', b'%PDF 001'), ('reviews/versions/001/review.md', b'# 1'),
                 ('reviews/versions/001/record.json', b'{"document": {"output": "bk_remediated.pdf"}}'),
                 ('reviews/_audit/digest.json', b'{}'), ('reviews/_audit/ocr_words/s1.png', b'png'), ('reviews/sessions/001.json', b'{"id": "001", "status": "applied"}'),
                 ('_intake/intake.pdf', b'%PDF intake'), ('_intake/intake.json', b'{"status": "done"}'), ('_audit/figs/f1.jpg', b'jpg'), ('_audit/verapdf.json', b'{}'),
                 ('release/shipped/001/bk_remediated.pdf', pdf), ('release/shipped/001/review.html', b'<html></html>')):
        (R / f).write_bytes(b)
    if shipped:
        (R / 'release' / 'shipped.json').write_text(json.dumps([{'n': 1, 'shipped': '2026-11-02T10:00:00', 'by': 'Kim', 'pdf': {'sha256': sha(pdf), 'file': 'bk_remediated.pdf', 'session': '001'}}]))
    if downloaded:
        (R / 'release' / 'downloads.json').write_text(json.dumps([{'what': 'record', 'sha256': sha(pdf), 'shipment': 1, 'complete': True, 'at': '2026-11-03T10:00:00'}]))
    return R

DELETED = {'bk_remediated.pdf', '_intake/intake.pdf', 'reviews/versions/ai/bk_remediated.pdf', 'reviews/versions/001/bk_remediated.pdf',
           'reviews/_audit/ocr_words/s1.png', '_audit/figs/f1.jpg'}

def files(R): return {os.path.relpath(os.path.join(d, f), R) for d, _, fs in os.walk(R) for f in fs if f not in ('.record.lock', '.lock')}

def test_clear_deletes_exactly_the_listed_files(tmp_path):
    R = shipped_run(tmp_path); before = files(R)
    g = CL.gate(str(R))
    assert g['ok'] and g['shipment'] == 1
    assert {x['path'] for x in CL.plan(str(R), g['sha'])} == DELETED
    c = CL.clear(str(R), 'Kim', 'CLEAR')
    assert c['state'] == 'done' and {x['path'] for x in c['files']} == DELETED and c['freed_bytes'] == sum(x['bytes'] for x in c['files'])
    assert all(len(x['sha256']) == 64 for x in c['files'])                               # each deleted file with its sha256
    assert files(R) == (before - DELETED) | {'release/cleared.json'}                      # every record, the shipped copy kept
    assert (R / 'release' / 'shipped' / '001' / 'bk_remediated.pdf').exists() and (R / 'reviews' / 'versions' / 'ai' / 'record.json').exists()
    assert json.load(open(R / 'release' / 'cleared.json'))['state'] == 'done'

@pytest.mark.parametrize('broken,words', [
    ('not_shipped', 'Only a shipped book'), ('no_download', 'Download the record'), ('copy_changed', 'shipped copy'),
    ('open_session', 'session of this book is open'), ('promoting', 'being made'), ('busy', 'A job'), ('cleared', 'cleared already'),
    ('changed_pdf', 'Only a shipped book')])
def test_each_gate_condition_alone_refuses(tmp_path, broken, words):
    R = shipped_run(tmp_path, downloaded=broken != 'no_download', shipped=broken != 'not_shipped')
    if broken == 'copy_changed': (R / 'release' / 'shipped' / '001' / 'bk_remediated.pdf').write_bytes(b'%PDF other')
    if broken == 'open_session': (R / 'reviews' / 'sessions' / '002.json').write_text('{"id": "002", "status": "open"}')
    if broken == 'promoting': (R / 'reviews' / 'promoting.json').write_text('{}')
    if broken == 'cleared': (R / 'release' / 'cleared.json').write_text('{"state": "done"}')
    if broken == 'changed_pdf': (R / 'bk_remediated.pdf').write_bytes(b'%PDF changed by hand')
    busy = (lambda: 'A job for this run is already running.') if broken == 'busy' else None
    assert not CL.gate(str(R), busy=busy)['ok'] and words in CL.gate(str(R), busy=busy)['why']
    before = files(R)
    with pytest.raises(S.Refused, match=words): CL.clear(str(R), 'Kim', 'CLEAR', busy=busy)
    assert files(R) == before                                                            # nothing deleted

def test_name_and_confirmation_are_required(tmp_path):
    R = shipped_run(tmp_path)
    with pytest.raises(S.Refused, match='Your Name'): CL.clear(str(R), '', 'CLEAR')
    with pytest.raises(S.Refused, match='Type CLEAR'): CL.clear(str(R), 'Kim', 'clear please')
    assert (R / 'bk_remediated.pdf').exists()

def test_a_clear_that_stopped_partway_is_finished_by_rehashing(tmp_path):
    R = shipped_run(tmp_path)
    items = CL.plan(str(R), CL.gate(str(R))['sha'])
    (R / 'release' / 'cleared.json').write_text(json.dumps({'schema': CL.SCHEMA, 'state': 'planned', 'by': 'Kim', 'shipment': 1, 'files': items}))
    os.remove(R / '_intake' / 'intake.pdf')                                              # deleted before the stop
    (R / '_audit' / 'figs' / 'f1.jpg').write_bytes(b'changed since the plan')           # changed: kept, named
    assert S.Refused and REL.cleared(str(R))['state'] == 'planned'
    with pytest.raises(S.Refused): S.not_cleared(str(R))                                 # planned already means read only
    c = CL.clear(str(R), 'Lee', 'CLEAR')
    assert c['state'] == 'done' and c['kept_changed'] == ['_audit/figs/f1.jpg'] and (R / '_audit' / 'figs' / 'f1.jpg').exists()
    assert not (R / 'reviews' / 'versions' / 'ai' / 'bk_remediated.pdf').exists() and c['finished_by'] == 'Lee'

def test_everything_is_refused_afterwards(tmp_path):
    R = shipped_run(tmp_path); CL.clear(str(R), 'Kim', 'CLEAR')
    for f in (lambda: S.pin(str(R)), lambda: S.replay_to(str(R), str(tmp_path / 'new')), lambda: S.open_session(str(R), {}),
              lambda: S.reapply(str(R), {'id': '002'}), lambda: M.record(str(R), 'pac', {}), lambda: M.ship(str(R), 'Kim'),
              lambda: prune.remove(str(R), [{'id': '001', 'sha256': 'x'}], 'Kim'), lambda: O.record(str(R), {}, 'page')):
        with pytest.raises(S.Refused, match='cleared'): f()

def test_the_shipped_copy_still_downloads(tmp_path):
    """02 B2: with the working PDF gone, the shipment's copy is listed (and no "current" entry), and both downloads build from it."""
    R = shipped_run(tmp_path); CL.clear(str(R), 'Kim', 'CLEAR')
    rec = json.load(open(R / 'record.json'))
    vs = DL.versions(str(R), rec)
    assert [v['id'] for v in vs] == ['shipment-1']
    d = DL.prepare(str(R), 'bk/r1', 'shipment-1', 'pdf'); got = d['fh'].read(); d['fh'].close()
    assert got == (R / 'release' / 'shipped' / '001' / 'bk_remediated.pdf').read_bytes()
    d = DL.prepare(str(R), 'bk/r1', 'shipment-1', 'record'); out = io.BytesIO(); DL.stream_zip(out, d)
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(out.getvalue()))
    assert any(n.endswith('/bk_remediated.pdf') for n in z.namelist()) and any(n.endswith('/READ-ME.txt') for n in z.namelist())
    with pytest.raises(DL.Refused): DL.prepare(str(R), 'bk/r1', 'current', 'pdf')

def test_the_download_record_counts_only_a_live_shipment(tmp_path):
    R = shipped_run(tmp_path, downloaded=False)
    rec = json.load(open(R / 'record.json'))
    d = DL.prepare(str(R), 'bk/r1', 'current', 'record'); DL.stream_zip(io.BytesIO(), d)
    e = DL.note_download(d)
    assert e['shipment'] == 1 and e['complete'] and json.load(open(R / 'release' / 'downloads.json'))[0]['sha256'] == e['sha256']
    assert CL.gate(str(R))['ok']
    d = DL.prepare(str(R), 'bk/r1', '001', 'record'); DL.stream_zip(io.BytesIO(), d)
    assert DL.note_download(d) is None and len(json.load(open(R / 'release' / 'downloads.json'))) == 1   # not a shipment: not counted

def test_clean_up_space_before_shipping_still_keeps_the_ai_version(tmp_path):
    """K9 holds for "Clean Up Space"; only clearing a shipped book deletes versions/ai's PDF (Patrick, 2026-11-05)."""
    R = shipped_run(tmp_path, shipped=False)
    assert 'ai' not in [x['id'] for x in prune.plan(str(R))]

def test_records_are_never_images_and_only_pdfs_and_images_go():
    src = open(os.path.join(HERE, 'review', 'clear.py'), encoding='utf-8').read()
    assert "IMAGES = ('.png', '.jpg', '.jpeg')" in src and "if f.lower().endswith('.pdf'): add(" in src and 'rmtree' not in src

def test_an_unreadable_clearing_record_is_never_overwritten(tmp_path):
    """05 H1: garbage in cleared.json: no offer, no clear, the file unchanged, the run still read only."""
    R = shipped_run(tmp_path)
    (R / 'release' / 'cleared.json').write_text('garbage{')
    g = CL.gate(str(R))
    assert not g['ok'] and g['why'] == CL.UNREADABLE
    with pytest.raises(S.Refused, match='clearing record can.t be read'): CL.clear(str(R), 'Kim', 'CLEAR')
    assert (R / 'release' / 'cleared.json').read_text() == 'garbage{' and (R / 'bk_remediated.pdf').exists()
    with pytest.raises(S.Refused, match='cleared'): S.not_cleared(str(R))

def test_while_a_clear_is_under_way_only_shipped_copies_are_listed(tmp_path):
    """05 L3: a planned clear lists the shipped copies only, not the versions whose PDFs are about to go."""
    R = shipped_run(tmp_path)
    (R / 'release' / 'cleared.json').write_text(json.dumps({'state': 'planned', 'files': []}))
    vs = DL.versions(str(R), json.load(open(R / 'record.json')))
    assert [v['id'] for v in vs] == ['shipment-1']
