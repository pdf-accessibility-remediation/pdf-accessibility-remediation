"""test_aisend.py: lib/aisend.py, the runner the three paid steps after the work order share (#135 (parallel requests)).
A fake sender, no network. Timing is held by events and barriers, never by clock windows (01 §4.9; review 02 H3 and M1):
- with a cap of N, never more than N requests are in flight, and with 1 they run in their order;
- replies finishing in reverse order are stored in request order;
- an interruption (Ctrl+C, or any exception) starts no queued request, waits for no call already sent, hands the requests
  in flight to on_stop and is raised again;
- the Budget's check and reservation are one locked step; a reservation moves to `spent` once;
- a failure is retried once, after 60 s for a 429 and 20 s otherwise; a retry with no room is not sent, and says which limit;
- the Record takes changes from many threads at once and ignores those after an interruption.
"""
import json, threading, _thread, pytest
from lib import aisend

def wait_for(ev, what):
    assert ev.wait(10), f'timed out waiting for {what}'      # a safety net only: the tests never depend on how long

# ------------------------------------------------------------------ the setting
@pytest.mark.parametrize('v,n', [(None, 16), ('', 16), ('1', 1), ('8', 8), (' 3 ', 3), ('0', 1), ('-2', 1), ('sixteen', 16)])
def test_ai_parallel_is_read_as_a_whole_number_of_at_least_one(v, n):
    assert aisend.cap({} if v is None else {'AI_PARALLEL': v}) == n

def test_the_pause_before_a_retry():
    assert aisend.pause(429) == 60 and aisend.pause('429') == 60 and aisend.pause(502) == 20 and aisend.pause('timeout') == 20 and aisend.pause(None) == 20

# ------------------------------------------------------------------ the runner
def test_never_more_than_the_cap_in_flight():
    """More jobs than the cap (a Barrier of N would hang with fewer): each holds until the test has seen the cap reached."""
    cap, n = 3, 8; lock = threading.Lock(); state = {'now': 0, 'peak': 0, 'started': 0}
    full, go = threading.Event(), threading.Event()
    def one(j):
        with lock:
            state['now'] += 1; state['started'] += 1; state['peak'] = max(state['peak'], state['now'])
            if state['now'] == cap: full.set()
        wait_for(go, 'release')
        with lock: state['now'] -= 1
        return j * 10
    out = {}
    t = threading.Thread(target=lambda: out.update(r=aisend.run(range(n), one, cap))); t.start()
    wait_for(full, 'the cap reached')
    with lock: assert state['started'] == cap                 # the fourth can't start while three hold
    go.set(); t.join(10)
    assert out['r'] == [j * 10 for j in range(n)] and state['peak'] == cap and state['started'] == n

def test_a_cap_of_one_runs_the_jobs_in_their_order():
    seen = []
    assert aisend.run(['a', 'b', 'c', 'd'], lambda j: seen.append(j) or j.upper(), 1) == ['A', 'B', 'C', 'D'] and seen == ['a', 'b', 'c', 'd']

def test_replies_finishing_in_reverse_order_are_stored_in_request_order():
    n = 4; go = [threading.Event() for _ in range(n)]; finished = [threading.Event() for _ in range(n)]; done_order = []
    def one(j):
        wait_for(go[j], f'job {j}'); return {'n': j}
    def on_done(j, r):
        done_order.append(j); finished[j].set()
    out = {}
    t = threading.Thread(target=lambda: out.update(r=aisend.run(range(n), one, n, on_done=on_done))); t.start()
    for j in reversed(range(n)):
        go[j].set(); wait_for(finished[j], f'job {j} done')
    t.join(10)
    assert done_order == [3, 2, 1, 0] and out['r'] == [{'n': 0}, {'n': 1}, {'n': 2}, {'n': 3}]

def test_no_jobs():
    assert aisend.run([], lambda j: 1 / 0, 4) == []

def interrupted(cap, n, interrupt):
    """Run n jobs at cap, each blocked on its own Event; interrupt() once `cap` are in flight. Returns what was seen."""
    go = [threading.Event() for _ in range(n)]; started = []; lock = threading.Lock(); full = threading.Event(); stops = []
    def one(j):
        with lock:
            started.append(j)
            if len(started) == cap: full.set()
        wait_for(go[j], f'job {j}')
        return j
    def on_stop(flying): stops.append(sorted(flying))
    def on_done(j, r):
        if r == 0 and interrupt == 'on_done': raise RuntimeError('a record could not be written')
    if interrupt == 'ctrl_c':
        threading.Thread(target=lambda: (wait_for(full, 'the cap reached'), _thread.interrupt_main())).start()
    elif interrupt == 'on_done':
        threading.Thread(target=lambda: (wait_for(full, 'the cap reached'), go[0].set())).start()
    with pytest.raises(KeyboardInterrupt if interrupt == 'ctrl_c' else RuntimeError):
        aisend.run(range(n), one, cap, on_done=on_done, on_stop=on_stop)
    blocked_at_raise = [j for j in range(cap) if not go[j].is_set()]
    for e in go: e.set()                                          # the blocked calls come back now: nothing queued may start
    for t in [t for t in threading.enumerate() if t.name.startswith('aisend-')]: t.join(10)
    return started, stops, blocked_at_raise

