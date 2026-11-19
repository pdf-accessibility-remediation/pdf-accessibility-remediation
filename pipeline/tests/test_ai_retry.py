"""test_ai_retry.py: #151 (App: hold the review when AI requests did not finish) through run_api.sh, against a fake
OpenRouter put into every subprocess by tests/fakeor/sitecustomize.py (no network, no key, no cost).

    python -m pytest tests/test_ai_retry.py -q

1. A paid run (REVIEW=1, AUTO=1) whose first language request fails twice stops held, with one request to send again;
   AI_RETRY=1 sends only that request, and the run is no longer held; timing.json keeps the first call's steps.
2. review 26 M1: a replay of the folder's own reply keeps the outcomes: a step left out for its cost stays held, and a
   language step with a failed request, replayed with --reuse, stays held.
A synthetic tagged book of 170 made-up candidate words (two language requests: up to 150 forms each); veraPDF off.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import aistatus  # noqa: E402

def words(n):
    """n distinct made-up words with a macron (class marks): candidate forms, no book text."""
    out, a = [], 'bdkmnprst'
    for i in range(n): out.append(a[i % 9] + 'ō' + a[(i // 9) % 9] + 'a' + a[(i // 81) % 9] + 'i')
    return out

def book(tmp_path, n=170):
    ws = words(n)
    lines = [' and '.join(ws[i:i + 5]) for i in range(0, n, 5)]                # each word its own form, never a passage
    return langpdf.build(str(tmp_path / 'book.pdf'), [{'font': 'F3', 'text': t} for t in lines], step=20)

def run(tmp_path, src, fail=(), **extra):
    cfg = tmp_path / 'fake.json'; log = tmp_path / 'calls.jsonl'
    cfg.write_text(json.dumps({'log': str(log), 'fail_language': list(fail)}))
    if log.exists(): log.unlink()
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(tmp_path / 'run'), INTAKE='off', OPENROUTER_API_KEY='test-not-a-key', FAKE_OR=str(cfg),
               PYTHONPATH=os.path.join(HERE, 'tests', 'fakeor'), AI_PARALLEL='1', COST_HISTORY=str(tmp_path / 'ledger.jsonl'),
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',
               RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **extra)
    for k in ('FROM', 'REPLY', 'LANG_REPLY', 'LANG_TAGS', 'ESTIMATE'):
        if k not in extra: env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', src, 'book', 'r1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=900)
    calls = [json.loads(l) for l in open(log, encoding='utf-8')] if log.exists() else []
    return r, tmp_path / 'run', calls

def test_a_failed_request_holds_and_the_retry_sends_only_it(tmp_path):
    src = book(tmp_path)
    r, R, calls = run(tmp_path, src, fail=(1, 2), REVIEW='1', AUTO='1', PAGE_READS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    lang = [c for c in calls if c['kind'] == 'language']
    assert len(lang) == 3                                                     # request 1 twice (500, its one retry), request 2 once
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['count'] == 1 and aistatus.outcome(str(R), 'language')['why'] == 'done'
    assert 'the review will hold: some AI suggestions are missing' in r.stdout
    assert os.path.exists(R / 'language_retry_estimate.json') and json.load(open(R / 'language_retry_estimate.json'))['to_send'] == 1
    first = json.load(open(R / 'timing.json'))
    r2, R, calls2 = run(tmp_path, src, AI_RETRY='1', AUTO='1', PAGE_READS='off')
    assert r2.returncode == 0, r2.stdout[-3000:] + r2.stderr[-2000:]
    lang2 = [c for c in calls2 if c['kind'] == 'language']
    assert len(lang2) == 1 and not [c for c in calls2 if c['kind'] == 'workorder']   # only the failed request; no new work order
    assert sorted(lang2[0]['ids']) == sorted(lang[0]['ids'])
    assert not aistatus.status(str(R))['held']
    assert json.load(open(R / 'workorder.ai.json')) == json.load(open(R / 'workorder.json'))
    t = json.load(open(R / 'timing.json'))
    assert all(t[k] == v for k, v in first.items()) and 'retry: language tags via OpenRouter' in t
    assert json.load(open(R / 'review_stop.json'))['src'] == src

def test_ai_retry_refuses_when_nothing_is_unfinished(tmp_path):
    src = book(tmp_path, n=16)
    r, R, _ = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off')
    assert r.returncode == 0 and not aistatus.status(str(R))['held']
    r2, R, calls = run(tmp_path, src, AI_RETRY='1', AUTO='1')
    assert r2.returncode == 1 and 'nothing that the AI can be asked again is unfinished' in r2.stdout and calls == []

def own_replay(tmp_path, src, setup):
    """A paid run that stopped after its AI steps (a later step failed: no review stop), changed by setup(R), then the
    same command again with REVIEW=1: line 156 reuses the folder's own reply (review 26 M1)."""
    r, R, _ = run(tmp_path, src, AUTO='1', PAGE_READS='off', REVIEW='1')
    assert r.returncode == 0, r.stdout[-3000:]
    for f in ('workorder.ai.json', 'review_items.json', 'review_stop.json'): (R / f).unlink()   # as if it had failed after the AI steps
    setup(R)
    return run(tmp_path, src, PAGE_READS='off', REVIEW='1')

