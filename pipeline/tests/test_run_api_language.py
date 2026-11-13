"""test_run_api_language.py: run_api.sh's language step (#118, step 3c) with a saved reply (REPLY=, as FROM= gives each
book): never a request (review 02, M3). Without saved language decisions the step is not run and says so; with them
(LANG_REPLY=) they are applied by form at no cost, and the record keeps them. A synthetic tagged book, veraPDF off, no
key and no network (a request would fail loudly).

    python -m pytest tests/test_run_api_language.py -q
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_api(tmp_path, **extra):
    src = langpdf.build(str(tmp_path / 'book.pdf'), [{'font': 'F3', 'text': 'The temple of Onjōji and mappō.'}])
    wo = {'document': {'lang': 'en', 'title': 'Synthetic language test'}}
    (tmp_path / 'reply.txt').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5', 'choices': [{'message': {'content': json.dumps(wo)}, 'finish_reason': 'stop'}],
                                                    'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.3}}))
    env = dict(os.environ, VERAPDF='off', RUN_DIR=str(tmp_path / 'run'), REPLY=str(tmp_path / 'reply.txt'), INTAKE='off', OPENROUTER_API_KEY='test-not-a-key',
               HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',   # no network
               RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **extra)
    for k in ('AUTO', 'FROM', 'LANG_REPLY', 'LANG_TAGS', 'REVIEW'):
        if k not in extra: env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', src, 'book', 'l1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    return r, tmp_path / 'run'

def test_a_saved_reply_never_starts_the_language_step(tmp_path):
    r, R = run_api(tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'language tags: not run' in r.stdout and 'language tags via OpenRouter' not in r.stdout
    rec = json.load(open(R / 'record.json'))
    assert 'language_run' not in rec and 'language_parts' not in rec['workorder']

def test_saved_language_decisions_are_applied_at_no_cost(tmp_path):
    saved = {'schema': 'language-run/1', 'model': 'anthropic/claude-sonnet-5.5', 'cost_usd': 0.05,
             'decisions': {'marks|Onjōji': {'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'},
                           'hawaiian|mappō': {'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}}}
    (tmp_path / 'book.language.json').write_text(json.dumps(saved))
    r, R = run_api(tmp_path, LANG_REPLY=str(tmp_path / 'book.language.json'), LANG_TAGS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'language tags: saved decisions (no cost)' in r.stdout
    rec = json.load(open(R / 'record.json'))
    assert rec['language_run']['replay']['used'] == 2 and rec['cost_total_usd'] == 0.3      # the saved reply's own; the language replay adds nothing
    assert sorted(p['text'] for p in rec['workorder']['language_parts']['parts']) == ['Onjōji', 'mappō']
    assert rec['apply']['language_parts']['split'] == 2