def test_ctrl_c_starts_no_queued_request_and_does_not_wait_for_those_sent():
    """review 02 H3: a stop at Ctrl+C (KeyboardInterrupt in the calling thread) while 3 of 7 requests are in flight."""
    started, stops, blocked = interrupted(3, 7, 'ctrl_c')
    assert sorted(started) == [0, 1, 2]                          # nothing queued started, before or after the interruption
    assert blocked == [0, 1, 2]                                  # raised while the three calls were still blocked: no wait
    assert stops == [[0, 1, 2]]                                  # handed over, to be recorded at their worst case

def test_any_exception_stops_the_same_way():
    started, stops, blocked = interrupted(2, 6, 'on_done')       # job 0 finishes, writing its record fails
    assert sorted(started) in ([0, 1], [0, 1, 2])                 # the worker freed by job 0 may take job 2 before the error is seen
    assert stops and 0 not in stops[0] and set(stops[0]) <= {1, 2} and 1 in stops[0]
    assert len(started) <= 3

def test_an_exception_in_a_job_is_raised_after_the_others_are_handed_over():
    go = threading.Event(); flying = []
    def one(j):
        if j == 1: raise ValueError('bad request')
        wait_for(go, 'release'); return j
    with pytest.raises(ValueError):
        aisend.run(range(5), one, 2, on_stop=flying.extend)
    assert flying == [0]; go.set()

# ------------------------------------------------------------------ money
def test_try_reserve_checks_and_reserves_in_one_step():
    """Two retries race for room for one: exactly one gets it, whatever the order."""
    b = aisend.Budget({'step': (1.0, 0.0), 'pdf': (8.0, 7.0)}, {'a': 0.0, 'b': 0.0})
    gate = threading.Barrier(2); got = {}
    def go(k): gate.wait(10); got[k] = b.try_reserve(k, 0.6)
    ts = [threading.Thread(target=go, args=(k,)) for k in 'ab']
    for t in ts: t.start()
    for t in ts: t.join(10)
    assert sorted(ok for ok, _ in got.values()) == [False, True] and b.room() == pytest.approx(0.4)

def test_the_refusal_names_the_limit_without_room():
    b = aisend.Budget({'language step': (6.0, 0.0), 'per-PDF': (8.0, 7.5)}, {'r1': 0.4})
    assert b.try_reserve('r1', 0.4) == (True, None)               # its own reservation is freed for it: 8 − 7.5 − 0 ≥ 0.4
    assert b.try_reserve('r2', 0.2) == (False, 'per-PDF')         # 8 − 7.5 − 0.4 = 0.1 < 0.2
    assert b.try_reserve('r2', 0.2, names=['language step']) == (True, None)
    assert b.try_reserve('r3', 2.0, call_cap=1.0) == (False, 'call')

def test_a_reservation_moves_to_spent_once():
    b = aisend.Budget({'x': (5.0, 1.0)}, {'r': 0.8})
    assert b.room() == pytest.approx(3.2)
    b.settle('r', 0.3); assert b.spent == pytest.approx(0.3) and b.planned == {} and b.room() == pytest.approx(3.7)
    b.settle('r', None); assert b.spent == pytest.approx(0.3)     # a settle with no reservation left adds only its cost
    b.try_reserve('r', 0.8); b.settle('r', 0.8)                   # a timeout: its worst case is spent, the hold released
    assert b.spent == pytest.approx(1.1) and b.planned == {} and b.room() == pytest.approx(2.9)
    assert aisend.Budget({'x': (None, 0)}).room() is None

# ------------------------------------------------------------------ records
def test_the_record_takes_changes_from_many_threads(tmp_path):
    p = tmp_path / 'step.json'; rec = aisend.Record(str(p), {'requests': []})
    gate = threading.Barrier(8)
    def go(k):
        gate.wait(10)
        for i in range(50): rec.change(lambda d: d['requests'].append({'n': k * 100 + i}))
    ts = [threading.Thread(target=go, args=(k,)) for k in range(8)]
    for t in ts: t.start()
    for t in ts: t.join(10)
    d = json.load(open(p))
    assert len(d['requests']) == 400 and len({r['n'] for r in d['requests']}) == 400
    assert not list(tmp_path.glob('*.tmp*'))                      # every write replaced the file whole

def test_after_an_interruption_the_record_ignores_later_changes(tmp_path):
    p = tmp_path / 'step.json'; rec = aisend.Record(str(p), {'in_flight': [{'n': 2, 'worst_usd': 0.5}]})
    rec.close(lambda d: d.update(stopped_in_flight=aisend.stopped(d.pop('in_flight'))))
    rec.change(lambda d: d.update(in_flight=[{'n': 2}]))          # a worker whose call came back after the stop
    d = json.load(open(p))
    assert 'in_flight' not in d and d['stopped_in_flight'][0]['worst_usd'] == 0.5 and d['stopped_in_flight'][0]['stopped'] is True

