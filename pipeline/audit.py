"""audit.py: step 1 of the API pipeline. Deterministic; no model calls.

    python audit.py ORIGINAL.pdf OUT_DIR

Reads the original PDF and writes the compact view Claude decides from:

    OUT_DIR/digest.json         document facts, tag styles, rare elements, figures, page map
    OUT_DIR/figures/*.png       one crop per figure, long side at most 800 px

Every element Claude may refer to is listed with its object number in the ORIGINAL file
("1234 0"); apply.py resolves those numbers against the same file. Text from the book is
included as data for Claude to read, never as instructions.
"""
import sys, os, re, json, hashlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import plumb_fix  # noqa: E401
import pikepdf, pdfplumber, pypdfium2 as pdfium

SRC, OUT = sys.argv[1], sys.argv[2]
RARE = 30            # styles with at most this many elements are listed one by one
os.makedirs(os.path.join(OUT, 'figures'), exist_ok=True)

pdf = pikepdf.open(SRC)
pages = list(pdf.pages); pidx = {p.obj.objgen: i + 1 for i, p in enumerate(pages)}
labels = {i + 1: str(p.label) for i, p in enumerate(pages)}
st = pdf.Root.get('/StructTreeRoot')
if st is None: sys.exit('untagged PDF: this pipeline repairs an existing tag tree; run a tagging step first')
RM = {str(k).lstrip('/'): str(v).lstrip('/') for k, v in (st.get('/RoleMap') or {}).items()}
KEEP_KEYS = ('text', 'x0', 'x1', 'top', 'bottom', 'size', 'fontname', 'mcid', 'tag')
class _Page:                                    # what the audit needs from a page; the full pdfplumber page is released
    def __init__(self, p):
        self.width, self.height = float(p.width), float(p.height)
        self.chars = [{k: c.get(k) for k in KEEP_KEYS} for c in p.chars]
        self.images = [{k: i.get(k) for k in ('x0', 'x1', 'top', 'bottom', 'mcid', 'tag')} for i in p.images]
class _PL:
    def __init__(self, path):
        self.pages = []
        with pdfplumber.open(path) as pl:
            for p in pl.pages:
                self.pages.append(_Page(p)); p.close()
PL = _PL(SRC)
ref = lambda n: f'{n.objgen[0]} {n.objgen[1]}'
def kids(n):
    k = n.get('/K'); return [] if k is None else (list(k) if isinstance(k, pikepdf.Array) else [k])
def is_elem(k): return isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) not in ('/MCR', '/OBJR')
def S(n): return str(n.get('/S', '')).lstrip('/')
def mapped(s):
    seen = set()
    while s in RM and s not in seen: seen.add(s); s = RM[s]
    return s
def clip(t, n): t = re.sub(r'\s+', ' ', t).strip(); return t if len(t) <= n else t[:n - 1] + '…'

# ---- characters by (page, mcid)
mc_chars = collections.defaultdict(list)
for pno, p in enumerate(PL.pages, 1):
    for c in p.chars:
        if c.get('mcid') is not None: mc_chars[(pno, c['mcid'])].append(c)
def mc_text(pg, m): return ''.join(c['text'] for c in mc_chars.get((pg, m), []))

# ---- walk the tree once
elems = []                 # dicts in reading order
info = {}                  # objgen -> dict
stack = [(k, None, None, 0) for k in reversed(kids(st))]
while stack:
    n, par, pg, depth = stack.pop()
    if not is_elem(n): continue
    pg = pidx[n.Pg.objgen] if '/Pg' in n else pg
    ms = []
    for k in kids(n):
        if isinstance(k, int): ms.append((pg, k))
        elif isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) == '/MCR':
            ms.append((pidx[k.Pg.objgen] if '/Pg' in k else pg, int(k.MCID)))
    e = {'el': n, 'par': par, 'style': S(n), 'page': pg, 'mcids': ms, 'depth': depth, 'kids': []}
    elems.append(e); info[n.objgen] = e
    if par is not None: info[par.objgen]['kids'].append(e)
    for k in reversed(kids(n)): stack.append((k, n, pg, depth + 1))
def text_of(e, depth=0):
    if depth > 40: return ''
    s = ''.join(mc_text(p, m) for p, m in e['mcids'])
    return s + ''.join(text_of(k, depth + 1) for k in e['kids'])
