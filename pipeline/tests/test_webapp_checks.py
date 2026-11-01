"""test_webapp_checks.py: the Manual Checks page and its routes (issue #38, stage 2): webapp/manualpage.py, the routes in
webapp/server.py, the strip, review/manual.py's drafts. An app on a temporary runs folder with a synthetic finished run at
batches/d1/clans (a run path of several segments) and a one-page synthetic PDF. No book, no model.

    python -m pytest tests/test_webapp_checks.py -q
"""
import os, re, sys, json, html, time, signal, threading, subprocess, http.client
import pytest
import pikepdf

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from webapp import manualpage as MP, server as W  # noqa: E402
from review import core, manual as M, sessions as S  # noqa: E402
from lib import release as REL, runlock, langtag  # noqa: E402
from test_webapp import setup, wait, free_port  # noqa: E402,F401  (fixtures)

RUN = 'batches/d1/clans'
CARD = '<section class="ship" aria-labelledby="ship-h"><h2 id="ship-h">Ready to Ship? No</h2><ul role="list"><li>x</li></ul></section>'
PAC = {'by': 'Kim', 'fields': {'pages_checked': '1'}, 'items': {k: {'result': 'pass'} for k in
       ('pac_wcag', 'title_language', 'spot_check', 'colour', 'contrast', 'images_of_text', 'needs_person')}}

def make_run(R, title='The Clan Records', record_sha=False):
    os.makedirs(R, exist_ok=True)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(300, 300)); doc.save(os.path.join(R, 'clans_remediated.pdf'))
    rec = {'document': {'file': 'clans.pdf', 'output': 'clans_remediated.pdf', 'pages': 1},
           'verify': {'doc': {'title': title, 'lang': 'en-US'}, 'tree': {'types': {'Table': 2}}}}
    if record_sha: rec['document']['output_sha256'] = REL.sha_file(os.path.join(R, 'clans_remediated.pdf'))
    core.save(os.path.join(R, 'record.json'), rec)
    open(os.path.join(R, 'review.md'), 'w').write('# Remediation Review: clans.pdf\n')
    open(os.path.join(R, 'review.html'), 'w').write(f'<!doctype html><html><head><title>r</title></head><body><header><h1>Review</h1></header>{CARD}<p>rest</p></body></html>')
    return R

@pytest.fixture
def mapp(setup):
    t = setup; R = make_run(str(t / 'runs' / 'batches' / 'd1' / 'clans'))
    open(t / 'runs' / 'batches' / 'd1' / 'summary.html', 'w').write('<p>batch</p>')
    port = json.loads((t / 'app.json').read_text())['port']
    env = {k: v for k, v in os.environ.items() if k != 'VERAPDF'}
    p = subprocess.Popen([sys.executable, 'app.py', '--config', str(t / 'app.json'), '--no-browser'], cwd=HERE, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ok = wait(lambda: p.poll() is not None or req(port, 'GET', '/api/ping')[0] == 200, 60)
    if p.poll() is not None or not ok: pytest.fail(p.stdout.read())
    yield {'port': port, 'R': R, 't': t}
    p.send_signal(signal.SIGINT)
    try: p.wait(timeout=10)
    except subprocess.TimeoutExpired: p.kill()

def req(port, method, path, body=None, raw=None, length=None, ctype='application/json'):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=15)
    try:
        data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None)
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        c.putheader('Host', f'127.0.0.1:{port}')
        if data is not None or length is not None:
            c.putheader('Content-Type', ctype); c.putheader('Content-Length', str(len(data or b'')) if length is None else length)
        c.endheaders(data)
        r = c.getresponse(); return r.status, r.read(), dict(r.getheaders())
    except OSError: return None, b'', {}
    finally: c.close()

def js(port, method, path, body=None):
    st, b, _ = req(port, method, path, body); return st, json.loads(b or b'{}')

