"""readorder.py: the reading-order rules shared by audit.py, apply.py, verify.py and the review page. No PDF library:
it works on plain entries and on callables the caller passes, so each script keeps its own tree walk.

    from lib import readorder
    readorder.is_container(style, mapped)          # a tag the order is shown and checked over (Sect, Story, Div, …)
    readorder.line(style, first, last, depth, text) / readorder.parse_line(s)   # the digest's one-line form, and back
    readorder.out_of_order(entries)                # the entries read away from their printed place
    readorder.section_move(root, groups, firsts, span, a, b, before)   # the move_section match (apply.py, review page)

An entry is {id, parent, style, first, last, depth, text, skip}: one container, in tree order (a parent before its
children). parent is the id of the nearest container above it (None at the top). first/last are its PDF pages (None
when it holds no marked content). skip marks content placed where it is referred to, not where it is printed.
"""
import re

GROUPING = {'Sect', 'Art', 'Part', 'Story', 'Article'}      # what apply.py treats as a section (and moves)
PLACED_ELSEWHERE = ('Note', 'Figure', 'Caption')             # placed where they are referred to: never out of order
LINE = re.compile(r'^(\S+) pp(\d+)-(\d+) depth(\d+): (.*)$', re.S)

def is_container(style, mapped):
    """A section (GROUPING) or a Div: the tags a reading order is listed by."""
    return style in GROUPING or mapped in GROUPING or style == 'Div' or mapped == 'Div'

def skip(mapped, kid_types):
    """True for a container that holds content placed where it is referred to (a Div around a figure or a note)."""
    return mapped == 'Div' and any(t in PLACED_ELSEWHERE for t in kid_types)

def line(style, first, last, depth, text):
    """The digest's form of one entry (digest.reading_order). audit.py writes it; parse_line reads it back."""
    return f'{style} pp{first}-{last} depth{depth}: {text}'

def parse_line(s, i=0):
    """An entry from a digest line, for runs audited before fulltext.json held the order. The parent is not in the line:
    it is taken as the nearest earlier entry with a smaller depth (set by parse_lines). A line that does not match is
    kept with no pages, so it is shown and never flagged."""
    m = LINE.match(s or '')
    if not m: return {'id': f'line:{i}', 'parent': None, 'style': None, 'first': None, 'last': None, 'depth': 0, 'text': s, 'skip': False}
    return {'id': f'line:{i}', 'parent': None, 'style': m[1], 'first': int(m[2]), 'last': int(m[3]), 'depth': int(m[4]),
            'text': m[5], 'skip': False}

def parse_lines(lines):
    es = [parse_line(s, i) for i, s in enumerate(lines or [])]
    for i, e in enumerate(es):
        e['parent'] = next((es[j]['id'] for j in range(i - 1, -1, -1) if es[j]['depth'] < e['depth']), None)
    return es

def _backbone(sib):
    """Indexes of the heaviest run of siblings whose first pages never go back, weighted by the pages each covers:
    what reads in printed order. The rest are what is out of place. Ties go to the earliest entries."""
    best, prev = [], []
    for i, e in enumerate(sib):
        w = e['last'] - e['first'] + 1
        j = max((j for j in range(i) if sib[j]['first'] <= e['first']), key=lambda j: (best[j], -j), default=None)
        best.append(w + (best[j] if j is not None else 0)); prev.append(j)
    if not sib: return set()
    i = max(range(len(sib)), key=lambda k: (best[k], -k)); keep = set()
    while i is not None: keep.add(i); i = prev[i]
    return keep

def out_of_order(entries):
    """Entries read away from their printed place: among the siblings under one container, those outside the longest
    run that reads in page order (most pages covered). A child is never compared with its parent, and skipped entries
    or entries with no pages are left out. Returns [{i, first, last, prev, next}] in tree order: i is the entry's index,
    prev the last page of the in-order sibling read just before it, next the first page of the one just after (None
    at either end)."""
    groups = {}
    for i, e in enumerate(entries):
        if e.get('first') is not None and not e.get('skip'): groups.setdefault(e.get('parent'), []).append(i)
    out = []
    for idx in groups.values():
        sib = [entries[i] for i in idx]; keep = _backbone(sib)
        for k, i in enumerate(idx):
            if k in keep: continue
            before = [entries[idx[j]] for j in sorted(keep) if j < k]; after = [entries[idx[j]] for j in sorted(keep) if j > k]
            out.append({'i': i, 'first': entries[i]['first'], 'last': entries[i]['last'],
                        'prev': before[-1]['last'] if before else None, 'next': after[0]['first'] if after else None})
    return sorted(out, key=lambda x: x['i'])

def section_move(root, groups, firsts, span, a, b, before):
    """The one match for move_section, used by apply.py on the tree it edits and by the review page on the original.
    groups(n): n's child sections, in order; firsts(n): the first page of each child tag of n that holds content, in
    order; span(n): (first, last) page of n, or None. Sections are found by walking down from root through sections
    only, in apply.py's order. Returns (candidates, host): candidates are the (section, parent) pairs whose pages lie
    inside a–b (exactly one is needed); host is the first section with a child starting at or after page before and one
    starting before page a, where the section goes (None if there is none)."""
    found, stack = [], [root]
    while stack:
        n = stack.pop()
        for k in groups(n): found.append((k, n)); stack.append(k)
    cand = [(c, p) for c, p in found if span(c) and span(c)[0] >= a and span(c)[1] <= b]
    host = next((c for c, _ in found if any(x >= before for x in firsts(c)) and any(x < a for x in firsts(c))), None)
    return cand, host
