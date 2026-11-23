"""lib/strays.py: tag-tree content kids that point at nothing drawn (#168, the auto-tagger's tree; checklist 7.x, 1.3.1).

The auto-tagger (OpenDataLoader) leaves three kinds of stray reference, measured on 54 books (handoff/166-form-text-tag-tree
01 §1.1, review 02 §1): a page-level kid (an integer, or an /MCR without /Stm) naming a number its page's own content does
not draw, because the run is a form's or the neighbouring page's; and an /MCR … /Stm kid naming a number its form does
not draw (one Figure per page pointing into a shared blank-page image the tagger marked as an artifact). A screen reader
that follows such a kid finds nothing; the run it was meant for is held by another kid.

    Reader(pdf)            what each stream draws, by parsing its content; the one reader for the repair and for
                           verify.py's counts, so the two can't disagree (review 02 M-a)
    find(pdf, reader)      every stray kid, with what the repair would do to it, and every drawn run's claims
    repair(pdf, empties)   removes the stray kids it may, clears the ParentTree slot each named (when it names that element);
                           empties='remove' (intake, which runs no fix_empty_tags) also removes an element left with no kids
                           and nothing that keeps it; empties='leave' (apply: fix_empty_tags removes them after)
    counts(pdf)            verify.py: {'kids_not_drawn', 'runs_named_twice', pages of each}

Rules (review 02 H1, H2, M-a, M-b):
- "drawn" is read from the stream's own content, with a BDC that names its properties resolved through the stream's
  /Properties (tagfix._props). A stream that fails to parse judges nothing: no kid pointing into it is touched.
- an /Stm kid is judged by the form's own content, wherever the form is drawn from; an /MCR with /StmOwn, or a kid with no
  page (no /Pg on it or any ancestor), is left alone.
- a stray page-level kid is removed unless some run it could mean (the same number in a form drawn on its page, or on the
  pages within NEAR of it, in their content or their forms) is drawn and named by no kid: that kid may be the only pointer
  to that text, so it stays, and is listed for a person. A stray /Stm kid is removed (its form is the only stream it can mean).
- the slot at the removed kid's number in its page's (or form's) ParentTree array is set to null when it names that element.
Pure pikepdf."""
import collections
import pikepdf
from lib import tagfix

NEAR = 2                    # pages each side where a stray page-level kid's run may really be (bringing: the page before)
FORM_DEPTH = 4              # forms nested deeper are not followed (as apply.py's _page_forms)
LISTED = 30                 # kept kids listed by name in the record (all are counted)
BLOCK_KEYS = ('/Alt', '/ActualText', '/E', '/ID')   # fix_empty_tags' blockers on an element's own keys


def tree_set(n, key, value):
    """The one write of a tag-tree key here (tests/test_apply_tree_writes.py's rule 1). apply.py calls repair() before it
    builds its kept tag-tree index (its first reindex()), so no kept index can go stale."""
    n[key] = value


def _kids(n):
    k = n.get('/K')
    return [] if k is None else (list(k) if isinstance(k, pikepdf.Array) else [k])


def _is_mcr(k): return isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) == '/MCR'


def _is_elem(k): return isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) not in ('/MCR', '/OBJR')


def _res(page):
    """The page's resources, inherited from its parents when the page has none of its own."""
    n, d = page.obj, 0
    while n is not None and d < 30:
        if '/Resources' in n: return n.Resources
        n, d = n.get('/Parent'), d + 1
    return None


