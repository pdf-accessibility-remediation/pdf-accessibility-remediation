"""test_origin.py: the AI call behind a run's work order (lib/origin.py; sponsor checklist 11.5, Patrick 2026-11-01): a real
call, a record from 2026-10-03 with only run.usage.cost_usd, a replay carrying original_call, a replay of a replay, a REPLY=
whose only trace is a record beside the reply, and a hand-written reply ("not recorded"). Synthetic records; no model.

    python -m pytest tests/test_origin.py -q
"""
import os, json
from lib import origin

def real(cost=0.255874, total=True, started='2026-10-26T00:30:47'):
    r = {'raw_reply': 'THE REPLY', 'document': {'pages': 437},
         'run': {'model': 'anthropic/claude-sonnet-5.5', 'prompt_file': 'workorder_v8.md', 'prompt_sha256': '4555d20a2fa08a40',
                 'started': started, 'response_from': None, 'usage': {'cost_usd': cost}}}
    if total: r['cost_total_usd'] = cost
    return r

def replay(**run):
    return {'raw_reply': 'THE REPLY', 'cost_total_usd': 0, 'document': {'pages': 437},
            'run': {'model': 'anthropic/claude-sonnet-5.5', 'prompt_file': 'workorder_v9.md', 'started': '2026-11-01T14:00:00',
                    'usage': {'cost_usd': None}, **run}}

def test_a_real_call_is_its_own_origin():
    oc = origin.of_record(real())
    assert oc == {'cost_usd': 0.255874, 'model': 'anthropic/claude-sonnet-5.5', 'prompt_file': 'workorder_v8.md',
                  'prompt_sha256': '4555d20a2fa08a40', 'date': '2026-10-26T00:30:47'}
    ai = origin.summary(real())
    assert ai['cost_per_page_usd'] == round(0.255874 / 437, 6) and ai['reused'] is False
    assert origin.words(ai) == ('$0.256 ($0.0006 per page)', 'anthropic/claude-sonnet-5.5 · Instructions: workorder_v8')

def test_a_record_from_2026_10_03_has_only_usage():
    assert origin.of_record(real(cost=0.31, total=False))['cost_usd'] == 0.31

def test_a_replay_carries_the_original_call():
    oc = origin.of_record(real())
    r = replay(response_from='/tmp/gone.reply.txt', original_call=oc)
    assert origin.of_record(r) == oc                                          # never the replay's own $0 or today's prompt
    ai = origin.summary(r)
    assert ai['reused'] and ai['prompt_file'] == 'workorder_v8.md'
    assert origin.words(ai)[0] == '$0.256 ($0.0006 per page), from the original AI request on October 26, 2026'

def test_a_replay_of_a_replay_still_names_the_first_call(tmp_path):
    first = real()
    second = replay(response_from=str(tmp_path / 'a.reply.txt'), original_call=origin.of_record(first))
    meta = origin.carried(second)                                             # what batch_api.sh FROM= writes beside the reply
    assert meta == {'original_call': origin.of_record(first)}
    p = tmp_path / 'b.reply.txt'; p.write_text('THE REPLY'); (tmp_path / 'b.reply.txt.meta.json').write_text(json.dumps(meta))
    third = replay(response_from=str(p))                                      # a record made before decide.py copied it
    assert origin.of_record(third)['cost_usd'] == 0.255874

def test_a_reply_whose_only_trace_is_a_record_beside_it(tmp_path):
    (tmp_path / 'paid1').mkdir(); (tmp_path / 'paid1' / 'record.json').write_text(json.dumps(real()))
    other = real(); other['raw_reply'] = 'ANOTHER REPLY'; other['cost_total_usd'] = 9.0
    (tmp_path / 'other').mkdir(); (tmp_path / 'other' / 'record.json').write_text(json.dumps(other))
    p = tmp_path / 'reply.txt'; p.write_text('THE REPLY')
    (tmp_path / 'reply.txt.meta.json').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5'}))   # an older meta: no cost
    r = replay(response_from=os.path.relpath(p, tmp_path / 'pipeline'))      # written relative to pipeline/, as run_api.sh does
    assert origin.of_record(r, here=str(tmp_path / 'pipeline'))['cost_usd'] == 0.255874   # only the same reply text counts

def test_a_hand_written_reply_is_not_recorded(tmp_path):
    p = tmp_path / 'minimal.reply.txt'; p.write_text('{"schema": "workorder"}')
    r = replay(response_from=str(p)); r['raw_reply'] = '{"schema": "workorder"}'
    assert origin.of_record(r) is None and origin.carried(r) == {}
    ai = origin.summary(r)
    assert ai['cost_usd'] is None and ai['cost_per_page_usd'] is None
    assert origin.words(ai) == ('not recorded', 'anthropic/claude-sonnet-5.5 · Instructions: not recorded')   # the model is the reply's own
    assert origin.summary(dict(r, ai_call={'cost_usd': 1.0})) == {'cost_usd': 1.0}   # a stored ai_call is read as written
