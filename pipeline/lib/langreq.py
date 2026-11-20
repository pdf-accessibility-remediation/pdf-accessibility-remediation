"""langreq.py: the language step's requests and replies (#118, language tagging). Builds the requests from the audit's
candidates (lib/langcands.py), counts their size, reads a model's reply, and turns its decisions into the work order's
`language_parts`. No network here: the caller sends (tools/lang_test.py for the paid test; name_languages.py later).

    langreq.forms(places, skip=...)                 -> [form]: places grouped by printed form and class
    langreq.requests(book, forms, words, ...)       -> [request]: each with its snippets and items, ready to send
    langreq.body(request, model, prompt, max_tokens)-> the OpenRouter request body (temperature as decide.py sends it)
    langreq.size(request, prompt)                   -> estimated input tokens
    langreq.parse(text, ids)                        -> (decisions {id: decision}, dropped [{id, why}])
    langreq.to_parts(forms, decisions)              -> language_parts {'parts': [...]}, as apply.py reads them

What leaves the machine (review 02, M11): for each item its printed form, class, italic flag and number of places, and
the context CTX sets around up to SNIPPETS_PER_FORM of its places (span(); docs/languages.md). Each snippet is sent once
per request, with every candidate in it marked [[id|text]]. Kana and hangul runs are not sent: their language is known
locally (lib/scripts.py).
"""
import json, re, collections, unicodedata
from lib import langtag, models

# The context sent around a place (review 14, item 1; measured in round 15, docs/languages.md):
#   unit      'pieces': every space-separated piece counts ("),", "52," and a spaceless run of Chinese characters each
#             count one); 'words': only a piece with a letter or a CJK character counts, numbers and punctuation ride along
#   size      counted pieces on each side (window mode)
#   mode      'window': size on each side; 'sentence': the place's sentence, one before and one after, at most `cap` on
#             each side
#   cjk_cap   a piece of CJK characters with no spaces longer than this keeps only the characters nearest the place
#             (None: whole), so no piece carries more than about a sentence
#   join      True: windows that meet on a page are sent as one snippet; False: each place's window on its own
#   item_snippets  True: each item lists the numbers of the snippets that hold it ("s": [1, 4])
# Adopted 2026-11-14 (Patrick, handoff 17 §3): 10 words each side (numbers and punctuation ride along), the
# 40-character CJK cap, joined snippets with each item's snippet numbers. On 473 test items, 3 runs each: fewer wrong
# answers on the masked-clue items than 15 pieces (12 against 19), a few more left for a person (11 against 3), the same
# cost; the differences are small (3 and 2 items). 30 words and sentence mode gave more wrong answers (round 15).
CTX = {'unit': 'words', 'size': 10, 'mode': 'window', 'cap': 60, 'cjk_cap': 40, 'join': True, 'item_snippets': True}
CONTEXT = CTX['size']           # kept for callers that read the old name
SNIPPETS_PER_FORM = 2           # contexts per form: the first place, and one more (italic vs roman, or a later chapter)
FORMS_PER_REQUEST = 150
LOCAL = ('cjk:kana', 'cjk:hangul')                     # decided locally (lib/scripts.py), never sent
ORDER = ['existing', 'cjk', 'marks', 'hawaiian', 'script', 'passage', 'accented', 'latin', 'unknown']   # request order (review 02, L4)
WHY = {'language', 'name', 'english', 'indeterminate', 'unsure', 'varies'}
CONF = {'high', 'medium', 'low'}

def group_of(classes):
    c = classes[0] if classes else 'unknown'
    for g in ORDER:
        if c == g or c.startswith(g + ':') or c.startswith(g): return g
    return 'unknown'

