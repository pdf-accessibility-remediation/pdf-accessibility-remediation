"""test_webapp_held.py: #151 (App: hold the review when AI requests did not finish) in the app. A run stopped for its
review (REVIEW=1) whose AI steps did not finish is held: "Open the Review Page" is refused, the run page shows each
missing part with "Ask the AI Again" (paid, through webapp/spend.py), "Get a New Estimate" (free) and "Review Without the
Missing Suggestions" (a name, then lib/aistatus.py set_override); the home and batch pages say "AI Suggestions Missing".

    python -m pytest tests/test_webapp_held.py -q

No book, no model, no network: the outcome files are synthetic, the credit is patched, and the one subprocess (the
estimate job's own command) runs against tests/fakeor's fake OpenRouter.
"""
import os, sys, json, subprocess
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import aistatus as AS, costs  # noqa: E402
from webapp import jobs, runs, spend as SP, home as HM, logs, failures  # noqa: E402
from test_webapp import setup, settings, get, app, sha  # noqa: E402,F401  (fixtures)

CLAUDE = 'anthropic/claude-sonnet-5.5'

def held_run(t, part='language', expected=0.45, name='book', label='rv', base=None):
    """A REVIEW=1 stop whose language step (or page readings) stopped with an error, with run_api.sh's retry estimate."""
    W = (base or t / 'runs' / name) / label; (W / '_intake').mkdir(parents=True); (W / '_audit').mkdir()
    src = t / 'samples' / f'{label}.pdf'; src.write_bytes(b'%PDF-1.4 the original ' + label.encode())
    (W / '_intake' / 'intake.json').write_text(json.dumps({'original': {'file': f'{label}.pdf', 'sha256': sha(src)}}))
    (W / 'workorder.ai.json').write_text('{}'); (W / 'review_items.json').write_text('{}')
    (W / 'review_stop.json').write_text(json.dumps({'src': str(src), 'name': name, 'env': {'OCR_LANG': 'eng', 'MODEL': CLAUDE, 'LANGUAGE_MODEL': CLAUDE}}))
    AS.create(str(W))
    x = {'expected': {'usd': expected}} if expected is not None else {}
    if part in ('language', 'both'):
        (W / 'language_estimate.json').write_text(json.dumps({'to_send': 2}))
        AS.record(str(W), 'language', 'error', AS.WORDS['error'], 'RuntimeError: boom')
        (W / 'language_retry_estimate.json').write_text(json.dumps({'schema': 'language-estimate/1', 'model': CLAUDE, 'prompt_sha256': SP.current_language_prompt(),
                                                                    'to_send': 2, 'worst_case_usd': 0.8234, 'per_call_worst_usd': 0.42, **x}))
    if part in ('pages', 'both'):
        (W / '_audit' / 'page_reads.json').write_text(json.dumps({'pages': [{'page': 3, 'image': 'p3.png'}, {'page': 4, 'image': 'p4.png'}]}))
        AS.record(str(W), 'pages', 'credit', AS.WORDS['credit'])
        (W / 'page_reads_retry_estimate.json').write_text(json.dumps({'schema': 'page-reads-estimate/1', 'model': CLAUDE, 'to_read': 2,
                                                                      'worst_case_usd': 0.3101, 'per_page_worst_usd': 0.16, **x}))
    return W, src

@pytest.fixture
def credit(monkeypatch):
    c = {'usd': 50.0}
    monkeypatch.setattr(SP, 'credit_read', lambda s: c['usd'])
    monkeypatch.setattr(SP, 'check_credit', lambda s: {'usd': c['usd']})
    return c

