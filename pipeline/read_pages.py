"""read_pages.py: whole-page AI readings of scanned Hawaiian pages (issue #49). PAID, its own step after decide.py.

    python read_pages.py AUDIT_DIR RUN_DIR [--dry-run] [--model ID] [--max-usd N]

The audit lists the scanned pages where most words have Hawaiian shape (AUDIT_DIR/page_reads.json, images in
page_reads/). Tesseract has no Hawaiian model, so their OCR lost the ʻokina and kahakō. Each page image goes to the
model in its own request, with prompts/page_reading_v1.md: it transcribes the page exactly as printed. The readings are
added to RUN_DIR/workorder.json as `page_readings` [{page, text}]; apply.py gives each OCR word its reading at its own
place (ActualText), and the report asks a person who reads Hawaiian to check every page.

    RUN_DIR/page_reads_run.json   model, prompt, the estimate, and each page's reply, usage and cost

Pages are read AI_PARALLEL at a time (lib/aisend.py, #135 (parallel requests)). A failure is sent once more after a pause
(60 s after a 429, 20 s otherwise), and a page reading cut off is sent once more with twice the room (up to the model's
output limit), each only when its worst case fits this step's limit and the PDF's; never more than two charged calls a
page. page_reads_run.json keeps one finished entry per page, with both calls' costs in its cost_usd; the pages being read
are listed in `in_flight` with their worst case, and an interruption (Ctrl+C) keeps them in `stopped_in_flight`, counted
toward the PDF's limit (lib/costs.pages_paid), never as money spent.
A page already read with the same model, prompt and image is reused, never paid for again. --dry-run prints the
estimate, writes it to RUN_DIR/page_reads_estimate.json (what the app's cost estimate adds to the book's, lib/costs.py)
and stops; it writes the file before the cap check, so the app sees an estimate over the default cap and judges it by its
own limits. The step refuses before any call when the worst case passes --max-usd (default 3) or the credit.
The API key comes from OPENROUTER_API_KEY or the nearest .env, as for decide.py.
"""
import sys, os, re, json, time, base64, hashlib, argparse, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import pagereads, costhistory, costs, aisend

ap = argparse.ArgumentParser()
ap.add_argument('audit_dir'); ap.add_argument('run_dir')
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--model', default=None, help="OpenRouter model id (default: the run's work-order model, else decide.py's DEFAULT_MODEL)")
ap.add_argument('--max-usd', type=float, default=float(os.environ.get('PAGE_READS_MAX_USD') or 3), help='the limit on what this step could cost, in dollars')
ap.add_argument('--book-max-usd', type=float, default=float(os.environ.get('BOOK_MAX_USD') or costs.DEFAULT_LIMITS['per_book_usd']),
                help="the PDF's limit, shared with the work order and the language step (review 06, M2)")
ap.add_argument('--max-tokens', type=int, default=8000, help='output limit per page (a dense Hawaiian page took 2,300–3,400)')
args = ap.parse_args()

CHARS_PER_TOKEN, INPUT_MARGIN = 2.2, 1.25          # decide.py's calibration
PROMPT_FILE = next((p for p in (os.path.join(HERE, 'prompts', pagereads.PROMPT_NAME), os.path.join(os.path.dirname(HERE), 'prompts', pagereads.PROMPT_NAME))
                    if os.path.isfile(p)), None)
if not PROMPT_FILE: sys.exit(f'no prompt file {pagereads.PROMPT_NAME} in pipeline/prompts/ or prompts/')
prompt = open(PROMPT_FILE, encoding='utf-8').read(); prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()[:16]
listing = os.path.join(args.audit_dir, 'page_reads.json')
pages = (json.load(open(listing, encoding='utf-8')).get('pages') or []) if os.path.exists(listing) else []
EST_PATH = os.path.join(args.run_dir, 'page_reads_estimate.json')
if not pages:
    if os.path.exists(EST_PATH): os.remove(EST_PATH)          # an earlier estimate of pages this audit no longer lists
    print('page readings: no scanned Hawaiian pages in this PDF, nothing to read'); sys.exit(0)

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
load_env()
def get(url, key=None):
    h = {'User-Agent': 'pdfremproto1', **({'Authorization': f'Bearer {key}'} if key else {})}
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r: return json.load(r)

run_json = os.path.join(args.run_dir, 'run.json')
model = args.model or ((json.load(open(run_json, encoding='utf-8')).get('model') if os.path.exists(run_json) else None)) \
    or re.search(r"^DEFAULT_MODEL = '([^']+)'", open(os.path.join(HERE, 'decide.py'), encoding='utf-8').read(), re.M).group(1)
