"""lib/tagfix.py: two checks around intake's auto-tagger (#127, the generated cover page; checklist rule 1 and 3.6).

restore(src, tagged)   puts back the marked-content spans the auto-tagger dropped that set how text is spoken
                       (/ActualText: small capitals on the publisher's cover, soft hyphens). Only RESTORE_KEYS are carried;
                       another property is one more entry there. A span is placed by glyph-byte offset inside its own
                       content stream (the page, or a form found by its name path), so a run the tagger split is still
                       found. A stream is restored all or nothing, and is a misfit (left as tagged, logged) when:
                         - its glyph bytes differ from the source, byte for byte;
                         - it uses the ' or " operators (they move to a new line as they show text);
                         - a span's ends fall inside one of the tagger's show operators;
                         - a span's run would cross the tagger's own marked content;
                         - its form sits deeper than FORM_DEPTH;
                         - the page or a form draws with a tiling pattern that shows text or draws a form (review 04 M1).
                       restore checks the glyph bytes only, not where they are drawn: the geometry is compare()'s (intake
                       runs it on every page after the restore: pixels, then text).
same_drawing(a, b, n)  page n draws exactly the same in both files: the operators through the page and its forms, with
                       the marked-content operators left out and consecutive Tj/TJ merged into one show sequence (a split
                       run is neutral in PDF: character spacing applies per glyph, word spacing per space byte, numbers in
                       order); operands compared to four decimals, TJ numbers of 0 dropped; each font compared by its
                       fingerprint (program, widths, encoding, ToUnicode), not by its resource name. A form deeper than
                       FORM_DEPTH, or a tiling pattern that shows text or draws a form, makes the page a misfit, never
                       a pass; any other tiling pattern's operators (paths, colours), matrix, box and steps are compared
                       (review 06 M3). Not compared: shadings, images' pixels, annotation appearance streams (intake's
                       pixel check covers them).
Pure pikepdf: no Java, no OCR."""
import re, hashlib, collections
import pikepdf

RESTORE_KEYS = ('/ActualText',)            # #127: ActualText only (/Alt, /E, /Lang: not measured, off this branch)
SHOW = {'Tj', 'TJ'}
MOVE_SHOW = {"'", '"'}                     # show text after moving to the next line: refused by restore
MC = {'BDC', 'BMC', 'EMC'}
FORM_DEPTH = 3                             # forms nested deeper than this are not read: a misfit, not a pass


class Unreadable(Exception):
    """A page this module does not read in full: a misfit for restore, never a pass for same_drawing."""


class TooDeep(Unreadable):
    pass


class PatternText(Unreadable):
    pass


def _patterns(res):
    """PatternText when a tiling pattern in these resources shows text or draws a form (review 04 M1: its content is not
    walked, so a change there would pass the operator comparison; PDFium's text check does not read it either)."""
    for name, pt in ((res or {}).get('/Pattern') or {}).items():
        if not isinstance(pt, pikepdf.Stream) or int(pt.get('/PatternType', 0)) != 1: continue
        xo = (pt.get('/Resources') or {}).get('/XObject') or {}
        for ins in pikepdf.parse_content_stream(pt):
            op = str(ins.operator)
            if op in SHOW or op in MOVE_SHOW or op == 'Do' and (xo.get(ins.operands[0]) or {}).get('/Subtype') == '/Form':
                raise PatternText(f'tiling pattern {name} {"shows text" if op != "Do" else "draws a form"}')


def _ins(ops):
    return [(i, str(i.operator), list(i.operands)) for i in ops]


def _parse(owner):
    return list(pikepdf.parse_content_stream(owner))


def streams(page):
    """{name path: (owner, resources)} for the page and every form it draws, depth first. TooDeep past FORM_DEPTH,
    PatternText for a tiling pattern that shows text or draws a form."""
    out = {}

    def walk(owner, res, key, d):
        out[key] = (owner, res); _patterns(res)
        for ins in _parse(owner):
            if str(ins.operator) != 'Do': continue
            x = ((res or {}).get('/XObject') or {}).get(ins.operands[0])
            if x is None or x.get('/Subtype') != '/Form': continue
            if d >= FORM_DEPTH: raise TooDeep(f'form {"/".join(key[1:] + (str(ins.operands[0]),))} is nested deeper than {FORM_DEPTH}')
            sub = key + (str(ins.operands[0]),)
            if sub not in out: walk(x, x.get('/Resources', res), sub, d + 1)
    walk(page, page.obj.get('/Resources'), ('page',), 0)
    return out


