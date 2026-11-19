"""test_editlinks.py: the link between a run and its hand-edited copies in the offline dashboards (#98): lib/editlinks.py's
states, the notes on review.html (parent and copy), the mark in summary.html, and report_html.refresh_page.

    python -m pytest tests/test_editlinks.py -q

No book, no model: the runs are folders holding only what the rules read (tests/test_handedit.py runs handedit.py itself).
"""
import os, sys, json, threading
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import report_html as H  # noqa: E402
from lib import editlinks as EL, runlock  # noqa: E402

MD = '# Review\n\n## Automated Checks\n\n'
REC = {'document': {'pages': 3}}

def finished(R, rec=REC, page=True):
    """A finished run: record.json and review.md, and review.html when page."""
    R.mkdir(parents=True, exist_ok=True)
    (R / 'record.json').write_text(json.dumps(rec)); (R / 'review.md').write_text(MD)
    if page: H.review_html(str(R), rec, MD, {})
    return R

def child(R, label, state, by='Pat', note='new photo'):
    """An edited copy of R, as handedit.py import leaves it, listed in R's hand_edits.json."""
    C = R.parent / label
    if state != 'removed':
        (C / '_handedit').mkdir(parents=True)
        (C / '_handedit' / 'hand_edit.json').write_text(json.dumps({'to': 'review', 'parent': {'run': str(R)}}))
    if state == 'waiting': (C / 'workorder.ai.json').write_text('{}')
    if state == 'finished': finished(C, {**REC, 'hand_edit': {'parent': {'run': str(R)}}})
    hp = R / 'hand_edits.json'; d = json.loads(hp.read_text()) if hp.exists() else {'exports': [], 'children': []}
    d['children'].append({'when': '2026-11-09T10:00:00', 'run': str(C), 'by': by, 'note': note}); hp.write_text(json.dumps(d))
    return C

def page(R, rec=REC): return open(H.review_html(str(R), rec, MD, {}), encoding='utf-8').read()

