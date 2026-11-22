"""Language tags on text drawn inside a form XObject (#165, proposal 08, review 09): made-up words on tiny tagged PDFs whose
text sits in one form, as an auto-tagged OCR layer's does (tests/langpdf.build_in_form), through apply.py and verify.py.
veraPDF off; the tag-tree check mode on (conftest), so a form key in the page index stops the test (review 09, R3).

A run in a form keeps its name (page, MCID); apply.py finds the stream that draws it, edits that stream, writes the form's
own index entries, and refuses whatever its conditions don't cover, with the reason, never half-written.
"""
import os, sys, json, subprocess
import pikepdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, langcands  # noqa: F401,E402


def run(script, *args, env=None):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off', **(env or {})),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stderr[-2000:]
    return r


def wo_of(forms_rows):
    """[(form, lang, [rows])], a row [page, mcid, first, last] or [page, segments] -> language_parts version 2 or 3."""
    forms, rows = [], []
    for i, (form, lang, rs) in enumerate(forms_rows):
        forms.append({'key': f'unknown|{form}', 'form': form, 'group': 'unknown', 'class': ['unknown'], 'lang': lang,
                      'confidence': 'high', 'why': 'language', 'tag': True, 'places': len(rs)})
        rows += [list(r) + [i] if len(r) == 4 else [r[0], r[1], i] for r in rs]
    return {'language_parts': {'version': 3 if any(len(r) == 3 for r in rows) else 2, 'forms': forms, 'parts': rows}}


def apply_verify(tmp_path, lines, wo, env=None, name='src.pdf', **build):
    src = langpdf.build_in_form(str(tmp_path / name), lines, **build)
    p = tmp_path / ('wo-' + name + '.json'); p.write_text(json.dumps(wo))
    out = str(tmp_path / ('out-' + name))
    run('apply.py', src, p, out, env=env); run('verify.py', src, out)
    return src, out, json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))


def form_marks(path, name='/Fm0'):
    with pikepdf.open(path) as pdf:
        f = pdf.pages[0].Resources.XObject[name]
        return {int(x.operands[1].MCID): {str(k): str(v) for k, v in x.operands[1].items()} for x in pikepdf.parse_content_stream(f)
                if str(x.operator) == 'BDC' and isinstance(x.operands[1], pikepdf.Dictionary) and '/MCID' in x.operands[1]}


def form_bytes(path, name='/Fm0'):
    with pikepdf.open(path) as pdf: return bytes(pdf.pages[0].Resources.XObject[name].read_bytes())


def spans(path):
    """[(lang, [MCIDs], parent type, [kid kinds: 'stm' | 'page'])] for every Span with a /Lang."""
    pdf = pikepdf.open(path); out = []                # kept open while walking
    def walk(n, d=0):
        if d > 40 or not isinstance(n, pikepdf.Dictionary): return
        if str(n.get('/S', '')) == '/Span' and '/Lang' in n:
            k = n.get('/K'); ks = list(k) if isinstance(k, pikepdf.Array) else [k]
            out.append((str(n.Lang), [int(x) if isinstance(x, int) else int(x.MCID) for x in ks], str(n.P.get('/S')).lstrip('/'),
                        ['stm' if isinstance(x, pikepdf.Dictionary) and '/Stm' in x else 'page' for x in ks]))
        k = n.get('/K')
        for x in (list(k) if isinstance(k, pikepdf.Array) else [k]): walk(x, d + 1)
    walk(pdf.Root.StructTreeRoot)
    return out


def form_index(path, name='/Fm0'):
    """The form's own ParentTree array, as the /S of each entry (None for an empty slot)."""
    with pikepdf.open(path) as pdf:
        f = pdf.pages[0].Resources.XObject[name]
        nums = pdf.Root.StructTreeRoot.ParentTree.Nums
        arr = next(nums[j + 1] for j in range(0, len(nums), 2) if int(nums[j]) == int(f.StructParents))
        return [None if e is None else str(e.S).lstrip('/') for e in arr]


def clean(v):
    """verify's checks on this file: no page draws or reads differently, no index entry dangles, and the tag tree's index
    has no entry missing or naming another element, the forms' arrays included (verify.py's tree section)."""
    t = v['tree']
    return (v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0
            and t['parenttree_missing'] == 0 and t['parenttree_mismatched'] == 0 and t['content_mcids_not_in_tree'] == 0)