def first_page(e):
    if e['mcids']: return min(p for p, _ in e['mcids'])
    ps = [first_page(k) for k in e['kids']]; ps = [p for p in ps if p]
    return min(ps) if ps else e['page']
def siblings(e):
    par = e['par']
    sib = [x for x in (info[par.objgen]['kids'] if par is not None else [x for x in elems if x['par'] is None])]
    i = next(i for i, x in enumerate(sib) if x is e)
    return (sib[i - 1] if i > 0 else None), (sib[i + 1] if i + 1 < len(sib) else None)
def brief(e): return None if e is None else {'style': e['style'], 'text': clip(text_of(e), 80)}

# ---- styles
by_style = collections.OrderedDict()
for e in elems: by_style.setdefault(e['style'], []).append(e)
styles = []
for s, es in by_style.items():
    pgs = [first_page(e) for e in es if first_page(e)]
    samples = [clip(text_of(e), 90) for e in es[:40] if text_of(e).strip()][:3]
    styles.append({'style': s, 'maps_to': mapped(s), 'count': len(es), 'pages': [min(pgs), max(pgs)] if pgs else None,
                   'samples': samples})

# ---- rare elements, listed one by one (headings, labels, title page, lists, captions …)
SKIP = {'Document', 'Story', 'Sect', 'Art', 'Part', 'Link', 'Index', 'Reference', 'Note', 'Span', 'Figure'}
rare = []
for s, es in by_style.items():
    if len(es) > RARE or s in SKIP or mapped(s) in ('Span', 'Link'): continue
    avg = sum(len(text_of(e)) for e in es) / max(1, len(es))
    if re.fullmatch(r'H[1-6]?', mapped(s)): continue                         # listed under headings
    if mapped(s) in ('L', 'LI', 'LBody', 'Lbl', 'Table', 'TR', 'TD', 'TH', 'THead', 'TBody', 'TFoot'): continue   # under lists / tables
    if avg > 110: continue                                                    # long body paragraphs: samples are enough
    for e in es:
        _, nxt = siblings(e)
        rare.append({'obj': ref(e['el']), 'style': s, 'page': first_page(e), 'label': labels.get(first_page(e)),
                     'text': clip(text_of(e), 110), 'next': None if nxt is None else f'{nxt["style"]}: {clip(text_of(nxt), 50)}'})

# ---- reading order of the big containers, as the tree has them
def page_span(e, acc=None):
    acc = set() if acc is None else acc
    acc.update(p for p, _ in e['mcids'] if p)
    for k in e['kids']: page_span(k, acc)
    return acc
reading_order = []
for e in elems:
    if e['style'] in ('Story', 'Sect', 'Art', 'Part', 'Div') or mapped(e['style']) in ('Sect', 'Art', 'Part'):
        ps = page_span(e)
        if ps:
            first = next((text_of(k) for k in e['kids'] if text_of(k).strip()), '')
            reading_order.append(f'{e["style"]} pp{min(ps)}-{max(ps)} depth{e["depth"]}: {clip(first, 40)}')

# ---- figures, with crops
docs = pdfium.PdfDocument(SRC); renders = {}
def crop(pg, box, name):
    if pg not in renders: renders[pg] = docs[pg - 1].render(scale=2).to_pil()
    im = renders[pg]; x0, t, x1, b = [v * 2 for v in box]
    c = im.crop((max(0, x0 - 4), max(0, t - 4), min(im.width, x1 + 4), min(im.height, b + 4)))
    if max(c.size) > 800: c.thumbnail((800, 800))
    c.convert('RGB').save(os.path.join(OUT, 'figures', name)); return c.size
