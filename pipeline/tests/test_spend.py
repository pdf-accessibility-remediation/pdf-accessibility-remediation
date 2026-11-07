"""test_spend.py: the cost estimate interface (lib/costs.py), the one spend gate (webapp/spend.py), the paid-path rule and
the needs-spend way out (webapp/jobs.py), New Run's names and "Try Again" (webapp/newrun.py). #45, 03 §1–§7. No model:
every run.json here is synthetic, and no job here may send.

    python -m pytest tests/test_spend.py -q
"""
import os, sys, json, time, hashlib, subprocess
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from lib import costs  # noqa: E402
from webapp import config, jobs, spend as SP, newrun as NR, runs as RN  # noqa: E402
from test_webapp import setup, settings, fake, wait  # noqa: E402,F401

MODEL, PROMPT = SP.current_model_and_prompt()

def run_folder(t, name='bk', label='l1', worst=0.6200, credit=14.3, model=MODEL, prompt=PROMPT, passes=None, price='openrouter /models', **e):
    R = t / 'runs' / name / label; (R / '_audit').mkdir(parents=True, exist_ok=True)
    (R / '_audit' / 'digest.json').write_text('{"source": {}}'); (R / 'request.json').write_text('{"r": 1}')
    est = {'input_tokens': 20000, 'images': 12, 'image_tokens': 9000, 'input_usd': 0.06, 'worst_case_output_usd': 0.56,
           'worst_case_total_usd': worst, 'cap_usd': 2.0, 'max_tokens': 48000, 'approximate': False, **e}
    if credit is not None: est['credit_available_usd'] = credit
    if passes: est['passes'] = passes
    (R / 'run.json').write_text(json.dumps({'model': model, 'prompt_sha256': prompt, 'price_source': price, 'estimate': est,
                                            'ocr_words': {'sheets': 4}}))
    return R

# ------------------------------------------------------------------ lib/costs.py
@pytest.mark.parametrize('x,want', [(0.62, 0.63), (0.6200, 0.63), (0.61991, 0.63), (0.6198, 0.62), (1.2, 1.21), (0.0, 0.01)])
def test_round_up_from_the_stored_value(x, want):
    assert costs.round_up(x) == want

def test_bound_never_above_the_limit():
    assert costs.bound(0.62, 2.0) == 0.63 and costs.bound(1.999, 2.0) == 2.0 and costs.bound(5.0, 2.0) == 2.0

def test_estimate_main_shape(setup):
    R = run_folder(setup)
    e = costs.estimate(str(R))
    assert e['schema'] == 'cost-estimate/1' and e['ceiling_usd'] == 0.62 and e['per_call_ceiling_usd'] == 0.62 and e['images'] == 12 and e['sheets'] == 4
    assert e['blocked'] is None and e['fits'] == {'per_call': True, 'per_book': True, 'credit': True} and e['expected'] is None
    assert e['bounds'] == {'MAX_USD': 0.63, 'BOOK_MAX_USD': None} and e['limits']['per_book_usd'] is None
    fp = e['fingerprint']
    (R / 'request.json').write_text('{"r": 2}')
    assert costs.estimate(str(R))['fingerprint'] != fp                     # the request is covered
    R2 = run_folder(setup, label='l2', credit=99.0)                         # the credit is not
    assert costs.estimate(str(R2))['fingerprint'] == fp

def test_estimate_of_63s_shape(setup):
    """#63 (alt text past 100 images): passes, a book cap and money spent before in this folder."""
    R = run_folder(setup, worst=1.9, passes=[{'pass': '1', 'worst_case_usd': 0.8}, {'pass': '2', 'worst_case_usd': 1.1}], book_cap_usd=5.0, spent_before_usd=0.3)
    e = costs.estimate(str(R))
    assert e['per_call_ceiling_usd'] == 1.1 and e['requests'] == 2 and e['spent_before_usd'] == 0.3
    assert e['bounds'] == {'MAX_USD': 1.11, 'BOOK_MAX_USD': 2.21} and e['limits']['per_book_usd'] == 5.0

@pytest.mark.parametrize('kw,code', [({'worst': 2.5}, 'per_call'), ({'credit': 0.1}, 'credit'), ({'credit': None}, 'no_credit'),
                                     ({'model': 'openai/gpt-5'}, 'model'), ({'price': 'ASSUMED $3 / $15 per million tokens (offline)'}, 'offline')])