def _glyphs(op, a):
    if op == 'Tj': return bytes(a[0])
    if op == 'TJ': return b''.join(bytes(x) for x in a[0] if isinstance(x, pikepdf.String))
    if op in MOVE_SHOW: return bytes(a[-1])
    return b''


def _props(a, res):
    p = a[1] if len(a) > 1 else None
    if isinstance(p, pikepdf.Name): p = ((res or {}).get('/Properties') or {}).get(p)
    return p if isinstance(p, pikepdf.Dictionary) else None


def bdc_props(operands, res):
    """The property list of a BDC: inline, or named (/P /MC0 BDC) and resolved through the stream's /Properties in res.
    #166, review 04 H1: the one way every reader asks what a BDC carries, so a named run is never read as untagged."""
    return _props(list(operands), res)


def bdc_mcid(operands, res):
    """The MCID a BDC gives (inline or through a named property list), or None."""
    p = _props(list(operands), res)
    return int(p.MCID) if p is not None and '/MCID' in p else None


# A form's MCIDs (#167, review 06 §2). #167 finds them by searching the form's bytes for /MCID, which is fast but sees only
# an inline property list. A form whose marked content names its properties (/P /MC0 BDC) holds no /MCID bytes, so its
# bytes are parsed operator by operator, and only then: the search for a named BDC is one more byte search, and a form
# without one gives exactly what the byte search gave before.
MCID_RX = re.compile(rb'/MCID\s+(\d+)')
_TOK = rb'[^\s/\[\]<>(){}%]+'
NAMED_BDC_RX = re.compile(rb'/' + _TOK + rb'\s*/' + _TOK + rb'\s+BDC(?![^\s/\[\]<>(){}%])')    # a tag, a property name, BDC


def names_props(data):
    """The stream's bytes show a BDC that names its property list (/P /MC0 BDC)."""
    return NAMED_BDC_RX.search(data) is not None


def form_mcids(x, res=None, data=None):
    """The MCIDs a content stream's own marked content gives (not those of the forms it draws), as a set. Without a named
    BDC: the byte search, as before. With one: each BDC resolved against res (the stream's own /Resources when not given);
    the byte search again if the stream can't be parsed."""
    if data is None:
        try: data = x.read_bytes()
        except Exception: return set()
    if not names_props(data): return set(map(int, MCID_RX.findall(data)))
    res = x.get('/Resources') if res is None else res
    try: return {m for m in (bdc_mcid(i.operands, res) for i in pikepdf.parse_content_stream(x, 'BDC')) if m is not None}
    except Exception: return set(map(int, MCID_RX.findall(data)))


def form_has_mcids(x, res=None, data=None):
    """The stream holds marked content with an MCID: b'/MCID' in its bytes, as before, or a named BDC that resolves to one."""
    if data is None:
        try: data = x.read_bytes()
        except Exception: return False
    return b'/MCID' in data or (names_props(data) and bool(form_mcids(x, res, data)))


def _spans(ops, res, empty=None):
    """Spans carrying RESTORE_KEYS: [(props {key: value}, glyph start, glyph end)], the stream's glyph bytes, and whether
    it uses ' or ". empty: a list that receives the props of each such span holding no glyph bytes (an image, a path or
    nothing: review 09 H-A), which restore cannot place by byte offset."""
    out, stack, buf, moves = [], [], bytearray(), False
    for ins, op, a in ops:
        if op == 'BDC':
            p = _props(a, res)
            keep = {k: p[k] for k in RESTORE_KEYS if p is not None and k in p}
            stack.append((keep, len(buf)))
        elif op == 'BMC': stack.append(({}, len(buf)))
        elif op == 'EMC' and stack:
            keep, s = stack.pop()
            if keep and len(buf) > s: out.append((keep, s, len(buf)))
            elif keep and empty is not None: empty.append(keep)
        elif op in SHOW or op in MOVE_SHOW:
            moves = moves or op in MOVE_SHOW
            buf += _glyphs(op, a)
    return out, bytes(buf), moves


