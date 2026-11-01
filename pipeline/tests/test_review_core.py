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

def save_data(wo=WO, o=None):
    o = order() if o is None else o
    return {'items': core.build_items(wo, digest(), o), 'reading_order': {'entries': o}}

def test_save_previews_the_reviewers_pages_with_the_same_match():
    data = save_data()
    dec = {'move_section': {'status': 'changed', 'value': {'pages': [101, 200], 'before_page': 11}}}   # ch2 before ch1
    pv = core.move_previews(data, dec, [], {})['move_section']
    assert pv['pages'] == [101, 200] and pv['candidates'] == 1 and pv['moved'] == 'ch2'
    assert [e['id'] for e in pv['siblings_after']] == ['ch2', 'ch1']
    assert core.move_previews(data, {'move_section': {'status': 'approved'}}, [], {})['move_section']['moved'] == 'ch2'
    assert core.move_previews(data, {'move_section': {'status': 'rejected'}}, [], {}) == {}           # no move left

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

def test_rules_that_each_match_part_of_a_section_remove_it_together():
    """A running head whose page number one rule matches and whose title another does: removed by the two together."""
    es = [entry('body', 10, 60), dict(entry('rh', 3, 3), runs=['186', 'Notes to Pages 7–11'])]
    wo = {'artifacts': {'text_rules': [{'label': 'notes heads', 'pages': [1, 50], 'regex': r'Notes to Pages \d+–\d+'},
                                       {'label': 'page numbers', 'pages': [1, 50], 'regex': r'\d+'}]}}
    x = core.reading_order({}, {'reading_order': es}, wo)['flagged'][0]
    assert x['run_rules'] == [['artifacts.text_rules:1'], ['artifacts.text_rules:0']]
    assert [r['id'] for r in x['hidden_by_rules']] == ['artifacts.text_rules:1', 'artifacts.text_rules:0']
    one = {'artifacts': {'text_rules': wo['artifacts']['text_rules'][:1]}}                # the title alone: not removed
    assert 'hidden_by_rules' not in core.reading_order({}, {'reading_order': es}, one)['flagged'][0]

def caption_case(wo, kid_styles=('CAP',)):
    es = [entry('body', 10, 60), dict(entry('cap', 12, 12), kid_styles=list(kid_styles), runs=['Map of the island']),
          dict(entry('tbl', 14, 14), kid_styles=['TN'], runs=['Table 1'])]
    ro = core.reading_order({}, {'reading_order': es}, wo)
    return ro, {it['id']: it for it in core.build_items(wo, {'source': {'pages': 60}}, es, ro)}

def test_a_late_caption_the_captions_decision_ties_is_left_off_the_late_card():
    ro, its = caption_case({'captions': {'style': 'CAP'}})
    assert [x.get('tied_by', {}).get('id') for x in ro['late']] == ['key:captions', None]
    c = its['reading_order:late']['context']
    assert c['count_late'] == 1 and c['late'][0]['page'] == 14 and c['tied'] == 1 and c['removed'] == 0
    assert its['key:captions']['context']['ties'] == [{'page': 12, 'text': 'cap', 'late': True}]

def test_no_tie_without_a_captions_decision_or_child_styles():
    ro, _ = caption_case({})
    assert not any('tied_by' in x for x in ro['late'])
    ro, _ = caption_case({'captions': {'style': 'CAP'}}, kid_styles=())          # an audit from before kid_styles
    assert not any('tied_by' in x for x in ro['late'])
    ro, _ = caption_case({'captions': {'style': 'CAP'}}, kid_styles=('CAP', 'P'))  # not captions only
    assert not any('tied_by' in x for x in ro['late'])

# ------------------------------------------------------------------ adding a section move; the figures the executor moves
def away_case(wo=None):
    """Under one part: front (PDF 1), body 10-60, then 'about' (PDF 3) read after it, then 'end' (PDF 70): about belongs
    before PDF 10 (the executor needs a page of the part before the moved section, here the front)."""
    es = [entry('part', 1, 70, firsts=[1, 10, 3, 70]), entry('front', 1, 1, 'part', 2, False, 'part', [1]),
          entry('body', 10, 60, 'part', 2, False, 'part', [10]),
          entry('about', 3, 3, 'part', 2, False, 'part', [3]), entry('end', 70, 70, 'part', 2, False, 'part', [70])]
    return es, core.reading_order({}, {'reading_order': es}, wo or {})

