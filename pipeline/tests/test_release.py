"""test_release.py: the manual checks, the status and the record lock (issue #38, stage 1): lib/release.py,
lib/runlock.py, review/manual.py, glance's PAC condition and sixth safety check. Synthetic run folders and a one-page
synthetic PDF; no model, nothing sent.

    python -m pytest tests/test_release.py -q
"""
import os, sys, time, shutil, threading, subprocess
import pytest
import pikepdf
from lib import release as REL, runlock, glance as G
from lib.titles import title_case
from review import core, sessions as S, manual as M, ocr as O

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B, C = 'a' * 64, 'b' * 64, 'c' * 64
PAC_OK = {k: {'result': 'pass'} for k in ('pac_wcag', 'title_language', 'spot_check', 'colour', 'contrast', 'images_of_text', 'needs_person')}
SR_OK = {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['screen_reader']}

def chk(sha, items, recorded='2026-11-01T10:00:00', by='Kim', session='002', **kw):
    return {'id': 1, 'recorded': recorded, 'by': by, 'pdf': {'sha256': sha, 'session': session, 'which': 'current'}, 'items': items, **kw}

def rel(pac=(), sr=(), shipped=()):
    return {'checks': {'schema': REL.SCHEMA, 'pac': list(pac), 'screen_reader': list(sr)}, 'shipped': list(shipped)}

def ship(sha, n=1, shipped='2026-11-02T09:00:00', **kw): return {'n': n, 'shipped': shipped, 'by': 'Lee', 'pdf': {'sha256': sha}, **kw}

def failing(items, key): return dict(items, **{key: {'result': 'fail', 'note': 'heard it wrong'}})

# ------------------------------------------------------------------ the evaluation line: results follow the hash, whatever it is
def test_evaluation_line_counts_exactly_when_the_hash_is_the_same():
    assert REL.evaluation_line(rel(), A) == (False, 'Not Completed')
    r = rel(pac=[chk(A, PAC_OK)], sr=[chk(A, SR_OK)])
    assert REL.evaluation_line(r, A) == (True, 'Completed')                      # the same hash (an apply that gave the same bytes): it counts
    ok, txt = REL.evaluation_line(r, B)                                          # another hash: an earlier version
    assert not ok and txt == ('Not Completed (PAC 2026: recorded on a previous version, Session 2; '
                              'Screen-Reader Test: recorded on a previous version, Session 2)')
    assert REL.evaluation_line(r, None)[0] is False                              # no recorded hash: nothing counts
    ok, txt = REL.evaluation_line(rel(pac=[chk(A, failing(PAC_OK, 'contrast'))]), A)   # one part, with a Fail
    assert not ok and txt == 'Not Completed (Screen-Reader Test not recorded; 1 issue noted)'
    r = rel(pac=[chk(A, failing(PAC_OK, 'contrast'))], sr=[chk(A, failing(failing(SR_OK, 'links'), 'tables'))])
    assert REL.evaluation_line(r, A) == (True, 'Completed (3 issues noted)')     # a Fail never blocks (2026-10-31)

def test_reads_fail_closed_and_retired_items_never_count():
    assert REL.complete(chk(A, PAC_OK), 'pac') and REL.issues(chk(A, PAC_OK), 'pac') == []
    old = chk(A, dict(PAC_OK, pac_pdfua={'result': 'not_run'}), fields={'pac_version': '2026.1'})    # try-rv1's older shape
    assert REL.complete(old, 'pac') and REL.issues(dict(old, items=dict(old['items'], pac_pdfua={'result': 'fail', 'note': 'x'})), 'pac') == []
    assert not REL.complete(chk(A, dict(PAC_OK, contrast={'result': 'maybe'})), 'pac')                  # an unknown result
    assert not REL.complete(chk(A, {k: v for k, v in PAC_OK.items() if k != 'colour'}), 'pac')          # missing
    assert not REL.complete(chk(A, dict(PAC_OK, later_item={'result': 'pass'})), 'pac')                 # an item this code does not know
    acc = chk(A, dict(PAC_OK, contrast={'result': 'fail', 'note': 'n', 'accepted': {'by': 'X'}}))       # once reserved: read by its result
    assert REL.complete(acc, 'pac') and REL.issues(acc, 'pac') == ['contrast']
    bad = chk(A, dict(failing(PAC_OK, 'contrast'), colour={'result': 'maybe'}))                         # unreadable: its Fails still count (H4)
    r = rel(pac=[bad], sr=[chk(A, SR_OK)])
    assert REL.evaluation_line(r, A) == (False, 'Not Completed (PAC 2026: could not be read in full: record it again; 1 issue noted)')
    assert REL.part(r, 'pac', A)['state'] == 'could not be read'

