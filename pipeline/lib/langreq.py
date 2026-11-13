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
about CONTEXT words before and after up to SNIPPETS_PER_FORM of its places. Each snippet is sent once per request, with
every candidate in it marked [[id|text]]. Kana and hangul runs are not sent: their language is known locally
(lib/scripts.py).
"""
import json, re, collections
from lib import langtag, models

CONTEXT = 15                    # words on each side
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

def forms(places, skip=LOCAL, unknown_italic_only=False):
    """Places grouped by (printed form, group): one decision per form. Each form keeps all its places."""
    by = collections.OrderedDict()
    for p in places:
        if any(c in skip for c in p['class']) and len(p['class']) == 1: continue
        g = group_of([c for c in p['class'] if c != 'passage'] or p['class'])
        if 'passage' in p['class']: g = 'passage'
        if unknown_italic_only and g == 'unknown' and not p.get('italic'): continue
        key = (p['form'], g)
        if 'existing' in p['class']: g = 'existing'; key = (p['form'], g, p.get('current'))
        f = by.setdefault(key, {'form': p['form'], 'group': g, 'class': sorted(set(p['class'])), 'places': [], 'italic_any': False, 'roman_any': False,
                                **({'current': p['current']} if p.get('current') else {})})
        f['places'].append(p); f['italic_any'] |= bool(p.get('italic')); f['roman_any'] |= not p.get('italic')
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

def _snippets(items, words):
    """Snippets for these (form, place) pairs: windows of CONTEXT words around each place, merged where they meet on a
    page, each candidate inside marked [[id|text]] (every candidate of this request found in it, not only the one it was
    made for)."""
    win = collections.defaultdict(list)                  # page -> [(w0, w1, id, text)]
    marks = collections.defaultdict(list)
    for fid, p, shown in items:
        if p.get('w0') is None: continue
        marks[p['page']].append((p['w0'], p['w1'], fid, p['text']))
        if shown: win[p['page']].append((max(0, p['w0'] - CONTEXT), p['w1'] + CONTEXT))
    out = []
    for page, ws in sorted(win.items()):
        ws.sort(); merged = []
        for a, b in ws:
            if merged and a <= merged[-1][1] + 1: merged[-1][1] = max(merged[-1][1], b)
            else: merged.append([a, b])
        pw = words.get(str(page)) or []
        for a, b in merged:
            b = min(b, len(pw) - 1)
            ms = sorted((m for m in marks[page] if m[0] >= a and m[1] <= b), key=lambda m: m[0])
            toks, k = [], a
            for w0, w1, fid, text in ms:
                if w0 < k: continue                         # overlapping marks: the first wins
                toks += pw[k:w0]; toks.append(f'[[{fid}|{text}]]'); k = w1 + 1
            toks += pw[k:b + 1]
            out.append({'page': page, 'text': ' '.join(toks)})
    return out

def requests(book, fs, words, per=FORMS_PER_REQUEST):
    """book: {'title', 'language'}. fs: forms (forms()), words: the audit's page word lists. Requests of at most `per`
    forms, in ORDER; each carries its own snippets."""
    out = []
    for i in range(0, len(fs), per):
        chunk = fs[i:i + per]
        pairs = []
        for f in chunk:
            shown = {id(p) for p in _contexts(f)}
            for p in f['places']: pairs.append((f['id'], p, id(p) in shown))
        items = [{'id': f['id'], 'form': f['form'], 'class': f['class'], 'italic': f['italic_any'] and not f['roman_any'],
                  'places': len(f['places']), **({'current': f['current']} if f.get('current') else {})} for f in chunk]
        out.append({'book': {'title': book.get('title') or '', 'language': book.get('language') or ''},
                    'snippets': [{'s': n + 1, 'text': s['text']} for n, s in enumerate(_snippets(pairs, words))],
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

def parse(text, ids):
    """The model's reply text → ({id: decision}, dropped). A decision: {lang (or None), confidence, why, note?}. A
    decision is dropped when its id is unknown or repeated, its tag is not one the step may write (langtag.valid_part),
    or its confidence or reason is not one of the listed words."""
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
        if not found: return {}, [{'id': None, 'why': 'reply is not a decisions object'}]
        dropped.append({'id': None, 'why': f'reply not valid JSON: {len(found)} decisions read one by one'})
        data = {'decisions': found}
    for d in data['decisions']:
        if not isinstance(d, dict): dropped.append({'id': None, 'why': 'not an object'}); continue
        i = str(d.get('id'))
        lang = d.get('lang'); conf = d.get('confidence'); why = d.get('why')
        if i not in ids: dropped.append({'id': i, 'why': 'unknown id'}); continue
        if i in out: dropped.append({'id': i, 'why': 'answered twice'}); continue
        if lang is not None and not langtag.valid_part(lang): dropped.append({'id': i, 'why': f'tag not allowed: {lang!r}'}); continue
        if conf not in CONF: dropped.append({'id': i, 'why': f'confidence not allowed: {conf!r}'}); continue
        if why not in WHY: dropped.append({'id': i, 'why': f'reason not allowed: {why!r}'}); continue
        out[i] = {'lang': lang, 'confidence': conf, 'why': why, **({'evidence': str(d['evidence'])[:160]} if d.get('evidence') else {}),
                  **({'note': str(d['note'])[:120]} if d.get('note') else {})}
    for i in ids:
        if i not in out and not any(x['id'] == i for x in dropped): dropped.append({'id': i, 'why': 'not answered'})
    return out, dropped

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

def to_rows(fs, decisions, tag_conf=('high', 'medium')):
    """Decisions → language_parts, version 2 (review 06, record size): one entry per form, with the AI's answer and whether
    it is tagged (`tag`: high or medium confidence with a language), and the places as rows [page, mcid, first, last,
    form index]. Every form with places is kept, tagged or not, so a person can tag what the AI left untagged; apply.py
    tags only forms with `tag` true. Existing tags carry `current` (the PDF's value), never `tag`: a person decides them."""
    forms, rows = [], []
    for f in fs:
        d = decisions.get(f['id']) or {}
        e = {'key': f'{f["group"]}|{f["form"]}' + (f'|{f["current"]}' if f.get('current') else ''), 'form': f['form'], 'group': f['group'],
             'class': f['class'], 'lang': d.get('lang'), 'confidence': d.get('confidence'), 'why': d.get('why'),
             **({'evidence': d['evidence']} if d.get('evidence') else {}), **({'current': f['current']} if f.get('current') else {}),
             'tag': bool(f['group'] != 'existing' and d.get('lang') and d.get('confidence') in tag_conf),
             **({'person': True} if needs_person(f, d) else {}), 'places': len(f['places'])}
        i = len(forms); forms.append(e)
        for p in f['places']: rows.append([p['page'], p['mcid'], p['first'], p['last'], i])
    return {'version': 2, 'forms': forms, 'parts': rows}

def expand(lp):
    """language_parts of either version → the parts to tag, as dicts {page, mcid, first, last, lang, form, text?}: version 1
    as written (every part tagged), version 2 the rows of forms with `tag` true. apply.py and the checks read this."""
    if not isinstance(lp, dict): return []
    if lp.get('version') != 2: return list(lp.get('parts') or [])
    forms = lp.get('forms') or []
    out = []
    for r in lp.get('parts') or []:
        if not (isinstance(r, list) and len(r) == 5 and isinstance(r[4], int) and 0 <= r[4] < len(forms)): continue
        f = forms[r[4]]
        if f.get('tag') and f.get('lang'):
            out.append({'page': r[0], 'mcid': r[1], 'first': r[2], 'last': r[3], 'lang': f['lang'], 'form': f.get('form'),
                        'class': f.get('class'), 'confidence': f.get('confidence')})
    return out
