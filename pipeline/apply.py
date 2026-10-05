"""apply.py — the executor.  No model calls, no decisions of its own.

    python apply.py ORIGINAL.pdf WORKORDER.json OUT.pdf

Reads the original PDF and a work order (the decisions), applies every decision with
pikepdf in ONE pass, and writes OUT.pdf plus OUT.log.json. The original is opened
read-only and never saved over. Element references in the work order are object numbers
in the ORIGINAL file ("1234 0"), which stay valid because everything happens in memory
before a single save.

Safety: every operation is guarded. An operation that fails, or whose target does not
look the way the work order assumes, is skipped and logged under "rejected" — it never
stops the run and never half-applies.
"""
import sys, os, json, re, collections, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import plumb_fix  # noqa: E401
import pikepdf, pdfplumber

SRC, WO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
assert os.path.abspath(SRC) != os.path.abspath(OUT), 'refusing to write over the original'
wo = json.load(open(WO, encoding='utf-8'))
if str(wo.get('schema', '')).startswith('record/'): wo = wo['workorder']      # a record.json from report.py works too
want = wo.get('source', {}).get('sha256')
if want and hashlib.sha256(open(SRC, 'rb').read()).hexdigest() != want:
    sys.exit('work order was written for a different file (sha256 mismatch)')

pdf = pikepdf.open(SRC)
pages = list(pdf.pages); pidx = {p.obj.objgen: i + 1 for i, p in enumerate(pages)}
labels = {i + 1: p.label for i, p in enumerate(pages)}
st = pdf.Root.StructTreeRoot
KEEP_KEYS = ('text', 'x0', 'x1', 'top', 'bottom', 'size', 'fontname', 'mcid', 'tag')
class _Page:                                    # chars and size only; each pdfplumber page is released after reading
    def __init__(self, p):
        self.width, self.height = p.width, p.height
        self.chars = [{k: c.get(k) for k in KEEP_KEYS} for c in p.chars]
class _PL:
    def __init__(self, path):
        self.pages = []
        with pdfplumber.open(path) as pl:
            for p in pl.pages: self.pages.append(_Page(p)); p.close()
PL = _PL(SRC)
log = {'applied': collections.Counter(), 'rejected': [], 'deferred': [], 'failed': [], 'empty_notes_removed': []}
def ok(k, n=1): log['applied'][k] += n
def reject(op, why): log['rejected'].append({'op': op, 'why': why})
def guarded(label):
    def deco(fn):
        def run(*a, **kw):
            try: return fn(*a, **kw)
            except Exception as e:
                log['failed'].append({'op': label, 'args': str(a)[:120], 'error': f'{type(e).__name__}: {e}'[:300]})
        return run
    return deco
def obj(ref):
    n, g = (int(x) for x in ref.split())
    return pdf.get_object((n, g))

# ------------------------------------------------------------------ tree helpers
def kids(n):
    k = n.get('/K')
    return [] if k is None else (list(k) if isinstance(k, pikepdf.Array) else [k])
def set_kids(n, lst): n.K = pikepdf.Array(lst)
def is_elem(k): return isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) not in ('/MCR', '/OBJR')
def same(a, b): return isinstance(a, pikepdf.Dictionary) and isinstance(b, pikepdf.Dictionary) and a.objgen == b.objgen
def S(n): return str(n.get('/S', '')).lstrip('/')
def is_objr(k): return isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) == '/OBJR'
def is_mcr(k): return isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) == '/MCR'
def new_elem(stype, parent, K, pg=None, **extra):
    d = pikepdf.Dictionary(Type=pikepdf.Name('/StructElem'), S=pikepdf.Name('/' + stype), P=parent, K=pikepdf.Array(K))
    if pg is not None: d.Pg = pages[pg - 1].obj
    for k, v in extra.items(): d['/' + k] = v
    return pdf.make_indirect(d)
def mcr(pg, m): return pikepdf.Dictionary(Type=pikepdf.Name('/MCR'), Pg=pages[pg - 1].obj, MCID=m)

# containers: any element whose type, after the RoleMap, is a grouping type (InDesign "Story", "Article", …)
RMAP = {str(k).lstrip('/'): str(v).lstrip('/') for k, v in (st.get('/RoleMap') or {}).items()}
def mapped(t):
    seen = set()
    while t in RMAP and t not in seen: seen.add(t); t = RMAP[t]
    return t
GROUPING = {'Sect', 'Art', 'Part', 'Story', 'Article'}
def is_container(n): return S(n) in GROUPING or mapped(S(n)) in GROUPING
DOC = next((k for k in kids(st) if is_elem(k) and S(k) == 'Document'), None)   # fix_root() makes sure there is exactly one
eff_pg, parent_of, owner = {}, {}, {}
def reindex():
    eff_pg.clear(); parent_of.clear(); owner.clear()
    stack = [(k, st, None) for k in kids(st)]
    while stack:
        n, par, pg = stack.pop()
        if not is_elem(n): continue
        pg = pidx[n.Pg.objgen] if '/Pg' in n else pg
        eff_pg[n.objgen] = pg; parent_of[n.objgen] = par
        for k in kids(n):
            if isinstance(k, int): owner[(pg, k)] = n
            elif is_mcr(k): owner[(pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID))] = n
            elif is_elem(k): stack.append((k, n, pg))
def all_elems():
    out, stack = [], [(k, st) for k in reversed(kids(st))]
    while stack:
        n, par = stack.pop()
        if not is_elem(n): continue
        out.append((n, par))
        for k in reversed(kids(n)): stack.append((k, n))
    return out
def own_mcids(n, pg):
    out = []
    for k in kids(n):
        if isinstance(k, int): out.append((pg, k))
        elif is_mcr(k): out.append((pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID)))
    return out
def mc_entry_index(el, pg, m):
    epg = eff_pg.get(el.objgen)
    for i, k in enumerate(kids(el)):
        if isinstance(k, int) and k == m and epg == pg: return i
        if is_mcr(k) and int(k.MCID) == m and (pidx[k.Pg.objgen] if '/Pg' in k else epg) == pg: return i
    return None
def nt_find(node, key):
    if '/Nums' in node:
        a = node.Nums
        for j in range(0, len(a), 2):
            if int(a[j]) == key: return node, j + 1
    for kid in node.get('/Kids') or []:
        lim = kid.get('/Limits')
        if lim is None or int(lim[0]) <= key <= int(lim[1]):
            r = nt_find(kid, key)
            if r: return r
def pt_arr(pg):
    sp = pages[pg - 1].obj.get('/StructParents')
    r = nt_find(st.ParentTree, int(sp)) if sp is not None else None
    return r[0].Nums[r[1]] if r else None