def group_han(places):
    """Adjacent one-character Han places on a line (each drawn as its own run, as OCR or a typesetter may: ryukyu's
    bibliography) read as one form, so 年, 前 and 本 are judged together as the word they spell (05 §8.1). The places stay
    one per run; only their form is the joined text."""
    one = lambda p: 'cjk:han_only' in p['class'] and len(p['class']) == 1 and len(p['text'].strip()) == 1 and p.get('w0') is not None
    ps = sorted(places, key=lambda p: (p['page'], p.get('w0') if p.get('w0') is not None else -1, p['mcid'], p['first']))
    out, i = [], 0
    while i < len(ps):
        j = i
        while one(ps[i]) and j + 1 < len(ps) and one(ps[j + 1]) and ps[j + 1]['page'] == ps[j]['page'] and ps[j + 1]['w0'] == ps[j]['w1'] + 1: j += 1
        if j > i:
            form = ''.join(p['text'].strip() for p in ps[i:j + 1])
            out += [{**p, 'form': form, 'class': ['cjk:han_only']} for p in ps[i:j + 1]]
        else: out.append(ps[i])
        i = j + 1
    return out

def forms(places, skip=LOCAL, unknown_italic_only=False, group=False):
    """Places grouped by (printed form, group): one decision per form. Each form keeps all its places. group: adjacent
    one-character Han places become one form first (group_han)."""
    by = collections.OrderedDict()
    if group: places = group_han(places)
    # a second half's place (#140, `half`) may come before its first half's (a lower MCID on the page): forms are met, and
    # so numbered, by their other places first, as before second halves were places
    for p in sorted(places, key=lambda p: bool(p.get('half'))):
        if any(c in skip for c in p['class']) and len(p['class']) == 1: continue
        g = group_of([c for c in p['class'] if c != 'passage'] or p['class'])
        if 'passage' in p['class']: g = 'passage'
        if unknown_italic_only and g == 'unknown' and not p.get('italic'): continue
        key = (p['form'], g)
        if 'existing' in p['class']: g = 'existing'; key = (p['form'], g, p.get('current'))
        f = by.setdefault(key, {'form': p['form'], 'group': g, 'class': sorted(set(p['class'])), 'places': [], 'italic_any': False, 'roman_any': False,
                                **({'current': p['current']} if p.get('current') else {})})
        f['places'].append(p); f['italic_any'] |= bool(p.get('italic')); f['roman_any'] |= not p.get('italic')
        if p.get('carried'): f['carried'] = p['carried'] if f.get('carried') in (None, p['carried']) else 'mixed'   # review 12, C
    out = list(by.values())
    out.sort(key=lambda f: (ORDER.index(f['group']) if f['group'] in ORDER else 99, f['places'][0]['page']))
    for i, f in enumerate(out, 1): f.setdefault('id', str(i))
    return out

def _contexts(f):
    """Up to SNIPPETS_PER_FORM places to show: the first, then one in the other type style or on a page far away."""
    ps = f['places']; pick = [ps[0]]
    if len(ps) > 1 and SNIPPETS_PER_FORM > 1:
        other = next((p for p in ps[1:] if bool(p.get('italic')) != bool(ps[0].get('italic'))), None) \
            or next((p for p in ps[1:] if abs(p['page'] - ps[0]['page']) > 20), None)
        if other: pick.append(other)
    return pick

_CJK = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af]')
_COUNTS = re.compile(r'[^\W\d_]')                                 # a letter or a CJK character
_END = re.compile(r'[.!?\u3002\uff01\uff1f]["\u201d\u2019\u00bb)\]\u300d\u300f]*$')   # . ! ? 。！？, closing quotes or brackets after
_ABBR = {'e.g.', 'i.e.', 'cf.', 'fl.', 'ca.', 'c.', 'vol.', 'vols.', 'no.', 'nos.', 'p.', 'pp.', 'ed.', 'eds.', 'trans.', 'mr.', 'mrs.',
         'dr.', 'st.', 'ch.', 'chap.', 'fig.', 'jr.', 'sr.', 'vs.', 'etc.', 'r.', 'd.', 'b.', 'ibid.', 'op.', 'cit.', 'jap.', 'chin.', 'kor.'}

