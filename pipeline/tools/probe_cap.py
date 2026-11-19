"""probe_cap.py: how many AI requests OpenRouter takes at once before it refuses some (#135 (parallel requests)).
PAID unless --dry-run, a few cents: tiny requests, no book text.

    python3 tools/probe_cap.py --dry-run [--waves 50,100,200]       nothing sent: the worst case per wave and in all
    python3 tools/probe_cap.py --out DIR [--waves 50,100,200] [--yes]

Each wave sends N identical tiny requests at once (one line of prompt, no book text, max_tokens 20, the language step's
model, provider data_collection deny), waits for every reply, then starts the next wave. It stops at the first 429 or
other failure (no request is retried: the point is to see where refusals begin), or when the next wave's worst case
would pass --max-usd (default $1, for all waves together). Writes DIR/calls.json (per request: wave, send and finish
time in seconds from the start, HTTP status, tokens, cost, finish reason) and DIR/summary.json (per wave: requests,
peak in flight, wall time, statuses, cost; where it stopped and why). Refuses a DIR that already holds a summary.json.
The API key comes from OPENROUTER_API_KEY or the nearest .env and is never printed.
"""
import sys, os, json, time, argparse, urllib.request, urllib.error
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # pipeline/
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tools'))
from lib import aisend, langreq
import cap_sweep

MODEL = 'anthropic/claude-sonnet-5.5'                 # name_languages.py's DEFAULT_MODEL
PROMPT = 'Reply with the single word: ok'
MAX_TOKENS = 20
PRICE = (2.0e-6, 10.0e-6)                             # $ per token, in and out: the dry run's prices (Cadatest2's record); a run reads today's

def body():
    return {'model': MODEL, 'max_tokens': MAX_TOKENS, 'messages': [{'role': 'user', 'content': PROMPT}],
            'provider': {'data_collection': 'deny'}, 'usage': {'include': True}}

def worst_each(pin, pout):
    """One request's worst case: its input as the language step counts input (with its margin), its full max_tokens."""
    return int(langreq.tokens(PROMPT) * langreq.INPUT_MARGIN + 10) * pin + MAX_TOKENS * pout

def dry_run(waves, limit):
    w = worst_each(*PRICE); total = 0.0
    print(f'dry run: nothing sent · {MODEL} · {len(waves)} wave(s) of tiny requests (max_tokens {MAX_TOKENS}, no book text)')
    for n in waves:
        total += n * w
        print(f'  wave of {n}: worst case ${n * w:.4f}' + ('' if total <= limit else f' · would pass the ${limit:.2f} limit: not sent'))
    print(f'  in all: {sum(waves)} requests · worst case ${sum(waves) * w:.4f} · limit ${limit:.2f}')

def run(waves, out, limit, yes):
    if os.path.exists(os.path.join(out, 'summary.json')): sys.exit(f'refusing: {out} already holds a run (summary.json)')
    key = cap_sweep.load_key()
    try:
        with urllib.request.urlopen(urllib.request.Request('https://openrouter.ai/api/v1/models', headers={'User-Agent': 'pdfremproto1'}), timeout=30) as r_:
            m = next((x for x in json.load(r_)['data'] if x['id'] == MODEL), None)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e: sys.exit(f'could not reach OpenRouter to look up the model: {e}')
    if m is None: sys.exit(f'refusing: model "{MODEL}" is not on OpenRouter')
    w = worst_each(float(m['pricing']['prompt']), float(m['pricing']['completion']))
    print(f'{len(waves)} wave(s): {", ".join(map(str, waves))} requests · worst case ${sum(waves) * w:.4f} · limit ${limit:.2f}')
    if not yes and input('send them? [y/N] ').strip().lower() != 'y': sys.exit('not sent')
    os.makedirs(out, exist_ok=True)
    raw = json.dumps(body()).encode(); t0 = time.time(); calls, per_wave, spent, stop = [], [], 0.0, None
    for k, n in enumerate(waves, 1):
        if spent + n * w > limit: stop = f'wave {k} ({n}) could pass the ${limit:.2f} limit: not sent'; break
        s = cap_sweep.Sender(key, t0, timeout=120); logs = [[] for _ in range(n)]; w0 = time.time()
        aisend.run(range(n), lambda i: s(raw, logs[i]), n)
        rows = [dict(r, wave=k) for lg in logs for r in lg]; calls += rows
        cost = round(sum(r.get('cost') or 0 for r in rows), 6); spent += cost
        bad = [r for r in rows if r.get('status') != 200 or r.get('finish') is None]
        st = {}
        for r in rows: st[str(r.get('status'))] = st.get(str(r.get('status')), 0) + 1
        per_wave.append({'wave': k, 'requests': n, 'peak_in_flight': s.peak, 'wall_seconds': round(time.time() - w0, 1), 'statuses': st,
                         'status_429': st.get('429', 0), 'failed': len(bad), 'cost_usd': cost,
                         'median_seconds': sorted(r['finished'] - r['sent'] for r in rows)[len(rows) // 2]})
        print(f'wave {k}: {n} at once · peak {s.peak} · {per_wave[-1]["wall_seconds"]:.1f} s · statuses {st} · ${cost:.4f}')
        if bad: stop = f'wave {k}: {len(bad)} request(s) refused or failed ({st}); no next wave'; break
    json.dump(calls, open(os.path.join(out, 'calls.json'), 'w'), indent=1)
    json.dump({'model': MODEL, 'waves': per_wave, 'cost_usd': round(spent, 6), 'stopped': stop}, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    print(f'in all: ${spent:.4f}' + (f' · stopped: {stop}' if stop else ' · every wave finished with no refusal'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--out'); ap.add_argument('--yes', action='store_true')
    ap.add_argument('--waves', default='50,100,200'); ap.add_argument('--max-usd', type=float, default=1.0)
    a = ap.parse_args(); waves = [int(x) for x in a.waves.split(',')]
    if a.dry_run: return dry_run(waves, a.max_usd)
    if not a.out: sys.exit('a paid run needs --out DIR (or --dry-run)')
    run(waves, a.out, a.max_usd, a.yes)

if __name__ == '__main__': main()
