"""test_name_languages.py: the language step (name_languages.py; #118, language tagging) against a fake OpenRouter.

    python -m pytest tests/test_name_languages.py -q

Synthetic pages only (tests/langpdf.py); no network (urlopen replaced, the key a dummy). Checks: a live run writes
language_parts and its own record; the estimate and the limit come before any request; a request answered before is
never paid for again; a saved language reply (FROM=, REPLY=) is applied by printed form with no request at all
(review 02, M3 and M4), listing forms no longer found; what is sent (no temperature where the model list doesn't take it,
data_collection deny).
"""
import json, os, runpy, sys, urllib.request
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
from test_decide_allowance import fake, MODEL  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import plumb_fix, plpages, langcands, langreq  # noqa: F401,E402

def tagged(R):
    """The places workorder.json tags (language_parts version 2, as apply.py reads them)."""
    wo = load(R / 'workorder.json')
    return langreq.expand(wo.get('language_parts'))

def answer_all(lang='ja-Latn'):
    def reply(body, n):
        items = json.loads(body['messages'][1]['content'])['items']
        dec = [{'id': it['id'], 'lang': lang, 'confidence': 'high', 'why': 'language', 'evidence': 'Hepburn ō'} for it in items]
        return {'choices': [{'message': {'content': json.dumps({'decisions': dec})}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 900, 'completion_tokens': 60 * len(items), 'cost': 0.004}}
    return reply

def folders(tmp_path, runs=None):
    src = langpdf.build(str(tmp_path / 'b.pdf'), runs or [{'font': 'F3', 'text': 'The temple of Onjōji and mappō.'}, {'font': 'F3', 'text': 'Later ryōgen wrote.'}])
    A = tmp_path / '_audit'; A.mkdir()
    json.dump(langcands.book(plpages.Pages(src), doc_lang='en'), open(A / 'lang_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False)
    R = tmp_path / 'run'; R.mkdir()
    (R / 'workorder.json').write_text(json.dumps({'document': {'lang': 'en', 'title': 'T'}}))
    return src, A, R

LAST = {}
def run(src, A, R, monkeypatch, *args, reply=None, ledger=None):
    calls = []
    monkeypatch.setattr(urllib.request, 'urlopen', fake(calls, reply or answer_all()))
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
    monkeypatch.setenv('COST_HISTORY', str(ledger or (R.parent / 'ledger.jsonl')))
    monkeypatch.setattr(sys, 'argv', ['name_languages.py', str(A), str(R), '--pdf', str(src), '--model', MODEL, *map(str, args)]); monkeypatch.chdir(HERE)
    LAST['exit'] = None
    try: runpy.run_path(os.path.join(HERE, 'name_languages.py'), run_name='__main__')
    except SystemExit as e: LAST['exit'] = e.code
    return calls

def load(p): return json.load(open(p, encoding='utf-8'))

def test_a_live_run_writes_parts_and_its_record(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    calls = run(src, A, R, monkeypatch)
    assert len(calls) == 1 and LAST['exit'] is None
    body = json.loads(calls[0])
    assert 'temperature' not in body and body['provider'] == {'data_collection': 'deny'}       # the fake list gives no temperature
    parts = tagged(R)
    assert sorted(p['form'] for p in parts) == ['Onjōji', 'mappō', 'ryōgen'] and {p['lang'] for p in parts} == {'ja-Latn'}
    lr = load(R / 'language_run.json')
    assert lr['cost_usd'] == 0.004 and len(lr['decisions']) == 3 and langreq.expand(lr['language_parts']) == parts
    assert os.path.exists(R / 'language_requests' / '001.request.json')
    assert run(src, A, R, monkeypatch) == [] and load(R / 'language_run.json')['cost_usd'] == 0.004     # answered before: never paid again

def test_the_estimate_and_the_limit_come_first(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    assert run(src, A, R, monkeypatch, '--dry-run') == [] and load(R / 'language_estimate.json')['to_send'] == 1
    assert run(src, A, R, monkeypatch, '--max-usd', '0.0001') == [] and 'refusing before any AI request' in str(LAST['exit'])
    assert tagged(R) == []

def test_a_saved_reply_is_applied_by_form_with_no_request(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch)
    saved = load(R / 'language_run.json'); saved['decisions']['marks|Gone form'] = {'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}
    (tmp_path / 'saved.language.json').write_text(json.dumps(saved))
    # the rerun's book lost one candidate (ryōgen) and the saved reply has one the book no longer holds
    (tmp_path / 'b2').mkdir()
    src2, A2, R2 = folders(tmp_path / 'b2', runs=[{'font': 'F3', 'text': 'The temple of Onjōji and mappō.'}, {'text': 'Later nothing.'}])
    calls = run(src2, A2, R2, monkeypatch, '--response-file', tmp_path / 'saved.language.json')
    assert calls == []
    lr = load(R2 / 'language_run.json')
    assert lr['replay']['used'] == 2 and lr['replay']['vanished_count'] == 2 and lr['cost_usd'] == 0 and lr['response_from']
    assert sorted(p['form'] for p in tagged(R2)) == ['Onjōji', 'mappō']

def test_a_saved_reply_without_decisions_runs_nothing(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    (tmp_path / 'empty.json').write_text('{}')
    assert run(src, A, R, monkeypatch, '--response-file', tmp_path / 'empty.json') == []
    assert 'not run' in load(R / 'language_run.json')['note'] and tagged(R) == []

def test_a_cut_off_reply_keeps_what_it_finished(tmp_path, monkeypatch):
    """A reply cut off at max_tokens (finish 'length') keeps every decision object it finished; the rest are counted as
    not decided, never lost silently (05, advisor)."""
    src, A, R = folders(tmp_path)
    def cut(body, n):
        items = json.loads(body['messages'][1]['content'])['items']
        whole = json.dumps({'decisions': [{'id': it['id'], 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'} for it in items]})
        return {'choices': [{'message': {'content': whole[:whole.rfind('{"id"') + 12]}, 'finish_reason': 'length'}],
                'usage': {'prompt_tokens': 900, 'completion_tokens': 100, 'cost': 0.004}}
    run(src, A, R, monkeypatch, reply=cut)
    lr = load(R / 'language_run.json')
    assert len(lr['decisions']) == 2 and lr['not_decided'] == 1 and len(tagged(R)) == 2

def test_reuse_reads_saved_replies_that_were_never_parsed(tmp_path, monkeypatch):
    """review 06, M3: a step that stopped after paying and before parsing left decisions {} beside complete replies;
    --reuse reads the replies again (no request) and lists what stays undecided by group."""
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch)
    lr = load(R / 'language_run.json'); lr['decisions'] = {}; (R / 'language_run.json').write_text(json.dumps(lr))
    wo = load(R / 'workorder.json'); wo.pop('language_parts'); (R / 'workorder.json').write_text(json.dumps(wo))
    assert run(src, A, R, monkeypatch, '--reuse') == []
    lr2 = load(R / 'language_run.json')
    assert len(lr2['decisions']) == 3 and lr2['not_decided'] == 0 and len(tagged(R)) == 3

def test_title_growth_and_han_grouping_are_options_off_by_default(tmp_path, monkeypatch):
    """review 08, M6: LANG_GROW and LANG_GROUP reach the real step (recorded under options); both are off unless set."""
    src, A, R = folders(tmp_path)
    monkeypatch.delenv('LANG_GROW', raising=False); monkeypatch.delenv('LANG_GROUP', raising=False)
    run(src, A, R, monkeypatch)
    assert load(R / 'language_run.json')['options'] == {'grow': False, 'group': False}
    (tmp_path / 'b').mkdir(); src2, A2, R2 = folders(tmp_path / 'b')
    monkeypatch.setenv('LANG_GROW', 'on'); monkeypatch.setenv('LANG_GROUP', 'on')
    run(src2, A2, R2, monkeypatch)
    lr = load(R2 / 'language_run.json')
    assert lr['options'] == {'grow': True, 'group': True} and 'titles grown' in lr['candidates']

def test_reuse_keeps_a_mismatched_form_echo_dropped(tmp_path, monkeypatch):
    """review 12, M1: two decisions echo "mappō", the second under another item's id. The first parse drops it; --reuse
    reads the replies again with the forms, so that item stays undecided instead of coming back at high confidence."""
    src, A, R = folders(tmp_path)
    def echo(body, n):
        items = json.loads(body['messages'][1]['content'])['items']
        m = next(it for it in items if it['form'] == 'mappō'); other = next(it for it in items if it['form'] != 'mappō')
        dec = [{'id': m['id'], 'form': 'mappō', 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'},
               {'id': other['id'], 'form': 'mappō', 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}]
        return {'choices': [{'message': {'content': json.dumps({'decisions': dec})}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 900, 'completion_tokens': 60, 'cost': 0.004}}
    run(src, A, R, monkeypatch, reply=echo)
    first = load(R / 'language_run.json'); assert len(first['decisions']) == 1
    assert run(src, A, R, monkeypatch, '--reuse') == []
    lr = load(R / 'language_run.json')
    assert sorted(lr['decisions']) == sorted(first['decisions']) and [p['form'] for p in tagged(R)] == ['mappō']
