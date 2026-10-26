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
