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
import fontTools.cffLib, fontTools.ttLib, fontTools.fontBuilder  # noqa: F401  required: reads font programs (no silent skip)

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
def PG(n):
    """A page as people should look it up: the PDF page, with the printed label beside it when it differs.
    (Machine fields in the log stay plain PDF page integers.)"""
    if n is None: return 'page: not on this tag'          # wording only: the log keeps null, never an invented page
    lab = str(labels.get(n) or '')
    return f'PDF {n}' + (f' (printed {lab})' if lab and lab != str(n) else '')
def PGR(a, b):
    if a == b: return PG(a)
    la, lb = str(labels.get(a) or ''), str(labels.get(b) or '')
    return f'PDF {a}–{b}' + (f' (printed {la}–{lb})' if la and lb and (la != str(a) or lb != str(b)) else '')
st = pdf.Root.StructTreeRoot
KEEP_KEYS = ('text', 'x0', 'x1', 'top', 'bottom', 'size', 'fontname', 'mcid', 'tag')
class _Page:                                    # chars, image boxes and size only; each pdfplumber page is released after reading
    def __init__(self, p):
        self.width, self.height = p.width, p.height
        self.chars = [{k: c.get(k) for k in KEEP_KEYS} for c in p.chars]
        self.images = [{k: i.get(k) for k in ('x0', 'x1', 'top', 'bottom', 'mcid', 'tag')} for i in p.images]
class _PL:
    def __init__(self, path):
        self.pages = []
        with pdfplumber.open(path) as pl:
            for p in pl.pages: self.pages.append(_Page(p)); p.close()
PL = _PL(SRC)
log = {'applied': collections.Counter(), 'rejected': [], 'deferred': [], 'failed': [], 'empty_notes_removed': [],
       'rolemap': {}, 'bookmarks': None}
def _versions():                               # recorded in record.json and at the top of review.md
    from importlib.metadata import version
    out = {'python': sys.version.split()[0], 'executable': sys.executable}
    for pkg in ('pikepdf', 'pdfplumber', 'pypdfium2', 'pillow', 'fonttools'):
        try: out[pkg] = version(pkg)
        except Exception: out[pkg] = '?'
    return out
log['environment'] = _versions()
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
# An MCR with /Stm points into a Form XObject: its MCID is numbered inside that form, not the page,
# so it must never be keyed as a page MCID (it would collide with the page's own marked content).
def is_pmcr(k): return is_mcr(k) and '/Stm' not in k
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
            elif is_pmcr(k): owner[(pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID))] = n
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
        elif is_pmcr(k): out.append((pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID)))
    return out
def mc_entry_index(el, pg, m):
    epg = eff_pg.get(el.objgen)
    for i, k in enumerate(kids(el)):
        if isinstance(k, int) and k == m and epg == pg: return i
        if is_pmcr(k) and int(k.MCID) == m and (pidx[k.Pg.objgen] if '/Pg' in k else epg) == pg: return i
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
        elif is_pmcr(k): s += mc_text(pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID))
        elif is_elem(k): s += elem_text(k, depth + 1)
    return s
reindex()
SEC = wo.get('sections', {})
def prange(key):
    r = SEC.get(key); return range(r[0], r[1] + 1) if r else range(0)
NOTES = prange('notes_pages'); TOC_PAGES = set(SEC.get('toc_pages', [])); INDEX_FROM = SEC.get('index_from', 10 ** 9)

def norm_ws(t): return re.sub(r'\s+', ' ', t).strip()
FORM_RUNS = {}
def form_runs(form, page):
    """{mcid: text} of the marked content inside one Form XObject, read on a scratch page holding only that form."""
    if form.objgen in FORM_RUNS: return FORM_RUNS[form.objgen]
    import io
    tmp = pikepdf.new(); fx = tmp.copy_foreign(form)
    w, h = float(page.mediabox[2]) - float(page.mediabox[0]), float(page.mediabox[3]) - float(page.mediabox[1])
    tp = tmp.add_blank_page(page_size=(w, h))
    tp.obj.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=fx))
    tp.obj.Contents = tmp.make_stream(b'q /F Do Q')
    buf = io.BytesIO(); tmp.save(buf); buf.seek(0)
    runs = collections.defaultdict(str)
    with pdfplumber.open(buf) as pl:
        for c in pl.pages[0].chars:
            if c.get('mcid') is not None: runs[c['mcid']] += c['text']
    FORM_RUNS[form.objgen] = dict(runs); return FORM_RUNS[form.objgen]
def page_forms(pno, done=()):
    """Form XObjects drawn on this page that hold marked content with MCIDs (or did, before this run artifacted them)."""
    out = []
    for name, x in (pages[pno - 1].obj.get('/Resources', {}).get('/XObject') or {}).items():
        if str(x.get('/Subtype')) == '/Form' and (x.objgen in done or b'/MCID' in x.read_bytes()): out.append(x)
    return out
def artifact_form(form, props, label):
    """Every marked run in this form matched a decoration rule: mark them all as artifacts inside the form,
    and take the form's content out of the tag tree (MCRs with /Stm pointing at it)."""
    out, n = [], 0
    for ins in pikepdf.parse_content_stream(form):
        if str(ins.operator) == 'BDC' and len(ins.operands) == 2 and isinstance(ins.operands[1], pikepdf.Dictionary) and '/MCID' in ins.operands[1]:
            out.append(pikepdf.ContentStreamInstruction([pikepdf.Name('/Artifact'), props], pikepdf.Operator('BDC'))); n += 1
        else: out.append(ins)
    form.write(pikepdf.unparse_content_stream(out))
    if '/StructParents' in form: del form['/StructParents']
    gone = set()
    for el, par in all_elems():
        ks = kids(el); keep = [k for k in ks if not (is_mcr(k) and '/Stm' in k and k.Stm.objgen == form.objgen)]
        if len(keep) == len(ks): continue
        if keep: set_kids(el, keep)
        else: set_kids(par, [k for k in kids(par) if not same(k, el)]); gone.add(el.objgen)
    ok(f'artifact: "{label}" (inside a shared form XObject)', n)
    return gone

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
    def in_band(band, top, H): return not (band == 'top' and top >= 70 or band == 'bottom' and top <= H - 60)
    forms_done, form_mcids = {}, collections.defaultdict(set)      # form objgen -> gone elements; page -> MCIDs drawn by an artifacted form
    for rule in spec.get('text_rules', []):
        rx = re.compile(rule.get('regex', '.*'), re.S); orphans = bool(rule.get('orphans'))
        band = rule.get('band', 'any'); label = rule.get('label', 'orphan rule' if orphans else 'text rule'); matched = 0
        props = pikepdf.Dictionary(Type=pikepdf.Name('/' + rule.get('type', 'Pagination')))
        if rule.get('subtype'): props.Subtype = pikepdf.Name('/' + rule['subtype'])
        for pno in range(rule['pages'][0], rule['pages'][1] + 1):
            H = float(PL.pages[pno - 1].height); by = collections.defaultdict(list)
            for c in PL.pages[pno - 1].chars:
                if c.get('mcid') is not None: by[c['mcid']].append(c)
            if band == 'any':                       # decoration drawn by a shared Form XObject (e.g. a junk text grid)
                for form in page_forms(pno, forms_done):
                    if form.objgen in forms_done:
                        form_mcids[pno] |= set(form_runs(form, pages[pno - 1])); continue
                    runs = {m: norm_ws(t) for m, t in form_runs(form, pages[pno - 1]).items()}
                    texts = [t for t in runs.values() if t]
                    if texts and all(rx.fullmatch(t) for t in texts):
                        forms_done[form.objgen] = artifact_form(form, props, label); form_mcids[pno] |= set(runs); matched += len(texts)
            for m, cs in by.items():
                raw = ''.join(c['text'] for c in cs); t = raw.strip(); top = min(c['top'] for c in cs)
                if top >= rule.get('top_max', 1e9) or not (rx.fullmatch(t) or rx.fullmatch(norm_ws(raw))): continue
                if not in_band(band, top, H): continue
                if m in form_mcids[pno]: continue
                matched += 1
                if orphans:                         # marked content that no tag-tree element owns
                    if (pno, m) not in owned_now: targets[(pno, m)] = (None, None, props, label)
                    continue
                hit = [(n, par, ms) for n, par, ms in elems if (pno, m) in ms]
                if len(hit) != 1: continue
                n, par, ms = hit[0]
                if len(ms) > 1 and band != 'any' and len(kids(n)) == len(ms) and all(p == pno and p2 in by and
                        in_band(band, min(c['top'] for c in by[p2]), H) for p, p2 in ms):
                    for pm in ms: targets[pm] = (n, par, props, label)      # a running head split into several runs, all in the band
                else: take(n, par, ms, props, label)
        if matched == 0:
            log['deferred'].append({'what': f'text rule "{label}" matched no text on {PGR(rule["pages"][0], rule["pages"][1])}',
                                    'why': 'nothing was hidden by this rule; check its pattern against the page (spacing, split runs)'})
    gone = set().union(*forms_done.values()) if forms_done else set()
    if gone:                                          # no ParentTree entry may point at an element that left the tree
        def clear(node):
            if '/Nums' in node:
                a = node.Nums
                for j in range(1, len(a), 2):
                    v = a[j]
                    if isinstance(v, pikepdf.Array):
                        for i in range(len(v)):
                            if isinstance(v[i], pikepdf.Dictionary) and v[i].objgen in gone: v[i] = None
                    elif isinstance(v, pikepdf.Dictionary) and v.objgen in gone: a[j] = pikepdf.Array([])
            for k in node.get('/Kids') or []: clear(k)
        clear(st.ParentTree)
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
                                    'why': 'still unreachable; examples: ' + '; '.join(f'{PG(p)} "{t}"' for p, t in missed[:8])})
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
        for m in ms - hit: reject(f'artifact {PG(pg)} mcid {m}', 'marked content not found in page stream')
        if not hit: continue
        page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(out))
        arr = pt_arr(pg)
        for m in hit:
            n, par, props, label = targets[(pg, m)]
            if n is not None: set_kids(par, [k for k in kids(par) if not same(k, n)])
            if arr is not None and m < len(arr): arr[m] = None
            ok(f'artifact: "{label}"'); done.append((pg, m))
    for pg, m in done:                     # the reader now sees these as artifacts too
        for c in PL.pages[pg - 1].chars:
            if c.get('mcid') == m: c['mcid'] = None; c['tag'] = 'Artifact'
    reindex()
    for rule in spec.get('untagged', []): untagged_rule(rule)
    reindex()

