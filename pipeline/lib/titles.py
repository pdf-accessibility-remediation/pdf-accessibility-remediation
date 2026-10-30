"""lib/titles.py: Title Case for the labels the app and the dashboards show (headings, fold toggles, table column headers,
card titles, buttons). Explanatory text stays in sentence case and is never passed here; neither is quoted book text.

    title_case("Review of the AI's decisions") == "Review of the AI's Decisions"
    title_case("Ready to ship? No")             == "Ready to Ship? No"
    title_case("veraPDF (WCAG rules)")          == "veraPDF (WCAG Rules)"

Articles, conjunctions and short prepositions stay lowercase unless first, last, or first after a colon or question mark.
A word already written with a capital inside it (veraPDF, WCAG, iOS), or holding a dot, slash, underscore or digit
(review.md, H1, 2026-10-29), is left as written. The same rule is in webapp/panel.js and review/page.html (tc()).
"""
import re

SMALL = {'a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'by', 'from', 'with'}
LEAD = '("\'*[`'

def _word(w, edge):
    i = 0
    while i < len(w) and w[i] in LEAD: i += 1
    core = w[i:]
    if not core or not core[0].isalpha(): return w
    if re.search(r'[./_@\d]', core) or any(c.isupper() for c in core[1:]): return w
    bare = core.rstrip(':?!.,;)"\'*`]')
    if not edge and bare in SMALL: return w
    return w[:i] + core[0].upper() + core[1:]

def title_case(s):
    words = s.split(' ')
    out, edge = [], True
    for n, w in enumerate(words):
        if not w: out.append(w); continue
        out.append(_word(w, edge or n == len(words) - 1))
        edge = w.endswith((':', '?', '—'))
    return ' '.join(out)
