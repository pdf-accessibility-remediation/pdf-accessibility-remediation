"""test_lang_exp.py: round 15's test tools (#118, language tagging; review 14, item 1): the masked-clue keys
(tools/lang_test.py reading_of, beside, masked) and the experiment's statistics (tools/lang_exp.py). Synthetic words only.

    python -m pytest tests/test_lang_exp.py -q
"""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tools'))
import lang_test as T  # noqa: E402
import lang_exp as X  # noqa: E402

def test_a_reading_proves_one_language_or_none():
    assert T.reading_of('(fujō', 'japan') == 'ja' and T.reading_of('かな', None) == 'ja' and T.reading_of('소주', None) == 'ko'
    assert T.reading_of('(jicao', 'china') == 'zh' and T.reading_of('Zhongguo', 'japan') == 'zh'     # a Chinese title in a book on Japan
    assert T.reading_of('soba-manjū', 'china') == 'ja' and T.reading_of('rekishōhen', 'china') == 'ja'   # macrons that also fit pinyin
    assert T.reading_of('dōu', 'china', toned=True) is None                                            # a book with tone marks: not settled
    assert T.reading_of('Chosŏn', 'korea') == 'ko' and T.reading_of('tzŭ', 'china') is None          # breves: Korean only in a book on Korea
    assert T.reading_of('the', 'china') is None and T.reading_of('Li', 'china') is None              # English, or too short

def test_only_a_reading_directly_beside_counts():
    pw = ['soju', '소주', 'su', '酥', 'next']                     # a glossary: the hangul belongs to soju, not to 酥
    assert T.beside(pw, 3, 3, 'china') == {}
    pw = ['monks', '(hansō', '半僧', ').']
    assert T.beside(pw, 2, 2, 'japan') == {1: 'ja'}
    pw = ['樂林', 'yung', '勇']                                    # a romanization after the characters is the next entry's
    assert T.beside(pw, 0, 0, 'china') == {}

def test_masking_removes_the_reading_and_keeps_the_place():
    cand = {'words': {'1': ['the', 'fan', '(fujō', '不浄', ').', 'More', 'text']},
            'places': [{'page': 1, 'mcid': 0, 'first': 0, 'last': 1, 'text': '不浄', 'form': '不浄', 'class': ['cjk:han_only'], 'w0': 3, 'w1': 3}]}
    got, hard, sh = T.masked('b', cand, 'japan')
    assert len(got) == 1 and got[0]['key'] == 'ja' and got[0]['reading'] == ['(fujō']
    assert got[0]['masked_words'] == ['the', 'fan', '不浄', ').', 'More', 'text'] and (got[0]['p']['w0'], got[0]['p']['w1']) == (2, 2)
    assert hard == [] and sh == {'han_only_places': 1, 'reading_within_3': 1, 'reading_within_15': 1}

def test_mcnemar_is_exact_and_two_sided():
    assert X.binom_two_sided(0, 0) == 1.0 and X.binom_two_sided(5, 5) == 1.0
    assert round(X.binom_two_sided(0, 6), 4) == 0.0312 and X.binom_two_sided(1, 4) > 0.05

def test_outcomes_follow_the_tagging_rule():
    assert X.outcome({'lang': 'ja', 'confidence': 'high', 'why': 'language'}, ['ja']) == 'right'
    assert X.outcome({'lang': 'zh', 'confidence': 'medium', 'why': 'language'}, ['ja']) == 'wrong'
    assert X.outcome({'lang': 'ja', 'confidence': 'medium', 'why': 'language'}, ['ja-Latn']) == 'wrong'    # the script differs
    assert X.outcome({'lang': 'zh', 'confidence': 'low', 'why': 'language'}, ['ja']) == 'untagged'          # low: never tagged
    assert X.outcome(None, ['ja']) == 'cut off'
