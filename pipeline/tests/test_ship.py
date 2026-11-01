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
    s = M.ship(R, 'Kim', 'ScholarSpace', 'first release', say=lambda *a: None, batch=False)
    F = os.path.join(R, 'release', 'shipped', '001')
    assert s['n'] == 1 and len(s['shipped']) == 19 and s['shipped'][10] == 'T' and s['issues'] == 1 and s['checks'] == {'pac': 1, 'screen_reader': 1}
    assert sorted(os.listdir(F)) == sorted(['b_remediated.pdf', 'review.md', 'review.html', 'record.json', 'evaluation-results.json',
                                            'disclosure.md', 'disclosure.html', 'READ-ME.txt'])
    assert REL.sha_file(os.path.join(F, 'b_remediated.pdf')) == s['pdf']['sha256']
    assert '**Status:** Shipped · 1 issue noted' in open(os.path.join(F, 'review.md'), encoding='utf-8').read()
    assert 'Shipped copy (shipment 1, ' in open(os.path.join(F, 'review.html'), encoding='utf-8').read()     # N9
    assert '**Status:** Shipped · 1 issue noted' in open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    st = open(os.path.join(F, 'disclosure.md'), encoding='utf-8').read()                   # reviewed before sessions were kept: Session 1
    assert s['pdf']['session'] == '001' and 'the version reviewed on October 31, 2026, shipped on ' in st and 'applied without a review' not in st
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
    def boom(*a, **k): raise RuntimeError('disk full while writing the statement')
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
    with pytest.raises(S.Refused, match='no shipment 9'): M.withdraw(R, 9, 'Kim', 'wrong file')
    w = M.withdraw(R, 1, 'Kim', 'wrong file')
    assert len(w['withdrawn']['date']) == 19 and w['withdrawn']['date'][10] == 'T'                         # N4: local isoformat, seconds
    with pytest.raises(S.Refused, match='already withdrawn'): M.withdraw(R, 1, 'Kim', 'again')
    rec = core.load(os.path.join(R, 'record.json'))
    assert MP.app_glance(R, rec, rec['glance'])['status']['name'] == 'Ready' and MP.ship_gate(R, rec)['ok']   # falls back; offered again
    assert M.ship(R, 'Kim', say=lambda *a: None, batch=False)['n'] == 2                                 # the same file, after a withdrawal

# ------------------------------------------------------------------ the accessibility statement (M3–M5, N6, N7)
from lib import disclosure as DS

def statement(rec, rel=None, ship=None, glance=None):
    ship = ship or {'n': 1, 'shipped': '2026-11-02T09:00:00', 'by': 'Kim', 'pdf': {'sha256': 'a' * 64, 'session': '006'}}
    blocks = DS.facts(rec, rel or REL.empty(), ship, glance or {'safety_ok': True, 'verapdf': {}})
    return blocks, DS.to_md(blocks, 'The Book'), DS.to_html(blocks, 'The Book')

def test_the_split_between_the_ai_and_people(tmp_path):
    rec = {'review': {'workorder': {'reviewer': 'Pat', 'date': '2026-10-31', 'counts': {'approved': 2, 'changed': 1, 'rejected': 1, 'added': 1}},
                      'decisions': [{'kind': 'Alt text', 'status': 'approved'}, {'kind': 'Alt text', 'status': 'changed'},
                                    {'kind': 'Heading or tag change', 'status': 'approved'}, {'kind': 'Heading or tag change', 'status': 'rejected'},
                                    {'kind': 'Deferred by the AI', 'status': 'approved'}, {'id': 'reading_order:3', 'kind': 'Reading order', 'status': 'seen'},
                                    {'id': 'notes_for_reviewer', 'kind': 'Deferred by the AI', 'status': 'seen'}]},
           'workorder': {'alt': {'f1': 'x', 'f2': 'y'}}, 'apply': {'rejected': [1], 'failed': 0, 'deferred': []}}
    _, md, _ = statement(rec)
    assert 'Decisions reviewed by a person: 2 approved as proposed, 1 changed, 1 rejected' in md
    assert 'Alt text: 1 approved as proposed, 1 changed' in md and 'Heading or tag change: 1 approved as proposed, 1 rejected' in md
    assert 'Added by a person: 1' in md and 'Deferred by the AI' not in md and 'Changes made to the PDF from these decisions: 1 (1 could not be applied)' in md
    rv1 = {'review': {'workorder': {'reviewer': 'Patrick', 'date': '2026-10-26', 'counts': {'approved': 159, 'changed': 0, 'rejected': 0, 'seen': 8, 'accepted_unreviewed': 0}}}}
    _, md, _ = statement(rv1)                                                               # an older reviewed run: totals only (M3)
    assert 'Decisions reviewed by a person: 159 approved as proposed' in md and 'Points the AI or the software left for a person: 8, each looked at' in md   # P1
    assert 'Totals only: the kind of each decision was not recorded for this book.' in md
    _, md, _ = statement({})
    assert "The split between the AI's proposals and a person's changes was not recorded for this book." in md