TEXT_OPS = {'Tj', 'TJ', "'", '"'}
def form_has_free_text(x):
    """True if a Form XObject shows text outside any marked-content sequence."""
    depth = 0
    for ins in pikepdf.parse_content_stream(x):
        op = str(ins.operator)
        if op in ('BDC', 'BMC'): depth += 1
        elif op == 'EMC': depth = max(0, depth - 1)
        elif op in TEXT_OPS and depth == 0: return True
    return False
def untagged_rule(rule):
    """Untagged text (in no marked-content sequence at all) that the work order says is decoration: a page notice that
    the regex fully matches, or text lying entirely inside Figures that carry alt text. Each page is all-or-nothing:
    every untagged character on it must qualify, and then every free text-showing operator on it is wrapped as an artifact."""
    label = rule.get('label', 'untagged text'); where = rule.get('where'); rx = re.compile(rule['regex'], re.S) if rule.get('regex') else None
    props = pikepdf.Dictionary(Type=pikepdf.Name('/' + rule.get('type', 'Layout')))
    for pno in range(rule['pages'][0], rule['pages'][1] + 1):
        U = [c for c in PL.pages[pno - 1].chars if c.get('mcid') is None and c.get('tag') != 'Artifact']
        if not U: continue
        if rx is not None:
            if not rx.fullmatch(norm_ws(''.join(c['text'] for c in U))):
                reject(f'untagged {PG(pno)}', f'the untagged text on the page does not fully match the rule "{label}"'); continue
        elif where == 'in_figure':
            boxes = [(f, box_of(f, pno)) for f, _ in all_elems() if mapped(S(f)) == 'Figure']
            boxes = [(f, b) for f, b in boxes if b is not None]
            if not boxes:
                reject(f'untagged {PG(pno)}', 'no Figure tag on this page: the drawing and its text are untagged; a person must tag it as a Figure with alt text first'); continue
            inside = lambda c: any(b[0] - 2 <= c['x0'] and c['x1'] <= b[2] + 2 and b[1] - 2 <= c['top'] and c['bottom'] <= b[3] + 2 for _, b in boxes)
            out = [c for c in U if not inside(c)]
            if out:
                reject(f'untagged {PG(pno)}', f'{len(out)} untagged characters lie outside every Figure'); continue
            if not all(str(f.get('/Alt', '')).strip() for f, _ in boxes):
                reject(f'untagged {PG(pno)}', 'a Figure on this page has no alt text to carry what its text says'); continue
        else:
            reject(f'untagged {PG(pno)}', 'rule needs "regex" or "where": "in_figure"'); continue
        page = pages[pno - 1]
        xo = page.obj.get('/Resources', {}).get('/XObject') or {}
        if any(str(x.get('/Subtype')) == '/Form' and form_has_free_text(x) for x in xo.values()):
            reject(f'untagged {PG(pno)}', 'some untagged text is inside a form XObject; not changed'); continue
        out, depth, n = [], 0, 0
        for ins in pikepdf.parse_content_stream(page):
            op = str(ins.operator)
            if op in ('BDC', 'BMC'): depth += 1
            elif op == 'EMC': depth = max(0, depth - 1)
            if op in TEXT_OPS and depth == 0:
                out.append(pikepdf.ContentStreamInstruction([pikepdf.Name('/Artifact'), props], pikepdf.Operator('BDC')))
                out.append(ins); out.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator('EMC'))); n += 1
            else: out.append(ins)
        if not n: continue
        page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(out))
        for c in U: c['tag'] = 'Artifact'
        ok(f'artifact: "{label}" (untagged text)', len(U)); log.setdefault('untagged_artifacts', []).append({'page': pno, 'label': label, 'chars': len(U)})

# ================================================================== orphans: real content adopted into the tree
BLOCK_PARENTS = {'Document', 'Div', 'Sect', 'Art', 'Part', 'NonStruct', 'BlockQuote', 'Note'}
def op_adopt_orphans(spec):
    """Marked content that no tag owns, on pages the work order names as real content (notes, bibliography, body text):
    added to the tree as P elements, in the order it is drawn on the page, right after the last block on that page
    (or on an earlier page) that already holds tagged content. Lines are joined into one P until a line ends short
    of the right margin, which is where a paragraph ends."""
    reindex()
    def anchor_for(pno):
        last = None
        for e, par in all_elems():
            if any(p == pno for p, _ in own_mcids(e, eff_pg.get(e.objgen))): last = e
        if last is None: return None
        while last.objgen in parent_of and not (is_container(parent_of[last.objgen]) or S(parent_of[last.objgen]) in BLOCK_PARENTS):
            last = parent_of[last.objgen]
        return last if last.objgen in parent_of else None
    for rule in spec:
        label = rule.get('label', 'orphan content')
        for pno in range(rule['pages'][0], rule['pages'][1] + 1):
            in_stream = {int(ins.operands[1].MCID) for ins in pikepdf.parse_content_stream(pages[pno - 1])
                         if str(ins.operator) == 'BDC' and len(ins.operands) == 2 and isinstance(ins.operands[1], pikepdf.Dictionary)
                         and '/MCID' in ins.operands[1]}      # only the page's own marked content, never a form XObject's
            order, by = [], collections.defaultdict(list)
            for c in PL.pages[pno - 1].chars:
                m = c.get('mcid')
                if m is None or (pno, m) in owner or m not in in_stream: continue
                if m not in by: order.append(m)
                by[m].append(c)
            if not order: continue
            right = max(c['x1'] for m in order for c in by[m])
            paras, cur, line_bottom, line_right = [], [], None, None
            for m in order:
                cs = by[m]; top = min(c['top'] for c in cs)
                new_line = line_bottom is None or top > line_bottom - 2
                if new_line and cur and line_right is not None and line_right < right - 15: paras.append(cur); cur = []
                cur.append(m)
                if new_line: line_bottom, line_right = max(c['bottom'] for c in cs), max(c['x1'] for c in cs)
                else: line_bottom, line_right = max(line_bottom, max(c['bottom'] for c in cs)), max(line_right, max(c['x1'] for c in cs))
            if cur: paras.append(cur)
            anc = None; q = pno
            while anc is None and q >= 1: anc = anchor_for(q); q -= 1
            host = parent_of[anc.objgen] if anc is not None else DOC
            new = [new_elem('P', host, list(ms), pg=pno) for ms in paras]
            ks = kids(host); j = next((i for i, k in enumerate(ks) if anc is not None and same(k, anc)), len(ks) - 1)
            set_kids(host, ks[:j + 1] + new + ks[j + 1:])
            for el, ms in zip(new, paras):
                for m in ms: owner[(pno, m)] = el
            reindex()
            ok(f'orphans: adopted as paragraphs ("{label}")', len(paras))
            log.setdefault('adopted', []).append({'page': pno, 'label': label, 'runs': len(order), 'paragraphs': len(paras),
                                                  'first': norm_ws(''.join(c['text'] for c in by[order[0]]))[:50]})

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
# Standard structure types (PDF 1.7 / PDF 2.0). A RoleMap entry may not remap one of these, so a decision like
# "H1 → H3" for a publisher style literally named H1 is carried out as a retype of every element with that tag.
STANDARD_TYPES = {'Document', 'DocumentFragment', 'Part', 'Art', 'Sect', 'Div', 'Aside', 'BlockQuote', 'Caption', 'TOC', 'TOCI',
                  'Index', 'NonStruct', 'Private', 'H', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'L', 'LI', 'Lbl', 'LBody', 'Table',
                  'TR', 'TH', 'TD', 'THead', 'TBody', 'TFoot', 'Span', 'Quote', 'Note', 'Reference', 'BibEntry', 'Code', 'Link',
                  'Annot', 'Ruby', 'RB', 'RT', 'RP', 'Warichu', 'WT', 'WP', 'Figure', 'Formula', 'Form', 'Title', 'FENote', 'Sub', 'Em', 'Strong'}
PENDING_STD = {}
def op_rolemap(spec):
    if '/RoleMap' not in st: st.RoleMap = pikepdf.Dictionary()
    RM = st.RoleMap
    for k, v in spec.items():
        if v not in STD_HEADINGS: reject(f'rolemap {k}', f'{v} is not an allowed target'); continue
        if '/' + k not in RM:
            if k in STANDARD_TYPES and k != v: PENDING_STD[k] = v; continue      # done by op_rolemap_standard, after merges
            reject(f'rolemap {k}', 'style not in RoleMap'); continue
        n = sum(1 for e, _ in all_elems() if S(e) == k)
        if str(RM['/' + k]) != '/' + v: RM['/' + k] = pikepdf.Name('/' + v); ok('heading: RoleMap level')
        log['rolemap'][k] = {'to': v, 'how': 'RoleMap', 'elements': n}
def op_rolemap_standard(_spec):
    """Carry out RoleMap decisions on standard tags (e.g. H1 → H3) as retypes. All targets are collected first, so
    H1 → H2 and H2 → H3 in the same work order do not chain."""
    if not PENDING_STD: return
    reindex(); todo = [(e, PENDING_STD[S(e)]) for e, _ in all_elems() if S(e) in PENDING_STD]
    cnt = collections.Counter()
    for e, v in todo: cnt[(S(e), v)] += 1; e.S = pikepdf.Name('/' + v)
    for k, v in PENDING_STD.items():
        n = cnt.get((k, v), 0); log['rolemap'][k] = {'to': v, 'how': 'retype (standard tag)', 'elements': n}
        if n: ok(f'heading: standard tag {k} → {v} (retyped)', n)
        else: reject(f'rolemap {k}', 'no element carries this tag')
    reindex()

