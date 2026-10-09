"""Verify work/remediated.pdf against the original. Read-only."""
import sys, json, re, collections
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import plumb_fix
import pikepdf, pdfplumber, pypdfium2 as pdfium
import fontTools.cffLib, fontTools.ttLib  # noqa: F401  required: a font that can't be read must not pass as OK
from PIL import ImageChops
A, B = sys.argv[1], sys.argv[2]
out = {}
# 1 pixels, every page
da, db = pdfium.PdfDocument(A), pdfium.PdfDocument(B)
out['pixel_pages_differing'] = [i + 1 for i in range(len(da)) if ImageChops.difference(
    da[i].render(scale=1.2).to_pil().convert('RGB'), db[i].render(scale=1.2).to_pil().convert('RGB')).getbbox()]
# 2 text + marking
tdiff, untag, art = [], 0, 0
_CM = set()
with pdfplumber.open(A) as pa, pdfplumber.open(B) as pb:
    for i in range(len(pa.pages)):
        PA, PB = pa.pages[i], pb.pages[i]
        ca, cb = PA.chars, PB.chars
        if ''.join(c['text'] for c in ca) != ''.join(c['text'] for c in cb): tdiff.append(i + 1)
        untag += sum(1 for c in cb if c.get('mcid') is None and c.get('tag') != 'Artifact')
        art += sum(1 for c in cb if c.get('tag') == 'Artifact')
        content_mcids_page = {(i + 1, c['mcid']) for c in cb if c.get('mcid') is not None}
        _CM.update(content_mcids_page); PA.close(); PB.close()
out['text_pages_changed'] = tdiff; out['untagged_chars'] = untag; out['artifact_chars'] = art
# 3 tree
pdf = pikepdf.open(B); st = pdf.Root.StructTreeRoot
pages = list(pdf.pages); pidx = {p.obj.objgen: i + 1 for i, p in enumerate(pages)}
def nt_all(node, acc):
    if '/Nums' in node:
        a = node.Nums
        for j in range(0, len(a), 2): acc[int(a[j])] = a[j + 1]
    for k in node.get('/Kids') or []: nt_all(k, acc)
    return acc
PT = nt_all(st.ParentTree, {})
live = {a.objgen: i for i, p in enumerate(pages, 1) for a in (p.obj.get('/Annots') or [])}
RM = {str(k).lstrip('/'): str(v).lstrip('/') for k, v in (st.get('/RoleMap') or {}).items()}
def mapped(s):
    for _ in range(5):
        if s in RM: s = RM[s]
    return s
owner, objr_owner, stale, types, nested_links, seq = {}, {}, 0, collections.Counter(), 0, []
root_kids = [str(k.get('/S')) for k in (st.K if isinstance(st.K, pikepdf.Array) else [st.K])]
stack = [(k, st, None, False) for k in reversed(list(st.K) if isinstance(st.K, pikepdf.Array) else [st.K])]
while stack:
    n, par, pg, in_link = stack.pop()
    if isinstance(n, int): owner[(pg, n)] = par.objgen; continue
    if not isinstance(n, pikepdf.Dictionary): continue
    t = str(n.get('/Type'))
    if t == '/MCR':
        if '/Stm' not in n: owner[(pidx[n.Pg.objgen] if '/Pg' in n else pg, int(n.MCID))] = par.objgen   # /Stm: numbered inside a form XObject
        continue
    if t == '/OBJR':
        if n.Obj.objgen in live: objr_owner[n.Obj.objgen] = par.objgen
        else: stale += 1
        continue
    s = mapped(str(n.get('/S')).lstrip('/')); types[s] += 1
    if re.fullmatch(r'H[1-6]', s): seq.append((int(s[1]), pidx.get(n.Pg.objgen) if '/Pg' in n else pg))
    if s == 'Link' and in_link: nested_links += 1
    pg = pidx[n.Pg.objgen] if '/Pg' in n else pg
    k = n.get('/K')
    for kid in reversed(list(k) if isinstance(k, pikepdf.Array) else ([k] if k is not None else [])):
        stack.append((kid, n, pg, in_link or s == 'Link'))
mism = missing = 0
for (pg, m), og in owner.items():
    arr = PT.get(int(pages[pg - 1].obj.get('/StructParents', -1)))
    got = arr[m] if arr is not None and m < len(arr) else None
    if got is None: missing += 1
    elif got.objgen != og: mism += 1
