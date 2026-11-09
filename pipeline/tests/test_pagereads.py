"""test_pagereads.py: whole-page AI readings of scanned Hawaiian pages (issue #49): which pages are read, how a reading is
paired with the OCR words, what the work-order check refuses, and what apply.py writes.

    python -m pytest tests/test_pagereads.py -q

The expected results follow docs/ocr-words.md ("Pages read whole"). No book content; nothing is sent anywhere; veraPDF is off.
"""
import os, sys, json, subprocess
import pikepdf, pytest
from lib import pagereads, workorder_check as wc

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- which pages
def test_a_mostly_hawaiian_page_is_read():
    words = ['ka', 'Hawai‘i', 'kēia', 'moolelo', 'kanaka', 'aina', 'hoomaka', 'Honolulu', 'lehulehu', 'naauao'] * 3
    assert pagereads.hawaiian_share(words) >= pagereads.SHARE_MIN

def test_an_english_page_is_not_read():
    words = ['the', 'island', 'people', 'Honolulu', 'harbor', 'during', 'their', 'first', 'years', 'there'] * 3
    assert pagereads.hawaiian_share(words) < pagereads.SHARE_MIN

def test_short_words_do_not_count():
    """he, me, no, ka have Hawaiian shape in English too: only words of 4+ letters count, and a page needs 20 of them."""
    assert pagereads.hawaiian_share(['he', 'me', 'no', 'ka'] * 30) is None
    assert pagereads.hawaiian_share(['kanaka'] * 19) is None

# ---- accepting a reading at one place
@pytest.mark.parametrize('ocr, reading, why', [
    ('Hawai‘i', 'Hawaiʻi', None),            # a quote mark for the ʻokina
    ('ike', 'ʻike', None),                   # a dropped ʻokina
    ('Manoa', 'Mānoa', None),                # a dropped kahakō
    ('Kéia', 'kēia', None),                  # a misread kahakō
    ('piilama', 'pūlama', None),             # ū read as "ii": a misreading ocr_words would accept
    ('apps', 'ʻapōpō', None),                # two letters garbled in a longer word: still a misreading
    ('Hawaii', 'Kalākaua', 'too different'), # another word: left as the OCR read it
    ('nd', 'pond', 'too different'), ('we', 'west', 'too different'), ('0', 'of', 'too different'),   # a short OCR word, a longer reading
    ('p6haku', 'pōhaku', None),              # ō read as 6
    ('bundle', 'bundles', None),             # a letter lost at a curled page edge
    ('a', 'sea', 'too different'),           # a short word paired with the wrong one on a hard page
    ('to', 'of', 'too different'),
    ('th', 'the', 'too different'),          # short: a misreading can't be told from another word
    ('e', '34', 'too different'),
    ('Na', 'Nā', None),                      # marks alone: any length
    ('0', 'o', None),                        # a short word read as junk: o → 0, lā → 1a, pū → pi
    ('1a', 'lā', None), ('pi', 'pū', None), ('14', 'lā', None),
    ('ai', 'Kai', 'too different'),          # a letter added: another word
    ('nd', 'nō', None), ('dina', 'ʻāina', None),
    ('na', 'na', 'same'),
    ('hoi', 'hoʻi no', 'not one word'),
])
def test_accept(ocr, reading, why):
    assert pagereads.accept(ocr, reading) == why

# ---- a reading that wrote every ʻokina as a quote mark
def test_a_page_of_quote_marks_for_the_okina_is_corrected():
    text = 'Ua hoʻi mai'.replace('ʻ', '‘') + ' ' + ' '.join(['ka‘ana', 'mana‘o', 'loa‘a', 'po‘i', 'i‘a'])
    fixed, n = pagereads.okina_slip(text)
    assert n == 6 and '‘' not in fixed and 'manaʻo' in fixed

def test_a_word_initial_okina_written_as_a_quote_mark_is_corrected():
    fixed, n = pagereads.okina_slip(' '.join(['‘o', '‘ana', '‘A‘ole', 'loa‘a', 'i‘a', 'ka']))
    assert fixed == 'ʻo ʻana ʻAʻole loaʻa iʻa ka' and n == 6

def test_a_printed_apostrophe_or_two_stays():
    assert pagereads.okina_slip("a ma'u mau hoi kahi wahi, he i'a") == ("a ma'u mau hoi kahi wahi, he i'a", 0)