@guarded('merge')
def merge(el, direction, allowed):
    par = parent_of[el.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, el))
    other = (ks[i + 1] if i + 1 < len(ks) else None) if direction == 'next' else (ks[i - 1] if i > 0 else None)
    if not (is_elem(other) and S(other) in allowed):
        reject(f'merge {S(el)} {el.objgen}', f'{direction} sibling is not one of {allowed}'); return
    spg = eff_pg[el.objgen]; moved = []
    for k in kids(el):
        if isinstance(k, int): moved.append(mcr(spg, k)); pt_set_mcid(spg, k, other)
        elif is_pmcr(k):
            p = pidx[k.Pg.objgen] if '/Pg' in k else spg; moved.append(mcr(p, int(k.MCID))); pt_set_mcid(p, int(k.MCID), other)
        elif is_mcr(k): moved.append(k)                      # form-XObject content keeps its own reference
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

def desc_mcids(n, pg=None, acc=None):
    """(page, mcid) of every page-level marked-content run under an element, its children included."""
    acc = [] if acc is None else acc
    if not isinstance(n, pikepdf.Dictionary): return acc
    pg = pidx[n.Pg.objgen] if '/Pg' in n else pg
    for k in kids(n):
        if isinstance(k, int): acc.append((pg, k))
        elif is_pmcr(k): acc.append((pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID)))
        elif is_elem(k): desc_mcids(k, pg, acc)
    return acc
def box_of(el, pno):
    """Bounding box (x0, top, x1, bottom) of an element's text and images on one page, or None."""
    ms = {m for p, m in desc_mcids(el, eff_pg.get(el.objgen)) if p == pno}
    pts = [c for c in PL.pages[pno - 1].chars if c.get('mcid') in ms] + [i for i in PL.pages[pno - 1].images if i.get('mcid') in ms]
    if not pts: return None
    return (min(p['x0'] for p in pts), min(p['top'] for p in pts), max(p['x1'] for p in pts), max(p['bottom'] for p in pts))
CLAIMED = set()
def pick_figure(cap, cpg, figs):
    """On a page with several figures: the one figure right next to the caption (directly above or below, at most 40 pt
    away, overlapping it horizontally). None when no figure fits, when two fit about equally well, or when the caption
    sits inside a figure's area (a panel letter such as "a" or "b"): those stay with a person."""
    cb = box_of(cap, cpg)
    if cb is None: return None
    cand = []
    for f in figs:
        fb = box_of(f, cpg)
        if fb is None: continue
        if fb[0] < cb[2] and cb[0] < fb[2] and fb[1] < cb[3] and cb[1] < fb[3]: return None     # caption inside a figure
        if f.objgen in CLAIMED: continue
        overlap = min(fb[2], cb[2]) - max(fb[0], cb[0])
        if overlap <= 0.3 * min(fb[2] - fb[0], cb[2] - cb[0]): continue
        gap = cb[1] - fb[3] if fb[3] <= cb[1] + 3 else (fb[1] - cb[3] if fb[1] >= cb[3] - 3 else None)
        if gap is not None and gap <= 40: cand.append((gap, f))
    cand.sort(key=lambda x: x[0])
    if not cand or (len(cand) > 1 and cand[1][0] - cand[0][0] < 6): return None
    return cand[0][1]

@guarded('caption')
def tie_caption(cap, wrapper_style):
    cpg = eff_pg.get(cap.objgen) or min((p for p, m in desc_mcids(cap) if p), default=None)
    if cpg is None:
        reject(f'caption {cap.objgen}', 'caption has no content on any page'); return
    cap.S = pikepdf.Name('/Caption')
    par = parent_of[cap.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, cap))
    prv = ks[i - 1] if i > 0 else None
    if is_elem(prv) and wrapper_style and S(prv) == wrapper_style:
        prv.S = pikepdf.Name('/Div'); detach(cap); cap.P = prv; set_kids(prv, kids(prv) + [cap]); reindex()
        ok('figure: caption tied (existing wrapper → Div)'); return
    if figure_holder_for(prv, cap, cpg):
        prv.S = pikepdf.Name('/Div'); detach(cap); cap.P = prv; set_kids(prv, kids(prv) + [cap]); reindex()
        ok('figure: caption tied (figure holder just before it → Div)')
        if len(kids(prv)) > 2: log.setdefault('captions_grouped', []).append({'page': cpg, 'figures': len(kids(prv)) - 1,
                                                                            'caption': norm_ws(elem_text(cap))[:60]})
        return
    fig = [e for e, _ in all_elems() if S(e) == 'Figure' and eff_pg.get(e.objgen) == cpg]
    if len(fig) == 1: f = fig[0]
    else:
        f = pick_figure(cap, cpg, fig) if fig else None
        if f is None:
            ok('figure: caption retyped only'); log['deferred'].append({'page': cpg, 'what': 'caption', 'why': f'{len(fig)} figures on page'}); return
        ok('figure: caption paired by position (several figures on the page)')
        log.setdefault('captions_paired', []).append({'page': cpg, 'caption': norm_ws(elem_text(cap))[:60]})
    CLAIMED.add(f.objgen)
    fpar = parent_of[f.objgen]
    blk = fpar if not (is_container(fpar) or S(fpar) == 'Document') else f
    bpar = parent_of[blk.objgen]
    anchor = next((j for j, k in enumerate(kids(bpar)) if same(k, blk)), len(kids(bpar)))
    detach(f); detach(cap)
    if is_container(par) and not kids(par): detach(par)
    div = new_elem('Div', bpar, [f, cap], pg=cpg); f.P = div; cap.P = div
    ks2 = kids(bpar)
    if same(blk, f): j = None
    else:
        j = next((j for j, k in enumerate(ks2) if same(k, blk)), -1)
        if j == -1: j = min(anchor, len(ks2)) - 1     # the figure sat inside the caption itself: the pair takes the caption's place
    set_kids(bpar, ks2 + [div] if j is None else ks2[:j + 1] + [div] + ks2[j + 1:])
    reindex(); ok('figure: caption tied (figure moved out of its paragraph)')
    if not same(blk, f) and blk.objgen in parent_of:             # the paragraph that held the figure may now be empty
        if 'refs' not in REFS: REFS['refs'] = struct_refs()
        if provably_empty(blk, REFS['refs']):
            set_kids(bpar, [k for k in kids(bpar) if not same(k, blk)]); reindex()
            ok('figure: empty figure-holder paragraph removed (proven empty)')
            log.setdefault('empty_holders_removed', []).append({'page': cpg, 'tag': S(blk)})
REFS = {}
def figure_holder_for(prv, cap, cpg):
    """The element just before a caption is its figures' group when it holds nothing but Figures (no text or content of
    its own), those figures are on the caption's page, and the caption sits below them."""
    if not is_elem(prv) or is_container(prv) or S(prv) in ('Document', 'Div', 'Figure') or mapped(S(prv)) in ('Figure', 'Table', 'L', 'TOC'): return False
    ks = kids(prv)
    if not ks or not all(is_elem(k) and mapped(S(k)) == 'Figure' for k in ks): return False
    if any(k in prv for k in ('/Alt', '/ActualText')): return False
    if any(eff_pg.get(k.objgen) != cpg for k in ks): return False
    cb = box_of(cap, cpg); fbs = [box_of(k, cpg) for k in ks]
    if cb is None or any(b is None for b in fbs): return False
    return cb[1] >= max(b[3] for b in fbs) - 2
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
    """Contents entries → TOC/TOCI. Entries are chosen by style (item_styles list, or item_prefix) and optionally limited
    to a page range; each run of consecutive sibling entries becomes one TOC (a contents page split over two pages, or
    interrupted by its heading, gives two)."""
    reindex()
    styles = set(spec.get('item_styles') or []); prefix = spec.get('item_prefix'); pr = spec.get('pages')
    def is_entry(e):
        if not (S(e) in styles or (prefix and S(e).startswith(prefix))): return False
        if pr:
            pgs = pp(e)
            if not pgs or min(pgs) < pr[0] or max(pgs) > pr[1]: return False
        return True
    entries = [e for e, _ in all_elems() if is_entry(e)]
    if not entries: reject('toc', 'no entries with those styles on those pages'); return
    done = set(); built = 0
    for first in entries:
        if first.objgen in done or first.objgen not in parent_of: continue
        par = parent_of[first.objgen]; ks = kids(par); i = next(j for j, k in enumerate(ks) if same(k, first))
        run = []
        for k in ks[i:]:
            if is_elem(k) and is_entry(k): run.append(k)
            else: break
        toc = new_elem('TOC', par, [], pg=eff_pg.get(first.objgen))
        for k in run: k.S = pikepdf.Name('/TOCI'); k.P = toc; done.add(k.objgen)
        set_kids(toc, run); set_kids(par, ks[:i] + [toc] + ks[i + len(run):]); reindex(); built += 1
        ok('contents: TOC entries', len(run))
    ok('contents: TOC built', built)

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
    if o is None: reject(f'lang {PG(pno)} m{m}', 'run not in tree'); return
    if S(o) == 'Span' and len(kids(o)) == 1: o.Lang = pikepdf.String(lang); ok(f'language: {lang} on existing Span'); return
    i = mc_entry_index(o, pno, m)
    if i is None: reject(f'lang {PG(pno)} m{m}', 'entry not found'); return
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
            log['deferred'].append({'page': pno, 'what': 'link on a page with no tagged text', 'why': f'tied to tagged text on {PG(npg)}'})
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
    reindex(); describe_url_links(live)

