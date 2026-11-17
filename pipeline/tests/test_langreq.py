"""test_langreq.py: the language step's requests and replies (lib/langreq.py; #118, language tagging). No network.

    python -m pytest tests/test_langreq.py -q
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import langreq, models  # noqa: E402

def place(page, mcid, first, last, text, cls, w0, italic=False):
    return {'page': page, 'mcid': mcid, 'first': first, 'last': last, 'text': text, 'form': text, 'class': cls, 'italic': italic,
            'w0': w0, 'w1': w0 + len(text.split()) - 1}

WORDS = {'1': 'The term mappō and the name 源信 appear here in the text , and mappō again'.split(),
         '2': 'Nothing here but ゆめ in kana .'.split()}
PLACES = [place(1, 0, 9, 13, 'mappō', ['marks'], 2), place(1, 0, 30, 31, '源信', ['cjk:han_only'], 6), place(1, 1, 0, 4, 'mappō', ['marks'], 13),
          place(2, 0, 17, 18, 'ゆめ', ['cjk:kana'], 3)]

def test_forms_group_and_skip_kana():
    fs = langreq.forms(PLACES)
    assert [(f['form'], f['group'], len(f['places'])) for f in fs] == [('源信', 'cjk', 1), ('mappō', 'marks', 2)]

def test_each_snippet_once_with_every_candidate_marked():
    fs = langreq.forms(PLACES)
    [r] = langreq.requests({'title': 'T', 'language': 'en'}, fs, WORDS)
    assert len(r['snippets']) == 1                         # the two windows on page 1 meet: one snippet
    s = r['snippets'][0]['text']
    assert s.count('[[') == 3 and '[[1|源信]]' in s and s.count('|mappō]]') == 2
    assert [i['id'] for i in r['items']] == ['1', '2'] and r['items'][1]['places'] == 2

def test_body_temperature_as_decide_sends_it():
    r = {'book': {}, 'snippets': [], 'items': []}
    assert langreq.body(r, 'anthropic/claude-sonnet-5.5', 'p', 100)['temperature'] == 0          # model list not known
    assert 'temperature' not in langreq.body(r, 'anthropic/claude-sonnet-5.5', 'p', 100, ['max_tokens', 'response_format'])
    b = langreq.body(r, 'anthropic/claude-opus-5.5', 'p', 100, ['temperature', 'response_format'])
    assert 'temperature' not in b and models.temperature_omitted('anthropic/claude-opus-5.5') == 'anthropic/claude-opus-5'
    assert b['provider'] == {'data_collection': 'deny'} and b['response_format'] == {'type': 'json_object'}
    assert 'response_format' not in langreq.body(r, 'x/y', 'p', 100)

def test_parse_and_parts():
    fs = langreq.forms(PLACES)
    reply = json.dumps({'decisions': [{'id': '1', 'lang': 'ja', 'confidence': 'high', 'why': 'language'},
                                      {'id': '2', 'lang': 'ja-Latn', 'confidence': 'medium', 'why': 'language'},
                                      {'id': '3', 'lang': 'ja', 'confidence': 'high', 'why': 'language'},
                                      {'id': '2', 'lang': 'jp', 'confidence': 'high', 'why': 'language'}]})
    dec, dropped = langreq.parse('Here it is: ' + reply, {'1', '2'})
    assert set(dec) == {'1', '2'} and {d['why'] for d in dropped} == {'unknown id', 'answered twice'}
    parts = langreq.to_parts(fs, dec)['parts']
    assert sorted((p['page'], p['mcid'], p['lang']) for p in parts) == [(1, 0, 'ja'), (1, 0, 'ja-Latn'), (1, 1, 'ja-Latn')]
    dec2, dropped2 = langreq.parse(json.dumps({'decisions': [{'id': '1', 'lang': 'jp', 'confidence': 'high', 'why': 'language'},
                                                             {'id': '2', 'lang': None, 'confidence': 'low', 'why': 'unsure'}]}), {'1', '2'})
    assert set(dec2) == {'2'} and "tag not allowed: 'jp'" in dropped2[0]['why']
    assert langreq.to_parts(fs, dec2)['parts'] == []        # low and null are never tagged
    assert langreq.parse('no json', {'1'})[1][0]['why'] == 'reply is not a decisions object'

def test_parse_salvages_decisions_from_broken_json():
    """Sonnet 5.5 sent a stray brace or a cut string in 5 of 18 replies (#118 test, round 1): each decision object that
    is valid on its own is kept, and the reply is counted as not valid JSON."""
    t = ('{"decisions":[{"id":"1","lang":"haw","confidence":"high","why":"language","evidence":"okina"}},'
         '{"id":"2","lang":"ja","confidence":"medium","why":"language"},{"id":"3","lang":"zh","conf')
    dec, dropped = langreq.parse(t, {'1', '2', '3'})
    assert set(dec) == {'1', '2'} and 'not valid JSON' in dropped[0]['why'] and dropped[-1] == {'id': '3', 'code': 'not_answered', 'why': 'not answered'}
    assert dropped[0]['code'] == 'partial' and langreq.no_answer(['3'], dropped) == {'3': 'invalid'}     # #137: the reply's form

def test_one_character_han_places_on_a_line_form_one_word():
    ps = [place(5, i, 0, 0, ch, ['cjk:han_only'], 10 + i) for i, ch in enumerate('日本考古')] + [place(5, 9, 0, 0, '年', ['cjk:han_only'], 30)]
    fs = langreq.forms(ps, group=True)
    assert [(f['form'], len(f['places'])) for f in fs] == [('日本考古', 4), ('年', 1)]
    assert [f['form'] for f in langreq.forms(ps)] == ['日', '本', '考', '古', '年']

def test_a_form_echo_that_does_not_match_drops_the_decision():
    """review 06, L1: an id off by one would put a decision on another form; the echo catches it."""
    t = json.dumps({'decisions': [{'id': '1', 'form': 'mappō', 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'},
                                  {'id': '2', 'form': 'mappō', 'lang': 'ja', 'confidence': 'high', 'why': 'language'},
                                  {'id': '3', 'form': ' ONRYŌ ', 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}]})
    dec, dropped = langreq.parse(t, {'1', '2', '3'}, forms={'1': 'mappō', '2': '源信', '3': 'onryō'})
    assert set(dec) == {'1', '3'} and dropped[0] == {'id': '2', 'code': 'echo', 'why': 'its form does not match the item',
                                                     'echo': 'mappō', 'lang': 'ja', 'confidence': 'high'}     # #137: the answer is kept

# ---- #137 (dropped language answers): the echo's rule U (review 02, H1)
def _answer(i, form, lang='ja-Latn'):
    return {'id': i, 'form': form, 'lang': lang, 'confidence': 'high', 'why': 'language'}

def _parse_req(req, answers):
    forms = {it['id']: it['form'] for it in req['items']}
    return langreq.parse(json.dumps({'decisions': answers}), set(forms), forms=forms, marks=langreq.marks_of(req))

def _req(items, snippets):
    return {'items': [{'id': i, 'form': f} for i, f in items], 'snippets': [{'s': n + 1, 'text': t} for n, t in enumerate(snippets)]}

def test_an_echo_of_the_printed_spelling_is_kept():
    """The request carries a form cleaned in its item and as printed in its mark; an answer that copies the printed
    spelling (punctuation, a possessive "s", a line's half of a broken word) is kept."""
    req = _req([('1', 'Tenpyō hōji ninen Naishōsen'), ('2', 'Onjōji Tōin'), ('3', 'qianyan guanshiyin')],
               ['in [[1|Tenpyō hōji ninen: Naishōsen]] and [[2|Onjōji’s Tōin]] and the sutra [[3|qianyan guanshi]] yin here'])
    dec, dropped = _parse_req(req, [_answer('1', 'Tenpyō hōji ninen: Naishōsen'), _answer('2', 'Onjōji’s Tōin'), _answer('3', 'qianyan guanshi', 'zh-Latn')])
    assert set(dec) == {'1', '2', '3'} and not dropped

def test_an_answer_for_another_word_is_still_dropped():
    """Neighbouring ids swapped: each echo names the other item's form."""
    req = _req([('1', 'mappō'), ('2', 'onryō')], ['[[1|mappō]] and [[2|onryō]]'])
    dec, dropped = _parse_req(req, [_answer('1', 'onryō'), _answer('2', 'mappō')])
    assert dec == {} and [d['id'] for d in dropped] == ['1', '2']

def test_two_items_that_differ_only_by_an_okina_are_never_swapped():
    """review 02, H1: maika‘i and maikai are two items; their loose keys are the same, so a swapped echo is not taken."""
    req = _req([('1', 'maika‘i'), ('2', 'maikai')], ['[[1|maika‘i]] and [[2|maikai]]'])
    dec, dropped = _parse_req(req, [_answer('1', 'maikai', 'haw'), _answer('2', 'maika‘i', 'haw')])
    assert dec == {} and len(dropped) == 2
    dec, _ = _parse_req(req, [_answer('1', 'maika‘i', 'haw'), _answer('2', 'maikai', 'haw')])
    assert set(dec) == {'1', '2'}                                     # each its own: kept, as before

def test_a_first_half_mark_that_is_another_items_form_is_not_taken():
    """review 02, H1: a broken word's first-half mark ("corpse") is another item's whole form, so "corpse" fits neither."""
    req = _req([('1', 'corpseworm'), ('2', 'corpse')], ['the [[1|corpse]] worm and a [[2|corpse]] here'])
    dec, dropped = _parse_req(req, [_answer('1', 'corpse', None), _answer('2', 'corpseworm', None)])
    assert dec == {} and len(dropped) == 2

def test_a_grouped_han_forms_one_character_mark_is_not_taken():
    """review 02, H1: with LANG_GROUP, 賀川光夫 is marked character by character, and 光 is an item of its own."""
    req = _req([('1', '賀川光夫'), ('2', '光')], ['[[1|賀]][[1|川]][[1|光]][[1|夫]] and [[2|光]]'])
    dec, dropped = _parse_req(req, [_answer('1', '光', 'ja'), _answer('2', '賀川光夫', 'ja')])
    assert dec == {} and len(dropped) == 2

def test_marks_of_reads_the_request_as_sent():
    req = _req([('1', 'a'), ('2', 'b')], ['[[1|Kōdan]] sha and [[2|b c]]', 'again [[1|Kōdansha]]'])
    assert langreq.marks_of(req) == {'1': ['Kōdan', 'Kōdansha'], '2': ['b c']}

# ---- review 14, item 1: the context is configurable (unit, size, sentence mode, CJK cap, joining, item snippet numbers)
PW = ['First', 'sentence', 'here.', 'The', 'monk', '(52),', 'wrote', 'X', 'in', 'Kyoto.', 'Then', 'he', 'left', 'for', 'Nara.', 'End', 'piece.']

def test_words_count_letters_and_cjk_while_numbers_ride_along():
    from lib import langreq as L
    assert L.span(PW, 7, 7, {'unit': 'pieces', 'size': 2}) == (5, 9)
    assert L.span(PW, 7, 7, {'unit': 'words', 'size': 2}) == (4, 9)          # "(52)," rides along, "monk" counts
    assert L.span(PW, 7, 7, {'unit': 'words', 'size': 1}) == (6, 8)

def test_sentence_mode_takes_one_sentence_each_side_capped():
    from lib import langreq as L
    assert L.span(PW, 7, 7, {'mode': 'sentence', 'unit': 'words', 'cap': 60}) == (0, 14)    # sentence before, own, after
    assert L.span(PW, 7, 7, {'mode': 'sentence', 'unit': 'words', 'cap': 2}) == (4, 9)      # capped at 2 words a side
    pw = ['See', 'p.', '4', 'and', 'Dr.', 'Li', 'on', 'X', 'here.']
    assert L.span(pw, 7, 7, {'mode': 'sentence', 'unit': 'words', 'cap': 60}) == (0, 8)     # "p." and "Dr." end no sentence

def test_the_cjk_cap_keeps_the_characters_nearest_the_place():
    from lib import langreq as L
    pw = ['甲' * 50, 'X', '乙' * 50, 'end']
    t = L.place_text({'page': 1, 'w0': 1, 'w1': 1}, {'1': pw}, {'cjk_cap': 10})
    assert t == '…' + '甲' * 10 + ' [X] ' + '乙' * 10 + '… end'
    assert L.place_text({'page': 1, 'w0': 1, 'w1': 1}, {'1': pw}, {'cjk_cap': None}) == ' '.join(['甲' * 50, '[X]', '乙' * 50, 'end'])   # no cap: whole
    assert L.place_text({'page': 1, 'w0': 1, 'w1': 1}, {'1': pw}) == '…' + '甲' * 40 + ' [X] ' + '乙' * 40 + '… end'          # the adopted 40

def test_joining_and_item_snippet_numbers():
    from lib import langreq as L
    words = {'1': ['a'] * 10 + ['X'] + ['b'] * 3 + ['Y'] + ['c'] * 10}
    fs = [{'id': '1', 'form': 'X', 'class': ['latin'], 'italic_any': False, 'roman_any': True, 'places': [{'page': 1, 'mcid': 0, 'first': 0, 'last': 0, 'text': 'X', 'w0': 10, 'w1': 10}]},
          {'id': '2', 'form': 'Y', 'class': ['latin'], 'italic_any': False, 'roman_any': True, 'places': [{'page': 1, 'mcid': 0, 'first': 0, 'last': 0, 'text': 'Y', 'w0': 14, 'w1': 14}]}]
    one = L.requests({'title': 't'}, fs, words, ctx={'size': 5, 'item_snippets': False})[0]
    two = L.requests({'title': 't'}, fs, words, ctx={'size': 5, 'join': False, 'item_snippets': True})[0]
    assert len(one['snippets']) == 1 and 's' not in one['items'][0]
    assert len(two['snippets']) == 2 and [it['s'] for it in two['items']] == [[1, 2], [1, 2]]   # each window holds both marks

def test_the_adopted_context_is_the_default():
    """Patrick's decision on handoff 17 §3: 10 words, the 40-character CJK cap, joined snippets with item numbers."""
    from lib import langreq as L
    assert L.CTX == {'unit': 'words', 'size': 10, 'mode': 'window', 'cap': 60, 'cjk_cap': 40, 'join': True, 'item_snippets': True}

def test_a_cjk_piece_between_two_marks_keeps_the_side_nearer_its_nearer_mark():
    """review 16, L1: a 60-character piece between two marks, nearer the second, keeps its end (next to the second mark);
    one nearer the first keeps its start."""
    from lib import langreq as L
    long = '甲' * 30 + '乙' * 30
    pw = ['X', 'a', 'b', long, 'Y']                                     # nearer Y (1 piece away) than X (3 away)
    marks = [(0, 0, '1', 'X'), (4, 4, '2', 'Y')]
    t, _ = L._text(pw, 0, 4, marks, 40)
    assert t == '[[1|X]] a b …' + '甲' * 10 + '乙' * 30 + ' [[2|Y]]'
    pw = ['X', long, 'a', 'b', 'Y']                                     # nearer X
    t, _ = L._text(pw, 0, 4, [(0, 0, '1', 'X'), (4, 4, '2', 'Y')], 40)
    assert t == '[[1|X]] ' + '甲' * 30 + '乙' * 10 + '… a b [[2|Y]]'

def test_the_page_sentence_is_the_sent_text():
    """review 19, L1: the review page's context sentence comes from the built snippet, so a long CJK piece nearer another
    mark is cut on the same side as in the request (it used to be cut toward the place on the page only)."""
    from lib import langreq as L
    long = '甲' * 30 + '乙' * 30
    words = {'1': ['X', 'a', 'b', long, 'Y', 'c']}
    fs = [{'id': '1', 'form': 'X', 'class': ['latin'], 'italic_any': False, 'roman_any': True, 'places': [{'page': 1, 'mcid': 0, 'first': 0, 'last': 0, 'text': 'X', 'w0': 0, 'w1': 0}]},
          {'id': '2', 'form': 'Y', 'class': ['latin'], 'italic_any': False, 'roman_any': True, 'places': [{'page': 1, 'mcid': 0, 'first': 0, 'last': 0, 'text': 'Y', 'w0': 4, 'w1': 4}]}]
    reqs = L.requests({'title': 't'}, fs, words)
    sent = reqs[0]['snippets'][0]['text']
    assert sent == '[[1|X]] a b …' + '甲' * 10 + '乙' * 30 + ' [[2|Y]] c'                        # cut toward Y, the nearer mark
    page = L.sent_contexts(reqs)
    assert page['1'] == '[X] a b …' + '甲' * 10 + '乙' * 30 + ' Y c'                              # the same cut on the page
    assert page['2'] == 'X a b …' + '甲' * 10 + '乙' * 30 + ' [Y] c'
    assert L.place_text(fs[0]['places'][0], words) != page['1']                                   # the old way cut it the other side

def test_dropped_answers_carry_a_code_and_each_form_a_reason():
    """#137: every dropped entry has a code; each id with no decision gets one NO_ANSWER reason."""
    t = json.dumps({'decisions': [_answer('1', 'mappō', 'tpx'), _answer('2', 'onryō', None) | {'confidence': 'sure'},
                                  _answer('9', 'x'), _answer('3', 'kami'), _answer('3', 'kami')]})
    dec, dropped = langreq.parse(t, {'1', '2', '3', '4'}, forms={'1': 'mappō', '2': 'onryō', '3': 'kami', '4': 'shinkō'})
    assert set(dec) == {'3'}
    assert {d['code'] for d in dropped} == {'tag', 'invalid', 'unknown_id', 'twice', 'not_answered'} <= set(langreq.DROP_CODES)
    assert langreq.no_answer(['1', '2', '4'], dropped) == {'1': 'tag', '2': 'invalid', '4': 'not_answered'}
    assert langreq.no_answer(['4'], dropped, finish='length') == {'4': 'cut_off'}
    rows = langreq.to_rows([{'id': i, 'form': f, 'group': 'marks', 'class': ['marks'], 'places': []} for i, f in (('1', 'mappō'), ('3', 'kami'), ('4', 'shinkō'))],
                           dec, reasons={'1': 'tag', '3': 'echo', '4': 'nonsense'})
    assert [f.get('no_answer') for f in rows['forms']] == ['tag', None, None]     # a decided form, and a value not in the set, get none
