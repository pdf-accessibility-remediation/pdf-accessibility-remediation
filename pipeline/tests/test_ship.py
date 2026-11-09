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
    assert g['ok'] is False and g['why'] == 'This version was shipped on November 2, 2026 (Shipment 1).'
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
    doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'sample_remediated.pdf'), deterministic_id=True)   # changed by hand
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
    shutil.copy(os.path.join(R, 'sample_remediated.pdf'), os.path.join(V, 'sample_remediated.pdf'))
    vrec = dict(rec, review={'session': '004'}, document=dict(rec['document'], output_sha256='4' * 64))
    core.save(os.path.join(V, 'record.json'), vrec)
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry(sha)])
    st = H.glance_of(V, vrec)['status']
    assert st['text'] == 'Previous version (the current version is Session 6)' and st['newer'] is None
    assert H.glance_of(V, vrec)['ready'] is False and 'Newer version' not in json.dumps(st)
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry('4' * 64)])            # this earlier version was itself shipped
    assert H.glance_of(V, vrec)['status']['text'] == 'Previous version (shipped as Shipment 1 on November 2, 2026; the current version is Session 6)'

# ------------------------------------------------------------------ Mark as Shipped (21 §A, M2), withdrawal (N4)
PAC_REC = {'by': 'Kim', 'fields': {}, 'items': dict(PAC_OK, contrast={'result': 'fail', 'note': 'grey <b>caption</b> ## on p. 12'})}
SR_REC = {'by': 'Lee', 'fields': {'screen_reader': 'NVDA 2026.1'}, 'items': SR_OK}

def real_ready(tmp_path, name='run', extra=None, pac=None):
    """A run that stays Ready when its glance is recomputed: sections with the five safety rows, a review on the review page,
    and both parts recorded through the writer. extra: record keys set first (intake, apply); pac: the PAC result to record."""
    from test_evaluation import make_run as eval_run
    sub = tmp_path / name; sub.mkdir()
    R = eval_run(sub, True)
    rec = core.load(os.path.join(R, 'record.json'))
    rec.update(extra or {})
    rec['review'] = {'workorder': {'reviewer': 'Pat <i>', 'date': '2026-10-31', 'method': 'page', 'counts': {'approved': 3}},
                     'decisions': [{'id': 'a', 'kind': 'Alt text', 'label': 'Figure 1', 'page': 1, 'status': 'approved'},
                                   {'id': 'b', 'kind': 'Alt text', 'label': 'Figure 2', 'page': 1, 'status': 'changed'},
                                   {'id': 'c', 'kind': 'Heading or tag change', 'label': 'Chapter 1', 'page': 1, 'status': 'rejected'}]}
    rec['verify'] = {'doc': {'title': 'The Book'}}
    core.save(os.path.join(R, 'record.json'), rec)
    M.record(R, 'pac', pac or PAC_REC, say=lambda *a: None, batch=False)
    M.record(R, 'screen_reader', SR_REC, say=lambda *a: None, batch=False)
    rec = core.load(os.path.join(R, 'record.json'))
    assert MP.ship_gate(R, rec)['ok'], MP.ship_gate(R, rec)
    return R

def test_ship_copies_the_version_and_the_status_reads_shipped(tmp_path):
    R = real_ready(tmp_path)
    s = M.ship(R, 'Kim', 'first release', say=lambda *a: None, batch=False)
    F = os.path.join(R, 'release', 'shipped', '001')
    assert s['n'] == 1 and len(s['shipped']) == 19 and s['shipped'][10] == 'T' and s['issues'] == 1 and s['checks'] == {'pac': 1, 'screen_reader': 1}
    assert sorted(os.listdir(F)) == sorted(['b_remediated.pdf', 'review.md', 'review.html', 'record.json', 'evaluation-results.json',
                                            'READ-ME.txt'])   # the full set: no accessibility statement (Patrick, 2026-11-01)
    assert REL.sha_file(os.path.join(F, 'b_remediated.pdf')) == s['pdf']['sha256']
    assert '**Status:** Shipped · 1 issue noted' in open(os.path.join(F, 'review.md'), encoding='utf-8').read()
    assert 'Shipped copy (Shipment 1, ' in open(os.path.join(F, 'review.html'), encoding='utf-8').read()     # N9
    assert '**Status:** Shipped · 1 issue noted' in open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    assert s['pdf']['session'] == '001' and s['note'] == 'first release' and 'where' not in s           # reviewed before sessions were kept: Session 1
    rec = core.load(os.path.join(R, 'record.json'))
    assert MP.ship_gate(R, rec)['why'].startswith('This version was shipped on ')                       # M1
    with pytest.raises(S.Refused, match='was shipped on'): M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    assert not [x for x in os.listdir(os.path.join(R, 'release', 'shipped')) if x.endswith('.tmp')]

