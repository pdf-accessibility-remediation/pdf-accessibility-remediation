"""langjoin.py: how the language step's finder reads a page's words across marked-content runs (#150, #161). Local only.

    langjoin.Structure(pdf)                        the tag tree's facts the joins need (a pikepdf.Pdf, or None)
    langjoin.reading(pno, chars, struct, rules)    -> Reading, or None when the page is read as its runs (today's reading)
    Reading.map(place)                              -> the place on the PDF's own runs (with `segments` when it spans several)

The finder (lib/langcands.book) reads a page as a list of *stretches*: by default each marked-content run is one, as
before. A Reading gives the finder copies of the page's characters, each stretch labelled with a pseudo MCID, and maps
every place the finder makes back to the PDF's own runs and character counts. Character indexes in the PDF never move:
a place's segments are [mcid, first, last] on the real runs, so a space drawn between two pieces stays inside the place.

The rules (`rules`, a set; lib/langcands.RULES):
  join   (#150) OCR-pattern pages (median words per text run at most 1.5: what OpenDataLoader and OCR layers write): runs
         are joined, never split, into stretches. Between two runs a stretch ends at a new line, a change of parent
         element, a gap over GAP x the page's median word gap, a word ending in , ; : . ? !, the first word of a line
         after a line ending in a hyphen (#140's check keeps its half), an opening quote or bracket (not one inside a
         word, nor one before a word of Hawaiian shape: an ʻokina), a note mark in its own run, and a run the tag tree
         keeps apart (not next to the last in its parent's /K, or under spoken text). Inside a word drawn across runs,
         the pieces stay one word when the piece beside the change holds one letter (cut at a dash, slash or quote) or
         when the letters joined are English and a piece is not; otherwise the change is a word break. Pieces with a
         space drawn over the next letter ("prob lems") are one word when English joined. The one-letter join: a single
         letter set apart from its word by under FRAG_GAP em (or a drop cap) is joined back (h4 round 14, reviews 22–26).
  inrun  (#161 A) on other pages, the one-letter join inside one run (a gap or a space character between a first letter
         and the rest). An ordinary place: no executor change.
  cross  (#161 B) on other pages, a word cut across two runs (a letter in its own run; or the reader kept it whole) is
         read with #150's word checks across runs: a note mark or a , ; : . ? ! before the change is a word break; else
         rule 1, then the one-letter join. A word that passes is read whole. It is placed (its two runs one stretch) only
         when the tag tree allows one tag over it: same parent, next to each other in /K, no spoken text in the way, one
         line. A drop cap is read whole and never placed (Patrick, 2026-11-19). A word read whole but not placed is
         returned in Reading.unplaced when its whole spelling is a candidate (#161 addition 3).
"""
import re, statistics, collections, unicodedata
import pikepdf
from lib import ocrwords

GAP, FRAG_GAP = 2.0, 0.15
OPEN = set('‘“"([{«„‚\'')
ENDS = set(',;:')
STOPS = set('.?!')
HYPH = set('-‐‑­')
PSEUDO = 1_000_000                      # pseudo MCIDs of stretches start here (real MCIDs are far smaller)


def is_letter(ch): return ch.isalpha() or unicodedata.category(ch) in ('Mn', 'Mc')


# ---------------------------------------------------------------- the tag tree's facts
_DO = re.compile(rb'/([^\s/\[\]<>(){}%]+)\s+Do\b')
_SINGLE = {}
def single_use_forms(pdf):
    """{page: [form XObject]}: the forms holding marked content that the page's own content draws, each drawn once in the
    whole document (from a page or another form). Their runs are tagged the way the page's are (#165); the marks of a form
    drawn in several places are read as before: not at all (apply.py refuses its runs). Counted once per PDF."""
    if id(pdf) in _SINGLE: return _SINGLE[id(pdf)]
    def xforms(res): return {str(k): v for k, v in ((res or {}).get('/XObject') or {}).items() if isinstance(v, pikepdf.Stream) and str(v.get('/Subtype')) == '/Form'}
    def raw(c):
        try: return b'' if c is None else b'\n'.join(x.read_bytes() for x in (c if isinstance(c, pikepdf.Array) else [c]))
        except Exception: return b''
    def res_of(page):
        n_ = page.obj
        for _ in range(30):
            if n_ is None: return {}
            if '/Resources' in n_: return n_.Resources
            n_ = n_.get('/Parent')
        return {}
    uses, direct = collections.Counter(), {}
    def walk(b, res, depth, pno):
        xs = xforms(res)
        for nm in _DO.findall(b):
            x = xs.get('/' + nm.decode('latin-1'))
            if x is None: continue
            uses[x.objgen] += 1
            if depth == 0: direct.setdefault(pno, {})[x.objgen] = x
            if depth < 4: walk(raw(x), x.get('/Resources') or res, depth + 1, pno)
    for pno, page in enumerate(pdf.pages, 1):
        walk(raw(page.obj.get('/Contents')), res_of(page), 0, pno)
    out = {}
    for pno, fs in direct.items():
        keep = [x for og, x in fs.items() if uses[og] == 1 and b'/MCID' in raw(x)]
        if keep: out[pno] = keep
    _SINGLE.clear(); _SINGLE[id(pdf)] = out
    return out


