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
PINYIN = re.compile(r"(?i)^(?:(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?(?:iang|iong|uang|ang|eng|ing|ong|ian|iao|uai|uan|üan|ai|ei|ao|ou|an|en|in|un|ün|ia|ie|iu|ua|uo|ui|üe|er|a|o|e|i|u|ü)(?:n|ng)?)+$")
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

def item_requests(C, items, which):
    """Requests for the chosen items, one batch per book (each book its own header), forms as langreq builds them."""
    out = []
    by_book = collections.defaultdict(list)
    for it in items:
        if which(it): by_book[it['book']].append(it)
    for book, its in by_book.items():
        if book == 'synthetic':
            words = {str(it['page']): it['words'] for it in its}; meta = {'title': 'Synthetic sentences', 'language': 'en'}
        else:
            words = C[book]['words']; meta = {'title': C[book].get('title') or book, 'language': C[book].get('language') or 'en'}
        fs = [{'id': it['id'], 'form': it['form'], 'group': langreq.group_of(it['class']), 'class': it['class'], 'italic_any': it['italic'],
               'roman_any': not it['italic'], 'places': [{k: it[k] for k in ('page', 'mcid', 'first', 'last', 'text', 'w0', 'w1')} | {'italic': it['italic']}]}
              for it in its]
        for r in langreq.requests(meta, fs, words):
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
    ap.add_argument('--ledger', default='spend.json', help='the ledger file and its own cap (the paid check: spend-check.json)')
    a = ap.parse_args()
    if a.cmd == 'build': build(a.out_dir, dict(b.split('=', 1) for b in a.books))
    elif a.cmd == 'build-v2': build_v2(a.out_dir, dict(b.split('=', 1) for b in a.books))
    else: send(a.out_dir, a.model, a.run, a.set, a.cap, a.prompt, a.requests, a.ledger)
