"""Title growth across " / " (#136, report 16 §5, review 17 §5): a spaced slash between romanized pieces of a verse line
is transparent to growth, so the line is one place with the slashes inside; growth still stops at English, at a run's
end and at anything that isn't a lone slash. Synthetic pages only (tests/langpdf.py): F6 is an oblique (italic) font,
F1 roman."""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import langpdf  # noqa: E402
from lib import plumb_fix, plpages, langcands  # noqa: F401,E402
from test_language_parts import apply_verify, part  # noqa: E402


def body(*pieces): return [f'/{f} 11 Tf ' + langpdf.show(f, t) for f, t in pieces]


def grown(tmp_path, runs, name='s.pdf'):
    src = langpdf.build(str(tmp_path / name), [{'body': b} if isinstance(b, list) else b for b in runs])
    c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True)
    return src, [(p['mcid'], p['form'], p['text']) for p in c['places']], c['words']['1']


def test_a_verse_line_grows_whole_across_its_slashes(tmp_path):
    """1 (and report 16's first): the line in one italic run, inside English: one place, the slashes inside its text."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'In the poem '), ('F6', 'tamayura no / tsuyu mo namida mo / todomarazu'),
                                     ('F1', ', she wept for the house.'))])
    assert ps == [(0, 'tamayura no tsuyu mo namida mo todomarazu', 'tamayura no / tsuyu mo namida mo / todomarazu')]


def test_a_slash_before_english_stops_growth(tmp_path):
    """2 (and report 16's second): "tsuyu mo namida / dew and tears": the English beyond the slash never joins."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'The line '), ('F6', 'tsuyu mo namida / dew and tears'), ('F1', ' is short.'))])
    assert ps == [(0, 'tsuyu mo namida', 'tsuyu mo namida')]


def test_a_particle_before_a_slash_and_an_english_word_stays_out(tmp_path):
    """3 (and report 16's third): "tamayura no / way": the particle looks past the slash, finds English, stays out."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'The line '), ('F6', 'tamayura no / way'), ('F1', ' is short.'))])
    assert ps == [(0, 'tamayura', 'tamayura')]


def test_an_unspaced_slash_a_date_or_a_url_changes_nothing(tmp_path):
    """4: "Kamakura/Muromachi", "and/or", "1/2", "http://": no lone slash, so the rule never applies."""
    _, ps, words = grown(tmp_path, [body(('F1', 'The Kamakura/Muromachi and/or 1/2 of http://x.org/a era of '), ('F6', 'tamayura'),
                                         ('F1', ' here.'))])
    assert '/' not in [w.strip() for w in words]
    assert ps == [(0, 'tamayura', 'tamayura')]


def test_a_slash_at_a_runs_end_stops_at_the_run(tmp_path):
    """5: the verse goes on in the next run: growth stays in each run, as before; the particle before the slash stays out."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'The line '), ('F6', 'tamayura no /')), body(('F6', 'tsuyu mo namida'), ('F1', ' ends the poem.'))])
    assert ps == [(0, 'tamayura', 'tamayura'), (1, 'tsuyu mo namida', 'tsuyu mo namida')]


def test_a_double_slash_or_nothing_romanized_beyond_joins_nothing(tmp_path):
    """6: "//" isn't a lone slash; a slash with a number beyond it joins nothing."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'The line '), ('F6', 'tamayura no // tsuyu mo namida'), ('F1', ' and '),
                                     ('F6', 'kokoro no / 12'), ('F1', ' end.'))])
    assert ps == [(0, 'tamayura', 'tamayura'), (0, 'tsuyu mo namida', 'tsuyu mo namida'), (0, 'kokoro', 'kokoro')]


def test_a_roman_slash_joins_italic_words_and_a_roman_word_beyond_stops_it(tmp_path):
    """7 (rule 3; report 16's fourth): the slash set in roman between italic pieces joins them; "kokoro" in roman after the
    next slash doesn't join the italic title, and the title doesn't end on that slash."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'The line '), ('F6', 'tamayura no'), ('F1', ' / '), ('F6', 'tsuyu mo namida'),
                                     ('F1', ' / kokoro and the rest.'))])
    assert ps == [(0, 'tamayura no tsuyu mo namida', 'tamayura no / tsuyu mo namida'), (0, 'kokoro', 'kokoro')]


def test_a_hawaiian_line_crosses_a_slash_only_into_words_off_the_english_list(tmp_path):
    """8, as decided after the measurement (report 18: no Hawaiian book changed): growth crosses the slash only when the
    word beyond isn't on the English list. "i ka leo o ka pule" are English-list spellings, so the line stops at the slash
    and the English after it never joins; "maliu mai" beyond the slash joins."""
    _, ps, _ = grown(tmp_path, [body(('F1', 'The chant '), ('F6', 'E maliu mai oe / i ka leo o ka pule'), ('F1', ' was sung at dawn by the family.'))])
    assert ps == [(0, 'E maliu mai oe', 'E maliu mai oe')]
    _, ps, _ = grown(tmp_path, [body(('F1', 'The chant '), ('F6', 'E maliu mai oe / maliu mai'), ('F1', ' was sung at dawn by the family.'))], 't.pdf')
    assert ps == [(0, 'E maliu mai oe maliu mai', 'E maliu mai oe / maliu mai')]


def test_apply_tags_the_grown_line_with_its_slashes_and_verify_matches(tmp_path):
    """9: the grown place goes through apply.py and verify.py: one Span over the line, slashes inside, verify matching
    every tag, the five checks clean."""
    runs = [{'body': body(('F1', 'In the poem '), ('F6', 'tamayura no / tsuyu mo namida mo / todomarazu'), ('F1', ', she wept.'))}]
    src = langpdf.build(str(tmp_path / 'g.pdf'), runs)
    c = langcands.book(plpages.Pages(src), doc_lang='en', grow=True)
    (p,) = c['places']
    _, out, log, v = apply_verify(tmp_path, runs, [part(1, p['mcid'], p['first'], p['last'], 'ja-Latn')])
    lp = log['language_parts']
    assert lp['split'] == 1 and not lp['refused'], lp
    assert [s['text'] for s in lp['spans']] == ['tamayura no / tsuyu mo namida mo / todomarazu']
    assert v['language']['all_match'] and v['language']['spans_written'] == 1
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0
    assert not (v.get('fonts') or {}).get('unreadable')
