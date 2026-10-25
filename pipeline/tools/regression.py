"""regression.py: does the pipeline still turn the baseline books into the same result? No model, no cost.

    python3 tools/regression.py [--books godzone,clans] [--out DIR] [--keep]
    python3 tools/regression.py --update --reason "why the output changed" [--seed RUNS_BATCH_DIR] [--from-dir DIR]

Each baseline book (tests/baseline/<book>/) holds a saved model reply (reply.txt, with reply.txt.meta.json: the
original model and temperature), the review.md it gave, and expect.json: a fingerprint of its record.json (veraPDF
rules before and after, what apply.py did, what the work-order checks dropped, the tag tree verify.py counted).
Each book is run again with run_api.sh REPLY= (the saved reply, so no API call) and compared:
  - expect.json, field by field;
  - review.md, line by line, leaving out "Time:", the run-start line and "Libraries:" (they change on every run or
    with the Python version: tools/compare_runs.py's rule, plus Libraries);
  - checks that hold whatever the baseline says: veraPDF ran, no more WCAG rules fail after than before, nothing failed
    in apply, no page looks different, no page's text changed, the original is unchanged.
An untagged book's folder also holds _intake/ (intake.json, intake.pdf): the intake result its reply was written for,
reused with INTAKE_REUSE=1, so OCR and auto-tagging (which vary with the Tesseract and OpenDataLoader versions) are not
rerun; tools/intake_cases.py tests intake itself.
Exit 0 when every book matches, 1 otherwise. Needs veraPDF (vera.py --check); without it nothing is compared.

--update reruns the books (or reads finished runs from --from-dir DIR/<book>/, e.g. a CI artifact) and writes their
review.md and expect.json as the new baseline, adding the reason to tests/baseline/UPDATES.md. Use it only when every
difference is one the change meant to make. --seed DIR copies each book's reply from DIR/<book>/record.json first
(DIR is a batch folder such as ../runs/batches/all9-v8, or one run folder such as ../runs/ilokano/base1 for a single
--books entry; an untagged book's _intake/ is copied too): needed once, and again whenever the prompt version changes.
"""
import sys, os, re, json, shutil, hashlib, argparse, datetime, subprocess, tempfile, difflib
HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE); ROOT = os.path.dirname(PIPE)
sys.path.insert(0, HERE)
import compare_runs

BASE = os.path.join(PIPE, 'tests', 'baseline')
BOOKS = ['godzone', 'clans']
IGNORE = [re.compile(r'^Libraries: ')]       # with compare_runs.VOLATILE: Time and the run-start line

def prompt_name():
    return re.search(r"^PROMPT_NAME = '([^']+)'", open(os.path.join(PIPE, 'decide.py'), encoding='utf-8').read(), re.M).group(1)

def sample(book):
    for d in sorted(os.listdir(os.path.join(ROOT, 'samples'))):
        p = os.path.join(ROOT, 'samples', d, f'{book}.pdf')
        if os.path.exists(p): return p
    sys.exit(f'no sample named {book}.pdf under samples/')

def fingerprint(r):
    """The parts of record.json the baseline holds: what changes when the pipeline's result changes, not timing or cost."""
    def vera(v): return {'totals': v.get('totals'), 'failed': {x['id']: x.get('failed') for x in v.get('rules') or []}}
    a, v = r['apply'], r['verify']
    return {'verapdf': {k: vera(r['verapdf'][k]) for k in ('before', 'after')},
            'apply': {'applied': a.get('applied'), **{k: len(a.get(k) or []) for k in ('rejected', 'failed', 'deferred', 'empty_notes_removed')}},
            'validation_dropped': sorted(f'{d.get("where")}: {d.get("why")}' for d in r.get('validation_dropped') or []),
            'verify': {'tree_types': v['tree'].get('types'), 'headings': v['headings'].get('counts'), 'skipped_levels': v['headings'].get('skipped_levels'),
                       'figures': v.get('figures'), 'structure': {k: len(x) if isinstance(x, list) else x for k, x in v['structure'].items() if not k.endswith('_examples')},
                       'pixel_pages_differing': v.get('pixel_pages_differing'), 'text_pages_changed': v.get('text_pages_changed'),
                       'untagged_chars': v.get('untagged_chars'), 'artifact_chars': v.get('artifact_chars')}}

def invariants(r, src):
    """What must hold for any good run, whatever the baseline says."""
    bad, vb, va = [], r['verapdf'].get('before') or {}, r['verapdf'].get('after') or {}
    if 'not_run' in va or 'totals' not in va: bad.append('veraPDF did not run on the result')
    elif va['totals']['wcag_failed_rules'] > (vb.get('totals') or {}).get('wcag_failed_rules', 0):
        bad.append(f'more WCAG rules fail after ({va["totals"]["wcag_failed_rules"]}) than before ({vb["totals"]["wcag_failed_rules"]})')
    if r['apply'].get('failed'): bad.append(f'apply.failed: {len(r["apply"]["failed"])} steps')
    if r['verify'].get('pixel_pages_differing'): bad.append(f'pages look different: {r["verify"]["pixel_pages_differing"][:10]}')
    if r['verify'].get('text_pages_changed'): bad.append(f'page text changed: {r["verify"]["text_pages_changed"][:10]}')
    if r['document']['sha256'] != hashlib.sha256(open(src, 'rb').read()).hexdigest(): bad.append('the original PDF changed')
    return bad