THREE = [[{'text': 'The '}, {'text': 'velunka '}, {'text': 'here.'}]]
WHOLE = [('velunka', 'haw', [[1, 1, 0, 6]])]
OCR = [[{'text': 'The '}, {'text': 'velunka '}, {'text': 'toramio '}, {'text': 'pasquet '}, {'text': 'here.'}]]
PHRASE = [('velunka toramio pasquet', 'haw', [[1, [[1, 0, 7], [2, 0, 7], [3, 0, 6]]]])]
LONG = [[{'text': 'These words are all made up: velunk'}, {'text': 'a'}, {'text': ' and more words come here today.'}]]
INRUN = [[{'text': 'These words are all made up: velunka and more.'}, {'text': 'Plain English here.'}]]
INRUN_WO = [('velunka', 'haw', [[1, 0, 29, 35]])]


# ---------------------------------------------------------------- proposal 08 §5
def test_1_a_whole_run_in_a_form_is_tagged_and_its_marks_lose_their_lang(tmp_path):
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE))
    assert spans(out) == [('haw', [1], 'P', ['stm'])], log['language_parts']
    m = form_marks(out)
    assert '/Lang' not in m[1] and m[0]['/Lang'] == 'en-US' and m[2]['/Lang'] == 'en-US'
    assert form_index(out)[1] == 'Span'                        # the form's own index names the Span (review 09 §3.4, case 3)
    with pikepdf.open(out) as P_: assert '/StructParents' not in P_.pages[0].obj  # the page has no index array of its own, and gets none
    assert v['language']['all_match'] and v['language']['spans_written'] == 1 and clean(v), v['language']


def test_2_a_place_inside_a_run_is_split_inside_the_form(tmp_path):
    src, out, log, v = apply_verify(tmp_path, INRUN, wo_of(INRUN_WO))
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'haw' and sp[0][3] == ['stm'] and sp[0][1][0] >= 2, sp     # a new MCID, past the form's own
    assert form_index(out)[sp[0][1][0]] == 'Span'
    m = form_marks(out)
    assert sp[0][1][0] in m and '/Lang' not in m[sp[0][1][0]] and len(m) == 4                       # before, place, after; and run 1
    assert v['language']['all_match'] and clean(v), v['language']


def test_3_a_phrase_across_three_runs_in_a_form_is_one_span(tmp_path):
    src, out, log, v = apply_verify(tmp_path, OCR, wo_of(PHRASE))
    assert log['language_parts']['phrases'] == 1 and not log['language_parts']['refused'], log['language_parts']
    assert spans(out) == [('haw', [1, 2, 3], 'P', ['stm', 'stm', 'stm'])]
    assert form_index(out)[1:4] == ['Span', 'Span', 'Span']
    m = form_marks(out)
    assert all('/Lang' not in m[k] for k in (1, 2, 3)) and m[0]['/Lang'] == 'en-US'
    assert v['language']['all_match'] and clean(v), v['language']


def test_4_a_phrase_refused_by_the_pixel_check_or_a_lost_entry_leaves_the_form_as_it_was(tmp_path):
    src = langpdf.build_in_form(str(tmp_path / 'f.pdf'), LONG)
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf)
    segs = next(p for p in c['places'] if p['form'] == 'velunka')['segments']
    src, out, log, v = apply_verify(tmp_path, LONG, wo_of([('velunka', 'haw', [[1, segs]])]), env={'APPLY_TEST_PIXEL_FAIL_RUN': '1:0'}, name='p.pdf')
    assert spans(out) == [] and log['language_parts']['refused'] == {'the page would look different': 1}, log['language_parts']
    assert form_bytes(out) == form_bytes(src) and clean(v)
    src, out, log, v = apply_verify(tmp_path, OCR, wo_of(PHRASE), env={'APPLY_TEST_LOSE_ENTRY': '1'}, name='l.pdf')
    assert spans(out) == [] and all(x['/Lang'] == 'en-US' for x in form_marks(out).values())
    assert v['language']['all_match'] and clean(v)


def test_5_a_form_drawn_twice_on_a_page_or_on_two_pages_is_refused(tmp_path):
    for name, kw in (('twice.pdf', {'draws': 2}), ('two.pdf', {'second_page': True})):
        src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), name=name, **kw)
        assert spans(out) == [] and log['language_parts']['refused'] == {'the text is drawn inside a form used in more than one place': 1}, (name, log['language_parts'])
        assert form_bytes(out) == form_bytes(src) and clean(v)


def test_6_a_number_two_forms_draw_on_the_page_is_refused(tmp_path):
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), two_forms_share=1)
    assert spans(out) == [] and log['language_parts']['refused'] == {"the text's number is used twice on the page": 1}, log['language_parts']
    assert form_bytes(out) == form_bytes(src) and clean(v)


