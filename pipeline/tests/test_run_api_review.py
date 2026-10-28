"""test_run_api_review.py: applying a reviewed work order (REVIEW=1, then run_api.sh again) never re-runs intake.

    python -m pytest tests/test_run_api_review.py -q

A synthetic run folder in the state a REVIEW=1 stop leaves (workorder.ai.json, review.json, _intake/), with the audit
already made (so run_api.sh reuses it): run_api.sh must apply to the saved intake result without running intake.py,
and must refuse an original whose sha256 is not the one the intake was made from. No model, veraPDF off; the apply
step itself is not reached in a meaningful way (no workorder.json), only the intake step is tested.
"""
import os, sys, json, shutil, hashlib, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
INTAKE_PDF = os.path.join(HERE, 'tests', 'baseline', 'ilokano', '_intake', 'intake.pdf')

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def reviewed_run(tmp_path):
    src = tmp_path / 'book.pdf'; src.write_bytes(b'%PDF-1.4 the original, untagged\n')
    R = tmp_path / 'run'; (R / '_intake').mkdir(parents=True); (R / '_audit').mkdir()
    shutil.copy(INTAKE_PDF, R / '_intake' / 'intake.pdf')
    (R / '_intake' / 'intake.json').write_text(json.dumps({'status': 'done', 'original': {'file': 'book.pdf', 'sha256': sha(src)},
                                                           'result': {'pdf': 'intake.pdf'}}))
    (R / '_audit' / 'digest.json').write_text(json.dumps({'source': {'sha256': sha(INTAKE_PDF)}}))   # the audit is reused
    (R / '_audit' / 'verapdf.json').write_text('{}')
    (R / 'workorder.ai.json').write_text('{}'); (R / 'review.json').write_text(json.dumps({'reviewer': 'Pat'}))
    return src, R

def run_api(src, R):
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(R), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    env.pop('INTAKE_REUSE', None); env.pop('INTAKE', None)
    return subprocess.run(['bash', 'run_api.sh', str(src), 'book', 'rv'], cwd=HERE, env=env, capture_output=True, text=True, timeout=300)

def test_applying_a_reviewed_order_does_not_rerun_intake(tmp_path):
    src, R = reviewed_run(tmp_path)
    before = {f: sha(R / '_intake' / f) for f in ('intake.json', 'intake.pdf')}
    r = run_api(src, R)
    assert 'intake: not re-run' in r.stdout, r.stdout + r.stderr
    assert '0/5 intake (local, no model)' not in r.stdout                           # intake.py was not started
    assert {f: sha(R / '_intake' / f) for f in ('intake.json', 'intake.pdf')} == before

def test_a_different_original_is_refused_before_anything_runs(tmp_path):
    src, R = reviewed_run(tmp_path)
    other = tmp_path / 'other.pdf'; other.write_bytes(b'%PDF-1.4 another book\n')
    before = sha(R / '_intake' / 'intake.json')
    r = run_api(other, R)
    assert r.returncode != 0 and 'is not the original this run' in r.stdout
    assert sha(R / '_intake' / 'intake.json') == before
