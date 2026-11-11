"""read_pages.py: whole-page AI readings of scanned Hawaiian pages (issue #49). PAID, its own step after decide.py.

    python read_pages.py AUDIT_DIR RUN_DIR [--dry-run] [--model ID] [--max-usd N]

The audit lists the scanned pages where most words have Hawaiian shape (AUDIT_DIR/page_reads.json, images in
page_reads/). Tesseract has no Hawaiian model, so their OCR lost the ʻokina and kahakō. Each page image goes to the
model in its own request, with prompts/page_reading_v1.md: it transcribes the page exactly as printed. The readings are
added to RUN_DIR/workorder.json as `page_readings` [{page, text}]; apply.py gives each OCR word its reading at its own
place (ActualText), and the report asks a person who reads Hawaiian to check every page.

    RUN_DIR/page_reads_run.json   model, prompt, the estimate, and each page's reply, usage and cost

A page already read with the same model, prompt and image is reused, never paid for again. --dry-run prints the
estimate, writes it to RUN_DIR/page_reads_estimate.json (what the app's cost estimate adds to the book's, lib/costs.py)
and stops; it writes the file before the cap check, so the app sees an estimate over the default cap and judges it by its
own limits. The step refuses before any call when the worst case passes --max-usd (default 3) or the credit.
The API key comes from OPENROUTER_API_KEY or the nearest .env, as for decide.py.
"""
import sys, os, re, json, time, base64, hashlib, argparse, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import pagereads, costhistory

ap = argparse.ArgumentParser()
ap.add_argument('audit_dir'); ap.add_argument('run_dir')
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--model', default=None, help="OpenRouter model id (default: the run's work-order model, else decide.py's DEFAULT_MODEL)")
ap.add_argument('--max-usd', type=float, default=float(os.environ.get('PAGE_READS_MAX_USD') or 3), help='the limit on what this step could cost, in dollars')
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
if args.dry_run:
    json.dump({'schema': 'page-reads-estimate/1', 'model': model, 'prompt_sha256': prompt_sha, **est,
               'images': {str(t['page']): t['image_sha256'] for t in todo}}, open(EST_PATH, 'w', encoding='utf-8'), indent=1)
print(f'page readings: {len(pages)} Hawaiian page{"s" if len(pages) != 1 else ""} ({len(reused)} already read) · {model}')
if todo: print('page readings: ' + costhistory.terminal_line(est['expected']))
print(f'page readings: Max Estimated Cost: ${worst:.2f} · Limit: ${args.max_usd:.2f}')
if worst > args.max_usd:
    sys.exit(f'refusing before any AI request: the page readings could cost up to ${worst:.2f}, more than the limit of ${args.max_usd:.2f}. To run it, raise the limit for this run: PAGE_READS_MAX_USD={int(worst) + 1}')
# cost_usd is the step's running total: a page read again after a cut-off keeps the first charge, a page reused adds nothing
rec = {'schema': 'page-reads/1', 'model': model, 'prompt_file': os.path.basename(PROMPT_FILE), 'prompt_sha256': prompt_sha, 'estimate': est,
       'pages': sorted(reused, key=lambda x: x['page']), 'cost_usd': round(max(done.get('cost_usd') or 0, sum(x.get('cost_usd') or 0 for x in done.get('pages') or [])), 6)}
if args.dry_run: print('dry run: nothing sent'); sys.exit(0)
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
    for t in todo:
        body = {'model': model, 'max_tokens': args.max_tokens, 'temperature': 0, 'usage': {'include': True}, 'provider': {'data_collection': 'deny'},
                'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(t['raw']).decode()}},
                                                          {'type': 'text', 'text': prompt}]}]}
        req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(body).encode(),
                                     headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'X-Title': 'UH PDF remediation prototype'})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=600) as r: d = json.load(r)
        except urllib.error.HTTPError as e:
            print(f'  page {t["page"]}: OpenRouter error {e.code}: {e.read().decode("utf-8", "replace")[:300]} (not retried)'); continue
        except (urllib.error.URLError, TimeoutError) as e:
            print(f'  page {t["page"]}: no reply ({e}); not retried'); continue
        u = d.get('usage') or {}; ch = (d.get('choices') or [{}])[0]
        x = {'page': t['page'], 'label': t.get('label'), 'text': (ch.get('message') or {}).get('content') or '', 'finish': ch.get('finish_reason'),
             'model': model, 'prompt_sha256': prompt_sha, 'image_sha256': t['image_sha256'], 'input_tokens': u.get('prompt_tokens'),
             'output_tokens': u.get('completion_tokens'), 'cost_usd': u.get('cost'), 'seconds': round(time.time() - t0, 1)}
        rec['pages'].append(x); rec['cost_usd'] = round(rec['cost_usd'] + (x['cost_usd'] or 0), 6)
        print(f'  page {t["page"]}: {x["output_tokens"]} tokens, ${x["cost_usd"] or 0:.4f}' + ('' if x['finish'] == 'stop' else f' · cut off ({x["finish"]}): not used'))
        json.dump(rec, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)   # after each page: a stop keeps what was paid for
        if x['finish'] == 'stop' and x['input_tokens'] and x['output_tokens']:                 # the expected cost's history (#65); a cut-off page teaches nothing
            try:
                costhistory.append({'kind': 'page', 'model': model, 'prompt': os.path.basename(PROMPT_FILE), 'input_est': t['input_est'], 'input_billed': x['input_tokens'], 'output': x['output_tokens'],
                                    'images': 1, 'forms': 0, 'date': started, 'book': costhistory.book_id(args.run_dir, digest), 'pass': str(t['page']), 'attempt': 1})
            except Exception: pass                 # a paid run is never stopped by the history
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
