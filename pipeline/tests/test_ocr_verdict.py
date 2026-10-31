"""test_ocr_verdict.py: the OCR text verdict (review/ocr.py, review_ocr.py, the review page's OCR routes), on synthetic run
folders and a one-page synthetic PDF. No model, nothing sent.

    python -m pytest tests/test_ocr_verdict.py -q

What is tested: the checks on a verdict (the three verdicts, one line, limits, "|" and "](" refused, pages within the
book, a reason except for "sent to a language reader", "I read" for non-Latin pages); review.md's row wording for each
verdict (the first two as review_ocr.py always wrote them); the writer (history kept, via and session, every file written
whole, no reviews/ folder left behind) and its lock (review_ocr.py refused while another process holds reviews/.lock);
the OCR-only page's routes (page text served only for the section's own pages; a verdict recorded; Close); and Ctrl+C
during a verdict write waiting until it is written.
"""
import os, sys, json, time, signal, socket, threading, subprocess, urllib.request, urllib.error
import pytest
import pikepdf
from review import core, ocr as O, sessions as S
from lib import glance as G

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def intake(added=(1,), cjk=(), ocr_lang='eng', pages=3):
    return {'original': {'file': 'book.pdf', 'pages': pages}, 'settings': {'OCR_LANG': ocr_lang},
            'ocr': {'pages_with_ocr_text': list(added), 'per_page': [{'page': p, 'words': 12, 'tokens': 14} for p in added],
                    'junk': {str(p): {'share': 0.07, 'junk': 1, 'tokens': 14, 'examples': ['#']} for p in added}},
            'cjk_probe': {'cjk_pages': list(cjk), 'cjk_characters': {str(p): 40 for p in cjk}},
            'review': {'ocr_text_approved': None}}

def run_folder(tmp_path, it=None, pdf=True):
    R = tmp_path / 'run'; (R / '_intake').mkdir(parents=True)
    core.save(str(R / '_intake' / 'intake.json'), it or intake())
    if pdf:
        doc = pikepdf.new()
        font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica)
        for t in ('Page one: Kailua', 'Page two', 'Page three'):
            page = doc.add_blank_page(page_size=(300, 300))
            page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
            page.Contents = doc.make_stream(f'BT /F1 12 Tf 20 250 Td ({t}) Tj ET'.encode())
        doc.save(str(R / '_intake' / 'intake.pdf'))
    return str(R)