def test_7_spoken_text_in_a_form_runs_marks_is_refused(tmp_path):
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), at_marks=(1,))
    assert spans(out) == [] and log['language_parts']['refused'] == {'the text has its own spoken text': 1}, log['language_parts']
    assert form_bytes(out) == form_bytes(src)


def test_8_a_persons_removal_of_a_lang_in_a_forms_marks_removes_it_from_the_form(tmp_path):
    lines = [[{'text': 'The '}, {'text': 'oui ', 'lang': 'fr'}, {'text': 'here.'}]]
    lp = {'version': 2, 'forms': [{'key': 'existing|oui|fr', 'form': 'oui', 'group': 'existing', 'class': ['existing'], 'current': 'fr',
                                   'lang': None, 'tag': False, 'decided': 'remove', 'places': 1}], 'parts': [[1, 1, 0, 2, 0]]}
    src, out, log, v = apply_verify(tmp_path, lines, {'language_parts': lp})
    m = form_marks(out)
    assert '/Lang' not in m[1] and m[0]['/Lang'] == 'en-US' and log['language_parts'].get('existing_removed') == 1, log['language_parts']
    assert clean(v)


def test_10_page_runs_and_form_runs_on_one_page_are_both_tagged(tmp_path):
    wo = wo_of([('velunka', 'haw', [[1, 1, 0, 6], [1, 3, 5, 11]])])
    src, out, log, v = apply_verify(tmp_path, THREE, wo, page_lines=['Also velunka here.'])
    sp = sorted(spans(out))
    assert len(sp) == 2 and sp[0][1] == [1] and sp[0][3] == ['stm'] and sp[1][3] == ['page'], sp
    assert sp[1][1][0] not in (0, 1, 2, 3)                     # the page split's new MCID avoids the form's numbers too
    assert v['language']['all_match'] and v['language']['spans_written'] == 2 and clean(v), v['language']


# ---------------------------------------------------------------- review 09 §3.4 and decision 5
def test_a_run_the_tree_names_both_as_page_text_and_in_the_form_is_tagged_after_the_strays_repair(tmp_path):
    """Decision 5 (condition 6), since #168: an integer page kid and an /MCR … /Stm both name form run 1. The page kid
    points at no text the page draws, and the run is held by its /Stm kid, so apply.py's strays repair (lib/strays.py)
    removes it before the language pass; the run is then tagged through its /Stm path. (run_at still refuses a run named
    twice, for a page kid the repair keeps.)"""
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), page_refs=(1,))
    assert log['strays']['removed']['page_kids'] == 1 and log['strays']['removed']['slots_cleared'] == 1
    assert [x[3] for x in spans(out)] == [['stm']] and not log['language_parts'].get('refused'), log['language_parts']
    assert v['language']['all_match'] and v['tree']['kids_not_drawn'] == 0 and v['tree']['runs_named_twice'] == 0


def test_a_run_named_only_by_a_page_kid_is_refused_as_before(tmp_path):
    """Sample N's PDF 87: the tree names form run 1 only by a page-level kid; the other runs have their /Stm path. The page
    path's own check refuses it (drawn_here), and nothing in the form changes."""
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), only_page_refs=(1,))
    assert spans(out) == [] and log['language_parts']['refused'] == {'this text is drawn inside a form XObject, not in the page': 1}, log['language_parts']
    assert form_bytes(out) == form_bytes(src)


def test_a_form_drawn_inside_marked_content_on_the_page_is_refused(tmp_path):
    # inside /Artifact, pdfplumber gives the form's characters no MCID, so the place is refused first by the character
    # check; inside marked content with an MCID, by condition 5. Either way nothing is written.
    for inside, why in (('artifact', 'the characters do not line up with the text'), ('mcid', 'the form is drawn inside marked content on the page')):
        src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), do_inside=inside, name=inside + '.pdf')
        assert spans(out) == [] and log['language_parts']['refused'] == {why: 1}, (inside, log['language_parts'])
        assert form_bytes(out) == form_bytes(src)


def test_a_form_with_no_tag_entry_is_refused(tmp_path):
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), no_structparents=True)
    assert spans(out) == [] and log['language_parts']['refused'] == {'the form has no tag entry': 1}, log['language_parts']


