"""test_listrule.py: real list markers, and the one-item list OpenDataLoader makes from a paragraph's first word.

    python -m pytest tests/test_listrule.py -q
"""
import pytest
from lib import listrule

@pytest.mark.parametrize('label', ['•', '–', '*', '1.', '12)', '(3)', 'a.', 'B)', '(c)', 'iv.', 'XII)', '(ii)', ' 2 . '])
def test_markers(label):
    assert listrule.is_marker(label)

@pytest.mark.parametrize('label', ['as', 'them', '1876', '1234.', 'abc.', '', None, '1', 'Chapter'])
def test_not_markers(label):
    assert not listrule.is_marker(label)

def test_false_one_item_list():
    assert listrule.is_false_one_item_list(1, ['Lbl', 'LBody'], 'as')
    assert listrule.is_false_one_item_list(1, ['LBody', 'Lbl'], '1876')         # order of the parts does not matter

def test_kept_lists():
    assert not listrule.is_false_one_item_list(2, ['Lbl', 'LBody'], 'as')        # more than one item
    assert not listrule.is_false_one_item_list(1, ['Lbl', 'LBody'], '1.')        # a real marker
    assert not listrule.is_false_one_item_list(1, ['Lbl', 'LBody'], '  ')        # no label text
    assert not listrule.is_false_one_item_list(1, ['LBody'], 'as')               # no label
    assert not listrule.is_false_one_item_list(1, ['Lbl', 'LBody', 'L'], 'as')   # more than a label and a body
