"""cap_sweep.py: how many language requests one PDF should send at once (#135 (parallel requests): AI_PARALLEL's default).
PAID unless --dry-run: it sends a finished run's saved language requests again, byte for byte, through lib/aisend.py.

    python3 tools/cap_sweep.py --dry-run --caps 4,8,15 FOLDER [FOLDER …]          nothing sent: the amounts per cap and in all
    python3 tools/cap_sweep.py --cap 8 --out DIR FOLDER [FOLDER …]                one run at cap 8 (asks first unless --yes)

FOLDER: a finished run folder with language_requests/NNN.request.json and record.json (its language_run). Each file is
sent as saved (it already carries provider data_collection deny; a file without it is refused, nothing sent), with
the language step's own retry rule: once more after 60 s for a 429, 20 s otherwise, when its worst case still fits the
limit (LANGUAGE_MAX_USD, default 6: checked before anything is sent, and each retry reserved against it, as the step
does). A reply cut off is recorded, not resent: the step's resend of a cut-off reply's undecided forms needs the book's
own forms, which this tool doesn't build.

Several folders: each folder is one PDF with its own runner at the cap, all side by side, as a batch's JOBS run them
(cap × folders in flight at most), each against its own limit. The amounts in --dry-run are per folder and in all.

Writes, under DIR (refused if DIR already holds a summary.json):
    replies/<folder>/NNN.reply.json   each reply as OpenRouter returned it (book text: never commit)
    calls.json                        per request: every call's send and finish time (seconds from the start), HTTP
                                      status, error, the pause before a retry, tokens, cost, finish reason
    summary.json                      per run: wall time, peak in flight, total cost; per reply, today's parse (decided,
                                      dropped by code) and rule U's gain over the old echo rule, split into answers kept
                                      by the loose key and kept only through a marked text
    forms.json                        with --forms FILE (one word form a line): each listed form's answer in these replies
The API key comes from OPENROUTER_API_KEY or the nearest .env and is never printed.
"""
import sys, os, json, time, glob, threading, argparse, urllib.request, urllib.error, socket
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # pipeline/
sys.path.insert(0, HERE)
from lib import aisend, langreq, costs

def requests_of(folder):
    """[(n, path, raw bytes, body)] of a folder's saved first requests, in order (resends, NNNr, are left out)."""
    out = []
    for p in sorted(glob.glob(os.path.join(folder, 'language_requests', '[0-9][0-9][0-9].request.json'))):
        raw = open(p, 'rb').read(); body = json.loads(raw)
        if (body.get('provider') or {}).get('data_collection') != 'deny': sys.exit(f'refusing: {p} does not carry provider data_collection deny')
        out.append((int(os.path.basename(p)[:3]), p, raw, body))
    if not out: sys.exit(f'no saved language requests in {folder}/language_requests')
    return out

def record_of(folder):
    r = json.load(open(os.path.join(folder, 'record.json'), encoding='utf-8'))
    lr = r.get('language_run') or {}
    if not lr.get('requests'): sys.exit(f'{folder}/record.json has no language_run requests')
    return lr

def worst_of(body, pin, pout):
    """The language step's worst case for one saved request: its input as langreq.size counts it, its full max_tokens."""
    ins = int((langreq.tokens(body['messages'][0]['content']) + langreq.tokens(body['messages'][1]['content'])) * langreq.INPUT_MARGIN) + 10
    return ins * pin + body['max_tokens'] * pout

def plan(folders, prices=None):
    """Per folder: its requests, their worst cases (at the record's prices, or `prices`), and what the saved run cost."""
    out = []
    for f in folders:
        lr = record_of(f); reqs = requests_of(f)
        pin, pout = prices or (x / 1e6 for x in lr['estimate']['price_per_million'])
        w = {n: worst_of(b, pin, pout) for n, _, _, b in reqs}
        out.append({'folder': f, 'name': os.path.basename(os.path.normpath(f)), 'reqs': reqs, 'worst': w, 'worst_usd': round(sum(w.values()), 4),
                    'saved_usd': round(lr.get('cost_usd') or 0, 6), 'saved_seconds': round(sum(x.get('seconds') or 0 for x in lr['requests']), 1),
                    'model': lr.get('model'), 'n': len(reqs)})
    return out