def _key(props):
    return tuple(sorted((k, str(v)) for k, v in props.items()))


def _has_restorable(page):
    """Cheap first look: does the page (or a form it draws, or a /Properties entry) mention a RESTORE_KEY at all?"""
    seen, todo = set(), [(page.obj, True)]
    names = [k.lstrip('/').encode() for k in RESTORE_KEYS]
    while todo:
        o, is_page = todo.pop()
        if o.objgen != (0, 0):
            if o.objgen in seen: continue
            seen.add(o.objgen)
        cont = o.get('/Contents') if is_page else o
        for s in (list(cont) if isinstance(cont, pikepdf.Array) else [cont]):
            if isinstance(s, pikepdf.Stream) and any(n in s.read_bytes() for n in names): return True
        res = o.get('/Resources') or {}
        for p in (res.get('/Properties') or {}).values():
            if isinstance(p, pikepdf.Dictionary) and any(k in p for k in RESTORE_KEYS): return True
        for x in (res.get('/XObject') or {}).values():
            if isinstance(x, pikepdf.Stream) and x.get('/Subtype') == '/Form': todo.append((x, False))
    return False


def restore(src, tagged):
    """Put the dropped RESTORE_KEYS spans back into `tagged` (saved in place when anything changed).
    Returns {'spans': N, 'pages': {page: N}, 'values': Counter of restored values, 'misfits': [(page, stream, why)]}."""
    rep = {'spans': 0, 'pages': {}, 'values': collections.Counter(), 'misfits': []}
    changed = False
    with pikepdf.open(src) as s, pikepdf.open(tagged, allow_overwriting_input=True) as t:
        if len(s.pages) != len(t.pages):
            rep['misfits'].append((None, None, 'page count differs')); return rep
        for n, (sp, tp) in enumerate(zip(s.pages, t.pages), 1):
            if not _has_restorable(sp): continue
            try: ss, ts = streams(sp), streams(tp)
            except Unreadable as e: rep['misfits'].append((n, None, str(e))); continue
            for key, (sown, sres) in ss.items():
                s_empty, t_empty = [], []
                want, sbytes, smove = _spans(_ins(_parse(sown)), sres, s_empty)
                if not want and not s_empty: continue
                where = '/'.join(key)
                if key not in ts: rep['misfits'].append((n, where, 'stream missing after tagging')); continue
                town, tres = ts[key]; tops = _ins(_parse(town))
                have, tbytes, tmove = _spans(tops, tres, t_empty)
                lost = collections.Counter(_key(p) for p in s_empty) - collections.Counter(_key(p) for p in t_empty)
                if lost:                                  # review 09 H-A: spoken text on an image or a drawing (no glyphs to place by)
                    rep['misfits'].append((n, where, f'spoken text on an image or a drawing was dropped ({", ".join(str(dict(k)) for k in list(lost)[:3])})'))
                if not want: continue
                if smove or tmove: rep['misfits'].append((n, where, "uses the ' or \" operator")); continue
                if sbytes != tbytes: rep['misfits'].append((n, where, 'glyph bytes differ from the source')); continue
                present = {(_key(p), b0, b1) for p, b0, b1 in have}
                todo = [(p, b0, b1) for p, b0, b1 in want if (_key(p), b0, b1) not in present]
                if not todo: continue
                rng, pos = [], 0                                  # (op index, glyph start, glyph end) of each show op
                for k, (ins, op, a) in enumerate(tops):
                    if op in SHOW:
                        g = len(_glyphs(op, a))
                        if g: rng.append((k, pos, pos + g))
                        pos += g
                placed, bad = [], None
                for p, b0, b1 in todo:
                    first = next((r for r in rng if r[1] == b0), None); last = next((r for r in rng if r[2] == b1), None)
                    if first is None or last is None or first[0] > last[0]:
                        bad = f'a span ({_key(p)}) ends inside one of the tagger\'s show operators'; break
                    depth = 0
                    for ins, op, a in tops[first[0]:last[0] + 1]:
                        depth += {'BDC': 1, 'BMC': 1, 'EMC': -1}.get(op, 0)
                        if depth < 0: break
                    if depth != 0:
                        bad = f'a span ({_key(p)}) would cross the tagger\'s marked content'; break
                    placed.append((first[0], last[0], p))
                if bad: rep['misfits'].append((n, where, bad)); continue
                for i0, i1, _ in placed:                          # spans must nest: no two may cross
                    for j0, j1, _ in placed:
                        if i0 < j0 <= i1 < j1: bad = 'two spans cross'
                if bad: rep['misfits'].append((n, where, bad)); continue
                opens, closes = collections.defaultdict(list), collections.defaultdict(list)
                for i0, i1, p in placed:
                    opens[i0].append((i1, p)); closes[i1].append(i0)
                out = []                                          # one pass: no index moves under a later insertion (M1)
                for k, (ins, op, a) in enumerate(tops):
                    for i1, p in sorted(opens.get(k, []), key=lambda x: -x[0]):    # the outer (longer) span opens first
                        out.append(pikepdf.ContentStreamInstruction(
                            [pikepdf.Name('/Span'), pikepdf.Dictionary({kk: pikepdf.String(bytes(v)) for kk, v in p.items()})],
                            pikepdf.Operator('BDC')))
                    out.append(ins)
                    for _ in closes.get(k, []):                   # spans closing here: inner first, all the same EMC
                        out.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator('EMC')))
                data = pikepdf.unparse_content_stream(out)
                if key == ('page',): tp.obj.Contents = t.make_stream(data)
                else: town.write(data)
                changed = True; rep['spans'] += len(placed); rep['pages'][n] = rep['pages'].get(n, 0) + len(placed)
                for _, _, p in placed:
                    for v in p.values(): rep['values'][str(v)] += 1
        if changed: t.save(tagged)
    return rep


