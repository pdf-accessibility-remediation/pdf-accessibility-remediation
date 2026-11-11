"""Page changes switch in one step (#93 (improve performance: home and batch pages, first-time "Review Again", and PDF
pipeline step timing), Patrick 2026-11-11): the current page stays until the new one replaces it complete. No fade, no
blank or white frame, no part drawn after the rest, no "Loading…" during a page change. The frame-by-frame proof is in
the browser (handoff/93-performance/15-builder-report.md); these tests keep what makes it hold."""
import os, re
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(HERE, 'webapp')
read = lambda *p: open(os.path.join(*p), encoding='utf-8').read()

def test_no_fade_and_nothing_kept_for_it():
    """The cross-document view transition (D7's fade) is gone, and so is the panel's height kept across pages, which only
    covered a panel drawn after the page first showed."""
    css = read(WEB, 'panel.css'); js = read(WEB, 'panel.js')
    assert '@view-transition' not in css and 'view-transition' not in css
    assert 'pp-h:' not in js and 'keepHeight' not in js and 'minHeight' not in js

import sys
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_webapp import setup, settings, get, app  # noqa: E402,F401

PAGES = ('/', '/?view=batches', '/run/book/r1/', '/run/old/r0/', '/run/book/r1/review.md', '/batch/b1/', '/batch/b1/summary.html',
         '/run/batches/b1/x/', '/run/book/r1/download?what=nothing')

def test_no_frame_is_ever_white(app):
    """html and body carry the app's background (panel.css; the review page its own), and every HTML page the app serves
    names its colour schemes in its head, once, so a canvas drawn before the stylesheets is dark in dark mode."""
    assert 'html, body { background: var(--bg); }' in read(WEB, 'panel.css')
    rp = read(HERE, 'review', 'page.html')
    assert '<meta name="color-scheme" content="light dark">' in rp.split('</head>')[0] and 'html { background: var(--bg); }' in rp
    for p in PAGES:
        st, b, h = get(app['port'], p)
        page = b.decode('utf-8')
        assert h.get('Content-Type', '').startswith('text/html'), (p, st)
        head = page.split('</head>')[0]
        assert page.count('<meta name="color-scheme" content="light dark">') == 1 and '<meta name="color-scheme"' in head, p

def test_the_apps_own_files_are_kept_by_their_version(app):
    """Each page names the app's scripts and stylesheets with their version (?v=, the sha256 of the file the server read at
    its start), and the browser keeps a file asked for by that version: a blocking script then never waits on the network.
    Asked for without it, or with another version, a file is never kept (an older page after an update gets the new file)."""
    import hashlib
    port = app['port']
    page = get(port, '/run/book/r1/')[1].decode('utf-8') + get(port, '/run/old/r0/')[1].decode('utf-8')
    found = re.findall(r'="/app/([\w.]+)\?v=([0-9a-f]{12})"', page)
    assert {'panel.css', 'panel.js', 'palette.css'} <= {n for n, _ in found} and not re.search(r'="/app/[\w.]+"', page)
    for n, v in set(found):
        st, b, h = get(port, f'/app/{n}?v={v}')
        assert st == 200 and h['Cache-Control'] == 'max-age=31536000, immutable' and hashlib.sha256(b).hexdigest()[:12] == v
        assert b == open(os.path.join(HERE, 'review' if n == 'palette.css' else 'webapp', n), 'rb').read()
        for q in ('', '?v=000000000000'):
            st2, b2, h2 = get(port, f'/app/{n}{q}')
            assert st2 == 200 and h2['Cache-Control'] == 'no-store' and b2 == b
    assert get(port, '/run/book/r1/')[2]['Cache-Control'] == 'no-store' and get(port, '/api/setup')[2]['Cache-Control'] == 'no-store'

# ------------------------------------------------------------------ every first view drawn while the page is read
import json, hashlib, base64
from webapp import home as HM, server as W  # noqa: E402

