"""test_run_dirs.py: a relative RUNS_DIR or RUN_DIR is taken from the folder the command runs in, as the PDF's path is,
and made absolute once (run_api.sh, batch_api.sh; #144). No AI call (DECIDE=none), veraPDF off.

    python -m pytest tests/test_run_dirs.py -q
"""
import os, sys, json, subprocess
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
    name = f'x-{tmp_path.name}'                                          # this test's own: no folder left by an older run can match
    r = sh(['bash', os.path.join(PIPE, 'run_api.sh'), 'book.pdf', 'book', 'r1'], str(tmp_path), RUN_DIR=f'sub/../{name}/', DECIDE='none')
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / name / 'record.json').exists() and f'done: {tmp_path / name}\n' in r.stdout
    assert not os.path.exists(os.path.join(PIPE, name))

def test_a_relative_reply_is_taken_from_where_the_command_runs(tmp_path):
    figures_pdf(tmp_path / 'book.pdf')
    wo = {'document': {'lang': 'en', 'title': 'Two figures'}}
    (tmp_path / 'reply.txt').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5', 'choices': [{'message': {'content': json.dumps(wo)}, 'finish_reason': 'stop'}],
                                                    'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}))
    r = sh(['bash', os.path.join(PIPE, 'run_api.sh'), 'book.pdf', 'book', 'r1'], str(tmp_path), REPLY='reply.txt', RUN_DIR='r',
           INTAKE='off', LANG_TAGS='off', PAGE_READS='off', OPENROUTER_API_KEY='test-not-a-key',
           HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9')   # no network
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert (tmp_path / 'r' / 'record.json').exists() and 'reuse saved reply (no cost)' in r.stdout

def test_a_batch_takes_a_relative_runs_dir_from_where_it_runs(tmp_path):
    r = sh(['bash', os.path.join(PIPE, 'batch_api.sh'), 'nob'], str(tmp_path), RUNS_DIR='runs', SUMMARY_ONLY='1')
    assert r.returncode == 1 and f'no batch nob in {tmp_path / "runs"}/batches' in r.stdout, r.stdout + r.stderr
