"""test_synthetic.py: the real pdfplumber, audit.py and apply.py on tiny hand-made PDFs, for rules no sample book reaches.

    python -m pytest tests/test_synthetic.py -q

- Word breaks drawn as gaps, with no space characters (TeX, Prince): every sample book has real spaces, so the regression
  test never reaches gaptext's gap rule through pdfplumber and plumb_fix.
- The one-item list rule: OpenDataLoader makes such lists from a paragraph's first word; no tagged sample has one.
- A harder table: title, group and note rows, and a false header cell, through the work order's `tables`.
- Harder title and note rows (#67): two title lines make one Caption, a note cell holding a P, a title cell's ActualText and
  Lang, Headers naming a removed or demoted cell, rows on two pages, text drawn in a form, a bad row number in one table.
- Reading order: a section read out of printed order, moved back with move_section (the review page's preview, apply.py's
  move and verify.py's section-order check, new or already in the original); no baseline book uses move_section.
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

# ---- reading order: a section read out of printed order, moved back with move_section (no sample book has one)
def sections_pdf(path, order=(1, 3, 2, 4)):
    """One page per entry of order, one paragraph each, each in its own Sect under one Part, read in the given page order."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    for n in range(1, len(order) + 1):
        content = f'/P <</MCID 0>> BDC BT /F1 11 Tf 72 500 Td (Section {n} opens on page {n}.) Tj ET EMC\n'
        pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], StructParents=n - 1,
                         Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)), Contents=pikepdf.Stream(pdf, content.encode('latin-1')))))
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    part = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Part, P=doc))
    nums, sects = pikepdf.Array(), {}
    for n in range(1, len(order) + 1):
        pg = pdf.pages[n - 1].obj
        sect = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Sect, P=part, Pg=pg))
        p = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=sect, Pg=pg, K=0))
        sect.K = pikepdf.Array([p]); sects[n] = sect; nums.append(n - 1); nums.append(pikepdf.Array([p]))
    part.K = pikepdf.Array([sects[n] for n in order]); doc.K = pikepdf.Array([part]); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=nums))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path)
    return path

def part_pages(path):
    with pikepdf.open(path) as p:
        px = {g.obj.objgen: i for i, g in enumerate(p.pages, 1)}
        doc = p.Root.StructTreeRoot.K
        doc = doc[0] if isinstance(doc, pikepdf.Array) else doc
        part = doc.K[0] if isinstance(doc.K, pikepdf.Array) else doc.K
        return [px[k.Pg.objgen] for k in part.K]

def apply_and_verify(tmp_path, src, wo, name):
    w = tmp_path / f'{name}.json'; w.write_text(json.dumps({'schema': 'workorder/0.1', **wo}))
    out = tmp_path / f'{name}.pdf'
    run('apply.py', src, w, out); run('verify.py', src, out)
    return out, json.load(open(str(out) + '.verify.json', encoding='utf-8'))['wcag']['section_order']

def test_section_read_out_of_order_is_flagged_and_moved_back(tmp_path):
    from review import core
    src = sections_pdf(tmp_path / 'sections.pdf')
    run('audit.py', src, tmp_path / 'audit')
    digest = json.load(open(tmp_path / 'audit' / 'digest.json', encoding='utf-8'))
    ro = core.reading_order(digest, json.load(open(tmp_path / 'audit' / 'fulltext.json', encoding='utf-8')))
    assert ro['detail'] and [ro['entries'][x['i']]['first'] for x in ro['flagged']] == [2]
    # the review page's preview uses the executor's match: it must show the order apply.py then makes
    move = {'pages': [2, 2], 'before_page': 3}
    c = core.move_preview(ro['entries'], 2, 2, 3)
    assert c['candidates'] == 1 and c['host_found'] and c['flags_before'] == 1 and c['flags_after'] == 0
    out, so = apply_and_verify(tmp_path, src, {'move_section': move}, 'moved')
    assert part_pages(out) == [e['first'] for e in c['siblings_after']] == [1, 2, 3, 4]
    assert so['flagged'] == [] and so['new_count'] == 0 and so['original_flagged'] == 1
    log = json.load(open(str(out) + '.log.json', encoding='utf-8'))['section_move']        # where it went, for report.py
    assert log == {'pages': [2, 2], 'host': 'Part', 'host_pages': [1, 4], 'before_page': 3, 'after_page': 1}
    assert (c['moved_pages'], c['host'], c['host_pages']) == ([2, 2], 'Part', [1, 4])     # the preview says the same

