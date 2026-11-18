"""test_cap_sweep.py: tools/cap_sweep.py (#135 (parallel requests): the cap sweep) on synthetic saved requests, against a
fake OpenRouter (no network, no book content). The dry run sends nothing and prints the amounts; a run sends each saved
file byte for byte, retries a 429 once after its pause, records every call, and reads the replies with today's parse.
"""
import io, json, os, sys, urllib.request, urllib.error
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools')); sys.path.insert(0, HERE)
import cap_sweep  # noqa: E402
from lib import langreq  # noqa: E402
MODEL = 'anthropic/claude-sonnet-5.5'

def folder(tmp_path, name='book', deny=True):
    F = tmp_path / name; (F / 'language_requests').mkdir(parents=True)
    for n, (form, printed) in enumerate([('Kenpo ban', 'Kenpō-ban:'), ('Onjoji', 'Onjōji')], 1):
        req = {'book': {'title': 'T', 'language': 'en'}, 'snippets': [{'s': 1, 'text': f'see [[a{n}|{printed}]] here'}],
               'items': [{'id': f'a{n}', 'form': form, 'class': ['latin'], 'italic': False, 'places': 1}]}
        body = {'model': MODEL, 'max_tokens': 1000, 'messages': [{'role': 'system', 'content': 'prompt ' * 50}, {'role': 'user', 'content': langreq.user_text(req)}],
                'provider': {'data_collection': 'deny'} if deny else {}, 'usage': {'include': True}}
        (F / 'language_requests' / f'{n:03d}.request.json').write_text(json.dumps(body, ensure_ascii=False))
    (F / 'record.json').write_text(json.dumps({'language_run': {'model': MODEL, 'cost_usd': 0.02, 'estimate': {'price_per_million': [2.0, 10.0]},
                                                                'requests': [{'n': 1, 'seconds': 5.0}, {'n': 2, 'seconds': 6.0}]}}))
    return F

class Resp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False

def fake(sent, first_429=True):
    def urlopen(rq, timeout=None):
        url = rq.full_url if hasattr(rq, 'full_url') else rq
        if url.endswith('/models'): return Resp(json.dumps({'data': [{'id': MODEL, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}}]}).encode())
        sent.append(rq.data)
        if first_429 and len(sent) == 1: raise urllib.error.HTTPError(url, 429, 'busy', {}, io.BytesIO(b'{"error": {"message": "rate limited"}}'))
        req = json.loads(json.loads(rq.data)['messages'][1]['content']); it = req['items'][0]
        echo = 'Kenpō-ban' if it['form'] == 'Kenpo ban' else 'Onjoji.'    # a marked text without its colon; the form with a stop
        dec = {'id': it['id'], 'form': echo, 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}
        return Resp(json.dumps({'choices': [{'message': {'content': json.dumps({'decisions': [dec]})}, 'finish_reason': 'stop'}],
                                'usage': {'prompt_tokens': 300, 'completion_tokens': 40, 'cost': 0.01}}).encode())
    return urlopen

def test_the_dry_run_sends_nothing_and_prints_the_amounts(tmp_path, monkeypatch, capsys):
    F = folder(tmp_path); sent = []
    monkeypatch.setattr(urllib.request, 'urlopen', fake(sent))
    cap_sweep.dry_run([str(F)], [4, 8, 15], 6.0); out = capsys.readouterr().out
    assert sent == [] and 'nothing sent' in out and 'expected $0.02' in out and 'in all, 3 run(s): expected $0.06' in out
    w = cap_sweep.plan([str(F)])[0]['worst_usd']
    assert w == pytest.approx(sum(cap_sweep.worst_of(json.load(open(p)), 2e-6, 1e-5) for p in sorted((F / 'language_requests').iterdir())), abs=1e-4)

def test_a_file_without_data_collection_deny_is_refused_before_anything_is_sent(tmp_path):
    with pytest.raises(SystemExit) as e: cap_sweep.requests_of(str(folder(tmp_path, deny=False)))
    assert 'data_collection deny' in str(e.value)

def test_a_run_sends_each_file_as_saved_retries_a_429_and_records_every_call(tmp_path, monkeypatch):
    F = folder(tmp_path); A = folder(tmp_path, 'other'); sent = []; waits = []
    monkeypatch.setattr(urllib.request, 'urlopen', fake(sent)); monkeypatch.setattr('time.sleep', waits.append)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
    (tmp_path / 'forms.txt').write_text('Kenpo ban\nOnjoji\nGone form\n')
    out = tmp_path / 'sweep' / 'cap2'
    monkeypatch.setattr(sys, 'argv', ['cap_sweep.py', '--cap', '2', '--out', str(out), '--yes', '--forms', str(tmp_path / 'forms.txt'), str(F), str(A)])
    cap_sweep.main()
    saved = {open(p, 'rb').read() for d in (F, A) for p in (d / 'language_requests').iterdir()}
    assert set(sent) == saved and len(sent) == 5 and waits == [60]               # byte for byte; the 429 once more after 60 s
    s = json.load(open(out / 'summary.json'))
    assert s['calls'] == 5 and s['status_429'] == 1 and s['retried'] == 1 and s['cost_usd'] == 0.04 and s['not_finished'] == 0
    assert 1 <= s['peak_in_flight'] <= 4 and s['rule_u_gain'] == {'loose_key': 2, 'mark_only': 2}
    calls = json.load(open(out / 'calls.json'))
    retried = next(x for per in calls.values() for x in per if len(x['calls']) == 2)
    assert [c['status'] for c in retried['calls']] == [429, 200] and retried['calls'][0]['why'] == 'rate limited; sent once more after 60 s'
    assert all(c['finished'] >= c['sent'] for per in calls.values() for x in per for c in x['calls'])
    f = json.load(open(out / 'forms.json', encoding='utf-8'))
    assert f['Kenpo ban']['decision']['lang'] == 'ja-Latn' and f['Gone form'] is None
    assert (out / 'replies' / 'book' / '001.reply.json').exists()
    with pytest.raises(SystemExit): cap_sweep.main()                              # never over an earlier run
