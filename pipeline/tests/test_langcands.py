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

def test_hyphen_english_rule():
    """#140 (hyphen at a line end): the form with its hyphen counts as English only for halves of 3+ plain letters whose
    joined form has no romanized shape (Hepburn or pinyin, a doubled consonant read as one)."""
    h = langcands.hyphen_english
    assert h('long', 'standing') and h('highest', 'ranking') and h('white', 'robed')
    assert not h('keg', 'are') and not h('ship', 'pei')          # kegare, shippei: Japanese split into English-looking halves
    assert not h('Kō', 'dan') and not h('ho', 'jo')              # marks, short halves
    assert not h('infor', 'mation')                              # no hyphen form: classify's joined check decides it

def test_english_compound_broken_at_its_hyphen(tmp_path):
    """#140: "long-" / "standing" across two runs (and two lines) is no candidate; "infor-" / "mation" neither."""
    runs = [{'text': 'A long-'}, {'text': 'standing rule, and infor-'}, {'text': 'mation here.'}]
    places, _ = langcands.page_places(1, plpages.Pages(langpdf.build(str(tmp_path / 'h.pdf'), runs)).pages[0].chars)
    assert places == []

def test_romanized_word_broken_across_runs(tmp_path):
    """#140: a romanized word broken across two runs is one form with two places, the second half's place with the form
    and classes of its first half's phrase; the phrase ends at the second half ("pusa" is a phrase of its own)."""
    runs = [{'text': 'The sutra qianyan guanshi-'}, {'text': 'yin pusa here.'}, {'text': 'A keg-'}, {'text': 'are rite.'}]
    places, _ = langcands.page_places(1, plpages.Pages(langpdf.build(str(tmp_path / 'r.pdf'), runs)).pages[0].chars)
    by = {(p['mcid'], p['text']): p for p in places}
    first, second = by[(0, 'qianyan guanshi')], by[(1, 'yin')]
    assert first['form'] == second['form'] == 'qianyan guanshiyin'
    assert first['class'] == second['class']
    assert (1, 'pusa') in by and by[(1, 'pusa')]['form'] == 'pusa'
    assert by[(2, 'keg')]['form'] == by[(3, 'are')]['form'] == 'kegare'   # English-looking halves of a Hepburn word stay a candidate

def test_romanized_word_broken_in_one_run(tmp_path):
    """#140: both halves in the same run: one place covering them, with the joined form."""
    runs = [{'body': ['(The sutra qianyan guanshi-) Tj', 'T*', '(yin pusa here.) Tj']}]
    places, _ = langcands.page_places(1, plpages.Pages(langpdf.build(str(tmp_path / 'o.pdf'), runs)).pages[0].chars)
    p = next(p for p in places if p['form'] == 'qianyan guanshiyin')
    assert p['text'].endswith('yin') and 'pusa' not in p['text']
    assert any(q['form'] == 'pusa' for q in places)

def test_a_second_half_after_a_passage_takes_the_passages_form(tmp_path):
    """#140: when the first half's run is a passage, the second half (in its own run) is a place of the passage's form;
    a second half counts toward no passage on its own."""
    runs = [{'text': 'qianyan zhibing heyao pusa jingdian nangajuk-'}, {'text': 'wama is a word.'}]
    places, _ = langcands.page_places(1, plpages.Pages(langpdf.build(str(tmp_path / 'p.pdf'), runs)).pages[0].chars)
    by = {(p['mcid'], p['text']): p for p in places}
    first = next(p for p in places if p['mcid'] == 0)
    assert first['class'][0] == 'passage' and by[(1, 'wama')]['form'] == first['form'] and by[(1, 'wama')]['class'] == first['class']

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

def test_title_growth_leaves_common_english_words_out(tmp_path):
    """review 08, M6: a common English word with a romanized shape (King, China) or an English name of a people (Japanese)
    never joins a title through the shape exception; a rarer one (Nihon, Kamakura) still does. Synthetic lines."""
    runs = [{'font': 'F6', 'text': 'King Kujaku myoo'}, {'text': 'and'}, {'font': 'F6', 'text': 'Kamakura bukkyo'}, {'text': 'in'},
            {'font': 'F6', 'text': 'Konjaku monogatarishu Japanese'}]
    src = langpdf.build(str(tmp_path / 'c.pdf'), runs)
    on = {p['form'] for p in langcands.page_places(1, plpages.Pages(src).pages[0].chars, grow=True)[0]}
    assert 'Kamakura bukkyo' in on and not any('King' in f or 'Japanese' in f for f in on)
    assert langcands.common_romanized('China') and langcands.common_romanized('Kongō') is False and langcands.common_romanized('Japanese')
    assert not langcands.common_romanized('Hō') and not langcands.common_romanized('Tang') and not langcands.common_romanized('Song')   # review 10, L4
