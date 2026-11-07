"""test_lang.py: "Language of the Scanned Pages" (#45 D4, part 1 of #37): intake.py's suggestion (suggest_language, the
--languages pass), the question and its plain-words evidence (webapp/lang.py), the answer for a single run and for a PDF in
a batch, and run_api.sh's ASK_LANG stop. No model.

    python -m pytest tests/test_lang.py -q
"""
import os, sys, json, shutil, subprocess, collections
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
import intake  # noqa: E402
from webapp import lang as LG, books as BK, newrun as NR, batches as BT, jobs  # noqa: E402
from test_webapp import setup, settings  # noqa: E402,F401
from test_webapp_home import pdf_bytes  # noqa: E402

C = collections.Counter
def pg(script, conf=10.0): return {'page': 1, 'script': script, 'orient_conf': conf, 'script_conf': 1.0}
@pytest.mark.parametrize('sc,pages,viet,others,want,ask,found', [
    (C(latin=500), [], 0, None, 'eng', False, 'latin'),                          # Latin script only: no question
    (C(), [pg('Latin')], 0, None, 'eng', False, 'latin'),
    (C(), [pg(None, None)], 0, None, 'eng', False, 'none'),                       # no text found (a cover): no question
    (C(latin=500), [pg('Cyrillic', 1.21)], 0, None, 'eng', False, 'latin'),      # a picture read as "Cyrillic": no text
    (C(kana=40, han=200), [], 0, None, 'jpn+eng', True, 'cjk'), (C(), [pg('Japanese')], 0, None, 'jpn+eng', True, 'cjk'),
    (C(hangul=80), [], 0, None, 'kor+eng', True, 'cjk'), (C(), [pg('Korean', 12.76)], 0, None, 'kor+eng', True, 'cjk'),
    (C(han=300, latin=50), [], 0, None, None, True, 'cjk'), (C(), [pg('HanT')], 0, None, None, True, 'cjk'),   # never guessed
    (C(kana=5, hangul=5), [], 0, None, None, True, 'mixed'), (C(latin=900), [], 120, None, 'vie+eng', True, 'vietnamese'),
    (C(latin=900), [pg('Cyrillic')], 0, None, 'eng', True, 'other'),             # another script: asked, English preselected
    (C(), [pg(None)], 0, None, None, True, 'unknown'),                            # text whose script couldn't be told: asked
    (C(latin=2000), [], 0, C(GREEK=60), 'eng', False, 'latin'),                  # a math book's Greek letters (under 5%)
    (C(latin=500), [], 0, C(CYRILLIC=400), 'eng', True, 'other'),                # Russian text: asked
    (C(han=2, latin=500), [], 0, None, 'eng', False, 'latin')])                  # a stray Chinese character
def test_the_suggestion(sc, pages, viet, others, want, ask, found):
    r = intake.suggest_language(sc, viet, pages, others)
    assert (r['suggestion'], r['ask'], r['found']) == (want, ask, found)

def test_ipa_letters_are_latin():
    assert not intake.other_letters('ɛ ŋ ʔ ā ʻ') and intake.other_letters('Москва')['CYRILLIC'] == 6

def test_no_question_when_the_language_does_not_matter(setup):
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'
    lj(R, ask=False, found='none', suggestion='eng')
    j = jobs.create(s['jobs'], 'estimate', 'bk/r1', ['true'], {}, R=str(R)); jobs.update(s['jobs'], j['id'], status='failed', exit=4)
    assert not LG.asks(str(R)) and LG.question(s, str(R)) is None

def lj(R, **kw):
    (R / '_intake').mkdir(parents=True, exist_ok=True)
    (R / '_intake' / 'languages.json').write_text(json.dumps({'needs_ocr': True, 'pages_to_ocr': 3, 'suggestion': None, 'han_only': False, 'evidence': {}, **kw}))

def test_the_question_and_its_words(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'jpn', 'kor', 'chi_tra', 'chi_sim'])
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'
    R.mkdir(parents=True)
    assert LG.question(s, str(R)) is None and not LG.asks(str(R))
    j = jobs.create(s['jobs'], 'estimate', 'bk/r1', ['true'], {}, R=str(R)); jobs.update(s['jobs'], j['id'], status='failed', exit=4)   # stopped to ask
    lj(R, suggestion='jpn+eng', evidence={'text_layer': {'kana': 1234, 'han': 20}, 'sampled_scans': 3, 'scan_scripts': {'Japanese': 2, 'Latin': 1}})
    q = LG.question(s, str(R))
    assert LG.asks(str(R)) and q['kind'] == 'first' and q['suggested'] == 'jpn+eng' and q['pages'] == 3
    assert "The PDF's text holds 1,234 Japanese kana characters." in q['evidence']
    assert 'Of the 3 scanned pages checked, 2 look like Japanese; 1 looks like Latin script.' in q['evidence']
    lj(R, han_only=True, evidence={'text_layer': {'han': 50}})
    q = LG.question(s, str(R))
    assert q['suggested'] is None and any('never' in x or "isn't chosen for you" in x for x in q['evidence'])
    lj(R, suggestion='vie+eng')                                              # not installed here: nothing preselected
    assert LG.question(s, str(R))['suggested'] is None
    (R / '_intake' / 'intake.json').write_text(json.dumps({'status': 'stopped', 'flags': [{'what': 'OCR language needed', 'pages': [4, 9]}]}))
    q = LG.question(s, str(R))
    assert q['kind'] == 'cjk' and q['suggested'] is None and all(any(x in c[0] for x in LG.CJK) for c in q['choices'])
    assert q['evidence'][0].startswith('Chinese, Japanese or Korean text was found on pages 4, 9')
    (R / '_intake' / 'intake.json').write_text(json.dumps({'status': 'done', 'flags': []}))
    assert LG.question(s, str(R)) is None and not LG.asks(str(R))