content_mcids = _CM                                # collected in the single pass above
unowned = len(content_mcids - set(owner))
annot_bad = [(live[og], og) for og in live if og not in objr_owner or
             (PT.get(int(pdf.get_object(og).get('/StructParent', -1))) is None) or
             PT[int(pdf.get_object(og).StructParent)].objgen != objr_owner[og]]
no_contents = sum(1 for og in live if '/Contents' not in pdf.get_object(og))
out['tree'] = {'root_children': dict(collections.Counter(root_kids)), 'types': dict(types.most_common()),
               'mcids_in_tree': len(owner), 'content_mcids_not_in_tree': unowned,
               'parenttree_missing': missing, 'parenttree_mismatched': mism,
               'stale_OBJRs': stale, 'annotations_unresolved': len(annot_bad), 'annotations_without_Contents': no_contents,
               'nested_Link_in_Link': nested_links}
lv = [l for l, _ in seq]
out['headings'] = {'first': seq[0] if seq else None, 'counts': dict(collections.Counter(f'H{l}' for l in lv)),
                   'skipped_levels': [(a, b) for a, b in zip(lv, lv[1:]) if b > a + 1][:5]}
figs = []
st2 = [st.K]
while st2:
    n = st2.pop()
    if isinstance(n, pikepdf.Array): st2.extend(list(n)); continue
    if not isinstance(n, pikepdf.Dictionary) or str(n.get('/Type')) in ('/MCR', '/OBJR'): continue
    if mapped(str(n.get('/S')).lstrip('/')) == 'Figure': figs.append(str(n.get('/Alt', '')))
    if '/K' in n: st2.append(n.K)
out['figures'] = {'count': len(figs), 'generic_or_empty': sum(1 for a in figs if a.strip().lower() in ('', 'illustration', 'image')),
                  'with_nul': sum('\x00' in a for a in figs)}
def _ids(node, acc):
    if '/Names' in node:
        nm = node.Names; acc += [bytes(nm[j]) for j in range(0, len(nm), 2)]
    for k in node.get('/Kids') or []: _ids(k, acc)
    return acc
keys = _ids(st.IDTree, []) if '/IDTree' in st else []
out['idtree'] = {'entries': len(keys), 'sorted': keys == sorted(keys) if '/IDTree' in st and '/Names' in st.IDTree else 'name tree with Kids', 'unique': len(keys) == len(set(keys))}
# Note tags: every Note needs a unique /ID, and the IDTree must lead to it
def _pairs(node, acc):
    if '/Names' in node:
        nm = node.Names; acc.update({bytes(nm[j]): nm[j + 1].objgen for j in range(0, len(nm), 2) if isinstance(nm[j + 1], pikepdf.Dictionary)})
    for k in node.get('/Kids') or []: _pairs(k, acc)
    return acc
idmap = _pairs(st.IDTree, {}) if '/IDTree' in st else {}
id_count, notes = collections.Counter(), []
st3 = [st.K]
while st3:
    n = st3.pop()
    if isinstance(n, pikepdf.Array): st3.extend(list(n)); continue
    if not isinstance(n, pikepdf.Dictionary) or str(n.get('/Type')) in ('/MCR', '/OBJR'): continue
    if '/ID' in n: id_count[bytes(n.ID)] += 1
    if mapped(str(n.get('/S')).lstrip('/')) == 'Note': notes.append(n)
    if '/K' in n: st3.append(n.K)
out['notes'] = {'count': len(notes), 'without_ID': sum('/ID' not in n for n in notes),
                'duplicate_ID': sum(1 for n in notes if '/ID' in n and id_count[bytes(n.ID)] > 1),
                'not_in_IDTree': sum(1 for n in notes if '/ID' in n and idmap.get(bytes(n.ID)) != n.objgen)}
def _count_outline():
    o = pdf.Root.get('/Outlines')
    if o is None or '/First' not in o: return 0
    with pdf.open_outline() as ol:
        def c(items): return sum(1 + c(i.children) for i in items)
        return c(ol.root)