def test_a_move_can_be_added_for_a_section_out_of_place_when_the_ai_made_none():
    es, ro = away_case()
    t = core.addable({}, {'source': {'pages': 70}}, ro)['move_section'][0]
    assert t['id'] == 'add:move_section:about' and t['edit'] == 'move'
    assert t['default'] == {'pages': [3, 3], 'before_page': 10} and t['context']['candidates'] == 1 and t['context']['host_found']
    assert 'move_section' not in core.addable({'move_section': {'pages': [3, 3], 'before_page': 10}}, {'source': {'pages': 70}}, ro)   # the AI moves it
    t = core.addable({'move_section': {'pages': [70, 70], 'before_page': 1}}, {'source': {'pages': 70}}, ro)['move_section'][0]
    assert t['context']['after_moves'] == 1                                # offered beside another AI move, previewed after it
    three = [{'pages': [p, p], 'before_page': p + 1} for p in (20, 30, 40)]
    assert 'move_section' not in core.addable({'move_section': three}, {'source': {'pages': 70}}, ro)   # already 3
    assert 'move_section' not in core.addable({}, {'source': {'pages': 70}})              # no reading order given

def test_an_added_move_is_written_and_a_second_one_refused():
    es, ro = away_case()
    adds = core.addable({}, {'source': {'pages': 70}}, ro)
    wo = {}
    add = [{'kind': 'move_section', 'target': 'about', 'value': {'pages': ['3', 3], 'before_page': '10'}}]
    assert core.add_entries(wo, add, adds, 'Kim') == []
    assert wo['move_section'] == [{'pages': [3, 3], 'before_page': 10, 'why': 'added by Kim in review'}]
    wo = {'move_section': {'pages': [70, 70], 'before_page': 1}}                    # the AI's single move: a list of two after
    assert core.add_entries(wo, add, adds) == [] and [m['pages'] for m in wo['move_section']] == [[70, 70], [3, 3]]
    three = [{'pages': [p, p], 'before_page': p + 1} for p in (20, 30, 40)]
    refused = core.add_entries({'move_section': three}, add, adds)
    assert refused and 'at most 3 section moves' in refused[0]['why']

def test_saved_added_move_gets_its_preview():
    es, _ = away_case()
    data = {'items': [], 'reading_order': {'entries': es}}
    def pv(v): return core.move_previews(data, {}, [{'kind': 'move_section', 'target': 'about', 'value': v}], {})['add:move_section:about']
    p = pv({'pages': ['3', 3], 'before_page': '10'})
    assert p['pages'] == [3, 3] and p['before_page'] == 10 and p['candidates'] == 1
    p = pv({'pages': [3, 3], 'before_page': 999})
    assert p['candidates'] == 1 and p['host_found'] is False                 # nothing holds pages from PDF 999 on: refused
    assert core.move_previews(data, {}, [], {}) == {}

def test_captions_are_in_the_reading_order_group():
    its = items({'captions': {'style': 'CAP'}})
    assert its['key:captions']['priority'] == 5 and its['key:captions']['kind'] == 'Reading order'

def test_figure_moves_from_the_trial_run_get_one_card():
    es, ro = away_case()
    moves = [{'page': 12, 'label': '3', 'was_after_page': 60, 'now_after_page': 12}]
    def card(dr):
        r = dict(ro, dryrun=dr)
        return {it['id']: it for it in core.build_items({}, {'source': {'pages': 70}}, es, r)}.get('reading_order:figures')
    c = card({'figure_moves': moves, 'seconds': 1.0})
    assert c['priority'] == 5 and c['context']['count_moves'] == 1 and c['context']['moves'] == moves and c['pages'] == [12, 12]
    assert card({'figure_moves': []}) is None                                                     # no moves: no card
    assert card(None) is None                                                                     # no trial run (an older run)
    c = card({'figure_moves': None, 'why': 'skipped: REVIEW_DRYRUN=off'})
    assert c['label'] == 'Figure moves not worked out' and c['context']['not_worked_out'].startswith('skipped')

def test_no_move_is_offered_where_the_executor_would_refuse_it():
    """A top-level section (sands' cover): no section around it to move it within."""
    es = [entry('body', 10, 60, firsts=[10]), entry('about', 3, 3, firsts=[3]), entry('end', 70, 70, firsts=[70])]
    ro = core.reading_order({}, {'reading_order': es}, {})
    assert ro['flagged'] and 'move_section' not in core.addable({}, {'source': {'pages': 70}}, ro)