# ------------------------------------------------------------------ the status
def test_status_before_and_after_shipping():
    both = dict(pac=[chk(A, PAC_OK)], sr=[chk(A, SR_OK)])
    assert REL.status(rel(), A, False)['text'] == 'Not Ready'
    assert REL.status(rel(), A, True)['text'] == 'Pending Evaluation'
    assert REL.status(rel(pac=[chk(A, failing(PAC_OK, 'contrast'))]), A, True)['text'] == 'Pending Evaluation · 1 issue noted'
    assert REL.status(rel(pac=[chk(A, failing(PAC_OK, 'contrast'))]), A, False)['text'] == 'Not Ready · 1 issue noted'   # Q1: on every status
    assert REL.status(rel(**both), A, True)['text'] == 'Ready'
    st = REL.status(rel(pac=[chk(A, failing(PAC_OK, 'contrast'))], sr=[chk(A, failing(SR_OK, 'links'))]), A, True)
    assert st['name'] == 'Ready' and st['text'] == 'Ready · 2 issues noted' and st['issues'] == 2
    assert REL.status(rel(**both, shipped=[ship(A)]), A, True)['text'] == 'Shipped'
    r = rel(pac=[chk(A, PAC_OK)], sr=[chk(A, failing(SR_OK, 'tables'), recorded='2026-11-03T10:00:00')], shipped=[ship(A)])
    assert REL.status(r, A, True)['text'] == 'Shipped · 1 issue noted'               # a test after shipping, on the shipped file
    r = rel(pac=[chk(A, PAC_OK), chk(B, failing(PAC_OK, 'colour'))], sr=[chk(A, SR_OK)], shipped=[ship(A)])
    assert REL.status(r, B, True)['text'] == 'Shipped'                                # Q5: the shipped file's issues, not the current one's

def test_status_withdrawal_falls_back_and_the_newer_version_line():
    w = ship(B, 2, withdrawn={'by': 'Lee', 'date': '2026-11-04', 'reason': 'wrong file'})
    assert REL.status(rel(shipped=[ship(A), w]), A, False)['name'] == 'Shipped'          # the latest non-withdrawn: shipment 1
    assert REL.status(rel(shipped=[dict(ship(A), withdrawn={'by': 'L'})]), A, True)['name'] == 'Pending Evaluation'   # none left
    r = rel(pac=[chk(B, failing(PAC_OK, 'contrast'))], sr=[chk(B, SR_OK)], shipped=[ship(A)])
    st = REL.status(r, B, True, None, '003')                                       # a newer version, applied: its own status
    assert st['name'] == 'Shipped' and st['newer'] == 'Newer version (Session 3): Ready · 1 issue noted'
    assert REL.status(rel(shipped=[ship(A)]), B, True, None, '003')['newer'] == 'Newer version (Session 3): Pending Evaluation'
    assert REL.status(r, B, False, {'finished': None, 'open': '004'})['newer'] == 'Newer version: Session 4 being reviewed'
    assert REL.status(r, A, False, {'finished': None, 'open': '004'})['newer'] == 'Newer version: Session 4 being reviewed'   # the shipped file is still current
    assert REL.status(r, A, False, {'finished': '004', 'open': '005'})['newer'] == 'Newer version: Session 4 finished, not applied'
    assert REL.status(r, A, False)['newer'] is None
    assert REL.status(rel(), A, False, {'finished': '004', 'open': None})['newer'] is None              # before any shipment: no line

FIVE = [{'what': label, 'ok': True} for _, label in G.SAFETY]
def test_a_failed_screen_reader_test_never_blocks_ready():
    g = {'schema': G.SCHEMA, 'ship': [{'what': w, 'ok': True, 'text': 'x'} for w in G.SHIP_BASE], 'safety': FIVE, 'needs_person': {'total': 0}}
    rec = {'document': {'output_sha256': A}}
    out = G.with_release(g, rec, rel(pac=[chk(A, PAC_OK)]))
    assert out['ready'] is False and out['status']['text'] == 'Pending Evaluation' and out['ship'][-1]['what'] == G.SHIP_EVAL
    out = G.with_release(g, rec, rel(pac=[chk(A, PAC_OK)], sr=[chk(A, failing(SR_OK, 'links'))]))
    assert out['ready'] is True and out['status']['text'] == 'Ready · 1 issue noted'
    assert out['ship'][-1] == {'what': G.SHIP_EVAL, 'ok': True, 'text': 'Completed (1 issue noted)'} and len(out['ship']) == 4
    out = G.with_release(g, rec, rel(pac=[chk(A, PAC_OK)], sr=[chk(A, SR_OK)], shipped=[ship(A)]))
    assert out['ready'] is False and out['status']['name'] == 'Shipped'               # H9: ready means the status is Ready