def visible(page):
    """The page's text as a person sees it: no tags, no JSON data block."""
    page = re.sub(r'<script[^>]*>.*?</script>', '', page, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', page)

# ------------------------------------------------------------------ serving
def test_the_page_is_served_with_the_csp_and_names_no_file(mapp):
    st, b, h = req(mapp['port'], 'GET', f'/run/{RUN}/checks'); page = b.decode()
    assert st == 200 and h['Content-Security-Policy'] == "frame-ancestors 'none'; script-src 'self'"   # no inline script
    assert '<script type="application/json" id="mc-data">' in page and '<script src="/app/manual.js" defer></script>' in page
    text = visible(page)
    assert 'The Clan Records' in text and 'Language: English' in text                 # the remediated PDF's title (Q2, F8)
    for bad in ('.pdf', 'review.md', 'release/', 'sha256', 'batches/d1', 'clans_remediated'): assert bad not in text, bad
    assert 'href="#pac"' not in page and 'href="#screen-reader"' not in page          # the two section links went (2026-10-31)
    assert 'WCAG 1.4.3' in text                                                         # the WCAG numbers stay (Q1)
    assert req(mapp['port'], 'GET', '/app/manual.js')[0] == 200

def test_the_name_falls_back_to_the_original_without_pdf(tmp_path):
    R = make_run(str(tmp_path / 'r'), title='')
    assert MP.book(core.load(os.path.join(R, 'record.json')))['title'] == 'clans'

@pytest.mark.parametrize('path,code', [(f'/run/{RUN}/release', 404), (f'/run/{RUN}/screen-reader', 404), (f'/run/{RUN}/ocr', 404),
                                       ('/run/batches/d1/nope/checks', 404)])
def test_the_old_reserved_pages_are_gone(mapp, path, code):
    assert req(mapp['port'], 'GET', path)[0] == code

def test_the_strip_follows_the_card_and_never_on_a_previous_result():
    page = W.with_panel(f'<html><head></head><body><header><h1>R</h1></header>{CARD}<p>rest</p></body></html>', RUN)
    assert page.index(CARD) + len(CARD) == page.index('\n<div id="pdfrem-checks"')
    assert 'pdfrem-checks' not in W.with_panel('<html><head></head><body><header></header><p>no card</p></body></html>', RUN)   # panel.js: in the panel
    assert 'pdfrem-checks' not in W.with_version(f'<html><head></head><body><header></header>{CARD}</body></html>', RUN, '001')

# ------------------------------------------------------------------ state, F1, F10
def test_a_run_with_no_recorded_hash_is_never_called_changed(mapp):
    st, s = js(mapp['port'], 'GET', f'/api/run/{RUN}/checks')
    assert st == 200 and s['disk']['same'] is None and s['refusal'] is None and s['sections']['pac']['current'] is None
    st, s = js(mapp['port'], 'GET', f'/api/run/{RUN}')
    assert s['manual']['disk_same'] is None and s['manual']['refusal'] is None and s['manual']['sections']['pac']['words'] == 'not completed'
    st, r = js(mapp['port'], 'POST', f'/api/run/{RUN}/checks/record', {'section': 'pac', 'data': PAC, 'shown_sha256': s.get('sha')})
    assert st == 200                                                                    # F1: the first Record takes the disk hash
    rec = core.load(os.path.join(mapp['R'], 'record.json'))
    assert rec['document']['output_sha256_from'].startswith('first check') and rec['manual_checks']['pac']['state'] == 'completed'
    st, s = js(mapp['port'], 'GET', f'/api/run/{RUN}')
    assert s['manual']['disk_same'] is True and s['manual']['sections']['pac']['ok'] is True

def test_a_changed_pdf_is_said_in_plain_words(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    with open(os.path.join(R, 'clans_remediated.pdf'), 'ab') as f: f.write(b'\n% edited by hand\n')
    s = MP.strip(R, core.load(os.path.join(R, 'record.json')))
    assert s['disk_same'] is False and s['refusal'] == MP.CHANGED_BY_HAND

def test_the_strip_says_the_live_status_when_the_card_is_older(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True); rec = core.load(os.path.join(R, 'record.json'))
    rec['glance'] = {'schema': 'glance/0.4', 'ship': [], 'status': {'text': 'Ready', 'newer': None}}
    s = MP.strip(R, rec)
    assert s['card_status'] == 'Ready' and s['status'] == 'Not Ready'                   # F10: the strip carries both

# ------------------------------------------------------------------ drafts, F2, F3
def test_drafts_newer_wins_and_a_late_one_after_record_is_refused(mapp):
    port, path = mapp['port'], f'/api/run/{RUN}/checks/draft'
    st, s = js(port, 'GET', f'/api/run/{RUN}/checks'); sha = s['sha']
    half = {'by': 'Kim', 'items': {'contrast': {'result': 'fail', 'note': 'p. 3'}}}
    assert js(port, 'POST', path, {'section': 'pac', 'data': half, 'saved_at': '2026-11-01T10:00:02.000Z', 'for_sha256': sha})[0] == 200
    st, r = js(port, 'POST', path, {'section': 'pac', 'data': {'by': 'Old'}, 'saved_at': '2026-11-01T10:00:01.000Z', 'for_sha256': sha})
    assert st == 409 and r['error'] == M.STALE                                          # two tabs: the newer one stays
    st, s = js(port, 'GET', f'/api/run/{RUN}/checks')
    assert s['sections']['pac']['draft']['data']['items']['contrast'] == {'result': 'fail', 'note': 'p. 3'}
    st, r = js(port, 'POST', path, {'section': 'pac', 'data': {'by': 'K' * 81}, 'saved_at': '2026-11-01T10:00:03.000Z', 'for_sha256': sha})
    assert st == 400 and r['errors'][0]['field'] == 'by'
    st, r = js(port, 'POST', f'/api/run/{RUN}/checks/record', {'section': 'pac', 'data': PAC, 'shown_sha256': sha,
                                                               'draft_saved_at': '2026-11-01T10:00:04.000Z'})
    assert st == 200
    st, r = js(port, 'POST', path, {'section': 'pac', 'data': half, 'saved_at': '2026-11-01T10:00:03.500Z', 'for_sha256': sha})
    assert st == 409                                                                    # F2: handled late, posted before Record
    st, s = js(port, 'GET', f'/api/run/{RUN}/checks')
    assert s['sections']['pac']['draft'] is None and s['sections']['pac']['current']['by'] == 'Kim'

def test_a_draft_from_an_earlier_version_is_offered_as_notes_only(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    M.save_draft(R, 'pac', {'by': 'Kim', 'items': {'contrast': {'result': 'fail', 'note': 'p. 3'}}}, '2026-11-01T10:00:00Z', 'f' * 64, wait=1)
    st = MP.state(R, 'r')
    assert st['sections']['pac']['draft'] is None and st['sections']['pac']['draft_earlier']['data']['by'] == 'Kim'

def test_a_failed_draft_clear_keeps_the_check(tmp_path, monkeypatch):
    R = make_run(str(tmp_path / 'r'))
    def boom(*a): raise OSError('disk full')
    monkeypatch.setattr(M, '_clear_draft', boom)
    said = []
    c = M.record(R, 'pac', PAC, say=said.append, batch=False)                           # F2: the check stands
    assert REL.load(R)['checks']['pac'][0]['id'] == c['id']
    assert any('draft was not cleared' in x for x in said)                             # and says so ...
    src = open(os.path.join(HERE, 'webapp', 'server.py'), encoding='utf-8').read()     # ... which the app writes to server.log (G3)
    assert "say=lambda *a: applog(" in src and "with open(os.path.join(J, 'server.log'), 'a'" in src

def test_a_save_refused_after_record_raises_no_alert():
    js_src = open(os.path.join(HERE, 'webapp', 'manual.js'), encoding='utf-8').read()   # G5: no alert while leaving or recording
    assert js_src.count('if (!leaving && !sec.recording) alarm(') == 2
    assert 'sec.recording = true;' in js_src and 'sec.recording = false;' in js_src

def test_the_session_hash_refusal_shows_before_the_form_is_filled(tmp_path):
    R = make_run(str(tmp_path / 'r'))                                                   # no recorded hash yet (F1)
    rec = S.load(os.path.join(R, 'record.json')); rec['review'] = {'session': '001'}; core.save(os.path.join(R, 'record.json'), rec)
    os.makedirs(os.path.join(R, 'reviews', 'sessions'))
    core.save(os.path.join(R, 'reviews', 'sessions', '001.json'), {'id': '001', 'status': 'applied', 'version': {'id': '001', 'pdf_sha256': '0' * 64}})
    st = MP.state(R, 'r')
    assert st['refusal'] == M.NOT_LAST_REVIEW                                           # G6: shown at once, as Record would refuse
    with pytest.raises(S.Refused, match='last review'): M.record(R, 'pac', PAC, say=lambda *a: None, batch=False)
    core.save(os.path.join(R, 'reviews', 'sessions', '001.json'), {'id': '001', 'status': 'applied',
              'version': {'id': '001', 'pdf_sha256': REL.sha_file(os.path.join(R, 'clans_remediated.pdf'))}})
    assert MP.state(R, 'r')['refusal'] is None                                          # the same file: no refusal

def test_a_note_holding_a_script_end_tag_stays_text(tmp_path):
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    evil = '</script><a href="https://example.com">x</a> & <b>'
    M.record(R, 'pac', dict(PAC, items=dict(PAC['items'], contrast={'result': 'fail', 'note': evil})), say=lambda *a: None, batch=False)
    M.record(R, 'pac', dict(PAC, items=dict(PAC['items'], contrast={'result': 'pass', 'note': 'fixed'})), say=lambda *a: None, batch=False)
    page = MP.page(R, 'r')                                                              # the first check is earlier: its notes are in the JSON block
    block = re.search(r'id="mc-data">(.*?)</script>', page, flags=re.S).group(1)
    assert page.count('</script>') == 2 and '\\u003c/script\\u003e' in block and '&' not in block   # F3: <, > and & escaped
    assert '<a href="https://example.com">' not in page                              # the earlier check's table escapes it too
    assert json.loads(block)['sections']['pac']['starts'][0]['items']['contrast']['note'] == evil   # and it round-trips as text

def test_the_page_in_the_words_decided_after_try_rv1(tmp_path):
    """13 §6: the names, the status line with what is unsatisfied, no PAC Version or PDF/UA item, no NVDA example, Pages
    optional, an h3 over the earlier results (G2), and the message after a Record, with Review Again after any Fail."""
    R = make_run(str(tmp_path / 'r'), record_sha=True)
    page = MP.page(R, 'r'); text = re.sub(r'\s+', ' ', visible(page))
    assert '<h1>Accessibility Evaluation</h1>' in page and 'PDF Title: ' in text and '<title>Accessibility Evaluation: The Clan Records</title>' in page
    assert 'Overall Status: Not Ready · Unsatisfied Requirements: Work Order Approval, Safety Checks, Accessibility Evaluation' in text
    assert '>PAC 2026</h2>' in page and '>Screen-Reader Test</h2>' in page and 'Manual Check' not in text and 'Sanity' not in text
    assert 'PAC Version' not in text and 'PDF/UA' not in text and 'For example NVDA' not in text and 'Pages Checked (optional)' in text
    assert 'Record the PAC 2026 Results' in text and 'Record the Screen-Reader Test Results' in text
    M.record(R, 'pac', dict(PAC, items=dict(PAC['items'], contrast={'result': 'fail', 'note': 'grey on grey'})), say=lambda *a: None, batch=False)
    M.record(R, 'pac', dict(PAC, items=dict(PAC['items'], contrast={'result': 'pass', 'note': 'darkened'})), say=lambda *a: None, batch=False)
    page = html.unescape(MP.page(R, 'r', recorded='pac'))
    assert ('PAC 2026 results recorded for this version. "Accessibility Evaluation" is satisfied once the Screen-Reader Test is recorded '
            'for this version too.') in page and 'id="mc-review"' not in page
    assert '<h3>Earlier Results (1)</h3><details class="mc-earlier"><summary>Show the 1 Earlier Result</summary><h4>' in page
    assert 'Current Results: Kim, ' in page and '<h3>Record New Results</h3>' in page
    sr = {'by': 'Lee', 'fields': {'screen_reader': 'NVDA'}, 'items': {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['screen_reader']}}
    sr['items']['tables'] = {'result': 'na', 'note': 'checked'}; sr['items']['links'] = {'result': 'fail', 'note': 'bare URL'}
    M.record(R, 'screen_reader', sr, say=lambda *a: None, batch=False)
    page = html.unescape(MP.page(R, 'r', recorded='screen_reader'))
    assert ('Screen-Reader Test results recorded for this version. "Accessibility Evaluation" is now satisfied. 1 issue noted: it is kept '
            'in the report for a person to fix.') in page and 'id="mc-review"' in page
    js_src = open(os.path.join(HERE, 'webapp', 'panel.js'), encoding='utf-8').read()
    assert 'Accessibility Evaluation (PAC 2026 &amp; Screen-Reader Test)' in js_src and '>Complete Evaluation</a>' in js_src
    assert "const hx = inPanel ? 'h3' : 'h2';" in js_src                          # the panel fallback: an h3 (G2)
    css = open(os.path.join(HERE, 'webapp', 'panel.css'), encoding='utf-8').read()   # G1: the panel's nowrap last column does not reach Notes
    assert '.mc td.mc-note { max-width: 120ch; overflow-wrap: anywhere; white-space: normal; }' in css and '.mc-tw { overflow-x: auto; }' not in css
    s = MP.strip(R, S.load(os.path.join(R, 'record.json')))
    assert s['sections']['screen_reader']['words'].startswith('completed on this version (Lee, ') and s['sections']['screen_reader']['words'].endswith(' · 1 issue noted')

# ------------------------------------------------------------------ Record and its refusals
def test_record_errors_come_back_per_field_and_nothing_is_written(mapp):
    st, r = js(mapp['port'], 'POST', f'/api/run/{RUN}/checks/record', {'section': 'pac', 'data': {'by': '', 'items': {}}})
    assert st == 400 and {'by', 'items.pac_wcag.result'} <= {e['field'] for e in r['errors']}
    assert not os.path.exists(os.path.join(mapp['R'], 'release', 'checks.json'))

def test_record_refusals_in_their_own_words(mapp):
    port, R = mapp['port'], mapp['R']
    st, r = js(port, 'POST', f'/api/run/{RUN}/checks/record', {'section': 'pac', 'data': PAC, 'shown_sha256': '0' * 64})
    assert st == 409 and r['error'] == M.CHANGED
    os.makedirs(os.path.join(R, 'reviews', 'work'))
    st, r = js(port, 'POST', f'/api/run/{RUN}/checks/record', {'section': 'pac', 'data': PAC})
    assert st == 409 and r['error'] == M.MAKING
    os.rmdir(os.path.join(R, 'reviews', 'work'))
    held, go = threading.Event(), threading.Event()
    def hold():
        with runlock.record_lock(R): held.set(); go.wait(15)
    t = threading.Thread(target=hold); t.start(); held.wait(5)
    t0 = time.monotonic(); st, r = js(port, 'POST', f'/api/run/{RUN}/checks/record', {'section': 'pac', 'data': PAC})
    go.set(); t.join(5)
    assert st == 409 and r['error'] == runlock.BUSY and 4 < time.monotonic() - t0 < 9      # a request waits about 5 s

# ------------------------------------------------------------------ requests: F5, F6
def test_the_length_is_checked_before_reading(mapp):
    port, path = mapp['port'], f'/api/run/{RUN}/checks/draft'
    assert req(port, 'POST', path, raw=b'{}', length='-1')[0] == 411
    assert req(port, 'POST', path, raw=b'{}', length='abc')[0] == 411
    assert req(port, 'POST', path, raw=b'{}', length='70000')[0] == 413
    assert req(port, 'POST', f'/api/run/{RUN}/discard', raw=b'{}')[0] in (202, 409)       # the existing routes still answer

def test_a_full_section_in_four_byte_characters_fits(mapp):
    port = mapp['port']; c = '\U0001D11E'                                               # 4 bytes in UTF-8
    st, s = js(port, 'GET', f'/api/run/{RUN}/checks')
    data = {'by': c * 80, 'fields': {'screen_reader': c * 80, 'pdf_reader': c * 80, 'pages_checked': '1'}, 'notes': c * 4000,
            'items': {x['key']: {'result': 'pass', 'note': c * 1000} for x in REL.CHECKLIST['screen_reader']}}
    raw = json.dumps({'section': 'screen_reader', 'data': data, 'saved_at': '2026-11-01T10:00:00Z', 'for_sha256': s['sha']}, ensure_ascii=False).encode()
    assert 50000 < len(raw) <= W.MAX_BODY
    st, b, _ = req(port, 'POST', f'/api/run/{RUN}/checks/draft', raw=raw)
    assert st == 200, b

# ------------------------------------------------------------------ F4, language names
def test_the_code_is_read_once_when_the_module_loads(monkeypatch):
    before = M.code()
    monkeypatch.setattr(M.subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(AssertionError('git read again')))
    assert M.code() == before == M.CODE

def test_language_names():
    assert langtag.name('en-US') == 'English' and langtag.name('zh-Hant-TW') == 'Chinese (Traditional)' and langtag.name('haw') == 'Hawaiian'
    assert langtag.name('xx') is None and langtag.name(None) is None and langtag.name('english') is None
    assert MP.lang_words({'lang': None, 'lang_name': None}) == 'not set'
    assert MP.lang_words({'lang': 'xx', 'lang_name': None}) == 'a language the app can\'t name; it is in the report'

# ------------------------------------------------------------------ two batch-page rebuilds at once (the app's thread after each Record)
def test_two_summary_rebuilds_at_once_leave_a_whole_page(tmp_path):
    import report_html as H
    B = tmp_path / 'b'
    for n in ('one', 'two'): make_run(str(B / n))
    errs = []
    def run():
        try: H.summary_html(str(B))
        except Exception as e: errs.append(e)
    ts = [threading.Thread(target=run) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join(60)
    page = (B / 'summary.html').read_text()
    assert not errs and page.rstrip().endswith('</html>') and page.count('<!doctype html>') == 1
    assert not [n for n in os.listdir(B) if n.endswith('.tmp')]
