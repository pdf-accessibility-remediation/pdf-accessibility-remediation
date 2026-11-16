"""test_handedit_trial.py: #93 Part 2's kept trial run (review/core.py keep_trial) on runs of a PDF edited by hand (#62).

    python -m pytest tests/test_handedit_trial.py -q

The whole loop at no cost (run_api.sh, handedit.py import, report.py; DECIDE=none, veraPDF off), on test_handedit.py's
two-figure book. A hand-edited run either keeps its apply and the first "Review Again" reuses it, giving exactly what a
fresh trial run gives, or keeps nothing and says why. A kept result is never used for another PDF: the edited file as
the person saved it is not the pipeline's input (_handedit/input.pdf, its copy with the stale alt text removed), so a
trial run on it is made anew. "Review Again" runs through the venv's python3, as the app and the terminal start it (the
key holds the interpreter's path: test_review_dryrun.py).
"""
import os, sys, json, shutil, hashlib, subprocess
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_handedit import figures_pdf, swap_image  # noqa: E402
from test_review_dryrun import pipeline_env  # noqa: E402
from review import core  # noqa: E402

KEPT = 'figure moves and section moves kept for a later review ('
NOT_KEPT = 'figure moves and section moves not kept for a later review: '
REUSED = 'is reused (nothing it depends on has changed)'
TRIAL = 'a trial run of apply.py on a copy'

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def sh(args, **kw):
    r = subprocess.run(args, cwd=PIPE, env=pipeline_env(**kw), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'Traceback' not in r.stdout + r.stderr, r.stdout[-3000:] + r.stderr[-2000:]
    return r.stdout

PY3 = lambda: shutil.which('python3', path=pipeline_env()['PATH'])

def review_again(R, **kw):
    """The first "Review Again" from the AI's decisions (sessions.open_session, as review_workorder.py --reopen does), in
    its own python3 process: (its output, the trial-run result the page shows)."""
    code = ('import sys, json; from review import core, sessions as S; R = sys.argv[1]; '
            'S.open_session(R, core.load(R + "/record.json"), src="ai", discard_open=True); '
            'print("DRYRUN=" + json.dumps(core.load(R + "/reviews/review_items.json")["reading_order"]["dryrun"]))')
    out = sh([PY3(), '-c', code, str(R)], **kw)
    return out, json.loads(out.split('DRYRUN=', 1)[1].strip())

def no_seconds(d): return {k: v for k, v in d.items() if k != 'seconds'}

def parent_and_edit(tmp_path):
    """A finished run of the book (no AI call, applied without review), and an edited copy of its result."""
    src = figures_pdf(tmp_path / 'book.pdf')
    out = sh(['bash', 'run_api.sh', src, 'book', 'parent'], RUNS_DIR=tmp_path / 'runs', DECIDE='none')
    assert KEPT in out                                                    # the parent itself: an unreviewed apply, kept
    P = tmp_path / 'runs' / 'book' / 'parent'
    sh([sys.executable, 'handedit.py', 'export', str(P), '--to', str(tmp_path / 'copy.pdf'), '--by', 'Pat'])
    return P, swap_image(tmp_path / 'copy.pdf', tmp_path / 'edited.pdf')

def test_an_unreviewed_hand_edit_keeps_its_apply_and_reuses_it_only_for_its_own_input(tmp_path):
    """--to pipeline's shape (an apply with no review stop; DECIDE=none in place of the paid call): the apply on
    _handedit/input.pdf is kept, the first Review Again reuses it and shows what a fresh trial run shows, and the same
    kept result is not reused for the edited file as saved, nor for the parent's result."""
    P, edited = parent_and_edit(tmp_path)
    sh([sys.executable, 'handedit.py', 'import', str(P), edited, '--by', 'Pat', '--note', 'a better scan', '--label', 'he1',
        '--to', 'pipeline', '--no-run'])
    C = P.parent / 'he1'; he = core.load(str(C / '_handedit' / 'hand_edit.json'))
    copy = C / '_handedit' / he['edited']['file']; inp = C / '_handedit' / 'input.pdf'
    assert inp.is_file() and sha(inp) != sha(copy)                        # the stale alt text removed in a working copy
    rec_p = core.load(str(P / 'record.json'))
    out = sh(['bash', 'run_api.sh', str(copy), 'book', 'he1'], RUN_DIR=C, OUT=rec_p['document']['output'], DECIDE='none')
    assert KEPT in out, out[-3000:]
    rec = core.load(str(C / 'record.json'))
    assert rec['document']['pipeline_input']['file'] == '_handedit/input.pdf' and rec['hand_edit']['parent']['run'] == str(P)
    kept = core.load(str(C / 'reviews' / '_audit' / 'dryrun.json'))
    assert kept['key']['pdf_sha256'] == sha(inp)                          # keyed on the PDF the apply worked on
    before = (C / 'reviews' / '_audit' / 'dryrun.json').read_bytes()
    log, first = review_again(C)
    assert REUSED in log and TRIAL not in log, log[-3000:]
    assert (C / 'reviews' / '_audit' / 'dryrun.json').read_bytes() == before
    log, fresh = review_again(C, REVIEW_DRYRUN='fresh')
    assert TRIAL in log and no_seconds(first) == no_seconds(fresh)        # what the page shows is the trial run's
    # never for another PDF: the edited file as saved, and the parent's result, each get a trial run of their own
    for other in (copy, P / rec_p['document']['output']):
        F = tmp_path / ('trial-' + other.name); F.mkdir(); (F / '_audit').mkdir()
        shutil.copyfile(C / 'reviews' / '_audit' / 'dryrun.json', F / '_audit' / 'dryrun.json')
        shutil.copyfile(C / 'reviews' / 'workorder.ai.json', F / 'workorder.ai.json')
        r = sh([PY3(), '-c', 'import sys; from review import core; core.dry_run(sys.argv[1], sys.argv[2])', str(F), str(other)])
        assert TRIAL in r and REUSED not in r, (other, r)

def test_a_reviewed_hand_edit_keeps_nothing_and_says_why(tmp_path):
    """--to review (the app's way): no AI call, a review, then the apply. The applied order is the review's, so nothing is
    kept, and the line says why; the first Review Again shows what a fresh trial run shows."""
    P, edited = parent_and_edit(tmp_path)
    sh([sys.executable, 'handedit.py', 'import', str(P), edited, '--by', 'Pat', '--note', 'a better scan', '--label', 'he2'])
    C = P.parent / 'he2'
    assert (C / 'workorder.ai.json').is_file() and not (C / 'record.json').exists()   # stopped for its review
    digest = core.load(str(C / '_audit' / 'digest.json')); p = C / 'workorder.json'; wo = core.load(str(p))
    gap = next(g for g in core.gaps(wo, digest) if g['id'] == 'figures_without_alt')
    wo['alt'] = [{'obj': gap['objs'][0], 'alt': 'A green square'}]; core.save(str(p), wo)
    sh([sys.executable, 'review_workorder.py', str(C), '--reviewer', 'Pat', '--note', 'test file'])
    he = core.load(str(C / '_handedit' / 'hand_edit.json'))
    out = sh(['bash', 'run_api.sh', str(C / '_handedit' / he['edited']['file']), 'book', 'he2'], RUN_DIR=C,
             OUT=core.load(str(P / 'record.json'))['document']['output'])
    assert NOT_KEPT + 'the order applied was reviewed' in out, out[-3000:]
    assert not (C / '_audit' / 'dryrun.key.json').exists() and not (C / 'reviews' / '_audit' / 'dryrun.key.json').exists()
    log, first = review_again(C)
    log, fresh = review_again(C, REVIEW_DRYRUN='fresh')
    assert TRIAL in log and no_seconds(first) == no_seconds(fresh)
