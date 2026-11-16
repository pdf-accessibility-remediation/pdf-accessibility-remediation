"""#121 (re-OCR keeping the page images): the pages REOCR reads (triage only), the old layer on record, the OCR-text gate,
and the app's choice in "Language of the Scanned Pages" with "Keep the Existing OCR Text" as the default. No Java, no
OCRmyPDF, no Tesseract here: the redo itself is an intake_cases --full case."""
import os, sys, json, gzip
import pikepdf, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import intake  # noqa: E402
from lib import glance  # noqa: E402
from webapp import lang as LG, books as BK, newrun as NR, jobs  # noqa: E402
from test_webapp import setup, settings  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402


def test_reocr_pages_come_from_triage_only():
    kinds = {'text': [1], 'ocr-layer': [3, 2, 5], 'image-only': [4], 'blank': [6]}
    got = intake.reocr_pages(kinds, [4], 'auto')
    assert got == {'reocr': [2, 3, 5], 'image': [4]} and 1 not in got['reocr'] + got['image']   # never the born-digital cover
    assert intake.reocr_pages(kinds, [4], 'off')['image'] == []
    assert intake.reocr_pages({'text': [1, 2]}, [], 'auto') == {'reocr': [], 'image': []}


def test_the_old_layer_is_kept_on_record(tmp_path):
    pdf = pikepdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica))
    for t in (b'Hawai i first page', b'second page'):
        pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 300, 300],
                         Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
                         Contents=pdf.make_stream(b'BT 3 Tr /F1 12 Tf 20 200 Td (' + t + b') Tj ET'))))
    p = str(tmp_path / 'a.pdf'); pdf.save(p)
    rec = {'original': {'producer': 'Some OCR tool'}, 'ocr_layer_test': {'verdict': 'usable', 'median_cer': 0.03, 'diacritics': {'pages': [1]}}}
    r = intake.keep_old_layer(p, [1, 2], str(tmp_path), rec, 'mri+eng')
    assert r['pages'] == [1, 2] and r['producer'] == 'Some OCR tool' and r['language'] == 'mri+eng'
    assert r['layer_test']['diacritics'] == {'pages': [1]} and set(r['old_text_sha256']) == {'1', '2'}
    old = json.load(gzip.open(tmp_path / 'old_ocr_layer.json.gz', 'rt'))
    assert 'Hawai i first page' in old['1'] and 'second page' in old['2']


def test_a_layer_missing_cjk_needs_ocr_approval():
    assert glance.ocr_layer_flagged({'ocr_layer_test': {'verdict': 'usable', 'cjk_on_images': {'pages': [12]}}})
    assert not glance.ocr_layer_flagged({'ocr_layer_test': {'verdict': 'usable'}})
    assert glance.ocr_review_needed({'ocr': {'mode': 'redo', 'pages_with_ocr_text': [2, 3], 'reocr_pages': [2, 3]}})


def intake_json(R, **kw):
    (R / '_intake').mkdir(parents=True, exist_ok=True)
    j = {'status': 'done', 'flags': [], 'settings': {'REOCR': False}, 'triage': {'counts': {'ocr-layer': 120, 'text': 1}},
         'reocr_suggested': {'why': ['diacritics'], 'pages': [14, 30]}, **kw}
    (R / '_intake' / 'intake.json').write_text(json.dumps(j))


def test_the_reocr_question(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'mri', 'chi_tra'])
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'
    intake_json(R)
    q = LG.question(s, str(R))
    assert LG.asks(str(R)) == 'reocr' and q['kind'] == 'reocr' and q['suggested'] == LG.KEEP and q['pages'] == 120
    assert q['choices'][0] == [LG.KEEP, 'Keep the Existing OCR Text'] and len(q['choices']) > 1
    assert q['evidence'] == ['The page images show accents or other marks that the existing OCR text lacks.']
    intake_json(R, reocr_suggested={'why': ['cjk'], 'pages': [3]})
    assert 'Chinese, Japanese or Korean' in LG.question(s, str(R))['evidence'][0]
    intake_json(R, settings={'REOCR': True})                                   # already read again: not asked
    assert LG.question(s, str(R)) is None and not LG.asks(str(R))
    intake_json(R, reocr_suggested=None)                                       # nothing suggested: not asked
    assert LG.question(s, str(R)) is None
    intake_json(R); (R / 'workorder.ai.json').write_text('{}')                 # the AI has decided: too late to ask
    assert LG.question(s, str(R)) is None
    B = setup / 'runs' / 'batches' / 'b1' / 'bk'; intake_json(B)              # a batch's PDF: not asked on the batch page yet
    assert LG.question(s, str(B)) is None


