"""handedit_check.py: the AI's check of a PDF edited by hand (issue #100). PAID, once, and only when you say yes.

    python handedit_check.py RUN_DIR [--dry-run] [--reply FILE] [--model ID] [--max-usd N] [--book-max-usd N] [--yes]

RUN_DIR is a run made by `handedit.py import … --to review` that waits for its first review. One request goes to the AI with
only what the import found (lib/hecheck.py): the figures that hold a new image or lost their tag (the ones with a card in the
review page's Edited by Hand section), and the pages whose text reads differently, with their old and new wording and a picture
of the page. The answers are suggestions for those cards, marked as the AI's; a person approves or changes each one, and nothing
is applied without that review.

    RUN_DIR/_handedit/ai_check.json            the request's answer, its cost and what was sent (a later run with the same
                                               figures, pages, model and instructions reuses it at no cost)
    RUN_DIR/_handedit/ai_check_estimate.json   the estimate (what the app's Spend shows, lib/costs.py)

--dry-run prints and saves the estimate and stops (ESTIMATE=1 does the same). The step refuses before any request when its worst
case passes --max-usd (default MAX_USD, else $2), when the PDF's spending so far plus it passes --book-max-usd (default
BOOK_MAX_USD, else $8), or when the credit is lower. It asks y/N unless AUTO=1 or --yes (the app's Spend sets AUTO=1).
--reply FILE uses a saved answer instead of a request (no cost, no network; the tests and tools/handedit_case.py). Relative paths
are taken from the folder the command runs in. The API key comes from OPENROUTER_API_KEY or the nearest .env, as for decide.py.
Exit 1: refused or failed, with the reason.
"""
import sys, os, re, json, time, argparse, hashlib, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import hecheck, costs

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

def refresh(R):
    """The saved answers into the review page's data (review_items.json), so the page and a later apply read the same defaults."""
    try:
        from review import core
        core.refresh_ai_check(R)
    except Exception as e: print(f'note: the review page\'s data was not updated ({type(e).__name__}: {e}); it reads the answers when it opens')

