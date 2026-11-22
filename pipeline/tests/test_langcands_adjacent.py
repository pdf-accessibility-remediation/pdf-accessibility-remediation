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


def mixed(parts):
    """One run drawing several fonts: parts [(font, text)] (F6 oblique, F1 roman)."""
    body = []
    for f, t in parts: body += [f'/{f} 11 Tf', langpdf.show(f, t)]
    return {'text': ''.join(t for _, t in parts), 'body': body}


PARTIAL = [[mixed([('F1', 'See the anthology '), ('F6', 'Shoku gosen')])], [mixed([('F6', 'wakashu'), ('F1', ' for the poems.')])]]


def test_a_title_starting_and_ending_mid_run_is_tagged_once_and_verify_matches(tmp_path):
    """Review 22, probe 1: one run per line, the title starting mid-line and ending mid-line on the next."""
    src = langpdf.build_lines(str(tmp_path / 'p.pdf'), PARTIAL)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    (p,) = c['places']
    assert p['form'] == 'Shoku gosen wakashu' and p['segments'] == [[0, 18, 28], [1, 0, 6]]
    _, out, log, v = apply_verify(tmp_path, PARTIAL, wo_of([(p['form'], 'ja-Latn', [[1, p['segments']]])]), name='q.pdf')
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'ja-Latn' and sorted(sp[0][1]) == [1, 2], sp
    assert not log['language_parts']['refused'] and not log.get('failed'), log['language_parts']
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['index']['dangling'] == 0 and not (v.get('fonts') or {}).get('unreadable')


def with_and_without_adjacency(tmp_path, monkeypatch, lines):
    from lib import langjoin
    on = full(tmp_path, lines, 'on.pdf')
    monkeypatch.setattr(langjoin.Structure, 'adjacent', lambda self, *a: False)
    return on, full(tmp_path, lines, 'off.pdf')


def full(tmp_path, lines, name):
    src = langpdf.build_lines(str(tmp_path / name), lines)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    return [(p['mcid'], p['form'], p['class'][0], p.get('segments')) for p in c['places']]


def test_a_title_grown_into_a_passages_run_keeps_its_piece_before_it(tmp_path, monkeypatch):
    """Review 22, M1 (probe 2): the next run is a passage. The passage holds its words; "Shoku gosen" stays a place of
    its own, as with growth stopping at the run boundary (before, the grown place was dropped whole)."""
    lines = [[mixed([('F1', 'See the anthology '), ('F6', 'Shoku gosen')])],
             [mixed([('F6', 'wakashu tsuki hana yuki kaze nami sora')])], [mixed([('F1', ' for the poems.')])]]
    on, off = with_and_without_adjacency(tmp_path, monkeypatch, lines)
    assert on == off == [(0, 'Shoku gosen', 'unknown', None), (1, 'wakashu tsuki hana yuki kaze nami sora', 'passage', None)]


def test_a_title_grown_out_of_a_passages_run_keeps_its_piece_after_it(tmp_path, monkeypatch):
    """Review 22, M1 (probe 3): the first run is the passage, "wakashu" opens the next run and stays a place."""
    lines = [[mixed([('F6', 'tsuki hana yuki kaze nami sora Shoku gosen')])], [mixed([('F6', 'wakashu'), ('F1', ' for the poems.')])]]
    on, off = with_and_without_adjacency(tmp_path, monkeypatch, lines)
    assert on == off == [(0, 'tsuki hana yuki kaze nami sora Shoku gosen', 'passage', None), (1, 'wakashu', 'unknown', None)]


THREE = [[mixed([('F1', 'See '), ('F6', 'Shoku')])], [mixed([('F6', 'gosen')])], [mixed([('F6', 'wakashu'), ('F1', ' here.')])]]


def test_a_title_over_three_lines_seeded_in_the_first_is_one_place(tmp_path):
    """Proposal 23 §3 (review 22's probe 4, review 24's probe C): with the italics rule on, the seed is "Shoku" in line 1;
    adjacency is asked of the run of the word before, so growth chains through all three lines. One Span, verify matching."""
    src = langpdf.build_lines(str(tmp_path / 'c.pdf'), THREE)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    (p,) = c['places']
    assert p['form'] == 'Shoku gosen wakashu' and p['segments'] == [[0, 4, 8], [1, 0, 4], [2, 0, 6]]
    _, out, log, v = apply_verify(tmp_path, THREE, wo_of([(p['form'], 'ja-Latn', [[1, p['segments']]])]), name='c2.pdf')
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'ja-Latn' and sorted(sp[0][1]) == [1, 2, 3], sp
    assert not log['language_parts']['refused'] and not log.get('failed'), log['language_parts']
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['index']['dangling'] == 0 and not (v.get('fonts') or {}).get('unreadable')


def test_an_english_word_in_the_middle_line_still_stops_the_chain(tmp_path):
    """Review 24's probe D: growth's word test stops at "house"; the chain adds no reach past it."""
    lines = [[mixed([('F1', 'See '), ('F6', 'Shoku')])], [mixed([('F6', 'house')])], [mixed([('F6', 'wakashu'), ('F1', ' here.')])]]
    assert [x[1] for x in places(tmp_path, lines, 'd.pdf')] == ['Shoku', 'wakashu']


def test_a_run_that_comes_back_after_another_gives_one_place_per_stretch(tmp_path):
    """Review 24 §5: interleaved MCIDs (the third line's run numbered as the first's). One place can't hold a run twice,
    so each stretch of one run is a place of its own; before, the later characters fell out of `segments`."""
    src = langpdf.build_lines(str(tmp_path / 'i.pdf'), THREE)
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        pg = pdf.pages[0]
        pg.obj.Contents = pdf.make_stream(pg.obj.Contents.read_bytes().replace(b'/MCID 2', b'/MCID 0'))
        el = pdf.Root.StructTreeRoot.K[0].K[0]
        el.K = pikepdf.Array([0, 1])
        pdf.Root.StructTreeRoot.ParentTree.Nums[1] = pdf.make_indirect(pikepdf.Array([el, el]))
        pdf.save(src)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    got = [(p['mcid'], p['first'], p['last'], p['form'], p.get('segments')) for p in c['places']]
    assert got == [(0, 4, 8, 'Shoku', None), (0, 9, 15, 'wakashu', None), (1, 0, 4, 'gosen', None)], got
