"""test_handedit.py: a PDF edited by hand and brought back (#62): lib/handedit.py, handedit.py and decide.py --no-model.

    python -m pytest tests/test_handedit.py -q

Tiny hand-made PDFs with two figures, each one image; the "edited" file swaps one image for another and is saved with its
objects in a different order, as an Acrobat save would. No book content; nothing is sent anywhere; veraPDF is off.
"""
import os, sys, json, shutil, hashlib, subprocess
import pikepdf
from lib import handedit, workorder_check

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def figures_pdf(path, colors=(b'\x00\x00\xff', b'\xff\x00\x00'), alts=('A blue square', 'A red square'), shuffle=False,
                text='(Two figures.) Tj', untag_first=False):
    """One page, a paragraph and two figures; figure i draws a 2x2 image of colors[i]. shuffle: the objects are made in
    another order, so their numbers differ from the first file's. text: how the paragraph is drawn. untag_first: the first
    image is drawn with no marked content and its Figure is gone, as Acrobat's Edit PDF leaves a page it rewrote."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
                              Encoding=pikepdf.Name.WinAnsiEncoding)
    if shuffle:
        for _ in range(5): pdf.make_indirect(pikepdf.Dictionary(Filler=True))
    ims = {f'/Im{i + 1}': pikepdf.Stream(pdf, c * 4, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=2, Height=2,
                                        ColorSpace=pikepdf.Name.DeviceRGB, BitsPerComponent=8) for i, c in enumerate(colors)}
    content = (f'/P <</MCID 0>> BDC BT /F1 11 Tf 72 520 Td {text} ET EMC\n'
               + ('q 100 0 0 100 72 300 cm /Im1 Do Q\n' if untag_first else '/Figure <</MCID 1>> BDC q 100 0 0 100 72 300 cm /Im1 Do Q EMC\n') +
               '/Figure <</MCID 2>> BDC q 100 0 0 100 72 100 cm /Im2 Do Q EMC\n')
    page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], StructParents=0,
                              Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(ims)),
                              Contents=pikepdf.Stream(pdf, content.encode('latin-1')))
    pdf.pages.append(pikepdf.Page(page)); pg = pdf.pages[0].obj
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    p = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg, K=0))
    figs = [pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=doc, Pg=pg, K=i + 1,
                                                 Alt=pikepdf.String(a))) for i, a in enumerate(alts) if not (untag_first and i == 0)]
    doc.K = pikepdf.Array([p] + figs); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=[0, pikepdf.Array([p] + ([None] if untag_first else []) + figs)]))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path)
    return str(path)

def edited_pair(tmp_path):
    base = figures_pdf(tmp_path / 'base.pdf')
    edited = figures_pdf(tmp_path / 'edited.pdf', colors=(b'\x00\x00\xff', b'\x00\xff\x00'), shuffle=True)   # the red one replaced
    return base, edited

# ---- lib/handedit.py
def test_a_replaced_image_marks_its_figure_and_only_that_one(tmp_path):
    base, edited = edited_pair(tmp_path)
    ch = handedit.changed(base, edited)
    assert ch['pages'] == [1, 1]
    assert [(f['page'], f['alt']) for f in ch['figures']] == [(1, 'A red square')]
    assert len(ch['new_images']) == 1 and len(ch['removed_images']) == 1 and ch['outside_figures'] == []

def test_the_same_file_saved_again_has_no_changes(tmp_path):
    base = figures_pdf(tmp_path / 'base.pdf')
    again = figures_pdf(tmp_path / 'again.pdf', shuffle=True)      # renumbered objects, same images
    ch = handedit.changed(base, again)
    assert ch['figures'] == [] and ch['new_images'] == [] and ch['removed_images'] == []

def test_stale_alt_is_removed_in_a_copy_and_the_edited_file_is_untouched(tmp_path):
    base, edited = edited_pair(tmp_path)
    before = sha(edited); ch = handedit.changed(base, edited)
    out = str(tmp_path / 'input.pdf')
    assert handedit.strip_stale_alt(edited, out, [f['obj'] for f in ch['figures']]) == []
    assert sha(edited) == before
    alts = sorted((f['alt'] or '') for f in handedit.figures(out))
    assert alts == ['', 'A blue square']                           # the unchanged figure keeps its alt

def test_a_figure_whose_tag_was_dropped_is_listed_as_lost(tmp_path):
    base = figures_pdf(tmp_path / 'base.pdf')
    edited = figures_pdf(tmp_path / 'edited.pdf', untag_first=True, shuffle=True)   # same images; the blue one's tag gone
    ch = handedit.changed(base, edited)
    assert ch['figures_lost'] == [{'page': 1, 'alt': 'A blue square'}] and ch['figures'] == [] and ch['new_images'] == []

def test_a_replaced_image_is_not_also_counted_as_lost(tmp_path):
    assert handedit.changed(*edited_pair(tmp_path))['figures_lost'] == []

def test_dropped_spaces_read_the_same_and_a_changed_word_does_not(tmp_path):
    base = figures_pdf(tmp_path / 'base.pdf')
    spaces = figures_pdf(tmp_path / 'spaces.pdf', text='[(Two) -400 (figures.)] TJ')     # no space character, a gap instead
    word = figures_pdf(tmp_path / 'word.pdf', text='(Two figurez.) Tj')
    assert handedit.changed(base, spaces)['text_pages'] == [{'page': 1, 'chars_before': 12, 'chars_after': 11, 'heard_same': True}]
    assert [x['heard_same'] for x in handedit.changed(base, word)['text_pages']] == [False]
    assert handedit.changed(base, figures_pdf(tmp_path / 'again.pdf', shuffle=True))['text_pages'] == []

def test_a_figure_that_cannot_be_found_is_listed_not_guessed(tmp_path):
    base, edited = edited_pair(tmp_path)
    assert handedit.strip_stale_alt(edited, str(tmp_path / 'input.pdf'), ['9999 0']) == ['9999 0']

# ---- handedit.py, run_api.sh DECIDE=none, report.py: the whole loop at no cost (veraPDF off, no AI call)
def env(**kw):
    e = dict(os.environ, VERAPDF='off', PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''), **kw)
    for k in ('INTAKE_REUSE', 'INTAKE', 'REVIEW', 'DECIDE', 'REPLY', 'ESTIMATE', 'RUN_DIR', 'OUT'): e.pop(k, None) if k not in kw else None
    return e

def sh(args, **kw):
    return subprocess.run(args, cwd=PIPE, env=env(**kw), capture_output=True, text=True, timeout=300)

def parent_run(tmp_path):
    """A finished run of the two-figure book (no AI call: an empty work order applied), as the run a person edits."""
    src = figures_pdf(tmp_path / 'book.pdf')
    r = sh(['bash', 'run_api.sh', src, 'book', 'parent'], RUNS_DIR=str(tmp_path / 'runs'), DECIDE='none')
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'no credit used' in r.stdout                                  # nothing looked up at OpenRouter either
    return src, str(tmp_path / 'runs' / 'book' / 'parent')

def swap_image(src, out, word=False):
    """The red image replaced by a green one; word: also "figures." changed to "figurez." in the page's text."""
    pdf = pikepdf.open(src); pdf.pages[0].Resources.XObject['/Im2'].write(b'\x00\xff\x00' * 4)
    if word:
        c = pdf.pages[0].obj.Contents; assert b'figures.' in c.read_bytes(); c.write(c.read_bytes().replace(b'figures.', b'figurez.'))
    pdf.save(out); return str(out)

