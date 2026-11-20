"""langpdf.py: tiny tagged PDFs for the language-tagging tests (#118): no book content. Imported by test_langcands.py,
test_mcsplit.py and test_language_parts.py.

    build(path, runs, doc_lang='en')  -> path

Each run is a dict:
    text      the text to draw (one string), or body: a list of content-stream lines drawn between the marks
    font      F1 Helvetica (WinAnsi) · F2 two-byte Type0 Identity-H with a bfchar ToUnicode map · F3 a simple font whose
              /Differences names macron glyphs and that has no ToUnicode map · F4 a simple font with a bfrange map ·
              F5 a Type3 font · F6 Helvetica-Oblique (italic)
    outside   True: the marks sit outside the text object (BDC BT … ET EMC), as in many InDesign books
    lang      a /Lang written inside the run's marks (the BDC), as most born-digital books carry 'en-US'
    tag       the structure type (P by default); span_lang: the run is already a Span with this /Lang
Every run gets its own P (or Span) under one Document, MCID = its index, one ParentTree array.
"""
import pikepdf

F3_CODES = {'ō': 0x80, 'ā': 0x81, 'ū': 0x82, 'ī': 0x83}         # F3's /Differences: 128 /omacron 129 /amacron …
F3_NAMES = ['/omacron', '/amacron', '/umacron', '/imacron']
T0_START = 0x100

def _cmap(entries, ranges=()):
    body = ''.join(f'<{c:04X}> <{t.encode("utf-16-be").hex().upper()}>\n' for c, t in entries)
    rng = ''.join(f'<{a:02X}> <{b:02X}> <{d.encode("utf-16-be").hex().upper()}>\n' for a, b, d in ranges)
    width = 2 if not ranges else 1
    cs = '<0000> <FFFF>' if width == 2 else '<00> <FF>'
    return ('/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo <</Registry (Adobe) /Ordering (UCS) /Supplement 0>> def\n'
            f'/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n{cs}\nendcodespacerange\n'
            + (f'{len(entries)} beginbfchar\n{body}endbfchar\n' if entries else '')
            + (f'{len(ranges)} beginbfrange\n{rng}endbfrange\n' if ranges else '')
            + 'endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n').encode()

T0_CHARS = [chr(c) for c in range(32, 127)] + list('ōāūīʻēŚṣṇ') + ['ﬁ'] + list('地獄と極楽中文한국어')   # CJK appended: earlier codes unchanged

def t0_hex(text):
    """F2's codes for text, as a hex string; 'ﬁ' stands for one ligature glyph that reads as 'fi'."""
    return '<' + ''.join(f'{T0_START + T0_CHARS.index(ch):04X}' for ch in text) + '>'

def f3_hex(text):
    return '<' + ''.join(f'{F3_CODES[ch]:02X}' if ch in F3_CODES else f'{ord(ch):02X}' for ch in text) + '>'

def lit(text):
    return '(' + text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') + ')'

def fonts(pdf):
    helv = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    obl = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name('/Helvetica-Oblique'),
                             Encoding=pikepdf.Name.WinAnsiEncoding)
    t0 = pikepdf.Dictionary(
        Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type0, BaseFont=pikepdf.Name('/Helvetica'), Encoding=pikepdf.Name('/Identity-H'),
        DescendantFonts=pikepdf.Array([pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.CIDFontType2, BaseFont=pikepdf.Name('/Helvetica'), DW=600,
            CIDSystemInfo=pikepdf.Dictionary(Registry=pikepdf.String('Adobe'), Ordering=pikepdf.String('Identity'), Supplement=0),
            FontDescriptor=pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.FontDescriptor, FontName=pikepdf.Name('/Helvetica'), Flags=32,
                                                                FontBBox=[0, -200, 1000, 900], ItalicAngle=0, Ascent=800, Descent=-200, CapHeight=700, StemV=80)),
            CIDToGIDMap=pikepdf.Name.Identity))]),
        ToUnicode=pdf.make_stream(_cmap([(T0_START + i, 'fi' if c == 'ﬁ' else c) for i, c in enumerate(T0_CHARS)])))
    f3 = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                            Encoding=pikepdf.Dictionary(Type=pikepdf.Name.Encoding, BaseEncoding=pikepdf.Name.WinAnsiEncoding,
                                                        Differences=pikepdf.Array([128] + [pikepdf.Name(n) for n in F3_NAMES])))
    f4 = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                            Encoding=pikepdf.Name.WinAnsiEncoding, ToUnicode=pdf.make_stream(_cmap([], [(0x20, 0x7E, ' ')])))
    glyph = pdf.make_stream(b'500 0 0 0 400 600 d1 0 0 400 600 re f')
    f5 = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type3, FontBBox=[0, 0, 400, 600],
                            FontMatrix=[0.001, 0, 0, 0.001, 0, 0], FirstChar=97, LastChar=122, Widths=[500] * 26,
                            Encoding=pikepdf.Dictionary(Type=pikepdf.Name.Encoding, Differences=pikepdf.Array([97] + [pikepdf.Name(f'/g{c}') for c in 'abcdefghijklmnopqrstuvwxyz'])),
                            CharProcs=pikepdf.Dictionary({f'/g{c}': glyph for c in 'abcdefghijklmnopqrstuvwxyz'}), Resources=pikepdf.Dictionary())
    return pikepdf.Dictionary(F1=helv, F2=t0, F3=f3, F4=f4, F5=f5, F6=obl)

def show(font, text):
    if font == 'F2': return f'{t0_hex(text)} Tj'
    if font == 'F3': return f'{f3_hex(text)} Tj'
    return f'{lit(text)} Tj'

