"""dict_measure.py: #141 (Language step: test downloaded dictionaries for deciding word forms locally). A measurement only:
nothing here changes the pipeline. It runs the sponsors' workflow ("Latin Language & Species Name Vocabularies for ADA
In-Text Tagging": species pass, Latin phrase pass, Latin word pass, stoplist, review sheet) and the other languages over
the candidate word forms the language step would send, and compares every local decision with the AI's answers and the
scored test set (proposal 03 §6).

    python3 tools/dict_measure.py build DICT_DIR [source …] word lists from each download, into DICT_DIR/<source>/_lists/
    python3 tools/dict_measure.py run DICT_DIR OUT_DIR      the workflow over the test books, the comparisons, the sheets

DICT_DIR holds one folder per source, as downloaded (never committed): lila/ (lemmaBank.ttl), whitaker/ (the repository's
data files), kaikki/ (<Language>.jsonl), omw/ (omw-1.4), wikidata/ (latest-lexemes.json.bz2), gbif/ (backbone.zip),
gnfinder/ (bin/gnfinder, nonet.sb: run offline only, under a network-denying sandbox, never with verification) and
latincy/ (its own .venv with spaCy and la_core_web_lg). Every list is read with plain Python (no code from a download is
imported); GNfinder and LatinCy run as separate processes.

The pure functions (normalizing, Whitaker's stem-and-ending match, the span and short-word rules, the phrase pass, the
GBIF pair match, filling the review sheet) are tested in tests/test_dict_measure.py on made-up data.
"""
import os, re, sys, csv, json, time, bz2, zipfile, tarfile, unicodedata, collections, subprocess

# ---------------------------------------------------------------- the sponsors' rules (their document's "Ambiguous words")
SHORT_SHARED = {'a', 'in', 'via', 'per', 'plus', 'sub', 'ex', 'ad', 'non', 'de'}   # never decided alone
PHRASES = ['in vitro', 'in vivo', 'in situ', 'a priori', 'a posteriori', 'per se', 'ad hoc', 'magna cum laude',
           'summa cum laude', 'cum laude', 'et cetera', 'inter alia', 'bona fide', 'de facto', 'de jure', 'ad infinitum',
           'ad nauseam', 'ex post facto', 'ex officio', 'in toto', 'in memoriam', 'mutatis mutandis', 'pro forma',
           'quid pro quo', 'sine qua non', 'status quo', 'vice versa', 'terra nullius', 'terra incognita', 'ipso facto',
           'prima facie', 'sui generis', 'per capita', 'per annum', 'post mortem', 'ante bellum', 'non sequitur',
           'alma mater', 'curriculum vitae', 'modus operandi', 'modus vivendi', 'tabula rasa', 'lingua franca',
           'raison d', 'magnum opus', 'deus ex machina', 'persona non grata', 'habeas corpus', 'ad hominem',
           'mea culpa', 'carpe diem', 'nota bene', 'in absentia', 'pro bono', 'in extremis', 'a fortiori']
ABBREVIATIONS = {'et al.': r'\bet al\.', 'ibid.': r'\bibid\.', 'op. cit.': r'\bop\.\s?cit\.', 'cf.': r'\bcf\.',
                 'viz.': r'\bviz\.', 'sic': r'\bsic\b', 'circa': r'\bcirca\b', 'c.': r'(?<![A-Za-z])c\.\s?\d', 'ca.': r'\bca\.\s?\d',
                 'i.e.': r'\bi\.e\.', 'e.g.': r'\be\.g\.', 'etc.': r'\betc\.', 'passim': r'\bpassim\b'}
LANGS_OTHER = ('haw', 'ja-Latn', 'ko-Latn', 'zh-Latn', 'tl', 'ja', 'zh', 'ko')


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.latinlist import latin_norm, whitaker_match  # noqa: E402  one copy, shared with the review page's marks (review 15, L2)


def plain(w):
    """Any other language's form as listed: NFC, lower case, no surrounding punctuation."""
    return unicodedata.normalize('NFC', (w or '').strip().strip('.,;:()[]{}"“”‘’\'').lower())


# ---------------------------------------------------------------- Whitaker's Words: stems and endings by inflection class
def whitaker_parse(dictline_lines, inflect_lines):
    """({(POS, class): {stem}}, {(POS, class): {ending}}) from DICTLINE.GEN (four 19-column stems, then POS and class) and
    INFLECTS.LAT (POS, class, variant, …, ending last). A class key is (POS, declension or conjugation)."""
    stems, ends = collections.defaultdict(set), collections.defaultdict(set)
    for l in dictline_lines:
        if len(l) < 80: continue
        ss = [latin_norm(l[i:i + 19]) for i in (0, 19, 38, 57)]
        f = l[76:].split()
        if not f: continue
        pos = f[0]; cls = f[1] if len(f) > 1 and f[1].isdigit() else '0'
        for s in ss:
            if s and s != 'zzz': stems[(pos, cls)].add(s)
    for l in inflect_lines:
        f = l.split('--')[0].split()
        if len(f) < 4 or not f[1].isdigit(): continue
        pos, cls = {'VPAR': 'V', 'SUPINE': 'V'}.get(f[0], f[0]), f[1]   # participles, gerundives and supines use the verb's stems
        # the stem key and the ending's length are the last two numbers in a row; the ending follows unless its length is 0
        k = max((i for i in range(2, len(f) - 1) if f[i].isdigit() and f[i + 1].isdigit()), default=None)
        if k is None: continue
        end = '' if f[k + 1] == '0' else (f[k + 2] if k + 2 < len(f) else '')
        ends[(pos, cls)].add(latin_norm(end))
    return stems, ends