def pt_set_mcid(pg, m, el):
    arr = pt_arr(pg)
    while len(arr) <= m: arr.append(None)
    arr[m] = el
def pt_set_key(key, el):
    r = nt_find(st.ParentTree, key); r[0].Nums[r[1]] = el
def detach(el):
    par = parent_of[el.objgen]; set_kids(par, [k for k in kids(par) if not same(k, el)])
def mc_text(pg, m): return ''.join(c['text'] for c in PL.pages[pg - 1].chars if c.get('mcid') == m)
def elem_text(el, depth=0):
    if depth > 30: return ''
    pg = eff_pg.get(el.objgen); s = ''
    for k in kids(el):
        if isinstance(k, int): s += mc_text(pg, k)
        elif is_mcr(k): s += mc_text(pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID))
        elif is_elem(k): s += elem_text(k, depth + 1)
    return s
reindex()
SEC = wo.get('sections', {})
def prange(key):
    r = SEC.get(key); return range(r[0], r[1] + 1) if r else range(0)
NOTES = prange('notes_pages'); TOC_PAGES = set(SEC.get('toc_pages', [])); INDEX_FROM = SEC.get('index_from', 10 ** 9)

# ================================================================== 1. artifacts (the only page-content edit)
def op_artifacts(spec):
    elems = []
    stack = [(k, st, None) for k in kids(st)]
    while stack:
        n, par, pg = stack.pop()
        if not is_elem(n): continue
        pg = pidx[n.Pg.objgen] if '/Pg' in n else pg
        for k in kids(n):
            if is_elem(k): stack.append((k, n, pg))
        elems.append((n, par, own_mcids(n, pg)))
    by_obj = {n.objgen: (n, par, ms) for n, par, ms in elems}
    targets = {}
    def take(n, par, ms, props, label):
        if len(ms) != 1 or len(kids(n)) != 1:
            reject(f'artifact {label} {n.objgen}', 'element is not a single marked-content run'); return
        targets[ms[0]] = (n, par, props, label)
    for item in spec.get('elements', []):
        o = obj(item['obj']); hit = by_obj.get(o.objgen)
        if hit is None: reject(f'artifact {item["obj"]}', 'not in the structure tree'); continue
        take(*hit, pikepdf.Dictionary(Type=pikepdf.Name('/' + item.get('type', 'Layout'))), item.get('label', 'element'))
    owned_now = {pm for _, _, ms in elems for pm in ms}
    for rule in spec.get('text_rules', []):
        rx = re.compile(rule.get('regex', '.*'), re.S); orphans = bool(rule.get('orphans'))
        band = rule.get('band', 'any')
        for pno in range(rule['pages'][0], rule['pages'][1] + 1):
            H = float(PL.pages[pno - 1].height); by = collections.defaultdict(list)
            for c in PL.pages[pno - 1].chars:
                if c.get('mcid') is not None: by[c['mcid']].append(c)
            for m, cs in by.items():
                t = ''.join(c['text'] for c in cs).strip(); top = min(c['top'] for c in cs)
                if top >= rule.get('top_max', 1e9) or not rx.fullmatch(t): continue
                if band == 'top' and top >= 70 or band == 'bottom' and top <= H - 60: continue
                props = pikepdf.Dictionary(Type=pikepdf.Name('/' + rule.get('type', 'Pagination')))
                if rule.get('subtype'): props.Subtype = pikepdf.Name('/' + rule['subtype'])
                if orphans:                         # marked content that no tag-tree element owns
                    if (pno, m) not in owned_now: targets[(pno, m)] = (None, None, props, rule.get('label', 'orphan rule'))
                    continue
                hit = [(n, par, ms) for n, par, ms in elems if (pno, m) in ms]
                if len(hit) == 1: take(*hit[0], props, rule.get('label', 'text rule'))
    for rule in spec.get('text_rules', []):          # report orphan runs a rule's band covered but its regex missed
        if not rule.get('orphans') or rule.get('band', 'any') == 'any': continue
        missed = []
        for pno in range(rule['pages'][0], rule['pages'][1] + 1):
            H = float(PL.pages[pno - 1].height); by = collections.defaultdict(list)
            for c in PL.pages[pno - 1].chars:
                if c.get('mcid') is not None and (pno, c['mcid']) not in owned_now: by[c['mcid']].append(c)
            for m, cs in by.items():
                top = min(c['top'] for c in cs)
                inband = top < 70 if rule['band'] == 'top' else top > H - 60
                if inband and (pno, m) not in targets: missed.append((pno, ''.join(c['text'] for c in cs).strip()[:30]))
        if missed:
            log['deferred'].append({'what': f'{len(missed)} orphan runs in the {rule["band"]} band were not matched by rule "{rule.get("label")}"',
                                    'why': 'still unreachable; examples: ' + '; '.join(f'p{p} "{t}"' for p, t in missed[:8])})
    by_page = collections.defaultdict(set)
    for (pg, m) in targets: by_page[pg].add(m)
    done = []
    for pg, ms in sorted(by_page.items()):
        page = pages[pg - 1]; out, hit = [], set()
        for ins in pikepdf.parse_content_stream(page):
            if str(ins.operator) == 'BDC' and len(ins.operands) == 2 and isinstance(ins.operands[1], pikepdf.Dictionary) \
                    and '/MCID' in ins.operands[1] and int(ins.operands[1].MCID) in ms:
                m = int(ins.operands[1].MCID)
                out.append(pikepdf.ContentStreamInstruction([pikepdf.Name('/Artifact'), targets[(pg, m)][2]], pikepdf.Operator('BDC')))
                hit.add(m)
            else: out.append(ins)
        for m in ms - hit: reject(f'artifact p{pg} mcid {m}', 'marked content not found in page stream')
        if not hit: continue
        page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(out))
        arr = pt_arr(pg)
        for m in hit:
            n, par, props, label = targets[(pg, m)]
            if n is not None: set_kids(par, [k for k in kids(par) if not same(k, n)])
            if arr is not None and m < len(arr): arr[m] = None
            ok(f'artifact: {label}'); done.append((pg, m))
    for pg, m in done:                     # the reader now sees these as artifacts too
        for c in PL.pages[pg - 1].chars:
            if c.get('mcid') == m: c['mcid'] = None; c['tag'] = 'Artifact'
    reindex()

