"""tools/lang_test.py send and probe (#142): any model on the live list, one max_tokens figure read by the body and the cap,
a reply with no cost counted at its worst case (review 04 M2), the reasoning setting recorded, and the probe's made-up text
sent under data_collection deny. No network: prices() and the POST are stubbed. Made-up words only."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import pytest
import lang_test as T  # noqa: E402

MODEL = 'example/made-up-model-1'


def _setup(tmp_path, monkeypatch, replies, n_req=3, items=2):
    reqs = []
    for k in range(n_req):
        its = [{'id': f'r{k}i{j}', 'form': f'velun{k}{j}', 'class': ['unknown'], 'italic': False, 'places': 1, 's': [1]} for j in range(items)]
        reqs.append({'book': 'made-up', 'request': {'book': {'title': 'Made up', 'language': 'en'},
                                                    'snippets': [{'s': 1, 'text': ' '.join(f'[[{i["id"]}|{i["form"]}]]' for i in its)}], 'items': its}})
    (tmp_path / 'requests').mkdir()
    (tmp_path / 'requests' / 'W10.json').write_text(json.dumps(reqs), encoding='utf-8')
    (tmp_path / 'prompt.md').write_text('A made-up prompt.', encoding='utf-8')
    monkeypatch.setattr(T, 'api_key', lambda: 'k')
    def prices():
        T.SUPPORTED[MODEL] = ['max_tokens', 'reasoning']
        return {MODEL: (1e-6, 1e-5)}, 'live'
    monkeypatch.setattr(T, 'prices', prices)
    sent = []
    def post(key, b):
        sent.append(b)
        return replies.pop(0) if replies else ({'usage': {'cost': 0.001}, 'provider': 'P', 'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}, None)
    monkeypatch.setattr(T, '_post', post)
    return sent


def test_any_model_on_the_live_list_is_sent_and_max_tokens_is_one_figure(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [])
    T.send(str(tmp_path), MODEL, 1, 'W10', 5.0, str(tmp_path / 'prompt.md'), max_tokens=12000)
    assert len(sent) == 3 and all(b['max_tokens'] == 12000 for b in sent)
    assert all(b['provider'] == {'data_collection': 'deny'} for b in sent)
    led = json.load(open(tmp_path / 'spend.json'))
    assert all(c['max_tokens'] == 12000 and c['provider'] == 'P' for c in led['calls'])
    # the worst case recorded is the one the body used: input at 1e-6 plus 12,000 at 1e-5 ($0.12) and a little input
    assert all(0.12 < c['worst'] < 0.13 for c in led['calls'])


def test_max_tokens_never_falls_below_the_allowance(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [], items=30)
    T.send(str(tmp_path), MODEL, 1, 'W10', 5.0, str(tmp_path / 'prompt.md'), max_tokens=100)
    assert all(b['max_tokens'] == T.costs.allowance('language', 30) for b in sent)


def test_a_reply_with_no_cost_counts_at_its_worst_case_and_the_cap_holds(tmp_path, monkeypatch, capsys):
    nocost = ({'provider': 'P', 'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}, None)
    sent = _setup(tmp_path, monkeypatch, [nocost, nocost, nocost])
    # each request's worst case is about $0.12 at 12,000 tokens: a $0.30 cap lets two through, then stops
    with pytest.raises(SystemExit) as e:
        T.send(str(tmp_path), MODEL, 1, 'W10', 0.30, str(tmp_path / 'prompt.md'), max_tokens=12000)
    assert 'stopped before request 3' in str(e.value)
    assert len(sent) == 2
    led = json.load(open(tmp_path / 'spend.json'))
    assert all(c['cost'] is None for c in led['calls']) and sum(T._counted(c) for c in led['calls']) > 0.24


def test_the_summary_counts_replies_with_no_cost(tmp_path, monkeypatch, capsys):
    nocost = ({'provider': 'P', 'choices': [{'finish_reason': 'length', 'message': {'content': ''}}]}, None)
    _setup(tmp_path, monkeypatch, [nocost], n_req=2)
    T.send(str(tmp_path), MODEL, 1, 'W10', 5.0, str(tmp_path / 'prompt.md'))
    out = capsys.readouterr().out
    assert '1 with no cost given (counted at their worst case), 1 cut off' in out


def test_reasoning_effort_is_sent_and_recorded(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [], n_req=1)
    monkeypatch.setattr(T, 'REASONING_EFFORT', 'low'); monkeypatch.setattr(T, 'NO_REASONING', False)
    T.send(str(tmp_path), MODEL, 1, 'W10', 5.0, str(tmp_path / 'prompt.md'))
    assert sent[0]['reasoning'] == {'effort': 'low'}
    assert json.load(open(tmp_path / 'spend.json'))['calls'][0]['reasoning'] == {'effort': 'low'}


def test_only_sends_the_named_requests_again(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [], n_req=4)
    monkeypatch.setattr(T, 'NO_REASONING', True)
    T.send(str(tmp_path), MODEL, 2, 'W10', 5.0, str(tmp_path / 'prompt.md'), only={2, 4})
    assert len(sent) == 2 and all(b['reasoning'] == {'enabled': False} for b in sent)
    assert [c['n'] for c in json.load(open(tmp_path / 'spend.json'))['calls']] == [2, 4]


def test_a_model_not_on_the_list_is_refused(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, [])
    with pytest.raises(SystemExit) as e:
        T.send(str(tmp_path), 'example/not-listed', 1, 'W10', 5.0, str(tmp_path / 'prompt.md'))
    assert 'not on OpenRouter' in str(e.value)


def test_the_probe_sends_made_up_text_under_deny_and_a_refusal_skips_the_model(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch, [(None, 'HTTP 404: No endpoints found matching your data policy')])
    assert T.probe(str(tmp_path), MODEL, 5.0, str(tmp_path / 'prompt.md')) is False
    b = sent[0]
    assert b['provider'] == {'data_collection': 'deny'} and 'velunkarai' in b['messages'][1]['content']
    led = json.load(open(tmp_path / 'spend.json'))
    assert led['calls'][0]['set'] == 'probe' and led['calls'][0]['cost'] is None and led['calls'][0]['worst'] > 0
    ok = ({'usage': {'cost': 0.0001}, 'provider': 'P', 'choices': [{'message': {'content': '{"decisions":[{"id":"p1","form":"velunkarai","lang":null,"confidence":"low","why":"unsure"}]}'}}]}, None)
    sent.clear(); monkeypatch.setattr(T, '_post', lambda k, b: (sent.append(b), ok)[1])
    assert T.probe(str(tmp_path), MODEL, 5.0, str(tmp_path / 'prompt.md')) is True
