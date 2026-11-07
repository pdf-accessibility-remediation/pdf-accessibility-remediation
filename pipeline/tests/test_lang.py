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
@pytest.mark.parametrize('sc,osd,viet,want,han_only', [
    (C(latin=500), C(), 0, 'eng', False), (C(), C(Latin=3), 0, 'eng', False),
    (C(kana=40, han=200), C(), 0, 'jpn+eng', False), (C(), C(Japanese=2), 0, 'jpn+eng', False),
    (C(hangul=80), C(), 0, 'kor+eng', False), (C(), C(Korean=1), 0, 'kor+eng', False),
    (C(han=300, latin=50), C(), 0, None, True), (C(), C(HanT=4), 0, None, True),     # Chinese or Japanese: never guessed
    (C(kana=5, hangul=5), C(), 0, None, False), (C(latin=900), C(), 120, 'vie+eng', False)])
def test_the_suggestion(sc, osd, viet, want, han_only):
    found = C({intake.OSD_SCRIPTS.get(s, s): n for s, n in osd.items()})
    r = intake.suggest_language(sc, viet, osd, found, 5)
    assert r['suggestion'] == want and r['han_only'] is han_only

def lj(R, **kw):
    (R / '_intake').mkdir(parents=True, exist_ok=True)
    (R / '_intake' / 'languages.json').write_text(json.dumps({'needs_ocr': True, 'pages_to_ocr': 3, 'suggestion': None, 'han_only': False, 'evidence': {}, **kw}))

def test_the_question_and_its_words(setup, monkeypatch):
    monkeypatch.setattr(BK, 'installed_langs', lambda s: ['eng', 'jpn', 'kor', 'chi_tra', 'chi_sim'])
    s = settings(setup); R = setup / 'runs' / 'bk' / 'r1'
    R.mkdir(parents=True)
    assert LG.question(s, str(R)) is None and not LG.asks(str(R))
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

@pytest.mark.skipif(not shutil.which('tesseract'), reason='Tesseract is needed for the script detection')
def test_run_api_stops_for_the_language_before_any_ocr(tmp_path):
    """ASK_LANG=1 with no OCR_LANG: intake.py --languages, then exit 4 before the full intake when pages need OCR."""
    from PIL import Image
    import pikepdf
    img = tmp_path / 'scan.png'; Image.new('L', (1240, 1754), 255).save(img)
    pdf = tmp_path / 'scan.pdf'
    Image.open(img).convert('RGB').save(pdf, 'PDF', resolution=150)
    env = dict(os.environ, ASK_LANG='1', ESTIMATE='1', RUNS_DIR=str(tmp_path / 'runs'), VERAPDF='off')
    env.pop('OCR_LANG', None)
    r = subprocess.run(['bash', 'run_api.sh', str(pdf), 'scan', 'l1'], cwd=HERE, env=env, capture_output=True, text=True, timeout=300)
    R = tmp_path / 'runs' / 'scan' / 'l1'
    assert r.returncode == 4, r.stdout + r.stderr
    d = json.load(open(R / '_intake' / 'languages.json'))
    assert d['needs_ocr'] and d['pages_to_ocr'] == 1 and not (R / '_intake' / 'intake.json').exists()
