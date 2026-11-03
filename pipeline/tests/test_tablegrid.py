"""test_tablegrid.py: who heads what in a table (lib/tablegrid.py). Expected results follow docs/work-order.md, "tables".

    python -m pytest tests/test_tablegrid.py -q
"""
import pytest
from lib.tablegrid import Cell, Refused, place, plan

C = Cell()                 # an ordinary cell
E = Cell(empty=True)
def wide(n): return Cell(colspan=n)
def tall(n): return Cell(rowspan=n)
def ths(p): return {k for k, v in p['cells'].items() if v['th']}

def test_place_counts_spans():
    pos = place([[tall(2), C], [C], [wide(2)]])
    assert [(p.col0, p.col1) for p in pos[0]] == [(0, 1), (1, 2)]
    assert [(p.col0, p.col1) for p in pos[1]] == [(1, 2)]        # the first column is taken from above
    assert [(p.col0, p.col1) for p in pos[2]] == [(0, 2)]

def test_plain_grid_uses_scope_only():
    p = plan([[C, C], [C, C], [C, C]], header_rows=1)
    assert not p['complex'] and ths(p) == {(0, 0), (0, 1)}
    assert p['cells'][(0, 0)]['scope'] == 'Column' and p['cells'][(1, 0)]['scope'] is None and p['cells'][(1, 0)]['headers'] == []

def test_header_column_and_corner():
    p = plan([[C, C], [C, C]], header_rows=1, header_cols=1)
    assert p['cells'][(0, 0)]['scope'] == 'Both' and p['cells'][(0, 1)]['scope'] == 'Column' and p['cells'][(1, 0)]['scope'] == 'Row'
    assert not p['cells'][(1, 1)]['th']

def test_cells_not_named_are_not_headers():
    """An abbreviation list: the first entry was tagged TH, but the headers are the first column."""
    p = plan([[C, wide(3)], [C, wide(3)]], header_cols=1)
    assert ths(p) == {(0, 0), (1, 0)}

def test_empty_cells_are_never_headers():
    """Name | (gap) | Occupation | (gap) | Location: empty spacer columns."""
    p = plan([[C, E, C], [C, E, C]], header_rows=1)
    assert ths(p) == {(0, 0), (0, 2)}

def test_title_and_note_rows_leave_the_table():
    rows = [[wide(2)], [C, C], [C, C], [wide(2)]]
    p = plan(rows, title_rows=1, note_rows=1, header_rows=1)
    assert p['title'] == [0] and p['note'] == [3] and set(p['cells']) == {(1, 0), (1, 1), (2, 0), (2, 1)} and ths(p) == {(1, 0), (1, 1)}

def test_group_rows_head_the_rows_below_by_id():
    """A title, column names, then a group row over its rows and a second group row over its."""
    rows = [[wide(2)], [C, C], [wide(2)], [C, C], [wide(2)], [C, C]]
    p = plan(rows, title_rows=1, header_rows=1, group_rows=[2, 4])
    assert p['complex'] and ths(p) == {(1, 0), (1, 1), (2, 0), (4, 0)}
    assert p['cells'][(3, 1)]['headers'] == [(1, 1), (2, 0)] and p['cells'][(5, 0)]['headers'] == [(1, 0), (4, 0)]

def test_two_level_column_header_lists_both():
    rows = [[C, wide(2)], [C, C, C], [C, C, C]]
    p = plan(rows, header_rows=2)
    assert p['complex'] and p['cells'][(2, 1)]['headers'] == [(0, 1), (1, 1)] and p['cells'][(2, 0)]['headers'] == [(0, 0), (1, 0)]

def test_row_header_spanning_rows_heads_each_row():
    rows = [[C, C, C], [tall(2), C, C], [C, C]]
    p = plan(rows, header_rows=1, header_cols=1)
    assert p['complex'] and p['cells'][(1, 0)]['th'] and p['cells'][(2, 0)]['headers'] == [(0, 1), (1, 0)]

def test_repeated_header_row_stays_a_header_and_heads_nothing_new():
    """A table that repeats its column names after a page break."""
    rows = [[C, C], [C, C], [C, C], [C, C]]
    p = plan(rows, header_rows=1, repeat_rows=[2])
    assert ths(p) == {(0, 0), (0, 1), (2, 0), (2, 1)} and not p['complex']

@pytest.mark.parametrize('rows, reading, why', [
    ([[C, C], [C, C]], {'header_rows': 2}, 'too few rows'),
    ([[wide(2)], [C, C]], {'title_rows': 1, 'header_rows': 1}, 'too few rows'),
    ([[C, C], [C, C], [C, C]], {'title_rows': 1}, 'holds more than one thing'),
    ([[C, C], [C, C], [C, C]], {'header_rows': 1, 'group_rows': [1]}, 'holds more than one thing'),
    ([[C], [C], [C]], {'header_rows': 1, 'group_rows': [0]}, 'outside the data rows'),
    ([[C, C], [C, C], [C, C]], {'header_rows': 1, 'repeat_rows': [7]}, 'outside the data rows'),
    ([[tall(2), C], [C], [C, C]], {'header_rows': 1}, 'spans into the data rows'),
    ([[wide(2), C], [wide(2), C]], {'header_cols': 1}, 'across the header column edge'),
    ([[tall(2)], [C], [C]], {'title_rows': 1}, 'spans into the next row'),
    ([[C, C], [E], [C, C]], {'header_rows': 1, 'group_rows': [1]}, 'is empty'),
])
def test_a_reading_that_does_not_fit_is_refused(rows, reading, why):
    with pytest.raises(Refused, match=why): plan(rows, **reading)

def test_one_label_row_with_empty_cells_counts():
    p = plan([[C, E], [C, C], [C, C]], title_rows=1, header_rows=1)
    assert p['title'] == [0]