def ctx_of(ctx=None): return {**CTX, **(ctx or {})}

def _ends(w):
    """A piece that ends a sentence: a final . ! ? 。！？ (closing quotes or brackets may follow), never an abbreviation, an
    initial ("N.") or a number ("52.")."""
    if not _END.search(w): return False
    core = w.lower().strip('"\u201c\u201d\u2018\u2019()[]')
    if core in _ABBR or re.fullmatch(r'[^\W\d_]\.', core) or re.fullmatch(r'[\d.,:–-]+', core): return False
    return True

def span(pw, w0, w1, ctx=None):
    """(a, b): the indexes of the first and last piece of a place's context on its page (pw: the page's pieces)."""
    c = ctx_of(ctx); n = len(pw)
    counts = (lambda w: True) if c['unit'] == 'pieces' else (lambda w: bool(_COUNTS.search(w)))
    def walk(size):
        a, k, i = w0, 0, w0 - 1
        while i >= 0 and k < size:
            if counts(pw[i]): k += 1
            a = i; i -= 1
        b, k, i = w1, 0, w1 + 1
        while i < n and k < size:
            if counts(pw[i]): k += 1
            b = i; i += 1
        return a, b
    if c['mode'] != 'sentence':
        return walk(c['size'])
    i = w0 - 1
    while i >= 0 and not _ends(pw[i]): i -= 1             # i: the end of the sentence before (or -1)
    if i >= 0:
        j = i - 1
        while j >= 0 and not _ends(pw[j]): j -= 1
        a = j + 1
    else: a = 0
    k = w1
    while k < n - 1 and not _ends(pw[k]): k += 1          # k: the end of the place's sentence
    m = k + 1
    while m < n - 1 and not _ends(pw[m]): m += 1
    b = min(m, n - 1) if k < n - 1 else n - 1
    ca, cb = walk(c['cap'])
    return max(a, ca), min(b, cb)

def _trim(w, keep_end, cap):
    """A spaceless CJK piece longer than cap: the cap characters nearest the place, '…' where it was cut."""
    if not cap or len(w) <= cap or not _CJK.search(w): return w
    return '…' + w[-cap:] if keep_end else w[:cap] + '…'

def _text(pw, a, b, marks, cap):
    """The snippet text of pieces a..b, each candidate inside marked [[id|text]] (overlapping marks: the first wins). A
    long CJK piece keeps the characters nearest its nearer mark: its end when the next mark is nearer (or it comes
    before the first), its start otherwise (review 16, L1: a piece between two marks once kept the far side)."""
    ms, k = [], a
    for m in sorted((m for m in marks if m[0] >= a and m[1] <= b), key=lambda m: m[0]):
        if m[0] >= k: ms.append(m); k = m[1] + 1
    def keep_end(x):
        prev = max((m[1] for m in ms if m[1] < x), default=None); nxt = min((m[0] for m in ms if m[0] > x), default=None)
        if nxt is None: return False
        return prev is None or nxt - x <= x - prev
    toks, k, ids = [], a, []
    for w0, w1, fid, text in ms:
        toks += [_trim(pw[x], keep_end(x), cap) for x in range(k, w0)]
        toks.append(f'[[{fid}|{text}]]'); ids.append(fid); k = w1 + 1
    toks += [_trim(pw[x], keep_end(x), cap) for x in range(k, b + 1)]
    return ' '.join(toks), ids

def place_text(p, words, ctx=None):
    """One place's context as the requests send it, the place in [brackets]: what the review page shows beside a form."""
    pw = words.get(str(p['page'])) or []
    if p.get('w0') is None or p['w0'] >= len(pw): return ''
    c = ctx_of(ctx); a, b = span(pw, p['w0'], p['w1'], c)
    left = [_trim(w, True, c['cjk_cap']) for w in pw[a:p['w0']]]; right = [_trim(w, False, c['cjk_cap']) for w in pw[p['w1'] + 1:b + 1]]
    return ' '.join(left + ['[' + ' '.join(pw[p['w0']:p['w1'] + 1]) + ']'] + right)

