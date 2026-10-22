"""compare_runs.py: are two runs' review.md files the same, book by book? No model, nothing sent, nothing changed.

    python3 tools/compare_runs.py <label-a> <label-b> [--runs-dir DIR] [--show N]

A label is a batch folder under runs/batches/ (e.g. s1-g3), or a prefix that names several of them (s1 → s1-g1, s1-g2, …;
a folder counts when its name is the prefix followed by "-"). Books are matched by folder name. Each review.md is compared
line by line, byte for byte, leaving out the two lines that change on every run: "Time: …" and the run-start line
("329 pages · run 2026-10-20T… · model …"). Everything else, "At a glance" included, must be identical.

Prints one line per book (identical / N lines differ, with the first difference / missing on one side) and a total.
Exit code 0 when every book is identical, 1 otherwise. Used as the acceptance test when review.md's writing code changes:
rerun the same books with FROM= on both versions of the code, then compare the two labels.
"""
import sys, os, re, argparse, difflib

VOLATILE = [re.compile(r'^Time: '), re.compile(r'^(\d+|not counted) pages · run ')]

def books(runs, label):
    """{book: path to its review.md} for a batch folder, or for every batch folder named <label>-…"""
    base = os.path.join(runs, 'batches')
    dirs = [label] if os.path.isdir(os.path.join(base, label)) else sorted(d for d in os.listdir(base) if d.startswith(label + '-') and os.path.isdir(os.path.join(base, d)))
    out = {}
    for d in dirs:
        for b in sorted(os.listdir(os.path.join(base, d))):
            p = os.path.join(base, d, b, 'review.md')
            if os.path.isfile(p):
                if b in out: sys.exit(f'{b} is in more than one folder for "{label}": {out[b]} and {p}')
                out[b] = p
    return out

def kept(path):
    return [l for l in open(path, encoding='utf-8').read().split('\n') if not any(rx.match(l) for rx in VOLATILE)]

def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--runs-dir', default=os.environ.get('RUNS_DIR') or os.path.join(os.path.dirname(here), 'runs'))
    ap.add_argument('--show', type=int, default=1, help='differing lines to show per book (default 1)')
    a = ap.parse_args()
    A, B = books(a.runs_dir, a.a), books(a.runs_dir, a.b)
    if not A and not B: sys.exit(f'no review.md found for "{a.a}" or "{a.b}" under {a.runs_dir}/batches')
    same = 0
    for b in sorted(set(A) | set(B)):
        if b not in A or b not in B:
            print(f'{b:16} missing in {a.a if b not in A else a.b}'); continue
        x, y = kept(A[b]), kept(B[b])
        if x == y: same += 1; print(f'{b:16} identical ({len(x)} lines)'); continue
        diff = [l for l in difflib.unified_diff(x, y, lineterm='', n=0) if l[:1] in '+-' and not l.startswith(('+++', '---'))]
        first = next(i for i, (p, q) in enumerate(zip(x + [None], y + [None])) if p != q) + 1
        print(f'{b:16} {sum(1 for l in diff if l.startswith("-"))} lines differ (- {a.a} / + {a.b}), first at line {first} of the compared text')
        for l in diff[:2 * a.show]: print(f'    {l[:200]}')
    n = len(set(A) | set(B))
    print(f'{same} of {n} books identical')
    sys.exit(0 if same == n else 1)

if __name__ == '__main__':
    main()