# ---------------------------------------------------------------- the sponsors' span rule and phrase pass
def in_span(tokens, i, is_latin):
    """The document's rule: a word is accepted only inside a multi-word Latin span: the word before or after it is Latin
    too (punctuation between ends the span)."""
    def latin_at(j): return 0 <= j < len(tokens) and re.search(r'[A-Za-zÀ-ɏ]', tokens[j]) and is_latin(tokens[j])
    return latin_at(i - 1) or latin_at(i + 1)


def decide_latin_word(form, tokens, i, is_latin):
    """'span' (decided: inside a multi-word Latin span), 'single' (a hit alone: counted, not decided), 'short' (a short
    word shared with English, alone: never decided), or None (no hit)."""
    words = [w for w in re.split(r'\s+', form.strip()) if w]
    if len(words) > 1:                                       # a passage: every word Latin
        return 'span' if all(is_latin(w) for w in words) else None
    if not is_latin(form): return None
    if latin_norm(form) in SHORT_SHARED: return 'span' if in_span(tokens, i, is_latin) else 'short'
    return 'span' if in_span(tokens, i, is_latin) else 'single'


def phrase_hits(text):
    """[(start, end, phrase)] of the fixed phrase list in a page's text, whole phrases only, longest first."""
    out, taken = [], set()
    low = text.lower()
    for ph in sorted(PHRASES, key=len, reverse=True):
        for m in re.finditer(r'(?<![A-Za-z])' + re.escape(ph) + r'(?![A-Za-z])', low):
            if any(k in taken for k in range(m.start(), m.end())): continue
            taken.update(range(m.start(), m.end())); out.append((m.start(), m.end(), ph))
    return out


def gbif_pairs(tokens, genera, species):
    """Genus + epithet pairs read from the page's words (L10): a capitalized word that is a GBIF genus, then a lower-case
    word, the two together a GBIF species name. Also "M. polymorpha" when one genus with that initial has that epithet on
    the page or in GBIF uniquely. Returns [(i, j, name)]."""
    out = []
    for i in range(len(tokens) - 1):
        g = tokens[i].strip('(),;:'); e = tokens[i + 1].strip('(),;:.')
        if not (g[:1].isupper() and e[:1].islower() and e.isalpha()): continue
        if g in genera and f'{g} {e}' in species: out.append((i, i + 1, f'{g} {e}'))
    return out


# ---------------------------------------------------------------- the review sheet
def fill_sheet(rows, answer_of, stop_min=3):
    """The review sheet filled from known answers: approve when the AI named Latin, reject otherwise; a rejected match
    with at least stop_min places goes on the stoplist. rows: [{'form', 'places', …}]; answer_of(form) -> 'la', another
    answer, or None (no answer known: left blank)."""
    out = []
    for r in rows:
        a = answer_of(r['form'])
        if a is None: d = ''
        elif a == 'la': d = 'approve'
        else: d = 'stoplist' if r['places'] >= stop_min else 'reject'
        out.append({**r, 'decision': d})
    return out


# ================================================================ build: word lists from the downloads
def _lists(d, src): p = os.path.join(d, src, '_lists'); os.makedirs(p, exist_ok=True); return p
def _write(path, words): open(path, 'w', encoding='utf-8').write('\n'.join(sorted(words)))
def _read(path): return set(open(path, encoding='utf-8').read().split('\n')) - {''} if os.path.exists(path) else set()


def build_lila(d):
    lem = set()
    for l in open(os.path.join(d, 'lila', 'lemmaBank.ttl'), encoding='utf-8'):
        m = re.search(r'ontolex:writtenRep\s+"([^"]+)"', l)
        if m: lem.add(latin_norm(m.group(1)))
    _write(os.path.join(_lists(d, 'lila'), 'latin.txt'), lem - {''})
    return {'lemmas': len(lem)}


def build_whitaker(d):
    w = next(os.path.join(d, 'whitaker', 'src', x) for x in os.listdir(os.path.join(d, 'whitaker', 'src')))
    stems, ends = whitaker_parse(open(os.path.join(w, 'DICTLINE.GEN'), encoding='latin-1'), open(os.path.join(w, 'INFLECTS.LAT'), encoding='latin-1'))
    uni = set()
    lines = open(os.path.join(w, 'UNIQUES.LAT'), encoding='latin-1').read().split('\n')
    for k in range(0, len(lines), 3):
        if lines[k].strip(): uni.add(latin_norm(lines[k]))
    json.dump({'stems': {f'{a}|{b}': sorted(v) for (a, b), v in stems.items()}, 'ends': {f'{a}|{b}': sorted(v) for (a, b), v in ends.items()},
               'uniques': sorted(uni)}, open(os.path.join(_lists(d, 'whitaker'), 'whitaker.json'), 'w'))
    return {'stems': sum(len(v) for v in stems.values()), 'endings': sum(len(v) for v in ends.values()), 'uniques': len(uni)}


