"""test_probe_cap.py: tools/probe_cap.py (#135 (parallel requests): how many requests at once before OpenRouter refuses)
against a fake server, no network: each wave goes out at once, the next only after it finished; it stops at the first
429, records every request, and keeps to its limit. No book text in any request."""
import io, json, os, sys, threading, urllib.request, urllib.error
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools')); sys.path.insert(0, HERE)
import probe_cap  # noqa: E402

class Resp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False

def fake(sent, refuse_from=None, hold=()):
    """hold: the running totals at which a wave is complete (3, 8 for waves of 3 and 5): each call waits until its whole
    wave has arrived, so the peak shows a wave going out at once (a condition, never a clock)."""
    cv = threading.Condition()
    def urlopen(rq, timeout=None):
        url = rq.full_url if hasattr(rq, 'full_url') else rq
        if url.endswith('/models'): return Resp(json.dumps({'data': [{'id': probe_cap.MODEL, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}}]}).encode())
        with cv:
            sent.append(json.loads(rq.data)); k = len(sent); cv.notify_all()
            edge = next((h for h in hold if h >= k), None)
            if edge is not None: assert cv.wait_for(lambda: len(sent) >= edge, timeout=10), 'the wave never arrived whole'

        if refuse_from and k >= refuse_from: raise urllib.error.HTTPError(url, 429, 'busy', {}, io.BytesIO(b'{"error": {"message": "rate limited"}}'))
        return Resp(json.dumps({'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}],
                                'usage': {'prompt_tokens': 12, 'completion_tokens': 2, 'cost': 0.0001}}).encode())
    return urlopen

def go(tmp_path, monkeypatch, *args, sent=None, **kw):
    sent = [] if sent is None else sent
    monkeypatch.setattr(urllib.request, 'urlopen', fake(sent, **kw)); monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
    out = tmp_path / 'probe'
    monkeypatch.setattr(sys, 'argv', ['probe_cap.py', '--out', str(out), '--yes', *args]); probe_cap.main()
    return sent, json.load(open(out / 'summary.json')), json.load(open(out / 'calls.json'))

def test_each_wave_goes_out_whole_and_every_request_is_recorded(tmp_path, monkeypatch):
    sent, s, calls = go(tmp_path, monkeypatch, '--waves', '3,5', hold=(3, 8))
    assert len(sent) == 8 and [w['requests'] for w in s['waves']] == [3, 5] and [w['peak_in_flight'] for w in s['waves']] == [3, 5]
    assert s['stopped'] is None and s['cost_usd'] == pytest.approx(0.0008) and len(calls) == 8
    assert all(c['status'] == 200 and c['finished'] >= c['sent'] for c in calls) and [c['wave'] for c in calls].count(2) == 5
    b = sent[0]
    assert b['provider'] == {'data_collection': 'deny'} and b['max_tokens'] == 20 and b['messages'] == [{'role': 'user', 'content': probe_cap.PROMPT}]

def test_it_stops_at_the_first_429_and_sends_no_next_wave(tmp_path, monkeypatch):
    sent, s, calls = go(tmp_path, monkeypatch, '--waves', '3,5,7', refuse_from=6)
    assert len(sent) == 8 and len(s['waves']) == 2 and s['waves'][1]['status_429'] == 3 and 'no next wave' in s['stopped']
    assert sum(1 for c in calls if c['status'] == 429) == 3                      # never retried

def test_a_wave_past_the_limit_is_not_sent(tmp_path, monkeypatch):
    sent, s, _ = go(tmp_path, monkeypatch, '--waves', '3,500', '--max-usd', '0.01')
    assert len(sent) == 3 and 'could pass the $0.01 limit' in s['stopped']

def test_the_dry_run_sends_nothing(monkeypatch, capsys):
    sent = []; monkeypatch.setattr(urllib.request, 'urlopen', fake(sent))
    monkeypatch.setattr(sys, 'argv', ['probe_cap.py', '--dry-run']); probe_cap.main()
    out = capsys.readouterr().out
    assert sent == [] and 'in all: 350 requests' in out