def test_a_move_the_reviewer_adds_is_made_like_the_ais(tmp_path):
    """No AI move: the review page offers one for the flagged section, with the suggested page; the reviewer's addition
    goes into the work order and apply.py makes it, as the preview shows."""
    from review import core
    src = sections_pdf(tmp_path / 'sections.pdf')
    run('audit.py', src, tmp_path / 'audit')
    digest = json.load(open(tmp_path / 'audit' / 'digest.json', encoding='utf-8'))
    ro = core.reading_order(digest, json.load(open(tmp_path / 'audit' / 'fulltext.json', encoding='utf-8')))
    t = core.addable({}, digest, ro)['move_section'][0]
    assert t['default'] == {'pages': [2, 2], 'before_page': 3} and t['context']['candidates'] == 1 and t['context']['host_found']
    wo = {}
    assert core.add_entries(wo, [{'kind': 'move_section', 'target': t['target'], 'value': t['default']}], {'move_section': [t]}, 'Kim') == []
    out, so = apply_and_verify(tmp_path, src, wo, 'added')
    assert part_pages(out) == [e['first'] for e in t['context']['siblings_after']] == [1, 2, 3, 4] and so['flagged'] == []

def test_the_trial_run_reports_the_executors_figure_moves(tmp_path):
    from review import core
    src = sections_pdf(tmp_path / 'sections.pdf')
    (tmp_path / 'workorder.ai.json').write_text(json.dumps({'schema': 'workorder/0.1'}))
    res = core.dry_run(str(tmp_path), str(src))
    assert res['figure_moves'] == [] and res['seconds'] >= 0 and res['section_move'] is None   # no figures, no move asked
    (tmp_path / 'workorder.ai.json').write_text(json.dumps({'schema': 'workorder/0.1', 'move_section': {'pages': [2, 2], 'before_page': 3}}))
    res = core.dry_run(str(tmp_path), str(src))
    assert res['section_move']['made']['before_page'] == 3 and res['section_moves'] == [res['section_move']]   # what the move card shows
    (tmp_path / 'workorder.ai.json').write_text(json.dumps({'schema': 'workorder/0.1', 'move_section': {'pages': [2, 2], 'before_page': 99}}))
    assert 'host found: False' in core.dry_run(str(tmp_path), str(src))['section_move']['refused']
    bad = core.dry_run(str(tmp_path), str(tmp_path / 'missing.pdf'))
    assert bad['figure_moves'] is None and 'stopped' in bad['why']             # the card then says they were not worked out

def test_two_moves_are_made_in_turn_as_the_previews_chain_them(tmp_path):
    """PDF 2 and PDF 5 both read out of place; two moves put them back, the second matched on the tree the first left."""
    from review import core
    src = sections_pdf(tmp_path / 'sections.pdf', order=(1, 3, 2, 4, 6, 5))
    run('audit.py', src, tmp_path / 'audit')
    digest = json.load(open(tmp_path / 'audit' / 'digest.json', encoding='utf-8'))
    ro = core.reading_order(digest, json.load(open(tmp_path / 'audit' / 'fulltext.json', encoding='utf-8')))
    assert sorted(ro['entries'][x['i']]['first'] for x in ro['flagged']) == [2, 5]
    moves = [{'pages': [2, 2], 'before_page': 3}, {'pages': [5, 5], 'before_page': 6}]
    pvs = core.chain_previews(ro['entries'], [(m['pages'], m['before_page']) for m in moves])
    assert [p['candidates'] for p in pvs] == [1, 1] and all(p['host_found'] for p in pvs) and pvs[1]['flags_after'] == 0
    out, so = apply_and_verify(tmp_path, src, {'move_section': moves}, 'two')
    assert part_pages(out) == [e['first'] for e in pvs[1]['siblings_after']] == [1, 2, 3, 4, 5, 6]
    assert so['flagged'] == [] and so['new_count'] == 0
    log = json.load(open(str(out) + '.log.json', encoding='utf-8'))
    assert [m['before_page'] for m in log['section_moves']] == [3, 6] and log['section_move'] == log['section_moves'][0]

