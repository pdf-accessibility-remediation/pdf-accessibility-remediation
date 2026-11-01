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

# ------------------------------------------------------------------ the PAC line: checks follow the hash, whatever it is
def test_pac_line_counts_exactly_when_the_hash_is_the_same():
    assert REL.pac_line(rel(), A) == (False, 'no (not done for this version)')
    r = rel(pac=[chk(A, PAC_OK)])
    assert REL.pac_line(r, A) == (True, 'yes (Kim on 2026-11-01)')               # the same hash (an apply that gave the same bytes): it counts
    ok, txt = REL.pac_line(r, B)                                                 # another hash: an earlier version
    assert not ok and txt == 'no (done on an earlier version, Session 2, by Kim on 2026-11-01; check this version)'
    assert REL.pac_line(r, None)[0] is False                                     # no recorded hash: nothing counts
    ok, txt = REL.pac_line(rel(pac=[chk(A, failing(PAC_OK, 'contrast'))]), A)
    assert not ok and txt == 'no (1 item failed: Contrast; Kim on 2026-11-01)'

def test_v1_reads_fail_closed_and_the_pdfua_item_never_blocks():
    assert REL.failed(chk(A, dict(PAC_OK, pac_pdfua={'result': 'fail', 'note': 'x'})), 'pac') == []
    assert REL.failed(chk(A, dict(PAC_OK, contrast={'result': 'maybe'})), 'pac') == ['contrast']           # an unknown result
    assert REL.failed(chk(A, dict(PAC_OK, contrast={'result': 'fail', 'note': 'n', 'accepted': {'by': 'X'}})), 'pac') == ['contrast']
    assert REL.failed(chk(A, dict(PAC_OK, contrast={'result': 'pass', 'accepted': {'by': 'X'}})), 'pac') == ['contrast']
    assert REL.failed(chk(A, {k: v for k, v in PAC_OK.items() if k != 'colour'}), 'pac') == ['colour']   # missing
    assert REL.failed(chk(A, dict(PAC_OK, later_item={'result': 'fail'})), 'pac') == ['later_item']    # a later version's item

# ------------------------------------------------------------------ the status
def test_status_before_and_after_shipping():
    assert REL.status(rel(), A, False)['name'] == 'Not Ready'
    assert REL.status(rel(), A, True)['name'] == 'Ready'
    assert REL.status(rel(shipped=[ship(A)]), A, True)['text'] == 'Shipped'
    after = chk(A, SR_OK, recorded='2026-11-03T10:00:00')
    assert REL.status(rel(sr=[after], shipped=[ship(A)]), A, True)['text'] == 'Verified'
    before = chk(A, SR_OK, recorded='2026-11-01T10:00:00')                     # before the shipment, on the same file: derived
    st = REL.status(rel(sr=[before], shipped=[ship(A)]), A, True)
    assert st['name'] == 'Verified' and st['text'] == 'Verified (checked before shipping, 2026-11-01)'
    assert REL.status(rel(sr=[chk(A, failing(SR_OK, 'tables'))], shipped=[ship(A)]), A, True)['name'] == 'Needs Rework'
    assert REL.status(rel(sr=[chk(B, SR_OK)], shipped=[ship(A)]), A, True)['name'] == 'Shipped'   # another file's check

def test_status_withdrawal_falls_back_and_the_newer_version_line():
    w = ship(B, 2, withdrawn={'by': 'Lee', 'date': '2026-11-04', 'reason': 'wrong file'})
    assert REL.status(rel(shipped=[ship(A), w]), A, False)['name'] == 'Shipped'          # the latest non-withdrawn: shipment 1
    assert REL.status(rel(shipped=[dict(ship(A), withdrawn={'by': 'L'})]), A, True)['name'] == 'Ready'   # none left: pre-ship rules
    r = rel(sr=[chk(A, failing(SR_OK, 'tables'))], shipped=[ship(A)])
    st = REL.status(r, B, False, None, '003')                                     # a newer version, applied: Needs Rework stays
    assert st['name'] == 'Needs Rework' and st['newer'] == 'Newer version (Session 3): Ready to Ship? No'
    assert REL.status(r, B, False, {'finished': None, 'open': '004'})['newer'] == 'Newer version: Session 4 being reviewed'
    assert REL.status(r, A, False, {'finished': None, 'open': '004'})['newer'] == 'Newer version: Session 4 being reviewed'   # the shipped file is still current
    assert REL.status(r, A, False, {'finished': '004', 'open': '005'})['newer'] == 'Newer version: Session 4 finished, not applied'
    assert REL.status(r, A, False)['newer'] is None
    assert REL.status(rel(), A, False, {'finished': '004', 'open': None})['newer'] is None              # before any shipment: no line

def test_a_failed_screen_reader_check_on_this_version_keeps_ready_at_no():
    g = {'schema': G.SCHEMA, 'ship': [{'what': w, 'ok': True, 'text': 'yes'} for w in G.SHIP_BASE]}
    rec = {'document': {'output_sha256': A}}
    assert G.with_release(g, rec, rel(pac=[chk(A, PAC_OK)]))['ready'] is True
    out = G.with_release(g, rec, rel(pac=[chk(A, PAC_OK)], sr=[chk(A, failing(SR_OK, 'links'))]))
    assert out['ready'] is False and out['ship'][-1]['what'] == 'Screen-reader check'
    assert out['ship'][-1]['text'] == 'no (1 item failed on this version: Links Say Where They Go; Kim on 2026-11-01)'
    assert len(G.with_release(g, rec, rel(pac=[chk(A, PAC_OK)], sr=[chk(B, failing(SR_OK, 'links'))]))['ship']) == 4   # another file: no line

