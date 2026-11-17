"""name_languages.py: the language step (#118, language tagging; WCAG 3.1.2). PAID, its own step after decide.py and
read_pages.py, with its own model (LANGUAGE_MODEL) and limit (LANGUAGE_MAX_USD).

    python name_languages.py AUDIT_DIR RUN_DIR --pdf PDF [--dry-run] [--model ID] [--max-usd N]
                             [--response-file F | --reuse]

The candidates are the audit's (AUDIT_DIR/lang_candidates.json, lib/langcands.py). On a scanned book whose work order
gives OCR words or pages a reading (ocr_words, page_readings), they are found again over what a screen reader speaks
(review 02, M5). The PDF's own language tags (lib/langcands.existing) go too, so a person can confirm, correct or remove
them. lib/langreq.py builds the requests with prompts/language_v3.md: one decision per printed form, about 15 words of
context, each snippet once per request, data_collection deny. The decisions become workorder.json's `language_parts`.

    RUN_DIR/language_estimate.json   --dry-run: the worst case and expected cost (lib/costs.py adds it to the PDF's)
    RUN_DIR/language_run.json        model, prompt, the estimate, every request's reply, usage and cost, the decisions by form
    RUN_DIR/language_requests/       each request as sent (local only)

No request is ever sent with --response-file (a saved language_run.json: FROM= or REPLY=) or --reuse (this folder's own
language_run.json, complete): the saved decisions are applied by printed form (review 02, M4), and forms no longer found
or not decided are listed. A request already answered with the same model and prompt is reused, never paid for again.
The step refuses before any call when its worst case passes --max-usd (LANGUAGE_MAX_USD, default 6, lib/costs.py) or the credit, for any
model (review 02, M7). Forms past LANGUAGE_MAX_FORMS (default 5000) are not sent, and listed.

Words in Chinese characters alone with a reading printed beside every place (kana or a Hepburn word, pinyin, hangul
or a Korean romanization), all naming one language, are decided by a local rule (lib/hanreading.py, #123): never sent,
never counted in the estimate, the same way every time. Their
decisions carry `rule: "reading"` and the reading as evidence; a person approves them on the review page like the AI's.
Every Han-only form's reading (#124: bibliographies left out) is kept in its language_parts entry as `reading`, for the
review page's "Approve Characters with Matching Readings". LANG_READING_RULE=off turns the rule off (every form to the AI).

Two options, both off by default (review 08, M6): LANG_GROW=on (--grow) finds the candidates again with a title's whole
extent (lib/langcands.book grow=True), and LANG_GROUP=on (--group) makes adjacent one-character Han places one form
(lib/langreq.forms group=True). language_run.json records them under `options`.
"""
import sys, os, re, json, time, hashlib, argparse, urllib.request, urllib.error, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import plumb_fix, plpages, langcands, langreq, costhistory, costs, workorder_check, hanreading  # noqa: F401

RULE_NAME = hanreading.RULE
PROMPT_NAME = 'language_v3.md'                   # v1 with v2's form echo and dictionary-phrase line (adopted 2026-11-13, 11 §2)
DEFAULT_MODEL = 'anthropic/claude-sonnet-5.5'   # kept after round 15's experiment: Opus 5.5 no more accurate at 2.2 times the cost
CHARS_PER_TOKEN = 3.5

def load_env():
    d = HERE
    while True:
        p = os.path.join(d, '.env')
        if os.path.isfile(p):
            for line in open(p, encoding='utf-8'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1); k = k.strip().removeprefix('export ').strip()
                    if not os.environ.get(k): os.environ[k] = v.strip().strip('"').strip("'")
            return
        if os.path.dirname(d) == d: return
        d = os.path.dirname(d)

def get(url, key=None):
    h = {'User-Agent': 'pdfremproto1', **({'Authorization': f'Bearer {key}'} if key else {})}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r: return json.load(r)

def form_key(f): return f'{f["group"]}|{f["form"]}' + (f'|{f["current"]}' if f.get('current') else '')

