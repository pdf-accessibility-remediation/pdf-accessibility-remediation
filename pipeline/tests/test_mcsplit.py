"""test_mcsplit.py: splitting a marked-content run to tag part of it (lib/mcsplit.py; #118, language tagging).

    python -m pytest tests/test_mcsplit.py -q

Each case draws one run on a synthetic page (tests/langpdf.py), splits it at a place given by character indexes, and
checks what the method promises: the page renders the same (pypdfium2 at verify.py's scale), pdfplumber reads the same
page text, the new Span's marked content holds exactly the place's characters, the rest of the run keeps its own MCIDs,
and unsafe cases are refused with the page unchanged. Places are found by counting codes, so fonts with no ToUnicode map,
a /Differences encoding or a bfrange map split the same way (review 02, H2). No book content; nothing is sent anywhere.
"""
import os, sys, collections
import pikepdf, pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, mcsplit  # noqa: F401,E402

def chars_by_mcid(path):
    by = collections.defaultdict(list)
    for c in plpages.Pages(path).pages[0].chars:
        if c.get('mcid') is not None: by[c['mcid']].append(c['text'])
    return by

def page_text(path): return ''.join(c['text'] for c in plpages.Pages(path).pages[0].chars)

def pixels(path):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(path)
    try: return d[0].render(scale=1.2).to_pil().convert('RGB').tobytes()
    finally: d.close()

def locate(chars, phrase, nth=0):
    """(first, last) of the nth occurrence of phrase in the run's characters (test helper: the pipeline gets indexes
    from lib/langcands.py)."""
    text, pos = '', []
    for i, t in enumerate(chars):
        for ch in t: text += ch; pos.append(i)
    at = -1
    for _ in range(nth + 1): at = text.index(phrase, at + 1)
    return pos[at], pos[at + len(phrase) - 1]

def split(tmp_path, runs, mcid, phrases, name='c'):
    src = langpdf.build(str(tmp_path / f'{name}.pdf'), runs)
    by = chars_by_mcid(src)
    cuts = [locate(by[mcid], p) if isinstance(p, str) else p for p in phrases]
    pdf = pikepdf.open(src); page = pdf.pages[0]
    ins = list(pikepdf.parse_content_stream(page))
    nxt = [max(mcsplit.drawn_mcids(ins)) + 1]
    def new_mcid():
        nxt[0] += 1; return nxt[0] - 1
    out, pieces = mcsplit.split_run(ins, page.obj.Resources.Font, mcid, cuts, new_mcid, expect_n=len(by[mcid]))
    page.obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(out))
    dst = str(tmp_path / f'{name}_split.pdf'); pdf.save(dst)
    return src, dst, pieces, cuts

def check_same(src, dst):
    assert page_text(src) == page_text(dst)
    assert pixels(src) == pixels(dst)

def span_texts(dst, pieces):
    by = chars_by_mcid(dst)
    return [''.join(by[m]) for m, kind, _ in pieces if kind == 'span']

CASES = [  # name, runs, phrase(s), the Span texts expected
    ('middle of a Tj', [{'text': 'The city of Heiankyo was the capital.'}], ['Heiankyo'], ['Heiankyo']),
    ('start of a kerned TJ', [{'body': ['[(Mapp) -20 (o) ( marks an age.)] TJ']}], ['Mappo'], ['Mappo']),
    ('across two lines', [{'body': ['(He said namu amida) Tj', 'T*', '(butsu every day.) Tj']}], ['namu amidabutsu'], ['namu amidabutsu']),
    ('end of a run', [{'text': 'The age of mappo'}], ['mappo'], ['mappo']),
    ('two-byte font', [{'font': 'F2', 'text': 'A word: kokua here.'}], ['kokua'], ['kokua']),
    ('ligature inside the place', [{'font': 'F2', 'text': 'the kaﬁr rule'}], ['kafir'], ['kafir']),
    ('quote operator', [{'body': ['(First line) Tj', "(then mappo again) '"]}], ['mappo'], ['mappo']),
    ('two places in one run', [{'text': 'Both mappo and shingon here.'}], ['mappo', 'shingon'], ['mappo', 'shingon']),
    ('Differences font, no ToUnicode', [{'font': 'F3', 'text': 'Ryōgen wrote of mappō then.'}], ['mappō'], ['mappō']),
    ('bfrange font', [{'font': 'F4', 'text': 'see the sutra here'}], ['sutra'], ['sutra']),
    ('marks outside the text object', [{'outside': True, 'text': 'The city of Heiankyo was the capital.'}], ['Heiankyo'], ['Heiankyo']),
    ('BDC Lang en-US on the run', [{'lang': 'en-US', 'text': 'The city of Heiankyo was the capital.'}], ['Heiankyo'], ['Heiankyo']),
    ('whole spoken-text span', [{'body': ['(The ) Tj', '/Span <</ActualText (aina)>> BDC', '(aina) Tj', 'EMC', '( is the land.) Tj']}], ['aina'], ['aina']),
]