# ================================================================== 2. document properties
def op_document(spec):
    if 'title' in spec:
        pdf.docinfo['/Title'] = spec['title']
        with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as meta: meta['dc:title'] = spec['title']
        ok('document: title')
    if spec.get('display_doc_title', True):
        if '/ViewerPreferences' not in pdf.Root: pdf.Root.ViewerPreferences = pikepdf.Dictionary()
        pdf.Root.ViewerPreferences.DisplayDocTitle = True; ok('document: DisplayDocTitle')
    if 'lang' in spec: pdf.Root.Lang = pikepdf.String(spec['lang']); ok('document: /Lang')
    if spec.get('remove_empty_acroform') and '/AcroForm' in pdf.Root and len(pdf.Root.AcroForm.get('/Fields') or []) == 0:
        del pdf.Root['/AcroForm']; ok('document: empty AcroForm removed')

# ================================================================== 3. headings
STD_HEADINGS = {'H', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'Span', 'Caption', 'Note', 'Div'}
def op_rolemap(spec):
    RM = st.RoleMap
    for k, v in spec.items():
        if v not in STD_HEADINGS: reject(f'rolemap {k}', f'{v} is not an allowed target'); continue
        if '/' + k not in RM: reject(f'rolemap {k}', 'style not in RoleMap'); continue
        if str(RM['/' + k]) != '/' + v: RM['/' + k] = pikepdf.Name('/' + v); ok('heading: RoleMap level')

@guarded('merge')
def merge(el, direction, allowed):
    par = parent_of[el.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, el))
    other = (ks[i + 1] if i + 1 < len(ks) else None) if direction == 'next' else (ks[i - 1] if i > 0 else None)
    if not (is_elem(other) and S(other) in allowed):
        reject(f'merge {S(el)} {el.objgen}', f'{direction} sibling is not one of {allowed}'); return
    spg = eff_pg[el.objgen]; moved = []
    for k in kids(el):
        if isinstance(k, int): moved.append(mcr(spg, k)); pt_set_mcid(spg, k, other)
        elif is_mcr(k):
            p = pidx[k.Pg.objgen] if '/Pg' in k else spg; moved.append(mcr(p, int(k.MCID))); pt_set_mcid(p, int(k.MCID), other)
        else:
            if is_elem(k): k.P = other
            moved.append(k)
    set_kids(other, moved + kids(other) if direction == 'next' else kids(other) + moved)
    detach(el); reindex(); ok(f'heading: merged into {direction}')
def op_merges(spec):
    for rule in spec:
        for el, par in all_elems():
            if S(el) == rule['style']: merge(el, rule['direction'], tuple(rule['with']))

@guarded('set')
def set_attr(item, key, value):
    o = obj(item['obj'])
    if o.objgen not in parent_of: reject(f'{key} {item["obj"]}', 'not in the structure tree'); return
    o[key] = value
def op_actual_text(spec):
    for it in spec: set_attr(it, '/ActualText', pikepdf.String(it['text'])); ok('heading: ActualText')
def op_retype(spec):
    for it in spec:
        if it['type'] not in STD_HEADINGS | {'Figure'}: reject(f'retype {it["obj"]}', 'type not allowed'); continue
        set_attr(it, '/S', pikepdf.Name('/' + it['type'])); ok(f'retype → {it["type"]}')

# ================================================================== 4. figures
def op_alt(spec):
    for it in spec:
        o = obj(it['obj'])
        if S(o) != 'Figure': reject(f'alt {it["obj"]}', 'not a Figure'); continue
        set_attr(it, '/Alt', pikepdf.String(it['alt'])); ok('figure: alt text')
def op_move_to_document_start(spec):
    for ref in spec:
        o = obj(ref)
        if any(same(k, o) for k in kids(st)): set_kids(st, [k for k in kids(st) if not same(k, o)])
        elif o.objgen in parent_of and not same(parent_of[o.objgen], DOC): detach(o)
        elif o.objgen in parent_of and same(kids(DOC)[0], o): continue          # already first
        elif o.objgen in parent_of: set_kids(DOC, [k for k in kids(DOC) if not same(k, o)])
        else: reject(f'move {ref}', 'not in the structure tree'); continue
        o.P = DOC; set_kids(DOC, [o] + kids(DOC)); ok('figure: moved into Document, first')
    reindex()

@guarded('caption')
def tie_caption(cap, wrapper_style):
    cpg = eff_pg.get(cap.objgen) or min(p for (p, m), o in owner.items() if same(o, cap))
    cap.S = pikepdf.Name('/Caption')
    par = parent_of[cap.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, cap))
    prv = ks[i - 1] if i > 0 else None
    if is_elem(prv) and S(prv) == wrapper_style:
        prv.S = pikepdf.Name('/Div'); detach(cap); cap.P = prv; set_kids(prv, kids(prv) + [cap]); reindex()
        ok('figure: caption tied (existing wrapper → Div)'); return
    fig = [e for e, _ in all_elems() if S(e) == 'Figure' and eff_pg.get(e.objgen) == cpg]
    if len(fig) != 1:
        ok('figure: caption retyped only'); log['deferred'].append({'page': cpg, 'what': 'caption', 'why': f'{len(fig)} figures on page'}); return
    f = fig[0]; fpar = parent_of[f.objgen]
    blk = fpar if not (is_container(fpar) or S(fpar) == 'Document') else f
    bpar = parent_of[blk.objgen]
    detach(f); detach(cap)
    if is_container(par) and not kids(par): detach(par)
    div = new_elem('Div', bpar, [f, cap], pg=cpg); f.P = div; cap.P = div
    ks2 = kids(bpar); j = next(j for j, k in enumerate(ks2) if same(k, blk)) if not same(blk, f) else None
    set_kids(bpar, ks2 + [div] if j is None else ks2[:j + 1] + [div] + ks2[j + 1:])
    reindex(); ok('figure: caption tied (figure moved out of its paragraph)')
def op_captions(spec):
    reindex()
    for cap in [e for e, _ in all_elems() if S(e) == spec['style']]: tie_caption(cap, spec.get('wrapper_style'))

# ================================================================== 5. lists, contents, notes
@guarded('list')
def build_list(first, rule):
    par = parent_of[first.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, first))
    run = []
    for k in ks[i:]:
        if is_elem(k) and S(k).startswith(rule['item_prefix']):
            run.append(k)
            if S(k) == rule.get('last_style'): break
        else: break
    texts = [elem_text(k).strip() for k in run]
    if rule.get('numbering') == 'Decimal' and not all(re.match(r'^\d+\.', t) for t in texts):
        reject('list', 'items do not all start with a number'); return
    L = new_elem('L', par, [], pg=eff_pg.get(first.objgen),
                 A=pikepdf.Dictionary(O=pikepdf.Name('/List'), ListNumbering=pikepdf.Name('/' + rule.get('numbering', 'None'))))
    items = []
    for k in run:
        li = new_elem('LI', L, [k]); k.P = li; k.S = pikepdf.Name('/LBody'); items.append(li)
    set_kids(L, items); set_kids(par, ks[:i] + [L] + ks[i + len(run):]); ok('list: built')