_MARK = re.compile(r'\[\[([^|\]]+)\|([^\]]*)\]\]')
def sent_contexts(reqs, ctx=None):
    """{form id: its first marked place in the requests as built, the other marks unmarked, the place in [brackets], cut
    to the context window}: what the review page shows, taken from the text actually sent (review 19, L1), so a long CJK
    piece is cut on the same side as in the request."""
    c = ctx_of(ctx); size = c['cap'] if c['mode'] == 'sentence' else c['size']
    counts = (lambda w: True) if c['unit'] == 'pieces' else (lambda w: bool(_COUNTS.search(w)))
    def keep(ws, n, from_end):
        out, k = [], 0
        for w in (reversed(ws) if from_end else ws):
            if k >= n: break
            out.append(w); k += counts(w)
        return list(reversed(out)) if from_end else out
    out = {}
    for r in reqs:
        for sn in r.get('snippets') or []:
            t = sn['text']
            for m in _MARK.finditer(t):
                fid = m.group(1)
                if fid in out: continue
                left = _MARK.sub(lambda x: x.group(2), t[:m.start()]).split()
                right = _MARK.sub(lambda x: x.group(2), t[m.end():]).split()
                out[fid] = ' '.join(keep(left, size, True) + ['[' + m.group(2) + ']'] + keep(right, size, False))
    return out

def _snippets(items, words, ctx=None):
    """Snippets for these (form, place) pairs: the context (span()) around each shown place, merged where they meet on a
    page when ctx['join'], each candidate inside marked [[id|text]] (every candidate of this request found in it, not only
    the one it was made for). Returns [{'page', 'text', 'ids'}]."""
    c = ctx_of(ctx)
    win = collections.defaultdict(list)                  # page -> [(a, b)]
    marks = collections.defaultdict(list)
    for fid, p, shown in items:
        if p.get('w0') is None: continue
        marks[p['page']].append((p['w0'], p['w1'], fid, p['text']))
        if shown:
            pw = words.get(str(p['page'])) or []
            if p['w0'] < len(pw): win[p['page']].append(span(pw, p['w0'], p['w1'], c))
    out = []
    for page, ws in sorted(win.items()):
        ws.sort(); merged = []
        for a, b in ws:
            if c['join'] and merged and a <= merged[-1][1] + 1: merged[-1][1] = max(merged[-1][1], b)
            else: merged.append([a, b])
        pw = words.get(str(page)) or []
        for a, b in merged:
            t, ids = _text(pw, a, min(b, len(pw) - 1), marks[page], c['cjk_cap'])
            out.append({'page': page, 'text': t, 'ids': ids})
    return out

def requests(book, fs, words, per=FORMS_PER_REQUEST, ctx=None):
    """book: {'title', 'language'}. fs: forms (forms()), words: the audit's page word lists. Requests of at most `per`
    forms, in ORDER; each carries its own snippets, built as ctx (CTX) says."""
    c = ctx_of(ctx); out = []
    for i in range(0, len(fs), per):
        chunk = fs[i:i + per]
        pairs = []
        for f in chunk:
            shown = {id(p) for p in _contexts(f)}
            for p in f['places']: pairs.append((f['id'], p, id(p) in shown))
        items = [{'id': f['id'], 'form': f['form'], 'class': f['class'], 'italic': f['italic_any'] and not f['roman_any'],
                  'places': len(f['places']), **({'current': f['current']} if f.get('current') else {})} for f in chunk]
        sn = _snippets(pairs, words, c)
        if c['item_snippets']:
            for it in items: it['s'] = [n + 1 for n, x in enumerate(sn) if it['id'] in x['ids']]
        out.append({'book': {'title': book.get('title') or '', 'language': book.get('language') or ''},
                    'snippets': [{'s': n + 1, 'text': x['text']} for n, x in enumerate(sn)],
                    'items': items})
    return out