def test_ready_needs_glance_04_or_05_all_three_base_lines_and_the_five_checks():
    """H1: a 0.3 glance is never Ready (it predates three base rules); H2: a 0.4 glance's sixth check is dropped and its
    Safety line rewritten from the five damage checks."""
    rec = {'document': {'output_sha256': A}}; r = rel(pac=[chk(A, PAC_OK)], sr=[chk(A, SR_OK)])
    base = [{'what': w, 'ok': True, 'text': 'x'} for w in G.SHIP_BASE]
    def g(schema=G.SCHEMA, ship=base, safety=FIVE): return {'schema': schema, 'ship': ship, 'safety': safety, 'needs_person': {'total': 0}}
    assert G.with_release(g(), rec, r)['ready'] is True
    assert G.with_release(g('glance/0.3'), rec, r)['ready'] is False
    six = FIVE + [{'what': G.SAFETY_VERA, 'ok': False}]
    old = g('glance/0.4', [base[0], base[1], {'what': 'Safety checks', 'ok': False, 'text': f'failed: {G.SAFETY_VERA}'}], six)
    out = G.with_release(old, rec, r)
    assert out['ready'] is True and out['ship'][2] == {'what': 'Safety checks', 'ok': True, 'text': 'Passed'} and len(out['safety']) == 5
    four = [dict(x) for x in FIVE[:4]]                                            # a run made before a check existed
    out = G.with_release(g(safety=four), rec, r)
    assert out['ready'] is False and out['ship'][2]['text'] == 'Not Checked (only 4 of the 5 checks were recorded for this run)'
    import report_html as H
    assert out['safety_ok'] is False and H.safety_state(out) == 'not checked'      # the line, the card and summary.html agree
    bad = [dict(x) for x in FIVE]; bad[1]['ok'] = False
    assert G.with_release(g(safety=bad), rec, r)['ship'][2]['text'] == 'Failed (text unchanged)'
    assert G.with_release(g(ship=base[:1] + base[2:]), rec, r)['ready'] is False
    assert G.with_release(g(ship=[]), rec, r)['ready'] is False                     # the evaluation line alone

def test_a_stored_old_glance_marked_ready_is_not_ready_now():
    from webapp import runs
    old = {'schema': 'glance/0.3', 'ready': True, 'ship': [{'what': w, 'ok': True, 'text': 'yes'} for w in G.SHIP_BASE]
           + [{'what': 'Manual check (PAC)', 'ok': None, 'text': 'not run'}], 'safety': FIVE}
    r = runs.ready('/nonexistent', {'glance': old, 'document': {}})
    assert r['answer'] == 'No' and r['status'] == 'Not Ready'
    assert r['lines'][-1] == 'Accessibility evaluation: Not Completed'

# ------------------------------------------------------------------ the veraPDF finding (was the sixth safety check)
SAFE = ['Every page looks the same as the original', 'Published text unchanged', 'All content tagged or marked as decoration',
        'Tag-tree index points only into the tree', 'Fonts: every embedded font program could be read']
def md_with(vera_ok):
    rows = [f'| {n} | OK | x |' for n in SAFE] + [f'| veraPDF: no rule newly failing or failing more often | {"OK" if vera_ok else "**CHECK**"} | x |']
    return '\n'.join(['# Remediation Review: b.pdf', '', '## Automated Checks', '', '| Check | Result | Detail |', '|---|---|---|'] + rows + [''])
def vera(rules): return {'rules': rules, 'totals': {'wcag_failed_rules': 0, 'wcag_failed_checks': 0}}

def test_newly_failing_is_a_finding_not_a_safety_check():
    pdfua_only = {'verapdf': {'before': vera([]), 'after': vera([{'id': '7.9-1', 'scope': 'ua_only', 'failed': 3}])}}
    g = G.glance(pdfua_only, md_with(False))
    assert g['safety_ok'] and len(g['safety']) == 5
    vi = [x for x in g['issues'] if x['text'].startswith('veraPDF:')]
    assert vi and vi[0]['rank'] == 2 and vi[0]['kind'] == 'check'               # PDF/UA only: an ordinary check
    wcag_new = {'verapdf': {'before': vera([]), 'after': vera([{'id': '7.18.1-1', 'scope': 'wcag', 'failed': 1}])}}
    md = md_with(False).replace('| Fonts: every embedded font program could be read | OK |', '| Fonts: every embedded font program could be read | OK |') \
        + '| Work order reviewed by a person before it was applied | **CHECK** | x |\n'
    g = G.glance(wcag_new, md)
    assert g['safety_ok'] and g['ship'][2]['text'] == 'Passed'
    vi = [x for x in g['issues'] if x['rank'] == 1]
    assert vi[0]['text'].startswith('veraPDF:') and vi[0]['kind'] == 'check' and 'lead' not in vi[0]   # first among rank 1 (H7)
    assert g['needs_person']['check_rows'] == 2                                  # counted once, as its CHECK row
    g = G.glance({'verapdf': {'before': {'not_run': 'VERAPDF=off'}, 'after': {'not_run': 'VERAPDF=off'}}}, md_with(False))
    assert g['safety_ok'] and [x for x in g['issues'] if x['text'].startswith('veraPDF:')][0]['rank'] == 1   # not compared: a finding (Q6)
    assert 'NOT CHECKED' not in '\n'.join(G.glance_md(g)) and '**Safety checks:** ' + ' · '.join(f'OK ✔ {x}' for _, x in G.SAFETY) in '\n'.join(G.glance_md(g))