URL_ONLY = re.compile(r'\s*(?:https?://|www\.)\S+\s*')
INLINE = {'Link', 'Span', 'Reference', 'Quote', 'Note', 'Code', 'Lbl', 'Em', 'Strong', 'Sub', 'BibEntry'}
def describe_url_links(live):
    """A link whose description is only a URL gets the book's own sentence around it, with the URL removed: no new words.
    In a caption the whole caption is used. If no words are left, the description stays and the link is listed for a
    person. A link address that looks broken (an unmatched closing bracket or trailing punctuation) is listed, not changed."""
    out = log.setdefault('link_descriptions', [])
    for pno, a in live:
        act = a.get('/A'); uri = str(act.get('/URI', '')) if act is not None and str(act.get('/S')) == '/URI' else ''
        if uri and (uri.count(')') > uri.count('(') or uri.count(']') > uri.count('[') or re.search(r'[.,;:]$', uri)):
            log.setdefault('link_addresses_suspect', []).append({'page': pno, 'uri': uri,
                'why': 'the address ends with punctuation or an unmatched closing bracket from the printed text; probably broken'})
        cur = str(a.get('/Contents', ''))
        if not URL_ONLY.fullmatch(cur) and not (uri and cur.strip(' .,;:()') == uri.strip(' .,;:()')): continue
        el = None
        if '/StructParent' in a:
            r = nt_find(st.ParentTree, int(a.StructParent)); el = r[0].Nums[r[1]] if r else None
        blk = el if isinstance(el, pikepdf.Dictionary) else None
        while blk is not None and blk.objgen in parent_of and mapped(S(blk)) in INLINE: blk = parent_of[blk.objgen]
        entry = {'page': pno, 'url': uri or cur.strip(), 'description': None}
        text = elem_text(blk) if blk is not None and blk.objgen in parent_of else ''
        printed = ''.join(c['text'] for c in rect_chars(pno, a))
        hit = None
        def trim(u):                                  # a closing bracket the URL has no opening for belongs to the sentence
            u = u.rstrip('.,;:')
            while u.endswith(')') and u.count(')') > u.count('('): u = u[:-1].rstrip('.,;:')
            return u
        for cand in sorted({trim(re.sub(r'\s+', '', printed)), trim(uri), trim(cur.strip())} - {''}, key=len, reverse=True):
            hit = re.search(r'[\s\u00ad\u2010-]*'.join(map(re.escape, cand)), text)   # the printed URL may break across lines
            if hit: break
        if hit is None:
            entry['why'] = 'the URL was not found in the text around the link'; out.append(entry); continue
        t = text[:hit.start()] + '\x00' + text[hit.end():]
        t = re.sub(r'\s+', ' ', t).strip()
        if mapped(S(blk)) != 'Caption':
            parts = re.split(r'(?<=[.!?])\s+(?=[A-Z\u00C0-\u024F\u201c"(\[]|\d{1,3}\.\s)', t)   # also before a note number
            t = next(p for p in parts if '\x00' in p)
        t = t.replace('\x00', '')
        t = re.sub(r'(?:https?://|www\.)\S+', '', t)            # other URLs in the same sentence: removed too, never rewritten
        t = re.sub(r'\(\s*\)|\[\s*\]|<\s*>', '', t)
        t = re.sub(r'\s+([.,;:!?)])', r'\1', re.sub(r'\s+', ' ', t)).strip()
        t = re.sub(r'([.,;:])[.,;:]+', r'\1', t).strip(' ,;:')
        t = re.sub(r'([.!?][\u201d"\u2019])[.,]', r'\1', t)
        t = re.sub(r'(?<=[.!?])\s+\d{1,3}\.$', '', t)        # the next note's number
        if not re.search(r'[^\W\d_]{2,}', t):
            entry['why'] = 'no words around the URL in its sentence; a person must write the description'; out.append(entry); continue
        a.Contents = pikepdf.String(t); entry['description'] = t; out.append(entry)
        ok('links: URL-only description replaced by the sentence around it')

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
        if target is None: reject(f'figure order {PG(fp)}', 'no target block'); continue
        set_kids(par, [k for k in kids(par) if not same(k, div)])
        tb, tp = target; tk = kids(tp); j = next(x for x, k in enumerate(tk) if same(k, tb))
        set_kids(tp, tk[:j + 1] + [div] + tk[j + 1:]); div.P = tp
        log.setdefault('figure_moves', []).append({'page': fp, 'label': labels.get(fp), 'was_after_page': max(prev_pages),
                                                   'now_after_page': max(pp(tb)) if pp(tb) else None})
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
                    elif is_pmcr(g): moved.append(g); pt_set_mcid(pidx[g.Pg.objgen] if '/Pg' in g else pg, int(g.MCID), ref)
                    elif is_mcr(g): moved.append(g)
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
                elif is_pmcr(k): p = pidx[k.Pg.objgen] if '/Pg' in k else dpg; moved.append(mcr(p, int(k.MCID))); pt_set_mcid(p, int(k.MCID), DOC)
                elif is_mcr(k): moved.append(k)
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
    FLATTENED.update(done)
    reindex()
FLATTENED = set()                             # everything inside a list or table the work order flattened



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

# ================================================================== always: tags proven empty are removed (source's or the run's)
TABLE_PARTS = {'TR', 'TH', 'TD', 'THead', 'TBody', 'TFoot'}
NOTABLE_EMPTY = {'Caption', 'Figure', 'Link', 'LI', 'Lbl', 'LBody', 'TOCI', 'Note', 'Reference'}
def _reference_map():
    """{objgen: [what refers to it]} for every reference to a structure element other than its parent's /K and its
    children's /P: ParentTree entries (each marked stale when the marked content it maps is no longer drawn, or no page,
    form or annotation uses the key), IDTree entries, and any other object (a /Ref, a bookmark, an annotation, …)."""
    refs = collections.defaultdict(list)
    skip = set()
    # who uses each ParentTree key, and which MCIDs each page / form really draws
    key_page = {int(p.obj['/StructParents']): i + 1 for i, p in enumerate(pages) if '/StructParents' in p.obj}
    key_annot, key_form = {}, {}
    for i, p in enumerate(pages, 1):
        for a in p.obj.get('/Annots') or []:
            if isinstance(a, pikepdf.Dictionary) and '/StructParent' in a: key_annot[int(a.StructParent)] = (i, str(a.get('/Subtype', '')).lstrip('/'))
        for x in (p.obj.get('/Resources', {}).get('/XObject') or {}).values():
            if isinstance(x, pikepdf.Stream) and '/StructParents' in x: key_form[int(x.StructParents)] = (i, x)
    drawn = {}
    def drawn_in(stream_like, key):
        if key not in drawn:
            try:
                drawn[key] = {int(ins.operands[1].MCID) for ins in pikepdf.parse_content_stream(stream_like)
                              if str(ins.operator) == 'BDC' and len(ins.operands) == 2 and isinstance(ins.operands[1], pikepdf.Dictionary) and '/MCID' in ins.operands[1]}
            except Exception: drawn[key] = set()
        return drawn[key]
    def pt_walk(node):
        skip.add(node.objgen) if node.is_indirect else None
        if '/Nums' in node:
            a = node.Nums
            for j in range(0, len(a), 2):
                key, v = int(a[j]), a[j + 1]
                if isinstance(v, pikepdf.Array):
                    if v.is_indirect: skip.add(v.objgen)
                    if key in key_page: where, d = key_page[key], drawn_in(pages[key_page[key] - 1], ('page', key))
                    elif key in key_form: where, d = key_form[key][0], drawn_in(key_form[key][1], ('form', key))
                    else: where, d = None, set()
                    for m, el in enumerate(v):
                        if isinstance(el, pikepdf.Dictionary) and el.is_indirect:
                            stale = where is None or m not in d
                            refs[el.objgen].append(f'ParentTree key {key}, MCID {m}' + (f' on {PG(where)}' if where else '')
                                                   + (' (stale: that marked content is not drawn there)' if stale and where else
                                                      ' (stale: no page or form uses this key)' if stale else ''))
                elif isinstance(v, pikepdf.Dictionary) and v.is_indirect:
                    if key in key_annot: refs[v.objgen].append(f'ParentTree key {key} (a {key_annot[key][1]} annotation on {PG(key_annot[key][0])})')
                    else: refs[v.objgen].append(f'ParentTree key {key} (stale: no annotation uses this key)')
        for k in node.get('/Kids') or []: pt_walk(k)
    if '/ParentTree' in st: pt_walk(st.ParentTree)
    def id_walk(node):
        skip.add(node.objgen) if node.is_indirect else None
        if '/Names' in node:
            nm = node.Names
            for j in range(0, len(nm), 2):
                if isinstance(nm[j + 1], pikepdf.Dictionary) and nm[j + 1].is_indirect:
                    refs[nm[j + 1].objgen].append(f'IDTree "{bytes(nm[j]).decode("latin-1")}"')
        for k in node.get('/Kids') or []: id_walk(k)
    if '/IDTree' in st: id_walk(st.IDTree)
    def is_se(d): return isinstance(d, pikepdf.Dictionary) and '/S' in d and '/P' in d
    def holder_name(o):
        if is_se(o): return f'{S(o)} tag' + (f' on {PG(pidx.get(o.Pg.objgen))}' if '/Pg' in o and o.Pg.objgen in pidx else '')
        if isinstance(o, pikepdf.Dictionary):
            if str(o.get('/Type')) == '/Annot' or '/Subtype' in o and '/Rect' in o: return f'a {str(o.get("/Subtype", "")).lstrip("/")} annotation'
            if '/Title' in o and ('/Parent' in o or '/First' in o): return 'a bookmark'
            return f'a {str(o.get("/Type", "object")).lstrip("/")}'
        return 'an array'
    def scan(o, skip_k, holder):
        items = o.items() if isinstance(o, pikepdf.Dictionary) else ((None, v) for v in o)
        for k, v in items:
            if k == '/P' or (k == '/K' and skip_k and not (isinstance(v, pikepdf.Array) and v.is_indirect)): continue
            if k in ('/ParentTree', '/IDTree') and isinstance(o, pikepdf.Dictionary) and str(o.get('/Type')) == '/StructTreeRoot': continue
            if isinstance(v, (pikepdf.Dictionary, pikepdf.Array)):
                if v.is_indirect:
                    if is_se(v) and holder is not None: refs[v.objgen].append(f'{k or "an entry"} of {holder}')
                else: scan(v, False, holder)
    for o in pdf.objects:
        if isinstance(o, (pikepdf.Dictionary, pikepdf.Array)) and o.objgen not in skip:
            st_root = isinstance(o, pikepdf.Dictionary) and str(o.get('/Type')) == '/StructTreeRoot'
            scan(o, is_se(o) or st_root, holder_name(o) if not st_root else None)
    return refs
