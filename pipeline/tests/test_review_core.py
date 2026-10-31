"""test_review_core.py: the review page's reading-order cards and list (review/core.py), on a small digest.

    python -m pytest tests/test_review_core.py -q

The expected results follow docs/review-step.md ("What the page shows": group 5, the reading-order list).
"""
from review import core

def digest():
    return {'source': {'pages': 240}, 'figures': [{'obj': '9 0', 'page': 1, 'image': 'figures/9_0.png'}],
            'unowned_content': [{'page': 20, 'orphan_runs': 3, 'runs': [{'kind': 'orphan', 'text': '1. A note'}, {'kind': 'untagged', 'text': 'x'}]},
                                {'page': 50, 'orphan_runs': 2, 'runs': [{'kind': 'orphan', 'text': 'elsewhere'}]}],
            'reading_order': ['Sect pp1-10 depth1: Front', 'Sect pp11-200 depth1: Body']}

def entry(id_, first, last, parent=None, depth=1, top=True, under=None, firsts=()):
    return {'id': id_, 'parent': parent, 'style': 'Sect', 'first': first, 'last': last, 'depth': depth, 'text': id_, 'skip': False,
            'group': True, 'top': top, 'under': under, 'firsts': list(firsts)}

def order():
    """front 1-10, body 11-200 (ch1 11-100, ch2 101-200), notes 201-230 read last; the AI moves ch2 before PDF 231."""
    return [entry('front', 1, 10, firsts=[1]), entry('body', 11, 200, firsts=[11, 101, 231]),
            entry('ch1', 11, 100, 'body', 2, False, 'body', [11]), entry('ch2', 101, 200, 'body', 2, False, 'body', [101]),
            entry('notes', 201, 230, firsts=[201])]

WO = {'move_section': {'pages': [101, 200], 'before_page': 231, 'why': 'test'}, 'move_to_document_start': ['9 0'],
      'adopt_orphans': [{'label': 'chapter 1 notes', 'pages': [20, 20]}]}

def items(wo=WO, o=None):
    return {it['id']: it for it in core.build_items(wo, digest(), order() if o is None else o)}

def test_reading_order_decisions_get_their_own_cards_in_group_5():
    its = items()
    assert {i for i, it in its.items() if it['kind'] == 'Reading order'} == {'move_section', 'move_to_document_start:0', 'adopt_orphans:0'}
    assert all(its[i]['priority'] == 5 for i in ('move_section', 'move_to_document_start:0', 'adopt_orphans:0'))
    assert not any(i.startswith('key:') for i in its)                    # none left under "Other decisions"

def test_move_section_card_has_its_pages_and_a_preview():
    it = items()['move_section']
    assert it['pages'] == [101, 200] and it['context']['before_page'] == 231
    c = it['context']
    assert c['candidates'] == 1 and c['host_found'] and c['moved'] == 'ch2'
    assert [e['id'] for e in c['siblings_after']] == ['ch1', 'ch2']
    core.pages_to_render(list(items().values()), 240)

def test_move_section_preview_says_when_the_executor_will_refuse():
    c = items({'move_section': {'pages': [150, 160], 'before_page': 231}})['move_section']['context']
    assert c['candidates'] == 0 and 'moved' not in c

def test_move_section_preview_needs_the_full_order():
    c = items(o=core.reading_order(digest())['entries'])['move_section']['context']
    assert 'candidates' not in c                                           # older run: digest lines only, no preview

def test_adopt_orphans_card_lists_only_its_pages_orphan_runs():
    c = items()['adopt_orphans:0']['context']
    assert c['orphans'] == [{'page': 20, 'runs': ['1. A note'], 'count': 3}]

def test_move_to_document_start_card_shows_the_figure():
    it = items()['move_to_document_start:0']
    assert it['page'] == 1 and it['context']['figure'] == 'figures/9_0.png'

def test_deferrals_move_to_groups_6_and_7():
    its = items({'deferrals': [{'what': 'a', 'pages': [3, 4]}, {'what': 'b'}]})
    assert its['deferrals:0']['priority'] == 6 and its['deferrals:1']['priority'] == 7

def test_rejecting_reading_order_decisions_removes_them():
    its = list(items().values())
    wo = core.apply_decisions(WO, its, {'move_section': {'status': 'rejected'}, 'adopt_orphans:0': {'status': 'rejected'},
                                        'move_to_document_start:0': {'status': 'approved'}})
    assert 'move_section' not in wo and 'adopt_orphans' not in wo and wo['move_to_document_start'] == ['9 0']

def test_reading_order_from_fulltext_or_digest_lines():
    ro = core.reading_order(digest(), {'reading_order': order()})
    assert ro['detail'] and not ro['flat'] and ro['flagged'] == []
    ro = core.reading_order(digest())
    assert not ro['detail'] and [e['first'] for e in ro['entries']] == [1, 11]

def test_a_flat_tree_has_no_order_to_show():
    assert core.reading_order({'reading_order': []}, {'reading_order': []})['flat']

