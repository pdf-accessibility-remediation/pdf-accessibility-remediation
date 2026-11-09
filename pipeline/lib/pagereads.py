"""pagereads.py: whole-page AI readings of scanned Hawaiian pages (issue #49, docs/ocr-words.md).

    pagereads.hawaiian_share(words)        -> share of a page's longer words that have Hawaiian shape, or None (too few)
    pagereads.align(ocr_words, ai_words)   -> {ocr index: reading} for the words to respell, and counts
    pagereads.okina_slip(text)             -> (text, n): a reading that wrote every ʻokina as a quote mark, corrected

The audit picks pages where most words look Hawaiian (Tesseract has no Hawaiian model, so the OCR lost the ʻokina and
kahakō). read_pages.py sends each page image to the model, which transcribes it exactly as printed. The executor then
gives each OCR word the reading at its own place (ActualText). Unlike ocr_words, a reading is per occurrence, not per
form: in Hawaiian the same letters can be two words (na / nā, ʻaina / ʻāina), so only the page context tells them apart.
"""
import difflib, re, unicodedata
from lib import ocrwords
from lib.workorder_check import distance, skeleton, JUNK

SHARE_MIN = 0.5            # a page is read when at least half its longer words have Hawaiian shape (Makalei: 86 of 90 pages)
WORDS_MIN = 20             # longer words a page needs before its share counts
LONG = 4                   # letters a word needs to count: short English words (he, me, no) have Hawaiian shape too
PROMPT_NAME = 'page_reading_v1.md'
OKINA_LIKE = ocrwords.OKINA_LIKE + ocrwords.OKINA

def hawaiian_share(words):
    """words: a page's word texts. The share of its longer words (LONG+ letters) with Hawaiian shape; None when it has
    fewer than WORDS_MIN of them (a figure page, a short page)."""
    long_ = [w for w in (ocrwords.core(x) for x in words) if len(re.sub(f'[{OKINA_LIKE}]', '', w)) >= LONG]
    if len(long_) < WORDS_MIN: return None
    return sum(ocrwords.hawaiian_shape(w) for w in long_) / len(long_)

SLIP_MIN = 5               # quote marks inside Hawaiian-shaped words, with no ʻokina at all, before a reading counts as a slip
def okina_slip(text):
    """The model sometimes writes every ʻokina on a page as a quote mark (Makalei p. 59: 169 times as ‘ in one run, all
    as ʻ in another, same prompt and image). A reading with no U+02BB at all and SLIP_MIN or more quote marks inside
    words of Hawaiian shape has them changed to ʻ. A page that prints an apostrophe once or twice (No ka hooulu's ma'u)
    stays as read. -> (text, number changed)."""
    if ocrwords.OKINA in text: return text, 0
    def fix(w):
        """A token with its ʻokina look-alikes made ʻ: inside a word of Hawaiian shape, and at its start (‘o, ‘ana)."""
        lead = re.match(r"^\W*", w).group(0); c = ocrwords.core(w)
        if not (ocrwords.hawaiian_shape(c) or (lead and c.lower() in ocrwords.HAW_VOWELS)): return w     # ‘o, ‘O: one vowel after the mark
        if lead and lead[-1] in "‘'`": lead = lead[:-1] + ocrwords.OKINA
        body = ''.join(ocrwords.OKINA if ch in ocrwords.OKINA_LIKE else ch for ch in c)
        return lead + body + w[len(re.match(r"^\W*", w).group(0)) + len(c):]
    toks = re.findall(r'\S+', text)
    if sum(fix(t) != t for t in toks) < SLIP_MIN: return text, 0
    out = re.sub(r'\S+', lambda m: fix(m.group(0)), text)
    return out, sum(a != b for a, b in zip(out, text))

def key(w):
    """What the OCR and the page have in common: letters only, lower case, no marks, no ʻokina or look-alike."""
    d = unicodedata.normalize('NFD', w.lower())
    return ''.join(c for c in d if c.isalnum() and c not in OKINA_LIKE and not unicodedata.combining(c))

LETTERS_MIN = 4            # letters a reading needs before its letters (not only its marks) may differ from the OCR word
def accept(ocr, reading):
    """None if the reading may replace the OCR word at this place, else why not. Marks alone (ʻokina, kahakō) may always
    differ. In a word of LETTERS_MIN+ letters, letters may differ as for an ocr_words reading (up to a third of it, at
    least 2, OCR junk counting a quarter); in a shorter word only where the OCR has junk (junk_only): on a hard page (two
    columns, a curved photo) a short OCR word can be paired with the wrong word (a → sea, to → of)."""
    if not reading or re.search(r'\s', reading): return 'not one word'
    if reading == ocr: return 'same'
    if key(reading) == key(ocr): return None                     # only marks differ: ʻokina, kahakō, case of a mark
    o_, r_ = (re.sub(f'[{OKINA_LIKE}]', '', w) for w in (ocr, reading))      # an ʻokina is a mark here, not a letter
    n = len(skeleton(r_))
    if min(n, len(skeleton(o_))) < LETTERS_MIN: return None if junk_only(o_, r_) else 'too different'   # either word short
    if distance(o_, r_) > max(2, 0.34 * n): return 'too different'
    return None

SHORT_JUNK = set(JUNK) | set('0123456789@d')    # what OCR makes of a letter it can't read in a short word: o → 0, lā → 1a, pū → pi, nō → nd
def junk_only(ocr, reading):
    """A short word's letters may differ only where the OCR has junk: every character it replaced or dropped is in
    SHORT_JUNK, nothing was added and the word is no longer (a → sea, th → the, 0 → formed; e → 34 replaces a real letter)."""
    a, b = skeleton(ocr), skeleton(reading)
    if len(b) > len(a): return False                              # junk stands for letters, never for more of them (1 → Molokaʻi)
    for op, i1, i2, _, _ in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == 'insert' or (op in ('replace', 'delete') and not set(a[i1:i2]) <= SHORT_JUNK): return False
    return True

def align(ocr_words, ai_words):
    """ocr_words, ai_words: the cores of the words in order (ocrwords.core). Pairs them by key(); only one-to-one
    pairs count (a word the OCR split or joined is left as it is). -> (changes {ocr index: reading}, counts)."""
    a, b = [key(w) for w in ocr_words], [key(w) for w in ai_words]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    changes, n = {}, {'ocr_words': len(ocr_words), 'ai_words': len(ai_words), 'paired': 0, 'changed': 0, 'too_different': 0, 'unpaired': 0}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                o, r = ocr_words[i1 + k], unicodedata.normalize('NFC', ai_words[j1 + k]); n['paired'] += 1
                why = accept(o, r)
                if why is None: changes[i1 + k] = r; n['changed'] += 1
                elif why == 'too different': n['too_different'] += 1
        else: n['unpaired'] += i2 - i1
    return changes, n