figures = []
for e in elems:
    if mapped(e['style']) != 'Figure': continue
    pg = first_page(e); box = None
    if pg:
        ids = {m for p, m in e['mcids'] if p == pg}
        ims = [i for i in PL.pages[pg - 1].images if i.get('mcid') in ids]
        if ims: box = [min(i['x0'] for i in ims), min(i['top'] for i in ims), max(i['x1'] for i in ims), max(i['bottom'] for i in ims)]
    prv, nxt = siblings(e)
    f = {'obj': ref(e['el']), 'page': pg, 'label': labels.get(pg), 'alt': str(e['el'].get('/Alt', '')) if '/Alt' in e['el'] else None,
         'at_root': e['par'] is None, 'parent_style': info[e['par'].objgen]['style'] if e['par'] is not None else None,
         'single_run': len(e['mcids']) == 1 and not e['kids'],
         'bbox_pt': [round(v) for v in box] if box else None, 'next': brief(nxt), 'image': None}
    if box and pg:
        W, H = float(PL.pages[pg - 1].width), float(PL.pages[pg - 1].height)
        f['area_pct'] = round(100 * (box[2] - box[0]) * (box[3] - box[1]) / (W * H), 1)
        name = f'p{pg:03d}_{e["el"].objgen[0]}.png'; f['image'] = 'figures/' + name; f['image_px'] = crop(pg, box, name)
    if f['alt'] and '\x00' in f['alt']: f['alt_has_nul'] = True; f['alt'] = f['alt'].replace('\x00', '\\x00')
    figures.append(f)

# ---- pages with no tags at all that hold a drawing (a full-page map, plate or cover): the executor wraps each
#      whole page in one Figure; the model sees the page image and writes its alt text (page_figures)
PAINT = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'}; PATHB = {'m', 'l', 'c', 'v', 'y', 're', 'h', 'W', 'W*'}; SHOW = {'Tj', 'TJ', "'", '"'}
def page_inventory(page):
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
            elif op in PATHB: path = True
            elif op == 'n': path = False
            elif op in PAINT and path: inv['paths'] += 1; path = False
            elif op in SHOW: inv['hidden_text' if tr == 3 else 'text'] += 1
            elif op in ('BI', 'INLINE IMAGE', 'sh'): inv['images'] += 1
            elif op == 'Do':
                x = xo.get(ops[0])
                if x is None: continue
                if str(x.get('/Subtype')) == '/Image': inv['images'] += 1
                elif str(x.get('/Subtype')) == '/Form': walk(x, x.get('/Resources') or res, tr, depth + 1)
    walk(page, page.obj.get('/Resources'), 0)
    return inv
page_figures = []
for pno, p in enumerate(PL.pages, 1):
    if any(c.get('mcid') is not None or c.get('tag') == 'Artifact' for c in p.chars + p.images): continue
    inv = page_inventory(pages[pno - 1])
    if inv['mcid'] or inv['artifact'] or inv['hidden_text'] or pages[pno - 1].obj.get('/Annots'): continue
    if not (inv['images'] or inv['paths']): continue
    name = f'page_{pno:03d}.png'
    page_figures.append({'page': pno, 'label': labels.get(pno), 'images': inv['images'], 'paths': inv['paths'], 'text_operators': inv['text'],
                         'sample_text': clip(''.join(c['text'] for c in p.chars), 80), 'image': 'figures/' + name,
                         'image_px': crop(pno, [0, 0, p.width, p.height], name)})

# ---- page map, repeated top/bottom lines, front matter
def lines(pno, tagged_only=True):
    cs = [c for c in PL.pages[pno - 1].chars if (c.get('mcid') is not None) or not tagged_only]
    rows = []
    for c in sorted(cs, key=lambda c: (round(c['top']), c['x0'])):
        if rows and abs(rows[-1][0] - c['top']) < 3: rows[-1][1].append(c)
        else: rows.append([c['top'], [c]])
    return [(top, ''.join(x['text'] for x in sorted(r, key=lambda x: x['x0']))) for top, r in rows]
page_map, rep = [], collections.defaultdict(list)
for pno in range(1, len(pages) + 1):
    ls = lines(pno); H = float(PL.pages[pno - 1].height)
    page_map.append(f'{pno}|{labels[pno]}|{clip(ls[0][1], 70) if ls else "(no tagged text)"}')
    by = collections.defaultdict(list)
    for c in PL.pages[pno - 1].chars:
        if c.get('mcid') is not None: by[c['mcid']].append(c)
    for m, cs in by.items():
        top = min(c['top'] for c in cs); t = clip(''.join(c['text'] for c in cs), 80)
        if top < 70 or top > H - 60:
            rep[(re.sub(r'[0-9ivxlc]+', '#', t.lower()), 'top' if top < 70 else 'bottom')].append((pno, t, m))
repeated = [{'pattern': k[0], 'position': k[1], 'count': len(v), 'pages': [v[0][0], v[-1][0]], 'example': v[0][1], 'runs': [(x[0], x[2]) for x in v]}
            for k, v in rep.items() if len(v) >= 3 and len(re.sub(r'[^a-z]', '', k[0])) >= 3]