def fix_empty_tags():
    """A tag is removed when it is proven empty: nothing under it holds content (marked content, an annotation), it
    carries no Alt, ActualText, E or ID, and nothing in the file refers to it except its parent. This holds whether the
    source or the run emptied it, and repeats until nothing changes (removing a child can empty its parent). Table
    cells and rows are never removed one by one; a table goes only when every part of it is empty. A tag that is
    empty but kept is reported with what keeps it (an attribute, or the exact reference, stale or not)."""
    reindex()
    refs = _reference_map()
    res = log['empty_tags'] = {'removed': [], 'tables_removed': [], 'kept': [], 'headings': [], 'notable': []}
    removed_ids = set()
    def blockers(n):
        why = [f'carries {k} "{str(n[k])[:40]}"' for k in ('/Alt', '/ActualText', '/E', '/ID') if k in n]
        return why + refs.get(n.objgen, [])
    def scan_subtree(n, acc, depth=0):
        """acc: {'content': bool, 'blocked': [(tag, why)]} for a whole subtree."""
        b = blockers(n)
        if b: acc['blocked'].append((n, b))
        if depth > 60: acc['content'] = True; return acc
        for k in kids(n):
            if isinstance(k, int) or is_mcr(k) or is_objr(k): acc['content'] = True
            elif is_elem(k): scan_subtree(k, acc, depth + 1)
            else: acc['content'] = True
        return acc
    def count_parts(n): return 1 + sum(count_parts(k) for k in kids(n) if is_elem(k))
    def record(n, par):
        t = mapped(S(n)); pgn = eff_pg.get(n.objgen)
        item = {'tag': S(n), 'type': t, 'page': pgn, 'from_flatten': n.objgen in FLATTENED}
        res['removed'].append(item); removed_ids.add(n.objgen)
        if re.fullmatch(r'H[1-6]?', t):
            found = None
            for e, _ in all_elems():
                if e.objgen == n.objgen or not re.fullmatch(r'H[1-6]?', mapped(S(e))): continue
                if pgn in pp(e):
                    txt = norm_ws(elem_text(e))
                    if txt: found = txt[:70]; break
            res['headings'].append({'tag': S(n), 'type': t, 'page': pgn, 'found': found})
        elif t in NOTABLE_EMPTY: res['notable'].append(item)
    kept_seen = {}
    changed = True
    while changed:
        changed = False
        for el, par in all_elems():
            if same(el, DOC) or el.objgen not in parent_of or not any(same(k, el) for k in kids(par)): continue
            t = mapped(S(el))
            if t in TABLE_PARTS: continue                          # only with their whole table
            if t == 'Table':
                acc = scan_subtree(el, {'content': False, 'blocked': []})
                if acc['content']: continue                        # a real table: its empty cells stay
                if acc['blocked']:
                    kept_seen[el.objgen] = {'tag': S(el), 'type': t, 'page': eff_pg.get(el.objgen),
                                            'why': [f'{S(n)} inside it: {w}' if not same(n, el) else w for n, ws in acc['blocked'] for w in ws][:6]}
                    continue
                n = count_parts(el); record(el, par); res['tables_removed'].append({'page': eff_pg.get(el.objgen), 'parts': n})
                set_kids(par, [k for k in kids(par) if not same(k, el)]); changed = True
                ok('structure: empty table removed (every part proven empty)'); continue
            if kids(el): continue
            b = blockers(el)
            if b:
                kept_seen[el.objgen] = {'tag': S(el), 'type': t, 'page': eff_pg.get(el.objgen), 'why': b}; continue
            record(el, par)
            set_kids(par, [k for k in kids(par) if not same(k, el)]); changed = True
            ok('structure: empty tag removed (proven empty)')
        if changed: reindex()
    res['kept'] = [v for og, v in kept_seen.items() if og not in removed_ids]
    # in the same pass: no index entry may point at a removed tag (by the proof there are none; clear any that appear)
    cleared = 0
    def clear(node):
        nonlocal cleared
        if '/Nums' in node:
            a = node.Nums
            for j in range(1, len(a), 2):
                v = a[j]
                if isinstance(v, pikepdf.Array):
                    for i in range(len(v)):
                        if isinstance(v[i], pikepdf.Dictionary) and v[i].objgen in removed_ids: v[i] = None; cleared += 1
                elif isinstance(v, pikepdf.Dictionary) and v.objgen in removed_ids: a[j] = None; cleared += 1
        for k in node.get('/Kids') or []: clear(k)
    if removed_ids and '/ParentTree' in st: clear(st.ParentTree)
    if removed_ids and '/IDTree' in st:
        def clear_ids(node):
            nonlocal cleared
            if '/Names' in node:
                nm = list(node.Names); keep = []
                for j in range(0, len(nm), 2):
                    if isinstance(nm[j + 1], pikepdf.Dictionary) and nm[j + 1].objgen in removed_ids: cleared += 1
                    else: keep += [nm[j], nm[j + 1]]
                if len(keep) != len(nm): node.Names = pikepdf.Array(keep)
            for k in node.get('/Kids') or []: clear_ids(k)
        clear_ids(st.IDTree)
    if cleared:
        log['failed'].append({'op': 'fix_empty_tags', 'error': f'{cleared} index entries pointed at tags proven unreferenced; cleared (this should not happen)'})

# ================================================================== always: bookmarks from the heading tags, when the file has none
HEADING_LEVEL = {'H1': 1, 'H2': 2, 'H3': 3, 'H4': 4, 'H5': 5, 'H6': 6}
def fix_outline():
    """Only when the file has heading tags and no bookmarks at all: build them from the headings, in tag-tree order,
    nested by level. Title = the heading's ActualText if it has one, else its text; target = the heading's page and top.
    An existing bookmark tree is never touched."""
    ol_root = pdf.Root.get('/Outlines')
    if ol_root is not None and '/First' in ol_root:
        log['bookmarks'] = {'built': False, 'why': 'the file already has bookmarks'}; return
    reindex(); heads = []
    for el, _ in all_elems():
        lvl = HEADING_LEVEL.get(mapped(S(el)))
        if not lvl: continue
        title = norm_ws(str(el.get('/ActualText'))) if '/ActualText' in el else norm_ws(elem_text(el))
        ms = desc_mcids(el, eff_pg.get(el.objgen)); pg = eff_pg.get(el.objgen) or min((p for p, _ in ms if p), default=None)
        if not title or pg is None: continue
        mine = {m for p, m in ms if p == pg}
        tops = [c['top'] for c in PL.pages[pg - 1].chars if c.get('mcid') in mine]
        mb = pages[pg - 1].mediabox; y = float(mb[3]) - (min(tops) if tops else 0) + 4
        heads.append((lvl, title[:200], pg, y))
    if not heads:
        log['bookmarks'] = {'built': False, 'why': 'no heading tags with text'}; return
    with pdf.open_outline() as outline:
        stack = []                                   # (level, OutlineItem)
        for lvl, title, pg, y in heads:
            item = pikepdf.OutlineItem(title, pg - 1, 'XYZ', top=y)
            while stack and stack[-1][0] >= lvl: stack.pop()
            (stack[-1][1].children if stack else outline.root).append(item)
            stack.append((lvl, item))
    log['bookmarks'] = {'built': True, 'items': len(heads)}; ok('bookmarks: built from heading tags', len(heads))

# ================================================================== always: a page with no tags at all that holds a drawing becomes one Figure
def _page_inventory(page):
    """What a page draws, through its form XObjects: marked content, decoration, images, painted paths, and text shown
    painted or invisible (render mode 3: neither filled nor stroked, the usual hidden OCR layer). Mode 7 text is a
    clipping shape for what is painted next (e.g. map labels filled with a texture), so it counts as drawn."""
    inv = collections.Counter()
    def walk(stream, res, tr, depth=0):
        if depth > 12: return
        xo = (res or {}).get('/XObject') or {}; gs = []; path = False
        for ins in pikepdf.parse_content_stream(stream):
            op, ops = str(ins.operator), ins.operands
            if op in ('BDC', 'BMC'):
                if str(ops[0]) == '/Artifact': inv['artifact'] += 1
                if len(ops) > 1 and isinstance(ops[1], pikepdf.Dictionary) and '/MCID' in ops[1]: inv['mcid'] += 1
            elif op == 'q': gs.append(tr)
            elif op == 'Q': tr = gs.pop() if gs else tr
            elif op == 'Tr': tr = int(ops[0])
            elif op in PATH_OPS: path = True
            elif op == 'n': path = False
            elif op in PAINT_OPS and path: inv['paths'] += 1; path = False
            elif op in TEXT_OPS: inv['hidden_text' if tr == 3 else 'text'] += 1
            elif op in ('BI', 'INLINE IMAGE', 'sh'): inv['images'] += 1
            elif op == 'Do':
                x = xo.get(ops[0])
                if x is None: continue
                if str(x.get('/Subtype')) == '/Image': inv['images'] += 1
                elif str(x.get('/Subtype')) == '/Form': walk(x, x.get('/Resources') or res, tr, depth + 1)
    walk(page, page.obj.get('/Resources'), 0)
    return inv
def _anchor_for(pno):
    """The block holding the last tagged content on this page (climbing out of inline elements), or None."""
    last = None
    for e, par in all_elems():
        if any(p == pno for p, _ in own_mcids(e, eff_pg.get(e.objgen))): last = e
    if last is None: return None
    while last.objgen in parent_of and not (is_container(parent_of[last.objgen]) or S(parent_of[last.objgen]) in BLOCK_PARENTS):
        last = parent_of[last.objgen]
    return last if last.objgen in parent_of else None
