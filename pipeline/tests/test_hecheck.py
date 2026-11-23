"""test_hecheck.py: the AI's check of a PDF edited by hand (#100): lib/hecheck.py and handedit_check.py.

    python -m pytest tests/test_hecheck.py -q

The two-figure book of test_handedit.py, run with no AI call (DECIDE=none), edited (the red image swapped, a word changed)
and brought back for review. Every request goes to a fake `send`: nothing is sent anywhere and nothing costs anything.
"""
import os, sys, json, shutil, subprocess
import pytest
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_handedit import parent_run, swap_image, sh, sha  # noqa: E402
from lib import hecheck  # noqa: E402

PROMPT = open(os.path.join(os.path.dirname(PIPE), 'prompts', 'handedit_check_v1.md'), encoding='utf-8').read()

@pytest.fixture(scope='module')
def waiting(tmp_path_factory):
    """The edited copy at its review stop (no AI call): returns its run folder."""
    tmp = tmp_path_factory.mktemp('hecheck')
    src, P = parent_run(tmp)
    r = sh([sys.executable, 'handedit.py', 'export', P, '--to', str(tmp / 'copy.pdf'), '--by', 'Pat']); assert r.returncode == 0, r.stderr
    edited = swap_image(tmp / 'copy.pdf', tmp / 'edited.pdf', word=True)
    r = sh([sys.executable, 'handedit.py', 'import', P, edited, '--by', 'Pat', '--note', 'a better scan', '--label', 'he1'])
    assert r.returncode == 0, r.stdout + r.stderr
    C = os.path.join(os.path.dirname(P), 'he1')
    assert os.path.isfile(os.path.join(C, 'workorder.ai.json')) and not os.path.isfile(os.path.join(C, 'record.json'))
    return C

@pytest.fixture
def copy(waiting, tmp_path):
    """A scratch copy of the waiting run, so a test may write ai_check.json in it."""
    D = str(tmp_path / 'he1'); shutil.copytree(waiting, D); return D

NOSLEEP = lambda s: None

def make_plan(R, model='test/model'): return hecheck.plan(R, PROMPT, 'handedit_check_v1.md', model)

