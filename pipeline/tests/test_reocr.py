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
                reocr_suggested={'why': ['cjk'], 'pages': [3]}, **kw)


def test_the_reocr_stop_question(setup, monkeypatch):
    """Review 04 H2: CJK under an OCR layer that lacks it stops the run; the question offers only CJK languages, no Keep."""
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'mri', 'chi_tra', 'jpn'])
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'
    stopped_json(R)
    q = LG.question(s, str(R))
    assert LG.asks(str(R)) == 'reocr' and q['kind'] == 'reocr' and q['stopped'] and q['suggested'] is None
    assert q['choices'] and all(any(x in c[0] for x in LG.CJK) for c in q['choices']) and LG.KEEP not in [c[0] for c in q['choices']]
    assert 'pictures of text' in q['evidence'][1]
    with pytest.raises(ValueError, match='Choose a language'): LG.check(s, str(R), LG.KEEP)
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


def test_the_cjk_page_rule():
    """Review 04 M3: 20+ different CJK characters, or 10+ that are 60%+ of those read; misreads repeat a few shapes."""
    assert intake.cjk_page(12, 12) and intake.cjk_page(19, 17) and intake.cjk_page(560, 86)
    assert not intake.cjk_page(40, 11) and not intake.cjk_page(30, 11) and not intake.cjk_page(16, 8) and not intake.cjk_page(7, 5)
    assert not intake.cjk_page(9, 9)                                           # under CJK_PROBE_MIN characters
