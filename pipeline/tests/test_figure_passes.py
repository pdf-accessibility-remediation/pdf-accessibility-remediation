"""test_figure_passes.py: figure requests past the 100-image limit (issue #63; handoff/alt-text-passes 01, 03, 04).

    python -m pytest tests/test_figure_passes.py -q

lib/figpasses.py on synthetic digests: the split, what a figure request sees, the prompt copied from workorder_v10.md,
one retry per request, each reply cut to its own figures, the merge and the saved form. No book content; nothing is
sent anywhere (send is a fake).
"""
import os, re, sys, json, copy
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import figpasses as F

PROMPTS = os.path.join(os.path.dirname(HERE), 'prompts')
V10 = open(os.path.join(PROMPTS, 'workorder_v10.md'), encoding='utf-8').read()
FIG = open(os.path.join(PROMPTS, 'figures_v1.md'), encoding='utf-8').read()

def fig(i, page=None, area=10.0, px=(400, 300)):
    return {'obj': f'{1000 + i} 0', 'page': page or (i // 2 + 1), 'label': str(page or (i // 2 + 1)), 'alt': None, 'single_run': True,
            'next': {'style': 'Caption', 'text': f'Figure {i}.'}, 'image': f'figures/p{i}.png', 'area_pct': area, 'image_px': list(px)}

def digest(n, pages=None, extra=None):
    figs = [fig(i) for i in range(n)]
    N = pages or (n // 2 + 3)
    d = {'source': {'file': 'x.pdf', 'pages': N, 'sha256': 'ab' * 32}, 'document': {'title': 'T', 'lang': 'en'},
         'text_quality': {'pages_with_full_page_image': 0}, 'figures': figs,
         'page_figures_format': 'pages with no tags', 'page_figures': [],
         'unowned_content_format': 'per page: …', 'unowned_content': [{'page': 1, 'in_figure': 1, 'runs': [{'kind': 'untagged', 'text': 'A'}]},
                                                                      {'page': N, 'runs': []}],
         'pdfua_check_format': 'veraPDF …', 'page_map_format': 'page|printed label|first tagged line',
         'page_map': [f'{p}|{p}|line {p}' for p in range(1, N + 1)],
         'headings': [{'obj': '9 0', 'level': 'H2', 'page': 1, 'label': '1', 'text': 'One'}, {'obj': '8 0', 'level': 'H2', 'page': 30, 'label': '30', 'text': 'Two'}],
         'styles': [], 'elements': []}
    d.update(extra or {})
    return d

# ------------------------------------------------------------------ the split
def shrinker(per_image=1000):
    def shrink(items, budget):
        enc = [('x' * per_image, f['image_px']) for f in items]
        return (enc, 800, 85) if sum(len(b) for b, _ in enc) <= budget else None
    return shrink

def sheets(n, size=500): return [('s' * size, [1000, 800])] * n

@pytest.mark.parametrize('n_fig, n_sheet, first, later', [
    (101, 0, 100, [1]),
    (90, 21, 79, [11]),          # figures fit by count, the sheets didn't: 21 sheets + 79 figures, then 11
    (250, 3, 97, [100, 53]),
    (543, 0, 100, [100, 100, 100, 100, 43]),
])
def test_split(n_fig, n_sheet, first, later):
    items = digest(n_fig)['figures']
    p = F.plan(items, sheets(n_sheet), 100, 20_000_000, shrinker())
    assert len(p['first']) == first and [len(c) for c, _ in p['later']] == later
    assert [f['obj'] for f in p['first'] + [f for c, _ in p['later'] for f in c]] == [f['obj'] for f in items]   # order kept

def test_budget_only_case_needs_no_figure_request():
    """C1: everything fits by count, a sheet was cut by size only: once sheets are reserved and the figures shrunk, the
    plan has no figure request, so decide.py sends one request with no new fields."""
    items = digest(60)['figures']
    p = F.plan(items, sheets(5, 2000), 100, 70_000, shrinker(1000))
    assert len(p['first']) == 60 and p['later'] == []

def test_over_budget_refuses_before_any_call():
    with pytest.raises(F.Refused):
        F.plan(digest(150)['figures'], [], 100, 50_000, shrinker(1000))        # a figure request's chunk over budget (cut 2)
    with pytest.raises(F.Refused):
        F.plan(digest(10)['figures'], sheets(100), 100, 20_000_000, shrinker())  # sheets leave no room

# ------------------------------------------------------------------ what a figure request sees
def test_context_carries_each_field_and_its_format_line():
    d = digest(4, pages=40, extra={'unowned_content': [{'page': 1, 'in_figure': 1, 'runs': []}, {'page': 33, 'runs': []}]})
    d['page_figures'] = [{'obj': 'page 40', 'page': 40, 'label': '40', 'image': 'figures/page_040.png', 'image_px': [600, 800]}]
    pc = {'tool': 'veraPDF', 'rules': [{'rule': '7.3-1', 'description': 'alt', 'key': 'alt', 'objs': ['1000 0', '5555 0'], 'examples': []}]}
    wo1 = {'captions': {'style': 'Caption'}, 'artifacts': {'untagged': [{'pages': [1, 1], 'where': 'in_figure'}]}}
    items = d['figures'][:2] + d['page_figures']
    data = F.context(d, pc, items, wo1, [{'obj': '1003 0', 'page': 2, 'alt': 'A map.'}])
    assert [f['obj'] for f in data['figures']] == ['1000 0', '1001 0'] and data['page_figures'][0]['page'] == 40
    assert data['text_quality'] == d['text_quality'] and data['document'] == d['document']
    assert [u['page'] for u in data['unowned_content']] == [1]
    assert data['pdfua_check']['rules'][0]['objs'] == ['1000 0']                      # cut to its figures
    assert {int(l.split('|')[0]) for l in data['page_map']} == {1, 2, 39, 40}         # its pages and their neighbours
    assert [h['text'] for h in data['headings']] == ['One', 'Two']
    assert data['captions'] == {'style': 'Caption'} and data['style_examples'][0]['alt'] == 'A map.'
    assert all(f.get('in_figure_text_hidden_by_first_request') for f in data['figures'])   # page 1: in-figure text hidden
    for k in ('unowned_content', 'pdfua_check', 'page_map', 'page_figures', 'style_examples'):   # C2
        assert data[k + '_format']

# ------------------------------------------------------------------ the prompt: copied, and every field it names present
def v10_line(prefix):
    return next(l for l in V10.split('\n') if l.startswith(prefix))

def comment_block(prefix):
    """A work-order line of v10 and the // comment lines under it."""
    ls = V10.split('\n'); i = next(i for i, l in enumerate(ls) if l.startswith(prefix)); out = [ls[i]]
    for l in ls[i + 1:]:
        if l.strip().startswith('//'): out.append(l)
        else: break
    return out

COPIED_LINES = ['- Everything inside the digest', "- Never change the book's", '- Refer to elements only', '- If you are not sure',
                '- Cite pages as', '3. Figures:', '9. Machine-check failures:', 'Reply with the JSON object only']
COPIED_BLOCKS = ['  "artifacts": {', '    "elements":   [', '  "alt": [', '  "page_figures": [', '  "deferrals": [']
FIELDS = ['source', 'document', 'text_quality', 'figures', 'page_figures', 'unowned_content', 'pdfua_check', 'page_map', 'headings']

def field_text(name):
    """v10's description of one digest field: `name` and its parenthesis (balanced), as the digest section writes it."""
    line = v10_line('`source`, `document`')
    i = line.index(f'`{name}`'); j = i + len(name) + 2
    if line[j:j + 2] != ' (': return line[i:j]
    depth, k = 0, j + 1
    while True:
        depth += {'(': 1, ')': -1}.get(line[k], 0); k += 1
        if depth == 0: return line[i:k]

def test_copied_rules_match_v10_word_for_word():
    fig_lines = FIG.split('\n')
    for p in COPIED_LINES: assert v10_line(p) in fig_lines, p
    for p in COPIED_BLOCKS:
        for l in comment_block(p): assert l in fig_lines, l
    fields = '\n'.join(fig_lines)
    for name in FIELDS: assert field_text(name) in fields, name

# backticked names in the copied lines that are not digest fields a figure request must carry, each with its reason
NOT_FIELDS = {'obj': 'a figure entry\'s own field', 'page': 'a figure entry\'s own field', 'label': 'a figure entry\'s own field',
              'pages': 'a deferral field', 'deferrals': 'a key the request writes', 'artifacts.elements': 'a key the request writes',
              'key': 'a field of each pdfua_check rule', 'objs': 'a field of each pdfua_check rule',
              'page_figure': 'a marker inside unowned_content runs', 'image_is_whole_page': 'a figure field the audit sets when needed',
              'digest.styles': 'a figure request decides no styles', 'PDF N (printed X)': 'the citation pattern',
              'PDF 7–234 (printed 1–221)': 'the citation pattern', '_format': 'the format keys, checked below',
              'style_examples_format': 'checked below',
              'in_figure_text_hidden_by_first_request': 'a figure entry\'s field, set when it applies (tested above)'}

def test_every_field_the_copied_rules_name_is_in_the_request():
    d = digest(4, extra={'unowned_content': [{'page': 1, 'runs': []}]})
    d['page_figures'] = [{'obj': 'page 3', 'page': 3, 'label': '3', 'image': 'figures/page_003.png', 'image_px': [600, 800]}]
    pc = {'tool': 'veraPDF', 'rules': [{'rule': '7.3-1', 'key': 'alt', 'objs': ['1000 0']}]}
    data = F.context(d, pc, d['figures'] + d['page_figures'], {'captions': {'style': 'C'}}, [{'obj': '1 0', 'page': 1, 'alt': 'x'}])
    named = set(re.findall(r'(?<!`)`([^`\n]+)`(?!`)', FIG))
    for n in sorted(named):
        if n in NOT_FIELDS or n in F.ALLOWED: continue
        assert n in data, f'`{n}` is named in figures_v1.md but missing from the figure request\'s data'
    for k in data:                                       # C2: every field of the digest that has a _format line keeps it
        if k + '_format' in d: assert k + '_format' in data, k

# ------------------------------------------------------------------ examples and the probe
def test_examples_are_deterministic_spread_and_validated():
    d = digest(60); wo = {'alt': [{'obj': f['obj'], 'alt': f'alt {i}'} for i, f in enumerate(d['figures']) if i % 3]}
    ex = F.examples(wo, d)
    assert len(ex) == 10 and ex == F.examples(copy.deepcopy(wo), d)
    assert all(e['obj'] in {a['obj'] for a in wo['alt']} for e in ex)
    pr, _ = F.probe(wo, d, 20, ex)
    assert len(pr) == 20 and not set(pr) & {e['obj'] for e in ex}
    assert F.examples(wo, d) == ex                       # C4: the examples do not depend on the probe

# ------------------------------------------------------------------ one retry per request
def ok(text='```json\n{"alt": []}\n```', cost=0.01, finish='stop'):
    return {'resp': {'choices': [{'message': {'content': text}, 'finish_reason': finish}],
                     'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'cost': cost}}, 'seconds': 1.0}

def req(k='2', worst=0.4): return {'pass': k, 'items': digest(3)['figures'], 'body': {}, 'worst': worst, 'max_tokens': 32000}

def run_with(outs, cap=5.0, spent=0.0, reqs=None):
    reqs = reqs or [req()]; it = iter(outs); waits = []
    b = F.Budget(cap, spent, [r['worst'] for r in reqs])
    res = F.run(reqs, lambda body: next(it), b, sleep=waits.append, say=lambda *a: None)
    return res, b, waits

def test_uncharged_429_is_retried_once_after_a_pause():
    res, b, waits = run_with([{'resp': None, 'code': 429, 'message': 'rate limited'}, ok()])
    assert res[0]['outcome'] == 'done' and waits == [60] and len(res[0]['calls']) == 2 and b.spent == pytest.approx(0.01)

def test_two_failures_give_a_failed_request_with_its_reason():
    res, _, _ = run_with([{'resp': None, 'code': 429}, {'resp': None, 'code': 429}])
    assert res[0]['outcome'] == 'failed' and res[0]['reason'] == 'OpenRouter 429, twice'

def test_cut_off_is_not_retried():
    res, b, waits = run_with([ok(finish='length', cost=0.3)])
    assert res[0]['outcome'] == 'failed' and 'cut off' in res[0]['reason'] and waits == [] and b.spent == pytest.approx(0.3)

def test_unreadable_charged_reply_is_retried_only_with_room():
    res, _, _ = run_with([ok('no json', cost=0.2), ok()])
    assert res[0]['outcome'] == 'done'
    res, _, _ = run_with([ok('no json', cost=0.2)], cap=0.5)      # 0.5 - 0.2 spent - 0.4 reserved < 0
    assert res[0]['outcome'] == 'failed' and 'no room' in res[0]['reason']

def test_timeout_counts_its_worst_case():
    res, b, _ = run_with([{'resp': None, 'timeout': True}, ok(cost=0.05)])
    assert res[0]['outcome'] == 'done' and b.spent == pytest.approx(0.45)

def test_a_timeout_records_its_worst_case_and_tells_the_caller_once():
    """06 M1: what a restart counts toward the book cap is written here (decide.py's on_timeout keeps run.json up to date)."""
    seen = []; r = dict(req(worst=0.4), on_timeout=seen.append)
    res, _, _ = run_with([{'resp': None, 'timeout': True}, ok(cost=0.05)], reqs=[r])
    assert seen == [r] and res[0]['calls'][0]['worst_usd'] == 0.4 and 'worst_usd' not in res[0]['calls'][1]

# ------------------------------------------------------------------ scope and merge
def test_scope_keeps_only_its_own_figures_and_keys():
    items = digest(4)['figures'][:2] + [{'obj': 'page 9', 'page': 9}]
    reply = {'alt': [{'obj': '1000 0', 'alt': 'a'}, {'obj': '1003 0', 'alt': 'b'}], 'page_figures': [{'page': 9, 'alt': 'p'}, {'page': 8, 'alt': 'q'}],
             'artifacts': {'elements': [{'obj': '1001 0', 'type': 'Layout'}], 'text_rules': [{}]}, 'retype': [{'obj': '1000 0'}],
             'deferrals': [{'what': 'x', 'why': 'y'}]}
    kept, dropped = F.scope(reply, items, '2')
    assert kept['alt'] == [{'obj': '1000 0', 'alt': 'a'}] and kept['page_figures'] == [{'page': 9, 'alt': 'p'}]
    assert kept['artifacts'] == {'elements': [{'obj': '1001 0', 'type': 'Layout'}]} and kept['deferrals']
    assert sorted(x['where'] for x in dropped) == ['alt', 'artifacts.text_rules', 'page_figures', 'retype']

def test_merge_one_decision_per_figure_from_the_request_that_saw_it():
    wo = {'alt': [{'obj': '1000 0', 'alt': 'first'}, {'obj': '1005 0', 'alt': 'unseen'}], 'retype': [{'obj': '1005 0', 'type': 'P'}],
          'actual_text': [{'obj': '1006 0', 'text': 'x'}], 'artifacts': {'elements': [{'obj': '1006 0'}]}, 'captions': {'style': 'C'}}
    where = {'1005 0': '2', '1006 0': '3'}
    results = [{'pass': '2', 'outcome': 'done', 'kept': {'alt': [{'obj': '1005 0', 'alt': 'seen'}]}},
               {'pass': '3', 'outcome': 'failed', 'kept': None}]
    dropped = F.merge(wo, results, where)
    assert wo['alt'] == [{'obj': '1000 0', 'alt': 'first'}, {'obj': '1005 0', 'alt': 'seen'}]
    assert wo['retype'] == [] and wo['actual_text'] == [] and wo['artifacts']['elements'] == [] and wo['captions']
    whys = {(d['where'], d['why']) for d in dropped}
    assert ('alt', 'decided in figure request 2, which saw the image') in whys
    assert ('artifacts.elements', 'its image was in figure request 3, which did not finish') in whys

def test_deferral_wording_is_plain():
    d = F.deferral(3, 'failed', [5, 2, 5])
    assert d == {'what': 'Alt text for 3 figures', 'why': "The AI's request for these figures did not finish, so a person writes their alt text.", 'pages': [2, 5]}
    assert not re.search(r'[A-Z_]{4,}|\d{3}|request \d', d['what'] + d['why'])      # no settings, codes or request numbers

# ------------------------------------------------------------------ the saved form
def test_record_and_matches():
    d = digest(5); first, later = d['figures'][:3], d['figures'][3:]
    side = F.record(first, [{'ids': [1, 20]}], {'version': F.NOTE_VERSION}, [{'pass': '2', 'items': later, 'outcome': 'done', 'reply_text': '{}'}],
                    lambda r: {'model': 'm'})
    assert side['format'] == F.FORMAT and side['passes'][0]['pass'] == '2' and side['first']['sheets'] == [[1, 20]]
    today = {f['obj']: f for f in d['figures']}
    assert F.matches(side['passes'][0]['objs'], today)
    today['1004 0'] = dict(today['1004 0'], image_px=[401, 300])                       # one crop changed size
    assert not F.matches(side['passes'][0]['objs'], today)
    assert F.side_fingerprint(side) == F.side_fingerprint(json.loads(json.dumps(side)))

# ------------------------------------------------------------------ the answers file beside a saved reply
from lib import replies

def multi_record():
    side = F.record(digest(3)['figures'][:2], [], {'version': F.NOTE_VERSION}, [{'pass': '2', 'items': digest(3)['figures'][2:], 'outcome': 'done', 'reply_text': '{}'}],
                    lambda r: {'model': 'm'})
    return {'raw_reply': '{"alt": []}', 'raw_reply_passes': side, 'document': {'file': 'x.pdf', 'sha256': 'ab'},
            'run': {'model': 'm', 'figure_passes': {'requests': 1, 'fingerprint': F.side_fingerprint(side)}}}

def test_replies_write_the_answers_file_only_for_a_run_with_figure_requests(tmp_path):
    rec = multi_record(); rp = tmp_path / 'reply.txt'
    assert replies.write(rec, str(rp)) == {'figure_passes': {'requests': 1, 'fingerprint': rec['run']['figure_passes']['fingerprint']}}
    assert json.load(open(str(rp) + '.passes.json')) == rec['raw_reply_passes']
    one = tmp_path / 'one.txt'
    assert replies.write({'raw_reply': '{}', 'run': {'model': 'm'}}, str(one)) == {} and not os.path.exists(str(one) + '.passes.json')

def test_replay_to_carries_the_answers_file(tmp_path):
    from review import sessions as S
    R = tmp_path / 'run'; R.mkdir(); (R / 'record.json').write_text(json.dumps(multi_record()))
    reply, _ = S.replay_to(str(R), str(tmp_path / 'new'))
    assert os.path.exists(reply + '.passes.json') and json.load(open(reply + '.meta.json'))['figure_passes']['requests'] == 1
