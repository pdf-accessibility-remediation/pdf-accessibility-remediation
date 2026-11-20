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
    # #159: the step is never refused for its own cost: what doesn't fit its limit is held back and listed
    assert run(src, A, R, monkeypatch, '--max-usd', '0.0001') == [] and LAST['exit'] is None
    lr = load(R / 'language_run.json')
    assert tagged(R) == [] and lr['held_back_count'] == 3 and lr['held_back_why'] == 'dollars' and lr['held_back_limit'] == {'usd': 0.0001, 'which': 'step'}

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

def test_the_estimate_follows_the_language_allowance(tmp_path, monkeypatch):
    """Round 17 (review 16, item 1): language_estimate.json's max_tokens are costs.allowance's, and its worst case is
    each request's input and allowance at the listed prices."""
    from lib import costs
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch, '--dry-run')
    e = load(R / 'language_estimate.json')
    assert e['max_tokens'] == [costs.allowance('language', 3)] == [1400]
    pin, pout = (x / 1e6 for x in e['price_per_million'])
    assert e['worst_case_usd'] > 1400 * pout and e['worst_case_usd'] == round(e['worst_case_usd'], 4)

# ---- #137 (dropped language answers): an echo of the printed spelling, with the marks as sent (review 02, H1 and M5)
TITLE = [{'font': 'F3', 'text': 'The year Tenpyō hōji ninen: Naishōsen here.'}, {'font': 'F3', 'text': 'Later ryōgen wrote.'}]

