"""test_credit.py: "Check Credit Again" and the credit's reasons (U8, #45, Patrick 2026-11-07). No network: webapp/credit.py's
HTTP calls are replaced; no key is read or printed.

    python -m pytest tests/test_credit.py -q
"""
import os, sys, json, io, urllib.error
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from lib import costs  # noqa: E402
from webapp import credit as CR  # noqa: E402
from webapp import spend as SP, batches as BT, books as BK, jobs  # noqa: E402
from test_webapp import setup, settings  # noqa: E402,F401
from test_spend import run_folder  # noqa: E402

class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass

@pytest.mark.parametrize('raise_,want', [(urllib.error.HTTPError('u', 401, 'Unauthorized', {}, None), 'refused'),
                                         (urllib.error.URLError('no route'), 'unreachable'), (TimeoutError(), 'unreachable'),
                                         (urllib.error.HTTPError('u', 500, 'Server', {}, None), 'error')])
def test_why_the_credit_couldnt_be_read(monkeypatch, raise_, want):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-test')
    def boom(*a, **k): raise raise_
    monkeypatch.setattr(CR.urllib.request, 'urlopen', boom)
    assert CR.check() == (None, want)

def test_the_credit_is_the_smaller_of_the_two(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-test')
    answers = iter([{'data': {'limit_remaining': 7.5}}, {'data': {'total_credits': 30, 'total_usage': 9.11}}])
    monkeypatch.setattr(CR.urllib.request, 'urlopen', lambda *a, **k: Resp(json.dumps(next(answers)).encode()))
    assert CR.check() == (7.5, None)

def test_no_key(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.setattr(CR, 'HERE', '/')                                         # no .env above /
    assert CR.check() == (None, 'no_key')

def test_check_credit_again_lets_a_batch_start(setup, monkeypatch):
    """A batch whose estimates couldn't read the credit: the page says why and offers "Check Credit Again"; a read that
    works (and fits) brings "Start Remediation" back, through the same checks; the fingerprint doesn't change."""
    s = settings(setup)
    for n in ('a', 'b'): (setup / 'uploads' / f'{n}.pdf').write_bytes(b'%PDF-1.4 ' + n.encode())
    js = BT.start(s, [], [b['key'] for b in BK.listing(s)], 'B2')
    for j in js:
        R = run_folder(setup, name='batches', label='B2/' + j['run'].split('/')[-1], worst=0.5, credit=None)
        jobs.update(s['jobs'], j['id'], status='done')
    st = BT.state(s, 'B2')
    assert st['phase'] == 'ready' and st['spend'] == {'ok': False, 'why': SP.CREDIT_WHY[None], 'code': 'no_credit'}
    fp = st['fingerprint']
    monkeypatch.setattr(CR, 'check', lambda timeout=30: (None, 'refused'))
    SP.check_credit(s)
    assert BT.state(s, 'B2')['spend']['why'] == SP.CREDIT_WHY['refused'] and 'revoked' in SP.CREDIT_WHY['refused']
    monkeypatch.setattr(CR, 'check', lambda timeout=30: (20.89, None))
    SP.check_credit(s)
    st = BT.state(s, 'B2')
    assert st['spend'] == {'ok': True, 'why': None, 'code': None} and st['totals']['credit_usd'] == 20.89 and st['fingerprint'] == fp
    monkeypatch.setattr(CR, 'check', lambda timeout=30: (0.6, None))                    # not enough: the paid rule still refuses
    SP.check_credit(s)
    assert BT.state(s, 'B2')['spend']['code'] == 'credit'

def test_the_advice_fits_the_reason():
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "s.spend.code === 'no_credit'" in js and 'Check Credit Again' in js and 'raise the limit or add credit' not in js
    pj = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "s.spend.code === 'no_credit'" in pj and 'id="pp-credit" data-act="credit">Check Credit Again' in pj and "batch: 'Batch'" in pj

# ------------------------------------------------------------------ U4: designed stops, and codes only under "Details"
def test_designed_stops_are_never_failed(setup):
    from webapp import runs as RN
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'; R.mkdir(parents=True)
    def view(**kw):
        j = jobs.create(s['jobs'], kw.pop('kind', 'estimate'), 'bk/r1', ['true'], {}, R=str(R))
        jobs.update(s['jobs'], j['id'], **kw)
        return RN.job_view(s, jobs.load(s['jobs'], j['id']))
    a = view(status='failed', exit=4)                                            # stopped to ask the language
    assert a['status'] == 'done' and a['reason'] is None and a['detail'] is None and 'stopped to ask the language' in a['result']
    b = view(status='failed', exit=3)                                            # intake stopped the PDF for a person
    assert b['status'] == 'stopped' and b['reason'] is None and 'stopped for a person' in b['result'] and 'failed' not in b['title']
    c = view(status='failed', exit=1)                                            # a real error: its code and log folded
    assert c['status'] == 'failed' and c['reason'] == 'The command ended with an error.' and 'exit' not in c['reason']
    assert c['detail'] == {'exit': 1, 'log': c['log']}
    d = view(kind='apply', status='failed', exit=4)                              # exit 4 is a stop only for an estimate
    assert d['status'] == 'failed'
    pj = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert "' Log: ' + esc(j.log)" not in pj and "is saved in ' + esc(j.log)" not in pj and '<details class="pp-details"><summary>Details</summary>' in pj

def test_test_mode_keeps_a_failed_read_as_no_credit(setup, monkeypatch):
    """21-L1: in test mode a refused read is stored as it is (no credit, with its reason), never $0.00, so a run whose
    estimate has no credit stays no_credit and "Start Remediation" is allowed (test mode lets no_credit through)."""
    from webapp import runs as RN
    s = settings(setup, test_reply_dir=str(setup / 'replies'))
    R = run_folder(setup, name='bk', label='l1', credit=None)
    monkeypatch.setattr(CR, 'check', lambda timeout=30: (None, 'refused'))
    d = SP.check_credit(s)
    assert d['usd'] is None and d['why'] == 'refused' and SP.credit_read(s) is None
    est = costs.estimate(str(R), 'workorder', costs.limits_of(s), credit_read=SP.credit_read(s))
    assert est['blocked']['code'] == 'no_credit'
    j = jobs.create(s['jobs'], 'estimate', 'bk/l1', ['bash', 'run_api.sh', 'x.pdf', 'bk', 'l1'], {}, R=str(R)); jobs.update(s['jobs'], j['id'], status='done')
    st = RN.pending_state(s, 'bk/l1', str(R))
    assert st['spend']['ok'] is True                                                    # test mode: allowed

# ------------------------------------------------------------------ V1, V2
@pytest.mark.parametrize('label,want', [('3/5 anthropic/claude-sonnet-5.5 via OpenRouter', 'sending to the AI (Claude Sonnet 5.5)'),
                                        ('3/5 anthropic/claude-opus-5.5 via OpenRouter', 'sending to the AI (Claude Opus 5.5)'),
                                        ('3/5 openai/gpt-4o via OpenRouter', 'sending to the AI (GPT-4o)'),
                                        ('3/5 openai/o3 via OpenRouter', 'sending to the AI (OpenAI o3)'),
                                        ('4/5 apply (no model)', 'applying the reviewed decisions')])
def test_the_ai_step_names_its_model_in_plain_words(label, want):
    """V2: the AI step names the run's own model (from its log's label, never the settings' current one) by its display name."""
    from webapp import logs
    assert logs.plain(label) == want
    assert logs.now_step('spend', [{'label': '3/5 anthropic/claude-sonnet-5.5 via OpenRouter', 'state': 'running', 'time': None}])['words'] == 'sending to the AI (Claude Sonnet 5.5)'

def test_the_batch_running_line():
    js = open(os.path.join(HERE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "Each PDF\\'s status is shown below." in js and 'is in the list of PDFs' not in js
