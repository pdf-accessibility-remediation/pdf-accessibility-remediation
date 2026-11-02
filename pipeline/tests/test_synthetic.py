"""test_synthetic.py: the real pdfplumber, audit.py and apply.py on tiny hand-made PDFs, for rules no sample book reaches.

    python -m pytest tests/test_synthetic.py -q

- Word breaks drawn as gaps, with no space characters (TeX, Prince): every sample book has real spaces, so the regression
  test never reaches gaptext's gap rule through pdfplumber and plumb_fix.
- The one-item list rule: OpenDataLoader makes such lists from a paragraph's first word; no tagged sample has one.
- A harder table: title, group and note rows, and a false header cell, through the work order's `tables`.
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