class Structure:
    """Built once per book by walking the tag tree from the StructTreeRoot (as apply.py indexes it: an MCID's owner is the
    element whose /K holds it, its page the element's /Pg or an MCR's own), never from the ParentTree alone: some
    auto-tagged PDFs have a tag tree but pages with no /StructParents. Each page's content marks are read when first
    asked. status: 'ok', 'unreadable' (no tag tree, or it could not be read) or 'not given' (no PDF)."""
    def __init__(self, pdf):
        self.pdf, self.par, self.status = pdf, {}, 'not given'
        self._kids, self._marks = {}, {}
        if pdf is None: return
        try:
            st = pdf.Root.get('/StructTreeRoot')
            if st is None or '/K' not in st: self.status = 'unreadable'; return
            pidx = {p.obj.objgen: i for i, p in enumerate(pdf.pages, 1)}
            seen, stm = set(), {}
            def key(el): return el.objgen if el.objgen != (0, 0) else ('direct', id(el))
            stack = [(k, None) for k in (list(st.K) if isinstance(st.K, pikepdf.Array) else [st.K])]
            while stack:
                el, pg = stack.pop()
                if not isinstance(el, pikepdf.Dictionary) or str(el.get('/Type', '')) in ('/MCR', '/OBJR'): continue
                k_ = key(el)
                if k_ in seen: continue
                seen.add(k_)
                if '/Pg' in el: pg = pidx.get(el.Pg.objgen, pg)
                k = el.get('/K')
                seq = []
                for kid in (list(k) if isinstance(k, pikepdf.Array) else ([k] if k is not None else [])):
                    if isinstance(kid, int):
                        seq.append(('mcid', pg, int(kid)))
                        if pg is not None: self.par.setdefault((pg, int(kid)), k_)
                    elif isinstance(kid, pikepdf.Dictionary):
                        t = str(kid.get('/Type', ''))
                        if t == '/MCR':
                            kp = pidx.get(kid.Pg.objgen) if '/Pg' in kid else pg
                            seq.append(('mcid', kp, int(kid.MCID)))
                            if kp is not None:
                                # numbered inside a form XObject (/Stm): pdfplumber lists its characters under that number
                                # on the page; kept apart, and used only where the page's own content has no such MCID
                                (stm if '/Stm' in kid else self.par).setdefault((kp, int(kid.MCID)), k_)
                        elif t == '/OBJR': seq.append(('objr',))
                        else: seq.append(('elem',)); stack.append((kid, pg))
                    else: seq.append(('other',))
                self._kids[k_] = (seq, '/ActualText' in el, {(s[1], s[2]): i for i, s in enumerate(seq) if s[0] == 'mcid'})
            for k_, v in stm.items(): self.par.setdefault(k_, v)
            self.status = 'ok' if self.par else 'unreadable'
        except Exception:
            self.par, self.status = {}, 'unreadable'

    @property
    def ok(self): return self.status == 'ok'

    def parent(self, pno, m): return self.par.get((pno, m))

    def _seq(self, og): return self._kids.get(og, (None, True, {}))

    def marks(self, pno):
        """{mcid: (own ActualText, under an enclosing ActualText)} from the page's content stream, and from the forms it
        draws that are drawn nowhere else (#165: their runs are tagged like the page's, so spoken text there counts too)."""
        if pno not in self._marks:
            out = {}
            try:
                page = self.pdf.pages[pno - 1]
                srcs = [(page, page.obj.get('/Resources', {}).get('/Properties', {}) or {})]
                srcs += [(f, (f.get('/Resources') or {}).get('/Properties', {}) or {}) for f in single_use_forms(self.pdf).get(pno, [])]
                for obj, props in srcs:
                    if obj is page:
                        c_ = page.obj.get('/Contents')
                        raw = b''.join(x.read_bytes() for x in (list(c_) if isinstance(c_, pikepdf.Array) else [c_]) if x is not None)
                    else: raw = obj.read_bytes()
                    if b'ActualText' not in raw and not any(isinstance(v, pikepdf.Dictionary) and '/ActualText' in v for v in props.values()):
                        continue                    # no spoken text in these marks: no need to parse the content (speed)
                    stack = []
                    for x in pikepdf.parse_content_stream(obj, 'BDC BMC EMC'):
                        op = str(x.operator)
                        if op == 'BMC': stack.append(False); continue
                        if op == 'EMC':
                            if stack: stack.pop()
                            continue
                        pr = x.operands[1] if len(x.operands) > 1 else None
                        if isinstance(pr, pikepdf.Name): pr = props.get(pr)
                        own = isinstance(pr, pikepdf.Dictionary) and '/ActualText' in pr
                        if isinstance(pr, pikepdf.Dictionary) and '/MCID' in pr: out.setdefault(int(pr.MCID), (own, any(stack)))
                        stack.append(own)
            except Exception:
                out = None
            self._marks[pno] = out
        return self._marks[pno]

    def why_apart(self, pno, ma, mb, run_text):
        """None when one tag may cover runs ma and mb (in that order) on page pno, else the reason: parent, not_adjacent,
        actualtext. run_text: {mcid: text} of the page, so blank runs between may be skipped."""
        if not self.ok: return 'parent'
        pa, pb = self.par.get((pno, ma)), self.par.get((pno, mb))
        if pa is None or pa != pb: return 'parent'
        seq, el_at, where = self._seq(pa)
        if seq is None: return 'not_adjacent'
        ia, ib = where.get((pno, ma)), where.get((pno, mb))
        if ia is None or ib is None or ib < ia: return 'not_adjacent'
        for s in seq[ia + 1:ib]:
            if s[0] != 'mcid' or s[1] != pno or (run_text.get(s[2]) or '').strip(): return 'not_adjacent'
        if el_at: return 'actualtext'
        mk = self.marks(pno)
        if mk is None: return 'actualtext'
        for m in (ma, mb):
            o, e = mk.get(m, (False, False))
            if o or e: return 'actualtext'
        return None


