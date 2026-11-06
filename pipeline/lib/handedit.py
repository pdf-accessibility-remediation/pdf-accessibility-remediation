"""lib/handedit.py: what changed when a person edited a run's PDF by hand (Acrobat or another tool), for handedit.py import.

    from lib import handedit
    imgs = handedit.page_images(path)              # {page: [{'sha256', 'box'}]}: each image drawn on a page, by its stream
    figs = handedit.figures(path)                  # [{'obj', 'page', 'alt', 'shas'}]: each Figure and the images it holds
    ch   = handedit.changed(base_path, edited_path) # new images per page, figures whose image changed, pages added or removed
    left = handedit.strip_stale_alt(edited_path, out_path, objs)   # a copy with /Alt and /ActualText removed from those figures

An image is the same when its stream's raw bytes are the same (sha256), compared page by page, so an Acrobat save that
renumbers every object changes nothing here. A figure "changed" when it holds an image that is not on the same page of
the base file: its old alt text described the old image, so it is removed in a working copy and written again (by the
AI, or by a person on the review page). The edited file itself is never written to.
"""
import hashlib
from lib import plumb_fix  # noqa: F401  patches pdfplumber first, so each image carries the nearest enclosing MCID
import pdfplumber, pikepdf

def _sha(img):
    s = img.get('stream')
    try: return hashlib.sha256(s.get_rawdata() if s is not None else b'').hexdigest()
    except Exception: return None                   # an image whose stream can't be read: never counted as the same

def page_images(path):
    """{page: [{'sha256', 'box', 'mcid'}]} for every image pdfplumber sees on each page (inline images included)."""
    out = {}
    with pdfplumber.open(path) as pl:
        for n, p in enumerate(pl.pages, 1):
            out[n] = [{'sha256': _sha(i), 'box': [round(float(i[k]), 1) for k in ('x0', 'top', 'x1', 'bottom')], 'mcid': i.get('mcid')}
                      for i in p.images]
            p.close()
    return out

def _kids(n):
    k = n.get('/K'); return [] if k is None else (list(k) if isinstance(k, pikepdf.Array) else [k])

def figures(path, imgs=None):
    """Each Figure element (after RoleMap) with its page, alt and the sha256 of every image under its marked content."""
    imgs = page_images(path) if imgs is None else imgs
    out = []
    with pikepdf.open(path) as pdf:
        st = pdf.Root.get('/StructTreeRoot')
        if st is None: return out
        pidx = {p.obj.objgen: i + 1 for i, p in enumerate(pdf.pages)}
        rm = {str(k).lstrip('/'): str(v).lstrip('/') for k, v in (st.get('/RoleMap') or {}).items()}
        def mapped(s):
            seen = set()
            while s in rm and s not in seen: seen.add(s); s = rm[s]
            return s
        def mcids(n, pg, acc, depth=0):                # every (page, mcid) under n, nested elements included
            if depth > 40: return acc
            for k in _kids(n):
                if isinstance(k, int): acc.append((pg, k))
                elif isinstance(k, pikepdf.Dictionary):
                    t = str(k.get('/Type'))
                    if t == '/MCR': acc.append((pidx.get(k.Pg.objgen) if '/Pg' in k else pg, int(k.MCID)))
                    elif t != '/OBJR': mcids(k, pidx.get(k.Pg.objgen) if '/Pg' in k else pg, acc, depth + 1)
            return acc
        stack, seen = [(k, None) for k in reversed(_kids(st))], set()
        while stack:
            n, pg = stack.pop()
            if not isinstance(n, pikepdf.Dictionary) or str(n.get('/Type')) in ('/MCR', '/OBJR'): continue
            if n.is_indirect:
                if n.objgen in seen: continue
                seen.add(n.objgen)
            pg = pidx.get(n.Pg.objgen) if '/Pg' in n else pg
            if mapped(str(n.get('/S', '')).lstrip('/')) == 'Figure':
                ms = mcids(n, pg, [])
                shas = sorted({i['sha256'] or '' for p, m in ms for i in imgs.get(p, []) if i['mcid'] == m})
                pages = sorted({p for p, _ in ms if p})
                out.append({'obj': f'{n.objgen[0]} {n.objgen[1]}', 'page': pages[0] if pages else pg, 'pages': pages,
                            'alt': str(n.Alt) if '/Alt' in n else None, 'shas': shas})
            for k in reversed(_kids(n)): stack.append((k, pg))
    return out

def changed(base, edited):
    """What the person changed, as far as images go: {'pages': (base count, edited count), 'new_images': [{page, box}],
    'removed_images': [{page, box}], 'figures': [{obj, page, alt}] whose image is new (obj in the EDITED file),
    'outside_figures': [{page, box}] new images that no Figure holds}."""
    bi, ei = page_images(base), page_images(edited)
    new, gone = [], []
    for pg, ims in ei.items():
        had = {i['sha256'] for i in bi.get(pg, []) if i['sha256']}
        new += [{'page': pg, 'box': i['box'], 'sha256': i['sha256'], 'mcid': i['mcid']} for i in ims if not i['sha256'] or i['sha256'] not in had]
    for pg, ims in bi.items():
        has = {i['sha256'] for i in ei.get(pg, []) if i['sha256']}
        gone += [{'page': pg, 'box': i['box']} for i in ims if not i['sha256'] or i['sha256'] not in has]
    new_by_page = {}
    for i in new: new_by_page.setdefault(i['page'], set()).add(i['sha256'] or '')
    figs, held = [], set()
    for f in figures(edited, ei):
        hit = [s for p in f['pages'] for s in new_by_page.get(p, ()) if s in f['shas']]
        if hit:
            figs.append({'obj': f['obj'], 'page': f['page'], 'alt': f['alt']}); held.update((p, s) for p in f['pages'] for s in hit)
    outside = [{'page': i['page'], 'box': i['box']} for i in new if (i['page'], i['sha256'] or '') not in held]
    return {'pages': [len(bi), len(ei)], 'new_images': [{'page': i['page'], 'box': i['box']} for i in new],
            'removed_images': gone, 'figures': figs, 'outside_figures': outside}

def strip_stale_alt(edited, out, objs):
    """Write a copy of `edited` to `out` with /Alt and /ActualText removed from the Figure elements `objs` ("N G" in the edited
    file). Returns the objs that could not be found (left as they are; nothing is half-changed). `edited` is never written to."""
    missing = []
    with pikepdf.open(edited) as pdf:
        for o in objs:
            try:
                n, g = (int(x) for x in str(o).split())
                el = pdf.get_object((n, g))
            except Exception: el = None
            if not isinstance(el, pikepdf.Dictionary) or '/S' not in el: missing.append(o); continue
            for k in ('/Alt', '/ActualText'):
                if k in el: del el[k]
        pdf.save(out)
    return missing
