"""sections.py: review.md's content as data, so review.md and review.html are both drawn from one source.

report.py writes review.md's lines into a Lines list exactly as before; a line can carry what the dashboard needs:

    L.append(line('- **Not embedded** …', key='fonts:not_embedded', pages=[4, 7]))
    L.append(line('… undefined character', pdfua(' (ISO 14289-1 7.21.8, PDF/UA)'), '. It has …'))   # a PDF/UA-only part
    L.append(line('PDF/UA-only, not required for WCAG …', scope='pdfua'))                           # a PDF/UA-only line

to_sections(lines) turns the finished lines into sections (record.json `sections`, with `sections_version`); render_md()
gives back review.md's text, line for line. In review.html a line's text_wcag() leaves out its PDF/UA-only parts, and a
line with scope "pdfua" is left out altogether: review.md keeps them as the record, the dashboard reports WCAG only.
"""
import re

VERSION = 1

class Line(str):
    """A review.md line (a str, so all existing code keeps working) with optional key, pages, scope, parts, the full texts of
    its excerpts (`full`: [[excerpt, full text]], for review.html's "show full text") and `entry` (False: a note such as
    "Not changed: …", not counted in a section's items) or `n_entries` (a line that groups several entries, e.g. index
    keys: how many it holds; the same name in record.json)."""
    key = None; pages = None; scope = None; parts = None; full = None; entry = None; n_entries = None   # not `count`: str.count

EXCERPT = 100                            # an excerpt of book text: about this many characters, ending at a word boundary

def excerpt(text, full=None, n=EXCERPT):
    """The text cut to about n characters at a word boundary, ending with "…" (whole, when it fits). When it is cut and a
    list is given, [excerpt, whole text] is added to it, for the line's `full`."""
    t = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(t) <= n: return t
    cut = t[:n + 1]; sp = cut.rfind(' ')
    ex = (cut[:sp] if sp > n * 0.6 else t[:n]).rstrip(' ,;:.–—-') + '…'
    if full is not None: full.append([ex, t])
    return ex

class Part(tuple):
    """(text, scope, wcag_text): a piece of a line; a "pdfua" piece shows as wcag_text (default '') in review.html."""

def pdfua(text, wcag_text=''): return Part((text, 'pdfua', wcag_text))
def nolink(text): return Part((text, 'nolink', None))   # shown as it is, but its page references are not this book's: no page links

def line(*pieces, key=None, pages=None, scope=None, full=None, entry=None, n_entries=None):
    parts = [p if isinstance(p, Part) else Part(tuple(p)) if isinstance(p, (tuple, list)) and len(p) == 3 else Part((str(p), None, None)) for p in pieces]
    s = Line(''.join(p[0] for p in parts))
    s.key, s.scope = key, scope
    if full: s.full = [list(x) for x in full]
    if entry is False: s.entry = False
    if n_entries is not None: s.n_entries = int(n_entries)
    s.pages = sorted({int(p) for p in pages if p is not None and str(p).lstrip('-').isdigit()}) if pages else None
    if any(p[1] for p in parts): s.parts = [list(p) for p in parts]
    return s

def text_wcag(item):
    """The item's text for review.html (WCAG only)."""
    if not item.get('parts'): return item['text']
    return ''.join(t if sc != 'pdfua' else (w or '') for t, sc, w in item['parts'])

def parts_wcag(item):
    """[(text, links pages?)] for review.html: PDF/UA-only parts swapped for their WCAG text, no-link parts flagged."""
    if not item.get('parts'): return [(item['text'], True)]
    return [(t if sc != 'pdfua' else (w or ''), sc != 'nolink') for t, sc, w in item['parts']]

def slug(title): return re.sub(r'\s', '-', re.sub(r'[^\w\- ]', '', title.strip().lower()))

SEP = re.compile(r'^\|[-:| ]+\|$')

def to_sections(lines):
    """The finished review.md lines as sections: [{key, n, title, level, anchor, items: [{id, kind, text, …}]}]."""
    secs = [{'key': 'header', 'n': None, 'title': None, 'level': 1, 'anchor': 'header', 'items': []}]
    cur = secs[0]; count = {}
    for i, l in enumerate(lines):
        m3 = re.match(r'^### (\d+)\. (.+?)\s*$', l)
        if l.startswith('## ') or m3 or l.startswith('# '):
            lvl = 1 if l.startswith('# ') else 2 if l.startswith('## ') else 3
            title = l[2 if lvl == 1 else 3 if lvl == 2 else 4:].strip()
            if m3: title = f'{m3.group(1)}. {m3.group(2)}'
            key = getattr(l, 'key', None) or ('title' if lvl == 1 else slug(title if not m3 else m3.group(2)))
            cur = {'key': key, 'n': int(m3.group(1)) if m3 else None, 'title': title, 'level': lvl,
                   'anchor': 'title' if lvl == 1 else slug(title), 'heading': str(l), 'items': []}
            secs.append(cur); continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        kind = ('blank' if not l else 'sep' if SEP.match(l.strip()) else 'head' if l.startswith('|') and SEP.match(nxt.strip())
                else 'row' if l.startswith('|') else 'li' if l.startswith('- ') else 'quote' if l.startswith('> ') else 'p')
        it = {'kind': kind, 'text': str(l)}
        if kind not in ('blank', 'sep', 'head'):
            count[cur['anchor']] = count.get(cur['anchor'], 0) + 1
            it['id'] = f'{cur["anchor"]}-{count[cur["anchor"]]}'
        for k in ('key', 'pages', 'scope', 'parts', 'full'):
            v = getattr(l, k, None)
            if v: it[k] = v
        if getattr(l, 'entry', None) is False: it['entry'] = False
        if getattr(l, 'n_entries', None) is not None: it['n_entries'] = l.n_entries
        cur['items'].append(it)
    return secs

def render_md(secs):
    """review.md's lines from the sections, exactly as they were written."""
    out = []
    for s in secs:
        if s.get('heading') is not None: out.append(s['heading'])
        out += [it['text'] for it in s['items']]
    return out

def by_key(secs):
    """{key: (section, item)} for every item or section that carries a key."""
    m = {}
    for s in secs:
        for it in s['items']:
            if it.get('key') and it['key'] not in m: m[it['key']] = (s, it)
    return m