# ---------------------------------------------------------------- page helpers (h4.py, round 14)
def lines_of(cs):
    out, m, prev = [], 0, None
    for c in cs:
        if prev is not None and abs((c['top'] or 0) - (prev['top'] or 0)) > 0.5 * max(prev.get('size') or 0, 1): m += 1
        out.append(m); prev = c
    return out

def ocr_pattern(cs):
    per = collections.defaultdict(str)
    for c in cs:
        if c.get('mcid') is not None: per[c['mcid']] += c['text'] or ''
    wpr = [len(t.split()) for t in per.values() if t.strip()]
    return bool(wpr) and statistics.median(wpr) <= 1.5

def notes_of(cs, ln):
    med = collections.defaultdict(list); base = collections.defaultdict(list)
    for c, l in zip(cs, ln):
        if (c['text'] or '').isalpha(): med[l].append(c.get('size') or 0); base[l].append(c['bottom'] or 0)
    out = set()
    for k, (c, l) in enumerate(zip(cs, ln)):
        if c.get('mcid') is None or not med[l]: continue
        ms, mb = statistics.median(med[l]), statistics.median(base[l])
        t = c['text'] or ' '
        if not t.isalpha() and t.strip() and ((c.get('size') or 0) < 0.8 * ms or (c['bottom'] or 0) < mb - 0.25 * ms): out.add(k)
    return out

def letters(ws): return ''.join(ch for w in ws for c in w for ch in c['text'] if ch.isalpha())

