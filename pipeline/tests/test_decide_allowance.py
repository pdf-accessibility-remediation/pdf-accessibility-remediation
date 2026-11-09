"""test_decide_allowance.py: what decide.py sends and spends under #65 (costs in dollars and an expected cost): each request's
max tokens, the doubling after a cut-off, the figure request's doubled retry and its limits, the expected figure and the ledger.

    python -m pytest tests/test_decide_allowance.py -q

Synthetic books only. A live run happens in this process against a fake OpenRouter (urlopen replaced; nothing leaves it, and the
key is a dummy); everything else is a dry run or a replay with the network blocked.
"""
import os, sys, json, runpy, shutil, time, io, urllib.request, urllib.error
import pytest

from test_figure_requests_run import book, decide, small_audit, reply_for, env, Resp, HERE   # noqa: F401  (book is a fixture)
sys.path.insert(0, HERE)
from lib import costs as C, costhistory as H, figpasses as F

MODEL = 'anthropic/claude-sonnet-5.5'

def stop(body, cost=0.01, finish='stop', tokens=100, text=None):
    import re
    objs = [m.group(1) for c in body['messages'][1]['content'] if c.get('type') == 'text' for m in [re.match(r'Figure obj "([^"]+)"', c['text'])] if m]
    return {'choices': [{'message': {'content': reply_for(objs, 'Alt from a request.') if text is None else text}, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 1000, 'completion_tokens': tokens, 'cost': cost}}

def fake(calls, reply, max_out=128000, ctx=1000000):
    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.endswith('/models'):
            return Resp({'data': [{'id': MODEL, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}, 'architecture': {'input_modalities': ['text', 'image']},
                                   'context_length': ctx, 'top_provider': {'max_completion_tokens': max_out}, 'supported_parameters': ['max_tokens']}]})
        if url.endswith('/key'): return Resp({'data': {'limit_remaining': 100}})
        if url.endswith('/credits'): return Resp({'data': {'total_credits': 100, 'total_usage': 0}})
        calls.append(req.data); out = reply(json.loads(req.data), len(calls))
        if isinstance(out, Exception): raise out
        return Resp(out)
    return urlopen

def live(A, R, monkeypatch, *args, reply=None, ledger=None, **kw):
    """decide.py as a real run would call it. Returns (the raw request bodies, the exit code or None)."""
    calls = []
    monkeypatch.setattr(urllib.request, 'urlopen', fake(calls, reply or (lambda b, n: stop(b)), **kw)); monkeypatch.setattr(time, 'sleep', lambda s: None)
    for k, v in env().items(): monkeypatch.setenv(k, v)
    if ledger is not None: monkeypatch.setenv('COST_HISTORY', str(ledger))
    monkeypatch.setattr(sys, 'argv', ['decide.py', str(A), str(R), *map(str, args)]); monkeypatch.chdir(HERE)
    code = None
    try: runpy.run_path(os.path.join(HERE, 'decide.py'), run_name='__main__')
    except SystemExit as e: code = e.code
    return calls, code

def load(p): return json.load(open(p, encoding='utf-8'))
def cut_second(b, n): return stop(b, cost=0.3, finish='length', tokens=32000, text='```json\n{"alt": [') if n == 2 else stop(b)

# ------------------------------------------------------------------ the whole request
def test_every_request_is_sent_with_its_usual_max_tokens(book, tmp_path, monkeypatch):
    calls, code = live(book[1], tmp_path / 'r', monkeypatch)
    assert code is None and [json.loads(c)['max_tokens'] for c in calls] == [48000, 32000]
    assert set(json.loads(calls[1])) == {'model', 'messages', 'max_tokens', 'usage', 'provider'}      # this model's listing takes no temperature

def test_a_retry_differs_from_its_first_send_only_in_max_tokens(book, tmp_path, monkeypatch):
    calls, _ = live(book[1], tmp_path / 'r', monkeypatch, reply=cut_second)
    a, b = json.loads(calls[1]), json.loads(calls[2])
    assert (a['max_tokens'], b['max_tokens']) == (32000, 64000) and dict(a, max_tokens=0) == dict(b, max_tokens=0)
    assert [json.loads(c)['max_tokens'] for c in calls] == [48000, 32000, 64000]