def test_keep_or_read_again(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'mri'])
    s = settings(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book'))
    key = BK.listing(s)[0]['key']
    j = NR.start_estimate(s, [], key, 'First'); jobs.update(s['jobs'], j['id'], status='done')
    R = setup / 'runs' / 'bk' / 'First'; intake_json(R)
    with pytest.raises(ValueError, match='Choose a language'): NR.answer_language(s, 'bk/First', str(R), 'xx')
    a = NR.answer_language(s, 'bk/First', str(R), 'mri+eng')                   # read again with the Māori pack (Hawaiian marks)
    assert a['env_set'] == {'ESTIMATE': '1', 'OCR_LANG': 'mri+eng', 'REOCR': '1'} and 'read again' in a['what']
    assert a['ocr_name'] == 'Hawaiian or Māori and English'
    jobs.update(s['jobs'], a['id'], status='done')
    assert NR.again_estimate(s, 'bk/First', str(R))['env_set']['REOCR'] == '1'   # the next estimate keeps it
    assert NR.answer_language(s, 'bk/First', str(R), LG.KEEP) is None           # Keep: no job, recorded
    assert (R / '_intake' / LG.KEEP_FILE).exists() and LG.question(s, str(R)) is None and not LG.asks(str(R))


def test_env_for():
    assert LG.env_for('eng') == {'ESTIMATE': '1'} and LG.env_for('eng', reocr=True) == {'ESTIMATE': '1', 'REOCR': '1'}


def stopped_json(R, **kw):
    intake_json(R, status='stopped', summary='CJK text the existing OCR text lacks (page 3): run again with REOCR=1 and OCR_LANG naming the language',
                flags=[{'what': 'OCR layer: CJK missing', 'why': '…', 'pages': [3], 'check': True}],
                reocr_suggested={'why': ['cjk'], 'pages': [3]},
                **{'ocr_layer_test': {'cjk_on_images': {'pages': [3], 'cjk_characters': {'3': 14}, 'cjk_distinct': {'3': 12}, 'found_by': {'3': 'picture-like page'}}}, **kw})


def test_the_reocr_stop_question(setup, monkeypatch):
    """Review 04 H2: CJK under an OCR layer that lacks it stops the run; the question offers the CJK languages and, since
    review 06 H1, "Keep the Existing OCR Text" with a person's name, and shows each page with its counts."""
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'mri', 'chi_tra', 'jpn'])
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'
    stopped_json(R)
    q = LG.question(s, str(R))
    assert LG.asks(str(R)) == 'reocr' and q['kind'] == 'reocr' and q['stopped'] and q['suggested'] is None
    assert q['choices'][0] == [LG.KEEP, 'Keep the Existing OCR Text'] and q['needs_name'] == LG.KEEP
    assert len(q['choices']) > 1 and all(any(x in c[0] for x in LG.CJK) for c in q['choices'][1:])
    assert q['found'] == [{'page': 3, 'characters': 14, 'different': 12, 'picture': True, 'image': False}]
    (R / '_intake' / 'cjk_page_3.png').write_bytes(b'\x89PNG')
    assert LG.question(s, str(R))['found'][0]['image']
    assert 'pictures of text' in q['evidence'][1]
    assert LG.check(s, str(R), LG.KEEP) == 'Keep the Existing OCR Text'
    stopped_json(R, settings={'REOCR': True})                                  # stopped again after a re-OCR: not this question
    assert LG.question(s, str(R)) is None
    B = setup / 'runs' / 'batches' / 'b1' / 'bk'; stopped_json(B)             # a batch's PDF: stopped with a CHECK, not asked
    assert LG.question(s, str(B)) is None and not LG.asks(str(B))