def figure_pdf(path):
    """Three pages, one paragraph each; page 1 also holds a figure whose Div is read last, after page 3."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    for n in range(1, 4):
        content = f'/P <</MCID 0>> BDC BT /F1 11 Tf 72 500 Td (Text on page {n}.) Tj ET EMC\n'
        if n == 1: content += '/Figure <</MCID 1>> BDC 0 0 1 rg 72 200 200 150 re f EMC\n'
        pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], StructParents=n - 1,
                         Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)), Contents=pikepdf.Stream(pdf, content.encode('latin-1')))))
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    nums, ks = pikepdf.Array(), []
    for n in range(1, 4):
        pg = pdf.pages[n - 1].obj
        p = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg, K=0)); ks.append(p)
        row = [p]
        if n == 1:
            div = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Div, P=doc, Pg=pg))
            fig = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=div, Pg=pg, K=1, Alt=pikepdf.String('A blue box')))
            div.K = pikepdf.Array([fig]); row.append(fig)
        nums.append(n - 1); nums.append(pikepdf.Array(row))
    doc.K = pikepdf.Array(ks + [div]); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=nums))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path)
    return path

def test_the_figure_step_runs_unless_the_work_order_turns_it_off(tmp_path):
    src = figure_pdf(tmp_path / 'figure.pdf')
    for name, wo, moved in (('default', {}, True), ('on', {'fix_figure_order': True}, True), ('off', {'fix_figure_order': False}, False)):
        w = tmp_path / f'{name}.json'; w.write_text(json.dumps({'schema': 'workorder/0.1', **wo}))
        out = tmp_path / f'{name}.pdf'
        run('apply.py', src, w, out)
        log = json.load(open(str(out) + '.log.json', encoding='utf-8'))
        assert bool(log.get('figure_moves')) == moved and bool(log.get('figure_order_off')) == (not moved), name
    from review import core                                   # the review's trial run lists them even when the AI turned it off
    (tmp_path / 'workorder.ai.json').write_text(json.dumps({'schema': 'workorder/0.1', 'fix_figure_order': False}))
    assert [m['page'] for m in core.dry_run(str(tmp_path), str(src))['figure_moves']] == [1]

def test_section_out_of_order_in_the_original_is_not_new(tmp_path):
    src = sections_pdf(tmp_path / 'sections.pdf')
    out, so = apply_and_verify(tmp_path, src, {}, 'kept')
    assert part_pages(out) == [1, 3, 2, 4]
    assert [(x['page'], x['state']) for x in so['flagged']] == [(2, 'original')] and so['new_count'] == 0

def test_a_move_that_puts_a_section_out_of_order_is_new(tmp_path):
    src = sections_pdf(tmp_path / 'sections.pdf', order=(1, 2, 3, 4))
    out, so = apply_and_verify(tmp_path, src, {'move_section': {'pages': [4, 4], 'before_page': 2}}, 'wrong')
    assert part_pages(out) == [1, 4, 2, 3]
    assert [(x['page'], x['state']) for x in so['flagged']] == [(4, 'new')] and so['new_count'] == 1

def test_a_misplaced_section_moved_to_another_wrong_place_counts_as_new(tmp_path):
    src = sections_pdf(tmp_path / 'sections.pdf', order=(1, 2, 3, 5, 6, 4))           # PDF 4 read last
    out, so = apply_and_verify(tmp_path, src, {'move_section': {'pages': [4, 4], 'before_page': 2}}, 'again')
    assert part_pages(out) == [1, 4, 2, 3, 5, 6]                                     # still out of place, somewhere else
    assert [(x['page'], x['state'], x['new']) for x in so['flagged']] == [(4, 'moved', True)] and so['new_count'] == 1

# ---- a table with a title row, column names, a group row and a source note, read through the work order (WCAG 1.3.1)
TABLE = [['Table 1 Clans'], ['Clan', 'Surname'], ['Moiety 1'], ['Wurra', 'Lalara'], ['Source: fieldwork']]

def table_pdf(path):
    flat = [t for row in TABLE for t in row]
    content = ''.join(f'/TD <</MCID {i}>> BDC BT /F1 11 Tf 72 {500 - 20 * i} Td ({t}) Tj ET EMC\n' for i, t in enumerate(flat))
    def tagged(pdf, page):
        root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
        doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
        def el(s, parent, k, **extra):
            return pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + s), P=parent, Pg=page.obj, K=k, **extra))
        table = el('Table', doc, pikepdf.Array()); leaves, rows, i = [], [], 0
        for row in TABLE:
            tr = el('TR', table, pikepdf.Array()); cells = []
            for _ in row:
                a = pikepdf.Dictionary(O=pikepdf.Name('/Table'), ColSpan=2) if len(row) == 1 else None
                c = el('TH' if i == 2 else 'TD', tr, i, **({'A': a} if a is not None else {})); cells.append(c); leaves.append(c); i += 1
            tr.K = pikepdf.Array(cells); rows.append(tr)
        table.K = pikepdf.Array(rows); doc.K = pikepdf.Array([table])
        root.K = doc; root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pikepdf.Array(leaves)])))
        page.obj.StructParents = 0
        pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
        return table
    return one_page(content, path, tagged)

def read_table(path):
    """-> first part of the table, rows as [[(tag, scope, headers)]], the document's top tags, and the IDTree."""
    pdf = pikepdf.open(path); root = pdf.Root.StructTreeRoot
    doc = root.K[0] if isinstance(root.K, pikepdf.Array) else root.K
    ks = list(doc.K) if isinstance(doc.K, pikepdf.Array) else [doc.K]
    t = next(k for k in ks if str(k.S) == '/Table'); parts = list(t.K)
    def attrs(c):
        a = c.get('/A')
        return next((d for d in (a if isinstance(a, pikepdf.Array) else [a] if a is not None else []) if str(d.get('/O')) == '/Table'), {})
    rows = [[(str(c.S)[1:], str(attrs(c).get('/Scope', ''))[1:], [bytes(h).decode() for h in attrs(c).get('/Headers', [])]) for c in r.K]
            for r in parts if str(r.S) == '/TR']
    ids = {}
    if '/IDTree' in root:
        names = root.IDTree.Names
        ids = {bytes(names[i]).decode(): names[i + 1] for i in range(0, len(names), 2)}
    return {'first': str(parts[0].S)[1:], 'rows': rows, 'after': [str(k.S)[1:] for k in ks], 'ids': ids, 'pdf': pdf}