def test_ship_refuses_without_a_name_and_when_not_ready(tmp_path):
    R = real_ready(tmp_path)
    with pytest.raises(S.Refused, match='Shipped By'): M.ship(R, ' ', say=lambda *a: None, batch=False)
    with pytest.raises(S.Refused, match="PDF changed since this page was opened"): M.ship(R, 'Kim', shown_sha='0' * 64, say=lambda *a: None, batch=False)
    os.makedirs(os.path.join(R, 'reviews', 'work'))
    with pytest.raises(S.Refused, match="can't be marked as shipped now"): M.ship(R, 'Kim', say=lambda *a: None, batch=False)

def test_numbering_never_reuses_a_number_and_a_leftover_tmp_goes(tmp_path):
    R = real_ready(tmp_path); sd = os.path.join(R, 'release', 'shipped')
    os.makedirs(os.path.join(sd, '004')); os.makedirs(os.path.join(sd, '007.tmp'))                     # a folder with no entry; a leftover
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry('9' * 64, n=5, withdrawn={'by': 'x', 'date': 'x', 'reason': 'r'})])   # an entry with no folder
    s = M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    assert s['n'] == 6 and os.path.isdir(os.path.join(sd, '006')) and not os.path.exists(os.path.join(sd, '007.tmp'))

def test_a_failure_after_write_run_leaves_nothing_saying_shipped(tmp_path, monkeypatch):
    R = real_ready(tmp_path)
    before = open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    def boom(*a, **k): raise RuntimeError('disk full while writing the shipped folder')
    monkeypatch.setattr(M, '_fill_shipped', boom)
    with pytest.raises(RuntimeError): M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    assert os.listdir(os.path.join(R, 'release', 'shipped')) == [] and not os.path.exists(os.path.join(R, 'release', 'shipped.json'))
    md = open(os.path.join(R, 'review.md'), encoding='utf-8').read(); h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert 'Shipped' not in md.split('## Automated')[0] and md == before and 'Status: <strong>Shipped' not in h
    assert (core.load(os.path.join(R, 'record.json')).get('release') or {}).get('shipped') == []                # the mirror too

def test_withdrawal_and_a_newer_version_shipping(tmp_path):
    R = real_ready(tmp_path)
    M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    with pytest.raises(S.Refused, match='name'): M.withdraw(R, 1, 'Kim', ' ')
    with pytest.raises(S.Refused, match='no Shipment 9'): M.withdraw(R, 9, 'Kim', 'wrong file')
    w = M.withdraw(R, 1, 'Kim', 'wrong file')
    assert len(w['withdrawn']['date']) == 19 and w['withdrawn']['date'][10] == 'T'                         # N4: local isoformat, seconds
    with pytest.raises(S.Refused, match='already withdrawn'): M.withdraw(R, 1, 'Kim', 'again')
    rec = core.load(os.path.join(R, 'record.json'))
    assert MP.app_glance(R, rec, rec['glance'])['status']['name'] == 'Ready' and MP.ship_gate(R, rec)['ok']   # falls back; offered again
    assert M.ship(R, 'Kim', say=lambda *a: None, batch=False)['n'] == 2                                 # the same file, after a withdrawal

# ------------------------------------------------------------------ the app: the strip, the POST, the downloads (M7, N2, N3)
from test_webapp import setup, wait, free_port  # noqa: F401,E402  (fixtures)
from test_webapp_checks import mapp, req, js, RUN  # noqa: F401,E402