def marks_for(x, folder, prompt_sha):
    """The marks a saved request entry carried ({sent id: marked texts}, #137): its own `id_marks`, or for a run made
    before them, its request file in the run folder that sent it (language_requests/NNN.request.json), used only when the
    file is the request that entry answered: sha256(prompt + its user content) equals the entry's `sha256` (review 02, M5:
    a later run may have written another request under the same number). None: the echo is compared with forms alone."""
    if isinstance(x.get('id_marks'), dict): return x['id_marks']
    if not (folder and prompt_sha and x.get('sha256') and x.get('n') is not None): return None
    try:
        body = json.load(open(os.path.join(folder, 'language_requests', f'{int(x["n"]):03d}.request.json'), encoding='utf-8'))
        text = body['messages'][1]['content']
    except (OSError, ValueError, KeyError, IndexError, TypeError): return None
    if hashlib.sha256((prompt_sha + text).encode()).hexdigest()[:16] != x['sha256']: return None
    return langreq.marks_of(json.loads(text))

def spoken_of(wo, digest):
    """What a screen reader speaks on a scanned book: {'forms': {OCR form: reading}, 'pages': {page: reading}}, or None."""
    forms = {it['text']: it['reads'] for it in wo.get('ocr_words') or [] if isinstance(it, dict) and it.get('text') and it.get('reads')}
    pages = {it['page']: it['text'] for it in wo.get('page_readings') or [] if isinstance(it, dict) and isinstance(it.get('page'), int) and it.get('text')}
    return {'forms': forms, 'pages': pages} if (forms or pages) else None

def candidates(args, wo):
    """(places, words, doc_lang, how): the audit's, found again over spoken text on a scanned book, plus existing tags."""
    doc_lang = ((wo.get('document') or {}).get('lang')) or ''
    path = os.path.join(args.audit_dir, 'lang_candidates.json')
    saved = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else None
    sp = spoken_of(wo, None)
    PL = None
    if sp or saved is None or args.grow or (doc_lang and saved.get('document_lang', '') != doc_lang):
        PL = plpages.Pages(args.pdf)
        c = langcands.book(PL, doc_lang=doc_lang or None, spoken=sp, grow=args.grow)
        how = ('found again over the spoken text' if sp else 'found with the work order\'s document language' if not args.grow or (doc_lang and saved and saved.get('document_lang', '') != doc_lang)
               else 'found again') + (', titles grown (LANG_GROW)' if args.grow else '')
    else: c, how = saved, 'the audit\'s'
    places = list(c['places'])
    try:
        import pikepdf
        with pikepdf.open(args.pdf) as pdf: places += langcands.existing(pdf, PL or plpages.Pages(args.pdf), doc_lang or str(pdf.Root.get('/Lang', '')))
    except Exception as e: print(f'language step: existing tags not read ({type(e).__name__})')
    return places, c['words'], doc_lang, how, c.get('fingerprint')