def apply_table(tmp_path, reading, name):
    src = tmp_path / 'table.pdf'; table_pdf(src)
    w = tmp_path / f'{name}.json'; w.write_text(json.dumps({'schema': 'workorder/0.2', 'tables': [{'obj': table_obj(src), **reading}]}))
    out = tmp_path / f'{name}.pdf'; run('apply.py', src, w, out)
    return src, out

def table_obj(path):
    pdf = pikepdf.open(path); doc = pdf.Root.StructTreeRoot.K
    doc = doc[0] if isinstance(doc, pikepdf.Array) else doc
    t = doc.K[0] if isinstance(doc.K, pikepdf.Array) else doc.K
    return f'{t.objgen[0]} {t.objgen[1]}'

def run_ok_tags(pdf):
    """Every tag on the one page says so, and each piece of marked content is owned by exactly the tag the ParentTree names."""
    root = pdf.Root.StructTreeRoot; arr = root.ParentTree.Nums[1]; page = pdf.pages[0].obj.objgen
    def walk(n):
        for k in (list(n.K) if isinstance(n.get('/K'), pikepdf.Array) else [n.K] if '/K' in n else []):
            if isinstance(k, pikepdf.Dictionary): yield from walk(k)
            else:
                assert n.Pg.objgen == page and arr[int(k)].objgen == n.objgen
                yield int(k)
    return sorted(walk(root.K[0] if isinstance(root.K, pikepdf.Array) else root.K)) == list(range(sum(len(r) for r in TABLE)))

