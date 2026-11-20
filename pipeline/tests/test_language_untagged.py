"""Words the finder could not place (#161 addition 3; review 02 M9, review 04 M1 and L2; Patrick, 2026-11-19): counted in
the Language Tags line's details and shown under "Languages", never a condition of Ready. Made-up words."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import glance
from review import core

UP = {'count': 12, 'by_reason': {'parent': 10, 'drop_cap': 2}, 'forms': [{'form': 'Vélunkata', 'pages': [3, 9]}]}


def rec(state, unplaced=None, **kw):
    st = {'candidates': kw.pop('candidates', 5), 'state': state}
    if unplaced: st['unplaced'] = unplaced
    return {'language_status': st, **kw}


def test_the_count_goes_into_the_line_details_and_never_blocks_ready():
    r = rec('decided', UP, workorder={'language_parts': {'version': 2, 'forms': [{'form': 'velunka', 'tag': True, 'lang': 'haw'}], 'parts': []}},
            language_review={'reviewer': 'Kim', 'date': '2026-11-19T10:00:00', 'not_reviewed': 0, 'forms': 1})
    ok, text = glance.language_line(r)
    assert ok and text == 'Approved (Kim on November 19, 2026 · 12 words not tagged)'
    ok, text = glance.language_line(rec('off', UP))
    assert not ok and text == 'Not Done (the language step was turned off · 12 words not tagged)'


def test_not_applicable_says_what_was_found():
    ok, text = glance.language_line(rec('not_run', {'count': 1, 'forms': []}, candidates=0))
    assert ok and text == 'Not Applicable (no word forms to decide · 1 word not tagged)'


def test_no_count_no_change():
    assert glance.language_line(rec('off')) == glance._language_line(rec('off'))


def test_the_review_page_reads_the_audit_while_the_run_waits(tmp_path):
    (tmp_path / '_audit').mkdir()
    json.dump({'unplaced': [{'page': 3, 'form': 'Vélunkata', 'reason': 'drop_cap', 'mcids': [0, 1]},
                            {'page': 9, 'form': 'Vélunkata', 'reason': 'parent', 'mcids': [4, 5]}]}, open(tmp_path / '_audit' / 'lang_candidates.json', 'w'))
    assert core.unplaced_info(str(tmp_path)) == {'count': 2, 'forms': [['Vélunkata', [3, 9]]]}
    json.dump({'language_status': {'candidates': 4, 'state': 'decided', 'unplaced': UP}}, open(tmp_path / 'record.json', 'w'))
    assert core.unplaced_info(str(tmp_path)) == {'count': 12, 'forms': [['Vélunkata', [3, 9]]]}
    json.dump({'language_status': {'candidates': 4, 'state': 'decided'}}, open(tmp_path / 'record.json', 'w'))
    assert core.unplaced_info(str(tmp_path)) is None              # the report ran and found none: the audit isn't read again


def test_the_review_page_shows_a_read_only_fold():
    page = open(os.path.join(os.path.dirname(core.__file__), 'page.html'), encoding='utf-8').read()
    assert "Words Not Tagged (' + fmtN(u.count)" in page and 'langUnplaced(LANGS.unplaced)' in page and 'tag tree' not in page.split('function langUnplaced')[1].split('function renderLanguages')[0]
