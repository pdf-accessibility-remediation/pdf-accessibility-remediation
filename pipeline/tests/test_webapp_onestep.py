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
