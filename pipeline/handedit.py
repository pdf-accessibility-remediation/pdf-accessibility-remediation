"""handedit.py: take a run's PDF out to edit it by hand (Acrobat or another tool), then bring the edited file back as a new run.

    python handedit.py export RUN_DIR [--to PATH] [--by NAME]                    # the remediated result, for editing
    python handedit.py export RUN_DIR --original --pdf ORIGINAL.pdf [--to PATH] [--by NAME]
    python handedit.py import RUN_DIR EDITED.pdf --by NAME --note "what changed" [--label LABEL] [--to review|pipeline]
                              [--base output|original] [--base-pdf ORIGINAL.pdf] [--no-run]

export copies the file (never the run's own) and logs it in RUN_DIR/hand_edits.json. Edit the copy, never the run's PDF:
its sha256 is what the release checks count.

import makes a new run of the same book, beside RUN_DIR (runs/<name>/<LABEL>/; default label handedit-YYYYMMDD-HHMM):
    _handedit/<edited file>   a copy of EDITED.pdf: the new run's source (record.json document.sha256)
    _handedit/input.pdf       the same with the alt text removed from each figure whose image changed (lib/handedit.py),
                              so the old alt is never reused for a new image; the run works on it (document.pipeline_input)
    _handedit/hand_edit.json  the link: parent run, base (output or original) and its sha256, the edited sha256, who, when,
                              the note, the figures whose alt was removed, the figures that lost their tag and the pages
                              whose text changed (Acrobat's Edit PDF can do both to pages nobody touched); record.json
                              keeps it as `hand_edit`
Then it runs run_api.sh on it:
    --to review    (default) no AI call (DECIDE=none) and stops for review (REVIEW=1): a person writes the new alt text on
                   the review page, where each changed figure shows as a figure with no alt; rerun the printed command
                   afterwards, or press Apply in the app
    --to pipeline  the whole pipeline: a new paid AI call (run_api.sh asks y/N first); ESTIMATE=1 and REPLY= work as usual
--no-run prints the run_api.sh command instead. RUN_DIR's hand_edits.json lists the new run. Nothing in RUN_DIR other than
hand_edits.json is written, and EDITED.pdf is never written to. Exit 3: the edited file is PDF 2.0 (lib/support.py).
"""
import sys, os, json, shutil, hashlib, datetime, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import support

HERE = os.path.dirname(os.path.abspath(__file__))

def die(msg, code=1): print(msg, file=sys.stderr); sys.exit(code)
def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def now(): return datetime.datetime.now().isoformat(timespec='seconds')
def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 >= len(argv) or argv[i + 1].startswith('--'): die(f'{name} needs a value')
        return argv[i + 1]
    return default
def load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None
def log(R, kind, entry):
    """Append to RUN_DIR/hand_edits.json ({'exports': [...], 'children': [...]}): the only file written in the parent run."""
    p = os.path.join(R, 'hand_edits.json'); d = load(p) or {'exports': [], 'children': []}
    d.setdefault(kind, []).append(entry)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)

def finished(R):
    rec = load(os.path.join(R, 'record.json'))
    if not isinstance(rec, dict): die(f'{R} holds no finished run (no record.json): a hand edit starts from a finished run')
    return rec

def output_of(R, rec):
    """The run's remediated PDF, refused when it is no longer the file the record describes (edited in place)."""
    doc = rec.get('document') or {}
    p = os.path.join(R, doc.get('output') or '')
    if not doc.get('output') or not os.path.isfile(p): die(f'the remediated PDF named in {R}/record.json is not there')
    want = doc.get('output_sha256')
    if want and sha_file(p) != want:
        die(f'{p} is not the file this run made (its sha256 differs from record.json document.output_sha256): it was changed in '
            'place. Edit an exported copy instead (handedit.py export), and keep the run\'s own PDF as it was made')
    return p, want or sha_file(p)