def test_status_line_sits_above_ready_to_ship_and_the_old_heading_still_parses():
    L = G.glance_md(G.glance({}, md_with(True)))
    i = L.index('**Status:** Not Ready')
    assert L[i + 2] == '**Ready to ship?**' and L[i + 3] == '- Work Order Approval: Not Approved (applied without a review)'
    assert L[i + 4] == '- ✓ OCR Text Approval: Not Applicable' and L[i + 5] == '- ✓ Safety Checks: Passed'
    assert L[i + 6] == '- Accessibility Evaluation: Not Completed'
    rows, _ = G.parse_md(md_with(True).replace('## Automated Checks', '## Automated checks'))
    assert len(rows) == 6

# ------------------------------------------------------------------ checking a check
def test_validate_fields_and_notes():
    good = {'by': 'Kim', 'fields': {'pages_checked': '5, 9-12'}, 'items': PAC_OK}
    assert REL.validate('pac', good, {'n_pages': 20})['fields'] == {'pages_checked': '5, 9-12'}
    def errs(data, ctx=None, section='pac'):
        with pytest.raises(REL.Invalid) as e: REL.validate(section, data, ctx or {'n_pages': 20})
        return dict(e.value.errors)
    assert 'items.contrast.note' in errs(dict(good, items=dict(PAC_OK, contrast={'result': 'fail'})))     # a Fail needs a note
    assert 'items.pac_wcag.result' in errs(dict(good, items=dict(PAC_OK, pac_wcag={'result': 'na'})))     # PAC itself: no N/A
    assert REL.validate('pac', dict(good, fields={}), {'n_pages': 20})['fields'] == {}                   # Pages Checked: optional (2026-10-31)
    assert 'fields.pages_checked' in errs(dict(good, fields={'pages_checked': '30'}))
    assert 'by' in errs(dict(good, by=' '))
    assert 'items.contrast.note' in errs(dict(good, items=dict(PAC_OK, contrast={'result': 'pass', 'note': 'a | b'})))
    assert 'notes' in errs(dict(good, notes='[x](javascript:alert(1))'))
    assert 'items.nope' in errs(dict(good, items=dict(PAC_OK, nope={'result': 'pass'})))
    sr = {'by': 'Kim', 'fields': {'screen_reader': 'NVDA 2026.1', 'pages_checked': '3'}, 'items': dict(SR_OK, tables={'result': 'na'})}
    assert 'items.tables.note' in errs(sr, {'n_pages': 9, 'found': {'tables': '12 tables'}}, 'screen_reader')   # found: N/A needs a note
    assert REL.validate('screen_reader', sr, {'n_pages': 9, 'found': {}})['items']['tables'] == {'result': 'na'}
    prev = chk(A, failing(SR_OK, 'links'))                                                               # a Pass after a Fail
    assert 'items.links.note' in errs(sr, {'n_pages': 9, 'previous': prev}, 'screen_reader')
    assert 'fields.screen_reader' in errs(dict(sr, fields={'pages_checked': '3'}), section='screen_reader')

def test_found_reads_the_record():
    rec = {'verify': {'tree': {'types': {'Table': 2, 'Link': 1, 'Figure': 0}}}, 'intake': {'ocr': {'pages_with_ocr_text': [1, 2]}}}
    assert REL.found(rec) == {'tables': '2 tables', 'links': '1 link', 'ocr_pages': 'OCR text on 2 pages'}
    rec['verify']['tree']['types']['Figure'] = 3                          # keyed as the checklist's `found` (a stage-2 find)
    assert REL.found(rec)['figures'] == '3 figures' and {x['found'] for x in REL.CHECKLIST['screen_reader'] if x.get('found')} <= set(REL.found(
        {'verify': {'tree': {'types': {'Figure': 1, 'Table': 1, 'Link': 1, 'L': 1, 'Formula': 1}}}, 'intake': {'ocr': {'pages_with_ocr_text': [1]}}}))
    sr = {'by': 'K', 'fields': {'screen_reader': 'NVDA', 'pages_checked': '1'}, 'items': dict(SR_OK, alt_text={'result': 'na'})}
    with pytest.raises(REL.Invalid) as e: REL.validate('screen_reader', sr, {'n_pages': 5, 'found': REL.found(rec)})
    assert 'items.alt_text.note' in dict(e.value.errors)

