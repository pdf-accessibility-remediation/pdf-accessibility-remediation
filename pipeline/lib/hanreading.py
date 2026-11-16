"""hanreading.py: the reading printed beside words in Chinese characters alone (kanji, hanzi, hanja), and what it proves
about their language (#123, #124). Local only: no model, no network.

    hanreading.reading_of(piece, subj, toned)      -> 'ja' | 'zh' | 'ko' | None: the language one piece beside the characters proves
    hanreading.beside(pw, w0, w1, subj, toned)     -> {index: language}: the reading directly beside a place
    hanreading.subject_of(places, words)           -> 'japan' | 'china' | 'korea' | None: the book's subject, from its readings
    hanreading.backmatter(digest)                  -> (pages, sections): {page: kinds} of glossaries, bibliographies and indexes
    hanreading.evidence(form, words, ...)          -> what the readings beside a form's places say
    hanreading.decide(forms, words, digest, ...)   -> ({form id: decision}, {form id: evidence}, stats)

A reading is kana or a Hepburn word (Japanese), a pinyin word (Chinese), or hangul, a McCune-Reischauer word with breves or
a Revised Romanization word in a book on Korea (Korean), printed directly before the characters (a piece of punctuation
alone may sit between), or kana or hangul directly after them. A romanization after the characters is never taken: in a
list it is the next entry's. These are the rules tools/lang_test.py used to make the language step's answer keys (round
15), moved here so the pipeline and the test tools share one copy. The pipeline adds one (strict): a word ending with a
colon, semicolon or period introduces the characters, never reads them.

The local rule (#123, strict form) decides a form without the AI only when every place of it has a reading beside it and
all of them name the same language. Every other form goes to the AI. The issue also asked to leave out glossary and
bibliography lines; measured on two books (2026-11-15), that cut the forms decided from 492 to 318 and from 18 to 0 while
the forms it left out were right, and the bibliography's real trap (a publisher's name before a title's characters,
"Tokyo: Kōdansha. 自然と文化…") is what the colon guard refuses. So no page is left out (Min, 2026-11-15).

The evidence of one form (#124) is the same reading, counted over its places outside bibliographies (a glossary's or an
index's reading counts there: a group approval needs the AI to name the same language too), plus kana in the same
phrase as the characters (大福もち, ご飯: the piece that holds them; #124 names it, #123's rule doesn't use it): its
language when every reading found names one language; None when there is none, or two (mixed).
"""
import re, collections, unicodedata
from lib import langcands, scripts

HEPBURN_ONLY = re.compile(r'[ōū]')
IAST = re.compile(r'[ṣṇṭḍśṛṃṅṁḥ]')
JA_SYL = re.compile(r"(?i)^(?:(?:ky|sh|ch|ts|ny|hy|my|ry|gy|by|py|j|[kgsztdnhbpmyrwf])?[aiueoāīūēō]|n(?![aiueoāīūēōy]))+$")
PINYIN = langcands.PINYIN_U          # the pinyin shape with üan, ün, üe, matched in linear time (CodeQL py/redos)
BREVE = re.compile(r'[ŏŭŎŬ]')        # McCune-Reischauer (Korean) and Wade-Giles (Chinese: tzŭ) use them
TONE = re.compile(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]')
TONE_OTHER = re.compile(r'[áǎàéěèíǐìóǒòúǔùǖǘǚǜ]')       # pinyin tones Hepburn never writes
HANGUL = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')
KANA_ = re.compile(r'[\u3040-\u30ff]')
RR = re.compile(r'(?i)eo|eu')        # Revised Romanization's vowels, never Hepburn's or pinyin's
PUNCT_ONLY = re.compile(r'^[\W_]+$')
TONED_MIN = 20                       # pieces with a pinyin tone mark Hepburn never writes: the book writes pinyin with tones
RULE = 'reading'                     # the one local rule (language_parts forms' `rule`)
CLASS = ['cjk:han_only']             # the forms the rule reads: Chinese characters alone

def toneless(w):
    """A pinyin word without its tone marks (ü kept): 'zhōngguó' → 'zhongguo'."""
    return unicodedata.normalize('NFC', ''.join(c for c in unicodedata.normalize('NFD', w) if not unicodedata.combining(c) or c == '\u0308'))

def latin_core(w): return re.sub(r"^\W+|\W+$", '', w)

