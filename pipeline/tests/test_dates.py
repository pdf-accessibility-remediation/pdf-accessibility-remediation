"""test_dates.py: lib/dates.py, the one way a date or a time is shown (decided 2026-10-31, #38), and its JavaScript copy
in webapp/panel.js and review/page.html (the same table, the same parse; run through node or macOS's jsc, under Honolulu time).

    python -m pytest tests/test_dates.py -q
"""
import os, sys, json, shutil, subprocess
import pytest
from lib import dates as D

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = [('2026-10-31', 'October 31, 2026', 'time not recorded', 'October 31, 2026'),
         ('2026-10-31T16:32:05', 'October 31, 2026', '4:32 PM', 'October 31, 2026 at 4:32 PM'),
         ('2026-10-31 09:05', 'October 31, 2026', '9:05 AM', 'October 31, 2026 at 9:05 AM'),
         ('2026-01-02T00:05:00.123456', 'January 2, 2026', '12:05 AM', 'January 2, 2026 at 12:05 AM'),   # midnight, fractional seconds
         ('2026-06-30T12:00:00', 'June 30, 2026', '12:00 PM', 'June 30, 2026 at 12:00 PM'),               # noon
         ('2026-10-31T23:59:59Z', 'October 31, 2026', '11:59 PM', 'October 31, 2026 at 11:59 PM'),       # an offset: its own time
         ('the 30th', 'the 30th', 'the 30th', 'the 30th'),                                               # free text: as written
         ('2026-13-01', '2026-13-01', '2026-13-01', '2026-13-01'),
         ('', 'date not recorded', 'time not recorded', 'date not recorded'),
         (None, 'date not recorded', 'time not recorded', 'date not recorded')]

@pytest.mark.parametrize('v, day, clock, when', CASES)
def test_dates(v, day, clock, when):
    assert (D.day(v), D.clock(v), D.when(v)) == (day, clock, when)

def src(f): return open(os.path.join(HERE, f), encoding='utf-8').read()
MONTHS_JS = "const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];"

def test_the_same_table_and_parse_in_the_pages():
    for f in ('webapp/panel.js', 'review/page.html'):
        t = src(f)
        assert MONTHS_JS in t and 'new Date(v' not in t, f                 # parsed by hand, never with Date (UTC midnight)
        assert r"const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$/;" in t, f

JSC = '/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc'   # macOS's own engine
def js_runner():
    """A JavaScript engine that runs here: node, else macOS's jsc (this machine's node lacks its OpenSSL), else None."""
    n = shutil.which('node')
    if n and subprocess.run([n, '-e', '1'], capture_output=True, timeout=30).returncode == 0: return [n, '-e']
    return [JSC, '-e'] if os.access(JSC, os.X_OK) else None

@pytest.mark.skipif(js_runner() is None, reason='no JavaScript engine (node or jsc) runs here')
@pytest.mark.parametrize('f', ['webapp/panel.js', 'review/page.html'])
def test_the_javascript_gives_the_same_words_in_honolulu(f):
    t = src(f)
    a = t.index('// ---- dates (lib/dates.py)'); b = t.index('// ---- end of dates', a)
    code = t[a:b] + f'\nconst cases = {json.dumps([c[0] for c in CASES])};\n' \
        '(typeof print === "function" ? print : console.log)(JSON.stringify(cases.map(v => [fmtDay(v), fmtClock(v), fmtWhen(v)])));'
    out = subprocess.run(js_runner() + [code], capture_output=True, text=True, env=dict(os.environ, TZ='Pacific/Honolulu'), timeout=30)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == [[c[1], c[2], c[3]] for c in CASES]