# ------------------------------------------------------------------ the checks
def test_the_three_verdicts_and_the_text_rules():
    it = intake()
    v = O.check({'verdict': 'Approved', 'reviewer': ' Kim ', 'reason': 'read\nagainst  the scan', 'pages': '1-2, 3'}, it, 3, '2026-10-31')
    assert v == {'verdict': 'approved', 'reviewer': 'Kim', 'date': '2026-10-31', 'reason': 'read against the scan', 'pages': '1-2, 3'}
    s = O.check({'verdict': 'sent to a language reader', 'reviewer': 'Kim', 'to': 'East Asia Library'}, it, 3, '2026-10-31')
    assert s == {'verdict': 'sent to a language reader', 'reviewer': 'Kim', 'date': '2026-10-31', 'to': 'East Asia Library'}   # no reason needed
    bad = [({'verdict': 'maybe', 'reviewer': 'K', 'reason': 'r'}, 'one of'),
           ({'verdict': 'approved', 'reviewer': '', 'reason': 'r'}, 'name is needed'),
           ({'verdict': 'not approved', 'reviewer': 'K'}, 'reason is needed'),
           ({'verdict': 'approved', 'reviewer': 'K', 'reason': 'a | b'}, '"|"'),
           ({'verdict': 'approved', 'reviewer': 'K|L', 'reason': 'r'}, '"|"'),
           ({'verdict': 'approved', 'reviewer': 'K', 'reason': '[x](javascript:alert(1))'}, r'"\]\("'),
           ({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r' * 1001}, 'at most 1000'),
           ({'verdict': 'approved', 'reviewer': 'K' * 81, 'reason': 'r'}, 'at most 80'),
           ({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r', 'pages': '2-1'}, 'goes up'),
           ({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r', 'pages': '4'}, 'pages 1 to 3'),
           ({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r', 'pages': 'p. 3'}, 'for example'),
           ({'verdict': 'sent to a language reader', 'reviewer': 'K', 'to': 'a|b'}, '"|"')]
    for fields, msg in bad:
        with pytest.raises(ValueError, match=msg): O.check(fields, it, 3, '2026-10-31')
    with pytest.raises(ValueError, match='YYYY-MM-DD'): O.check({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r'}, it, 3, '31/10/2026')

def test_non_latin_pages_need_i_read_to_approve():
    cjk = intake(added=(1, 2), cjk=(2,), ocr_lang='chi_tra+eng')
    lang = O.languages(cjk, [1, 2])
    assert lang == {'non_latin': True, 'names': ['Chinese (Traditional)'], 'label': 'Chinese (Traditional)'}
    with pytest.raises(ValueError, match='read Chinese'): O.check({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r'}, cjk, 3)
    ok = O.check({'verdict': 'approved', 'reviewer': 'K', 'reason': 'r', 'reads': ['Chinese (Traditional)']}, cjk, 3)
    assert ok['reads'] == ['Chinese (Traditional)']
    for v in ('not approved', 'sent to a language reader'):                      # always allowed
        assert O.check({'verdict': v, 'reviewer': 'K', 'reason': 'r'}, cjk, 3)['verdict'] == v
    han = intake(added=(1,), cjk=(1,), ocr_lang='eng')                           # Han found, no CJK language named: never guessed
    assert O.languages(han, [1])['label'] == 'the language of these pages'
    kana = {'ocr_layer_test': {'verdict': 'unusable', 'pages': [{'page': 3, 'script': 'kana'}]}, 'ocr': {}}
    assert O.languages(kana, [3])['names'] == ['Japanese']                       # kana is Japanese (team rule)
    assert not O.languages(intake(), [1])['non_latin']
    assert O.text_lang(cjk) == (None, 'it was read as more than one language') and O.text_lang(intake(ocr_lang='jpn'))[0] == 'ja'

def test_the_section_speaks_plainly(tmp_path):
    """The page is for library staff: language names, not OCR_LANG codes; no tool names or technical terms; "ex." for examples."""
    it = intake(added=(1, 2), cjk=(2,), ocr_lang='chi_tra+eng')
    it['ocr']['image_pages_without_text'] = [3]
    R = run_folder(tmp_path, it=it, pdf=False)
    s = O.section(R)
    assert s['what'] == ['During intake, OCR added text to 2 pages, read as Chinese (Traditional) and English.', 'PDF 3 is a picture with no text.']
    assert s['pages'][1]['findings'] == ['12 words read by OCR', '1 of 14 words and symbols look like junk (7%), ex. #', '40 Chinese, Japanese or Korean characters']
    text = json.dumps([s['what'], [p['findings'] for p in s['pages']], s['lang_why']])
    for word in ('OCR_LANG', 'chi_tra', 'tokens', 'CJK', 'layer', 'for example', 'PDFium', 'pdfplumber', 'Tesseract', '.json'):
        assert word not in text, word
    assert O.and_list([1, 5, 9]) == '1, 5 and 9'
    layer = {'verdict': 'unusable', 'median_cer': 1.6, 'scored': 9, 'sample': 10, 'diacritics': {'pages': [3]}}
    assert O.layer_words(layer) == ('The book came with its own OCR text. During intake it was compared with a new OCR reading on 9 of 10 sample pages: '
                                    'it looks unusable (almost none of its characters match). It is missing accent marks on letters (ex. ā, ō) that a new OCR reading found.')
    assert O.plain_reason({'reason': 'Tesseract model haw is not installed'}) == 'the OCR language needed to check it is not installed on this computer'
    assert O.plain_reason({'reason': 'only 128 characters in the OCR layer'}) == 'only 128 characters in its OCR text'

def test_row_wording_for_each_verdict():
    base = {'reviewer': 'Kim', 'date': '2026-10-31', 'reason': 'checked', 'pages': '1-3'}
    assert G.ocr_verdict_row(dict(base, verdict='approved')) == (True, 'approved by Kim on 2026-10-31 (pages 1-3): checked')
    assert G.ocr_verdict_row(dict(base, verdict='not approved')) == (False, 'not approved by Kim on 2026-10-31 (pages 1-3): checked')
    sent = {'verdict': 'sent to a language reader', 'reviewer': 'Kim', 'date': '2026-10-31', 'to': 'East Asia Library'}
    assert G.ocr_verdict_row(sent) == (False, 'sent to a language reader (East Asia Library) by Kim on 2026-10-31')
    import review_ocr
    assert review_ocr.row_text(dict(base, verdict='approved')) == '| OCR text reviewed by a person | OK | approved by Kim on 2026-10-31 (pages 1-3): checked |'
    assert review_ocr.row_text(None) is None

# ------------------------------------------------------------------ the writer and its lock
def test_record_keeps_history_and_leaves_nothing_behind(tmp_path):
    R = run_folder(tmp_path, pdf=False)
    v1, rec = O.record(R, {'verdict': 'not approved', 'reviewer': 'Kim', 'reason': 'garbled'}, via='page', session='002', date='2026-10-30')
    assert rec is None and v1['via'] == 'page' and v1['session'] == '002' and v1['recorded']
    v2, _ = O.record(R, {'verdict': 'approved', 'reviewer': 'Lee', 'reason': 'fixed upstream'}, via='review_ocr.py', date='2026-10-31')
    it = core.load(os.path.join(R, '_intake', 'intake.json'))
    assert it['review']['ocr_text_approved']['reviewer'] == 'Lee' and it['review']['history'][0]['reviewer'] == 'Kim'
    assert 'approved by Lee on 2026-10-31' in open(os.path.join(R, '_intake', 'intake.md'), encoding='utf-8').read()
    left = [n for d in (R, os.path.join(R, '_intake')) for n in os.listdir(d) if n.endswith('.tmp')]
    assert not left and not os.path.exists(os.path.join(R, 'reviews'))           # no temp files, no reviews/ made for nothing

def test_a_book_without_ocr_text_is_refused(tmp_path):
    R = run_folder(tmp_path, it=intake(added=()), pdf=False)
    with pytest.raises(ValueError, match='no OCR text to review'):
        O.record(R, {'verdict': 'approved', 'reviewer': 'K', 'reason': 'r'}, via='page')

def test_review_ocr_is_refused_while_a_review_page_holds_the_lock(tmp_path):
    R = run_folder(tmp_path, pdf=False)
    core.save(os.path.join(R, 'record.json'), {'intake': {}})                    # a finished run
    os.makedirs(os.path.join(R, 'reviews'))
    other = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', 'review_workorder.py'])   # a live review process
    try:
        json.dump({'pid': other.pid, 'since': '2026-10-31T10:00:00', 'what': 'reopen'}, open(os.path.join(R, 'reviews', '.lock'), 'w'))
        r = subprocess.run([sys.executable, 'review_ocr.py', R, '--verdict', 'approved', '--reviewer', 'K', '--reason', 'r'],
                           cwd=HERE, capture_output=True, text=True)
        assert r.returncode == 1 and 'refused: another review of this run is running' in r.stderr
        assert core.load(os.path.join(R, '_intake', 'intake.json'))['review']['ocr_text_approved'] is None   # nothing written
        with pytest.raises(S.Refused): O.record(R, {'verdict': 'approved', 'reviewer': 'K', 'reason': 'r'}, via='page')
    finally: other.kill(); other.wait()
    # the holder itself (held=True) records it
    O.record(R, {'verdict': 'not approved', 'reviewer': 'K', 'reason': 'r'}, via='page', held=True)
    assert core.load(os.path.join(R, '_intake', 'intake.json'))['review']['ocr_text_approved']['verdict'] == 'not approved'

# ------------------------------------------------------------------ the OCR-only page
def free_port():
    with socket.socket() as s: s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

def call(port, path, body=None):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()

def ocr_data(R):
    return {'mode': 'ocr', 'book': 'book.pdf', 'run': 'run', 'pages': 3, 'pdf': os.path.join(R, '_intake', 'intake.pdf'),
            'items': [], 'groups': {}, 'levels': [], 'add_kinds': {}, 'addable': {}, 'session': {'key': 'k:ocr', 'id': None}}

def test_ocr_only_page_serves_listed_pages_and_records(tmp_path):
    from review import server
    R = run_folder(tmp_path)
    port = free_port(); out = {}
    tmp = tmp_path / 'img'; tmp.mkdir()
    t = threading.Thread(target=lambda: out.update(v=server.serve(str(tmp), '2026-10-31', port, open_browser=False, run_dir=R,
                                                                   lock_held=True, data=ocr_data(R))), daemon=True)
    t.start(); time.sleep(0.8)
    st, b = call(port, '/')
    assert st == 200 and b'"mode": "ocr"' in b and b'"pages": [{"page": 1' in b
    st, b = call(port, '/ocr/text/1.json')
    assert st == 200 and json.loads(b)['text'] == 'Page one: Kailua'
    for p in ('/ocr/text/2.json', '/ocr/text/-1.json', '/ocr/text/..%2f1.json', '/ocr/text/%2e%2e/1.json', '/ocr/text/1'):
        assert call(port, p)[0] == 404, p                                       # only the section's own pages
    assert call(port, '/save', {})[0] == 404                                     # no decisions in OCR-only mode
    st, b = call(port, '/ocr-verdict', {'verdict': 'approved', 'reviewer': 'Kim', 'reason': 'a | b'})
    assert st == 400 and '"|"' in json.loads(b)['error']
    st, b = call(port, '/ocr-verdict', {'verdict': 'approved', 'reviewer': 'Kim', 'reason': 'checked against the scan', 'pages': '1'})
    got = json.loads(b)
    assert st == 200 and got['recorded']['via'] == 'page' and 'session' not in got['recorded'] and got['ocr']['current']['verdict'] == 'approved'
    assert call(port, '/close', {})[0] == 200
    t.join(5)
    assert not t.is_alive()
    assert core.load(os.path.join(R, '_intake', 'intake.json'))['review']['ocr_text_approved']['reason'] == 'checked against the scan'

SLOW_WRITE = r'''
import sys, time
sys.path.insert(0, sys.argv[1])
from review import ocr as O, server
real = O.write
def slow(*a, **k):
    print('writing', flush=True); time.sleep(2); real(*a, **k); print('written', flush=True)
O.write = slow
R = sys.argv[2]
data = {'mode': 'ocr', 'book': 'b', 'run': 'r', 'pages': 3, 'pdf': R + '/_intake/intake.pdf', 'items': [], 'groups': {}, 'levels': [],
        'add_kinds': {}, 'addable': {}, 'session': {'key': 'k', 'id': None}}
server.serve(sys.argv[3], '2026-10-31', int(sys.argv[4]), open_browser=False, run_dir=R, lock_held=True, data=data)
print('ended', flush=True)
'''

def test_ctrl_c_during_a_verdict_write_waits_for_it(tmp_path):
    R = run_folder(tmp_path)
    port = free_port(); img = tmp_path / 'img'; img.mkdir()
    p = subprocess.Popen([sys.executable, '-c', SLOW_WRITE, HERE, R, str(img), str(port)], stdout=subprocess.PIPE, text=True)
    try:
        assert 'review page:' in p.stdout.readline()
        res = {}
        th = threading.Thread(target=lambda: res.update(r=call(port, '/ocr-verdict', {'verdict': 'not approved', 'reviewer': 'Kim', 'reason': 'garbled'})))
        th.start()
        lines = [p.stdout.readline() for _ in range(1)]                       # skip the page's second line
        while 'writing' not in lines[-1]: lines.append(p.stdout.readline())
        p.send_signal(signal.SIGINT)                                           # Ctrl+C in the middle of the write
        th.join(10); rest = p.communicate(timeout=15)[0]
        assert res['r'][0] == 200
        assert rest.index('written') < rest.index('stopped: the OCR review page is closed.') < rest.index('ended')
        assert core.load(os.path.join(R, '_intake', 'intake.json'))['review']['ocr_text_approved']['reason'] == 'garbled'
    finally:
        if p.poll() is None: p.kill()

SLOW_CHECK = SLOW_WRITE.replace('real = O.write', 'real_section = O.section\ndef slow_section(*a, **k):\n'
                                '    print("checking", flush=True); time.sleep(2); return real_section(*a, **k)\nO.section = slow_section\nreal = O.write')

def test_ctrl_c_before_a_verdict_reaches_its_lock_waits_too(tmp_path):
    """Review 07 L2: a Ctrl+C that comes while the request is still being checked (before the write lock) waits for it too."""
    R = run_folder(tmp_path)
    port = free_port(); img = tmp_path / 'img'; img.mkdir()
    p = subprocess.Popen([sys.executable, '-c', SLOW_CHECK, HERE, R, str(img), str(port)], stdout=subprocess.PIPE, text=True)
    try:
        assert 'review page:' in p.stdout.readline()
        res = {}
        th = threading.Thread(target=lambda: res.update(r=call(port, '/ocr-verdict', {'verdict': 'not approved', 'reviewer': 'Kim', 'reason': 'garbled'})))
        th.start()
        lines = [p.stdout.readline()]
        while 'checking' not in lines[-1]: lines.append(p.stdout.readline())
        p.send_signal(signal.SIGINT)                                           # Ctrl+C before the handler has taken the write lock
        th.join(15); rest = p.communicate(timeout=20)[0]
        assert res['r'][0] == 200
        assert rest.index('written') < rest.index('stopped: the OCR review page is closed.') < rest.index('ended')
        assert core.load(os.path.join(R, '_intake', 'intake.json'))['review']['ocr_text_approved']['reason'] == 'garbled'
    finally:
        if p.poll() is None: p.kill()

def test_finish_ocr_review_records_closes_and_leaves_no_reviews_folder(tmp_path):
    """review_ocr.py --serve on a finished run never pinned: Finish OCR Review (close: true) records the verdict, dated the
    day it is recorded, the page closes, and no empty reviews/ stays (review 07 L3). --date with --serve is refused
    (review 10 L4): a page verdict always takes the day it is recorded."""
    import datetime
    R = run_folder(tmp_path)
    core.save(os.path.join(R, 'record.json'), {'document': {'file': 'book.pdf', 'pages': 3}, 'intake': {}})
    r = subprocess.run([sys.executable, 'review_ocr.py', R, '--serve', '--no-browser', '--date', '2020-01-01'], cwd=HERE, capture_output=True, text=True)
    assert r.returncode == 1 and 'leave out --date' in r.stderr and not os.path.exists(os.path.join(R, 'reviews'))
    port = free_port()
    p = subprocess.Popen([sys.executable, 'review_ocr.py', R, '--serve', '--no-browser', '--port', str(port)],
                         cwd=HERE, stdout=subprocess.PIPE, text=True)
    try:
        assert 'review page:' in p.stdout.readline()
        assert os.path.exists(os.path.join(R, 'reviews', '.lock'))             # held while the page is open
        st, b = call(port, '/ocr-verdict', {'verdict': 'not approved', 'reviewer': 'Kim', 'reason': 'garbled', 'close': True})
        got = json.loads(b)
        assert st == 200 and got['closed'] is True and got['recorded']['date'] == datetime.date.today().isoformat()
        out = p.communicate(timeout=20)[0]
        assert p.returncode == 0 and 'closed: the OCR review page is closed' in out
        assert not os.path.exists(os.path.join(R, 'reviews'))
        assert core.load(os.path.join(R, 'record.json'))['intake']['review']['ocr_text_approved']['verdict'] == 'not approved'
    finally:
        if p.poll() is None: p.kill()
