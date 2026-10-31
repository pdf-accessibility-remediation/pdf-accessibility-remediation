"""reorder_case.py: move_section on a real book's tag tree, from a hand-written reply. No model, no cost.

    python3 tools/reorder_case.py [--book godzone] [--moves 1|2] [--out DIR]

No saved reply uses move_section, so the regression test never reaches it on a real tree. This takes a tagged sample,
moves one section one place later among its sibling sections in the tag tree (the pages do not change), and runs
run_api.sh on that copy with a reply that holds only a move_section putting it back (no object numbers, so it fits the
copy whatever pikepdf renumbers). Then it checks, PASS or FAIL each:
  - the audit flags the swapped pair (lib/readorder.py);
  - the review page's preview finds the one section and its host, and shows the order apply.py then makes;
  - apply.py made the move, and its log names the same section and host as the preview;
  - the sections under that host read in the original book's order again;
  - verify.py's section check finds nothing new.
--moves 2 swaps two separate pairs and puts both back with a reply holding two moves (a list, prompt v9), each
matched on the tree the first left, and checks each the same way (the preview chained as the review page does).
The section chosen has no sections inside it (or move_section would find several) and a sibling before it. The copy and
the run go to DIR (default: a temporary folder, kept when a check fails). veraPDF is off. Exit 1 on any FAIL.
"""
import sys, os, json, shutil, argparse, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE); ROOT = os.path.dirname(PIPE)
sys.path.insert(0, PIPE)
import pikepdf
from lib import readorder
from review import core

def sample(book):
    for d in sorted(os.listdir(os.path.join(ROOT, 'samples'))):
        p = os.path.join(ROOT, 'samples', d, f'{book}.pdf')
        if os.path.exists(p): return p
    sys.exit(f'no sample named {book}.pdf under samples/')

class Tree:
    """apply.py's view of a tag tree: the Document, its sections (readorder.GROUPING) and the pages under a tag."""
    def __init__(self, pdf):
        st = pdf.Root.StructTreeRoot
        self.px = {g.obj.objgen: i for i, g in enumerate(pdf.pages, 1)}
        self.rm = {str(k).lstrip('/'): str(v).lstrip('/') for k, v in (st.get('/RoleMap') or {}).items()}
        top = self.kids(st)
        self.doc = next((k for k in top if self.is_elem(k) and self.mapped(self.S(k)) == 'Document'), st)
    def kids(self, n):
        k = n.get('/K'); return [] if k is None else (list(k) if isinstance(k, pikepdf.Array) else [k])
    def is_elem(self, k): return isinstance(k, pikepdf.Dictionary) and '/S' in k and str(k.get('/Type', '/StructElem')) not in ('/MCR', '/OBJR')
    def S(self, n): return str(n.get('/S', '')).lstrip('/')
    def mapped(self, s):
        for _ in range(5): s = self.rm.get(s, s)
        return s
    def group(self, n): return self.is_elem(n) and (self.S(n) in readorder.GROUPING or self.mapped(self.S(n)) in readorder.GROUPING)
    def pages(self, n, pg=None, acc=None, d=0):
        acc = set() if acc is None else acc
        if isinstance(n, int): acc.add(pg); return acc
        if not isinstance(n, pikepdf.Dictionary): return acc
        t = str(n.get('/Type'))
        if t == '/OBJR': return acc
        pg = self.px.get(n.Pg.objgen) if '/Pg' in n else pg
        if t == '/MCR': acc.add(pg); return acc
        if d < 60:
            for k in self.kids(n): self.pages(k, pg, acc, d + 1)
        return acc
    def pp(self, n): return self.pages(n) - {None}
    def groups(self, n): return [k for k in self.kids(n) if self.group(k)]
    def move(self, a, b, before):
        return readorder.section_move(self.doc, self.groups, lambda c: [min(self.pp(k)) for k in self.kids(c) if self.is_elem(k) and self.pp(k)],
                                      lambda c: (min(self.pp(c)), max(self.pp(c))) if self.pp(c) else None, a, b, before)
    def sections(self):
        out, stack = [], [self.doc]
        while stack:
            n = stack.pop()
            for k in self.groups(n): out.append((k, n)); stack.append(k)
        return out
    def order(self, host):
        """First pages of host's child sections, in reading order."""
        return [min(self.pp(k)) for k in self.groups(host) if self.pp(k)]