def build_kaikki(d):
    """Wiktionary (kaikki): words and their forms; for Japanese and Korean also the romanizations."""
    out = {}
    for lang, code in (('Latin', 'la'), ('Hawaiian', 'haw'), ('Japanese', 'ja'), ('Korean', 'ko'), ('Tagalog', 'tl')):
        words, roman = set(), set()
        for l in open(os.path.join(d, 'kaikki', f'{lang}.jsonl'), encoding='utf-8'):
            try: e = json.loads(l)
            except ValueError: continue
            skip = ('romanization', 'table-tags', 'inflection-template')
            ws = [e.get('word', '')] + [f.get('form', '') for f in e.get('forms') or [] if not set(f.get('tags') or []) & set(skip)]
            for x in ws:
                if x: words.add(latin_norm(x) if code == 'la' else plain(x))
            for f in e.get('forms') or []:
                if 'romanization' in (f.get('tags') or []) and f.get('form'): roman.add(plain(f['form']))
        _write(os.path.join(_lists(d, 'kaikki'), f'{code}.txt'), words - {''})
        if roman: _write(os.path.join(_lists(d, 'kaikki'), f'{code}-Latn.txt'), roman - {''})
        out[lang] = {'words': len(words), 'romanizations': len(roman)}
    return out


def build_omw(d):
    """OMW 1.4: the Japanese and Chinese wordnets' written forms (1.4 has no Latin, Hawaiian, Korean or Tagalog wordnet)."""
    base, out = os.path.join(d, 'omw', 'src', 'omw-1.4'), {}
    for code, sub in (('ja', 'omw-ja'), ('zh', 'omw-cmn')):
        ws = set()
        for l in open(os.path.join(base, sub, f'{sub}.xml'), encoding='utf-8'):
            for m in re.finditer(r'writtenForm="([^"]+)"', l): ws.add(plain(m.group(1)))
        _write(os.path.join(_lists(d, 'omw'), f'{code}.txt'), ws - {''}); out[code] = len(ws)
    return out


def build_wikidata(d):
    """Wikidata lexemes: lemmas and form representations by language code."""
    by = collections.defaultdict(set)
    want = {'la', 'haw', 'ja', 'ja-hira', 'ja-kana', 'ja-latn', 'ko', 'ko-latn', 'tl', 'ilo', 'zh', 'zh-hans', 'zh-hant', 'zh-latn-pinyin', 'vi', 'sa', 'pi'}
    with bz2.open(os.path.join(d, 'wikidata', 'latest-lexemes.json.bz2'), 'rt', encoding='utf-8') as f:
        for l in f:
            l = l.strip().rstrip(',')
            if not l.startswith('{'): continue
            try: e = json.loads(l)
            except ValueError: continue
            reps = list((e.get('lemmas') or {}).values())
            for fm in e.get('forms') or []: reps += list((fm.get('representations') or {}).values())
            for r in reps:
                c = (r.get('language') or '').lower()
                if c in want: by[c].add(latin_norm(r['value']) if c == 'la' else plain(r['value']))
    for c, ws in by.items(): _write(os.path.join(_lists(d, 'wikidata'), f'{c}.txt'), ws - {''})
    return {c: len(v) for c, v in sorted(by.items())}


def build_gbif(d):
    """GBIF Backbone: genera, and species and lower ranks as "Genus epithet"."""
    gen, spe = set(), set()
    with zipfile.ZipFile(os.path.join(d, 'gbif', 'backbone.zip')) as z:
        with z.open('Taxon.tsv') as f:
            head = f.readline().decode('utf-8').rstrip('\n').split('\t')
            ci, ri, gi, ei = head.index('canonicalName'), head.index('taxonRank'), head.index('genericName'), head.index('specificEpithet')
            for raw in f:
                c = raw.decode('utf-8', 'replace').rstrip('\n').split('\t')
                if len(c) <= max(ci, ri, gi, ei): continue
                rank = c[ri].lower()
                if rank == 'genus' and c[ci]: gen.add(c[ci])
                elif c[gi] and c[ei] and rank in ('species', 'subspecies', 'variety', 'form'): spe.add(f'{c[gi]} {c[ei]}'); gen.add(c[gi])
    _write(os.path.join(_lists(d, 'gbif'), 'genera.txt'), gen); _write(os.path.join(_lists(d, 'gbif'), 'species.txt'), spe)
    return {'genera': len(gen), 'species': len(spe)}