def user_text(req): return json.dumps(req, ensure_ascii=False, separators=(',', ':'))

def tokens(text):
    """A rough count: one token per CJK character, one per 3.5 other characters (Claude's tokenizer on mixed text)."""
    cjk = len(re.findall(r'[　-鿿豈-﫿가-힯＀-￯]', text))
    return cjk + (len(text) - cjk) / 3.5

INPUT_MARGIN = 1.7            # billed input / tokens() on the first paid round (Sonnet 5.5, 18 requests: 1.52–1.66), 2026-11-12
def size(req, prompt): return int((tokens(prompt) + tokens(user_text(req))) * INPUT_MARGIN) + 10

def body(req, model, prompt, max_tokens, supported=None):
    """supported: the model's supported_parameters from OpenRouter's model list (None: not known). Temperature is sent as
    decide.py sends it: never to a model in OMIT_TEMPERATURE or one OpenRouter lists without it (Sonnet 5.5 and Opus 5.5
    both, 2026-11-12); response_format only where it is listed."""
    b = {'model': model, 'max_tokens': max_tokens, 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_text(req)}],
         'provider': {'data_collection': 'deny'}}
    if supported is not None and 'response_format' in supported: b['response_format'] = {'type': 'json_object'}
    if not models.temperature_omitted(model) and (supported is None or 'temperature' in supported): b['temperature'] = models.TEMPERATURE
    return b

def _same_form(a, b):
    return unicodedata.normalize('NFC', ' '.join(str(a or '').split())).casefold() == unicodedata.normalize('NFC', ' '.join(str(b or '').split())).casefold()

def _loose(s):
    """An echo's loose key (#137, review 02 H1): letters and digits only, NFC, case folded."""
    return ''.join(ch for ch in unicodedata.normalize('NFC', str(s or '')).casefold() if ch.isalnum())

def marks_of(req):
    """{item id: the texts marked [[id|…]] with it in this request's snippets}, sorted: what the reply may echo besides
    the item's form. Read from the request as sent, so nothing new is sent (#137)."""
    out = collections.defaultdict(set)
    for sn in (req or {}).get('snippets') or []:
        for m in _MARK.finditer(sn.get('text') or ''): out[m.group(1)].add(m.group(2))
    return {i: sorted(v) for i, v in out.items()}

def echo_owners(forms, marks):
    """{loose key: the ids of this request whose form or a mark has it}: rule U's ownership test."""
    own = collections.defaultdict(set)
    for i, f in (forms or {}).items():
        for t in [f, *((marks or {}).get(i) or [])]:
            k = _loose(t)
            if k: own[k].add(i)
    return own

def echo_ok(e, i, forms, owners):
    """Rule U (#137, review 02 H1): the echo matches the item's form with spacing and case ignored (the rule before), or
    its loose key is the loose key of the item's form or of a text marked with its id, and of no other item's in the same
    request. A reply that copied the printed spelling ("Tenpyō hōji ninen:", a line's half of a broken word) is kept; an
    answer that landed on another item (two items differing only by an ʻokina or punctuation, a mark that is another
    item's whole form) is not."""
    if _same_form(e, forms.get(i)): return True
    k = _loose(e)
    return bool(k) and owners.get(k) == {i}

