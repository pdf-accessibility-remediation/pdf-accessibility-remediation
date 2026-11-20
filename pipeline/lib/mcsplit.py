"""mcsplit.py: tag part of a marked-content run, by splitting it into new runs (#118, language tagging). Pure functions
on a page's content-stream instructions (pikepdf); apply.py writes the structure (fix_language_parts).

    split_run(ins, fonts_at, mcid, cuts, new_mcid)  -> (instructions, pieces)  or raises Refuse(reason)
    drop_lang(ins, mcid)                             -> (instructions, True if a /Lang was removed)
    drawn_mcids(ins)                                 -> MCIDs drawn in these instructions

A place is found by counting character codes, never by decoding text (review 02, H2): `cuts` are (first, last) indexes
of the run's characters, counted as pdfplumber lists them (one character per character code, in content order; the codes
under a nested spoken-text span are counted, the span's own text is not). One byte per code for a simple font, two for a
Type0 font with Identity-H; anything else is refused. So a font with no ToUnicode map, a /Differences encoding or a
bfrange map is split the same way.

How a run is split, with nothing that draws or moves the pen added, removed or changed:
  1. A run opened outside its text object (BDC BT … ET EMC) has its marks moved inside each text object it holds (BT BDC
     … EMC ET), one run per text object (the first keeps the MCID, later ones get new MCIDs), so no marked content crosses
     a text object once it is split. A run that draws anything outside its text objects is refused.
  2. Text-showing operators are cut at each place's first and last character: a Tj into Tj + Tj, a TJ into TJ + TJ, each
     kerning number staying with the text before it when a string precedes it in that piece, else moving to the next
     piece (the pen moves the same either way). ' becomes T* Tj inside the run; a run with " is refused (pdfminer
     reads " without its line move, so the text verify.py reads would change).
  3. Marks: the run is closed before the place, /Span <</MCID s>> opened for it (no /Lang: the structure element carries
     the language, and marked content that names another language would override it: review 02, H1), and the run
     reopened after it with its own properties and a new MCID.
A boundary inside a glyph (a ligature) or inside a spoken-text span, or a place across two text objects, is refused.
`pieces` lists the run's new marked-content sequences in content order: (mcid, 'run' | 'span', index of the cut or None).
"""
import pikepdf

