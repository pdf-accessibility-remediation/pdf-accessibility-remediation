"""lang_test.py: the language step's two-model test (#118, language tagging; review 02, M1 and M2). Builds the test items
and their keys, writes the requests exactly as lib/langreq.py builds them, estimates their cost from live prices, and
(only with --send) sends them through OpenRouter. Paid: --send needs Patrick's OK; the whole test's cap is $10.

    python3 tools/lang_test.py build OUT_DIR BOOK=PDF …       items.json, requests/, estimate.md (free, no network
                                                              except OpenRouter's public model list for prices)
    python3 tools/lang_test.py send OUT_DIR --model ID --run N --set tune|score|nokey|book [--cap USD]   (paid)

Items (each a form with one place and its context), keys kept apart (never pooled; scored by tools/lang_score.py):
  ga_raw / ga_corrected   globalasias's 42 publisher tags, raw and with review 02 H3's corrections
  silver:<source>         local evidence, two signals per item (a rule on the form or its neighbours, and the book's
                          subject): kana next to Han (ja), a Hepburn reading next to Han (ja), pinyin next to Han (zh),
                          Hepburn marks (ja-Latn), IAST marks (sa-Latn or pi-Latn), ʻokina in a Hawaiian word (haw)
  synthetic               kana runs and checked globalasias forms in neutral sentences (labelled synthetic)
  nokey                   Han-only forms with no reading nearby: no key; model-to-model agreement and the spot check
Halves: each item's id is hashed into "tune" or "score" (fixed); the prompt is tuned on tune and scored on score.
A whole book (cadaverous) is sent once per model, to measure the cost per book.
No book text is written outside OUT_DIR (runs/, never committed).
"""
import sys, os, json, re, hashlib, random, collections, argparse, time, shutil, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import plumb_fix, plpages, langcands, langreq, scripts, models  # noqa: F401

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT = os.path.join(os.path.dirname(PIPE), 'prompts', 'language_v1.md')
PROMPT_V2 = os.path.join(os.path.dirname(PIPE), 'prompts', 'language_v2.md')
MODELS = ['anthropic/claude-sonnet-5.5', 'anthropic/claude-opus-5.5', 'anthropic/claude-haiku-5.5']
SUBJECT = {'cadaverous': 'japan', 'teika': 'japan', 'evangelist': 'japan', 'transnational': 'japan', 'buddhist': 'pali',
           'hawaii3': 'hawaii', 'expedition': 'china', 'sojourners': 'china', 'dwellings': 'china', 'globalasias': 'mixed',
           'korea-matters': 'korea', 'chung-taka': 'korea', 'yoon-topics': 'korea', 'memorial-ko': 'korea', 'ktimes-1990': 'korea',
           'taiwan-matters': 'china', 'tclt7': 'china', 'romanization-guide': 'china', 'taichen': 'china',
           'yao-history': 'china', 'yao-intelligences': 'china', 'yao-popularizing': 'china', 'mohr-zen': 'japan',
           'vietnamese': 'vietnam', 'ryukyu': 'ryukyu'}
# The body text's own language, where it is not English (from each sample's manifest): CJK documents, whose Latin-script
# parts are the reverse direction (English inside Chinese, Japanese or Korean)
DOC_LANG = {'yao-history': 'zh', 'yao-intelligences': 'zh', 'yao-popularizing': 'zh', 'mohr-zen': 'ja', 'ktimes-1990': 'ko'}
NOKEY_BOOKS = ('cadaverous', 'teika', 'globalasias', 'taiwan-matters', 'tclt7', 'korea-matters', 'memorial-ko', 'ryukyu')
PER_SOURCE = 25
NOKEY_PER_BOOK = 12
HEPBURN_ONLY = re.compile(r'[ōū]')
IAST = re.compile(r'[ṣṇṭḍśṛṃṅṁḥ]')
JA_SYL = re.compile(r"(?i)^(?:(?:ky|sh|ch|ts|ny|hy|my|ry|gy|by|py|j|[kgsztdnhbpmyrwf])?[aiueoāīūēō]|n(?![aiueoāīūēōy]))+$")
PINYIN = langcands.PINYIN_U          # the pinyin shape with üan, ün, üe, matched in linear time (CodeQL py/redos)
SIMPLIFIED = set('创农乐这们说时为长门见车东发书马习头实对应现经过还进动边关开问间听记识语')   # simplified-only: never in Japanese (国, 数, 学 are)
HAW_LETTERS = set('aeiouāēīōūhklmnpwʻ')
BREVE = re.compile(r'[ŏŭŎŬ]')                 # McCune-Reischauer (Korean) and Wade-Giles (Chinese: tzŭ) use them
TONE = re.compile(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]')
VIET = re.compile(r'[ơưđạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹƠƯĐ]')
BUDDHIST = {'cadaverous', 'buddhist'}         # books on Buddhism: IAST letters there are Sanskrit or Pali

def toneless(w):
    """A pinyin word without its tone marks (ü kept): 'zhōngguó' → 'zhongguo'."""
    import unicodedata
    return unicodedata.normalize('NFC', ''.join(c for c in unicodedata.normalize('NFD', w) if not unicodedata.combining(c) or c == '\u0308'))

def half(i): return 'tune' if int(hashlib.sha256(i.encode()).hexdigest(), 16) % 2 == 0 else 'score'

