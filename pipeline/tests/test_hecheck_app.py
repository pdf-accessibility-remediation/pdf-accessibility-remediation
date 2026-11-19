"""test_hecheck_app.py: the AI's check of a hand edit (#100) in the cost interface, the Spend gate, the app's routes and the
record's wording. No model, no network: every estimate and saved check here is synthetic, and no job here may send.

    python -m pytest tests/test_hecheck_app.py -q
"""
import os, sys, json
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from lib import costs, hecheck, origin  # noqa: E402
from webapp import config, jobs, spend as SP, runs as RN  # noqa: E402
from test_webapp import setup, settings, fake, wait  # noqa: E402,F401

MODEL, _ = SP.current_model_and_prompt()
PROMPT = SP.current_check_prompt()

def waiting_copy(t, name='bk', label='he1'):
    """An edited copy at its review stop, as far as the app can tell (synthetic files)."""
    R = t / 'runs' / name / label; (R / '_handedit').mkdir(parents=True, exist_ok=True)
    (R / 'workorder.ai.json').write_text('{}')
    (R / '_handedit' / 'hand_edit.json').write_text(json.dumps({'schema': 'hand_edit/1', 'to': 'review', 'by': 'Pat', 'figures_changed': [{'page': 1, 'alt': 'x'}]}))
    return R

def estimate_file(R, worst=0.03, model=MODEL, prompt=PROMPT, credit=14.3, **kw):
    e = {'schema': 'handedit-check-estimate/1', 'model': model, 'prompt_file': 'handedit_check_v1.md', 'prompt_sha256': prompt, 'fingerprint': 'f1',
         'figures': 2, 'text_pages': 1, 'input_est': 3000, 'max_tokens': 3500, 'worst_case_usd': worst, 'cap_usd': 2.0, 'price_per_million': [3.0, 15.0], 'note': None, **kw}
    if credit is not None: e['credit_available_usd'] = credit
    (R / '_handedit').mkdir(parents=True, exist_ok=True)
    (R / hecheck.ESTIMATE).write_text(json.dumps(e)); return e

def saved_check(R, cost=0.02, outcome='done'):
    (R / '_handedit').mkdir(parents=True, exist_ok=True)
    (R / hecheck.SAVED).write_text(json.dumps({'schema': hecheck.FORMAT, 'cost_usd': cost, 'outcome': outcome, 'model': 'm', 'prompt_file': 'handedit_check_v1.md',
                                              'prompt_sha256': 'abc', 'date': '2026-11-18T10:00:00', 'sent': {'figures': [{'obj': '1 0', 'page': 1}], 'text_pages': []},
                                              'kept': {'alt': [{'obj': '1 0', 'alt': 'A green square.'}]}, 'dropped': []}))

# ------------------------------------------------------------------ lib/costs.py
def test_the_estimate_has_the_shape_the_pages_read(setup):
    R = waiting_copy(setup); estimate_file(R)
    e = costs.estimate(str(R), 'handedit_check')
    assert e['schema'] == 'cost-estimate/1' and e['kind'] == 'handedit_check' and e['ceiling_usd'] == 0.03 and e['requests'] == 1 and e['figures'] == 2
    assert e['blocked'] is None and e['fits'] == {'per_call': True, 'per_book': True, 'credit': True}
    assert e['bounds'] == {'MAX_USD': 0.04, 'BOOK_MAX_USD': 0.04} and e['expected'] is None
    fp = e['fingerprint']
    estimate_file(R, credit=99.0); assert costs.estimate(str(R), 'handedit_check')['fingerprint'] == fp      # the credit is not covered
    estimate_file(R, fingerprint='f2'); assert costs.estimate(str(R), 'handedit_check')['fingerprint'] != fp  # another request is

def test_no_estimate_file_is_no_estimate(setup):
    assert costs.estimate(str(waiting_copy(setup)), 'handedit_check') is None

@pytest.mark.parametrize('kw,code', [({'worst': 2.5}, 'per_call'), ({'credit': 0.001}, 'credit'), ({'credit': None}, 'no_credit'), ({'model': 'openai/gpt-5'}, 'model')])
def test_the_estimate_is_blocked_like_the_work_orders(setup, kw, code):
    R = waiting_copy(setup); estimate_file(R, **{('worst' if k == 'worst' else k): v for k, v in kw.items()} if 'worst' not in kw else {'worst_case_usd': kw['worst']})
    assert costs.estimate(str(R), 'handedit_check')['blocked']['code'] == code

