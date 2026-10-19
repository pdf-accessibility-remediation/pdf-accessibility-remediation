"""listrule.py: the one-item list rule, shared by audit.py (marks the lists in the digest) and apply.py (applies it).

OpenDataLoader sometimes takes the first word of a paragraph's line ("as", "at", "them", a year such as "1876") for a
list label and wraps the whole paragraph in a one-item list. A list counts as such a false list when it has exactly one
item, made of one label and one body, and the label is not a list marker. A marker is a bullet symbol on its own, or a
number, letter or roman numeral followed by "." or ")" or enclosed in parentheses.
"""
import re

MARKER = re.compile(r'^(?:[•◦▪▫‣⁃●○■□◆◇►▶➢✓✔∙·*–—-]'
                    r'|\(?(?:\d{1,3}|[A-Za-z]|[ivxlcdm]{1,6}|[IVXLCDM]{1,6})[.)]'
                    r'|\((?:\d{1,3}|[A-Za-z]|[ivxlcdm]{1,6}|[IVXLCDM]{1,6})\))$')

def is_marker(label):
    """True if the label text (white space ignored) is a real list marker."""
    return bool(MARKER.match(re.sub(r'\s+', '', label or '')))

def is_false_one_item_list(item_count, parts, label):
    """item_count: LIs in the list; parts: the standard types of the LI's children in order; label: the Lbl's text."""
    return item_count == 1 and sorted(parts) == ['LBody', 'Lbl'] and bool((label or '').strip()) and not is_marker(label)
