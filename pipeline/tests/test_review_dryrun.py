"""test_review_dryrun.py: the review stop's trial run of apply.py is reused while nothing it depends on has changed (#52).

    python -m pytest tests/test_review_dryrun.py -q

On test_synthetic.py's three-page figure PDF, with the real apply.py (counted through core.run_apply): the same inputs a
second time reuse the saved result and give the same review items; a changed work order, PDF, code, or variable apply.py
reads runs it again, while the AI turning the figure step off does not (the trial run has it on either way); a failed
trial run, an older dryrun.json without a key, and REVIEW_DRYRUN=fresh are never reused; the copy report.py keeps in
reviews/_audit is reused by Review Again; and every variable apply.py or lib/ reads is part of the key. No model; veraPDF is off.
"""
import os, re, sys, json, shutil, hashlib
import pytest

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_synthetic import figure_pdf, run  # noqa: E402
from review import core, sessions as S  # noqa: E402

@pytest.fixture
def book(tmp_path, monkeypatch):
    """A run folder at the review stop (audit + the AI's order), and a counter of the real apply.py runs."""
    monkeypatch.setenv('VERAPDF', 'off'); monkeypatch.delenv('REVIEW_DRYRUN', raising=False)
    for k in core.DRYRUN_ENV: monkeypatch.delenv(k, raising=False)
    src = figure_pdf(tmp_path / 'book.pdf')
    R = tmp_path / 'run'; R.mkdir()
    run('audit.py', src, R / '_audit')
    sha = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    core.save(str(R / 'workorder.ai.json'), {'schema': 'workorder/0.1', 'source': {'sha256': sha}, 'alt': [{'obj': '16 0', 'alt': 'A blue box'}]})
    calls = []
    real = core.run_apply
    def counted(*a, **k):
        calls.append(a[0]); return real(*a, **k)
    monkeypatch.setattr(core, 'run_apply', counted)
    return R, src, calls

def prepare(R, src):
    return core.prepare(str(R), str(src))

def set_ai(R, **kv):
    ai = core.load(str(R / 'workorder.ai.json')); ai.update(kv); core.save(str(R / 'workorder.ai.json'), ai)

def test_same_inputs_reuse_the_trial_run_and_the_page_is_the_same(book):
    R, src, calls = book
    first = prepare(R, src)
    assert len(calls) == 1 and first['reading_order']['dryrun']['figure_moves']        # the figure read last is moved back
    saved = core.load(str(R / '_audit' / 'dryrun.json'))
    assert saved['key']['pdf_sha256'] == hashlib.sha256(open(src, 'rb').read()).hexdigest() and saved['made']
    second = prepare(R, src)
    assert len(calls) == 1                                                             # not run again
    assert second == first                                                             # the page gets exactly the same
    assert 'key' not in second['reading_order']['dryrun'] and 'made' not in second['reading_order']['dryrun']

@pytest.mark.parametrize('change', ['workorder', 'pdf', 'code', 'env'])
def test_a_changed_input_runs_it_again(book, change, monkeypatch, tmp_path):
    R, src, calls = book
    prepare(R, src)
    if change == 'workorder': set_ai(R, alt=[{'obj': '16 0', 'alt': 'A blue square'}])
    elif change == 'pdf':
        with open(src, 'ab') as f: f.write(b'\n% one more byte\n')                    # a trailing comment: still a readable PDF
    elif change == 'code':
        extra = tmp_path / 'extra.py'; extra.write_text('# one helper\n')
        files = core.dryrun_code() + [str(extra)]
        monkeypatch.setattr(core, 'dryrun_code', lambda: files)
        extra.write_text('# one helper, changed\n')
    elif change == 'env': monkeypatch.setenv('ALLOW_PDF20', '1')
    prepare(R, src)
    assert len(calls) == 2, change

def test_the_ai_turning_the_figure_step_off_alone_reuses_it(book):
    """The trial run always has the figure step on (the card shows what turning it on or off changes)."""
    R, src, calls = book
    prepare(R, src)
    set_ai(R, fix_figure_order=False)
    assert prepare(R, src)['reading_order']['dryrun']['figure_moves'] and len(calls) == 1

def test_a_failed_trial_run_is_never_reused(book, monkeypatch):
    R, src, calls = book
    real = core.run_apply
    monkeypatch.setattr(core, 'run_apply', lambda *a, **k: (calls.append(a[0]), (1, None))[1])
    assert prepare(R, src)['reading_order']['dryrun']['figure_moves'] is None
    assert 'key' not in core.load(str(R / '_audit' / 'dryrun.json'))
    monkeypatch.setattr(core, 'run_apply', real)
    assert prepare(R, src)['reading_order']['dryrun']['figure_moves'] and len(calls) == 2   # tried again, and it worked

def test_an_older_result_without_a_key_and_fresh_run_it_again(book, monkeypatch):
    R, src, calls = book
    prepare(R, src)
    old = core.load(str(R / '_audit' / 'dryrun.json')); old.pop('key'); core.save(str(R / '_audit' / 'dryrun.json'), old)
    prepare(R, src); assert len(calls) == 2                                            # a run prepared before #52
    prepare(R, src); assert len(calls) == 2                                            # its new result has a key
    monkeypatch.setenv('REVIEW_DRYRUN', 'fresh')
    prepare(R, src); assert len(calls) == 3
    monkeypatch.delenv('REVIEW_DRYRUN')
    (R / '_audit' / 'dryrun.json').write_text('{"figure_moves": [')                    # cut short
    prepare(R, src); assert len(calls) == 4

def test_review_again_reuses_the_copy_report_keeps(book):
    """report.py's tidy copies dryrun.json into reviews/_audit; a reopen prepares reviews/ with the same input."""
    R, src, calls = book
    prepare(R, src)
    S.keep_audit(str(R), str(R / '_audit'), core.load(str(R / 'workorder.ai.json')), inp=str(src))
    shutil.copyfile(R / 'workorder.ai.json', R / 'reviews' / 'workorder.ai.json')
    core.prepare(str(R / 'reviews'), str(src))
    assert len(calls) == 1

def test_every_variable_apply_reads_is_in_the_key():
    """A variable apply.py or lib/ reads changes what the trial run does, so it must be in DRYRUN_ENV."""
    names = set()
    for f in core.dryrun_code():
        names |= set(re.findall(r'''(?:environ\.get|environ\[|getenv)\(?\s*['"]([A-Z0-9_]+)['"]''', open(f, encoding='utf-8').read()))
    assert names and names <= set(core.DRYRUN_ENV), sorted(names - set(core.DRYRUN_ENV))