def test_a_flag_that_only_a_removed_block_causes_is_cleared():
    """translation's About the Author (PDF 254) read after a stray block on PDF 255 that a rule removes: in place after."""
    es = [entry('part', 1, 255, firsts=[1, 255, 254]), entry('book', 1, 250, 'part', 2, False, 'part', [1]),
          dict(entry('stray', 255, 255, 'part', 2, False, 'part', [255]), runs=['hn hk io']),
          dict(entry('about', 254, 254, 'part', 2, False, 'part', [254]), runs=['About the Author'])]
    wo = {'artifacts': {'text_rules': [{'label': 'stray', 'pages': [1, 257], 'regex': r'(hn|hk|io| )+'}]}}
    ro = core.reading_order({}, {'reading_order': es}, wo)
    about = next(x for x in ro['flagged'] if es[x['i']]['id'] == 'about')
    assert about['cleared_by'] == [[['artifacts.text_rules:0']]] and ro['removed'] == [2]
    its = {it['id']: it for it in core.build_items(wo, {'source': {'pages': 257}}, es, ro)}
    assert 'reading_order:away:about' not in its
    assert {'page': 254, 'text': 'about', 'late': False, 'cleared': True} in its['artifacts.text_rules:0']['context']['hides']
    assert 'reading_order:away:about' in {it['id'] for it in core.build_items({}, {'source': {'pages': 257}}, es, core.reading_order({}, {'reading_order': es}, {}))}

# ------------------------------------------------------------------ the preview leaves out what the text rules remove first
def stray_case():
    """translation: About the Author (PDF 254) read after a block on PDF 255 that the letters rule removes. apply.py removes
    the block before it moves sections, so a move of 254 before 255 finds nothing on 255 and is refused."""
    es = [entry('part', 1, 255, firsts=[1, 255, 254]), entry('book', 1, 250, 'part', 2, False, 'part', [1]),
          dict(entry('stray', 255, 255, 'part', 2, False, 'part', [255]), runs=['hn hk io']),
          dict(entry('about', 254, 254, 'part', 2, False, 'part', [254]), runs=['About the Author'])]
    wo = {'artifacts': {'text_rules': [{'label': 'letters', 'pages': [1, 257], 'regex': r'(hn|hk|io| )+'}]},
          'move_section': {'pages': [254, 254], 'before_page': 255, 'why': 'test'}}
    return es, wo

def test_removed_ids_are_the_entries_reading_order_removes():
    es, wo = stray_case()
    ro = core.reading_order({}, {'reading_order': es}, wo)
    assert core.removed_ids(es, wo) == ro['removed_by'] == {'stray': ['letters']}
    assert core.removed_ids(es, {}) == {}

def test_a_move_onto_a_block_the_rules_remove_is_refused_and_says_why():
    es, wo = stray_case()
    assert core.move_preview(es, 254, 254, 255)['host_found']                       # on the original's tags it would work
    pv = core.move_preview(es, 254, 254, 255, core.removed_ids(es, wo))
    assert pv['candidates'] == 1 and pv['host_found'] is False and pv['refused_by_rules'] == ['letters']
    ro = core.reading_order({}, {'reading_order': es}, wo)
    c = {it['id']: it for it in core.build_items(wo, {'source': {'pages': 257}}, es, ro)}['move_section']['context']
    assert c['host_found'] is False and c['refused_by_rules'] == ['letters']

def test_a_section_the_rules_remove_is_no_candidate():
    es, wo = stray_case()
    pv = core.move_preview(es, 255, 255, 254, core.removed_ids(es, wo))
    assert pv['candidates'] == 0 and pv['refused_by_rules'] == ['letters']

def test_rejecting_the_rule_brings_the_block_back_in_the_saved_preview():
    es, wo = stray_case()
    data = {'items': core.build_items(wo, {'source': {'pages': 257}}, es), 'reading_order': {'entries': es}}
    assert core.move_previews(data, {}, [], wo)['move_section']['host_found'] is False
    reviewed = {'move_section': wo['move_section']}                               # the letters rule rejected
    pv = core.move_previews(data, {}, [], reviewed)['move_section']
    assert pv['host_found'] and pv['lands_before'] == 'stray' and 'refused_by_rules' not in pv
    add = [{'kind': 'move_section', 'target': 'about', 'value': {'pages': [254, 254], 'before_page': 255}}]
    data['items'] = []
    assert core.move_previews(data, {}, add, wo)['add:move_section:about']['host_found'] is False
    assert core.move_previews(data, {}, add, {})['add:move_section:about']['host_found']

def test_removed_siblings_are_left_out_of_the_preview_lists():
    es, _ = stray_case()
    pv = core.move_preview(es, 254, 254, 1, {'stray': ['letters']})
    assert 'stray' not in [e['id'] for e in pv['siblings_before'] + pv['siblings_after']]

def test_the_move_card_carries_the_trial_run():
    es, wo = stray_case()
    ro = dict(core.reading_order({}, {'reading_order': es}, wo), dryrun={'figure_moves': [], 'section_move': {'refused': '1 candidate sections, host found: False'}})
    c = {it['id']: it for it in core.build_items(wo, {'source': {'pages': 257}}, es, ro)}['move_section']['context']
    assert c['trial'] == {'refused': '1 candidate sections, host found: False'}