def original_of(R, rec, given, flag):
    """The run's original PDF: --pdf/--base-pdf when given, else the review basis's input when it is the original itself."""
    want = (rec.get('document') or {}).get('sha256')
    cands = [given] if given else [((load(os.path.join(R, 'reviews', 'basis.json')) or {}).get('input') or {}).get('path')]
    for p in cands:
        if p and os.path.isfile(p):
            if want and sha_file(p) != want: die(f'{p} is not this run\'s original (sha256 differs from record.json document.sha256)')
            return p, want or sha_file(p)
    die(f'the original PDF was not found: give it with {flag} ORIGINAL.pdf')

def export(argv):
    if not argv or argv[0].startswith('--'): die(__doc__)
    R = os.path.abspath(argv[0]); rec = finished(R)
    if '--original' in argv: src, sha = original_of(R, rec, opt(argv, '--pdf'), '--pdf')
    else: src, sha = output_of(R, rec)
    stem = os.path.splitext(os.path.basename(src))[0]
    to = os.path.abspath(opt(argv, '--to') or os.path.join(R, 'exports', f'{stem}_for-editing.pdf'))
    if os.path.exists(to): die(f'{to} already exists: choose another --to')
    os.makedirs(os.path.dirname(to), exist_ok=True); shutil.copyfile(src, to)
    log(R, 'exports', {'when': now(), 'by': opt(argv, '--by'), 'base': 'original' if '--original' in argv else 'output',
                       'sha256': sha, 'to': to})
    print(f'exported: {to}\nEdit this copy, then bring it back:\n'
          f'  python3 {os.path.join(HERE, "handedit.py")} import "{R}" "{to}" --by "<your name>" --note "<what you changed>"')

def child_dir(R, rec, label):
    """Beside the parent: runs/<name>/<label>/. A batch book (runs/batches/<batch>/<name>/) gets runs/<name>/<label>/."""
    parts = os.path.normpath(R).split(os.sep)
    if 'batches' in parts[:-2]:
        i = len(parts) - 1 - parts[::-1].index('batches')
        return os.sep.join(parts[:i] + [parts[-1], label]), parts[-1]
    return os.path.join(os.path.dirname(R), label), os.path.basename(os.path.dirname(R))

