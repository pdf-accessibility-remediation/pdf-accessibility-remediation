"""test_figure_requests_restart.py: run_api.sh on a folder whose figure requests did not all finish (issue #63; 04 cut 3, C3, C5).

    python -m pytest tests/test_figure_requests_restart.py -q

- A run stopped while its figure requests were being sent: every request it paid for is logged (the one in flight with
  its charge unknown), its state is removed, and the run starts over (here: ESTIMATE=1, so it stops at the new estimate).
- A run whose requests all finished and whose apply or report failed: its work order is applied with no new call, and
  its own calls stay this run's spending (not a replay: no response_from).
- A first request that was complete but unreadable, in a book planned with figure requests, is not re-read as a replay
  (that would leave the figure requests unsent): its cost is logged and the run starts over.
Synthetic book, network blocked, dummy key: nothing is sent.
"""
import json, shutil
from test_figure_requests_run import book, run_api   # noqa: F401  (book is a fixture)

def stopped_folder(book, tmp_path, state):
    R = tmp_path / 'r'; shutil.copytree(book[1], R / '_audit')
    run = {'started': '2026-11-03T10:00:00', 'usage': {'cost_usd': 0.9}, 'finish_reason': 'stop', 'estimate': {'passes': [{}, {}]},
           'passes': [{'pass': '1', 'usage': {'cost_usd': 0.5}, 'finish_reason': 'stop'},
                      {'pass': '2', 'usage': {'cost_usd': 0.4}, 'calls': [{'finish_reason': 'stop'}]}],
           'figure_passes': {'requests': 2, 'state': state, **({'in_flight': '3'} if state == 'calling' else {})}}
    (R / 'run.json').write_text(json.dumps(run)); (R / 'response.json').write_text('{}')
    return R

def test_a_run_stopped_during_its_figure_requests_logs_every_cost_and_starts_over(book, tmp_path):
    R = stopped_folder(book, tmp_path, 'calling'); (R / 'passes.json').write_text('{}')
    r = run_api(book[0], R, ESTIMATE=1)
    assert 'was stopped while its figure requests were being sent: $0.900' in r.stdout, r.stdout + r.stderr
    att = json.load(open(R / 'attempts.json'))
    assert [(a['pass'], a['cost_usd']) for a in att] == [('1', 0.5), ('2', 0.4), ('3', None)] and all(a['stopped'] for a in att)
    assert not (R / 'passes.json').exists()
    new = json.load(open(R / 'run.json'))                                    # the new estimate: a fresh run, not a replay
    assert new.get('response_from') is None and new['estimate']['spent_before_usd'] == 0.9   # the book cap counts what was spent

def test_a_run_whose_requests_all_finished_is_applied_with_no_new_call(book, tmp_path):
    R = stopped_folder(book, tmp_path, 'merged'); (R / 'workorder.json').write_text(json.dumps({'schema': 'workorder/0.2'}))
    r = run_api(book[0], R)
    assert 'applying its work order, no new API call' in r.stdout, r.stdout + r.stderr
    assert '2/5' not in r.stdout and '3/5' not in r.stdout                   # decide.py was never started
    run = json.load(open(R / 'record.json'))['run'] if (R / 'record.json').exists() else json.load(open(R / 'run.json'))
    assert run.get('response_from') is None and run['usage']['cost_usd'] == 0.9 and len(run['passes']) == 2

def test_an_unreadable_first_reply_of_a_planned_book_is_not_replayed(book, tmp_path):
    R = tmp_path / 'r'; shutil.copytree(book[1], R / '_audit')
    (R / 'run.json').write_text(json.dumps({'started': '2026-11-03T10:00:00', 'usage': {'cost_usd': 0.5}, 'finish_reason': 'stop',
                                            'estimate': {'passes': [{}, {}]}, 'parse_error': 'no JSON object in the reply'}))
    (R / 'response.json').write_text('{}')
    r = run_api(book[0], R, ESTIMATE=1)
    assert 'previous attempt logged: $0.500' in r.stdout, r.stdout + r.stderr
    assert 'reading it again' not in r.stdout

