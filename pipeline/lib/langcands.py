"""langcands.py: words and passages that may be in another language, found locally (no model, no network): the language
step's candidates (#118, language tagging; WCAG 3.1.2).

    langcands.page_places(pno, chars, page_chars=None, italic=None)  -> (places, words) for one page
    langcands.book(PL)                                               -> {'places': [...], 'pages': {...}, 'stats': {...}}
    langcands.in_english(word)                                       -> True when the word is in the English word list

A place is where a tag could go: (page, mcid, first, last), the first and last character index within that marked-content
run, counted over pdfplumber's characters for the MCID in content order (one character per character code; the codes
under a spoken-text span are counted, the span's text is not). The executor finds the place by the same count, never by
reading the text again, so a font's encoding never matters (lib/mcsplit.py). The phrase is kept beside it for people and
for checks.

Classes (a place may have more than one):
  cjk:kana, cjk:hangul, cjk:han_only, cjk:mixed   a stretch of CJK characters (lib/scripts.kind)
  script:<name>                                   Greek, Cyrillic, Arabic, Hebrew, Thai, Devanagari …
  hawaiian    an ʻokina (U+02BB, or a quote mark inside a Hawaiian-shape word), a kahakō in a Hawaiian-shape word, or a
              4+ letter Hawaiian-shape word not in the English list; also every word of a run of 3+ Hawaiian-shape words
              (single vowels between them allowed), one of them not in the English list
  marks       romanization marks (Hepburn, IAST: ā ī ū ē ō ś ṣ ṇ ṭ ḍ ṃ ṛ ḥ ñ …)
  accented    other Latin accents (é è ü ö ç …)
  unknown     4+ letters, lower case, not in the English list
  latin       in a Chinese, Japanese or Korean document only: any Latin-script word of 2+ letters (English, romanization …)
A word whose letters, with marks and the ʻokina folded away, are in the English list is part of English and never a
candidate on its own (lūʻau, ʻukulele, sūtra: Patrick, 2026-11-12); a run of 3+ Hawaiian-shape words still takes it in.
Names are not removed here: deciding what is a name is the AI's job (WCAG exempts Latin-script names only; CJK and other
scripts are never exempt).

Words are split as the OCR-word sheets split them (lib/ocrwords.words: spaces, gaps, new lines), then at dashes, slashes
and quotes, and where the script changes between CJK and Latin. A word broken by a hyphen at a line end is rejoined for the
list check, without its hyphen ("oppor-" + "tunities") and with it ("long-" + "standing", halves of three or more plain
letters: hyphen_english); English either way, it is no candidate. A candidate's second half is classed with its first and
ends the phrase it is in (#140): when both halves are in the same run, one place covers them; when they are in different
runs, the second half is a place of its own with the form and classes of the place its first half ended in (a passage's,
when the first half's run is one), so the two places are one form and one decision. All this only at a real line end
(line_end, review 04 H1): a hyphen inside its line whose second part the PDF draws after the next line's first word
("homes-" then "are") leaves that word as before (the join still serves the list check). A second half classed only
through its first half (`half_cls`) counts toward no passage, and gets no place when its first half has none (drawn
across two runs); one that is a candidate on its own (in a run of Hawaiian-shape words) is treated as before.
Consecutive candidate words in one run form one phrase. A run in which most words are candidates (PASSAGE_SHARE, at least
PASSAGE_MIN words) is one place for the whole run.
"""
import os, re, json, bisect, hashlib, unicodedata, collections
from lib import scripts, ocrwords

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDLIST = os.path.join(HERE, 'data', 'english-words.txt')
PASSAGE_SHARE, PASSAGE_MIN = 0.75, 6      # of the run's words of 2+ letters
HAW_RUN = 3                         # this many Hawaiian-shape words in a row make a phrase without marks

ROMAN = re.compile(r'[āīūēōĀĪŪĒŌṃṁṇṭḍśṣṛṝḷḥṅŚṢṬḌṆṚḤṄǎěǐǒǔ]')
HAW_MARK = re.compile(r'[āēīōūĀĒĪŌŪʻ]')
LATIN = re.compile(r'[A-Za-zÀ-ɏḀ-ỿ]')
ACCENTED = re.compile(r'[À-ÿĀ-ɏḀ-ỿ]')
SCRIPTS = [('greek', r'[Ͱ-Ͽἀ-῿]'), ('cyrillic', r'[Ѐ-ӿ]'), ('hebrew', r'[֐-׿]'), ('arabic', r'[؀-ۿ]'), ('thai', r'[฀-๿]'),
           ('devanagari', r'[ऀ-ॿ]'), ('khmer', r'[ក-៿]'), ('lao', r'[຀-໿]'), ('burmese', r'[က-႟]')]
SCRIPTS = [(n, re.compile(p)) for n, p in SCRIPTS]
CUT = set('—–/“”"…«»„‚()[]{}')
HYPHENS = '-‐‑'
GROW_STOP = {'of', 'or', 'and', 'the', 'by', 'for', 'with', 'from', 'at'}   # English function words never join a title (#136)
RUN_END = re.compile(r'[.,;:!?)\]}”"’»]\s*$')   # growth into the next run (proposal 20 (b)): a word ending a phrase stops it,
RUN_OPEN = re.compile(r'^\s*[(\[{“"‘«]')          # and so does one opening a bracket or quote at the start of the next run
PHRASE_END = re.compile(r'[,;][”"’»)\]}]*\s*$')    # L3 (review 22; Patrick, 2026-11-21): a word ending in a comma or semicolon
QUOTE_OPEN, QUOTE_CLOSE, QUOTE_WINDOW = '“"«', '”"»', 10   # ends a phrase in a run, unless inside quotes (review 24 §7.3)
PERIOD_END = re.compile(r'\.[”"’»)\]}]*\s*$')    # a period ends one too (review 26 §11, variant P; Patrick, 2026-11-21),
_SHORT = re.compile(r'\d[\d,]*|[^\W\d_]{1,2}|(?:[^\W\d_]{1,2}\.)+[^\W\d_]{1,2}')   # except after a short core:


def period_end(t):
    """A word ending in a period (any closing quote or bracket after it) ends a phrase, unless its core is a number ("1."),
    one or two letters ("K.", "St.", "pp.") or initials of one or two letters each ("D.T."). No list of abbreviations:
    "vols." and "Mohd." end a phrase (review 26 §11 measured it)."""
    if not PERIOD_END.search(t): return False
    core = re.sub(r'[.”"’»)\]}\s]+$', '', t.strip()).lstrip('“"‘«([{')
    return not _SHORT.fullmatch(core)
ITALIC = re.compile(r'(?i)ital|oblique|-it$|-it[A-Z]|It$')
NUMERAL = re.compile(r'(?i)[ivxlcdm]+|\d[\d,.]*\w{0,3}')