def op_lists(spec):
    for rule in spec:
        reindex()
        for el in [e for e, _ in all_elems() if S(e) == rule['first_style']]: build_list(el, rule)

@guarded('toc')
def op_toc(spec):
    reindex()
    firsts = [e for e, _ in all_elems() if S(e).startswith(spec['item_prefix'])]
    if not firsts: reject('toc', 'no entries with that style'); return
    first = firsts[0]; par = parent_of[first.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, first))
    run = []
    for k in ks[i:]:
        if is_elem(k) and S(k).startswith(spec['item_prefix']): run.append(k)
        else: break
    toc = new_elem('TOC', par, [], pg=eff_pg.get(first.objgen))
    for k in run: k.S = pikepdf.Name('/TOCI'); k.P = toc
    set_kids(toc, run); set_kids(par, ks[:i] + [toc] + ks[i + len(run):]); ok('contents: TOC built')


# ------------------------------------------------------------------ Note tags: proof of emptiness, unique IDs
def struct_refs():
    """objgens of everything referred to from anywhere except a structure element's own /K (its children) or /P
    (its parent): ParentTree entries, IDTree entries, /Ref, … A Note shell is removed only if nothing here points at it."""
    refs = set()
    def is_se(d): return isinstance(d, pikepdf.Dictionary) and ('/S' in d and '/P' in d or str(d.get('/Type')) == '/StructTreeRoot')
    def scan(o, skip_k):
        for k, v in (o.items() if isinstance(o, pikepdf.Dictionary) else ((None, v) for v in o)):
            if k == '/P' or (k == '/K' and skip_k and not (isinstance(v, pikepdf.Array) and v.is_indirect)): continue
            if isinstance(v, (pikepdf.Dictionary, pikepdf.Array)):
                if v.is_indirect: refs.add(v.objgen)
                else: scan(v, False)
    for o in pdf.objects:
        if isinstance(o, (pikepdf.Dictionary, pikepdf.Array)): scan(o, is_se(o))
    return refs
def provably_empty(el, refs):
    """True only if the element and everything under it hold no content (no marked content, no annotation), carry no
    text of their own (Alt, ActualText, E, ID), and nothing in the file but their parent refers to them."""
    stack = [el]
    while stack:
        n = stack.pop()
        if n.objgen in refs or any(k in n for k in ('/Alt', '/ActualText', '/E', '/ID')): return False
        for k in kids(n):
            if isinstance(k, int) or is_mcr(k) or is_objr(k): return False
            if isinstance(k, pikepdf.Dictionary) and k.is_indirect and '/S' in k: stack.append(k)
            else: return False                      # anything unexpected counts as content
    return True
def op_notes(spec):
    reindex()
    def id_pairs(node, acc):
        if '/Names' in node:
            nm = node.Names; acc += [(bytes(nm[j]), nm[j + 1]) for j in range(0, len(nm), 2)]
        for k in node.get('/Kids') or []: id_pairs(k, acc)
        return acc
    old_pairs = id_pairs(st.IDTree, []) if '/IDTree' in st else []
    existing = {k for k, _ in old_pairs}
    new_ids, n_no = [], 0; refs = struct_refs()
    for el, par in all_elems():
        if S(el) not in spec['styles']: continue
        ks = kids(el); keep = []
        for k in ks:
            if is_elem(k) and mapped(S(k)) == 'Note' and provably_empty(k, refs):
                ok('notes: empty Note shell removed'); log['empty_notes_removed'].append({'obj': f'{k.objgen[0]} {k.objgen[1]}', 'in': S(el)}); continue
            keep.append(k)
        if len(keep) != len(ks): set_kids(el, keep)
        n_no += 1; nid = f'{spec.get("id_prefix", "note-")}{n_no:04d}'.encode()
        while nid in existing: nid += b'x'
        el.S = pikepdf.Name('/Note'); el.ID = pikepdf.String(nid); new_ids.append((nid, el)); ok('notes: Note with /ID')
    if new_ids:
        pairs = old_pairs + new_ids                  # rewritten as one flat, sorted name array (Kids-based trees too)
        st.IDTree = pikepdf.Dictionary(Names=pikepdf.Array())
        pairs.sort(key=lambda x: x[0]); flat = []
        for k, v in pairs: flat += [pikepdf.String(k), v]
        st.IDTree.Names = pikepdf.Array(flat)

# ================================================================== 6. language
KANA = re.compile(r'[぀-ヿㇰ-ㇿｦ-ﾟ]')
CJK = re.compile(r'[　-ヿ㐀-䶿一-鿿＀-￯]')
def tag_run(pno, m, lang):
    o = owner.get((pno, m))
    if o is None: reject(f'lang p{pno} m{m}', 'run not in tree'); return
    if S(o) == 'Span' and len(kids(o)) == 1: o.Lang = pikepdf.String(lang); ok(f'language: {lang} on existing Span'); return
    i = mc_entry_index(o, pno, m)
    if i is None: reject(f'lang p{pno} m{m}', 'entry not found'); return
    ks = kids(o)
    sp = new_elem('Span', o, [m if isinstance(ks[i], int) else ks[i]], pg=pno if isinstance(ks[i], int) else None, Lang=pikepdf.String(lang))
    if isinstance(ks[i], int) and eff_pg.get(o.objgen) != pno: sp.K = pikepdf.Array([mcr(pno, m)])
    ks[i] = sp; set_kids(o, ks); pt_set_mcid(pno, m, sp); owner[(pno, m)] = sp; eff_pg[sp.objgen] = pno
    ok(f'language: {lang} Span')
def op_language(spec):
    reindex()
    explicit = {(r['page'], r['mcid']): r['lang'] for r in spec.get('runs', [])}
    han = []
    for pno in range(1, len(pages) + 1):
        by = collections.defaultdict(str)
        for c in PL.pages[pno - 1].chars:
            if c.get('mcid') is not None: by[c['mcid']] += c['text']
        for m, t in by.items():
            if (pno, m) in explicit: tag_run(pno, m, explicit[(pno, m)]); continue
            if not CJK.search(t): continue
            if re.sub(r'[\s\W\d_]', '', CJK.sub('', t)):
                log['deferred'].append({'page': pno, 'mcid': m, 'what': 'CJK mixed with Latin in one run'}); continue
            if spec.get('kana_runs') and KANA.search(t): tag_run(pno, m, spec['kana_runs']); continue
            han.append({'page': pno, 'label': labels.get(pno), 'mcid': m, 'text': t.strip()})
    log['deferred'].append({'what': 'Han-only runs (ja vs zh)', 'count': len(han)}); log['han_only'] = han

