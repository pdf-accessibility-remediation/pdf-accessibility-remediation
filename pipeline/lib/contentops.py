"""contentops.py: the content-stream operators verify.py's untagged-content loop (`_walk`) acts on, and the filter that asks
pikepdf for those only (#93 (improve performance: home and batch pages, first-time "Review Again", and PDF pipeline step
timing), Part 3, C1). One source: the loop compares against these sets, and FILTER is built from them.

    from lib import contentops as CO
    pikepdf.parse_content_stream(stream, CO.FILTER)

pikepdf parses the stream in C++ and hands Python only the operators named in the filter (about half of a book's
operators), with their own operands, in order. Two traps, both closed here in code:
  - pikepdf reports an inline image as the single operator `INLINE IMAGE`, but the filter must name it `BI ID EI`, all
    three: with `BI` alone (or `BI ID`) everything after the first inline image is lost; without them, inline images
    vanish from the parse. `filter_for()` builds the three from `INLINE IMAGE` and refuses anything else.
  - The filter and the loop must name the same operators: tests/test_contentops.py reads `_walk` and checks that the
    operator names it compares `op` against are exactly HANDLED.
Relies on pikepdf's documented filter (pinned in requirements.txt); the tests fail if a later pikepdf changes it.
"""
PAINT = frozenset({'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'})    # paint the current path
SHOW = frozenset({'Tj', 'TJ', "'", '"'})                              # show text
PATH = frozenset({'m', 'l', 'c', 'v', 'y', 're'})                     # build a path
INLINE = ('BI', 'ID', 'EI')                                           # an inline image, as the filter must name it
HANDLED = frozenset({'BDC', 'BMC', 'EMC', 'q', 'Q', 'Tf', 'Tr', 'n', 'Do', 'sh', 'INLINE IMAGE'}) | PAINT | SHOW | PATH

def filter_for(ops):
    """pikepdf's filter string for these operator names: INLINE IMAGE becomes BI ID EI (all three, never one alone)."""
    ops = set(ops)
    if ops & set(INLINE): raise ValueError('name an inline image INLINE IMAGE: the filter needs BI, ID and EI together')
    if 'INLINE IMAGE' in ops: ops = (ops - {'INLINE IMAGE'}) | set(INLINE)
    out = ' '.join(sorted(ops))
    names = set(out.split())
    if names & set(INLINE) and not set(INLINE) <= names: raise ValueError('BI, ID and EI go together in a filter')
    return out

FILTER = filter_for(HANDLED)
assert set(INLINE) <= set(FILTER.split()), 'the filter must keep inline images (BI ID EI)'
