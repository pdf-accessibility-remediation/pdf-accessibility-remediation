"""gaptext.py: text as a reader hears it, from characters that may carry no space characters.

Many PDFs (Prince, TeX) mark word breaks only by a gap between glyphs. Joining their characters gives "aswellasowning".
gap_text() puts a space where a line holds a gap wider than GAP_EM of the type size and wider than GAP_TYPICAL times
the typical gap on that line (so letter-spaced type stays one word), and between lines (except after a hyphen).
Used for the digest and review.md, and by apply.py to match text rules whitespace-insensitively. It never changes
the PDF.
"""
import re

GAP_EM = 0.10           # a gap narrower than 0.10 of the type size is never a word break
GAP_TYPICAL = 2.5       # ... nor one under 2.5 times the line's typical gap (letter-spaced type: performing's running heads)
HYPHENS = '-‐‑­'

def _upright(c): return c.get('upright', True) is not False
def _stacked(p, c):
    """Glyphs set one under another in a column (vertical text that is not flagged as rotated)."""
    size = max(float(c.get('size') or 0), float(p.get('size') or 0), 1.0)
    return abs(c['x0'] - p['x0']) < 0.3 * size and abs(c['x1'] - p['x1']) < 0.3 * size and abs(c['top'] - p['top']) < 3 * size
def _vertical(p, c): return not _upright(c) or (_stacked(p, c) and abs(c['bottom'] - p['bottom']) > 0.5 * max(float(c.get('size') or 0), 1.0))
def _gap(p, c):
    if not _vertical(p, c): return c['x0'] - p['x1']
    return max(c['top'] - p['bottom'], p['top'] - c['bottom'])
def _same_line(p, c):
    size = max(float(c.get('size') or 0), float(p.get('size') or 0), 1.0)
    if _upright(c) != _upright(p): return False
    if _upright(c) and _stacked(p, c): return True                       # a column of glyphs counts as one line
    if _upright(c): return abs(c['bottom'] - p['bottom']) <= 0.5 * size and c['x0'] >= p['x0'] - 0.5 * size
    return abs((c['x0'] + c['x1']) / 2 - (p['x0'] + p['x1']) / 2) <= 0.5 * size

_LINES = {}
def _line_index(lst):
    """The page's upright, non-space glyphs bucketed by baseline (2-point bands), cached per page."""
    key = id(lst)
    if key not in _LINES:
        idx = {}
        for o in lst:
            if o['text'].strip() and _upright(o): idx.setdefault(int(o['bottom'] // 2), []).append(o)
        _LINES[key] = (lst, idx)                       # keep lst alive so its id is not reused
    return _LINES[key][1]
def _filled(p, c, page_chars):
    """True when a glyph that is not in this text (another tag, or untagged) sits in the gap between p and c: the gap is a
    hole left by that glyph, not a word break (e.g. an accented letter drawn in another font)."""
    if page_chars is None or 'pg' not in c or not _upright(c): return False
    size = max(float(c.get('size') or 0), 1.0); lo, hi = p['x1'], c['x0']; idx = _line_index(page_chars(c['pg']))
    band = int(c['bottom'] // 2); reach = int(0.5 * size // 2) + 1
    for k in range(band - reach, band + reach + 1):
        for o in idx.get(k, ()):
            if o is p or o is c: continue
            if abs(o['bottom'] - c['bottom']) <= 0.5 * size and min(o['x1'], hi) - max(o['x0'], lo) > 0.5 * (hi - lo): return True
    return False

def gap_text(chars, page_chars=None):
    """chars: pdfplumber-style dicts (text, x0, x1, top, bottom, size, upright; 'pg' optional) in content order.
    page_chars(pg): every character on that page, so a gap filled by a glyph outside this text is not taken for a space."""
    cs = [c for c in chars if c.get('text') is not None]
    if not cs: return ''
    typical, start = [0.0] * len(cs), 0                # the typical gap of each line (a letter-spaced line has its own)
    for i in range(1, len(cs) + 1):
        if i == len(cs) or not _same_line(cs[i - 1], cs[i]):
            g = sorted(_gap(cs[j - 1], cs[j]) for j in range(start + 1, i) if cs[j - 1]['text'].strip() and cs[j]['text'].strip())
            for j in range(start, i): typical[j] = g[len(g) // 2] if g else 0.0
            start = i
    out = [cs[0]['text']]
    for i, (p, c) in enumerate(zip(cs, cs[1:]), 1):
        t = c['text']
        if t.strip() and out[-1] and not out[-1][-1].isspace():
            if _same_line(p, c):
                g = _gap(p, c); size = max(float(c.get('size') or 0), 1.0)
                if g > GAP_EM * size and g > GAP_TYPICAL * typical[i] and not _filled(p, c, page_chars): out.append(' ')
            elif out[-1][-1] not in HYPHENS: out.append(' ')
        out.append(t)
    return re.sub(r'\s+', ' ', ''.join(out)).strip()

def loosen(pattern):
    """The same regular expression with every space (a literal space, '\\ ', '\\s', '\\s+', '\\s*') made optional, so a
    pattern written against spaced text also matches the text a PDF gives without space characters, and vice versa."""
    return re.sub(r'(?:\\s[+*?]?|\\ | +)+', r'\\s*', pattern)