def test_no_model_writes_an_empty_order_the_check_accepts(tmp_path):
    src, P = parent_run(tmp_path)
    rec = json.load(open(os.path.join(P, 'record.json'), encoding='utf-8'))
    assert rec['run']['no_model'] and rec['cost_total_usd'] == 0 and rec['validation_dropped'] == []
    assert rec['ai_call']['no_model'] and rec['ai_call']['cost_usd'] == 0
    wo = {k: v for k, v in rec['workorder'].items() if k not in ('source', 'decided_by')}
    assert workorder_check.check(dict(wo), {'source': {'pages': 1}, 'elements': [], 'figures': [], 'styles': []}, set(), set()) == []
    md = open(os.path.join(P, 'review.md'), encoding='utf-8').read()
    assert 'no AI call' in md and 'model not recorded' not in md and 'None' not in md

def test_a_hand_edited_pdf_comes_back_for_review_and_is_recorded(tmp_path):
    src, P = parent_run(tmp_path)
    out = os.path.join(P, json.load(open(os.path.join(P, 'record.json')))['document']['output'])
    keep = {p: sha(p) for p in (src, out)}
    r = sh([sys.executable, 'handedit.py', 'export', P, '--to', str(tmp_path / 'copy.pdf'), '--by', 'Pat'])
    assert r.returncode == 0, r.stderr
    edited = swap_image(tmp_path / 'copy.pdf', tmp_path / 'edited.pdf', word=True); ed_sha = sha(edited)
    r = sh([sys.executable, 'handedit.py', 'import', P, edited, '--by', 'Pat', '--note', 'a better scan of the red square', '--label', 'he1'])
    assert r.returncode == 0, r.stdout + r.stderr
    C = os.path.join(os.path.dirname(P), 'he1')
    assert 'stopped for review' in r.stdout and not os.path.exists(os.path.join(C, 'record.json'))
    items = json.load(open(os.path.join(C, 'review_items.json'), encoding='utf-8'))
    assert items['hand_edit']['alt_removed'] == 1 and items['hand_edit']['figure_pages'] == [1]
    assert items['hand_edit']['text_differs'] == [1] and items['hand_edit']['text_same'] == 0 and items['hand_edit']['lost'] == []
    (t,) = items['hand_edit']['targets']                                  # the Edited by Hand card's "Add Alt Text"
    assert t['kind'] == 'alt' and t['page'] == 1 and t['suggest'] is None and t['why'] == 'new_image' and t['old_alt'] == 'A red square'
    assert items['hand_edit']['earlier'] == {'reviewed_by': None, 'reviewed_on': None, 'items': []}   # the parent's order was empty
    assert next(it for it in items['addable']['alt'] if it['target'] == t['target'])['default'] == ''   # a new image: no suggestion
    from review import core
    digest = json.load(open(os.path.join(C, '_audit', 'digest.json'), encoding='utf-8'))
    gap = next(g for g in core.gaps(json.load(open(os.path.join(C, 'workorder.json'))), digest) if g['id'] == 'figures_without_alt')
    assert len(gap['objs']) == 1                                          # the new image needs alt; the old alt is not reused
    # the person writes the new alt (the hand-edit path of review_workorder.py), then the same command applies it
    p = os.path.join(C, 'workorder.json'); wo = json.load(open(p)); wo['alt'] = [{'obj': gap['objs'][0], 'alt': 'A green square'}]
    json.dump(wo, open(p, 'w'))
    assert sh([sys.executable, 'review_workorder.py', C, '--reviewer', 'Pat', '--note', 'test file']).returncode == 0
    he = json.load(open(os.path.join(C, '_handedit', 'hand_edit.json')))
    r = sh(['bash', 'run_api.sh', os.path.join(C, '_handedit', he['edited']['file']), 'book', 'he1'], RUN_DIR=C, OUT=os.path.basename(out))
    assert r.returncode == 0, r.stdout + r.stderr
    rec = json.load(open(os.path.join(C, 'record.json'), encoding='utf-8'))
    h = rec['hand_edit']
    assert h['by'] == 'Pat' and h['base_sha256'] == keep[out] and h['edited']['sha256'] == ed_sha and h['parent']['run'] == P
    assert rec['document']['sha256'] == ed_sha and rec['document']['pipeline_input']['file'] == '_handedit/input.pdf'
    assert {p: sha(p) for p in keep} == keep and sha(edited) == ed_sha                    # nothing it came from was written to
    assert json.load(open(os.path.join(P, 'hand_edits.json')))['children'][0]['run'] == C
    md = open(os.path.join(C, 'review.md'), encoding='utf-8').read()
    assert 'Edited by Hand' in md and '"A red square" | "A green square"' in md and 'None' not in md
    assert 'CHECK: the text reads differently after the edit on PDF 1' in md and 'lost' not in md
    assert '**Decisions (no AI call):**' in md and 'started from an empty work order (no AI call)' in md and '**AI decisions:**' not in md

