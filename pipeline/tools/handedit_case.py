"""handedit_case.py: a real book edited by hand and brought back for review (handedit.py import, #62). No model, no cost.

    python3 tools/handedit_case.py [--book hawaii3] [--out DIR]

The unit tests bring back a one-page PDF; this brings back a real book's remediated result, so apply.py's automatic steps
(off-page text, the list rule, tab order, font maps, figure order) run a second time on a file that already holds them.
  1. A parent run of the book from its saved baseline reply (tests/baseline/<book>/reply.txt), as REPLY= does.
  2. export; then one figure's image in the copy is replaced by an image of another color (same size), as a person
     replacing a photo in Acrobat would.
  3. import --to review (no AI call); the work order is filled by hand with alt text for the gap's figure; run_api.sh
     applies it.
Checks, PASS or FAIL each:
  - import lists exactly that one figure and removes its alt in the working copy; the review gap names one figure;
  - the parent's PDF and the edited file are unchanged, and record.json `hand_edit` holds both sha256s;
  - verify.py's safety checks pass on the new result wherever they passed on the parent's;
  - the link descriptions are the parent's (apply.py redoes them on every run, from the carried `sections` and `links`);
  - apply.py failed nothing, and the new alt text is in the result while the other figures kept theirs;
  - what apply.py changed again on an already-remediated file (its `applied` counts), printed for a person to read.
The runs go to DIR (default: a temporary folder, kept when a check fails). veraPDF is off. Exit 1 on any FAIL.
"""
import sys, os, json, shutil, argparse, subprocess, tempfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE); ROOT = os.path.dirname(PIPE)
sys.path.insert(0, PIPE)
import pikepdf
from lib import handedit
from review import core

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def sample(book):
    for d in sorted(os.listdir(os.path.join(ROOT, 'samples'))):
        p = os.path.join(ROOT, 'samples', d, f'{book}.pdf')
        if os.path.exists(p): return p
    sys.exit(f'no sample named {book}.pdf under samples/')
def env(**kw):
    e = dict(os.environ, VERAPDF='off', PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **kw)
    for k in ('INTAKE_REUSE', 'REVIEW', 'DECIDE', 'REPLY', 'ESTIMATE', 'RUN_DIR', 'OUT', 'KEEP'):
        if k not in kw: e.pop(k, None)
    return e
def run(args, **kw):
    r = subprocess.run(args, cwd=PIPE, env=env(**kw), capture_output=True, text=True)
    if r.returncode != 0: print(r.stdout[-3000:], r.stderr[-3000:], sep='\n'); sys.exit(f'failed: {" ".join(map(str, args[:3]))} …')
    return r