def test_shipped_copies_in_the_downloads_and_the_file_check(tmp_path):
    import io, zipfile
    R = real_ready(tmp_path)
    s = M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    rec = core.load(os.path.join(R, 'record.json'))
    vs = DL.versions(R, rec)
    assert [x['id'] for x in vs] == ['current'] and vs[0]['state'] == 'Shipped'                 # the current file is the shipped one
    d = DL.prepare(R, 'r', 'current', 'record')
    assert d['name'] == 'b_remediated_record_shipment-1.zip' and [m[0] for m in d['members']] == ['b_remediated.pdf', 'review.html']
    buf = io.BytesIO(); DL.stream_zip(buf, d); names = zipfile.ZipFile(buf).namelist()
    assert not any(n.endswith('record.json') for n in names) and not any(n.endswith('.md') for n in names)   # N2: never the folder's record.json
    doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'b_remediated.pdf'), deterministic_id=True)   # changed by hand (M7)
    vs = DL.versions(R, rec)
    assert [x['id'] for x in vs] == ['current', 'shipment-1'] and vs[1]['label'].startswith('Shipment 1, shipped on ')
    with pytest.raises(DL.Refused): DL.prepare(R, 'r', 'current', 'pdf')                        # the current download refused (L1)
    assert DL.prepare(R, 'r', 'shipment-1', 'pdf')['name'] == 'b_remediated.pdf'               # the shipped copy still downloads
    M.withdraw(R, 1, 'Kim', 'wrong file')
    rec = core.load(os.path.join(R, 'record.json'))
    sv = next(x for x in DL.versions(R, rec) if x['id'] == 'shipment-1')
    assert sv['label'].endswith('(withdrawn)') and DL.marked_line(sv['state']) == 'The downloaded files are marked "withdrawn."'
    assert DL.prepare(R, 'r', 'shipment-1', 'pdf')['name'] == 'b_remediated_shipment-1_withdrawn.pdf'   # N3

def test_a_shipped_version_has_no_line_under_the_downloads(tmp_path):
    """The line above the downloads and the version's label already say it was shipped: the line is hidden and the select is
    not described by it; every other state keeps its line (Patrick, 2026-11-01)."""
    R = real_ready(tmp_path)
    assert MP.downloads_form('/run/r/', MP.downloads_data(R, core.load(os.path.join(R, 'record.json')), page=True)).count('aria-describedby="mc-dl-marked"') == 1
    M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    rec = core.load(os.path.join(R, 'record.json'))
    assert DL.marked_line(REL.SHIPPED) == '' and MP.downloads_data(R, rec)['versions'][0]['marked'] == ''
    f = MP.downloads_form('/run/r/', MP.downloads_data(R, rec, page=True))
    assert '<select id="mc-dlv" name="v">' in f and 'aria-describedby' not in f and '<p id="mc-dl-marked" class="pp-note" hidden></p>' in f
    assert 'publish' not in MP.page(R, 'r').lower().replace('published text', '')
    for name in ('panel.js', 'manual.js'):                                                       # the scripts hide it the same way
        src = open(os.path.join(os.path.dirname(MP.__file__), name), encoding='utf-8').read()
        assert "p.hidden = !m;" in src and "removeAttribute('aria-describedby')" in src, name

def test_the_reports_name_the_shipment_and_never_where(tmp_path):
    """No statement is linked, and an older shipment's stored `where` is kept in its record, never shown (Patrick, 2026-11-01)."""
    R = real_ready(tmp_path)
    M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<li>Shipment 1: by Kim on ' in h and 'Accessibility Statement' not in h and 'shipped/001/' not in h
    assert 'Shipped on ' in open(os.path.join(R, 'review.md'), encoding='utf-8').read() and ' by Kim (Shipment 1).' in open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    sp = REL.paths(R)['shipped']; e = core.load(sp); e[0]['where'] = 'ScholarSpace'; core.save(sp, e)   # a shipment recorded before
    M.refresh(R)
    for f in ('review.md', 'review.html'): assert 'ScholarSpace' not in open(os.path.join(R, f), encoding='utf-8').read(), f
    assert core.load(sp)[0]['where'] == 'ScholarSpace'

