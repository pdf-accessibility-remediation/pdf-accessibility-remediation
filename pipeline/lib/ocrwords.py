"""ocrwords.py: which OCR words in a scanned book look misread, for audit.py's word sheets (docs/ocr-words.md).

    ocrwords.words(chars, page_chars)   -> lists of characters, one list per word
    ocrwords.suspect(core)              -> True when the word should be read from the scan

Words are split where a reader hears a break: a space character, a gap between glyphs (gaptext.breaks, the rule the digest
uses; OCR layers such as Acrobat 8's draw each word apart with no space character), a new line, or untagged text.

A word is a suspect when OCR's look-alikes for letters it doesn't know show in it:
  - "ii" for ā, ū, ü or ñ (nibbāna → nibbiina), or ; : ¢ £ | between letters for ṇ, ḍ, ṃ (put;l¢arlka);
  - a quote mark for the ʻokina inside a word of Hawaiian shape (Hawai‘i, Moloka‘i; never don't or O'Brien).
One reading is applied to every occurrence of a form, so a form must stand for one printed word. A kahakō that OCR
dropped (Māui → Maui) leaves a normal-looking word, and in Hawaiian the same letters can be two words (na / nā, ʻaina /
ʻāina), so such words are not suspects: fixing them needs a reading per occurrence.
"""
import re, unicodedata
from lib import gaptext

SUSPECT = re.compile(r'(?<=[A-Za-z])ii|ii(?=[a-z])|[A-Za-z][;:¢£·|][A-Za-z¢£]|[¢£]')
OKINA = 'ʻ'                                  # U+02BB, the correct character
OKINA_LIKE = "‘’'`"                          # what OCR and typists put for it
HAW_LETTERS = set('aeiouāēīōūhklmnpw')       # the Hawaiian alphabet
HAW_VOWELS = set('aeiouāēīōū')

def core(t):
    """The word without the punctuation around it (the executor splits words the same way)."""
    return re.sub(r'^\W+|\W+$', '', t)

def words(chars, page_chars=None):
    """chars: a page's characters in content order. Yields one list of characters per word, in tagged content only."""
    cs, brk = gaptext.breaks(chars, page_chars)
    word = []
    for i, c in enumerate(cs):
        if c.get('mcid') is None or c['text'].isspace() or brk[i] or (word and abs(c['top'] - word[-1]['top']) > 3):
            if word: yield word
            word = []
        if c.get('mcid') is not None and not c['text'].isspace(): word.append(c)
    if word: yield word

def hawaiian_shape(w):
    """Only Hawaiian letters (with an ʻokina or a look-alike between them), at least two letters, ending in a vowel:
    every Hawaiian word has this shape; few English words do (they end in a consonant or use b, d, r, s, t …)."""
    w = unicodedata.normalize('NFC', w.lower())
    letters = [ch for ch in w if ch not in OKINA_LIKE and ch != OKINA]
    return len(letters) >= 2 and all(ch in HAW_LETTERS for ch in letters) and letters[-1] in HAW_VOWELS

def okina_lookalike(w):
    """A quote mark standing for an ʻokina inside a word of Hawaiian shape (Hawai‘i, Lili‘uokalani)."""
    return hawaiian_shape(w) and any(ch in OKINA_LIKE for ch in w)

URL = re.compile(r'@|://|www\.|\.(?:com|org|net|edu|gov)\b', re.I)

def suspect(w):
    if not w or re.fullmatch(r'[ivxlcdm]+', w.lower()): return False     # a roman numeral (ii, iii, xii)
    if URL.search(w): return False                                       # a web or email address (koreatimeshawaii.com)
    return bool(SUSPECT.search(w)) or okina_lookalike(w)

# ---- a saved reply reused (REPLY= / FROM= / the regression test): do its ids still name the words it was written for?
# The model answers by id, and an id is a place in the audit's list; decide.py fingerprints the list it sends.

def replay_verdict(saved_fp, now_fp, then_n=None, now_n=None):
    """saved_fp: the fingerprint of the list the reply was written for (None: not recorded); now_fp: today's list.
    then_n, now_n: the number of forms then and now (then_n None: not recorded).
    -> ('same list', None) | ('list changed', why) | ('no fingerprint', why). Only 'same list' lets the readings be used."""
    if saved_fp and saved_fp == now_fp: return 'same list', None
    if then_n is not None and then_n != now_n:
        return 'list changed', f'the word list changed since ({then_n} forms then, {now_n} now)'
    if saved_fp: return 'list changed', 'the word list changed since'
    return 'no fingerprint', 'the reply predates the OCR-word fingerprint, so its ids cannot be checked against the current word list'

def carried(run):
    """What a saved reply takes with it into a later reuse (FROM=, regression.py --seed): the fingerprint, size and
    list (id → form) of the OCR-word list the reply was written for. A run that made the call passes on its own list;
    a run that reused a reply passes on what it was given, never the list it was replayed against."""
    ow = run.get('ocr_words') or {}
    if run.get('response_from'): fp, n, lst = ow.get('reply_fingerprint'), ow.get('reply_read'), ow.get('reply_list')
    else: fp, n, lst = ow.get('fingerprint'), ow.get('sent') or None, ow.get('list')
    return {k: v for k, v in (('ocr_words_fingerprint', fp), ('ocr_words_sent', n), ('ocr_words_list', lst)) if v is not None}