# ------------------------------------------------------------------ the card
def test_the_card_names_each_part_and_the_cost_shown(setup):
    s = settings(setup); W, _ = held_run(setup)
    h = runs.waiting_state(s, 'book/rv', str(W))['held']
    assert h['intro'] == 'Some AI suggestions are missing, so the review can\'t start yet.'
    assert h['parts'] == [{'heading': 'Language Suggestions Not Finished', 'text': 'The step stopped with an error (2 requests not finished).',
                           'detail': 'RuntimeError: boom'}]
    assert h['retry']['cost'] == 'This uses AI credit: Expected Cost: $0.45 · Max Estimated Cost: $0.83.' and h['retry']['note'] is None
    assert h['retry']['fingerprint'] == SP.retry_fingerprint(str(W), 'language') and h['estimate'] and h['test'] is None
    assert h['without'] == '"Review Without the Missing Suggestions" lets the review start without them. Your name is recorded with this choice.'
    W2, _ = held_run(setup, label='rv2', expected=None)
    assert runs.held_view(s, 'book/rv2', str(W2))['retry']['cost'] == 'This uses AI credit: Max Estimated Cost: $0.83.'

def test_pages_go_first_and_say_why_the_language_waits(setup):
    s = settings(setup); W, _ = held_run(setup, part='both')
    h = runs.held_view(s, 'book/rv', str(W))
    assert [p['heading'] for p in h['parts']] == ['Language Suggestions Not Finished', 'Page Readings Not Finished']
    assert h['parts'][1]['text'] == 'There was not enough AI credit (2 pages not read).'
    assert h['retry']['part'] == 'pages' and h['retry']['cost'] == 'This uses AI credit: Expected Cost: $0.45 · Max Estimated Cost: $0.32.'
    assert h['retry']['note'] == ('"Ask the AI Again" requests the page readings first. The language suggestions are estimated again afterward, '
                                  'because the readings change some of the words.')

def test_a_part_left_out_for_its_cost_offers_only_the_override(setup):
    s = settings(setup); W, _ = held_run(setup)
    AS.record(str(W), 'language', 'cap', AS.WORDS['cap']['language'])
    h = runs.held_view(s, 'book/rv', str(W))
    assert h['parts'][0]['heading'] == 'Language Suggestions Not Made' and h['retry'] is None and not h['estimate']
    assert h['parts'][0]['text'] == AS.WORDS['cap']['language']

def test_a_missing_or_refused_estimate_offers_a_new_one(setup):
    s = settings(setup); W, _ = held_run(setup)
    (W / 'language_retry_estimate.json').unlink()
    h = runs.held_view(s, 'book/rv', str(W))
    assert h['retry'] is None and h['estimate'] and h['why'] == SP.NO_RETRY_ESTIMATE
    (W / 'language_retry_estimate.json').write_text(json.dumps({'to_send': 2, 'worst_case_usd': 9, 'model': CLAUDE, 'refused': {'why': 'cap', 'words': 'Too much.'}}))
    h = runs.held_view(s, 'book/rv', str(W))
    assert h['retry'] is None and h['estimate'] and h['why'] == 'Too much.'

# ------------------------------------------------------------------ the hold and the override
def test_the_first_review_is_refused_while_held_and_opens_after_the_override(setup):
    s = settings(setup); W, _ = held_run(setup)
    with pytest.raises(ValueError) as e: runs.start_first_review(s, 'book/rv', str(W), 8123)
    assert str(e.value) == ('The review can\'t start yet because some AI suggestions are missing. Language Suggestions Not Finished: The step '
                            'stopped with an error (2 requests not finished). Select "Ask the AI Again" or "Review Without the Missing Suggestions".')
    for by in ('', '   ', None):
        with pytest.raises(ValueError, match='Enter your name in "Your Name".'): runs.review_without(s, 'book/rv', str(W), by)
    assert not (W / 'ai_override.json').exists()
    d = runs.review_without(s, 'book/rv', str(W), ' Kim ')
    assert d['by'] == 'Kim' and json.load(open(W / 'ai_override.json'))['by'] == 'Kim'
    assert runs.waiting_state(s, 'book/rv', str(W))['held'] is None                       # no card after the override
    assert runs.start_first_review(s, 'book/rv', str(W), 8123)['kind'] == 'review'
    with pytest.raises(ValueError, match='No AI suggestions are missing'): runs.review_without(s, 'book/rv', str(W), 'Kim')

