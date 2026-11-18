"""test_ladder.py: tools/ladder.py (#135 (parallel requests): requests out at once across several PDFs). No network, no
model: a fake language step (a small script standing in for name_languages.py) writes each book's language_run.json
with synthetic request times. Checks: every book of a level starts at once; the peak is counted across processes from
the requests' own times; the stop rules (a 429, a slower median, the credit) hold the next level back; the dry run."""
import json, os, sys, textwrap, time
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import ladder  # noqa: E402

FAKE = textwrap.dedent('''
    import json, os, sys, time
    audit, run = sys.argv[1], sys.argv[2]
    spec = json.load(open(os.path.join(run, 'spec.json')))
    t0 = time.time(); reqs = []
    for i, (start, secs, err) in enumerate(spec['requests'], 1):
        x = {'n': i, 'sent_at': round(t0 + start, 3), 'finished_at': round(t0 + start + secs, 3), 'cost_usd': 0 if err else 0.1, 'finish': None if err else 'stop'}
        if err: x['error'] = {'code': err, 'message': 'x'}; x['calls'] = [{'attempt': 1, 'sent_at': x['sent_at'], 'finished_at': x['finished_at'], 'error': {'code': err}}]
        reqs.append(x)
    open(os.path.join(run, 'started.txt'), 'w').write(str(t0))
    json.dump({'requests': reqs, 'cost_usd': round(sum(r['cost_usd'] for r in reqs), 6)}, open(os.path.join(run, 'language_run.json'), 'w'))
''')

def book(tmp_path, name, requests, worst=1.0):
    R = tmp_path / name; (R / '_audit').mkdir(parents=True)
    (R / 'spec.json').write_text(json.dumps({'requests': requests}))
    (R / 'language_estimate.json').write_text(json.dumps({'to_send': len(requests), 'sent': 100 * len(requests), 'worst_case_usd': worst}))
    return {'name': name, 'run': str(R), 'pdf': 'x.pdf', 'env': {'AI_PARALLEL': str(len(requests))}}

def go(tmp_path, plan, credit=50.0):
    fake = tmp_path / 'fake.py'; fake.write_text(FAKE)
    out = tmp_path / 'out'
    ladder.run(plan, str(out), f'{sys.executable} {fake}', True, credit_fn=lambda: credit)
    return json.load(open(out / 'summary.json'))

def test_the_peak_is_counted_across_the_books_from_their_times(tmp_path):
    a = book(tmp_path, 'a', [(0, 10, None), (0, 10, None), (5, 10, None)])       # 3 out at 5–10 s
    b = book(tmp_path, 'b', [(1, 10, None), (20, 1, None)])                       # 1 more at 5–10 s
    s = go(tmp_path, {'reference_median_s': 10, 'levels': [{'name': 'level 1', 'books': [a, b]}]})
    m = s['levels'][0]['measured']
    assert s['stopped'] is None and m['calls'] == 5 and m['peak_per_book'] == {'a': 3, 'b': 1}
    assert m['status_429'] == 0 and m['failures'] == 0 and m['median_seconds'] == 10 and m['cost_usd'] == pytest.approx(0.5)
    starts = [float(open(os.path.join(x['run'], 'started.txt')).read()) for x in (a, b)]
    assert abs(starts[0] - starts[1]) < 30                                         # both books started together (a level is one wave)

def test_peak_spans_processes(tmp_path):
    a = book(tmp_path, 'a', [(0, 10, None), (0, 10, None)]); b = book(tmp_path, 'b', [(0, 10, None), (0, 10, None)])
    m = go(tmp_path, {'levels': [{'name': 'level 1', 'books': [a, b]}]})['levels'][0]['measured']
    assert m['peak_in_flight'] == 4                     # the two processes' 10 s requests overlap (they start well within 10 s)

def test_a_429_stops_the_next_level(tmp_path):
    a = book(tmp_path, 'a', [(0, 1, None), (0, 1, '429')]); b = book(tmp_path, 'b', [(0, 1, None)])
    s = go(tmp_path, {'levels': [{'name': 'level 1', 'books': [a]}, {'name': 'level 2', 'books': [b]}]})
    assert len(s['levels']) == 1 and s['levels'][0]['measured']['status_429'] == 1 and '429s' in s['stopped']
    assert not os.path.exists(os.path.join(b['run'], 'language_run.json'))

def test_a_slower_median_stops_the_next_level(tmp_path):
    a = book(tmp_path, 'a', [(0, 13, None)]); b = book(tmp_path, 'b', [(0, 1, None)])
    s = go(tmp_path, {'reference_median_s': 10, 'levels': [{'name': 'level 1', 'books': [a]}, {'name': 'level 2', 'books': [b]}]})
    assert len(s['levels']) == 1 and 'more than 20% above 10 s' in s['stopped']

def test_a_level_that_does_not_fit_the_credit_is_not_run(tmp_path):
    a = book(tmp_path, 'a', [(0, 1, None)], worst=60.0)
    s = go(tmp_path, {'levels': [{'name': 'level 1', 'books': [a]}]}, credit=44.31)
    assert s['levels'] == [] and "doesn't fit the $44.31 credit left" in s['stopped']

def test_the_dry_run_starts_nothing(tmp_path, capsys):
    a = book(tmp_path, 'a', [(0, 1, None)] * 3, worst=2.5)
    e, w = ladder.dry_run({'levels': [{'name': 'level 1', 'books': [a]}]}, 44.31)
    out = capsys.readouterr().out
    assert (e, w) == (pytest.approx(0.33), 2.5) and '3 requests at once at most' in out and 'credit left $44.31' in out
    assert not os.path.exists(os.path.join(a['run'], 'language_run.json'))

def test_never_over_an_earlier_run(tmp_path):
    (tmp_path / 'out').mkdir(); (tmp_path / 'out' / 'summary.json').write_text('{}')
    with pytest.raises(SystemExit): ladder.run({'levels': []}, str(tmp_path / 'out'), 'x', True, credit_fn=lambda: 1)