def test_import_refuses_an_unchanged_file_a_missing_note_and_an_in_place_edit(tmp_path):
    src, P = parent_run(tmp_path)
    out = os.path.join(P, json.load(open(os.path.join(P, 'record.json')))['document']['output'])
    same = str(tmp_path / 'same.pdf'); open(same, 'wb').write(open(out, 'rb').read())
    r = sh([sys.executable, 'handedit.py', 'import', P, same, '--by', 'Pat', '--note', 'n', '--no-run'])
    assert r.returncode == 1 and 'nothing was edited' in r.stderr
    r = sh([sys.executable, 'handedit.py', 'import', P, same, '--by', 'Pat', '--no-run'])
    assert r.returncode == 1 and '--note' in r.stderr
    os.replace(swap_image(out, tmp_path / 'inplace.pdf'), out)           # the run's own PDF edited in place
    r = sh([sys.executable, 'handedit.py', 'export', P, '--to', str(tmp_path / 'x.pdf')])
    assert r.returncode == 1 and 'changed in place' in r.stderr and not os.path.exists(tmp_path / 'x.pdf')
    assert not os.path.exists(os.path.join(os.path.dirname(P), 'he1'))

def no_model_order(tmp_path, pages):
    """decide.py --no-model in a hand-edit run whose parent's order names contents pages; pages: (before, after)."""
    P = tmp_path / 'parent'; P.mkdir()
    (P / 'record.json').write_text(json.dumps({'workorder': {'sections': {'toc_pages': [2, 3]}, 'links': {'toc_text_fixes': [['\\.{3,}', ' ']]},
                                                             'alt': [{'obj': '9 0', 'alt': 'old'}]}}))
    A, R = tmp_path / 'audit', tmp_path / 'run'; A.mkdir(); (R / '_handedit').mkdir(parents=True)
    (A / 'digest.json').write_text(json.dumps({'source': {'file': 'e.pdf', 'sha256': 'x', 'pages': pages[1]},
                                               'elements': [], 'figures': [], 'styles': []}))
    (R / '_handedit' / 'hand_edit.json').write_text(json.dumps({'parent': {'run': str(P)}, 'pages': list(pages)}))
    r = subprocess.run([sys.executable, 'decide.py', str(A), str(R), '--no-model'], cwd=PIPE, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.load(open(R / 'workorder.json')), json.load(open(R / 'run.json'))

def test_no_model_carries_the_parents_page_decisions_only_when_the_pages_are_the_same(tmp_path):
    wo, run = no_model_order(tmp_path, (5, 5))
    assert wo['sections'] == {'toc_pages': [2, 3]} and wo['links']['toc_text_fixes'] and 'alt' not in wo   # never object-based ones
    assert run['carried_from_parent'] == ['sections', 'links'] and run['usage']['cost_usd'] == 0
    (tmp_path / 'b').mkdir(); wo, run = no_model_order(tmp_path / 'b', (5, 6))
    assert 'sections' not in wo and 'carried_from_parent' not in run

# ---- the review page's Edited by Hand cards: one-click alt text for what the edit touched (review/core.py hand_edit_targets)
def add_item(kind, target, page, before=None, decoration=None):
    return {'id': f'add:{kind}:{target}', 'kind': kind, 'target': target, 'page': page, 'before': before,
            'context': {'decoration': decoration} if decoration else {}}

def test_banner_targets_suggest_the_old_alt_only_for_a_figure_that_lost_its_tag():
    from review import core
    adds = {'alt': [add_item('alt', '820 0', 5), add_item('alt', '9 0', 5, before='kept alt'), add_item('alt', '7 0', 3)],
            'page_figures': [add_item('page_figures', 1, 1)]}
    he = {'figure_pages': [5], 'changed': [{'page': 5, 'alt': 'Old logo'}], 'lost': [{'page': 1, 'alt': 'Book cover'}]}
    assert core.hand_edit_targets(he, adds) == [
        {'kind': 'page_figures', 'target': 1, 'page': 1, 'why': 'lost_tag', 'old_alt': 'Book cover', 'suggest': 'Book cover'},   # now a whole-page figure
        {'kind': 'alt', 'target': '820 0', 'page': 5, 'why': 'new_image', 'old_alt': 'Old logo', 'suggest': None}]   # shown, never suggested

def test_banner_targets_leave_out_decided_and_decoration_figures():
    from review import core
    adds = {'alt': [add_item('alt', '4 0', 2, decoration='artifacts.elements:4 0')], 'page_figures': []}   # 820 0 decided: not in adds
    assert core.hand_edit_targets({'figure_pages': [2, 5], 'lost': [{'page': 2, 'alt': 'old'}]}, adds) == []
    adds = {'alt': [add_item('alt', '5 0', 2)], 'page_figures': []}                    # a lost figure tagged anew on a tagged page
    assert core.hand_edit_targets({'figure_pages': [], 'lost': [{'page': 2, 'alt': 'old'}]}, adds) == [
        {'kind': 'alt', 'target': '5 0', 'page': 2, 'why': 'lost_tag', 'old_alt': 'old', 'suggest': 'old'}]

# ---- the review page's Earlier Review section (review/core.py earlier_review), and earlier notes on check cards
def reviewed_parent(tmp_path, review=True):
    """The synthetic parent run, its record given one applied alt decision and (review) a reviewer's statuses and notes."""
    src, P = parent_run(tmp_path)
    digest = json.load(open(os.path.join(P, 'reviews', '_audit', 'digest.json'), encoding='utf-8'))
    obj = digest['figures'][1]['obj']
    rp = os.path.join(P, 'record.json'); rec = json.load(open(rp, encoding='utf-8'))
    rec['workorder']['alt'] = [{'obj': obj, 'alt': 'A red square, darker'}]
    if review:
        rec['review'] = {'workorder': {'reviewer': 'Pat', 'date': '2026-11-09'}, 'decisions': [
            {'id': f'alt:{obj}', 'kind': 'Alt text', 'label': f'Figure {obj}', 'page': 1, 'status': 'changed', 'note': 'darker red'},
            {'id': 'reading_order:jump:1', 'kind': 'Reading order check', 'label': 'Text on PDF 1 jumps back up the page', 'page': 1,
             'status': 'seen', 'note': 'fine as it is'}]}
    else: rec.pop('review', None)
    json.dump(rec, open(rp, 'w', encoding='utf-8'))
    return P, obj

def test_earlier_review_lists_the_parents_decisions_with_status_and_note(tmp_path):
    from review import core
    P, obj = reviewed_parent(tmp_path)
    er = core.earlier_review({'parent': {'run': P}})
    assert er['reviewed_by'] == 'Pat' and er['reviewed_on'] == '2026-11-09'
    by = {x['id']: x for x in er['items']}
    assert by[f'alt:{obj}']['value'] == 'A red square, darker' and by[f'alt:{obj}']['page'] == 1
    assert by[f'alt:{obj}']['status'] == 'changed by the reviewer' and by[f'alt:{obj}']['note'] == 'darker red'
    assert by['reading_order:jump:1']['status'] == 'seen' and by['reading_order:jump:1']['note'] == 'fine as it is'

def test_earlier_review_of_an_unreviewed_parent_and_of_one_whose_digest_is_gone(tmp_path):
    from review import core
    P, obj = reviewed_parent(tmp_path, review=False)
    er = core.earlier_review({'parent': {'run': P}})
    assert er['reviewed_by'] is None and [x['status'] for x in er['items']] == ['applied as the AI wrote it']
    os.remove(os.path.join(P, 'reviews', '_audit', 'digest.json'))
    assert core.earlier_review({'parent': {'run': P}}) is None

def test_a_check_card_that_comes_back_shows_its_earlier_note_only_when_the_pages_are_the_same(tmp_path, monkeypatch):
    from review import core
    P, obj = reviewed_parent(tmp_path)
    R = tmp_path / 'child'; (R / '_handedit').mkdir(parents=True); (R / '_audit').mkdir()
    shutil.copy(os.path.join(P, 'reviews', '_audit', 'digest.json'), R / '_audit' / 'digest.json')
    (R / 'workorder.ai.json').write_text(json.dumps({'schema': 'workorder/0.2'}))
    def run_prepare(pages):
        (R / '_handedit' / 'hand_edit.json').write_text(json.dumps({'parent': {'run': P}, 'pages': pages, 'figures_changed': [], 'figures_lost': []}))
        card = {'id': 'reading_order:jump:1', 'key': 'reading_order', 'kind': 'Reading order check', 'priority': 5, 'images': [], 'context': {}, 'page': 1}
        monkeypatch.setattr(core, 'dry_run', lambda R, pdf: {})
        monkeypatch.setattr(core, 'reading_order_for', lambda *a: {'entries': []})
        monkeypatch.setattr(core, 'build_items', lambda *a, **k: [dict(card, context={})] if len(a) > 2 else [])
        monkeypatch.setattr(core, 'render_pages', lambda *a: None)
        monkeypatch.setattr(core, 'addable', lambda *a: {k: [] for k in core.ADD_KINDS})
        return core.prepare(str(R), 'x.pdf')['items'][0]['context']
    assert run_prepare([1, 1]) == {'earlier_note': 'fine as it is', 'earlier_status': 'seen'}
    assert run_prepare([1, 2]) == {}

# ---- carried decisions: no card, still applied (review/core.py prepare, apply_decisions)
def test_carried_decisions_get_no_card_and_are_still_applied(tmp_path, monkeypatch):
    from review import core
    R = tmp_path / 'child'; (R / '_audit').mkdir(parents=True)
    ai = {'schema': 'workorder/0.2', 'sections': {'toc_pages': [6, 7, 8, 9, 10, 11]}}
    (R / 'workorder.ai.json').write_text(json.dumps(ai)); (R / '_audit' / 'digest.json').write_text(json.dumps({'source': {'pages': 12}}))
    cards = [{'id': 'key:sections', 'key': 'sections', 'kind': 'Other decisions', 'priority': None, 'images': [], 'context': {}, 'page': None},
             {'id': 'reading_order:jump:3', 'key': 'reading_order', 'kind': 'Reading order check', 'priority': 5, 'images': [], 'context': {}, 'page': 3, 'loc': None}]
    monkeypatch.setattr(core, 'dry_run', lambda R, pdf: {})
    monkeypatch.setattr(core, 'reading_order_for', lambda *a: {'entries': []})
    monkeypatch.setattr(core, 'build_items', lambda *a, **k: [dict(c, context={}) for c in cards] if len(a) > 2 else [])
    monkeypatch.setattr(core, 'render_pages', lambda *a: None)
    monkeypatch.setattr(core, 'addable', lambda *a: {k: [] for k in core.ADD_KINDS})
    assert [it['id'] for it in core.prepare(str(R), 'x.pdf')['items']] == ['key:sections', 'reading_order:jump:3']   # not edited by hand: a card
    (R / '_handedit').mkdir(); (R / '_handedit' / 'hand_edit.json').write_text(json.dumps({'pages': [12, 12]}))
    (R / 'run.json').write_text(json.dumps({'no_model': 'x', 'carried_from_parent': ['sections']}))
    d = core.prepare(str(R), 'x.pdf')
    assert [it['id'] for it in d['items']] == ['reading_order:jump:3']
    assert d['hand_edit']['carried'] == [{'key': 'sections', 'what': 'contents pages (PDF 6–11)'}]
    wo = core.apply_decisions(ai, d['items'], {})
    assert wo['sections'] == {'toc_pages': [6, 7, 8, 9, 10, 11]}                    # no card, still in the order Finish applies

# ---- import paths: the original as base, an untagged file, PDF 2.0, pages added, a new image in no figure, a batch parent,
#      running the same import again, and the hand_edit read back when reviewing again
def no_run(P, edited, *more, label='x'):
    return sh([sys.executable, 'handedit.py', 'import', P, str(edited), '--by', 'Pat', '--note', 'n', '--label', label, '--no-run', *more])

def he_json(P, label='x'): return json.load(open(os.path.join(os.path.dirname(P), label, '_handedit', 'hand_edit.json')))

def test_the_original_can_be_the_base_and_must_be_the_runs_own(tmp_path):
    src, P = parent_run(tmp_path)
    edited = swap_image(src, tmp_path / 'orig-edited.pdf')
    r = no_run(P, edited, '--base', 'original', '--base-pdf', src)
    assert r.returncode == 0, r.stderr
    h = he_json(P); assert h['base'] == 'original' and h['base_sha256'] == sha(src) and [f['page'] for f in h['figures_changed']] == [1]
    other = figures_pdf(tmp_path / 'other.pdf', alts=('x', 'y'))
    r = no_run(P, edited, '--base', 'original', '--base-pdf', other, label='y')
    assert r.returncode == 1 and "is not this run's original" in r.stderr and not os.path.exists(os.path.join(os.path.dirname(P), 'y'))

def test_an_untagged_edited_file_gets_no_working_copy(tmp_path):
    src, P = parent_run(tmp_path)
    out = os.path.join(P, json.load(open(os.path.join(P, 'record.json')))['document']['output'])
    pdf = pikepdf.open(out); del pdf.Root['/StructTreeRoot']; pdf.save(tmp_path / 'untagged.pdf')
    assert no_run(P, tmp_path / 'untagged.pdf').returncode == 0
    h = he_json(P); assert h['input'] is None and h['figures_changed'] == [] and len(h['figures_lost']) == 2   # intake tags it in the run

def test_a_pdf_2_edit_stops_for_a_person_before_any_folder_is_made(tmp_path):
    src, P = parent_run(tmp_path)
    out = os.path.join(P, json.load(open(os.path.join(P, 'record.json')))['document']['output'])
    pdf = pikepdf.open(swap_image(out, tmp_path / 'e.pdf')); pdf.save(tmp_path / 'v2.pdf', min_version='2.0')
    r = no_run(P, tmp_path / 'v2.pdf')
    assert r.returncode == 3 and 'refused: the edited PDF is not supported yet: PDF 2.0' in r.stderr
    assert not os.path.exists(os.path.join(os.path.dirname(P), 'x'))

def test_pages_added_are_recorded(tmp_path):
    src, P = parent_run(tmp_path)
    out = os.path.join(P, json.load(open(os.path.join(P, 'record.json')))['document']['output'])
    pdf = pikepdf.open(out); pdf.add_blank_page(page_size=(432, 576)); pdf.save(tmp_path / 'more.pdf')
    assert no_run(P, tmp_path / 'more.pdf').returncode == 0 and he_json(P)['pages'] == [1, 2]

def test_a_new_image_that_no_figure_holds_is_listed(tmp_path):
    base = figures_pdf(tmp_path / 'base.pdf')
    edited = figures_pdf(tmp_path / 'edited.pdf', colors=(b'\x00\xff\x00', b'\xff\x00\x00'), untag_first=True)   # new, untagged
    ch = handedit.changed(base, edited)
    assert len(ch['outside_figures']) == 1 and ch['outside_figures'][0]['page'] == 1 and ch['figures'] == []
    assert ch['figures_lost'] == [{'page': 1, 'alt': 'A blue square'}]

def test_a_batch_books_edited_copy_lands_in_runs_name_label(tmp_path):
    src, P = parent_run(tmp_path)
    B = tmp_path / 'runs' / 'batches' / 'b1' / 'book'; shutil.copytree(P, B)
    out = os.path.join(B, json.load(open(B / 'record.json'))['document']['output'])
    assert no_run(str(B), swap_image(out, tmp_path / 'e.pdf'), label='fromb').returncode == 0
    assert (tmp_path / 'runs' / 'book' / 'fromb' / '_handedit' / 'hand_edit.json').exists()
    assert not (tmp_path / 'runs' / 'batches' / 'b1' / 'fromb').exists()

def test_the_same_import_again_carries_on_and_another_file_is_refused(tmp_path):
    src, P = parent_run(tmp_path)
    out = os.path.join(P, json.load(open(os.path.join(P, 'record.json')))['document']['output'])
    e1 = swap_image(out, tmp_path / 'e1.pdf')
    assert no_run(P, e1).returncode == 0
    r = no_run(P, e1); assert r.returncode == 0 and 'already in place' in r.stdout
    e2 = swap_image(out, tmp_path / 'e2.pdf', word=True)
    r = no_run(P, e2); assert r.returncode == 1 and 'already exists for another file or mode' in r.stderr

def test_reviewing_again_reads_the_hand_edit_from_the_record(tmp_path):
    from review import core
    R = tmp_path / 'run'; (R / 'reviews').mkdir(parents=True)
    (R / 'record.json').write_text(json.dumps({'hand_edit': {'by': 'Pat', 'figures_changed': [{'page': 2, 'alt': 'old'}]}}))
    assert core.hand_edit_raw(str(R / 'reviews'))['by'] == 'Pat' and core.hand_edit(str(R / 'reviews'))['figure_pages'] == [2]
    assert core.hand_edit_raw(str(R)) is None                                       # only reviews/ falls back to the record

# ---- wording in a run with no AI call
def test_a_run_with_no_ai_call_never_credits_the_ai(tmp_path):
    from lib import glance as G
    from review import sessions as S
    g = {'ai_decisions': {'count': 1, 'reviewed': None, 'no_model': True}}
    assert S.from_label('ai', True) == 'the beginning (no AI call)' and S.from_label('ai') == "the AI's decisions"
    assert "'Decisions (no AI call)' if ad.get('no_model')" in open(os.path.join(PIPE, 'report_html.py')).read()
    assert '"Decisions (no AI call)" if ad.get("no_model")' in open(os.path.join(PIPE, 'lib', 'glance.py')).read()
    R = tmp_path / 'r'; R.mkdir(); (R / 'run.json').write_text(json.dumps({'no_model': 'x'}))
    assert S.no_model(str(R)) and not S.no_model(str(tmp_path))


# ---- no AI call means none at all: main's page readings (#49, read_pages.py) are never offered with DECIDE=none
def test_a_run_with_no_ai_call_reads_no_pages():
    sh_ = open(os.path.join(PIPE, 'run_api.sh'), encoding='utf-8').read()
    gate = next(l for l in sh_.splitlines() if l.startswith('if [[ ${PAGE_READS} != off'))
    assert '${DECIDE:-} != none' in gate
    assert "'DECIDE': 'none', 'REVIEW': '1', 'PAGE_READS': 'off'" in open(os.path.join(PIPE, 'handedit.py'), encoding='utf-8').read()
