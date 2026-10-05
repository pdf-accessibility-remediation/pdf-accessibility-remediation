"""Verify work/remediated.pdf against the original. Read-only."""
import sys, json, re, collections
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import plumb_fix
import pikepdf, pdfplumber, pypdfium2 as pdfium
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
    if t == '/MCR': owner[(pidx[n.Pg.objgen] if '/Pg' in n else pg, int(n.MCID))] = par.objgen; continue
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
out['doc'] = {'title': str(pdf.docinfo.Title), 'lang': str(pdf.Root.Lang), 'DisplayDocTitle': bool(pdf.Root.ViewerPreferences.DisplayDocTitle),
              'acroform': '/AcroForm' in pdf.Root, 'encrypted': pdf.is_encrypted}
with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as m: out['doc']['xmp_title'] = str(m.get('dc:title')); out['doc']['pdfua_stamped'] = any('pdfuaid' in k for k in m.keys())
json.dump(out, open(B + '.verify.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