# ------------------------------------------------------------------ the figure request's doubled retry
def test_a_cut_off_figure_request_is_sent_again_and_recorded(book, tmp_path, monkeypatch):
    R = tmp_path / 'r'; live(book[1], R, monkeypatch, reply=cut_second)
    run = load(R / 'run.json'); wo = load(R / 'workorder.json'); side = load(R / 'passes.json')
    assert run['figure_passes']['cut_off_retries'] == [{'pass': '2', 'max_tokens': 64000, 'cost_usd': 0.01, 'outcome': 'done'}]
    p = run['passes'][1]; assert p['outcome'] == 'done' and [c['max_tokens'] for c in p['calls']] == [32000, 64000] and p['calls'][1]['doubled'] is True
    assert side['passes'][0]['call']['max_tokens'] == 64000 and side['passes'][0]['call']['doubled'] is True and side['format'] == 'figure-passes/1'
    assert 'failed' not in run['figure_passes'] and not any('Alt text for' in d.get('what', '') for d in wo.get('deferrals') or [])
    a = C.actual(str(R)); assert a['retry_usd'] == 0.01 and a['usd'] == pytest.approx(0.32)
    assert run['estimate']['worst_case_total_usd'] == pytest.approx(sum(x['worst_case_usd'] for x in run['estimate']['passes']), abs=1e-3)      # what was shown, unchanged

def test_the_retry_is_trimmed_to_the_models_maximum(book, tmp_path, monkeypatch):
    calls, _ = live(book[1], tmp_path / 'r', monkeypatch, reply=cut_second, max_out=48000)
    assert json.loads(calls[2])['max_tokens'] == 48000

def gone_to_a_person(R):
    run = load(R / 'run.json'); wo = load(R / 'workorder.json')
    return run['figure_passes']['failed']['2'], [d for d in wo['deferrals'] if d['what'] == 'Alt text for 30 figures']

@pytest.mark.parametrize('args,kw,why', [
    (('--figure-retry-max-usd', '0.5'), {}, 'could cost more than the limit per AI call'),
    (('--figure-retry-book-max-usd', '0.9'), {}, 'could cost more than the limit per PDF'),
    (('--max-tokens', '10000'), {'ctx': 60000}, 'wouldn\'t fit what the AI model can take')])    # the first request (about 48,000) and the figure request (44,000) fit
def test_a_retry_that_cannot_be_sent_goes_to_a_person_and_says_why(book, tmp_path, monkeypatch, args, kw, why):
    R = tmp_path / 'r'; calls, code = live(book[1], R, monkeypatch, *args, reply=cut_second, **kw)
    assert code is None and len(calls) == 2
    reason, d = gone_to_a_person(R); assert why in reason and reason.startswith('cut off at 32,000 output tokens; not sent again') and len(d) == 1

def test_a_model_that_cannot_write_more_gets_no_retry(book, tmp_path, monkeypatch):
    R = tmp_path / 'r'; calls, code = live(book[1], R, monkeypatch, '--max-tokens', '32000', reply=cut_second, max_out=32000)
    assert code is None and len(calls) == 2 and 'can\'t write a longer answer' in gone_to_a_person(R)[0]

def test_the_retry_uses_the_real_limits_not_the_estimate_shown(book, tmp_path, monkeypatch):
    bound = ('--max-usd', '0.6', '--book-max-usd', '1.2')             # what Spend binds: under the retry's worst case (about $0.68)
    calls, _ = live(book[1], tmp_path / 'a', monkeypatch, *bound, reply=cut_second)
    assert len(calls) == 2 and 'limit per AI call' in gone_to_a_person(tmp_path / 'a')[0]
    calls, _ = live(book[1], tmp_path / 'b', monkeypatch, *bound, '--figure-retry-max-usd', '2', '--figure-retry-book-max-usd', '5', reply=cut_second)
    assert len(calls) == 3 and load(tmp_path / 'b' / 'run.json')['passes'][1]['outcome'] == 'done'

def test_a_second_cut_off_goes_to_a_person(book, tmp_path, monkeypatch):
    R = tmp_path / 'r'; calls, _ = live(book[1], R, monkeypatch, reply=lambda b, n: stop(b, finish='length', text='x') if n >= 2 else stop(b))
    assert len(calls) == 3 and gone_to_a_person(R)[0] == 'cut off at 32,000 output tokens, then cut off at 64,000 output tokens'
    assert load(R / 'run.json')['figure_passes']['cut_off_retries'][0]['outcome'] == 'failed'