# ================================================================== 7. links
NAMED = {}
def _walk_names(node):
    if '/Names' in node:
        a = node.Names
        for j in range(0, len(a), 2): NAMED[bytes(a[j])] = a[j + 1]
    for k in node.get('/Kids') or []: _walk_names(k)
if '/Names' in pdf.Root and '/Dests' in pdf.Root.Names: _walk_names(pdf.Root.Names.Dests)
if '/Dests' in pdf.Root:
    for k, v in pdf.Root.Dests.items(): NAMED[str(k).lstrip('/').encode()] = v
def dest_page(a):
    act = a.get('/A'); d = None
    if act is not None and str(act.get('/S')) == '/GoTo': d = act.get('/D')
    elif '/Dest' in a: d = a.Dest
    if isinstance(d, pikepdf.String): d = NAMED.get(bytes(d))
    elif isinstance(d, pikepdf.Name): d = NAMED.get(str(d).lstrip('/').encode())
    if isinstance(d, pikepdf.Dictionary) and '/D' in d: d = d.D
    if isinstance(d, pikepdf.Array) and len(d) and isinstance(d[0], pikepdf.Dictionary): return pidx.get(d[0].objgen)
def rect_chars(pno, a):
    H = float(PL.pages[pno - 1].height); r = [float(v) for v in a.Rect]
    x0, x1 = sorted((r[0], r[2])); y0, y1 = sorted((r[1], r[3]))
    return [c for c in PL.pages[pno - 1].chars if x0 <= (c['x0'] + c['x1']) / 2 <= x1 and y0 <= H - (c['top'] + c['bottom']) / 2 <= y1]
def contents_for(pno, a, text, fix):
    t = re.sub(r'\s+', ' ', text).strip(); act = a.get('/A')
    if act is not None and str(act.get('/S')) == '/URI': return t or str(act.URI)
    dp = dest_page(a)
    if pno in TOC_PAGES:
        r = [float(v) for v in a.Rect]; H = float(PL.pages[pno - 1].height)
        top, bot = H - max(r[1], r[3]), H - min(r[1], r[3])
        sel = [c for c in PL.pages[pno - 1].chars if c.get('tag') != 'Artifact' and top - 3 <= (c['top'] + c['bottom']) / 2 <= bot + 3]
        rows = []
        for c in sorted(sel, key=lambda c: c['bottom']):
            if rows and abs(rows[-1][0] - c['bottom']) < 6: rows[-1][1].append(c)
            else: rows.append([c['bottom'], [c]])
        order = {id(c): i for i, c in enumerate(PL.pages[pno - 1].chars)}
        full = ' '.join(''.join(x['text'] for x in sorted(cs, key=lambda x: (round(x['x0']), order[id(x)]))) for _, cs in rows)
        full = re.sub(r'\s+', ' ', full).strip()
        for f_, r_ in fix: full = re.sub(f_, r_, full)
        m = re.match(r'^(.*?)\s*([0-9]+|[ivxlc]+)$', full)
        if m and m.group(1): return f'{m.group(1)}, page {m.group(2)}'
        if full: return full
    if pno in NOTES and dp is not None and dp not in NOTES:
        n = re.search(r'(\d+)\.?\s*$', t)
        if n: return f'Note {n.group(1)}: back to the reference in the text'
    if dp in NOTES and pno not in NOTES:
        n = re.search(r'(\d+)\s*$', t)
        if n: return f'Note {n.group(1)}'
    if pno >= INDEX_FROM:
        u = t.strip(' .,;:')
        nn = re.fullmatch(r'(\d+)n(\d+)', u)
        if nn: return f'Page {nn.group(1)}, note {nn.group(2)}'
        if re.fullmatch(r'[\divxlc]+', u): return f'Page {u}'
        if re.fullmatch(r'[\divxlc]+\s*[–-]\s*[\divxlc]+', u): return f'Pages {u}'
        if dp: return f'Page {labels.get(dp, dp)}'
    t = re.sub(r'^((?:figure|chapter) \d+)\)$', r'\1', t)
    if t: return t
    return f'Go to page {labels.get(dp, dp)}' if dp else 'Link'