def test_the_reocr_stop_answer(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'chi_tra'])
    s = settings(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book'))
    key = BK.listing(s)[0]['key']
    j = NR.start_estimate(s, [], key, 'First'); jobs.update(s['jobs'], j['id'], status='failed', exit=3)
    R = setup / 'runs' / 'bk' / 'First'; stopped_json(R)
    a = NR.answer_language(s, 'bk/First', str(R), 'chi_tra+eng')
    assert a['env_set'] == {'ESTIMATE': '1', 'OCR_LANG': 'chi_tra+eng', 'REOCR': '1'} and 'read again' in a['what']


def test_keep_at_the_cjk_stop(setup, monkeypatch):
    """Review 06 H1: Keep at the CJK stop records the pages, the name, the date and the counts, and gets the estimate again
    with KEEP_CJK_PAGES; every later job of the run carries it (the next estimate, Try Again, Spend), so intake is reused."""
    from webapp import config, spend as SP
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'chi_tra'])
    s = settings(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book'))
    key = BK.listing(s)[0]['key']
    j = NR.start_estimate(s, [], key, 'First'); jobs.update(s['jobs'], j['id'], status='failed', exit=3)
    R = setup / 'runs' / 'bk' / 'First'; stopped_json(R)
    with pytest.raises(ValueError, match='Your Name'): NR.answer_language(s, 'bk/First', str(R), LG.KEEP)
    with pytest.raises(ValueError, match='Your Name'): NR.answer_language(s, 'bk/First', str(R), LG.KEEP, '   ')
    a = NR.answer_language(s, 'bk/First', str(R), LG.KEEP, '  Kim   Lee ')
    assert a['env_set'] == {'ESTIMATE': '1', 'KEEP_CJK_PAGES': '3'} and 'kept on page 3' in a['what']
    k = json.loads((R / '_intake' / LG.CJK_KEEP_FILE).read_text())
    assert k['pages'] == [3] and k['by'] == 'Kim Lee' and k['at'] and k['counts'] == {'3': {'cjk_characters': 14, 'cjk_distinct': 12}}
    jobs.update(s['jobs'], a['id'], status='failed', exit=3)                  # stopped again on another page: both are kept
    stopped_json(R, settings={'REOCR': False, 'KEEP_CJK_PAGES': [3]}, ocr_layer_test={'cjk_on_images': {
        'pages': [9], 'cjk_characters': {'9': 30}, 'cjk_distinct': {'9': 21}, 'found_by': {'9': 'picture-like page'}}})
    a = NR.answer_language(s, 'bk/First', str(R), LG.KEEP, 'Kim')
    assert a['env_set']['KEEP_CJK_PAGES'] == '3,9'
    k = json.loads((R / '_intake' / LG.CJK_KEEP_FILE).read_text())
    assert k['pages'] == [3, 9] and set(k['counts']) == {'3', '9'}
    jobs.update(s['jobs'], a['id'], status='done'); intake_json(R, settings={'REOCR': False, 'KEEP_CJK_PAGES': [3, 9]}, reocr_suggested=None)
    assert NR.again_estimate(s, 'bk/First', str(R))['env_set']['KEEP_CJK_PAGES'] == '3,9'
    assert 'KEEP_CJK_PAGES' in config.JOB_ENV
    assert config.child_env(s, {'KEEP_CJK_PAGES': '3,9'}).get('KEEP_CJK_PAGES') == '3,9'
    import inspect                                                              # Spend and Try Again: the same carry lists
    assert "'KEEP_CJK_PAGES')" in inspect.getsource(SP.authorize) and "'KEEP_CJK_PAGES')" in inspect.getsource(NR.start_rerun)


def test_kept_pages_are_skipped_by_the_cjk_check():
    """Review 06 H1: the samples are drawn as before and the kept pages left out (no other page probed in their place);
    every picture-like hit is found at once, so one Keep covers the book."""
    seen = []
    def probe(i): seen.append(i); return {35: (14, 12), 41: (30, 21), 50: (0, 0)}.get(i, (0, 0))
    pick = list(range(1, 31)); pics = lambda: [5, 35, 41, 50, 60, 70, 80, 90, 100, 110]
    hit, by_, r = intake.layer_cjk_hits(pick, pics, set(), probe)
    assert hit == {35: (14, 12), 41: (30, 21)} and by_ == {35: 'picture-like page', 41: 'picture-like page'}
    assert seen == [1, 11, 21, 5, 35, 41, 50, 60, 70, 80, 90] and r['picture_like_checked'] == 8 and r['picture_like_pages'] == 10
    seen.clear(); hit, by_, r = intake.layer_cjk_hits(pick, pics, {35, 41}, probe)
    assert hit == {} and seen == [1, 11, 21, 5, 50, 60, 70, 80, 90] and r['kept_pages_skipped'] == [35, 41]
    seen.clear(); hit, _, r = intake.layer_cjk_hits(pick, None, set(), probe)  # REOCR: the sample pages only
    assert seen == [1, 11, 21] and 'picture_like_pages' not in r
    seen.clear(); hit, by_, _ = intake.layer_cjk_hits([35, 40, 45], pics, set(), probe)   # review 08 M2: a sample hit and a
    assert hit == {35: (14, 12), 41: (30, 21)} and by_ == {35: 'sample page', 41: 'picture-like page'}   # picture-like hit: one stop
    assert seen == [35, 40, 45, 5, 41, 50, 60, 70, 80, 90]                     # lists both; 35 is not read twice
    seen.clear(); hit, _, _ = intake.layer_cjk_hits([35, 40, 45], None, set(), probe)     # REOCR: the sample stops at its first hit
    assert hit == {35: (14, 12)} and seen == [35]


def test_the_cjk_page_rule():
    """Review 04 M3: 20+ different CJK characters, or 10+ that are 60%+ of those read; misreads repeat a few shapes."""
    assert intake.cjk_page(12, 12) and intake.cjk_page(19, 17) and intake.cjk_page(560, 86)
    assert not intake.cjk_page(40, 11) and not intake.cjk_page(30, 11) and not intake.cjk_page(16, 8) and not intake.cjk_page(7, 5)
    assert not intake.cjk_page(9, 9)                                           # under CJK_PROBE_MIN characters



def test_a_language_answer_after_a_keep_keeps_the_pages(setup, monkeypatch):
    """Review 08 M1: after a Keep, the run asks "Language of the Scanned Pages" again; the answer's estimate still names
    the kept pages, so the CJK check doesn't stop on them again."""
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'chi_tra'])
    s = settings(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book'))
    key = BK.listing(s)[0]['key']
    j = NR.start_estimate(s, [], key, 'First'); jobs.update(s['jobs'], j['id'], status='failed', exit=3)
    R = setup / 'runs' / 'bk' / 'First'; stopped_json(R)
    a = NR.answer_language(s, 'bk/First', str(R), LG.KEEP, 'Kim'); jobs.update(s['jobs'], a['id'], status='failed', exit=3)
    stopped_json(R, settings={'REOCR': False, 'KEEP_CJK_PAGES': [3]}, ocr_layer_test={'cjk_kept': {'pages': [3]}})   # stopped on the
    q = LG.question(s, str(R))                                                          # diacritics question instead
    b = NR.answer_language(s, 'bk/First', str(R), 'chi_tra+eng')
    assert b['env_set']['KEEP_CJK_PAGES'] == '3' and b['env_set'].get('REOCR') == '1' and q['kind'] == 'reocr'


def test_keep_cjk_pages_takes_only_pages_the_stop_named(tmp_path):
    """Review 09 L-B: a comma list only, of pages the last CJK stop named (or kept before); anything else stops with a plain
    message. Checked before any OCR or tagging, so no Tesseract is needed here."""
    import subprocess
    pdf = tmp_path / 'b.pdf'; pdf.write_bytes(pdf_bytes(5, 'A Book'))
    out = tmp_path / 'o'; out.mkdir()
    def run(v, prior=None):
        if prior is not None: (out / 'intake.json').write_text(json.dumps(prior))
        env = {**os.environ, 'KEEP_CJK_PAGES': v}; env.pop('REOCR', None)
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'intake.py'), str(pdf), str(out)],
                       env=env, capture_output=True, text=True)
        return json.loads((out / 'intake.json').read_text())
    stop_ = {'status': 'stopped', 'ocr_layer_test': {'cjk_on_images': {'pages': [2, 4]}, 'cjk_kept': {'pages': [1]}}}
    assert 'comma list' in run('2-4', stop_)['summary']
    j = run('3', stop_); assert j['status'] == 'stopped' and 'page 3, which the last CJK stop of this run did not name (it named 1, 2, 4)' in j['summary']
    assert 'pages 9' not in run('9', stop_)['summary'] and 'page 9' in run('9', stop_)['summary']   # outside the book
    j = run('2, 4,1', stop_); assert 'KEEP_CJK_PAGES' not in (j.get('summary') or '')              # named or kept before: accepted
    out = tmp_path / 'new'; out.mkdir()                     # review 11 M1: a new folder holds no stop, and the message says where to run
    j = run('2'); assert 'no CJK stop is recorded in this run folder' in j['summary'] and 'with RUN_DIR for a book of a batch' in j['summary']