def ok(text, cost=0.01, finish='stop'):
    return {'resp': {'choices': [{'message': {'content': text}, 'finish_reason': finish}], 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': cost}}, 'seconds': 1.0}

def fenced(d): return '```json\n' + json.dumps(d) + '\n```'

def test_only_the_changed_figure_and_the_changed_page_are_sent(copy):
    p = make_plan(copy)
    assert [(f['page'], f['edit']) for f in p['items']] == [(1, 'new_image')]            # the swapped image's figure, not the blue one
    assert [t['page'] for t in p['texts']] == [1] and 'figurez' in p['texts'][0]['after'] and 'figures' in p['texts'][0]['before']
    msgs = p['messages'][1]['content']
    assert sum(1 for c in msgs if c['type'] == 'image_url') == 2                          # the figure and the page, nothing else
    assert p['messages'][0]['content'] == PROMPT and p['fingerprint'] and p['input_est'] > 0
    assert p['data']['figures'] == [{k: v for k, v in p['items'][0].items() if k not in ('old_alt', 'edit')}]

def test_the_old_alt_text_goes_in_as_context_only(copy):
    he = json.load(open(os.path.join(copy, '_handedit', 'hand_edit.json')))
    he['figures_lost'] = [{'page': 1, 'alt': 'A red square'}]
    p = hecheck.plan(copy, PROMPT, 'handedit_check_v1.md', 'm', targets_=(he, *hecheck.targets(copy)[1:]))
    text = ' '.join(c['text'] for c in p['messages'][1]['content'] if c['type'] == 'text')
    assert 'Alt text it had before the edit' in text and '"A red square"' in text and 'context only' in text

def test_the_reply_is_cut_to_what_was_sent(copy):
    p = make_plan(copy); obj = p['items'][0]['obj']
    reply = {'alt': [{'obj': obj, 'alt': 'A green square.'}, {'obj': '999 0', 'alt': 'Not sent'}, {'obj': obj, 'alt': ' '}],
             'page_figures': [{'page': 1, 'alt': 'not a page figure'}], 'retype': [{'obj': obj, 'type': 'H1'}],
             'text_pages': [{'page': 1, 'verdict': 'correction', 'why': 'figures became figurez'}, {'page': 7, 'verdict': 'damage', 'why': 'x'},
                            {'page': 1, 'verdict': 'fine', 'why': 'x'}]}
    out = hecheck.execute(copy, p, lambda body: ok(fenced(reply)))
    assert out['outcome'] == 'done' and out['kept']['alt'] == [{'obj': obj, 'alt': 'A green square.'}]
    assert out['kept']['text_pages'] == [{'page': 1, 'verdict': 'correction', 'why': 'figures became figurez'}]
    assert {'page_figures', 'retype', 'text_pages', 'alt'} <= {d['where'] for d in out['dropped']}
    a = hecheck.answers(hecheck.saved(copy))
    assert a['alt'] == {obj: 'A green square.'} and a['text'] == {1: {'verdict': 'correction', 'why': 'figures became figurez'}}

def test_the_request_asks_for_no_more_than_the_edit(copy):
    seen = []
    p = make_plan(copy)
    hecheck.execute(copy, p, lambda body: seen.append(body) or ok(fenced({})))
    b = seen[0]
    assert b['provider'] == {'data_collection': 'deny'} and b['usage'] == {'include': True} and b['max_tokens'] == p['max_tokens']

def test_a_saved_check_is_reused_only_for_the_same_request(copy):
    p = make_plan(copy)
    hecheck.execute(copy, p, lambda body: ok(fenced({})))
    s = hecheck.saved(copy)
    assert hecheck.reusable(s, p) and hecheck.reusable(s, make_plan(copy))               # the same files: the same request
    assert not hecheck.reusable(s, make_plan(copy, model='other/model'))                 # another model asks again
    assert not hecheck.reusable(dict(s, outcome='cut_off'), p)

def test_a_charged_reply_that_was_cut_off_is_kept_with_its_cost_but_not_reused(copy):
    p = make_plan(copy)
    out = hecheck.execute(copy, p, lambda body: ok('```json\n{"alt": [', cost=0.02, finish='length'))
    assert out['outcome'] == 'cut_off' and out['kept'] is None and hecheck.paid(copy) == 0.02
    assert not hecheck.reusable(hecheck.saved(copy), p) and 'cut off' in hecheck.words(hecheck.saved(copy))
    assert hecheck.answers(hecheck.saved(copy)) == {'alt': {}, 'page_figures': {}, 'decoration': {}, 'text': {}, 'deferrals': []}

def test_a_failed_request_is_sent_once_more_and_saves_nothing_when_nothing_was_charged(copy):
    calls = []
    with pytest.raises(hecheck.Stop, match='429'):
        hecheck.execute(copy, make_plan(copy), lambda body: calls.append(1) or {'resp': None, 'code': 429, 'message': 'slow down'}, sleep=NOSLEEP)
    assert len(calls) == 2 and hecheck.saved(copy) is None and hecheck.paid(copy) == 0                  # main's one retry rule (lib/aisend.py)

def test_a_failure_then_an_answer_is_one_check(copy):
    p = make_plan(copy); seq = iter([{'resp': None, 'code': 500, 'message': 'oops'}, ok(fenced({}), cost=0.01)])
    out = hecheck.execute(copy, p, lambda body: next(seq), sleep=NOSLEEP)
    assert out['outcome'] == 'done' and out['attempts'] == 2 and out['cost_usd'] == 0.01 and hecheck.paid(copy) == 0.01

def test_a_charge_that_is_not_known_counts_at_its_worst_case(copy):
    p = make_plan(copy)
    out = hecheck.execute(copy, p, lambda body: {'resp': None, 'timeout': True}, worst=0.04, sleep=NOSLEEP)     # sent, no reply in time, twice
    assert out['outcome'] == 'failed' and out['worst_usd'] == 0.08 and hecheck.paid(copy) == 0.08 and out['attempts'] == 2
    out = hecheck.execute(copy, p, lambda body: {'resp': None, 'timeout': True}, worst=0.04, sleep=NOSLEEP, limits={'check': (0.05, 0.0)})
    assert out['attempts'] == 1 and out['worst_usd'] == 0.04                                              # no room for a second one under the limit
    assert hecheck.paid(copy) == 0.12                                                                    # the first check's charge is still counted

def test_a_reply_that_reports_no_cost_counts_at_its_worst_case(copy):
    p = make_plan(copy); r = ok(fenced({})); del r['resp']['usage']['cost']
    out = hecheck.execute(copy, p, lambda body: r, worst=0.04, sleep=NOSLEEP)
    assert out['outcome'] == 'done' and out['cost_usd'] == 0 and out['worst_usd'] == 0.04 and hecheck.paid(copy) == 0.04

def test_an_earlier_checks_charge_is_kept_when_a_new_one_replaces_its_file(copy):
    from lib import costs
    p = make_plan(copy)
    hecheck.execute(copy, p, lambda body: ok('```json\n{"alt": [', cost=0.40, finish='length'), sleep=NOSLEEP)    # cut off: paid, not reused
    out = hecheck.execute(copy, p, lambda body: ok(fenced({}), cost=0.40), sleep=NOSLEEP)
    assert out['earlier_cost_usd'] == 0.4 and hecheck.paid(copy) == 0.8 and costs.book_spent(copy) == 0.8
    hecheck.from_reply(copy, p, fenced({}))                                                              # a saved reply never resets what was paid
    assert hecheck.paid(copy) == 0.8
    s = hecheck.summary(hecheck.saved(copy)); assert hecheck.total(s) == 0.8 and s['earlier_cost_usd'] == 0.8

def test_nothing_to_check_is_refused_with_the_reason(copy):
    f = os.path.join(copy, '_handedit', 'hand_edit.json'); he = json.load(open(f))
    he.update(figures_changed=[], figures_lost=[], text_pages=[]); json.dump(he, open(f, 'w'))
    with pytest.raises(hecheck.Stop, match='nothing to check'): make_plan(copy)

def test_a_finished_run_and_an_ordinary_run_are_refused(copy, tmp_path):
    open(os.path.join(copy, 'record.json'), 'w').write('{}')
    with pytest.raises(hecheck.Stop, match='finished'): hecheck.targets(copy)
    with pytest.raises(hecheck.Stop, match='no hand edit'): hecheck.targets(str(tmp_path))

def test_the_text_window_keeps_the_difference_and_its_surroundings():
    a = 'x' * 5000 + 'the figures.' + 'y' * 5000; b = 'x' * 5000 + 'the figurez.' + 'y' * 5000
    wa, wb = hecheck.window(a, b)
    assert 'figures' in wa and 'figurez' in wb and len(wa) <= hecheck.TEXT_CHARS + 2 and wa.startswith('…')
    assert hecheck.window('same', 'same2') == ('same', 'same2')

def test_the_script_uses_a_saved_reply_at_no_cost_from_a_relative_folder(copy, tmp_path):
    """--reply and RUN_DIR are taken from where the command runs (#144); no network, no cost."""
    p = make_plan(copy); obj = p['items'][0]['obj']
    work = tmp_path / 'elsewhere'; work.mkdir()
    (work / 'reply.txt').write_text(fenced({'alt': [{'obj': obj, 'alt': 'A green square.'}]}))
    rel = os.path.relpath(copy, work)
    r = subprocess.run([sys.executable, os.path.join(PIPE, 'handedit_check.py'), rel, '--reply', 'reply.txt'], cwd=work, capture_output=True, text=True,
                       env=dict(os.environ, HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9'))
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'no cost' in r.stdout and hecheck.answers(hecheck.saved(copy))['alt'] == {obj: 'A green square.'} and hecheck.paid(copy) == 0

def test_the_script_refuses_a_missing_folder_without_sending(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(PIPE, 'handedit_check.py'), str(tmp_path / 'nope')], capture_output=True, text=True,
                       env=dict(os.environ, HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9'))
    assert r.returncode == 1 and r.stderr.startswith('refused:') and 'Traceback' not in r.stderr

# ------------------------------------------------------------------ the review page's cards (review/core.py)
from review import core  # noqa: E402

def drafted(copy, reply=None, cost=0.0):
    """The check run on the copy with a fake send, then its answers put into review_items.json (as handedit_check.py does)."""
    p = make_plan(copy); obj = p['items'][0]['obj']
    rep = reply if reply is not None else {'alt': [{'obj': obj, 'alt': 'A green square.'}],
                                          'text_pages': [{'page': 1, 'verdict': 'correction', 'why': 'figures became figurez'}],
                                          'deferrals': [{'what': 'Cover page description', 'why': 'the picture may sit in another object', 'pages': [1]}]}
    hecheck.execute(copy, p, lambda body: ok(fenced(rep), cost=cost))
    assert core.refresh_ai_check(copy)
    data = core.load(os.path.join(copy, 'review_items.json'))
    return obj, data, next(x for x in data['addable']['alt'] if x['target'] == obj)

def test_the_ai_draft_is_the_cards_default_and_marked(copy):
    obj, data, card = drafted(copy)
    assert card['default'] == 'A green square.' and card['context']['suggested_by_ai'] and 'suggested_from_before_edit' not in card['context']
    he = data['hand_edit']; t = next(x for x in he['targets'] if x['target'] == obj)
    assert t['ai'] and t['suggest'] == 'A green square.' and he['ai_check']['outcome'] == 'done' and 'ai_estimate' not in he
    assert he['text_checks'] == [{'page': 1, 'verdict': 'correction', 'why': 'figures became figurez'}]
    again = json.loads(json.dumps(data)); core.hand_edit_ai(copy, again); assert again == data          # the same again changes nothing

def test_nothing_is_added_until_a_person_adds_it_and_the_wording_follows(copy):
    obj, data, card = drafted(copy)
    wo = {}
    assert core.add_entries(wo, [], data['addable'], 'Pat') == [] and wo == {}                          # no approval: nothing in the order
    core.add_entries(wo, [{'kind': 'alt', 'target': obj, 'value': 'A green square. '}], data['addable'], 'Pat')
    assert wo['alt'] == [{'obj': obj, 'alt': 'A green square. ', 'why': 'added by Pat in review', 'ai_draft': 'approved'}]
    wo = {}; core.add_entries(wo, [{'kind': 'alt', 'target': obj, 'value': 'A bright green square.'}], data['addable'], 'Pat')
    assert wo['alt'][0]['ai_draft'] == 'changed'
    other = next(x for x in data['addable']['alt'] if x['target'] != obj)                                # a card the AI never drafted
    wo = {}; core.add_entries(wo, [{'kind': 'alt', 'target': other['target'], 'value': 'Mine'}], data['addable'], 'Pat')
    assert 'ai_draft' not in wo['alt'][0]

def test_a_draft_that_checks_out_survives_the_work_order_check(copy):
    from lib import workorder_check
    obj, data, card = drafted(copy)
    wo = {}; core.add_entries(wo, [{'kind': 'alt', 'target': obj, 'value': card['default']}], data['addable'], 'Pat', mark=True)
    digest = core.load(os.path.join(copy, '_audit', 'digest.json'))
    assert workorder_check.check(wo, digest, set(), set()) == [] and wo['alt'][0]['ai_draft'] == 'approved'

def test_a_lost_figures_old_alt_is_replaced_only_when_the_ai_says_so(copy):
    he = json.load(open(os.path.join(copy, '_handedit', 'hand_edit.json'))); he['figures_lost'] = [{'page': 1, 'alt': 'A red square'}]
    p = hecheck.plan(copy, PROMPT, 'handedit_check_v1.md', 'm', targets_=(he, *hecheck.targets(copy)[1:])); obj = p['items'][0]['obj']
    hecheck.execute(copy, p, lambda body: ok(fenced({'alt': [{'obj': obj, 'alt': 'A red square'}]})))        # it still fits: returned unchanged
    assert core.refresh_ai_check(copy)
    t = next(x for x in core.load(os.path.join(copy, 'review_items.json'))['hand_edit']['targets'] if x['target'] == obj)
    assert t['ai'] and t['suggest'] == 'A red square'

def test_a_new_image_the_ai_calls_decoration_is_a_note_not_a_draft(copy):
    p = make_plan(copy); obj = p['items'][0]['obj']
    hecheck.execute(copy, p, lambda body: ok(fenced({'artifacts': {'elements': [{'obj': obj, 'label': 'a plain ornament'}]}})))
    assert core.refresh_ai_check(copy)
    data = core.load(os.path.join(copy, 'review_items.json')); card = next(x for x in data['addable']['alt'] if x['target'] == obj)
    t = next(x for x in data['hand_edit']['targets'] if x['target'] == obj)
    assert card['default'] == '' and t['ai_decoration'] == 'a plain ornament' and not t.get('ai') and card['context']['ai_decoration'] == 'a plain ornament'

def test_an_estimate_not_yet_spent_is_shown_and_a_failed_check_gives_no_draft(copy):
    json.dump({'worst_case_usd': 0.05}, open(os.path.join(copy, hecheck.ESTIMATE), 'w'))
    assert core.refresh_ai_check(copy)
    assert core.load(os.path.join(copy, 'review_items.json'))['hand_edit']['ai_estimate'] == 0.05
    p = make_plan(copy); hecheck.execute(copy, p, lambda body: ok('no json here'), sleep=NOSLEEP)       # unreadable (twice): kept, with no answers
    assert core.refresh_ai_check(copy)
    he = core.load(os.path.join(copy, 'review_items.json'))['hand_edit']
    assert he['ai_check']['outcome'] == 'unreadable' and 'ai_estimate' not in he and he['text_checks'] == []
    assert all(not t.get('ai') for t in he['targets'])

# ------------------------------------------------------------------ the whole loop: approve, apply, record
def test_an_approved_draft_is_recorded_with_its_cost_and_the_report_says_who_decided(copy):
    from lib import costs
    obj, data, card = drafted(copy, cost=0.02)
    wo_p = os.path.join(copy, 'workorder.json'); wo = core.load(wo_p) or {}
    assert not core.add_entries(wo, [{'kind': 'alt', 'target': obj, 'value': card['default']}], data['addable'], 'Pat')
    json.dump(wo, open(wo_p, 'w'))
    he = json.load(open(os.path.join(copy, '_handedit', 'hand_edit.json')))
    P = he['parent']['run']; src = os.path.join(copy, '_handedit', he['edited']['file'])
    r = sh([sys.executable, 'review_workorder.py', copy, '--reviewer', 'Pat', '--note', 'checked']); assert r.returncode == 0, r.stdout + r.stderr
    r = sh(['bash', 'run_api.sh', src, 'book', 'he1'], RUN_DIR=copy, OUT=he['parent']['output']); assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-1000:]
    rec = json.load(open(os.path.join(copy, 'record.json'))); md = open(os.path.join(copy, 'review.md'), encoding='utf-8').read()
    assert rec['hand_edit']['ai_check']['cost_usd'] == 0.02 and rec['cost_total_usd'] == 0.02
    assert rec['ai_call']['cost_usd'] == 0.02 and rec['ai_call']['no_model'] and rec['ai_call']['hand_edit_check']['model'] == 'test/model'
    assert rec['run']['no_model']                                                                       # the work order was still a person's
    assert '"A green square." (drafted by the AI, approved by Pat)' in md and 'The AI checked the edit before the review' in md
    assert 'figures became figurez' in md and 'the AI\'s check of the hand edit cost $0.020' in md and 'None' not in md
    assert 'The AI left this to a person: **Cover page description** (PDF 1): the picture may sit in another object.' in md
    assert costs.after_line(copy) == f'AI Cost: $0.02 ({costs.CHECK_WORDS})' and costs.actual(copy)['calls'] == 1
    assert hecheck.paid(copy) == 0.02                                                                    # the working file stays with the run

# ------------------------------------------------------------------ handedit.py --ai-check
def test_ai_check_goes_with_the_review_path_only(waiting, tmp_path):
    he = json.load(open(os.path.join(waiting, '_handedit', 'hand_edit.json')))
    P, edited = he['parent']['run'], os.path.join(waiting, '_handedit', he['edited']['file'])
    r = sh([sys.executable, 'handedit.py', 'import', P, edited, '--by', 'Pat', '--note', 'n', '--label', 'he-x', '--to', 'pipeline', '--ai-check', '--no-run'])
    assert r.returncode == 1 and 'goes with --to review' in r.stderr and not os.path.exists(os.path.join(os.path.dirname(P), 'he-x'))
    r = sh([sys.executable, 'handedit.py', 'import', P, edited, '--by', 'Pat', '--note', 'n', '--label', 'he-y', '--ai-check', '--no-run'])
    assert r.returncode == 0, r.stderr
    assert 'handedit_check.py' in r.stdout and 'to ask the AI to check the edit' in r.stdout
    r = sh([sys.executable, 'handedit.py', 'import', P, edited, '--by', 'Pat', '--note', 'n', '--label', 'he-z', '--no-run'])
    assert 'handedit_check' not in r.stdout                                                               # without the flag: as before

# ------------------------------------------------------------------ figures with no image, the base PDF, the prompt, the model
def test_a_figure_with_no_image_is_reported_not_skipped_silently(copy):
    for f in os.listdir(os.path.join(copy, '_audit', 'figures')): os.remove(os.path.join(copy, '_audit', 'figures', f))
    he = json.load(open(os.path.join(copy, '_handedit', 'hand_edit.json'))); rest = hecheck.targets(copy)[1:]
    p = hecheck.plan(copy, PROMPT, 'handedit_check_v1.md', 'm', targets_=(he, *rest))                   # the changed page still goes
    assert p['items'] == [] and p['lacking'] == [1] and [t['page'] for t in p['texts']] == [1] and 'had no image to send (PDF 1)' in p['note']
    out = hecheck.execute(copy, p, lambda body: ok(fenced({'text_pages': [{'page': 1, 'verdict': 'unsure', 'why': 'cannot tell'}]})), sleep=NOSLEEP)
    assert out['sent']['lacking'] == [1] and 'no image to send' in hecheck.words(out)
    assert hecheck.estimate(p, 3e-6, 15e-6)['note'] == p['note']
    with pytest.raises(hecheck.Stop, match='no figure had an image to send'):                           # the figure alone: said, not "no figure with a card"
        hecheck.plan(copy, PROMPT, 'handedit_check_v1.md', 'm', targets_=(dict(he, text_pages=[]), *rest))

def test_the_base_pdf_is_hashed_once_per_plan(copy, monkeypatch):
    n = []; real = hecheck._sha_file
    monkeypatch.setattr(hecheck, '_sha_file', lambda path: n.append(path) or real(path))
    make_plan(copy)
    assert len(n) == 1

def test_the_script_and_the_app_read_the_same_prompt_file():
    from webapp import spend as SP
    path = hecheck.prompt_path(PIPE)
    assert path and os.path.samefile(path, os.path.join(os.path.dirname(PIPE), 'prompts', 'handedit_check_v1.md'))
    import hashlib
    assert SP.current_check_prompt() == hashlib.sha256(open(path, encoding='utf-8').read().encode()).hexdigest()[:16]

def test_the_script_takes_the_model_from_MODEL_and_refuses_an_auto_choice(copy):
    env = dict(os.environ, HTTPS_PROXY='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9')
    r = subprocess.run([sys.executable, os.path.join(PIPE, 'handedit_check.py'), copy, '--dry-run'], capture_output=True, text=True, env=dict(env, MODEL='auto:sonnet'))
    assert r.returncode == 1 and r.stderr.startswith('refused:') and 'not a model' in r.stderr
    r = subprocess.run([sys.executable, os.path.join(PIPE, 'handedit_check.py'), copy, '--dry-run'], capture_output=True, text=True, env=dict(env, MODEL='anthropic/test-model'))
    assert 'anthropic/test-model' in r.stdout                                                           # used (the lookup then stops: no network here)

# ------------------------------------------------------------------ what the AI left to a person (information only)
def test_what_the_ai_left_to_a_person_reaches_the_page_data_cleaned_and_never_the_work_order(copy):
    junk = ['not a dict', {'what': '', 'why': ''}, {'what': 'Cover', 'why': 'check it', 'pages': [3, 'x', True, 1, 3]}, {'why': 'only a reason'}]
    obj, data, card = drafted(copy, reply={'deferrals': junk})
    assert data['hand_edit']['ai_deferrals'] == [{'what': 'Cover', 'why': 'check it', 'pages': [1, 3]},
                                                 {'what': 'Something the AI left to a person', 'why': 'only a reason', 'pages': []}]
    assert card['default'] == '' and not any(t.get('ai') for t in data['hand_edit']['targets'])         # a deferral drafts nothing
    wo = {}; assert core.add_entries(wo, [], data['addable'], 'Pat') == [] and wo == {}                  # and adds nothing
    assert 'he.ai_deferrals' in open(os.path.join(PIPE, 'review', 'page.html'), encoding='utf-8').read()

def test_no_deferral_means_no_line_anywhere(copy):
    obj, data, card = drafted(copy, reply={'alt': [{'obj': 'x', 'alt': 'dropped: not sent'}]})
    assert data['hand_edit']['ai_deferrals'] == [] and hecheck.answers(hecheck.saved(copy))['deferrals'] == []

# ------------------------------------------------------------------ #100's open question, pinned: the check is optional
def test_a_check_that_gave_no_draft_never_holds_the_review(copy):
    """A hand edit is a DECIDE=none run, so lib/aistatus.py finds no unfinished AI step: a cut-off, unreadable or failed check leaves the
    review open (the run page offers Get a New Estimate instead). Changing this is a decision, not a fix."""
    from lib import aistatus
    p = make_plan(copy)
    hecheck.execute(copy, p, lambda body: ok('```json\n{"alt": [', cost=0.02, finish='length'), sleep=NOSLEEP)
    assert hecheck.saved(copy)['outcome'] == 'cut_off'
    assert aistatus.status(copy)['held'] is False
    hecheck.execute(copy, p, lambda body: {'resp': None, 'timeout': True}, worst=0.04, sleep=NOSLEEP)
    assert hecheck.saved(copy)['outcome'] == 'failed' and aistatus.status(copy)['held'] is False
