"""#170 (Language step: tag words whose letters sit in a child tag of the same paragraph): made-up words on tiny tagged PDFs
(no book content), through lib/langcands (the finder), apply.py and verify.py, veraPDF off.

The shape (clans): P [MCID "… Ky", Span [MCID "ô"], MCID "nggi …"]. The child Span is one slot of the P when it carries no
keys beyond /Type /S /P /K /Pg /C /ID, maps to Span, holds runs of letters only, has no spoken text on or around its runs,
is named by nothing (a table header, a /Ref), and every run of it is a whole piece of the place (lib/langjoin.ChildRule,
apply.py plan_phrase). One Span is then written over [the first piece, the child, the last piece]."""
import os, sys, json, subprocess
import pikepdf
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, langcands  # noqa: F401,E402

HELV = dict(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)


def lit(t): return '(' + ''.join(f'\\{ord(ch):03o}' if ord(ch) > 126 else ch for ch in t) + ')'


def build(path, pieces, child_extra=None, child_marks='', child_type='Span', headers_id=None, p_type='P', rolemap=None):
    """pieces: [(text, 'own' | 'child')] on one line, MCID = index. Every 'child' piece is its own child tag of the one P."""
    pdf = pikepdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(**HELV))
    ops = ['BT /F1 11 Tf 72 700 Td']
    for n, (t, kind) in enumerate(pieces):
        extra = child_marks if kind == 'child' else ''
        ops.append(f'/Span <</MCID {n}{extra}>> BDC {lit(t)} Tj EMC')
    ops.append('ET')
    pg = pdf.add_blank_page(page_size=(612, 792))
    pg.obj.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    pg.obj.Contents = pdf.make_stream('\n'.join(ops).encode('latin-1')); pg.obj.StructParents = 0
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, K=pikepdf.Array()))
    st = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot, K=pikepdf.Array([doc])))
    doc.P = st
    p = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + p_type), P=doc, Pg=pg.obj, K=pikepdf.Array()))
    doc.K.append(p)
    arr, ids, kids_ = [], [], []
    for n, (t, kind) in enumerate(pieces):
        if kind == 'own': p.K.append(n); arr.append(p)
        else:
            e = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name('/' + child_type), P=p, Pg=pg.obj,
                                                     K=pikepdf.Array([n]), C=pikepdf.Name('/adbe_text'), ID=pikepdf.String(f'id{n}'), **(child_extra or {})))
            p.K.append(e); arr.append(e); ids += [pikepdf.String(f'id{n}'), e]; kids_.append(e)
    if headers_id is not None:                     # a table cell elsewhere names the child's ID in its /Headers
        tbl = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Table, P=doc, K=pikepdf.Array()))
        td = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.TD, P=tbl, K=pikepdf.Array(),
                                                  A=pikepdf.Dictionary(O=pikepdf.Name('/Table'), Headers=pikepdf.Array([pikepdf.String(headers_id)]))))
        tbl.K.append(td); doc.K.append(tbl)
    st.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pdf.make_indirect(pikepdf.Array(arr))])))
    st.ParentTreeNextKey = 1
    st.IDTree = pdf.make_indirect(pikepdf.Dictionary(Names=pikepdf.Array(ids)))
    st.RoleMap = pikepdf.Dictionary({k: pikepdf.Name(v) for k, v in (rolemap or {}).items()})
    pdf.Root.StructTreeRoot = st; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path)
    return path


def run(script, *args, env=None):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off', **(env or {})),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stderr[-2000:]


def wo(segs, brk=None, lang='ko-Latn', form='Kyônggi'):
    f = {'key': f'unknown|{form}', 'form': form, 'group': 'unknown', 'class': ['unknown'], 'lang': lang, 'confidence': 'high',
         'why': 'language', 'tag': True, 'places': 1}
    return {'language_parts': {'version': 3, 'forms': [f], 'parts': [[1, segs, 0, brk or ['inside'] * (len(segs) - 1)]]}}


def apply_verify(tmp_path, src, w, env=None):
    p = tmp_path / 'wo.json'; p.write_text(json.dumps(w))
    out = str(tmp_path / 'out.pdf')
    run('apply.py', src, p, out, env=env); run('verify.py', src, out)
    return out, json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))