def _cut(page):
    """Where the page's head ends: its </head>, or (a page with no head tag, as the tests' review.html) where the browser's
    implicit head ends, the first element that belongs in the body."""
    if '</head>' in page: return page.index('</head>')
    return min(i for i in (page.find(t) for t in ('<body', '<header', '<p', '<a ', '<div', '<main', '<nav')) if i >= 0)
def head(page): return page[:_cut(page)]
def body(page): return page[_cut(page):]
def scripts(page): return re.findall(r'<script\b([^>]*)>', page)

def test_scripts_that_draw_are_plain_in_the_head_and_called_right_after_what_they_fill(app):
    """Each script that draws part of a first view (panel.js, batch.js, shared.js, home.js, manual.js) is a plain blocking
    script in the head (never defer or async: a deferred script runs after the browser may have shown the page), and the
    page calls its drawing function right after the elements it fills, before anything else of the page."""
    port = app['port']
    (app['R'] / 'review.html').write_text(DOC)                                        # a report as report_html.py writes one
    pages = {p: W_unver(get(port, p)[1]) for p in ('/', '/run/book/r1/', '/run/old/r0/', '/run/batches/b1/x/', '/batch/b1/')}
    for p, page in pages.items():
        for a in scripts(body(page)):
            assert 'src=' not in a or '/app/trash.js' in a, (p, a)            # trash.js draws nothing until it is used: it may defer
        for a in scripts(head(page)):
            if 'src=' in a: assert 'defer' not in a and 'async' not in a and 'blocking' not in a, (p, a)
    home = pages['/']
    assert ['shared.js', 'home.js'] == re.findall(r'/app/(\w+\.js)', head(home))
    assert home.index('id="hm-active"') < home.index('id="hm-first"') < home.index(HM.call('homeActive')) < home.index('id="hm-books-h"')
    assert home.index('</form></section>' + HM.call('homeAdded')) < home.index('id="hm-runs-h"')            # right after "Upload a PDF"
    assert home.index(HM.call('home')) > home.index('</main>')
    run = pages['/run/book/r1/']
    i = run.index('<div id="pdfrem-panel"')
    assert run.index('id="pp-first"', i) < run.index(HM.call('panel'), i) < run.index('<main', i) and 'Loading' not in run
    assert '<div id="pdfrem-panel" data-strip="card"' in run and '</section>\n<div id="pdfrem-checks" data-run="book/r1"></div>\n' + HM.call('strip') in run
    assert run.count('<script>') == 3                                                  # the two calls and the report's own
    batch_book = pages['/run/batches/b1/x/']
    assert re.findall(r'/app/(\w+\.js)', head(batch_book)) == ['panel.js', 'batch.js']
    nav_end = batch_book.index('</nav>', batch_book.index('id="pp-bnav"'))
    assert batch_book[nav_end:].startswith('</nav>' + HM.call('batchNav'))                                # the side list, set at once
    b = pages['/batch/b1/']
    assert ['shared.js', 'batch.js'] == re.findall(r'/app/(\w+\.js)', head(b)) and 'data-batch-page="1"' in b
    assert b[b.index('</nav>', b.index('id="pp-bnav"')):].startswith('</nav>' + HM.call('batchNav'))
    assert b.index('id="bt-first"') < b.index(HM.call('batchPage')) and 'Loading' not in b

DOC = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>r1</title></head><body><a class="skip" href="#main">Skip to the content</a>'
       '<header class="top"><h1>r1</h1></header><main id="main"><section class="ship" aria-labelledby="ship-h"><h2 id="ship-h">Ready to Ship? No</h2></section>'
       '<p>the report</p></main><script>var report = 1;</script></body></html>')

def W_unver(b):
    from test_webapp import unver
    return unver(b)

