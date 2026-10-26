"""test_gaptext.py: where gap_text() puts word breaks in characters that carry no space characters.

    python -m pytest tests/test_gaptext.py -q
"""
import re
from lib import gaptext

def ch(text, x0, width=5, bottom=10, size=10, **kw):
    """One pdfplumber-style character on a horizontal line."""
    return dict(text=text, x0=x0, x1=x0 + width, top=bottom - size, bottom=bottom, size=size, **kw)

def run(text, start=0, gap=0, width=5, **kw):
    """The characters of text set one after another with the same gap."""
    return [ch(t, start + i * (width + gap), width, **kw) for i, t in enumerate(text)]

def test_wide_gap_is_a_space():
    chars = run('as') + run('well', start=14)            # 4pt gap at 10pt type: wider than GAP_EM, letters touch
    assert gaptext.gap_text(chars) == 'as well'

def test_no_gap_no_space():
    assert gaptext.gap_text(run('aswell')) == 'aswell'

def test_letter_spaced_line_stays_one_word():
    assert gaptext.gap_text(run('PREFACE', gap=2)) == 'PREFACE'     # every gap alike: letter spacing, not word breaks

def test_letter_spaced_line_with_kerning_stays_one_word():
    chars = run('PRE', gap=2) + run('FACE', start=3 * 7 + 1, gap=2)   # one 3pt gap among 2pt ones: under 2.5 x typical
    assert gaptext.gap_text(chars) == 'PREFACE'

def test_letter_spaced_line_keeps_its_wider_word_gap():
    chars = run('FISHING', gap=2) + run('MAUI', start=7 * 7 + 6, gap=2)   # 8pt between the words, 2.5 x 2pt = 5pt
    assert gaptext.gap_text(chars) == 'FISHING MAUI'

def test_gap_filled_by_another_glyph_is_not_a_space():
    text = [ch('u', 0, pg=1), ch('n', 5, pg=1), ch('a', 14, pg=1), ch('d', 19, pg=1)]   # a 4pt hole between n and a
    accent = ch('á', 10, width=4, pg=1)             # drawn in another font, outside this text
    page = text + [accent]
    assert gaptext.gap_text(text, page_chars=lambda pg: page) == 'unad'
    assert gaptext.gap_text(text) == 'un ad'             # without the page's characters the hole reads as a break

def test_new_line_is_a_space():
    assert gaptext.gap_text(run('end') + run('next', bottom=25)) == 'end next'

def test_no_space_after_a_line_end_hyphen():
    assert gaptext.gap_text(run('com-') + run('puter', bottom=25)) == 'com-puter'

def stacked(text, gap=0, size=10):
    """Glyphs set one under another (vertical text not flagged as rotated)."""
    return [dict(text=t, x0=0, x1=size, top=i * (size + gap), bottom=i * (size + gap) + size, size=size) for i, t in enumerate(text)]

def test_vertical_text_touching_is_one_word():
    assert gaptext.gap_text(stacked('縦書き')) == '縦書き'

def test_vertical_text_wide_gap_is_a_space():
    chars = stacked('縦書きの') + [dict(text='文', x0=0, x1=10, top=48, bottom=58, size=10)]   # 8pt gap below the fourth glyph
    assert gaptext.gap_text(chars) == '縦書きの 文'

def test_empty():
    assert gaptext.gap_text([]) == ''

def test_loosen_matches_with_or_without_spaces():
    rx = re.compile(gaptext.loosen(r'as well\s+as'))
    assert rx.fullmatch('aswellas') and rx.fullmatch('as well as')
