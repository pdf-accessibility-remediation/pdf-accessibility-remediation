"""test_scripts.py: which CJK script a run is in, and what language tag it gets (lib/scripts.py).

    python -m pytest tests/test_scripts.py -q

The expected results follow WCAG 3.1.2: a run needs a tag only when its language differs from the document's.
"""
import pytest
from lib import scripts

@pytest.mark.parametrize('text, kind', [
    ('The Lotus Sutra', None),
    ('한국어 문장을 읽습니다.', 'hangul'),
    ('서울 대학교 (首爾)', 'hangul'),                 # Korean with hanja is Korean
    ('ひらがなとカタカナ', 'kana'),
    ('日本語の文章を読みます。', 'kana'),
    ('羯諦羯諦', 'han_only'),
    ('Fumon\'in 普門院', 'mixed_with_latin'),
    ('한국일보 Friday', 'mixed_with_latin'),
    ('（２０１０）', None),                            # full-width digits and brackets only: no CJK letter
    ('Smith（ed.）', None),                          # an English run with a full-width bracket is not CJK mixed with Latin
    ('「」。', None),
])
def test_kind(text, kind):
    assert scripts.kind(text) == kind

def test_private_use_is_not_cjk():
    """A legacy font's private-use codes (U+E000-F8FF, e.g. U+F036 in translation) are not Chinese characters."""
    assert scripts.kind('\uf036\uf036') is None and scripts.kind('\ue000') is None and not scripts.HAN.search('\uf8ff')
    assert scripts.HAN.search('\uf900') and scripts.HAN.search('\ufa6d')          # compatibility ideographs are

def test_hangul_is_cjk():
    """Hangul was missing from the old CJK pattern, so Korean runs were never seen."""
    assert scripts.CJK.search('가') and scripts.CJK.search('힣') and scripts.CJK.search('ㄱ')

@pytest.mark.parametrize('lang, primary', [('zh-Hant-TW', 'zh'), ('ja', 'ja'), ('ko_KR', 'ko'), ('EN-US', 'en'), ('', ''), (None, '')])
def test_primary(lang, primary):
    assert scripts.primary(lang) == primary

@pytest.mark.parametrize('kind, text, doc, kana, expected', [
    # an English document: runs in another language are tagged, Han-only goes to a person
    ('hangul', '한국어', 'en-US', None, ('tag', 'ko')),
    ('kana', 'ひらがな', 'en-US', 'ja', ('tag', 'ja')),
    ('kana', 'ひらがな', 'en-US', None, ('tag', 'ja')),            # kana is only Japanese
    ('han_only', '羯諦', 'en-US', 'ja', ('defer', 'Han-only runs (ja vs zh)')),
    ('mixed_with_latin', '普門院 Fumon', 'en-US', 'ja', ('defer', 'CJK mixed with Latin in one run')),
    # the document's own language: nothing to tag, nothing for a person
    ('han_only', '多元智能', 'zh-CN', None, ('inherit', None)),
    ('han_only', '文化', 'ja', None, ('inherit', None)),            # Japanese kanji
    ('han_only', '首爾', 'ko', None, ('inherit', None)),            # Korean hanja
    ('hangul', '한국어', 'ko-KR', None, ('inherit', None)),
    ('kana', 'ひらがな', 'ja-JP', 'ja', ('inherit', None)),
    ('mixed_with_latin', '한국일보 Friday', 'ko', None, ('inherit', None)),
    ('mixed_with_latin', '普門院 Fumon', 'zh', None, ('inherit', None)),
    # a CJK document with a run in another CJK language
    ('hangul', '한국어', 'ja', None, ('tag', 'ko')),
    ('kana', 'ひらがな', 'zh-Hant', 'ja', ('tag', 'ja')),
])
def test_action(kind, text, doc, kana, expected):
    assert scripts.action(kind, text, doc, kana) == expected