def test_a_harder_table_reads_as_caption_headers_groups_and_note(tmp_path):
    src, out = apply_table(tmp_path, {'title_rows': 1, 'header_rows': 1, 'group_rows': [2], 'note_rows': 1}, 'read')
    t = read_table(out)
    assert t['first'] == 'Caption' and t['after'] == ['Table', 'P'] and len(t['rows']) == 3
    assert [c[:2] for c in t['rows'][0]] == [('TH', 'Column'), ('TH', 'Column')] and t['rows'][1][0][:2] == ('TH', 'Column')
    data = t['rows'][2]
    assert all(tag == 'TD' and scope == '' and len(hs) == 2 for tag, scope, hs in data)
    for _, _, hs in data:
        for h in hs: assert h in t['ids'] and str(t['ids'][h].S) == '/TH'
    assert gap_text_of(out) == gap_text_of(src)         # the page's text is untouched
    assert run_ok_tags(t['pdf'])

def test_a_header_the_reading_does_not_name_goes_back_to_a_data_cell(tmp_path):
    """"Surname" is tagged TH in the source; here only the first column heads anything."""
    _, out = apply_table(tmp_path, {'title_rows': 1, 'header_cols': 1, 'note_rows': 1, 'group_rows': [2]}, 'demote')
    t = read_table(out)
    assert t['rows'][0][0][0] == 'TH' and t['rows'][0][1][0] == 'TD' and t['rows'][0][1][1] == ''

def test_a_reading_that_does_not_fit_leaves_the_table_alone(tmp_path):
    _, out = apply_table(tmp_path, {'title_rows': 2, 'header_rows': 1}, 'refuse')       # row 1 holds two things
    t = read_table(out)
    assert t['first'] == 'TR' and len(t['rows']) == 5