def build_lewis_short(d):
    """Lewis & Short (Perseus TEI XML, the Unicode file): every Latin headword and its alternative forms (lemmas only)."""
    ws = set()
    for l in open(os.path.join(d, 'lewis-short', 'lat.ls.perseus-eng2.xml'), encoding='utf-8'):
        for m in re.finditer(r'<orth[^>]*lang="la"[^>]*>([^<]+)</orth>', l): ws.add(latin_norm(m.group(1)))
    ws.discard(''); _write(os.path.join(_lists(d, 'lewis-short'), 'latin.txt'), ws)
    return {'headwords': len(ws)}


def build_col(d):
    """Catalogue of Life (Darwin Core archive): genera, and species and lower ranks as "Genus epithet"."""
    gen, spe = set(), set()
    with zipfile.ZipFile(os.path.join(d, 'col', 'latest_dwca.zip')) as z:
        name = next(n for n in z.namelist() if n.lower().endswith('taxon.tsv') or n.lower().endswith('taxon.txt'))
        with z.open(name) as f:
            head = [h.split(':')[-1] for h in f.readline().decode('utf-8').rstrip('\r\n').split('\t')]
            ri, gi, ei = head.index('taxonRank'), head.index('genericName'), head.index('specificEpithet')
            ci = head.index('scientificName')
            for raw in f:
                c = raw.decode('utf-8', 'replace').rstrip('\r\n').split('\t')
                if len(c) <= max(ri, gi, ei, ci): continue
                rank = c[ri].lower()
                if rank == 'genus' and c[gi]: gen.add(c[gi])
                elif rank == 'genus' and c[ci]: gen.add(c[ci].split()[0])
                elif c[gi] and c[ei] and rank in ('species', 'subspecies', 'variety', 'form'): spe.add(f'{c[gi]} {c[ei]}'); gen.add(c[gi])
    _write(os.path.join(_lists(d, 'col'), 'genera.txt'), gen); _write(os.path.join(_lists(d, 'col'), 'species.txt'), spe)
    return {'genera': len(gen), 'species': len(spe)}


def build_ncbi(d):
    """NCBI Taxonomy (taxdump): genera, and the scientific names of species and lower ranks, as "Genus epithet"."""
    rank = {}
    with tarfile.open(os.path.join(d, 'ncbi', 'taxdump.tar.gz')) as t:
        for l in t.extractfile('nodes.dmp'):
            f = l.decode('utf-8').rstrip('\t|\n').split('\t|\t')
            rank[f[0].strip()] = f[2].strip()
        gen, spe = set(), set()
        for l in t.extractfile('names.dmp'):
            f = [x.strip() for x in l.decode('utf-8').rstrip('\t|\n').split('\t|\t')]
            if len(f) < 4 or f[3] != 'scientific name': continue
            r, nm = rank.get(f[0]), f[1].split()
            if r == 'genus' and nm: gen.add(nm[0])
            elif r in ('species', 'subspecies', 'varietas', 'forma') and len(nm) >= 2 and nm[0][:1].isupper() and nm[1][:1].islower():
                spe.add(f'{nm[0]} {nm[1]}'); gen.add(nm[0])
    _write(os.path.join(_lists(d, 'ncbi'), 'genera.txt'), gen); _write(os.path.join(_lists(d, 'ncbi'), 'species.txt'), spe)
    return {'genera': len(gen), 'species': len(spe)}


BUILDERS = {'lila': build_lila, 'whitaker': build_whitaker, 'kaikki': build_kaikki, 'omw': build_omw, 'wikidata': build_wikidata, 'gbif': build_gbif,
            'lewis-short': build_lewis_short, 'col': build_col, 'ncbi': build_ncbi}


def build(d, which=None):
    """Each source's lists, with its build time, into DICT_DIR/build.json (kept from earlier builds)."""
    path = os.path.join(d, 'build.json')
    t = json.load(open(path)) if os.path.exists(path) else {}
    for name in which or BUILDERS:
        t0 = time.time(); r = BUILDERS[name](d)
        t[name] = {**r, 'seconds': round(time.time() - t0, 1)}
        print(name, json.dumps(t[name]), flush=True)
        json.dump(t, open(path, 'w'), indent=1)


# ================================================================ run: the workflow over the test books
def load(d):
    t0 = time.time(); L = {}
    L['lila'] = _read(os.path.join(d, 'lila', '_lists', 'latin.txt'))
    w = json.load(open(os.path.join(d, 'whitaker', '_lists', 'whitaker.json')))
    L['wh_stems'] = {tuple(k.split('|')): set(v) for k, v in w['stems'].items()}
    L['wh_ends'] = {tuple(k.split('|')): set(v) for k, v in w['ends'].items()}
    L['wh_uni'] = set(w['uniques'])
    for c in ('la', 'haw', 'ja', 'ko', 'tl', 'ja-Latn', 'ko-Latn'): L[f'kk_{c}'] = _read(os.path.join(d, 'kaikki', '_lists', f'{c}.txt'))
    for c in ('ja', 'zh'): L[f'omw_{c}'] = _read(os.path.join(d, 'omw', '_lists', f'{c}.txt'))
    for f in os.listdir(os.path.join(d, 'wikidata', '_lists')): L['wd_' + f[:-4]] = _read(os.path.join(d, 'wikidata', '_lists', f))
    L['genera'] = _read(os.path.join(d, 'gbif', '_lists', 'genera.txt')); L['species'] = _read(os.path.join(d, 'gbif', '_lists', 'species.txt'))
    L['ls'] = _read(os.path.join(d, 'lewis-short', '_lists', 'latin.txt'))
    L['checklists'] = {'GBIF': (L['genera'], L['species'])}
    for name, sub in (('Catalogue of Life', 'col'), ('NCBI Taxonomy', 'ncbi')):
        g, sp = _read(os.path.join(d, sub, '_lists', 'genera.txt')), _read(os.path.join(d, sub, '_lists', 'species.txt'))
        if g or sp: L['checklists'][name] = (g, sp)
    L['_secs'] = round(time.time() - t0, 1)
    return L


