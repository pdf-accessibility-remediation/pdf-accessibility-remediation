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

def run(tmp_path, src, fail=(), fake=None, **extra):
    cfg = tmp_path / 'fake.json'; log = tmp_path / 'calls.jsonl'
    cfg.write_text(json.dumps({'log': str(log), 'fail_language': list(fail), **(fake or {})}))
    if log.exists(): log.unlink()
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(tmp_path / 'run'), INTAKE='off', OPENROUTER_API_KEY='test-not-a-key', FAKE_OR=str(cfg),
               PYTHONPATH=os.path.join(HERE, 'tests', 'fakeor'), AI_PARALLEL='1', COST_HISTORY=str(tmp_path / 'ledger.jsonl'),
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',
               RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    env.update(extra)
    for k in ('FROM', 'REPLY', 'LANG_REPLY', 'LANG_TAGS', 'ESTIMATE', 'OUT'):
        if k not in extra: env.pop(k, None)
    for k in [k for k, v in env.items() if v is None]: env.pop(k)              # None: left unset (a terminal call with no settings)
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

def page_held(tmp_path, n=20):
    """A run whose language step finished and whose one page reading failed (the page listed by hand: a synthetic tagged
    book has no scanned page)."""
    from PIL import Image
    src = book(tmp_path, n=n)
    r, R, _ = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off')
    assert r.returncode == 0 and not aistatus.status(str(R))['held']
    A = R / '_audit'; (A / 'page_reads').mkdir(exist_ok=True)
    Image.new('RGB', (200, 260), 'white').save(A / 'page_reads' / 'p1.png')
    (A / 'page_reads.json').write_text(json.dumps({'pages': [{'page': 1, 'image': 'page_reads/p1.png'}]}))
    (R / 'page_reads_run.json').write_text(json.dumps({'schema': 'page-reads/1', 'pages': [{'page': 1, 'error': {'code': 500, 'message': 'x'}}], 'cost_usd': 0}))
    aistatus.record(str(R), 'pages', 'done')
    s = aistatus.status(str(R))
    assert s['held'] and aistatus.retry_parts(s) == 'pages' and 'language' not in s['steps']
    return src, R

def test_the_page_part_goes_first_and_alone(tmp_path):
    """review 25 §2.4: the first AI_RETRY reads only the unfinished page and sends no language request. On this tagged
    page the reading replaces no word the language step read (readings replace words on scanned pages), so its re-estimate
    reuses every answer: the language step stays `done` and the hold clears."""
    src, R = page_held(tmp_path)
    r1, R, calls1 = run(tmp_path, src, AI_RETRY='1', AUTO='1')
    assert r1.returncode == 0, r1.stdout[-3000:] + r1.stderr[-2000:]
    assert [c['kind'] for c in calls1] == ['page']
    assert json.load(open(R / 'workorder.ai.json'))['page_readings'] == [{'page': 1, 'text': 'Ua hele mai ka wahine i ka hale'}]
    assert json.load(open(R / 'language_retry_estimate.json'))['to_send'] == 0
    assert aistatus.outcome(str(R), 'language')['why'] == 'done' and not aistatus.status(str(R))['held']

def test_after_the_page_part_changed_words_hold_for_a_second_part(tmp_path):
    """review 26 M2: when the language step's re-estimate after the page part has requests to send, the outcome is
    pages_changed and the run stays held for the language part, which the second AI_RETRY sends. On a scanned page the new
    reading changes the words; here the change is simulated by making the saved answers unusable (another prompt)."""
    src, R = page_held(tmp_path)
    lr = json.load(open(R / 'language_run.json')); lr['prompt_sha256'] = 'another-prompt'; json.dump(lr, open(R / 'language_run.json', 'w'))
    r1, R, calls1 = run(tmp_path, src, AI_RETRY='1', AUTO='1')
    assert r1.returncode == 0, r1.stdout[-3000:] + r1.stderr[-2000:]
    assert [c['kind'] for c in calls1] == ['page'] and aistatus.outcome(str(R), 'language')['why'] == 'pages_changed'
    assert 'the new page readings changed some words' in r1.stdout
    s = aistatus.status(str(R))
    assert s['held'] and 'pages' not in s['steps'] and aistatus.retry_parts(s) == 'language'
    assert aistatus.lines(s) == ['Language Suggestions Not Finished: New page readings changed some words (1 request not finished).']
    r2, R, calls2 = run(tmp_path, src, AI_RETRY='1', AUTO='1')
    assert r2.returncode == 0, r2.stdout[-3000:] + r2.stderr[-2000:]
    assert [c['kind'] for c in calls2] == ['language'] and not aistatus.status(str(R))['held']