def lost_values(src, tagged):
    """The whole-file backstop after restore (review 09 H-A): {page: [RESTORE_KEYS values the source carries that the tagged
    file does not]}, each value counted as often as it occurs on the page and in the forms it draws (drawing's props).
    A page either file cannot read in full is left out (restore lists it as a misfit)."""
    out = {}
    with pikepdf.open(src) as s, pikepdf.open(tagged) as t:
        if len(s.pages) != len(t.pages): return out
        for n, (sp, tp) in enumerate(zip(s.pages, t.pages), 1):
            if not _has_restorable(sp): continue
            try: a, b = collections.Counter(drawing(sp)[1]), collections.Counter(drawing(tp)[1])
            except Unreadable: continue
            miss = a - b
            if miss: out[n] = sorted(v for (k, v), c in miss.items() for _ in range(c))
    return out


# ------------------------------------------------------------------ same drawing
def _v(x):
    if isinstance(x, bool): return x
    if isinstance(x, (int, float)) or type(x).__name__ == 'Decimal': return round(float(x), 4)
    if isinstance(x, pikepdf.Array): return tuple(_v(y) for y in x)
    if isinstance(x, pikepdf.String): return bytes(x)
    if isinstance(x, pikepdf.Name): return str(x)
    if isinstance(x, pikepdf.Dictionary): return 'dict'
    return repr(x)


def _h(o):
    if isinstance(o, pikepdf.Stream): return hashlib.sha256(o.read_bytes()).hexdigest()[:16]
    if isinstance(o, pikepdf.Array): return tuple(_h(x) for x in o)
    if isinstance(o, pikepdf.Dictionary): return tuple(sorted((str(k), _h(v)) for k, v in o.items() if str(k) not in ('/Parent', '/P')))
    return _v(o)