# ------------------------------------------------------------------ one request with the retry rule
def reply(text='{"a": 1}', cost=0.01, finish='stop'):
    return {'resp': {'choices': [{'message': {'content': text}, 'finish_reason': finish}],
                     'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'cost': cost}}, 'seconds': 1.0}

def call(outs, budget=None, **kw):
    it = iter(outs); waits = []; sent = []
    b = budget or aisend.Budget({'step': (6.0, 0.0), 'per-PDF': (8.0, 0.0)}, {'r': 0.5})
    r = aisend.call(lambda body: sent.append(body) or next(it), {'max_tokens': 10}, 'r', 0.5, b, label='request 1', say=lambda *a: None,
                    sleep=waits.append, **kw)
    return r, b, waits, sent

def test_each_call_records_its_send_and_finish_time():
    import time
    t0 = time.time(); r, _, _, _ = call([{'resp': None, 'code': 502}, reply()])
    a, b = r['calls']
    assert t0 - 0.001 <= a['sent_at'] <= a['finished_at'] <= b['sent_at'] <= b['finished_at'] <= time.time() + 0.001     # rounded to ms

def test_a_429_is_retried_once_after_60_s():
    r, b, waits, sent = call([{'resp': None, 'code': 429, 'message': 'rate limited'}, reply()])
    assert waits == [60] and len(r['calls']) == 2 and r['final']['finish'] == 'stop' and r['cost_usd'] == 0.01 and b.spent == pytest.approx(0.01)
    assert r['calls'][0]['why'] == 'rate limited; sent once more after 60 s' and b.planned == {}

def test_other_failures_wait_20_s_and_are_retried_only_once():
    r, _, waits, _ = call([{'resp': None, 'code': 502}, {'resp': None, 'code': 502}])
    assert waits == [20] and len(r['calls']) == 2 and r['final']['error']['code'] == '502'

def test_an_unreadable_reply_is_retried_and_a_cut_off_is_left_to_the_step():
    r, _, waits, _ = call([reply('not json', cost=0.1), reply()], readable=lambda t: t.startswith('{'))
    assert waits == [20] and len(r['calls']) == 2 and r['cost_usd'] == pytest.approx(0.11)
    r, _, waits, _ = call([reply('{"a"', finish='length', cost=0.2)], readable=lambda t: t.startswith('{"a": 1}'))
    assert waits == [] and len(r['calls']) == 1 and r['final']['finish'] == 'length'

def test_a_timeout_counts_its_worst_case_apart_from_the_known_cost():
    r, b, waits, _ = call([{'resp': None, 'timeout': True}, reply(cost=0.05)])
    assert r['worst_usd'] == 0.5 and r['cost_usd'] == 0.05 and r['calls'][0]['worst_usd'] == 0.5 and b.spent == pytest.approx(0.55)

def test_a_retry_with_no_room_is_not_sent_and_says_which_limit():
    b = aisend.Budget({'language step': (6.0, 0.0), 'per-PDF': (8.0, 7.6)}, {'r': 0.5})   # 8 − 7.6 − 0.3 spent < 0.5
    r, _, waits, sent = call([reply('nope', cost=0.3)], budget=b, readable=lambda t: False)
    assert len(sent) == 1 and waits == [] and r['final']['why'] == 'the reply could not be read; not sent again: the per-PDF limit has no room for it'

def test_on_retry_reports_what_a_stop_must_count():
    seen = []
    call([reply('nope', cost=0.3), reply()], readable=lambda t: t.startswith('{'), on_retry=lambda k, known, worst: seen.append((k, known, worst)))
    assert seen == [('r', pytest.approx(0.3), 0.5)]

@pytest.mark.parametrize('resp', [
    {'choices': [{'message': {'content': ''}, 'finish_reason': 'error'}], 'usage': {'cost': 0}},
    {'choices': [{'message': {'content': '{"a": 1}'}, 'finish_reason': 'stop'}], 'error': {'code': 502, 'message': 'provider failed'}},
    {'choices': [{'message': {'content': ''}, 'finish_reason': 'stop', 'error': {'code': 'server_error', 'message': 'x'}}]}])
def test_a_200_reply_that_reports_an_error_is_a_failure_never_an_answer(resp):
    """round 11: finish_reason "error", or an error object beside or inside the choices: retried once, then recorded as
    failed, with its code."""
    r, _, waits, sent = call([{'resp': resp, 'seconds': 1.0}, {'resp': resp, 'seconds': 1.0}])
    assert len(sent) == 2 and waits == [20] and all('error' in c for c in r['calls']) and 'finish' not in r['final']
    assert aisend.failed_reply(resp) is not None and aisend.failed_reply(reply()['resp']) is None