def bring_back(argv):
    if len(argv) < 2 or argv[0].startswith('--') or argv[1].startswith('--'): die(__doc__)
    R, edited = os.path.abspath(argv[0]), os.path.abspath(argv[1]); rec = finished(R)
    by, note = opt(argv, '--by'), opt(argv, '--note')
    if not by: die('say who edited the PDF: --by NAME (it is kept in the record)')
    if not note: die('say what was changed: --note "replaced the low-resolution photo on PDF 12" (it is kept in the record)')
    base, to = opt(argv, '--base', 'output'), opt(argv, '--to', 'review')
    if base not in ('output', 'original'): die('--base is output (the remediated result, the default) or original')
    if to not in ('review', 'pipeline'): die('--to is review (no AI call, the default) or pipeline (a new paid AI call)')
    if not os.path.isfile(edited): die(f'no such PDF: {edited}')
    base_pdf, base_sha = output_of(R, rec) if base == 'output' else original_of(R, rec, opt(argv, '--base-pdf'), '--base-pdf')
    ed_sha = sha_file(edited)
    if ed_sha == base_sha: die(f'{edited} is the same file as the {"remediated result" if base == "output" else "original"} (same sha256): nothing was edited')
    import pikepdf
    with pikepdf.open(edited) as pdf:
        why = support.unsupported(pdf)
    if why: die(f'handedit: stopped: {why}', 3)

    label = opt(argv, '--label') or 'handedit-' + datetime.datetime.now().strftime('%Y%m%d-%H%M')
    C, name = child_dir(R, rec, label)
    if os.path.exists(os.path.join(C, 'record.json')): die(f'{C} already holds a finished run: choose another --label')
    H = os.path.join(C, '_handedit')
    old = load(os.path.join(H, 'hand_edit.json'))
    if os.path.exists(C) and not (old and (old.get('edited') or {}).get('sha256') == ed_sha and old.get('to') == to):
        die(f'{C} already exists for another file or mode: choose another --label')
    os.makedirs(H, exist_ok=True)
    fname = os.path.basename(edited)
    if fname == 'input.pdf': fname = 'edited.pdf'                     # input.pdf is the working copy's name
    copy = os.path.join(H, fname)
    if not old:
        shutil.copyfile(edited, copy)
        if sha_file(copy) != ed_sha: die(f'the copy of {edited} does not match it (sha256): the file changed while it was copied')
        from lib import handedit
        print('▶ comparing the edited PDF with the file it was made from (images, page by page)')
        ch = handedit.changed(base_pdf, copy)
        objs = [f['obj'] for f in ch['figures'] if f.get('alt')]     # a figure with no alt has nothing stale to remove
        missing, inp = [], None
        if objs:
            ip = os.path.join(H, 'input.pdf')
            missing = handedit.strip_stale_alt(copy, ip, objs)
            inp = {'file': '_handedit/input.pdf', 'sha256': sha_file(ip)}
        doc = rec.get('document') or {}
        he = {'schema': 'hand_edit/1', 'when': now(), 'by': by, 'note': note, 'to': to, 'base': base, 'base_sha256': base_sha,
              'parent': {'run': R, 'output': doc.get('output'), 'output_sha256': doc.get('output_sha256'),
                         'original': doc.get('file'), 'original_sha256': doc.get('sha256')},
              'edited': {'file': fname, 'sha256': ed_sha, 'given_as': edited}, 'input': inp,
              'pages': ch['pages'], 'figures_changed': [{'page': f['page'], 'alt': f['alt']} for f in ch['figures']],
              'alt_not_removed': [f for f in ch['figures'] if f['obj'] in missing],
              'outside_figures': ch['outside_figures'], 'images_new': len(ch['new_images']), 'images_removed': len(ch['removed_images']),
              'figures_lost': ch['figures_lost'], 'text_pages': ch['text_pages']}
        with open(os.path.join(H, 'hand_edit.json'), 'w', encoding='utf-8') as f: json.dump(he, f, ensure_ascii=False, indent=1)
        log(R, 'children', {'when': he['when'], 'run': C, 'by': by, 'note': note, 'to': to, 'edited_sha256': ed_sha})
        print(f'  {len(ch["new_images"])} new image(s); {len(ch["figures"])} figure(s) hold a new one'
              + (f', alt text removed from {len(objs) - len(missing)}' if objs else '')
              + (f'; {len(ch["outside_figures"])} new image(s) in no figure' if ch['outside_figures'] else '')
              + (f'; pages {ch["pages"][0]} → {ch["pages"][1]}' if ch['pages'][0] != ch['pages'][1] else ''))
        tp = ch['text_pages']; same = sum(1 for x in tp if x['heard_same'])
        if ch['figures_lost'] or tp:
            print('  ' + '; '.join(x for x in (
                f'⚠ {len(ch["figures_lost"])} figure(s) lost their tag (PDF ' + ', '.join(str(f['page']) for f in ch['figures_lost']) + ')' if ch['figures_lost'] else '',
                f'text changed on {len(tp)} page(s), of which {same} read the same with spaces from gaps' if tp else '') if x))
        if missing: print(f'  ⚠ alt text left on {len(missing)} figure(s) that could not be found again: check them on the review page')
    else: print(f'▶ {C}: the edited PDF is already in place; carrying on')

    env = {'RUN_DIR': C, 'OUT': (rec.get('document') or {}).get('output') or ''}
    if to == 'review': env.update({'DECIDE': 'none', 'REVIEW': '1'})
    cmd = ['bash', os.path.join(HERE, 'run_api.sh'), copy, name, label]
    shown = ' '.join(f'{k}={v}' for k, v in env.items() if v) + ' ' + ' '.join(f'"{x}"' if ' ' in x else x for x in cmd)
    if '--no-run' in argv: print(f'next (from {HERE}):\n  {shown}'); return 0
    print(f'▶ {shown}', flush=True)                                   # before run_api.sh's own output
    return subprocess.call(cmd, cwd=HERE, env={**os.environ, **{k: v for k, v in env.items() if v}})

def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('export', 'import'): die(__doc__)
    sys.exit(export(a[1:]) or 0 if a[0] == 'export' else bring_back(a[1:]))

if __name__ == '__main__': main()