def haw_rest(t):
    """The word after an opening quote read as Hawaiian: marks folded, punctuation around it stripped; a lone vowel counts."""
    t = ''.join(ch for ch in unicodedata.normalize('NFD', t.lower()) if not unicodedata.combining(ch))
    t = t.strip('.,;:!?)]}"”’\'')
    return ocrwords.hawaiian_shape(t) or (len(t) == 1 and t in 'aeiou')

def quote_kept(a, b, g):
    """No break at an opening quote drawn with no gap before it (inside a word), or before a word of Hawaiian shape."""
    if g <= FRAG_GAP * max(b[0].get('size') or 0, 1): return True
    return len(b) > 1 and haw_rest(''.join(x['text'] for x in b[1:]))

def _cut(c):
    from lib import langcands
    return c['text'] in langcands.CUT

def _tail(w):
    t = []
    for c in w: t = [] if _cut(c) else t + [c]
    return t

def _head(w):
    t = []
    for c in w:
        if _cut(c): break
        t.append(c)
    return t

def _nlet(cs_): return sum(1 for c in cs_ for ch in c['text'] if is_letter(ch))
def _lets(cs_): return ''.join(ch for c in cs_ for ch in c['text'] if ch.isalpha())


def one_letter(cs, ln, words, pos, drop, joins, allow):
    """The one-letter join (h4 round 14, review 24 M6): letters the word reader set apart, joined back. allow(a_char,
    b_char, kind) says whether a link between two words may join (the page's rules: in-run only, cross-run only, or
    both). Joined links are returned in `joins` as (first char of the second word, kind); spaces between go to `drop`."""
    from lib import langcands
    def lone_vowel(cs_): return _nlet(cs_) == 1 and unicodedata.normalize('NFD', _lets(cs_).lower())[:1] in tuple('aeiouy')
    def lets_h(cs_): return ''.join(ch for c in cs_ for ch in c['text'] if ch.isalpha() or ch in '-‐‑')
    def a_word(cs_): return any(len(t) >= 2 and (langcands.in_english(t) or haw_rest(t)) for t in re.split(r'[-‐‑]', lets_h(cs_)))
    def geom(a, b):
        ka, kb = pos[id(a[-1])], pos[id(b[0])]
        if any(not cs[k]['text'].isspace() for k in range(ka + 1, kb)) or not b[0]['text'][:1].isalpha(): return None
        ta, hb = _tail(a), _head(b)
        if not _nlet(ta) or not _nlet(hb) or not (_nlet(ta) == 1 or _nlet(hb) == 1): return None
        L1, B0 = ta[-1], b[0]
        if _nlet(ta) == 1 and (L1.get('size') or 0) >= 2 * (B0.get('size') or 1) and (L1['top'] or 0) - 1 <= (B0['top'] or 0) <= (L1['bottom'] or 0) \
                and B0['x0'] - L1['x1'] <= 0.5 * max(B0.get('size') or 0, 1): kind = 'drop cap'
        elif not (ln[ka] == ln[kb] and (B0['x0'] - L1['x1']) <= FRAG_GAP * max(B0.get('size') or 0, 1)): return None
        else: kind = 'close'
        return kind if allow(a[-1], b[0], kind) else None
    g = [geom(a, b) for a, b in zip(words, words[1:])]
    one = [_nlet(w) == 1 for w in words]
    spaced = [False] * len(words)
    x = 0
    while x < len(words):
        y = x
        while y < len(words) - 1 and one[y] and one[y + 1] and g[y] == 'close': y += 1
        if y - x >= 2:
            for z in range(x, y + 1): spaced[z] = True
        x = max(y, x + 1)
    def link(n):
        k = g[n]
        if not k or k == 'drop cap' or spaced[n] or spaced[n + 1]: return k
        ta, hb = _tail(words[n]), _head(words[n + 1])
        if lone_vowel(ta) and lone_vowel(hb): return None
        if lone_vowel(ta) and a_word(hb): return None
        if lone_vowel(hb) and a_word(ta): return None
        if _nlet(hb) == 1 and _nlet(ta) > 1 and not langcands.in_english(_lets(ta) + _lets(hb)): return None
        if _nlet(ta) == 1 and _nlet(hb) == 1 and not langcands.in_english(_lets(ta) + _lets(hb)): return None
        return k
    i = 0
    while i < len(words) - 1:
        j, kinds = i, []
        while j < len(words) - 1:
            k = link(j)
            if not k: break
            kinds.append(k); j += 1
        if j == i: i += 1; continue
        chain = words[i:j + 1]
        for a, b, k in zip(chain, chain[1:], kinds):
            drop.update(range(pos[id(a[-1])] + 1, pos[id(b[0])]))
            b[0]['_join'] = True                 # the word reader keeps no break before it (gaptext.breaks, ocrwords.words)
            joins.append((b[0], k, a[-1]))
        i = j