def parse(text, ids, forms=None, marks=None):
    """The model's reply text → ({id: decision}, dropped). A decision: {lang (or None), confidence, why, note?}. A
    decision is dropped when its id is unknown or repeated, its form echo fits no item or another (echo_ok; marks: the
    request's marks_of, None to compare forms only), its tag is not one the step may write (langtag.valid_part), or its
    confidence or reason is not one of the listed words. Each dropped entry (#137) carries a `code` (DROP_CODES) beside
    its `why`, and an answer's own `echo`, `lang` and `confidence`, so the record keeps what was thrown away."""
    m = re.search(r'\{.*\}', text or '', re.S)
    try: data = json.loads(m.group(0)) if m else None
    except ValueError: data = None
    out, dropped = {}, []
    if not isinstance(data, dict) or not isinstance(data.get('decisions'), list):
        # not valid JSON as a whole (a stray brace, a cut string): keep every decision object that is itself valid
        found = []
        for x in re.finditer(r'\{[^{}]*"id"[^{}]*\}', text or ''):
            try: found.append(json.loads(x.group(0)))
            except ValueError: pass
        if not found: return {}, [{'id': None, 'code': 'unreadable', 'why': 'reply is not a decisions object'}]
        dropped.append({'id': None, 'code': 'partial', 'why': f'reply not valid JSON: {len(found)} decisions read one by one'})
        data = {'decisions': found}
    owners = echo_owners(forms, marks) if forms else {}
    def drop(i, code, why, d=None):
        e = {'id': i, 'code': code, 'why': why}
        if isinstance(d, dict):
            if 'form' in d: e['echo'] = str(d['form'])[:200]
            e['lang'] = d.get('lang'); e['confidence'] = d.get('confidence')
        dropped.append(e)
    for d in data['decisions']:
        if not isinstance(d, dict): drop(None, 'invalid', 'not an object'); continue
        i = str(d.get('id'))
        lang = langtag.without_suppressed_script(d.get('lang')); conf = d.get('confidence'); why = d.get('why')   # 'ms-Latn' → 'ms' (#137)
        if i not in ids: drop(i, 'unknown_id', 'unknown id', d); continue
        if i in out: drop(i, 'twice', 'answered twice', d); continue
        if forms and 'form' in d and not echo_ok(d['form'], i, forms, owners):     # the form echo (review 06, L1): an id off by one
            drop(i, 'echo', 'its form does not match the item', d); continue
        if lang is not None and not langtag.valid_part(lang): drop(i, 'tag', f'tag not allowed: {lang!r}', d); continue
        if conf not in CONF: drop(i, 'invalid', f'confidence not allowed: {conf!r}', d); continue
        if why not in WHY: drop(i, 'invalid', f'reason not allowed: {why!r}', d); continue
        out[i] = {'lang': lang, 'confidence': conf, 'why': why, **({'evidence': str(d['evidence'])[:160]} if d.get('evidence') else {}),
                  **({'note': str(d['note'])[:120]} if d.get('note') else {})}
    for i in ids:
        if i not in out and not any(x['id'] == i for x in dropped): drop(i, 'not_answered', 'not answered')
    return out, dropped

DROP_CODES = ('echo', 'tag', 'invalid', 'unknown_id', 'twice', 'not_answered', 'unreadable', 'partial')
# Why a word form has no AI decision (#137), as language_parts version-2 forms carry it (`no_answer`) and the review page
# words it. One per form: its own answer's reason when it had one; else what became of its request.
NO_ANSWER = ('echo', 'tag', 'invalid', 'not_answered', 'cut_off', 'failed', 'unreadable')   # unreadable: #151 (review 22 M3)

KIND_WORDS = {'existing': 'language tags already in the PDF', 'cjk': 'words in Chinese, Japanese or Korean characters',   # #159: plain names
              'marks': 'words with macrons or other marks', 'hawaiian': 'Hawaiian-looking words', 'script': 'words in other scripts',
              'passage': 'passages', 'accented': 'words with accents', 'latin': 'other Latin-script words',
              'unknown': 'words not in the English word list'}

