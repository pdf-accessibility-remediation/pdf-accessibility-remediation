"""request_sweep.py: does decide.py build the same request as before, book by book? Free: --dry-run only, never a call.

    python3 tools/request_sweep.py <old-commit> [--out DIR] [--only BOOK …]

request.json keeps only the first 300 characters of the digest, and regression.py and compare_runs.py never see the
request, so this compares the whole request (base64 images included) by its sha256, written by decide.py's test-only
DECIDE_SWEEP hook, and run.json without its start time and the credit read at that moment.

1. Audits (free, local, veraPDF on as in a run): each book of rd2's 19 (runs/batches/rd2-*/<book>/) is audited from the
   file that run worked on (its _intake/intake.pdf, or the tagged original in samples/) into <out>/audit/<book>/, once;
   later sweeps reuse them. The digest's fingerprint is checked against the rd2 record's run.digest_sha256 and any book
   that no longer reproduces is listed: both sides use the same audit, so the comparison still holds for it.
   henrycukim's kept e2e audit (runs/henrycukim/e2e-1/_audit, crops kept) is used as it is.
2. The old side: `git archive <old-commit> pipeline prompts` unpacked under <out>/trees/<commit>/ (read-only git).
3. Both sides' `decide.py --dry-run`, the old one first and the working tree's right after it (decide.py reads
   OpenRouter's /models for prices and limits, so the two sides run back to back).
4. A report, <out>/report-<commit>.md, one line per book: identical, or what differs. A request whose new side writes a
   `normalised` hash (the change a book over the image limit is meant to get, undone) is compared by that hash.

Exit code 0 when every book is identical, 1 otherwise.
"""
import sys, os, json, glob, shutil, hashlib, argparse, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # pipeline/
ROOT = os.path.dirname(HERE)
TAGGED = ('group1', 'group2', 'group3most')

def books(runs):
    """{book: (input pdf, rd2 digest fingerprint)} for rd2's books."""
    out = {}
    for rec in sorted(glob.glob(os.path.join(runs, 'batches', 'rd2-*', '*', 'record.json'))):
        d = os.path.dirname(rec); b = os.path.basename(d)
        r = json.load(open(rec, encoding='utf-8'))
        pdf = os.path.join(d, '_intake', 'intake.pdf')
        if not os.path.exists(pdf):
            pdf = next((p for g in TAGGED for p in [os.path.join(ROOT, 'samples', g, b + '.pdf')] if os.path.exists(p)), None)
        if pdf: out[b] = (pdf, (r.get('run') or {}).get('digest_sha256'))
    return out

