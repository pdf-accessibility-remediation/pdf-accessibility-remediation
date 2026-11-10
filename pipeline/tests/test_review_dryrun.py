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

# ------------------------------------------------------------------ #93 Part 2: the run's own apply, kept for the first Review Again
# A run that applied the AI's own order with the figure step on has, in its apply log, exactly what the trial run would
# find (the same apply.py on the same PDF and order): report.py keeps it, under the key run_api.sh worked out before the
# apply, and the first "Review Again" reuses it through the check above, unchanged.
import subprocess  # noqa: E402

OUT = 'book_remediated.pdf'

def applied(R, src, **change):
    """A run's own apply as run_api.sh makes it (no review stop, so no workorder.ai.json): the key before the apply, apply.py
    on the AI's order, the record report.py writes (workorder: the order applied), the timing."""
    ai = core.load(str(R / 'workorder.ai.json')); os.remove(R / 'workorder.ai.json')
    wo = dict(ai, **change)
    core.save(str(R / 'workorder.json'), wo)
    core.save_key(str(src), str(R / 'workorder.json'), str(R / '_audit' / 'dryrun.key.json'))
    code, log = core.run_apply(str(src), wo, str(R / OUT))
    assert code == 0 and log is not None
    core.save(str(R / 'record.json'), {'workorder': wo, 'document': {'file': 'book.pdf', 'output': OUT}})
    core.save(str(R / 'timing.json'), {'4/5 apply (no model)': 2.5, '4/5 verify (no model)': 1.0})
    return wo

def reopen(R, src):
    """What Review Again does before the page opens: the AI's order from the record into reviews/, then prepare (the trial
    run, or its reuse)."""
    shutil.copyfile(R / 'workorder.json', R / 'reviews' / 'workorder.ai.json')
    return core.prepare(str(R / 'reviews'), str(src))

def no_seconds(d): return {k: v for k, v in d.items() if k != 'seconds'}

def test_a_runs_own_apply_is_kept_and_the_first_review_again_reuses_it(book, monkeypatch):
    R, src, calls = book
    wo = applied(R, src)
    n = len(calls)
    line = core.keep_trial(str(R), str(R / '_audit'), OUT, str(src))
    assert line.startswith('figure moves and section moves kept for a later review (1 figure move, 0 section moves)'), line
    kept = core.load(str(R / '_audit' / 'dryrun.json'))
    assert list(kept) == ['figure_moves', 'seconds', 'section_moves', 'section_move', 'key', 'made'] and kept['seconds'] == 2.5
    assert kept['key'] == core.dryrun_key(str(src), core.trial_order(wo))
    S.keep_audit(str(R), str(R / '_audit'), wo, inp=str(src))
    first = reopen(R, src)
    assert len(calls) == n                                                             # no trial run
    monkeypatch.setenv('REVIEW_DRYRUN', 'fresh')
    fresh = reopen(R, src)
    assert len(calls) == n + 1
    assert no_seconds(first['reading_order']['dryrun']) == no_seconds(fresh['reading_order']['dryrun'])
    assert first['items'] == fresh['items']                                            # the same move cards

@pytest.mark.parametrize('case', ['figure_step_off', 'figure_order_off_in_log', 'review_json', 'review_session', 'from_record', 'key_changed',
                                  'no_key_file', 'no_log', 'order_not_the_records', 'not_its_own_audit'])