def no_answer(ids, dropped, finish=None):
    """{id: NO_ANSWER code} for one request's ids with no decision: echo, tag or invalid from the id's own dropped answer;
    else, for a reply cut off (finish 'length'), cut_off; for a reply that couldn't be read at all, unreadable (#151); for a
    reply read only in pieces, invalid; otherwise
    not_answered (a complete reply skipped it). `failed` (a request with no reply) is the caller's."""
    whole = {d['code'] for d in dropped if d.get('id') is None}
    out = {}
    for i in ids:
        own = next((d['code'] for d in dropped if d.get('id') == i and d.get('code') in ('echo', 'tag', 'invalid')), None)
        if own: out[i] = own
        elif finish == 'length': out[i] = 'cut_off'
        elif 'unreadable' in whole and 'partial' not in whole: out[i] = 'unreadable'   # #151: the whole reply couldn't be read
        elif whole & {'unreadable', 'partial'}: out[i] = 'invalid'
        else: out[i] = 'not_answered'
    return out

def to_parts(fs, decisions, tag_conf=('high', 'medium')):
    """Decisions → language_parts: every place of a form tagged with high or medium confidence. Low, null and unsure
    stay untagged (listed for a person: review page, stage D)."""
    parts = []
    for f in fs:
        if f['group'] == 'existing': continue           # a tag already in the PDF: the decision is a person's to apply (stage D)
        d = decisions.get(f['id'])
        if not d or not d['lang'] or d['confidence'] not in tag_conf: continue
        for p in f['places']:
            parts.append({'page': p['page'], 'mcid': p['mcid'], 'first': p['first'], 'last': p['last'], 'lang': d['lang'],
                          'text': p['text'], 'form': f['form'], 'class': f['class'], 'confidence': d['confidence']})
    return {'parts': parts}

NON_LATIN = ('cjk:', 'script:')

def needs_person(f, d):
    """True when a form's place must be decided by a person even untagged (review 02, M6): CJK or another non-Latin
    script the AI left untagged or low, an existing tag, or a form with no decision at all."""
    non_latin = any(c.startswith(NON_LATIN) for c in f['class'])
    return f['group'] == 'existing' or not d or (non_latin and (not d.get('lang') or d.get('confidence') == 'low'))

# ---- the rows of language_parts, version 2 and 3: the one reader (review 02, H2). Every other module reads rows through
# rows() and has_forms(), never by a row's length or the version number: a version 3 row is [page, [[mcid, first, last],
# …], form index] (#150, #161: one place across several runs), a version 2 row [page, mcid, first, last, form index].
def _whole(v): return isinstance(v, int) and not isinstance(v, bool)

def has_forms(lp):
    """True for language_parts with forms and rows (version 2, or 3 with segmented rows)."""
    return isinstance(lp, dict) and lp.get('version') in (2, 3)

def parse_row(r):
    """(page, segments [[mcid, first, last], …], form index), or (None, why) for a row of neither shape."""
    if isinstance(r, list) and len(r) == 5 and all(_whole(x) for x in r): return r[0], [[r[1], r[2], r[3]]], r[4]
    if isinstance(r, list) and len(r) == 3 and _whole(r[0]) and _whole(r[2]) and isinstance(r[1], list) and len(r[1]) >= 2 \
            and all(isinstance(x, list) and len(x) == 3 and all(_whole(v) for v in x) for x in r[1]):
        return r[0], [list(x) for x in r[1]], r[2]
    return None, ('segments not lists of three whole numbers' if isinstance(r, list) and len(r) == 3 and isinstance(r[1], list) else 'not five whole numbers')

def segments_problem(segs):
    """None, or why a row's segments are out of order: a run index below 0, a character range not in order, a run twice."""
    if any(m < 0 or not 0 <= f <= l for m, f, l in segs): return 'run or character indexes not in order'
    if len({m for m, _, _ in segs}) != len(segs): return 'a run appears twice in one place'
    return None

def rows(lp):
    """Yields (page, segments, form index) for every row of a usable shape whose form exists; others are skipped, as each
    reader skipped them before (workorder_check reports them: row_problem)."""
    if not has_forms(lp): return
    n = len(lp.get('forms') or [])
    for r in lp.get('parts') or []:
        page, segs, *fi = parse_row(r)
        if page is None or not fi or not 0 <= fi[0] < n: continue
        yield page, segs, fi[0]