def diff(a, b, path=''):
    """[(field, baseline value, new value)] where two fingerprints differ."""
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b), key=str) for d in diff(a.get(k), b.get(k), f'{path}.{k}' if path else str(k))]
    return [] if a == b else [(path, a, b)]

def run_book(book, run_dir):
    """run_api.sh on the sample with the saved reply; the finished run folder, or exit with its log."""
    env = dict(os.environ, REPLY=os.path.join(BASE, book, 'reply.txt'), RUN_DIR=run_dir, AUTO='1')
    frozen = os.path.join(BASE, book, '_intake')
    if os.path.exists(os.path.join(frozen, 'intake.json')):    # an untagged book: reuse the intake result the reply was written for
        shutil.copytree(frozen, os.path.join(run_dir, '_intake')); env['INTAKE_REUSE'] = '1'   # (as batch_api.sh FROM= does)
    env['PATH'] = os.path.dirname(sys.executable) + os.pathsep + env.get('PATH', '')   # run_api.sh's python3 is this one
    log = run_dir + '.log'
    with open(log, 'w') as f:
        rc = subprocess.run(['bash', os.path.join(PIPE, 'run_api.sh'), sample(book), book, 'regression'], env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc != 0 or not os.path.exists(os.path.join(run_dir, 'record.json')):
        sys.stdout.write(''.join(open(log).readlines()[-30:]))
        sys.exit(f'{book}: run_api.sh failed (exit {rc}); log: {log}')
    return run_dir

def seed(src_dir, books):
    for b in books:
        p = os.path.join(src_dir, b, 'record.json')
        if not os.path.exists(p) and len(books) == 1: p = os.path.join(src_dir, 'record.json')    # a single run folder: runs/<name>/<label>
        if not os.path.exists(p): sys.exit(f'--seed: no {p}')
        r = json.load(open(p, encoding='utf-8'))
        if not r.get('raw_reply'): sys.exit(f'--seed: {p} holds no raw_reply')
        os.makedirs(os.path.join(BASE, b), exist_ok=True)
        open(os.path.join(BASE, b, 'reply.txt'), 'w', encoding='utf-8').write(r['raw_reply'])
        json.dump({k: r['run'][k] for k in ('model', 'temperature') if k in r['run']}, open(os.path.join(BASE, b, 'reply.txt.meta.json'), 'w'), indent=1)
        prompt = os.path.basename(r['run'].get('prompt_file') or '')
        if prompt and prompt != prompt_name(): sys.exit(f'--seed: {b}\'s reply was made with {prompt}, but decide.py uses {prompt_name()}')
        old_in, new_in = os.path.join(os.path.dirname(p), '_intake'), os.path.join(BASE, b, '_intake')
        if os.path.exists(os.path.join(old_in, 'intake.pdf')):       # untagged: the reply refers to objects in this intake.pdf
            os.makedirs(new_in, exist_ok=True)
            for f in ('intake.json', 'intake.pdf'): shutil.copyfile(os.path.join(old_in, f), os.path.join(new_in, f))
        print(f'{b:10} reply seeded from {p}' + (' (with its intake result)' if os.path.exists(new_in) else ''))

def intake_drift(book):
    """A note when the frozen intake was made by another OpenDataLoader than requirements.txt pins: the regression test
    reuses the frozen result, so the newer auto-tagger is not tested here (tools/intake_cases.py --full tests it)."""
    j = os.path.join(BASE, book, '_intake', 'intake.json')
    if not os.path.exists(j): return None
    made = (json.load(open(j, encoding='utf-8')).get('tools') or {}).get('opendataloader_pdf')
    pin = re.search(r'^opendataloader-pdf==(\S+)', open(os.path.join(PIPE, 'requirements.txt')).read(), re.M)
    if pin and made != pin.group(1):
        return f'its frozen intake was made with OpenDataLoader {made}, requirements.txt pins {pin.group(1)}: re-seed it (docs/testing.md)'

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--books', help='comma-separated (default: every book in tests/baseline/)')
    ap.add_argument('--out', help='folder for the run folders (kept); default a temporary folder, removed when all match')
    ap.add_argument('--keep', action='store_true', help='keep the run folders')
    ap.add_argument('--update', action='store_true', help='write the new results as the baseline (needs --reason)')
    ap.add_argument('--reason', help='why the output changed: recorded in tests/baseline/UPDATES.md')
    ap.add_argument('--seed', metavar='RUNS_BATCH_DIR', help='with --update: copy each book\'s reply from RUNS_BATCH_DIR/<book>/record.json first')
    ap.add_argument('--from-dir', metavar='DIR', help='with --update: take finished runs from DIR/<book>/ (a CI artifact) instead of running')
    ap.add_argument('--show', type=int, default=5, help='differences to show per book (default 5)')
    a = ap.parse_args()
    if (a.seed or a.from_dir) and not a.update: sys.exit('--seed and --from-dir go with --update')
    if a.update and not (a.reason or '').strip(): sys.exit('--update needs --reason "why the output changed"')
    meta_p = os.path.join(BASE, 'meta.json')
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    books = a.books.split(',') if a.books else meta.get('books') or BOOKS
    if a.seed: seed(a.seed, books); meta['prompt'] = prompt_name()
    if meta.get('prompt') and meta['prompt'] != prompt_name():
        sys.exit(f'the baseline replies were made with {meta["prompt"]}, but decide.py now uses {prompt_name()}: re-seed the baseline '
                 f'(a paid run of {", ".join(books)}, then --update --seed; see docs/testing.md)')
    missing = [b for b in books if not os.path.exists(os.path.join(BASE, b, 'reply.txt'))]
    if missing: sys.exit(f'no saved reply for {", ".join(missing)}: run --update --seed RUNS_BATCH_DIR first')
    py = '.'.join(map(str, sys.version_info[:2]))
    if meta.get('python') and meta['python'] != py and not a.update:
        print(f'note: the baseline was made with Python {meta["python"]}, this is {py}: a difference may come from that')
    if not a.from_dir:
        v = subprocess.run([sys.executable, os.path.join(PIPE, 'vera.py'), '--check'], capture_output=True, text=True)
        if v.returncode != 0: sys.exit(f'veraPDF is needed (vera.py --check: {v.stdout.strip() or v.stderr.strip()}); see docs/verapdf.md')
    out = os.path.abspath(a.out) if a.out else tempfile.mkdtemp(prefix='regression-')
    os.makedirs(out, exist_ok=True)
    same, results = 0, {}
    for b in books:
        R = os.path.join(a.from_dir, b) if a.from_dir else os.path.join(out, b)
        if not a.from_dir:
            if os.path.exists(R): shutil.rmtree(R)
            print(f'{b:10} running (saved reply, no API call) …', flush=True); run_book(b, R)
        r = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
        results[b] = (R, r)
        drift = intake_drift(b)
        if drift: print(f'{b:10} note: {drift}')
        broken = invariants(r, sample(b))
        for x in broken: print(f'{b:10} BROKEN: {x}')
        exp_p, md_p = os.path.join(BASE, b, 'expect.json'), os.path.join(BASE, b, 'review.md')
        if not os.path.exists(exp_p) or not os.path.exists(md_p):
            print(f'{b:10} no baseline yet' + ('' if a.update else ': run --update'))
            continue
        d = diff(json.load(open(exp_p, encoding='utf-8')), fingerprint(r))
        x, y = compare_runs.kept(md_p, IGNORE), compare_runs.kept(os.path.join(R, 'review.md'), IGNORE)
        md = [l for l in difflib.unified_diff(x, y, lineterm='', n=0) if l[:1] in '+-' and not l.startswith(('+++', '---'))]
        if not d and not md and not broken: same += 1; print(f'{b:10} identical'); continue
        print(f'{b:10} {len(d)} record fields differ, {sum(1 for l in md if l.startswith("-"))} review.md lines differ (- baseline / + now)')
        for f, old, new in d[:a.show]: print(f'    {f}: {json.dumps(old, ensure_ascii=False)[:150]} → {json.dumps(new, ensure_ascii=False)[:150]}')
        for l in md[:2 * a.show]: print(f'    {l[:200]}')
    n = len(books)
    print(f'{same} of {n} books identical')
    if a.update:
        broken_books = [b for b in books if invariants(results[b][1], sample(b))]
        if broken_books: sys.exit(f'not updated: {", ".join(broken_books)} break checks that must always hold (above); that is a bug, not a new baseline')
        for b in books:
            R, r = results[b]
            shutil.copyfile(os.path.join(R, 'review.md'), os.path.join(BASE, b, 'review.md'))
            json.dump(fingerprint(r), open(os.path.join(BASE, b, 'expect.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False, sort_keys=True)
        meta.update({'books': list(dict.fromkeys((meta.get('books') or []) + books)), 'python': '.'.join(r['environment']['python'].split('.')[:2]) if a.from_dir else py,
                     'prompt': meta.get('prompt') or prompt_name()})
        json.dump(meta, open(meta_p, 'w'), indent=1)
        log = os.path.join(BASE, 'UPDATES.md')
        head = '' if os.path.exists(log) else '# Baseline updates\n\nWhy each regression baseline update was made (newest last). Written by `tools/regression.py --update`.\n'
        open(log, 'a', encoding='utf-8').write(f'{head}\n- {datetime.date.today()} · {", ".join(books)} · Python {meta["python"]} · {meta["prompt"]}: {a.reason.strip()}\n')
        print(f'baseline updated: {", ".join(books)} ({os.path.relpath(BASE, ROOT)})')
    if a.out or a.keep or same < n and not a.update: print(f'run folders: {out}')
    else: shutil.rmtree(out, ignore_errors=True)
    sys.exit(0 if a.update or same == n else 1)

if __name__ == '__main__':
    main()