def test_a_reply_from_elsewhere_stops_without_a_hold(tmp_path):
    """23 §3.2: a saved reply from elsewhere (FROM=, the app's test mode) was never to send anything: not_run, never held."""
    src = book(tmp_path, n=16)
    (tmp_path / 'reply.txt').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5', 'choices': [{'message': {'content': json.dumps(
        {'document': {'lang': 'en', 'title': 'T'}})}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}))
    r, R, calls = run(tmp_path, src, REVIEW='1', REPLY=str(tmp_path / 'reply.txt'))
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert calls == [] and aistatus.outcome(str(R), 'language')['why'] == 'not_run' and not aistatus.status(str(R))['held']

def test_the_override_is_listed_in_review_md_and_survives_the_tidy(tmp_path):
    src = book(tmp_path, n=16)
    r, R, _ = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off')
    aistatus.record(str(R), 'pages', 'cap', aistatus.WORDS['cap']['pages'])
    (R / '_audit' / 'page_reads.json').write_text(json.dumps({'pages': [{'page': 1, 'image': 'x.png'}]}))
    rw = subprocess.run([sys.executable, 'review_workorder.py', str(R), '--reviewer', 'Kim', '--override', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert rw.returncode == 0, rw.stdout + rw.stderr
    r2, R, calls = run(tmp_path, src, PAGE_READS='off')                       # the apply after the review
    assert r2.returncode == 0, r2.stdout[-3000:] + r2.stderr[-2000:]
    md = open(R / 'review.md', encoding='utf-8').read(); rec = json.load(open(R / 'record.json'))
    assert '**Reviewed without missing AI suggestions:** Kim on ' in md and 'Page Readings Not Made' in md
    assert rec['ai_override']['by'] == 'Kim' and os.path.exists(R / aistatus.OVERRIDE) and not os.path.exists(R / aistatus.NAME)

def test_a_terminal_retry_keeps_the_runs_settings(tmp_path):
    """review 29 M1: AI_RETRY=1 with no settings, on a run stopped with OUT and INTAKE=off, takes them from review_stop.json:
    no intake runs, and review_stop.json is left as the first call wrote it."""
    src = book(tmp_path)
    r, R, _ = run(tmp_path, src, fail=(1, 2), REVIEW='1', AUTO='1', PAGE_READS='off', OUT='mine.pdf')
    assert r.returncode == 0 and aistatus.status(str(R))['held'], r.stdout[-2000:]
    stop = json.load(open(R / 'review_stop.json'))
    assert stop['env']['OUT'] == 'mine.pdf' and stop['env']['INTAKE'] == 'off'
    r2, R, calls = run(tmp_path, src, AI_RETRY='1', AUTO='1', INTAKE=None)      # the printed command: no settings
    assert r2.returncode == 0, r2.stdout[-3000:] + r2.stderr[-2000:]
    assert 'INTAKE=off (from this run\'s review stop)' in r2.stdout and 'OUT=mine.pdf (from this run\'s review stop)' in r2.stdout
    assert '0/5 intake' not in r2.stdout and json.load(open(R / 'review_stop.json')) == stop

def test_a_retry_is_estimated_under_the_current_limit_and_can_be_asked_again(tmp_path):
    """review 29 M2: the app's retry job runs with the language limit bound to the amount shown. When it leaves a request
    unfinished again and prices have risen, the stop's new estimate is made under the current limit, never that bound,
    so it isn't refused, and a second retry sends the request."""
    src = book(tmp_path)
    r, R, _ = run(tmp_path, src, fail=(1, 2), REVIEW='1', AUTO='1', PAGE_READS='off')
    first = json.load(open(R / 'language_retry_estimate.json'))
    bound = f'{first["worst_case_usd"] + 0.01:.2f}'
    cfg = tmp_path / 'fake.json'
    r2, R, calls2 = run(tmp_path, src, fail=(1, 2), AI_RETRY='1', AUTO='1', LANGUAGE_MAX_USD=bound)   # fails again
    assert r2.returncode == 0 and aistatus.status(str(R))['held'], r2.stdout[-3000:]
    # prices rise by half, then "Get a New Estimate" (the stop's estimate again, with the job's bound still in its env)
    cfg.write_text(json.dumps({'log': str(tmp_path / 'calls.jsonl'), 'price_mult': 1.5}))
    env = dict(os.environ, FAKE_OR=str(cfg), PYTHONPATH=os.path.join(HERE, 'tests', 'fakeor'), OPENROUTER_API_KEY='test-not-a-key', LANGUAGE_MAX_USD=bound)
    p = subprocess.run(['bash', '-c', 'env -u LANGUAGE_MAX_USD python3 name_languages.py "$1" "$2" --pdf "$3" --dry-run --estimate-to "$2/language_retry_estimate.json"',
                        '_', str(R / '_audit'), str(R), src], cwd=HERE, env=env, capture_output=True, text=True)
    est = json.load(open(R / 'language_retry_estimate.json'))
    assert p.returncode == 0 and est['worst_case_usd'] > float(bound) and 'refused' not in est, p.stdout + p.stderr
    r3, R, calls3 = run(tmp_path, src, AI_RETRY='1', AUTO='1')
    assert r3.returncode == 0 and [c['kind'] for c in calls3] == ['language'] and not aistatus.status(str(R))['held']

def test_a_model_lookup_that_fails_is_recorded_and_held(tmp_path):
    """review 29 §3: the run-path dry run records `lookup` (a model the service doesn't list); the run holds with
    "Ask the AI Again" offered."""
    src = book(tmp_path, n=16)
    r, R, calls = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off', LANGUAGE_MODEL='anthropic/not-a-model')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    o = aistatus.outcome(str(R), 'language')
    assert o['why'] == 'lookup' and 'not on OpenRouter' in o['detail'] and not [c for c in calls if c['kind'] == 'language']
    s = aistatus.status(str(R))
    assert s['held'] and aistatus.retry_parts(s) == 'language'

def test_a_kept_refused_estimate_never_counts_as_cost(tmp_path):
    """review 29 §3 (23 L5): a refused language estimate kept in the folder leaves "Expected Cost" and the cost lines as a
    folder without it."""
    from lib import costs
    src = book(tmp_path, n=16)
    r, R, _ = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off')
    p = R / 'language_estimate.json'
    if p.exists(): p.unlink()
    without = (costs.after_line(str(R)), json.dumps(costs.estimate(str(R), 'workorder'), sort_keys=True, default=str))
    # a step that still doesn't fit today's per-PDF limit ($60 against $50 since #155): costs.estimate works the refusal out again
    # from today's limits (fit_optional), so a refused step that fits now would count, and would no longer be left out
    p.write_text(json.dumps({'schema': 'language-estimate/1', 'to_send': 3, 'worst_case_usd': 60.0, 'expected': {'usd': 36.0},
                             'refused': {'why': 'book', 'words': 'left out'}}))
    withref = (costs.after_line(str(R)), json.dumps(costs.estimate(str(R), 'workorder'), sort_keys=True, default=str))
    assert withref[0] == without[0]
    a, b = json.loads(without[1]), json.loads(withref[1])
    if a and b:
        assert (a.get('ceiling_usd'), a.get('expected'), a.get('language')) == (b.get('ceiling_usd'), b.get('expected'), b.get('language'))

# ------------------------------------------------------------------ #159: word forms the limits hold back
EVIL = 'kō<ra&"mi'                                   # a made-up held-back form: escaped wherever it is shown (review 29 L5)

def held_back_run(tmp_path, limit='0.0001'):
    src = book(tmp_path, n=16)
    r, R, calls = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off', LANGUAGE_MAX_USD=limit)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    return src, r, R, calls

def test_the_terminal_says_what_is_held_back_before_sending(tmp_path):
    src, r, R, calls = held_back_run(tmp_path)
    assert 'word forms will not be sent to the AI: they don\'t fit within the limit for language suggestions ($0.00).' in r.stdout
    assert 'raise the limit for this run: LANGUAGE_MAX_USD=' in r.stdout
    assert r.stdout.index('will not be sent to the AI') < r.stdout.index('AUTO=1: naming languages without asking')
    assert not [c for c in calls if c['kind'] == 'language'] and not aistatus.status(str(R))['held']   # never refused, never held

def test_nothing_is_said_when_nothing_is_held_back(tmp_path):
    src = book(tmp_path, n=16)
    r, R, _ = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off')
    assert 'will not be sent to the AI' not in r.stdout

def english_book(tmp_path):
    """16 made-up candidate words in 4 lines, and 25 lines of ordinary English that are no candidates in an English
    document; in a Japanese one every Latin-script line is (langcands.py), so the work order's language adds forms."""
    ws, plain = words(16), ['river', 'house', 'garden', 'morning', 'window', 'table', 'letter', 'market', 'harbor', 'island']
    lines = [' and '.join(ws[i:i + 4]) for i in range(0, 16, 4)] + [f'the {a} near the {b}' for a in plain[:5] for b in plain[5:]]
    return langpdf.build(str(tmp_path / 'book.pdf'), [{'font': 'F3', 'text': t} for t in lines], step=20)

def test_more_forms_after_the_estimate_hold_the_review_with_the_warning(tmp_path):
    """Review 33 F1: an English book whose work order names Japanese finds every Latin word again after the estimate, so
    more word forms would be held back than were shown. With nobody at the keyboard (AUTO=1, as every app job) nothing is
    sent: the review holds with forms_changed, and "Ask the AI Again" shows the new estimate with its warning."""
    src = english_book(tmp_path)
    r, R, calls = run(tmp_path, src, fake={'doc_lang': 'ja'}, REVIEW='1', AUTO='1', PAGE_READS='off', LANGUAGE_MAX_USD='0.0001',
                      APP_LANGUAGE_MAX_USD='0.0001')                       # the app's Settings: the stop's retry estimate holds back too
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert not [c for c in calls if c['kind'] == 'language']
    o = aistatus.outcome(str(R), 'language')
    assert o['why'] == 'forms_changed' and o['words'] == 'More word forms were found after the estimate.'
    assert 'more word forms would be held back than the estimate showed (29 against 16): nothing sent' in r.stdout
    s = aistatus.status(str(R))
    assert s['held'] and s['steps']['language']['retry'] and aistatus.retry_parts(s) == 'language'
    assert s['steps']['language']['count'] == 0                               # requests: under the Settings limit every form is held back
    assert aistatus.lines(s) == ['Language Suggestions Not Finished: More word forms were found after the estimate.']
    sys.path.insert(0, HERE)
    from webapp import runs as WR
    v = WR.held_back_view(str(R), 'language_retry_estimate.json')          # the retry card's warning (review 31 M3)
    assert v['held_back_count'] == 29 and '29 word forms will not be sent to the AI' in v['held_back_words']

def test_a_batch_pdf_with_no_estimate_shown_holds(tmp_path):
    """Review 33 F1 with F2: a batch PDF whose language estimate was missing runs bound to $0.00 with LANG_HELD_SHOWN=0.
    Its own first dry run holds every form back, but none was shown, so the review holds with forms_changed."""
    src = english_book(tmp_path)
    r, R, calls = run(tmp_path, src, REVIEW='1', AUTO='1', PAGE_READS='off', LANGUAGE_MAX_USD='0.00', LANG_HELD_SHOWN='0')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert aistatus.outcome(str(R), 'language')['why'] == 'forms_changed' and not [c for c in calls if c['kind'] == 'language']
    assert '(16 against 0): nothing sent' in r.stdout and aistatus.status(str(R))['held']
    (tmp_path / 'b').mkdir()                                                # all 16 shown: a fresh run sends as before
    r, R, calls = run(tmp_path / 'b', src, REVIEW='1', AUTO='1', PAGE_READS='off', LANGUAGE_MAX_USD='0.00', LANG_HELD_SHOWN='16')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert aistatus.outcome(str(R), 'language')['why'] == 'done' and not aistatus.status(str(R))['held']

def test_the_same_forms_after_the_estimate_send_as_before(tmp_path):
    """Review 33 F1: when the work order's language finds the same word forms, the run sends as before (no hold)."""
    src = english_book(tmp_path)
    r, R, calls = run(tmp_path, src, fake={'doc_lang': 'en-US'}, REVIEW='1', AUTO='1', PAGE_READS='off', LANGUAGE_MAX_USD='0.0001')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert aistatus.outcome(str(R), 'language')['why'] == 'done'           # sent as before: everything held back by the same limit
    assert 'more word forms would be held back' not in r.stdout and not aistatus.status(str(R))['held']
    assert 'AUTO=1: naming languages without asking' in r.stdout and json.load(open(R / 'language_run.json'))['held_back_count'] == 16

def test_held_back_forms_reach_the_record_the_line_and_review_md_and_html(tmp_path):
    src, r, R, _ = held_back_run(tmp_path)
    lr = json.load(open(R / 'language_run.json')); lr['held_back'][0] = EVIL; json.dump(lr, open(R / 'language_run.json', 'w'))
    from review import core
    hb = core.held_back_info(str(R))                                          # the first review reads language_run.json
    assert hb['count'] == lr['held_back_count'] and EVIL in hb['forms'] and hb['accepted'] is None
    assert ' were not sent to the AI: ' in hb['sentence'] and 'They are not tagged' in hb['sentence']      # review 31 L3: past tense after the run
    assert all(k[0][:1].isupper() for k in hb['by_kind'])                                          # review 31 L3: lines in sentence case
    rw = subprocess.run([sys.executable, 'review_workorder.py', str(R), '--reviewer', 'Kim'], cwd=HERE, capture_output=True, text=True)
    assert rw.returncode == 0, rw.stdout + rw.stderr
    r2, R, _ = run(tmp_path, src, PAGE_READS='off')                          # the apply
    assert r2.returncode == 0, r2.stdout[-3000:] + r2.stderr[-2000:]
    rec = json.load(open(R / 'record.json'))
    st = rec['language_status']['held_back']
    assert st['count'] == lr['held_back_count'] and st['why'] == 'dollars' and st['sha'] == lr['held_back_sha'] and EVIL in st['forms']
    line = next(x for x in rec['glance']['ship'] if x['what'] == 'Language tags')
    assert line['ok'] is False and 'were not sent: more than the limit for language suggestions' in line['text']
    md = open(R / 'review.md', encoding='utf-8').read()
    assert f'**Word forms not sent ({st["count"]}):** more than the limit for language suggestions; they are not tagged.' in md and f'"{EVIL}"' in md
    html = open(R / 'review.html', encoding='utf-8').read()
    assert EVIL not in html and 'kō&lt;ra&amp;' in html
    # "Review Again": language_run.json is gone; the list comes from record.json, and an acceptance names these forms
    assert not os.path.exists(R / 'language_run.json')
    hb2 = core.held_back_info(str(R))
    assert hb2['count'] == st['count'] and hb2['sha'] == st['sha'] and EVIL in hb2['forms']

def test_an_acceptance_names_the_forms_and_review_again_keeps_it(tmp_path, monkeypatch):
    """#159 Part 1, review 29 L2: "Accept Without the Word Forms Not Sent" is recorded with the reviewer's name, the count
    and the forms' hash; a later session carries it while the same forms are held back, and a different set reopens it."""
    from review import core
    from lib import glance as G
    monkeypatch.setattr(core, 'check', lambda R_, wo: [])
    R = tmp_path; (R / '_audit').mkdir(); (R / '_audit' / 'digest.json').write_text('{}')
    hb = {'count': 2, 'sha': 'abcd', 'why': 'dollars', 'limit': {'usd': 25, 'which': 'step'}, 'by_kind': {'unknown': 2}, 'forms': ['a', 'b']}
    (R / 'record.json').write_text(json.dumps({'language_status': {'candidates': 5, 'state': 'decided', 'held_back': hb}}))
    wo = {'document': {'lang': 'en', 'title': 'T'}}
    v = core.finish(str(R), wo, dict(wo), 'Kim', '2026-11-18', 'page', held_back=core.held_back_info(str(R)), accept_held_back=True, gap_default='t')
    acc = v['language']['held_back_accepted']
    assert acc == {'by': 'Kim', 'date': '2026-11-18', 'count': 2, 'sha': 'abcd'}
    rec = {'workorder': {'language_parts': {'version': 2, 'forms': []}}, 'language_status': {'candidates': 5, 'state': 'decided', 'held_back': hb},
           'language_review': v['language']}
    assert G.language_line(rec) == (True, 'Approved (Kim on November 18, 2026 · 2 word forms not sent, accepted by Kim)')
    (R / 'record.json').write_text(json.dumps(rec))                           # the next session ("Review Again") carries it
    v2 = core.finish(str(R), wo, dict(wo), 'Lee', '2026-11-19', 'page', held_back=core.held_back_info(str(R)), gap_default='t')
    assert v2['language']['held_back_accepted']['by'] == 'Kim'
    rec['language_status']['held_back'] = {**hb, 'sha': 'other'}               # another set of the same size: open again
    assert G.language_line(rec)[0] is False
    (R / 'record.json').write_text(json.dumps(rec))
    assert core.held_back_info(str(R))['accepted'] is None

def test_the_line_says_both_when_forms_wait_for_decisions_too():
    from lib import glance as G
    rec = {'workorder': {'language_parts': {'version': 2, 'forms': [{'form': 'x', 'lang': 'haw', 'confidence': 'high', 'tag': True}]}},
           'language_status': {'candidates': 5, 'state': 'decided', 'held_back': {'count': 2400, 'sha': 's', 'why': 'dollars', 'limit': {'which': 'step'}}},
           'language_review': {'not_reviewed': 3200, 'forms': {}}}
    assert G.language_line(rec)[1] == 'Not Reviewed (3,200 word forms to decide on the review page; 2,400 not sent: more than the limit for language suggestions)'
    rec['language_status']['held_back']['why'] = 'forms'
    assert 'more than the set number of word forms' in G.language_line(rec)[1]