def test_estimate_blocked(setup, kw, code):
    assert costs.estimate(str(run_folder(setup, **kw)))['blocked']['code'] == code

def test_expected_is_shown_when_present(setup, monkeypatch):
    """The #65 (dollar-only cost limits) hook: one function fills `expected`; the pages read it as it is."""
    monkeypatch.setattr(costs, '_expected', lambda x: {'usd': 0.25, 'low': 0.18, 'high': 0.36, 'basis': 'test'})
    assert costs.estimate(str(run_folder(setup)))['expected']['usd'] == 0.25
    js = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "'About ' + usd(x.usd)" in js and "' (usually ' + usd(x.low) + '–' + usd(x.high) + ')'" in js and "'Worst-case estimate ' + usd(e.ceiling_usd)" in js

def test_ocr_draft_is_named_not_built(setup):
    with pytest.raises(costs.NotBuilt): costs.estimate(str(run_folder(setup)), 'ocr-draft')

def test_batch_sums(setup):
    a, b = run_folder(setup, label='a', worst=0.5), run_folder(setup, label='b', worst=0.7, credit=1.0)
    c = setup / 'runs' / 'bk' / 'c'; c.mkdir(); (c / 'workorder.json').write_text('{}'); (c / 'response.json').write_text('{}')
    t = costs.batch([str(a), str(b), str(c)])
    assert t['ceiling_usd'] == 1.2 and t['credit_usd'] == 1.0 and t['fits'] == {'batch': True, 'credit': False}
    assert t['bounds'] == {'MAX_USD': 0.71, 'BATCH_MAX_USD': 1.21} and t['books'][2]['adds_usd'] == 0.0

# ------------------------------------------------------------------ the paid-path rule (03 §2)
def test_auto_only_in_a_paid_spend_or_batch(setup):
    s = settings(setup); J = s['jobs']
    env = config.child_env(s, {'AUTO': '1'})
    for kind in ('estimate', 'rerun', 'apply', 'replay', 'review'):
        with pytest.raises(ValueError): jobs.create(J, kind, 'a/r', ['true'], env, env_set={'AUTO': '1'})
    with pytest.raises(ValueError): jobs.create(J, 'spend', 'a/r', ['true'], env, env_set={'AUTO': '1'}, paid=True)                  # no fingerprint
    with pytest.raises(ValueError): jobs.create(J, 'spend', 'a/r', ['true'], env, env_set={'AUTO': '1'}, fingerprint='f')
    with pytest.raises(ValueError): jobs.create(J, 'apply', 'a/r', ['true'], config.child_env(s), paid=True)
    j = jobs.create(J, 'spend', 'a/r', ['true'], env, env_set={'AUTO': '1'}, paid=True, fingerprint='f')
    assert j['paid'] and j['env_set'] == {'AUTO': '1'}

def test_a_paid_job_is_never_a_then(setup):
    s = settings(setup); J = s['jobs']
    for then in ({'kind': 'spend', 'argv': ['true'], 'env': config.child_env(s), 'paid': True},
                 {'kind': 'rerun', 'argv': ['true'], 'env': config.child_env(s, {'AUTO': '1'}), 'env_set': {'AUTO': '1'}},
                 {'kind': 'pin', 'argv': ['true'], 'env': config.child_env(s), 'then': {'kind': 'spend', 'argv': ['true'], 'env': {}, 'paid': True}}):
        with pytest.raises(ValueError): jobs.create(J, 'apply', 'a/r', ['true'], config.child_env(s), then=then)
    # an older job file whose then asks for a paid job: tick() never queues it
    j = fake(setup, s, 'b/r', 0.05)
    raw = json.load(open(jobs.path(J, j['id']))); raw['then'] = {'kind': 'spend', 'argv': ['true'], 'env': {'AUTO': '1'}, 'paid': True}
    json.dump(raw, open(jobs.path(J, j['id']), 'w'))
    assert wait(lambda: (jobs.tick(J, s), jobs.load(J, j['id']).get('then_job'))[1])
    assert jobs.load(J, j['id'])['then_job'] == 'refused' and not [x for x in jobs.all_jobs(J) if x['kind'] == 'spend']