def local_rule(args, fs, words, doc_lang, places):
    """The reading rule (#123) and every Han-only form's reading (#124): (local {form id: decision}, readings {form id:
    compact evidence}, stats). Off (nothing local) with LANG_READING_RULE=off; readings are kept either way."""
    try: digest = json.load(open(os.path.join(args.audit_dir, 'digest.json'), encoding='utf-8'))
    except (OSError, ValueError): digest = None           # no headings: the rule still runs; #124's evidence needs the bibliography's pages
    local, evid, stats = hanreading.decide(fs, words, digest or {}, doc_lang, places)
    if os.environ.get('LANG_READING_RULE', 'on').lower() in ('0', 'off', 'no', 'false'):
        local, stats = {}, {**stats, 'decided': 0, 'by_language': {}, 'off': 'LANG_READING_RULE=off'}
    return local, {i: hanreading.compact(e) for i, e in evid.items()}, stats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audit_dir'); ap.add_argument('run_dir'); ap.add_argument('--pdf', required=True)
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--model', default=None)
    ap.add_argument('--max-usd', type=float, default=float(os.environ.get('LANGUAGE_MAX_USD') or costs.DEFAULT_LANGUAGE_USD))
    ap.add_argument('--max-forms', type=int, default=int(os.environ.get('LANGUAGE_MAX_FORMS') or 5000))
    ap.add_argument('--book-max-usd', type=float, default=float(os.environ.get('BOOK_MAX_USD') or costs.DEFAULT_LIMITS['per_book_usd']),
                    help="the PDF's limit, shared with the work order and the page readings (review 06, M2)")
    on = lambda k: os.environ.get(k, 'off').lower() in ('1', 'on', 'yes', 'true')
    ap.add_argument('--grow', action='store_true', default=on('LANG_GROW'), help="a title's whole extent (LANG_GROW=on; off by default, review 08 M6)")
    ap.add_argument('--group', action='store_true', default=on('LANG_GROUP'), help='adjacent one-character Han places as one form (LANG_GROUP=on; off by default)')
    g = ap.add_mutually_exclusive_group(); g.add_argument('--response-file'); g.add_argument('--reuse', action='store_true')
    args = ap.parse_args()
    R = args.run_dir
    wo_path = os.path.join(R, 'workorder.json')
    wo = json.load(open(wo_path, encoding='utf-8')) if os.path.exists(wo_path) else {}
    prompt_file = next((p for p in (os.path.join(HERE, 'prompts', PROMPT_NAME), os.path.join(os.path.dirname(HERE), 'prompts', PROMPT_NAME)) if os.path.isfile(p)), None)
    if not prompt_file: sys.exit(f'no prompt file {PROMPT_NAME}')
    prompt = open(prompt_file, encoding='utf-8').read(); prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    places, words, doc_lang, how, fp = candidates(args, wo)
    fs = langreq.forms(places, group=args.group)      # LANG_GROUP: adjacent one-character Han places as one form (review 08, M6)
    est_path, run_path = os.path.join(R, 'language_estimate.json'), os.path.join(R, 'language_run.json')
    if not fs:
        for p in (est_path,):
            if os.path.exists(p): os.remove(p)
        print('language step: no candidates in this PDF, nothing to send'); merge(R, wo_path, fs, {}, None); return
    local, readings, rule = local_rule(args, fs, words, doc_lang, places)     # #123: decided here, never sent
    ai_fs = [f for f in fs if f['id'] not in local]
    sent, held = ai_fs[:args.max_forms], ai_fs[args.max_forms:]
    sent_ids = {x['id'] for x in sent}
    written = [f for f in fs if f['id'] in local or f['id'] in sent_ids]      # the forms written into the work order, in their order
    title = str(((wo.get('document') or {}).get('title')) or '')
    reqs = langreq.requests({'title': title, 'language': doc_lang}, sent, words)
    rule_rec = {'rule': RULE_NAME, 'decided': len(local), **{k: v for k, v in rule.items() if k != 'decided'}}
    if local or rule.get('off'):
        print(f'language step: {len(local)} word form{"" if len(local) == 1 else "s"} in Chinese characters decided by the reading printed '
              f'beside every place (no AI request)' + (f' · {", ".join(f"{k} {v}" for k, v in sorted(rule.get("by_language", {}).items()))}' if local else '')
              + (f' · rule off: {rule["off"]}' if rule.get('off') else ''))
    # --- replay: decisions by printed form (M4), never a request
    if args.response_file or args.reuse:
        src = args.response_file or run_path
        old = json.load(open(src, encoding='utf-8')) if os.path.exists(src) else None
        if isinstance(old, dict) and old.get('requests'):
            # the saved replies themselves, read again (review 06, M3): a step that stopped after paying and before parsing
            # left decisions {} beside complete replies; reading them costs nothing
            found = dict(old.get('decisions') or {})
            form_of = {form_key(f): f['form'] for f in fs}
            src_dir = os.path.dirname(os.path.abspath(src))          # the run that sent these requests (review 02, M5)
            for x in old['requests']:
                if not x.get('text'): continue
                idk = x.get('id_keys') or dict(zip(x.get('ids') or [], x.get('keys') or []))
                # with the forms and the marks as sent, as the first parse: a decision whose form echo names another item stays
                # dropped (review 12, M1; #137 rule U)
                d, _ = langreq.parse(x['text'], set(idk), forms={i: form_of.get(k, k.split('|')[1] if '|' in k else k) for i, k in idk.items()},
                                     marks=marks_for(x, src_dir, old.get('prompt_sha256')))
                for i, v in d.items(): found.setdefault(idk[i], v)
            old['decisions'] = found
        if not isinstance(old, dict) or not (old.get('decisions') or (local and not ai_fs)):   # #123: a book decided wholly by the rule
            print(f'language step: no saved decisions in {src}: not run')
            merge(R, wo_path, fs, {}, {'schema': 'language-run/1', 'decisions': {}, 'requests': [], 'cost_usd': 0, 'response_from': os.path.abspath(src)},
                  note='not run (the saved reply has no language decisions)'); return
        by_key = old.get('decisions') or {}
        dec = {f['id']: by_key[form_key(f)] for f in sent if form_key(f) in by_key}
        now_keys = {form_key(f) for f in sent}
        local_keys = {form_key(f) for f in fs if f['id'] in local}         # decided by the reading rule now: never the saved answer
        replay = {'from': os.path.abspath(src), 'used': len(dec), 'vanished': sorted(k for k in by_key if k not in now_keys and k not in local_keys)[:200],
                  'vanished_count': sum(1 for k in by_key if k not in now_keys and k not in local_keys), 'not_decided': sum(1 for f in sent if form_key(f) not in by_key),
                  'local': len(local), 'local_over_saved': sum(1 for k in by_key if k in local_keys),
                  'saved_fingerprint': old.get('fingerprint'), 'fingerprint': fp}
        rec = {**{k: old.get(k) for k in ('schema', 'model', 'prompt_file', 'prompt_sha256', 'started')}, 'response_from': os.path.abspath(src),
               'own_reply': bool(args.reuse) or os.path.abspath(src) == os.path.abspath(run_path), 'replay': replay,
               'decisions': by_key, 'requests': old.get('requests') if args.reuse else [], 'cost_usd': (old.get('cost_usd') or 0) if args.reuse else 0,
               'original_cost_usd': old.get('cost_usd'), 'candidates': how, 'reading_rule': rule_rec,
               'local': {form_key(f): local[f['id']] for f in fs if f['id'] in local}}
        if not args.reuse: json.dump(rec, open(run_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        merge(R, wo_path, written, {**dec, **local}, rec, held=held, contexts=contexts_of(written, words, reqs), readings=readings)
        print(f'language step: saved decisions applied by form ({len(dec)} of {len(sent)} forms; {replay["vanished_count"]} no longer found; '
              f'{replay["not_decided"]} not decided) · {len(local)} decided by the reading rule · no AI request'); return
    if not ai_fs:                                      # every form decided by the reading rule (#123): nothing to send, no network
        if args.dry_run:
            json.dump({'schema': 'language-estimate/1', 'model': None, 'prompt_sha256': prompt_sha, 'forms': len(fs), 'local': len(local), 'sent': 0,
                       'held_back': 0, 'requests': 0, 'to_send': 0, 'reused': 0, 'worst_case_usd': 0.0, 'per_call_worst_usd': 0.0, 'cap_usd': args.max_usd,
                       'max_tokens': [], 'words_sent': 0}, open(est_path, 'w', encoding='utf-8'), indent=1)
            print(f'language step: {len(fs)} forms, all decided by the reading rule · nothing to send'); print('dry run: nothing sent'); return
        rec = {'schema': 'language-run/1', 'model': None, 'prompt_file': os.path.basename(prompt_file), 'prompt_sha256': prompt_sha,
               'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'fingerprint': fp, 'candidates': how, 'options': {'grow': bool(args.grow), 'group': bool(args.group)},
               'reading_rule': rule_rec, 'local': {form_key(f): local[f['id']] for f in fs if f['id'] in local},
               'requests': [], 'decisions': {}, 'cost_usd': 0, 'not_decided': 0}
        json.dump(rec, open(run_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        merge(R, wo_path, written, dict(local), rec, contexts=contexts_of(written, words, reqs), readings=readings)
        print(f'language step: {len(local)} of {len(fs)} forms decided by the reading rule · no AI request · $0.0000 spent on this step'); return
    # --- the model, its price and parameters (any model is capped: M7)
    load_env()
    model = args.model or os.environ.get('LANGUAGE_MODEL') or DEFAULT_MODEL     # its own default, never the work order's (Patrick, 2026-11-14)
    try: m = next((x for x in get('https://openrouter.ai/api/v1/models')['data'] if x['id'] == model), None)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e: sys.exit(f'could not reach OpenRouter to look up the model: {e}')
    if m is None: sys.exit(f'refusing: model "{model}" is not on OpenRouter')
    pin, pout = float(m['pricing']['prompt']), float(m['pricing']['completion']); supported = m.get('supported_parameters')
    done = json.load(open(run_path, encoding='utf-8')) if os.path.exists(run_path) else {}
    reuse_ok = done.get('model') == model and done.get('prompt_sha256') == prompt_sha and not done.get('response_from')
    answered = {r['sha256']: r for r in done.get('requests') or [] if reuse_ok and r.get('finish') == 'stop'}
    todo = []
    for n, r in enumerate(reqs, 1):
        text = langreq.user_text(r); sha = hashlib.sha256((prompt_sha + text).encode()).hexdigest()[:16]
        mt = costs.allowance('language', len(r['items'])); ins = langreq.size(r, prompt)
        todo.append({'n': n, 'req': r, 'sha256': sha, 'max_tokens': mt, 'input_est': ins, 'worst': ins * pin + mt * pout, 'reused': sha in answered})
    send = [t for t in todo if not t['reused']]
    worst = sum(t['worst'] for t in send)
    est = {'forms': len(fs), 'local': len(local), 'sent': len(sent), 'held_back': len(held), 'requests': len(todo), 'to_send': len(send), 'reused': len(todo) - len(send),
           'worst_case_usd': round(worst, 4), 'per_call_worst_usd': round(max((t['worst'] for t in send), default=0), 4), 'cap_usd': args.max_usd,
           'price_per_million': [round(pin * 1e6, 4), round(pout * 1e6, 4)], 'max_tokens': [t['max_tokens'] for t in send], 'words_sent': sum(len(s['text'].split()) for r in reqs for s in r['snippets'])}
    if send:
        try: est['expected'] = costhistory.expected([{'kind': 'language', 'input_est': t['input_est'], 'max_tokens': t['max_tokens']} for t in send], model, pin, pout, worst)
        except Exception as ex: est['expected'] = {'none': 'error'}; print(f'note: the expected cost could not be worked out ({type(ex).__name__})')
    over_cap = worst > args.max_usd
    kept = {}
    if args.dry_run:                                   # one over its own cap is marked refused: never counted toward the PDF (review 08, H1)
        new = {'schema': 'language-estimate/1', 'model': model, 'prompt_sha256': prompt_sha, **est}
        kept = {} if over_cap else costs.kept_refusal(R, 'language', new)      # decide.py's "left out" survives this dry run
        json.dump({**new, **({'refused': {'why': 'cap', 'words': f'The language step could cost up to ${worst:.2f}, more than its limit of ${args.max_usd:.2f}.'}} if over_cap else kept)},
                  open(est_path, 'w', encoding='utf-8'), indent=1)
    print(f'language step: {len(fs)} forms ({len(local)} decided by the reading rule; {len(held)} held back by LANGUAGE_MAX_FORMS); '
          f'{len(sent)} in {len(todo)} requests ({len(todo) - len(send)} answered before) · {model}')
    if send: print('language step: ' + costhistory.terminal_line(est['expected']))
    print(f'language step: Max Estimated Cost: ${worst:.2f} · Limit: ${args.max_usd:.2f}')
    if over_cap:
        sys.exit(f'refusing before any AI request: the language step could cost up to ${worst:.2f}, more than the limit of ${args.max_usd:.2f}. '
                 f'To run it, raise the limit for this run: LANGUAGE_MAX_USD={int(worst) + 1}')
    if kept and os.path.exists(os.path.join(R, 'response.json')):       # the work order has run: the step stays left out
        sys.exit(f'refusing before any AI request: {kept["refused"].get("words")}')
    ref = costs.refused(R, 'language') if not args.dry_run and send else None
    if ref and ref.get('why') == 'book':               # decide.py left it out of the PDF's estimate: it stays out (review 08, H1)
        sys.exit(f'refusing before any AI request: {ref.get("words") or "the language step was left out of this PDF's estimate"}')
    spent = costs.book_spent(R)
    if not args.dry_run and spent + worst > args.book_max_usd:
        sys.exit(f'refusing before any AI request: this PDF has spent ${spent:.2f} and the language step could add ${worst:.2f}, more than the '
                 f'limit of ${args.book_max_usd:.2f} per PDF. To run it, raise the limit for this run: BOOK_MAX_USD={int(spent + worst) + 1}')
    if args.dry_run: print('dry run: nothing sent'); return
    rec = {'schema': 'language-run/1', 'model': model, 'prompt_file': os.path.basename(prompt_file), 'prompt_sha256': prompt_sha,
           'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'estimate': est, 'fingerprint': fp, 'candidates': how,
           'options': {'grow': bool(args.grow), 'group': bool(args.group)}, 'reading_rule': rule_rec,
           'local': {form_key(f): local[f['id']] for f in fs if f['id'] in local},
           'requests': [answered[t['sha256']] for t in todo if t['reused']], 'decisions': {}, 'cost_usd': round(done.get('cost_usd') or 0, 6) if reuse_ok else 0}
    if send:
        key = os.environ.get('OPENROUTER_API_KEY') or sys.exit('no OPENROUTER_API_KEY: put it in .env or export it')
        try:
            credit = get('https://openrouter.ai/api/v1/key', key).get('data', {}).get('limit_remaining')
            if credit is not None and float(credit) < worst: sys.exit(f'refusing: the language step could cost up to ${worst:.2f}, more than the ${float(credit):.2f} of credit left')
        except (urllib.error.URLError, TimeoutError, ValueError): pass
        os.makedirs(os.path.join(R, 'language_requests'), exist_ok=True)
        try: digest = json.load(open(os.path.join(args.audit_dir, 'digest.json'), encoding='utf-8'))
        except (OSError, ValueError): digest = None
        for t in send:
            body = langreq.body(t['req'], model, prompt, t['max_tokens'], supported); body['usage'] = {'include': True}
            json.dump(body, open(os.path.join(R, 'language_requests', f'{t["n"]:03d}.request.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(body).encode(),
                                         headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'X-Title': 'UH PDF remediation prototype'})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=900) as r: d = json.load(r)
            except urllib.error.HTTPError as e: print(f'  request {t["n"]}: OpenRouter error {e.code}: {e.read().decode("utf-8", "replace")[:300]} (not retried)'); continue
            except (urllib.error.URLError, TimeoutError) as e: print(f'  request {t["n"]}: no reply ({e}); not retried'); continue
            u = d.get('usage') or {}; ch = (d.get('choices') or [{}])[0]
            x = {'n': t['n'], 'sha256': t['sha256'], 'ids': [it['id'] for it in t['req']['items']], 'id_keys': {f['id']: form_key(f) for f in sent if f['id'] in {it['id'] for it in t['req']['items']}},
                 'id_marks': langreq.marks_of(t['req']),          # #137: what the reply may echo, by the ids as sent (review 02, M5)
                 'text': (ch.get('message') or {}).get('content') or '', 'finish': ch.get('finish_reason'), 'input_tokens': u.get('prompt_tokens'),
                 'output_tokens': u.get('completion_tokens'), 'cost_usd': u.get('cost'), 'seconds': round(time.time() - t0, 1)}
            rec['requests'].append(x); rec['cost_usd'] = round(rec['cost_usd'] + (x['cost_usd'] or 0), 6)
            print(f'  request {t["n"]}/{len(todo)}: {x["output_tokens"]} tokens, ${x["cost_usd"] or 0:.4f}' + ('' if x['finish'] == 'stop' else f' · cut off ({x["finish"]}): its finished decisions are kept'))
            json.dump(rec, open(run_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            if x['finish'] == 'stop' and x['input_tokens'] and x['output_tokens']:
                try: costhistory.append({'kind': 'language', 'model': model, 'prompt': os.path.basename(prompt_file), 'input_est': t['input_est'], 'input_billed': x['input_tokens'],
                                         'output': x['output_tokens'], 'images': 0, 'forms': len(x['ids']), 'date': rec['started'],
                                         'book': costhistory.book_id(R, digest), 'pass': str(t['n']), 'attempt': 1})
                except Exception: pass
    # decisions by form, from every complete reply
    dec, dropped = {}, []
    by_id = {f['id']: f for f in sent}
    for x in rec['requests']:                        # a reply cut off (finish 'length') keeps every decision it finished
        d, dr = langreq.parse(x.get('text') or '', set(x['ids']), forms={i: by_id[i]['form'] for i in x['ids'] if i in by_id},
                              marks=marks_for(x, R, rec.get('prompt_sha256'))); dec.update(d); dropped += dr
    rec['decisions'] = {form_key(by_id[i]): v for i, v in dec.items() if i in by_id}     # the AI's only: the rule's are under `local`
    rec['dropped'] = dropped[:200]
    rec['not_decided'] = sum(1 for f in sent if f['id'] not in dec)          # cut off, invalid, or never sent: listed for a person
    json.dump(rec, open(run_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    merge(R, wo_path, written, {**dec, **local}, rec, held=held, contexts=contexts_of(written, words, reqs), readings=readings)
    print(f'language step: {len(dec)} of {len(sent)} forms decided by the AI ({rec["not_decided"]} not decided), {len(local)} by the reading rule'
          f' · ${rec["cost_usd"]:.4f} spent on this step')

CONTEXT_CUT = 2000                 # characters: well above the longest adopted context (sentence mode caps each side)
def contexts_of(fs, words, reqs=None):
    """{form id: its first place's context as the requests sent it, the place in [brackets]}: what the review page shows
    beside a form. Taken from the built requests' own snippets (langreq.sent_contexts, review 19 L1); a form no snippet
    shows falls back to langreq.place_text. Rows of a finished run keep the contexts stored when its step ran."""
    sent = langreq.sent_contexts(reqs or [])
    out = {}
    for f in fs:
        if f['id'] in sent: out[f['id']] = sent[f['id']][:CONTEXT_CUT]; continue
        p = next((q for q in f['places'] if q.get('w0') is not None), None)
        if p is None: continue
        out[f['id']] = langreq.place_text(p, words)[:CONTEXT_CUT]
    return out

def merge(R, wo_path, fs, dec, rec, held=(), note=None, contexts=None, readings=None):
    """workorder.json's language_parts from the decisions (checked as every work order is), and, beside them in
    language_run.json, what a person must decide: non-Latin places the AI left untagged (review 02, M6) and every
    existing tag's answer. Always written, on every path (a fresh call, a reuse, a saved reply), so a later rebuild of
    workorder.json (decide.py --response-file) can put them back (review 02, M8)."""
    if not os.path.exists(wo_path): return
    wo = json.load(open(wo_path, encoding='utf-8'))
    lp = langreq.to_rows(fs, dec, readings=readings)
    pages = max([p['page'] for f in fs for p in f['places']] + [1])
    tmp = {'language_parts': lp}; dropped = workorder_check.check_language_parts(tmp, 10 ** 6)
    if tmp.get('language_parts', {}).get('parts'): wo['language_parts'] = tmp['language_parts']
    else: wo.pop('language_parts', None)
    lp = wo.get('language_parts') or {}
    json.dump(wo, open(wo_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if rec is None: return
    person = []
    for f in fs:
        d = dec.get(f['id'])
        non_latin = any(c.startswith('cjk:') or c.startswith('script:') for c in f['class'])
        if f['group'] == 'existing' or (non_latin and (not d or not d.get('lang') or d.get('confidence') == 'low')):
            person.append({'form': f['form'], 'group': f['group'], 'places': len(f['places']), 'current': f.get('current'),
                           'answer': d, 'pages': sorted({p['page'] for p in f['places']})[:20]})
    rec['needs_person'] = person; rec['parts'] = len(langreq.expand(wo.get('language_parts'))); rec['parts_dropped'] = dropped[:50]
    rec['language_parts'] = wo.get('language_parts') or {'parts': []}      # decide.py puts these back when it rebuilds workorder.json (M8)
    if contexts:                                       # the words around each form, for the review page only (kept beside the digest, never in the record)
        key_of = {f['id']: e['key'] for f, e in zip(fs, (wo.get('language_parts') or {}).get('forms') or [])}
        rec['contexts'] = {key_of[i]: c for i, c in contexts.items() if i in key_of}
    rec['held_back'] = [f['form'] for f in held][:200]; rec['held_back_count'] = len(held)
    nd = collections.defaultdict(list)                  # forms with no decision (cut off, invalid, a failed request), by group
    for f in fs:
        if f['id'] not in dec: nd[f['group']].append(f['form'])
    rec['not_decided_forms'] = {g: v[:200] for g, v in nd.items()}; rec['not_decided'] = sum(len(v) for v in nd.values())
    rec['parts_local'] = sum(1 for f in (wo.get('language_parts') or {}).get('forms') or [] if f.get('rule'))       # #123
    if note: rec['note'] = note
    json.dump(rec, open(os.path.join(R, 'language_run.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__': main()
