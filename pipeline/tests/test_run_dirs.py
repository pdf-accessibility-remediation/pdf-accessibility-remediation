"""test_run_dirs.py: a relative RUNS_DIR or RUN_DIR is taken from the folder the command runs in, as the PDF's path is,
and made absolute once (run_api.sh, batch_api.sh; #144). No AI call (DECIDE=none), veraPDF off.

    python -m pytest tests/test_run_dirs.py -q
"""
import os, sys, subprocess
from test_handedit import PIPE, env, figures_pdf

def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, env=env(**kw), capture_output=True, text=True, timeout=300)

def test_a_relative_runs_dir_is_taken_from_where_the_command_runs(tmp_path):
    figures_pdf(tmp_path / 'book.pdf')
    r = sh(['bash', os.path.join(PIPE, 'run_api.sh'), 'book.pdf', 'book', 'r1'], str(tmp_path), RUNS_DIR='runs', DECIDE='none')
    assert r.returncode == 0, r.stdout + r.stderr
    R = tmp_path / 'runs' / 'book' / 'r1'
    assert (R / 'record.json').exists() and f'done: {R}\n' in r.stdout

def test_a_relative_run_dir_with_dots_and_a_trailing_slash_is_one_absolute_folder(tmp_path):
    figures_pdf(tmp_path / 'book.pdf'); (tmp_path / 'sub').mkdir()
    r = sh(['bash', os.path.join(PIPE, 'run_api.sh'), 'book.pdf', 'book', 'r1'], str(tmp_path), RUN_DIR='sub/../x/', DECIDE='none')
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / 'x' / 'record.json').exists() and f'done: {tmp_path / "x"}\n' in r.stdout
    assert not os.path.exists(os.path.join(PIPE, 'x'))

def test_a_batch_takes_a_relative_runs_dir_from_where_it_runs(tmp_path):
    r = sh(['bash', os.path.join(PIPE, 'batch_api.sh'), 'nob'], str(tmp_path), RUNS_DIR='runs', SUMMARY_ONLY='1')
    assert r.returncode == 1 and f'no batch nob in {tmp_path / "runs"}/batches' in r.stdout, r.stdout + r.stderr
