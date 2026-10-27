"""test_ocrwords.py: which OCR words a scanned book's audit sends to the model, and how words are split (lib/ocrwords.py).

    python -m pytest tests/test_ocrwords.py -q

The expected results follow docs/ocr-words.md.
"""
import pytest
from lib import ocrwords

@pytest.mark.parametrize('word, expected', [
    # OCR's look-alikes for diacritics
    ('nibbiina', True), ('tathiigata', True), ('Miiller', True), ('iitman', True), ("Saddharmaput;l¢arlka", True),
    # ʻokina read as a quote mark, inside a word of Hawaiian shape
    ('Hawai‘i', True), ("Hawai'i", True), ('Hawai’i', True), ('Moloka‘i', True), ('Lili‘uokalani', True), ('O‘ahu', True),
    # not suspects
    ('ii', False), ('iii', False), ('xii', False),                      # roman numerals
    ("don't", False), ("it's", False), ("O'Brien", False), ("we'll", False), ("he'd", False),
    ('Hawaiʻi', False), ('ʻōlelo', False),                              # already the right ʻokina
    ('Maui', False), ('aina', False), ('Kalakaua', False),              # a dropped kahakō: na / nā can be two words
    ('literature', False), ('', False),
    ('koreatimeshawaii.com', False), ('edit@koreatimeshawaii.com', False), ('www.koreatimeshawaii.com', False),
])
def test_suspect(word, expected):
    assert ocrwords.suspect(word) is expected

@pytest.mark.parametrize('word, shape', [('hawaii', True), ('aloha', True), ('kahakō', True), ('Lāna‘i', True),
                                         ('make', True), ('the', False), ('words', False), ('a', False), ('maui', True)])
def test_hawaiian_shape(word, shape):
    assert ocrwords.hawaiian_shape(word) is shape

def test_core_strips_surrounding_punctuation_only():
    assert ocrwords.core('(nibbiina),') == 'nibbiina'
    assert ocrwords.core('“Hawai‘i.”') == 'Hawai‘i'

def ch(text, x0, top=100, size=10, mcid=1):
    return {'text': text, 'x0': x0, 'x1': x0 + 0.5 * size, 'top': top, 'bottom': top + size, 'size': size, 'upright': True, 'mcid': mcid}

def as_text(ws): return [''.join(c['text'] for c in w) for w in ws]

def test_words_split_at_spaces():
    cs = [ch('k', 0), ch('a', 5), ch(' ', 10), ch('m', 15), ch('e', 20)]
    assert as_text(ocrwords.words(cs)) == ['ka', 'me']

def test_words_split_at_gaps_with_no_space_character():
    """An OCR layer that draws each word apart, with no space between (Acrobat 8 on 'No ka hooulu'): one word per gap."""
    cs = [ch('k', 0), ch('e', 5), ch('l', 10), ch('a', 15),       # kela, letters touching
          ch('m', 30), ch('e', 35),                                # 10 pt gap: a new word
          ch('k', 50), ch('e', 55), ch('i', 60), ch('a', 65)]
    assert as_text(ocrwords.words(cs)) == ['kela', 'me', 'keia']

def test_words_split_at_line_and_untagged_text():
    cs = [ch('k', 0), ch('a', 5), ch('m', 0, top=120), ch('e', 5, top=120), ch('x', 10, top=120, mcid=None), ch('o', 15, top=120)]
    assert as_text(ocrwords.words(cs)) == ['ka', 'me', 'o']

# ---- a reused reply's OCR-word readings (docs/ocr-words.md, "Reused replies")
@pytest.mark.parametrize('saved, now, then_n, now_n, verdict, why', [
    ('abc', 'abc', 4, 4, 'same list', None),
    ('abc', 'abc', None, 4, 'same list', None),
    ('abc', 'xyz', 4, 4, 'list changed', 'the word list changed since'),
    ('abc', 'xyz', 4, 8, 'list changed', 'the word list changed since (4 forms then, 8 now)'),
    (None, 'xyz', 4, 8, 'list changed', 'the word list changed since (4 forms then, 8 now)'),     # sands: counts known, no fingerprint
    (None, 'xyz', 645, 645, 'no fingerprint', 'predates'),                                        # same size proves nothing
    (None, 'xyz', None, 645, 'no fingerprint', 'predates'),
    (None, None, None, 0, 'no fingerprint', 'predates'),
])
def test_replay_verdict(saved, now, then_n, now_n, verdict, why):
    v, w = ocrwords.replay_verdict(saved, now, then_n, now_n)
    assert v == verdict
    assert (w is None) if why is None else why in w

def test_carried_from_a_call():
    run = {'ocr_words': {'forms': 8, 'sent': 8, 'fingerprint': 'f8'}}
    assert ocrwords.carried(run) == {'ocr_words_fingerprint': 'f8', 'ocr_words_sent': 8}

def test_carried_from_a_replay_passes_on_the_reply_list_not_todays():
    run = {'response_from': 'x/reply.txt', 'ocr_words': {'sent': 645, 'fingerprint': 'today', 'reply_read': 648}}
    assert ocrwords.carried(run) == {'ocr_words_sent': 648}          # no fingerprint was given, so none is passed on

def test_carried_nothing_without_ocr_words():
    assert ocrwords.carried({'ocr_words': {'forms': 0, 'sent': 0}}) == {}
    assert ocrwords.carried({}) == {}