def test_a_keep_keeps_ocr_text_approval_required(tmp_path):
    """Review 09 M-A: pages kept at the CJK stop leave the OCR gate open (a typed name is not an approval of the text), and
    the review page's OCR Text section names them, who kept them and when."""
    from review import ocr as RO
    ck = {'pages': [35], 'by': 'Kim Lee', 'at': '2026-11-15T10:00:00', 'counts': {'35': {'cjk_characters': 14, 'cjk_distinct': 12}}}
    it = {'status': 'done', 'ocr_layer_test': {'verdict': 'usable', 'pages': [{'page': 20, 'verdict': 'usable', 'cer': 0.01}], 'cjk_kept': ck},
          'triage': {'pages': {'ocr-layer': [20, 35]}}}
    assert glance.ocr_layer_flagged(it) and glance.ocr_review_needed(it)
    assert not glance.ocr_layer_flagged({'ocr_layer_test': {'verdict': 'usable'}})
    assert 35 in RO.listed_pages(it)
    w = RO.layer_words(it['ocr_layer_test'])
    assert 'On PDF 35, a check read Chinese, Japanese or Korean characters' in w and 'Kim Lee kept it on November 15, 2026' in w
    R = tmp_path / 'r'; (R / '_intake').mkdir(parents=True); (R / '_intake' / 'intake.json').write_text(json.dumps(it))
    sec = RO.section(str(R))
    f35 = next(p for p in sec['pages'] if p['page'] == 35)['findings']
    assert any('kept at the Chinese, Japanese or Korean check: 14 such characters' in x for x in f35)