def test_every_route_job_keeps_the_rule():
    """The app's own job makers: only spend.py's (spend, batch) put AUTO in a job, and each passes paid and the tick."""
    for f in ('runs.py', 'newrun.py', 'batches.py'):
        p = os.path.join(HERE, 'webapp', f)
        if os.path.exists(p): assert "'AUTO'" not in open(p, encoding='utf-8').read(), f
    sp = open(os.path.join(HERE, 'webapp', 'spend.py'), encoding='utf-8').read()
    assert sp.count("'AUTO': '1'") == 3 and 'personal' not in sp           # the tick was removed (Patrick, 2026-11-06)

# ------------------------------------------------------------------ needs-spend has a way out (03 §1)
def test_restart_needs_spend_then_a_new_estimate_then_spend(setup):
    s = settings(setup); J = s['jobs']; R = setup / 'runs' / 'a' / 'r'; R.mkdir(parents=True)
    paid = fake(setup, s, 'a/r', kind='spend', paid=True)
    jobs.recover(J)
    assert jobs.load(J, paid['id'])['status'] == 'needs-spend'
    with pytest.raises(ValueError): fake(setup, s, 'a/r', R=str(R))            # blocked while it waits
    est = jobs.create(J, 'estimate', 'a/r', ['true'], config.child_env(s), R=str(R), supersede_waiting=True)
    old = jobs.load(J, paid['id'])
    assert old['status'] == 'superseded' and est['id'] in old['note'] and jobs.busy(J, 'a/r', str(R))   # the estimate itself is active
    jobs.update(J, est['id'], status='done')
    j = jobs.create(J, 'spend', 'a/r', ['true'], config.child_env(s), R=str(R), paid=True, fingerprint='f')
    assert j['status'] == 'queued'

def test_dismiss(setup):
    s = settings(setup); J = s['jobs']
    paid = fake(setup, s, 'a/r', kind='spend', paid=True); jobs.recover(J)
    assert jobs.dismiss(J, 'a/r') == 1 and jobs.load(J, paid['id'])['status'] == 'superseded' and jobs.busy(J, 'a/r', str(setup)) is None

# ------------------------------------------------------------------ batches: related runs and slots (02 M4)
@pytest.mark.parametrize('a,b,want', [('batches/x', 'batches/x/bikol', True), ('batches/x/bikol', 'batches/x', True), ('batches/x', 'batches/x2', False),
                                      ('batches/x/a', 'batches/x/b', False), ('a/r', 'a/r', True), ('a/r', 'a/r2', False)])
def test_related(a, b, want):
    assert jobs.related(a, b) is want

def test_busy_by_prefix_both_ways(setup):
    s = settings(setup); J = s['jobs']
    fake(setup, s, 'batches/x/bikol', 5)
    assert jobs.busy(J, 'batches/x', str(setup)) and not jobs.busy(J, 'batches/x2', str(setup))
    with pytest.raises(ValueError): jobs.create(J, 'batch', 'batches/x', ['true'], config.child_env(s), R=str(setup), paid=True, fingerprint='f')

def test_one_run_at_a_time_a_batch_is_one_place_and_a_new_run_waits(setup):
    """Patrick, 2026-11-06: max_jobs 1; a batch takes one place whatever its JOBS (batch_jobs 10); a New Run's estimate
    queued behind it says what it waits for, by its plain name, and starts when the batch ends; nothing starves."""
    from webapp import names as NM
    s = settings(setup, max_jobs=1, batch_jobs=10, test_batch_from='v8-p7a'); J = s['jobs']
    b = jobs.create(J, 'batch', 'batches/x', [sys.executable, '-c', 'import time; time.sleep(1.5)'], config.child_env(s, {'JOBS': '10'}),
                    env_set={'JOBS': '10'}, paid=True, fingerprint='f')
    NM.set_run_name(s, 'x', 'Spring backlist', kind='batches')
    jobs.tick(J, s)
    assert jobs.load(J, b['id'])['status'] == 'running' and jobs.counts(jobs.load(J, b['id']), s['runs']) == 1
    e = fake(setup, s, 'bk/r1', 0.1, 'estimate', kind='estimate')
    late = fake(setup, s, 'bk/r2', 0.1, 'late', kind='estimate')
    jobs.tick(J, s)
    v = RN.job_view(s, jobs.load(J, e['id']))
    assert v['status'] == 'queued' and v['waiting_for'] == 'the batch "Spring backlist"'
    assert wait(lambda: (jobs.tick(J, s), jobs.load(J, e['id'])['status'] in ('running', 'done'))[1], 30)
    assert jobs.load(J, b['id'])['status'] == 'done'                       # it started only once the batch had ended
    assert wait(lambda: (jobs.tick(J, s), jobs.load(J, late['id'])['status'] == 'done')[1], 30)   # and the next after it