def audit(pdf, A):
    if os.path.exists(os.path.join(A, 'digest.json')): return
    tmp = A + '.tmp'; shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run([sys.executable, os.path.join(HERE, 'audit.py'), pdf, tmp], cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    os.rename(tmp, A)

def tree(commit, out):
    """The old side's files, unpacked once."""
    t = os.path.join(out, 'trees', commit)
    if not os.path.exists(os.path.join(t, 'pipeline', 'decide.py')):
        os.makedirs(t, exist_ok=True)
        tar = subprocess.run(['git', 'archive', commit, 'pipeline', 'prompts'], cwd=ROOT, check=True, capture_output=True).stdout
        subprocess.run(['tar', '-x', '-C', t], input=tar, check=True)
    return os.path.join(t, 'pipeline')

def dry_run(pipe, A, R):
    """One side's dry run of one audit: (the request hashes, run.json without its volatile fields)."""
    shutil.rmtree(R, ignore_errors=True); os.makedirs(R)
    sweep = os.path.join(R, 'sweep.json')
    args = [sys.executable, os.path.join(pipe, 'decide.py'), A, R, '--dry-run']
    assert '--dry-run' in args                      # never a call: this tool must not spend anything
    p = subprocess.run(args, cwd=pipe, env=dict(os.environ, DECIDE_SWEEP=sweep), capture_output=True, text=True)
    if p.returncode or not os.path.exists(sweep):
        return None, {'error': (p.stderr or p.stdout).strip().splitlines()[-1:] or ['no output']}
    run = json.load(open(os.path.join(R, 'run.json'), encoding='utf-8'))
    run.pop('started', None); (run.get('estimate') or {}).pop('credit_available_usd', None)
    return json.load(open(sweep, encoding='utf-8'))['requests'], run

def diff_keys(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        return [x for k in sorted(set(a) | set(b)) for x in diff_keys(a.get(k), b.get(k), f'{path}.{k}' if path else k)]
    return [] if a == b else [path]

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('old', help='the commit to compare the working tree with')
    ap.add_argument('--out', default=os.path.join(ROOT, 'runs', 'alt-text-passes', 'sweep'))
    ap.add_argument('--only', nargs='*', help='these books only')
    a = ap.parse_args()
    commit = subprocess.run(['git', 'rev-parse', '--short', a.old], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    todo = books(os.path.join(ROOT, 'runs'))
    audits = {}
    for b, (pdf, fp) in todo.items():
        if a.only and b not in a.only: continue
        A = os.path.join(a.out, 'audit', b); print(f'audit {b}', flush=True); audit(pdf, A)
        got = hashlib.sha256(open(os.path.join(A, 'digest.json'), 'rb').read()).hexdigest()[:16]
        audits[b] = (A, None if got == fp else f'digest {got} differs from rd2\'s {fp}')
    hk = os.path.join(ROOT, 'runs', 'henrycukim', 'e2e-1', '_audit')
    if os.path.exists(os.path.join(hk, 'digest.json')) and (not a.only or 'henrycukim' in a.only):
        audits['henrycukim'] = (hk, 'kept e2e audit (328 figures + 1 sheet): its first request is meant to change')
    old = tree(commit, a.out)
    rows, same = [], 0
    for b, (A, note) in audits.items():
        print(f'dry runs {b}', flush=True)
        r_old = dry_run(old, A, os.path.join(a.out, commit, b))       # back to back: old, then new
        r_new = dry_run(HERE, A, os.path.join(a.out, 'working', b))
        (q_old, run_old), (q_new, run_new) = r_old, r_new
        if q_old is None or q_new is None:
            rows.append(f'| {b} | **error** | old: {run_old.get("error") if q_old is None else "ok"} · new: {run_new.get("error") if q_new is None else "ok"} | {note or ""} |'); continue
        req = [f'request {i + 1}' for i in range(max(len(q_old), len(q_new)))
               if i >= len(q_old) or i >= len(q_new) or q_old[i]['sha256'] != q_new[i].get('normalised', q_new[i]['sha256'])]
        keys = diff_keys(run_old, run_new)
        if not req and not keys: same += 1
        what = 'identical' if not req and not keys else '; '.join(
            ([f'{len(q_old)} → {len(q_new)} requests'] if len(q_old) != len(q_new) else [])
            + ([f'{", ".join(req)} differ'] if req else [])
            + ([f'run.json: {", ".join(keys[:12])}{" …" if len(keys) > 12 else ""}'] if keys else []))
        norm = ' (pass 1 compared by its normalised hash)' if q_new and 'normalised' in q_new[0] else ''
        rows.append(f'| {b} | {what}{norm} | {len(q_old)} / {len(q_new)} | {note or ""} |')
    L = [f'# Request sweep: {commit} against the working tree', '',
         f'{same} of {len(audits)} identical (whole request by sha256, and run.json without `started` and the credit).', '',
         '| Book | Result | Requests (old / new) | Note |', '|---|---|---|---|', *rows, '']
    p = os.path.join(a.out, f'report-{commit}.md'); open(p, 'w', encoding='utf-8').write('\n'.join(L))
    print('\n'.join(L)); print(f'saved: {p}')
    sys.exit(0 if same == len(audits) else 1)

if __name__ == '__main__':
    main()