def test_the_route_on_the_app(app):
    port, t = app['port'], app['t']
    W, _ = held_run(t)
    def post(path, body=None):
        st, b, _ = get(port, path, method='POST', headers={'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{port}'}, body=json.dumps(body or {}))
        return st, json.loads(b or b'{}')
    d = json.loads(get(port, '/api/run/book/rv')[1])
    assert d['mode'] == 'waiting' and d['held']['parts'][0]['heading'] == 'Language Suggestions Not Finished'
    st, b = post('/api/run/book/rv/review')
    assert st == 409 and b['error'].startswith('The review can\'t start yet because some AI suggestions are missing.')
    assert post('/api/run/book/rv/review-without', {'by': ''}) == (409, {'error': 'Enter your name in "Your Name".'})
    st, b = post('/api/run/book/rv/review-without', {'by': 'Kim'})
    assert st == 200 and b['override']['by'] == 'Kim'
    assert json.loads(get(port, '/api/run/book/rv')[1])['held'] is None
    st, b = post('/api/run/book/r1/ai-retry', {'fingerprint': 'x'})             # a finished run: nothing to ask again
    assert st == 409 and b['error'] == 'This run isn\'t waiting for its review, so there is nothing to ask the AI again.'

# ------------------------------------------------------------------ "Ask the AI Again" and its Spend check
def test_ask_again_starts_a_bound_paid_job(setup, credit):
    s = settings(setup); W, src = held_run(setup)
    fp = runs.held_view(s, 'book/rv', str(W))['retry']['fingerprint']
    j = runs.start_ai_retry(s, 'book/rv', str(W), {'fingerprint': fp})
    assert j['kind'] == 'ai-retry' and j['paid'] and j['fingerprint'] == fp and j['argv'] == ['bash', 'run_api.sh', str(src), 'book', 'rv']
    assert j['env_set'] == {'RUN_DIR': str(W), 'OCR_LANG': 'eng', 'AI_RETRY': '1', 'AUTO': '1', 'BOOK_MAX_USD': '50.00',
                            'LANGUAGE_MODEL': CLAUDE, 'LANGUAGE_MAX_USD': '0.83', 'MODEL': CLAUDE}
    assert j['env']['AI_RETRY'] == '1' and j['env']['LANGUAGE_MAX_USD'] == '0.83' and j['env']['PAGE_READS'] == 'off'
    v = runs.job_view(s, j)
    assert v['heading'] == 'Processing: Asking the AI Again' and v['action'] == 'Ask the AI again'
    W2, _ = held_run(setup, part='both', label='rv2')                                # the page readings first
    j2 = runs.start_ai_retry(s, 'book/rv2', str(W2), {'fingerprint': SP.retry_fingerprint(str(W2), 'pages')})
    assert j2['env_set']['PAGE_READS_MAX_USD'] == '0.32' and j2['env_set']['MODEL'] == CLAUDE and 'LANGUAGE_MAX_USD' not in j2['env_set']

def test_ask_again_is_refused_when_the_run_is_not_waiting_not_held_or_overridden(setup, credit):
    s = settings(setup)
    W, _ = held_run(setup); fp = SP.retry_fingerprint(str(W), 'language')
    (W / 'record.json').write_text('{}')
    with pytest.raises(ValueError, match='isn\'t waiting for its review'): runs.start_ai_retry(s, 'book/rv', str(W), {'fingerprint': fp})
    W, _ = held_run(setup, label='ok')
    AS.record(str(W), 'language', 'done'); (W / 'language_run.json').write_text(json.dumps({'estimate': {'requests': 0}, 'requests': []}))
    assert not AS.status(str(W))['held']
    with pytest.raises(ValueError, match=SP.NOTHING_TO_RETRY): runs.start_ai_retry(s, 'book/ok', str(W), {'fingerprint': SP.retry_fingerprint(str(W), 'language')})
    W, _ = held_run(setup, label='ov'); AS.set_override(str(W), 'Kim')
    with pytest.raises(ValueError, match='opened without the missing suggestions'):
        runs.start_ai_retry(s, 'book/ov', str(W), {'fingerprint': SP.retry_fingerprint(str(W), 'language')})
    assert not [j for j in jobs.all_jobs(s['jobs']) if j['kind'] == 'ai-retry']