def shuffle(src, dst, n=1):
    """Swap n sections, each with the next one under a section host (n separate pairs); returns [(spec, the host's
    original order, the host's pages)] or exits."""
    pdf = pikepdf.open(src); t = Tree(pdf); out, used, orig = [], set(), {}
    for c, par in t.sections():
        if len(out) == n: break
        if par is t.doc or t.groups(c) or not t.pp(c) or c.objgen in used: continue
        sib = [k for k in t.kids(par) if t.is_elem(k)]
        i = next(j for j, k in enumerate(sib) if k.objgen == c.objgen)
        if i == 0 or i + 1 >= len(sib) or not t.group(sib[i + 1]) or not t.pp(sib[i + 1]) or not t.pp(sib[i - 1]): continue
        y = sib[i + 1]
        if max(t.pp(c)) >= min(t.pp(y)) or min(t.pp(sib[i - 1])) >= min(t.pp(c)) or used & {y.objgen, sib[i - 1].objgen}: continue
        before = orig.setdefault(par.objgen, t.order(par))        # the host's order before any swap
        ks = t.kids(par); a = next(j for j, k in enumerate(ks) if isinstance(k, pikepdf.Dictionary) and k.objgen == c.objgen)
        b = next(j for j, k in enumerate(ks) if isinstance(k, pikepdf.Dictionary) and k.objgen == y.objgen)
        ks[a], ks[b] = ks[b], ks[a]; par.K = pikepdf.Array(ks)
        spec = {'pages': [min(t.pp(c)), max(t.pp(c))], 'before_page': min(t.pp(y))}
        cand, host = t.move(spec['pages'][0], spec['pages'][1], spec['before_page'])
        if len(cand) == 1 and host is not None and host.objgen == par.objgen:
            out.append((spec, before, [min(t.pp(par)), max(t.pp(par))])); used |= {c.objgen, y.objgen, sib[i - 1].objgen}; continue
        ks[a], ks[b] = ks[b], ks[a]; par.K = pikepdf.Array(ks)          # another section would match too: try the next one
    if len(out) < n: sys.exit(f'{os.path.basename(src)}: not {n} sections that fit (a leaf section between two others under a section host)')
    pdf.save(dst)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--book', default='godzone'); ap.add_argument('--out')
    ap.add_argument('--moves', type=int, choices=(1, 2), default=1, help='sections to swap and move back (2: a list of two moves)')
    a = ap.parse_args()
    out = a.out or tempfile.mkdtemp(prefix='reorder-case-'); os.makedirs(out, exist_ok=True)
    src = os.path.join(out, f'{a.book}.pdf')
    cases = shuffle(sample(a.book), src, a.moves)
    specs = [c[0] for c in cases]
    for spec, _, _ in cases:
        print(f'{a.book}: section on PDF {spec["pages"][0]}-{spec["pages"][1]} now read after the one starting on PDF {spec["before_page"]}; '
              f'reply: move_section {json.dumps(spec)}')
    reply = os.path.join(out, 'reply.txt')
    ms = {**specs[0], 'why': 'reorder_case.py'} if a.moves == 1 else [{**sp, 'why': 'reorder_case.py'} for sp in specs]
    open(reply, 'w').write('```json\n' + json.dumps({'schema': 'workorder/0.1', 'move_section': ms}, indent=1) + '\n```\n')
    R = os.path.join(out, 'run')
    env = dict(os.environ, REPLY=reply, RUN_DIR=R, AUTO='1', KEEP='1', VERAPDF='off', INTAKE='off')
    env['PATH'] = os.path.dirname(sys.executable) + os.pathsep + env.get('PATH', '')
    with open(R + '.log', 'w') as f:
        rc = subprocess.run(['bash', os.path.join(PIPE, 'run_api.sh'), src, f'{a.book}-reorder', 'case'], env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc != 0 or not os.path.exists(os.path.join(R, 'record.json')):
        print(''.join(open(R + '.log').readlines()[-20:])); print(f'FAIL  run_api.sh failed (exit {rc}); folder: {out}'); sys.exit(1)
    rec = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
    digest = json.load(open(os.path.join(R, '_audit', 'digest.json'), encoding='utf-8'))
    full = json.load(open(os.path.join(R, '_audit', 'fulltext.json'), encoding='utf-8'))
    ro = core.reading_order(digest, full)
    pvs = core.chain_previews(ro['entries'], [(sp['pages'], sp['before_page']) for sp in specs])
    logs = rec['apply'].get('section_moves') or [rec['apply'].get('section_move')]
    pdf = pikepdf.open(os.path.join(R, next(f for f in os.listdir(R) if f.endswith('_remediated.pdf')))); t = Tree(pdf)
    so = rec['verify']['wcag']['section_order']
    flagged = {ro['entries'][x['i']]['first'] for x in ro['flagged']}
    checks = [('apply.py made every move', (rec['apply'].get('applied') or {}).get('order: section moved') == len(specs), f'rejected: {rec["apply"].get("rejected")}')]
    for k, ((spec, before, host_pages), pv) in enumerate(zip(cases, pvs)):
        log = (logs[k] if k < len(logs) else None) or {}
        host = next((h for h, _ in t.sections() if t.pp(h) and [min(t.pp(h)), max(t.pp(h))] == host_pages and sorted(t.order(h)) == sorted(before)), None)
        tag = f'move {k + 1}: ' if len(specs) > 1 else ''
        checks += [
            (tag + 'the audit flags the swapped pair', bool(flagged & {spec['pages'][0], spec['before_page']}), f'flagged first pages: {sorted(flagged)}'),
            (tag + 'the preview finds one section and its host', pv.get('candidates') == 1 and pv.get('host_found'), f'candidates {pv.get("candidates")}, host {pv.get("host_found")}'),
            (tag + 'apply.py moved what the preview showed', log.get('pages') == pv.get('moved_pages') and log.get('host_pages') == pv.get('host_pages'),
             f'apply {log.get("pages")} in {log.get("host_pages")}, preview {pv.get("moved_pages")} in {pv.get("host_pages")}'),
            (tag + 'the host reads in the original order again', host is not None and t.order(host) == before, f'now {t.order(host) if host is not None else "host not found"}, original {before}'),
        ]
        if k == len(specs) - 1 or cases[k + 1][2] != host_pages:     # the last move under this host: its order is the one apply.py made
            checks.append((tag + 'the preview shows the order apply.py made', host is not None and
                [e['first'] for e in pv.get('siblings_after') or [] if e.get('style') and e['first'] is not None and
                 (e['style'] in readorder.GROUPING or t.mapped(e['style']) in readorder.GROUPING)] == t.order(host),
                f'preview {[e["first"] for e in pv.get("siblings_after") or []]}'))
    checks.append(('verify finds nothing new', so['new_count'] == 0, f'{so["new_count"]} new: {[x for x in so["flagged"] if x["new"]][:3]}'))
    bad = 0
    for name, ok, detail in checks:
        print(f'{"PASS" if ok else "FAIL"}  {name}' + ('' if ok else f': {detail}')); bad += not ok
    print(f'{len(checks) - bad} of {len(checks)} checks passed' + (f'; folder: {out}' if bad or a.out else ''))
    if not bad and not a.out: shutil.rmtree(out, ignore_errors=True)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