def test_a_reading_that_uses_the_okina_is_left_alone():
    text = 'hoʻi ' + ' '.join(['ka‘ana'] * 6)              # one real ʻokina: the quote marks are what the page prints
    assert pagereads.okina_slip(text) == (text, 0)

def test_english_apostrophes_are_not_okina():
    text = ' '.join(["don't", "O'Brien's", "can't", "isn't", "won't", "it's"])
    assert pagereads.okina_slip(text) == (text, 0)

# ---- pairing a page
def test_each_place_gets_its_own_reading():
    """na and nā are both right, each where the page prints it: a reading per place, not per form."""
    changes, n = pagereads.align(['na', 'kanaka', 'na', 'aina'], ['nā', 'kanaka', 'na', 'ʻāina'])
    assert changes == {0: 'nā', 3: 'ʻāina'} and n['changed'] == 2 and n['paired'] == 4

def test_a_word_the_ocr_split_is_left_alone():
    changes, n = pagereads.align(['Hawai', '‘i', 'nei'], ['Hawaiʻi', 'nei'])
    assert changes == {} and n['unpaired'] == 2 and n['paired'] == 1

def test_extra_words_in_the_reading_do_not_shift_the_pairs():
    changes, _ = pagereads.align(['ka', 'aina', 'nui'], ['59', 'ka', 'ʻāina', 'nui'])
    assert changes == {1: 'ʻāina'}

# ---- the work-order check
def check(wo):
    return wc.check(wo, {'source': {'pages': 10}, 'elements': [], 'figures': [], 'headings': [], 'styles': []}, set(), set())

def test_page_readings_kept_and_normalized():
    wo = {'page_readings': [{'page': 2, 'text': 'Ua mākaukau'}]}
    assert check(wo) == [] and wo['page_readings'] == [{'page': 2, 'text': 'Ua mākaukau'}]

@pytest.mark.parametrize('item, why', [
    ({'page': 11, 'text': 'x'}, 'bad page'), ({'page': '2', 'text': 'x'}, 'bad page'), ({'page': True, 'text': 'x'}, 'bad page'),
    ({'page': 2, 'text': '  '}, 'empty'), ({'page': 2}, 'empty'),
])
def test_page_reading_dropped(item, why):
    wo = {'page_readings': [item]}
    assert [d['why'] for d in check(wo)] == [why] and 'page_readings' not in wo

def test_the_same_page_twice_keeps_the_first():
    wo = {'page_readings': [{'page': 2, 'text': 'a'}, {'page': 2, 'text': 'b'}]}
    assert [d['why'] for d in check(wo)] == ['the same page twice'] and wo['page_readings'] == [{'page': 2, 'text': 'a'}]

# ---- apply.py on a tiny tagged page, its OCR words on the page or in a form (OCRmyPDF 17 draws the layer in a form)
WORDS = 'BT /F1 11 Tf 72 500 Td (Hawai\x91i) Tj 60 0 Td (na) Tj 30 0 Td (ke) Tj 30 0 Td (na) Tj ET'
def hawaiian_pdf(path, in_form, words=WORDS):
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    marked = f'/P <</MCID 0>> BDC {words} EMC\n'
    res = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], Resources=res, StructParents=0)
    if in_form:
        fx = pikepdf.Stream(pdf, marked.encode('latin-1')); fx.Type = pikepdf.Name.XObject; fx.Subtype = pikepdf.Name.Form
        fx.BBox = [0, 0, 432, 576]; fx.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)); fx.StructParents = 1
        fx = pdf.make_indirect(fx); res.XObject = pikepdf.Dictionary(OCR=fx)
        page.Contents = pikepdf.Stream(pdf, b'q /OCR Do Q\n')
    else: page.Contents = pikepdf.Stream(pdf, marked.encode('latin-1'))
    pdf.pages.append(pikepdf.Page(page)); pg = pdf.pages[0].obj
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    p_ = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg))
    p_.K = pikepdf.Array([pikepdf.Dictionary(Type=pikepdf.Name.MCR, MCID=0, Pg=pg, Stm=fx)]) if in_form else 0
    doc.K = pikepdf.Array([p_]); root.K = pikepdf.Array([doc])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([1, pikepdf.Array([p_])] if in_form else [0, pikepdf.Array([p_])])))
    root.ParentTreeNextKey = 2
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('haw')
    pdf.save(path, deterministic_id=True)
    return path

def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off'), capture_output=True, text=True)
    assert r.returncode == 0, f'{script} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}'