def reading_of(w, subj, toned=False):
    """The language a piece beside a Han-only place proves, or None: kana or a Hepburn word (ja); pinyin (zh); hangul, a
    McCune-Reischauer word with breves, or a Revised Romanization word in a book on Korea (ko). A word with Hepburn
    macrons that also fits pinyin ("dōu", "soba-manjū") is Japanese, unless the book writes pinyin with tone marks
    (toned: then it is not decided); a romanization without marks proves zh only when it is long, not English and not
    Japanese in shape; breves prove ko only in a book on Korea (Wade-Giles uses them for Chinese)."""
    if KANA_.search(w): return 'ja'
    if HANGUL.search(w): return 'ko'
    c = latin_core(w); lw = c.lower(); bare = toneless(lw).replace("'", '').replace('’', '')
    if not c or not bare.replace('-', '').isalpha(): return None
    shape = bool(PINYIN.match(bare.replace('-', ''))); pin = shape and not langcands.in_english(lw)
    hep = bool(HEPBURN_ONLY.search(lw) and JA_SYL.match(lw.replace('-', '')) and not IAST.search(lw) and not TONE_OTHER.search(lw))
    if hep and shape: return None if toned else 'ja'
    if hep: return 'ja'
    if subj == 'korea' and (BREVE.search(c) and not TONE.search(c) or (RR.search(lw) and not langcands.in_english(lw) and len(lw) > 3)): return 'ko'
    if subj == 'korea': return None                 # McCune-Reischauer without breves looks like pinyin ("minyu bangbon")
    if pin and not BREVE.search(c) and (TONE_OTHER.search(lw) or (len(bare) > 3 and not JA_SYL.match(bare.replace('-', '')))): return 'zh'
    return None

INTRODUCES = re.compile(r'[:;.]["\u201d\u2019)\]]*$')   # a piece that ends a clause: what follows is quoted, not read

def beside(pw, w0, w1, subj, toned=False, strict=False):
    """{index: language} of the reading directly beside a place: the run of reading pieces that ends right before it
    (a piece of punctuation alone may sit between), else the kana or hangul right after it, at most 3 pieces. A
    reading two pieces away that belongs to a neighbouring entry (a glossary's "soju 소주 su 酥") is never taken.
    strict (the pipeline's, #123): a word before the characters that ends with a colon, semicolon or period introduces
    them, never reads them ("the Wakan rōeishū: 扶桑豈無影乎…", teika p. 145), and neither does such punctuation alone
    between. The test tools' answer keys (tools/lang_test.py) were made without it."""
    for step, start in ((-1, w0 - 1), (1, w1 + 1)):
        i, got = start, {}
        if 0 <= i < len(pw) and PUNCT_ONLY.match(pw[i]):
            if strict and step == -1 and INTRODUCES.search(pw[i]): continue
            i += step
        if strict and step == -1 and 0 <= i < len(pw) and INTRODUCES.search(pw[i]): continue
        while 0 <= i < len(pw) and len(got) < 3:
            r = reading_of(pw[i], subj, toned)
            if step == 1 and r and not (KANA_.search(pw[i]) or HANGUL.search(pw[i])): r = None   # a romanization after: the next entry's
            if not r: break
            got[i] = r; i += step
        if got: return got
    return {}

def _han_only(p): return 'cjk:han_only' in p['class'] and p.get('w0') is not None

def subject_of(places, words):
    """A book's subject from the readings beside its Han-only places: the most common language among them, as a subject
    ('japan', 'china', 'korea'), or None when no place has one."""
    c = collections.Counter()
    for p in places:
        if not _han_only(p): continue
        pw = words.get(str(p['page'])) or []
        for w in pw[max(0, p['w0'] - 3):p['w0']] + pw[p['w1'] + 1:p['w1'] + 4]:
            r = reading_of(w, None) or ('ko' if HANGUL.search(w) else None)
            if r: c[r] += 1
    return {'ja': 'japan', 'zh': 'china', 'ko': 'korea'}.get(c.most_common(1)[0][0]) if c else None

def toned_of(words):
    """True when the book writes pinyin with tone marks (more than TONED_MIN pieces with a tone Hepburn never writes)."""
    return sum(1 for pw in words.values() for w in pw if TONE_OTHER.search(w)) > TONED_MIN