def test_the_text_sentences_follow_the_record():
    _, md, _ = statement({})
    assert "No AI wrote or changed the book's printed text." in md and 'OCR' not in md.split('## What the AI')[0]
    rec = {'apply': {'ocr_words': {'forms': 12}}, 'intake': {'ocr': {'pages_with_ocr_text': [3, 4, 5]},
                                                               'review': {'ocr_text_approved': {'verdict': 'approved', 'reviewer': 'Kim', 'date': '2026-10-30'}}}}
    _, md, _ = statement(rec)
    assert "For 12 words the OCR misread, an AI's reading is given as spoken text only" in md
    assert 'On 3 scanned pages the text is local OCR (not corrected), approved by Kim on October 30, 2026.' in md
    _, md, _ = statement({'intake': {'ocr_layer_test': {'verdict': 'usable'}}})
    assert "The publisher's text layer on scanned pages is OCR; it was checked and kept as published." in md

def test_the_model_only_for_a_real_call_and_verapdf_not_checked():
    real = {'run': {'model': 'anthropic/claude-sonnet-5.5', 'prompt_file': 'workorder_v8.md', 'prompt_sha256': '4555d20a2fa08a40aa', 'started': '2026-10-20T10:00:00'}}
    _, md, _ = statement(real)
    assert 'Model: anthropic/claude-sonnet-5.5. Instructions: workorder\\_v8.md (4555d20a2fa08a40). Decided on October 20, 2026.' in md
    replay = {'run': dict(real['run'], prompt_file='workorder_v9.md', response_from='v8-g1')}
    _, md, _ = statement(replay)                                                          # M5: a v8 reply replayed on v9 code
    assert 'workorder\\_v9' not in md and 'Model and instructions: not recorded for this book.' in md
    assert 'veraPDF (WCAG 2.2 machine checks): not checked (it checked only one of the two files, or neither).' in md   # N6
    _, md, _ = statement({}, glance={'safety_ok': True, 'verapdf': {'ran_before': True, 'ran_after': True, 'before_rules': 7, 'after_rules': 0, 'newly_failing': []}})
    assert '7 rules failing before → 0 after; 0 newly failing.' in md

def test_names_and_notes_are_escaped_in_both_files(tmp_path):
    evil = '<script>x</script> **bold** ](javascript:)'
    rel = {'checks': {'schema': REL.SCHEMA, 'screen_reader': [],
                      'pac': [chk('a' * 64, dict(PAC_OK, contrast={'result': 'fail', 'note': '# heading ' + evil}))]}, 'shipped': []}
    rel['checks']['pac'][0]['by'] = evil
    _, md, h = statement({'review': {'workorder': {'reviewer': evil, 'date': '2026-10-31'}}}, rel,
                         {'n': 1, 'shipped': '2026-11-02T09:00:00', 'by': evil, 'where': evil, 'pdf': {'sha256': 'a' * 64}})
    assert '<script>' not in h and '&lt;script&gt;' in h and '<script>' not in md and '\\<script\\>' in md and '\\*\\*bold\\*\\*' in md
    assert 'Draft wording: to be agreed with the sponsors.' in md and 'not a legal certification' in md and 'not legal sign-off' in md
    assert 'PAC 2026, Contrast: # heading' in md and '\n# heading' not in md and ' we ' not in md.lower() and 'Issues Noted' in md

@pytest.mark.skipif(not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'runs', 'review-disclosure', 'regr8')),
                    reason='the regression run regr8 is local only')