def build(path, runs, doc_lang='en', step=40):
    pdf = pikepdf.new()
    lines, y = [], 740
    for n, r in enumerate(runs):
        font = r.get('font', 'F1')
        props = f'<</MCID {n}' + (f' /Lang ({r["lang"]})' if r.get('lang') else '') + '>>'
        tag = 'Span' if r.get('span_lang') else r.get('tag', 'P')
        body = r.get('body') or [show(font, r['text'])]
        if r.get('outside'):
            lines += [f'/{tag} {props} BDC', 'BT', f'/{font} 11 Tf 13 TL 72 {y} Td', *body, 'ET', 'EMC']
        else:
            lines += ['BT', f'/{font} 11 Tf 13 TL 72 {y} Td', f'/{tag} {props} BDC', *body, 'EMC', 'ET']
        y -= step                                       # step: the line spacing (smaller fits more runs on the one page)
    page = pdf.add_blank_page(page_size=(612, 792))
    page.obj.Resources = pikepdf.Dictionary(Font=fonts(pdf))
    page.obj.Contents = pdf.make_stream('\n'.join(lines).encode('latin-1'))
    page.obj.StructParents = 0
    st = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=st, K=pikepdf.Array()))
    els = []
    for n, r in enumerate(runs):
        d = pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + ('Span' if r.get('span_lang') else r.get('tag', 'P'))),
                               P=doc, Pg=page.obj, K=pikepdf.Array([n]))
        if r.get('span_lang'): d.Lang = pikepdf.String(r['span_lang'])
        if r.get('actual_text'): d.ActualText = pikepdf.String(r['actual_text'])
        els.append(pdf.make_indirect(d))
    doc.K = pikepdf.Array(els); st.K = pikepdf.Array([doc])
    st.ParentTree = pikepdf.Dictionary(Nums=pikepdf.Array([0, pdf.make_indirect(pikepdf.Array(els))])); st.ParentTreeNextKey = 1
    pdf.Root.StructTreeRoot = st; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String(doc_lang)
    pdf.docinfo['/Title'] = 'Synthetic language test'; pdf.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
    pdf.save(path, deterministic_id=True)
    return path


def build_lines(path, lines, doc_lang='en', at_parent=None):
    """Several runs on one line (#150, #161): lines is a list of lines, each a list of pieces drawn left to right in one text
    object, so a piece starts where the last ended unless it says otherwise. A piece is a dict:
        text      the text (F1 Helvetica unless font says otherwise); body: content-stream lines instead (a TJ with kerning)
        parent    the structure element it belongs to (any key; P elements, in order of first use; default 'P0')
        gap       space before it, in thousandths of an em (a TJ move; 0 by default: the pieces touch)
        size      the type size (11 by default); rise: a text rise (a raised note mark)
        at        an ActualText in the run's own marks (BDC); lang: a /Lang in them ('en-US', as born-digital books carry)
        untagged  True: drawn with no marks (no MCID); xy: (x, y) in PDF points, where it is drawn
    Every tagged piece is its own run (MCID in drawing order). at_parent: {parent key: ActualText on that element}.
    Returns the path."""
    pdf = pikepdf.new()
    lines_out, y, n, kids, order = [], 740, 0, {}, []
    for line in lines:
        lines_out += ['BT', f'72 {y} Td']
        cur = None
        for pc in line:
            size, font = pc.get('size', 11), pc.get('font', 'F1')
            if (font, size) != cur: lines_out.append(f'/{font} {size} Tf'); cur = (font, size)
            if pc.get('gap'): lines_out.append(f'[-{pc["gap"]}] TJ')
            if pc.get('xy'): lines_out.append(f'1 0 0 1 {pc["xy"][0]} {pc["xy"][1]} Tm')     # drawn at this point (later in content order)
            lines_out.append(f'{pc.get("rise", 0)} Ts')
            if pc.get('untagged'): lines_out.append(show(font, pc['text'])); continue
            props = f'<</MCID {n}' + (f' /ActualText {lit(pc["at"])}' if pc.get('at') else '') + (f' /Lang ({pc["lang"]})' if pc.get('lang') else '') + '>>'
            lines_out += [f'/Span {props} BDC', *(pc.get('body') or [show(font, pc['text'])]), 'EMC']
            key = pc.get('parent', 'P0')
            if key not in kids: kids[key] = []; order.append(key)
            kids[key].append(n); n += 1
        lines_out.append('ET'); y -= 30
    page = pdf.add_blank_page(page_size=(612, 792))
    page.obj.Resources = pikepdf.Dictionary(Font=fonts(pdf))
    page.obj.Contents = pdf.make_stream('\n'.join(lines_out).encode('latin-1'))
    page.obj.StructParents = 0
    st = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=st, K=pikepdf.Array()))
    els, by_mcid = [], {}
    for key in order:
        d = pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=page.obj, K=pikepdf.Array(kids[key]))
        if at_parent and key in at_parent: d.ActualText = pikepdf.String(at_parent[key])
        el = pdf.make_indirect(d); els.append(el)
        for m in kids[key]: by_mcid[m] = el
    doc.K = pikepdf.Array(els); st.K = pikepdf.Array([doc])
    st.ParentTree = pikepdf.Dictionary(Nums=pikepdf.Array([0, pdf.make_indirect(pikepdf.Array([by_mcid[m] for m in range(n)]))]))
    st.ParentTreeNextKey = 1
    pdf.Root.StructTreeRoot = st; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String(doc_lang)
    pdf.docinfo['/Title'] = 'Synthetic language test'; pdf.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
    pdf.save(path, deterministic_id=True)
    return path
