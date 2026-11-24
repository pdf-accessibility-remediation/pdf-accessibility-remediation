"""cjkocr.py: CJK OCR checks and AI page readings matched to OCR lines (#119). Local only: no model, no network.

    cjkocr.score(ref, got)                -> {ref, ocr, matched, edits}: CJK characters only (the measure of #119)
    cjkocr.align_page(lines, reading)     -> (readings {line index: text}, unused AI lines, matched share)
    cjkocr.is_ruby(line_text, height, median_height) -> True for furigana cut out as its own line
    cjkocr.refused(reading)               -> True when a model answered with a refusal instead of the page's text
    cjkocr.split_line(words, reading)     -> one reading per OCR word of a line, by character alignment

Measured on 27 test pages (20 born-digital pages made to look scanned, 7 synthetic: vertical Japanese and Chinese,
furigana, Korean with Hanja, Japanese only; 2026-11-22, tools/cjk_ocr_test.py): a whole-page AI reading matched back to
Tesseract's lines read 98.4% of the CJK characters (Tesseract alone 89.7%) and invented 1.2%. Pages whose lines don't
match (maps, newspapers) are left to a person as a whole-page draft (MATCH_MIN).
"""
import re, difflib, collections

CJK = re.compile(r'[぀-ヿ㐀-鿿豈-﫿가-힯]')
KANA = re.compile(r'[぀-ヿ]')
ACCEPT = 0.2          # similarity a Tesseract line and an AI line need to be paired (order is kept: a skip costs nothing).
                      # Measured: 0.5 left Hanja lines Tesseract read as junk unpaired (Korean with Hanja 92.5% read);
                      # 0.2 read 99.7% there and 98.4% overall, with no wrong pairing found
MATCH_MIN = 0.7       # share of a page's text lines that must be paired for its reading to be attached line by line;
                      # below it the page (a map, a newspaper, lines Tesseract never found) is a draft for a person.
                      # Measured: 0.57–0.79 on the four map and chart pages, 0.82–1.0 on the text pages
GAP_MAX = 3            # unpaired lines filled by order between two pairs (equal counts on both sides only)
RUBY_HEIGHT, RUBY_KANA = 0.7, 0.8   # furigana: under 0.7 of the page's median line height, 80%+ of its letters kana

def lev(a, b):
    """Edit distance (insertions, deletions, substitutions)."""
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def score(ref, got):
    """The test set's measure, CJK characters only: matched (in order), edits, and both lengths. read = matched / ref,
    invented = (ocr - matched) / ocr, CER = edits / ref."""
    r, o = ''.join(CJK.findall(ref or '')), ''.join(CJK.findall(got or ''))
    m = sum(b.size for b in difflib.SequenceMatcher(None, r, o, autojunk=False).get_matching_blocks())
    return {'ref': len(r), 'ocr': len(o), 'matched': m, 'edits': lev(r, o)}

def norm(t): return ''.join(c for c in (t or '').lower() if c.isalnum())

def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b: return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()

def align_page(lines, reading, accept=ACCEPT):
    """lines: the OCR's lines in reading order (strings); reading: the AI's text, one printed line per line. A monotone
    alignment of the two sequences, each pair scored by sim (pairs under accept never made; a skip on either side costs
    nothing), so the order of lines is kept. Returns (readings {line index: AI line}, the AI lines left unused, the share
    of the OCR's text lines that were paired)."""
    ai = [x.strip() for x in (reading or '').split('\n') if norm(x)]
    n, m = len(lines), len(ai)
    S = [[0.0] * (m + 1) for _ in range(n + 1)]; B = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best, how = S[i - 1][j], 'up'
            if S[i][j - 1] > best: best, how = S[i][j - 1], 'left'
            s = sim(lines[i - 1], ai[j - 1])
            if s >= accept and S[i - 1][j - 1] + s > best: best, how = S[i - 1][j - 1] + s, 'diag'
            S[i][j], B[i][j] = best, how
    i, j, read, used = n, m, {}, set()
    while i > 0 and j > 0:
        h = B[i][j]
        if h == 'diag': read[i - 1] = ai[j - 1]; used.add(j - 1); i -= 1; j -= 1
        elif h == 'up': i -= 1
        else: j -= 1
    # gaps (#119): between two paired lines (or a page edge and a paired line), the same number of unpaired text lines on
    # both sides, at most GAP_MAX, are the same printed lines in the same order: a line the OCR read as junk (mostly Latin
    # noise, too unlike its reading to pair on its own) still gets its reading. Unequal gaps stay unpaired.
    idx = _pairs(read, ai, used)
    bounds = [(-1, -1)] + idx + [(n, m)]
    for (i0, j0), (i1, j1) in zip(bounds, bounds[1:]):
        gi = [k for k in range(i0 + 1, i1) if norm(lines[k])]; gj = [k for k in range(j0 + 1, j1)]
        if gi and len(gi) == len(gj) <= GAP_MAX and (i0 >= 0 or i1 < n):          # never a page with no anchor at all
            for k, j in zip(gi, gj): read[k] = ai[j]; used.add(j)
    texty = [k for k, t in enumerate(lines) if norm(t)]
    share = sum(1 for k in texty if k in read) / len(texty) if texty else 0.0
    return read, [ai[k] for k in range(m) if k not in used], share

