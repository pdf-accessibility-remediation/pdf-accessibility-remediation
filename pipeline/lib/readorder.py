"""readorder.py: the reading-order rules shared by audit.py, apply.py, verify.py and the review page. No PDF library:
it works on plain entries and on callables the caller passes, so each script keeps its own tree walk.

    from lib import readorder
    readorder.is_container(style, mapped)          # a tag the order is shown and checked over (Sect, Story, Div, …)
    readorder.line(style, first, last, depth, text) / readorder.parse_line(s)   # the digest's one-line form, and back
    readorder.out_of_order(entries)                # the entries read away from their printed place
    readorder.read_late(entries)                   # small entries read well after their page, inside a longer one's span
    readorder.section_move(root, groups, firsts, span, a, b, before)   # the move_section match (apply.py, review page)
    readorder.page_jumps(seq)                      # pages whose text, in tag order, jumps back up a column (audit, verify)

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
    if not sib: return set()
    pages = sorted({e['first'] for e in sib}); rank = {p: k + 1 for k, p in enumerate(pages)}
    tree = [None] * (len(pages) + 1)       # Fenwick tree over first pages: the best (weight, -index) ending at or below a page
    best, prev = [], []
    for i, e in enumerate(sib):
        k, top = rank[e['first']], None
        while k > 0:
            if tree[k] is not None and (top is None or tree[k] > top): top = tree[k]
            k -= k & -k
        best.append(e['last'] - e['first'] + 1 + (top[0] if top else 0)); prev.append(-top[1] if top else None)
        k = rank[e['first']]
        while k <= len(pages):
            if tree[k] is None or (best[i], -i) > tree[k]: tree[k] = (best[i], -i)
            k += k & -k
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

def page_jumps(seq):
    """seq: {page: [(top, x0, size) of each tagged text run's first character, in tag-tree order]}, leaving out runs in
    PLACED_ELSEWHERE tags. A jump is a run that starts more than two lines above the previous one (twice its size, at
    least 6 pt) in the same column (within 72 pt across). Pages with 2+ jumps: [{page, jumps_up, runs}], most jumps first."""
    ro = []
    for p, s in sorted(seq.items()):
        up = sum(1 for (t0, x0, z0), (t1, x1, z1) in zip(s, s[1:]) if t1 < t0 - 2 * max(z0, 6) and abs(x1 - x0) < 72)
        if up >= 2: ro.append({'page': p, 'jumps_up': up, 'runs': len(s)})
    return sorted(ro, key=lambda x: -x['jumps_up'])

LATE_PAGES = 5            # read_late: how many pages past its own a small entry may be read before it is listed
def read_late(entries, flagged=None, small=2, n=LATE_PAGES):
    """Small entries (at most `small` pages) that out_of_order does not flag but that are read more than n pages after their
    printed page: an earlier sibling already reached that far, for example a figure section read after the whole chapter
    it sits in. Overlapping stories are normal in InDesign books, so these are listed, never failed. flagged: the
    indexes out_of_order returned (left out here). Returns [{i, first, last, after}]: after is the furthest page read before it."""
    flagged = {x['i'] for x in out_of_order(entries)} if flagged is None else set(flagged)
    groups = {}
    for i, e in enumerate(entries):
        if e.get('first') is not None and not e.get('skip'): groups.setdefault(e.get('parent'), []).append(i)
    out = []
    for idx in groups.values():
        reach = None
        for i in idx:
            e = entries[i]
            if reach is not None and i not in flagged and e['last'] - e['first'] < small and reach - e['first'] > n:
                out.append({'i': i, 'first': e['first'], 'last': e['last'], 'after': reach})
            reach = e['last'] if reach is None else max(reach, e['last'])
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
