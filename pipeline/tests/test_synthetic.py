"""test_synthetic.py: the real pdfplumber, audit.py and apply.py on tiny hand-made PDFs, for rules no sample book reaches.

    python -m pytest tests/test_synthetic.py -q

- Word breaks drawn as gaps, with no space characters (TeX, Prince): every sample book has real spaces, so the regression
  test never reaches gaptext's gap rule through pdfplumber and plumb_fix.
- The one-item list rule: OpenDataLoader makes such lists from a paragraph's first word; no tagged sample has one.
No book content; nothing is sent anywhere; veraPDF is off.
"""
import os, sys, json, subprocess
import pikepdf

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def one_page(content, path, tagged=None):
    """A one-page PDF drawing content (a content stream, Helvetica as /F1); tagged(pdf, page) builds a tag tree."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
                              Contents=pikepdf.Stream(pdf, content.encode('latin-1')))
    pdf.pages.append(pikepdf.Page(page))
    if tagged: tagged(pdf, pdf.pages[0])
    pdf.save(path)
    return path

# ---- word breaks drawn as gaps
def gap_text_of(path):
    from lib import plumb_fix, plpages, gaptext  # noqa: F401  plumb_fix before pdfplumber reads a page
    return gaptext.gap_text(plpages.Pages(path).pages[0].chars)

def test_gaps_from_text_moves_are_spaces(tmp_path):
    # Helvetica 11pt: "as" is 11.6pt wide, "well" 18.9pt; each word starts 4-7pt after the last one ends
    p = one_page('BT /F1 11 Tf 72 500 Td (as) Tj 16 0 Td (well) Tj 26 0 Td (as) Tj 16 0 Td (owning) Tj ET\n', str(tmp_path / 'td.pdf'))
    assert gap_text_of(p) == 'as well as owning'

def test_gaps_from_kerning_are_spaces(tmp_path):
    # TeX's way: one TJ, words separated by a kerning shift of 0.4 em, letters by none
    p = one_page('BT /F1 11 Tf 72 500 Td [(as) -400 (well) -400 (as) -400 (owning)] TJ ET\n', str(tmp_path / 'tj.pdf'))
    assert gap_text_of(p) == 'as well as owning'

def test_tight_kerning_is_not_a_space(tmp_path):
    p = one_page('BT /F1 11 Tf 72 500 Td [(W) 80 (ave) -30 (s)] TJ ET\n', str(tmp_path / 'kern.pdf'))    # ordinary pair kerning
    assert gap_text_of(p) == 'Waves'

# ---- the one-item list rule, through audit.py and apply.py
TEXT = [('P', 'This page opens with a short paragraph of plain text.'),
        ('Lbl', 'as'), ('LBody', 'the river rose over its banks, the village moved uphill.'),     # a paragraph OpenDataLoader took for a list
        ('Lbl', '1.'), ('LBody', 'First real item.'), ('Lbl', '2.'), ('LBody', 'Second real item.')]

def list_pdf(path):
    content = ''.join(f'/{tag} <</MCID {i}>> BDC BT /F1 11 Tf {72 if tag != "LBody" else 96} {500 - 20 * (i - (tag == "LBody"))} Td ({t}) Tj ET EMC\n'
                      for i, (tag, t) in enumerate(TEXT))
    def tagged(pdf, page):
        root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
        doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
        def el(s, parent, k):
            return pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + s), P=parent, Pg=page.obj, K=k))
        leaves = []
        def leaf(s, parent, i): e = el(s, parent, i); leaves.append(e); return e
        def lst(first, n):
            L = el('L', doc, pikepdf.Array()); lis = []
            for j in range(n):
                li = el('LI', L, pikepdf.Array()); li.K = pikepdf.Array([leaf('Lbl', li, first + 2 * j), leaf('LBody', li, first + 2 * j + 1)]); lis.append(li)
            L.K = pikepdf.Array(lis); return L
        doc.K = pikepdf.Array([leaf('P', doc, 0), lst(1, 1), lst(3, 2)])
        root.K = doc; root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pikepdf.Array(leaves)])))
        page.obj.StructParents = 0
        pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    return one_page(content, path, tagged)

def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off'),
                       capture_output=True, text=True)
    assert r.returncode == 0, f'{script} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}'

def doc_kids(path):
    with pikepdf.open(path) as p:
        doc = p.Root.StructTreeRoot.K
        doc = doc[0] if isinstance(doc, pikepdf.Array) else doc
        return [str(k.S).lstrip('/') for k in doc.K]

def test_one_item_list_rule(tmp_path):
    src = list_pdf(tmp_path / 'lists.pdf')
    assert doc_kids(src) == ['P', 'L', 'L']
    run('audit.py', src, tmp_path / 'audit')
    lists = json.load(open(tmp_path / 'audit' / 'digest.json', encoding='utf-8'))['lists']
    assert [(x['items'], bool(x.get('flattened_by_rule'))) for x in lists] == [(1, True), (2, False)]
    wo = tmp_path / 'workorder.json'; wo.write_text(json.dumps({'schema': 'workorder/0.1'}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, wo, out)
    assert doc_kids(out) == ['P', 'P', 'L']                  # the false list became a paragraph; the real one stayed a list
    rule = json.load(open(str(out) + '.log.json', encoding='utf-8'))['list_rule']
    assert [x['label'] for x in rule['flattened']] == ['as'] and rule['flattened'][0]['text'].startswith('as the river rose')

def test_one_item_list_kept_when_the_work_order_says_so(tmp_path):
    src = list_pdf(tmp_path / 'lists.pdf')
    run('audit.py', src, tmp_path / 'audit')
    false_list = json.load(open(tmp_path / 'audit' / 'digest.json', encoding='utf-8'))['lists'][0]['obj']
    wo = tmp_path / 'workorder.json'; wo.write_text(json.dumps({'schema': 'workorder/0.1', 'keep_lists': [{'obj': false_list}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, wo, out)
    assert doc_kids(out) == ['P', 'L', 'L']