@pytest.mark.parametrize('name,runs,phrases,want', CASES, ids=[c[0] for c in CASES])
def test_split(tmp_path, name, runs, phrases, want):
    src, dst, pieces, _ = split(tmp_path, runs, 0, phrases)
    check_same(src, dst)
    got = span_texts(dst, pieces)
    assert got == want
    assert pieces[0][0] == 0                                  # the run's own MCID stays on its first piece
    assert len({m for m, _, _ in pieces}) == len(pieces)     # every piece its own MCID

def test_span_marks_carry_no_lang_and_the_rest_keeps_its_own(tmp_path):
    """review 02, H1: the Span's marked content names no language (the structure element's /Lang must win); the rest
    of the run is English and keeps its 'en-US'."""
    src, dst, pieces, _ = split(tmp_path, [{'lang': 'en-US', 'text': 'The city of Heiankyo was the capital.'}], 0, ['Heiankyo'])
    pdf = pikepdf.open(dst)
    props = {int(x.operands[1].MCID): x.operands[1] for x in pikepdf.parse_content_stream(pdf.pages[0])
             if str(x.operator) == 'BDC' and isinstance(x.operands[1], pikepdf.Dictionary) and '/MCID' in x.operands[1]}
    for m, kind, _ in pieces:
        if kind == 'span': assert '/Lang' not in props[m]
        else: assert str(props[m].get('/Lang')) == 'en-US'

def test_marks_moved_inside_the_text_object(tmp_path):
    """A run opened outside its text object: after the split no marked content crosses BT or ET."""
    _, dst, _, _ = split(tmp_path, [{'outside': True, 'text': 'The city of Heiankyo was the capital.'}], 0, ['Heiankyo'])
    depth_at_bt = []; d = 0
    pdf = pikepdf.open(dst)
    for x in pikepdf.parse_content_stream(pdf.pages[0]):
        op = str(x.operator)
        if op in ('BDC', 'BMC'): d += 1
        elif op == 'EMC': d -= 1
        elif op in ('BT', 'ET'): depth_at_bt.append(d)
    assert depth_at_bt == [0, 0]

def test_whole_place_is_one_piece(tmp_path):
    src = langpdf.build(str(tmp_path / 'w.pdf'), [{'text': 'Heiankyo'}])
    pdf = pikepdf.open(src); ins = list(pikepdf.parse_content_stream(pdf.pages[0]))
    out, pieces = mcsplit.split_run(ins, pdf.pages[0].obj.Resources.Font, 0, [(0, 7)], lambda: 99, expect_n=8)
    assert pieces == [(0, 'span', 0)]

def test_drop_lang(tmp_path):
    src = langpdf.build(str(tmp_path / 'd.pdf'), [{'lang': 'en-US', 'text': 'kana here'}])
    pdf = pikepdf.open(src); ins = list(pikepdf.parse_content_stream(pdf.pages[0]))
    out, changed = mcsplit.drop_lang(ins, 0)
    assert changed and not any(str(x.operator) == 'BDC' and '/Lang' in x.operands[1] for x in out)
    pdf.pages[0].obj.Contents = pdf.make_stream(pikepdf.unparse_content_stream(out)); dst = str(tmp_path / 'd2.pdf'); pdf.save(dst)
    check_same(src, dst)

REFUSED = [
    ('double-quote operator', [{'body': ['(First) Tj', '1 0.5 (so the mappo age) "']}], ['mappo'], '"'),
    ('part of a spoken-text span', [{'body': ['/Span <</ActualText (aina momona)>> BDC', '(aina momona) Tj', 'EMC', '( here) Tj']}], ['momona'], 'spoken-text span'),
    ('Type3 font', [{'font': 'F5', 'text': 'abc def'}], [(4, 6)], 'Type3'),
    ('across two text objects', [{'outside': True, 'body': ['(Ka pono) Tj', 'ET', 'BT /F1 11 Tf 300 740 Td', '(kahiko mau) Tj']}], [(3, 12)], 'two text objects'),
    ('wrong character count', [{'text': 'The age of mappo'}], [(11, 15)], 'line up'),
]

@pytest.mark.parametrize('name,runs,cuts,why', REFUSED, ids=[c[0] for c in REFUSED])
def test_refused(tmp_path, name, runs, cuts, why):
    src = langpdf.build(str(tmp_path / 'r.pdf'), runs)
    by = chars_by_mcid(src)
    cuts = [locate(by[0], c) if isinstance(c, str) else c for c in cuts]
    pdf = pikepdf.open(src); ins = list(pikepdf.parse_content_stream(pdf.pages[0]))
    n = len(by[0]) + (1 if name == 'wrong character count' else 0)
    with pytest.raises(mcsplit.Refuse) as e:
        mcsplit.split_run(ins, pdf.pages[0].obj.Resources.Font, 0, cuts, lambda: 99, expect_n=n)
    assert why in str(e.value)