def fix_page_figures():
    """A page on which nothing is tagged and nothing is marked as decoration, with no annotations, no hidden text layer,
    and at least one image or painted path (a full-page map, plate or cover) is wrapped whole in one Figure: one
    marked-content sequence around its content stream, with a bounding box, placed in reading order after the block
    holding the last tagged content before it (a paragraph that runs across the page goes first), or first in the
    Document when nothing comes before it. Nothing on the page is changed or removed. Alt text comes only from the
    work order (page_figures); without it the Figure has no alt and review.md asks a person to write one."""
    reindex()
    alts = {}
    for item in wo.get('page_figures') or []:
        try: alts[int(item['page'])] = str(item.get('alt') or '').strip()
        except Exception: reject(f'page_figures {item}', 'needs a page number')
    res = log['page_figures'] = {'wrapped': [], 'left': []}
    for pno in range(1, len(pages) + 1):
        page = pages[pno - 1]
        pc = PL.pages[pno - 1]
        if any(c.get('mcid') is not None or c.get('tag') == 'Artifact' for c in pc.chars + pc.images): continue
        inv = _page_inventory(page)
        if inv['mcid'] or inv['artifact']: continue                     # something on it is tagged or decoration
        if not (inv['images'] or inv['paths'] or inv['text'] or inv['hidden_text']): continue   # a blank page
        why = None
        if inv['hidden_text']: why = f'hidden text layer ({inv["hidden_text"]} text operators in render mode 3, e.g. OCR): the page is text, not a figure'
        elif page.obj.get('/Annots'): why = f'has {len(page.obj.Annots)} annotation(s) (links)'
        elif not (inv['images'] or inv['paths']): why = 'only text is drawn (no image or path): real text, not a figure'
        if why:
            res['left'].append({'page': pno, 'label': labels.get(pno), 'why': why})
            if pno in alts: reject(f'page_figures {PG(pno)}', f'page not wrapped: {why}')
            continue
        with pdfplumber.open(SRC, pages=[pno]) as one:
            pg = one.pages[0]; H = float(pg.height)
            objs = pg.chars + pg.images + pg.rects + pg.lines + pg.curves
            W = float(pg.width)
            if not objs: objs = [{'x0': 0, 'x1': W, 'top': 0, 'bottom': H}]           # e.g. only a shading: the whole page
            x0 = max(0, min(o['x0'] for o in objs)); x1 = min(W, max(o['x1'] for o in objs))
            top = max(0, min(o['top'] for o in objs)); bot = min(H, max(o['bottom'] for o in objs))
        mb = [float(v) for v in page.mediabox]
        bbox = pikepdf.Array([round(x0 + mb[0], 2), round(H - bot + mb[1], 2), round(x1 + mb[0], 2), round(H - top + mb[1], 2)])
        c = page.obj.Contents
        data = b'\n'.join(x.read_bytes() for x in c) if isinstance(c, pikepdf.Array) else c.read_bytes()
        page.obj.Contents = pdf.make_stream(b'/Figure <</MCID 0>> BDC\n' + data + b'\nEMC\n')
        anc, q = None, pno - 1
        while anc is None and q >= 1: anc = _anchor_for(q); q -= 1
        host = parent_of[anc.objgen] if anc is not None else DOC
        extra = {'A': pikepdf.Dictionary(O=pikepdf.Name('/Layout'), BBox=bbox, Placement=pikepdf.Name('/Block'))}
        if alts.get(pno): extra['Alt'] = pikepdf.String(alts[pno])
        fig = new_elem('Figure', host, [0], pg=pno, **extra)
        ks = kids(host)
        if anc is None: set_kids(host, [fig] + ks)
        else:
            j = next(i for i, k in enumerate(ks) if same(k, anc)); set_kids(host, ks[:j + 1] + [fig] + ks[j + 1:])
        for o in pc.chars + pc.images: o['mcid'] = 0
        reindex()
        res['wrapped'].append({'page': pno, 'label': labels.get(pno), 'alt': bool(alts.get(pno)),
                               'after': 'start of the document' if anc is None else f'"{norm_ws(elem_text(anc))[-50:]}" ' + (f'on {PG(max(pp(anc)))}' if pp(anc) else '(page: not on this tag)'),
                               'objects': {k: inv[k] for k in ('images', 'paths', 'text')}})
        ok('figure: whole page wrapped as one Figure')
        if alts.get(pno): ok('figure: alt text from the work order (page figure)')
    for p in alts:
        if not any(w['page'] == p for w in res['wrapped']) and not any(l['page'] == p for l in res['left']):
            reject(f'page_figures {PG(p)}', 'page has tagged content or decoration (or nothing drawn); not wrapped')

# ================================================================== always: untagged paths that carry no content become decoration
PAINT_OPS = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'}
PATH_OPS = {'m', 'l', 'c', 'v', 'y', 're', 'h', 'W', 'W*'}
STROKES, FILLS = {'S', 's', 'B', 'B*', 'b', 'b*'}, {'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'}
PATH_LEAVE = {   # why an untagged path was left alone, in the order the tests run
    'rotated': 'page is rotated: positions not checked',
    'props': 'inside marked content that carries properties (ActualText, optional content)',
    'pattern': 'painted with a pattern (a pattern can draw text or images)',
    'annot': 'overlaps a link or other annotation',
    'drawing': 'part of an untagged drawing (touches untagged text or images): a person should tag it as a Figure with alt text',
    'tagged': 'in a shared form that is also drawn inside tagged content'}
def _mul(a, b): return [a[0]*b[0] + a[1]*b[2], a[0]*b[1] + a[1]*b[3], a[2]*b[0] + a[3]*b[2], a[2]*b[1] + a[3]*b[3],
                        a[4]*b[0] + a[5]*b[2] + b[4], a[4]*b[1] + a[5]*b[3] + b[5]]
def _pt(m, x, y): return (m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5])
def _touch(b, boxes, pad=1.0):
    return any(b[0] - pad < x1 and x0 < b[2] + pad and b[1] - pad < y1 and y0 < b[3] + pad for x0, y0, x1, y1 in boxes)
def fix_paths():
    """A vector path (a rule, border, box or line) drawn outside any tag and outside any artifact is marked as decoration
    when nothing ties it to content: it is not inside marked content that carries properties, it is not painted with a
    pattern, it does not overlap an annotation, and it does not touch untagged text or untagged images on its page (that
    would make it part of an untagged drawing, which needs a Figure tag instead). A path in a shared form XObject is
    changed only if it qualifies everywhere the form is drawn; the form is edited once."""
    parsed, streams, rec, spans, under = {}, {}, collections.defaultdict(list), {}, collections.defaultdict(int)
    def instrs(key, stream):
        if key not in parsed: parsed[key] = list(pikepdf.parse_content_stream(stream)); streams[key] = stream
        return parsed[key]
    def page_ctx(pno):
        page = pages[pno - 1]; mb = [float(v) for v in page.mediabox]; H = float(PL.pages[pno - 1].height)
        pc = PL.pages[pno - 1]
        free = [c for c in pc.chars if c.get('mcid') is None and c.get('tag') != 'Artifact']
        free += [i for i in pc.images if i.get('mcid') is None and i.get('tag') != 'Artifact']
        boxes = [(c['x0'], H - c['bottom'], c['x1'], H - c['top']) for c in free]
        tagged = [(c['x0'], H - c['bottom'], c['x1'], H - c['top']) for c in pc.chars if c.get('mcid') is not None]
        annots = []
        for a in page.obj.get('/Annots') or []:
            if isinstance(a, pikepdf.Dictionary) and '/Rect' in a:
                r = [float(v) for v in a.Rect]
                annots.append((min(r[0], r[2]) - mb[0], min(r[1], r[3]) - mb[1], max(r[0], r[2]) - mb[0], max(r[1], r[3]) - mb[1]))
        return {'boxes': boxes, 'tagged': tagged, 'annots': annots, 'rotated': int(page.obj.get('/Rotate', 0)) % 360 != 0,
                'ctm': [1, 0, 0, 1, -mb[0], -mb[1]], 'thin': []}
    def underline(b, tagged):
        """A thin horizontal stroke sitting under one run of tagged text, no wider than the text: listed for a person,
        because an underline can carry meaning (emphasis, a sound in a romanization)."""
        if b[3] - b[1] > 1.5 or b[2] - b[0] < 2: return False
        above = sorted((t for t in tagged if t[0] < b[2] and b[0] < t[2] and t[1] - 3 <= b[3] <= t[1] + 0.4 * (t[3] - t[1])), key=lambda t: t[0])
        if not above: return False
        if any(y[0] - x[2] > 6 for x, y in zip(above, above[1:])): return False
        covered = sum(max(0, min(b[2], t[2]) - max(b[0], t[0])) for t in above)
        return above[0][0] - 3 <= b[0] and b[2] <= above[-1][2] + 3 and covered >= 0.6 * (b[2] - b[0])
    def scan(key, stream, ctm, pno, res, outer, ctx, depth=0):
        if depth > 12: return
        stack, gs, m, fpat, spat, start, pts = [], [], ctm, False, False, None, []
        xo = (res or {}).get('/XObject') or {}
        for i, ins in enumerate(instrs(key, stream)):
            op, ops = str(ins.operator), ins.operands
            if start is not None and op not in PATH_OPS and op not in PAINT_OPS and op != 'n':
                start, pts = None, []            # something other than path building inside a path: leave that path alone
            if op in ('BDC', 'BMC'):
                props = ops[1] if len(ops) > 1 else None
                stack.append('art' if str(ops[0]) == '/Artifact' else 'mc' if isinstance(props, pikepdf.Dictionary) and '/MCID' in props
                             else 'props' if props is not None else 'plain'); continue
            if op == 'EMC':
                if stack: stack.pop()
                continue
            if op == 'q': gs.append((m, fpat, spat)); continue
            if op == 'Q':
                if gs: m, fpat, spat = gs.pop()
                continue
            if op == 'cm': m = _mul([float(v) for v in ops], m); continue
            if op in ('cs', 'g', 'rg', 'k', 'sc'): fpat = False; continue
            if op in ('CS', 'G', 'RG', 'K', 'SC'): spat = False; continue
            if op == 'scn': fpat = bool(ops) and isinstance(ops[-1], pikepdf.Name); continue
            if op == 'SCN': spat = bool(ops) and isinstance(ops[-1], pikepdf.Name); continue
            if op in PATH_OPS:
                if start is None: start = i
                if op in ('m', 'l'): pts.append(_pt(m, float(ops[0]), float(ops[1])))
                elif op == 'c': pts += [_pt(m, float(ops[k]), float(ops[k + 1])) for k in (0, 2, 4)]
                elif op in ('v', 'y'): pts += [_pt(m, float(ops[k]), float(ops[k + 1])) for k in (0, 2)]
                elif op == 're':
                    x, y, w, h = (float(v) for v in ops)
                    pts += [_pt(m, x, y), _pt(m, x + w, y), _pt(m, x, y + h), _pt(m, x + w, y + h)]
                continue
            if op == 'n': start, pts = None, []; continue
            if op in PAINT_OPS:
                if start is not None and pts and not ('art' in stack or 'mc' in stack) and outer != 'art':
                    if outer == 'mc': rec[(key, i)].append('tagged')
                    else:
                        xs, ys = [p[0] for p in pts], [p[1] for p in pts]; b = (min(xs), min(ys), max(xs), max(ys))
                        v = ('rotated' if ctx['rotated'] else 'props' if 'props' in stack
                             else 'pattern' if (fpat and op in FILLS) or (spat and op in STROKES)
                             else 'annot' if _touch(b, ctx['annots'], 0) else 'drawing' if _touch(b, ctx['boxes']) else 'ok')
                        rec[(key, i)].append(v); spans[(key, i)] = start
                        if v == 'ok' and b[3] - b[1] <= 1.5: ctx['thin'].append(b)
                        if v == 'ok' and underline(b, ctx['tagged']): under[(key, i, pno)] = b
                start, pts = None, []; continue
            if op == 'Do':
                x = xo.get(ops[0])
                if x is not None and str(x.get('/Subtype')) == '/Form':
                    inner = outer or ('art' if 'art' in stack else 'mc' if 'mc' in stack else None)
                    fm = [float(v) for v in x.get('/Matrix', [1, 0, 0, 1, 0, 0])]
                    scan(('form', x.objgen), x, _mul(fm, m), pno, x.get('/Resources') or res, inner, ctx, depth + 1)
    for pno in range(1, len(pages) + 1):
        page = pages[pno - 1]; ctx = page_ctx(pno)
        scan(('page', pno), page, ctx['ctm'], pno, page.obj.get('/Resources'), None, ctx)
        for k in [k for k in under if k[2] == pno]:       # a segment of a longer ruled line (a table rule) is not an underline
            b = under[k]
            if any(t is not b and abs(t[1] - b[1]) < 0.75 and (abs(t[0] - b[2]) < 1.5 or abs(b[0] - t[2]) < 1.5) for t in ctx['thin']): del under[k]
    take = collections.defaultdict(dict); left = collections.Counter(); left_pages = collections.defaultdict(set)
    first_page = {}
    for (key, i, pno) in under: first_page.setdefault((key, i), pno)
    for (key, i), vs in rec.items():
        if all(v == 'ok' for v in vs): take[key][i] = spans[(key, i)]
        else:
            why = next(k for k in PATH_LEAVE if k in vs); left[why] += 1
            if key[0] == 'page': left_pages[why].add(key[1])
    props = pikepdf.Dictionary(Type=pikepdf.Name('/Layout')); n = 0
    for key, paints in take.items():
        starts = set(paints.values()); out = []
        for i, ins in enumerate(parsed[key]):
            if i in starts: out.append(pikepdf.ContentStreamInstruction([pikepdf.Name('/Artifact'), props], pikepdf.Operator('BDC')))
            out.append(ins)
            if i in paints: out.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator('EMC'))); n += 1
        data = pikepdf.unparse_content_stream(out)
        if key[0] == 'page': pages[key[1] - 1].obj.Contents = pdf.make_stream(data)
        else: streams[key].write(data)
    ul = collections.Counter(p for (key, i, p) in under if i in take.get(key, {}))
    if n: ok('artifact: untagged path with no content (rule, border, line)', n)
    log['paths'] = {'artifacted': n, 'in_forms': sum(len(v) for k, v in take.items() if k[0] == 'form'),
                    'left': {PATH_LEAVE[k]: c for k, c in left.items()},
                    'left_pages': {PATH_LEAVE[k]: sorted(v)[:12] for k, v in left_pages.items()},
                    'underlines': [{'page': p, 'count': c} for p, c in sorted(ul.items())]}