def test_a_429_then_a_cut_off_still_gets_its_doubled_retry(book, tmp_path, monkeypatch):
    def r(b, n):
        if n == 2: return urllib.error.HTTPError('u', 429, 'x', {}, io.BytesIO(b'{"error": {"message": "busy"}}'))
        return stop(b, finish='length', text='x') if n == 3 else stop(b)
    calls, _ = live(book[1], tmp_path / 'r', monkeypatch, reply=r)
    assert [json.loads(c)['max_tokens'] for c in calls] == [48000, 32000, 32000, 64000]

def test_two_charged_calls_are_the_most_a_request_can_cost(book, tmp_path, monkeypatch):
    def r(b, n): return stop(b, cost=0.2, text='no json') if n == 2 else stop(b, cost=0.2, finish='length', text='x') if n == 3 else stop(b)
    R = tmp_path / 'r'; calls, _ = live(book[1], R, monkeypatch, reply=r)
    assert len(calls) == 3 and 'already been charged twice' in gone_to_a_person(R)[0]

def test_a_timeout_on_the_retry_counts_its_own_worst_case_and_is_not_retried(book, tmp_path, monkeypatch):
    R = tmp_path / 'r'; calls, code = live(book[1], R, monkeypatch, reply=lambda b, n: TimeoutError() if n == 3 else cut_second(b, n))
    run = load(R / 'run.json'); c = run['passes'][1]['calls'][-1]
    assert code is None and len(calls) == 3 and c['worst_usd'] > 0.64 and c['max_tokens'] == 64000

def test_a_stop_during_the_retry_counts_the_cut_off_and_the_retry(book, tmp_path, monkeypatch):
    seen = {}; R = tmp_path / 'r'
    def r(b, n):
        if n == 3: seen.update(load(R / 'run.json')['figure_passes'])
        return cut_second(b, n)
    live(book[1], R, monkeypatch, reply=r)
    assert seen['in_flight'] == '2' and seen['in_flight_paid_usd'] == 0.3 and seen['in_flight_cut_off'] is True and 0.64 < seen['in_flight_worst_usd'] < 0.75   # known and unknown apart

def test_the_in_flight_fields_are_gone_once_a_request_is_done(book, tmp_path, monkeypatch):
    R = tmp_path / 'r'; live(book[1], R, monkeypatch, reply=cut_second)
    assert not [k for k in load(R / 'run.json')['figure_passes'] if k.startswith('in_flight')]