def test_a_failed_page_plan_on_a_form_page_keeps_the_whole_run_tag_and_refuses_the_split(tmp_path):
    """review 09 §2 on both streams: the whole run's Span holds (its marks in the form lose /Lang), the split is refused."""
    lines = [[{'text': 'velunka '}, {'text': 'These words are all made up: toramio and more.'}]]
    wo = wo_of([('velunka', 'haw', [[1, 0, 0, 6]]), ('toramio', 'haw', [[1, 1, 29, 35]])])
    src, out, log, v = apply_verify(tmp_path, lines, wo, env={'APPLY_FAIL_LANG_PAGE': '1'})
    lp = log['language_parts']
    assert [(x['mcid'], x['whole']) for x in lp['spans']] == [(0, True)] and lp['refused'] == {'the page could not be planned': 1}, lp
    m = form_marks(out)
    assert '/Lang' not in m[0] and m[1]['/Lang'] == 'en-US' and len(m) == 2
    assert v['language']['all_match'] and clean(v)


def test_a_form_with_no_resources_uses_the_pages(tmp_path):
    src, out, log, v = apply_verify(tmp_path, INRUN, wo_of(INRUN_WO), form_resources=False)
    assert len(spans(out)) == 1 and not log['language_parts']['refused'], log['language_parts']
    assert v['language']['all_match'] and clean(v)


def test_the_local_rule_tags_a_kana_run_in_a_form(tmp_path):
    """The local rule (kana -> ja, no AI) now reaches text in forms (review 09 §3.3), on any form-text book."""
    lines = [[{'text': 'The '}, {'text': 'と', 'font': 'F2'}, {'text': ' here.'}]]
    src, out, log, v = apply_verify(tmp_path, lines, {})
    assert spans(out) == [('ja', [1], 'P', ['stm'])], log['language_parts']
    assert '/Lang' not in form_marks(out)[1]
    assert v['language']['all_match'] and clean(v)


def test_a_split_whose_form_text_reads_differently_is_refused(tmp_path):
    """review 09, R7: form text is often invisible, so a page whose form was edited is also read before and after; a
    difference (here through a test hook) is treated as a pixel difference."""
    src, out, log, v = apply_verify(tmp_path, INRUN, wo_of(INRUN_WO), env={'APPLY_TEST_TEXT_FAIL_RUN': '1:0'})
    assert spans(out) == [] and log['language_parts']['refused'] == {'the page would read differently': 1}, log['language_parts']   # its own reason (review 11 §2)
    assert form_bytes(out) == form_bytes(src) and clean(v)


def test_9_verify_catches_a_run_moved_out_of_a_phrase_span_in_a_form(tmp_path):
    src, out, log, v = apply_verify(tmp_path, OCR, wo_of(PHRASE))
    assert v['language']['all_match']
    with pikepdf.open(out, allow_overwriting_input=True) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']
        nums = pdf.Root.StructTreeRoot.ParentTree.Nums
        arr = next(nums[j + 1] for j in range(0, len(nums), 2) if int(nums[j]) == int(f.StructParents))
        sp = arr[3]; par = sp.P
        k3 = sp.K[2]; sp.K = pikepdf.Array([sp.K[0], sp.K[1]]); par.K.append(k3)
        arr[3] = par                                           # run 3 now sits under the P that carries no language
        pdf.save(out)
    run('verify.py', src, out)
    lg = json.load(open(out + '.verify.json'))['language']
    assert not lg['all_match'] and lg['mismatch_examples'][0]['why'] in ('its runs sit under different tags', 'its tag holds other runs')


def test_verify_reads_a_lang_left_in_a_form_runs_marks(tmp_path):
    """verify reads the marks inside the form (#165): a Span over a form run whose marks still say another language fails."""
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE))
    with pikepdf.open(out, allow_overwriting_input=True) as pdf:
        f = pdf.pages[0].Resources.XObject['/Fm0']
        ins = list(pikepdf.parse_content_stream(f))
        ins = [pikepdf.ContentStreamInstruction([x.operands[0], pikepdf.Dictionary(MCID=1, Lang=pikepdf.String('fr'))], x.operator)
               if str(x.operator) == 'BDC' and int(x.operands[1].get('/MCID', -1)) == 1 else x for x in ins]
        f.write(pikepdf.unparse_content_stream(ins)); pdf.save(out)
    run('verify.py', src, out)
    lg = json.load(open(out + '.verify.json'))['language']
    assert not lg['all_match'] and lg['mismatch_examples'][0]['why'] == 'its marked content says fr', lg