front = [{'page': p, 'label': labels[p], 'text': clip(' / '.join(t for _, t in lines(p)), 900)} for p in range(1, min(12, len(pages)) + 1)]
contents_pages = [int(x.split('|')[0]) for x in page_map if re.fullmatch(r'contents', x.split('|', 2)[2].strip().lower())]
for p in contents_pages:
    front = [x for x in front if x['page'] != p]
    front.append({'page': p, 'label': labels[p], 'text': clip(' / '.join(t for _, t in lines(p)), 2500), 'why': 'contents page'})

# ---- CJK and links (summaries only; the executor handles them by rule)
KANA = re.compile(r'[぀-ヿㇰ-ㇿｦ-ﾟ]'); CJK = re.compile(r'[　-ヿ㐀-䶿一-鿿＀-￯]')
cjk = collections.Counter(); cjk_ex = []
for (p, m), cs in mc_chars.items():
    t = ''.join(c['text'] for c in cs)
    if not CJK.search(t): continue
    kind = 'mixed_with_latin' if re.sub(r'[\s\W\d_]', '', CJK.sub('', t)) else ('kana' if KANA.search(t) else 'han_only')
    cjk[kind] += 1
    if len(cjk_ex) < 12 and kind == 'han_only': cjk_ex.append({'page': p, 'text': clip(t, 30)})
link_pages = collections.Counter()
for pno, p in enumerate(pages, 1):
    for a in p.obj.get('/Annots') or []:
        if str(a.get('/Subtype')) == '/Link': link_pages[pno] += 1

# ---- fonts: body size, so headings can be told apart from body text
def is_bold(c): return bool(re.search(r'Bold|Semibold|Black|Heavy|Demi', c.get('fontname', ''), re.I))
size_count = collections.Counter(round(c['size'] * 2) / 2 for cs in mc_chars.values() for c in cs)
BODY = size_count.most_common(1)[0][0] if size_count else 10.0
def chars_of(e, depth=0):
    out = [c for p, m in e['mcids'] for c in mc_chars.get((p, m), [])]
    if depth < 40:
        for k in e['kids']: out += chars_of(k, depth + 1)
    return out
def font_of(e):
    cs = [c for c in chars_of(e) if c['text'].strip()]
    if not cs: return None, None
    size = collections.Counter(round(c['size'] * 2) / 2 for c in cs).most_common(1)[0][0]
    return size, round(sum(is_bold(c) for c in cs) / len(cs), 2)
def in_band(e):
    cs = chars_of(e)
    if not cs: return False
    p = e['page'] or first_page(e) or 1; H = float(PL.pages[p - 1].height); top = min(c['top'] for c in cs)
    return top < 70 or top > H - 60

# ---- every heading, whatever its count; and short body lines that look like headings
headings, candidates = [], []
for e in elems:
    m = mapped(e['style']); t = text_of(e).strip()
    if re.fullmatch(r'H[1-6]?', m):
        size, bold = font_of(e); _, nxt = siblings(e)
        headings.append({'obj': ref(e['el']), 'style': e['style'], 'level': m, 'page': first_page(e), 'label': labels.get(first_page(e)),
                         'text': clip(t, 110), 'size': size, 'bold': bold,
                         'next': None if nxt is None else f'{nxt["style"]}: {clip(text_of(nxt), 50)}'})
    elif m == 'P' and 2 <= len(t) <= 90 and (not in_band(e) or (font_of(e)[0] or 0) >= BODY * 1.3):
        # a large line in the top band is a chapter opener's title (running heads are body size or smaller)
        size, bold = font_of(e)
        if size and (size >= BODY * 1.15 or (size >= BODY + 0.5 and len(t) <= 40) or (bold >= 0.9 and len(t) <= 70 and not t.endswith('.'))):
            candidates.append({'obj': ref(e['el']), 'style': e['style'], 'page': first_page(e), 'label': labels.get(first_page(e)),
                               'text': clip(t, 90), 'size': size, 'bold': bold})
candidates = sorted(candidates, key=lambda c: (-c['size'], c['page'] or 0))[:200]
candidates.sort(key=lambda c: c['page'] or 0)