def test_a_changed_estimate_is_refused(setup, credit):
    s = settings(setup); W, _ = held_run(setup)
    fp = SP.retry_fingerprint(str(W), 'language')
    (W / 'language_run.json').write_text('{"requests": []}')                       # the step's record changed since the card was shown
    with pytest.raises(SP.Refused) as e: SP.authorize(s, 'retry', 'book/rv', str(W), fp)
    assert str(e.value) == 'The estimate changed since it was shown. Select "Get a New Estimate" and look at the new cost.'

def test_test_mode_refuses_ask_again_and_keeps_the_override(setup, credit):
    s = settings(setup, test_reply_dir=str(setup / 'replies')); W, _ = held_run(setup)
    h = runs.held_view(s, 'book/rv', str(W))
    assert h['retry'] is None and not h['estimate'] and h['test'] == '"Ask the AI Again" isn\'t available in test mode.'
    with pytest.raises(SP.Refused, match='This isn\'t available in test mode.'): SP.authorize(s, 'retry', 'book/rv', str(W), SP.retry_fingerprint(str(W), 'language'))
    assert runs.review_without(s, 'book/rv', str(W), 'Kim')['by'] == 'Kim'

def test_a_batch_pdf_must_fit_what_is_left_of_the_batch_limit(setup, credit, monkeypatch):
    s = settings(setup, limits={'per_batch_usd': 10}); B = setup / 'runs' / 'batches' / 'b1'
    W, _ = held_run(setup, name='bk', label='bk', base=B)
    fp = SP.retry_fingerprint(str(W), 'language')
    monkeypatch.setattr(costs, 'batch_spent', lambda B_, rd=None: {'usd': 9.5})
    with pytest.raises(SP.Refused) as e: SP.authorize(s, 'retry', 'batches/b1/bk', str(W), fp)
    assert str(e.value) == 'Asking the AI again could cost up to $0.83, more than the $0.50 left within this batch\'s limit of $10.00.'
    monkeypatch.setattr(costs, 'batch_spent', lambda B_, rd=None: {'usd': 1.0})
    a = SP.authorize(s, 'retry', 'batches/b1/bk', str(W), fp)
    assert a['argv'][3:] == ['bk', 'b1'] and a['env_set']['LANGUAGE_MAX_USD'] == '0.83'

def test_the_credit_and_the_pdf_limit_are_checked(setup, credit):
    s = settings(setup); W, _ = held_run(setup); fp = SP.retry_fingerprint(str(W), 'language')
    credit['usd'] = 0.5
    with pytest.raises(SP.Refused, match=r'could cost up to \$0.83, more than the \$0.50 of credit left'): SP.authorize(s, 'retry', 'book/rv', str(W), fp)
    credit['usd'] = None
    with pytest.raises(SP.Refused, match='The credit couldn\'t be checked'): SP.authorize(s, 'retry', 'book/rv', str(W), fp)
    credit['usd'] = 50.0
    s2 = settings(setup, limits={'per_book_usd': 0.5})
    with pytest.raises(SP.Refused, match=r'This PDF could cost up to \$0.83, more than the limit of \$0.50 per PDF.'): SP.authorize(s2, 'retry', 'book/rv', str(W), fp)

def test_a_restart_leaves_ask_again_waiting_for_a_new_estimate(setup, credit):
    s = settings(setup); W, _ = held_run(setup)
    j = runs.start_ai_retry(s, 'book/rv', str(W), {'fingerprint': SP.retry_fingerprint(str(W), 'language')})
    jobs.recover(s['jobs'])
    assert jobs.load(s['jobs'], j['id'])['status'] == 'needs-spend'
    h = runs.held_view(s, 'book/rv', str(W))
    assert h['retry'] is None and h['estimate'] and h['restarted'].startswith('The app restarted before the AI request started')
    e = runs.start_ai_retry_estimate(s, 'book/rv', str(W))
    assert jobs.load(s['jobs'], j['id'])['status'] == 'superseded' and e['kind'] == 'ai-retry-estimate' and not e['paid']
    assert e['argv'][1:] == ['name_languages.py', str(W / '_audit'), str(W), '--pdf', str(setup / 'samples' / 'rv.pdf'), '--dry-run',
                             '--estimate-to', str(W / 'language_retry_estimate.json'), '--model', CLAUDE]
    assert 'AUTO' not in e['env'] and runs.job_view(s, e)['heading'] == 'Processing: New Cost Estimate'