# ---------------------------------------------------------------- one page's reading
class Reading:
    """A page read in stretches. chars: copies of the page's characters (pseudo MCIDs, `_m` the real MCID, `_k` the index
    in the real run, `_syn` for a space put in at a word break). unplaced: words read whole across runs that no tag can
    cover, whose whole spelling the finder will classify (langcands keeps those that are candidates)."""
    def __init__(self, pno, chars, real_runs, kind):
        self.pno, self.chars, self.real_runs, self.kind = pno, chars, real_runs, kind
        self.runs = collections.defaultdict(list)
        for c in chars:
            if c.get('mcid') is not None: self.runs[c['mcid']].append(c)
        self.stretch_of = {}                    # pseudo MCID -> 'join' (OCR page, several runs), 'cross' (#161 B) or None
        self.unplaced_keys = {}                 # id(first char of the word) -> reason
        self.words = None

    def map(self, p):
        """A place on the stretch -> the same place on the PDF's runs: (mcid, first, last) for one run, or with
        `segments` [[mcid, first, last], …] in reading order. None when a run would appear twice (not in order)."""
        cs = self.runs.get(p['mcid'])
        if cs is None: return p
        real = [c for c in cs[p['first']:p['last'] + 1] if not c.get('_syn')]
        if not real: return None
        segs = []
        for c in real:
            if segs and segs[-1][0] == c['_m']: segs[-1][2] = c['_k']
            else: segs.append([c['_m'], c['_k'], c['_k']])
        if len({s[0] for s in segs}) != len(segs): return None
        q = dict(p)
        m, f, l = segs[0]
        rr = self.real_runs.get(m) or []
        q.update(mcid=m, first=f, last=l, n=len(rr))
        if len(segs) == 1:
            q['text'] = ''.join(c['text'] for c in rr[f:l + 1])
            q['whole'] = not re.search(r'[^\W_]', ''.join(c['text'] for k, c in enumerate(rr) if k < f or k > l))
        else:
            q['segments'] = segs
            q['text'] = ''.join(c['text'] for s in segs for c in (self.real_runs.get(s[0]) or [])[s[1]:s[2] + 1])
            q['whole'] = False
        src = set(q.get('source') or [])
        st = self.stretch_of.get(p['mcid'])
        if st and len(segs) > 1: src.add(st)
        if any(c.get('_join') and c.get('_jin') for c in real): src.add('inrun')
        if any(c.get('_join') and not c.get('_jin') for c in real) and self.kind == 'ocr': src.add('join')
        if src: q['source'] = sorted(src)
        return q


def reading(pno, chars, struct, rules):
    """None when the page is read as its runs (no rule applies). Otherwise a Reading."""
    if not chars or not rules: return None
    real_runs = collections.defaultdict(list)
    copies = []
    for c in chars:
        m = c.get('mcid')
        k = None
        if m is not None: k = len(real_runs[m]); real_runs[m].append(c)
        copies.append(dict(c, _m=m, _k=k))
    ocr = ocr_pattern(copies)
    if ocr:
        if 'join' not in rules: return None
        return _ocr_page(pno, copies, real_runs, struct)
    if not ({'inrun', 'cross'} & set(rules)): return None
    return _other_page(pno, copies, real_runs, struct, rules)


def _words(cs):
    return list(ocrwords.words(cs, lambda _p, _c=cs: _c))