out['bookmarks'] = {'items': _count_outline(), 'pages': len(pages)}
out['doc'] = {'title': str(pdf.docinfo.Title), 'lang': str(pdf.Root.Lang), 'DisplayDocTitle': bool(pdf.Root.ViewerPreferences.DisplayDocTitle),
              'acroform': '/AcroForm' in pdf.Root, 'encrypted': pdf.is_encrypted}
with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as m: out['doc']['xmp_title'] = str(m.get('dc:title')); out['doc']['pdfua_stamped'] = any('pdfuaid' in k for k in m.keys())
# 4 content that is neither tagged nor an artifact (text, paths, images), and font problems, in one pass over
#   every content stream. A form XObject is counted once, however many pages draw it (as checkers do).
import io
PAINT = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'}; SHOW = {'Tj', 'TJ', "'", '"'}
free = collections.Counter(); free_pages = collections.defaultdict(collections.Counter); seen_forms = set()
font_use = collections.defaultdict(lambda: {'refs': 0, 'ops': 0, 'pages': set(), 'modes': collections.Counter()})
font_obj = {}
def _walk(stream, pno, resources, inherited, tr=0):
    stack = []; cur = None; path = False; gs = []
    fonts = {str(k): v for k, v in ((resources or {}).get('/Font') or {}).items()}
    xo = (resources or {}).get('/XObject') or {}
    for operands, op in pikepdf.parse_content_stream(stream):
        op = str(op)
        if op in ('BDC', 'BMC'):
            props = operands[1] if len(operands) > 1 else None
            stack.append('art' if str(operands[0]) == '/Artifact' else ('mc' if isinstance(props, pikepdf.Dictionary) and '/MCID' in props else 'x'))
            continue
        if op == 'EMC':
            if stack: stack.pop()
            continue
        state = inherited or next((x for x in reversed(stack) if x in ('art', 'mc')), None)
        if op == 'q': gs.append((tr, cur)); continue
        if op == 'Q':
            if gs: tr, cur = gs.pop()
            continue
        if op == 'Tf': cur = str(operands[0]); continue
        if op == 'Tr': tr = int(operands[0]); continue
        if op in ('m', 'l', 'c', 'v', 'y', 're'): path = True; continue
        if op == 'n': path = False; continue
        kind = None
        if op in PAINT and path: kind = 'path'; path = False
        elif op in SHOW:
            kind = 'text'; f = fonts.get(cur)
            if f is not None:
                u = font_use[f.objgen]; font_obj[f.objgen] = f; u['ops'] += 1; u['pages'].add(pno); u['modes'][tr] += 1
                two = str(f.get('/Subtype')) == '/Type0'
                for x in ([operands[-1]] if op != 'TJ' else [y for y in operands[0] if isinstance(y, pikepdf.String)]):
                    u['refs'] += len(bytes(x)) // (2 if two else 1)
        elif op == 'Do':
            x = xo.get(operands[0])
            if x is None: continue
            if str(x.get('/Subtype')) == '/Image': kind = 'image'
            elif x.objgen not in seen_forms:
                seen_forms.add(x.objgen); _walk(x, pno, x.get('/Resources') or resources, state, tr); continue
            else: continue
        elif op in ('sh', 'BI'): kind = 'image'
        if kind and state is None: free[kind] += 1; free_pages[pno][kind] += 1
for i, pg in enumerate(pages, 1):
    try: _walk(pg, i, pg.obj.get('/Resources'), None)
    except Exception as e: free['unreadable stream'] += 1
out['untagged_paths'] = free.get('path', 0)          # a vector path drawn outside any tag and any artifact
out['untagged_objects'] = {'total': sum(free.values()), 'by_kind': dict(free),
                           'top_pages': [[p, dict(c)] for p, c in sorted(free_pages.items(), key=lambda kv: -sum(kv[1].values()))[:8]]}
def _glyph_count(f):
    """Glyphs in an embedded font program; None if there is none; 'unreadable' if it can't be read."""
    d = f.get('/FontDescriptor')
    if str(f.get('/Subtype')) == '/Type0': d = f.DescendantFonts[0].get('/FontDescriptor')
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
            return TTFont(io.BytesIO(d.FontFile2.read_bytes())).getGlyphOrder().__len__()
    except Exception: return 'unreadable'
    return None