def test_an_answer_starts_the_estimate_again(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'jpn'])
    s = settings(setup)
    (setup / 'uploads' / 'bk.pdf').write_bytes(pdf_bytes(1, 'A Book'))
    key = BK.listing(s)[0]['key']
    j = NR.start_estimate(s, [], key, 'First')
    assert j['env_set'] == {'ESTIMATE': '1', 'ASK_LANG': '1'}
    R = setup / 'runs' / 'bk' / 'First'; jobs.update(s['jobs'], j['id'], status='failed', exit=4)
    lj(R, suggestion='eng')
    with pytest.raises(ValueError, match='Choose a language'): NR.answer_language(s, 'bk/First', str(R), 'xx')
    a = NR.answer_language(s, 'bk/First', str(R), 'eng')
    assert a['env_set'] == {'ESTIMATE': '1'} and a['ocr_name'] == 'English'                # English: as before this question
    jobs.update(s['jobs'], a['id'], status='done')
    assert LG.question(s, str(R)) is None                                       # answered: not asked again
    jobs.update(s['jobs'], a['id'], status='failed', exit=4)                    # (as if it had stopped to ask once more)
    b = NR.answer_language(s, 'bk/First', str(R), 'jpn+eng')
    assert b['env_set'] == {'ESTIMATE': '1', 'OCR_LANG': 'jpn+eng'}
    jobs.update(s['jobs'], b['id'], status='done')
    assert NR.again_estimate(s, 'bk/First', str(R))['env_set'] == {'ESTIMATE': '1', 'OCR_LANG': 'jpn+eng'}   # never asked again

def test_a_batch_pdf_is_asked_on_its_row(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'kor'])
    s = settings(setup)
    for n in ('a', 'b'): (setup / 'uploads' / f'{n}.pdf').write_bytes(pdf_bytes(1, f'Book {n}'))
    js = BT.start(s, [], [b['key'] for b in BK.listing(s)], 'Spring')
    for j in js: jobs.update(s['jobs'], j['id'], status='failed', exit=4)
    B = setup / 'runs' / 'batches' / 'Spring'
    lj(B / 'a', suggestion='kor+eng'); lj(B / 'b', suggestion='eng')
    st = BT.state(s, 'Spring')
    assert st['phase'] == 'language' and sorted(st['asking']) == ['a', 'b']
    assert {b['name']: b['status'] for b in st['books']} == {'a': 'Waiting for a Language', 'b': 'Waiting for a Language'}
    j = BT.answer_language(s, 'Spring', 'a', 'kor+eng')
    assert j['env_set'] == {'ESTIMATE': '1', 'OCR_LANG': 'kor+eng', 'RUN_DIR': str(B / 'a')}
    BT.answer_language(s, 'Spring', 'b', 'eng')
    assert [l for l in (B / 'ocr_langs.tsv').read_text().splitlines() if not l.startswith('#')] == ['a\tkor+eng']   # English: unset
    assert json.load(open(BT.meta_path(s, 'Spring')))['langs'] == {'a': 'kor+eng', 'b': 'eng'}
    with pytest.raises(ValueError, match='no such PDF'): BT.answer_language(s, 'Spring', 'zz', 'eng')

KOREAN_FONT = '/System/Library/Fonts/AppleSDGothicNeo.ttc'

def scan_pdf(tmp_path, text=None):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGB', (1240, 1754), 'white')
    if text:
        d = ImageDraw.Draw(im); f = ImageFont.truetype(KOREAN_FONT, 48)
        for k in range(14): d.text((100, 120 + k * 100), text, fill='black', font=f)
    pdf = tmp_path / 'scan.pdf'; im.save(pdf, 'PDF', resolution=150)
    return pdf

def run_api(tmp_path, pdf):
    env = dict(os.environ, ASK_LANG='1', ESTIMATE='1', RUNS_DIR=str(tmp_path / 'runs'), VERAPDF='off')
    env.pop('OCR_LANG', None)
    r = subprocess.run(['bash', 'run_api.sh', str(pdf), 'scan', 'l1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=300)
    return r, tmp_path / 'runs' / 'scan' / 'l1'

@pytest.mark.skipif(not shutil.which('tesseract') or not os.path.exists(KOREAN_FONT), reason='Tesseract and a Korean font are needed')
def test_run_api_stops_for_the_language_before_any_ocr(tmp_path):
    """ASK_LANG=1 with no OCR_LANG: intake.py --languages, then exit 4 before the full intake when the language matters."""
    r, R = run_api(tmp_path, scan_pdf(tmp_path, '한국어 문서의 내용입니다 대한민국'))
    assert r.returncode == 4, r.stdout + r.stderr
    d = json.load(open(R / '_intake' / 'languages.json'))
    assert d['needs_ocr'] and d['ask'] and d['suggestion'] == 'kor+eng' and not (R / '_intake' / 'intake.json').exists()

@pytest.mark.skipif(not shutil.which('tesseract'), reason='Tesseract is needed for the script detection')
def test_run_api_goes_on_when_the_scans_hold_no_text(tmp_path):
    """Patrick, 2026-11-07: a page with no text to read (a cover) doesn't ask; the run goes on as before."""
    r, R = run_api(tmp_path, scan_pdf(tmp_path))
    d = json.load(open(R / '_intake' / 'languages.json'))
    assert d['needs_ocr'] and not d['ask'] and d['found'] == 'none' and r.returncode != 4