I, Op = pikepdf.ContentStreamInstruction, pikepdf.Operator
SHOW = {'Tj', 'TJ', "'", '"'}
DRAW = {'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'S', 's', 'sh', 'Do', 'BI', 'INLINE IMAGE', 'EI'}

class Refuse(Exception): pass

def _props(x):
    return x.operands[1] if str(x.operator) == 'BDC' and len(x.operands) > 1 and isinstance(x.operands[1], pikepdf.Dictionary) else None

def _mcid(x):
    p = _props(x)
    return int(p.MCID) if p is not None and '/MCID' in p else None

def drawn_mcids(ins):
    return {m for m in (_mcid(x) for x in ins) if m is not None}

def find_run(ins, mcid):
    """(start, end): indexes of the run's BDC and its matching EMC, or None when it is not drawn here."""
    start = next((i for i, x in enumerate(ins) if _mcid(x) == mcid), None)
    if start is None: return None
    d = 0
    for k in range(start, len(ins)):
        op = str(ins[k].operator)
        if op in ('BDC', 'BMC'): d += 1
        elif op == 'EMC':
            d -= 1
            if d == 0: return start, k
    raise Refuse("the text's marked content is not closed")

def count_codes(ins, fonts, mcid, xobjects=None):
    """How many character codes run `mcid` shows in these instructions, nested marked content and spoken-text spans
    included: the count pdfplumber gives its MCID when the run is drawn here. Raises Refuse only when the run is not
    drawn here, or its codes can't be counted (a font with an unknown encoding, a form drawn inside it). Unlike
    split_run, nothing else refuses: a run with a path, an image, its own ActualText or a " operator is still counted
    (review 06, M1: apply.py's check that a tag lands on the run pdfplumber read)."""
    se = find_run(ins, mcid)
    if se is None: raise Refuse('the text is not drawn in the page content')
    start, end = se
    cur = _font_state(ins, start, fonts); q = []; n = 0
    for i in range(start + 1, end):
        x = ins[i]; op = str(x.operator)
        if op == 'Tf': cur = (str(x.operands[0]), fonts.get(x.operands[0]) if fonts is not None else None)
        elif op == 'q': q.append(cur)
        elif op == 'Q' and q: cur = q.pop()
        elif op == 'Do':                             # an image adds no characters; a form may (with or without its own MCIDs)
            xo = (xobjects or {}).get(x.operands[0]) if xobjects is not None else None
            if xo is None or str(xo.get('/Subtype')) != '/Image': raise Refuse('cannot count: a form drawn inside the text')
        elif op in ('Tj', 'TJ', "'", '"'):
            f = cur[1] if cur else None
            if f is None: raise Refuse('cannot count: text before any font')
            st = str(f.get('/Subtype'))
            if st == '/Type0':
                if str(f.get('/Encoding')) not in ('/Identity-H', '/Identity-V'): raise Refuse('cannot count: two-byte font with another encoding')
                nb = 2
            else: nb = 1
            arg = x.operands[-1]
            strs = [y for y in arg if isinstance(y, pikepdf.String)] if op == 'TJ' else [arg]
            n += sum(len(bytes(y)) // nb for y in strs)
    return n

def count_all(ins, fonts, xobjects=None):
    """{mcid: count, or the reason count_codes would refuse} for every run in these instructions, in one pass (#165: a
    form's text is thousands of runs, and count_codes scans the whole list for each). The same rules as count_codes: a
    run's own codes and those of marked content nested in it; the first run of a number only (find_run's); the font in
    force from the start (Tf, q and Q); a form drawn inside a run, text before any font, or a two-byte font with another
    encoding refuse the runs open at that point; a run never closed is refused as find_run refuses it."""
    out, open_, seen, cur, q = {}, [], set(), None, []
    def refuse(why):
        for _d, m in open_:
            if m is not None and not isinstance(out[m], str): out[m] = why
    for x in ins:
        op = str(x.operator)
        if op in ('BDC', 'BMC'):
            m = _mcid(x)
            if m is not None and m in seen: m = None            # a second run of the same number: find_run takes the first
            if m is not None: seen.add(m); out[m] = 0
            open_.append((len(open_), m)); continue
        if op == 'EMC':
            if open_: open_.pop()
            continue
        if op == 'Tf': cur = (str(x.operands[0]), fonts.get(x.operands[0]) if fonts is not None else None)
        elif op == 'q': q.append(cur)
        elif op == 'Q' and q: cur = q.pop()
        elif op == 'Do':
            if not any(m is not None for _d, m in open_): continue
            xo = (xobjects or {}).get(x.operands[0]) if xobjects is not None else None
            if xo is None or str(xo.get('/Subtype')) != '/Image': refuse('cannot count: a form drawn inside the text')
        elif op in ('Tj', 'TJ', "'", '"'):
            if not any(m is not None for _d, m in open_): continue
            f = cur[1] if cur else None
            if f is None: refuse('cannot count: text before any font'); continue
            if str(f.get('/Subtype')) == '/Type0':
                if str(f.get('/Encoding')) not in ('/Identity-H', '/Identity-V'): refuse('cannot count: two-byte font with another encoding'); continue
                nb = 2
            else: nb = 1
            arg = x.operands[-1]
            k = sum(len(bytes(y)) // nb for y in ([y for y in arg if isinstance(y, pikepdf.String)] if op == 'TJ' else [arg]))
            for _d, m in open_:
                if m is not None and not isinstance(out[m], str): out[m] += k
    for _d, m in open_:
        if m is not None: out[m] = "the text's marked content is not closed"
    return out

def drop_lang_many(ins, mcids):
    """drop_lang for several runs in one pass: (instructions, how many /Lang were removed)."""
    ins, n, todo = list(ins), 0, set(mcids)
    for i, x in enumerate(ins):
        if not todo: break
        m = _mcid(x)
        if m in todo:
            todo.discard(m); p = _props(x)
            if '/Lang' in p:
                ins[i] = I([x.operands[0], pikepdf.Dictionary({k: v for k, v in p.items() if k != '/Lang'})], Op('BDC')); n += 1
    return ins, n

def code_bytes(font):
    """Bytes per character code: 1 (simple font), 2 (Type0, Identity-H). Refused otherwise."""
    if font is None: raise Refuse('text before any font')
    st = str(font.get('/Subtype'))
    if st == '/Type3': raise Refuse('Type3 font')
    if st == '/Type0':
        enc = str(font.get('/Encoding'))
        if enc == '/Identity-H': return 2
        raise Refuse('vertical writing' if enc == '/Identity-V' else 'two-byte font with another encoding')
    return 1

def drop_lang(ins, mcid):
    """The run's BDC without /Lang (the structure element carries the language: review 02, H1)."""
    ins = list(ins)
    for i, x in enumerate(ins):
        if _mcid(x) == mcid:
            p = _props(x)
            if '/Lang' not in p: return ins, False
            d = pikepdf.Dictionary({k: v for k, v in p.items() if k != '/Lang'})
            ins[i] = I([x.operands[0], d], Op('BDC'))
            return ins, True
    return ins, False

def _font_state(ins, upto, fonts):
    """The font in force just before instruction `upto` (Tf is graphics state: saved by q, restored by Q)."""
    cur, gs = None, []
    for x in ins[:upto]:
        op = str(x.operator)
        if op == 'Tf': cur = fonts.get(x.operands[0]) if fonts is not None else None; cur = (str(x.operands[0]), cur)
        elif op == 'q': gs.append(cur)
        elif op == 'Q' and gs: cur = gs.pop()
    return cur

def split_run(ins, fonts, mcid, cuts, new_mcid, expect_n=None):
    """ins: the page's instructions. fonts: the page's /Font resources. cuts: [(first, last), …], indexes of the run's
    characters, not overlapping. new_mcid(): the next free MCID on the page. expect_n: how many characters pdfplumber
    lists for this MCID; any other count of codes here refuses the run (the content changed since, or a code the two
    count differently).
    Returns (new instructions, pieces) with pieces [(mcid, kind, cut index or None)], or raises Refuse."""
    ins = list(ins)
    se = find_run(ins, mcid)
    if se is None: raise Refuse('the text is not drawn in the page content')
    start, end = se
    p0 = _props(ins[start]); tag = ins[start].operands[0]
    if '/ActualText' in p0 or '/Alt' in p0: raise Refuse('the text has its own spoken text')
    bt = 0
    for x in ins[:start]:
        op = str(x.operator)
        if op == 'BT': bt += 1
        elif op == 'ET': bt -= 1
    inside = bt > 0
    # 1. the run's text objects (segments): (open, close) instruction indexes, exclusive of the marks
    segs, d, k, b0 = [], 0, start + 1, None
    if inside:
        for j in range(start + 1, end):
            if str(ins[j].operator) in ('BT', 'ET'): raise Refuse('the text crosses into another text object')
        segs = [(start, end)]
    else:
        for j in range(start + 1, end):
            op = str(ins[j].operator)
            if op == 'BT':
                if b0 is not None: raise Refuse('nested text objects')
                b0 = j
            elif op == 'ET':
                if b0 is None: raise Refuse("text object not opened inside the text's marked content")
                segs.append((b0, j)); b0 = None
            elif b0 is None and (op in DRAW or op in SHOW or op in ('BDC', 'BMC', 'EMC')):
                raise Refuse("the text's marked content draws outside its text objects")
        if b0 is not None or not segs: raise Refuse('the text has no closed text object')
    # 2. units: character codes in content order (a nested spoken-text span's codes form one group)
    units = []                       # dict(seg, i, e, b0, b1, group)
    fcur = _font_state(ins, (segs[0][0] if not inside else start), fonts)
    gid, q = 0, []
    for s, (a, z) in enumerate(segs):
        if not inside: fcur = _font_state(ins, a, fonts)
        depth, group = 0, None
        for i in range(a + 1, z):
            x = ins[i]; op = str(x.operator)
            if op == 'Tf': fcur = (str(x.operands[0]), fonts.get(x.operands[0]) if fonts is not None else None)
            elif op == 'q': q.append(fcur)
            elif op == 'Q' and q: fcur = q.pop()
            elif op in ('Do', 'BI', 'INLINE IMAGE'): raise Refuse('an image or form drawn inside the text')
            elif op in ('BDC', 'BMC'):
                p = _props(x)
                if depth == 0 and p is not None and '/ActualText' in p and '/MCID' not in p:
                    gid += 1; group = gid; depth = 1
                elif depth == 0 and op == 'BDC' and isinstance(x.operands[1], pikepdf.Name): raise Refuse('named property list')
                else: raise Refuse('other marked content nested in the text')
            elif op == 'EMC':
                if depth: depth, group = 0, None
            elif op == '"': raise Refuse('the text uses the " operator')
            elif op in ('Tj', 'TJ', "'"):
                nb = code_bytes(fcur[1] if fcur else None)
                parts = [(None, x.operands[0])] if op != 'TJ' else [(e, y) for e, y in enumerate(x.operands[0]) if isinstance(y, pikepdf.String)]
                for e, sv in parts:
                    raw = bytes(sv)
                    if len(raw) % nb: raise Refuse('odd byte count in a two-byte font')
                    for b in range(0, len(raw), nb):
                        units.append({'seg': s, 'i': i, 'e': e, 'b0': b, 'b1': b + nb, 'group': group})
    # 3. pieces: every unit gets a piece number; cuts must sit between units of different groups, in one segment
    n = len(units)
    if expect_n is not None and n != expect_n: raise Refuse('the characters do not line up with the text')
    piece = [0] * n
    order = sorted(cuts)
    bounds = []                      # (unit index where a piece starts, kind, cut index)
    prev_last = -1
    for ci, (f, l) in sorted(enumerate(cuts), key=lambda t: t[1]):
        if not (0 <= f <= l < n): raise Refuse('the characters do not line up with the text')
        if f <= prev_last: raise Refuse('places overlap')
        prev_last = l
        if units[f]['seg'] != units[l]['seg']: raise Refuse('the place crosses two text objects')
        for at in (f, l + 1):
            if 0 < at < n and units[at]['group'] is not None and units[at]['group'] == units[at - 1]['group']:
                raise Refuse('a boundary falls inside a spoken-text span')
        bounds.append((f, 'span', ci)); bounds.append((l + 1, 'run', None))
    del order
    # piece boundaries: the cuts, and each new segment
    starts = {}
    for s in range(len(segs)):
        first_u = next((u for u in range(n) if units[u]['seg'] == s), None)
        if first_u is not None: starts.setdefault(first_u, ('run', None))
    for at, kind, ci in bounds:
        if at < n: starts[at] = (kind, ci)
    plist = []                        # (first unit, kind, cut index)
    for at in sorted(starts):
        plist.append((at,) + starts[at])
    if not plist or plist[0][0] != 0: plist.insert(0, (0, 'run', None))
    # a 'run' piece with no units (a cut at the run's very end) disappears
    pieces = []
    for pi, (at, kind, ci) in enumerate(plist):
        nxt = plist[pi + 1][0] if pi + 1 < len(plist) else n
        if nxt <= at: continue
        for u in range(at, nxt): piece[u] = len(pieces)
        pieces.append([None, kind, ci, units[at]['seg']])
    if len(pieces) == 1 and pieces[0][1] == 'run': return ins, [(mcid, 'run', None)]
    for k_, pc in enumerate(pieces): pc[0] = mcid if k_ == 0 else new_mcid()
    # 4. rewrite each segment: cut showing operators where the piece changes, and put marks between pieces
    def bdc(pc):
        if pc[1] == 'span': return I([pikepdf.Name.Span, pikepdf.Dictionary(MCID=pc[0])], Op('BDC'))
        drop = ('/MCID',) if pc[0] == mcid else ('/MCID', '/E')   # /E (the expansion of an abbreviation) stays on the first piece only
        return I([tag, pikepdf.Dictionary({**{k: v for k, v in p0.items() if k not in drop}, '/MCID': pc[0]})], Op('BDC'))
    by_ins = {}
    for u, un in enumerate(units): by_ins.setdefault(un['i'], []).append(u)
    out = list(ins[:start]) if inside else list(ins[:start])
    def seg_body(s, a, z):
        res, cur = [], None
        first_u = next((u for u in range(n) if units[u]['seg'] == s), None)
        cur = piece[first_u] if first_u is not None else None
        if cur is None: return list(ins[a + 1:z]), None
        res.append(bdc(pieces[cur]))
        j = a + 1
        while j < z:
            x = ins[j]; op = str(x.operator)
            us = by_ins.get(j)
            if op in ('BDC', 'BMC') and j + 1 < z:
                # a nested spoken-text span: switch pieces before it when its first unit starts a new piece
                nu = next((by_ins[t][0] for t in range(j + 1, z) if t in by_ins), None)
                if nu is not None and piece[nu] != cur and all(units[t]['group'] is not None for t in [nu]):
                    res += [I([], Op('EMC')), bdc(pieces[piece[nu]])]; cur = piece[nu]
                res.append(x); j += 1; continue
            if not us:
                res.append(x); j += 1; continue
            if op == "'":
                res.append(I([], Op('T*'))); x = I([x.operands[0]], Op('Tj')); op = 'Tj'
            if op == 'Tj':
                raw = bytes(x.operands[0]); chunk = b''; cp = piece[us[0]]
                if cp != cur: res += [I([], Op('EMC')), bdc(pieces[cp])]; cur = cp
                for u in us:
                    if piece[u] != cur:
                        if chunk: res.append(I([pikepdf.String(chunk)], Op('Tj')))
                        res += [I([], Op('EMC')), bdc(pieces[piece[u]])]; cur = piece[u]; chunk = b''
                    chunk += raw[units[u]['b0']:units[u]['b1']]
                if chunk: res.append(I([pikepdf.String(chunk)], Op('Tj')))
            else:                                    # TJ
                arr = list(x.operands[0]); el, chunk = [], b''
                ue = {}
                for u in us: ue.setdefault(units[u]['e'], []).append(u)
                cp = piece[us[0]]
                if cp != cur: res += [I([], Op('EMC')), bdc(pieces[cp])]; cur = cp
                for e, y in enumerate(arr):
                    if not isinstance(y, pikepdf.String): el.append(y); continue
                    raw = bytes(y); chunk = b''
                    for u in ue.get(e, []):
                        if piece[u] != cur:
                            if chunk: el.append(pikepdf.String(chunk))
                            if any(isinstance(z_, pikepdf.String) and len(bytes(z_)) for z_ in el):
                                res.append(I([pikepdf.Array(el)], Op('TJ')))
                                res += [I([], Op('EMC')), bdc(pieces[piece[u]])]; el = []
                            else:                    # only kerning numbers so far: they move to the next piece
                                res += [I([], Op('EMC')), bdc(pieces[piece[u]])]
                            cur = piece[u]; chunk = b''
                        chunk += raw[units[u]['b0']:units[u]['b1']]
                    if chunk or not raw: el.append(pikepdf.String(chunk))
                if el: res.append(I([pikepdf.Array(el)], Op('TJ')))
            j += 1
        res.append(I([], Op('EMC')))
        return res, cur
    if inside:
        body, _ = seg_body(0, start, end)
        out += body
        out += ins[end + 1:]
    else:
        j = start + 1
        for s, (a, z) in enumerate(segs):
            out += ins[j:a]                          # state operators between text objects, now outside marked content
            out.append(ins[a])                       # BT
            body, _ = seg_body(s, a, z)
            out += body
            out.append(ins[z])                       # ET
            j = z + 1
        out += ins[j:end]
        out += ins[end + 1:]
    return out, [(pc[0], pc[1], pc[2]) for pc in pieces]