STD_ENC = {'/WinAnsiEncoding', '/MacRomanEncoding', '/MacExpertEncoding'}
def _unicode_from_encoding(f):
    """A simple, non-symbolic font whose encoding is WinAnsi, MacRoman or MacExpert with no /Differences: every code's
    character is fixed by that standard encoding, so no ToUnicode map is needed. Anything else needs one."""
    if str(f.get('/Subtype')) not in ('/Type1', '/TrueType', '/MMType1'): return False
    enc = f.get('/Encoding')
    if isinstance(enc, pikepdf.Name): std = str(enc) in STD_ENC
    elif isinstance(enc, pikepdf.Dictionary): std = '/Differences' not in enc and str(enc.get('/BaseEncoding')) in STD_ENC
    else: return False                                  # missing: the font program's own (possibly custom) encoding
    d = f.get('/FontDescriptor')
    return std and d is not None and not (int(d.get('/Flags', 0)) & 4)     # bit 3: symbolic
fonts_out = {'no_ToUnicode': [], 'not_embedded': [], 'only_notdef': [], 'no_ToUnicode_not_needed': [], 'unreadable': []}
for og, f in font_obj.items():
    name = str(f.get('/BaseFont')).lstrip('/').split('+')[-1]; u = font_use[og]
    d = f.DescendantFonts[0].get('/FontDescriptor') if str(f.get('/Subtype')) == '/Type0' else f.get('/FontDescriptor')
    embedded = d is not None and any(k in d for k in ('/FontFile', '/FontFile2', '/FontFile3'))
    if '/ToUnicode' not in f: fonts_out['no_ToUnicode_not_needed' if _unicode_from_encoding(f) else 'no_ToUnicode'].append(name)
    if not embedded: fonts_out['not_embedded'].append(name)
    elif (gc := _glyph_count(f)) == 'unreadable':
        fonts_out['unreadable'].append({'font': name, 'render_modes': sorted(u['modes']), 'pages': len(u['pages'])})
    elif gc == 1:                           # the program holds nothing but .notdef: every glyph it is asked for is undefined
        fonts_out['only_notdef'].append({'font': name, 'glyph_references': u['refs'], 'text_operators': u['ops'], 'pages': len(u['pages']),
                                         'first_pages': sorted(u['pages'])[:8], 'render_modes': dict(u['modes']), 'has_ToUnicode': '/ToUnicode' in f})
agg = collections.defaultdict(lambda: {'font': None, 'glyph_references': 0, 'text_operators': 0, 'pages': set(), 'render_modes': collections.Counter(), 'has_ToUnicode': True})
for x in fonts_out['only_notdef']:
    a = agg[x['font']]; a['font'] = x['font']; a['glyph_references'] += x['glyph_references']; a['text_operators'] += x['text_operators']
    a['pages'] |= set(x['first_pages']); a['render_modes'].update(x['render_modes']); a['has_ToUnicode'] &= x['has_ToUnicode']
pages_by_font = collections.defaultdict(set)
for og, f in font_obj.items(): pages_by_font[str(f.get('/BaseFont')).lstrip('/').split('+')[-1]] |= font_use[og]['pages']
out['fonts'] = {'no_ToUnicode': sorted(set(fonts_out['no_ToUnicode'])), 'not_embedded': sorted(set(fonts_out['not_embedded'])),
                'no_ToUnicode_not_needed': sorted(set(fonts_out['no_ToUnicode_not_needed'])),
                'unreadable': fonts_out['unreadable'],
                'only_notdef': [{**{k: v for k, v in a.items() if k not in ('pages', 'render_modes')}, 'pages': len(pages_by_font[a['font']]),
                                 'first_pages': sorted(pages_by_font[a['font']])[:8], 'render_modes': dict(a['render_modes'])} for a in agg.values()]}
# the hidden OCR layer of a scanned page (text drawn only in render mode 3) whose font program defines no glyph
out['fonts']['ocr_overlay_undefined'] = [{'font': a['font'], 'glyph_references': a['glyph_references'], 'pages': a['pages']}
                                         for a in out['fonts']['only_notdef'] if set(a['render_modes']) == {3}]
# 5 structure: empty tags, paragraphs holding nothing but figures, captions not grouped with a figure, URL-only links
def _kids(n):
    k = n.get('/K'); return [] if k is None else (list(k) if isinstance(k, pikepdf.Array) else [k])