def test_an_own_replay_keeps_a_left_out_step_held(tmp_path):
    src = book(tmp_path, n=16)
    def setup(R):
        (R / 'language_run.json').unlink()
        aistatus.record(str(R), 'language', 'book', aistatus.WORDS['book']['language'])
    r, R, calls = own_replay(tmp_path, src, setup)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert "reusing it, no new AI request" in r.stdout and calls == []
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['state'] == 'left_out'

def test_an_own_replay_with_reuse_keeps_a_failed_request_held(tmp_path):
    src = book(tmp_path)
    def setup(R):
        run_ = json.load(open(R / 'language_run.json'))
        run_['requests'][0] = {k: v for k, v in run_['requests'][0].items() if k not in ('text', 'finish')} | {'error': {'code': 500, 'message': 'x'}}
        json.dump(run_, open(R / 'language_run.json', 'w'))
    r, R, calls = own_replay(tmp_path, src, setup)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert "language tags: this run's own decisions (no cost)" in r.stdout and calls == []
    assert aistatus.outcome(str(R), 'language')['why'] == 'done'             # `saved` never replaces `done` (26 M1)
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['count'] == 1
    r2, R, calls2 = run(tmp_path, src, AI_RETRY='1', AUTO='1', PAGE_READS='off')
    assert r2.returncode == 0, r2.stdout[-3000:] + r2.stderr[-2000:]
    assert len([c for c in calls2 if c['kind'] == 'language']) == 1 and not aistatus.status(str(R))['held']

def test_the_terminal_review_page_is_held_and_an_override_opens_it(tmp_path):
    src = book(tmp_path, n=16)
    r, R, _ = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off')
    aistatus.record(str(R), 'language', 'cap', aistatus.WORDS['cap']['language'])
    rw = subprocess.run([sys.executable, 'review_workorder.py', str(R), '--reviewer', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert rw.returncode == 1 and 'this run is held' in rw.stderr and 'Language Suggestions Not Made' in rw.stderr
    rw = subprocess.run([sys.executable, 'review_workorder.py', str(R), '--reviewer', 'Kim', '--override', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert rw.returncode == 0, rw.stdout + rw.stderr
    assert json.load(open(R / 'review.json'))['ai_override']['by'] == 'Kim'

REFUSED = {'schema': 'language-estimate/1', 'to_send': 1, 'refused': {'why': 'book', 'words': 'The language step would pass this PDF\'s limit.'}}

def test_a_run_whose_estimate_left_the_language_step_out_stops_held(tmp_path):
    """review 24 M2/M3: the Spend runs with the step off (LANG_TAGS=off); line 248 records the estimate's refusal before
    it removes the file, and says so; the run stops held with the left-out card, never `not_run`."""
    src = book(tmp_path, n=16)
    R = tmp_path / 'run'; R.mkdir(); (R / 'language_estimate.json').write_text(json.dumps(REFUSED))
    r, R, calls = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off', LANG_TAGS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'language tags: left out for their cost by an earlier estimate in this folder' in r.stdout
    assert not [c for c in calls if c['kind'] == 'language'] and not os.path.exists(R / 'language_estimate.json')
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['state'] == 'left_out' and aistatus.outcome(str(R), 'language')['why'] == 'book'

def test_a_one_book_batch_whose_language_step_was_left_out_stops_held(tmp_path):
    """review 24 M2: every book's step left out, so the batch runs with LANG_TAGS=off; its estimate step keeps the refused
    estimate (an estimate records nothing), and the book's run records it: held."""
    src = book(tmp_path, n=16)
    B = tmp_path / 'runs' / 'batches' / 'b1'; (B / 'book').mkdir(parents=True)
    (B / 'book' / 'language_estimate.json').write_text(json.dumps(REFUSED))
    cfg = tmp_path / 'fake.json'; cfg.write_text(json.dumps({'log': str(tmp_path / 'calls.jsonl')}))
    env = dict(os.environ, VERAPDF='off', INTAKE='off', OPENROUTER_API_KEY='test-not-a-key', FAKE_OR=str(cfg), AUTO='1', REVIEW='1', PAGE_READS='off',
               PYTHONPATH=os.path.join(HERE, 'tests', 'fakeor'), COST_HISTORY=str(tmp_path / 'ledger.jsonl'), RUNS_DIR=str(tmp_path / 'runs'), JOBS='1',
               HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    for k in ('FROM', 'REPLY', 'LANG_REPLY', 'LANG_TAGS', 'ESTIMATE', 'RUN_DIR', 'RETRY'): env.pop(k, None)
    r = subprocess.run(['bash', 'batch_api.sh', 'b1', src], cwd=HERE, env=env, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    s = aistatus.status(str(B / 'book'))
    assert s['held'] and s['steps']['language']['state'] == 'left_out', open(B / 'book.log').read()[-3000:]
