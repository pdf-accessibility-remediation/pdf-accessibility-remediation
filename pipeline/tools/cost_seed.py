"""cost_seed.py: build lib/cost_seed.json, the committed starting history of the expected cost, from past records. Free, read-only
on every run folder; no book content leaves a record.

    python3 tools/cost_seed.py [--runs ../runs] [--out lib/cost_seed.json]

Each row is one finished paid AI call (kind, model, prompt file, input estimate, billed input, output tokens, images, OCR word
forms, date, book label): numbers, two names, a date and a plain label such as b07. Cut-off calls and replays are left out. A
book is identified by its original PDF's sha256 (from _intake/intake.json, else the record's document); a call with neither is
dropped. The seed holds labels only, so nobody holding a PDF can confirm it was processed: the link from a sha-based id to
its label stays on this computer, in <runs>/.cost-book-labels.json (runs/ is never committed). Rebuilding keeps every label
it already gave. Calls that are also in the local ledger are counted once (lib/costhistory.py rows()).
"""
import os, sys, json, hashlib, argparse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import costhistory as H

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def original_sha(d, rec):
    for j in (_load(os.path.join(d, '_intake', 'intake.json')), (rec or {}).get('intake')):
        s = ((j or {}).get('original') or {}).get('sha256') if isinstance(j, dict) else None
        if s: return s
    return ((rec or {}).get('document') or {}).get('sha256')

def calls_of(run, sha):
    """The paid, complete calls of one record or run.json, as rows with the sha still on them."""
    if run.get('response_from'): return []
    e = run.get('estimate') or {}
    ow = run.get('ocr_words') if isinstance(run.get('ocr_words'), dict) else {}
    base = {'model': run.get('model'), 'date': run.get('started'), 'sha': sha}
    out = []
    def add(kind, prompt, est, images, forms, u, fin):
        if fin == 'length' or not est or not u.get('prompt_tokens') or not u.get('completion_tokens'): return
        out.append({'kind': kind, 'model': base['model'], 'prompt': prompt, 'input_est': est, 'input_billed': u['prompt_tokens'],
                    'output': u['completion_tokens'], 'images': images or 0, 'forms': forms, 'date': base['date'], 'sha': sha})
    if run.get('passes'):
        ep = {str(p.get('pass')): p for p in e.get('passes') or []}
        for p in run['passes']:
            k = str(p['pass'])
            if k == 'probe' or (p.get('usage') or {}).get('cost_usd') is None: continue
            fin = 'length' if any(c.get('finish_reason') == 'length' for c in p.get('calls') or []) else p.get('finish_reason') or ((p.get('calls') or [{}])[-1]).get('finish_reason')   # a request's usage is the sum of its calls: one with a cut-off teaches nothing
            kind = 'workorder' if k == '1' else 'figure'
            prompt = run.get('prompt_file') if k == '1' else (run.get('figure_passes') or {}).get('prompt_file')
            ee = ep.get(k) or {}
            add(kind, prompt, ee.get('input_tokens'), ee.get('images') if ee else p.get('images'), (ow.get('sent') or 0) if k == '1' else 0, p['usage'], fin)
    elif (run.get('usage') or {}).get('cost_usd') is not None:
        add('workorder', run.get('prompt_file'), e.get('input_tokens'), e.get('images'), ow.get('sent') or 0, run['usage'], run.get('finish_reason'))
    return out

def collect(runs):
    rows, seen, dropped = [], set(), 0
    for d, subs, fs in os.walk(runs):
        subs[:] = [s for s in subs if s not in ('_audit', '_intake', 'release', 'reviews', '.app')]
        rec = _load(os.path.join(d, 'record.json')) if 'record.json' in fs else None
        run = (rec or {}).get('run') or (_load(os.path.join(d, 'run.json')) if 'run.json' in fs and not rec else None)
        if not isinstance(run, dict): continue
        sha = original_sha(d, rec)
        for c in calls_of(run, sha):
            k = (c['date'], c['kind'], c['input_est'], c['input_billed'], c['output'], c['model'])
            if k in seen: continue
            seen.add(k)
            if not c['sha']: dropped += 1; continue
            rows.append(c)
    return sorted(rows, key=lambda c: c['date']), dropped

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--runs', default=os.path.join(os.path.dirname(HERE), 'runs'))
    ap.add_argument('--out', default=H.SEED)
    a = ap.parse_args()
    rows, dropped = collect(a.runs)
    map_path = os.path.join(a.runs, H.LABELS_NAME)
    labels = _load(map_path) or {}
    n = max([int(v[1:]) for v in labels.values()] or [0])
    for c in rows:
        i = hashlib.sha256(c['sha'].encode()).hexdigest()[:16]
        if i not in labels: n += 1; labels[i] = f'b{n:02d}'
        c['book'] = labels[i]; del c['sha']
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('{"format": "cost-seed/1", "rows": [\n' + ',\n'.join(json.dumps({k: c[k] for k in H.SEED_KEYS}, ensure_ascii=False, separators=(',', ':')) for c in rows) + '\n]}\n')
    with open(map_path, 'w', encoding='utf-8') as f: json.dump(labels, f, indent=1)
    print(f'{len(rows)} calls, {len({c["book"] for c in rows})} books, {dropped} dropped (no original PDF on record)')
    print(f'written: {a.out}\nlabels (local only): {map_path}')

if __name__ == '__main__':
    main()