# ---- harder cases for the title and note rows (#67): built with tables_pdf, one case per way they could go wrong
def tables_pdf(path, tables, npages=1, caption=False):
    """Tables on npages pages. A table is a list of rows; a cell is its text, or a dict: text, page (1, 2, …), tag (TD or
    TH), inner (a tag between the cell and its text, e.g. 'P'), attrs ({key: value} on the cell), id, headers (IDs),
    rowspan, form (the text is drawn in a form XObject, reached by an MCR with /Stm). caption: the first table already
    has a Caption. -> the tables' object refs."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    xobjs = [pikepdf.Dictionary() for _ in range(npages)]
    for p in range(npages):
        pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], StructParents=p,
                                                         Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=xobjs[p]))))
    pages = [pg.obj for pg in pdf.pages]
    draw = [[] for _ in range(npages)]; pt = [[] for _ in range(npages)]; forms = []; ids = []
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    def el(s, parent, k, p, **extra):
        return pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + s), P=parent, Pg=pages[p], K=k, **extra))
    def mark(owner, text, p, form):
        y = 540 - 16 * (len(draw[p]) + len(forms))
        if not form:
            m = len(pt[p]); pt[p].append(owner)
            draw[p].append(f'/Span <</MCID {m}>> BDC BT /F1 11 Tf 72 {y} Td ({text}) Tj ET EMC\n'); return m
        fx = pikepdf.Stream(pdf, f'/Span <</MCID 0>> BDC BT /F1 11 Tf 72 {y} Td ({text}) Tj ET EMC\n'.encode('latin-1'))
        fx.Type = pikepdf.Name.XObject; fx.Subtype = pikepdf.Name.Form; fx.BBox = [0, 0, 432, 576]
        fx.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)); fx.StructParents = 100 + len(forms)
        name = f'/Fm{len(forms)}'; xobjs[p][name] = fx; draw[p].append(f'q {name} Do Q\n'); forms.append((fx, owner))
        return pikepdf.Dictionary(Type=pikepdf.Name.MCR, Pg=pages[p], Stm=fx, MCID=0)
    top = []
    for n, rows in enumerate(tables):
        table = el('Table', doc, pikepdf.Array(), 0); trs = []
        if caption and n == 0:
            cap = el('Caption', table, pikepdf.Array(), 0); cap.K = pikepdf.Array([mark(cap, 'Old caption', 0, False)]); trs.append(cap)
        for row in rows:
            cells = [c if isinstance(c, dict) else {'text': c} for c in row]
            tr = el('TR', table, pikepdf.Array(), cells[0].get('page', 1) - 1); tcs = []
            for c in cells:
                p = c.get('page', 1) - 1
                a = pikepdf.Dictionary(O=pikepdf.Name('/Table'))
                if len(row) == 1: a.ColSpan = 2
                if c.get('rowspan'): a.RowSpan = c['rowspan']
                if c.get('headers'): a.Headers = pikepdf.Array([pikepdf.String(h) for h in c['headers']])
                cell = el(c.get('tag', 'TD'), tr, pikepdf.Array(), p, A=a)
                for k, v in (c.get('attrs') or {}).items(): cell[k] = v
                if c.get('id'): cell.ID = pikepdf.String(c['id']); ids.append((c['id'], cell))
                if c.get('inner'):
                    inner = el(c['inner'], cell, pikepdf.Array(), p); inner.K = pikepdf.Array([mark(inner, c['text'], p, c.get('form'))])
                    cell.K = pikepdf.Array([inner])
                else: cell.K = pikepdf.Array([mark(cell, c['text'], p, c.get('form'))])
                tcs.append(cell)
            tr.K = pikepdf.Array(tcs); trs.append(tr)
        table.K = pikepdf.Array(trs); top.append(table)
    doc.K = pikepdf.Array(top); root.K = doc
    nums = []
    for p in range(npages): nums += [p, pdf.make_indirect(pikepdf.Array(pt[p]))]
    for fx, owner in forms: nums += [int(fx.StructParents), pdf.make_indirect(pikepdf.Array([owner]))]
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array(nums))); root.ParentTreeNextKey = 100 + len(forms)
    if ids: root.IDTree = pikepdf.Dictionary(Names=pikepdf.Array([x for i, c in sorted(ids, key=lambda t: t[0]) for x in (pikepdf.String(i), c)]))
    for p in range(npages): pages[p].Contents = pikepdf.Stream(pdf, ''.join(draw[p]).encode('latin-1'))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path)
    with pikepdf.open(path) as p:                       # saving renumbers the objects
        return [f'{t.objgen[0]} {t.objgen[1]}' for t in elems(elems(p.Root.StructTreeRoot)[0])]

def apply_tables(tmp_path, tables, readings, npages=1, caption=False):
    """-> the remediated PDF (open) and the executor's log."""
    src = tmp_path / 'tables.pdf'; refs = tables_pdf(src, tables, npages, caption)
    w = tmp_path / 'wo.json'
    w.write_text(json.dumps({'schema': 'workorder/0.2', 'tables': [{'obj': r, **x} for r, x in zip(refs, readings) if x is not None]}))
    out = tmp_path / 'out.pdf'; run('apply.py', src, w, out)
    return pikepdf.open(out), json.loads(open(f'{out}.log.json').read())

