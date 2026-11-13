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
    assert set(dec) == {'1', '2'} and 'not valid JSON' in dropped[0]['why'] and dropped[-1] == {'id': '3', 'why': 'not answered'}