# ---------------------------------------------------------------- the finder (proposal 08 §3.4–3.5)
def test_the_finder_lists_a_publishers_lang_in_a_form_and_counts_spoken_text_there(tmp_path):
    """A /Lang in a single-use form's marks is listed as an existing tag (for a person to keep or remove); /ActualText in a
    form's marks is seen by the finder's structure reader, so a word joined across runs there is counted not tagged
    ("actualtext"), as on page text. (A single run under spoken text is refused by the executor: test 7.)"""
    lines = [[{'text': 'The '}, {'text': 'oui ', 'lang': 'fr'}, {'text': 'velunka '}, {'text': 'toramio '}, {'text': 'here.'}]]
    src = langpdf.build_in_form(str(tmp_path / 'f.pdf'), lines, at_marks=(3,))
    with pikepdf.open(src) as pdf:
        c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf)
        ex = langcands.existing(pdf, plpages.Pages(src), 'en')        # the language step adds these (name_languages.py)
    assert [(p['mcid'], p['current']) for p in ex] == [(1, 'fr')], ex
    assert any(p['form'] == 'velunka' for p in c['places'])
    from lib import langjoin
    with pikepdf.open(src) as pdf:
        mk = langjoin.Structure(pdf).marks(1)
    assert mk[3] == (True, False) and mk[2] == (False, False), mk


def test_the_finder_leaves_a_shared_forms_tags_alone(tmp_path):
    """A form drawn in several places: its /Lang is neither listed nor removed (apply.py never tags its runs)."""
    lines = [[{'text': 'The '}, {'text': 'oui ', 'lang': 'fr'}, {'text': 'here.'}]]
    src = langpdf.build_in_form(str(tmp_path / 's.pdf'), lines, draws=2)
    with pikepdf.open(src) as pdf: assert langcands.existing(pdf, plpages.Pages(src), 'en') == []



# ---------------------------------------------------------------- review 11
def test_a_tag_in_a_form_keeps_the_artifact_marks_fix_paths_put_there(tmp_path):
    """§3: fix_paths marks the form's untagged rule as an artifact after op_language first read the form; the late pass
    reads the form again, so the tag and the /Artifact are both in it, and verify finds no untagged path."""
    src, out, log, v = apply_verify(tmp_path, THREE, wo_of(WHOLE), form_rules=1)
    assert spans(out) == [('haw', [1], 'P', ['stm'])], log['language_parts']
    assert b'/Artifact' in form_bytes(out) and (log.get('fix_paths') or {}).get('artifacted', 1) >= 1
    assert v['untagged_paths'] == 0 and v['language']['all_match'] and clean(v), (v['untagged_paths'], v['language'])


def test_a_removal_on_text_no_tree_reference_names_is_refused(tmp_path):
    """L2: a person's "Remove" of a /Lang in a form run that no tree reference names, and that the page doesn't draw, is
    refused (not counted as removed while the form keeps its /Lang)."""
    lines = [[{'text': 'The '}, {'text': 'oui ', 'lang': 'fr'}, {'text': 'here.'}]]
    lp = {'version': 2, 'forms': [{'key': 'existing|oui|fr', 'form': 'oui', 'group': 'existing', 'class': ['existing'], 'current': 'fr',
                                   'lang': None, 'tag': False, 'decided': 'remove', 'places': 1}], 'parts': [[1, 1, 0, 2, 0]]}
    src, out, log, v = apply_verify(tmp_path, lines, {'language_parts': lp}, no_ref=(1,))
    lp_ = log['language_parts']
    assert lp_['refused'] == {'this text is not in the tag tree': 1} and not lp_.get('existing_removed'), lp_
    assert form_marks(out)[1]['/Lang'] == 'fr'


def test_the_single_use_form_list_belongs_to_the_pdf_it_was_asked_for(tmp_path):
    """L3: the finder's cache of single-use forms answers only for the PDF it was made for."""
    from lib import langjoin
    a = langpdf.build_in_form(str(tmp_path / 'a.pdf'), THREE)
    b = langpdf.build_in_form(str(tmp_path / 'b.pdf'), THREE, draws=2)       # its form is shared: no single-use form
    with pikepdf.open(a) as pa, pikepdf.open(b) as pb:
        assert len(langjoin.single_use_forms(pa).get(1, [])) == 1
        assert langjoin.single_use_forms(pb) == {}
        assert len(langjoin.single_use_forms(pa).get(1, [])) == 1
        # the cache holds the PDF object itself, so a later PDF given a closed one's id() is never answered from it
        # (review 15: with both PDFs open their ids differ, so the lines above passed on the id-keyed cache too)
        assert langjoin._SINGLE.get('pdf') is pa