def test_a_charge_not_known_counts_its_worst_case_toward_the_book_cap(book, tmp_path):
    """06 M1: the request in flight and a timed-out call are logged with their worst case, and the next estimate counts it."""
    R = stopped_folder(book, tmp_path, 'calling'); run = json.load(open(R / 'run.json'))
    run['figure_passes']['in_flight_worst_usd'] = 0.47
    run['passes'][1]['calls'] = [{'error': {'code': 'timeout'}, 'worst_usd': 0.45}, {'finish_reason': 'stop'}]
    (R / 'run.json').write_text(json.dumps(run))
    r = run_api(book[0], R, ESTIMATE=1)
    assert r.returncode == 0, r.stdout + r.stderr
    att = {a['pass']: a for a in json.load(open(R / 'attempts.json'))}
    assert att['2']['worst_usd'] == 0.45 and att['3']['worst_usd'] == 0.47 and att['3']['cost_usd'] is None and 'worst_usd' not in att['1']
    assert json.load(open(R / 'run.json'))['estimate']['spent_before_usd'] == 1.82   # 0.5 + 0.4 known, 0.45 + 0.47 not known

def test_a_stop_during_the_doubled_retry_keeps_the_paid_cut_off(book, tmp_path):
    """review 04 M1: the cut-off's known cost and the retry's unknown charge are two rows. The limit counts both, the cost line
    the known one, and the folder remembers the cut-off without doubling the work order."""
    from lib import costs
    R = stopped_folder(book, tmp_path, 'calling'); run = json.load(open(R / 'run.json'))
    run['figure_passes'].update(in_flight_paid_usd=0.25, in_flight_worst_usd=1.10, in_flight_cut_off=True)
    (R / 'run.json').write_text(json.dumps(run))
    r = run_api(book[0], R, ESTIMATE=1); assert r.returncode == 0, r.stdout + r.stderr
    att = json.load(open(R / 'attempts.json')); rows = [a for a in att if a['pass'] == '3']
    assert [(a['cost_usd'], a.get('worst_usd'), a.get('finish_reason')) for a in rows] == [(0.25, None, 'length'), (None, 1.1, None)] and all('max_tokens' not in a for a in rows)
    e = json.load(open(R / 'run.json'))['estimate']
    assert e['spent_before_usd'] == 2.25 and e['max_tokens'] == 48000 and e['expected'] == {'none': 'cut_off'}     # 0.9 + 0.25 + 1.10; a figure request's cut-off doesn't double the work order
    assert costs.actual(str(R))['usd'] == 1.15

def test_a_finished_request_with_a_cut_off_call_is_logged_as_cut_off(book, tmp_path):
    R = stopped_folder(book, tmp_path, 'calling'); run = json.load(open(R / 'run.json'))
    run['passes'][1]['calls'] = [{'finish_reason': 'length'}, {'finish_reason': 'stop', 'doubled': True}]
    (R / 'run.json').write_text(json.dumps(run))
    assert run_api(book[0], R, ESTIMATE=1).returncode == 0
    assert {a['pass']: a.get('finish_reason') for a in json.load(open(R / 'attempts.json'))}['2'] == 'length'
    assert json.load(open(R / 'run.json'))['estimate']['expected'] == {'none': 'cut_off'}

def test_a_stop_between_workorder_and_run_json_is_not_replayed_as_one_reply(book, tmp_path):
    """06 L1: workorder.json written, run.json still "calling": every cost is logged and the run starts over."""
    R = stopped_folder(book, tmp_path, 'calling'); (R / 'workorder.json').write_text('{}')
    r = run_api(book[0], R, ESTIMATE=1)
    assert 'was stopped while its figure requests were being sent' in r.stdout, r.stdout + r.stderr
    assert 'reply was complete' not in r.stdout and not (R / 'workorder.json').exists()   # nor found by a later rerun
    assert json.load(open(R / 'run.json')).get('response_from') is None