def candidates(name, pdf, cache):
    f = os.path.join(cache, f'{name}.json')
    if os.path.exists(f):
        r = json.load(open(f, encoding='utf-8')); r['language'] = DOC_LANG.get(name) or 'en'; return r
    r = langcands.book(plpages.Pages(pdf), doc_lang=DOC_LANG.get(name)); r['title'] = ''
    import pikepdf
    with pikepdf.open(pdf) as p: r['title'] = str(p.docinfo.get('/Title', '')).strip()
    r['language'] = DOC_LANG.get(name) or 'en'      # every other sample's body is English (intake may set /Lang from the OCR language: ryukyu ja, vietnamese vi)
    json.dump(r, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    return r

def near(places, p, pred, span=3):
    """True when another place within `span` words of p on its page satisfies pred."""
    return any(q is not p and q['page'] == p['page'] and q.get('w0') is not None and p.get('w0') is not None
               and abs(q['w0'] - p['w0']) <= span + (p['w1'] - p['w0']) and pred(q) for q in places)

def neighbour_words(words, p, span=3):
    pw = words.get(str(p['page'])) or []
    if p.get('w0') is None: return []
    return pw[max(0, p['w0'] - span):p['w0']] + pw[p['w1'] + 1:p['w1'] + 1 + span]

def latin_core(w): return re.sub(r"^\W+|\W+$", '', w)

def silver(name, cand):
    """{source: [item]} by local evidence, two signals per item (the rule, and the book's subject)."""
    subj = SUBJECT.get(name); P = cand['places']; W = cand['words']; out = collections.defaultdict(list)
    han = [p for p in P if 'cjk:han_only' in p['class']]
    for p in han:
        nb = [latin_core(w) for w in neighbour_words(W, p)]
        if subj in ('japan', 'ryukyu') and near(P, p, lambda q: 'cjk:kana' in q['class']): out['kana_next_to_han'].append((p, 'ja'))
        elif subj in ('japan', 'ryukyu') and any(HEPBURN_ONLY.search(w) and JA_SYL.match(w.lower()) and not IAST.search(w) for w in nb if w):
            out['hepburn_next_to_han'].append((p, 'ja'))
        elif (subj == 'china' or set(p['text']) & SIMPLIFIED) and any(len(w) > 3 and PINYIN.match(w) and not langcands.in_english(w) for w in nb if w):
            out['pinyin_next_to_han'].append((p, 'zh'))
        elif subj == 'korea' and near(P, p, lambda q: 'cjk:hangul' in q['class']): out['hangul_next_to_han'].append((p, 'ko'))
    for p in P:
        f = p['form']
        if ' ' in f or 'passage' in p['class']: continue
        lw = f.lower()
        if subj == 'japan' and 'marks' in p['class'] and HEPBURN_ONLY.search(lw) and JA_SYL.match(lw) and not IAST.search(lw) \
                and not set(lw) <= HAW_LETTERS and f[:1].islower():
            out['hepburn_marks'].append((p, 'ja-Latn'))
        elif name in BUDDHIST and 'marks' in p['class'] and IAST.search(lw) and f[:1].islower():
            out['iast_marks'].append((p, 'sa-Latn|pi-Latn'))
        elif subj == 'hawaii' and 'hawaiian' in p['class'] and 'ʻ' in f and set(lw) <= HAW_LETTERS and f[:1].islower():
            out['okina_hawaiian'].append((p, 'haw'))
        elif subj == 'korea' and BREVE.search(f) and not TONE.search(f):
            out['breve_korean'].append((p, 'ko-Latn'))
        elif subj == 'korea' and p.get('italic') and 'unknown' in p['class'] and f[:1].islower():
            out['yale_italic'].append((p, 'ko-Latn'))     # Korean linguistics papers set Yale romanization in italics (mwulkoki-lul)
        elif subj == 'china' and BREVE.search(f) and f[:1].islower():
            out['breve_wade_giles'].append((p, 'zh-Latn'))
        elif subj == 'china' and TONE.search(f) and f[:1].islower() and not langcands.in_english(f) and PINYIN.match(toneless(lw)) and not JA_SYL.match(lw) and not set(lw) <= HAW_LETTERS:
            out['tone_pinyin'].append((p, 'zh-Latn'))
        elif subj == 'vietnam' and VIET.search(f) and f[:1].islower():
            out['vietnamese_letters'].append((p, 'vi'))
        elif name in DOC_LANG and 'latin' in p['class'] and langcands.in_english(f) and len(f) >= 4:
            out['english_in_cjk_doc'].append((p, 'en'))
    return out

def no_evidence(cand):
    P, W = cand['places'], cand['words']; out = []
    for p in P:
        if 'cjk:han_only' not in p['class']: continue
        pw = W.get(str(p['page'])) or []
        if p.get('w0') is None: continue
        ctx = pw[max(0, p['w0'] - 15):p['w1'] + 16]
        if any(scripts.KANA.search(w) for w in ctx): continue
        if any(HEPBURN_ONLY.search(w) or (len(latin_core(w)) > 3 and PINYIN.match(latin_core(w)) and not langcands.in_english(latin_core(w))) for w in ctx): continue
        out.append(p)
    return out

def build(out_dir, books):
    os.makedirs(out_dir, exist_ok=True); cache = os.path.join(out_dir, 'cand'); os.makedirs(cache, exist_ok=True)
    prev = os.path.join(out_dir, 'items.json')
    earlier_nokey = [it for it in json.load(open(prev, encoding='utf-8'))['items'] if it['source'] == 'nokey'] if os.path.exists(prev) else []
    rnd = random.Random(118)
    C = {n: candidates(n, p, cache) for n, p in books.items()}
    items = []
    def add(src, key, name, p, accept=None, synthetic_words=None):
        iid = f'{src.split(":")[-1][:6]}-{name[:4]}-{p["page"]}-{p["mcid"]}-{p["first"]}'
        if any(x['id'] == iid for x in items): return
        items.append({'id': iid, 'source': src, 'book': name, 'page': p['page'], 'mcid': p['mcid'], 'first': p['first'], 'last': p['last'],
                      'text': p['text'], 'form': p['form'], 'class': p['class'], 'italic': p.get('italic', False), 'w0': p.get('w0'), 'w1': p.get('w1'),
                      'key': key, 'accept': accept or ([] if key is None else key.split('|')), 'half': half(iid),
                      **({'words': synthetic_words} if synthetic_words else {})})
    # 1. globalasias, raw and corrected (one item each; both keys on it)
    if 'globalasias' in C:
        key = json.load(open(os.path.join(os.path.dirname(out_dir.rstrip('/')), 'key', 'globalasias_corrected.json'), encoding='utf-8'))
        P = C['globalasias']['places']; found = 0
        for k in key['items']:
            hit = next((p for p in P if p['page'] == k['page'] and [p['page'], p['mcid']] in k['mcids']
                        and (k['text'] in p['text'] or p['text'] in k['text'])), None)
            if hit: found += 1
            else:
                m = k['mcids'][0][1]
                hit = {'page': k['page'], 'mcid': m, 'first': 0, 'last': max(len(k['text']) - 1, 0), 'text': k['text'], 'form': k['text'],
                       'class': ['cjk:han_only' if not scripts.KANA.search(k['text']) else 'cjk:mixed'], 'w0': None, 'w1': None}
            add('ga', k['key'], 'globalasias', hit, accept=k['accept'])
            items[-1]['raw'] = k['raw']; items[-1]['ga_id'] = k['id']; items[-1]['found_by_detector'] = hit.get('w0') is not None
        recall = found
    # 2. silver
    for name, cand in C.items():
        for src, lst in silver(name, cand).items():
            seen, picked = set(), []
            for p, key in rnd.sample(lst, len(lst)):
                if p['form'] in seen: continue
                seen.add(p['form']); picked.append((p, key))
                if len(picked) >= PER_SOURCE: break
            for p, key in picked: add(f'silver:{src}', key, name, p)
    # 3. synthetic: kana phrases (always Japanese) and corrected globalasias forms, in a neutral sentence
    syn = []
    for name, cand in C.items():
        syn += [(p, 'ja') for p in cand['places'] if p['class'] == ['cjk:kana'] and len(p['form']) >= 2]
    rnd.shuffle(syn)
    for n, (p, key) in enumerate(syn[:10]):
        words = ['In', 'the', 'source', 'the', 'phrase', p['text'], 'is', 'quoted', 'without', 'a', 'translation.']
        add('synthetic', key, 'synthetic', {**p, 'page': 9000 + n, 'mcid': 0, 'first': 0, 'last': len(p['text']) - 1, 'w0': 5, 'w1': 5}, synthetic_words=words)
    # 4. no evidence: Han-only with nothing nearby. The items of an earlier build come first (the spot-check sheet keeps
    #    them), then up to NOKEY_PER_BOOK forms per book, drawn with their own seed.
    for it in earlier_nokey:
        if it['book'] in C: add('nokey', None, it['book'], {k: it[k] for k in ('page', 'mcid', 'first', 'last', 'text', 'form', 'class', 'w0', 'w1')} | {'italic': it['italic']})
    r2 = random.Random(119)
    for name in NOKEY_BOOKS:
        if name not in C: continue
        ne = no_evidence(C[name]); r2.shuffle(ne); seen = {it['form'] for it in items if it['source'] == 'nokey' and it['book'] == name}
        for p in ne:
            if p['form'] in seen or len(seen) >= NOKEY_PER_BOOK: continue
            seen.add(p['form']); add('nokey', None, name, p)
    json.dump({'built': time.strftime('%Y-%m-%dT%H:%M:%S'), 'books': {n: os.path.basename(p) for n, p in books.items()},
               'detector_recall_globalasias': f'{recall} of 42' if 'globalasias' in C else None, 'items': items},
              open(os.path.join(out_dir, 'items.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_requests(out_dir, C, items)
    return items

def item_requests(C, items, which, ctx=None):
    """Requests for the chosen items, one batch per book (each book its own header), forms as langreq builds them with
    context ctx (langreq.CTX). A masked-clue item carries its own page of words (its reading removed): those go in a batch
    of their own per book, each on a page of its own."""
    out = []
    by_book = collections.defaultdict(list)
    for it in items:
        if which(it): by_book[(it['book'], it.get('kind') == 'masked')].append(it)
    for (book, is_masked), its in by_book.items():
        if book == 'synthetic':
            words = {str(it['page']): it['words'] for it in its}; meta = {'title': 'Synthetic sentences', 'language': 'en'}
        elif is_masked:
            words = {str(it['page']): it['words'] for it in its}
            meta = {'title': C[book].get('title') or book, 'language': C[book].get('language') or 'en'}
        else:
            words = C[book]['words']; meta = {'title': C[book].get('title') or book, 'language': C[book].get('language') or 'en'}
        fs = [{'id': it['id'], 'form': it['form'], 'group': langreq.group_of(it['class']), 'class': it['class'], 'italic_any': it['italic'],
               'roman_any': not it['italic'], 'places': [{k: it[k] for k in ('page', 'mcid', 'first', 'last', 'text', 'w0', 'w1')} | {'italic': it['italic']}]}
              for it in its]
        for r in langreq.requests(meta, fs, words, ctx=ctx):
            out.append({'book': book, 'request': r})
    return out

def book_requests(C, name):
    cand = C[name]; fs = langreq.forms(cand['places'])
    return fs, [{'book': name, 'request': r} for r in langreq.requests({'title': cand.get('title') or name, 'language': cand.get('language') or 'en'}, fs, cand['words'])]

def prices():
    """Live prices from OpenRouter's public model list (no key, no book text): {model: (in, out) $ per token}."""
    try:
        with urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=30) as r: data = json.load(r)['data']
        SUPPORTED.update({m['id']: m.get('supported_parameters') for m in data if m['id'] in MODELS})
        return {m['id']: (float(m['pricing']['prompt']), float(m['pricing']['completion'])) for m in data if m['id'] in MODELS}, 'live'
    except Exception as e:
        return {'anthropic/claude-sonnet-5.5': (2e-6, 10e-6), 'anthropic/claude-opus-5.5': (4e-6, 20e-6), 'anthropic/claude-haiku-5.5': (1e-7, 5e-7)}, f'ASSUMED ({type(e).__name__})'

NO_REASONING = False       # send --no-reasoning
SUPPORTED = {}             # model -> supported_parameters, from the same public list
OUT_PER_ITEM = 75          # tokens per decision: {"id":"…","lang":"ja-Latn","confidence":"high","why":"language"}, + a note now and then

def write_requests(out_dir, C, items):
    prompt = open(PROMPT, encoding='utf-8').read()
    rq = os.path.join(out_dir, 'requests'); os.makedirs(rq, exist_ok=True)
    sets = {'tune': lambda it: it['half'] == 'tune' and it['source'] != 'nokey', 'score': lambda it: it['half'] == 'score' and it['source'] != 'nokey',
            'nokey': lambda it: it['source'] == 'nokey'}
    summary = {}
    for name, pred in sets.items():
        reqs = item_requests(C, items, pred)
        json.dump(reqs, open(os.path.join(rq, f'{name}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        summary[name] = {'requests': len(reqs), 'items': sum(len(r['request']['items']) for r in reqs),
                         'snippets': sum(len(r['request']['snippets']) for r in reqs), 'in_tokens': sum(langreq.size(r['request'], prompt) for r in reqs)}
    if 'cadaverous' in C:
        fs, reqs = book_requests(C, 'cadaverous')
        json.dump(reqs, open(os.path.join(rq, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        summary['book'] = {'requests': len(reqs), 'items': sum(len(r['request']['items']) for r in reqs),
                           'snippets': sum(len(r['request']['snippets']) for r in reqs), 'in_tokens': sum(langreq.size(r['request'], prompt) for r in reqs),
                           'places': sum(len(f['places']) for f in fs), 'words_sent': sum(len(s['text'].split()) for r in reqs for s in r['request']['snippets'])}
    pr, how = prices()
    lines = [f'# Paid test estimate ({time.strftime("%Y-%m-%d %H:%M")}; prices {how})', '',
             f'Prompt `language_v1.md`: {int(langreq.tokens(prompt))} tokens. Output: {OUT_PER_ITEM} tokens per item.', '',
             '| set | requests | items | snippets | input tokens | ' + ' | '.join(f'{m.split("/")[-1]} $' for m in MODELS) + ' |', '|---|---:|---:|---:|---:|' + '---:|' * len(MODELS)]
    cost = {}
    for name, s in summary.items():
        c = {m: s['in_tokens'] * pr[m][0] + s['items'] * OUT_PER_ITEM * pr[m][1] for m in MODELS if m in pr}
        cost[name] = c
        lines.append(f'| {name} | {s["requests"]} | {s["items"]} | {s["snippets"]} | {s["in_tokens"]:,} | ' + ' | '.join(f'{c.get(m, 0):.3f}' for m in MODELS) + ' |')
    json.dump({'summary': summary, 'prices': {m: list(v) for m, v in pr.items()}, 'prices_from': how, 'cost': cost},
              open(os.path.join(out_dir, 'estimate.json'), 'w'), indent=1)
    open(os.path.join(out_dir, 'estimate.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

def build_v2(out_dir, books):
    """The paid check's requests (07; review 06 M4 and 05 §8.1): the same test items as requests/ (only the prompt changes:
    language_v2.md, the form echo and shorter replies), and each named book whole with title growth (langcands grow=True)
    and one-character Han grouping (langreq.forms group=True), in requests-v2/book-<name>.json, with v1's whole-book
    requests beside them for the counts."""
    cache = os.path.join(out_dir, 'cand-v2'); os.makedirs(cache, exist_ok=True)
    rq = os.path.join(out_dir, 'requests-v2'); os.makedirs(rq, exist_ok=True)
    for st in ('tune', 'score', 'nokey'): shutil.copyfile(os.path.join(out_dir, 'requests', f'{st}.json'), os.path.join(rq, f'{st}.json'))
    prompt = open(PROMPT_V2, encoding='utf-8').read(); summary = {}
    for name, pdf in books.items():
        f = os.path.join(cache, f'{name}.json')
        if os.path.exists(f): cand = json.load(open(f, encoding='utf-8'))
        else:
            cand = langcands.book(plpages.Pages(pdf), doc_lang=DOC_LANG.get(name), grow=True)
            json.dump(cand, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
        v1 = candidates(name, pdf, os.path.join(out_dir, 'cand'))
        meta = {'title': v1.get('title') or name, 'language': DOC_LANG.get(name) or 'en'}
        fs = langreq.forms(cand['places'], group=True)
        reqs = [{'book': name, 'request': r} for r in langreq.requests(meta, fs, cand['words'])]
        json.dump(reqs, open(os.path.join(rq, f'book-{name}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        fs1 = langreq.forms(v1['places'])
        summary[name] = {'forms_v1': len(fs1), 'forms_v2': len(fs), 'places_v1': sum(len(x['places']) for x in fs1), 'places_v2': sum(len(x['places']) for x in fs),
                         'requests': len(reqs), 'in_tokens': sum(langreq.size(r['request'], prompt) for r in reqs),
                         'titles_grown': sum(1 for p in cand['places'] if 'title' in p['class'])}
    for st in ('tune', 'score', 'nokey'):
        reqs = json.load(open(os.path.join(rq, f'{st}.json'), encoding='utf-8'))
        summary[st] = {'requests': len(reqs), 'items': sum(len(r['request']['items']) for r in reqs), 'in_tokens': sum(langreq.size(r['request'], prompt) for r in reqs)}
    json.dump(summary, open(os.path.join(out_dir, 'estimate-v2.json'), 'w'), indent=1)
    print(json.dumps(summary, indent=1))

# ---- round 15 (review 14, item 1, as Patrick widened it): masked-clue Han-only items, the hard places, variants
HANGUL = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')
KANA_ = re.compile(r'[\u3040-\u30ff]')
RR = re.compile(r'(?i)eo|eu')                                 # Revised Romanization's vowels, never Hepburn's or pinyin's

TONE_OTHER = re.compile(r'[áǎàéěèíǐìóǒòúǔùǖǘǚǜ]')       # pinyin tones Hepburn never writes
def reading_of(w, subj, toned=False):
    """The language a piece beside a Han-only place proves, or None: kana or a Hepburn word (ja); pinyin (zh); hangul, a
    McCune-Reischauer word with breves, or a Revised Romanization word in a book on Korea (ko). A word with Hepburn
    macrons that also fits pinyin ("dōu", "soba-manjū") is Japanese, unless the book writes pinyin with tone marks
    (toned: then it is not decided); a romanization
    without marks proves zh only when it is long, not English and not Japanese in shape; breves prove ko only in a book
    on Korea (Wade-Giles uses them for Chinese)."""
    if KANA_.search(w): return 'ja'
    if HANGUL.search(w): return 'ko'
    c = latin_core(w); lw = c.lower(); bare = toneless(lw).replace("'", '').replace('’', '')
    if not c or not bare.replace('-', '').isalpha(): return None
    shape = bool(PINYIN.match(bare.replace('-', ''))); pin = shape and not langcands.in_english(lw)
    hep = bool(HEPBURN_ONLY.search(lw) and JA_SYL.match(lw.replace('-', '')) and not IAST.search(lw) and not TONE_OTHER.search(lw))
    if hep and shape: return None if toned else 'ja'
    if hep: return 'ja'
    if subj == 'korea' and (BREVE.search(c) and not TONE.search(c) or (RR.search(lw) and not langcands.in_english(lw) and len(lw) > 3)): return 'ko'
    if subj == 'korea': return None                 # McCune-Reischauer without breves looks like pinyin ("minyu bangbon")
    if pin and not BREVE.search(c) and (TONE_OTHER.search(lw) or (len(bare) > 3 and not JA_SYL.match(bare.replace('-', '')))): return 'zh'
    return None

PUNCT_ONLY = re.compile(r'^[\W_]+$')
def beside(pw, w0, w1, subj, toned=False):
    """{index: language} of the reading directly beside a place: the run of reading pieces that ends right before it
    (a piece of punctuation alone may sit between), else the kana or hangul right after it, at most 3 pieces. A
    reading two pieces away that belongs to a neighbouring entry (a glossary's "soju 소주 su 酥") is never taken."""
    for step, start in ((-1, w0 - 1), (1, w1 + 1)):
        i, got = start, {}
        if 0 <= i < len(pw) and PUNCT_ONLY.match(pw[i]): i += step
        while 0 <= i < len(pw) and len(got) < 3:
            r = reading_of(pw[i], subj, toned)
            if step == 1 and r and not (KANA_.search(pw[i]) or HANGUL.search(pw[i])): r = None   # a romanization after: the next entry's
            if not r: break
            got[i] = r; i += step
        if got: return got
    return {}

def subject_of(cand):
    """A book's subject from the readings beside its Han-only places (for books outside SUBJECT): the most common."""
    W, c = cand['words'], collections.Counter()
    for p in cand['places']:
        if 'cjk:han_only' not in p['class'] or p.get('w0') is None: continue
        pw = W.get(str(p['page'])) or []
        for w in pw[max(0, p['w0'] - 3):p['w0']] + pw[p['w1'] + 1:p['w1'] + 4]:
            r = reading_of(w, None) or ('ko' if HANGUL.search(w) else None)
            if r: c[r] += 1
    return {'ja': 'japan', 'zh': 'china', 'ko': 'korea'}.get(c.most_common(1)[0][0]) if c else None

NEAR, WIDE = 15, 60          # "within 15 words" for the hard places; 60: the widest context tested

def clue_near(pw, w0, w1, span, subj):
    return any(reading_of(w, subj) for w in pw[max(0, w0 - span):w0] + pw[w1 + 1:w1 + 1 + span])

def masked(name, cand, subj):
    """(items, hard, share): masked-clue items (a Han-only place whose reading beside it, within 3 pieces, proves one
    language; that reading's pieces removed from a copy of the page's words: test input only), the hard places (no
    reading within NEAR pieces), and the book's shares of Han-only places with a reading within 3 and within NEAR."""
    W = cand['words']; out, hard = [], []; n = n3 = n15 = 0
    toned = sum(1 for pw in W.values() for w in pw if TONE_OTHER.search(w)) > 20       # writes pinyin with tone marks
    for p in cand['places']:
        if 'cjk:han_only' not in p['class'] or len(p['class']) != 1 or p.get('w0') is None: continue
        pw = W.get(str(p['page'])) or []
        if p['w1'] >= len(pw): continue
        n += 1
        idx = [i for i in list(range(max(0, p['w0'] - 3), p['w0'])) + list(range(p['w1'] + 1, min(len(pw), p['w1'] + 4)))]
        if any(reading_of(pw[i], subj) for i in idx): n3 += 1
        rs = beside(pw, p['w0'], p['w1'], subj, toned)
        if clue_near(pw, p['w0'], p['w1'], NEAR, subj): n15 += 1
        else: hard.append(p)
        langs = set(rs.values())
        if len(langs) != 1: continue                          # none, or two languages beside it: not settled
        key = langs.pop()
        if key == 'ja' and subj == 'korea' and not any(KANA_.search(pw[i]) for i in rs): continue
        if key == 'ko' and subj == 'japan' and not any(HANGUL.search(pw[i]) for i in rs): continue
        mw = [w for i, w in enumerate(pw) if i not in rs]
        shift = sum(1 for i in rs if i < p['w0'])
        q = {**p, 'w0': p['w0'] - shift, 'w1': p['w1'] - shift}
        out.append({'p': q, 'key': key, 'reading': [pw[i] for i in sorted(rs)], 'masked_words': mw,
                    'other_clue_15': clue_near(mw, q['w0'], q['w1'], NEAR, subj), 'other_clue_60': clue_near(mw, q['w0'], q['w1'], WIDE, subj),
                    'printed': ' '.join(pw[max(0, p['w0'] - 6):p['w1'] + 7])})
    return out, hard, {'han_only_places': n, 'reading_within_3': n3, 'reading_within_15': n15}

CLASS_OF = {'kana_next_to_han': 'Han-only', 'hepburn_next_to_han': 'Han-only', 'pinyin_next_to_han': 'Han-only', 'hangul_next_to_han': 'Han-only',
            'hepburn_marks': 'romanized', 'iast_marks': 'romanized', 'tone_pinyin': 'romanized', 'breve_korean': 'romanized',
            'breve_wade_giles': 'romanized', 'yale_italic': 'romanized', 'okina_hawaiian': 'Hawaiian'}
def kind_class(it):
    """(kind, class) of an item for the round-15 tables."""
    src = it['source'].split(':')
    if src[0] == 'masked': return 'masked', 'masked Han-only'
    if src[0] == 'silver': return 'silver', CLASS_OF.get(src[1], 'other')
    if src[0] == 'synthetic': return 'synthetic', 'kana'
    if src[0] == 'nokey': return 'nokey', 'Han-only'
    f = it['form']
    cl = 'Han-only' if not KANA_.search(f) and re.search(r'[\u3400-\u9fff]', f) else 'kana' if KANA_.search(f) else 'other'
    return 'ga', cl

# Books left out of the masked items: a body in Chinese or Japanese (its Han-only places are the body text, so the key is
# the document's language), and the Ryukyu book (kana or romanization beside its characters may be Okinawan)
MASK_SKIP = {'tclt7': 'body in Chinese', 'mohr-zen': 'body in Japanese', 'yao-history': 'body in Chinese', 'yao-intelligences': 'body in Chinese',
             'yao-popularizing': 'body in Chinese', 'ktimes-1990': 'body in Korean', 'ryukyu': 'readings may be Okinawan'}
CANTONESE = {'sojourners'}          # Chinese in Hawaii: many readings are Cantonese, so a zh key accepts yue too
def build_exp(out_dir, old_dir, per_lang=140, cap=0.25, drop=()):
    """Round 15's item set: the earlier items (kind and class marked) and masked-clue Han-only items from every cached
    book in out_dir/cand, at most per_lang per language and no book over `cap` of the masked set; one place per form and
    book, places with no other reading within NEAR pieces first. Writes items.json, hard.json (the hard places) and
    shares.json (per book). Free, no network."""
    old = json.load(open(os.path.join(old_dir, 'items.json'), encoding='utf-8'))['items']
    items = []
    for it in old:
        k, c = kind_class(it)
        items.append({**it, 'kind': k, 'cls': c, 'lang': (it.get('key') or '').split('|')[0].split('-')[0] or None})
    cache = os.path.join(out_dir, 'cand'); pool = collections.defaultdict(list); hard = []; shares = {}
    for f in sorted(os.listdir(cache)):
        name = f[:-5]; cand = json.load(open(os.path.join(cache, f), encoding='utf-8'))
        subj = SUBJECT.get(name) or subject_of(cand)
        got, hd, sh = masked(name, cand, subj)
        shares[name] = {**sh, 'subject': subj}
        hard += [{'book': name, **{k: p[k] for k in ('page', 'mcid', 'first', 'last', 'text', 'form', 'class', 'w0', 'w1')}} for p in hd]
        seen = set()
        if name in MASK_SKIP: shares[name]['left_out'] = MASK_SKIP[name]; continue
        for x in got:
            if (name, x['key']) in drop or x['p']['form'] in seen: continue
            seen.add(x['p']['form']); pool[x['key']].append((name, x))
    rnd = random.Random(1515); chosen = []
    total_target = sum(min(per_lang, len(v)) for v in pool.values())
    book_cap = max(1, int(cap * total_target))
    per_book = collections.Counter()
    for lang in sorted(pool):
        cands = pool[lang][:]; rnd.shuffle(cands)
        cands.sort(key=lambda t: (t[1]['other_clue_15'], t[1]['other_clue_60']))       # clean ones first (stable: shuffled within)
        n = 0
        by_book = collections.defaultdict(list)
        for name, x in cands: by_book[name].append(x)
        while n < per_lang and any(by_book.values()):           # round robin over books, so no book dominates
            for name in sorted(by_book, key=lambda b: per_book[b]):
                if not by_book[name] or n >= per_lang: continue
                if per_book[name] >= book_cap: by_book[name] = []; continue
                x = by_book[name].pop(0); chosen.append((name, x)); per_book[name] += 1; n += 1
    for n, (name, x) in enumerate(chosen):
        p = x['p']; iid = f'mask-{name[:8]}-{p["page"]}-{p["mcid"]}-{p["first"]}'
        items.append({'id': iid, 'source': 'masked', 'kind': 'masked', 'cls': 'masked Han-only', 'lang': x['key'], 'book': name,
                      'page': 200000 + n, 'orig_page': p['page'], 'mcid': p['mcid'], 'first': p['first'], 'last': p['last'],
                      'text': p['text'], 'form': p['form'], 'class': p['class'], 'italic': p.get('italic', False), 'w0': p['w0'], 'w1': p['w1'],
                      'key': x['key'], 'accept': [x['key']] + (['yue'] if x['key'] == 'zh' and name in CANTONESE else []), 'half': half(iid), 'words': x['masked_words'], 'reading': x['reading'],
                      'printed': x['printed'], 'other_clue_15': x['other_clue_15'], 'other_clue_60': x['other_clue_60']})
    json.dump({'built': time.strftime('%Y-%m-%dT%H:%M:%S'), 'book_cap': book_cap, 'per_lang': per_lang, 'items': items},
              open(os.path.join(out_dir, 'items.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(hard, open(os.path.join(out_dir, 'hard.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(shares, open(os.path.join(out_dir, 'shares.json'), 'w'), indent=1)
    m = [it for it in items if it['kind'] == 'masked']
    print('masked:', collections.Counter((it['lang'], it['half']) for it in m), 'books:', collections.Counter(it['book'] for it in m))
    return items

def exp_requests(out_dir, variant, ctx, halves=('score',)):
    """One variant's request set (requests/<variant>.json): every keyed item of the given halves (masked included), built
    with context ctx. The estimate comes from these requests' own text (langreq.size)."""
    items = json.load(open(os.path.join(out_dir, 'items.json'), encoding='utf-8'))['items']
    C = {}
    for b in {it['book'] for it in items if it['book'] != 'synthetic'}:
        C[b] = json.load(open(os.path.join(out_dir, 'cand', f'{b}.json'), encoding='utf-8')); C[b]['language'] = DOC_LANG.get(b) or 'en'
    reqs = item_requests(C, items, lambda it: it['half'] in halves and it['kind'] != 'nokey', ctx)
    rq = os.path.join(out_dir, 'requests'); os.makedirs(rq, exist_ok=True)
    json.dump(reqs, open(os.path.join(rq, f'{variant}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return reqs

def key_sheet(out_dir, n=40, seed=40):
    """The masked-clue key sheet: n keys drawn at random, stratified by language and book, each with the place as
    printed, the reading that set the key, and the key, for a reader of Japanese, Chinese and Korean (key-sheet.csv)."""
    import csv
    items = [it for it in json.load(open(os.path.join(out_dir, 'items.json'), encoding='utf-8'))['items'] if it['kind'] == 'masked']
    rnd = random.Random(seed); by = collections.defaultdict(list)
    for it in items: by[(it['lang'], it['book'])].append(it)
    for v in by.values(): rnd.shuffle(v)
    langs = sorted({it['lang'] for it in items}); per = {l: max(1, round(n * sum(1 for it in items if it['lang'] == l) / len(items))) for l in langs}
    share = {l: sum(1 for it in items if it['lang'] == l) for l in langs}
    while sum(per.values()) < n: per[max(langs, key=lambda l: (share[l] - per[l] * len(items) / n, l))] += 1   # rounding: n keys in all
    pick = []
    for l in langs:
        cells = [k for k in sorted(by) if k[0] == l]; i = 0
        while sum(1 for it in pick if it['lang'] == l) < per[l] and any(by[k] for k in cells):
            k = cells[i % len(cells)]; i += 1
            if by[k]: pick.append(by[k].pop())
    pick = pick[:n]
    with open(os.path.join(out_dir, 'key-sheet.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['n', 'item', 'book', 'form', 'place as printed', 'reading that set the key', 'key', 'reader: key right? (yes / no / cannot tell)', 'reader: note'])
        for k, it in enumerate(pick, 1): w.writerow([k, it['id'], it['book'], it['form'], it['printed'], ' '.join(it['reading']), it['key'], '', ''])
    return pick

def hard_items(out_dir, n=100, seed=100):
    """Up to n of the real hard places (Han-only, no reading within NEAR pieces), stratified by book, one per form and
    book, as items with no key (kind 'hard'): sent once on the adopted setup for the second reader sheet."""
    hard = json.load(open(os.path.join(out_dir, 'hard.json'), encoding='utf-8'))
    rnd = random.Random(seed); by = collections.defaultdict(list); seen = set()
    for p in hard:
        if p['book'] in MASK_SKIP or (p['book'], p['form']) in seen: continue
        seen.add((p['book'], p['form'])); by[p['book']].append(p)
    for v in by.values(): rnd.shuffle(v)
    pick, i, books = [], 0, sorted(by)
    while len(pick) < n and any(by.values()):
        b = books[i % len(books)]; i += 1
        if by[b]: pick.append(by[b].pop())
    out = [{'id': f'hard-{p["book"][:8]}-{p["page"]}-{p["mcid"]}-{p["first"]}', 'source': 'hard', 'kind': 'hard', 'cls': 'hard Han-only', 'lang': None,
            'book': p['book'], **{k: p[k] for k in ('page', 'mcid', 'first', 'last', 'text', 'form', 'class', 'w0', 'w1')}, 'italic': False,
            'key': None, 'accept': [], 'half': 'hard'} for p in pick]
    json.dump(out, open(os.path.join(out_dir, 'hard-items.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return out

# ---- sending (paid; only on Patrick's OK)
def send(out_dir, model, run, which, cap, prompt_file=None, req_dir='requests', ledger_name='spend.json'):
    key = None
    for d in [PIPE, os.path.dirname(PIPE)]:
        f = os.path.join(d, '.env')
        if os.path.exists(f):
            for line in open(f):
                if line.startswith('OPENROUTER_API_KEY='): key = line.split('=', 1)[1].strip().strip('"\'')
    if not key: sys.exit('no OPENROUTER_API_KEY in .env')
    prompt = open(prompt_file or PROMPT, encoding='utf-8').read()
    reqs = json.load(open(os.path.join(out_dir, req_dir, f'{which}.json'), encoding='utf-8'))
    ledger_f = os.path.join(out_dir, ledger_name)
    ledger = json.load(open(ledger_f)) if os.path.exists(ledger_f) else {'cap': cap, 'calls': []}
    spent = sum(c.get('cost') or 0 for c in ledger['calls'])
    pr, how = prices()
    if how != 'live' or SUPPORTED.get(model) is None: sys.exit(f'refused: OpenRouter\'s model list not read ({how}), so the request\'s parameters cannot be checked')
    pi, po = pr[model]
    worst = sum(langreq.size(r['request'], prompt) * pi + (len(r['request']['items']) * 100 + 300) * po for r in reqs)
    if spent + worst > cap: print(f'note: ${spent:.2f} spent + ${worst:.2f} worst case for the whole set passes the ${cap:.2f} cap: each request is checked, and the set stops before one could pass it')
    od = os.path.join(out_dir, 'replies', model.split('/')[-1], f'run{run}', which); os.makedirs(od, exist_ok=True)
    print(f'{which} on {model}, run {run}: {len(reqs)} requests, worst case ${worst:.2f}; ${spent:.2f} spent of the ${cap:.2f} cap so far')
    for n, r in enumerate(reqs, 1):
        mt = len(r['request']['items']) * 100 + 300
        e1 = langreq.size(r['request'], prompt) * pi + mt * po
        spent_now = sum(c.get('cost') or 0 for c in ledger['calls'])
        if spent_now + e1 > cap: sys.exit(f'stopped before request {n}: ${spent_now:.2f} spent + ${e1:.2f} worst case would pass the ${cap:.2f} cap')
        print(f'  request {n}/{len(reqs)}: {len(r["request"]["items"])} items, estimate up to ${e1:.3f} … ', end='', flush=True)
        b = langreq.body(r['request'], model, prompt, mt, SUPPORTED.get(model)); b['usage'] = {'include': True}
        if NO_REASONING: b['reasoning'] = {'enabled': False}     # Haiku 5.5 reasons by default, and its reasoning filled max_tokens
        json.dump(b, open(os.path.join(od, f'{n:03d}.request.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(b).encode(),
                                     headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=600) as resp: rep = json.load(resp)
        json.dump(rep, open(os.path.join(od, f'{n:03d}.reply.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        cost = (rep.get('usage') or {}).get('cost')
        ledger['calls'].append({'model': model, 'run': run, 'set': which, 'n': n, 'cost': cost, 'at': time.strftime('%Y-%m-%dT%H:%M:%S')})
        json.dump(ledger, open(ledger_f, 'w'), indent=1)
        print(f'${cost:.4f}' if isinstance(cost, (int, float)) else 'cost not given')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'build-v2', 'send']); ap.add_argument('out_dir'); ap.add_argument('books', nargs='*')
    ap.add_argument('--model'); ap.add_argument('--run', type=int, default=1); ap.add_argument('--set', default='tune'); ap.add_argument('--cap', type=float, default=10.0)
    ap.add_argument('--prompt', default=None, help='a prompt file instead of language_v1.md (the paid check: language_v2.md)')
    ap.add_argument('--requests', default='requests', help='the folder of request sets (the paid check: requests-v2)')
    ap.add_argument('--no-reasoning', action='store_true', help="ask the model not to reason first (reasoning enabled false)")
    ap.add_argument('--ledger', default='spend.json', help='the ledger file and its own cap (the paid check: spend-check.json)')
    a = ap.parse_args(); NO_REASONING = a.no_reasoning
    if a.cmd == 'build': build(a.out_dir, dict(b.split('=', 1) for b in a.books))
    elif a.cmd == 'build-v2': build_v2(a.out_dir, dict(b.split('=', 1) for b in a.books))
    else: send(a.out_dir, a.model, a.run, a.set, a.cap, a.prompt, a.requests, a.ledger)