def test_title_case_keeps_as_lowercase():
    assert title_case('Untagged text marked as decoration') == 'Untagged Text Marked as Decoration'
    assert title_case('Mark as shipped') == 'Mark as Shipped' and title_case('as it was') == 'As It Was'

# ------------------------------------------------------------------ the record lock
def test_the_lock_raises_when_taken_twice_in_one_thread(tmp_path):
    with runlock.record_lock(str(tmp_path)):
        with pytest.raises(RuntimeError):
            with runlock.record_lock(str(tmp_path / '.' )): pass               # the same run by another spelling (realpath)
    with runlock.record_lock(str(tmp_path)): pass                              # released: free again

def test_the_lock_keeps_threads_and_processes_apart(tmp_path):
    R = str(tmp_path); got = threading.Event(); go = threading.Event()
    def hold():
        with runlock.record_lock(R):
            got.set(); go.wait(5)
    t = threading.Thread(target=hold); t.start(); got.wait(5)
    t0 = time.monotonic()
    with pytest.raises(runlock.Busy) as e:
        with runlock.record_lock(R, wait=0.3): pass
    assert str(e.value) == runlock.BUSY and 0.25 < time.monotonic() - t0 < 2
    go.set(); t.join(5)
    p = subprocess.Popen([sys.executable, '-c', 'import sys,time; sys.path.insert(0, sys.argv[2]); from lib import runlock\n'
                          'with runlock.record_lock(sys.argv[1]):\n print("held", flush=True); time.sleep(3)', R, HERE], stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == 'held'
    with pytest.raises(runlock.Busy):
        with runlock.record_lock(R, wait=0.3): pass
    p.wait(10)
    with runlock.record_lock(R, wait=1): pass

# ------------------------------------------------------------------ the writer, on a synthetic finished run
def finished_run(tmp_path, session_sha=None, record_sha=None):
    R = tmp_path / 'run'; R.mkdir(parents=True)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(300, 300)); doc.save(str(R / 'b_remediated.pdf'), deterministic_id=True)
    rec = {'document': {'file': 'b.pdf', 'output': 'b_remediated.pdf', 'pages': 1, **({'output_sha256': record_sha} if record_sha else {})},
           'review': {'session': '002'}}
    core.save(str(R / 'record.json'), rec)
    if session_sha is not None:
        (R / 'reviews' / 'sessions').mkdir(parents=True)
        core.save(str(R / 'reviews' / 'sessions' / '002.json'), {'id': '002', 'status': 'applied', 'version': {'pdf_sha256': session_sha}})
    return str(R)

def pac_data(): return {'by': 'Kim', 'fields': {'pages_checked': '1'}, 'items': PAC_OK}

def test_first_check_takes_the_disk_hash_after_the_sessions_own(tmp_path):
    R = finished_run(tmp_path / 'one'); disk = REL.sha_file(os.path.join(R, 'b_remediated.pdf'))      # no session hash: taken as it is
    c = M.record(R, 'pac', pac_data(), say=lambda *a: None)
    rec = core.load(os.path.join(R, 'record.json'))
    assert c['pdf']['sha256'] == disk and rec['document']['output_sha256'] == disk
    assert rec['document']['output_sha256_from'].startswith('first check, ') and rec['manual_checks']['pac']['state'] == 'completed'
    R2 = finished_run(tmp_path / 'two', session_sha='0' * 64)                   # the session's own hash matches: accepted
    core.save(os.path.join(R2, 'reviews', 'sessions', '002.json'),               # (pikepdf's /ID follows the clock: hash this file)
              {'id': '002', 'status': 'applied', 'version': {'pdf_sha256': REL.sha_file(os.path.join(R2, 'b_remediated.pdf'))}})
    assert M.record(R2, 'pac', pac_data(), say=lambda *a: None)['id'] == 1
    R3 = finished_run(tmp_path / 'three', session_sha='0' * 64)                 # it does not: refused, nothing written
    with pytest.raises(S.Refused, match='last review produced'): M.record(R3, 'pac', pac_data(), say=lambda *a: None)
    assert not os.path.exists(os.path.join(R3, 'release'))

def test_record_refuses_a_changed_or_undescribed_pdf(tmp_path):
    R = finished_run(tmp_path, record_sha='9' * 64)
    with pytest.raises(S.Refused, match='not the one this book'): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    R2 = finished_run(tmp_path / 'b')
    with pytest.raises(S.Refused, match='changed since this page was opened'): M.record(R2, 'pac', pac_data(), shown_sha='1' * 64, say=lambda *a: None)