def _is_el(k): return isinstance(k, pikepdf.Dictionary) and '/S' in k and str(k.get('/Type', '/StructElem')) not in ('/MCR', '/OBJR')
# Pages for the rows a person reads: a tag's own /Pg. A tag that holds a figure or other content and has no /Pg of its own
# takes the page of the figure inside it, else of the first content inside it. An empty tag takes its parent's /Pg (one
# step up, never a Sect further up that only stores the page it starts on). None when that is missing too.
def _own_pg(n):
    try: return pidx.get(n.Pg.objgen) if '/Pg' in n else None
    except Exception: return None
def _first_pg(n, d=0):                     # n's own page, else the page of the first content inside it, in tree order
    p = _own_pg(n)
    if p is not None or d > 60: return p
    for k in _kids(n):
        if not isinstance(k, pikepdf.Dictionary): continue
        t = str(k.get('/Type', ''))
        if t in ('/MCR', '/OBJR'):
            p = _own_pg(k)
            if p is None and t == '/OBJR':
                try: p = pidx.get(k.Obj.P.objgen) if '/P' in k.Obj else None
                except Exception: p = None
            if p is not None: return p
        elif _is_el(k) and (p := _first_pg(k, d + 1)) is not None: return p
    return None
def _first_figure(n, d=0):
    for k in _kids(n):
        if _is_el(k):
            if mapped(str(k.S).lstrip('/')) == 'Figure': return k
            if d < 60 and (f := _first_figure(k, d + 1)) is not None: return f
    return None
def _holder_pg(n):                         # a tag that holds something
    p = _own_pg(n)
    if p is not None: return p
    f = _first_figure(n)
    if f is not None and (p := _first_pg(f)) is not None: return p
    return _first_pg(n)
def _empty_pg(n, par):                     # a tag with nothing inside
    p = _own_pg(n)
    return p if p is not None or par is None else _own_pg(par)
el_type, empty_el, fig_only, cap_loose = {}, [], [], []
stk = [(k, None) for k in reversed(_kids(st))]
while stk:
    n, par = stk.pop()
    if not _is_el(n): continue
    s_ = mapped(str(n.S).lstrip('/')); el_type[n.objgen] = s_; ks = _kids(n); els = [k for k in ks if _is_el(k)]
    if not ks and '/Alt' not in n and '/ActualText' not in n and s_ not in ('TD', 'TH'):    # an empty table cell is normal
        empty_el.append({'page': _empty_pg(n, par), 'tag': str(n.S).lstrip('/')})
    if s_ == 'P' and els and len(els) == len(ks) and all(mapped(str(k.S).lstrip('/')) == 'Figure' for k in els):
        fig_only.append({'page': _holder_pg(n), 'tag': str(n.S).lstrip('/'), 'figures': len(els)})
    if s_ == 'Caption':
        pt_ = mapped(str(par.S).lstrip('/')) if par is not None else 'root'
        sib = [mapped(str(k.S).lstrip('/')) for k in _kids(par) if _is_el(k)] if par is not None else []
        if pt_ not in ('Figure', 'Table', 'L', 'TOC', 'Formula') and not any(x in ('Figure', 'Table', 'Formula') for x in sib):
            cap_loose.append({'page': _holder_pg(n), 'parent': pt_})
    for k in reversed(ks): stk.append((k, n))
URL_ONLY = re.compile(r'\s*(?:https?://|www\.)\S+\s*')
url_links = [{'page': live[og], 'contents': str(pdf.get_object(og).get('/Contents', ''))} for og in live
             if str(pdf.get_object(og).get('/Subtype')) == '/Link' and URL_ONLY.fullmatch(str(pdf.get_object(og).get('/Contents', '')))]
# tables whose every cell is empty (empty cells inside a real table are normal and not counted above)
def _has_content(n, d=0):
    for k in _kids(n):
        if isinstance(k, int) or (isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) in ('/MCR', '/OBJR')): return True
        if _is_el(k) and (d > 60 or _has_content(k, d + 1)): return True
    return False
empty_tables = []
stk = [(k, None) for k in _kids(st)]
while stk:
    n, par = stk.pop()
    if not _is_el(n): continue
    if mapped(str(n.S).lstrip('/')) == 'Table' and not _has_content(n): empty_tables.append({'page': _empty_pg(n, par)})
    for k in _kids(n): stk.append((k, n))