def test_a_changed_section_move_keeps_its_reason_and_gets_whole_numbers():
    its = list(items().values())
    wo = core.apply_decisions(WO, its, {'move_section': {'status': 'changed', 'value': {'pages': ['11', 100], 'before_page': '231'}}})
    assert wo['move_section'] == {'pages': [11, 100], 'before_page': 231, 'why': 'test'}

def test_save_previews_the_reviewers_pages_with_the_same_match():
    wo = {'move_section': {'pages': [101, 200], 'before_page': 11}}                 # ch2 before ch1
    pv = core.changed_move(wo, {'reading_order': {'entries': order()}}, {'move_section': {'status': 'changed'}})
    assert pv['pages'] == [101, 200] and pv['candidates'] == 1 and pv['moved'] == 'ch2'
    assert [e['id'] for e in pv['siblings_after']] == ['ch2', 'ch1']
    assert core.changed_move(wo, {'reading_order': {'entries': order()}}, {'move_section': {'status': 'approved'}}) is None

def test_flags_a_text_rule_will_hide_are_marked():
    es = [entry('body', 10, 60), dict(entry('folio', 6, 6), runs=['vi', ' Contents ']), dict(entry('real', 3, 3), runs=['A real paragraph'])]
    wo = {'artifacts': {'text_rules': [{'label': 'running head', 'pages': [1, 50], 'regex': r'\d+|[ivx]+|Contents', 'band': 'top'}]}}
    fl = core.reading_order({}, {'reading_order': es}, wo)['flagged']
    assert [(es[x['i']]['id'], x.get('hidden_by')) for x in fl] == [('folio', 'running head'), ('real', None)]
    assert all('hidden_by' not in x for x in core.reading_order({}, {'reading_order': es})['flagged'])   # no work order, no marks

# ------------------------------------------------------------------ findings no decision answers: cards marked seen, with a note
RULES = {'artifacts': {'text_rules': [{'label': 'running head', 'pages': [1, 50], 'regex': r'\d+|[ivx]+|Contents'},
                                      {'label': 'roman folios', 'pages': [1, 50], 'regex': r'[ivx]+'}]}}

def findings_case(wo=RULES):
    """body 10-60 read first; folio (6, a rule hides it), real (3, nothing hides it) and a figure caption on 12, read after
    the body, then a page jump on PDF 7."""
    es = [entry('body', 10, 60), dict(entry('folio', 6, 6), runs=['vi']), dict(entry('real', 3, 3), runs=['A real paragraph']),
          dict(entry('cap', 12, 12), runs=['Figure 1'])]
    ro = core.reading_order({}, {'reading_order': es, 'page_jumps': [{'page': 7, 'jumps_up': 3, 'runs': 20}]}, wo)
    return ro, {it['id']: it for it in core.build_items(wo, {'source': {'pages': 60}}, es, ro)}

def test_an_entry_two_rules_hide_names_both_by_card_id():
    ro, _ = findings_case()
    folio = next(x for x in ro['flagged'] if x['first'] == 6)
    assert [r['id'] for r in folio['hidden_by_rules']] == ['artifacts.text_rules:0', 'artifacts.text_rules:1']
    assert folio['hidden_by'] == 'running head'

def test_findings_no_rule_hides_get_seen_only_cards_in_group_5():
    ro, its = findings_case()
    f = {i: it for i, it in its.items() if it['key'] == 'reading_order'}
    assert set(f) == {'reading_order:away:real', 'reading_order:jump:7', 'reading_order:late'}
    assert all(it['priority'] == 5 and it['loc'] is None and it['edit'] is None for it in f.values())
    assert f['reading_order:away:real']['ai'] == {'finding': 'away', 'entry': 'real', 'pages': [3, 3], 'prev': 60, 'next': 12}
    assert f['reading_order:jump:7']['context']['jumps_up'] == 3
    assert f['reading_order:late']['context']['count_late'] == 1 and f['reading_order:late']['context']['late'][0]['page'] == 12
    assert 'reading_order:away:folio' not in its                       # a rule hides it: listed on the rule's card instead

def test_a_rule_card_lists_what_it_hides():
    _, its = findings_case()
    assert its['artifacts.text_rules:0']['context']['hides'] == [{'page': 6, 'text': 'folio', 'late': False}]
    assert its['artifacts.text_rules:1']['context']['hides'] == [{'page': 6, 'text': 'folio', 'late': False}]

def test_no_late_card_when_a_rule_hides_every_late_entry():
    wo = {'artifacts': {'text_rules': RULES['artifacts']['text_rules'] + [{'label': 'figure labels', 'pages': [1, 50], 'regex': r'Figure \d+'}]}}
    _, its = findings_case(wo)
    assert 'reading_order:late' not in its and its['artifacts.text_rules:2']['context']['hides'] == [{'page': 12, 'text': 'cap', 'late': True}]

def test_findings_change_nothing_in_the_work_order():
    _, its = findings_case()
    for st in ('seen', 'rejected'):
        wo = core.apply_decisions(RULES, list(its.values()), {i: {'status': st, 'note': 'fix by hand'} for i in its if i.startswith('reading_order:')})
        assert wo == RULES

def test_without_the_reading_order_there_are_no_finding_cards():
    assert not any(i.startswith('reading_order:') for i in items())