def test_the_statement_builds_on_the_seven_baseline_records():
    import report_html as H
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'runs', 'review-disclosure', 'regr8')
    from lib.glance import n_decisions
    for b in sorted(os.listdir(base)):
        p = os.path.join(base, b, 'record.json')
        if not os.path.isfile(p): continue
        rec = json.load(open(p, encoding='utf-8'))
        blocks, md, h = statement(rec, glance=H.glance_of(os.path.join(base, b), rec))
        n, nn = DS.applied(rec)
        assert n == n_decisions(rec.get('workorder') or {}) and f'Changes made to the PDF from these decisions: {n - nn}' in md, b
        assert 'was not recorded for this book' in md, b                                       # the baselines are unreviewed

# ------------------------------------------------------------------ the app: the strip, the POST, the statement, the downloads (M7, N2, N3)
from test_webapp import setup, wait, free_port  # noqa: F401,E402  (fixtures)
from test_webapp_checks import mapp, req, js, RUN  # noqa: F401,E402

def test_shipped_copies_in_the_downloads_and_the_file_check(tmp_path):
    import io, zipfile
    R = real_ready(tmp_path)
    s = M.ship(R, 'Kim', 'ScholarSpace', say=lambda *a: None, batch=False)
    rec = core.load(os.path.join(R, 'record.json'))
    vs = DL.versions(R, rec)
    assert [x['id'] for x in vs] == ['current'] and vs[0]['state'] == 'Shipped'                 # the current file is the shipped one
    d = DL.prepare(R, 'r', 'current', 'record')
    assert d['name'] == 'b_remediated_record_shipment-1.zip' and 'disclosure.html' in [m[0] for m in d['members']]
    buf = io.BytesIO(); DL.stream_zip(buf, d); names = zipfile.ZipFile(buf).namelist()
    assert not any(n.endswith('record.json') for n in names) and any(n.endswith('disclosure.md') for n in names)   # N2: never the folder's record.json
    doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'b_remediated.pdf'))   # changed by hand (M7)
    vs = DL.versions(R, rec)
    assert [x['id'] for x in vs] == ['current', 'shipment-1'] and vs[1]['label'].startswith('Shipment 1, shipped on ')
    with pytest.raises(DL.Refused): DL.prepare(R, 'r', 'current', 'pdf')                        # the current download refused (L1)
    assert DL.prepare(R, 'r', 'shipment-1', 'pdf')['name'] == 'b_remediated.pdf'               # the shipped copy still downloads
    M.withdraw(R, 1, 'Kim', 'wrong file')
    rec = core.load(os.path.join(R, 'record.json'))
    sv = next(x for x in DL.versions(R, rec) if x['id'] == 'shipment-1')
    assert sv['label'].endswith('(withdrawn)') and DL.marked_line(sv['state']) == 'The downloaded files are marked "withdrawn".'
    assert DL.prepare(R, 'r', 'shipment-1', 'pdf')['name'] == 'b_remediated_shipment-1_withdrawn.pdf'   # N3

def test_the_statement_is_linked_and_review_md_names_the_shipment(tmp_path):
    R = real_ready(tmp_path)
    M.ship(R, 'Kim', 'ScholarSpace', say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<a href="release/shipped/001/disclosure.html">View the Accessibility Statement</a>' in h and 'Disclosure' not in h   # N5
    assert 'Shipped on ' in open(os.path.join(R, 'review.md'), encoding='utf-8').read() and '(shipment 1, ScholarSpace).' in open(os.path.join(R, 'review.md'), encoding='utf-8').read()

def test_the_strip_offers_ship_and_the_post_ships(mapp, monkeypatch):
    port, R = mapp['port'], mapp['R']
    st, s = js(port, 'GET', f'/api/run/{RUN}')
    assert s['manual']['ship']['ok'] is False and s['manual']['ship']['why'] is None   # not Ready: the card says why, the strip does not repeat it
    st, r = js(port, 'POST', f'/api/run/{RUN}/ship', {'by': 'Kim'})
    assert st == 409 and 'not ready to ship' in r['error']
    pj = open(os.path.join(os.path.dirname(MP.__file__), 'panel.js'), encoding='utf-8').read()
    assert '>Mark as Shipped</button>' in pj and 'Shipped By' in pj and 'Where It Was Published <span class="pp-note">(optional)</span>' in pj
    assert 'Records that this version was published. It does not publish anything.' in pj

def test_only_the_statement_is_served_from_a_shipped_folder(mapp):
    port, R = mapp['port'], mapp['R']
    F = os.path.join(R, 'release', 'shipped', '001'); os.makedirs(F)
    open(os.path.join(F, 'disclosure.html'), 'w').write('<p>statement</p>'); core.save(os.path.join(F, 'record.json'), {'raw_reply': 'secret'})
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship_entry('a' * 64, folder='shipped/001')])
    assert req(port, 'GET', f'/run/{RUN}/release/shipped/001/disclosure.html')[0] == 200
    for p in ('release/shipped/001/record.json', 'release/shipped/002/disclosure.html', 'release/shipped.json', 'release/shipped/001/../001/disclosure.html'):
        assert req(port, 'GET', f'/run/{RUN}/{p}')[0] == 404, p


