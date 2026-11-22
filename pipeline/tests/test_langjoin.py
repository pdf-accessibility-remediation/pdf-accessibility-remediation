"""The finder's joined reading (#150, #161; lib/langjoin, lib/langcands.book): made-up words on tiny tagged PDFs."""
import pikepdf
from lib import plpages, langcands, langjoin, gaptext
import langpdf


def find(tmp_path, lines, rules=None, with_pdf=True, name='j.pdf', at_parent=None):
    src = langpdf.build_lines(str(tmp_path / name), lines, at_parent=at_parent)
    with pikepdf.open(src) as pdf:
        return langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf if with_pdf else None, rules=rules)


def forms(c): return sorted(p['form'] for p in c['places'])
def place(c, form): return next(p for p in c['places'] if p['form'] == form)


OCR = [{'text': 'The '}, {'text': 'velunka '}, {'text': 'toramio '}, {'text': 'pasquet '}, {'text': 'here.'}]


def test_a_phrase_across_runs_on_an_ocr_page_is_one_place_with_segments(tmp_path):
    c = find(tmp_path, [OCR])
    p = place(c, 'velunka toramio pasquet')
    assert p['segments'] == [[1, 0, 7], [2, 0, 7], [3, 0, 6]] and p['mcid'] == 1 and p['first'] == 0
    assert p['source'] == ['join'] and p['text'].split() == ['velunka', 'toramio', 'pasquet']
    assert c['reading'] == {'rules': ['cross', 'inrun', 'italic', 'join'], 'asked': ['cross', 'inrun', 'italic', 'join'], 'parents': 'ok'} and c['version'] == 2
    today = find(tmp_path, [OCR], rules=set(), name='t.pdf')
    assert forms(today) == ['pasquet', 'toramio', 'velunka'] and not any(p.get('segments') for p in today['places'])


def test_without_the_pdf_no_run_is_joined(tmp_path):
    c = find(tmp_path, [OCR], with_pdf=False)
    assert forms(c) == ['pasquet', 'toramio', 'velunka'] and c['reading']['parents'] == 'not given'
    assert 'join' not in c['reading']['rules'] and 'inrun' in c['reading']['rules']


def test_a_parent_change_a_comma_and_a_column_gap_end_a_stretch(tmp_path):
    par = [dict(x) for x in OCR]; par[2]['parent'] = 'P1'
    assert 'velunka toramio pasquet' not in forms(find(tmp_path, [par], name='a.pdf'))
    com = [dict(x) for x in OCR]; com[1]['text'] = 'velunka, '
    assert forms(find(tmp_path, [com], name='b.pdf')) == ['toramio pasquet', 'velunka']
    gap = [dict(x) for x in OCR]; gap[2]['gap'] = 3000
    assert forms(find(tmp_path, [gap], name='c.pdf')) == ['toramio pasquet', 'velunka']


def test_a_note_mark_in_its_own_run_stays_apart(tmp_path):
    line = [{'text': 'The '}, {'text': 'velunka'}, {'text': '4', 'size': 6, 'rise': 5}, {'text': ' toramio '}, {'text': 'here.'}]
    c = find(tmp_path, [line])
    assert not any('4' in f for f in forms(c)) and 'velunka' in forms(c)


def test_a_word_drawn_across_runs_with_a_one_letter_piece_is_one_word(tmp_path):
    line = [{'text': 'The '}, {'text': 'velunk'}, {'text': 'a '}, {'text': 'here.'}]
    p = place(find(tmp_path, [line]), 'velunka')
    assert p['segments'] == [[1, 0, 5], [2, 0, 0]] and p['text'] == 'velunka'
    assert 'velunka' not in forms(find(tmp_path, [line], rules=set(), name='t.pdf'))     # today: no place at all


def test_rule_1_breaks_a_word_whose_pieces_are_words_of_their_own(tmp_path):
    c = find(tmp_path, [[{'text': 'The '}, {'text': 'velun'}, {'text': 'toram '}, {'text': 'here.'}]])
    assert forms(c) == ['velun toram']                         # two words, one phrase; never "veluntoram"