# the tag-tree index must point only into the tree: a ParentTree or IDTree entry naming a tag that is not in the tree is
# dangling; an entry for marked content that is no longer drawn (or a key nothing uses) is stale
in_tree = set(el_type)
key_page = {int(p.obj['/StructParents']): i for i, p in enumerate(pages, 1) if '/StructParents' in p.obj}
key_annot = {int(a.StructParent) for p in pages for a in (p.obj.get('/Annots') or []) if isinstance(a, pikepdf.Dictionary) and '/StructParent' in a}
key_form = {int(x.StructParents) for p in pages for x in (p.obj.get('/Resources', {}).get('/XObject') or {}).values() if isinstance(x, pikepdf.Stream) and '/StructParents' in x}
dangling, stale = [], 0
drawn_cache = {}
def _drawn(i):
    if i not in drawn_cache:
        drawn_cache[i] = {int(ins.operands[1].MCID) for ins in pikepdf.parse_content_stream(pages[i - 1])
                          if str(ins.operator) == 'BDC' and len(ins.operands) == 2 and isinstance(ins.operands[1], pikepdf.Dictionary) and '/MCID' in ins.operands[1]}
    return drawn_cache[i]
for key, v in PT.items():
    if isinstance(v, pikepdf.Array):
        for m, el in enumerate(v):
            if isinstance(el, pikepdf.Dictionary):
                if el.objgen not in in_tree: dangling.append({'index': 'ParentTree', 'key': key, 'mcid': m, 'page': key_page.get(key)})
                elif (key in key_page and m not in _drawn(key_page[key])) or (key not in key_page and key not in key_form): stale += 1
    elif isinstance(v, pikepdf.Dictionary):
        if v.objgen not in in_tree: dangling.append({'index': 'ParentTree', 'key': key, 'page': None})
        elif key not in key_annot: stale += 1
for idk, og in idmap.items():
    if og not in in_tree: dangling.append({'index': 'IDTree', 'id': idk.decode('latin-1'), 'page': None})
def _id_nulls(node, acc):                          # an ID that maps to nothing at all
    if '/Names' in node:
        nm = node.Names; acc += [bytes(nm[j]).decode('latin-1') for j in range(0, len(nm), 2) if not isinstance(nm[j + 1], pikepdf.Dictionary)]
    for k in node.get('/Kids') or []: _id_nulls(k, acc)
    return acc
for idk in (_id_nulls(st.IDTree, []) if '/IDTree' in st else []): dangling.append({'index': 'IDTree', 'id': idk, 'page': None})
out['index'] = {'dangling': len(dangling), 'dangling_examples': dangling[:12], 'stale_entries': stale}
out['structure'] = {'empty_tags': len(empty_el), 'empty_tag_examples': empty_el[:12], 'empty_tables': empty_tables,
                    'paragraphs_holding_only_figures': fig_only, 'captions_not_grouped': cap_loose, 'links_url_only': url_links}
# 6 pages wrapped whole as one Figure, and pages with no tags at all that still hold drawn content
src = pikepdf.open(A)
def _raw(p):
    c = p.obj.get('/Contents')
    if c is None: return b''
    return b'\n'.join(x.read_bytes() for x in c) if isinstance(c, pikepdf.Array) else c.read_bytes()
pf, uo_pages = [], []
for i, p in enumerate(pages, 1):
    raw = _raw(p)
    if raw.lstrip().startswith(b'/Figure <</MCID 0>> BDC'):
        figs_here = {og for (pg_, m), og in owner.items() if pg_ == i and el_type.get(og) == 'Figure'}
        others = {og for (pg_, m), og in owner.items() if pg_ == i and el_type.get(og) != 'Figure'}
        alt = any(str(pdf.get_object(og).get('/Alt', '')).strip() for og in figs_here)
        pf.append({'page': i, 'figures': len(figs_here), 'other_tags': len(others), 'alt': alt, 'untagged_left': sum(free_pages[i].values())})
    elif free_pages.get(i) and not any(pg_ == i for pg_, _ in owner) and b'/Artifact' not in raw:
        uo_pages.append({'page': i, 'untagged': dict(free_pages[i]), 'same_as_source': raw == _raw(src.pages[i - 1])})
out['page_figures'] = pf; out['untagged_only_pages'] = uo_pages
json.dump(out, open(B + '.verify.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