def spans(path):
    """The ActualText spans of the page and its forms, in drawing order."""
    out = []
    with pikepdf.open(path) as pdf:
        pg = pdf.pages[0]
        streams = [pg] + [x for x in (pg.obj.Resources.get('/XObject') or {}).values()]
        for c in streams:
            for ins in pikepdf.parse_content_stream(c):
                if str(ins.operator) == 'BDC' and len(ins.operands) > 1 and '/ActualText' in ins.operands[1]: out.append(str(ins.operands[1].ActualText))
    return out

@pytest.mark.parametrize('in_form', [False, True], ids=['on the page', 'in a form'])
def test_apply_gives_each_place_its_reading(tmp_path, in_form):
    src = hawaiian_pdf(str(tmp_path / 'haw.pdf'), in_form)
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'schema': 'workorder/0.2', 'page_readings': [{'page': 1, 'text': 'Hawaiʻi nā ke\nna'}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, w, out); run('verify.py', src, out)
    assert spans(out) == ['Hawaiʻi', 'nā']                     # the second na is printed without a kahakō: left alone
    log = json.load(open(str(out) + '.log.json', encoding='utf-8'))
    assert log['page_readings'][0]['changed'] == 2 and any('pages read by the AI' in d['what'] for d in log['deferred'])
    v = json.load(open(str(out) + '.verify.json', encoding='utf-8'))
    assert not v.get('pixel_pages_differing') and not v.get('text_pages_changed') and v['actual_text_spans']['result'] == 2

@pytest.mark.parametrize('in_form', [False, True], ids=['on the page', 'in a form'])
def test_a_quote_mark_read_for_a_word_initial_okina_is_replaced_not_kept(tmp_path, in_form):
    """Tesseract reads a word-initial ʻokina as a quote mark (‘o, ‘aina): the reading's ʻ takes its place. A screen reader
    is never given ‘ʻo (the quote mark and the ʻokina); a real quotation mark before a word stays."""
    src = hawaiian_pdf(str(tmp_path / 'haw.pdf'), in_form, 'BT /F1 11 Tf 72 500 Td (\x91o) Tj 30 0 Td (Hina) Tj 40 0 Td (\x93\x91aina) Tj 50 0 Td (ka) Tj ET')
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'schema': 'workorder/0.2', 'page_readings': [{'page': 1, 'text': 'ʻo Hina “ʻāina kā'}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, w, out)
    assert spans(out) == ['ʻo', '“ʻāina', 'kā']

def test_ocr_words_replace_the_quote_mark_too(tmp_path):
    src = hawaiian_pdf(str(tmp_path / 'haw.pdf'), True, 'BT /F1 11 Tf 72 500 Td (\x91ina) Tj 40 0 Td (ka) Tj ET')
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'schema': 'workorder/0.2', 'ocr_words': [{'id': 1, 'text': 'ina', 'reads': 'ʻāina', 'count': 1}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, w, out)
    assert spans(out) == ['ʻāina']

def test_a_shared_form_is_not_changed(tmp_path):
    """A form drawn from two places would show a change in both: its words are left alone."""
    src = hawaiian_pdf(str(tmp_path / 'haw.pdf'), True)
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        pg = pdf.pages[0].obj; pg.Contents = pdf.make_stream(b'q /OCR Do Q q 1 0 0 1 0 -40 cm /OCR Do Q\n'); pdf.save(src)
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'schema': 'workorder/0.2', 'page_readings': [{'page': 1, 'text': 'Hawaiʻi nā ke na'}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, w, out)
    assert spans(out) == []

@pytest.mark.parametrize('in_form', [False, True], ids=['on the page', 'in a form'])
def test_ocr_words_reach_the_ocr_layer_in_a_form(tmp_path, in_form):
    """ocr_words uses the same walk: a form drawn from one page (OCRmyPDF 17's OCR layer) is followed, so a reading is found."""
    src = hawaiian_pdf(str(tmp_path / 'haw.pdf'), in_form)
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'schema': 'workorder/0.2', 'ocr_words': [{'id': 1, 'text': 'Hawai\u2018i', 'reads': 'Hawai\u02bbi', 'count': 1}]}))
    out = tmp_path / 'out.pdf'
    run('apply.py', src, w, out)
    assert spans(out) == ['Hawaiʻi']
    assert json.load(open(str(out) + '.log.json', encoding='utf-8'))['ocr_words']['by_form'][0]['found'] == 1