def latin_sources(L):
    """name -> is_latin(word), one per Latin source alone."""
    return {'LiLa': lambda w: latin_norm(w) in L['lila'],
            "Whitaker's Words": lambda w: whitaker_match(w, L['wh_stems'], L['wh_ends'], L['wh_uni']),
            'Wiktionary (kaikki)': lambda w: latin_norm(w) in L['kk_la'],
            'Wikidata lexemes': lambda w: latin_norm(w) in L.get('wd_la', set()),
            **({'Lewis & Short': lambda w: latin_norm(w) in L['ls']} if L.get('ls') else {})}


def other_sources(L):
    """name -> {lang: set}: each other-language source's lists (romanized lists matched in lower case, with marks)."""
    return {'Wiktionary (kaikki)': {'haw': L['kk_haw'], 'ja-Latn': L['kk_ja-Latn'], 'ko-Latn': L['kk_ko-Latn'], 'tl': L['kk_tl'],
                                    'ja': L['kk_ja'], 'ko': L['kk_ko']},
            'OMW 1.4': {'ja': L['omw_ja'], 'zh': L['omw_zh']},
            'Wikidata lexemes': {'haw': L.get('wd_haw', set()), 'ja-Latn': L.get('wd_ja-latn', set()), 'ko-Latn': L.get('wd_ko-latn', set()),
                                 'tl': L.get('wd_tl', set()), 'ilo': L.get('wd_ilo', set()), 'ja': L.get('wd_ja', set()) | L.get('wd_ja-hira', set()) | L.get('wd_ja-kana', set()),
                                 'ko': L.get('wd_ko', set()), 'zh': L.get('wd_zh', set()) | L.get('wd_zh-hans', set()) | L.get('wd_zh-hant', set()),
                                 'zh-Latn': L.get('wd_zh-latn-pinyin', set()), 'vi': L.get('wd_vi', set())}}


def primary(t): return (t or '').split('-')[0].lower() if t else None
def same(a, b):
    """Two language answers agree: same tag, or same primary language where one has no script."""
    if not a or not b: return False
    a, b = a.lower(), b.lower()
    return a == b or (primary(a) == primary(b) and ('-' not in a or '-' not in b))


def answers(run_dir):
    """{form key: answer}: the language tag, or 'English', 'name', 'none' (no language), from a language_run.json."""
    try: lr = json.load(open(os.path.join(run_dir, 'language_run.json'), encoding='utf-8'))
    except (OSError, ValueError): return {}
    out = {}
    for k, v in (lr.get('decisions') or {}).items():
        out[k] = v.get('lang') or {'english': 'English', 'name': 'name'}.get(v.get('why'), 'none')
    return out


def page_texts(pdf):
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf); out = []
    try:
        for i in range(len(doc)):
            tp = doc[i].get_textpage()
            try: out.append(tp.get_text_range())
            finally: tp.close()
    finally: doc.close()
    return out


def gnfinder(d, texts, work):
    """GNfinder over the book's text, offline under the network-denying sandbox, no verification: [(page, name, cardinality)]."""
    path = os.path.join(work, 'text.txt')
    sep = '\n\n\f\n\n'
    open(path, 'w', encoding='utf-8').write(sep.join(texts))
    starts, pos = [], 0
    for t in texts: starts.append(pos); pos += len(t) + len(sep)
    g = os.path.join(d, 'gnfinder')
    r = subprocess.run(['sandbox-exec', '-f', os.path.join(g, 'nonet.sb'), os.path.join(g, 'bin', 'gnfinder'), '-U', '--no-tika', '-f', 'compact', path],
                       capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-500:])
    out = []
    import bisect
    for n in json.loads(r.stdout).get('names') or []:
        pg = bisect.bisect_right(starts, n['start'])
        out.append((pg, n['name'], n.get('cardinality', 0), n.get('verbatim', '')))
    return out


def name_checked(name, card, genera, species, ep):
    """A GNfinder name found in a checklist (as gbif_checked, for any list: its genera, its species, its epithet index)."""
    w = name.split()
    if card == 1: return w[0] in genera
    if len(w) >= 2:
        if f'{w[0]} {w[1]}' in species: return True
        if re.fullmatch(r'[A-Z]\.', w[0]): return any(x.startswith(w[0][0]) for x in ep.get(w[1], ()))
    return False


