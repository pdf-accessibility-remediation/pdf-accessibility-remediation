"""test_contentops.py: verify.py's untagged-content loop reads only the operators it acts on (#93 (improve performance:
home and batch pages, first-time "Review Again", and PDF pipeline step timing), Part 3, C1; lib/contentops.py).

    python -m pytest tests/test_contentops.py -q

- One source: the operator names `_walk` compares `op` against (read from verify.py's own code) are exactly HANDLED, and
  any comparison of `op` this test can't read fails it.
- The filter keeps inline images: BI, ID and EI together, never one alone (with BI alone pikepdf drops everything after
  the first inline image; without them inline images vanish).
- Filtered and unfiltered parses give the same handled operators, with the same operands, in the same order: on a page
  with inline images (tagged and not), text, paths and operators the loop ignores; and on broken streams, where pikepdf
  stops silently with a warning in both modes (review 12 L1), so the survivors must be the same.
"""
import os, ast, warnings
import pikepdf
import pytest
from lib import contentops as CO

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def walk_ops(src=None):
    """Every operator name verify.py's _walk compares `op` against. Any other read of `op` in _walk (written the other way
    round, `'cm' == op`, or through a call, `str(op) in (…)`) fails, so no operator the loop looks at can be left out
    of the filter unseen (review 14 L1); the one exception is the line `op = str(op)`."""
    tree = ast.parse(src if src is not None else open(os.path.join(PIPE, 'verify.py'), encoding='utf-8').read())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_walk')
    names = {'PAINT': CO.PAINT, 'SHOW': CO.SHOW, 'PATH': CO.PATH}
    seen, read = set(), set()
    for a in (n for n in ast.walk(fn) if isinstance(n, ast.Assign)):           # op = str(op)
        v = a.value
        if ([type(t) for t in a.targets] == [ast.Name] and a.targets[0].id == 'op' and isinstance(v, ast.Call)
                and isinstance(v.func, ast.Name) and v.func.id == 'str' and len(v.args) == 1 and not v.keywords
                and isinstance(v.args[0], ast.Name) and v.args[0].id == 'op'):
            read.add(id(v.args[0]))
    for c in (n for n in ast.walk(fn) if isinstance(n, ast.Compare)):
        if not (isinstance(c.left, ast.Name) and c.left.id == 'op'): continue
        read.add(id(c.left))
        for comp in c.comparators:
            if isinstance(comp, ast.Constant) and isinstance(comp.value, str): seen.add(comp.value)
            elif isinstance(comp, (ast.Tuple, ast.List, ast.Set)) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in comp.elts):
                seen |= {e.value for e in comp.elts}
            elif isinstance(comp, ast.Name) and comp.id in names: seen |= names[comp.id]
            else: raise AssertionError(f'a comparison of op this test cannot read: line {c.lineno}')
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and n.id == 'op' and isinstance(n.ctx, ast.Load) and id(n) not in read:
            raise AssertionError(f'a read of op this test cannot follow: line {n.lineno}')
    return seen

def test_the_loop_and_the_filter_name_the_same_operators():
    assert walk_ops() == CO.HANDLED

@pytest.mark.parametrize('line', ["if 'cm' == op: continue", "if str(op) in ('cm', 'w'): continue", "f(op)"])
def test_a_read_of_op_the_test_cannot_follow_fails(line):
    """review 14 L1: verify.py's _walk with one more line that reads `op` some other way (on a copy of the source, in
    memory): walk_ops refuses it instead of passing it by."""
    src = open(os.path.join(PIPE, 'verify.py'), encoding='utf-8').read()
    at = '        op = str(op)\n'
    assert src.count(at) == 1
    with pytest.raises(AssertionError, match='a read of op this test cannot follow'):
        walk_ops(src.replace(at, at + '        ' + line + '\n'))

def test_verify_parses_its_loop_with_the_filter():
    src = open(os.path.join(PIPE, 'verify.py'), encoding='utf-8').read()
    assert 'pikepdf.parse_content_stream(stream, CO.FILTER)' in src and 'contentops as CO' in src

def test_the_filter_keeps_inline_images_whole():
    names = CO.FILTER.split()
    assert {'BI', 'ID', 'EI'} <= set(names) and 'INLINE' not in names and 'IMAGE' not in names
    for bad in ({'q', 'BI'}, {'q', 'BI', 'ID'}, {'EI'}):
        with pytest.raises(ValueError): CO.filter_for(bad)
    assert CO.filter_for({'q', 'Q'}) == 'Q q'

PAGE = (b'/P <</MCID 0>> BDC q 10 0 0 10 10 10 cm BI /W 1 /H 1 /BPC 8 /CS /G ID \x80 EI Q EMC\n'
        b'q 2 w 14 TL 10 0 0 10 30 30 cm BI /W 1 /H 1 /BPC 8 /CS /G ID \x81 EI Q\n'
        b'BT /F1 12 Tf 3 Tr 0 0 Td (after) Tj [(a) -40 (b)] TJ (c) \' 1 2 (d) " ET\n'
        b'0 0 m 10 10 l 5 5 10 10 re h W n 1 0 0 RG 0 0 m 20 20 l S /Fm1 Do /Sh0 sh /Artifact BMC 0 0 1 1 re f EMC\n')

def handled(stream_bytes, flt):
    pdf = pikepdf.new()
    s = pdf.make_stream(stream_bytes)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        ops = pikepdf.parse_content_stream(s, flt) if flt else pikepdf.parse_content_stream(s)
    return [(str(i.operator), pikepdf.unparse_content_stream([i])) for i in ops if str(i.operator) in CO.HANDLED]

def test_filtered_equals_unfiltered_with_inline_images_text_and_paths():
    a, b = handled(PAGE, None), handled(PAGE, CO.FILTER)
    assert a == b and [o for o, _ in b].count('INLINE IMAGE') == 2
    assert [o for o, _ in b][-7:] == ['S', 'Do', 'sh', 'BMC', 're', 'f', 'EMC']          # what follows the images survives
    assert {'Tj', 'TJ', "'", '"', 'S', 'Do', 'sh'} <= {o for o, _ in b}

@pytest.mark.parametrize('broken', [
    b'BT /F1 12 Tf (never closed Tj ET 0 0 m 10 10 l S',                                   # an unterminated string
    b'q 0 0 m 10 10 l S ] ) >> BT /F1 12 Tf (x) Tj ET Q',                                 # stray closers
    b'q 10 0 0 10 0 0 cm BI /W 1 /H 1 /BPC 8 /CS /G ID \x80\x80\x80 Q 0 0 m 1 1 l S',      # an inline image with no EI
])
def test_a_broken_stream_gives_the_same_survivors_both_ways(broken):
    assert handled(broken, None) == handled(broken, CO.FILTER)
