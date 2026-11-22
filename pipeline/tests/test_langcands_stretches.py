"""H1 (a) (proposal 23 §4, review 24 §6; Patrick, 2026-11-21): title growth goes on across the stretches of a joined
reading, as on a page read as its runs. On an OCR-pattern page only a line break qualifies; on a publisher page read
joined, any run change between stretches does, with Structure.adjacent, the clean break and a word break there (a new
line, or a space). A grown place maps to the PDF's runs segment by segment (Reading.map); one that can't map is one
place per stretch. Synthetic pages (tests/langpdf.build_lines: each piece its own run; F6 oblique, F1 roman)."""
import os, sys
import pikepdf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import langpdf  # noqa: E402
from lib import plumb_fix, plpages, langcands, langjoin  # noqa: F401,E402
from test_language_phrases import wo_of, apply_verify, spans  # noqa: E402
import test_langcands_adjacent as ADJ  # noqa: E402


def I(t, **k): return dict(text=t, font='F6', **k)
def R(t, **k): return dict(text=t, **k)


def book(tmp_path, lines, name='s.pdf'):
    src = langpdf.build_lines(str(tmp_path / name), lines)
    with pikepdf.open(src) as pdf:
        st = langjoin.Structure(pdf); PL = plpages.Pages(src)
        kinds = []
        for pno, pg in enumerate(PL.pages, 1):
            r = langjoin.reading(pno, pg.chars, st, {'join', 'inrun', 'cross'}); kinds.append(r.kind if r else 'runs')
        c = langcands.book(PL, doc_lang='en', grow=True, pdf=pdf)
    return c, kinds


def got(c): return [(p['form'], p.get('segments')) for p in c['places']]


# an OCR-pattern page: one run a word, a four-word title over two lines in one P
OCR = [[R('See '), R('the '), R('old '), I('Shoku '), I('gosen')], [I('wakashu '), I('kokin '), R('for '), R('the '), R('poems.')]]


def test_an_ocr_page_title_over_a_line_break_is_one_place_and_one_span(tmp_path):
    c, kinds = book(tmp_path, OCR)
    assert kinds == ['ocr']
    (p,) = c['places']
    assert p['form'] == 'Shoku gosen wakashu kokin' and [s[0] for s in p['segments']] == [3, 4, 5, 6], p
    assert {'grow', 'join'} <= set(p['source'])
    _, out, log, v = apply_verify(tmp_path, OCR, wo_of([(p['form'], 'ja-Latn', [[1, p['segments']]])]), name='o2.pdf')
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'ja-Latn' and sorted(sp[0][1]) == [3, 4, 5, 6], sp
    assert not log['language_parts']['refused'] and not log.get('failed'), log['language_parts']
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['index']['dangling'] == 0 and not (v.get('fonts') or {}).get('unreadable')


def test_a_comma_ending_the_line_stops_growth_by_run_ends_test(tmp_path):
    """The line break qualifies, but growth's own clean-break test (RUN_END on "gosen,") stops it."""
    lines = [OCR[0][:4] + [I('gosen,')], OCR[1]]
    c, _ = book(tmp_path, lines)
    assert [f for f, _ in got(c)] == ['Shoku gosen', 'wakashu kokin']


def test_the_next_line_under_another_element_is_not_entered(tmp_path):
    lines = [OCR[0], [dict(x, parent='P1') for x in OCR[1]]]
    c, _ = book(tmp_path, lines)
    assert [f for f, _ in got(c)] == ['Shoku gosen', 'wakashu kokin']


DROP = [[dict(text='V', size=30, parent='PD'), dict(text='elunkata is a made up word and there are more of them.', parent='PD')]]


def test_on_a_publisher_page_read_joined_the_adjacent_run_cases_hold(tmp_path):
    """Review 24 §6.1: a drop cap elsewhere makes the page a joined reading ('other'); the adjacent-run cases give the same
    places as on a page read as its runs, a same-line title in three runs included (transnational's "Nihon Rettō |
    Kaizō | Ron")."""
    cases = {
        'broken': ADJ.BROKEN,
        'another element': [[ADJ.R('See the anthology '), ADJ.I('Shoku gosen')], [ADJ.I('wakashu', parent='P1'), ADJ.R(' for the poems.', parent='P1')]],
        'not next': [[ADJ.R('See the anthology '), ADJ.I('Shoku gosen'), ADJ.R(' and ')], [ADJ.I('wakashu'), ADJ.R(' for the poems.')]],
        'english': [[ADJ.R('See the anthology '), ADJ.I('Shoku gosen')], [ADJ.I('house'), ADJ.R(' for the poems.')]],
        'comma': [[ADJ.R('See the anthologies '), ADJ.I('Shoku gosen,')], [ADJ.I('wakashu'), ADJ.R(' for the poems.')]],
        'bracket': [[ADJ.R('See the anthologies '), ADJ.I('Shoku gosen')], [ADJ.I('(wakashu)'), ADJ.R(' for the poems.')]],
        'same line': [[ADJ.R('See the book called '), ADJ.I('Nihon Retto'), ADJ.I(' Kaizo'), ADJ.I(' Ron'), ADJ.R(' which is a long one.')],
                      [ADJ.R('There are many more English words on this second line of the text.')]],
    }
    for k, lines in cases.items():
        plain, kp = book(tmp_path, lines, k.replace(' ', '_') + '.pdf')
        joined, kj = book(tmp_path, lines + DROP, k.replace(' ', '_') + '_d.pdf')
        assert kp == ['runs'] and kj == ['other'], (k, kp, kj)
        a = [f for f, _ in got(plain)]; b = [f for f, _ in got(joined) if 'lunkata' not in f]
        assert a == b, (k, a, b)
    assert [f for f, _ in got(book(tmp_path, cases['same line'] + DROP, 'sl.pdf')[0]) if 'lunkata' not in f] == ['Nihon Retto Kaizo Ron']