def test_a_batch_runs_ten_books_at_once_with_one_place(setup):
    s = settings(setup, max_jobs=1, batch_jobs=10)
    total = costs.batch([str(run_folder(setup, name='batches', label='b/a', worst=0.5))])
    a = SP.authorize_batch(s, 'b', '/x/books.txt', total, 'f')
    assert a['env_set']['JOBS'] == '10' and 'slots' not in a['extra']

# ------------------------------------------------------------------ child_env: MODEL and FROM (03 §5, L2)
def test_child_env_model_and_from(setup):
    s = settings(setup)
    assert config.child_env(s, {'MODEL': 'anthropic/claude-x'})['MODEL'] == 'anthropic/claude-x'
    with pytest.raises(ValueError): config.child_env(s, {'MODEL': 'openai/gpt-5'})
    with pytest.raises(ValueError): config.child_env(s, {'FROM': 'v8-p7a'})
    with pytest.raises(ValueError): config.child_env(s, {'FORCE_OCR': '1'})
    s2 = settings(setup, test_batch_from='v8-p7a')
    assert config.child_env(s2, {'FROM': 'v8-p7a'})['FROM'] == 'v8-p7a'

def test_test_batch_from_only_from_config(setup):
    b = setup / 'base'; b.mkdir()
    (b / 'settings.json').write_text(json.dumps({'host': '127.0.0.1', 'port': 8760, 'runs': str(setup / 'runs'), 'samples': str(setup / 'samples'),
                                                'uploads': 'u', 'jobs': 'j', 'max_jobs': 2, 'test_batch_from': 'x'}))
    with pytest.raises(config.Bad): config.load(None, base=str(b), environ={})

# ------------------------------------------------------------------ the spend gate (03 §5, §6)
def spend_setup(setup, **kw):
    s = settings(setup, **kw); J = s['jobs']
    src = setup / 'samples' / 'bk.pdf'; src.write_bytes(b'%PDF-1.4 book')
    R = run_folder(setup)
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    e = jobs.create(J, 'estimate', 'bk/l1', ['bash', 'run_api.sh', str(src), 'bk', 'l1'], config.child_env(s, {'ESTIMATE': '1', 'OCR_LANG': 'eng'}),
                    env_set={'ESTIMATE': '1', 'OCR_LANG': 'eng'}, R=str(R), book_sha=sha, review_first=True)
    jobs.update(J, e['id'], status='done')
    return s, R, costs.estimate(str(R), limits=costs.limits_of(s))

def test_spend_binds_the_estimate_shown(setup):
    s, R, est = spend_setup(setup)
    a = SP.authorize(s, 'workorder', 'bk/l1', str(R), est['fingerprint'])
    assert a['env_set'] == {'OCR_LANG': 'eng', 'REVIEW': '1', 'AUTO': '1', 'MAX_USD': '0.63', 'MODEL': MODEL}
    assert a['argv'][1:] == ['run_api.sh', str(setup / 'samples' / 'bk.pdf'), 'bk', 'l1'] and a['extra']['fingerprint'] == est['fingerprint']
    j = NR.start_spend(s, 'bk/l1', str(R), {'kind': 'workorder', 'fingerprint': est['fingerprint']})
    assert j['paid'] and j['kind'] == 'spend' and j['env']['MAX_USD'] == '0.63'

@pytest.mark.parametrize('change,words', [('fingerprint', 'changed since it was shown'), ('model', 'out of date'),
                                          ('prompt', 'out of date'), ('limit', 'limit of $0.50'), ('file', 'changed or is gone')])