def kids_of(n):
    k = n.get('/K')
    return [] if k is None else list(k) if isinstance(k, pikepdf.Array) else [k]
def elems(n): return [k for k in kids_of(n) if isinstance(k, pikepdf.Dictionary) and '/S' in k]
def tag(n): return str(n.S)[1:]
def top_tags(pdf):
    doc = elems(pdf.Root.StructTreeRoot)[0]
    return doc, elems(doc)
def every_elem(pdf):
    out, stack = [], list(elems(pdf.Root.StructTreeRoot))
    while stack:
        n = stack.pop(); out.append(n); stack += elems(n)
    return out
def owners_ok(pdf):
    """Each piece of marked content, on each page and in each form, is owned by exactly the tag its ParentTree entry names."""
    nums = pdf.Root.StructTreeRoot.ParentTree.Nums; pt = {int(nums[i]): nums[i + 1] for i in range(0, len(nums), 2)}
    page_key = {p.objgen: int(p.StructParents) for p in (pg.obj for pg in pdf.pages)}
    seen = 0
    for n in every_elem(pdf):
        for k in kids_of(n):
            if isinstance(k, int):
                assert pt[page_key[n.Pg.objgen]][k].objgen == n.objgen, f'MCID {k} of {tag(n)} is on another page or owned by another tag'
            elif isinstance(k, pikepdf.Dictionary) and str(k.get('/Type')) == '/MCR':
                key = int(k.Stm.StructParents) if '/Stm' in k else page_key[(k.Pg if '/Pg' in k else n.Pg).objgen]
                assert pt[key][int(k.MCID)].objgen == n.objgen, f'MCR {int(k.MCID)} of {tag(n)} is indexed under another tag'
            else: continue
            seen += 1
    return seen
def table_cells(t): return [c for r in elems(t) if tag(r) == 'TR' for c in elems(r)]
def headers_of(c):
    a = c.get('/A'); ds = a if isinstance(a, pikepdf.Array) else [a] if a is not None else []
    return [bytes(h).decode() for d in ds if isinstance(d, pikepdf.Dictionary) for h in d.get('/Headers', [])]

T2 = [['Table 3'], ['Clan names by moiety'], ['Clan', 'Surname'], ['Wurra', 'Lalara'], ['Source: fieldwork']]

def test_two_title_rows_make_one_caption(tmp_path):
    pdf, log = apply_tables(tmp_path, [T2], [{'title_rows': 2, 'header_rows': 1, 'note_rows': 1}])
    _, top = top_tags(pdf); t = top[0]
    assert [tag(k) for k in elems(t)].count('Caption') == 1 and tag(elems(t)[0]) == 'Caption'
    assert len(kids_of(elems(t)[0])) == 2 and owners_ok(pdf) == 7

def test_a_table_that_has_a_caption_gets_no_second_one(tmp_path):
    pdf, log = apply_tables(tmp_path, [T2], [{'title_rows': 2, 'header_rows': 1}], caption=True)
    _, top = top_tags(pdf); t = top[0]
    assert [tag(k) for k in elems(t)].count('Caption') == 1 and len([k for k in elems(t) if tag(k) == 'TR']) == 5
    assert any('already has a caption' in r['why'] for r in log['rejected'])

def test_a_note_cell_holding_a_paragraph_is_not_wrapped_in_another(tmp_path):
    rows = T2[1:-1] + [[{'text': 'Source: fieldwork', 'inner': 'P'}]]
    pdf, _ = apply_tables(tmp_path, [rows], [{'title_rows': 1, 'header_rows': 1, 'note_rows': 1}])
    _, top = top_tags(pdf)
    assert [tag(k) for k in top] == ['Table', 'P'] and not elems(top[1])     # the cell's own P, not a P holding a P
    assert owners_ok(pdf) == 6