def gbif_checked(name, card, L):
    """A GNfinder name found in the GBIF list: a binomial (or the binomial part of a trinomial) in its species, a uninomial
    in its genera; an abbreviated genus ("M. polymorpha") when some genus with that initial has that epithet."""
    w = name.split()
    if card == 1: return w[0] in L['genera']
    if len(w) >= 2:
        if f'{w[0]} {w[1]}' in L['species']: return True
        if re.fullmatch(r'[A-Z]\.', w[0]):
            return any(s.startswith(w[0][0]) and s.endswith(' ' + w[1]) for s in L['_ep'].get(w[1], ()))
    return False


def book_tokens(text):
    return re.findall(r"[^\s]+", text)


def latincy_lemmas(d, spans):
    """{span: [lemma, …]} from LatinCy, in its own venv, on candidate Latin spans only (the document's advice)."""
    if not spans: return {}
    py = os.path.join(d, 'latincy', '.venv', 'bin', 'python3')
    code = ("import sys,json,spacy\nnlp=spacy.load('la_core_web_lg')\nsp=json.load(sys.stdin)\n"
            "print(json.dumps({s:[t.lemma_ for t in nlp(s)] for s in sp}))")
    r = subprocess.run([py, '-I', '-c', code], input=json.dumps(sorted(spans)), capture_output=True, text=True, cwd='/tmp')
    if r.returncode: raise RuntimeError(r.stderr[-800:])
    return json.loads(r.stdout)