def test_record_is_refused_while_a_new_version_is_being_made(tmp_path):
    R = finished_run(tmp_path)
    os.makedirs(os.path.join(R, 'reviews', 'sessions'), exist_ok=True)
    core.save(os.path.join(R, 'reviews', 'sessions', '003.json'), {'id': '003', 'status': 'finished'})   # a re-apply under way (or failed)
    with pytest.raises(S.Refused, match='Session 3 is finished and not yet applied'): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    os.remove(os.path.join(R, 'reviews', 'sessions', '003.json')); os.makedirs(os.path.join(R, 'reviews', 'work'))
    with pytest.raises(S.Refused, match='being made'): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    os.rmdir(os.path.join(R, 'reviews', 'work')); core.save(os.path.join(R, 'reviews', 'promoting.json'), {'stage': 'move new'})
    with pytest.raises(S.Refused, match='did not finish'): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    assert not os.path.exists(os.path.join(R, 'release'))

def test_a_record_waits_for_the_lock_and_gives_up_in_plain_words(tmp_path):
    R = finished_run(tmp_path)
    with runlock.record_lock(R):
        box = {}
        def run():
            try: M.record(R, 'pac', pac_data(), wait=0.3, say=lambda *a: None)
            except S.Refused as e: box['e'] = str(e)
        th = threading.Thread(target=run); th.start(); th.join(5)
    assert box['e'] == runlock.BUSY

def test_ocr_verdict_reads_record_json_inside_the_lock(tmp_path):
    """A verdict and a manual check at once: the verdict's load of record.json is inside the record lock, so a check
    recorded first is not lost when the verdict writes record.json."""
    from tests.test_ocr_verdict import run_folder, intake
    R = run_folder(tmp_path, intake(added=(1,), pages=3))
    shutil.copy(os.path.join(R, '_intake', 'intake.pdf'), os.path.join(R, 'b_remediated.pdf'))
    core.save(os.path.join(R, 'record.json'), {'document': {'output': 'b_remediated.pdf', 'pages': 3}, 'intake': intake(added=(1,), pages=3)})
    box = {}
    with runlock.record_lock(R):                                             # a writer holds it: the verdict waits, then gives up
        def run():
            try: O.record(R, {'verdict': 'approved', 'reviewer': 'Kim', 'reason': 'read'}, via='page', held=True, wait=0.3, say=lambda *a: None)
            except S.Refused as e: box['e'] = str(e)
        th = threading.Thread(target=run); th.start(); th.join(5)
    assert box['e'] == runlock.BUSY
    assert core.load(os.path.join(R, '_intake', 'intake.json'))['review']['ocr_text_approved'] is None   # nothing written
    M.record(R, 'pac', pac_data(), say=lambda *a: None)
    O.record(R, {'verdict': 'approved', 'reviewer': 'Kim', 'reason': 'read'}, via='page', held=True, say=lambda *a: None)
    rec = core.load(os.path.join(R, 'record.json'))
    assert rec['manual_checks']['pac']['by'] == 'Kim' and rec['intake']['review']['ocr_text_approved']['verdict'] == 'approved'

def test_promote_remirrors_a_check_recorded_during_the_reapply(tmp_path):
    R = finished_run(tmp_path); disk = REL.sha_file(os.path.join(R, 'b_remediated.pdf'))
    W = os.path.join(R, 'reviews', 'work'); os.makedirs(W)
    shutil.copy(os.path.join(R, 'b_remediated.pdf'), os.path.join(W, 'b_remediated.pdf'))
    core.save(os.path.join(W, 'record.json'), {'document': {'output': 'b_remediated.pdf', 'output_sha256': disk}, 'review': {'session': '003'},
                                                'manual_checks': {'pac': None}})             # written by report.py before the check
    os.makedirs(os.path.join(R, 'release'))
    core.save(os.path.join(R, 'release', 'checks.json'), {'schema': REL.SCHEMA, 'pac': [chk(disk, PAC_OK)], 'screen_reader': []})
    S.promote(R, '003', 'b_remediated.pdf', say=lambda *a: None)
    rec = core.load(os.path.join(R, 'record.json'))
    assert rec['manual_checks']['pac']['state'] == 'completed' and not os.path.exists(os.path.join(R, 'reviews', 'promoting.json'))
    assert os.path.exists(os.path.join(R, 'reviews', 'versions', '002', 'record.json'))

def test_mark_pending_writes_whole_files_under_the_lock(tmp_path):
    R = finished_run(tmp_path)
    with runlock.record_lock(R):
        box = {}
        def run():
            try: S.mark_pending(R, None)
            except Exception as e: box['e'] = e
        th = threading.Thread(target=run); th.start(); th.join(0.5)
        assert th.is_alive()                                                   # waiting for the lock (a command waits up to 120 s)
    th.join(10)
    assert 'e' not in box and not [n for n in os.listdir(R) if n.endswith('.tmp')]