def to_rows(fs, decisions, tag_conf=('high', 'medium'), readings=None, reasons=None):
    """Decisions → language_parts, version 2 (review 06, record size): one entry per form, with the AI's answer and whether
    it is tagged (`tag`: high or medium confidence with a language), and the places as rows [page, mcid, first, last,
    form index]. Every form with places is kept, tagged or not, so a person can tag what the AI left untagged; apply.py
    tags only forms with `tag` true. Existing tags carry `current` (the PDF's value), never `tag`: a person decides them.
    A decision made by the reading rule (lib/hanreading.py, #123) carries `rule`; readings ({form id: the reading printed
    beside a Han-only form, hanreading.compact}) go into each form's `reading` (#124's group approval). reasons ({form id:
    NO_ANSWER code}): why a form has no decision at all, kept as its `no_answer` (#137)."""
    forms, rows = [], []
    for f in fs:
        d = decisions.get(f['id']) or {}
        e = {'key': f'{f["group"]}|{f["form"]}' + (f'|{f["current"]}' if f.get('current') else ''), 'form': f['form'], 'group': f['group'],
             'class': f['class'], 'lang': d.get('lang'), 'confidence': d.get('confidence'), 'why': d.get('why'),
             **({'evidence': d['evidence']} if d.get('evidence') else {}), **({'current': f['current']} if f.get('current') else {}),
             **({'rule': d['rule']} if d.get('rule') else {}), **({'reading': (readings or {})[f['id']]} if f['id'] in (readings or {}) else {}),
             **({'carried': f['carried']} if f.get('carried') else {}),
             **({'no_answer': (reasons or {})[f['id']]} if not d and (reasons or {}).get(f['id']) in NO_ANSWER else {}),
             'tag': bool(f['group'] != 'existing' and d.get('lang') and d.get('confidence') in tag_conf),
             **({'person': True} if needs_person(f, d) else {}), 'places': len(f['places'])}
        i = len(forms); forms.append(e)
        for p in f['places']:
            rows.append([p['page'], [list(x) for x in p['segments']], i] if p.get('segments') else [p['page'], p['mcid'], p['first'], p['last'], i])
    return {'version': 3 if any(len(r) == 3 for r in rows) else 2, 'forms': forms, 'parts': rows}   # version 2 byte for byte with no segments

def to_decide(forms):
    """The indexes of the version-2 forms a person decides on the review page: those the AI tagged or left to a person;
    when the AI proposed no tag at all, every form, so a person confirms what it left untagged (Patrick, 2026-11-14:
    never Not Applicable after the step ran). One rule for the review page's rows and the Language Tags line."""
    fs = [f if isinstance(f, dict) else {} for f in forms or []]
    pick = [i for i, f in enumerate(fs) if f.get('tag') or f.get('person')]
    return pick if pick else list(range(len(fs)))

def expand(lp):
    """language_parts of any version → the parts to tag, as dicts {page, mcid, first, last, lang, form, text?}: version 1
    as written (every part tagged), versions 2 and 3 the rows of forms with `tag` true. A version 3 row across several runs
    carries `segments` [[mcid, first, last], …] (mcid, first, last: its first segment's). apply.py and the checks read this."""
    if not isinstance(lp, dict): return []
    if not has_forms(lp): return list(lp.get('parts') or [])
    forms = lp.get('forms') or []
    out = []
    for page, segs, fi in rows(lp):
        f = forms[fi]
        if f.get('tag') and f.get('lang'):
            m, a, b = segs[0]
            out.append({'page': page, 'mcid': m, 'first': a, 'last': b, 'lang': f['lang'], 'form': f.get('form'),
                        'class': f.get('class'), 'confidence': f.get('confidence'), **({'segments': segs} if len(segs) > 1 else {})})
    return out
