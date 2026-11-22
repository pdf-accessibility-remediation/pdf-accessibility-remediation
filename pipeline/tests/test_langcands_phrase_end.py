"""L3 (review 22; proposal 23's L3 design; Patrick, 2026-11-21): a comma or semicolon ends a phrase of consecutive
candidates inside a run, and stops growth there too; a colon does not (a title and its subtitle, one language). Inside
quotes a comma doesn't count, except on the closing word itself (review 24 §7.3). Synthetic pages (tests/langpdf: F6
oblique, F1 roman; `mixed` draws one run in several fonts)."""
import os, sys
import pikepdf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import langpdf  # noqa: E402
from lib import plumb_fix, plpages, langcands, langjoin  # noqa: F401,E402
from test_language_phrases import wo_of, apply_verify, spans  # noqa: E402
from test_langcands_adjacent import mixed  # noqa: E402


def I(t): return ('F6', t)
def R(t): return ('F1', t)


def found(tmp_path, lines, name='l.pdf'):
    src = langpdf.build_lines(str(tmp_path / name), lines)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    return c


def forms(tmp_path, lines, name='l.pdf'): return [p['form'] for p in found(tmp_path, lines, name)['places']]
def one(*parts): return [[mixed(list(parts))]]


COMMA = one(R('See '), I('Dainihon bukkyo zensho, yuhoden sosho'), R(' for these.'))


def test_a_comma_or_a_semicolon_between_candidates_ends_the_phrase(tmp_path):
    assert forms(tmp_path, COMMA) == ['Dainihon bukkyo zensho', 'yuhoden sosho']
    assert forms(tmp_path, one(R('See '), I('Shoku gosen; kokiroku'), R(' for these.')), 's.pdf') == ['Shoku gosen', 'kokiroku']


def test_a_colon_between_a_title_and_its_subtitle_does_not(tmp_path):
    assert forms(tmp_path, one(R('See '), I('Higashikuni nikki: Nihon gekidoki'), R(' for these.'))) == ['Higashikuni nikki Nihon gekidoki']


def test_an_english_title_with_a_comma_stops_growth_there(tmp_path):
    """"Winesburg, Ohio": growth took "Ohio" across the comma before; now "Ohio" is in no place."""
    assert forms(tmp_path, one(R('See '), I('Winesburg, Ohio'), R(' for these.'))) == ['Winesburg']


def test_a_comma_before_a_number_changes_nothing(tmp_path):
    assert forms(tmp_path, one(R('See '), I('Dainihon zensho dai'), R(' 1, 2 for these.'))) == ['Dainihon zensho dai']


def test_a_comma_on_the_closing_word_of_a_quote_still_ends_the_phrase(tmp_path):
    """Review 24 §7.3, test 5 with its opening quote: the closing word's own mark counts."""
    lines = one(R('In "'), I('Minamatabyo to Kanada," Genchi ni Miru'), R(' for these.'))
    assert forms(tmp_path, lines) == ['Minamatabyo to Kanada', 'Genchi ni Miru']


def test_a_comma_ending_the_run_is_run_ends_work_as_before(tmp_path):
    lines = [[mixed([R('See '), I('Shoku gosen,')])], [mixed([I('wakashu'), R(' for the poems.')])]]
    assert forms(tmp_path, lines) == ['Shoku gosen', 'wakashu']


def test_growth_backward_across_a_comma_stops(tmp_path):
    """"Nihon" joins only through growth, so with the comma it is in no place, like any English-list word alone."""
    assert forms(tmp_path, one(R('See the '), I('Nihon, kokiroku'), R(' for these.'))) == ['kokiroku']


def test_a_quoted_title_with_a_comma_inside_is_one_place(tmp_path):
    """Review 24 §7.3: the refinement acts in the phrase loop (these are consecutive candidates, no growth needed)."""
    assert forms(tmp_path, one(R('See "'), I('Hyakunin isshu, Sogi sho'), R('" for these.'))) == ['Hyakunin isshu Sogi sho']


def test_an_unclosed_straight_quote_is_no_span(tmp_path):
    assert forms(tmp_path, one(R('In "'), I('Velunka toramio, pasquet kiro'), R(' for these.'))) == ['Velunka toramio', 'pasquet kiro']


def test_the_sample_h_shape_splits_at_the_closing_word(tmp_path):
    """"Account of the City of Cairo," Nat. Mag.: the quote closes on the comma's own word, so the comma counts."""
    lines = one(R('"Account of the City of '), I('Velunka," Toramio Pasquet'), R(' for these.'))
    assert forms(tmp_path, lines) == ['Velunka', 'Toramio Pasquet']


def test_a_comma_before_a_slash_stops_growth_across_it(tmp_path):
    """Review 24 §7.1: at a slash, each word it crosses counts ("tamayura no, / tsuyu")."""
    got = forms(tmp_path, one(R('A line '), I('tamayura no, / tsuyu mo namida'), R(' here.')))
    assert got == ['tamayura', 'tsuyu mo namida'], got
    assert forms(tmp_path, one(R('A line '), I('tamayura no / tsuyu mo namida'), R(' here.')), 'b.pdf') == ['tamayura no tsuyu mo namida']


