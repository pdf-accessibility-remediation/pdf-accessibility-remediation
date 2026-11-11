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