# ---- lists and tables, one by one, so false ones can be flattened
def kids_mapped(e, t): return [k for k in e['kids'] if mapped(k['style']) == t]
lists = []
for e in elems:
    if mapped(e['style']) != 'L': continue
    items = kids_mapped(e, 'LI')
    lists.append({'obj': ref(e['el']), 'style': e['style'], 'page': first_page(e), 'label': labels.get(first_page(e)), 'items': len(items),
                  'has_labels': any(kids_mapped(i, 'Lbl') for i in items),
                  'first_items': [clip(text_of(i), 70) for i in items[:2]]})
tables = []
def rows_of(e):
    out = []
    for k in e['kids']:
        if mapped(k['style']) == 'TR': out.append(k)
        elif mapped(k['style']) in ('THead', 'TBody', 'TFoot'): out += rows_of(k)
    return out
for e in elems:
    if mapped(e['style']) != 'Table': continue
    rows = rows_of(e); cols = max((len([c for c in r['kids'] if mapped(c['style']) in ('TD', 'TH')]) for r in rows), default=0)
    ps = sorted({first_page(r) for r in rows if first_page(r)})
    tables.append({'obj': ref(e['el']), 'page': first_page(e), 'label': labels.get(first_page(e)), 'pages': [ps[0], ps[-1]] if ps else None,
                   'rows': len(rows), 'cols': cols, 'header_cells': sum(1 for r in rows for c in r['kids'] if mapped(c['style']) == 'TH'),
                   'first_rows': [clip(' | '.join(text_of(c) for c in r['kids']), 100) for r in rows[:2]]})

# ---- content a screen reader never reaches: marked but not in the tree, or not marked at all
owned = {pm for e in elems for pm in e['mcids']}
for r in repeated:
    rs = r.pop('runs'); r['tagged'] = sum(1 for pm in rs if pm in owned); r['orphan'] = len(rs) - r['tagged']
fig_boxes = collections.defaultdict(list)
for f in figures:
    if f.get('bbox_pt') and f['page']: fig_boxes[f['page']].append(f['bbox_pt'])
unowned, unowned_tot = [], collections.Counter()
for pno, p in enumerate(PL.pages, 1):
    H = float(p.height); runs = collections.defaultdict(list)
    for c in p.chars:
        if c.get('mcid') is not None and (pno, c['mcid']) not in owned: runs[('orphan', c['mcid'])].append(c)
        elif c.get('mcid') is None and c.get('tag') != 'Artifact': runs[('untagged', round(c['top']))].append(c)
    if not runs: continue
    kinds = collections.Counter(k[0] for k in runs); bands = collections.Counter()
    infig = 0
    for k, cs in runs.items():
        top = min(c['top'] for c in cs); bands['top' if top < 70 else 'bottom' if top > H - 60 else 'body'] += 1
        cx, cy = (cs[0]['x0'] + cs[0]['x1']) / 2, (cs[0]['top'] + cs[0]['bottom']) / 2
        infig += any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in fig_boxes.get(pno, []))
    unowned_tot.update(kinds)
    def band_of(cs): top = min(c['top'] for c in cs); return 'top' if top < 70 else 'bottom' if top > H - 60 else 'body'
    runs_listed = [{'kind': k[0], 'band': band_of(cs), 'text': clip(''.join(c['text'] for c in cs), 50)}
                   for k, cs in sorted(runs.items(), key=lambda kv: min(c['top'] for c in kv[1]))[:6]]
    unowned.append({'page': pno, 'label': labels[pno], 'orphan_runs': kinds['orphan'], 'untagged_runs': kinds['untagged'],
                    **({'page_figure': True} if any(f['page'] == pno for f in page_figures) else {}),
                    'by_band': {b: bands[b] for b in ('top', 'body', 'bottom') if bands[b]}, 'in_figure': infig,
                    'runs': runs_listed})

# ---- scan and OCR signals
full_page_imgs = sum(1 for p in PL.pages if any((i['x1'] - i['x0']) * (i['bottom'] - i['top']) > 0.8 * float(p.width) * float(p.height) for i in p.images))
tok_bad = tok_all = 0; worst = []
for pno, p in enumerate(PL.pages, 1):
    toks = re.findall(r'\S+', ''.join(c['text'] if c['text'] != '\n' else ' ' for c in p.chars).replace('  ', ' '))
    bad = sum(1 for t in toks if (len(t) == 1 and t.isalpha() and t not in 'aAI') or re.search(r'[A-Za-z][^A-Za-z\s\'’\-.,;:!?)\]”"]+[A-Za-z]', t))
    tok_bad += bad; tok_all += len(toks)
    if toks: worst.append((round(1000 * bad / len(toks)), pno))
