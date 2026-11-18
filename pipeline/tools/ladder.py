"""ladder.py: how many language requests can be out at once across several PDFs (#135 (parallel requests)). PAID unless
--dry-run: it runs the real language step (name_languages.py) on prepared run folders, several at once, level by level.

    python3 tools/ladder.py PLAN.json --dry-run          nothing sent: each level's books, requests and amounts, and the credit
    python3 tools/ladder.py PLAN.json --out DIR [--yes]  the levels in order, each only after the one before finished

PLAN.json: {"reference_median_s": 54.4, "levels": [{"name": "level 1", "books": [{"name": "bikol", "run": RUN_DIR,
"pdf": PDF, "env": {"AI_PARALLEL": "40", "LANGUAGE_MAX_USD": "14", "BOOK_MAX_USD": "16"}}, …]}, …]}. Each run folder
holds the audit (_audit/) and, ideally, the work order; its language_estimate.json (from name_languages.py --dry-run)
gives the requests, the worst case and the forms sent. Every book of a level starts at once, as a batch's JOBS would
start them, each a name_languages.py process with its own environment (limits raised for this test only, never in the
code's defaults).

After each level it reads every book's language_run.json and works out, from the requests' own send and finish times
(sent_at, finished_at: clock seconds, comparable across processes):
  - the true peak of requests out at once, across all the level's books, and per book;
  - every 429 and other failure (a call's error), and each request's own time (finish − send);
  - the level's cost (each record's cost_usd) and anything whose charge is not known (in flight, stopped, timed out).
Stop rules, checked before each next level (the reason is written in summary.json):
  - any 429 or failure in the level just run;
  - its median request time more than 20% above the reference (PLAN's reference_median_s: the 24-in-flight batch test);
  - the next level's worst case not fitting the credit left (read from OpenRouter's key endpoint, never printed);
  - a book's process ending with an error (its log is kept in DIR).
Writes DIR/<level>/<book>.log, DIR/<level>/summary.json and DIR/summary.json. Refuses a DIR that holds a summary.json.
--cmd (tests only) replaces "python3 name_languages.py"; the API key is never printed.
"""
import sys, os, json, time, math, shlex, statistics, argparse, subprocess, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # pipeline/
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tools'))
from lib import aisend

def estimate(book):
    try: return json.load(open(os.path.join(book['run'], 'language_estimate.json'), encoding='utf-8'))
    except (OSError, ValueError): return {}

RATE = 0.0011                     # dollars per word form sent: M1, 2026-11-17 ($2.4499 for 2,217 forms; Cadatest2 $2.4558 for 2,230)

def amounts(level):
    rows = []
    for b in level['books']:
        e = estimate(b)
        rows.append({'name': b['name'], 'requests': e.get('to_send', e.get('requests', 0)) or 0, 'forms': e.get('sent', 0) or 0,
                     'worst': e.get('worst_case_usd', 0) or 0, 'expected': round((e.get('sent', 0) or 0) * RATE, 2), 'env': b.get('env') or {}})
    return rows

def credit_left():
    import cap_sweep
    key = cap_sweep.load_key()
    rq = urllib.request.Request('https://openrouter.ai/api/v1/key', headers={'Authorization': f'Bearer {key}', 'User-Agent': 'pdfremproto1'})
    with urllib.request.urlopen(rq, timeout=30) as r: d = json.load(r).get('data', {})
    return d.get('limit_remaining')

def dry_run(plan, credit=None):
    tot_e = tot_w = 0.0
    for lv in plan['levels']:
        rows = amounts(lv); e, w = sum(r['expected'] for r in rows), sum(r['worst'] for r in rows)
        n = sum(min(r['requests'], int(r['env'].get('AI_PARALLEL') or aisend.DEFAULT_CAP)) for r in rows)   # each book at most its own cap
        tot_e += e; tot_w += w
        print(f'{lv["name"]}: {len(rows)} book(s), {n} requests at once at most · expected ${e:.2f} · worst case ${w:.2f}')
        for r in rows:
            print(f'  {r["name"]:20} {r["requests"]:3} requests · {r["forms"]:6} forms · expected ${r["expected"]:.2f} · worst ${r["worst"]:.2f}'
                  + (' · ' + ' '.join(f'{k}={v}' for k, v in r['env'].items()) if r['env'] else ''))
    print(f'in all: expected ${tot_e:.2f} · worst case ${tot_w:.2f}' + ('' if credit is None else f' · credit left ${credit:.2f}'))
    return tot_e, tot_w