def dry_run(folders, caps, limit):
    P = plan(folders)
    print(f'dry run: nothing sent · {len(P)} folder(s), {sum(p["n"] for p in P)} requests')
    for p in P:
        print(f'  {p["name"]}: {p["n"]} requests · {p["model"]} · the saved run cost ${p["saved_usd"]:.2f} in {p["saved_seconds"]:.0f} s of calls (one at a time)'
              f' · worst case of the first sends ${p["worst_usd"]:.2f} · with every retry, at most the limit, ${limit:.2f}')
        if p['worst_usd'] > limit: print(f'  {p["name"]}: REFUSED at any cap: the worst case passes the limit of ${limit:.2f}')
    exp, worst, ceil = sum(p['saved_usd'] for p in P), sum(p['worst_usd'] for p in P), limit * len(P)
    for c in caps:
        print(f'  cap {c}: expected ${exp:.2f} (the saved run\'s cost, the same requests) · worst case ${worst:.2f} (first sends) · ${ceil:.2f} with retries (the limit)')
    print(f'  in all, {len(caps)} run(s): expected ${exp * len(caps):.2f} · worst case ${worst * len(caps):.2f} (first sends) · ${ceil * len(caps):.2f} with retries')

# ------------------------------------------------------------------ a paid run
def load_key():
    d = HERE
    while not os.environ.get('OPENROUTER_API_KEY'):
        p = os.path.join(d, '.env')
        if os.path.isfile(p):
            for line in open(p, encoding='utf-8'):
                k, _, v = line.strip().partition('=')
                if k.strip().removeprefix('export ').strip() == 'OPENROUTER_API_KEY' and v: os.environ['OPENROUTER_API_KEY'] = v.strip().strip('"').strip("'")
            break
        if os.path.dirname(d) == d: break
        d = os.path.dirname(d)
    return os.environ.get('OPENROUTER_API_KEY') or sys.exit('no OPENROUTER_API_KEY: put it in .env or export it')

class Sender:
    """send(raw bytes) for aisend.call: the saved bytes as they are, every call logged (times from t0), the peak in flight."""
    def __init__(self, key, t0, timeout=900):
        self.key, self.t0, self.timeout, self.lock, self.now, self.peak = key, t0, timeout, threading.Lock(), 0, 0
    def __call__(self, raw, log):
        rq = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=raw,
                                    headers={'Authorization': f'Bearer {self.key}', 'Content-Type': 'application/json', 'X-Title': 'UH PDF remediation prototype'})
        with self.lock: self.now += 1; self.peak = max(self.peak, self.now)
        row = {'sent': round(time.time() - self.t0, 2)}; out = None
        try:
            with urllib.request.urlopen(rq, timeout=self.timeout) as r_: row['status'] = r_.status; out = {'resp': json.load(r_)}
        except urllib.error.HTTPError as e:
            row['status'] = e.code; err = e.read().decode('utf-8', 'replace')
            try: msg = (json.loads(err).get('error') or {}).get('message')
            except ValueError: msg = err[:300]
            out = {'resp': None, 'code': e.code, 'message': msg}
        except (TimeoutError, socket.timeout): row['status'] = 'timeout'; out = {'resp': None, 'timeout': True}
        except (urllib.error.URLError, OSError, ValueError) as e: row['status'] = 'network'; out = {'resp': None, 'code': 'network', 'message': str(e)[:300]}
        finally:
            with self.lock: self.now -= 1
        row['finished'] = round(time.time() - self.t0, 2); out['seconds'] = round(row['finished'] - row['sent'], 1)
        u = ((out.get('resp') or {}).get('usage') or {}); ch = ((out.get('resp') or {}).get('choices') or [{}])[0]
        row.update(input_tokens=u.get('prompt_tokens'), output_tokens=u.get('completion_tokens'), cost=u.get('cost'), finish=ch.get('finish_reason'))
        if out.get('message'): row['error'] = str(out['message'])[:300]
        log.append(row)
        return out