def test_the_strip_offers_ship_and_the_post_ships(mapp, monkeypatch):
    port, R = mapp['port'], mapp['R']
    st, s = js(port, 'GET', f'/api/run/{RUN}')
    assert s['manual']['ship']['ok'] is False and s['manual']['ship']['why'] is None   # not Ready: the card says why, the strip does not repeat it
    st, r = js(port, 'POST', f'/api/run/{RUN}/ship', {'by': 'Kim'})
    assert st == 409 and 'not ready to ship' in r['error']
    pj = open(os.path.join(os.path.dirname(MP.__file__), 'panel.js'), encoding='utf-8').read()
    assert '>Mark as Shipped</button>' in pj and 'Shipped By' in pj and 'Where It Was Published' not in pj and 'where' not in pj.split('function shipDlg')[1].split('// "Available Downloads"')[0]
    assert '<span class="pp-note">Records that this version was reviewed and shipped.</span>' in pj and "<p>Records that this version was reviewed and shipped.' +" in pj
    assert 'does not publish' not in pj and 'accessibility statement' not in pj.lower()

def test_nothing_is_served_from_a_shipped_folder(mapp):
    """The accessibility statement was dropped (Patrick, 2026-11-01: writing it is for the institution that adopts the
    pipeline): a folder shipped before keeps its files on disk, untouched, and none of them is served."""
    port, R = mapp['port'], mapp['R']
    F = os.path.join(R, 'release', 'shipped', '001'); os.makedirs(F)
    for n in ('accessibility-statement.html', 'disclosure.html'): open(os.path.join(F, n), 'w').write('<p>statement</p>')
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry('a' * 64, folder='shipped/001', where='ScholarSpace')])
    for p in ('release/shipped/001/accessibility-statement.html', 'release/shipped/001/disclosure.html', 'release/shipped/001/record.json',
              'release/shipped.json', 'release/shipped/001/accessibility-statement.md'):
        assert req(port, 'GET', f'/run/{RUN}/{p}')[0] == 404, p
    assert sorted(os.listdir(F)) == ['accessibility-statement.html', 'disclosure.html']        # left as they were

def test_an_older_page_is_shown_without_the_statement_link_or_where():
    old = ('<li>Shipment 1: by Kim on November 2, 2026 · where: ScholarSpace · <a href="release/shipped/001/disclosure.html">View the '
           'Accessibility Statement</a></li><li>Shipment 2: by Lee on November 3, 2026 · <a href="../../../release/shipped/002/accessibility-statement.html">'
           'View the Accessibility Statement</a>, withdrawn by Lee on November 4, 2026: wrong file</li><p>· where: book text stays</p>')
    assert REL.no_statement(old) == ('<li>Shipment 1: by Kim on November 2, 2026</li><li>Shipment 2: by Lee on November 3, 2026, withdrawn by Lee '
                                     'on November 4, 2026: wrong file</li><p>· where: book text stays</p>')

def test_the_run_page_drops_the_green_border_while_the_pdf_on_disk_differs(tmp_path):
    """N8 and Q1 on the run page: the card is review.html's (built against the record's hash); the app drops its green border
    whenever the file on disk is not the record's, a Ready book's or a shipped one's. review.html on disk is not rebuilt."""
    from webapp import server as W
    for name, ship in (('ready', False), ('shipped', True)):
        R = real_ready(tmp_path, name)
        if ship: M.ship(R, 'Kim', say=lambda *a: None, batch=False)
        page = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
        assert '<section class="ship yes" aria-labelledby="ship-h">' in page and W.card_border(page, R) == page, name   # unchanged: green
        doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'b_remediated.pdf'), deterministic_id=True)
        rec = core.load(os.path.join(R, 'record.json'))
        st = MP.app_glance(R, rec, rec['glance'])['status']
        assert (st['name'], st.get('warning')) == (REL.SHIPPED, MP.SHIPPED_WARNING) if ship else st['text'] == MP.CHANGED_STATUS, name
        served = W.card_border(page, R)
        assert '<section class="ship" aria-labelledby="ship-h">' in served and 'class="ship yes"' not in served, name
        assert '<section class="ship yes"' in open(os.path.join(R, 'review.html'), encoding='utf-8').read(), name   # the file itself unchanged