def test_the_in_run_one_letter_join_on_a_page_of_long_runs(tmp_path):
    body = ['[(These words are all made up: v) -120 (elunkata is one of them here.)] TJ']
    c = find(tmp_path, [[{'text': '', 'body': body}]])
    p = place(c, 'velunkata')
    assert 'segments' not in p and p['source'] == ['inrun'] and p['text'] == 'v elunkata'.replace(' ', '') or p['text'].replace(' ', '') == 'velunkata'
    today = find(tmp_path, [[{'text': '', 'body': body}]], rules=set(), name='t.pdf')
    assert 'velunkata' not in forms(today) and 'elunkata' in forms(today)
    off = find(tmp_path, [[{'text': '', 'body': body}]], rules={'join', 'cross'}, name='o.pdf')
    assert 'velunkata' not in forms(off)


LONG = [{'text': 'These words are all made up: velunk'}, {'text': 'a'}, {'text': ' and more words come here today.'}]


def test_a_last_letter_in_its_own_run_is_placed_across_the_two_runs(tmp_path):
    c = find(tmp_path, [LONG])
    p = place(c, 'velunka')
    assert p['segments'] == [[0, 29, 34], [1, 0, 0]] and p['source'] == ['cross'] and c['unplaced'] == []
    assert 'velunka' not in forms(find(tmp_path, [LONG], rules=set(), name='t.pdf'))
    assert 'velunka' not in forms(find(tmp_path, [LONG], rules={'join', 'inrun'}, name='o.pdf'))


def test_a_word_across_two_parents_is_read_whole_and_counted_not_placed(tmp_path):
    line = [dict(x) for x in LONG]; line[1]['parent'] = 'P1'
    c = find(tmp_path, [line])
    assert 'velunka' not in forms(c) and 'velunk' not in forms(c)
    assert c['unplaced'] == [{'page': 1, 'form': 'velunka', 'reason': 'parent', 'mcids': [0, 1]}] and c['stats']['unplaced'] == 1


def test_spoken_text_in_the_way_is_counted_not_placed(tmp_path):
    line = [dict(x) for x in LONG]; line[1]['at'] = 'a'
    assert [u['reason'] for u in find(tmp_path, [line])['unplaced']] == ['actualtext']
    assert [u['reason'] for u in find(tmp_path, [LONG], name='p.pdf', at_parent={'P0': 'spoken'})['unplaced']] == ['actualtext']


def test_an_english_word_cut_at_its_last_letter_is_neither_placed_nor_counted(tmp_path):
    line = [{'text': 'These words are all made up: problem'}, {'text': 's'}, {'text': ' and more words come here today.'}]
    c = find(tmp_path, [line])
    assert c['unplaced'] == [] and not any(f.startswith('problem') for f in forms(c))


def test_a_sentence_end_before_the_run_change_is_a_word_break(tmp_path):
    line = [{'text': 'These words are all made up: velunka.'}, {'text': 'Toramiopa'}, {'text': ' and more words come here today.'}]
    c = find(tmp_path, [line])
    assert 'velunka' in forms(c) and not any('.' in f for f in forms(c))


def test_a_drop_cap_is_read_whole_and_never_placed(tmp_path):
    lines = [[{'text': 'V', 'size': 30, 'parent': 'P1'}, {'text': 'élunkata is a made up word and there are more of them.'}]]
    c = find(tmp_path, lines)
    assert not any('lunkata' in f for f in forms(c))
    assert [(u['form'], u['reason']) for u in c['unplaced']] == [('Vélunkata', 'drop_cap')]


def test_rules_from_the_environment():
    assert langcands.rules_from_env('')[0] == {'join', 'inrun', 'cross', 'italic'} and langcands.rules_from_env('')[1] == ''
    r, note = langcands.rules_from_env('-inrun,-cross')
    assert r == {'join', 'italic'} and note == 'LANG_FINDER_RULES=-inrun,-cross'
    assert langcands.rules_from_env('join,cross', grow=True)[0] == {'join', 'cross', 'grow'}


def test_the_reader_keeps_a_joined_letter_with_its_word():
    xs = [(0, 5), (7, 12), (12, 14), (14, 19), (19, 24)]
    cs = [{'text': t, 'x0': a, 'x1': b, 'top': 0, 'bottom': 10, 'size': 10, 'mcid': 0} for t, (a, b) in zip('velun', xs)]
    assert gaptext.breaks(cs)[1] == [False, True, False, False, False]
    cs[1]['_join'] = True
    assert gaptext.breaks(cs)[1] == [False] * 5