def test_a_trial_run_is_never_kept_when_it_could_differ(book, case, monkeypatch, tmp_path):
    """§3.3: the AI turning the figure step off (the key leaves that out on purpose, so only this refusal catches it), a
    reviewed run or a re-apply (their apply used another order, and a kept file is never overwritten), anything the key
    covers changed during the run, no key or no apply log, a record whose order Review Again would rebuild differently,
    and an audit folder other than the run's own (review 02 M3)."""
    R, src, calls = book
    applied(R, src, **({'fix_figure_order': False} if case == 'figure_step_off' else {}))
    A, kw = R / '_audit', {}
    if case == 'figure_order_off_in_log':
        lp = R / (OUT + '.log.json'); log = core.load(str(lp)); log['figure_order_off'] = True; core.save(str(lp), log)
    elif case == 'review_json': core.save(str(R / 'review.json'), {'reviewer': 'Kim'})
    elif case == 'review_session': core.save(str(R / 'review_session.json'), {'session': '002'})
    elif case == 'from_record': kw['from_record'] = True
    elif case == 'key_changed': monkeypatch.setenv('ALLOW_PDF20', '1')
    elif case == 'no_key_file': os.remove(A / 'dryrun.key.json')
    elif case == 'no_log': os.remove(R / (OUT + '.log.json'))
    elif case == 'order_not_the_records':
        rec = core.load(str(R / 'record.json')); rec['workorder'] = dict(rec['workorder'], alt=[]); core.save(str(R / 'record.json'), rec)
    elif case == 'not_its_own_audit':
        A = R / 'reviews' / '_audit'; A.mkdir(parents=True); shutil.copy(R / '_audit' / 'dryrun.key.json', A / 'dryrun.key.json')
    line = core.keep_trial(str(R), str(A), OUT, str(src), **kw)
    assert line.startswith('figure moves and section moves not kept for a later review: '), (case, line)
    assert not line.startswith(('refused: ', 'done: '))                               # never read as the job's outcome (logs.py)
    assert not (A / 'dryrun.json').exists() and not (R / '_audit' / 'dryrun.json').exists(), case

def test_one_builder_makes_the_result_and_its_source_is_in_the_key(book, monkeypatch):
    """Review 02 M2: dry_run and keep_trial build the saved result with trial_result(); its source and trial_order()'s are
    hashed with dry_run's, so changing either invalidates every saved result."""
    R, src, _ = book
    wo = core.trial_order(core.load(str(R / 'workorder.ai.json')))
    k0 = core.dryrun_key(str(src), wo)['code_sha256']
    for name in ('trial_result', 'trial_order'):
        real = getattr(core, name)
        monkeypatch.setattr(core, name, lambda *a, **k: real(*a, **k))
        assert core.dryrun_key(str(src), wo)['code_sha256'] != k0, name
        monkeypatch.setattr(core, name, real)
    assert core.dryrun_key(str(src), wo)['code_sha256'] == k0
    assert core.trial_order({'a': 1, 'fix_figure_order': False}) == {'a': 1} and core.trial_order({'fix_figure_order': True}) == {'fix_figure_order': True}