def _rule1(words, pos, put_space, notes=None, strict=False):
    """A word drawn across runs: kept whole when the piece beside the change holds one letter (cut at a dash, slash or
    quote), or its letters joined are English and a piece is not; else a word break before the next piece with letters.
    strict (#161 B): a note mark after the change, or , ; : . ? ! before it, is always a word break."""
    from lib import langcands
    for w in words:
        pieces, cur = [], [w[0]]
        for c in w[1:]:
            if c.get('_m') != cur[-1].get('_m'): pieces.append(cur); cur = [c]
            else: cur.append(c)
        pieces.append(cur)
        if len(pieces) == 1: continue
        lets = [''.join(ch for c in pc for ch in c['text'] if ch.isalpha()) for pc in pieces]
        english = langcands.in_english(''.join(lets)) and not all(langcands.in_english(x) for x in lets if x)
        lp = [i for i, x in enumerate(lets) if x]
        if strict:
            for i in range(1, len(pieces)):
                a, b = pieces[i - 1], pieces[i]
                if (notes is not None and pos[id(b[0])] in notes) or a[-1]['text'] in ENDS | STOPS or b[0]['text'] in ENDS | STOPS:
                    put_space.add(pos[id(b[0])])
        for i0, i1 in zip(lp, lp[1:]):
            a, b = pieces[i0], pieces[i1]
            ta, hb = [], []
            for c in a: ta = [] if _cut(c) else ta + [c]
            for c in b:
                if _cut(c): break
                hb.append(c)
            single = any(_nlet(pc) == 1 for pc in (ta, hb))
            if single or english: continue
            put_space.add(pos[id(b[0])])


def _glue(cs, ln, words, pos, drop, cross_only=False):
    """Pieces of one word with a space drawn over the next letter ("prob lems"): one word when English joined."""
    from lib import langcands
    i = 0
    while i < len(words) - 1:
        glued = False
        for n in (3, 2):
            grp = words[i:i + n]
            if len(grp) < n or len({ln[pos[id(w[0])]] for w in grp}) > 1: continue
            ok = True
            for a, b in zip(grp, grp[1:]):
                ka, kb = pos[id(a[-1])], pos[id(b[0])]
                if not (a[-1]['text'].isalpha() and b[0]['text'].isalpha()) or kb == ka + 1: ok = False; break
                if any(not cs[k]['text'].isspace() for k in range(ka + 1, kb)): ok = False; break
                if (b[0]['x0'] - a[-1]['x1']) > FRAG_GAP * max(a[-1].get('size') or 0, 1): ok = False; break
                if cross_only and a[-1].get('_m') == b[0].get('_m'): ok = False; break
            if not ok: continue
            parts = [letters([w]) for w in grp]
            if min(len(x) for x in parts) < 2: continue
            if langcands.in_english(''.join(parts)) and not all(langcands.in_english(x) for x in parts):
                for a, b in zip(grp, grp[1:]):
                    drop.update(range(pos[id(a[-1])] + 1, pos[id(b[0])])); b[0]['_join'] = True
                i += n; glued = True; break
        if not glued: i += 1


def _rebuild(cs, ln, notes, drop, put_space):
    out, oln, onote = [], [], []
    for k, c in enumerate(cs):
        if k in drop: continue
        if k in put_space:
            out.append(dict(c, text=' ', x1=c['x0'], _syn=True, _join=False)); oln.append(ln[k]); onote.append(False)
        out.append(c); oln.append(ln[k]); onote.append(k in notes)
    return out, oln, onote


