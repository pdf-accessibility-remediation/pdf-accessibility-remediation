"""test_langtag.py: BCP 47 tags are tidied (separator, case, spaces), never guessed.

    python -m pytest tests/test_langtag.py -q
"""
import json
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

def test_kept_value_is_what_fix_lang_values_leaves():
    """review 12, C: a code in its shortest form, a name as its code when its words fit, anything else as written."""
    from lib import langtag as L
    assert L.kept_value('fr-FR') == 'fr-FR' and L.kept_value('jpn') == 'ja' and L.kept_value('en_US') == 'en-US'
    assert L.kept_value('Hawaiian', 'Aloha mai kakou e hele ana') == 'haw'
    assert L.kept_value('Hawaii', 'Oahu, a Giant Military Base') == 'Hawaii'                     # mostly English: for a person
    assert L.kept_value('Hungarian', 'Kaleo Mahoe Akana') == 'Hungarian' and L.kept_value('xx-nonsense!') == 'xx-nonsense!'
    import os
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'apply.py'), encoding='utf-8').read()
    assert 'def name_misfit' not in src and 'langtag.name_misfit(code, text)' in src                # one copy, in lib/langtag.py

def test_every_tag_the_language_prompt_names_is_allowed():
    """#137 (dropped language answers): a tag the language prompt asks for is one the step may write. Every BCP 47-shaped
    word in the prompt's backticks is checked, except the ones it forbids and the reply's field names."""
    import os, re
    import name_languages
    prompt = open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'prompts',
                               name_languages.PROMPT_NAME), encoding='utf-8').read()
    forbidden, fields = {'jp', 'cn', 'eng', 'jpn'}, {'id', 'low', 'why'}
    tags = set(re.findall(r'`([a-z]{2,3}(?:-[A-Za-z]{2,4})?)`', prompt)) - forbidden - fields
    assert {'yue-Latn', 'ja-Latn', 'zh', 'haw'} <= tags                      # the scan finds the tags it should
    assert [t for t in sorted(tags) if not langtag.valid_part(t)] == []
    assert not any(langtag.valid_part(t) for t in forbidden)

def test_tags_once_refused_are_named():
    """#137: romanized Cantonese and Ancient Greek, and Tok Pisin (Patrick, 2026-11-17); Hawaiʻi Creole English is not
    in this branch."""
    for t, n in (('yue-Latn', 'Cantonese (Romanized)'), ('grc-Latn', 'Ancient Greek (Romanized)'), ('tpi', 'Tok Pisin'),
                 ('jv', 'Javanese'), ('aoi', 'Anindilyakwa')):            # #140's stricter join gives these words back
        assert langtag.valid_part(t) and langtag.name(t) == n
    assert langtag.shortest('jav') == 'jv' and not langtag.valid_part('jav')   # the shortest form only
    assert not langtag.valid_part('hwc')

def test_the_languages_the_ladder_named_are_written():
    """#137, round 11: languages the AI named in the reference books' answers and the table lacked, each a language
    subtag in the IANA registry. A specific language stays itself: Central Bikol is bcl, never its macrolanguage bik."""
    for t, n in (('bcl', 'Central Bikol'), ('ban', 'Balinese'), ('su', 'Sundanese'), ('min', 'Minangkabau'), ('aly', 'Alyawarr'),
                 ('bbc', 'Batak Toba'), ('mak', 'Makasar'), ('rar', 'Rarotongan'), ('jv-Latn', 'Javanese (Latin script)'),
                 ('ryu-Latn', 'Okinawan (Romanized)'), ('bo-Latn', 'Tibetan (Romanized)'), ('hi-Latn', 'Hindi (Romanized)'),
                 ('ar-Latn', 'Arabic (Romanized)'), ('ks-Latn', 'Kashmiri (Romanized)'), ('kk-Latn', 'Kazakh (Romanized)')):
        assert langtag.valid_part(t) and langtag.name(t) == n, t
    assert langtag.name('bcl') != langtag.name('bik')

def test_a_latn_subtag_the_registry_suppresses_is_left_out():
    """BCP 47: a script subtag equal to the language's Suppress-Script is left out. ms-Latn is ms; a romanization of a
    language written in another script keeps it, and so does a language with no Suppress-Script (jv)."""
    w = langtag.without_suppressed_script
    assert w('ms-Latn') == 'ms' and w('vi-Latn') == 'vi' and w('tl-Latn') == 'tl' and w('en-Latn') == 'en'
    assert w('ja-Latn') == 'ja-Latn' and w('bo-Latn') == 'bo-Latn' and w('ryu-Latn') == 'ryu-Latn' and w('jv-Latn') == 'jv-Latn'
    assert w('ms') == 'ms' and w(None) is None and w('ms-Latn-MY') == 'ms-Latn-MY'

def test_a_tag_the_table_cannot_name_is_still_refused():
    """A collection code (btk, "Batak languages") and an unknown tag stay refused: their words go to a person."""
    assert not langtag.valid_part('btk') and not langtag.valid_part('xx-Zzzz') and not langtag.valid_part('qqq')

def test_the_reply_parse_reads_ms_latn_as_ms_and_keeps_the_new_tags():
    from lib import langreq
    reply = json.dumps({'decisions': [{'id': '1', 'lang': 'ms-Latn', 'confidence': 'high', 'why': 'language'},
                                      {'id': '2', 'lang': 'bcl', 'confidence': 'high', 'why': 'language'},
                                      {'id': '3', 'lang': 'btk', 'confidence': 'medium', 'why': 'language'}]})
    d, dr = langreq.parse(reply, {'1', '2', '3'})
    assert d['1']['lang'] == 'ms' and d['2']['lang'] == 'bcl' and '3' not in d and [e['code'] for e in dr if e['id'] == '3'] == ['tag']