# ================================================================== always: an invisible OCR text layer whose font defines no glyphs
OCR_FONT_NAMES = {'HiddenHorzOCR', 'HiddenVertOCR', 'GlyphLessFont'}
def _font_name(f): return str(f.get('/BaseFont', '')).lstrip('/').split('+')[-1]
def _glyph_count(f):
    """Glyphs in the embedded font program of a font; None if it has none; 'unreadable' if it can't be read."""
    import io
    d = f.DescendantFonts[0].get('/FontDescriptor') if str(f.get('/Subtype')) == '/Type0' else f.get('/FontDescriptor')
    if d is None: return None
    try:
        if '/FontFile3' in d:
            data = d.FontFile3.read_bytes()
            if str(d.FontFile3.get('/Subtype')) == '/OpenType':
                from fontTools.ttLib import TTFont
                return len(TTFont(io.BytesIO(data)).getGlyphOrder())
            from fontTools.cffLib import CFFFontSet, Index        # bare CFF: count the CharStrings index itself, which
            f = io.BytesIO(data); cff = CFFFontSet(); cff.decompile(f, None)   # also works with a predefined charset
            f.seek(cff.topDictIndex[0].rawDict['CharStrings']); return len(Index(f, isCFF2=False))
        if '/FontFile2' in d:
            from fontTools.ttLib import TTFont
            return len(TTFont(io.BytesIO(d.FontFile2.read_bytes())).getGlyphOrder())
        if '/FontFile' in d: return None
    except Exception: return 'unreadable'
    return None
def _blank_truetype(advances):
    """A tiny TrueType font: .notdef plus one empty (but defined) glyph per advance width, 1000 units per em."""
    import io
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    order = ['.notdef'] + [f'blank{k}' for k in range(len(advances))]
    fb = FontBuilder(1000, isTTF=True); fb.setupGlyphOrder(order); fb.setupCharacterMap({})
    pen = TTGlyphPen(None); pen.moveTo((0, 0)); pen.lineTo((0, 1)); pen.lineTo((1, 1)); pen.closePath()
    glyphs = {'.notdef': pen.glyph()}; glyphs.update({g: TTGlyphPen(None).glyph() for g in order[1:]})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({'.notdef': (max(advances), 0), **{g: (a, 0) for g, a in zip(order[1:], advances)}})
    fb.setupHorizontalHeader(ascent=1000, descent=-250)
    fb.setupNameTable({'familyName': 'GlyphLessOverlay', 'styleName': 'Regular'}); fb.setupOS2(); fb.setupPost()
    b = io.BytesIO(); fb.save(b); return b.getvalue()
def _cid_widths(cf):
    """{cid: width} from a CIDFont's /W array, and its default width."""
    dw = int(round(float(cf.get('/DW', 1000)))); out = {}; W = list(cf.get('/W') or []); i = 0
    while i < len(W):
        if isinstance(W[i + 1], pikepdf.Array):
            for k, w in enumerate(W[i + 1]): out[int(W[i]) + k] = int(round(float(w)))
            i += 2
        else:
            for c in range(int(W[i]), int(W[i + 1]) + 1): out[c] = int(round(float(W[i + 2])))
            i += 3
    return out, dw
def fix_ocr_fonts():
    """The hidden OCR layer of a scanned page is text drawn in render mode 3 (invisible). Some OCR tools embed a font
    program for it that holds only .notdef, so every character is undefined (PDF/UA 7.21.8, whatever the render mode).
    A font qualifies when its name is HiddenHorzOCR, HiddenVertOCR or GlyphLessFont, every use of it is in render mode 3,
    and its embedded program really holds only .notdef. Its program is swapped for a blank TrueType one in which every
    character code maps to a defined, empty glyph of the same width. Nothing else changes: same character codes, same
    ToUnicode map (so the same text is read aloud), same widths, still render mode 3. The swap is kept only if a replay
    shows no page looks different and no page's text changed; otherwise it is undone and reported."""
    import io
    use, fobj = collections.defaultdict(lambda: {'modes': collections.Counter(), 'pages': set(), 'refs': 0}), {}
    def walk(stream, pno, res, tr, depth=0):
        if depth > 12: return
        fonts = (res or {}).get('/Font') or {}; xo = (res or {}).get('/XObject') or {}; cur = None; gs = []
        for ins in pikepdf.parse_content_stream(stream):
            op, ops = str(ins.operator), ins.operands
            if op == 'q': gs.append((tr, cur))
            elif op == 'Q':
                if gs: tr, cur = gs.pop()
            elif op == 'Tf': cur = fonts.get(ops[0])
            elif op == 'Tr': tr = int(ops[0])
            elif op in TEXT_OPS and cur is not None and _font_name(cur) in OCR_FONT_NAMES:
                u = use[cur.objgen]; fobj[cur.objgen] = cur; u['modes'][tr] += 1; u['pages'].add(pno)
                strs = [ops[-1]] if op != 'TJ' else [y for y in ops[0] if isinstance(y, pikepdf.String)]
                u['refs'] += sum(len(bytes(s)) for s in strs) // (2 if str(cur.get('/Subtype')) == '/Type0' else 1)
            elif op == 'Do':
                x = xo.get(ops[0])
                if x is not None and str(x.get('/Subtype')) == '/Form': walk(x, pno, x.get('/Resources') or res, tr, depth + 1)
    for pno, page in enumerate(pages, 1): walk(page, pno, page.obj.get('/Resources'), 0)
    if not fobj: return
    res_log = log['ocr_fonts'] = {'replaced': [], 'left': []}
    todo = []
    for og, f in fobj.items():
        u, name = use[og], _font_name(f)
        if set(u['modes']) != {3}:
            res_log['left'].append({'font': name, 'why': f'also drawn visibly (render modes {sorted(u["modes"])}); not changed'}); continue
        if str(f.get('/Subtype')) != '/Type0':
            res_log['left'].append({'font': name, 'why': 'not a Type0 (CID) font; not changed'}); continue
        g = _glyph_count(f)
        if g == 'unreadable':
            res_log['left'].append({'font': name, 'why': 'its embedded font program could not be read; not changed'}); continue
        if g != 1: continue                       # no program (exempt in mode 3), or it already defines glyphs: nothing to fix
        todo.append(f)
    if not todo: _group_left(res_log); return
    before = io.BytesIO(); pdf.save(before)
    undo = []
    try: _swap_and_replay(todo, use, undo, before, res_log)
    except Exception:
        for f, d, bf in undo: f.DescendantFonts = d; f.BaseFont = bf
        raise