def _ocr_page(pno, cs, real_runs, struct):
    ln = lines_of(cs); notes = notes_of(cs, ln)
    pos = {id(c): k for k, c in enumerate(cs)}
    words = _words(cs)
    put_space, drop = set(), set()
    _rule1(words, pos, put_space)
    _glue(cs, ln, words, pos, drop)
    joins = []
    one_letter(cs, ln, words, pos, drop, joins, lambda a, b, kind: True)
    cs, ln, onote = _rebuild(cs, ln, notes, drop, put_space)
    pos = {id(c): k for k, c in enumerate(cs)}
    words = _words(cs)
    gaps_page = []
    for a, b in zip(words, words[1:]):
        if ln[pos[id(a[-1])]] == ln[pos[id(b[0])]]:
            g = b[0]['x0'] - a[-1]['x1']
            if g >= 0: gaps_page.append(g)
    med = statistics.median(gaps_page) if gaps_page else None
    first_of = {pos[id(w[0])]: w for w in words}
    last_before = {}
    for a, b in zip(words, words[1:]): last_before[pos[id(b[0])]] = a
    hy_half = set()
    for a, b in zip(words, words[1:]):
        if ln[pos[id(a[-1])]] != ln[pos[id(b[0])]] and a[-1]['text'] in HYPH: hy_half.add(id(b[0]))
    run_text = {m: ''.join(c['text'] for c in rr) for m, rr in real_runs.items()}
    R = Reading(pno, cs, real_runs, 'ocr')
    seg, prev_m, prev_note, members = 0, None, False, collections.defaultdict(set)
    brk_why = {}                            # position -> why the tag tree keeps the runs apart (a word cut there: unplaced)
    for k, c in enumerate(cs):
        m0 = c.get('_m')
        if c.get('mcid') is None: continue
        why = None
        if prev_m is not None and m0 != prev_m:
            if onote[k] or prev_note: why = 'note'
            elif k and ln[k] != ln[k - 1]: why = 'line'
            elif struct is None or not struct.ok or struct.parent(pno, prev_m) != struct.parent(pno, m0): why = 'parent'
            elif k in first_of and k in last_before:
                a, b = last_before[k], first_of[k]
                g = b[0]['x0'] - a[-1]['x1']
                if med is not None and g > GAP * max(med, 0.5): why = 'gap'
                elif a[-1]['text'] in ENDS: why = 'punct'
                elif a[-1]['text'] in STOPS: why = 'stop'
                elif id(a[0]) in hy_half: why = 'hyphen half'
                elif b[0]['text'] in OPEN and not quote_kept(a, b, g): why = 'quote'
            if why is None:
                apart = struct.why_apart(pno, prev_m, m0, run_text)
                if apart: why = 'structure'; brk_why[k] = apart
            elif why == 'parent': brk_why[k] = 'parent'
        if why: seg += 1
        c['mcid'] = PSEUDO + seg
        if m0 is not None: members[PSEUDO + seg].add(m0)
        if m0 is not None and not c['text'].isspace(): prev_m = m0
        prev_note = onote[k]
    R.runs = collections.defaultdict(list)
    for c in cs:
        if c.get('mcid') is not None: R.runs[c['mcid']].append(c)
    R.stretch_of = {s: 'join' for s, ms in members.items() if len(ms) > 1}
    R.words = words                         # the finder reads these words again otherwise (the same characters)
    for w in words:                         # a word the tag tree cuts (runs under different elements, or out of order): read whole, unplaced
        why = next((brk_why[pos[id(c)]] for i_, c in enumerate(w[1:], 1) if pos[id(c)] in brk_why
                    and w[i_ - 1]['text'] not in ENDS | STOPS and w[i_]['text'] not in ENDS | STOPS), None)   # never a list label glued on ("a" + ".Labials")
        if why:
            for c in w: R.unplaced_keys[id(c)] = why
    return R