def lang_spans(path):
    """[(lang, [kinds of its kids: an MCID number, or 'el:<S>' for an element])] for every Span with a /Lang."""
    out = []
    with pikepdf.open(path) as pdf:
        def walk(n, d=0):
            if d > 30 or not isinstance(n, pikepdf.Dictionary): return
            if str(n.get('/S')) == '/Span' and '/Lang' in n:
                k = n.get('/K'); ks = list(k) if isinstance(k, pikepdf.Array) else [k]
                out.append((str(n.Lang), [x if isinstance(x, int) else f'el:{str(x.S).lstrip("/")}' if '/S' in x else int(x.MCID) for x in ks]))
            k = n.get('/K')
            for x in (list(k) if isinstance(k, pikepdf.Array) else [k]): walk(x, d + 1)
        walk(pdf.Root.StructTreeRoot)
    return out


KY = [('The Ky', 'own'), ('ô', 'child'), ('nggi palace.', 'own')]
SEGS = [[0, 4, 5], [1, 0, 0], [2, 0, 3]]


def test_the_finder_places_the_word_instead_of_listing_it_not_tagged(tmp_path):
    src = build(str(tmp_path / 's.pdf'), KY)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf, grow=True)
    ps = [p for p in c['places'] if p['form'] == 'Kyônggi']
    assert len(ps) == 1 and ps[0]['segments'] == SEGS and ps[0]['breaks'] == ['inside', 'inside'] and not c['unplaced']


def test_one_span_over_the_word_with_the_child_inside(tmp_path):
    src = build(str(tmp_path / 's.pdf'), KY)
    out, log, v = apply_verify(tmp_path, src, wo(SEGS))
    lp = log['language_parts']
    assert lp['phrases'] == 1 and not lp['refused'], lp
    sp = lang_spans(out)
    assert len(sp) == 1 and sp[0][0] == 'ko-Latn' and sp[0][1][1] == 'el:Span' and len(sp[0][1]) == 3, sp
    with pikepdf.open(out) as pdf:
        p = pdf.Root.StructTreeRoot.K[0].K[0]
        span = next(k for k in p.K if isinstance(k, pikepdf.Dictionary) and '/Lang' in k)
        child = span.K[1]
        assert child.P.objgen == span.objgen and list(child.K) == [1]           # moved in whole, its run its own
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [], v['language']
    assert v['index']['dangling'] == 0 and v['tree']['parenttree_mismatched'] == 0


def test_two_children_in_one_word(tmp_path):
    src = build(str(tmp_path / 's.pdf'), [('Ry', 'own'), ('ò', 'child'), ('z', 'own'), ('ò', 'child'), (' here.', 'own')])
    out, log, v = apply_verify(tmp_path, src, wo([[0, 0, 1], [1, 0, 0], [2, 0, 0], [3, 0, 0]], form='Ryòzò'))
    assert log['language_parts']['phrases'] == 1 and not log['language_parts']['refused']
    assert [k for k in lang_spans(out)[0][1]] == [0, 'el:Span', 2, 'el:Span'] and v['language']['all_match']


def test_a_child_at_the_start_of_the_word(tmp_path):
    src = build(str(tmp_path / 's.pdf'), [('Ô', 'child'), ('saka is here.', 'own')])
    out, log, v = apply_verify(tmp_path, src, wo([[0, 0, 0], [1, 0, 3]], form='Ôsaka', lang='ja-Latn'))
    assert log['language_parts']['phrases'] == 1 and lang_spans(out)[0][1][0] == 'el:Span' and v['language']['all_match']


def refused(tmp_path, **kw):
    src = build(str(tmp_path / 's.pdf'), KY, **kw)
    out, log, v = apply_verify(tmp_path, src, wo(SEGS))
    return log['language_parts'], lang_spans(out)


def test_refused_shapes_stay_untagged(tmp_path):
    cases = {
        'actualtext on the child tag': dict(child_extra={'ActualText': pikepdf.String('o')}),
        'alt text on the child tag': dict(child_extra={'Alt': pikepdf.String('o')}),
        'spoken text in its marks': dict(child_marks=' /ActualText (o)'),
        'a Link, not a Span': dict(child_type='Link'),
        'a table header names its ID': dict(headers_id='id1'),
    }
    for name, kw in cases.items():
        d = tmp_path / name.replace(' ', '_'); d.mkdir()
        lp, sp = refused(d, **kw)
        assert sp == [] and lp.get('phrases_refused') == 1 and not lp.get('fallback'), (name, lp.get('refused'))


def test_a_child_holding_more_than_letters_is_refused(tmp_path):
    src = build(str(tmp_path / 's.pdf'), [('The Ky', 'own'), ('ô1', 'child'), ('nggi palace.', 'own')])
    out, log, v = apply_verify(tmp_path, src, wo([[0, 4, 5], [1, 0, 1], [2, 0, 3]]))
    assert lang_spans(out) == [] and 'the child tag holds more than letters' in log['language_parts']['refused']


