"""Title growth into the adjacent run of the same element (proposal 20 (b); Patrick, 2026-11-21): a title broken at a line
end, each line its own run, is one place with two segments, so the voice switches once. Growth enters the next run only
when the runs share their element and sit next to each other among its kids, under growth's own word test, at a clean
break. Synthetic pages (tests/langpdf.build_lines: each piece its own run; F6 oblique, F1 roman)."""
import os, sys
import pikepdf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import langpdf  # noqa: E402
from lib import plumb_fix, plpages, langcands  # noqa: F401,E402
from test_language_phrases import wo_of, apply_verify, spans  # noqa: E402


def I(t, **k): return dict(text=t, font='F6', **k)          # italic
def R(t, **k): return dict(text=t, **k)                     # roman


def places(tmp_path, lines, name='s.pdf'):
    src = langpdf.build_lines(str(tmp_path / name), lines)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    return [(p['mcid'], p['form'], p.get('segments')) for p in c['places']]


BROKEN = [[R('See the anthology '), I('Shoku gosen')], [I('wakashu'), R(' for the poems.')]]


def test_a_title_broken_at_a_line_end_is_one_place_with_two_segments(tmp_path):
    assert places(tmp_path, BROKEN) == [(1, 'Shoku gosen wakashu', [[1, 0, 10], [2, 0, 6]])]


def test_the_next_run_in_another_element_is_not_entered(tmp_path):
    lines = [[R('See the anthology '), I('Shoku gosen')], [I('wakashu', parent='P1'), R(' for the poems.', parent='P1')]]
    assert places(tmp_path, lines) == [(1, 'Shoku gosen', None), (2, 'wakashu', None)]


def test_a_run_that_is_not_next_among_the_elements_kids_is_not_entered(tmp_path):
    lines = [[R('See the anthology '), I('Shoku gosen'), R(' and ')], [I('wakashu'), R(' for the poems.')]]
    assert places(tmp_path, lines) == [(1, 'Shoku gosen', None), (3, 'wakashu', None)]


def test_an_english_word_starting_the_next_run_stops_growth(tmp_path):
    lines = [[R('See the anthology '), I('Shoku gosen')], [I('house'), R(' for the poems.')]]
    assert places(tmp_path, lines) == [(1, 'Shoku gosen', None)]


def test_two_titles_one_after_the_other_stay_two(tmp_path):
    """The break must be clean: a comma (or any phrase end) closing the first run, or a bracket or quote opening the
    next, keeps two titles in adjacent runs apart."""
    comma = [[R('See the anthologies '), I('Shoku gosen,')], [I('wakashu'), R(' for the poems.')]]
    assert places(tmp_path, comma) == [(1, 'Shoku gosen', None), (2, 'wakashu', None)]
    bracket = [[R('See the anthologies '), I('Shoku gosen')], [I('(wakashu)'), R(' for the poems.')]]
    assert places(tmp_path, bracket, 'b.pdf') == [(1, 'Shoku gosen', None), (2, 'wakashu', None)]


def test_apply_tags_the_joined_title_once_and_verify_matches(tmp_path):
    src = langpdf.build_lines(str(tmp_path / 'g.pdf'), BROKEN)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    (p,) = c['places']
    _, out, log, v = apply_verify(tmp_path, BROKEN, wo_of([('Shoku gosen wakashu', 'ja-Latn', [[1, p['segments']]])]))
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'ja-Latn' and sorted(sp[0][1]) == [1, 2], sp
    assert not log['language_parts']['refused'], log['language_parts']
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['index']['dangling'] == 0 and not (v.get('fonts') or {}).get('unreadable')