def _other_page(pno, cs, real_runs, struct, rules):
    """#161 on a page that isn't an OCR-pattern page: in-run one-letter joins (A) and words across two runs (B)."""
    ln = lines_of(cs); notes = notes_of(cs, ln)
    pos = {id(c): k for k, c in enumerate(cs)}
    words = _words(cs)
    put_space, drop = set(), set()
    cross = 'cross' in rules
    if cross: _rule1(words, pos, put_space, notes, strict=True)
    _glue(cs, ln, words, pos, drop, cross_only='inrun' not in rules)     # "prob lems": English joined (within a run only with inrun)
    joins = []
    from lib import langcands
    last_of = {id(w[-1]): i for i, w in enumerate(words)}
    def touching(i):                        # words i and i + 1 drawn with no real gap (a space drawn over the next letter)
        a, b = words[i], words[i + 1]
        return ln[pos[id(a[-1])]] == ln[pos[id(b[0])]] and (b[0]['x0'] - a[-1]['x1']) <= FRAG_GAP * max(b[0].get('size') or 0, 1)
    def piece_of_english(i):
        """Words i and i + 1 joined are not English, but with the words touching them they are ("geo graph i cal": "i" and
        "cal" are pieces of "geographical", never a word "ical"): such a letter is not joined."""
        if langcands.in_english(letters(words[i:i + 2])): return False
        for lo in range(i, max(-1, i - 4), -1):
            if lo < i and not touching(lo): break
            for hi in range(i + 1, min(len(words), i + 5)):
                if hi > i + 1 and not touching(hi - 1): break
                if (lo, hi) != (i, i + 1) and len(letters(words[lo:hi + 1])) >= 4 and langcands.in_english(letters(words[lo:hi + 1])): return True
        return False
    def allow(a, b, kind):
        same = a.get('_m') == b.get('_m')
        if not ((('inrun' in rules) if same else (cross and pos[id(b)] not in notes))): return False
        if kind != 'drop cap' and a['text'] in ENDS | STOPS: return False   # "L. Camacho", "v. Asian", "C., and": a word end (review 06, M2)
        i = last_of.get(id(a))
        return kind == 'drop cap' or i is None or i + 1 >= len(words) or not piece_of_english(i)
    one_letter(cs, ln, words, pos, drop, joins, allow)
    # on these pages the spaces between joined pieces stay where they are (soft: the word reader reads through them):
    # taking them out changes the line's typical gap, and the reader then splits other words ("geo graph ical")
    for k in drop: cs[k]['_soft'] = True
    soft = bool(drop); drop = set()
    crossing = cross and any(len({c.get('_m') for c in w if c.get('_m') is not None}) > 1 for w in words)
    if not joins and not soft and not put_space and not crossing: return None
    for b, kind, a in joins:
        if a.get('_m') == b.get('_m'): b['_jin'] = True
        elif kind == 'drop cap': b['_drop'] = True
    if cross:                               # a word the reader kept whole across runs that is itself a piece of an English word
        for i, w in enumerate(words):        # drawn with touching neighbours ("po" "l|iti" "cal"): a word break at the run change
            if len({c.get('_m') for c in w if c.get('_m') is not None}) < 2 or langcands.in_english(letters([w])): continue
            spans = []
            if i > 0 and touching(i - 1): spans += [(i - 1, i)] + ([(i - 2, i)] if i > 1 and touching(i - 2) else [])
            if i + 1 < len(words) and touching(i): spans += [(i, i + 1)] + ([(i, i + 2)] if i + 2 < len(words) and touching(i + 1) else [])
            if i > 0 and i + 1 < len(words) and touching(i - 1) and touching(i): spans.append((i - 1, i + 1))
            if any(langcands.in_english(letters(words[lo:hi + 1])) for lo, hi in spans):
                for k_ in range(1, len(w)):
                    if w[k_].get('_m') != w[k_ - 1].get('_m'): put_space.add(pos[id(w[k_])])
    cs, ln, onote = _rebuild(cs, ln, notes, drop, put_space)
    pos = {id(c): k for k, c in enumerate(cs)}
    words = _words(cs)
    run_text = {m: ''.join(c['text'] for c in rr) for m, rr in real_runs.items()}
    # where a word crosses runs: placed (no stretch break) when one tag may cover it, else read whole, unplaced
    keep = set()
    R = Reading(pno, cs, real_runs, 'other')
    for w in words:
        ms = [c.get('_m') for c in w]
        if len(set(m for m in ms if m is not None)) < 2: continue
        why = None
        for i in range(1, len(w)):
            if ms[i] == ms[i - 1] or ms[i] is None or ms[i - 1] is None: continue
            if w[i].get('_drop'): why = 'drop_cap'; break
            if not cross: why = 'cross_off'; break
            why = (struct.why_apart(pno, ms[i - 1], ms[i], run_text) if struct is not None else 'parent') or why
            if why: break
            if abs(ln[pos[id(w[i])]] - ln[pos[id(w[i - 1])]]) > 0: why = 'line'; break
        if why:
            for c in w: R.unplaced_keys[id(c)] = why
        else:
            for i in range(1, len(w)):
                if ms[i] != ms[i - 1]: keep.add(pos[id(w[i])])
    seg, prev_m, members = 0, None, collections.defaultdict(set)
    for k, c in enumerate(cs):
        m0 = c.get('_m')
        if c.get('mcid') is None: continue
        if c.get('_soft'): c['mcid'] = PSEUDO + seg; continue      # inside a joined word: never a stretch break
        if prev_m is not None and m0 != prev_m and k not in keep: seg += 1
        c['mcid'] = PSEUDO + seg
        if m0 is not None: members[PSEUDO + seg].add(m0)
        if m0 is not None and not c['text'].isspace(): prev_m = m0
    R.runs = collections.defaultdict(list)
    for c in cs:
        if c.get('mcid') is not None: R.runs[c['mcid']].append(c)
    R.stretch_of = {s: 'cross' for s, ms in members.items() if len(ms) > 1}
    R.words = words
    return R