def test_a_title_over_three_lines_on_a_joined_page_seeded_in_the_first_is_one_place(tmp_path):
    lines = [[R('See '), R('the '), I('Shoku')], [I('gosen')], [I('wakashu '), R('for '), R('the '), R('poems.')]]
    c, kinds = book(tmp_path, lines)
    assert kinds == ['ocr'] and got(c) == [('Shoku gosen wakashu', [[2, 0, 4], [3, 0, 4], [4, 0, 6]])], got(c)


def test_four_one_word_lines_are_one_place(tmp_path):
    """Review 24's probe E: every run one word, the page an OCR pattern."""
    lines = [[R('See '), I('Shoku')], [I('gosen')], [I('wakashu')], [I('kokin')], [R('for '), R('the '), R('poems.')]]
    c, kinds = book(tmp_path, lines)
    assert kinds == ['ocr'] and [f for f, _ in got(c)] == ['Shoku gosen wakashu kokin']


def test_reading_map_joins_stretch_segments_and_refuses_a_run_twice(tmp_path):
    src = langpdf.build_lines(str(tmp_path / 'm.pdf'), OCR)
    with pikepdf.open(src) as pdf:
        r = langjoin.reading(1, plpages.Pages(src).pages[0].chars, langjoin.Structure(pdf), {'join', 'inrun', 'cross'})
    ss = sorted(r.runs)
    a, b = ss[0], ss[1]                                   # line 1's stretch and line 2's
    la, lb = len(r.runs[a]) - 1, len(r.runs[b]) - 1
    q = r.map({'page': 1, 'mcid': a, 'first': 0, 'last': la, 'segments': [[a, 0, la], [b, 0, lb]], 'form': 'x', 'class': ['title']})
    assert q is not None and [s[0] for s in q['segments']] == list(range(10)) and q['text'].replace(' ', '') == 'SeetheoldShokugosenwakashukokinforthepoems.'
    assert r.map({'page': 1, 'mcid': a, 'first': 0, 'last': la, 'segments': [[a, 0, la], [a, 0, la]], 'form': 'x', 'class': []}) is None
    assert r.can_map([[a, 0, la], [b, 0, lb]]) and not r.can_map([[a, 0, la], [a, 0, la]])


def test_a_grown_place_that_cannot_map_is_one_place_per_stretch(tmp_path):
    """Review 24, L4: when the joined reading can't map a grown place, its candidates stay, one place per stretch."""
    src = langpdf.build_lines(str(tmp_path / 'f.pdf'), ADJ.BROKEN)
    with pikepdf.open(src) as pdf: st = langjoin.Structure(pdf)
    chars = plpages.Pages(src).pages[0].chars
    adj = lambda a, b: st.adjacent(1, a, b)
    whole, _ = langcands.page_places(1, chars, lambda p: chars, doc_lang='en', grow=True, adjacent=adj, extra={'italic'})
    cut, _ = langcands.page_places(1, chars, lambda p: chars, doc_lang='en', grow=True, adjacent=adj, extra={'italic'}, can_map=lambda segs: False)
    assert [p['form'] for p in whole] == ['Shoku gosen wakashu'] and [(p['mcid'], p['form']) for p in cut] == [(1, 'Shoku gosen'), (2, 'wakashu')]


def test_a_title_grown_into_a_passage_stretch_keeps_its_piece_on_a_joined_page(tmp_path):
    lines = [[ADJ.mixed([('F1', 'See the anthology '), ('F6', 'Shoku gosen')])],
             [ADJ.mixed([('F6', 'wakashu tsuki hana yuki kaze nami sora')])], [ADJ.mixed([('F1', ' for the poems.')])]] + DROP
    c, kinds = book(tmp_path, lines)
    assert kinds == ['other']
    assert [(p['form'], p['class'][0]) for p in c['places'] if 'lunkata' not in p['form']] == [('Shoku gosen', 'unknown'), ('wakashu tsuki hana yuki kaze nami sora', 'passage')]


def test_a_romanized_title_and_its_english_translation_on_the_next_line_stay_apart(tmp_path):
    lines = [[R('See '), R('the '), I('Shoku '), I('gosen')], [I('Later '), I('Collection '), R('for '), R('the '), R('poems.')]]
    c, kinds = book(tmp_path, lines)
    assert kinds == ['ocr'] and [f for f, _ in got(c)] == ['Shoku gosen']


def test_a_line_end_hyphen_on_an_ocr_page_takes_the_half_once(tmp_path):
    """Review 24 §6.2: "Zhong-" ‖ "guo shi". Growth crosses the line into the hyphen half: one place over both halves, the
    hyphen itself outside it, and the half in no other place. The joined reading ends a stretch after the first word of a
    line that follows a line-end hyphen ('hyphen half', not 'line'), so "shi" stays a place of its own."""
    lines = [[R('See '), R('the '), I('Zhong-')], [I('guo '), I('shi '), R('for '), R('the '), R('story.')]]
    c, kinds = book(tmp_path, lines)
    assert kinds == ['ocr']
    assert got(c) == [('Zhongguo', [[2, 0, 4], [3, 0, 2]]), ('shi', None)], got(c)
