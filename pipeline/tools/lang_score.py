"""lang_score.py: score the language step's test replies (#118, language tagging; review 02, M1). Free, no network.

    python3 tools/lang_score.py TEST_DIR [--half score|tune|all]  -> TEST_DIR/score.md (and score.json)

Reads TEST_DIR/items.json (tools/lang_test.py) and every reply under TEST_DIR/replies/<model>/run<N>/<set>/. Each key is
scored on its own line, never pooled: ga_raw (globalasias's publisher tags as printed), ga_corrected (review 02 H3),
silver:<source> (local evidence, two signals per item), synthetic. Per key and per model and run:
  right       the tag's language is the key's (any of the accepted ones; a romanized key needs -Latn)
  script      the language is right but the script subtag differs (ja for ja-Latn): counted apart, not as right
  wrong       tagged with another language
  untagged    left untagged as a name, part of English or indeterminate where the key gives a language
  unsure      left untagged as unsure, or answered with low confidence (never tagged): neither right nor wrong
Coverage (tagged / all) is reported beside accuracy (right / tagged), with counts and a Wilson 95% interval: with about
100 items a five-point gap is noise. Every disagreement with a key is listed item by item. Items with no key (Han-only
forms with nothing nearby) get model-to-model and run-to-run agreement only: their error rate is not measured until a
reader of the language checks them (tools/lang_sheet.py).
"""
import sys, os, json, glob, math, collections, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import langreq

def wilson(k, n, z=1.96):
    if not n: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

def primary(t): return (t or '').split('-')[0].lower()
def latn(t): return '-Latn' in (t or '')

def verdict(ans, accept):
    if ans is None: return 'missing'
    lang, conf, why = ans.get('lang'), ans.get('confidence'), ans.get('why')
    if lang is None or conf == 'low':
        return 'unsure' if (why in ('unsure', 'varies') or conf == 'low') else 'untagged'
    for a in accept:
        if primary(lang) == primary(a) or {primary(lang), primary(a)} == {'zh', 'yue'} and set(accept) >= {'zh', 'yue'}:
            return 'right' if latn(lang) == latn(a) else 'script'
    return 'wrong'

def answers(test_dir, runs=None):
    """{(model, run): {item id: decision}} from every saved reply, read with langreq.parse against its own request."""
    out = collections.defaultdict(dict)
    for rep in sorted(glob.glob(os.path.join(test_dir, 'replies', '*', 'run*', '*', '*.reply.json'))):
        model, run = rep.split(os.sep)[-4], rep.split(os.sep)[-3]
        if runs and run not in runs: continue
        req = json.load(open(rep.replace('.reply.json', '.request.json'), encoding='utf-8'))
        ids = [it['id'] for it in json.loads(req['messages'][1]['content'])['items']]
        r = json.load(open(rep, encoding='utf-8'))
        text = ((r.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        dec, _ = langreq.parse(text, set(ids))
        out[(model, run)].update(dec)
    return out

def score(test_dir, which='score', runs=None):
    items = json.load(open(os.path.join(test_dir, 'items.json'), encoding='utf-8'))['items']
    A = answers(test_dir, runs)
    runs = sorted(A)
    keyed = [it for it in items if it['source'] != 'nokey' and (which == 'all' or it['half'] == which)]
    keys = collections.OrderedDict()
    for it in keyed:
        if it['source'] == 'ga':
            keys.setdefault('ga_raw', []).append((it, [it['raw']]))
            keys.setdefault('ga_corrected', []).append((it, it['accept']))
        else: keys.setdefault(it['source'], []).append((it, it['accept']))
    lines = [f'# Language test scores ({which} half)', '', 'Each key on its own line; counts first. "acc" is right / tagged, "cov" tagged / all.', '']
    res = {}
    for kname, lst in keys.items():
        lines += [f'## {kname} ({len(lst)} items)', '', '| model, run | right | script | wrong | untagged | unsure | cov | acc (95% CI) |', '|---|---:|---:|---:|---:|---:|---:|---|']
        for mr in runs:
            c = collections.Counter(verdict(A[mr].get(it['id']), acc) for it, acc in lst)
            tagged = c['right'] + c['script'] + c['wrong']; n = len(lst)
            lo, hi = wilson(c['right'], tagged)
            lines.append(f'| {mr[0]} {mr[1]} | {c["right"]} | {c["script"]} | {c["wrong"]} | {c["untagged"]} | {c["unsure"] + c["missing"]} | '
                         f'{tagged}/{n} | {c["right"]}/{tagged} ({lo:.0%}–{hi:.0%}) |')
            res[f'{kname}|{mr[0]}|{mr[1]}'] = dict(c)
        lines.append('')
    # every disagreement, item by item
    lines += ['## Every disagreement with a key', '', '| key | item | form | page | key says | answers |', '|---|---|---|---:|---|---|']
    for kname, lst in keys.items():
        for it, acc in lst:
            vs = {mr: verdict(A[mr].get(it['id']), acc) for mr in runs}
            if all(v == 'right' for v in vs.values()) and vs: continue
            ans = '; '.join(f'{mr[0].split("-")[1] if "-" in mr[0] else mr[0]} {mr[1]}: {(A[mr].get(it["id"]) or {}).get("lang")} '
                            f'({(A[mr].get(it["id"]) or {}).get("confidence")}, {(A[mr].get(it["id"]) or {}).get("why")})' for mr in runs)
            lines.append(f'| {kname} | {it["id"]} | {it["form"][:40]} | {it["page"]} | {"/".join(acc)} | {ans or "no reply yet"} |')
    # agreement where there is no key
    nk = [it for it in items if it['source'] == 'nokey']
    lines += ['', f'## No key ({len(nk)} Han-only forms with nothing nearby): agreement only', '',
              'Their error rate is not measured: a reader of Japanese or Chinese would have to check them (the spot-check sheet).', '']
    for a in range(len(runs)):
        for b in range(a + 1, len(runs)):
            both = [it for it in nk if it['id'] in A[runs[a]] and it['id'] in A[runs[b]]]
            same = sum(1 for it in both if primary(A[runs[a]][it['id']].get('lang')) == primary(A[runs[b]][it['id']].get('lang')))
            lines.append(f'- {runs[a][0]} {runs[a][1]} vs {runs[b][0]} {runs[b][1]}: {same} of {len(both)} the same language')
    if not runs: lines.append('- no replies yet')
    open(os.path.join(test_dir, f'score-{which}.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    json.dump(res, open(os.path.join(test_dir, f'score-{which}.json'), 'w'), indent=1)
    print('\n'.join(lines[:60]))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('test_dir'); ap.add_argument('--half', default='score', choices=['score', 'tune', 'all'])
    ap.add_argument('--runs', default=None, help='comma-separated run folders to score (run1,run2); default every run')
    a = ap.parse_args(); score(a.test_dir, a.half, set(a.runs.split(',')) if a.runs else None)
