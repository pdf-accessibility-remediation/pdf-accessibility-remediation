"""lang_exp.py: score round 15's staged experiment on the language step's context (#118, language tagging; review 14,
item 1, as widened). Free, no network.

    python3 tools/lang_exp.py OUT_DIR VARIANT=MODEL/SET … [--compare A,B,…] [--md FILE]

OUT_DIR holds items.json (tools/lang_test.py build_exp) and replies/<model>/run<N>/<set>/. Each VARIANT names one set of
replies (e.g. A=claude-sonnet-5.5/A). Per variant, run and item the answer is one of:
  right      tagged with the key's language (and script: ja-Latn for a romanized key)
  wrong      tagged, at high or medium confidence, with another language or script
  untagged   left untagged (a name, part of English, unsure, varies) or answered at low confidence (never tagged)
  cut off    no answer in the reply (cut off or missing)
Rates come with a Wilson 95% range. Two variants are compared on the same items, run by run and pooled over the runs,
with an exact McNemar test on the items whose outcome differs; a difference not significant at 0.05 is "too close to
tell". Masked-clue items (a worst case, the reading beside the characters removed) are scored apart, never in the
overall rate. Adoption, fixed before the runs (15-builder-report.md): fewest wrong, then fewest untagged or cut off,
then the most agreement across runs, then the lowest cost; each rule on the real items first, then the masked ones.
"""
import sys, os, json, glob, math, collections, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import langreq
from lang_score import verdict, wilson

def outcome(ans, accept):
    v = verdict(ans, accept)
    return {'right': 'right', 'script': 'wrong', 'wrong': 'wrong', 'untagged': 'untagged', 'unsure': 'untagged'}.get(v, 'cut off')