def test_structure_reports_an_unreadable_tree():
    pdf = pikepdf.new(); pdf.add_blank_page()
    assert langjoin.Structure(pdf).status == 'unreadable' and langjoin.Structure(None).status == 'not given'


# ---- #136's rules (measured; off unless named: Patrick decides after stage 3's text check)

TITLE = [{'text': 'The made up book ', 'font': 'F1'}, {'text': 'Dai Nihon kokiroku', 'font': 'F6'}, {'text': ' is cited here today.', 'font': 'F1'}]


def test_growth_reads_a_romanized_title_whole_and_no_common_word_joins_it(tmp_path):
    long_ = [[{'text': 'These are made up words from a book: ', 'font': 'F1'}, {'text': 'Dai Nihon kokiroku', 'font': 'F6'}, {'text': ' in China', 'font': 'F6'},
              {'text': ' and more words come here.', 'font': 'F1'}]]
    off = find(tmp_path, long_, name='o.pdf')
    assert forms(off) == ['Dai', 'kokiroku']          # "Dai" from the italics rule, on by default (2026-11-21)
    on = find(tmp_path, long_, rules={'join', 'inrun', 'cross', 'grow'}, name='g.pdf')
    p = place(on, 'Dai Nihon kokiroku')
    assert 'grow' in p['source'] and 'China' not in ' '.join(forms(on))


def test_the_looser_rule_takes_three_letters_and_capitals(tmp_path):
    line = [[{'text': 'These are made up words like Velk and kwo and vel here.'}]]
    assert forms(find(tmp_path, line, name='a.pdf')) == []
    got = find(tmp_path, line, rules={'join', 'inrun', 'cross', 'looser'}, name='b.pdf')
    assert forms(got) == ['Velk', 'kwo', 'vel'] and all(p['source'] == ['looser'] for p in got['places'])


ITALIC_LINE = [[{'text': 'The made up reading ', 'font': 'F1'}, {'text': 'ri', 'font': 'F6'}, {'text': ' and also ri and the ', 'font': 'F1'},
                {'text': 'house', 'font': 'F6'}, {'text': ' words are here today.', 'font': 'F1'}]]


def test_the_italics_rule_takes_short_italic_words_only(tmp_path):
    got = find(tmp_path, ITALIC_LINE, rules={'join', 'inrun', 'cross', 'italic'})
    assert [(p['form'], p['source']) for p in got['places']] == [('ri', ['italic'])]


def test_the_italics_rule_is_on_by_default(tmp_path, monkeypatch):
    """Patrick, 2026-11-21 (report 21 §4): the audit's rules (rules_from_env with nothing set) and book(rules=None)
    both take the italic word, and record the rule in `reading`."""
    monkeypatch.delenv('LANG_FINDER_RULES', raising=False)
    rules, note = langcands.rules_from_env()
    assert 'italic' in rules and note == ''
    for got in (find(tmp_path, ITALIC_LINE, rules=rules, name='a.pdf'), find(tmp_path, ITALIC_LINE, name='b.pdf')):
        assert [(p['form'], p['source']) for p in got['places']] == [('ri', ['italic'])]
        assert 'italic' in got['reading']['rules'] and 'italic' in got['reading']['asked']


def test_the_italics_rule_turned_off_for_a_measurement(tmp_path, monkeypatch):
    """LANG_FINDER_RULES=-italic (measurement only) turns it off; the joins stay on and the note says so."""
    monkeypatch.setenv('LANG_FINDER_RULES', '-italic')
    rules, note = langcands.rules_from_env()
    assert rules == {'join', 'inrun', 'cross'} and note == 'LANG_FINDER_RULES=-italic'
    got = find(tmp_path, ITALIC_LINE, rules=rules)
    assert got['places'] == [] and 'italic' not in got['reading']['rules']


def test_growth_grows_across_a_joined_stretch_and_stops_at_a_parent_change(tmp_path):
    ocr = [{'text': 'The '}, {'text': 'Dai ', 'font': 'F6'}, {'text': 'Nihon ', 'font': 'F6'}, {'text': 'kokiroku ', 'font': 'F6'}, {'text': 'here.'}]
    rules = {'join', 'inrun', 'cross', 'grow'}
    p = place(find(tmp_path, [ocr], rules=rules, name='a.pdf'), 'Dai Nihon kokiroku')
    assert len(p['segments']) == 3 and set(p['source']) >= {'grow', 'join'}
    apart = [dict(x) for x in ocr]; apart[3]['parent'] = 'P1'
    got = forms(find(tmp_path, [apart], rules=rules, name='b.pdf'))
    assert 'Dai Nihon kokiroku' not in got and 'kokiroku' in got     # L1: growth never crosses a stretch's break