def measure(level, out):
    """What a finished level did, from each book's language_run.json."""
    reqs, per, cost, unknown, errors = [], {}, 0.0, 0.0, []
    for b in level['books']:
        try: lr = json.load(open(os.path.join(b['run'], 'language_run.json'), encoding='utf-8'))
        except (OSError, ValueError): errors.append(f'{b["name"]}: no language_run.json'); continue
        cost += lr.get('cost_usd') or 0
        unknown += sum(x.get('worst_usd') or 0 for x in list(lr.get('in_flight') or []) + list(lr.get('stopped_in_flight') or []) + list(lr.get('requests') or []))
        calls = []
        for x in lr.get('requests') or []:
            for c in x.get('calls') or [{'sent_at': x.get('sent_at'), 'finished_at': x.get('finished_at'), 'error': x.get('error')}]:
                calls.append({'book': b['name'], 'n': x.get('n'), **c})
        per[b['name']] = calls; reqs += calls
    def peak(cs):
        ev = sorted([(c['sent_at'], 1) for c in cs if c.get('sent_at')] + [(c['finished_at'], -1) for c in cs if c.get('finished_at')], key=lambda e: (e[0], e[1]))
        cur = top = 0
        for _, d in ev: cur += d; top = max(top, cur)
        return top
    secs = [c['finished_at'] - c['sent_at'] for c in reqs if c.get('sent_at') and c.get('finished_at')]
    codes = [str((c.get('error') or {}).get('code')) for c in reqs if c.get('error')]
    starts = [c['sent_at'] for c in reqs if c.get('sent_at')]; ends = [c['finished_at'] for c in reqs if c.get('finished_at')]
    return {'calls': len(reqs), 'peak_in_flight': peak(reqs), 'peak_per_book': {k: peak(v) for k, v in per.items()},
            'status_429': codes.count('429'), 'failures': len(codes) - codes.count('429'), 'error_codes': codes,
            'median_seconds': round(statistics.median(secs), 1) if secs else None, 'slowest_seconds': round(max(secs), 1) if secs else None,
            'wall_seconds': round(max(ends) - min(starts), 1) if starts and ends else None,
            'cost_usd': round(cost, 6), 'not_known_usd': round(unknown, 4), 'errors': errors}

def run(plan, out, cmd, yes, credit_fn=credit_left):
    if os.path.exists(os.path.join(out, 'summary.json')): sys.exit(f'refusing: {out} already holds a run (summary.json)')
    dry_run(plan)
    if not yes and input('run these levels? [y/N] ').strip().lower() != 'y': sys.exit('not sent')
    os.makedirs(out, exist_ok=True); done, stop = [], None; ref = plan.get('reference_median_s')
    for k, lv in enumerate(plan['levels']):
        rows = amounts(lv); worst = sum(r['worst'] for r in rows)
        if done:
            last = done[-1]['measured']
            if last['status_429'] or last['failures'] or last['errors']: stop = f'{done[-1]["name"]}: 429s, failures or a step error; no next level'; break
            if ref and last['median_seconds'] and last['median_seconds'] > 1.2 * ref:
                stop = f'{done[-1]["name"]}: median request {last["median_seconds"]} s, more than 20% above {ref} s; no next level'; break
        c = credit_fn()
        if c is not None and worst > c: stop = f'{lv["name"]}: worst case ${worst:.2f} doesn\'t fit the ${c:.2f} credit left; not run'; break
        d = os.path.join(out, lv['name'].replace(' ', '-')); os.makedirs(d, exist_ok=True)
        procs = []
        for b in lv['books']:
            env = dict(os.environ, **{k_: str(v) for k_, v in (b.get('env') or {}).items()})
            args = shlex.split(cmd) + [os.path.join(b['run'], '_audit'), b['run'], '--pdf', b['pdf']]
            procs.append((b, subprocess.Popen(args, cwd=HERE, env=env, stdout=open(os.path.join(d, f'{b["name"]}.log'), 'w'), stderr=subprocess.STDOUT)))
        t0 = time.time()
        codes = {b['name']: p.wait() for b, p in procs}
        m = measure(lv, d); m['exit_codes'] = codes; m['errors'] += [f'{n}: exit {c_}' for n, c_ in codes.items() if c_]
        m['level_seconds'] = round(time.time() - t0, 1)
        done.append({'name': lv['name'], 'books': [b['name'] for b in lv['books']], 'measured': m})
        json.dump(done[-1], open(os.path.join(d, 'summary.json'), 'w'), indent=1)
        print(f'{lv["name"]}: peak {m["peak_in_flight"]} in flight · {m["status_429"]} × 429 · {m["failures"]} failures · median {m["median_seconds"]} s · '
              f'${m["cost_usd"]:.4f}' + (f' · errors: {m["errors"]}' if m['errors'] else ''))
    json.dump({'levels': done, 'stopped': stop, 'reference_median_s': ref}, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    print(f'stopped: {stop}' if stop else 'every level ran')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out'); ap.add_argument('--yes', action='store_true'); ap.add_argument('--cmd', default=f'{sys.executable} name_languages.py')
    a = ap.parse_args(); plan = json.load(open(a.plan, encoding='utf-8'))
    if a.dry_run:
        try: c = credit_left()
        except Exception: c = None
        return dry_run(plan, c)
    if not a.out: sys.exit('a paid run needs --out DIR (or --dry-run)')
    run(plan, a.out, a.cmd, a.yes)

if __name__ == '__main__': main()