class Reader:
    """What each stream draws: page(n) and form(f) are the MCIDs in that stream's own content (None when it can't be
    parsed); forms_on(n) the forms drawn from page n, at any depth up to FORM_DEPTH (None when a stream on the way can't be
    parsed)."""
    def __init__(self, pdf):
        self.pdf, self.pages = pdf, list(pdf.pages)
        self.pidx = {p.obj.objgen: i for i, p in enumerate(self.pages, 1)}
        self._drawn, self._forms = {}, {}

    @staticmethod
    def _mcids(owner, res):
        try:
            out = set()
            for ins in pikepdf.parse_content_stream(owner, 'BDC'):
                p = tagfix.bdc_props(ins.operands, res)   # indexed in place: list() would convert every operand
                if p is not None and '/MCID' in p: out.add(int(p.MCID))
            return out
        except Exception:
            return None

    def page(self, n):
        if ('p', n) not in self._drawn:
            pg = self.pages[n - 1]
            self._drawn[('p', n)] = self._mcids(pg, _res(pg))
        return self._drawn[('p', n)]

    def form(self, f):
        if ('f', f.objgen) not in self._drawn:
            self._drawn[('f', f.objgen)] = self._mcids(f, f.get('/Resources'))
        return self._drawn[('f', f.objgen)]

    def forms_on(self, n):
        if n in self._forms: return self._forms[n]
        out, ok, seen = [], True, set()
        def walk(owner, res, depth):
            nonlocal ok
            xs = (res or {}).get('/XObject') or {}
            try: names = [ins.operands[0] for ins in pikepdf.parse_content_stream(owner, 'Do') if ins.operands]
            except Exception: ok = False; return
            for nm in names:
                x = xs.get(nm)
                if not isinstance(x, pikepdf.Stream) or str(x.get('/Subtype')) != '/Form' or x.objgen in seen: continue
                seen.add(x.objgen); out.append(x)
                if depth < FORM_DEPTH: walk(x, x.get('/Resources') or res, depth + 1)
        pg = self.pages[n - 1]
        walk(pg, _res(pg), 1)
        self._forms[n] = out if ok else None
        return self._forms[n]

    def draws(self, where, m):
        """True / False whether stream `where` (('p', n) or a form) draws MCID m; None when it can't be read."""
        d = self.page(where[1]) if isinstance(where, tuple) else self.form(where)
        return None if d is None else m in d


def _pt(pdf):
    """{ParentTree key: its value} (arrays for pages and forms)."""
    out = {}
    st = pdf.Root.get('/StructTreeRoot')
    stack = [st.ParentTree] if st is not None and '/ParentTree' in st else []
    seen = set()
    while stack:
        n = stack.pop()
        if n.is_indirect:
            if n.objgen in seen: continue
            seen.add(n.objgen)
        if '/Nums' in n:
            a = n.Nums
            for j in range(0, len(a) - 1, 2): out[int(a[j])] = a[j + 1]
        stack += list(n.get('/Kids') or [])
    return out


def find(pdf, reader=None):
    """{'strays': [...], 'claims': {(stream, MCID): [element objgen, …]}, 'skipped': {why: count}}. Each stray is a dict:
    el, kid, kind ('page' or 'stm'), page, mcid, form (for 'stm'), action ('remove' or 'keep') and why. stream: ('p', n)
    for page n's content, or ('f', form objgen)."""
    R = reader or Reader(pdf)
    st = pdf.Root.get('/StructTreeRoot')
    out = {'strays': [], 'claims': collections.defaultdict(list), 'skipped': collections.Counter(), 'claim_page': {}}
    if st is None: return out
    seen = set()
    stack = [(k, None) for k in reversed(_kids(st))]
    pending = []
    while stack:
        n, pg = stack.pop()
        if not _is_elem(n): continue
        if n.is_indirect:
            if n.objgen in seen: continue
            seen.add(n.objgen)
        if '/Pg' in n: pg = R.pidx.get(n.Pg.objgen, pg)
        ks = _kids(n)
        for k in ks:
            if isinstance(k, int) or (_is_mcr(k) and '/Stm' not in k and '/StmOwn' not in k):
                p = pg if isinstance(k, int) else (R.pidx.get(k.Pg.objgen) if '/Pg' in k else pg)
                m = int(k) if isinstance(k, int) else int(k.get('/MCID', -1))
                if p is None or m < 0: out['skipped']['a kid with no page'] += 1; continue
                d = R.draws(('p', p), m)
                if d is None: out['skipped']["its page's content could not be read"] += 1
                elif d: out['claims'][(('p', p), m)].append(n.objgen)
                else: pending.append({'el': n, 'kid': k, 'kind': 'page', 'page': p, 'mcid': m})
            elif _is_mcr(k) and '/StmOwn' in k: out['skipped']['an /MCR with /StmOwn'] += 1
            elif _is_mcr(k) and isinstance(k.get('/Stm'), pikepdf.Stream):
                f, m = k.Stm, int(k.get('/MCID', -1))
                p = R.pidx.get(k.Pg.objgen) if '/Pg' in k else pg
                d = R.draws(f, m) if m >= 0 else None
                if d is None: out['skipped']["its form's content could not be read"] += 1
                elif d:
                    out['claims'][(('f', f.objgen), m)].append(n.objgen)
                    if p: out['claim_page'].setdefault((('f', f.objgen), m), p)
                else: pending.append({'el': n, 'kid': k, 'kind': 'stm', 'page': p, 'mcid': m, 'form': f})
        for k in reversed(ks):
            if _is_elem(k): stack.append((k, pg))
    npages = len(R.pages)
    for s in pending:
        if s['kind'] == 'stm':
            s['action'], s['why'] = 'remove', "its form draws no such number"
            out['strays'].append(s); continue
        p, m = s['page'], s['mcid']
        cands, unread = [], False
        fs = R.forms_on(p)
        if fs is None: unread = True
        else: cands += [('f', f.objgen) for f in fs if R.draws(f, m)]
        if any(R.draws(f, m) is None for f in fs or []): unread = True
        for d in range(-NEAR, NEAR + 1):
            q = p + d
            if d == 0 or not 1 <= q <= npages: continue
            x = R.draws(('p', q), m)
            if x is None: unread = True
            elif x: cands.append(('p', q))
            fq = R.forms_on(q)
            if fq is None: unread = True; continue
            for f in fq:
                y = R.draws(f, m)
                if y is None: unread = True
                elif y: cands.append(('f', f.objgen))
        free = [c for c in cands if not out['claims'].get((c, m))]
        if unread: s['action'], s['why'] = 'keep', 'a page or form near it could not be read'
        elif free: s['action'], s['why'] = 'keep', 'a run nearby that no tag names may be what it points at'
        else:
            s['action'] = 'remove'
            s['why'] = 'another tag names the run it could mean' if cands else 'nothing near its page draws that number'
        out['strays'].append(s)
    return out