OCR_BOOK = {'intake': {'ocr': {'pages_with_ocr_text': [1]},
                       'review': {'ocr_text_approved': {'verdict': 'approved', 'reviewer': 'Ana', 'date': '2026-10-30'}}},
            'apply': {'ocr_words': {'forms': 3}}}
PAC_NEEDS = {'by': 'Kim', 'fields': {}, 'items': dict(PAC_OK, needs_person={'result': 'fail', 'note': 'two figures not looked at'})}

@pytest.mark.parametrize('book', ['born-digital', 'ocr'])
def test_the_statement_uses_no_internal_terms(tmp_path, book):
    """P2 and 26 Q2: a public reader's words; none of the app's or the report's internal terms in either file, on a book
    without OCR and on one with OCR pages, an approved verdict and OCR-word readings (the OCR sentences). Q4: the PAC item
    named after the report's section is renamed in the statement."""
    ocr = book == 'ocr'
    R = real_ready(tmp_path, extra=OCR_BOOK if ocr else None, pac=PAC_NEEDS if ocr else None)
    M.ship(R, 'Kim', 'ScholarSpace', say=lambda *a: None, batch=False)
    F = os.path.join(R, 'release', 'shipped', '001')
    import re
    for f in ('disclosure.md', 'disclosure.html'):
        text = open(os.path.join(F, f), encoding='utf-8').read().replace('\\', '')
        for bad in ('work order', 'work-order', 'Session', 'review page', 'intake', 'pipeline', 'executor', 'tag tree',
                    'listed for a person in the report', 'What Needs a Person', 'For a Person to Check'):
            assert bad not in text, (f, bad)
        assert not re.search(r'\b(run|report)\b', text), f
    md = open(os.path.join(F, 'disclosure.md'), encoding='utf-8').read()
    assert "the document's structure" in md and 'a semi-automated process' in md
    if not ocr:
        assert 'OCR text: none was added.' in md
    else:
        assert 'OCR text: approved by Ana on October 30, 2026.' in md
        assert 'On 1 scanned page the text is local OCR (not corrected), approved by Ana on October 30, 2026.' in md
        assert "For 3 words the OCR misread, an AI's reading is given as spoken text only; each was listed for a person to check." in md
        assert 'PAC 2026, Points the AI or the Software Left for a Person to Check: two figures not looked at' in md

def test_the_run_page_drops_the_green_border_while_the_pdf_on_disk_differs(tmp_path):
    """N8 and Q1 on the run page: the card is review.html's (built against the record's hash); the app drops its green border
    whenever the file on disk is not the record's, a Ready book's or a shipped one's. review.html on disk is not rebuilt."""
    from webapp import server as W
    for name, ship in (('ready', False), ('shipped', True)):
        R = real_ready(tmp_path, name)
        if ship: M.ship(R, 'Kim', say=lambda *a: None, batch=False)
        page = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
        assert '<section class="ship yes" aria-labelledby="ship-h">' in page and W.card_border(page, R) == page, name   # unchanged: green
        doc = pikepdf.new(); doc.add_blank_page(page_size=(500, 500)); doc.save(os.path.join(R, 'b_remediated.pdf'))
        rec = core.load(os.path.join(R, 'record.json'))
        st = MP.app_glance(R, rec, rec['glance'])['status']
        assert (st['name'], st.get('warning')) == (REL.SHIPPED, MP.SHIPPED_WARNING) if ship else st['text'] == MP.CHANGED_STATUS, name
        served = W.card_border(page, R)
        assert '<section class="ship" aria-labelledby="ship-h">' in served and 'class="ship yes"' not in served, name
        assert '<section class="ship yes"' in open(os.path.join(R, 'review.html'), encoding='utf-8').read(), name   # the file itself unchanged