def test_the_chain_stops_at_a_comma_inside_a_line(tmp_path):
    lines = [[mixed([R('See '), I('Shoku')])], [mixed([I('gosen, kokin')])], [mixed([I('wakashu'), R(' here.')])]]
    c = found(tmp_path, lines)
    assert [(p['form'], p.get('segments')) for p in c['places']] == [('Shoku gosen', [[0, 4, 8], [1, 0, 4]]), ('kokin wakashu', [[1, 7, 11], [2, 0, 6]])]


def test_a_title_beside_a_passage_keeps_its_piece_with_a_comma_in_the_passage(tmp_path):
    lines = [[mixed([R('See the anthology '), I('Shoku gosen')])],
             [mixed([I('wakashu, tsuki hana yuki kaze nami sora')])], [mixed([R(' for the poems.')])]]
    c = found(tmp_path, lines)
    assert [(p['mcid'], p['form'], p['class'][0]) for p in c['places']] == [(0, 'Shoku gosen', 'unknown'), (1, 'wakashu tsuki hana yuki kaze nami sora', 'passage')]


def test_on_an_ocr_pattern_page_a_comma_inside_a_multi_word_run_ends_the_phrase(tmp_path):
    """The joined reading breaks a stretch at , ; : only where the run changes; a run of several words is the finder's."""
    line = [R('The '), R('words '), R('here '), R('are '), I('Velunka Toramio, Pasquet'), R(' and '), R('more '), R('words.')]
    src = langpdf.build_lines(str(tmp_path / 'o.pdf'), [[{'text': t, 'font': f} for f, t in line]])
    with pikepdf.open(src) as pdf:
        assert langjoin.reading(1, plpages.Pages(src).pages[0].chars, langjoin.Structure(pdf), {'join', 'inrun', 'cross'}).kind == 'ocr'
        c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True, pdf=pdf)
    assert [p['form'] for p in c['places']] == ['Velunka Toramio', 'Pasquet']


def test_apply_and_verify_tag_the_two_phrases_apart(tmp_path):
    c = found(tmp_path, COMMA)
    a, b = c['places']
    wo = wo_of([(x['form'], 'ja-Latn', [[1, x['mcid'], x['first'], x['last']]]) for x in (a, b)])
    _, out, log, v = apply_verify(tmp_path, COMMA, wo, name='av.pdf')
    sp = spans(out)
    assert len(sp) == 2 and all(x[0] == 'ja-Latn' for x in sp), sp
    assert not log['language_parts']['refused'] and not log.get('failed'), log['language_parts']
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['index']['dangling'] == 0 and not (v.get('fonts') or {}).get('unreadable')


def test_a_period_ends_a_phrase_between_two_non_english_sentences(tmp_path):
    """Review 26 §11, variant P (Patrick, 2026-11-21): translation's "muwilyaba mämawurriya. Muwilyaba …"."""
    got = forms(tmp_path, one(R('Then '), I('muwilyaba mamawurriya. Muwilyaba nemederrenda'), R(' here.')))
    assert got == ['muwilyaba mamawurriya', 'Muwilyaba nemederrenda'], got


def test_a_short_core_before_a_period_does_not_end_a_phrase():
    """A number, one or two letters, or initials of one or two letters each: "1.", "K.", "St.", "pp.", "D.T." (and
    "n.a."); no list of abbreviations, so "vols." and "Mohd." end a phrase, as measured."""
    assert not any(langcands.period_end(t) for t in ('1.', '1940.', 'K.', 'St.', 'pp.', 'D.T.', 'n.a.', '(Ka.)'))
    assert all(langcands.period_end(t) for t in ('wakashu.', 'vols.', 'Mohd.', 'kokin.”', 'gosen.)'))


def test_a_two_letter_core_inside_a_phrase_keeps_it_whole_and_a_longer_one_ends_it(tmp_path):
    assert forms(tmp_path, one(R('See '), I('Velunka Qx. Toramio'), R(' for these.'))) == ['Velunka Qx Toramio']
    assert forms(tmp_path, one(R('See '), I('Velunka Qxz. Toramio'), R(' for these.')), 'b.pdf') == ['Velunka Qxz', 'Toramio']


def test_a_quoted_title_ending_in_a_period_ends_the_phrase_on_its_closing_word(tmp_path):
    assert forms(tmp_path, one(R('In "'), I('Velunka toramio." Pasquet kiro'), R(' here.'))) == ['Velunka toramio', 'Pasquet kiro']
    assert forms(tmp_path, one(R('See "'), I('Hyakunin isshu. Sogi sho'), R('" here.')), 'q.pdf') == ['Hyakunin isshu Sogi sho']


def test_a_two_language_pair_splits_at_its_period(tmp_path):
    """buddhist PDF 175's shape: a Sanskrit title, then a French one."""
    got = forms(tmp_path, one(R('See '), I('Vijnaptimatratasiddhi. La Siddhi Hiuan-Tsang'), R(' here.')))
    assert got[0] == 'Vijnaptimatratasiddhi' and not any('Vijnaptimatratasiddhi' in f and 'Siddhi ' in f for f in got), got