# ---- glossaries, bibliographies and indexes: a heading's whole text, as books title them. An "Appendix:" or "Selected"
#      may come before it. A glossary, a bibliography, an index or a list may go on ("Glossary of Chinese Characters",
#      "Bibliography and Abbreviations", "Index of Poems Cited", "List of Characters", "Characters for Place Names"); the
#      others stand alone ("Works Cited", "References", "Sources Consulted") or name a language ("Sources in Japanese",
#      "Sources in Western Languages"), so a chapter called "Sources of Japanese Tradition" is not one.
_PRE = r"(?i)^\W*(?:appendix\s*[\w.]*\s*[:.–—-]\s*)?(?:(?:the|an?)\s+)?(?:(?:select(?:ed)?|annotated|general|chinese|japanese|korean|character)\s+)*"
BACK_ON = re.compile(_PRE + r"(?:bibliograph(?:y|ies)|glossar(?:y|ies)|index(?:es)?|character\s+(?:list|glossary)|characters|"
                     r"list\s+of\s+(?:chinese\s+|japanese\s+|korean\s+)?(?:characters|terms|names))"
                     r"(?:\s+(?:of|and|for|to|in)\b.*|\s*[:(–—-].*)?\W*$")
BACK_ALONE = re.compile(_PRE + r"(?:works\s+cited|references(?:\s+cited)?|literature\s+cited|sources(?:\s+cited|\s+consulted)?|"
                        r"(?:sources|references|works|bibliography)\s+in\s+(?:\w+\s+)?(?:languages?|\w+ese|chinese|korean|english|\w+)|"
                        r"(?:chinese|japanese|korean)\s+characters|further\s+reading)\W*$")
def back_heading(text):
    """True when a heading's whole text names a glossary, bibliography, index or list of characters (BACK_ON, BACK_ALONE)."""
    t = ' '.join(str(text or '').split())
    return bool(BACK_ON.match(t) or BACK_ALONE.match(t))

KIND = [('bibliography', re.compile(r'(?i)bibliograph|works\s+cited|references|literature|sources|further\s+reading|^\W*works\s+in\b')),
        ('index', re.compile(r'(?i)\bindex')),
        ('glossary', re.compile(r'(?i)glossar|character|terms|names'))]
STRICT_SKIP = ()                                      # #123: no page is left out; the colon guard handles bibliographies (Min, 2026-11-15)
EVIDENCE_SKIP = ('bibliography',)                     # #124: bibliography entries are never evidence; the AI must agree anyway

def kind_of(text):
    """'bibliography', 'index' or 'glossary': the kind of back-matter section a heading back_heading() matched names."""
    return next((k for k, rx in KIND if rx.search(text)), 'glossary')

def _level(h):
    m = re.fullmatch(r'H([1-6])', str(h.get('level') or ''))
    return int(m.group(1)) if m else 1                  # "H", or a heading candidate (no level): ended by any heading

def backmatter(digest):
    """(pages, sections): {page: {kinds}} of the book's glossaries, bibliographies and indexes (kind_of), from the digest's
    headings and heading candidates. A section runs from its heading's page to the page of the next heading of its level
    or above, that page included (a section may end mid-page). (None, []) when the digest has no headings at all: then
    where a glossary is can't be known."""
    heads = [h for h in (digest or {}).get('headings') or [] if isinstance(h, dict) and isinstance(h.get('page'), int)]
    heads += [dict(h, level=None) for h in (digest or {}).get('heading_candidates') or [] if isinstance(h, dict) and isinstance(h.get('page'), int)]
    if not heads: return None, []
    heads.sort(key=lambda h: h['page'])
    n = int(((digest or {}).get('source') or {}).get('pages') or max(h['page'] for h in heads))
    pages, sections = collections.defaultdict(set), []
    for i, h in enumerate(heads):
        t = str(h.get('text') or '')
        if not back_heading(t): continue
        lv, k = _level(h), kind_of(t)
        end = next((x['page'] for x in heads[i + 1:] if x['page'] > h['page'] and _level(x) <= lv), n)
        for pg in range(h['page'], end + 1): pages[pg].add(k)
        sections.append({'text': t[:60], 'kind': k, 'pages': [h['page'], end]})
    return dict(pages), sections

