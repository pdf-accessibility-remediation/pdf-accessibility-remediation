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

def test_cjk_document_reverse_direction(tmp_path):
    """In a Chinese, Japanese or Korean document, Latin-script words are candidates even when English ('latin'), and
    CJK text in the document's own language is not."""
    runs = [{'text': 'see the house here'}, {'font': 'F3', 'text': 'mappō'}]
    src = langpdf.build(str(tmp_path / 'z.pdf'), runs, doc_lang='zh')
    chars = plpages.Pages(src).pages[0].chars
    zh, _ = langcands.page_places(1, chars, doc_lang='zh')
    en, _ = langcands.page_places(1, chars, doc_lang='en')
    assert any('latin' in p['class'] and p['text'] == 'see the house here' for p in zh)
    assert not any('latin' in p['class'] for p in en)
    assert any(p['text'] == 'mappō' for p in zh) and any(p['text'] == 'mappō' for p in en)

def test_spoken_text_finds_what_ocr_hid(tmp_path):
    """review 02, M5: on a scanned page the OCR lost the marks (ʻāina → aina, Māui → Maui); the readings (OCR-word forms,
    or a page reading paired word by word) decide the class, and the place stays on the OCR characters."""
    runs = [{'text': 'The aina was'}, {'text': 'good on Maui here'}]
    src = langpdf.build(str(tmp_path / 's.pdf'), runs)
    chars = plpages.Pages(src).pages[0].chars
    plain, _ = langcands.page_places(1, chars)
    assert not any(p['form'] == 'ʻāina' for p in plain)
    by_form, _ = langcands.page_places(1, chars, spoken={'forms': {'aina': 'ʻāina'}})
    p = next(p for p in by_form if p['text'] == 'aina')
    assert p['form'] == 'ʻāina' and 'hawaiian' in p['class'] and (p['mcid'], p['first'], p['last']) == (0, 4, 7)
    by_page, words = langcands.page_places(1, chars, spoken={'reading': 'The ʻāina was good on Māui here'})
    assert {p['form'] for p in by_page} >= {'ʻāina'} and any('ʻāina' in w for w in words)

def test_title_growth_takes_the_whole_italic_title(tmp_path):
    """review 06, M4: a romanized title is one place, capitalized and short words included; an English title around a
    foreign word is not swallowed."""
    runs = [{'font': 'F6', 'text': 'Nihon koten bungaku taikei'}, {'text': 'See the'}, {'font': 'F6', 'text': 'Annals of mappoji Buddhism'}]
    src = langpdf.build(str(tmp_path / 't.pdf'), runs)
    chars = plpages.Pages(src).pages[0].chars
    off = {p['form'] for p in langcands.page_places(1, chars)[0]}
    on = {p['form'] for p in langcands.page_places(1, chars, grow=True)[0]}
    assert 'koten bungaku taikei' in off and 'Nihon koten bungaku taikei' in on
    assert 'mappoji' in on and not any('Annals' in f for f in on)