def test_ready_needs_the_current_schema_and_all_three_base_lines():
    """R2: a 0.3 glance (five safety checks) with a counting PAC check reads No; so does a 0.4 glance missing a base line."""
    rec = {'document': {'output_sha256': A}}; r = rel(pac=[chk(A, PAC_OK)])
    base = [{'what': w, 'ok': True, 'text': 'yes'} for w in G.SHIP_BASE]
    assert G.with_release({'schema': G.SCHEMA, 'ship': base}, rec, r)['ready'] is True
    assert G.with_release({'schema': 'glance/0.3', 'ship': base}, rec, r)['ready'] is False
    assert G.with_release({'schema': G.SCHEMA, 'ship': base[:1] + base[2:]}, rec, r)['ready'] is False
    assert G.with_release({'schema': G.SCHEMA, 'ship': []}, rec, r)['ready'] is False             # the PAC line alone

def test_a_stored_old_glance_marked_ready_is_not_ready_now():
    from webapp import runs
    old = {'schema': 'glance/0.3', 'ready': True, 'ship': [{'what': w, 'ok': True, 'text': 'yes'} for w in G.SHIP_BASE]
           + [{'what': 'Manual check (PAC)', 'ok': None, 'text': 'not run'}]}
    r = runs.ready('/nonexistent', {'glance': old, 'document': {}})
    assert r['answer'] == 'No' and r['status'] == 'Not Ready' and r['lines'][-1] == 'Manual check (PAC): no (not done for this version)'

# ------------------------------------------------------------------ the sixth safety check
SAFE = ['Every page looks the same as the original', 'Published text unchanged', 'All content tagged or marked as decoration',
        'Tag-tree index points only into the tree', 'Fonts: every embedded font program could be read']
def md_with(vera_ok):
    rows = [f'| {n} | OK | x |' for n in SAFE] + [f'| veraPDF: no rule newly failing or failing more often | {"OK" if vera_ok else "**CHECK**"} | x |']
    return '\n'.join(['# Remediation Review: b.pdf', '', '## Automated Checks', '', '| Check | Result | Detail |', '|---|---|---|'] + rows + [''])
def vera(rules): return {'rules': rules, 'totals': {'wcag_failed_rules': 0, 'wcag_failed_checks': 0}}

def test_sixth_safety_check_counts_wcag_rules_only_and_not_run_is_not_checked():
    pdfua_only = {'verapdf': {'before': vera([]), 'after': vera([{'id': '7.9-1', 'scope': 'ua_only', 'failed': 3}])}}
    g = G.glance(pdfua_only, md_with(False))
    assert g['safety_ok'] and len(g['safety']) == 6
    vi = [x for x in g['issues'] if x['text'].startswith('veraPDF:')]
    assert vi and vi[0]['rank'] == 2 and vi[0]['kind'] == 'check'               # not a safety issue: the Safety card says OK
    wcag_new = {'verapdf': {'before': vera([]), 'after': vera([{'id': '7.18.1-1', 'scope': 'wcag', 'failed': 1}])}}
    g = G.glance(wcag_new, md_with(False))
    assert not g['safety_ok'] and g['ship'][2]['text'] == f'failed: {G.SAFETY_VERA}'
    assert [x for x in g['issues'] if x['text'].startswith('veraPDF:')][0]['rank'] == 0
    g = G.glance({'verapdf': {'before': {'not_run': 'VERAPDF=off'}, 'after': {'not_run': 'VERAPDF=off'}}}, md_with(False))
    assert not g['safety_ok'] and not g['ready'] and g['safety'][-1]['state'] == 'not checked'
    assert g['ship'][2]['text'] == f'not checked: {G.SAFETY_VERA} (veraPDF did not run on both files)'
    assert 'NOT CHECKED – no WCAG rule newly failing (veraPDF) (veraPDF did not run on both files)' in '\n'.join(G.glance_md(g))
    import report_html as H
    assert H.safety_state(g) == 'not checked'

def test_status_line_sits_above_ready_to_ship_and_the_old_heading_still_parses():
    L = G.glance_md(G.glance({}, md_with(True)))
    i = L.index('**Status:** Not Ready')
    assert L[i + 2] == '**Ready to ship?** No' and L[i + 3].startswith('- ')
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
    assert 'fields.pages_checked' in errs(dict(good, fields={}))                                          # the spot-check's pages
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
    doc = pikepdf.new(); doc.add_blank_page(page_size=(300, 300)); doc.save(str(R / 'b_remediated.pdf'))
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
    assert rec['document']['output_sha256_from'].startswith('first check, ') and rec['manual_checks']['pac']['state'] == 'counts'
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
    assert rec['manual_checks']['pac']['state'] == 'counts' and not os.path.exists(os.path.join(R, 'reviews', 'promoting.json'))
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
    assert REL.pac_line(REL.load(R), rec['document']['output_sha256'])[0] is True   # it counts on the same file