def num(name, default):
    try: return float(os.environ.get(name) or default)
    except ValueError: sys.exit(f'refused: {name} must be a number: {os.environ.get(name)}')

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir'); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--reply', default=None)
    ap.add_argument('--model', default=None); ap.add_argument('--yes', action='store_true')
    ap.add_argument('--max-usd', type=float, default=None); ap.add_argument('--book-max-usd', type=float, default=None)
    args = ap.parse_args(argv)
    R = os.path.abspath(args.run_dir)                         # from the folder the command runs in, as run_api.sh's paths are (#144)
    reply_file = os.path.abspath(args.reply) if args.reply else None
    dry = args.dry_run or bool(os.environ.get('ESTIMATE'))
    max_usd = args.max_usd if args.max_usd is not None else num('MAX_USD', costs.DEFAULT_LIMITS['per_call_usd'])
    book_max = args.book_max_usd if args.book_max_usd is not None else num('BOOK_MAX_USD', costs.DEFAULT_LIMITS['per_book_usd'])
    prompt_file = next((p for p in (os.path.join(HERE, 'prompts', 'handedit_check_v1.md'), os.path.join(os.path.dirname(HERE), 'prompts', 'handedit_check_v1.md'))
                        if os.path.isfile(p)), None)
    if not prompt_file: sys.exit('refused: no prompt file handedit_check_v1.md in pipeline/prompts/ or prompts/')
    prompt = open(prompt_file, encoding='utf-8').read()
    model = args.model or re.search(r"^DEFAULT_MODEL = '([^']+)'", open(os.path.join(HERE, 'decide.py'), encoding='utf-8').read(), re.M).group(1)
    try: p = hecheck.plan(R, prompt, os.path.basename(prompt_file), model)
    except hecheck.Stop as e: sys.exit(f'refused: {e}')
    print(f'AI check of the hand edit: {len(p["items"])} figure(s), {len(p["texts"])} page(s) of changed text · {model}')
    if p.get('note'): print('note: ' + p['note'])
    s = hecheck.saved(R)
    if hecheck.reusable(s, p) and not reply_file:
        print(f'AI check of the hand edit: already made with the same figures, pages, model and instructions: no cost (${s.get("cost_usd") or 0:.4f} was paid before)')
        refresh(R); return 0
    if reply_file:
        try: text = open(reply_file, encoding='utf-8').read()
        except OSError as e: sys.exit(f'refused: the saved reply {reply_file} cannot be read ({e})')
        out = hecheck.from_reply(R, p, text)
        print(f'AI check of the hand edit: saved reply used, no cost ({hecheck.words(out)})'); refresh(R); return 0
    load_env()
    key = os.environ.get('OPENROUTER_API_KEY')
    try:
        m = next((x for x in get('https://openrouter.ai/api/v1/models')['data'] if x['id'] == model), None)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e: sys.exit(f'refused: could not reach OpenRouter to look up the model: {e}')
    if m is None: sys.exit(f'refused: model "{model}" is not on OpenRouter')
    if 'image' not in ((m.get('architecture') or {}).get('input_modalities') or []): sys.exit(f'refused: {model} cannot take images')
    pin, pout = float(m['pricing']['prompt']), float(m['pricing']['completion'])
    est = hecheck.estimate(p, pin, pout, max_usd); worst = est['worst_case_usd']
    credit = None
    if key:
        try: credit = get('https://openrouter.ai/api/v1/key', key).get('data', {}).get('limit_remaining')
        except (urllib.error.URLError, TimeoutError, ValueError): credit = None
    if isinstance(credit, (int, float)) and not isinstance(credit, bool): est['credit_available_usd'] = round(float(credit), 4)
    est_path = os.path.join(R, hecheck.ESTIMATE)
    with open(est_path, 'w', encoding='utf-8') as f: json.dump(est, f, indent=1)
    spent = costs.book_spent(R)
    print(f'AI check of the hand edit: Max Estimated Cost: ${worst:.2f} · Limit: ${max_usd:.2f}')
    if worst > max_usd:
        sys.exit(f'refused before any AI request: the check could cost up to ${worst:.2f}, more than the limit of ${max_usd:.2f}. '
                 f'To run it, raise the limit for this run: MAX_USD={int(worst) + 1}')
    if not dry and spent + worst > book_max:
        sys.exit(f'refused before any AI request: this PDF has spent ${spent:.2f} and the check could add ${worst:.2f}, more than the limit of '
                 f'${book_max:.2f} per PDF. To run it, raise the limit for this run: BOOK_MAX_USD={int(spent + worst) + 1}')
    if dry: print('dry run: nothing sent'); refresh(R); return 0               # the page shows the estimate
    if not key: sys.exit('refused: no OPENROUTER_API_KEY: put it in a .env file in pipeline/ or a folder above it, or export it')
    if credit is not None and float(credit) < worst: sys.exit(f'refused: the check could cost up to ${worst:.2f}, more than the ${float(credit):.2f} of credit left')
    if not (os.environ.get('AUTO') or args.yes):
        try: ok = input(f'Send this to the AI now (up to ${worst:.2f})? [y/N] ')
        except EOFError: ok = 'n'
        if not ok.strip().lower().startswith('y'): print('not sent'); return 0
    def send(body):
        rq = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(body).encode(),
                                    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'X-Title': 'UH PDF remediation prototype'})
        t0 = time.time()
        try:
            with urllib.request.urlopen(rq, timeout=600) as r: return {'resp': json.load(r), 'seconds': round(time.time() - t0, 1)}
        except urllib.error.HTTPError as e: return {'resp': None, 'code': e.code, 'message': e.read().decode('utf-8', 'replace')[:300]}
        except (urllib.error.URLError, TimeoutError) as e: return {'resp': None, 'code': 'no reply', 'message': str(e), 'timeout': True}
    try: out = hecheck.execute(R, p, send)
    except hecheck.Stop as e: sys.exit(f'failed: {e}')
    print(f'AI check of the hand edit: ${out.get("cost_usd") or 0:.4f} · {hecheck.words(out)}')
    refresh(R)
    return 0 if out['outcome'] == 'done' else 1

if __name__ == '__main__': sys.exit(main())
