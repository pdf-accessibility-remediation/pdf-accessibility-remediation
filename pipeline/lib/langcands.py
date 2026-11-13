"""langcands.py: words and passages that may be in another language, found locally (no model, no network): the language
step's candidates (#118, language tagging; WCAG 3.1.2).

    langcands.page_places(pno, chars, page_chars=None, italic=None)  -> (places, words) for one page
    langcands.book(PL)                                               -> {'places': [...], 'pages': {...}, 'stats': {...}}
    langcands.in_english(word)                                       -> True when the word is in the English word list

A place is where a tag could go: (page, mcid, first, last), the first and last character index within that marked-content
run, counted over pdfplumber's characters for the MCID in content order (one character per character code; the codes
under a spoken-text span are counted, the span's text is not). The executor finds the place by the same count, never by
reading the text again, so a font's encoding never matters (lib/mcsplit.py). The phrase is kept beside it for people and
for checks.

Classes (a place may have more than one):
  cjk:kana, cjk:hangul, cjk:han_only, cjk:mixed   a stretch of CJK characters (lib/scripts.kind)
  script:<name>                                   Greek, Cyrillic, Arabic, Hebrew, Thai, Devanagari …
  hawaiian    an ʻokina (U+02BB, or a quote mark inside a Hawaiian-shape word), a kahakō in a Hawaiian-shape word, or a
              4+ letter Hawaiian-shape word not in the English list; also every word of a run of 3+ Hawaiian-shape words
              (single vowels between them allowed), one of them not in the English list
  marks       romanization marks (Hepburn, IAST: ā ī ū ē ō ś ṣ ṇ ṭ ḍ ṃ ṛ ḥ ñ …)
  accented    other Latin accents (é è ü ö ç …)
  unknown     4+ letters, lower case, not in the English list
  latin       in a Chinese, Japanese or Korean document only: any Latin-script word of 2+ letters (English, romanization …)
A word whose letters, with marks and the ʻokina folded away, are in the English list is part of English and never a
candidate on its own (lūʻau, ʻukulele, sūtra: Patrick, 2026-11-12); a run of 3+ Hawaiian-shape words still takes it in.
Names are not removed here: deciding what is a name is the AI's job (WCAG exempts Latin-script names only; CJK and other
scripts are never exempt).

Words are split as the OCR-word sheets split them (lib/ocrwords.words: spaces, gaps, new lines), then at dashes, slashes
and quotes, and where the script changes between CJK and Latin. A word broken by a hyphen at a line end is rejoined for the
list check ("oppor-" + "tunities"); when its two halves are in different runs it becomes two places of one form.
Consecutive candidate words in one run form one phrase. A run in which most words are candidates (PASSAGE_SHARE, at least
PASSAGE_MIN words) is one place for the whole run.
"""
import os, re, json, hashlib, unicodedata, collections
from lib import scripts, ocrwords

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDLIST = os.path.join(HERE, 'data', 'english-words.txt')
CONTEXT_WORDS = 15                  # words of context on each side, for the AI (M11: about ±15 words)
PASSAGE_SHARE, PASSAGE_MIN = 0.75, 6      # of the run's words of 2+ letters
HAW_RUN = 3                         # this many Hawaiian-shape words in a row make a phrase without marks

ROMAN = re.compile(r'[āīūēōĀĪŪĒŌṃṁṇṭḍśṣṛṝḷḥṅŚṢṬḌṆṚḤṄǎěǐǒǔ]')
HAW_MARK = re.compile(r'[āēīōūĀĒĪŌŪʻ]')
LATIN = re.compile(r'[A-Za-zÀ-ɏḀ-ỿ]')
ACCENTED = re.compile(r'[À-ÿĀ-ɏḀ-ỿ]')
SCRIPTS = [('greek', r'[Ͱ-Ͽἀ-῿]'), ('cyrillic', r'[Ѐ-ӿ]'), ('hebrew', r'[֐-׿]'), ('arabic', r'[؀-ۿ]'), ('thai', r'[฀-๿]'),
           ('devanagari', r'[ऀ-ॿ]'), ('khmer', r'[ក-៿]'), ('lao', r'[຀-໿]'), ('burmese', r'[က-႟]')]
SCRIPTS = [(n, re.compile(p)) for n, p in SCRIPTS]
CUT = set('—–/“”"…«»„‚()[]{}')
HYPHENS = '-‐‑'
ITALIC = re.compile(r'(?i)ital|oblique|-it$|-it[A-Z]|It$')
NUMERAL = re.compile(r'(?i)[ivxlcdm]+|\d[\d,.]*\w{0,3}')