def test_the_continuation_rule_reads_a_hyphenated_word_whose_second_part_is_drawn_later(tmp_path):
    first = [[{'text': 'These are made up words like tamo-'}], [{'text': 'and here more words go on today.'}]]
    src = langpdf.build_lines(str(tmp_path / 'probe.pdf'), first)
    hy = [c for c in plpages.Pages(src).pages[0].chars if c['text'] == '-'][0]
    lines = first + [[{'text': 'lirra', 'xy': (hy['x1'] + 0.5, 792 - hy['bottom'] + 2.1)}]]
    lines[0][0]['text'] = 'These are made up words like tamo-'
    off = find(tmp_path, lines, name='o.pdf')
    on = find(tmp_path, lines, rules={'join', 'inrun', 'cross', 'continuation'}, name='c.pdf')
    assert 'tamo-lirra' not in forms(off) and 'tamo-lirra' in forms(on), (forms(off), forms(on))
    eng = [[{'text': 'These are made up words like para-'}], [{'text': 'and here more words go on today.'}]]
    src2 = langpdf.build_lines(str(tmp_path / 'probe2.pdf'), eng)
    hy2 = [c for c in plpages.Pages(src2).pages[0].chars if c['text'] == '-'][0]
    eng.append([{'text': 'military', 'xy': (hy2['x1'] + 0.5, 792 - hy2['bottom'] + 2.1)}])
    assert not any('para' in f for f in forms(find(tmp_path, eng, rules={'join', 'inrun', 'cross', 'continuation'}, name='e.pdf')))


def test_growth_never_joins_an_english_function_word_or_a_piece_of_an_english_word(tmp_path):
    line = [[{'text': 'These are made up words from a book: ', 'font': 'F1'}, {'text': 'velunkatari of toramio', 'font': 'F6'},
             {'text': ' and more words come here.', 'font': 'F1'}]]
    got = forms(find(tmp_path, line, rules={'join', 'inrun', 'cross', 'grow'}))
    assert got == ['toramio', 'velunkatari']
    line2 = [[{'text': 'These are made up words from a book: ', 'font': 'F1'}, {'text': 'kotoba Se lections', 'font': 'F6'},
              {'text': ' and more words come here.', 'font': 'F1'}]]
    assert not any(' ' in f for f in forms(find(tmp_path, line2, rules={'join', 'inrun', 'cross', 'grow'}, name='b.pdf')))   # never "kotoba Se lections"


def test_a_letter_is_not_joined_to_a_piece_of_an_english_word_drawn_in_pieces(tmp_path):
    """#161 part A: "geo graph i cal" drawn with a space glyph over the next letter: the single "i" is a piece of
    "geographical", so it is not joined to "cal" ("ical" would be a junk word form)."""
    body = ['[(These words are drawn in pieces like geo) ( ) 278 (graph) ( ) 278 (i) ( ) 278 (cal here and more words go on.)] TJ']
    got = forms(find(tmp_path, [[{'text': '', 'body': body}]]))
    assert 'ical' not in got and not any('cal' in f for f in got), got


def test_an_initial_and_its_period_are_never_joined_to_the_next_word(tmp_path):
    """review 06 M2: a tightly set "L. velunkata" or "v. toramio" (a space drawn over the next letter) read as one letter and
    the next word; the period or comma after the letter is a word end, so "L.velunkata" is never made. A letter with no
    period is still joined."""
    body = ['[(These names are all made up: L.) ( ) 278 (velunkata and v.) ( ) 278 (toramio, C.,) ( ) 278 (pasquet here.)] TJ']
    got = forms(find(tmp_path, [[{'text': '', 'body': body}]]))
    assert not any('.' in f[:-1] or ',' in f[:-1] for f in got), got
    assert {'velunkata', 'toramio', 'pasquet'} <= set(got), got
    still = ['[(These words are all made up: v) ( ) 278 (elunkata is one of them here.)] TJ']
    assert 'velunkata' in forms(find(tmp_path, [[{'text': '', 'body': still}]], name='s.pdf'))