def _pairs(read, ai, used):
    """(line index, AI line index) of each pair align_page made: the AI line paired with a line is the used one holding
    its text, taken in order (two equal AI lines pair in order)."""
    out, free = [], sorted(used)
    for i in sorted(read):
        j = next(j for j in free if ai[j] == read[i]); free.remove(j); out.append((i, j))
    return out

def is_ruby(text, height, median):
    """Furigana cut out as its own line: shorter than RUBY_HEIGHT of the page's median line height, and RUBY_KANA or
    more of its letters kana. Judged on the OCR's own text, never an AI reading."""
    letters = [c for c in (text or '') if c.isalpha()]
    return bool(letters) and bool(median) and height < RUBY_HEIGHT * median and sum(1 for c in letters if KANA.match(c)) >= RUBY_KANA * len(letters)

REFUSAL = re.compile(r"(?i)\b(?:i can(?:'|no)t|i (?:am|'m) (?:not able|unable)|cannot (?:transcribe|reproduce|help)|copyright(?:ed)?)\b")
def refused(reading, ocr_text=''):
    """A refusal instead of the page's text (Sonnet 5.5 refused one test page as copyrighted, the same page on every
    run): refusal wording, and the reading holds no CJK although the OCR found some. Never used as a reading."""
    t = reading or ''
    if not t.strip(): return True
    return bool(REFUSAL.search(t[:400])) and (not CJK.search(t) or bool(CJK.search(ocr_text or '')) and len(CJK.findall(t)) < 0.2 * len(CJK.findall(ocr_text)))

def split_line(words, reading, spaces=False):
    """words: the OCR words of one line, in order (strings); reading: the line's AI reading. One reading per word, so each
    word's hidden text can be respelled where it sits. When the reading has as many space-separated words as the OCR line
    (Korean, mixed CJK and Latin), they map one to one. Otherwise the characters are aligned (difflib): each OCR word takes
    the reading characters aligned to its own; characters the OCR dropped go to the word before them, or, when they start
    a word of the reading (a space before them), to the word after.
    spaces: return [(text, space after)] instead, space after true where the reading has a space after that word's part
    (so two OCR boxes of one printed word are written without a space between them)."""
    if not words: return []
    r = (reading or '').strip()
    toks = r.split()
    if len(toks) == len(words): return [(t, k < len(toks) - 1) for k, t in enumerate(toks)] if spaces else toks
    ocr = ''.join(words); owner = []
    for k, w in enumerate(words): owner += [k] * len(w)
    out = [[] for _ in words]; last_pos = [-1] * len(words)
    sm = difflib.SequenceMatcher(None, ocr, r, autojunk=False); last = 0
    for tag, a, b, c, d in sm.get_opcodes():
        if tag == 'equal' or tag == 'replace':
            for x in range(d - c):
                src = a + min(x, max(0, b - a - 1)) if b > a else max(0, a - 1)
                k = owner[src] if src < len(owner) else last; last = k
                if r[c + x] != ' ': out[k].append(r[c + x]); last_pos[k] = max(last_pos[k], c + x)      # a space separates, never belongs
        elif tag == 'insert':
            k = owner[a] if a < len(owner) and (a == 0 or (c > 0 and r[c - 1] == ' ')) else owner[a - 1] if a > 0 else 0
            for x in range(c, d):
                if r[x] != ' ': out[k].append(r[x]); last_pos[k] = max(last_pos[k], x)
            last = k
        else:                                         # delete: the OCR has characters the reading doesn't
            if a < len(owner): last = owner[min(b, len(owner)) - 1]
    texts = [''.join(x).strip() for x in out]
    if not spaces: return texts
    def space_after(k):
        e = last_pos[k]
        return e >= 0 and e + 1 < len(r) and r[e + 1] == ' '
    return [(t, space_after(k)) for k, t in enumerate(texts)]