# ------------------------------------------------------------------ a reply read again in its own folder (review 04 H1)
PAID_REPLY = {'model': MODEL, 'choices': [{'message': {'content': reply_for([])}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}
def paid_folder(book, tmp_path, name='r'):
    A = small_audit(book, tmp_path, 3); R = tmp_path / name; R.mkdir()
    (R / 'run.json').write_text(json.dumps({'model': MODEL, 'started': '2026-11-08T10:00:00', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost_usd': 0.3}, 'finish_reason': 'stop',
                                            'estimate': {'worst_case_total_usd': 0.67, 'expected': {'usd': 0.31}, 'credit_available_usd': 9.0, 'max_tokens': 48000}}))
    (R / 'response.json').write_text(json.dumps(PAID_REPLY)); (R / 'workorder.json').write_text('{}')
    return A, R

def test_a_reply_read_again_in_its_own_folder_is_still_this_runs_money(book, tmp_path):
    A, R = paid_folder(book, tmp_path); assert decide(A, R, '--response-file', R / 'response.json').returncode == 0
    run = load(R / 'run.json'); assert run['own_reply'] is True and run['response_from'] and run['usage']['cost_usd'] == 0.3
    assert run['estimate']['expected'] == {'usd': 0.31} and run['estimate']['worst_case_total_usd'] == 0.67 and 'credit_available_usd' not in run['estimate']   # as shown; the credit isn't kept stale
    a = C.actual(str(R)); assert a['usd'] == 0.3 and a['reused'] is False
    assert C.after_line(str(R)) == 'AI Cost: $0.30 (expected $0.31, max estimated $0.67)'

def test_it_stays_so_when_read_a_second_time_and_after_the_folder_moved(book, tmp_path):
    A, R = paid_folder(book, tmp_path); decide(A, R, '--response-file', R / 'response.json')
    N = tmp_path / 'moved'; R.rename(N); assert C.actual(str(N))['usd'] == 0.3                                  # stored, not worked out from a path
    assert decide(A, N, '--response-file', N / 'response.json').returncode == 0 and load(N / 'run.json')['own_reply'] is True and C.actual(str(N))['usd'] == 0.3

def test_a_copied_folder_keeps_the_count_on_both_sides(book, tmp_path):
    A, R = paid_folder(book, tmp_path); decide(A, R, '--response-file', R / 'response.json')
    C2 = tmp_path / 'copy'; shutil.copytree(R, C2)
    assert C.actual(str(R))['usd'] == 0.3 and C.actual(str(C2))['usd'] == 0.3
    assert decide(A, C2, '--response-file', C2 / 'response.json').returncode == 0 and load(C2 / 'run.json')['own_reply'] is True
    assert C.actual(str(R))['usd'] == 0.3 and C.actual(str(C2))['usd'] == 0.3

def test_another_runs_response_json_is_not_this_runs_money(book, tmp_path):
    A, R = paid_folder(book, tmp_path); O = tmp_path / 'other'
    assert decide(A, O, '--response-file', R / 'response.json').returncode == 0
    run = load(O / 'run.json'); assert 'own_reply' not in run and run['usage']['cost_usd'] == 0.3                 # the saved reply carries its cost, and it was spent elsewhere
    a = C.actual(str(O)); assert a['usd'] == 0 and a['reused'] is True and C.after_line(str(O)) == 'AI Cost: none (a saved reply was used)'
    assert decide(A, O, '--response-file', O / 'response.json').returncode == 0                                   # its response.json is now "here", but this folder never paid for it
    assert 'own_reply' not in load(O / 'run.json') and C.actual(str(O))['usd'] == 0

def ocr_folder(book, tmp_path):
    """An own paid reply on a book with OCR words: the audit has one word sheet, the run.json the list the reply was written for."""
    from PIL import Image
    src, A0, d = book; A = tmp_path / '_audit_ocr'; shutil.copytree(A0, A)
    Image.new('RGB', (40, 20), 'white').save(A / 'sheet.png')
    d2 = dict(d, figures=d['figures'][:3], ocr_words=[{'id': 1, 'text': 'kaio', 'count': 1, 'pages': [1]}, {'id': 2, 'text': 'maka', 'count': 1, 'pages': [1]}], ocr_word_sheets=[{'ids': [1, 2], 'image': 'sheet.png'}])
    json.dump(d2, open(A / 'digest.json', 'w', encoding='utf-8'), ensure_ascii=False)
    R = tmp_path / 'r'; assert decide(A, R, '--dry-run').returncode == 0
    run = load(R / 'run.json'); run.update(started='2026-11-01T09:00:00', prompt_file='workorder_v8.md', prompt_sha256='first', temperature=0, usage=PAID_REPLY['usage'] | {'cost_usd': 0.3}, finish_reason='stop')
    (R / 'run.json').write_text(json.dumps(run))
    (R / 'response.json').write_text(json.dumps(dict(PAID_REPLY, choices=[{'message': {'content': '```json\n{"ocr_words": {"1": "kaʻio", "2": "maka"}}\n```'}, 'finish_reason': 'stop'}])))
    (R / 'workorder.json').write_text('{}')
    return A, R

def test_a_third_read_keeps_the_ocr_readings_and_the_first_calls_details(book, tmp_path):
    """review 06 M1: reading the folder's own reply again keeps what the first call was, however many times it is read."""
    A, R = ocr_folder(book, tmp_path)
    for i in range(3):
        r = decide(A, R, '--response-file', R / 'response.json'); assert r.returncode == 0, r.stderr
        run = load(R / 'run.json'); oc = run['original_call']
        assert run['own_reply'] is True and run['temperature'] == 0 and (oc['date'], oc['prompt_file'], oc['prompt_sha256'], oc['cost_usd']) == ('2026-11-01T09:00:00', 'workorder_v8.md', 'first', 0.3), i
        assert run['ocr_words']['reply_check'] == 'same list' and load(R / 'workorder.json')['ocr_words'][0]['reads'] == 'kaʻio', i

def test_another_file_over_an_own_folder_takes_nothing_from_it(book, tmp_path):
    A, R = paid_folder(book, tmp_path); decide(A, R, '--response-file', R / 'response.json')
    other = tmp_path / 'other.json'; other.write_text(json.dumps(dict(PAID_REPLY, model='anthropic/other')))
    assert decide(A, R, '--response-file', other).returncode == 0
    run = load(R / 'run.json'); assert run['model'] == 'anthropic/other' and 'own_reply' not in run and 'temperature' not in run and not run.get('original_call')
    assert C.actual(str(R))['usd'] == 0

def test_a_saved_response_with_usage_writes_no_ledger_row(book, tmp_path):
    A = small_audit(book, tmp_path, 3); led = tmp_path / 'led.jsonl'; rp = tmp_path / 'saved.json'; rp.write_text(json.dumps(PAID_REPLY))
    assert decide(A, tmp_path / 'r', '--response-file', rp, COST_HISTORY=led).returncode == 0 and not led.exists()

def test_the_probe_gets_no_retry_and_no_ledger_row(book, tmp_path, monkeypatch):
    led = tmp_path / 'led.jsonl'
    def r(b, n): return stop(b, finish='length', text='x') if n == 3 else stop(b)        # the third call is the probe
    calls, code = live(book[1], tmp_path / 'r', monkeypatch, '--figure-probe', '5', reply=r, ledger=led)
    assert code is None and len(calls) == 3 and [l['pass'] for l in map(json.loads, open(led))] == ['1', '2']

def saved(R, tmp_path, name='reply.txt'):
    """R's reply as a saved one (what batch_api.sh FROM= writes)."""
    rp = tmp_path / name; side = load(R / 'passes.json'); rp.write_text((R / 'reply.txt').read_text())
    (tmp_path / (name + '.meta.json')).write_text(json.dumps({'model': MODEL, 'figure_passes': {'requests': 1, 'fingerprint': F.side_fingerprint(side)}}))
    (tmp_path / (name + '.passes.json')).write_text(json.dumps(side))
    return rp

def test_a_replay_of_a_retried_run_uses_its_final_answer_free(book, tmp_path):
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch(); R = tmp_path / 'r'
    try: live(book[1], R, mp, reply=cut_second)
    finally: mp.undo()
    R2 = tmp_path / 'r2'; r = decide(book[1], R2, '--response-file', saved(R, tmp_path)); assert r.returncode == 0, r.stderr
    run = load(R2 / 'run.json'); wo = load(R2 / 'workorder.json')
    assert run['figure_passes']['state'] == 'merged' and 'cut_off_retries' not in run['figure_passes'] and sum(a['alt'].startswith('Alt from') for a in wo['alt']) >= 30

# ------------------------------------------------------------------ the ledger
def test_a_paid_run_writes_one_row_per_finished_call_and_no_cut_off(book, tmp_path, monkeypatch):
    led = tmp_path / 'led.jsonl'; live(book[1], tmp_path / 'r', monkeypatch, reply=cut_second, ledger=led)
    rows = [json.loads(l) for l in open(led)]
    assert [(r['kind'], r['pass'], r['attempt']) for r in rows] == [('workorder', '1', 1), ('figure', '2', 2)]
    assert all(H._good(r) and r['model'] == MODEL and r['input_billed'] == 1000 and len(r['book']) == 16 for r in rows)

def test_a_cut_off_work_order_writes_nothing(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); led = tmp_path / 'led.jsonl'
    _, code = live(A, tmp_path / 'r', monkeypatch, reply=lambda b, n: stop(b, finish='length', text='```json\n{'), ledger=led)
    assert 'the next attempt allows 96,000' in str(code) and not led.exists()

def test_a_saved_reply_writes_nothing(book, tmp_path):
    led = tmp_path / 'led.jsonl'; A = small_audit(book, tmp_path, 3); rp = tmp_path / 'reply.txt'; rp.write_text(reply_for([]))
    assert decide(A, tmp_path / 'r', '--response-file', rp, COST_HISTORY=led).returncode == 0 and not led.exists()

def test_a_ledger_that_cannot_be_written_does_not_stop_the_run(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); (tmp_path / 'file').write_text('x')
    _, code = live(A, tmp_path / 'r', monkeypatch, ledger=tmp_path / 'file' / 'led.jsonl'); H._warned = False
    assert code is None and (tmp_path / 'r' / 'workorder.json').exists()

# ------------------------------------------------------------------ the doubling after a work-order cut-off
def attempts(R, *rows):
    R.mkdir(parents=True, exist_ok=True); (R / 'attempts.json').write_text(json.dumps(list(rows)))

CUT = {'cost_usd': 0.5, 'finish_reason': 'length', 'max_tokens': 48000}
@pytest.mark.parametrize('rows,want,book_cap', [
    ([CUT], 96000, 5.0),
    ([CUT, dict(CUT, max_tokens=96000)], 192000, 5.0),
    ([dict(CUT, finish_reason='stop')], 48000, 5.0),                                       # an unusable reply is not a cut-off
    ([dict(CUT, **{'pass': '2'})], 48000, 5.0),                                            # nor a figure request's
    ([{'cost_usd': 0.5, 'finish_reason': 'length'}], 48000, 5.0),                          # no max_tokens on the entry
    ([dict(CUT, **{'pass': '1'})], 96000, 5.0)])
def test_only_a_work_order_cut_off_doubles_the_next_attempt(book, tmp_path, rows, want, book_cap):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, *rows)
    assert decide(A, R, '--dry-run').returncode == 0
    e = load(R / 'run.json')['estimate']; assert e['max_tokens'] == want and e['spent_before_usd'] and e['book_cap_usd'] == book_cap

def test_max_tokens_beats_the_doubling(book, tmp_path):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, CUT)
    decide(A, R, '--dry-run', '--max-tokens', '50000'); assert load(R / 'run.json')['estimate']['max_tokens'] == 50000