def test_spend_refusals(setup, change, words):
    s, R, est = spend_setup(setup, **({'limits': {'per_call_usd': 0.5}} if change == 'limit' else {}))
    fp = est['fingerprint']
    if change == 'fingerprint': fp = 'x' * 64
    if change in ('model', 'prompt'):
        orig = SP.current_model_and_prompt
        SP.current_model_and_prompt = (lambda: ('anthropic/other', PROMPT)) if change == 'model' else (lambda: (MODEL, '0' * 16))
    if change == 'file': (setup / 'samples' / 'bk.pdf').write_bytes(b'%PDF-1.4 changed')
    try:
        with pytest.raises(SP.Refused) as e: SP.authorize(s, 'workorder', 'bk/l1', str(R), fp)
        assert words in str(e.value)
        assert not [j for j in jobs.all_jobs(s['jobs']) if j['kind'] == 'spend']         # nothing queued
    finally:
        if change in ('model', 'prompt'): SP.current_model_and_prompt = orig

def test_model_and_prompt_come_from_decides_source():
    src = open(os.path.join(HERE, 'decide.py'), encoding='utf-8').read()
    assert f"DEFAULT_MODEL = '{MODEL}'" in src and MODEL.startswith('anthropic/') and len(PROMPT) == 16
    assert "hashlib.sha256(prompt.encode()).hexdigest()[:16]" in src and "prompt = open(args.prompt, encoding='utf-8').read()" in src
    assert 'import decide' not in open(os.path.join(HERE, 'webapp', 'spend.py'), encoding='utf-8').read()

def test_test_mode_spend_is_a_saved_reply(setup):
    rd = setup / 'replies'; rd.mkdir()
    s, R, est = spend_setup(setup, test_reply_dir=str(rd))
    with pytest.raises(SP.Refused) as e: SP.authorize(s, 'workorder', 'bk/l1', str(R), est['fingerprint'])
    assert 'no saved test reply' in str(e.value)
    (rd / 'bk.txt').write_text('{}')
    a = SP.authorize(s, 'workorder', 'bk/l1', str(R), est['fingerprint'])
    assert 'AUTO' not in a['env_set'] and a['env_set']['REPLY'] == str(rd / 'bk.txt') and a['env_set']['INTAKE_REUSE'] == '1'
    R2 = run_folder(setup, label='l2', price='ASSUMED $3 / $15 per million tokens (offline)')       # offline prices: allowed in test mode only
    assert costs.estimate(str(R2))['blocked']['code'] == 'offline'

def test_run_api_carries_63s_max_usd_hunk():
    """L1: the whole run_api.sh hunk of e9afcba (#63, alt text past 100 images), byte for byte."""
    sh = open(os.path.join(HERE, 'run_api.sh'), encoding='utf-8').read()
    for line in ('# MAX_USD=3 bash run_api.sh …   the cap on one call\'s worst case, in dollars (default 2, set in decide.py; Claude models only)',
                 'if [[ -n ${MAX_USD:-} && ! $MAX_USD =~ ^[0-9]+([.][0-9]+)?$ ]]; then echo "MAX_USD must be a number of dollars: $MAX_USD"; exit 1; fi',
                 '[[ -z ${MAX_USD:-} ]] || MT+=(--max-usd "$MAX_USD")',
                 'echo "AUTO=1: sending without asking (decide.py still refuses a Claude estimate over the \\$${MAX_USD:-2} cap or your credit)"'):
        assert line in sh, line
    r = subprocess.run(['git', 'cat-file', '-e', 'e9afcba'], cwd=HERE, capture_output=True)
    if r.returncode == 0:
        theirs = subprocess.run(['git', 'diff', '-U0', 'e9afcba~1', 'e9afcba', '--', 'run_api.sh'], cwd=HERE, capture_output=True, text=True).stdout
        for l in theirs.splitlines():
            if l.startswith('+') and not l.startswith('+++'): assert l[1:] in sh

# ------------------------------------------------------------------ New Run's names and Try Again
def test_short_name_is_unique_per_sha(setup):
    s = settings(setup); book = {'path': '/x/My Book!.pdf', 'key': 'a' * 64}
    assert NR.short_name(s, book) == 'My_Book'
    d = setup / 'runs' / 'My_Book' / 'l1' / '_intake'; d.mkdir(parents=True)
    (d / 'intake.json').write_text(json.dumps({'original': {'sha256': 'b' * 64}}))
    assert NR.short_name(s, book) == 'My_Book-2'
    (d / 'intake.json').write_text(json.dumps({'original': {'sha256': 'a' * 64}}))
    assert NR.short_name(s, book) == 'My_Book'
    assert NR.short_name(s, {'path': '/x/日本.pdf', 'key': 'c' * 64}) == 'book'