# the shapes of romanized Japanese (Hepburn syllables) and Chinese (pinyin syllables), marks removed: a word in the English
# list with one of these shapes ("Nihon", "Kyoto") may still join a romanized title (grow); "Annals", "Buddhism" may not, nor
# a common English word of that shape or an English name of a people ("China", "Home", "King", "Japanese": common_romanized)
JA_SYL = re.compile(r"(?i)^(?:(?:ky|sh|ch|ts|ny|hy|my|ry|gy|by|py|j|[kgsztdnhbpmyrwf])?[aiueo]|n(?![aiueoy]))+$")
_PY_INITIALS = ('zh', 'ch', 'sh') + tuple('bpmfdtnlgkhjqxrzcsyw') + ('',)
_PY_FINALS = ('iang', 'iong', 'uang', 'ang', 'eng', 'ing', 'ong', 'ian', 'iao', 'uai', 'uan', 'ai', 'ei', 'ao', 'ou', 'an', 'en', 'in',
              'un', 'ia', 'ie', 'iu', 'ua', 'uo', 'ui', 'er', 'a', 'o', 'e', 'i', 'u', 'ü')
_PY_UNITS = sorted({i + f + t for i in _PY_INITIALS for f in _PY_FINALS for t in ('', 'n', 'ng')}, key=len, reverse=True)
class _Pinyin:
    """The pinyin shape: the word is a run of syllables (an initial or none, a final, an optional n or ng), case ignored.
    Matched by segmenting in linear time: the regular expression it replaces could backtrack exponentially (CodeQL
    py/redos, #118 final round). match(w) is truthy exactly when that expression matched."""
    MAX = max(len(u) for u in _PY_UNITS)
    UNITS = frozenset(_PY_UNITS)
    def match(self, w):
        w = (w or '').lower(); n = len(w)
        if not n: return False
        ok = [False] * (n + 1); ok[0] = True
        for i in range(n):
            if not ok[i]: continue
            for j in range(i + 1, min(n, i + self.MAX) + 1):
                if w[i:j] in self.UNITS: ok[j] = True
        return ok[n]
PINYIN = _Pinyin()
class _PinyinU(_Pinyin):
    UNITS = frozenset(_PY_UNITS) | {i + f + t for i in _PY_INITIALS for f in ('üan', 'ün', 'üe') for t in ('', 'n', 'ng')}
PINYIN_U = _PinyinU()   # tools/lang_test.py's variant
def romanized_shape(w):
    b = ''.join(ch for ch in unicodedata.normalize('NFD', w.lower()) if not unicodedata.combining(ch))
    return bool(b) and b.isalpha() and bool(JA_SYL.match(b) or PINYIN.match(b))

COMMON = os.path.join(HERE, 'data', 'english-common-romanized.txt')   # SCOWL sizes 10-35 with a romanized shape (review 08, M6)
DYNASTIES = {'xia', 'shang', 'zhou', 'qin', 'han', 'jin', 'sui', 'tang', 'song', 'liao', 'yuan', 'ming', 'qing', 'wei', 'liang', 'chen'}   # may join a title (review 10, L4)
EN_PEOPLE = {'japan', 'japanese', 'korea', 'korean', 'chinese', 'taiwanese', 'tibetan'}   # English names of places and peoples
_COMMON = None
def common_romanized(w):
    """A common English word (SCOWL sizes 10-35) that has a romanized shape, or an English name of a people or place (Japan,
    Japanese): it never joins a romanized title through the shape exception (China, Home, One, King, Rite; review 08, M6)."""
    global _COMMON
    if _COMMON is None:
        with open(COMMON, encoding='utf-8') as f: _COMMON = frozenset(x.strip() for x in f if x.strip())
    d = unicodedata.normalize('NFD', w.lower())
    if any(unicodedata.combining(ch) for ch in d): return False          # Hō, Dō, Shō: a word with marks is never common English (review 10, L4)
    b = ''.join(ch for ch in d if not unicodedata.combining(ch))
    if b in DYNASTIES: return False                                       # Song gaoseng zhuan, Tang huiyao
    return b in _COMMON or b in EN_PEOPLE

_LIST = None
def wordlist():
    global _LIST
    if _LIST is None:
        with open(WORDLIST, encoding='utf-8') as f: _LIST = frozenset(w.strip() for w in f if w.strip())
    return _LIST