def test_the_title_cell_keeps_its_actual_text_and_language(tmp_path):
    rows = [[{'text': 'Tbl 3', 'attrs': {'/ActualText': pikepdf.String('Table 3'), '/Lang': pikepdf.String('en-GB')}}]] + T2[1:]
    pdf, _ = apply_tables(tmp_path, [rows], [{'title_rows': 2, 'header_rows': 1, 'note_rows': 1}])
    _, top = top_tags(pdf); cap = elems(top[0])[0]
    held = [cap] + [k for k in every_elem(pdf) if k.get('/P') is not None and k.P.objgen == cap.objgen]
    assert any(str(k.get('/ActualText', '')) == 'Table 3' and str(k.get('/Lang', '')) == 'en-GB' for k in held)
    assert str(cap.get('/ActualText', '')) != 'Table 3'                   # not on the Caption: it would hide the subtitle

def test_no_cell_names_a_removed_or_demoted_header(tmp_path):
    rows = [[{'text': 'Table 3', 'id': 'cap'}], [{'text': 'Clan', 'id': 'h1', 'tag': 'TH'}, {'text': 'Surname', 'id': 'h2', 'tag': 'TH'}],
            ['Wurra', {'text': 'Lalara', 'headers': ['cap', 'h2']}], [{'text': 'Rrawa', 'id': 'r1', 'tag': 'TH'}, {'text': 'Mamarika', 'headers': ['r1']}]]
    pdf, _ = apply_tables(tmp_path, [rows], [{'title_rows': 1, 'header_rows': 1}])     # no header column: "Rrawa" goes back to TD
    _, top = top_tags(pdf); live = {bytes(c.ID).decode() for c in every_elem(pdf) if '/ID' in c and tag(c) == 'TH'}
    for c in table_cells(top[0]): assert set(headers_of(c)) <= live, f'{tag(c)} names {headers_of(c)}'
    names = pdf.Root.StructTreeRoot.IDTree.Names
    reach = {c.objgen for c in every_elem(pdf)}
    assert all(names[i + 1].objgen in reach for i in range(0, len(names), 2))

def test_a_note_row_on_the_next_page_keeps_its_page(tmp_path):
    rows = T2[:-1] + [[{'text': 'Source: fieldwork', 'page': 2}]]
    pdf, _ = apply_tables(tmp_path, [rows], [{'title_rows': 2, 'header_rows': 1, 'note_rows': 1}], npages=2)
    _, top = top_tags(pdf)
    assert [tag(k) for k in top] == ['Table', 'P'] and owners_ok(pdf) == 7

def test_title_rows_from_two_pages_keep_their_pages(tmp_path):
    rows = [['Table 3'], [{'text': 'Clan names by moiety', 'page': 2}], [{'text': 'Clan', 'page': 2}, {'text': 'Surname', 'page': 2}],
            [{'text': 'Wurra', 'page': 2}, {'text': 'Lalara', 'page': 2}]]
    pdf, _ = apply_tables(tmp_path, [rows], [{'title_rows': 2, 'header_rows': 1}], npages=2)
    assert owners_ok(pdf) == 6

def test_note_text_drawn_in_a_form_is_indexed_under_its_new_tag(tmp_path):
    rows = T2[1:-1] + [[{'text': 'Source: fieldwork', 'form': True}]]
    pdf, _ = apply_tables(tmp_path, [rows], [{'title_rows': 1, 'header_rows': 1, 'note_rows': 1}])
    _, top = top_tags(pdf)
    assert [tag(k) for k in top] == ['Table', 'P'] and owners_ok(pdf) == 6

def test_a_bad_row_number_rejects_only_that_table(tmp_path):
    pdf, log = apply_tables(tmp_path, [T2, T2], [{'header_rows': 1, 'title_rows': 2, 'group_rows': [40]}, {'title_rows': 2, 'header_rows': 1, 'note_rows': 1}])
    _, top = top_tags(pdf)
    assert not log['failed'] and any('not in the table' in r['why'] for r in log['rejected'])
    assert tag(elems(top[0])[0]) == 'TR' and tag(elems(top[1])[0]) == 'Caption'