def test_each_copy_has_a_state_in_the_order_it_was_brought_back(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1')
    assert EL.copies(str(R)) == [] and EL.parent(str(R), {}) is None
    for label, st in (('done', 'finished'), ('wait', 'waiting'), ('cold', 'not started'), ('gone', 'removed')): child(R, label, st)
    assert [(c['label'], c['state'], c['by']) for c in EL.copies(str(R))] == [
        ('done', 'finished', 'Pat'), ('wait', 'waiting for its review', 'Pat'), ('cold', 'not started', 'Pat'), ('gone', 'removed', 'Pat')]

def test_the_parent_comes_from_the_record_or_before_it_from_handedit(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1'); C = child(R, 'cold', 'not started')
    assert EL.parent(str(C), None) == {'run': str(R), 'label': 'book/r1', 'state': 'finished'}            # _handedit/hand_edit.json
    assert EL.parent(str(C), {'hand_edit': {'parent': {'run': '/nowhere/book/r0'}}})['state'] == 'removed'   # the record first

def test_hand_edit_reads_the_record_first_and_is_none_for_any_other_run(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1'); C = child(R, 'cold', 'not started')
    assert EL.hand_edit(str(C))['parent']['run'] == str(R)                                     # _handedit/hand_edit.json (#99)
    assert EL.hand_edit(str(C), {'hand_edit': {'base_sha256': 'b' * 64}}) == {'base_sha256': 'b' * 64}
    assert EL.hand_edit(str(R), {}) is None and EL.hand_edit(str(R), {'hand_edit': 'damaged'}) is None
    assert EL.parent(str(R), {'hand_edit': ['damaged']}) is None
    assert EL.parent(str(R), {'hand_edit': {'parent': 'x'}}) is None and EL.parent(str(R), {'hand_edit': {'parent': {'run': 3}}}) is None

def test_the_parents_page_lists_each_copy_and_links_only_a_finished_one(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1')
    for label, st in (('done', 'finished'), ('wait', 'waiting'), ('cold', 'not started'), ('gone', 'removed')): child(R, label, st)
    child(R, 'anon', 'not started', by=None, note=None)
    p = page(R)
    assert 'Edited Copies' in p and '5 new runs' in p and 'Evaluate and ship the version you mean to keep.' in p
    assert '<a href="../done/review.html">done</a>: edited by Pat on November 9, 2026, note: "new photo". Finished.' in p
    assert '<strong>wait</strong>' in p and 'Waiting for its review (no dashboard yet).' in p
    assert '<strong>cold</strong>' in p and 'Not started (no dashboard yet).' in p
    assert '<strong>gone</strong>' in p and 'Its folder is no longer there.' in p
    assert 'edited by a person (name not given)' in p and 'no note given' in p
    assert str(tmp_path) not in p and 'None' not in p and 'unknown' not in p
    assert p.index('Edited Copies') < p.index('Ready to Ship?')                 # read before the run's own status

def test_a_copys_page_links_its_parent_and_says_when_it_is_gone(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1'); C = child(R, 'done', 'finished')
    rec = json.loads((C / 'record.json').read_text())
    assert 'Made from a hand edit of <a href="../r1/review.html">book/r1</a>.' in page(C, rec)
    (R / 'review.html').unlink()
    assert 'Made from a hand edit of <strong>book/r1</strong> (that run has no dashboard).' in page(C, rec)
    gone = {**rec, 'hand_edit': {'parent': {'run': str(tmp_path / 'runs' / 'book' / 'r0')}}}
    assert 'Made from a hand edit of <strong>book/r0</strong>: that run\'s folder is no longer there.' in page(C, gone)

def test_a_previous_versions_page_names_no_copy(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1'); child(R, 'done', 'finished')
    V = R / 'reviews' / 'versions' / '001'; finished(V, page=False)
    assert 'Edited Copies' in page(R) and 'Edited Copies' not in page(V)

def test_summary_marks_a_book_with_an_edited_copy_and_links_it(tmp_path):
    B = tmp_path / 'runs' / 'batches' / 'b1'; R = finished(B / 'book'); finished(B / 'other')
    C = tmp_path / 'runs' / 'book' / 'fromb'                                   # handedit.py: runs/<name>/<label>/
    finished(C); d = {'children': [{'when': '2026-11-09T10:00:00', 'run': str(C), 'by': 'Pat', 'note': 'n'}]}
    (R / 'hand_edits.json').write_text(json.dumps(d))
    rows = {r['name']: r for r in H.summary_rows(str(B))}
    assert rows['book']['edited'] == [{'label': 'fromb', 'state': 'finished', 'href': '../../book/fromb/review.html'}]
    assert rows['other']['edited'] == []
    s = open(H.summary_html(str(B)), encoding='utf-8').read()
    assert s.count('Edited cop') == 1 and 'Edited copy: <a href="../../book/fromb/review.html">fromb</a> (finished)' in s
    assert '<a href="../../../book/fromb/review.html">fromb</a>' in page(R)    # from the book's own folder, one level down

def test_refresh_page_redraws_the_page_and_never_stops_the_caller(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1'); child(R, 'cold', 'not started')
    said = []
    H.refresh_page(str(R), said.append)
    assert '<strong>cold</strong>' in (R / 'review.html').read_text(encoding='utf-8') and 'rebuilt' in said[0]
    H.refresh_page(str(tmp_path / 'nowhere'), said.append); H.refresh_page(None, said.append)
    assert len(said) == 1                                                      # no record: nothing to draw, nothing said
    held, done = threading.Event(), threading.Event()
    def hold():
        with runlock.record_lock(str(R)): held.set(); done.wait(30)
    t = threading.Thread(target=hold); t.start(); held.wait(5)
    old, runlock.REQUEST_WAIT = runlock.REQUEST_WAIT, 0.2
    try: H.refresh_page(str(R), said.append)
    finally: runlock.REQUEST_WAIT = old; done.set(); t.join()
    assert 'not rebuilt (the run is busy)' in said[-1]

def test_a_previous_version_is_never_drawn_again(tmp_path):
    R = finished(tmp_path / 'runs' / 'book' / 'r1'); child(R, 'done', 'finished')
    V = R / 'reviews' / 'versions' / '001'; finished(V, page=False)
    (V / 'review.html').write_text('<p class="replaced">This result (Session 1) was replaced by Session 2.</p>')
    said = []
    H.refresh_page(str(V), said.append)
    assert 'was replaced by' in (V / 'review.html').read_text() and said == []   # its banner kept, nothing said

@pytest.mark.parametrize('bad', [5, ['x'], {'a': 1}, None, ''])
def test_a_damaged_hand_edits_file_never_breaks_a_page(tmp_path, bad):
    R = finished(tmp_path / 'runs' / 'book' / 'r1')
    (R / 'hand_edits.json').write_text(json.dumps({'children': [{'run': bad, 'by': 'Pat'}, 'not a dict']}))
    assert [(c['label'], c['state'], c['run']) for c in EL.copies(str(R))] == [('run not recorded', 'removed', None)]
    assert 'Its folder is no longer there.' in page(R)
    assert EL.parent(str(R), {'hand_edit': {'parent': {'run': bad}}}) is None
    assert EL.parent(str(R), {'hand_edit': {'parent': 'x'}}) is None

def test_one_wording_for_each_state():
    assert EL.words('removed') == 'Its folder is no longer there.' and EL.words('removed', inline=True) == 'its folder is no longer there'
    assert EL.words('being prepared') == 'being prepared'                   # the app's own state, shown as it is