def analyse(text, body, watch, name, n):
    """Today's parse of one reply, and rule U's gain: answers the old echo rule (spacing and case only) would drop that
    rule U keeps, split by how (the loose key of the item's form, or only a marked text)."""
    req = json.loads(body['messages'][1]['content']); forms = {it['id']: it['form'] for it in req['items']}
    marks = langreq.marks_of(req)
    d, dr = langreq.parse(text, set(forms), forms=forms, marks=marks)
    codes = {}
    for e in dr: codes[e.get('code')] = codes.get(e.get('code'), 0) + 1
    raw = []
    try: raw = (json.loads(text[text.index('{'):text.rindex('}') + 1]) or {}).get('decisions') or []
    except ValueError: pass
    loose = mark = 0
    for x in raw:
        i = str(x.get('id')) if isinstance(x, dict) else None
        if i not in d or 'form' not in x or langreq._same_form(x['form'], forms.get(i)): continue
        if langreq._loose(x['form']) == langreq._loose(forms.get(i)): loose += 1
        else: mark += 1
    seen = {}
    for i, f in forms.items():
        if f in watch: seen[f] = {'folder': name, 'request': n, 'id': i, 'decision': d.get(i),
                                  'dropped': [e for e in dr if e.get('id') == i] or None}
    return {'decided': len(d), 'items': len(forms), 'dropped': codes, 'rule_u_gain': {'loose_key': loose, 'mark_only': mark}}, seen