def op_links(spec):
    reindex()
    fix = [(f, r) for f, r in spec.get('toc_text_fixes', [])]
    live = [(pno, a) for pno, p in enumerate(pages, 1) for a in (p.obj.get('/Annots') or []) if str(a.get('/Subtype')) == '/Link']
    live_ids = {a.objgen for _, a in live}
    wrapper = {}
    for k in kids(st):
        if is_elem(k) and S(k) in ('Link', 'Index'):
            for g in kids(k):
                if is_objr(g): wrapper[g.Obj.objgen] = k
    objr_home = {}                              # annotation -> element inside the Document that already holds it
    for el, par in all_elems():
        if same(par, st): continue
        for g in kids(el):
            if is_objr(g): objr_home[g.Obj.objgen] = el
    def pt_all_keys(node, acc):
        if '/Nums' in node: acc += [int(node.Nums[j]) for j in range(0, len(node.Nums), 2)]
        for k in node.get('/Kids') or []: pt_all_keys(k, acc)
        return acc
    def add_struct_parent(a):
        """Give an annotation that has none a new ParentTree key (appended at the end of the number tree)."""
        key = max([int(st.get('/ParentTreeNextKey', 0))] + [k + 1 for k in pt_all_keys(st.ParentTree, [])])
        node = st.ParentTree; path = [node]
        while '/Kids' in node and len(node.Kids): node = node.Kids[len(node.Kids) - 1]; path.append(node)
        if '/Nums' not in node: node.Nums = pikepdf.Array()
        node.Nums.append(key); node.Nums.append(None)
        for n in path:
            if '/Limits' in n: n.Limits = pikepdf.Array([n.Limits[0], key])
        a.StructParent = key; st.ParentTreeNextKey = key + 1
    def link_ancestor(el):
        for _ in range(5):
            if el is None or same(el, st) or is_container(el) or S(el) in ('Document', 'Div'): return None
            if mapped(S(el)) == 'Link' and not same(parent_of.get(el.objgen), st): return el
            el = parent_of.get(el.objgen)
    @guarded('link')
    def place(pno, a):
        chars = rect_chars(pno, a); pagechars = PL.pages[pno - 1].chars
        under = []
        for c in chars:
            if c.get('mcid') is not None and c['mcid'] not in under: under.append(c['mcid'])
        wholly = [m for m in under if all(c in chars for c in pagechars if c.get('mcid') == m)]
        if wholly: under = wholly; text = ''.join(c['text'] for c in pagechars if c.get('mcid') in wholly)
        else: text = ''.join(c['text'] for c in chars)
        a.Contents = pikepdf.String(contents_for(pno, a, text, fix)); ok('links: /Contents set')
        W = wrapper.get(a.objgen)
        if '/StructParent' not in a: add_struct_parent(a)
        home = next((h for h in (link_ancestor(owner.get((pno, m))) for m in under) if h is not None), None)
        if home is not None:
            ks = [k for k in kids(home) if not (is_objr(k) and k.Obj.objgen not in live_ids)]
            if not any(is_objr(k) and k.Obj.objgen == a.objgen for k in ks):
                ks.append(pikepdf.Dictionary(Type=pikepdf.Name('/OBJR'), Obj=a, Pg=pages[pno - 1].obj))
            set_kids(home, ks)
            pt_set_key(int(a.StructParent), home)
            if W is not None: set_kids(st, [k for k in kids(st) if not same(k, W)])
            prev = objr_home.get(a.objgen)              # another element inside the document held it too
            if prev is not None and not same(prev, home):
                set_kids(prev, [k for k in kids(prev) if not (is_objr(k) and k.Obj.objgen == a.objgen)])
            objr_home[a.objgen] = home
            ok('links: joined existing Link'); return
        if W is None:
            h = objr_home.get(a.objgen)
            if h is not None and mapped(S(h)) == 'Link':
                pt_set_key(int(a.StructParent), h); ok('links: already tied to a Link inside the document'); return
            W = new_elem('Link', st, []); pt_set_key(int(a.StructParent), W); ok('links: new Link element created')
        W.S = pikepdf.Name('/Link'); W.Pg = pages[pno - 1].obj
        objr = pikepdf.Dictionary(Type=pikepdf.Name('/OBJR'), Obj=a, Pg=pages[pno - 1].obj)
        set_kids(st, [k for k in kids(st) if not same(k, W)])
        if under and not all((pno, m) in owner for m in under):      # the link's text is not in the tag tree
            log['deferred'].append({'page': pno, 'what': 'link on text that is missing from the tag tree',
                                    'why': f'tied to the nearest tagged text instead: "{re.sub(chr(10), " ", text)[:60]}"'})
            under = []
        whole = bool(under) and all(all(c in chars for c in pagechars if c.get('mcid') == m) for m in under)
        if under:
            o = owner.get((pno, under[-1]))
            if o is None: raise ValueError('no owner for MCID under link')
            same_owner = all(same(owner.get((pno, m)), o) for m in under)
            idxs = [mc_entry_index(o, pno, m) for m in under]
            if whole and same_owner and None not in idxs and sorted(idxs) == list(range(min(idxs), min(idxs) + len(idxs))):
                ks = kids(o); lo, hi = min(idxs), max(idxs)
                W.K = pikepdf.Array([mcr(pno, m) for m in under] + [objr])
                for m in under: pt_set_mcid(pno, m, W); owner[(pno, m)] = W
                dp = dest_page(a)
                if dp in NOTES and pno not in NOTES and S(o) != 'Reference':
                    R = new_elem('Reference', o, [W], pg=pno); W.P = R; ks[lo:hi + 1] = [R]; ok('links: note reference wrapped')
                else:
                    W.P = o; ks[lo:hi + 1] = [W]; ok('links: wraps its text')
                set_kids(o, ks); parent_of[W.objgen] = o; eff_pg[W.objgen] = pno; return
            i = max(x for x in idxs if x is not None) if any(x is not None for x in idxs) else len(kids(o)) - 1
            W.K = pikepdf.Array([objr]); W.P = o
            ks = kids(o); ks.insert(i + 1, W); set_kids(o, ks); parent_of[W.objgen] = o
            ok('links: placed after shared text'); return
        H = float(PL.pages[pno - 1].height); x0, y0, x1, y1 = [float(v) for v in a.Rect]
        cy = H - (y0 + y1) / 2
        near = min((c for c in pagechars if c.get('mcid') is not None and (pno, c['mcid']) in owner),
                   key=lambda c: abs(c['top'] - cy) + abs(c['x0'] - x0) / 10, default=None)
        npg = pno
        if near is None:                            # nothing tagged on this page: last tagged text before it, else first after
            for d in [x for k in range(1, len(pages)) for x in (-k, k)]:
                q = pno + d
                if not 1 <= q <= len(pages): continue
                cs = [c for c in PL.pages[q - 1].chars if c.get('mcid') is not None and (q, c['mcid']) in owner]
                if cs: near, npg = (cs[-1] if d < 0 else cs[0]), q; break
            if near is None: raise ValueError('no tagged text in the document')
            log['deferred'].append({'page': pno, 'what': 'link on a page with no tagged text', 'why': f'tied to tagged text on page {npg}'})
        o = owner[(npg, near['mcid'])]; i = mc_entry_index(o, npg, near['mcid'])
        W.K = pikepdf.Array([objr]); W.P = o
        ks = kids(o); ks.insert((i if i is not None else len(ks) - 1) + 1, W); set_kids(o, ks); parent_of[W.objgen] = o
        ok('links: placed beside nearest text')
    for pno, a in live: place(pno, a)
    stale = 0                                   # references to annotations that sit on no page: nothing to read
    for el, _ in all_elems():
        ks = kids(el); keep = [k for k in ks if not (is_objr(k) and k.Obj.objgen not in live_ids)]
        if len(keep) != len(ks): stale += len(ks) - len(keep); set_kids(el, keep)
    if stale: ok('links: references to off-page annotations removed', stale)
    reindex()
    for el, par in all_elems():
        if S(el) == 'Reference' and not elem_text(el).strip() and kids(el) and all(
                is_elem(k) and S(k) == 'Link' and all(is_objr(g) and g.Obj.objgen not in live_ids for g in kids(k)) for k in kids(el)):
            set_kids(par, [k for k in kids(par) if not same(k, el)]); ok('links: dead Reference shell removed')

# ================================================================== 8. reading order
def pages_of(n, pg=None, acc=None):
    acc = set() if acc is None else acc
    if isinstance(n, int): acc.add(pg); return acc
    if not isinstance(n, pikepdf.Dictionary): return acc
    t = str(n.get('/Type'))
    if t == '/MCR': acc.add(pidx[n.Pg.objgen] if '/Pg' in n else pg); return acc
    if t == '/OBJR': return acc
    pg = pidx[n.Pg.objgen] if '/Pg' in n else pg
    for k in kids(n): pages_of(k, pg, acc)
    return acc
def pp(n): return pages_of(n) - {None}
def containers():
    out, stack = [], [DOC]
    while stack:
        n = stack.pop()
        for k in kids(n):
            if is_elem(k) and is_container(k): out.append((k, n)); stack.append(k)
    return out