def test_the_doubling_is_trimmed_to_the_models_maximum(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, CUT)
    calls, code = live(A, R, monkeypatch, '--dry-run', max_out=64000)
    assert code in (None, 0) and load(R / 'run.json')['estimate']['max_tokens'] == 64000

def test_a_reply_cut_off_at_the_models_maximum_stops(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, dict(CUT, max_tokens=128000))
    calls, code = live(A, R, monkeypatch, max_out=128000)
    assert not calls and 'writes at most 128,000 output tokens, and the previous attempt was already cut off' in str(code)

def test_the_cut_off_line_at_the_models_maximum_promises_nothing_more(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, dict(CUT, max_tokens=64000))
    _, code = live(A, R, monkeypatch, max_out=128000, reply=lambda b, n: stop(b, finish='length', text='```json\n{'))
    assert load(R / 'run.json')['estimate']['max_tokens'] == 128000 and 'Another attempt would be cut off too' in str(code) and 'next attempt allows' not in str(code)

def test_the_doubled_value_either_fits_or_the_run_stops(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, CUT)
    calls, code = live(A, R, monkeypatch, '--max-usd', '0.6')
    assert not calls and 'more than the limit of $0.60 per AI call' in str(code)

def test_a_replay_keeps_its_estimate_as_it_was(book, tmp_path):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, CUT); rp = tmp_path / 'reply.txt'; rp.write_text(reply_for([]))
    assert decide(A, R, '--response-file', rp).returncode == 0
    e = load(R / 'run.json')['estimate']; assert e['max_tokens'] == 48000 and not {'book_cap_usd', 'spent_before_usd', 'expected'} & set(e)