# ------------------------------------------------------------------ R1: one rule for "a newer session"
def sessions_at(R, current, rows):
    rec = core.load(os.path.join(R, 'record.json')); rec['review'] = {'session': current}; core.save(os.path.join(R, 'record.json'), rec)
    shutil.rmtree(os.path.join(R, 'reviews', 'sessions'), ignore_errors=True); os.makedirs(os.path.join(R, 'reviews', 'sessions'))
    for sid, st in rows: core.save(os.path.join(R, 'reviews', 'sessions', f'{sid}.json'), {'id': sid, 'status': st})

def test_a_finished_session_older_than_the_current_result_never_blocks(tmp_path):
    from webapp import runs
    R = finished_run(tmp_path)
    sessions_at(R, '005', [('004', 'finished'), ('005', 'applied')])         # 4's apply failed, then 5 was reviewed and applied
    assert S.newer(R)['finished'] is None and runs.unapplied(R) is None and M.being_made(R) is None
    assert M.record(R, 'pac', pac_data(), say=lambda *a: None)['id'] == 1
    sessions_at(R, '005', [('004', 'finished'), ('005', 'applied'), ('006', 'finished')])   # 6: newer, finished (applying, or failed)
    assert S.newer(R)['finished']['id'] == '006' and runs.unapplied(R)['id'] == '006'
    with pytest.raises(S.Refused, match='Session 6 is finished'): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    sessions_at(R, 'ai', [('001', 'finished'), ('002', 'applied')])          # a record that lags: Apply hides 1 (the newest done
    assert S.newer(R)['finished'] is None                                    # session decides), and Record is refused
    with pytest.raises(S.Refused, match='out of step'): M.record(R, 'pac', pac_data(), say=lambda *a: None)

def test_the_newer_version_line_comes_from_the_session_files(tmp_path):
    R = finished_run(tmp_path); disk = REL.sha_file(os.path.join(R, 'b_remediated.pdf'))
    os.makedirs(os.path.join(R, 'release'))
    core.save(os.path.join(R, 'release', 'shipped.json'), [ship(disk)])
    sessions_at(R, '005', [('005', 'applied'), ('006', 'open')])             # Review Again after shipping: 6 is open
    rec = core.load(os.path.join(R, 'record.json')); rec['document']['output_sha256'] = disk
    st = REL.status(REL.load(R, rec), disk, False, REL.load(R, rec).get('newer'), '005')
    assert st['name'] == 'Shipped' and st['newer'] == 'Newer version: Session 6 being reviewed'
    sessions_at(R, '005', [('005', 'applied'), ('006', 'finished')])         # a page Finish whose apply failed
    assert REL.status(REL.load(R, rec), disk, False, REL.load(R, rec)['newer'], '005')['newer'] == 'Newer version: Session 6 finished, not applied'

# ------------------------------------------------------------------ a failed refresh never leaves a check without its record
def test_a_check_is_rolled_back_when_the_refresh_fails(tmp_path, monkeypatch):
    R = finished_run(tmp_path); before = open(os.path.join(R, 'record.json')).read()
    def boom(*a, **k): raise ImportError('as under an old Python')
    monkeypatch.setattr(M, 'write_run', boom)
    with pytest.raises(ImportError): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    assert not os.path.exists(os.path.join(R, 'release', 'checks.json'))   # the first check: no file left
    assert open(os.path.join(R, 'record.json')).read() == before
    monkeypatch.undo()
    M.record(R, 'pac', pac_data(), say=lambda *a: None)                      # a check that worked, then one whose refresh fails
    kept = open(os.path.join(R, 'release', 'checks.json')).read()
    monkeypatch.setattr(M, 'write_run', boom)
    with pytest.raises(ImportError): M.record(R, 'pac', pac_data(), say=lambda *a: None)
    assert open(os.path.join(R, 'release', 'checks.json')).read() == kept   # back to the one that worked
    rec = core.load(os.path.join(R, 'record.json'))
    assert REL.part(REL.load(R), 'pac', rec['document']['output_sha256'])['state'] == 'completed'   # it counts on the same file