def op_move_section(spec):
    a, b = spec['pages']; before = spec['before_page']
    sec = [(c, p) for c, p in containers() if pp(c) and min(pp(c)) >= a and max(pp(c)) <= b]
    host = None
    for c, p in containers():
        firsts = [min(pp(k)) for k in kids(c) if is_elem(k) and pp(k)]
        if any(x >= before for x in firsts) and any(x < a for x in firsts): host = c; break
    if len(sec) != 1 or host is None: reject('move_section', f'{len(sec)} candidate sections, host found: {host is not None}'); return
    s, spar = sec[0]; set_kids(spar, [k for k in kids(spar) if not same(k, s)])
    hk = kids(host); j = next(i for i, k in enumerate(hk) if is_elem(k) and pp(k) and min(pp(k)) >= before)
    set_kids(host, hk[:j] + [s] + hk[j:]); s.P = host; ok('order: section moved')
def walk_blocks():
    out, stack = [], [(DOC, None)]
    while stack:
        n, par = stack.pop()
        if not is_elem(n): continue
        if S(n) == 'Document' or is_container(n):
            for k in reversed(kids(n)): stack.append((k, n))
        else: out.append((n, par))
    return out
def op_fix_figure_order(_spec):
    for div, par in list(walk_blocks()):
        if S(div) != 'Div' or not any(is_elem(k) and S(k) == 'Figure' for k in kids(div)): continue
        fps = pages_of(div, pidx.get(div.Pg.objgen) if '/Pg' in div else None) - {None}
        if not fps: continue
        fp = min(fps); blocks = walk_blocks()
        pos = next(i for i, (b, _) in enumerate(blocks) if same(b, div))
        prev_pages = next((pp(b) for b, _ in reversed(blocks[:pos]) if pp(b)), {fp})
        if max(prev_pages) <= fp + 1: continue
        target = None
        for b, bp in blocks:
            ps = pp(b)
            if same(b, div) or not ps: continue
            if min(ps) <= fp and not any(is_elem(k) and S(k) == 'Figure' for k in kids(b)): target = (b, bp)
            if min(ps) > fp: break
        if target is None: reject(f'figure order p{fp}', 'no target block'); continue
        set_kids(par, [k for k in kids(par) if not same(k, div)])
        tb, tp = target; tk = kids(tp); j = next(x for x, k in enumerate(tk) if same(k, tb))
        set_kids(tp, tk[:j + 1] + [div] + tk[j + 1:]); div.P = tp
        c = par
        while c is not None and is_container(c) and not kids(c):
            gp = c.P; set_kids(gp, [k for k in kids(gp) if not same(k, c)]); c = gp
        ok('order: figure moved to its page')
def op_toc_finalize(_spec):
    stack = [DOC]
    while stack:
        n = stack.pop()
        for k in kids(n):
            if not is_elem(k): continue
            if S(k) == 'Link' and S(n) == 'TOCI' and not any(is_objr(g) for g in kids(k)):
                k.S = pikepdf.Name('/Span'); ok('contents: annotation-less Link → Span')
            stack.append(k)
    stack = [DOC]
    while stack:
        n = stack.pop()
        for k in kids(n):
            if not is_elem(k): continue
            if S(k) == 'TOCI' and not (len(kids(k)) == 1 and is_elem(kids(k)[0]) and S(kids(k)[0]) == 'Reference'):
                pg = pidx[k.Pg.objgen] if '/Pg' in k else None
                ref = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name('/StructElem'), S=pikepdf.Name('/Reference'), P=k,
                                                           K=pikepdf.Array([]), **({'Pg': k.Pg} if '/Pg' in k else {})))
                moved = []
                for g in kids(k):
                    if isinstance(g, int): moved.append(g); pt_set_mcid(pg, g, ref)
                    elif is_mcr(g): moved.append(g); pt_set_mcid(pidx[g.Pg.objgen] if '/Pg' in g else pg, int(g.MCID), ref)
                    else:
                        if is_elem(g): g.P = ref
                        moved.append(g)
                ref.K = pikepdf.Array(moved); k.K = pikepdf.Array([ref]); ok('contents: entry wrapped in Reference')
            stack.append(k)
def op_remove_empty_containers(_spec):
    for _ in range(3):
        for c, p in containers():
            if not kids(c): set_kids(p, [k for k in kids(p) if not same(k, c)]); ok('order: empty container removed')


# ================================================================== 0. always: one Document root, tagged flag, title shown
def fix_root():
    global DOC
    roots = [k for k in kids(st) if is_elem(k) and S(k) == 'Document']
    if not roots:                                   # Auto-Tag output often has Part/Sect/Figure at the root
        others = [k for k in kids(st) if is_elem(k)]
        DOC = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name('/StructElem'), S=pikepdf.Name('/Document'), P=st, K=pikepdf.Array(others)))
        for k in others: k.P = DOC
        set_kids(st, [DOC] + [k for k in kids(st) if not is_elem(k)]); ok('document: Document root created')
    else:
        DOC = roots[0]
        for extra_doc in roots[1:]:                 # a second Document root: fold its content into the first
            reindex(); dpg = eff_pg.get(extra_doc.objgen); moved = []
            for k in kids(extra_doc):
                if isinstance(k, int): moved.append(mcr(dpg, k)); pt_set_mcid(dpg, k, DOC)
                elif is_mcr(k): p = pidx[k.Pg.objgen] if '/Pg' in k else dpg; moved.append(mcr(p, int(k.MCID))); pt_set_mcid(p, int(k.MCID), DOC)
                elif is_objr(k):
                    moved.append(k)
                    if '/StructParent' in k.Obj: pt_set_key(int(k.Obj.StructParent), DOC)
                else:
                    if is_elem(k): k.P = DOC
                    moved.append(k)
            set_kids(DOC, kids(DOC) + moved); set_kids(st, [k for k in kids(st) if not same(k, extra_doc)])
            ok('document: second Document root merged')
    reindex()
def fix_flags():
    if '/MarkInfo' not in pdf.Root: pdf.Root.MarkInfo = pikepdf.Dictionary()
    if not pdf.Root.MarkInfo.get('/Marked', False): pdf.Root.MarkInfo.Marked = True; ok('document: marked as tagged')
    if '/ViewerPreferences' not in pdf.Root: pdf.Root.ViewerPreferences = pikepdf.Dictionary()
    if not pdf.Root.ViewerPreferences.get('/DisplayDocTitle', False): pdf.Root.ViewerPreferences.DisplayDocTitle = True; ok('document: DisplayDocTitle')
    if '/Metadata' in pdf.Root and b'pdfuaid' in pdf.Root.Metadata.read_bytes():
        log['deferred'].append({'what': 'the source file already claims PDF/UA conformance', 'why': 'not verified by this pipeline; check it with PAC before relying on it'})

