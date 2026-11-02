"""tablegrid.py: who heads what in a table, from its rows' cells and the work order's reading of them. No PDF here.

    tablegrid.place(rows)           -> where each cell really sits, spans counted
    tablegrid.plan(rows, **reading) -> what apply.py's op_tables does to each row and cell, or raises Refused(why)

rows: one list per table row, one Cell(colspan, rowspan, empty) per cell, in tag order.
reading: title_rows, note_rows (counts at the top and bottom), header_rows, header_cols (counts, after the title rows),
group_rows, repeat_rows (row numbers from 0, in the whole table as tagged).

A table a screen reader can read needs each data cell tied to its headers. A Scope on the header cell is enough when the
table is a plain grid. It isn't when a column has two levels of header (a spanning "1990s" over "Men" and "Women"), when
a header column cell spans rows, or when section rows ("Moiety 1") head the rows below them: then each data cell lists its
headers by ID (WCAG 1.3.1, PDF 14.8.5.7).
"""
from collections import namedtuple

Cell = namedtuple('Cell', 'colspan rowspan empty', defaults=(1, 1, False))
Placed = namedtuple('Placed', 'row index col0 col1 row1')     # row, index in the row; columns col0..col1-1; rows row..row1-1

class Refused(Exception):
    """The reading doesn't fit the table: the sentence says why, for a person."""

def place(rows):
    """Each cell's real position: a cell starts at the first column not taken by a cell spanning down from above."""
    taken, out = {}, []
    for r, cells in enumerate(rows):
        col, line = 0, []
        for i, c in enumerate(cells):
            while (r, col) in taken: col += 1
            cs, rs = max(1, c.colspan), max(1, c.rowspan)
            line.append(Placed(r, i, col, col + cs, r + rs))
            for rr in range(r, r + rs):
                for cc in range(col, col + cs): taken[(rr, cc)] = True
            col += cs
        out.append(line)
    return out

def one_label(cells):
    """True when a row holds one thing: one cell, or one with text and the others empty."""
    return sum(not c.empty for c in cells) == 1 or (len(cells) == 1)

def plan(rows, title_rows=0, note_rows=0, header_rows=0, header_cols=0, group_rows=(), repeat_rows=()):
    """-> {'title': [row numbers], 'note': [...], 'cells': {(row, index): {'th': bool, 'scope': str or None, 'headers': [(row, index)]}},
           'complex': bool}. Every cell of the rows left in the table appears in 'cells'. Empty cells are never headers."""
    n = len(rows); placed = place(rows)
    title = list(range(title_rows)); note = list(range(n - note_rows, n)) if note_rows else []
    group, repeat = sorted(set(group_rows)), sorted(set(repeat_rows))
    head = list(range(title_rows, title_rows + header_rows))
    body_first, body_end = title_rows + header_rows, n - note_rows
    if body_first >= body_end: raise Refused('the table has too few rows for this: no data rows would be left')
    for name, rs in (('title', title), ('note', note), ('group', group)):
        for r in rs:
            if not rows[r] or not one_label(rows[r]): raise Refused(f'row {r} is named a {name} row but holds more than one thing')
    for r in group + repeat:
        if not body_first <= r < body_end: raise Refused(f'row {r} is outside the data rows')
    for r in group:
        if all(c.empty for c in rows[r]): raise Refused(f'row {r} is named a group row but is empty')
    if set(group) & set(repeat): raise Refused('a row is named both a group row and a repeated header row')
    for p in (x for r in title + note for x in placed[r]):
        if p.row1 - p.row > 1: raise Refused(f'row {p.row} spans into the next row, so it can\'t be taken out of the table')
    for r in head:
        for p in placed[r]:
            if p.row1 > body_first: raise Refused('a header cell spans into the data rows')
    if header_cols:
        data_rows = [r for r in range(body_first, body_end) if r not in group and r not in repeat]
        if not data_rows: raise Refused('no data rows would be left')
        for r in data_rows:
            if max((p.col1 for p in placed[r]), default=0) <= header_cols: raise Refused('the table has too few columns for this')
            for p in placed[r]:
                if p.col0 < header_cols < p.col1: raise Refused('a cell spans across the header column edge')
    gone = set(title + note)
    # complex: a two-level column header, a row header spanning rows, or section rows
    colhead_spans = any(p.col1 - p.col0 > 1 for r in head for p in placed[r])
    rowhead_spans = header_cols and any(p.col0 < header_cols and p.row1 - p.row > 1 for r in range(body_first, body_end) for p in placed[r])
    is_complex = bool(group) or (header_rows > 1 and colhead_spans) or bool(rowhead_spans)
    cells = {}
    def is_row_head(p, r): return r >= body_first and p.col0 < header_cols
    cur_group = None
    for r in range(n):
        if r in gone: continue
        if r in group: cur_group = next(p for p, c in zip(placed[r], rows[r]) if not c.empty)
        for p, c in zip(placed[r], rows[r]):
            key = (r, p.index)
            if r in repeat or r in head: th = not c.empty; scope = 'Column' if not (header_cols and p.col0 < header_cols) else 'Both'
            elif r in group: th = p is cur_group or (p.row, p.index) == (cur_group.row, cur_group.index); scope = 'Column'
            elif is_row_head(p, r): th = not c.empty; scope = 'Row'
            else: th, scope = False, None
            info = {'th': th, 'scope': scope if th else None, 'headers': []}
            if is_complex and not c.empty and not th:
                hs = [(q.row, q.index) for hr_ in head for q, qc in zip(placed[hr_], rows[hr_])
                      if not qc.empty and q.col0 < p.col1 and p.col0 < q.col1]          # the column headers above it
                if header_cols:
                    for rr in range(body_first, r + 1):
                        hs += [(q.row, q.index) for q, qc in zip(placed[rr], rows[rr]) if rr not in group and rr not in repeat and not qc.empty
                               and q.col0 < header_cols and q.row <= r < q.row1]        # the row headers beside it
                if cur_group is not None: hs.append((cur_group.row, cur_group.index))
                info['headers'] = hs
            cells[key] = info
    return {'title': title, 'note': note, 'cells': cells, 'complex': is_complex}