# ------------------------------------------------------------------ several moves; the figures card decides fix_figure_order
def two_away():
    """Under one part: front 1, body 10-60, then 'about' (3) and 'end' (70) read after 'tail' (80): two sections to put back."""
    es = [entry('part', 1, 80, firsts=[1, 10, 80, 3, 70]), entry('front', 1, 1, 'part', 2, False, 'part', [1]),
          entry('body', 10, 60, 'part', 2, False, 'part', [10]), entry('tail', 80, 80, 'part', 2, False, 'part', [80]),
          entry('about', 3, 3, 'part', 2, False, 'part', [3]), entry('end', 70, 70, 'part', 2, False, 'part', [70])]
    wo = {'move_section': [{'pages': [3, 3], 'before_page': 10}, {'pages': [70, 70], 'before_page': 80}]}
    return es, wo

def test_two_moves_get_two_cards_each_previewed_after_the_earlier():
    es, wo = two_away()
    its = {it['id']: it for it in core.build_items(wo, {'source': {'pages': 80}}, es)}
    a, b = its['move_section'], its['move_section:1']
    assert a['loc'] == ['move_section', 0] and b['loc'] == ['move_section', 1] and b['context']['move_number'] == 2
    assert [e['id'] for e in a['context']['siblings_after']] == ['front', 'about', 'body', 'tail', 'end']
    assert [e['id'] for e in b['context']['siblings_before']] == ['front', 'about', 'body', 'tail', 'end']   # sees the first move
    assert [e['id'] for e in b['context']['siblings_after']] == ['front', 'about', 'body', 'end', 'tail']
    assert b['context']['flags_after'] == 0 and b['context']['after_moves'] == 1

def test_changing_or_rejecting_the_second_move_touches_only_it():
    es, wo = two_away()
    its = core.build_items(wo, {'source': {'pages': 80}}, es)
    out = core.apply_decisions(wo, its, {'move_section:1': {'status': 'changed', 'value': {'pages': ['70', 70], 'before_page': '79'}}})
    assert out['move_section'] == [{'pages': [3, 3], 'before_page': 10}, {'pages': [70, 70], 'before_page': 79}]
    out = core.apply_decisions(wo, its, {'move_section': {'status': 'rejected'}})
    assert out['move_section'] == [{'pages': [70, 70], 'before_page': 80}]
    out = core.apply_decisions(wo, its, {'move_section': {'status': 'rejected'}, 'move_section:1': {'status': 'rejected'}})
    assert 'move_section' not in out
    pvs = core.move_previews({'items': its, 'reading_order': {'entries': es}}, {'move_section': {'status': 'rejected'}}, [], wo)
    assert list(pvs) == ['move_section:1'] and 'after_moves' not in pvs['move_section:1']       # now the first move made

def figures(wo):
    es, ro = away_case()
    r = dict(ro, dryrun={'figure_moves': [{'page': 12, 'label': '3', 'was_after_page': 60, 'now_after_page': 12}]})
    return {it['id']: it for it in core.build_items(wo, {'source': {'pages': 70}}, es, r)}

def test_rejecting_the_figures_card_turns_the_figure_step_off():
    its = figures({'fix_figure_order': True})
    assert 'key:fix_figure_order' not in its                                 # the figures card is that decision
    f = its['reading_order:figures']
    assert not f['context'].get('ai_off')
    assert core.apply_decisions({'fix_figure_order': True}, list(its.values()), {f['id']: {'status': 'rejected'}})['fix_figure_order'] is False
    assert core.apply_decisions({}, list(its.values()), {f['id']: {'status': 'approved'}}) == {}

def test_when_the_ai_turned_it_off_rejecting_turns_it_on():
    its = figures({'fix_figure_order': False})
    f = its['reading_order:figures']
    assert f['context']['ai_off']
    assert core.apply_decisions({'fix_figure_order': False}, list(its.values()), {f['id']: {'status': 'rejected'}}) == {}
    assert core.apply_decisions({'fix_figure_order': False}, list(its.values()), {f['id']: {'status': 'approved'}}) == {'fix_figure_order': False}

def test_without_a_figures_card_the_key_card_stays():
    es, ro = away_case()
    its = {it['id'] for it in core.build_items({'fix_figure_order': True}, {'source': {'pages': 70}}, es, ro)}
    assert 'key:fix_figure_order' in its and 'reading_order:figures' not in its    # no trial run (an older run)

def test_a_dropped_second_move_links_to_its_own_card():
    es, wo = two_away()
    its = core.build_items(wo, {'source': {'pages': 80}}, es)
    assert core.card_of(its, {'where': 'move_section', 'item': wo['move_section'][1], 'why': 'bad pages'}) == 'move_section:1'