def pipeline_env(**kw):
    e = dict(os.environ, VERAPDF='off', OPENROUTER_API_KEY='test-not-a-key', HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9',
             PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    for k in ('INTAKE_REUSE', 'INTAKE', 'REPLY', 'REVIEW', 'KEEP', 'REVIEW_DRYRUN', 'AUTO', 'ESTIMATE', 'MAX_USD') + core.DRYRUN_ENV: e.pop(k, None)
    e.update({k: str(v) for k, v in kw.items()}); return e

def test_a_whole_run_keeps_its_apply_and_a_re_apply_never_touches_it(tmp_path, monkeypatch):
    """run_api.sh end to end on a saved reply (no model): the key before the apply, the result kept in reviews/_audit; the
    first Review Again opens without a trial run; then a re-apply of that review (report.py with reviews/_audit as its
    audit folder, review 02 M3) leaves the kept file byte for byte as it was."""
    monkeypatch.setenv('VERAPDF', 'off'); monkeypatch.delenv('REVIEW_DRYRUN', raising=False)
    for k in core.DRYRUN_ENV: monkeypatch.delenv(k, raising=False)
    src = figure_pdf(tmp_path / 'book.pdf'); R = tmp_path / 'run'
    reply = tmp_path / 'reply.txt'; reply.write_text('```json\n' + json.dumps({'schema': 'workorder/0.2', 'alt': [{'obj': '16 0', 'alt': 'A blue box'}]}) + '\n```\n')
    r = subprocess.run(['bash', 'run_api.sh', str(src), 'book', 'x'], cwd=PIPE, env=pipeline_env(RUN_DIR=R, INTAKE='off', REPLY=reply),
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'figure moves and section moves kept for a later review (1 figure move, 0 section moves)' in r.stdout, r.stdout[-3000:]
    kept = R / 'reviews' / '_audit' / 'dryrun.json'
    assert kept.is_file() and not (R / '_audit').exists() and 'Traceback' not in r.stdout + r.stderr
    before = kept.read_bytes()
    # Review Again in its own process, with the interpreter run_api.sh used (python3 on the same PATH, as the app and the
    # terminal run both): the key holds its path, so `python -m pytest`'s own `python` would make one trial run (safe, slower)
    py = shutil.which('python3', path=pipeline_env()['PATH'])
    r = subprocess.run([py, '-c', 'import sys; from review import core, sessions as S; S.open_session(sys.argv[1], core.load(sys.argv[1] + "/record.json"))', str(R)],
                       cwd=PIPE, env=pipeline_env(), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and 'is reused (nothing it depends on has changed)' in r.stdout, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'a trial run of apply.py on a copy' not in r.stdout and kept.read_bytes() == before   # reused as it is
    rec = core.load(str(R / 'record.json')); s = S.sessions(str(R))[-1]
    p = S.P(str(R)); items = core.load(p['items'])['items']; ai = core.load(p['ai'])
    S.save(p['draft'], {'reviewer': 'Kim', 'decisions': {}, 'additions': []})
    wo = core.apply_decisions(ai, items, {}); S.save(os.path.join(p['dir'], 'workorder.json'), wo)
    S.save(os.path.join(p['dir'], 'review.json'), {'reviewer': 'Kim', 'date': '2026-11-10', 'method': 'page', 'changes': core.diff(ai, wo)})
    S.finish_session(str(R), s, rec)
    r = subprocess.run([sys.executable, 'review_workorder.py', str(R), '--apply'], cwd=PIPE, env=pipeline_env(), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'figure moves and section moves kept for a later review' not in r.stdout and kept.read_bytes() == before

@pytest.mark.parametrize('before_page', [3, 99])
def test_a_kept_section_move_is_the_trial_runs(tmp_path, monkeypatch, before_page):
    """Section moves too, made or refused with the reason (no saved reply on today's code has a section move the work-order
    check keeps, so the synthetic four-page book stands in): the kept result equals a fresh trial run's, key included."""
    from test_synthetic import sections_pdf
    monkeypatch.setenv('VERAPDF', 'off'); monkeypatch.delenv('REVIEW_DRYRUN', raising=False)
    for k in core.DRYRUN_ENV: monkeypatch.delenv(k, raising=False)
    src = sections_pdf(tmp_path / 'sections.pdf'); R = tmp_path / 'run'; R.mkdir()
    run('audit.py', src, R / '_audit')
    core.save(str(R / 'workorder.ai.json'), {'schema': 'workorder/0.1', 'move_section': {'pages': [2, 2], 'before_page': before_page}})
    applied(R, src)
    assert 'kept for a later review (0 figure moves, 1 section move)' in core.keep_trial(str(R), str(R / '_audit'), OUT, str(src))
    kept = core.load(str(R / '_audit' / 'dryrun.json'))
    assert ('made' if before_page == 3 else 'refused') in kept['section_move']
    F = R / 'fresh'; (F / '_audit').mkdir(parents=True); shutil.copyfile(R / 'workorder.json', F / 'workorder.ai.json')
    monkeypatch.setenv('REVIEW_DRYRUN', 'fresh')
    fresh = core.dry_run(str(F), str(src))
    strip = lambda d: {k: v for k, v in d.items() if k not in ('seconds', 'made')}
    assert strip(kept) == strip(fresh)
