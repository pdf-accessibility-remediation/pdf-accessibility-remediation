"""test_workorder_check.py: the checks every work order goes through, one test per reason an item is dropped.

    python -m pytest tests/test_workorder_check.py -q

The expected results follow docs/work-order.md and docs/ocr-words.md, not the code's current output.
"""
import pytest
from lib import workorder_check as wc

def digest():
    """A minimal digest: 10 pages, one text element, two figures (obj 2 a single run), two styles, two OCR word forms,
    one table and one list the one-item rule flattens."""
    return {'source': {'pages': 10},
            'elements': [{'obj': 1}], 'figures': [{'obj': 2, 'single_run': True}, {'obj': 3}], 'headings': [],
            'styles': [{'style': 'Body'}, {'style': 'Heading 1'}],
            'ocr_words': [{'id': 1, 'text': 'Maiiana', 'count': 3}, {'id': 2, 'text': 'Kaimuki', 'count': 1},
                          {'id': 3, 'text': 'xxxxxefghijkl', 'count': 1}, {'id': 4, 'text': 'xxxxefghijkl', 'count': 1}],
            'tables': [{'obj': 20}, {'obj': 21}], 'lists': [{'obj': 30, 'flattened_by_rule': True}, {'obj': 31}]}

def check(wo, not_sent=(), words_sent=(1, 3, 4)):
    return wc.check(wo, digest(), set(not_sent), set(words_sent))

def whys(dropped, where=None): return [d['why'] for d in dropped if where is None or d['where'] == where]

# distance: OCR junk is cheap, diacritics are free, a different letter costs 1
def test_distance_junk_is_a_quarter():
    assert wc.distance('ii', 'ñ') == 0.5                   # ñ read as "ii": change one i, drop the other
    assert wc.distance('l;l', 'ṇ') == 0.75

def test_distance_ignores_diacritics():
    assert wc.distance('n', 'ṇ') == 0 and wc.distance('Hawaii', 'Hawaiʻi'.replace('ʻ', '')) == 0

def test_distance_real_letter_costs_one():
    assert wc.distance('cat', 'bat') == 1 and wc.distance('cat', 'cats') == 1

# ocr_words readings
def readings(wo): return {it['id']: it['reads'] for it in wo.get('ocr_words', [])}

def test_ocr_word_kept_as_executor_list():
    wo = {'ocr_words': {'1': 'Mañana'}}
    assert check(wo) == []
    assert wo['ocr_words'] == [{'id': 1, 'text': 'Maiiana', 'reads': 'Mañana', 'count': 3}]

@pytest.mark.parametrize('item, why', [
    ({'id': 99, 'reads': 'x'}, 'unknown id'),
    ({'id': 'abc', 'reads': 'x'}, 'unknown id'),
    ({'id': 2, 'reads': 'Kaimukī'}, 'its word sheet was not sent'),
    ({'id': 1, 'reads': '  '}, 'empty'),
    ({'id': 1, 'reads': 'Ma ñana'}, 'not one word'),
    ({'id': 1, 'reads': 'M' * 81}, 'not one word'),
    ({'id': 1, 'reads': 'Maiiana'}, 'same as the OCR text'),
    ({'id': 1, 'reads': 'Tomorrow'}, 'too different from the OCR text to be a misreading of it'),
])
def test_ocr_word_dropped(item, why):
    wo = {'ocr_words': [item]}
    assert whys(check(wo)) == [why] and 'ocr_words' not in wo

def test_ocr_word_one_third_limit():
    """A 12-letter reading may differ in up to 0.34 x 12 = 4.08 letters: 4 real changes pass, 5 do not."""
    wo = {'ocr_words': {'4': 'abcdefghijkl', '3': 'abcdefghijkl'}}
    dropped = check(wo)
    assert readings(wo) == {4: 'abcdefghijkl'}
    assert [(d['item']['id'], d['why']) for d in dropped] == [('3', 'too different from the OCR text to be a misreading of it')]

def test_ocr_word_short_reading_may_differ_by_two():
    wo = {'ocr_words': {'1': 'Mañanu'}}                    # 0.5 for the junk + 1 for the last letter: under the floor of 2
    assert check(wo) == [] and readings(wo) == {1: 'Mañanu'}