@pytest.mark.parametrize('files,run,want', [
    ({'record.json': {}}, None, None), ({'workorder.ai.json': {}}, None, 'apply'), ({'workorder.json': {}, 'response.json': {}}, None, 'rerun'),
    ({'response.json': {}}, {'usage': {'cost_usd': 0.2}, 'finish_reason': 'stop'}, 'rerun'),
    ({'response.json': {}}, {'usage': {'cost_usd': 0.2}, 'finish_reason': 'length'}, 'estimate'),
    ({'response.json': {}}, {'usage': {'cost_usd': 0.2}, 'finish_reason': 'stop', 'error': {'code': 429}}, 'estimate'),
    ({}, {'estimate': {}}, 'estimate'), ({}, None, 'estimate')])
def test_try_again_is_decided_from_disk(tmp_path, files, run, want):
    for n, d in files.items(): (tmp_path / n).write_text(json.dumps(d))
    if run is not None: (tmp_path / 'run.json').write_text(json.dumps(run))
    assert NR.retry_kind(str(tmp_path)) == want

def test_run_name_rules():
    for ok in ('a', 'run-2026-11-05-1430', 'A_1'): assert NR.RUN_NAME.fullmatch(ok)
    for bad in ('-a', '_a', 'a b', 'a/b', '', 'x' * 65, '..'): assert not NR.RUN_NAME.fullmatch(bad)

# ------------------------------------------------------------------ New Run from the Saved Reply (free)
def test_replay_is_a_free_two_step_job(setup):
    s = settings(setup); J = s['jobs']
    src = setup / 'samples' / 'bk.pdf'; src.write_bytes(b'%PDF-1.4 book')
    R = setup / 'runs' / 'bk' / 'old'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'raw_reply': '{}', 'document': {'file': 'bk.pdf', 'sha256': hashlib.sha256(src.read_bytes()).hexdigest()}}))
    j = NR.start_replay(s, 'bk/old', str(R), 'again1')
    D = setup / 'runs' / 'bk' / 'again1'
    assert j['kind'] == 'replay-copy' and j['argv'][1:] == ['review_workorder.py', str(R), '--replay-to', str(D)] and not j['paid']
    t = j['then']
    assert t['kind'] == 'replay' and t['env_set'] == {'INTAKE_REUSE': '1', 'REPLY': str(D) + '.reply.txt', 'REVIEW': '1', 'RUN_DIR': str(D)}
    assert 'AUTO' not in t['env'] and t['argv'][1:] == ['run_api.sh', str(src), 'bk', 'again1']
    with pytest.raises(ValueError): NR.start_replay(s, 'bk/old', str(R), 'again1')        # the name is taken now
    (R / 'release').mkdir(); (R / 'release' / 'cleared.json').write_text(json.dumps({'state': 'done'}))
    with pytest.raises(ValueError, match='cleared'): NR.start_replay(s, 'bk/old', str(R), 'again2')

def test_a_run_made_outside_the_app_offers_no_buttons(setup):
    """A terminal's estimate-only folder (a run.json, no job of the app): no Spend, Get a New Estimate, Try Again or Dismiss,
    which could only refuse; a batch's book points to its batch page, and a single-run Spend of it is refused."""
    s = settings(setup)
    R = run_folder(setup, name='bk', label='term')
    st = RN.pending_state(s, 'bk/term', str(R))
    assert st['phase'] == 'outside' and st['spend'] is None and not st['from_app']
    B = run_folder(setup, name='batches', label='b1/bk')
    j = jobs.create(s['jobs'], 'batch-estimate', 'batches/b1/bk', ['bash', 'run_api.sh', '/x.pdf', 'bk', 'b1'], config.child_env(s), R=str(B))
    jobs.update(s['jobs'], j['id'], status='done')
    st = RN.pending_state(s, 'batches/b1/bk', str(B))
    assert st['phase'] == 'batch' and st['batch'] == 'b1' and st['spend'] is None
    with pytest.raises(SP.Refused, match='no estimate'): SP.authorize(s, 'workorder', 'batches/b1/bk', str(B), st['estimate']['fingerprint'])
    js = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "s.phase === 'outside'" in js and 'Open the Batch Page' in js