def replies(out_dir, model, which):
    """{run: {item id: decision}} for one model and set, every run found, each reply read against its own request."""
    out = {}
    for d in sorted(glob.glob(os.path.join(out_dir, 'replies', model, 'run*', which))):
        run = d.split(os.sep)[-2]; got = {}
        for rep in sorted(glob.glob(os.path.join(d, '*.reply.json'))):
            req = json.load(open(rep.replace('.reply.json', '.request.json'), encoding='utf-8'))
            ids = [it['id'] for it in json.loads(req['messages'][1]['content'])['items']]
            r = json.load(open(rep, encoding='utf-8'))
            text = ((r.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
            dec, _ = langreq.parse(text, set(ids)); got.update(dec)
        out[run] = got
    return out

def cost(out_dir, model, which, ledger='spend-ctx15.json'):
    p = os.path.join(out_dir, ledger)
    if not os.path.exists(p): return None
    calls = [c for c in json.load(open(p))['calls'] if c['model'].split('/')[-1] == model.split('/')[-1] and c['set'] == which]
    runs = collections.defaultdict(float)                # the ledger names the model with its provider ("anthropic/…")
    for c in calls: runs[c['run']] += c.get('cost') or 0
    return {'total': round(sum(runs.values()), 4), 'per_run': round(sum(runs.values()) / max(1, len(runs)), 4), 'runs': len(runs)}

def binom_two_sided(b, c):
    """Exact McNemar: two-sided binomial p for b against c (p = 0.5)."""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)

def table(items, A, keyfn):
    """{group: {outcome: [count per run]}, 'n': items} for one variant's answers A ({run: {id: dec}})."""
    out = collections.defaultdict(lambda: {'n': 0, 'runs': collections.defaultdict(collections.Counter), 'agree': 0})
    runs = sorted(A)
    for it in items:
        for g in keyfn(it):
            x = out[g]; x['n'] += 1
            seen = []
            for r in runs:
                d = A[r].get(it['id']); x['runs'][r][outcome(d, it['accept'])] += 1
                seen.append(None if not d else (d.get('lang') if d.get('confidence') in ('high', 'medium') else None))
            if len(set(seen)) == 1 and len(seen) == len(runs): x['agree'] += 1
    return out

def fmt(k, n):
    lo, hi = wilson(k, n)
    return f'{k} ({100 * k / n:.1f}%, {100 * lo:.1f}–{100 * hi:.1f})' if n else '0'

def summary(items, A, keyfn):
    rows = {}
    for g, x in table(items, A, keyfn).items():
        runs = sorted(x['runs']); n = x['n']; R = len(runs)
        tot = collections.Counter()
        for r in runs: tot.update(x['runs'][r])
        rows[g] = {'n': n, 'runs': R, **{o: tot[o] for o in ('right', 'wrong', 'untagged', 'cut off')},
                   'agree': x['agree'], 'per_run': {r: dict(x['runs'][r]) for r in runs}}
    return rows

def md_rows(rows, title):
    L = [f'**{title}** (counts over all runs: n items × runs; % and 95% range)', '',
         '| group | items | runs | right | wrong (high/medium) | untagged or low | cut off | same answer in every run |', '|---|---:|---:|---|---|---|---|---|']
    for g in sorted(rows, key=lambda g: (-rows[g]['n'], g)):
        x = rows[g]; N = x['n'] * x['runs']
        L.append(f'| {g} | {x["n"]} | {x["runs"]} | {fmt(x["right"], N)} | {fmt(x["wrong"], N)} | {fmt(x["untagged"], N)} | {fmt(x["cut off"], N)} | {fmt(x["agree"], x["n"])} |')
    return L + ['']

def mcnemar(items, A, B, flag):
    """Per run and pooled: (b, c, p) where b = items flagged under A only, c = under B only (flag: outcome predicate)."""
    out = {}; tb = tc = 0
    for r in sorted(set(A) & set(B)):
        b = c = 0
        for it in items:
            fa = flag(outcome(A[r].get(it['id']), it['accept'])); fb = flag(outcome(B[r].get(it['id']), it['accept']))
            b += fa and not fb; c += fb and not fa
        out[r] = (b, c, round(binom_two_sided(b, c), 4)); tb += b; tc += c
    out['pooled'] = (tb, tc, round(binom_two_sided(tb, tc), 4))
    return out

def agree_flags(items, A):
    """{id: True when every run gave the same answer} (the agreement rule's paired outcome)."""
    out = {}
    for it in items:
        seen = [None if not A[r].get(it['id']) else (A[r][it['id']].get('lang') if A[r][it['id']].get('confidence') in ('high', 'medium') else None) for r in sorted(A)]
        out[it['id']] = len(set(seen)) == 1
    return out

def adopt(variants, real, masked, ans, costs, log):
    """The fixed adoption rule: candidates narrowed by fewest wrong, then fewest untagged or cut off, then agreement,
    then cost; at each rule the real items first, then the masked ones. A variant stays while its pooled McNemar test
    against the best is not significant at 0.05 ("too close to tell")."""
    keep = list(variants)
    def narrow(items, flag, what, scope):
        nonlocal keep
        if len(keep) < 2 or not items: return
        tot = {v: sum(flag(outcome(ans[v][r].get(it['id']), it['accept'])) for r in ans[v] for it in items) for v in keep}
        best = min(keep, key=lambda v: tot[v])
        new = [best]
        for v in keep:
            if v == best: continue
            b, c, p = mcnemar(items, ans[best], ans[v], flag)['pooled']
            log.append(f'- {what}, {scope}: {best} {tot[best]} against {v} {tot[v]} (only {best}: {b}, only {v}: {c}; p = {p})'
                       + (': too close to tell' if p >= 0.05 else f': {v} drops'))
            if p >= 0.05: new.append(v)
        keep = new
    for scope, items in (('real items', real), ('masked items', masked)):
        narrow(items, lambda o: o == 'wrong', 'Rule 1, wrong', scope)
    for scope, items in (('real items', real), ('masked items', masked)):
        narrow(items, lambda o: o in ('untagged', 'cut off'), 'Rule 2, untagged or cut off', scope)
    if len(keep) > 1:
        for scope, items in (('real items', real), ('masked items', masked)):
            if len(keep) < 2: break
            fl = {v: agree_flags(items, ans[v]) for v in keep}
            best = max(keep, key=lambda v: sum(fl[v].values())); new = [best]
            for v in keep:
                if v == best: continue
                b = sum(1 for i in fl[best] if fl[best][i] and not fl[v][i]); c = sum(1 for i in fl[best] if fl[v][i] and not fl[best][i])
                p = round(binom_two_sided(b, c), 4)
                log.append(f'- Rule 3, agreement, {scope}: {best} {sum(fl[best].values())} against {v} {sum(fl[v].values())} (p = {p})'
                           + (': too close to tell' if p >= 0.05 else f': {v} drops'))
                if p >= 0.05: new.append(v)
            keep = new
    if len(keep) > 1:
        c = {v: (costs.get(v) or {}).get('per_run', 9e9) for v in keep}
        log.append('- Rule 4, cost per run: ' + ', '.join(f'{v} ${c[v]:.4f}' for v in keep))
        keep = [min(keep, key=lambda v: c[v])]
    return keep[0]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out_dir'); ap.add_argument('variants', nargs='+')
    ap.add_argument('--md', default=None); ap.add_argument('--ledger', default='spend-ctx15.json'); ap.add_argument('--half', default='score')
    a = ap.parse_args()
    items = [it for it in json.load(open(os.path.join(a.out_dir, 'items.json'), encoding='utf-8'))['items']
             if it['half'] == a.half and it['kind'] != 'nokey']
    real = [it for it in items if it['kind'] != 'masked']; masked = [it for it in items if it['kind'] == 'masked']
    V = collections.OrderedDict(v.split('=', 1) for v in a.variants)
    ans = {v: replies(a.out_dir, *spec.split('/', 1)) for v, spec in V.items()}
    costs = {v: cost(a.out_dir, *spec.split('/', 1), a.ledger) for v, spec in V.items()}
    L = [f'# Round 15 scores: {", ".join(f"{v} = {s}" for v, s in V.items())}', '',
         f'Score half: {len(real)} real items, {len(masked)} masked-clue items (scored apart). Costs from `{a.ledger}`.', '']
    res = {}
    for v in V:
        res[v] = {'overall': summary(real, ans[v], lambda it: ['all real items']),
                  'masked': summary(masked, ans[v], lambda it: ['masked: all', f'masked: {it["lang"]}']),
                  'kind': summary(real, ans[v], lambda it: [it['kind']]),
                  'class': summary(real + masked, ans[v], lambda it: [it['cls'] + (f' ({it["lang"]})' if it['kind'] == 'masked' else '')]),
                  'book': summary(real + masked, ans[v], lambda it: [it['book'] + (' (masked)' if it['kind'] == 'masked' else '')]),
                  'cost': costs[v], 'runs': sorted(ans[v])}
        L += [f'## Variant {v} ({V[v]}): runs {", ".join(res[v]["runs"])}; cost {costs[v]}', '']
        for k, t in (('overall', 'Overall (real items)'), ('masked', 'Masked-clue items (worst case, apart)'), ('kind', 'By kind'),
                     ('class', 'By class'), ('book', 'By book')):
            L += md_rows(res[v][k], t)
    vs = list(V)
    if len(vs) > 1:
        L += ['## Paired comparisons (exact McNemar; b = only the first, c = only the second; per run and pooled)', '']
        for scope, its in (('real', real), ('masked', masked)):
            for what, fl in (('wrong', lambda o: o == 'wrong'), ('untagged or cut off', lambda o: o in ('untagged', 'cut off'))):
                for i in range(len(vs)):
                    for j in range(i + 1, len(vs)):
                        m = mcnemar(its, ans[vs[i]], ans[vs[j]], fl)
                        L.append(f'- {scope}, {what}, {vs[i]} vs {vs[j]}: ' + '; '.join(f'{r} b={b} c={c} p={p}' for r, (b, c, p) in m.items())
                                 + (' → too close to tell' if m['pooled'][2] >= 0.05 else ''))
        log = []
        win = adopt(vs, real, masked, ans, costs, log)
        L += ['', '## Adoption (the fixed rule)', ''] + log + ['', f'**Adopted: {win}**', '']
        res['_adopted'] = win; res['_log'] = log
    md = '\n'.join(L) + '\n'
    if a.md:
        open(a.md, 'w', encoding='utf-8').write(md); json.dump(res, open(a.md.replace('.md', '.json'), 'w'), indent=1, default=dict)
    print(md)

if __name__ == '__main__': main()