# ------------------------------------------------------------------ the current version's own status (review 16 J1)
def test_status_current_is_the_current_versions_own_status_before_and_after_shipping():
    """Mark as Shipped (stage 4) is gated on status['current']['name'] == 'Ready': after a shipment glance.ready is False
    even when a newer version is Ready."""
    g = {'schema': G.SCHEMA, 'ship': [{'what': w, 'ok': True, 'text': 'x'} for w in G.SHIP_BASE], 'safety': FIVE, 'needs_person': {'total': 0}}
    rec = {'document': {'output_sha256': B}}
    both_b = dict(pac=[chk(A, PAC_OK), chk(B, failing(PAC_OK, 'contrast'))], sr=[chk(A, SR_OK), chk(B, SR_OK)])
    out = G.with_release(g, rec, rel(**both_b, shipped=[ship(A)]))                # shipped A, then a newer Ready version B
    assert out['status']['name'] == 'Shipped' and out['ready'] is False and out['status']['current'] == {'name': 'Ready', 'issues': 1}
    out = G.with_release(g, rec, rel(pac=[chk(A, PAC_OK), chk(B, PAC_OK)], sr=[chk(A, SR_OK)], shipped=[ship(A)]))   # B: Pending Evaluation
    assert out['status']['current'] == {'name': 'Pending Evaluation', 'issues': 0}
    bad = dict(g, ship=[dict(s, ok=False) if s['what'] == 'OCR text approved' else s for s in g['ship']])     # B: a base requirement unsatisfied
    assert G.with_release(bad, rec, rel(**both_b, shipped=[ship(A)]))['status']['current']['name'] == 'Not Ready'
    for r in (rel(), rel(pac=[chk(B, PAC_OK)]), rel(**both_b)):                     # no shipment: the status itself
        st = G.with_release(g, rec, r)['status']
        assert st['current'] == {'name': st['name'], 'issues': st['issues']}

def test_the_app_reads_the_status_against_the_file_on_disk(tmp_path):
    """In the app the current version is the file on disk (webapp/manualpage.py app_sha), not only the record's hash: a
    run whose record has no output_sha256 yet, with both parts recorded on the disk file, reads Ready."""
    from webapp import manualpage as MP, runs
    R = finished_run(tmp_path); disk = REL.sha_file(os.path.join(R, 'b_remediated.pdf'))
    os.makedirs(os.path.join(R, 'release'))
    core.save(os.path.join(R, 'release', 'checks.json'), rel(pac=[chk(disk, PAC_OK)], sr=[chk(disk, SR_OK)])['checks'])
    rec = core.load(os.path.join(R, 'record.json')); rec.pop('review')
    rec['glance'] = {'schema': G.SCHEMA, 'ship': [{'what': w, 'ok': True, 'text': 'x'} for w in G.SHIP_BASE], 'safety': FIVE, 'needs_person': {'total': 0}}
    assert MP.app_sha(R, rec) == disk and not rec['document'].get('output_sha256')
    assert G.with_release(rec['glance'], rec, REL.load(R))['status']['name'] == 'Pending Evaluation'   # the record's hash alone: none
    assert runs.ready(R, rec)['status'] == 'Ready' and MP.strip(R, rec)['status'] == 'Ready'

def test_a_pdf_copied_back_by_hand_is_a_changed_file_never_ready(tmp_path):
    """Review 18 K1: results were recorded on 001's PDF; a later apply made 002 (the record's hash); then 001's PDF is
    copied back over 002 by hand. The record's hash comes first, so the status is about 002, and the file on disk reads
    as changed: never Ready in runs.ready(), the strip or status['current'] (stage 4's gate)."""
    from webapp import manualpage as MP, runs
    R = finished_run(tmp_path); disk = REL.sha_file(os.path.join(R, 'b_remediated.pdf'))   # the file on disk is 001's
    os.makedirs(os.path.join(R, 'release'))
    core.save(os.path.join(R, 'release', 'checks.json'), rel(pac=[chk(disk, PAC_OK)], sr=[chk(disk, SR_OK)])['checks'])
    rec = core.load(os.path.join(R, 'record.json')); rec.pop('review'); rec['document']['output_sha256'] = C   # 002's
    rec['glance'] = {'schema': G.SCHEMA, 'ship': [{'what': w, 'ok': True, 'text': 'x'} for w in G.SHIP_BASE], 'safety': FIVE, 'needs_person': {'total': 0}}
    assert MP.app_sha(R, rec) == C and MP.disk_state(R, rec)['same'] is False
    r = runs.ready(R, rec)
    assert r['answer'] == 'No' and r['status'] == MP.CHANGED_STATUS
    s = MP.strip(R, rec)
    assert s['status'] == MP.CHANGED_STATUS and s['refusal'] == MP.strip_words(MP.CHANGED_BY_HAND)   # the strip: one line for both actions (R2)
    g = MP.app_glance(R, rec, rec['glance'])
    assert g['ready'] is False and g['status']['current']['name'] == 'Not Ready'
    core.save(os.path.join(R, 'record.json'), rec)                                # the evaluation page reads the record from disk
    st = MP.state(R, 'r')
    assert st['status'] == MP.CHANGED_STATUS and st['refusal'] == MP.CHANGED_BY_HAND
