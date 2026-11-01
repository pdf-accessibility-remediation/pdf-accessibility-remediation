"""test_readorder.py: the reading-order rules shared by audit.py, apply.py, verify.py and the review page.

    python -m pytest tests/test_readorder.py -q

The expected results follow docs/verapdf.md (the section-order check) and docs/review-step.md (the reading-order list).
"""
from lib import readorder as ro

def E(id_, first, last=None, parent=None, depth=1, skip=False, style='Sect'):
    return {'id': id_, 'parent': parent, 'style': style, 'first': first, 'last': first if last is None else last,
            'depth': depth, 'text': id_, 'skip': skip}

def flagged(es): return [es[x['i']]['id'] for x in ro.out_of_order(es)]

# out_of_order
def test_in_printed_order_flags_nothing():
    assert flagged([E('a', 1, 10), E('b', 11, 20), E('c', 21, 30)]) == []

def test_a_section_read_out_of_order_is_flagged():
    es = [E('a', 1, 10), E('c', 21, 30), E('b', 11, 20), E('d', 31, 40)]
    assert flagged(es) == ['b']
    x = ro.out_of_order(es)[0]
    assert (x['first'], x['last'], x['prev'], x['next']) == (11, 20, 30, 31)

def test_the_small_misplaced_entry_is_flagged_not_the_long_one():
    # an InDesign folio story on PDF 6 read before the main story that starts on PDF 2
    assert flagged([E('folio', 6), E('main', 2, 23), E('next', 24, 40)]) == ['folio']

def test_a_child_is_never_compared_with_its_parent():
    es = [E('part', 1, 40), E('ch1', 1, 20, parent='part', depth=2), E('ch2', 21, 40, parent='part', depth=2), E('back', 41, 50)]
    assert flagged(es) == []

def test_nested_siblings_are_checked_inside_their_parent_only():
    es = [E('p1', 1, 20), E('a', 11, 20, parent='p1', depth=2), E('b', 1, 10, parent='p1', depth=2), E('p2', 21, 30)]
    assert flagged(es) == ['b']                             # same weight: the one read first stays in place

def test_skipped_entries_are_never_flagged_and_never_the_reference():
    es = [E('a', 1, 10), E('fig', 30, skip=True, style='Div'), E('b', 11, 20)]
    assert flagged(es) == []

def test_entries_with_no_pages_are_left_out():
    assert flagged([E('a', 1, 10), {'id': 'x', 'parent': None, 'first': None, 'last': None}, E('b', 11, 20)]) == []

def test_cover_read_last_is_flagged_with_no_next():
    x = ro.out_of_order([E('body', 2, 300), E('cover', 1)])
    assert [(y['first'], y['prev'], y['next']) for y in x] == [(1, 300, None)]

# skip
def test_skip_is_a_div_around_placed_content():
    assert ro.skip('Div', ['Figure', 'Caption']) and ro.skip('Div', ['P', 'Note'])
    assert not ro.skip('Div', ['P']) and not ro.skip('Sect', ['Figure'])

# line / parse_line: the digest's format, round trip
def test_line_round_trip():
    s = ro.line('Story', 2, 23, 2, 'THE PEARL FRONTIER: a title')
    assert s == 'Story pp2-23 depth2: THE PEARL FRONTIER: a title'          # the digest's format: changing it changes the model input
    e = ro.parse_line(s)
    assert (e['style'], e['first'], e['last'], e['depth'], e['text']) == ('Story', 2, 23, 2, 'THE PEARL FRONTIER: a title')

def test_a_line_that_does_not_parse_is_kept_without_pages():
    e = ro.parse_line('something else')
    assert e['first'] is None and e['text'] == 'something else'
    assert flagged(ro.parse_lines(['something else', ro.line('Sect', 1, 2, 1, '')])) == []

def test_parse_lines_takes_the_parent_from_depth():
    es = ro.parse_lines([ro.line('Part', 1, 40, 1, ''), ro.line('Sect', 1, 20, 2, ''), ro.line('Sect', 21, 40, 2, ''), ro.line('Sect', 41, 50, 1, '')])
    assert [e['parent'] for e in es] == [None, 'line:0', 'line:0', None]

# section_move: the one match apply.py and the review page use
TREE = {'root': ['front', 'body', 'notes'], 'front': [], 'body': ['ch1', 'ch2'], 'ch1': [], 'ch2': [], 'notes': []}
SPAN = {'front': (1, 10), 'body': (11, 200), 'ch1': (11, 100), 'ch2': (101, 200), 'notes': (201, 230)}
FIRSTS = {'front': [1], 'body': [11, 101, 231], 'ch1': [11], 'ch2': [101], 'notes': [201]}

def move(a, b, before, tree=TREE, span=SPAN, firsts=FIRSTS):
    return ro.section_move('root', lambda n: tree.get(n, []), lambda n: firsts.get(n, []), lambda n: span.get(n), a, b, before)

def test_section_move_one_candidate_and_a_host():
    cand, host = move(101, 200, 231)
    assert cand == [('ch2', 'body')] and host == 'body'

def test_section_move_no_candidate():
    cand, host = move(150, 160, 231)
    assert cand == []

def test_section_move_two_candidates_when_sections_nest_inside_the_range():
    cand, _ = move(11, 200, 231, tree={**TREE, 'root': ['front', 'body', 'notes']})
    assert len(cand) == 3                                   # body, ch1 and ch2 all lie inside 11-200: refused

def test_section_move_no_host():
    cand, host = move(201, 230, 500)
    assert cand == [('notes', 'root')] and host is None

# read_late
def test_a_small_section_read_after_the_long_one_it_sits_in_is_listed():
    es = [E('ch', 2, 60), E('fig', 30), E('fig2', 58), E('next', 61, 80)]
    assert [(es[x['i']]['id'], x['after']) for x in ro.read_late(es)] == [('fig', 60)]    # 58 is only 2 pages early

def test_read_late_leaves_out_long_flagged_and_skipped_entries():
    es = [E('ch', 2, 60), E('long', 10, 20), E('div', 30, skip=True), E('next', 61, 80), E('back', 1)]
    assert ro.read_late(es) == []                         # long: more than 2 pages; div: skipped; back: flagged by out_of_order
