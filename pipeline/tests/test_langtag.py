"""test_langtag.py: BCP 47 tags are tidied (separator, case, spaces), never guessed.

    python -m pytest tests/test_langtag.py -q
"""
import pytest
from lib import langtag

@pytest.mark.parametrize('value, tag', [
    ('en_US', 'en-US'), (' EN ', 'en'), ('en', 'en'), ('haw', 'haw'), ('zh-hant-tw', 'zh-Hant-TW'),
    ('es-419', 'es-419'), ('ja-JP', 'ja-JP'), ('x-klingon', 'x-klingon'), ('en-x-pig', 'en-x-pig'),
])
def test_tidied(value, tag):
    assert langtag.norm(value) == tag

@pytest.mark.parametrize('value', ['english', 'English', '', 'en US', 'en--US', 'e', '12', 'en-'])
def test_not_a_tag(value):
    assert langtag.norm(value) is None

def test_from_name_maps_only_certain_names():
    from lib import langtag as L
    assert [L.from_name(x) for x in ('Hawaiian', 'Hawaii', 'Marshallese ', ' japanese', 'Hawai', 'Kyoto', 'English (US)', '')] == \
        ['haw', 'haw', 'mh', 'ja', 'haw', None, None, None]
    assert L.shortest('jpn-Latn') == 'ja-Latn' and L.shortest('haw') == 'haw'