def _referenced(pdf, ogs):
    """{objgen: [what refers to it]} for the given elements: any reference other than a structure element's /K or /P,
    the ParentTree and the IDTree (an annotation, a bookmark, a /Ref …), as fix_empty_tags' _reference_map counts them."""
    refs = collections.defaultdict(list)
    if not ogs: return refs
    st = pdf.Root.get('/StructTreeRoot')
    skip = set()
    def mark(n):
        if isinstance(n, (pikepdf.Dictionary, pikepdf.Array)) and n.is_indirect:
            if n.objgen in skip: return
            skip.add(n.objgen)
        if isinstance(n, pikepdf.Dictionary):
            for k in n.get('/Kids') or []: mark(k)
            if '/Nums' in n: [mark(v) for v in list(n.Nums)[1::2] if isinstance(v, pikepdf.Array)]
    for key in ('/ParentTree', '/IDTree'):
        if st is not None and key in st: mark(st[key])
    def scan(o, holder, skip_k):
        items = o.items() if isinstance(o, pikepdf.Dictionary) else ((None, v) for v in o)
        for k, v in items:
            if k == '/P' or (k == '/K' and skip_k): continue
            if k in ('/ParentTree', '/IDTree') and isinstance(o, pikepdf.Dictionary) and str(o.get('/Type')) == '/StructTreeRoot': continue
            if isinstance(v, (pikepdf.Dictionary, pikepdf.Array)):
                if v.is_indirect:
                    if v.objgen in ogs: refs[v.objgen].append(f'{k or "an entry"} of another object')
                else: scan(v, holder, False)
    for o in pdf.objects:
        if isinstance(o, (pikepdf.Dictionary, pikepdf.Array)) and o.objgen not in skip:
            se = isinstance(o, pikepdf.Dictionary) and ('/S' in o and '/P' in o or str(o.get('/Type')) == '/StructTreeRoot')
            scan(o, o, se)
    return refs


