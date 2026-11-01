"""test_ship.py: stage 4 of #38 (21, review 22): the Ship gate (M1 and note (d)), a shipped book whose PDF changed on disk
(21 §D), a previous result's page (note (c)), Mark as Shipped (the copy, the numbering, the rollback: M2), withdrawal (N4)
and the downloads of shipped copies (M7, N3). Synthetic run folders with one-page PDFs; no model, nothing sent.

    python -m pytest tests/test_ship.py -q
"""
import os, json, shutil
import pytest
import pikepdf
from lib import release as REL, glance as G
from review import core, manual as M, sessions as S
from webapp import manualpage as MP, downloads as DL
from test_webapp_checks import make_run

FIVE = [{'what': label, 'ok': True} for _, label in G.SAFETY]
PAC_OK = {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['pac']}
SR_OK = {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['screen_reader']}

def chk(sha, items, n=1): return {'id': n, 'recorded': '2026-11-01T10:00:00', 'by': 'Kim', 'pdf': {'sha256': sha, 'which': 'current'}, 'items': items}

def ready_run(tmp_path, name='r'):
    """A run whose current version is Ready: base lines OK (a stored glance/0.5), both parts recorded on its file."""
    R = make_run(str(tmp_path / name), record_sha=True)
    rec = core.load(os.path.join(R, 'record.json'))
    rec['glance'] = {'schema': G.SCHEMA, 'ship': [{'what': w, 'ok': True, 'text': 'x'} for w in G.SHIP_BASE], 'safety': FIVE,
                     'needs_person': {'total': 0}}
    core.save(os.path.join(R, 'record.json'), rec)
    sha = rec['document']['output_sha256']
    os.makedirs(os.path.join(R, 'release'), exist_ok=True)
    core.save(os.path.join(R, 'release', 'checks.json'), {'schema': REL.SCHEMA, 'pac': [chk(sha, PAC_OK)], 'screen_reader': [chk(sha, SR_OK)]})
    return R, rec, sha

def ship_entry(sha, n=1, **kw): return {'n': n, 'shipped': '2026-11-02T09:00:00', 'by': 'Lee', 'pdf': {'sha256': sha}, **kw}

# ------------------------------------------------------------------ the gate (M1, note (d))
def test_the_gate_offers_ready_refuses_the_same_file_twice_and_reoffers_after_a_withdrawal(tmp_path):
    R, rec, sha = ready_run(tmp_path)
    assert MP.ship_gate(R, rec) == {'ok': True, 'shipped': None, 'why': None}
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry(sha)])                 # shipped: the same file never again
    g = MP.ship_gate(R, rec)
    assert g['ok'] is False and g['why'] == 'This version was shipped on November 2, 2026 (shipment 1).'
    assert MP.app_glance(R, rec, rec['glance'])['status']['current']['name'] == 'Ready'   # pre_status alone would offer it (M1)
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry(sha, withdrawn={'by': 'L', 'date': 'x', 'reason': 'r'})])
    assert MP.ship_gate(R, rec)['ok'] is True                                                # after a withdrawal: offered again
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry('b' * 64)])            # an older file shipped; this one Ready
    assert MP.ship_gate(R, rec)['ok'] is True

def test_the_gate_refuses_what_is_not_ready_in_ships_words(tmp_path):
    R, rec, sha = ready_run(tmp_path)
    core.save(os.path.join(R, 'release', 'checks.json'), {'schema': REL.SCHEMA, 'pac': [chk(sha, PAC_OK)], 'screen_reader': []})
    g = MP.ship_gate(R, rec)
    assert g['ok'] is False and g['why'] == 'This version is not ready to ship: Accessibility Evaluation still unsatisfied.'
    os.makedirs(os.path.join(R, 'reviews', 'work'))
    assert MP.ship_gate(R, rec)['why'] == "A new version of this book is being made, so this version can't be marked as shipped now."

# ------------------------------------------------------------------ a shipped book whose PDF changed on disk (21 §D, N8)
def test_a_shipped_book_whose_file_changed_keeps_shipped_with_a_warning(tmp_path):
    R, rec, sha = ready_run(tmp_path)
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry(sha)])
    doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'clans_remediated.pdf'))   # changed by hand
    st = MP.app_glance(R, rec, rec['glance'])['status']
    assert st['name'] == 'Shipped' and st['text'] == 'Shipped · The current PDF has changed since this report was made.'
    assert st['warning'] == MP.SHIPPED_WARNING and st['current']['name'] == 'Not Ready'
    assert MP.ship_gate(R, rec)['ok'] is False

# ------------------------------------------------------------------ a previous result's page (note (c))
def test_a_previous_results_page_reads_earlier_version_never_newer(tmp_path):
    import report_html as H
    R, rec, sha = ready_run(tmp_path)
    rec['review'] = {'session': '006'}; core.save(os.path.join(R, 'record.json'), rec)
    V = os.path.join(R, 'reviews', 'versions', '004'); os.makedirs(V)
    shutil.copy(os.path.join(R, 'clans_remediated.pdf'), os.path.join(V, 'clans_remediated.pdf'))
    vrec = dict(rec, review={'session': '004'}, document=dict(rec['document'], output_sha256='4' * 64))
    core.save(os.path.join(V, 'record.json'), vrec)
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry(sha)])
    st = H.glance_of(V, vrec)['status']
    assert st['text'] == 'Earlier version (the current version is Session 6)' and st['newer'] is None
    assert H.glance_of(V, vrec)['ready'] is False and 'Newer version' not in json.dumps(st)
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry('4' * 64)])            # this earlier version was itself shipped
    assert H.glance_of(V, vrec)['status']['text'] == 'Earlier version (shipped as shipment 1 on November 2, 2026; the current version is Session 6)'