# ------------------------------------------------------------------ a refusal said once (review 29 R2); no name prefilled (Patrick, 2026-11-01)
def test_a_standing_refusal_is_said_once_on_the_strip(tmp_path):
    R, rec, sha = ready_run(tmp_path)
    os.makedirs(os.path.join(R, 'reviews', 'work'))                                        # a new version being made
    s = MP.strip(R, rec)
    assert s['ship']['ok'] is False and s['ship']['why'] is None                           # no second line from Ship
    assert s['refusal'] == 'A new version of this book is being made, so nothing can be recorded or marked as shipped now. Check it once it is done.'
    assert MP.ship_gate(R, rec)['why'] == "A new version of this book is being made, so this version can't be marked as shipped now."   # a POST: Ship's words
    os.rmdir(os.path.join(R, 'reviews', 'work'))
    doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'sample_remediated.pdf'), deterministic_id=True)   # changed by hand
    s = MP.strip(R, rec)
    assert s['ship']['why'] is None and s['refusal'] == ("The book's PDF has changed since this report was made, so no results can be recorded for it "
                                                         "and it can't be marked as shipped. Whoever looks after the app can check it.")
    assert MP.state(R, 'r')['refusal'] == MP.CHANGED_BY_HAND                               # the evaluation page keeps Record's words
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry(sha)])               # shipped, then changed: two different lines
    s = MP.strip(R, rec)
    assert s['ship']['why'] == 'This version was shipped on November 2, 2026 (Shipment 1).' and 'marked as shipped' in s['refusal']
    fin = 'Session 3 is finished and not yet applied: its result will replace this version. Check the new version once it is applied.'
    for why in (MP.CHANGED_BY_HAND, MP.MISSING, M.PROMOTING, M.MAKING, M.OUT_OF_STEP, M.NOT_LAST_REVIEW, fin):
        t = MP.strip_words(why)
        assert t != why and 'recorded' in t and 'marked as shipped' in t, why
    assert MP.strip_words(fin).startswith('Session 3 is finished and not yet applied: its result will replace this version, so nothing')

def test_no_name_field_is_prefilled(tmp_path):
    import re
    R, rec, sha = ready_run(tmp_path)                                                      # results by Kim on this file
    rel = core.load(os.path.join(R, 'release', 'checks.json'))
    rel['pac'].append(dict(chk('b' * 64, PAC_OK, n=2), by='Lee'))                          # and by Lee on another file
    core.save(os.path.join(R, 'release', 'checks.json'), rel)
    page = MP.page(R, 'r')
    for p in ('pac', 'sr'):                                                                # "Checked By" starts empty
        assert re.search(rf'<input type="text" id="{p}-by" data-field="by" value="" autocomplete="name"', page), p
    data = json.loads(re.search(r'id="mc-data">(.*?)</script>', page, re.S).group(1))
    starts = data['sections']['pac']['starts']
    assert starts and all('by' not in x for x in starts)                                   # "Start from These Notes" copies no name
    here = os.path.dirname(MP.__file__)
    pj = open(os.path.join(here, 'panel.js'), encoding='utf-8').read(); mj = open(os.path.join(here, 'manual.js'), encoding='utf-8').read()
    assert pj.count('checks:by') == 1 and "localStorage.removeItem('checks:by')" in pj      # the old memory is only cleared
    assert mj.count('checks:by') == 1 and "store.del('checks:by')" in mj
    for f in ('pp-ship-by', 'pp-prune-by'):                                                # the two dialogs: no value
        assert f'<input type="text" id="{f}" autocomplete="name"></p>' in pj, f
    assert "if (results || f !== 'by') el.value = v || '';" in mj
    assert '<div class="mc-lines"><p>These results are recorded for' in page                # the lines under the status: one block, no gap
    assert ('Every item needs a result, and a "Fail" needs a note. A "Fail" does not hold the book back; it is kept in the report '
            'with its note for future reference and further review.</p></div>') in page