def repair(pdf, empties='leave', reader=None):
    """Removes the stray kids find() marks 'remove' and clears their ParentTree slots. Returns the record:
    {'removed': {'page_kids', 'stm_kids', 'slots_cleared', 'elements'}, 'kept': count, 'kept_listed': [...], 'pages': [...],
    'emptied': [objgen of each element left with no kids], 'skipped': {why: count}}."""
    R = reader or Reader(pdf)
    F = find(pdf, R)
    rec = {'removed': {'page_kids': 0, 'stm_kids': 0, 'slots_cleared': 0, 'elements': 0}, 'kept': 0, 'kept_listed': [],
           'pages': [], 'emptied': [], 'skipped': dict(F['skipped'])}
    pt = _pt(pdf)
    used = {int(pg.obj.StructParents) for pg in R.pages if '/StructParents' in pg.obj}      # keys a page, a form or an
    for o in pdf.objects:                                                                   # annotation uses; an array under
        if isinstance(o, (pikepdf.Stream, pikepdf.Dictionary)):                             # any other key maps nothing
            for k in ('/StructParents', '/StructParent'):
                if k in o and isinstance(o.get(k), int): used.add(int(o[k]))
    unused = [v for key, v in pt.items() if key not in used and isinstance(v, pikepdf.Array)]
    pages = set()
    by_el = collections.defaultdict(list)
    for s in F['strays']:
        if s['action'] == 'keep':
            rec['kept'] += 1
            if len(rec['kept_listed']) < LISTED:
                rec['kept_listed'].append({'page': s['page'], 'mcid': s['mcid'], 'tag': str(s['el'].get('/S', '')).lstrip('/'), 'why': s['why']})
            continue
        by_el[s['el'].objgen].append(s)
    for og, ss in by_el.items():
        el = ss[0]['el']
        drop = {id(s['kid']) for s in ss if not isinstance(s['kid'], int)}
        drop_int = collections.Counter(int(s['kid']) for s in ss if isinstance(s['kid'], int))
        keep = []
        for k in _kids(el):
            if isinstance(k, int) and drop_int.get(int(k)): drop_int[int(k)] -= 1; continue
            if not isinstance(k, int) and _is_mcr(k) and any(_same_kid(k, s['kid']) for s in ss if not isinstance(s['kid'], int)): continue
            keep.append(k)
        tree_set(el, '/K', pikepdf.Array(keep))
        if not keep: rec['emptied'].append(og)
        for s in ss:
            rec['removed']['page_kids' if s['kind'] == 'page' else 'stm_kids'] += 1
            if s['page']: pages.add(s['page'])
            owner = R.pages[s['page'] - 1].obj if s['kind'] == 'page' and s['page'] else s.get('form')
            arr = pt.get(int(owner.StructParents)) if owner is not None and '/StructParents' in owner else None
            m = s['mcid']
            for a in ([arr] if isinstance(arr, pikepdf.Array) else []) + unused:   # its own stream's array, and any array no
                if m < len(a) and isinstance(a[m], pikepdf.Dictionary) and a[m].objgen == og:   # stream uses (Sample N: one per
                    a[m] = None; rec['removed']['slots_cleared'] += 1             # blank-page Figure, review of pass p168)
    if empties == 'remove' and rec['emptied']:
        cands = {og for og in rec['emptied']}
        els = {og: pdf.get_object(og) for og in cands}
        refs = _referenced(pdf, cands)
        gone = set()
        for og, el in els.items():
            if any(k in el for k in BLOCK_KEYS) or refs.get(og): continue
            par = el.get('/P')
            if not isinstance(par, pikepdf.Dictionary): continue
            pk = _kids(par)                                  # review 04: only when it really is one of its /P's kids (a stale
            if not any(isinstance(k, pikepdf.Dictionary) and k.objgen == og for k in pk): continue   #   /P would leave it in the tree)
            tree_set(par, '/K', pikepdf.Array([k for k in pk if not (isinstance(k, pikepdf.Dictionary) and k.objgen == og)]))
            gone.add(og)
        if gone:
            for v in pt.values():
                if isinstance(v, pikepdf.Array):
                    for i in range(len(v)):
                        if isinstance(v[i], pikepdf.Dictionary) and v[i].objgen in gone: v[i] = None; rec['removed']['slots_cleared'] += 1
            rec['removed']['elements'] = len(gone)
            rec['emptied'] = [og for og in rec['emptied'] if og not in gone]
    rec['pages'] = sorted(pages)
    return rec


def _same_kid(a, b):
    """The same /MCR dictionary (an indirect one by its objgen; a direct one by its keys)."""
    if a.is_indirect or b.is_indirect: return a.is_indirect and b.is_indirect and a.objgen == b.objgen
    return all(str(a.get(k)) == str(b.get(k)) for k in ('/MCID', '/Pg', '/Stm')) and \
        (('/Stm' not in a) or a.Stm.objgen == b.Stm.objgen) and (('/Pg' not in a) or a.Pg.objgen == b.Pg.objgen)


def counts(pdf):
    """verify.py's two counts on a file: kids that point at no number their stream draws (kept on purpose by the repair,
    or left by a later step), and drawn runs that two or more kids name. Pages listed for each (first 20)."""
    F = find(pdf)
    nd = F['strays']
    twice = [(c, m) for (c, m), v in F['claims'].items() if len(v) > 1]
    tw_pages = sorted({p for p in ((c[1] if c[0] == 'p' else F['claim_page'].get((c, m))) for c, m in twice) if p})
    return {'kids_not_drawn': len(nd), 'kids_not_drawn_pages': sorted({s['page'] for s in nd if s['page']})[:20],
            'runs_named_twice': len(twice), 'runs_named_twice_pages': tw_pages[:20],
            'kids_not_judged': sum(F['skipped'].values())}       # review 04: kids no one could judge (a page that can't be read)