def test_the_prompt_check_fails_closed(setup):
    """05 M5: when decide.py's prompt can't be read, Spend is refused (it was skipped)."""
    s, R, est = spend_setup(setup)
    orig = SP.current_model_and_prompt
    SP.current_model_and_prompt = lambda: (MODEL, None)
    try:
        with pytest.raises(SP.Refused, match='out of date'): SP.authorize(s, 'workorder', 'bk/l1', str(R), est['fingerprint'])
    finally: SP.current_model_and_prompt = orig
    src = open(os.path.join(HERE, 'webapp', 'spend.py'), encoding='utf-8').read()
    assert 'prompt and prompt' not in src and 'not prompt or prompts - {prompt}' in src

def test_file_names_are_cleaned_on_every_page(setup):
    """05 M4: a record's file name with a control or direction character is cleaned before any page shows it."""
    s = settings(setup)
    R = setup / 'runs' / 'bk' / 'fin'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'document': {'file': 'a‮b\u0007.pdf', 'output': 'x.pdf'}}))
    assert RN.state(s, 'bk/fin', str(R))['file'] == 'ab.pdf'
    W = setup / 'runs' / 'bk' / 'w'; (W / '_intake').mkdir(parents=True)
    (W / '_intake' / 'intake.json').write_text(json.dumps({'original': {'file': 'c‏d.pdf'}}))
    assert RN.waiting_title('bk/w', str(W)) == 'cd.pdf' and RN.book_of(s, 'bk/w', str(W))[1] == 'cd.pdf'

def test_replay_of_a_batch_book_never_lands_in_another_books_folder(setup):
    """05 L2: the new folder for a batch book's replay is short_name(), so runs/<stem>/ of another book is not used."""
    s = settings(setup)
    src = setup / 'samples' / 'bk.pdf'; src.write_bytes(b'%PDF-1.4 book')
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    other = setup / 'runs' / 'bk' / 'x' / '_intake'; other.mkdir(parents=True)
    (other / 'intake.json').write_text(json.dumps({'original': {'sha256': 'f' * 64}}))
    R = setup / 'runs' / 'batches' / 'b1' / 'bk'; R.mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'raw_reply': '{}', 'document': {'file': 'bk.pdf', 'sha256': sha}}))
    j = NR.start_replay(s, 'batches/b1/bk', str(R), 'again1')
    assert j['run'] == 'bk-2/again1'

def test_auto_without_a_fingerprint_is_still_refused(setup):
    """With the personal-information tick removed (Patrick, 2026-11-06), the kind, paid and the fingerprint still hold."""
    s = settings(setup); J = s['jobs']
    env = config.child_env(s, {'AUTO': '1'})
    with pytest.raises(ValueError, match='its own start'): jobs.create(J, 'spend', 'a/r', ['true'], env, env_set={'AUTO': '1'}, paid=True)
    with pytest.raises(ValueError): jobs.create(J, 'spend', 'a/r', ['true'], env, env_set={'AUTO': '1'}, paid=True, fingerprint='')
    with pytest.raises(ValueError): jobs.create(J, 'batch', 'b/r', ['true'], env, env_set={'AUTO': '1'}, paid=True)
    assert jobs.create(J, 'spend', 'a/r', ['true'], env, env_set={'AUTO': '1'}, paid=True, fingerprint='f')['paid']

def test_start_remediation_is_described_by_its_worst_case_line():
    """Patrick, 2026-11-06: "Spend" became "Start Remediation" (visible words only: the kind, routes and ids stay 'spend'),
    and the button is described by the worst-case line. No visible "Spend" is left in the pages' strings."""
    import re
    pj = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    bj = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert 'aria-describedby="pp-cost">Start Remediation</button>' in pj and '<p id="pp-cost">' in pj
    assert 'aria-describedby="bt-cost">Start Remediation</button>' in bj and '<p id="bt-cost">' in bj
    for f in ('panel.js', 'batch.js', 'home.js', 'failures.py', 'newrun.py', 'batches.py', 'runs.py', 'home.py', 'jobs.py', 'spend.py'):
        src = open(os.path.join(HERE, 'webapp', f), encoding='utf-8').read()
        code = '\n'.join(l.split('//')[0] if f.endswith('.js') else l.split('#')[0] for l in src.splitlines())
        strings = re.findall(r"'([^'\n]*)'", re.sub(r'"""[\s\S]*?"""', '', code))
        assert not [s for s in strings if re.search(r'\bSpend\b', s)], f