def run_one(p, cap, budget_limit, sender, out_dir, say, watch):
    budget = aisend.Budget({'language step': (budget_limit, 0.0)}, {n: p['worst'][n] for n, _, _, _ in p['reqs']})
    rows, found = {}, {}
    os.makedirs(os.path.join(out_dir, 'replies', p['name']), exist_ok=True)
    def job(item):
        n, path, raw, body = item; log = []
        r = aisend.call(lambda b: sender(raw, log), body, n, p['worst'][n], budget, label=f'{p["name"]} request {n}', say=say)
        f = r['final']
        for c, row in zip(r['calls'], log):
            if c.get('why'): row['why'] = c['why']
        for a, b in zip(log, log[1:]): a['pause_before_retry'] = round(b['sent'] - a['finished'], 1)
        if 'text' in f:
            json.dump({'finish': f.get('finish'), 'text': f['text'], 'calls': log}, open(os.path.join(out_dir, 'replies', p['name'], f'{n:03d}.reply.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return {'n': n, 'calls': log, 'cost_usd': r['cost_usd'], 'worst_usd': r['worst_usd'], 'finish': f.get('finish'), 'text': f.get('text')}
    def done(item, x):
        rows[x['n']] = x
        say(f'  {p["name"]} request {x["n"]}: ' + (f'{x["calls"][-1].get("output_tokens")} tokens, ${x["cost_usd"]:.4f}, {x["finish"]}' if x['finish'] else f'no reply ({x["calls"][-1].get("status")})')
            + f' ({len(rows)} of {p["n"]} done)')
    aisend.run(p['reqs'], job, cap, on_done=done)
    per, gain = [], {'loose_key': 0, 'mark_only': 0}
    for n, _, _, body in p['reqs']:
        x = rows[n]
        a, seen = analyse(x.pop('text') or '', body, watch, p['name'], n) if x['finish'] else ({}, {})
        found.update(seen); x['parse'] = a
        for k in gain: gain[k] += (a.get('rule_u_gain') or {}).get(k, 0)
        per.append(x)
    return per, gain, found

def paid(folders, cap, out_dir, limit, yes, watch):
    if os.path.exists(os.path.join(out_dir, 'summary.json')): sys.exit(f'refusing: {out_dir} already holds a run (summary.json)')
    key = load_key()
    try:
        with urllib.request.urlopen(urllib.request.Request('https://openrouter.ai/api/v1/models', headers={'User-Agent': 'pdfremproto1'}), timeout=30) as r_: models = json.load(r_)['data']
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e: sys.exit(f'could not reach OpenRouter to look up the model: {e}')
    P = plan(folders)
    for p in P:                                       # today's prices, as the language step reads them
        m = next((x for x in models if x['id'] == p['model']), None) or sys.exit(f'refusing: model "{p["model"]}" is not on OpenRouter')
        p.update(plan([p['folder']], (float(m['pricing']['prompt']), float(m['pricing']['completion'])))[0])
        if p['worst_usd'] > limit: sys.exit(f'refusing before any AI request: {p["name"]} could cost up to ${p["worst_usd"]:.2f}, more than the limit of ${limit:.2f}')
    total = sum(p['worst_usd'] for p in P)
    print(f'cap {cap}: {sum(p["n"] for p in P)} requests from {len(P)} folder(s) · expected about ${sum(p["saved_usd"] for p in P):.2f} · worst case ${total:.2f} '
          f'(first sends; retries up to ${limit:.2f} a folder)')
    if not yes and input('send them? [y/N] ').strip().lower() != 'y': sys.exit('not sent')
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time(); sender = Sender(key, t0); say = aisend.locked(print); res = {}
    def one_folder(p): res[p['name']] = run_one(p, cap, limit, sender, out_dir, say, watch)
    ts = [threading.Thread(target=one_folder, args=(p,), daemon=True) for p in P]
    for t in ts: t.start()
    for t in ts:
        while t.is_alive(): t.join(0.25)              # a short wait keeps Ctrl+C prompt
    wall = round(time.time() - t0, 1)
    calls = {name: per for name, (per, _, _) in res.items()}
    json.dump(calls, open(os.path.join(out_dir, 'calls.json'), 'w', encoding='utf-8'), indent=1)
    s = {'cap': cap, 'folders': [p['folder'] for p in P], 'wall_seconds': wall, 'peak_in_flight': sender.peak,
         'cost_usd': round(sum(x['cost_usd'] for per in calls.values() for x in per), 6),
         'worst_usd_not_known': round(sum(x['worst_usd'] for per in calls.values() for x in per), 4),
         'calls': sum(len(x['calls']) for per in calls.values() for x in per),
         'status_429': sum(1 for per in calls.values() for x in per for c in x['calls'] if c.get('status') == 429),
         'retried': sum(1 for per in calls.values() for x in per if len(x['calls']) > 1),
         'not_finished': sum(1 for per in calls.values() for x in per if x['finish'] != 'stop'),
         'rule_u_gain': {k: sum(g[k] for _, g, _ in res.values()) for k in ('loose_key', 'mark_only')},
         'per_folder': {p['name']: {'requests': p['n'], 'saved_usd': p['saved_usd'], 'saved_seconds': p['saved_seconds'], 'worst_usd': p['worst_usd'],
                                    'cost_usd': round(sum(x['cost_usd'] for x in calls[p['name']]), 6)} for p in P}}
    json.dump(s, open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8'), indent=1)
    if watch:
        found = {}
        for _, _, f in res.values(): found.update(f)
        json.dump({f: found.get(f) for f in watch}, open(os.path.join(out_dir, 'forms.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'cap {cap}: {wall:.0f} s · peak {sender.peak} in flight · ${s["cost_usd"]:.4f} · {s["status_429"]} × 429 · {s["retried"]} retried · '
          f'{s["not_finished"]} not finished · rule U kept {s["rule_u_gain"]["loose_key"]} by the loose key, {s["rule_u_gain"]["mark_only"]} only through a mark')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folders', nargs='+')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--caps', default='4,8,15')
    ap.add_argument('--cap', type=int); ap.add_argument('--out'); ap.add_argument('--yes', action='store_true')
    ap.add_argument('--forms', help='a file of word forms, one a line, whose answers to report (forms.json)')
    ap.add_argument('--max-usd', type=float, default=float(os.environ.get('LANGUAGE_MAX_USD') or costs.DEFAULT_LANGUAGE_USD))
    a = ap.parse_args()
    if a.dry_run: return dry_run(a.folders, [int(c) for c in a.caps.split(',')], a.max_usd)
    if not (a.cap and a.out): sys.exit('a paid run needs --cap N and --out DIR (or --dry-run)')
    watch = [l.strip() for l in open(a.forms, encoding='utf-8') if l.strip()] if a.forms else []
    paid(a.folders, a.cap, a.out, a.max_usd, a.yes, watch)

if __name__ == '__main__': main()