def font_fingerprint(font, cache):
    """What decides a font's glyphs and text: program, widths, encoding, ToUnicode (and a Type0 font's descendant)."""
    if font is None: return None
    k = font.objgen
    if k != (0, 0) and k in cache: return cache[k]
    parts = [str(font.get('/Subtype')), str(font.get('/BaseFont'))]
    for key in ('/Encoding', '/Widths', '/FirstChar', '/ToUnicode', '/CharProcs', '/FontMatrix'):
        parts.append((key, _h(font.get(key)) if key in font else None))
    fd = font.get('/FontDescriptor')
    if fd is not None:
        for key in ('/FontFile', '/FontFile2', '/FontFile3'):
            if key in fd: parts.append((key, _h(fd[key])))
    for d in font.get('/DescendantFonts') or []:
        parts.append(('descendant', font_fingerprint(d, cache)))
        for key in ('/W', '/DW', '/CIDToGIDMap'):
            if key in d: parts.append((key, _h(d[key])))
    fp = hashlib.sha256(repr(parts).encode()).hexdigest()[:16]
    if k != (0, 0): cache[k] = fp
    return fp


def drawing(page):
    """(normalised operator list, RESTORE_KEYS values in order) for a page and its forms, with each tiling pattern's own
    operators, matrix, box and steps (review 06 M3). TooDeep past FORM_DEPTH, PatternText for a tiling pattern that shows
    text or draws a form. Not compared: shading patterns and shadings (dictionaries, named only), images' pixels (the image
    XObject's name only), annotation appearance streams; intake's pixel check covers those."""
    out, props, cache = [], [], {}

    def walk(owner, res, d):
        _patterns(res)
        for nm, pt in sorted((((res or {}).get('/Pattern') or {}).items()), key=lambda kv: str(kv[0])):   # review 06 M3: a tiling
            if isinstance(pt, pikepdf.Stream) and int(pt.get('/PatternType', 0)) == 1:   # pattern's paths and colours count too
                out.append(('PATTERN', (str(nm), _v(pt.get('/Matrix')) if '/Matrix' in pt else None, _v(pt.get('/BBox')),
                                        _v(pt.get('/XStep')), _v(pt.get('/YStep')), int(pt.get('/PaintType', 1)),
                                        tuple((str(i.operator), tuple(_v(x) for x in i.operands)) for i in pikepdf.parse_content_stream(pt)))))
        for ins in _parse(owner):
            op, a = str(ins.operator), list(ins.operands)
            if op in MC:
                if op == 'BDC':
                    p = _props(a, res)
                    for k in RESTORE_KEYS:
                        if p is not None and k in p: props.append((k, str(p[k])))
                continue
            if op in SHOW:
                items = [bytes(a[0])] if op == 'Tj' else [bytes(x) if isinstance(x, pikepdf.String) else round(float(x), 4) for x in a[0]]
                if out and out[-1][0] == 'SHOW': out[-1][1].extend(items)
                else: out.append(('SHOW', items))
                continue
            if op == 'Tf':
                f = ((res or {}).get('/Font') or {}).get(a[0])
                out.append(('Tf', (font_fingerprint(f, cache), _v(a[1])))); continue
            out.append((op, tuple(_v(x) for x in a)))
            if op == 'Do':
                x = ((res or {}).get('/XObject') or {}).get(a[0])
                if x is not None and x.get('/Subtype') == '/Form':
                    if d >= FORM_DEPTH: raise TooDeep(f'form {a[0]} is nested deeper than {FORM_DEPTH}')
                    out.append(('FORM', (_v(x.get('/Matrix')) if '/Matrix' in x else None, _v(x.get('/BBox')))))
                    walk(x, x.get('/Resources', res), d + 1); out.append(('ENDFORM', ()))
    walk(page, page.obj.get('/Resources'), 0)
    norm = []
    for op, a in out:
        if op == 'SHOW':                                  # ["B", " "] and ["B "] draw the same; a 0 number moves nothing
            m = []
            for it in a:
                if isinstance(it, bytes):
                    if m and isinstance(m[-1], bytes): m[-1] += it
                    else: m.append(it)
                elif it != 0.0: m.append(it)
            norm.append((op, tuple(m)))
        else: norm.append((op, a))
    return norm, props


def same_drawing(a_pdf, b_pdf, n):
    """(same drawing, same spoken-text properties, why) for page n of two open pikepdf files; why is set on a misfit."""
    try:
        da, pa = drawing(a_pdf.pages[n - 1]); db, pb = drawing(b_pdf.pages[n - 1])
    except Unreadable as e: return False, False, str(e)
    return da == db, pa == pb, None