def test_the_check_counts_toward_the_pdfs_money_and_the_after_line(setup):
    R = waiting_copy(setup)
    (R / 'run.json').write_text(json.dumps({'no_model': 'no AI call: a PDF edited by hand', 'usage': {'cost_usd': 0}}))
    assert costs.book_spent(str(R)) == 0 and costs.after_line(str(R)) == 'AI Cost: ' + costs.NO_MODEL_WORDS
    saved_check(R, cost=0.02)
    a = costs.actual(str(R))
    assert a['usd'] == 0.02 and a['calls'] == 1 and a['no_model'] and a['check_usd'] == 0.02 and costs.book_spent(str(R)) == 0.02
    assert costs.after_line(str(R)) == f'AI Cost: $0.02 ({costs.CHECK_WORDS})'

def test_a_cut_off_check_that_was_charged_still_counts(setup):
    R = waiting_copy(setup); saved_check(R, cost=0.05, outcome='cut_off')
    assert hecheck.paid(str(R)) == 0.05 and costs.book_spent(str(R)) == 0.05

def test_a_finished_record_counts_the_check_once(tmp_path):
    rec = {'run': {'no_model': 'no AI call: a PDF edited by hand', 'usage': {'cost_usd': 0}}, 'cost_total_usd': 0.02, 'document': {'pages': 4},
           'hand_edit': {'ai_check': {'cost_usd': 0.02, 'outcome': 'done'}}}
    a = costs.actual(str(tmp_path), rec)
    assert a['usd'] == 0.02 and a['calls'] == 1 and a['no_model']

# ------------------------------------------------------------------ lib/origin.py
def test_ai_call_shows_the_checks_cost_and_still_says_no_work_order_call():
    rec = {'run': {'no_model': 'no AI call: a PDF edited by hand'}, 'document': {'pages': 4},
           'hand_edit': {'ai_check': {'cost_usd': 0.021, 'model': 'anthropic/x', 'prompt_file': 'handedit_check_v1.md', 'prompt_sha256': 'abc', 'date': '2026-11-18'}}}
    ai = origin.summary(rec)
    assert ai['cost_usd'] == 0.021 and ai['no_model'] and ai['hand_edit_check']['model'] == 'anthropic/x'
    cost, model = origin.words(ai)
    assert '$0.021' in cost and 'no AI call for the work order' in cost and 'handedit_check_v1' in model and 'None' not in cost + model
    assert origin.words(origin.summary({'run': {'no_model': 'no AI call: x'}}))[0] == '$0: no AI call'   # no check: as before

# ------------------------------------------------------------------ webapp/spend.py
def test_authorize_binds_the_job_to_the_estimate_shown(setup):
    s = settings(setup); R = waiting_copy(setup); estimate_file(R)
    fp = costs.estimate(str(R), 'handedit_check', costs.limits_of(s))['fingerprint']
    a = SP.authorize(s, 'handedit_check', 'bk/he1', str(R), fp)
    assert a['argv'][1:] == ['handedit_check.py', str(R), '--model', MODEL] and a['argv'][0] == sys.executable
    assert a['env_set'] == {'AUTO': '1', 'MAX_USD': '0.04', 'BOOK_MAX_USD': '0.04'} and a['extra']['fingerprint'] == fp and not a['extra']['test']
    with pytest.raises(SP.Refused) as e: SP.authorize(s, 'handedit_check', 'bk/he1', str(R), 'not-the-fingerprint')
    assert str(e.value) == SP.CHANGED

def test_authorize_refuses_an_estimate_for_other_instructions_or_a_model_that_changed(setup):
    s = settings(setup); R = waiting_copy(setup)
    for kw in ({'prompt': 'deadbeefdeadbeef'}, {'model': 'anthropic/not-the-default'}):
        estimate_file(R, **kw)
        fp = costs.estimate(str(R), 'handedit_check', costs.limits_of(s))['fingerprint']
        with pytest.raises(SP.Refused) as e: SP.authorize(s, 'handedit_check', 'bk/he1', str(R), fp)
        assert str(e.value) == SP.OUT_OF_DATE

def test_authorize_refuses_what_the_limits_block(setup):
    s = settings(setup); R = waiting_copy(setup); estimate_file(R, credit=0.001)
    fp = costs.estimate(str(R), 'handedit_check', costs.limits_of(s))['fingerprint']
    with pytest.raises(SP.Refused, match='credit'): SP.authorize(s, 'handedit_check', 'bk/he1', str(R), fp)