# ------------------------------------------------------------------ the record ZIP for staff (Patrick, 2026-11-01): four files, working links
def _zip(R, v):
    import io, zipfile
    d = DL.prepare(R, 'r', v, 'record'); buf = io.BytesIO(); DL.stream_zip(buf, d)
    z = zipfile.ZipFile(buf); f = d['folder']
    return d['name'], {n[len(f) + 1:]: z.read(n) for n in z.namelist() if n.startswith(f + '/')}

def _links_stay_in_the_zip(files):
    import re
    page = files['review.html'].decode()
    for h in re.findall(r'<a\b[^>]*?\bhref="([^"]*)"', page):
        assert h.startswith('#') or h.startswith('https://') or h.startswith('http://') or h in files, h
    assert 'review.md' not in page.split('</header>')[0]                                  # the header's review.md link dropped
    return page

def test_the_record_zip_holds_only_its_files_in_every_state(tmp_path):
    from lib import dates as D
    READY = ['b_remediated.pdf', 'review.html', 'han_review.csv', 'READ-ME.txt']          # this book has Han-only runs
    # not ready: without han_review.csv, then with it (review 30 S1: back in the ZIP when the book has one)
    R0 = make_run(str(tmp_path / 'nr'), record_sha=True)
    name, files = _zip(R0, 'current')
    assert name.endswith('_not-ready.zip') and sorted(files) == sorted(['sample_remediated.pdf', 'review.html', 'READ-ME.txt'])
    assert 'han_review.csv' not in files['READ-ME.txt'].decode()
    open(os.path.join(R0, 'han_review.csv'), 'w').write('pdf_page,text\n1,漢\n')
    name, files = _zip(R0, 'current')
    assert sorted(files) == sorted(['sample_remediated.pdf', 'review.html', 'han_review.csv', 'READ-ME.txt'])
    assert files['han_review.csv'] == 'pdf_page,text\n1,漢\n'.encode('utf-8')
    assert '- han_review.csv: passages in Chinese or Japanese a person needs to check, as a spreadsheet.\n' in files['READ-ME.txt'].decode()
    _links_stay_in_the_zip(files)
    # Ready, not shipped
    R = real_ready(tmp_path)
    open(os.path.join(R, 'han_review.csv'), 'w').write('pdf_page,text\n1,漢\n')
    name, files = _zip(R, 'current')
    assert name.endswith('_not-shipped.zip') and sorted(files) == sorted(READY)
    rd = files['READ-ME.txt'].decode()
    assert 'Status: Ready' in rd and 'Shipment' not in rd and 'accessibility-statement' not in rd
    # shipped: the same files (no accessibility statement: Patrick, 2026-11-01); the shipment's lines in the read-me
    s = M.ship(R, 'Kim', say=lambda *a: None, batch=False)
    name, files = _zip(R, 'current')
    assert name == 'b_remediated_record_shipment-1.zip' and sorted(files) == sorted(READY)
    page = _links_stay_in_the_zip(files)
    assert 'Accessibility Statement' not in page
    rd = files['READ-ME.txt'].decode()
    assert f'Status: Shipped\nShipment 1, shipped on {D.day(s["shipped"])} by Kim\nAccessibility evaluation results recorded on this file: ' in rd
    assert 'Published at' not in rd and 'accessibility statement' not in rd.lower() and 'not a legal certification.' in rd
    F = os.path.join(R, 'release', 'shipped', '001')                                       # the shipped folder keeps the full set
    assert {'review.md', 'han_review.csv', 'evaluation-results.json', 'record.json'} <= set(os.listdir(F)) and not [n for n in os.listdir(F) if 'statement' in n]
    fr = open(os.path.join(F, 'READ-ME.txt'), encoding='utf-8').read()
    assert f'\nShipment 1, shipped on {D.day(s["shipped"])} by Kim\nStatus: Shipped' in fr and 'statement' not in fr
    assert 'han_review.csv: passages in Chinese or Japanese a person needs to check, as a spreadsheet.' in fr and 'record.json: ' in fr and 'which identifies this exact file (sha256): ' + s['pdf']['sha256'] in fr
    # an earlier version: its own page, links leading out of the ZIP unwrapped
    V = os.path.join(R, 'reviews', 'versions', '001'); os.makedirs(V)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(200, 200)); doc.save(os.path.join(V, 'b_remediated.pdf'), deterministic_id=True)
    core.save(os.path.join(V, 'record.json'), {'document': {'file': 'b.pdf', 'output': 'b_remediated.pdf'}})
    shutil.copy2(os.path.join(R, 'review.html'), os.path.join(V, 'review.html'))
    with open(os.path.join(V, 'review.html'), 'a', encoding='utf-8') as f:            # and, written before 2026-11-01, a statement link and `where`
        f.write('<a href="../002/review.html">previous result</a><a href="https://example.org/">web</a>'
                '<ul><li>Shipment 1: by Kim on November 2, 2026 · where: ScholarSpace · <a href="../../../release/shipped/001/disclosure.html">View the Accessibility Statement</a></li></ul>')
    name, files = _zip(R, '001')                                                            # its folder has no han_review.csv
    assert name.endswith('_session-1_previous-version.zip') and sorted(files) == sorted(['b_remediated.pdf', 'review.html', 'READ-ME.txt'])
    page = _links_stay_in_the_zip(files)
    assert 'previous result' in page and '<a href="https://example.org/">web</a>' in page and 'Accessibility Statement' not in page
    assert '<li>Shipment 1: by Kim on November 2, 2026</li>' in page and 'ScholarSpace' not in page
    assert 'Status: previous version' in files['READ-ME.txt'].decode()
    # withdrawn: the shipped copy, with its withdrawal
    M.withdraw(R, 1, 'Lee', 'wrong file')
    name, files = _zip(R, 'shipment-1')
    assert name == 'b_remediated_record_shipment-1_withdrawn.zip' and sorted(files) == sorted(READY)
    _links_stay_in_the_zip(files)
    rd = files['READ-ME.txt'].decode()
    w = REL.load(R)['shipped'][0]['withdrawn']
    assert (f'Status: Withdrawn\nShipment 1, shipped on {D.day(s["shipped"])} by Kim\n'
            f'Withdrawn on {D.day(w["date"])} by Lee: wrong file\n') in rd
    assert not any(n.endswith(('.md', '.json')) for n in files)