try:
    m = next((x for x in get('https://openrouter.ai/api/v1/models')['data'] if x['id'] == model), None)
except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e: sys.exit(f'could not reach OpenRouter to look up the model: {e}')
if m is None: sys.exit(f'refusing: model "{model}" is not on OpenRouter')
if 'image' not in ((m.get('architecture') or {}).get('input_modalities') or []): sys.exit(f'refusing: {model} cannot take images')
pin, pout = float(m['pricing']['prompt']), float(m['pricing']['completion'])

out_path = os.path.join(args.run_dir, 'page_reads_run.json')
done = json.load(open(out_path, encoding='utf-8')) if os.path.exists(out_path) else {}
from PIL import Image
todo, reused = [], []
for p in pages:
    img = os.path.join(args.audit_dir, p['image']); raw = open(img, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()[:16]
    prev = next((x for x in done.get('pages') or [] if x.get('page') == p['page']), None)
    if prev and prev.get('text') and prev.get('finish') == 'stop' and (prev.get('model'), prev.get('prompt_sha256'), prev.get('image_sha256')) == (model, prompt_sha, sha):
        reused.append(prev); continue
    w, h = Image.open(img).size
    t_in = (len(prompt) / CHARS_PER_TOKEN + w * h / 750) * INPUT_MARGIN
    todo.append({**p, 'raw': raw, 'image_sha256': sha, 'input_est': round(t_in / INPUT_MARGIN), 'worst': t_in * pin + args.max_tokens * pout})
worst = sum(t['worst'] for t in todo)
est = {'pages': len(pages), 'to_read': len(todo), 'reused': len(reused), 'worst_case_usd': round(worst, 4),
       'per_page_worst_usd': round(max((t['worst'] for t in todo), default=0), 4),
       'cap_usd': args.max_usd, 'price_per_million': [round(pin * 1e6, 4), round(pout * 1e6, 4)]}
if todo:                                           # the expected cost (#65): learned from past page readings, kind "page"; shown only
    try: est['expected'] = costhistory.expected([{'kind': 'page', 'input_est': t['input_est'], 'max_tokens': args.max_tokens} for t in todo], model, pin, pout, worst,
                                                cut_off=any(x.get('finish') == 'length' for x in done.get('pages') or []))
    except Exception as ex: est['expected'] = {'none': 'error'}; print(f'note: the expected cost could not be worked out ({type(ex).__name__})')
_kept = {}
if args.dry_run:                                   # one over its own cap is marked refused: never counted toward the PDF (review 08, H1)
    _new = {'schema': 'page-reads-estimate/1', 'model': model, 'prompt_sha256': prompt_sha, **est, 'images': {str(t['page']): t['image_sha256'] for t in todo}}
    _kept = {} if worst > args.max_usd else costs.kept_refusal(args.run_dir, 'page_reads', _new)   # decide.py's "left out" survives this dry run
    json.dump({**_new, **({'refused': {'why': 'cap', 'words': f'The page readings could cost up to ${worst:.2f}, more than their limit of ${args.max_usd:.2f}.'}} if worst > args.max_usd else _kept)},
              open(EST_PATH, 'w', encoding='utf-8'), indent=1)
print(f'page readings: {len(pages)} Hawaiian page{"s" if len(pages) != 1 else ""} ({len(reused)} already read) · {model}')
if todo: print('page readings: ' + costhistory.terminal_line(est['expected']))
print(f'page readings: Max Estimated Cost: ${worst:.2f} · Limit: ${args.max_usd:.2f}')
if worst > args.max_usd:
    sys.exit(f'refusing before any AI request: the page readings could cost up to ${worst:.2f}, more than the limit of ${args.max_usd:.2f}. To run it, raise the limit for this run: PAGE_READS_MAX_USD={int(worst) + 1}')
if _kept and os.path.exists(os.path.join(args.run_dir, 'response.json')):   # the work order has run: the readings stay left out
    sys.exit(f'refusing before any AI request: {_kept["refused"].get("words")}')
_ref = costs.refused(args.run_dir, 'page_reads') if not args.dry_run and todo else None
if _ref and _ref.get('why') == 'book':             # decide.py left them out of the PDF's estimate: they stay out (review 08, H1)
    sys.exit(f'refusing before any AI request: {_ref.get("words") or "the page readings were left out of this PDF\'s estimate"}')
_spent = costs.book_spent(args.run_dir)
if not args.dry_run and _spent + worst > args.book_max_usd:
    sys.exit(f'refusing before any AI request: this PDF has spent ${_spent:.2f} and the page readings could add ${worst:.2f}, more than the '
             f'limit of ${args.book_max_usd:.2f} per PDF. To run it, raise the limit for this run: BOOK_MAX_USD={int(_spent + worst) + 1}')
# cost_usd is the step's running total: a page read again after a cut-off keeps the first charge, a page reused adds nothing.
# What an earlier attempt left in flight, or stopped, or a call of it with no reply in time not reused here, is kept at its
# worst case (review 02 M2).
_kept_ids = {id(x) for x in reused}
_stopped = list(done.get('stopped_in_flight') or []) + aisend.stopped(done.get('in_flight') or [], 'in flight when the step stopped; any charge is not known') \
    + [{'page': x.get('page'), 'worst_usd': x['worst_usd'], 'stopped': False, 'note': 'no reply in time in an earlier attempt; any charge is not known'}
       for x in done.get('pages') or [] if isinstance(x, dict) and x.get('worst_usd') and id(x) not in _kept_ids]
rec = {'schema': 'page-reads/1', 'model': model, 'prompt_file': os.path.basename(PROMPT_FILE), 'prompt_sha256': prompt_sha, 'estimate': est,
       'pages': sorted(reused, key=lambda x: x['page']), 'cost_usd': round(max(done.get('cost_usd') or 0, sum(x.get('cost_usd') or 0 for x in done.get('pages') or [])), 6),
       **({'stopped_in_flight': _stopped} if _stopped else {})}
if args.dry_run: print('dry run: nothing sent'); sys.exit(0)
# the doubled room after a cut-off (L5 of review 02): twice --max-tokens, up to the model's output limit; none when that
# gives no more room
MAX_OUT = (m.get('top_provider') or {}).get('max_completion_tokens') or m.get('context_length') or args.max_tokens
DOUBLED = min(2 * args.max_tokens, int(MAX_OUT))
if not todo: print('page readings: every page was read before, no cost')
else:
    key = os.environ.get('OPENROUTER_API_KEY') or sys.exit('no OPENROUTER_API_KEY: put it in .env or export it')
    try:
        k = get('https://openrouter.ai/api/v1/key', key).get('data', {}); credit = k.get('limit_remaining')
        if credit is not None and float(credit) < worst: sys.exit(f'refusing: the page readings could cost up to ${worst:.2f}, more than the ${float(credit):.2f} of credit left')
    except (urllib.error.URLError, TimeoutError, ValueError): pass
    started = time.strftime('%Y-%m-%dT%H:%M:%S')
    try: digest = json.load(open(os.path.join(args.audit_dir, 'digest.json'), encoding='utf-8'))
    except (OSError, ValueError): digest = None
    R_ = aisend.Record(out_path, rec); R_.change()
    budget = aisend.Budget({'page readings': (args.max_usd, 0.0), 'per-PDF': (args.book_max_usd, _spent)}, {str(t['page']): t['worst'] for t in todo})
    http = aisend.openrouter(key, 600); say = aisend.locked(print); fin = [0]
    def flying(d, page): return next((e for e in d.setdefault('in_flight', []) if e['page'] == page), None)
    def read(t):
        page, k_ = t['page'], str(t['page'])
        body = {'model': model, 'max_tokens': args.max_tokens, 'temperature': 0, 'usage': {'include': True}, 'provider': {'data_collection': 'deny'},
                'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(t['raw']).decode()}},
                                                          {'type': 'text', 'text': prompt}]}]}
        R_.change(lambda d: d.setdefault('in_flight', []).append({'page': page, 'worst_usd': round(t['worst'], 4)}))
        def on_retry(k, known, w, cut_off=False):
            def f(d):
                e = flying(d, page)
                if e is not None: e.update(paid_usd=round(known, 6), worst_usd=round(w, 4), **({'cut_off': True} if cut_off else {}))
            R_.change(f)
        r = aisend.call(http, body, k_, t['worst'], budget, label=f'page {page}', say=say, on_retry=on_retry)
        calls = list(r['calls']); known, unknown = r['cost_usd'], r['worst_usd']
        f_ = r['final']; doubled = None
        if f_.get('finish') == 'length':
            charged = sum(1 for c in calls if c.get('cost') or c.get('worst_usd'))
            w2 = t['worst'] - args.max_tokens * pout + DOUBLED * pout
            why = (f'this page has already been charged twice' if charged >= 2 else
                   f'the model gives no more than {MAX_OUT:,} output tokens' if DOUBLED <= args.max_tokens else None)
            if why is None:
                ok, no = budget.try_reserve(k_, w2)
                if not ok: why = f'the {no} limit has no room for a longer reading'
            if why: f_['why'] = f'cut off at {args.max_tokens:,} output tokens; not sent again: {why}'; say(f'  page {page}: {f_["why"]}')
            else:
                say(f'  page {page}: cut off at {args.max_tokens:,} output tokens; sending it once more with room for {DOUBLED:,}')
                on_retry(k_, known, unknown + w2, cut_off=True)
                r2 = aisend.call(http, dict(body, max_tokens=DOUBLED), k_, w2, budget, label=f'page {page} (twice the room)', say=say, retry=False)
                for c in r2['calls']: c.update(attempt=len(calls) + 1, doubled=True); calls.append(c)
                known, unknown, f_ = round(known + r2['cost_usd'], 6), round(unknown + r2['worst_usd'], 4), r2['final']
                doubled = {'max_tokens': DOUBLED, 'cost_usd': r2['cost_usd'], 'outcome': 'done' if f_.get('finish') == 'stop' else 'failed'}
        budget.release(k_)
        x = {'page': page, 'label': t.get('label'), 'text': f_.get('text') or '', 'finish': f_.get('finish'),
             'model': model, 'prompt_sha256': prompt_sha, 'image_sha256': t['image_sha256'], 'input_tokens': f_.get('input_tokens'),
             'output_tokens': f_.get('output_tokens'), 'cost_usd': known, 'seconds': round(sum(c.get('seconds') or 0 for c in calls), 1),
             'sent_at': calls[0].get('sent_at'), 'finished_at': calls[-1].get('finished_at')}
        if unknown: x['worst_usd'] = unknown                       # a call with no reply in time: its charge is not known
        if len(calls) > 1 or calls[0].get('why') or f_.get('why'):
            x['calls'] = [{k: c.get(k) for k in ('attempt', 'seconds', 'sent_at', 'finished_at', 'cost', 'finish', 'error', 'why', 'worst_usd', 'doubled') if c.get(k) is not None} for c in calls]
        if doubled: x['cut_off_retry'] = doubled
        if 'error' in f_: x['error'] = f_['error']
        def store(d):                              # one finished entry per page, in page order; it leaves in_flight
            d['in_flight'] = [e for e in d.get('in_flight') or [] if e['page'] != page]
            if not d['in_flight']: d.pop('in_flight')
            d['pages'] = sorted([y for y in d['pages'] if y.get('page') != page] + [x], key=lambda y: y['page'])
            d['cost_usd'] = round(d['cost_usd'] + (x['cost_usd'] or 0), 6)
        R_.change(store)
        return x
    def on_done(t, x):
        fin[0] += 1
        say(f'  page {x["page"]}: ' + (f'no reply: {x["error"]["message"] or x["error"]["code"]}' if 'error' in x else f'{x["output_tokens"]} tokens, ${x["cost_usd"] or 0:.4f}')
            + ('' if x['finish'] == 'stop' or 'error' in x else f' · cut off ({x["finish"]}): not used') + f' ({fin[0]} of {len(todo)} done)')
        if x['finish'] == 'stop' and x['input_tokens'] and x['output_tokens']:   # the expected cost's history (#65); a cut-off page teaches nothing
            try:
                costhistory.append({'kind': 'page', 'model': model, 'prompt': os.path.basename(PROMPT_FILE), 'input_est': t['input_est'], 'input_billed': x['input_tokens'], 'output': x['output_tokens'],
                                    'images': 1, 'forms': 0, 'date': started, 'book': costhistory.book_id(args.run_dir, digest), 'pass': str(t['page']), 'attempt': len(x.get('calls') or [1])})
            except Exception: pass                 # a paid run is never stopped by the history
    def on_stop(started_):                         # an interruption: nothing queued starts; what was in flight counts at its worst case
        R_.close(lambda d: d.update(stopped_in_flight=list(d.get('stopped_in_flight') or []) + aisend.stopped(d.pop('in_flight', None) or [])))
    aisend.run(todo, read, aisend.cap(), on_done=on_done, on_stop=on_stop)
rec['pages'].sort(key=lambda x: x['page'])
json.dump(rec, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# into the work order: only complete replies
wo_path = os.path.join(args.run_dir, 'workorder.json')
if os.path.exists(wo_path):
    wo = json.load(open(wo_path, encoding='utf-8'))
    wo['page_readings'] = [{'page': x['page'], 'text': x['text']} for x in rec['pages'] if x.get('finish') == 'stop' and (x.get('text') or '').strip()]
    if not wo['page_readings']: del wo['page_readings']
    json.dump(wo, open(wo_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'page readings: {len([x for x in rec["pages"] if x.get("finish") == "stop"])} of {len(pages)} pages read · ${rec["cost_usd"]:.4f} spent on this step')