def run(d, out, books):
    """books: [{name, pdf, audit (lang_candidates.json), run (language_run.json's folder) or None, kind}]"""
    os.makedirs(out, exist_ok=True)
    L = load(d); print('lists loaded', L['_secs'], 's', flush=True)
    ep = collections.defaultdict(set)
    for s in L['species']:
        g, e = s.split(' ', 1); ep[e].add(s)
    L['_ep'] = ep
    L['_eps'] = {}
    for k, (g, sp) in L['checklists'].items():
        e = collections.defaultdict(set)
        for x in sp:
            a_, b_ = x.split(' ', 1); e[b_].add(x)
        L['_eps'][k] = e
    LS, OS = latin_sources(L), other_sources(L)
    memo = {}
    def is_latin_any(w):                                    # any Latin source, cached per word (the span rule asks often)
        k = latin_norm(w)
        if k not in memo: memo[k] = bool(k) and any(f(w) for f in LS.values())
        return memo[k]
    from lib import ocrwords
    res = {'lists_load_seconds': L['_secs'], 'books': {}}
    sheet = collections.defaultdict(lambda: {'places': 0, 'books': set(), 'sources': set(), 'span': 0, 'single': 0, 'short': 0, 'context': '', 'answers': collections.Counter()})
    for b in books:
        t0 = time.time(); B = {'kind': b['kind']}
        c = json.load(open(b['audit'], encoding='utf-8'))
        ans = answers(b['run']) if b.get('run') else {}
        texts = page_texts(b['pdf'])
        work = os.path.join(out, 'work', b['name']); os.makedirs(work, exist_ok=True)
        # forms: one row per form key the language step would send, with its places
        forms = collections.defaultdict(list)
        for p in c['places']:
            g = 'passage' if 'passage' in p['class'] else ('existing' if 'existing' in p['class'] else None)
            forms[p['form']].append(p)
        keys = {}
        for k in ans: keys.setdefault(k.split('|', 1)[1].split('|')[0] if '|' in k else k, k)
        # 1. species
        t1 = time.time(); names = gnfinder(d, texts, work); B['gnfinder_seconds'] = round(time.time() - t1, 1)
        sp_words = collections.defaultdict(set); B['gnfinder_names'] = len(names); B['gnfinder_in_gbif'] = 0
        by_list = {k: collections.defaultdict(set) for k in L['checklists']}; B['gnfinder_in'] = collections.Counter()
        for pg, nm, card, verb in names:
            ok = gbif_checked(nm, card, L)
            B['gnfinder_in_gbif'] += ok
            if ok:
                for w in re.findall(r'[A-Za-z]+', verb): sp_words[pg].add(w.lower())
            for k, (g, sp) in L['checklists'].items():           # each checklist on its own (report 12's addendum)
                if name_checked(nm, card, g, sp, L['_eps'][k]):
                    B['gnfinder_in'][k] += 1
                    for w in re.findall(r'[A-Za-z]+', verb): by_list[k][pg].add(w.lower())
        pairs = 0; pair_words = collections.defaultdict(set)
        for i, t in enumerate(texts, 1):
            toks = book_tokens(t)
            for a_, b_, nm in gbif_pairs(toks, L['genera'], L['species']):
                pairs += 1; pair_words[i] |= {nm.split()[0].lower(), nm.split()[1].lower()}
        B['gbif_pairs'] = pairs
        # 2. phrases, 7. abbreviations
        ph_words = collections.defaultdict(set); B['phrases'] = collections.Counter()
        B['abbreviations'] = collections.Counter()
        for i, t in enumerate(texts, 1):
            for s_, e_, ph in phrase_hits(t):
                B['phrases'][ph] += 1; ph_words[i] |= set(ph.split())
            for name_, rx in ABBREVIATIONS.items(): B['abbreviations'][name_] += len(re.findall(rx, t, re.I))
        # 3. Latin words, per source and together; 6. other languages, per source
        tok_pages = {i: book_tokens(t) for i, t in enumerate(texts, 1)}
        lower_pages = {i: [x.lower().strip('.,;:()[]"“”‘’') for x in toks] for i, toks in tok_pages.items()}
        decided = {}                                          # form -> (lang, how)
        per_src = collections.defaultdict(dict)                # source -> form -> lang
        cands_latin_spans = set()
        for form, ps in forms.items():
            words = form.split()
            spc = sum(1 for p in ps if all(w.lower().strip('.,;:()') in sp_words[p['page']] | pair_words[p['page']] for w in words))
            if spc: decided[form] = ('la', 'species'); continue
            if any(all(w.lower() in ph_words[p['page']] for w in words) for p in ps): decided[form] = ('la', 'phrase'); continue
        for form, ps in forms.items():
            for k, words_ in by_list.items():
                if any(all(w.lower().strip('.,;:()') in words_[p['page']] for w in form.split()) for p in ps):
                    per_src['Species: ' + k][form] = 'la'
            for sname, f in LS.items():
                if all(f(w) for w in form.split()): per_src['Latin: ' + sname][form] = 'la'
            for sname, langs in OS.items():
                hit = [lg for lg, ws in langs.items() if plain(form) in ws]
                if len(hit) == 1: per_src['other: ' + sname][form] = hit[0]
            if form in decided: continue
            kinds = collections.Counter()
            for p in ps[:20]:
                toks = lower_pages.get(p['page'], [])
                first = form.split()[0].lower()
                idx = [k for k, x in enumerate(toks) if x == first]
                if not idx: kinds['single' if is_latin_any(form) else 'none'] += 1; continue
                kinds[decide_latin_word(form, toks, idx[0], is_latin_any) or 'none'] += 1
                if is_latin_any(form) and len(cands_latin_spans) < 4000:
                    k = idx[0]; cands_latin_spans.add(' '.join(tok_pages[p['page']][max(0, k - 3):k + 4]))
            if kinds['span']: decided[form] = ('la', 'latin span')
            if is_latin_any(form):
                r = sheet[form]; r['places'] += len(ps); r['books'].add(b['name'])
                r['sources'] |= {s for s, f in LS.items() if all(f(w) for w in form.split())}
                r['span'] += kinds['span']; r['single'] += kinds['single']; r['short'] += kinds['short']
                if not r['context']:
                    p = ps[0]; toks = tok_pages.get(p['page'], []); first = form.split()[0]
                    k = next((j for j, x in enumerate(toks) if x.strip('.,;:()').lower() == first.lower()), None)
                    r['context'] = ' '.join(toks[max(0, k - 5):k + 6]) if k is not None else ''
                a = ans.get(keys.get(form)) if keys.get(form) else None
                if a: r['answers'][a] += 1
        # 8. Hawaiian-shaped forms decided Latin: wrong whatever the AI said
        haw_wrong = [f for f, (lg, how) in decided.items() if lg == 'la' and ocrwords.hawaiian_shape(f.lower()) and how != 'species']
        B['decided'] = {f: list(v) for f, v in decided.items()}
        B['per_source'] = {s: v for s, v in per_src.items()}
        B['answers'] = {f: ans.get(keys[f]) for f in forms if keys.get(f)}
        B['forms'] = len(forms); B['sent_forms'] = len(ans)
        B['hawaiian_shaped_latin'] = haw_wrong
        B['latincy_spans'] = sorted(cands_latin_spans)
        B['seconds'] = round(time.time() - t0, 1)
        res['books'][b['name']] = B
        print(f"{b['name']}: forms {len(forms)}, decided {len(decided)}, gnfinder {B['gnfinder_names']} ({B['gnfinder_in_gbif']} in GBIF), pairs {pairs}, {B['seconds']} s", flush=True)
    # LatinCy on the candidate Latin spans: lemmas looked up in LiLa
    spans = sorted({s for B in res['books'].values() for s in B['latincy_spans']})
    t0 = time.time(); lem = latincy_lemmas(d, spans[:6000]); res['latincy_seconds'] = round(time.time() - t0, 1); res['latincy_spans'] = len(lem)
    lem_in_lila = {}
    for s, ls in lem.items():
        for tok, l in zip(s.split(), ls):
            lem_in_lila[tok.lower().strip('.,;:()')] = latin_norm(l) in L['lila']
    for B in res['books'].values():
        B['per_source']['Latin: LatinCy + LiLa'] = {f: 'la' for f in B['answers'] if all(lem_in_lila.get(w.lower(), False) for w in f.split())}
    rows = sorted(({'form': f, 'places': r['places'], 'books': len(r['books']), 'sources': ', '.join(sorted(r['sources'])),
                    'in_span': r['span'], 'alone': r['single'], 'short_alone': r['short'], 'context': r['context'],
                    'ai_answer': (r['answers'].most_common(1)[0][0] if r['answers'] else '')} for f, r in sheet.items()),
                  key=lambda x: (-x['places'], x['form']))
    res['sheet_rows'] = rows
    json.dump(res, open(os.path.join(out, 'results.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=list)
    return res


# ================================================================ score: right and wrong, per source and for the workflow
RATE = 0.00098            # dollars per word form sent: level 4's measured rate (report 07 §4)
PER_REQUEST = 150         # word forms per request (lib/langreq.py)


def tally(pairs):
    """pairs: [(decided lang, AI answer)] -> {'decided', 'right', 'wrong', 'by_lang': {lang: [right, wrong]}}."""
    out = {'decided': 0, 'right': 0, 'wrong': 0, 'by_lang': collections.defaultdict(lambda: [0, 0])}
    for lg, a in pairs:
        out['decided'] += 1
        ok = same(lg, a)
        out['right' if ok else 'wrong'] += 1; out['by_lang'][lg][0 if ok else 1] += 1
    out['by_lang'] = dict(out['by_lang'])
    return out


def score(out, stoplist=frozenset(), test_items=None, sonnet=None, scored_books=None):
    """From run()'s results.json: per source and for the workflow (species, phrases, Latin spans, less the stoplist),
    the forms decided among those the AI answered, right and wrong against its answer by language, the forms still sent,
    and the money and requests saved. test_items/sonnet: the scored test set and Sonnet's replies on it (#142), for each
    source's wrong answers against the AI's own on the same items."""
    res = json.load(open(os.path.join(out, 'results.json'), encoding='utf-8'))
    S = collections.defaultdict(list); W = []; wrong_rows = collections.defaultdict(list); sent = 0; haw = []
    for name, B in res['books'].items():
        if scored_books is not None and name not in scored_books: continue
        A = {f: a for f, a in B['answers'].items() if a}
        sent += len(A)
        for src, dec in B['per_source'].items():
            for f, lg in dec.items():
                if f in A:
                    S[src].append((lg, A[f]))
                    if not same(lg, A[f]): wrong_rows[src].append((name, f, lg, A[f]))
        for f, (lg, how) in B['decided'].items():
            if f in A and latin_norm(f) not in stoplist:
                W.append((lg, A[f]))
                if not same(lg, A[f]): wrong_rows['workflow'].append((name, f, lg, A[f], how))
        haw += [(name, f) for f in B['hawaiian_shaped_latin']]
    r = {'forms_sent': sent, 'sources': {}, 'workflow': tally(W)}
    for src, pairs in sorted(S.items()): r['sources'][src] = tally(pairs)
    for k, v in list(r['sources'].items()) + [('workflow', r['workflow'])]:
        v['still_sent'] = sent - v['decided']; v['saved_usd'] = round(v['decided'] * RATE, 2); v['requests_saved'] = round(v['decided'] / PER_REQUEST, 1)
    r['wrong_examples'] = {k: v for k, v in wrong_rows.items()}
    r['hawaiian_shaped_latin'] = haw
    if test_items:
        # each source on the scored test set's forms, against the truth, beside Sonnet's own wrong answers on the same items
        L = res.get('_lists_for_test')
        r['test_set'] = test_items
    return r


def score_test_set(L, items, sonnet_runs, outcome):
    """Each source on the scored test set (#142's W10 items, with their accepted answers), against Sonnet's answers on
    the same items: {source: {'decided', 'right', 'wrong', 'sonnet_wrong_same_items', 'sonnet_untagged_same_items'}}."""
    LS, OS = latin_sources(L), other_sources(L)
    out = {}
    def add(src, it, lg):
        x = out.setdefault(src, {'decided': 0, 'right': 0, 'wrong': 0, 'sonnet_wrong_same_items': 0, 'sonnet_untagged_same_items': 0,
                                 'runs': len(sonnet_runs), 'wrong_examples': []})
        x['decided'] += 1
        ok = any(same(lg, a) for a in it['accept'] if a)
        x['right' if ok else 'wrong'] += 1
        if not ok and len(x['wrong_examples']) < 40: x['wrong_examples'].append((it['form'], lg, it['accept']))
        for run in sonnet_runs.values():
            o = outcome(run.get(it['id']), it['accept'])
            if o == 'wrong': x['sonnet_wrong_same_items'] += 1
            elif o == 'untagged': x['sonnet_untagged_same_items'] += 1
    for it in items:
        if not it.get('accept') or it.get('kind') == 'nokey': continue
        f = it['form']
        for src, fn in LS.items():
            if all(fn(w) for w in f.split()): add('Latin: ' + src, it, 'la')
        for src, langs in OS.items():
            hit = [lg for lg, ws in langs.items() if plain(f) in ws]
            if len(hit) == 1: add('other: ' + src, it, hit[0])
    return out


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if len(sys.argv) >= 3 and sys.argv[1] == 'build': build(sys.argv[2], sys.argv[3:] or None)
    elif len(sys.argv) >= 4 and sys.argv[1] == 'run':
        books = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else []
        run(sys.argv[2], sys.argv[3], books)
    else: sys.exit(__doc__)