def test_a_draft_never_keeps_checked_by(tmp_path):
    """Patrick, 2026-11-01 (after review 30): a draft carries no name to the next person: none saved, and an old draft's
    name dropped as it loads (the server's drafts.json and the browser's copy)."""
    import re
    R, rec, sha = ready_run(tmp_path)
    M.save_draft(R, 'screen_reader', {'by': 'Kim', 'notes': 'half done'}, '2026-11-01T10:00:00Z', sha, wait=1)
    raw = json.load(open(M.drafts_path(R), encoding='utf-8'))
    assert 'by' not in raw['screen_reader'] and 'by' not in raw['screen_reader']['data'] and raw['screen_reader']['data']['notes'] == 'half done'
    raw['pac'] = {'data': {'by': 'Lee', 'items': {}}, 'saved_at': '2026-10-31T09:00:00Z', 'for_sha256': sha, 'by': 'Lee'}   # saved before
    core.save(M.drafts_path(R), raw)
    assert all('by' not in v and 'by' not in v['data'] for v in M.load_drafts(R).values())
    page = MP.page(R, 'r')
    for p in ('pac', 'sr'):
        assert re.search(rf'<input type="text" id="{p}-by" data-field="by" value="" autocomplete="name"', page), p
    assert 'Lee' not in page and 'Kim' not in page.split('id="mc-data"')[0].split('Current Results')[0]
    mj = open(os.path.join(os.path.dirname(MP.__file__), 'manual.js'), encoding='utf-8').read()
    assert 'const kept = sec.collect(); delete kept.by;' in mj and 'delete mine.data.by;' in mj   # the browser's copy: none kept, an old one dropped