# ------------------------------------------------------------------ limits and refusals
def test_a_one_request_pdf_is_held_to_the_limit_per_pdf(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3)
    calls, code = live(A, tmp_path / 'r', monkeypatch, '--book-max-usd', '0.1')
    assert not calls and "refusing before any call: this PDF could cost up to" in str(code) and 'more than the limit of $0.10 per PDF' in str(code) and 'BOOK_MAX_USD=1' in str(code)

def test_previous_attempts_count_toward_the_limit_per_pdf(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; attempts(R, {'cost_usd': 4.8, 'finish_reason': 'stop'})
    calls, code = live(A, R, monkeypatch)
    assert not calls and '(including $4.80 spent by previous attempts in this folder)' in str(code)

def test_a_bound_estimate_can_be_spent(book, tmp_path, monkeypatch):
    """Idempotence: the app's bound MAX_USD and BOOK_MAX_USD applied to the same request give the same request."""
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    live(A, R, monkeypatch, '--dry-run'); e = load(R / 'run.json')['estimate']
    b = {'m': C.bound(e['worst_case_total_usd'], 2.0)}
    calls, code = live(A, R, monkeypatch, '--max-usd', b['m'], '--book-max-usd', b['m'])
    assert code is None and json.loads(calls[0])['max_tokens'] == 48000

# ------------------------------------------------------------------ the expected figure
def small_with_expected(book, tmp_path, *extra, **kw):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    assert decide(A, R, '--dry-run', *extra, **kw).returncode == 0
    return A, R

def test_the_estimate_stores_the_expected_figure_and_the_terminal_prints_both(book, tmp_path):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'; r = decide(A, R, '--dry-run')
    x = load(R / 'run.json')['estimate']['expected']; assert x['usd'] > 0 and x['low'] <= x['usd'] <= x['high'] and x['basis']['calls'] == 80
    assert 'Expected Cost: $' in r.stdout and '(usually $' in r.stdout and 'Max Estimated Cost: $' in r.stdout and 'Limits: $2.00 per AI call, $5.00 per PDF' in r.stdout

def stored(R, value, **changes):
    run = load(R / 'run.json'); run['estimate']['expected'] = value; run.update(changes); (R / 'run.json').write_text(json.dumps(run))

KEPT = {'usd': 0.123, 'low': 0.1, 'high': 0.2, 'basis': {'calls': 80, 'books': 9}}
def test_a_figure_already_shown_is_carried_forward(book, tmp_path):
    A, R = small_with_expected(book, tmp_path); stored(R, KEPT)
    decide(A, R, '--dry-run'); assert load(R / 'run.json')['estimate']['expected'] == KEPT

def test_a_changed_request_gets_a_new_figure(book, tmp_path):
    A, R = small_with_expected(book, tmp_path); stored(R, KEPT, prompt_sha256='different')
    decide(A, R, '--dry-run'); assert load(R / 'run.json')['estimate']['expected']['usd'] != 0.123

def test_not_available_is_worked_out_again(book, tmp_path):
    A, R = small_with_expected(book, tmp_path); stored(R, {'none': 'too_few'})
    decide(A, R, '--dry-run'); assert load(R / 'run.json')['estimate']['expected'].get('usd')

def test_a_cut_off_in_the_folder_gives_not_available_even_if_a_figure_was_shown(book, tmp_path):
    A, R = small_with_expected(book, tmp_path); stored(R, KEPT); attempts(R, CUT)
    r = decide(A, R, '--dry-run'); assert load(R / 'run.json')['estimate']['expected'] == {'none': 'cut_off'} and 'Expected Cost: Not Available Yet (' in r.stdout

def test_a_pdf_past_100_images_has_no_figure_yet(book, tmp_path):
    R = tmp_path / 'r'; r = decide(book[1], R, '--dry-run', COST_HISTORY=tmp_path / 'none.jsonl')      # the seed alone
    assert load(R / 'run.json')['estimate']['expected'] == {'none': 'too_few', 'kind': 'figure', 'calls': 5, 'books': 1}
    assert 'needs 12 from 6' in r.stdout and 'Max Estimated Cost: $' in r.stdout and 'for 2 AI requests' in r.stdout

def test_a_model_other_than_claude_says_so(book, tmp_path, monkeypatch):
    A = small_audit(book, tmp_path, 3); R = tmp_path / 'r'
    from contextlib import redirect_stdout
    buf = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', buf)
    calls = []
    monkeypatch.setattr(urllib.request, 'urlopen', lambda req, timeout=None: Resp({'data': [{'id': 'openai/x', 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}, 'architecture': {'input_modalities': ['text', 'image']},
                                                                                              'context_length': 1000000, 'top_provider': {'max_completion_tokens': 128000}, 'supported_parameters': []}]})
                        if str(getattr(req, 'full_url', req)).endswith('/models') else Resp({'data': {'limit_remaining': 100}}))
    for k, v in env().items(): monkeypatch.setenv(k, v)
    monkeypatch.setattr(sys, 'argv', ['decide.py', str(A), str(R), '--model', 'openai/x', '--dry-run']); monkeypatch.chdir(HERE)
    try: runpy.run_path(os.path.join(HERE, 'decide.py'), run_name='__main__')
    except SystemExit: pass
    out = buf.getvalue()
    assert 'Expected Cost: Not Available Yet (0 past calls of this kind, from 0 PDFs; needs 12 from 6)' in out
    assert 'Max Estimated Cost: about $' in out and 'approximate and not a limit: the dollar limits apply to Claude models only' in out