def list_sha256():
    with open(WORDLIST, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()

def fold(w):
    """Lower case, ligatures split (NFKC), marks and the ʻokina (and its look-alikes) removed: lūʻau → luau."""
    w = unicodedata.normalize('NFKC', w).lower()
    w = ''.join(ch for ch in unicodedata.normalize('NFD', w) if not unicodedata.combining(ch))
    return re.sub(r"[ʻ‘’'`]", '', w) if ocrwords.hawaiian_shape(w) else w.replace('’', "'")

def in_english(word):
    """True when the word, or every part of it between hyphens, is in the English list (marks folded)."""
    L = wordlist(); w = fold(word)
    if w in L or w.replace("'", '') in L or unicodedata.normalize('NFC', word).lower() in L: return True    # café is listed with its accent
    parts = [p for p in re.split(r"[-‐‑]", w) if p]
    return len(parts) > 1 and all(p in L for p in parts)

class LineIndex:
    """A page's visible characters sorted by their vertical midpoint (review 06, L1): near(ref) gives the characters whose
    midpoint lies within half an em of ref's, a superset of those line_end's same-line test accepts, so line_end reads
    two lines instead of the page and decides exactly as it does on the page's characters."""
    def __init__(self, chars):
        vis = sorted(((c['top'] + c['bottom']) / 2, i, c) for i, c in enumerate(chars) if c['text'].strip())
        self.mids, self.chars = [v[0] for v in vis], [v[2] for v in vis]
    def near(self, *refs):
        out = []
        for r in refs:
            if not r: continue
            mid, h = (r['top'] + r['bottom']) / 2, _em(r) / 2 + 1e-6          # a hair wider: line_end's own test decides
            out += self.chars[bisect.bisect_left(self.mids, mid - h):bisect.bisect_right(self.mids, mid + h)]
        return out

def _em(c): return max(float(c.get('size') or 0), float(c['bottom']) - float(c['top']), 1.0)

def line_end(hy, first, chars):
    """#140 (review 04, H1): True when a hyphen ends its line and the word joined to it starts its own: (a) no visible
    character to the hyphen's right on its line within one em (the hyphen's font size), measured from its right edge;
    (b) no visible character to the left of the joined word's first character on its line within one em. A mid-line
    compound whose second part comes later in content order ("homes-abroad" with "are" from the next line next; "non-
    Western" or "neo- Tahiti" with a wide gap) fails (a); a word inside its line fails (b). hy: the hyphen's char (None:
    False); first: the joined word's first char; chars: the page's characters."""
    if not hy or not first or hy.get('text') not in HYPHENS: return False
    em = _em
    def same_line(c, ref): return abs((c['top'] + c['bottom']) / 2 - (ref['top'] + ref['bottom']) / 2) <= em(ref) / 2
    for c in chars:
        if c is hy or c is first or not c['text'].strip(): continue
        # (a) anything that reaches right of the hyphen, a letter kerned under it included (review 06, M1: the "W" of
        # "non-Western" starts 0.9 pt inside the hyphen's right edge); (b) the mirror on the joined word's line
        if same_line(c, hy) and c['x1'] > hy['x1'] + 0.5 and c['x0'] - hy['x1'] < em(hy): return False
        if same_line(c, first) and c['x0'] < first['x0'] - 0.5 and first['x0'] - c['x1'] < em(first): return False
    return True

PLAIN_HALF = re.compile(r'[A-Za-z]{3,}')
def hyphen_english(a, b):
    """#140 (hyphen at a line end): a word broken at a line end at its own hyphen ("long-" / "standing") is English when the
    form with the hyphen is (in_english: every part between hyphens is listed), as well as when the form without it is
    ("infor-" / "mation", checked by classify). Only halves of three or more plain letters count, and never a word whose
    joined form has a romanized shape (Hepburn or pinyin syllables): a romanized word split into syllables that happen to be
    English ("keg-" / "are" for kegare, "ship-" / "pei" for shippei) or carrying marks ("Kō-" / "dan") stays a candidate."""
    if not (PLAIN_HALF.fullmatch(a or '') and PLAIN_HALF.fullmatch(b or '')): return False
    w = (a + b).lower()
    if romanized_shape(w) or romanized_shape(GEMINATE.sub(r'\1', w.replace('tch', 'ch'))): return False   # shippei, gakkō, kitte
    return in_english(f'{a}-{b}')
GEMINATE = re.compile(r'([kgsztdbpfhmr])\1')         # Hepburn's doubled consonant (a small tsu), read as one for the shape test

def other_script(t):
    return next((n for n, rx in SCRIPTS if rx.search(t)), None)

def classify(core, italic=False):
    """The classes of one Latin or other-script word (CJK is found per stretch, not here). [] when it is no candidate."""
    if not core: return []
    s = other_script(core)
    if s: return [f'script:{s}']
    letters = sum(1 for ch in core if ch.isalpha())
    if not LATIN.search(core) or letters < 2 or NUMERAL.fullmatch(core): return []
    if ocrwords.URL.search(core) or core.lower() in ('http', 'https', 'www', 'doi'): return []
    if in_english(core): return []
    cls = []
    shape = ocrwords.hawaiian_shape(core)
    okina = ocrwords.OKINA in core or ocrwords.okina_lookalike(core)
    if shape and (okina or HAW_MARK.search(core)): cls.append('hawaiian')
    elif ROMAN.search(core): cls.append('marks')
    elif ACCENTED.search(core): cls.append('accented')
    if shape and 'hawaiian' not in cls and letters >= 4 and core[:1].islower(): cls.append('hawaiian')
    if not cls and letters >= 4 and core[:1].islower() and not core.isupper(): cls.append('unknown')
    return cls

def _is_cjk(t): return bool(t) and bool(scripts.CJK.search(t))

def _pieces(word):
    """A word's characters cut at dashes, slashes and quotes, and where CJK meets Latin."""
    cur, prev_cjk = [], None
    for c in word:
        t = c['text']
        if t in CUT:
            if cur: yield cur
            cur, prev_cjk = [], None; continue
        cj = _is_cjk(t)
        if cur and prev_cjk is not None and cj != prev_cjk:
            yield cur; cur = []
        cur.append(c); prev_cjk = cj
    if cur: yield cur

def _core_span(cs):
    """(i0, i1) of the word's core within its characters: punctuation around it trimmed, a possessive 's dropped."""
    i0, i1 = 0, len(cs) - 1
    while i0 <= i1 and not (cs[i0]['text'][:1].isalnum()): i0 += 1
    while i1 >= i0 and not (cs[i1]['text'][-1:].isalnum()): i1 -= 1
    if i1 - i0 >= 2 and cs[i1]['text'] in ('s', 'S') and cs[i1 - 1]['text'] in "’'": i1 -= 2
    return i0, i1

def page_places(pno, chars, page_chars=None, italic=None, doc_lang=None, spoken=None, grow=False, keep=None, removed=None, info=None, words0=None, extra=(),
                adjacent=None, can_map=None):
    """chars: one page's pdfplumber characters in content order (plpages). Returns (places, words): the page's candidate
    places, and the page's words in reading order (for context: each place names its words by index). keep: joined
    spellings (lower case) the hyphen check must not take for English, because the book prints them whole (#140, book());
    removed: a list the caller supplies, to which the spellings the hyphen check took for English are appended."""
    italic = italic or (lambda fn: bool(ITALIC.search((fn or '').split('+')[-1])))
    cjk_doc = scripts.primary(doc_lang) in scripts.CJK_DOC          # a Chinese, Japanese or Korean document
    idx, runs = {}, collections.defaultdict(list)           # id(char) -> (mcid, index in its run); mcid -> chars
    for c in chars:
        m = c.get('mcid')
        if m is None: continue
        idx[id(c)] = (m, len(runs[m])); runs[m].append(c)
    pc = (lambda _p: chars) if page_chars is None else page_chars
    # 1. words, in order; each with its run, its index range and its text
    words = []
    for w0 in (ocrwords.words(chars, pc) if words0 is None else words0):   # words0: lib/langjoin read them already (the same chars)
        ps = list(_pieces(w0))
        pos = {id(c): k for k, c in enumerate(w0)}
        if not ps: words.append({'chars': [], 'text': '', 'all': ''.join(c['text'] for c in w0), 'mcid': None}); continue
        prev = -1
        for n_, w in enumerate(ps):
            end = pos[id(w[-1])] if n_ < len(ps) - 1 else len(w0) - 1
            shown = ''.join(c['text'] for c in w0[prev + 1:end + 1]); prev = end      # the cut characters stay in the context
            i0, i1 = _core_span(w)
            core = ''.join(c['text'] for c in w[i0:i1 + 1]) if i0 <= i1 else ''
            ms = {idx[id(c)][0] for c in w[i0:i1 + 1]} if core else set()
            words.append({'chars': w[i0:i1 + 1] if core else [], 'text': unicodedata.normalize('NFC', core),
                          'all': shown, 'mcid': next(iter(ms)) if len(ms) == 1 else None, 'tail': w0[end]})   # tail: a hyphen's char (#140)
    # 1b. scanned books (review 02, M5): the text a screen reader speaks, where the OCR text was given a reading. spoken =
    #     {'forms': {OCR form: reading}} (the work order's ocr_words) and/or {'reading': the page's AI reading} (page_readings,
    #     paired word by word as apply.py pairs them). The reading decides the class and the form; the place stays the OCR
    #     characters (the indexes), so the tag lands where apply.py put the reading.
    if spoken:
        forms_ = spoken.get('forms') or {}
        for w in words:
            if w['text'] in forms_: w['spoken'] = unicodedata.normalize('NFC', forms_[w['text']])
        if spoken.get('reading'):
            from lib import pagereads
            text, _ = pagereads.okina_slip(spoken['reading'])
            ai = [c for c in (re.match(r'^\W*(.*?)\W*$', t, re.S).group(1) for t in text.split()) if c]
            idx_ = [k for k, w in enumerate(words) if w['text']]
            changes, _ = pagereads.align([words[k]['text'] for k in idx_], ai)
            for i_, r in changes.items(): words[idx_[i_]]['spoken'] = r
        for w in words:
            if 'spoken' in w:
                w['printed'] = w['text']; w['all'] = w['all'].replace(w['text'], w['spoken'], 1) if w['text'] else w['all']; w['text'] = w['spoken']
    # 2. rejoin a word broken by a hyphen at a line end, for the list check only: only at a real line end (line_end), or
    #    when the rejoined word is English (a real break the line-end test misjudges: "prac-" / "tices" beside a drop cap or
    #    a narrow gutter). A hyphen inside its line whose second part the PDF draws later in content order is no join
    #    (#140, review 06/08): each half stays a word of its own, as an unbroken word
    lines = None                                         # the page's characters by line, made at the first join (review 06, L1)
    for a, b in zip(words, words[1:]):
        if a['all'][-1:] in HYPHENS and a['chars'] and b['chars'] and abs(a['chars'][-1]['top'] - b['chars'][0]['top']) > 3 \
                and b['text'][:1].islower():
            lines = lines or LineIndex(chars)
            le = line_end(a.get('tail'), b['chars'][0], lines.near(a.get('tail'), b['chars'][0]))
            if not le and not in_english(a['text'] + b['text']): continue
            a['joined'] = b['joined_from'] = a['text'] + b['text']
            a['hy_to'] = b
            a['line_end'] = le                       # #140: only then is the second half a place
    # 2b. #136 (its comment, the continuation rule; measured, off unless `extra` names it): a hyphen inside its line whose
    #     right neighbour letter touches it (within a quarter em, on the same line) has its real continuation there, drawn
    #     elsewhere in content order: the hyphenated word is classified whole ("na-" + "akwa"); English as a whole
    #     ("para-military"), its first part is no candidate. The continuation word is a second place of the same form.
    if 'continuation' in extra:
        first_of_word = {id(w['chars'][0]): w for w in words if w['chars']}
        for a in words:
            hy = a.get('tail')
            if not hy or hy.get('text') not in HYPHENS or not a['chars'] or 'hy_to' in a or 'joined_from' in a: continue
            lines = lines or LineIndex(chars)
            em_ = _em(hy); mid = (hy['top'] + hy['bottom']) / 2
            near = [c for c in lines.near(hy) if c is not hy and abs((c['top'] + c['bottom']) / 2 - mid) <= em_ / 2
                    and -0.05 * em_ <= c['x0'] - hy['x1'] <= 0.25 * em_ and c['text'][:1].isalpha()]
            b = next((first_of_word[id(c)] for c in sorted(near, key=lambda c: c['x0']) if id(c) in first_of_word), None)
            if b is None or b is a or 'joined_from' in b or 'hy_to' in b or not b['text']: continue
            whole = a['text'] + b['text']               # English joined either way ("para-" + "military"): no candidate
            a['joined'] = b['joined_from'] = whole if in_english(whole) else a['text'] + '-' + b['text']
            a['hy_to'] = b; a['line_end'] = True; a['src'] = 'continuation'
    # 3. classify Latin and other-script words
    for w in words:
        t = w['text']
        if not t or _is_cjk(t): w['cls'] = []; continue
        if 'joined_from' in w: w.setdefault('cls', []); continue       # the second half: classified with the first, on its turn (#140)
        form = w.get('joined', t)
        it = all(italic(c.get('fontname')) for c in w['chars'] if c['text'].strip())
        w['italic'] = it; w['cls'] = classify(form, it); w['form'] = form
        if not w['cls'] and extra and LATIN.search(form) and not NUMERAL.fullmatch(form) and not ocrwords.URL.search(form) \
                and not other_script(form) and not in_english(form):
            n_ = sum(1 for ch in form if ch.isalpha())
            if 'italic' in extra and it and n_ >= 2: w['cls'] = ['unknown']; w['src'] = 'italic'      # #136: italics, 2+ letters
            elif 'looser' in extra and n_ >= 3 and not form.isupper(): w['cls'] = ['unknown']; w['src'] = 'looser'   # #136: 3+, capitals too
        if w['cls'] and 'hy_to' in w and hyphen_english(t, w['hy_to']['text']):                   # "long-" / "standing" (#140)
            spelling = (t + w['hy_to']['text']).lower()
            if not (keep and spelling in keep):      # a spelling the book prints whole stays a candidate: madjoe, bumbye (#140)
                w['cls'] = []
                if removed is not None: removed.append(spelling)
        if cjk_doc and not w['cls'] and LATIN.search(form) and sum(ch.isalpha() for ch in form) >= 2 and not NUMERAL.fullmatch(form) \
                and not ocrwords.URL.search(form):
            w['cls'] = ['latin']                     # in a CJK document every Latin-script word is in another language (English, …)
        if w['cls'] and 'hy_to' in w:
            b = w['hy_to']; b['form'] = form; b['italic'] = it
            if w.get('line_end'):                    # #140 (review 04, H1): a genuine line break; else the join paired a mid-line
                b['cls'] = list(w['cls'])            # compound's first part with the next line's word: that word stays as on main
                b['half_cls'] = True                 # a candidate only through its first half (main gave it no classes)
    # a run of HAW_RUN or more Hawaiian-shape words of 2+ letters in one run (single vowels between them allowed: "E iho
    # ana o luna"), at least one of them not in the English list ("we make a home" stays English), is Hawaiian
    def hw(w): return bool(w['text']) and w['mcid'] is not None and not _is_cjk(w['text']) and ocrwords.hawaiian_shape(w['text'])
    def hv(w): return bool(w['text']) and w['mcid'] is not None and len(w['text']) == 1 and w['text'].lower() in ocrwords.HAW_VOWELS
    i = 0
    while i < len(words):
        if not hw(words[i]): i += 1; continue
        j = i
        while j + 1 < len(words) and words[j + 1]['mcid'] == words[i]['mcid'] and (hw(words[j + 1]) or hv(words[j + 1])): j += 1
        if j > i and i > 0 and hv(words[i - 1]) and words[i - 1]['mcid'] == words[i]['mcid']: i -= 1
        chain = words[i:j + 1]; real = [w for w in chain if hw(w)]
        if len(real) >= HAW_RUN and any(not in_english(w['text']) for w in real):
            for w in chain:
                if w.get('half_cls'): w['cls'] = []; w['half_cls'] = False     # #140: in a chain, a second half is a candidate of its own
                if 'hawaiian' not in w['cls']: w['cls'] = w['cls'] + ['hawaiian']; w.setdefault('form', w['text']); w.setdefault('italic', False)
        i = j + 1
    # 4. places: CJK stretches per run, then phrases of candidate words
    places = []
    def place(m, f, l, cls, form, it, wi):
        cs = runs[m]
        text = ''.join(c['text'] for c in cs[f:l + 1])
        rest = ''.join(c['text'] for k, c in enumerate(cs) if k < f or k > l)
        places.append({'page': pno, 'mcid': m, 'first': f, 'last': l, 'n': len(cs), 'text': text, 'form': form,
                       'class': sorted(set(cls)), 'italic': it, 'whole': not re.search(r'[^\W_]', rest),
                       'w0': wi[0], 'w1': wi[1]})
        src = sorted({x['src'] for x in words[wi[0]:wi[1] + 1] if x.get('src')}) if wi[0] is not None else []
        if src: places[-1]['source'] = src
    # word index of each character, for context
    wix = {}
    for k, w in enumerate(words):
        for c in w['chars']: wix[id(c)] = k
    def letter(t): return scripts.kind(t) is not None                  # kana, hangul or a Chinese character
    for m, cs in runs.items():
        k = 0
        while k < len(cs):
            if not letter(cs[k]['text']): k += 1; continue
            j = k
            while j + 1 < len(cs) and (_is_cjk(cs[j + 1]['text']) or (cs[j + 1]['text'].isspace() and j + 2 < len(cs) and _is_cjk(cs[j + 2]['text']))):
                j += 1
            l = j
            while l > k and not letter(cs[l]['text']): l -= 1                    # trailing CJK punctuation stays outside
            text = ''.join(c['text'] for c in cs[k:l + 1])
            kd = scripts.kind(text)
            if cjk_doc and scripts.action(kd, text, doc_lang)[0] == 'inherit': k = j + 1; continue   # the document's own language
            ws = [wix[id(c)] for c in cs[k:l + 1] if id(c) in wix]
            place(m, k, l, [f'cjk:{"mixed" if kd == "mixed_with_latin" else kd}'], re.sub(r'\s+', '', text), False,
                  (min(ws), max(ws)) if ws else (None, None))
            k = j + 1
    def latin_word(x): return bool(x['text']) and x['mcid'] is not None and bool(LATIN.search(x['text'])) and not _is_cjk(x['text'])
    def quoted_inside(n):
        """Word n is inside a quoted span and is not its closing word (review 24 §7.3): the span runs from a word opening
        with “ " « to the first word after it carrying ” " » (before any , . ; :), within QUOTE_WINDOW words. The closing
        word's own mark still ends a phrase; an opening with no close in the window is no span; ’ never counts (kan’yō)."""
        def opens(x): return words[x]['all'].lstrip()[:1] in QUOTE_OPEN
        def closes(x): return words[x]['all'].rstrip(' ,.;:')[-1:] in QUOTE_CLOSE
        if closes(n): return False
        for a in range(n, max(-1, n - QUOTE_WINDOW), -1):
            if a < n and closes(a): return False          # a span closed before n
            if opens(a): return any(closes(b) for b in range(n + 1, min(len(words), a + QUOTE_WINDOW)))
        return False
    def phrase_end(n):
        return 0 <= n < len(words) and bool(PHRASE_END.search(words[n]['all']) or period_end(words[n]['all'])) and not quoted_inside(n)
    def is_italic(x): return bool(x['chars']) and all(italic(c.get('fontname')) for c in x['chars'] if c['text'].strip())
    def form_cls(grp):
        form = ' '.join(x.get('form', x['text']) for n_, x in enumerate(grp)
                        if (n_ == 0 or 'joined_from' not in x) and (x.get('form') or x['text']))   # a rejoined half once; a slash never
        return form, [c for x in grp for c in x['cls']]
    def candidate(x): return bool(set(x.get('cls') or []) - {'title'})   # a class of its own, not only growth's
    def run_pieces(k0, j0):
        """Words k0..j0 in stretches of one run each (a word with no characters stays with the stretch it is in):
        [((first, last), words)] for the stretches that hold a candidate."""
        out_, cur, cur_m = [], [], None
        for n_ in range(k0, j0 + 1):
            x = words[n_]
            m_ = idx[id(x['chars'][0])][0] if x['chars'] else cur_m
            if cur and m_ != cur_m: out_.append(cur); cur = []
            cur.append(n_); cur_m = m_
        if cur: out_.append(cur)
        return [((ns[0], ns[-1]), [words[n_] for n_ in ns]) for ns in out_ if any(candidate(words[n_]) for n_ in ns)]
    def pieces_of(wi, first_m):
        for (a, b), piece in run_pieces(wi[0], wi[1]):
            emit(piece, (a, b), *form_cls(piece), first_m if a == wi[0] else None)
    def emit(grp, wi, form, cls, first_m=None):
        """One place for the phrase grp (words wi[0]..wi[1]): `segments` when growth went on into another run of the
        element (proposal 20 (b)), [run, first, last] per run in reading order. A run that comes back after another
        (interleaved MCIDs) can't be one place: each stretch of one run that holds a candidate is a place of its own
        (review 24 §5), as Reading.map refuses a repeated run."""
        segs = []
        for x in grp:
            for c in x['chars']:
                m_, k_ = idx[id(c)]
                if segs and segs[-1][0] == m_: segs[-1][2] = k_
                elif not segs or m_ not in {s[0] for s in segs}: segs.append([m_, k_, k_])
                else:                                # the run again: one place per stretch of one run
                    return pieces_of(wi, first_m)
        if len(segs) > 1 and can_map is not None and not can_map(segs):   # a joined page's stretches that don't map to the
            return pieces_of(wi, first_m)                                  # PDF's runs (review 24, L4): one place per stretch
        it = all(x.get('italic') for x in grp if x['text'])
        place(segs[0][0], segs[0][1], segs[-1][2] if len(segs) == 1 else segs[0][2], cls, form, it, wi)
        if len(segs) > 1:
            places[-1].update(segments=segs, text=''.join(c['text'] for s in segs for c in runs[s[0]][s[1]:s[2] + 1]), whole=False,
                              source=sorted(set(places[-1].get('source') or []) | {'grow'}))
        if first_m is not None: places[-1].update(_first_mcid=first_m, half=True)   # step 5: its first half's run may become a passage;
                                                                                    # half: lib/langreq.forms numbers forms by their other places
    k, last_end = 0, -1
    while k < len(words):
        w = words[k]
        if not w.get('cls') or w['mcid'] is None: k += 1; continue
        j = k
        while j + 1 < len(words) and words[j + 1].get('cls') and words[j + 1]['mcid'] == w['mcid'] and not words[j].get('half_cls') \
                and not phrase_end(j):           # a phrase ends at the second half of a broken word (#140): its form stays the first half's;
            j += 1                               # and at a comma or semicolon (L3)
        if grow:                                     # a title's whole extent (review 06, M4): the voice switches once, not mid-title
            m0 = w['mcid']
            def slash(i): return 0 <= i < len(words) and words[i]['all'].strip() == '/'
            def in_run(i, step):
                """Word i is in the title's run, or growth may go on into its run (proposal 20 (b)): the next run of the
                same element (`adjacent`, from the tag tree; italic titles only, step ≠ 0), entered at a clean break: the
                earlier word doesn't end a phrase (. , ; : ! ? or a closing bracket or quote) and the later one doesn't
                open one. Two titles one after the other ("Kokinshū, Shinkokinshū") stay two. Adjacency is asked of the
                run of the word before, in growth's direction (proposal 23 §3), so a title over three lines grows from a
                seed in any of them."""
                m = words[i]['mcid']
                if m == m0: return True
                if adjacent is None or m is None or step == 0: return False
                p = i - step
                while slash(p): p -= step
                if not 0 <= p < len(words): return False
                if words[p]['mcid'] == m: return True               # already inside the next run
                if words[p]['mcid'] is None or not adjacent(words[p]['mcid'], m): return False   # chained from the run before
                a, b = (words[p], words[i]) if step > 0 else (words[i], words[p])   # a: the earlier in reading order
                return not RUN_END.search(a['all']) and not RUN_OPEN.match(b['all'])
            def same(i, step=0):
                """Word i may join the title: Latin script, in this run, after the last place, and not English (a short
                particle such as no, to, wa only with a word that is not English beyond it: "Nihon no kenkyū", never "of the").
                A spaced " / " (a verse line's break: "tamayura no / tsuyu mo namida mo") is transparent: it joins when the
                word beyond it joins, and a particle before it looks past it (#136, report 16 §5)."""
                if 0 <= i < len(words) and i > last_end and slash(i):   # a lone slash may carry no run of its own: the
                    return True if step == 0 else same(i + step, step)   # word beyond it must be in this run
                if not (0 <= i < len(words) and i > last_end and in_run(i, step) and latin_word(words[i])): return False
                if step:                                 # L3: no step over a comma or semicolon, on the earlier word of the pair in
                    q = i - step                          # reading order (and at a slash, on each word it crosses)
                    while slash(q): q -= step
                    lo, hi = (q, i) if step > 0 else (i, q)
                    if any(phrase_end(n_) for n_ in range(max(lo, 0), hi)): return False
                    if 0 <= lo and words[lo].get('hy_to') is words[hi]: return False   # never across a line-end hyphen join:
                                                  # its two halves are two places of one form (#140); one place over both
                                                  # would hold the hyphen between its pieces, which apply.py refuses
                t = words[i]['text']
                if t.lower() in GROW_STOP: return False                  # #136's narrower rule: "Tsurezuregusa of Kenkō", "… or …"
                for n_ in (i - 1, i + 1):                               # a piece of an English word the PDF draws apart ("Se lections",
                    if 0 <= n_ < len(words) and words[n_]['text'] and t.isalpha() and words[n_]['text'].isalpha():   # "Japa nese")
                        if in_english(words[n_]['text'] + t if n_ < i else t + words[n_]['text']) and not (in_english(t) and in_english(words[n_]['text'])): return False
                if not in_english(t) or (t[:1].isupper() and romanized_shape(t) and not common_romanized(t)): return True
                nx = i + step                                           # the word beyond, past any slash
                while slash(nx): nx += step
                return step != 0 and len(t) <= 2 and t.islower() and 0 <= nx < len(words) and same(nx, step) and not in_english(words[nx]['text'])
            if all(is_italic(x) for x in words[k:j + 1]):                    # the italic run
                while same(k - 1, -1) and (is_italic(words[k - 1]) or slash(k - 1)): k -= 1   # a slash is often set in roman
                while same(j + 1, 1) and (is_italic(words[j + 1]) or slash(j + 1)): j += 1
            else:
                a = next((i for i in range(k, max(last_end, k - 10), -1) if words[i]['all'].lstrip()[:1] in '“"«'), None)   # inside quotes
                b = next((i for i in range(j, min(len(words), j + 10)) if words[i]['all'].rstrip(' ,.;:')[-1:] in '”"»'), None)
                if a is not None and b is not None and all(same(i) or k <= i <= j for i in range(a, b + 1)): k, j = a, b
                elif j + 1 < len(words) and words[j + 1]['text'] and _is_cjk(words[j + 1]['text']):    # the romanized words before a Han gloss
                    while same(k - 1, -1) and len(words[k:j + 1]) < 8 and words[k - 1]['all'].rstrip()[-1:] not in '.;:,)':
                        k -= 1
            while k < j and slash(j): j -= 1                             # a title never starts or ends on a slash
            while k < j and slash(k): k += 1
            for n_ in range(k, j + 1):
                x = words[n_]
                if not x.get('cls') and not slash(n_): x['cls'] = ['title']; x.setdefault('form', x['text']); x.setdefault('italic', is_italic(x))
        last_end = j
        grp = words[k:j + 1]
        form, cls = form_cls(grp)
        if grp[0].get('half_cls') and not grp[0].get('phrase'):     # its first half has no place (drawn across two runs: no mcid):
            k = j + 1; continue                                     # neither has, as before #140, never half a word tagged
        first_m = None
        if grp[0].get('half_cls'): form, cls, first_m = grp[0]['phrase']   # a second half in its own run: its first half's
        if grp[-1].get('hy_to', {}).get('half_cls'): grp[-1]['hy_to']['phrase'] = (form, cls, grp[-1]['mcid'])    # form and classes (#140): one form, two places
        emit(grp, (k, j), form, cls, first_m)
        k = j + 1
    def pieces_outside(k0, j0, passage):
        """The stretches of words k0..j0 outside the passages' runs that hold a candidate (a word with a class of its own,
        not only growth's `title`: review 24, L1): [((first, last), words)], slashes trimmed at their ends. A grown word
        at a kept stretch's edge stays in it (cadaverous PDF 311's "ra mokuroku")."""
        out_, cur = [], []
        for n_ in range(k0, j0 + 1):
            x = words[n_]
            if x['mcid'] is not None and x['mcid'] in passage:
                if cur: out_.append(cur); cur = []
                continue
            cur.append(n_)
        if cur: out_.append(cur)
        res = []
        for ns in out_:
            while ns and (words[ns[0]]['all'].strip() == '/' or not words[ns[0]]['chars']): ns = ns[1:]
            while ns and (words[ns[-1]]['all'].strip() == '/' or not words[ns[-1]]['chars']): ns = ns[:-1]
            if ns and any(candidate(words[n_]) for n_ in ns): res.append(((ns[0], ns[-1]), [words[n_] for n_ in ns]))
        return res
    # 5. passages: a run where most words are candidates becomes one place for the whole run
    by_run = collections.defaultdict(list)
    for k, w in enumerate(words):
        if w['mcid'] is not None and w['text'] and LATIN.search(w['text']) and sum(ch.isalpha() for ch in w['text']) >= 2: by_run[w['mcid']].append(w)
    out = []
    passage = set()
    for m, ws in by_run.items():
        cand = sum(1 for w in ws if w.get('cls') and not w.get('half_cls'))   # #140: a second half counts only on its own
        if len(ws) >= PASSAGE_MIN and cand / len(ws) >= PASSAGE_SHARE:
            passage.add(m)
    pas = {}
    for m in sorted(passage):
        cs = runs[m]; ws = by_run[m]
        f = idx[id(ws[0]['chars'][0])][1]; l = idx[id(ws[-1]['chars'][-1])][1]
        cls = sorted({c for w in ws if not w.get('half_cls') for c in w.get('cls', [])}) or ['unknown']
        wi = [wix[id(w['chars'][0])] for w in ws if w['chars'] and id(w['chars'][0]) in wix]
        pas[m] = ({'page': pno, 'mcid': m, 'first': f, 'last': l, 'n': len(cs), 'text': ''.join(c['text'] for c in cs[f:l + 1]),
                    'form': ' '.join(w.get('form', w['text']) for w in ws), 'class': ['passage'] + cls,
                    'italic': all(w.get('italic') for w in ws if w.get('cls') and not w.get('half_cls')),
                    'whole': not re.search(r'[^\W_]', ''.join(c['text'] for k_, c in enumerate(cs) if k_ < f or k_ > l)),
                    'w0': min(wi) if wi else None, 'w1': max(wi) if wi else None})
    for p in list(places):
        fm = p.pop('_first_mcid', None)
        if p.get('segments') and any(s[0] in passage for s in p['segments']):
            # a title grown into a passage's run (review 22, M1): the passage holds its words there, and each stretch of its
            # words outside the passage that holds a candidate is a place of its own
            n0 = len(places)
            for piece in pieces_outside(p['w0'], p['w1'], passage): emit(piece[1], piece[0], *form_cls(piece[1]))
            for q in places[n0:]: q.pop('_first_mcid', None); out.append(q)
            del places[n0:]
            continue
        if p['mcid'] in passage and not p['class'][0].startswith('cjk:'): continue
        if fm in pas: p['form'], p['class'] = pas[fm]['form'], list(pas[fm]['class'])   # #140: a second half of a passage's last word
        out.append(p)
    out += [pas[m] for m in sorted(pas)]
    out.sort(key=lambda p: (p['mcid'], p['first']))
    if info is not None: info['words'] = words           # book(): words read whole across runs that got no place (#161)
    return out, [w['all'] for w in words]

_TOKEN = re.compile(r"[^\W\d_](?:[^\W\d_]|['’ʻ‘])*[^\W\d_]|[^\W\d_]")
def whole_spellings(words):
    """The spellings a book prints whole (#140): every word-shaped token, lower case, of its pages' words ({page: [word
    as shown]}) that doesn't end in a hyphen (a line-end break is not a printed-whole spelling). Tokens inside URLs and
    bibliography entries count too ("www.smalltown…" for "smalltown"): at worst an English compound broken at a line end
    stays a candidate, a place of a form the language step calls English."""
    out = set()
    for ws in words.values():
        for w in ws:
            if w.rstrip()[-1:] in HYPHENS: continue
            out.update(x.lower() for x in _TOKEN.findall(w))
    return out

RULES = ('join', 'inrun', 'cross')              # lib/langjoin: #150's join, #161's in-run and cross-run joins (all on)
RULE_NAMES = RULES + ('grow', 'looser', 'italic', 'continuation')   # #136's three, measured; italic is on by default
DEFAULT_RULES = RULES + ('italic',)             # the finder's default (audit.py, the language step, book(rules=None)):
                                                # italic on by default (Patrick, 2026-11-21; report 21 §4: 46% tagged)

def rules_from_env(value=None, grow=None):
    """LANG_FINDER_RULES (measurement only, never from the app): '-inrun,-italic' turns rules off, 'join' alone lists
    them. grow: LANG_GROW's answer (None: off). Returns (rules, note) where note names a non-default setting, else ''."""
    v = (os.environ.get('LANG_FINDER_RULES', '') if value is None else value).strip()
    rules = set(DEFAULT_RULES)
    if v:
        items = [x.strip() for x in v.split(',') if x.strip()]
        if all(x.startswith('-') for x in items): rules -= {x[1:] for x in items}
        else: rules = {x for x in items if x in RULE_NAMES}
    if grow: rules.add('grow')
    return rules, (f'LANG_FINDER_RULES={v}' if v else '')

def book(PL, pages=None, doc_lang=None, spoken=None, grow=False, pdf=None, rules=None):
    """Every page's places, the page word lists (for context), and counts. PL: plpages.Pages. doc_lang: the document's
    language (its /Lang, or the work order's): in a Chinese, Japanese or Korean document, Latin-script words are
    candidates ('latin') and CJK text in the document's own language is not. spoken: {'forms': {OCR form: reading},
    'pages': {page: reading}} for a scanned book's readings (M5), else None.
    pdf: the open pikepdf.Pdf, for the tag tree the joins need (#150, #161; lib/langjoin). Without it, or with a ParentTree
    that can't be read, no run is joined to another (today's reading); the in-run join (#161 A) still runs. rules: the
    set of rules on (DEFAULT_RULES; None: the default, as audit.py runs them). `reading` in the result records what was applied.
    Two passes (#140, the printed-whole check): a word broken at a line end that the hyphen check would take for English
    ("mad-" + "joe") stays a candidate when the book prints the joined spelling whole elsewhere (madjoe). Pass 1 reads
    every page and collects the spellings the check removed; the book's whole spellings are the word-shaped tokens of its
    pages' words that don't end in a hyphen (whole_spellings: URLs and bibliography entries count); pass 2 reads again
    only the pages with a removed spelling the book prints whole. With pages=…, the whole spellings come from those pages
    only. Places from a joined reading carry `source` (join, inrun, cross) and, when they span runs, `segments`."""
    from lib import langjoin, gaptext, latinlist
    asked = sorted(set(DEFAULT_RULES if rules is None else rules) | ({'grow'} if grow else set()))
    rules = set(DEFAULT_RULES if rules is None else rules)
    grow = grow or 'grow' in rules
    extra = rules & {'looser', 'italic', 'continuation'}
    rules -= {'grow', 'looser', 'italic', 'continuation'}
    struct = langjoin.Structure(pdf if rules & {'join', 'cross'} or grow else None)   # growth reads it too (proposal 20 (b))
    if not struct.ok: rules -= {'join', 'cross'}
    C = collections.Counter()
    unplaced = []
    def read(pno, pg, keep=None, removed=None, collect=False):
        if struct.ok: struct.use_streams(pno, pg.chars)   # #166: each run's owner by the stream that draws it
        R = langjoin.reading(pno, pg.chars, struct, rules) if rules else None
        chars = R.chars if R else pg.chars
        info = {}
        adj = None                                   # growth into the adjacent run (proposal 20 (b)); on a joined page across
        if grow and struct.ok and R is None:         # stretches (H1 (a), review 24 §6.1): one rule for every reading
            runs_ = collections.defaultdict(list); first_at = {}
            for i_, c in enumerate(pg.chars):
                m_ = c.get('mcid')
                if m_ is not None: runs_[m_].append(c); first_at.setdefault(m_, i_)
            def adj(a, b, _p=pno, _r=runs_, _f=first_at):
                if not struct.adjacent(_p, a, b): return False
                x, y = sorted((a, b), key=lambda m_: _f.get(m_, 0))
                return langjoin.run_break_ok(_r.get(x) or [], _r.get(y) or [])
        elif grow and struct.ok:
            adj = lambda a, b, _R=R: _R.adjacent(struct, a, b)
        places, words_ = page_places(pno, chars, lambda p, _c=chars: _c, doc_lang=doc_lang, grow=grow, keep=keep, removed=removed, info=info,
                                     words0=R.words if R else None, extra=extra, adjacent=adj,
                                     can_map=(lambda segs, _R=R: _R.can_map(segs, struct)) if R else (lambda segs, _r=runs_, _p=pno: langjoin.pieces_fill(_r, segs)
                                              and struct.in_order(_p, segs, {m_: ''.join(c['text'] for c in cs_) for m_, cs_ in _r.items()})) if adj else None,
                                     spoken={'forms': (spoken or {}).get('forms') or {}, 'reading': ((spoken or {}).get('pages') or {}).get(pno)} if spoken else None)
        if R:
            gaptext._LINES.pop(id(chars), None)
            places = [q for q in (R.map(p) for p in places) if q is not None]
            if collect:
                for w in info.get('words') or []:
                    if not w.get('chars') or w.get('mcid') is not None or not w.get('cls'): continue
                    why = next((R.unplaced_keys[id(c)] for c in w['chars'] if id(c) in R.unplaced_keys), None)
                    if why is None or why == 'cross_off' or not classify(w.get('form') or w['text'], w.get('italic', False)): continue
                    ms = sorted({c['_m'] for c in w['chars'] if c.get('_m') is not None})
                    unplaced.append({'page': pno, 'form': w.get('form') or w['text'], 'reason': why, 'mcids': ms})
        for p in places:
            if grow and 'title' in p['class']: p['source'] = sorted(set(p.get('source') or []) | {'grow'})
            p.update(latinlist.mark(p, words_))   # the review page's dictionary marks, from the words this reading made (review 15, M1)
        return places, words_
    by_page, words, gone = {}, {}, {}
    for pno, pg in enumerate(PL.pages, 1):
        if pages and pno not in pages: continue
        rm = []; by_page[pno], words[str(pno)] = read(pno, pg, removed=rm, collect=True)
        if rm: gone[pno] = set(rm)
    if gone:
        whole = whole_spellings(words)
        for pno, rm in gone.items():
            if rm & whole: by_page[pno], words[str(pno)] = read(pno, PL.pages[pno - 1], keep=rm & whole)
    allp = [p for pno in sorted(by_page) for p in by_page[pno]]
    forms = collections.defaultdict(set)
    for p in allp:
        for c in p['class']:
            C[c] += 1; C[f'{c}:{"whole" if p["whole"] else "split"}'] += 1; forms[c].add(p['form'])
    fp = hashlib.sha256(json.dumps(sorted((p['form'], p['class']) for p in allp), ensure_ascii=False).encode()).hexdigest()[:16]
    applied = sorted(rules | extra | ({'grow'} if grow else set()))
    return {'version': 2, 'document_lang': doc_lang or '', 'wordlist_sha256': list_sha256()[:16], 'fingerprint': fp, 'places': allp, 'words': words,
            'reading': {'rules': applied, 'asked': asked, 'parents': struct.status}, 'unplaced': unplaced,
            'stats': {'places': len(allp), 'by_class': dict(sorted(C.items())),
                      'forms': {k: len(v) for k, v in sorted(forms.items())}, 'unplaced': len(unplaced),
                      'segmented': sum(1 for p in allp if p.get('segments'))}}

def existing(pdf, PL, doc_lang, limit=300):
    """Language tags already in the PDF (a publisher's), on text not in the document's language: one place per run, its
    whole text, with `current` the value as written (fr-FR on an English copyright page, "Hawaiian", JA on Chinese). From
    the marks' /Lang in each page's content and from the /Lang of tag-tree elements over their own runs. pdf: pikepdf."""
    import pikepdf
    doc = scripts.primary(doc_lang)
    runs = collections.defaultdict(dict)
    for pno, pg in enumerate(PL.pages, 1):
        for c in pg.chars:
            if c.get('mcid') is not None: runs[pno].setdefault(c['mcid'], []).append(c['text'])
    found = {}
    pidx = {p.obj.objgen: i for i, p in enumerate(pdf.pages, 1)}
    from lib import langjoin
    forms_on = langjoin.single_use_forms(pdf)           # #165: a form drawn once, from this page, is read like the page;
    for pno, page in enumerate(pdf.pages, 1):          # a form drawn in several places is not (its runs are never tagged)
        page_ms = set()
        for obj in [page] + forms_on.get(pno, []):
            try:
                for x in pikepdf.parse_content_stream(obj, 'BDC'):
                    pr = x.operands[1] if len(x.operands) > 1 else None
                    if not (isinstance(pr, pikepdf.Dictionary) and '/MCID' in pr): continue
                    m = int(pr.MCID)
                    if obj is page: page_ms.add(m)
                    elif m in page_ms: continue        # a number the page itself draws: the page's run
                    if '/Lang' in pr and scripts.primary(str(pr.Lang)) != doc: found.setdefault((pno, m), str(pr.Lang))
            except Exception: pass
    st = pdf.Root.get('/StructTreeRoot')
    stack = [(k, None, ()) for k in (st.get('/K') if isinstance(st.get('/K'), pikepdf.Array) else [st.get('/K')])] if st is not None else []
    seen, chain = set(), {}                              # chain: (page, mcid) -> the /Lang of its owner and the owner's ancestors
    while stack and len(seen) < 200000:
        n, pg, up = stack.pop()
        if not isinstance(n, pikepdf.Dictionary) or n.objgen in seen: continue
        seen.add(n.objgen)
        pg = pidx.get(n.Pg.objgen) if '/Pg' in n else pg
        lang = str(n.get('/Lang', '')) if '/Lang' in n else None
        here = ((lang,) + up)[:8]                        # apply.py's remove_existing looks at the owner and 7 ancestors
        k = n.get('/K'); ks = list(k) if isinstance(k, pikepdf.Array) else ([k] if k is not None else [])
        for kid in ks:
            if isinstance(kid, int):
                if pg: chain.setdefault((pg, kid), here)
                if lang and scripts.primary(lang) != doc and pg: found.setdefault((pg, kid), lang)
            elif isinstance(kid, pikepdf.Dictionary):
                if str(kid.get('/Type')) == '/MCR' and '/MCID' in kid:   # a page MCR, or an /MCR … /Stm into a form (#165)
                    p_ = pidx.get(kid.Pg.objgen) if '/Pg' in kid else pg
                    if '/Stm' in kid and not any(f.objgen == kid.Stm.objgen for f in forms_on.get(p_, [])): continue   # a shared form
                    if p_: chain.setdefault((p_, int(kid.MCID)), here)
                    if lang and scripts.primary(lang) != doc and p_: found.setdefault((p_, int(kid.MCID)), lang)
                else: stack.append((kid, pg, here))
    out = []
    for (pno, m), cur in sorted(found.items()):
        cs = runs.get(pno, {}).get(m)
        if not cs or not ''.join(cs).strip(): continue
        # carried: an element over the run holds the value (apply.py tidies it there), or the marks alone (left as written)
        on_el = any(x is not None and x.strip() == cur.strip() for x in chain.get((pno, m), ()))
        out.append({'page': pno, 'mcid': m, 'first': 0, 'last': len(cs) - 1, 'n': len(cs), 'text': ''.join(cs), 'form': ''.join(cs).strip(),
                    'class': ['existing'], 'current': cur, 'carried': 'element' if on_el else 'marks', 'italic': False, 'whole': True, 'w0': None, 'w1': None})
        if len(out) >= limit: break
    return out