def test_the_estimate_job_writes_only_the_retry_estimate(setup, tmp_path):
    """The job's own command, run as the job runs it (its environment), against tests/fakeor's fake OpenRouter."""
    from PIL import Image
    s = settings(setup); W, _ = held_run(setup, part='pages')
    for n in (3, 4): Image.new('RGB', (40, 60), 'white').save(W / '_audit' / f'p{n}.png')
    (W / 'page_reads_retry_estimate.json').unlink()
    before = {os.path.relpath(os.path.join(d, f), W): os.path.getmtime(os.path.join(d, f)) for d, _, fs in os.walk(W) for f in fs}
    e = runs.start_ai_retry_estimate(s, 'book/rv', str(W))
    assert e['argv'][1:5] == ['read_pages.py', str(W / '_audit'), str(W), '--dry-run'] and '--outcome' not in e['argv']
    cfg = tmp_path / 'fake.json'; cfg.write_text(json.dumps({'log': str(tmp_path / 'calls.jsonl')}))
    env = dict(e['env'], PYTHONPATH=os.path.join(HERE, 'tests', 'fakeor'), FAKE_OR=str(cfg), HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9')
    r = subprocess.run(e['argv'], cwd=HERE, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    after = {os.path.relpath(os.path.join(d, f), W): os.path.getmtime(os.path.join(d, f)) for d, _, fs in os.walk(W) for f in fs}
    assert set(after) - set(before) == {'page_reads_retry_estimate.json'} and all(after[k] == v for k, v in before.items())
    est = json.load(open(W / 'page_reads_retry_estimate.json'))
    assert est['to_read'] == 2 and est['model'] == CLAUDE and not (tmp_path / 'calls.jsonl').exists()   # no chat request

# ------------------------------------------------------------------ the home and batch pages, the log lines, the failures
def test_the_home_label_of_a_held_run(setup):
    s = settings(setup); W, _ = held_run(setup)
    assert [r['status'] for r in HM.index(s)['runs'] if r['run'] == 'book/rv'] == ['AI Suggestions Missing']
    AS.set_override(str(W), 'Kim')
    assert [r['status'] for r in HM.index(s)['runs'] if r['run'] == 'book/rv'] == ['Waiting for Review']   # the cached row is read again

def test_the_retry_lines_are_run_api_shs():
    sh = open(os.path.join(HERE, 'run_api.sh'), encoding='utf-8').read()
    assert 'stage "retry: page readings via OpenRouter"' in sh and 'stage "retry: language tags via OpenRouter"' in sh
    assert 'stage "${RETRY:+retry: }review: page images (no model)"' in sh
    assert 'echo "▶ asking the AI again for the unfinished $( [[ $RETRY_PART == pages ]] && echo \'page readings\' || echo \'language suggestions\' ) (the work order is not decided again)"' in sh
    assert logs.plain('retry: page readings via OpenRouter') == 'sending to the AI: Hawaiian page readings'
    assert logs.plain('retry: language tags via OpenRouter') == 'sending to the AI: language tags'
    assert logs.plain('retry: review: page images (no model)') == 'preparing the review page'
    assert logs.plain('asking the AI again for the unfinished language suggestions (the work order is not decided again)') == \
        'asking the AI again for the unfinished language suggestions'

def test_a_failed_retry_explains_itself_on_the_card(setup, credit):
    s = settings(setup); W, _ = held_run(setup)
    j = runs.start_ai_retry(s, 'book/rv', str(W), {'fingerprint': SP.retry_fingerprint(str(W), 'language')})
    open(jobs.log_path(s['jobs'], j['id']), 'w').write('▶ asking the AI again for the unfinished language suggestions (the work order is not decided again)\n'
                                                       '▶ retry: language tags via OpenRouter\nTraceback (most recent call last):\nRuntimeError: x\n')
    jobs.update(s['jobs'], j['id'], status='failed', exit=1)
    f = runs.held_view(s, 'book/rv', str(W))['failure']
    assert f['code'] == 'R1' and f['next'] == [] and f['details']['step'] == 'asking the AI again'
    assert HM.index(s)['runs'][0]['status'] == 'AI Suggestions Missing'               # never "Failed": the card says why

def test_a_held_pdf_in_a_batch_says_so_on_its_row(setup):
    from webapp import batches as BT
    s = settings(setup); B = setup / 'runs' / 'batches' / 'b1'
    W, _ = held_run(setup, name='bk', label='bk', base=B)
    row = BT._book_status(s, 'b1', {'name': 'bk'}, str(W), [], None)
    assert row['words'] == 'AI Suggestions Missing' and BT.tone(row, str(W)) == 'person'

def test_the_apps_retry_job_runs_run_api_sh(setup, credit, tmp_path):
    """The job "Ask the AI Again" makes, run as the dispatcher would run it (its argv and its environment), against the fake
    OpenRouter: run_api.sh accepts the app's variables, sends only the failed request and the run is no longer held."""
    import test_ai_retry as TR
    src = TR.book(tmp_path)
    r, R, calls = TR.run(tmp_path, src, fail=(1, 2), REVIEW='1', AUTO='1', PAGE_READS='off')
    assert r.returncode == 0 and AS.status(str(R))['held'] and AS.retry_parts(AS.status(str(R))) == 'language', r.stdout[-2000:]
    s = settings(setup)
    j = runs.start_ai_retry(s, 'book/r1', str(R), {'fingerprint': SP.retry_fingerprint(str(R), 'language')})
    cfg = tmp_path / 'fake2.json'; log = tmp_path / 'calls2.jsonl'; cfg.write_text(json.dumps({'log': str(log)}))
    env = dict(j['env'], VERAPDF='off', PYTHONPATH=os.path.join(HERE, 'tests', 'fakeor'), FAKE_OR=str(cfg), OPENROUTER_API_KEY='test-not-a-key',
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',
               COST_HISTORY=str(tmp_path / 'ledger2.jsonl'), AI_PARALLEL='1')
    p = subprocess.run(j['argv'], cwd=HERE, env=env, capture_output=True, text=True, timeout=900)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-2000:]
    sent = [json.loads(l) for l in open(log, encoding='utf-8')]
    assert [c['kind'] for c in sent] == ['language'] and not AS.status(str(R))['held']
    assert '▶ retry: language tags via OpenRouter' in p.stdout

def test_the_batch_page_counts_held_pdfs_apart(setup):
    """review 29 M3: a batch's waiting PDFs with missing AI suggestions are counted apart, so the page doesn't tell them
    to "Finish Review"."""
    from webapp import batches as BT
    s = settings(setup); B = setup / 'runs' / 'batches' / 'b1'
    held_run(setup, name='bk', label='bk', base=B)
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "' missing AI suggestions: open ' + (s.held === 1 ? 'it' : 'each') +" in js and "' to ask the AI again or to review without them.'" in js
    src = open(os.path.join(HERE, 'webapp', 'batches.py'), encoding='utf-8').read()
    assert "if HM.held(R): held_n += 1" in src and "'held': held_n" in src

def test_the_card_says_every_request_goes_again_when_the_instructions_changed(setup):
    """review 29 L1."""
    W, _ = held_run(setup)
    (W / 'language_run.json').write_text(json.dumps({'estimate': {'requests': 3}, 'requests': [
        {'n': 1, 'sha256': 'a', 'ids': ['1'], 'finish': 'stop'}, {'n': 2, 'sha256': 'b', 'ids': ['1'], 'error': {'code': 500}}]}))
    est = json.load(open(W / 'language_retry_estimate.json')); est.update(to_send=3, reused=0); (W / 'language_retry_estimate.json').write_text(json.dumps(est))
    assert runs.all_again(str(W), 'language', est) == 'All 3 requests are sent again because the instructions for language suggestions have changed.'
    est['reused'] = 1
    assert runs.all_again(str(W), 'language', est) is None

def test_the_retry_estimate_job_uses_the_current_limit(setup):
    """review 29 M2: "Get a New Estimate" runs under the step's limit from Settings (or the code's default), never the
    bound review_stop.json keeps."""
    s = settings(setup); W, _ = held_run(setup)
    st = json.load(open(W / 'review_stop.json')); st['env']['LANGUAGE_MAX_USD'] = '0.01'; (W / 'review_stop.json').write_text(json.dumps(st))
    j = runs.start_ai_retry_estimate(s, 'book/rv', str(W))
    assert j['env_set'].get('LANGUAGE_MAX_USD') != '0.01'

def test_estimate_jobs_get_the_per_pdf_limit_from_settings(setup):
    """review 31 M1: an estimate job and "Get a New Estimate" for a retry carry the per-PDF limit from Settings, since the
    language step fills to the room left in it; L1: every job carries the app's limits under their own names (APP_*), for
    run_api.sh's estimates at a review stop, and no job may set those."""
    from webapp import config
    s = settings(setup)
    for usd in (80, 20):
        s['limits'] = {'per_book_usd': usd, 'language_usd': 30}
        e = config.child_env(s, {'ESTIMATE': '1'})
        assert e['BOOK_MAX_USD'] == f'{usd:.2f}' and e['LANGUAGE_MAX_USD'] == '30.00'
        W, _ = held_run(setup, label=f'rv{usd}')
        j = runs.start_ai_retry_estimate(s, f'book/rv{usd}', str(W))
        assert j['env_set']['BOOK_MAX_USD'] == f'{usd:.2f}' and j['env']['BOOK_MAX_USD'] == f'{usd:.2f}'
        a = config.child_env(s, {'AUTO': '1', 'BOOK_MAX_USD': '3.17'})          # a paid job: the bound, and the limits apart
        assert a['BOOK_MAX_USD'] == '3.17' and a['APP_BOOK_MAX_USD'] == f'{usd:.2f}' and a['APP_LANGUAGE_MAX_USD'] == '30.00'
    with pytest.raises(ValueError): config.child_env(s, {'APP_BOOK_MAX_USD': '999'})

# ------------------------------------------------------------------ #159: the warning before money is spent
def held_back_estimate(W, n=2400, total=31127):
    (W / 'language_estimate.json').write_text(json.dumps({'schema': 'language-estimate/1', 'forms': total, 'local': 0, 'sent': total - n, 'held_back': n,
                                                          'held_back_why': 'dollars', 'held_back_limit': {'usd': 25, 'which': 'step'}, 'to_send': 3, 'worst_case_usd': 24.9}))

def test_the_run_page_warns_beside_the_cost_when_forms_are_held_back(setup):
    W = setup / 'runs' / 'book' / 'est'; W.mkdir(parents=True)
    assert runs.held_back_view(str(W)) == {}
    held_back_estimate(W)
    v = runs.held_back_view(str(W))
    assert v['held_back_words'] == ("2,400 of 31,127 word forms will not be sent to the AI: they don't fit within the limit for language "
                                    "suggestions ($25). They will not be tagged, and the PDF can't be Ready until someone accepts that.")
    assert v['held_back_raise'].startswith('To send more of them, the app administrator can raise the limit for language suggestions')
    js = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "(e.held_back_words ? '</p><p class=\"pp-warn-t\" id=\"pp-held-back\">' + esc(e.held_back_words)" in js

def test_the_batch_estimate_lists_the_pdfs_that_hold_forms_back(setup):
    from webapp import batches as BT
    src = open(os.path.join(HERE, 'webapp', 'batches.py'), encoding='utf-8').read()
    assert "held_back.append({'name': b.get('title') or b['name'], 'count': hb_['held_back_count']})" in src and "'held_back': held_back}" in src
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "word forms back because they don\\'t fit within the limit for language suggestions: '" in js and 'heldBackLine(T.held_back)' in js