_LIST = None
def wordlist():
    global _LIST
    if _LIST is None:
        with open(WORDLIST, encoding='utf-8') as f: _LIST = frozenset(w.strip() for w in f if w.strip())
    return _LIST

def list_sha256():
    with open(WORDLIST, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()

def fold(w):
    """Lower case, ligatures split (NFKC), marks and the ʻokina (and its look-alikes) removed: lūʻau → luau."""
    w = unicodedata.normalize('NFKC', w).lower()
    w = ''.join(ch for ch in unicodedata.normalize('NFD', w) if not unicodedata.combining(ch))
    return re.sub(r"[ʻ‘’'`]", '', w) if ocrwords.hawaiian_shape(w) else w.replace('’', "'")

def in_english(word):
    """True when the word, or every part of it between hyphens, is in the English list (marks folded)."""
    L = wordlist(); w = fold(word)
    if w in L or w.replace("'", '') in L: return True
    parts = [p for p in re.split(r"[-‐‑]", w) if p]
    return len(parts) > 1 and all(p in L for p in parts)

def other_script(t):
    return next((n for n, rx in SCRIPTS if rx.search(t)), None)

def classify(core, italic=False):
    """The classes of one Latin or other-script word (CJK is found per stretch, not here). [] when it is no candidate."""
    if not core: return []
    s = other_script(core)
    if s: return [f'script:{s}']
    letters = sum(1 for ch in core if ch.isalpha())
    if not LATIN.search(core) or letters < 2 or NUMERAL.fullmatch(core): return []
    if ocrwords.URL.search(core) or core.lower() in ('http', 'https', 'www', 'doi'): return []
    if in_english(core): return []
    cls = []
    shape = ocrwords.hawaiian_shape(core)
    okina = ocrwords.OKINA in core or ocrwords.okina_lookalike(core)
    if shape and (okina or HAW_MARK.search(core)): cls.append('hawaiian')
    elif ROMAN.search(core): cls.append('marks')
    elif ACCENTED.search(core): cls.append('accented')
    if shape and 'hawaiian' not in cls and letters >= 4 and core[:1].islower(): cls.append('hawaiian')
    if not cls and letters >= 4 and core[:1].islower() and not core.isupper(): cls.append('unknown')
    return cls

def _is_cjk(t): return bool(t) and bool(scripts.CJK.search(t))

def _pieces(word):
    """A word's characters cut at dashes, slashes and quotes, and where CJK meets Latin."""
    cur, prev_cjk = [], None
    for c in word:
        t = c['text']
        if t in CUT:
            if cur: yield cur
            cur, prev_cjk = [], None; continue
        cj = _is_cjk(t)
        if cur and prev_cjk is not None and cj != prev_cjk:
            yield cur; cur = []
        cur.append(c); prev_cjk = cj
    if cur: yield cur

def _core_span(cs):
    """(i0, i1) of the word's core within its characters: punctuation around it trimmed, a possessive 's dropped."""
    i0, i1 = 0, len(cs) - 1
    while i0 <= i1 and not (cs[i0]['text'][:1].isalnum()): i0 += 1
    while i1 >= i0 and not (cs[i1]['text'][-1:].isalnum()): i1 -= 1
    if i1 - i0 >= 2 and cs[i1]['text'] in ('s', 'S') and cs[i1 - 1]['text'] in "’'": i1 -= 2
    return i0, i1

def page_places(pno, chars, page_chars=None, italic=None, doc_lang=None, spoken=None):
    """chars: one page's pdfplumber characters in content order (plpages). Returns (places, words): the page's candidate
    places, and the page's words in reading order (for context: each place names its words by index)."""
    italic = italic or (lambda fn: bool(ITALIC.search((fn or '').split('+')[-1])))
    cjk_doc = scripts.primary(doc_lang) in scripts.CJK_DOC          # a Chinese, Japanese or Korean document
    idx, runs = {}, collections.defaultdict(list)           # id(char) -> (mcid, index in its run); mcid -> chars
    for c in chars:
        m = c.get('mcid')
        if m is None: continue
        idx[id(c)] = (m, len(runs[m])); runs[m].append(c)
    pc = (lambda _p: chars) if page_chars is None else page_chars
    # 1. words, in order; each with its run, its index range and its text
    words = []
    for w0 in ocrwords.words(chars, pc):
        ps = list(_pieces(w0))
        pos = {id(c): k for k, c in enumerate(w0)}
        if not ps: words.append({'chars': [], 'text': '', 'all': ''.join(c['text'] for c in w0), 'mcid': None}); continue
        prev = -1
        for n_, w in enumerate(ps):
            end = pos[id(w[-1])] if n_ < len(ps) - 1 else len(w0) - 1
            shown = ''.join(c['text'] for c in w0[prev + 1:end + 1]); prev = end      # the cut characters stay in the context
            i0, i1 = _core_span(w)
            core = ''.join(c['text'] for c in w[i0:i1 + 1]) if i0 <= i1 else ''
            ms = {idx[id(c)][0] for c in w[i0:i1 + 1]} if core else set()
            words.append({'chars': w[i0:i1 + 1] if core else [], 'text': unicodedata.normalize('NFC', core),
                          'all': shown, 'mcid': next(iter(ms)) if len(ms) == 1 else None})
    # 1b. scanned books (review 02, M5): the text a screen reader speaks, where the OCR text was given a reading. spoken =
    #     {'forms': {OCR form: reading}} (the work order's ocr_words) and/or {'reading': the page's AI reading} (page_readings,
    #     paired word by word as apply.py pairs them). The reading decides the class and the form; the place stays the OCR
    #     characters (the indexes), so the tag lands where apply.py put the reading.
    if spoken:
        forms_ = spoken.get('forms') or {}
        for w in words:
            if w['text'] in forms_: w['spoken'] = unicodedata.normalize('NFC', forms_[w['text']])
        if spoken.get('reading'):
            from lib import pagereads
            text, _ = pagereads.okina_slip(spoken['reading'])
            ai = [c for c in (re.match(r'^\W*(.*?)\W*$', t, re.S).group(1) for t in text.split()) if c]
            idx_ = [k for k, w in enumerate(words) if w['text']]
            changes, _ = pagereads.align([words[k]['text'] for k in idx_], ai)
            for i_, r in changes.items(): words[idx_[i_]]['spoken'] = r
        for w in words:
            if 'spoken' in w:
                w['printed'] = w['text']; w['all'] = w['all'].replace(w['text'], w['spoken'], 1) if w['text'] else w['all']; w['text'] = w['spoken']
    # 2. rejoin a word broken by a hyphen at a line end, for the list check only
    for a, b in zip(words, words[1:]):
        if a['all'][-1:] in HYPHENS and a['chars'] and b['chars'] and abs(a['chars'][-1]['top'] - b['chars'][0]['top']) > 3 \
                and b['text'][:1].islower():
            a['joined'] = b['joined_from'] = a['text'] + b['text']
            a['hy_to'] = b
    # 3. classify Latin and other-script words
    for w in words:
        t = w['text']
        if not t or _is_cjk(t): w['cls'] = []; continue
        if 'joined_from' in w: w['cls'] = []; continue                 # the second half: classified with the first
        form = w.get('joined', t)
        it = all(italic(c.get('fontname')) for c in w['chars'] if c['text'].strip())
        w['italic'] = it; w['cls'] = classify(form, it); w['form'] = form
        if cjk_doc and not w['cls'] and LATIN.search(form) and sum(ch.isalpha() for ch in form) >= 2 and not NUMERAL.fullmatch(form) \
                and not ocrwords.URL.search(form):
            w['cls'] = ['latin']                     # in a CJK document every Latin-script word is in another language (English, …)
        if w['cls'] and 'hy_to' in w:
            b = w['hy_to']; b['cls'] = list(w['cls']); b['form'] = form; b['italic'] = it
    # a run of HAW_RUN or more Hawaiian-shape words of 2+ letters in one run (single vowels between them allowed: "E iho
    # ana o luna"), at least one of them not in the English list ("we make a home" stays English), is Hawaiian
    def hw(w): return bool(w['text']) and w['mcid'] is not None and not _is_cjk(w['text']) and ocrwords.hawaiian_shape(w['text'])
    def hv(w): return bool(w['text']) and w['mcid'] is not None and len(w['text']) == 1 and w['text'].lower() in ocrwords.HAW_VOWELS
    i = 0
    while i < len(words):
        if not hw(words[i]): i += 1; continue
        j = i
        while j + 1 < len(words) and words[j + 1]['mcid'] == words[i]['mcid'] and (hw(words[j + 1]) or hv(words[j + 1])): j += 1
        if j > i and i > 0 and hv(words[i - 1]) and words[i - 1]['mcid'] == words[i]['mcid']: i -= 1
        chain = words[i:j + 1]; real = [w for w in chain if hw(w)]
        if len(real) >= HAW_RUN and any(not in_english(w['text']) for w in real):
            for w in chain:
                if 'hawaiian' not in w['cls']: w['cls'] = w['cls'] + ['hawaiian']; w.setdefault('form', w['text']); w.setdefault('italic', False)
        i = j + 1
    # 4. places: CJK stretches per run, then phrases of candidate words
    places = []
    def place(m, f, l, cls, form, it, wi):
        cs = runs[m]
        text = ''.join(c['text'] for c in cs[f:l + 1])
        rest = ''.join(c['text'] for k, c in enumerate(cs) if k < f or k > l)
        places.append({'page': pno, 'mcid': m, 'first': f, 'last': l, 'n': len(cs), 'text': text, 'form': form,
                       'class': sorted(set(cls)), 'italic': it, 'whole': not re.search(r'[^\W_]', rest),
                       'w0': wi[0], 'w1': wi[1]})
    # word index of each character, for context
    wix = {}
    for k, w in enumerate(words):
        for c in w['chars']: wix[id(c)] = k
    def letter(t): return scripts.kind(t) is not None                  # kana, hangul or a Chinese character
    for m, cs in runs.items():
        k = 0
        while k < len(cs):
            if not letter(cs[k]['text']): k += 1; continue
            j = k
            while j + 1 < len(cs) and (_is_cjk(cs[j + 1]['text']) or (cs[j + 1]['text'].isspace() and j + 2 < len(cs) and _is_cjk(cs[j + 2]['text']))):
                j += 1
            l = j
            while l > k and not letter(cs[l]['text']): l -= 1                    # trailing CJK punctuation stays outside
            text = ''.join(c['text'] for c in cs[k:l + 1])
            kd = scripts.kind(text)
            if cjk_doc and scripts.action(kd, text, doc_lang)[0] == 'inherit': k = j + 1; continue   # the document's own language
            ws = [wix[id(c)] for c in cs[k:l + 1] if id(c) in wix]
            place(m, k, l, [f'cjk:{"mixed" if kd == "mixed_with_latin" else kd}'], re.sub(r'\s+', '', text), False,
                  (min(ws), max(ws)) if ws else (None, None))
            k = j + 1
    k = 0
    while k < len(words):
        w = words[k]
        if not w.get('cls') or w['mcid'] is None: k += 1; continue
        j = k
        while j + 1 < len(words) and words[j + 1].get('cls') and words[j + 1]['mcid'] == w['mcid']:
            j += 1
        grp = words[k:j + 1]
        f = idx[id(grp[0]['chars'][0])][1]; l = idx[id(grp[-1]['chars'][-1])][1]
        form = ' '.join(x.get('form', x['text']) for n_, x in enumerate(grp) if n_ == 0 or 'joined_from' not in x)   # a rejoined half once
        place(w['mcid'], f, l, [c for x in grp for c in x['cls']], form, all(x.get('italic') for x in grp), (k, j))
        k = j + 1
    # 5. passages: a run where most words are candidates becomes one place for the whole run
    by_run = collections.defaultdict(list)
    for k, w in enumerate(words):
        if w['mcid'] is not None and w['text'] and LATIN.search(w['text']) and sum(ch.isalpha() for ch in w['text']) >= 2: by_run[w['mcid']].append(w)
    out = []
    passage = set()
    for m, ws in by_run.items():
        cand = sum(1 for w in ws if w.get('cls'))
        if len(ws) >= PASSAGE_MIN and cand / len(ws) >= PASSAGE_SHARE:
            passage.add(m)
    for p in places:
        if p['mcid'] in passage and not p['class'][0].startswith('cjk:'): continue
        out.append(p)
    for m in sorted(passage):
        cs = runs[m]; ws = by_run[m]
        f = idx[id(ws[0]['chars'][0])][1]; l = idx[id(ws[-1]['chars'][-1])][1]
        cls = sorted({c for w in ws for c in w.get('cls', [])}) or ['unknown']
        wi = [wix[id(w['chars'][0])] for w in ws if w['chars'] and id(w['chars'][0]) in wix]
        out.append({'page': pno, 'mcid': m, 'first': f, 'last': l, 'n': len(cs), 'text': ''.join(c['text'] for c in cs[f:l + 1]),
                    'form': ' '.join(w.get('form', w['text']) for w in ws), 'class': ['passage'] + cls,
                    'italic': all(w.get('italic') for w in ws if w.get('cls')),
                    'whole': not re.search(r'[^\W_]', ''.join(c['text'] for k_, c in enumerate(cs) if k_ < f or k_ > l)),
                    'w0': min(wi) if wi else None, 'w1': max(wi) if wi else None})
    out.sort(key=lambda p: (p['mcid'], p['first']))
    return out, [w['all'] for w in words]

def book(PL, pages=None, doc_lang=None, spoken=None):
    """Every page's places, the page word lists (for context), and counts. PL: plpages.Pages. doc_lang: the document's
    language (its /Lang, or the work order's): in a Chinese, Japanese or Korean document, Latin-script words are
    candidates ('latin') and CJK text in the document's own language is not. spoken: {'forms': {OCR form: reading},
    'pages': {page: reading}} for a scanned book's readings (M5), else None."""
    allp, words, C = [], {}, collections.Counter()
    for pno, pg in enumerate(PL.pages, 1):
        if pages and pno not in pages: continue
        pls, ws = page_places(pno, pg.chars, lambda p, _c=pg.chars: _c, doc_lang=doc_lang,
                              spoken={'forms': (spoken or {}).get('forms') or {}, 'reading': ((spoken or {}).get('pages') or {}).get(pno)} if spoken else None)
        allp += pls; words[str(pno)] = ws
    forms = collections.defaultdict(set)
    for p in allp:
        for c in p['class']:
            C[c] += 1; C[f'{c}:{"whole" if p["whole"] else "split"}'] += 1; forms[c].add(p['form'])
    fp = hashlib.sha256(json.dumps(sorted((p['form'], p['class']) for p in allp), ensure_ascii=False).encode()).hexdigest()[:16]
    return {'version': 1, 'document_lang': doc_lang or '', 'wordlist_sha256': list_sha256()[:16], 'fingerprint': fp, 'places': allp, 'words': words,
            'stats': {'places': len(allp), 'by_class': dict(sorted(C.items())),
                      'forms': {k: len(v) for k, v in sorted(forms.items())}}}

def existing(pdf, PL, doc_lang, limit=300):
    """Language tags already in the PDF (a publisher's), on text not in the document's language: one place per run, its
    whole text, with `current` the value as written (fr-FR on an English copyright page, "Hawaiian", JA on Chinese). From
    the marks' /Lang in each page's content and from the /Lang of tag-tree elements over their own runs. pdf: pikepdf."""
    import pikepdf
    doc = scripts.primary(doc_lang)
    runs = collections.defaultdict(dict)
    for pno, pg in enumerate(PL.pages, 1):
        for c in pg.chars:
            if c.get('mcid') is not None: runs[pno].setdefault(c['mcid'], []).append(c['text'])
    found = {}
    pidx = {p.obj.objgen: i for i, p in enumerate(pdf.pages, 1)}
    for pno, page in enumerate(pdf.pages, 1):
        try:
            for x in pikepdf.parse_content_stream(page, 'BDC'):
                pr = x.operands[1] if len(x.operands) > 1 else None
                if isinstance(pr, pikepdf.Dictionary) and '/MCID' in pr and '/Lang' in pr and scripts.primary(str(pr.Lang)) != doc:
                    found[(pno, int(pr.MCID))] = str(pr.Lang)
        except Exception: pass
    st = pdf.Root.get('/StructTreeRoot')
    stack = [(k, None) for k in (st.get('/K') if isinstance(st.get('/K'), pikepdf.Array) else [st.get('/K')])] if st is not None else []
    seen = set()
    while stack and len(seen) < 200000:
        n, pg = stack.pop()
        if not isinstance(n, pikepdf.Dictionary) or n.objgen in seen: continue
        seen.add(n.objgen)
        pg = pidx.get(n.Pg.objgen) if '/Pg' in n else pg
        lang = str(n.get('/Lang', '')) if '/Lang' in n else None
        k = n.get('/K'); ks = list(k) if isinstance(k, pikepdf.Array) else ([k] if k is not None else [])
        for kid in ks:
            if isinstance(kid, int):
                if lang and scripts.primary(lang) != doc and pg: found.setdefault((pg, kid), lang)
            elif isinstance(kid, pikepdf.Dictionary):
                if str(kid.get('/Type')) == '/MCR' and '/Stm' not in kid:
                    p_ = pidx.get(kid.Pg.objgen) if '/Pg' in kid else pg
                    if lang and scripts.primary(lang) != doc and p_: found.setdefault((p_, int(kid.MCID)), lang)
                else: stack.append((kid, pg))
    out = []
    for (pno, m), cur in sorted(found.items()):
        cs = runs.get(pno, {}).get(m)
        if not cs or not ''.join(cs).strip(): continue
        out.append({'page': pno, 'mcid': m, 'first': 0, 'last': len(cs) - 1, 'n': len(cs), 'text': ''.join(cs), 'form': ''.join(cs).strip(),
                    'class': ['existing'], 'current': cur, 'italic': False, 'whole': True, 'w0': None, 'w1': None})
        if len(out) >= limit: break
    return out
