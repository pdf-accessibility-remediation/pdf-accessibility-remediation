"""test_langcands.py: which words may be in another language (lib/langcands.py; #118, language tagging). Strings and one
synthetic page; no book content. The offline English list (pipeline/data/english-words.txt) is committed, so no download.

    python -m pytest tests/test_langcands.py -q
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, langcands  # noqa: F401,E402

def test_english_list_with_marks_folded():
    """Patrick, 2026-11-12: a word in the English list printed with Hawaiian marks is part of English."""
    for w in ('aloha', 'lūʻau', 'ʻukulele', 'karma', 'sushi', 'began', 'self-esteem', 'naïve'):
        assert langcands.in_english(w), w
    for w in ('mappō', 'Heiankyo', 'kuleana', 'onryō'):
        assert not langcands.in_english(w), w

def test_classes():
    c = langcands.classify
    assert c('mappō') == ['hawaiian']                 # Hawaiian shape and a kahakō: the AI decides (Japanese here)
    assert c('onryō') == ['marks'] and c('dhāraṇī') == ['marks'] and c('āveśa') == ['marks']
    assert c('ʻāina') == ['hawaiian'] and c('Hawai‘i') == []      # Hawaii is in the English list once the ʻokina is folded
    assert c('Sørensen') == ['accented'] and c('déjà') == ['accented']
    assert c('kuleana') == ['hawaiian']                # 4+ letters, Hawaiian shape, not in the list
    assert c('anthropotechnics') == ['unknown']
    assert c('Ελληνικά') == ['script:greek'] and c('Русский') == ['script:cyrillic']
    for w in ('house', 'aloha', 'xiv', '1984', 'https', 'koreatimes.com', 'the'):
        assert c(w) == [], w

def test_places_on_a_page(tmp_path):
    runs = [{'font': 'F3', 'text': 'The word mappō and onryō here.'}, {'text': 'An oppor-'}, {'text': 'tunities word.'},
            {'font': 'F2', 'text': 'The ʻāina mōʻī word.'}]
    src = langpdf.build(str(tmp_path / 'p.pdf'), runs)
    places, words = langcands.page_places(1, plpages.Pages(src).pages[0].chars)
    by = {(p['mcid'], p['text']): p for p in places}
    assert (0, 'mappō') in by and (0, 'onryō') in by                    # two places, not one phrase ("and" is English)
    assert not any(p['mcid'] in (1, 2) for p in places)                 # "oppor-" + "tunities" rejoined: English
    p = by[(0, 'mappō')]
    assert (p['first'], p['last'], p['n'], p['whole']) == (9, 13, 30, False)
    assert words[p['w0']].startswith('mapp')