# the other drops
def test_unknown_key_dropped_pipeline_keys_kept():
    wo = {'schema': 'workorder/0.1', 'bogus': 1, 'decided_by': 'model', 'reviewed_by': 'person'}
    assert whys(check(wo)) == ['unknown key']
    assert set(wo) == {'schema', 'decided_by', 'reviewed_by'}

def test_unknown_obj_dropped():
    wo = {'actual_text': [{'obj': 1, 'text': 'x'}, {'obj': 99, 'text': 'y'}], 'retype': [{'obj': 1, 'type': 'H2'}, {'obj': 1, 'type': 'Table'}]}
    dropped = check(wo)
    assert whys(dropped, 'actual_text') == ['unknown obj'] and wo['actual_text'] == [{'obj': 1, 'text': 'x'}]
    assert whys(dropped, 'retype') == ['type not allowed'] and wo['retype'] == [{'obj': 1, 'type': 'H2'}]

def test_alt():
    wo = {'alt': [{'obj': 2, 'alt': 'A wave'}, {'obj': 3, 'alt': 'Unseen'}, {'obj': 1, 'alt': 'Text'}, {'obj': 2, 'alt': ' '}]}
    dropped = check(wo, not_sent=[3])
    assert wo['alt'] == [{'obj': 2, 'alt': 'A wave'}]
    assert whys(dropped) == ['not a figure or empty alt', 'not a figure or empty alt',
                             'its image was not sent (over --max-images), so the alt was written unseen']

def test_rolemap():
    wo = {'rolemap': {'Body': 'P', 'Heading 1': 'Figure', 'Nope': 'P'}}
    assert sorted(whys(check(wo))) == ['target not allowed', 'unknown style']
    assert wo['rolemap'] == {'Body': 'P'}

def test_artifact_rules():
    wo = {'artifacts': {'elements': [{'obj': 2}, {'obj': 3}, {'obj': 99}],
                        'text_rules': [{'regex': '^Preface$', 'pages': [1, 10], 'band': 'top'}, {'regex': '(', 'pages': [1, 2]},
                                       {'regex': 'x', 'pages': [1, 11]}, {'regex': 'x', 'pages': [1, 2], 'band': 'middle'}]}}
    dropped = check(wo)
    assert wo['artifacts']['elements'] == [{'obj': 2}]
    assert whys(dropped, 'artifacts.elements') == ['not a single-run figure listed in the digest', 'unknown obj']
    assert len(wo['artifacts']['text_rules']) == 1
    assert whys(dropped, 'artifacts.text_rules') == ['bad regex', 'bad page range', 'band must be top, bottom or any']

def test_tables():
    wo = {'flatten': [{'obj': 21}],
          'tables': [{'obj': 20, 'header_rows': 1}, {'obj': 20, 'header_rows': 1}, {'obj': 21, 'header_rows': 1},
                     {'obj': 20, 'header_rows': 4}, {'obj': 20, 'header_rows': True}, {'obj': 20, 'header_rows': 0},
                     {'obj': 99, 'header_rows': 1}]}
    dropped = check(wo)
    assert wo['tables'] == [{'obj': 20, 'header_rows': 1}]
    assert whys(dropped, 'tables') == ['also flattened', 'header_rows and header_cols must be whole numbers 0-3',
                                       'header_rows and header_cols must be whole numbers 0-3', 'no header rows or columns',
                                       'not a table listed in the digest', 'the same table twice']

def test_keep_lists():
    wo = {'keep_lists': [{'obj': 30}, {'obj': 31}]}
    assert whys(check(wo)) == ['not a list the one-item rule would flatten'] and wo['keep_lists'] == [{'obj': 30}]

def test_language_tidied_or_dropped():
    wo = {'document': {'lang': 'en_US'}}
    assert check(wo) == [] and wo['document']['lang'] == 'en-US'
    wo = {'document': {'lang': 'english', 'title': 'T'}}
    assert whys(check(wo)) == ['not a BCP 47 language tag'] and wo['document'] == {'title': 'T'}

def test_deferral_pages():
    wo = {'deferrals': [{'what': 'a', 'pages': [2, 0, 11]}, {'what': 'b', 'pages': 'x'}]}
    assert whys(check(wo)) == ['not PDF page numbers in range'] * 2
    assert wo['deferrals'] == [{'what': 'a', 'pages': [2]}, {'what': 'b'}]
