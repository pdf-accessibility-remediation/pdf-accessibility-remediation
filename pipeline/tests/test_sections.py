"""test_sections.py: review.md's lines go into sections and come back out unchanged; review.html's WCAG-only view.

    python -m pytest tests/test_sections.py -q
"""
from lib.sections import line, pdfua, nolink, to_sections, render_md, text_wcag, parts_wcag, by_key, excerpt

def lines():
    return ['# Remediation review: book.pdf', '', 'Result: `book_remediated.pdf`', '',
            '## Automated checks', '',
            '| Check | Result |', '|---|---|',
            line('| Fonts | 2 not embedded |', key='fonts:not_embedded', pages=[7, 4, None]),
            '', '### 3. For a person to check', '',
            line('- Undefined character', pdfua(' (ISO 14289-1 7.21.8, PDF/UA)'), ' on page 4', key='chars', pages=[4]),
            line('PDF/UA-only, not required for WCAG', scope='pdfua'),
            line('> quoted', nolink(' p. 12 of the source')),
            '- second item', 'A paragraph.']

def test_round_trip():
    ls = lines()
    assert render_md(to_sections(ls)) == ls

def test_sections_and_items():
    secs = to_sections(lines())
    assert [s['key'] for s in secs] == ['header', 'title', 'automated-checks', 'for-a-person-to-check']
    person = secs[3]
    assert person['n'] == 3 and person['title'] == '3. For a person to check' and person['level'] == 3
    assert person['anchor'] == '3-for-a-person-to-check'          # the key leaves out the number, the anchor keeps it
    kinds = [it['kind'] for it in secs[2]['items']]
    assert kinds == ['blank', 'head', 'sep', 'row', 'blank']
    row = secs[2]['items'][3]
    assert row['id'] == 'automated-checks-1' and row['pages'] == [4, 7] and row['key'] == 'fonts:not_embedded'
    assert [it.get('id') for it in person['items'] if it['kind'] != 'blank'] == [f'3-for-a-person-to-check-{i}' for i in range(1, 6)]

def test_wcag_view():
    items = to_sections(lines())[3]['items']
    undefined, ua_line, quoted = items[1], items[2], items[3]
    assert undefined['text'] == '- Undefined character (ISO 14289-1 7.21.8, PDF/UA) on page 4'
    assert text_wcag(undefined) == '- Undefined character on page 4'
    assert ua_line['scope'] == 'pdfua'
    assert parts_wcag(quoted) == [('> quoted', True), (' p. 12 of the source', False)]

def test_by_key():
    assert set(by_key(to_sections(lines()))) == {'fonts:not_embedded', 'chars'}

def test_excerpt():
    full = []
    assert excerpt('short text', full) == 'short text' and full == []
    long = 'word ' * 40
    ex = excerpt(long, full, n=30)
    assert ex.endswith('…') and len(ex) <= 31 and full == [[ex, long.strip()]]