def test_test_mode_uses_a_saved_reply_and_never_sends(setup):
    s = settings(setup); R = waiting_copy(setup); estimate_file(R, credit=None)
    reply = setup / 'replies'; reply.mkdir(); s['test_reply_dir'] = str(reply)
    fp = costs.estimate(str(R), 'handedit_check', costs.limits_of(s))['fingerprint']
    with pytest.raises(SP.Refused, match='no saved test reply'): SP.authorize(s, 'handedit_check', 'bk/he1', str(R), fp)
    (reply / 'handedit_check.txt').write_text('```json\n{}\n```')
    a = SP.authorize(s, 'handedit_check', 'bk/he1', str(R), fp)
    assert a['argv'][-2:] == ['--reply', str(reply / 'handedit_check.txt')] and a['env_set'] == {} and a['extra']['test']

# ------------------------------------------------------------------ webapp/runs.py
def test_the_estimate_job_is_free_and_the_spend_job_is_paid(setup):
    s = settings(setup); R = waiting_copy(setup)
    j = RN.start_ai_check(s, 'bk/he1', str(R), 'estimate')
    assert j['kind'] == 'ai-estimate' and not j['paid'] and j['argv'][1:] == ['handedit_check.py', str(R), '--dry-run'] and 'AUTO' not in j['env_set'] and 'AUTO' not in j['env']
    jobs.update(s['jobs'], j['id'], status='done')
    estimate_file(R)
    fp = costs.estimate(str(R), 'handedit_check', costs.limits_of(s))['fingerprint']
    sp = RN.start_ai_check(s, 'bk/he1', str(R), 'spend', {'fingerprint': fp})
    assert sp['kind'] == 'spend' and sp['paid'] and sp['env_set']['AUTO'] == '1' and sp['fingerprint'] == fp and 'AI check' in sp['what']
    assert RN.heading(sp) == 'Processing: AI Check of the Hand Edit'
    assert RN.heading(j) == 'Processing: Cost Estimate (AI Check of the Hand Edit)'

def test_the_spend_job_needs_the_estimate_that_was_shown(setup):
    s = settings(setup); R = waiting_copy(setup); estimate_file(R)
    with pytest.raises(ValueError, match='estimate changed'): RN.start_ai_check(s, 'bk/he1', str(R), 'spend', {'fingerprint': 'stale'})
    assert not [j for j in jobs.all_jobs(s['jobs']) if j['kind'] == 'spend']

def test_only_an_edited_copy_waiting_for_its_review_can_be_checked(setup):
    s = settings(setup)
    plain = setup / 'runs' / 'bk' / 'plain'; plain.mkdir(parents=True); (plain / 'workorder.ai.json').write_text('{}')      # waiting, but not a hand edit
    with pytest.raises(ValueError, match='hand edit'): RN.start_ai_check(s, 'bk/plain', str(plain), 'estimate')
    done = waiting_copy(setup, label='he2'); (done / 'record.json').write_text('{}')
    with pytest.raises(ValueError, match='hand edit'): RN.start_ai_check(s, 'bk/he2', str(done), 'estimate')
    rev = waiting_copy(setup, label='he3'); (rev / 'review.json').write_text('{}')
    with pytest.raises(ValueError, match='review is finished'): RN.start_ai_check(s, 'bk/he3', str(rev), 'estimate')
    assert RN.ai_check_view(s, str(plain)) is None and RN.ai_check_view(s, str(done)) is None and RN.ai_check_view(s, str(rev)) is None

def test_the_run_page_offers_the_estimate_then_the_result(setup):
    s = settings(setup); R = waiting_copy(setup)
    v = RN.ai_check_view(s, str(R)); assert v == {'done': None, 'estimate': None}
    estimate_file(R)
    v = RN.ai_check_view(s, str(R))
    assert v['estimate']['ceiling_usd'] == 0.03 and v['estimate']['figures'] == 2 and v['estimate']['blocked'] is None and v['done'] is None
    saved_check(R)
    v = RN.ai_check_view(s, str(R))
    assert v['done']['outcome'] == 'done' and v['done']['cost_usd'] == 0.02 and 'None' not in v['done']['words']

def test_no_other_job_kind_may_carry_the_check_paid(setup):
    s = settings(setup); R = waiting_copy(setup)
    with pytest.raises(ValueError): jobs.create(s['jobs'], 'ai-estimate', 'bk/he1', ['true'], config.child_env(s, {'AUTO': '1'}), env_set={'AUTO': '1'}, R=str(R))
    with pytest.raises(ValueError): jobs.create(s['jobs'], 'ai-estimate', 'bk/he1', ['true'], config.child_env(s), paid=True, R=str(R))