def test_the_strip_is_drawn_right_after_its_own_place():
    """The evaluation strip sits after the "Ready to Ship?" card, further down than Run Actions: its own call follows it,
    and the panel is told to leave it to that call (data-strip="card"); a page with no card keeps the strip in the panel."""
    page = '<!doctype html><html><head></head><body><header class="top">h</header><main><section class="ship" aria-labelledby="ship-h">s</section><p>rest</p></main></body></html>'
    out = W.with_panel(page, 'a/b', first={'run': {}, 'setup': []})
    assert '<div id="pdfrem-panel" data-strip="card" data-run="a/b"' in out
    assert '</section>\n<div id="pdfrem-checks" data-run="a/b"></div>\n' + HM.call('strip') + '\n<p>rest</p>' in out
    plain = W.with_panel(page.replace(' aria-labelledby="ship-h"', ''), 'a/b')
    assert 'data-strip' not in plain and 'pdfrem-checks' not in plain and HM.call('strip') not in plain
    js = read(WEB, 'panel.js')
    assert "if (!sb && box.dataset.strip === 'card') return;" in js and 'window.Pdfrem.strip = () => { if (st && !WAITING) renderStrip(st); };' in js

def test_every_call_the_pages_make_is_defined_and_allowed():
    """Each call (home.py CALLS) is defined by one of the app's scripts, and the page's policy allows exactly the calls it
    holds, by their sha256, beside the one other inline script a report may have; a second other inline script is still
    refused, and a call's text with anything added is not a call."""
    js = ''.join(read(WEB, f) for f in ('panel.js', 'batch.js', 'home.js', 'manual.js'))
    for n in HM.CALLS: assert re.search(r'\bP\.' + n + r' = ', js), n
    sha = lambda t: "'sha256-" + base64.b64encode(hashlib.sha256(t.encode()).digest()).decode() + "'"
    page = '<!doctype html><p>x</p>' + HM.call('panel') + HM.call('strip') + '<script>var report = 1;</script>'
    assert W.csp(page) == f"frame-ancestors 'none'; script-src 'self' {' '.join(sorted([sha('Pdfrem.panel()'), sha('Pdfrem.strip()')]))} {sha('var report = 1;')}" \
        or W.csp(page) == f"frame-ancestors 'none'; script-src 'self' {sha('Pdfrem.panel()')} {sha('Pdfrem.strip()')} {sha('var report = 1;')}"
    two = page + '<script>var other = 2;</script>'
    assert sha('var report = 1;') not in W.csp(two) and sha('Pdfrem.panel()') in W.csp(two)
    assert sha('Pdfrem.panel();alert(1)') not in W.csp('<script>Pdfrem.panel();alert(1)</script><script>x</script>')

def test_the_previous_result_and_a_saved_batchs_address_come_with_what_they_draw(app):
    """A previous result's bar draws "Review Again from This Session" from the page's own first answer (no request after
    the page shows), and a saved batch's address opens home with its pop-up's contents in the page (no "Loading…")."""
    port = app['port']
    (app['R'] / 'reviews' / 'versions' / '001' / 'review.html').write_text(DOC)
    page = W_unver(get(port, '/run/book/r1/reviews/versions/001/review.html')[1])
    m = re.search(r'<script type="application/json" id="pp-vfirst">(.*?)</script>', page)
    assert m and json.loads(m.group(1))['run'] == json.loads(get(port, '/api/run/book/r1')[1])
    assert page.index('id="pdfrem-version"') < page.index('id="pp-vfirst"') < page.index(HM.call('version'))
    assert '/app/panel.js' in head(page) and '/app/panel.js' not in body(page)
    js = read(WEB, 'panel.js')
    assert "const vf = readBlock('pp-vfirst');\n  if (vf && vf.run) drawAct(vf.run);" in js
    sh = read(WEB, 'shared.js')
    assert "if (html) {\n    dlg.innerHTML = html; if (!dlg.open) dlg.showModal();" in sh
    assert "window.Pdfrem.openDialog('/api/form?what=batch&saved=' + encodeURIComponent(lab), null, op && op.html);" in read(WEB, 'home.js')