def _swap_and_replay(todo, use, undo, before, res_log):
    import io
    f_name, shared = {}, {}
    for f in todo:
        cf = f.DescendantFonts[0]; widths, dw = _cid_widths(cf)
        advances = sorted({dw, *widths.values()}); gid = {a: k + 1 for k, a in enumerate(advances)}
        cmap = bytearray(gid[dw].to_bytes(2, 'big') * 65536)
        for c, w in widths.items():
            if 0 <= c < 65536: cmap[2 * c:2 * c + 2] = gid[w].to_bytes(2, 'big')
        if tuple(advances) not in shared:              # fonts with the same widths share one program and one map
            ttf = pdf.make_stream(_blank_truetype(advances)); ttf.Length1 = len(ttf.read_bytes()); shared[tuple(advances)] = ttf
        ttf = shared[tuple(advances)]
        mk = hashlib.sha256(bytes(cmap)).hexdigest()
        if mk not in shared: shared[mk] = pdf.make_stream(bytes(cmap))
        od = cf.get('/FontDescriptor') or pikepdf.Dictionary()
        desc = pikepdf.Dictionary(Type=pikepdf.Name('/FontDescriptor'), FontName=pikepdf.Name('/GlyphLessOverlay'), Flags=4,
                                  FontBBox=pikepdf.Array([0, -250, max(advances), 1000]), ItalicAngle=0, Ascent=1000, Descent=-250,
                                  CapHeight=1000, StemV=80, FontFile2=ttf)
        nd = pikepdf.Dictionary(Type=pikepdf.Name('/Font'), Subtype=pikepdf.Name('/CIDFontType2'), BaseFont=pikepdf.Name('/GlyphLessOverlay'),
                                CIDSystemInfo=cf.CIDSystemInfo, FontDescriptor=pdf.make_indirect(desc), CIDToGIDMap=shared[mk], DW=dw)
        for k in ('/W', '/W2', '/DW2'):
            if k in cf: nd[k] = cf[k]
        undo.append((f, f.DescendantFonts, f.BaseFont)); f_name[f.objgen] = _font_name(f)
        f.DescendantFonts = pikepdf.Array([pdf.make_indirect(nd)]); f.BaseFont = pikepdf.Name('/GlyphLessOverlay')
    after = io.BytesIO(); pdf.save(after)
    check = sorted(set().union(*(use[f.objgen]['pages'] for f in todo)))
    import pypdfium2 as pdfium
    A, B, differ, changed = pdfium.PdfDocument(before.getvalue()), pdfium.PdfDocument(after.getvalue()), [], []
    for pno in check:
        a, b = A[pno - 1], B[pno - 1]
        if a.render(scale=1).to_pil().tobytes() != b.render(scale=1).to_pil().tobytes(): differ.append(pno)
        ta, tb = a.get_textpage(), b.get_textpage()
        if ta.get_text_range() != tb.get_text_range(): changed.append(pno)
    A.close(); B.close()
    if differ or changed:
        for f, d, bf in undo: f.DescendantFonts = d; f.BaseFont = bf
        log['deferred'].append({'what': 'invisible OCR-layer font with no defined glyphs: blank-glyph replacement undone',
                                'why': f'the replay showed {len(differ)} pages looking different ({", ".join(map(PG, differ[:8]))}) and {len(changed)} pages with changed text ({", ".join(map(PG, changed[:8]))}); a person must fix the font'})
        res_log['left'] += [{'font': f_name[f.objgen], 'why': 'replay showed a change; replacement undone'} for f, _, _ in undo]
        _group_left(res_log); return
    names = collections.Counter(f_name[f.objgen] for f, _, _ in undo)
    for nm, c in names.items():
        fs = [f for f, _, _ in undo if f_name[f.objgen] == nm]
        res_log['replaced'].append({'font': nm, 'font_objects': c, 'pages': len(set().union(*(use[f.objgen]['pages'] for f in fs))),
                                    'glyph_references': sum(use[f.objgen]['refs'] for f in fs), 'pages_replayed': len(check)})
    ok('fonts: invisible OCR-layer font given defined blank glyphs', len(undo))
    _group_left(res_log)
def _group_left(res_log):
    c = collections.Counter((x['font'], x['why']) for x in res_log['left'] if 'font_objects' not in x)
    res_log['left'] = [x for x in res_log['left'] if 'font_objects' in x] + [{'font': f, 'why': w, 'font_objects': n} for (f, w), n in c.items()]

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

# ================================================================== always, after the index is rebuilt: no entry may point outside the tree
def fix_index():
    """ParentTree and IDTree entries that point at a tag no longer reachable from the StructTreeRoot (dangling) are
    cleared: a ParentTree entry becomes null (its key stays, so no page, form or annotation loses its index), and the
    IDTree is rewritten without the dangling names. Nothing on a page, no text and no reachable tag changes."""
    tree = set(); stack = list(kids(st))
    while stack:
        n = stack.pop()
        if is_elem(n): tree.add(n.objgen); stack += kids(n)
    key_page = {int(p.obj['/StructParents']): i + 1 for i, p in enumerate(pages) if '/StructParents' in p.obj}
    res = log['index_cleanup'] = {'parenttree': [], 'idtree': []}
    def walk(node):
        if '/Nums' in node:
            a = node.Nums
            for j in range(1, len(a), 2):
                key, v = int(a[j - 1]), a[j]
                if isinstance(v, pikepdf.Array):
                    for m in range(len(v)):
                        el = v[m]
                        if isinstance(el, pikepdf.Dictionary) and el.objgen not in tree:
                            res['parenttree'].append({'key': key, 'mcid': m, 'page': key_page.get(key), 'tag': S(el) if '/S' in el else '?'})
                            v[m] = None
                elif isinstance(v, pikepdf.Dictionary) and v.objgen not in tree:
                    res['parenttree'].append({'key': key, 'page': None, 'tag': S(v) if '/S' in v else '?'}); a[j] = None
        for k in node.get('/Kids') or []: walk(k)
    if '/ParentTree' in st: walk(st.ParentTree)
    if '/IDTree' in st:
        pairs = []
        def idw(node):
            if '/Names' in node:
                nm = node.Names
                for j in range(0, len(nm), 2): pairs.append((bytes(nm[j]), nm[j + 1]))
            for k in node.get('/Kids') or []: idw(k)
        idw(st.IDTree)
        keep = []
        for k, v in pairs:
            if isinstance(v, pikepdf.Dictionary) and v.objgen in tree: keep.append((k, v))
            else: res['idtree'].append({'id': k.decode('latin-1'), 'tag': (S(v) if '/S' in v else 'not a tag') if isinstance(v, pikepdf.Dictionary) else 'null: points at nothing'})
        if res['idtree']:
            flat = []
            for k, v in sorted(keep, key=lambda kv: kv[0]): flat += [pikepdf.String(k), v]
            st.IDTree = pikepdf.Dictionary(Names=pikepdf.Array(flat))
    if res['parenttree']: ok('tag tree index: entries pointing outside the tree cleared (ParentTree)', len(res['parenttree']))
    if res['idtree']: ok('tag tree index: entries pointing outside the tree removed (IDTree)', len(res['idtree']))

# ================================================================== run, in a fixed order
STEPS = [('artifacts', op_artifacts), ('document', op_document), ('adopt_orphans', op_adopt_orphans), ('rolemap', op_rolemap), ('merges', op_merges),
         ('actual_text', op_actual_text), ('rolemap', op_rolemap_standard), ('retype', op_retype), ('flatten', op_flatten), ('alt', op_alt),
         ('move_to_document_start', op_move_to_document_start), ('captions', op_captions), ('lists', op_lists),
         ('toc', op_toc), ('notes', op_notes), ('language', op_language), ('links', op_links),
         ('move_section', op_move_section), ('fix_figure_order', op_fix_figure_order),
         ('toc', op_toc_finalize), ('remove_empty_containers', op_remove_empty_containers)]
wo.setdefault('links', {})                 # links are always tied to their text and described
for fn in (fix_root, fix_flags):
    try: fn()
    except Exception as e: log['failed'].append({'op': fn.__name__, 'error': f'{type(e).__name__}: {e}'[:300]})
ALWAYS = {'fix_figure_order'}               # mechanical: run whether or not the work order asks
for key, fn in STEPS:
    if key in ALWAYS or (key in wo and wo[key] not in (None, False)):
        try: fn(wo.get(key))
        except Exception as e: log['failed'].append({'op': key, 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_page_figures()
except Exception as e: log['failed'].append({'op': 'fix_page_figures', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_notes()
except Exception as e: log['failed'].append({'op': 'fix_notes', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_empty_tags()
except Exception as e: log['failed'].append({'op': 'fix_empty_tags', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_outline()
except Exception as e: log['failed'].append({'op': 'fix_outline', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_paths()
except Exception as e: log['failed'].append({'op': 'fix_paths', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_parenttree()
except Exception as e: log['failed'].append({'op': 'fix_parenttree', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_index()
except Exception as e: log['failed'].append({'op': 'fix_index', 'error': f'{type(e).__name__}: {e}'[:300]})
try: fix_ocr_fonts()
except Exception as e: log['failed'].append({'op': 'fix_ocr_fonts', 'error': f'{type(e).__name__}: {e}'[:300]})
left = [S(k) for k in kids(st) if is_elem(k) and not same(k, DOC)]
if left: log['deferred'].append({'what': 'elements still outside the Document', 'count': len(left)})
pdf.save(OUT)
log['applied'] = dict(log['applied'])
json.dump(log, open(OUT + '.log.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(log['applied'], indent=1, ensure_ascii=False))
print('rejected:', len(log['rejected']), '| failed:', len(log['failed']), '| deferred:', [d.get('what') for d in log['deferred']][:6])
