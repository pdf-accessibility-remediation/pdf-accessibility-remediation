"""Latin dictionary marks on the review page's "Languages" rows (#141, proposal 14): two facts about a word form, recorded
by the candidate finder (lib/langcands.book) on each place and shown by the review page. They decide nothing.

    latin_norm(w)              -> a word as the Latin list is matched ('' for a word with a letter Latin doesn't write)
    in_latin(form)             -> True when every word of the form is a Latin form Whitaker's Words recognizes
    phrase_at(words, w0, w1)   -> the book's own words of a whole known Latin phrase holding words w0..w1, or None
    mark(place, words)         -> {'latin_list': True, 'latin_phrase': '...'}: the facts for one place (only those that hold)

The data: pipeline/data/latin-whitaker.json (Whitaker's Words' stems, endings and unique forms, built by
tools/dict_measure.py) and pipeline/data/latin-phrases.txt (the Latin phrases of #141's measurement); see data/README.md.
tools/dict_measure.py imports latin_norm and whitaker_match from here, so the measurement and the marks match alike."""
import os, re, json, unicodedata

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
WHITAKER = os.path.join(DATA, 'latin-whitaker.json')
PHRASES = os.path.join(DATA, 'latin-phrases.txt')


def latin_norm(w):
    """A word as Latin lists are matched: compatibility forms folded (NFKD: "ﬁ" → "fi", "ſ" → "s"), no marks (macrons,
    breves), lower case, æ and œ as ae and oe, v as u and j as i (LatinCy and many lists write uitro, iam); punctuation
    and digits dropped. '' (no match) for a word with any other letter outside a-z, so an IPA respelling ("diŋ", "láɪ")
    never folds onto a shorter Latin word (review 15, L2; report 12 §8.2)."""
    w = unicodedata.normalize('NFKD', w or '')
    w = ''.join(ch for ch in w if not unicodedata.combining(ch)).lower().replace('æ', 'ae').replace('œ', 'oe')
    if any(ch.isalpha() and not 'a' <= ch <= 'z' for ch in w): return ''
    w = re.sub(r'[^a-z]', '', w)
    return w.replace('v', 'u').replace('j', 'i')


def whitaker_match(word, stems, ends, uniques=frozenset()):
    """A Latin form Whitaker's data recognizes: a unique form, or a stem of some class followed by an ending of that class.
    stems, ends: {(part of speech, class): set}; class '0' in the endings means every class of that part of speech."""
    w = latin_norm(word)
    if not w: return False
    if w in uniques: return True
    for key, es in ends.items():
        if key[1] == '0':                                   # class 0: every class of that part of speech
            if (key[0], '*') not in stems: stems[(key[0], '*')] = set().union(*[v for k_, v in stems.items() if k_[0] == key[0] and k_[1] != '*'])
            ss = stems[(key[0], '*')]
        else: ss = stems.get(key)
        if not ss: continue
        for e in es:
            if w.endswith(e) and len(w) > len(e) and w[:len(w) - len(e)] in ss: return True
            if e == '' and w in ss: return True
    return False


_W = {}
def _whitaker():
    if not _W:
        d = json.load(open(WHITAKER, encoding='utf-8'))
        _W['stems'] = {tuple(k.split('|')): set(v) for k, v in d['stems'].items()}
        _W['ends'] = {tuple(k.split('|')): set(v) for k, v in d['ends'].items()}
        _W['uniques'] = frozenset(d['uniques'])
        _W['memo'] = {}
    return _W


def in_latin(form):
    """Every word of the form is a Latin form in Whitaker's Words (a form with no word in it: False)."""
    ws = [x for x in re.split(r'\s+', (form or '').strip()) if x]
    if not ws: return False
    W = _whitaker(); memo = W['memo']
    for x in ws:
        k = latin_norm(x)
        if k not in memo: memo[k] = bool(k) and whitaker_match(x, W['stems'], W['ends'], W['uniques'])
        if not memo[k]: return False
    return True


_P = {}
def phrases():
    """[(tuple of normalized words, length)], longest first: the Latin phrase list, one phrase a line."""
    if 'list' not in _P:
        ps = [l.strip() for l in open(PHRASES, encoding='utf-8') if l.strip() and not l.startswith('#')]
        _P['list'] = sorted({tuple(latin_norm(x) for x in p.split()) for p in ps}, key=lambda t: -len(t))
    return _P['list']


_EDGE = '.,;:!?()[]{}"\'“”‘’«»—–-'
def phrase_at(words, w0, w1):
    """The words of a whole list phrase that holds words w0..w1 of the page's word list, as the book prints them (outer
    punctuation trimmed), or None. Whole phrases only, longest first: "cum laude" inside "magna cum laude" is the longer."""
    if w0 is None or w1 is None or not words or not 0 <= w0 <= w1 < len(words): return None
    for ph in phrases():
        k = len(ph)
        if k < w1 - w0 + 1: continue
        for s in range(max(0, w1 - k + 1), min(w0, len(words) - k) + 1):
            if all(latin_norm(words[s + j]) == ph[j] for j in range(k)):
                return ' '.join(words[s:s + k]).strip(_EDGE)
    return None


def mark(place, words):
    """The facts for one place: latin_list when its form is all Whitaker's Words, latin_phrase (the book's words) when it
    sits inside a whole list phrase. {} when neither holds."""
    out = {}
    if in_latin(place.get('form')): out['latin_list'] = True
    ph = phrase_at(words, place.get('w0'), place.get('w1'))
    if ph: out['latin_phrase'] = ph
    return out