def test_a_lang_in_the_childs_marks_is_removed_while_its_word_is_tagged(tmp_path):
    """translation's 13 words: the child's run carries /Lang (en-US) in its marks; it goes with the phrase's own marks edits,
    so verify finds no marks naming another language under the word's Span."""
    src = build(str(tmp_path / 's.pdf'), KY, child_marks=' /Lang (en-US)')
    out, log, v = apply_verify(tmp_path, src, wo(SEGS))
    assert log['language_parts']['phrases'] == 1 and v['language']['all_match'], v['language']
    with pikepdf.open(out) as pdf:
        marks = {int(x.operands[1].MCID): x.operands[1] for x in pikepdf.parse_content_stream(pdf.pages[0])
                 if str(x.operator) == 'BDC' and isinstance(x.operands[1], pikepdf.Dictionary) and '/MCID' in x.operands[1]}
        assert '/Lang' not in marks[1]


def test_a_late_refusal_leaves_the_child_where_it_was(tmp_path):
    """The Span (and the child's move) is written only after the page passes its checks: a forced render failure refuses
    the place, and the child is still the P's kid, with its own /P (no undo is needed)."""
    src = build(str(tmp_path / 's.pdf'), KY)
    out, log, v = apply_verify(tmp_path, src, wo(SEGS), env={'APPLY_TEST_PIXEL_FAIL_RUN': '1:0'})
    assert lang_spans(out) == [] and log['language_parts']['refused'] == {'the page would look different': 1}
    with pikepdf.open(out) as pdf:
        p = pdf.Root.StructTreeRoot.K[0].K[0]
        child = next(k for k in p.K if isinstance(k, pikepdf.Dictionary))
        assert child.P.objgen == p.objgen and str(child.S) == '/Span'



def test_a_phrase_inside_a_tag_the_role_map_fix_retypes_still_matches(tmp_path):
    """clans' Sub (a standard tag remapped to Span, veraPDF 7.1-7): fix_standard_remaps retypes it to Span after the
    language write; the phrase's record follows, so verify still finds its Span where the place was."""
    src = build(str(tmp_path / 's.pdf'), [('The Ky', 'own'), ('ônggi palace.', 'own')], p_type='Sub', rolemap={'/Sub': '/Span'})
    out, log, v = apply_verify(tmp_path, src, wo([[0, 4, 5], [1, 0, 4]]))
    assert any('standard tag Sub was remapped' in k for k in log['applied'])
    assert log['language_parts']['phrases'] == 1 and v['language']['all_match'], v['language']


def test_a_work_order_mapping_the_childs_style_to_p_refuses_the_place(tmp_path):
    """Review 06 S2: the rule reads the role map op_rolemap left, not the source's. clans' ParagraphSpan maps to Span, so
    its child is one slot; a work order mapping ParagraphSpan to P makes it a block, and the place is refused."""
    kw = dict(child_type='ParagraphSpan', rolemap={'/ParagraphSpan': '/Span'})
    src = build(str(tmp_path / 's.pdf'), KY, **kw)
    out, log, v = apply_verify(tmp_path, src, wo(SEGS))
    assert log['language_parts']['phrases'] == 1 and v['language']['all_match']          # as the source maps it: placed
    (tmp_path / 'b').mkdir()
    out, log, v = apply_verify(tmp_path / 'b', src, dict(wo(SEGS), rolemap={'ParagraphSpan': 'P'}))
    assert log['rolemap'] == {'ParagraphSpan': {'to': 'P', 'how': 'RoleMap', 'elements': 1}}
    assert not log['language_parts'].get('phrases') and log['language_parts']['refused'] and lang_spans(out) == [], log['language_parts']



def test_a_word_made_only_of_two_adjacent_child_tags(tmp_path):
    """Review 06 S3: no run of the paragraph's own in the word; the Span holds the two children only, and verify's branch
    for a place with no own runs finds each where the place had it."""
    src = build(str(tmp_path / 's.pdf'), [('The ', 'own'), ('Ky', 'child'), ('ô', 'child'), (' palace.', 'own')])
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf, grow=True)
    ps = [p for p in c['places'] if p['form'] == 'Kyô']
    assert len(ps) == 1 and ps[0]['segments'] == [[1, 0, 1], [2, 0, 0]] and not c['unplaced'], c['places']
    out, log, v = apply_verify(tmp_path, src, wo([[1, 0, 1], [2, 0, 0]], form='Kyô'))
    assert log['language_parts']['phrases'] == 1 and not log['language_parts']['refused'], log['language_parts']
    assert lang_spans(out) == [('ko-Latn', ['el:Span', 'el:Span'])]
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [], v['language']
    assert v['index']['dangling'] == 0 and v['tree']['parenttree_mismatched'] == 0