text_quality = {'producer_says_ocr': 'Paper Capture' in str(pdf.docinfo.get('/Producer', '')) or 'OCR' in str(pdf.docinfo.get('/Producer', '')),
                'pages_with_full_page_image': full_page_imgs, 'suspect_tokens_per_1000': round(1000 * tok_bad / max(1, tok_all), 1),
                'worst_pages': [p for _, p in sorted(worst, reverse=True)[:8]]}

af = pdf.Root.get('/AcroForm')
with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as meta: xmp_title = meta.get('dc:title')
digest = {
    'schema': 'digest/0.2',
    'source': {'file': os.path.basename(SRC), 'sha256': hashlib.sha256(open(SRC, 'rb').read()).hexdigest(), 'pages': len(pages),
               'creator': str(pdf.docinfo.get('/Creator', '')), 'producer': str(pdf.docinfo.get('/Producer', ''))},
    'document': {'title': str(pdf.docinfo.get('/Title', '')), 'xmp_title': str(xmp_title) if xmp_title else None,
                 'lang': str(pdf.Root.get('/Lang', '')),
                 'display_doc_title': bool(pdf.Root.ViewerPreferences.get('/DisplayDocTitle')) if '/ViewerPreferences' in pdf.Root else False,
                 'acroform': None if af is None else {'fields': len(af.get('/Fields') or [])},
                 'marked': bool(pdf.Root.get('/MarkInfo', {}).get('/Marked', False)) if '/MarkInfo' in pdf.Root else False,
                 'has_document_root': any(e['par'] is None and mapped(e['style']) == 'Document' for e in elems),
                 'encrypted': pdf.is_encrypted, 'pdfua_claimed': 'pdfuaid' in str(pdf.Root.get('/Metadata').read_bytes()[:20000]) if '/Metadata' in pdf.Root else False},
    'tree': {'elements': len(elems), 'root_children': dict(collections.Counter(e['style'] for e in elems if e['par'] is None)),
             'rolemap': RM},
    'reading_order_format': 'containers in the order a screen reader meets them: style, PDF page span, depth, first text',
    'reading_order': reading_order,
    'styles': styles,
    'elements': rare,
    'body_font_size': BODY,
    'headings': headings[:400],
    'heading_candidates_format': 'body-tagged lines whose size or weight looks like a heading',
    'heading_candidates': candidates,
    'lists': lists[:200],
    'tables': tables[:100],
    'figures': figures,
    'page_figures_format': 'pages with no tags at all that hold a drawing (map, plate, cover); the executor wraps each whole page in one Figure. Its letters are labels, not body text. Write page_figures alt text from the page image.',
    'page_figures': page_figures,
    'unowned_content_format': 'per page: counts of orphan runs (marked, no tag owns them) and untagged runs (not marked), by band; runs inside figures; up to 6 runs, top to bottom, EACH ITEM ONE SEPARATE RUN',
    'unowned_content_totals': dict(unowned_tot),
    'unowned_content': unowned[:300],
    'text_quality': text_quality,
    'repeated_lines': sorted(repeated, key=lambda r: -r['count'])[:25],
    'page_map_format': 'page|printed label|first tagged line',
    'page_map': page_map,
    'front_matter': front,
    'cjk_runs': dict(cjk), 'cjk_han_only_examples': cjk_ex,
    'links': {'annotations': sum(link_pages.values()),
              'per_page_top': [[p, n] for p, n in sorted(link_pages.items(), key=lambda x: -x[1])[:15]]},
}
json.dump(digest, open(os.path.join(OUT, 'digest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'digest: {len(styles)} styles · {len(headings)} headings + {len(candidates)} candidates · {len(lists)} lists · {len(tables)} tables · '
      f'unowned {dict(unowned_tot)} · {len(rare)} other listed · {len(figures)} figures ({sum(1 for f in figures if f["image"])} crops) · '
      f'{len(page_figures)} page figures · '
      f'{len(repeated)} repeated lines · {len(page_map)} pages · {os.path.getsize(os.path.join(OUT, "digest.json")) // 1024} KB')