def echo_marked(body, n):
    """Each answer copies the text marked for its id (the printed spelling), not the item's form."""
    req = json.loads(body['messages'][1]['content'])
    marks = langreq.marks_of(req)
    dec = [{'id': it['id'], 'form': (marks.get(it['id']) or [it['form']])[0], 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}
           for it in req['items']]
    return {'choices': [{'message': {'content': json.dumps({'decisions': dec})}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 900, 'completion_tokens': 60, 'cost': 0.004}}

def test_an_echo_of_the_printed_spelling_is_used(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path, TITLE)
    run(src, A, R, monkeypatch, reply=echo_marked)
    lr = load(R / 'language_run.json')
    assert 'cjk|x' not in lr and any(k.endswith('|Tenpyō hōji ninen Naishōsen') for k in lr['decisions'])
    assert not [d for d in lr.get('dropped') or [] if 'form' in d['why']]
    marks = lr['requests'][0]['id_marks']
    assert any('Tenpyō hōji ninen: Naishōsen' in v for v in marks.values())

def test_a_replay_reads_marks_from_the_request_it_answered(tmp_path, monkeypatch):
    """A run made before `id_marks` (stripped here): --reuse reads the marks from language_requests/ only while that file's
    sha256 matches the entry's; another request under the same number leaves the echo to the forms alone."""
    src, A, R = folders(tmp_path, TITLE)
    run(src, A, R, monkeypatch, reply=echo_marked)
    def strip():
        lr = load(R / 'language_run.json'); lr['decisions'] = {}
        for x in lr['requests']: x.pop('id_marks', None)
        (R / 'language_run.json').write_text(json.dumps(lr))
        wo = load(R / 'workorder.json'); wo.pop('language_parts', None); (R / 'workorder.json').write_text(json.dumps(wo))
    strip()
    assert run(src, A, R, monkeypatch, '--reuse') == []
    assert any(k.endswith('|Tenpyō hōji ninen Naishōsen') for k in load(R / 'language_run.json')['decisions'])
    lr = load(R / 'language_run.json'); x = lr['requests'][0]; nl = runpy.run_path(os.path.join(HERE, 'name_languages.py'))
    assert x.get('id_marks') is None
    got = nl['marks_for'](x, str(R), lr['prompt_sha256'])
    assert any('Tenpyō hōji ninen: Naishōsen' in v for v in got.values())
    f = R / 'language_requests' / '001.request.json'
    body = load(f); body['messages'][1]['content'] = body['messages'][1]['content'].replace('here', 'there'); f.write_text(json.dumps(body))
    assert nl['marks_for'](x, str(R), lr['prompt_sha256']) is None                # another request under that number: not read
    assert nl['marks_for']({**x, 'id_marks': {'1': ['a']}}, str(R), lr['prompt_sha256']) == {'1': ['a']}

# ------------------------------------------------------------------ #135 (parallel requests): the retry, the resend, the stops
def dec(it, lang='ja-Latn'): return {'id': it['id'], 'lang': lang, 'confidence': 'high', 'why': 'language'}
def answer(items, text=None, finish='stop', cost=0.004):
    return {'choices': [{'message': {'content': text if text is not None else json.dumps({'decisions': [dec(it) for it in items]})}, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 900, 'completion_tokens': 100, 'cost': cost}}
def items_of(body): return json.loads(body['messages'][1]['content'])['items']

def test_a_cut_off_reply_resends_only_its_not_answered_forms(tmp_path, monkeypatch):
    """01 §4.3, §5: the first item decided, the second's answer refused (a tag the step may not write), the third never
    reached. Only the third is sent again, once, as a smaller request; the refused answer is never resent."""
    src, A, R = folders(tmp_path); seen = []
    def reply(body, n):
        its = items_of(body); seen.append([it['form'] for it in its])
        if n > 1: return answer(its)
        text = json.dumps({'decisions': [dec(its[0]), dec(its[1], lang='xx-notalang'), dec(its[2])]})
        return answer(its, text=text[:text.rfind('{"id"') + 12], finish='length')
    calls = run(src, A, R, monkeypatch, reply=reply)
    assert len(calls) == 2 and len(seen[1]) == 1 and seen[1][0] == seen[0][2]
    lr = load(R / 'language_run.json')
    assert [(x['n'], x.get('resend_of')) for x in lr['requests']] == [(1, None), (1, 1)] and lr['requests'][0]['resend'] == '1 undecided forms sent once more'
    assert lr['requests'][1]['resend_of_sha256'] == lr['requests'][0]['sha256'] and (R / 'language_requests' / '001r.request.json').exists()
    assert len(lr['decisions']) == 2 and lr['cost_usd'] == 0.008 and 'in_flight' not in lr
    no = {p['form']: p.get('no_answer') for p in load(R / 'workorder.json')['language_parts']['forms']}
    assert no[seen[0][1]] == 'tag'
    assert run(src, A, R, monkeypatch, reply=reply) == []                 # a rerun reuses the pair: nothing is paid again
    assert len(load(R / 'language_run.json')['decisions']) == 2

def test_a_reply_read_only_in_pieces_resends_its_unreached_forms_once(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    def reply(body, n):
        its = items_of(body)
        good = json.dumps(dec(its[0]))
        return answer(its, text='{"decisions": [' + good + ', {"id": oops' if n == 1 else '{"decisions": [' + good + ', {"id": oops')
    calls = run(src, A, R, monkeypatch, reply=reply)
    lr = load(R / 'language_run.json')
    assert len(calls) == 2 and len(json.loads(json.loads(calls[1])['messages'][1]['content'])['items']) == 2    # sent once, not again
    assert len(lr['decisions']) == 2 and lr['requests'][1]['resend_of'] == 1

def test_an_unreadable_reply_is_retried_whole_once(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    monkeypatch.setattr('time.sleep', lambda s: None)
    calls = run(src, A, R, monkeypatch, reply=lambda b, n: answer(items_of(b), text='no decisions here') if n == 1 else answer(items_of(b)))
    lr = load(R / 'language_run.json')
    assert len(calls) == 2 and calls[0] == calls[1] and len(lr['decisions']) == 3 and lr['cost_usd'] == 0.008
    assert lr['requests'][0]['calls'][0]['why'] == 'the reply could not be read; sent once more after 20 s'

def test_a_resend_with_no_room_under_the_step_limit_is_not_sent(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    def reply(body, n):
        its = items_of(body); text = json.dumps({'decisions': [dec(it) for it in its]})
        return answer(its, text=text[:text.rfind('{"id"') + 12], finish='length', cost=0.5)
    est = run(src, A, R, monkeypatch, '--dry-run')                         # the worst case of the one request
    worst = load(R / 'language_estimate.json')['worst_case_usd']
    calls = run(src, A, R, monkeypatch, '--max-usd', worst + 0.01, reply=reply)
    lr = load(R / 'language_run.json')
    assert est == [] and len(calls) == 1 and 'the language step limit has no room' in lr['requests'][0]['resend']

def test_a_stopped_step_counts_what_was_in_flight_and_a_new_model_keeps_it(tmp_path, monkeypatch):
    """review 02 M2: between steps an entry in flight means the step stopped; it counts at its worst case toward the PDF, and
    a rerun with another model keeps it (stopped_in_flight) and what the earlier attempt paid (earlier_cost_usd)."""
    from lib import costs
    src, A, R = folders(tmp_path)
    (R / 'language_run.json').write_text(json.dumps({'schema': 'language-run/1', 'model': 'other/model', 'prompt_sha256': 'x', 'cost_usd': 0.2,
                                                     'requests': [{'n': 2, 'sha256': 'y', 'finish': None, 'error': {'code': 'timeout'}, 'cost_usd': 0, 'worst_usd': 0.3}],
                                                     'in_flight': [{'n': 1, 'worst_usd': 0.5}]}))
    assert costs.language_paid(str(R)) == 1.0 and costs.book_spent(str(R)) == 1.0       # 0.2 known, 0.5 and 0.3 not known
    run(src, A, R, monkeypatch)
    lr = load(R / 'language_run.json')
    assert lr['earlier_cost_usd'] == 0.2 and lr['cost_usd'] == 0.004
    assert sorted((e['n'], e['worst_usd']) for e in lr['stopped_in_flight']) == [(1, 0.5), (2, 0.3)]
    assert costs.language_paid(str(R)) == 1.004 and costs.actual(str(R))['usd'] == 0.204    # the worst cases count toward the limit, never as money spent

def test_an_interruption_during_a_resend_keeps_the_first_call_and_counts_the_resend_at_its_worst(tmp_path, monkeypatch):
    """review 02 H3, with the language step: the first call's known cost is stored as it comes back; the resend in flight
    when the run stops is kept in stopped_in_flight at its worst case, and the interruption is raised again."""
    from lib import costs
    src, A, R = folders(tmp_path)
    def reply(body, n):
        its = items_of(body)
        if n > 1: raise KeyboardInterrupt                 # Ctrl+C reaches the run while the resend is out
        text = json.dumps({'decisions': [dec(it) for it in its]})
        return answer(its, text=text[:text.rfind('{"id"') + 12], finish='length')
    with pytest.raises(KeyboardInterrupt):
        run(src, A, R, monkeypatch, reply=reply)
    lr = load(R / 'language_run.json')
    st, = lr['stopped_in_flight']
    assert st['n'] == 1 and st['resend'] and st['stopped'] and st['worst_usd'] > 0 and 'in_flight' not in lr
    assert lr['cost_usd'] == 0.004 and len(lr['requests']) == 1
    assert costs.language_paid(str(R)) == pytest.approx(0.004 + st['worst_usd'])

def test_a_reply_cut_off_before_its_first_decision_is_resent_whole_once(tmp_path, monkeypatch):
    """A reply cut off with nothing readable has no code per form: every form is unreached, so the whole request is sent
    once more as its resend, and that resend, cut off again, is not resent."""
    src, A, R = folders(tmp_path)
    calls = run(src, A, R, monkeypatch, reply=lambda b, n: answer(items_of(b), text='', finish='length'))
    lr = load(R / 'language_run.json')
    assert len(calls) == 2 and len(items_of(json.loads(calls[1]))) == 3 and [x.get('resend_of') for x in lr['requests']] == [None, 1]
    assert lr['decisions'] == {} and {p.get('no_answer') for p in load(R / 'workorder.json')['language_parts']['forms']} == {'cut_off'}

def test_a_replay_of_an_interrupted_step_keeps_its_worst_cases_and_earlier_cost(tmp_path, monkeypatch):
    """review 02 M2 on the replay path: run_api.sh replays this folder's own record with --reuse after a later step failed;
    the record it writes keeps what an interruption left in flight. A saved reply from elsewhere keeps it too, with this
    folder's own cost as earlier_cost_usd."""
    from lib import costs
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch)
    lr = load(R / 'language_run.json'); lr['in_flight'] = [{'n': 2, 'worst_usd': 0.5}]; (R / 'language_run.json').write_text(json.dumps(lr))
    before = costs.language_paid(str(R))
    assert run(src, A, R, monkeypatch, '--reuse') == []
    lr2 = load(R / 'language_run.json')
    assert lr2['stopped_in_flight'][0]['worst_usd'] == 0.5 and costs.language_paid(str(R)) == before == 0.504
    other = tmp_path / 'other.json'; other.write_text(json.dumps({**lr, 'in_flight': [], 'cost_usd': 0.9}))
    assert run(src, A, R, monkeypatch, '--response-file', other) == []
    lr3 = load(R / 'language_run.json')
    assert lr3['earlier_cost_usd'] == 0.004 and lr3['stopped_in_flight'][0]['worst_usd'] == 0.5 and costs.language_paid(str(R)) == 0.504

def test_each_request_records_when_it_was_sent_and_finished(tmp_path, monkeypatch):
    """#135 (parallel requests): send and finish times (wall clock, epoch seconds) on every request, so the requests out at
    once can be counted across several PDFs run side by side."""
    import time
    src, A, R = folders(tmp_path); t0 = time.time()
    run(src, A, R, monkeypatch)
    x, = load(R / 'language_run.json')['requests']
    assert t0 - 0.001 <= x['sent_at'] <= x['finished_at'] <= time.time() + 0.001     # rounded to ms

def test_a_reply_that_reports_an_error_leaves_its_forms_failed(tmp_path, monkeypatch):
    """round 11: a 200 reply with finish_reason "error" is a failed request (sent once more, then recorded with its error),
    so its forms read "failed", never "invalid"."""
    src, A, R = folders(tmp_path); monkeypatch.setattr('time.sleep', lambda s: None)
    calls = run(src, A, R, monkeypatch, reply=lambda b, n: answer(items_of(b), text='', finish='error'))
    x, = load(R / 'language_run.json')['requests']
    assert len(calls) == 2 and x['error']['code'] == 'error' and 'text' not in x
    assert {f.get('no_answer') for f in load(R / 'workorder.json')['language_parts']['forms']} == {'failed'}

def test_the_fill_sends_the_first_forms_that_fit_and_holds_back_the_rest(tmp_path, monkeypatch):
    """#159: a limit that admits only part of the one request: the first forms in order are sent (a smaller request),
    the rest held back, named in the record with their kinds and a hash of their keys; no refusal."""
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch, '--dry-run', '--max-usd', '1000')
    full = load(R / 'language_estimate.json')['worst_case_usd']
    calls = run(src, A, R, monkeypatch, '--max-usd', str(round(full * 0.85, 6)))
    lr = load(R / 'language_run.json')
    sent = json.loads(json.loads(calls[0])['messages'][1]['content'])['items']
    assert LAST['exit'] is None and len(calls) == 1 and 0 < len(sent) < 3 and lr['held_back_count'] == 3 - len(sent)
    order = [f['form'] for f in langreq.forms(load(A / 'lang_candidates.json')['places'])]
    assert [it['form'] for it in sent] == order[:len(sent)] and lr['held_back'] == order[len(sent):]
    assert lr['held_back_why'] == 'dollars' and sum(lr['held_back_by_kind'].values()) == lr['held_back_count'] and len(lr['held_back_sha']) == 16

def test_the_fill_stops_at_the_room_left_in_the_pdfs_limit(tmp_path, monkeypatch):
    """review 29 M4: the step's own limit is large, the PDF's room small (a work order still to pay in its estimate):
    the fill stops at the room, and the estimate says which limit held the forms back."""
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch, '--dry-run', '--max-usd', '1000')
    full = load(R / 'language_estimate.json')['worst_case_usd']
    (R / 'run.json').write_text(json.dumps({'estimate': {'worst_case_total_usd': 1.0}}))          # the work order, priced, not yet paid
    run(src, A, R, monkeypatch, '--dry-run', '--max-usd', '1000', '--book-max-usd', str(round(1.0 + full * 0.5, 6)))
    e = load(R / 'language_estimate.json')
    assert e['held_back'] >= 1 and e['worst_case_usd'] <= full * 0.5 + 1e-6 and e['held_back_limit']['which'] == 'book' and 'refused' not in e

def test_the_per_pdf_limit_from_the_environment_sets_the_room(tmp_path, monkeypatch):
    """review 31 M1: the room comes from BOOK_MAX_USD as the app passes it (Settings): a raised per-PDF limit sends more,
    a lowered one holds forms back instead of leaving the step out."""
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch, '--dry-run', '--max-usd', '1000')
    full = load(R / 'language_estimate.json')
    (R / 'run.json').write_text(json.dumps({'estimate': {'worst_case_total_usd': 1.0}}))          # the work order, priced, not yet paid
    monkeypatch.setenv('BOOK_MAX_USD', str(round(1.0 + full['worst_case_usd'] * 0.5, 6)))         # "lowered": half the step's worst fits
    run(src, A, R, monkeypatch, '--dry-run', '--max-usd', '1000')
    low = load(R / 'language_estimate.json')
    assert low['held_back'] >= 1 and low['held_back_limit']['which'] == 'book' and 'refused' not in low
    monkeypatch.setenv('BOOK_MAX_USD', '80')                                                      # "raised": everything fits
    run(src, A, R, monkeypatch, '--dry-run', '--max-usd', '1000')
    high = load(R / 'language_estimate.json')
    assert high['held_back'] == 0 and high['sent'] == full['sent'] > low['sent']

def test_run_api_sh_stop_estimates_use_the_apps_limits():
    """review 31 L1: at_limits (run_api.sh) runs a stop's estimate under the app's limits (APP_*) in an app job, never the
    job's bounds; with no APP_* (a terminal run) the step limits are the code's defaults and BOOK_MAX_USD the caller's."""
    import subprocess, re
    sh = open(os.path.join(HERE, 'run_api.sh'), encoding='utf-8').read()
    fn = re.search(r'^at_limits\(\) \{.*?^\}', sh, re.S | re.M).group(0)
    def env_of(**kw):
        e = {k: v for k, v in os.environ.items() if not k.startswith(('APP_', 'LANGUAGE_MAX', 'PAGE_READS_MAX', 'BOOK_MAX'))}
        out = subprocess.run(['bash', '-c', fn + '\nat_limits env'], env={**e, **kw}, capture_output=True, text=True).stdout
        return {k: v for k, v in (l.split('=', 1) for l in out.splitlines() if '=' in l) if k.endswith('_MAX_USD')}
    app = env_of(LANGUAGE_MAX_USD='3.17', PAGE_READS_MAX_USD='1.02', BOOK_MAX_USD='4.50',
                 APP_LANGUAGE_MAX_USD='40.00', APP_PAGE_READS_MAX_USD='30.00', APP_BOOK_MAX_USD='80.00')
    assert (app['LANGUAGE_MAX_USD'], app['PAGE_READS_MAX_USD'], app['BOOK_MAX_USD']) == ('40.00', '30.00', '80.00')
    term = env_of(LANGUAGE_MAX_USD='3.17', BOOK_MAX_USD='60')
    assert 'LANGUAGE_MAX_USD' not in term and term['BOOK_MAX_USD'] == '60'

@pytest.mark.parametrize('title', ['A' * 200, '仏' * 200], ids=['latin', 'cjk'])
def test_the_estimate_reserves_room_for_the_title_and_language(tmp_path, monkeypatch, title):
    """review 31 M2 (Patrick: option (a)): an estimate made before the work order prices the title and language at a
    reserve, so the real run, with a 200-character title and bound to round_up(worst) as a Spend binds it, holds nothing
    back and sends what the estimate showed. Without the reserve (an empty title priced) the real worst case is higher."""
    from lib import costs
    src, A, R = folders(tmp_path, runs=[{'font': 'F3', 'text': f'The temple of Onjōji{i} and mappō{i}, later ryōgen{i}.'} for i in range(40)])
    (R / 'workorder.json').unlink()
    run(src, A, R, monkeypatch, '--dry-run')
    est = load(R / 'language_estimate.json')
    assert est['held_back'] == 0 and est['sent'] >= 100
    (R / 'workorder.json').write_text(json.dumps({'document': {'lang': 'en', 'title': ''}}))   # what the estimate priced before the reserve
    run(src, A, R, monkeypatch, '--dry-run')
    bare = load(R / 'language_estimate.json')['worst_case_usd']
    (R / 'workorder.json').write_text(json.dumps({'document': {'lang': 'en', 'title': title}}))
    run(src, A, R, monkeypatch, '--dry-run')
    real = load(R / 'language_estimate.json')['worst_case_usd']
    assert bare < real <= est['worst_case_usd']                                      # the title raises it; the reserve covers it
    run(src, A, R, monkeypatch, '--max-usd', f'{costs.bound(est["worst_case_usd"], 25):.2f}')
    lr = load(R / 'language_run.json')
    assert LAST['exit'] is None and lr['held_back_count'] == 0 and len(lr['decisions']) == est['sent']

def test_the_reserve_takes_a_longer_metadata_title_and_ends_with_the_work_order(tmp_path):
    import name_languages as NL
    A, wo = tmp_path / '_audit', tmp_path / 'workorder.json'; A.mkdir()
    assert NL.price_book(str(A), str(wo)) == {'title': NL.RESERVE_TITLE, 'language': NL.RESERVE_LANG}
    long = '経' * 320
    (A / 'digest.json').write_text(json.dumps({'document': {'title': 'Short', 'xmp_title': long}}))
    assert NL.price_book(str(A), str(wo))['title'] == long
    (A / 'digest.json').write_text(json.dumps({'document': {'title': 'L' * 900}}))          # 900 Latin characters: fewer tokens than the reserve
    assert NL.price_book(str(A), str(wo))['title'] == NL.RESERVE_TITLE
    wo.write_text('{}'); assert NL.price_book(str(A), str(wo)) is None

def test_below_the_limit_nothing_about_held_back_forms_is_written(tmp_path, monkeypatch):
    """#159: a run under its limits writes no held-back fields (the records of the regression books stay identical)."""
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch)
    lr, e = load(R / 'language_run.json'), load(R / 'language_run.json')['estimate']
    assert lr['held_back_count'] == 0 and not any(k.startswith('held_back_') and k != 'held_back_count' for k in lr)
    assert e['held_back'] == 0 and not any(k.startswith('held_back_') for k in e)

def test_an_audit_from_before_the_joined_reading_is_found_again(tmp_path, monkeypatch):
    """#150 (03 §2.1, review 02 M4): a stopped run's audit made before the joined reading (version 1, no `reading`) is
    found again with today's rules, so the estimate counts today's forms, and nothing is sent that wasn't estimated."""
    src, A, R = folders(tmp_path)
    old = load(A / 'lang_candidates.json')
    old['version'] = 1; old.pop('reading'); old['places'] = [p for p in old['places'] if p['form'] != 'ryōgen']
    json.dump(old, open(A / 'lang_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False)
    assert run(src, A, R, monkeypatch, '--dry-run') == []
    est = load(R / 'language_estimate.json')
    assert est['forms'] == 3                                      # ryōgen found again, not the old audit's two
    same = load(A / 'lang_candidates.json'); same['version'] = 2
    json.dump(old | {'version': 2, 'reading': {'rules': ['inrun'], 'asked': ['cross', 'inrun', 'join'], 'parents': 'not given'}},
              open(A / 'lang_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False)
    os.remove(R / 'language_estimate.json')
    assert run(src, A, R, monkeypatch, '--dry-run') == [] and load(R / 'language_estimate.json')['forms'] == 2   # today's: kept as saved