# ================================================================== flatten: false lists and false tables become plain paragraphs
BLOCK = {'P', 'H', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'L', 'Table', 'Div', 'BlockQuote', 'Figure', 'Note', 'TOC'}
def op_flatten(spec):
    def convert(n, depth=0):
        if depth > 40: return
        t = mapped(S(n))
        for k in kids(n):
            if is_elem(k): convert(k, depth + 1)
        if t in ('L', 'LI', 'Table', 'TR', 'THead', 'TBody', 'TFoot'): new = 'Div'
        elif t in ('LBody', 'TD', 'TH'): new = 'Div' if any(is_elem(k) and mapped(S(k)) in BLOCK | {'Div'} for k in kids(n)) else 'P'
        elif t == 'Lbl': new = 'Span'
        else: return
        n.S = pikepdf.Name('/' + new)
        if '/A' in n: del n['/A']                    # list / table attributes no longer apply
    done = set()
    def mark(n, depth=0):
        done.add(n.objgen)
        if depth < 40:
            for k in kids(n):
                if is_elem(k): mark(k, depth + 1)
    for it in spec:
        o = obj(it['obj'])
        if o.objgen in done: ok('flatten: nested list/table already flattened with its parent'); continue
        if o.objgen not in parent_of: reject(f'flatten {it["obj"]}', 'not in the structure tree'); continue
        if mapped(S(o)) not in ('L', 'Table'): reject(f'flatten {it["obj"]}', f'{S(o)} is not a list or table'); continue
        mark(o)
        kind = mapped(S(o)); convert(o); ok(f'flatten: false {"list" if kind == "L" else "table"} → paragraphs')
    reindex()



# ================================================================== always, near the end: every Note has a unique ID
def fix_notes():
    """Mechanical, whatever the work order says: Note tags proven empty are removed; every other Note gets a unique
    /ID (kept if it already has one nobody else uses), and the IDTree is rebuilt from the tree when anything changed."""
    reindex()
    notes = [(el, par) for el, par in all_elems() if mapped(S(el)) == 'Note']
    if not notes: return
    refs = struct_refs(); removed = 0
    for el, par in notes:
        if provably_empty(el, refs) and any(same(k, el) for k in kids(par)):
            set_kids(par, [k for k in kids(par) if not same(k, el)]); removed += 1
            log['empty_notes_removed'].append({'obj': f'{el.objgen[0]} {el.objgen[1]}', 'in': S(par)})
            ok('notes: empty Note tag removed (no content; nothing refers to it)')
    seen, added, n = set(), 0, 0
    for el, _ in all_elems():
        cur = bytes(el.ID) if '/ID' in el else None
        if mapped(S(el)) == 'Note' and (cur is None or cur in seen):
            while True:
                n += 1; nid = f'note-auto-{n:04d}'.encode()
                if nid not in seen: break
            el.ID = pikepdf.String(nid); cur = nid; added += 1; ok('notes: unique /ID added')
        if cur is not None: seen.add(cur)
    if added or removed:
        first = {}
        for el, _ in all_elems():
            if '/ID' in el: first.setdefault(bytes(el.ID), el)
        flat = []
        for k in sorted(first): flat += [pikepdf.String(k), first[k]]
        st.IDTree = pikepdf.Dictionary(Names=pikepdf.Array(flat))

# ================================================================== always, last: the tag-tree index matches the tree
def fix_parenttree():
    reindex()
    def keys(node, acc):
        if '/Nums' in node: acc += [int(node.Nums[j]) for j in range(0, len(node.Nums), 2)]
        for k in node.get('/Kids') or []: keys(k, acc)
        return acc
    def new_key(value):
        key = max([int(st.get('/ParentTreeNextKey', 0))] + [k + 1 for k in keys(st.ParentTree, [])])
        node = st.ParentTree; path = [node]
        while '/Kids' in node and len(node.Kids): node = node.Kids[len(node.Kids) - 1]; path.append(node)
        if '/Nums' not in node: node.Nums = pikepdf.Array()
        node.Nums.append(key); node.Nums.append(value)
        for n in path:
            if '/Limits' in n: n.Limits = pikepdf.Array([n.Limits[0], key])
        st.ParentTreeNextKey = key + 1
        return key
    by_page = collections.defaultdict(list)
    for (pg, m), el in owner.items():
        if pg: by_page[pg].append((m, el))
    fixed = 0
    for pg, items in by_page.items():
        page = pages[pg - 1].obj; arr = pt_arr(pg) if '/StructParents' in page else None
        if arr is None:
            arr = pdf.make_indirect(pikepdf.Array()); page.StructParents = new_key(arr); arr = pt_arr(pg)
        for m, el in items:
            while len(arr) <= m: arr.append(None)
            cur = arr[m]
            if not (isinstance(cur, pikepdf.Dictionary) and cur.objgen == el.objgen): arr[m] = el; fixed += 1
    if fixed: ok('tag tree index: entries repaired', fixed)

# ================================================================== run, in a fixed order
STEPS = [('artifacts', op_artifacts), ('document', op_document), ('rolemap', op_rolemap), ('merges', op_merges),
         ('actual_text', op_actual_text), ('retype', op_retype), ('flatten', op_flatten), ('alt', op_alt),
         ('move_to_document_start', op_move_to_document_start), ('captions', op_captions), ('lists', op_lists),
         ('toc', op_toc), ('notes', op_notes), ('language', op_language), ('links', op_links),
         ('move_section', op_move_section), ('fix_figure_order', op_fix_figure_order),
         ('toc', op_toc_finalize), ('remove_empty_containers', op_remove_empty_containers)]
wo.setdefault('links', {})                 # links are always tied to their text and described
for fn in (fix_root, fix_flags):
    try: fn()
    except Exception as e: log['failed'].append({'op': fn.__name__, 'error': f'{type(e).__name__}: {e}'[:300]})
for key, fn in STEPS:
    if key in wo and wo[key] not in (None, False):
        try: fn(wo[key])
        except Exception as e: log['failed'].append({'op': key, 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_notes()
except Exception as e: log['failed'].append({'op': 'fix_notes', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_parenttree()
except Exception as e: log['failed'].append({'op': 'fix_parenttree', 'error': f'{type(e).__name__}: {e}'[:300]})
left = [S(k) for k in kids(st) if is_elem(k) and not same(k, DOC)]
if left: log['deferred'].append({'what': 'elements still outside the Document', 'count': len(left)})
pdf.save(OUT)
log['applied'] = dict(log['applied'])
json.dump(log, open(OUT + '.log.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(log['applied'], indent=1, ensure_ascii=False))
print('rejected:', len(log['rejected']), '| failed:', len(log['failed']), '| deferred:', [d.get('what') for d in log['deferred']][:6])