def swap_one(src, dst):
    """Replace the first figure's image (one that has alt text and one image stream) with a solid image of the same size.
    Returns (page, alt)."""
    figs = [f for f in handedit.figures(src) if f['alt'] and len(f['shas']) == 1 and f['shas'][0]]
    if not figs: sys.exit('no figure with alt text and one image in this book')
    f = figs[0]
    pdf = pikepdf.open(src)
    def walk(res, d=0):
        for _, x in ((res or {}).get('/XObject') or {}).items():
            if str(x.get('/Subtype')) == '/Image':
                try:
                    if hashlib.sha256(x.read_raw_bytes()).hexdigest() == f['shas'][0]: return x
                except Exception: pass
            elif str(x.get('/Subtype')) == '/Form' and d < 8:
                y = walk(x.get('/Resources'), d + 1)
                if y is not None: return y
    im = walk(pdf.pages[f['page'] - 1].obj.get('/Resources'))
    if im is None: sys.exit(f'the image of figure {f["obj"]} was not found on PDF {f["page"]}')
    w, h = int(im.Width), int(im.Height)
    im.write(b'\x20\xa0\x60' * (w * h))                        # a solid green, uncompressed
    for k in ('/Filter', '/DecodeParms', '/SMask', '/Mask', '/Decode'):
        if k in im: del im[k]
    im.ColorSpace = pikepdf.Name.DeviceRGB; im.BitsPerComponent = 8
    pdf.save(dst)
    return f['page'], f['alt']

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--book', default='hawaii3'); ap.add_argument('--out')
    a = ap.parse_args()
    reply = os.path.join(PIPE, 'tests', 'baseline', a.book, 'reply.txt')
    if not os.path.exists(reply): sys.exit(f'no saved reply for {a.book} in tests/baseline/')
    out = a.out or tempfile.mkdtemp(prefix='handedit-case-'); runs = os.path.join(out, 'runs'); os.makedirs(out, exist_ok=True)
    fails = []
    def check(ok, what): print(('PASS ' if ok else 'FAIL ') + what); ok or fails.append(what)

    print(f'▶ parent run of {a.book} from its saved reply (no cost)')
    run(['bash', 'run_api.sh', sample(a.book), a.book, 'parent'], RUNS_DIR=runs, REPLY=reply)
    P = os.path.join(runs, a.book, 'parent'); prec = json.load(open(os.path.join(P, 'record.json'), encoding='utf-8'))
    res = os.path.join(P, prec['document']['output']); res_sha = sha(res)
    copy = os.path.join(out, 'copy.pdf'); edited = os.path.join(out, 'edited.pdf')
    run([sys.executable, 'handedit.py', 'export', P, '--to', copy, '--by', 'handedit_case'])
    page, old_alt = swap_one(copy, edited); ed_sha = sha(edited)
    print(f'▶ replaced the image of a figure on PDF {page}; import --to review')
    run([sys.executable, 'handedit.py', 'import', P, edited, '--by', 'handedit_case', '--note', f'replaced the image on PDF {page}', '--label', 'he'])
    C = os.path.join(runs, a.book, 'he')
    he = json.load(open(os.path.join(C, '_handedit', 'hand_edit.json'), encoding='utf-8'))
    check([f['page'] for f in he['figures_changed']] == [page] and he['input'] and not he['alt_not_removed'],
          f'import lists the one figure on PDF {page} and removed its alt ({len(he["figures_changed"])} listed)')
    digest = json.load(open(os.path.join(C, '_audit', 'digest.json'), encoding='utf-8'))
    wo_p = os.path.join(C, 'workorder.json'); wo = json.load(open(wo_p, encoding='utf-8'))
    gap = next((g for g in core.gaps(wo, digest) if g['id'] == 'figures_without_alt'), None)
    new_bare = [o for o in (gap or {}).get('objs', []) if (next((f for f in digest['figures'] if f['obj'] == o), {}) or {}).get('page') == page]
    check(len(new_bare) == 1, f'the review gap names the figure on PDF {page} ({len((gap or {}).get("objs", []))} figures without alt in all)')
    if new_bare:
        wo['alt'] = [{'obj': new_bare[0], 'alt': 'A solid green rectangle (test image)', 'why': 'handedit_case'}]
        json.dump(wo, open(wo_p, 'w', encoding='utf-8'), indent=1)
    run([sys.executable, 'review_workorder.py', C, '--reviewer', 'handedit_case', '--note', 'handedit_case: only the new figure'])
    print('▶ apply the reviewed order')
    run(['bash', 'run_api.sh', os.path.join(C, '_handedit', he['edited']['file']), a.book, 'he'], RUN_DIR=C, OUT=prec['document']['output'])
    rec = json.load(open(os.path.join(C, 'record.json'), encoding='utf-8'))
    h = rec.get('hand_edit') or {}
    check(sha(res) == res_sha and sha(edited) == ed_sha, 'the parent\'s result and the edited file are unchanged')
    check(h.get('base_sha256') == res_sha and (h.get('edited') or {}).get('sha256') == ed_sha and rec['document']['sha256'] == ed_sha,
          'record.json hand_edit holds both sha256s; the edited file is the source')
    ss = (rec.get('glance') or {}).get('safety') or []
    check(not (rec.get('apply') or {}).get('failed'), f'apply.py failed nothing ({len((rec.get("apply") or {}).get("rejected") or [])} rejected)')
    was_ok = {x['what']: x.get('ok') for x in (prec.get('glance') or {}).get('safety') or []}
    worse = [x['what'] for x in ss if x.get('ok') is False and was_ok.get(x['what']) is not False]
    check(bool(ss) and not worse, 'verify.py\'s safety checks pass wherever the parent\'s did'
          + (f': now failing: {", ".join(worse)}' if worse else f' ({sum(1 for x in ss if not x.get("ok"))} already failing in the parent)'))
    def links(p):
        with pikepdf.open(p) as pdf:
            return [str(a.get('/Contents', '')) for g in pdf.pages for a in (g.obj.get('/Annots') or []) if a.get('/Subtype') == '/Link']
    la, lb = links(res), links(os.path.join(C, rec['document']['output']))
    diff = [(x, y) for x, y in zip(la, lb) if x != y]
    check(len(la) == len(lb) and not diff, f'link descriptions are the parent\'s ({len(diff)} of {len(la)} differ'
          + (f', e.g. "{diff[0][0]}" → "{diff[0][1]}"' if diff else '') + ')')
    after = handedit.figures(os.path.join(C, rec['document']['output'])); was = handedit.figures(res)
    check(any(f['alt'] == 'A solid green rectangle (test image)' for f in after), 'the new alt text is in the result')
    lost = sum(1 for f in was if f['alt']) - sum(1 for f in after if f['alt'])
    check(lost <= 0, f'no other figure lost its alt text ({sum(1 for f in after if f["alt"])} with alt after, {sum(1 for f in was if f["alt"])} before)')
    print('\nWhat apply.py did again on the already-remediated file (read this):')
    ap_ = rec.get('apply') or {}
    for k, val in (ap_.get('applied') or {}).items():
        if val: print(f'  {k}: {val if not isinstance(val, (list, dict)) else len(val)}')
    for k in ('offpage', 'list_rule', 'font_maps', 'tabs_set', 'section_move'):
        if ap_.get(k): print(f'  {k}: {json.dumps(ap_[k])[:200]}')
    print(f'\n{len(fails)} FAIL' if fails else '\nall PASS', f'· runs in {out}')
    if not fails and not a.out: shutil.rmtree(out, ignore_errors=True)
    sys.exit(1 if fails else 0)

if __name__ == '__main__': main()