def evidence(f, words, back, subj, toned, skip=STRICT_SKIP, phrase=False):
    """What the readings beside a form's places say: {'lang': one language or None, 'langs': every language found,
    'reading': the first reading's pieces, 'with': places with a reading of one language, 'places': its places,
    'back': places on a page of a back-matter kind in skip (never counted), 'none': places with no reading,
    'mixed': places with readings of two languages}. A reading that names Japanese in a book on Korea counts only as
    kana, and one that names Korean in a book on Japan only as hangul (tools/lang_test.py masked). phrase (#124): with no
    reading beside it, kana in the piece that holds the characters (the same phrase) is a Japanese reading."""
    out = {'lang': None, 'langs': [], 'reading': None, 'with': 0, 'places': len(f['places']), 'back': 0, 'none': 0, 'mixed': 0}
    langs = set()
    for p in f['places']:
        if back and back.get(p['page'], set()) & set(skip): out['back'] += 1; continue
        pw = words.get(str(p['page'])) or []
        if p.get('w0') is None or p.get('w1') is None or p['w1'] >= len(pw): out['none'] += 1; continue
        rs = beside(pw, p['w0'], p['w1'], subj, toned, strict=True)
        if not rs and phrase:
            rs = {i: 'ja' for i in range(p['w0'], p['w1'] + 1) if KANA_.search(pw[i])}
        ls = set(rs.values())
        if len(ls) == 1:
            k = next(iter(ls))
            if (k == 'ja' and subj == 'korea' and not any(KANA_.search(pw[i]) for i in rs)) or \
               (k == 'ko' and subj == 'japan' and not any(HANGUL.search(pw[i]) for i in rs)): ls = set()
        if not ls: out['none'] += 1; continue
        if len(ls) > 1: out['mixed'] += 1; langs |= ls; continue
        out['with'] += 1; langs |= ls
        if out['reading'] is None: out['reading'] = ' '.join(latin_core(pw[i]) or pw[i] for i in sorted(rs))
    out['langs'] = sorted(langs)
    if len(langs) == 1 and not out['mixed']: out['lang'] = out['langs'][0]
    return out

def strict(ev):
    """True when the evidence decides the form locally (#123): every place has a reading, all of one language."""
    return bool(ev['lang'] and ev['places'] and ev['with'] == ev['places'] and not (ev['back'] or ev['none'] or ev['mixed']))

def applies(f): return f.get('group') == 'cjk' and f.get('class') == CLASS and 'current' not in f

def decide(forms, words, digest, doc_lang=None, places=None):
    """forms: lib/langreq.forms(). Returns (local, evid, stats): local {form id: decision} for the forms the rule decides
    (#123), evid {form id: evidence} for every Han-only form with any reading outside bibliographies (#124), and the
    counts. The rule never runs in a Chinese, Japanese or Korean document (Han-only text there is in the body's
    language). A book whose digest has no headings gets no evidence for #124 (its bibliography can't be found)."""
    han = [f for f in forms if applies(f)]
    stats = {'han_only_forms': len(han), 'decided': 0, 'by_language': {}, 'not': {}, 'backmatter': [], 'subject': None, 'toned': False}
    if not han: return {}, {}, stats
    if scripts.primary(doc_lang) in scripts.CJK_DOC:
        stats['off'] = 'a Chinese, Japanese or Korean document'; return {}, {}, stats
    back, sections = backmatter(digest)
    stats['backmatter'] = sections
    if back is None: stats['no_evidence'] = 'the digest has no headings, so the bibliography can\'t be found: no group-approval evidence'
    subj = subject_of(places if places is not None else [p for f in han for p in f['places']], words); toned = toned_of(words)
    stats['subject'], stats['toned'] = subj, toned
    local, evid, why, by = {}, {}, collections.Counter(), collections.Counter()
    for f in han:
        ev = evidence(f, words, back, subj, toned, STRICT_SKIP)
        eb = evidence(f, words, back, subj, toned, EVIDENCE_SKIP, phrase=True) if back is not None else None
        if eb and eb['langs']: evid[f['id']] = eb
        if strict(ev):
            local[f['id']] = {'lang': ev['lang'], 'confidence': 'high', 'why': 'language', 'rule': RULE,
                              'evidence': f'the reading printed beside it: {ev["reading"]}'[:160]}
            by[ev['lang']] += 1; continue
        why['readings of two languages' if ev['mixed'] or len(ev['langs']) > 1
            else 'no reading at some place' if ev['with'] else 'no reading'] += 1
    stats.update(decided=len(local), by_language=dict(by), **{'not': dict(why)})
    return local, evid, stats

def compact(ev):
    """The evidence as a work order keeps it (language_parts forms' `reading`): the language (None: none or mixed), the
    languages found, the first reading, places with a reading, places, places in back matter."""
    return {'lang': ev['lang'], 'langs': ev['langs'], 'text': (ev['reading'] or '')[:80], 'with': ev['with'], 'places': ev['places'], 'back': ev['back']}
