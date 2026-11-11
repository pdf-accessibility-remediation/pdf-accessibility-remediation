"""test_webapp_first.py: each panel's first answer comes with its page (#93, Patrick's test of the app: no "Loading…").

    python -m pytest tests/test_webapp_first.py -q

On test_webapp.py's app (started as a person starts it): the run page (with and without review.html), the batch page and
the home page each carry, as a JSON data block, exactly what the panel's first request returns; the block is never a
script (the page's policy is unchanged) and no text in it can end it. Also the home page's line after a move to the Trash.
"""
import os, re, sys, json, urllib.parse
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_webapp import setup, settings, get, app, unver  # noqa: E402,F401
from webapp import home as HM, server as W  # noqa: E402

def block(page, eid):
    m = re.findall(r'<script type="application/json" id="' + eid + r'">(.*?)</script>', page.decode('utf-8'), re.S)
    assert len(m) == 1, (eid, len(m))
    return json.loads(m[0])

def api(port, path):
    st, b, _ = get(port, path); assert st == 200, (path, st, b[:300]); return json.loads(b)

def test_the_run_page_carries_the_panels_first_answer(app):
    port = app['port']
    for run in ('book/r1', 'old/r0'):                                    # with review.html, and without one
        st, page, h = get(port, f'/run/{run}/')
        assert st == 200 and b'pdfrem-panel' in page
        first = block(page, 'pp-first')
        assert first == {'run': api(port, f'/api/run/{run}'), 'setup': api(port, '/api/setup')}, run

def test_the_batch_page_carries_this_batchs_first_answer(app):
    st, page, _ = get(app['port'], '/batch/b1/')
    assert st == 200 and b'id="bt-body"></div>' in page and 'Loading' not in page.decode('utf-8')
    assert block(page, 'bt-first') == api(app['port'], '/api/batch/b1')
    assert b'<section class="pp" id="bt-panel" data-label="b1" aria-labelledby="bt-h">' in page   # review 09 N1

def test_the_home_page_carries_runs_in_progress(app):
    st, page, _ = get(app['port'], '/')
    assert st == 200 and b'id="hm-active"></div>' in page
    assert block(page, 'hm-first') == api(app['port'], '/api/jobs?active=1&seen=')

def test_the_block_is_data_and_nothing_in_it_ends_it():
    nasty = {'name': '</script><script>alert(1)</script> & <!-- x -->', 'n': [1, None, 'é']}
    h = HM.first_answer('pp-first', nasty)
    inner = h[len('<script type="application/json" id="pp-first">'):-len('</script>')]
    assert '<' not in inner and '>' not in inner and '&' not in inner and json.loads(inner) == nasty
    page = '<!doctype html><script>var a = 1;</script>' + h                # the page's one inline script, and the block
    assert W.csp(page) == W.csp('<!doctype html><script>var a = 1;</script>') and "'sha256-" in W.csp(page)

def test_the_home_page_names_what_was_moved_to_the_trash(app):
    port = app['port']
    page = get(port, '/?trashed=' + urllib.parse.quote('A <b>Book</b>'))[1].decode('utf-8')
    assert '<p id="hm-added" hidden>Moved to the Trash: A &lt;b&gt;Book&lt;/b&gt;.</p>' in page
    assert '<p id="hm-added" hidden>Moved to the Trash.</p>' in get(port, '/?trashed=1')[1].decode('utf-8')   # an older link
    assert 'drag it' not in page and 'put it back' not in page

# ------------------------------------------------------------------ review 09, 12c: Run Actions in the first frame
PANEL_JS = '<script src="/app/panel.js" defer blocking="render"></script>'

def in_head(page):
    """panel.js once, in the head (a render-blocking script counts only before <body>), and nowhere else."""
    page = unver(page)
    assert page.count('/app/panel.js') == 1 and page.count(PANEL_JS) == 1, page[-400:]
    if '</head>' not in page:                                           # the test's review.html has no head: right after its doctype
        return '<!doctype html><link rel="stylesheet" href="/app/panel.css">\n' + PANEL_JS in page
    return page.index(PANEL_JS) < page.index('</head>') < page.index('<body')

def test_every_kind_of_run_page_loads_panel_js_in_its_head(app, setup):
    port = app['port']
    for run in ('book/r1', 'old/r0', 'batches/b1/x'):                   # finished; no dashboard; a book in a batch
        st, page, _ = get(port, f'/run/{run}/')
        assert st == 200 and in_head(page), run
    s = settings(setup)
    W_ = (setup / 'runs' / 'wt' / 'l1'); W_.mkdir(parents=True)
    assert in_head(W.waiting_page('wt/l1', str(W_), s=s, first={'run': {}, 'setup': {}}))   # waiting and pending runs
    assert in_head(W.no_dashboard('wt/l1', str(W_)))
    plain = W.with_panel('<!doctype html><html><head><title>t</title></head><body><header><h1>t</h1></header></body></html>', 'a/b')
    assert in_head(plain) and plain.index('/app/panel.css') < plain.index(PANEL_JS)
    bare = W.with_panel('<p>no head</p>', 'a/b')                         # no head, no doctype: before the page's own content
    assert bare.count(PANEL_JS) == 1 and bare.index(PANEL_JS) < bare.index('<p>no head</p>')
    dt = W.with_panel('<!DOCTYPE html><title>r1</title><p>x</p>', 'a/b')  # never before the doctype (quirks mode)
    assert '<!DOCTYPE html><link rel="stylesheet" href="/app/panel.css">\n' + PANEL_JS in dt

# ------------------------------------------------------------------ review 09, L1: the batch page after a partial move
def test_the_batch_page_names_the_pdfs_moved_to_the_trash(app):
    port = app['port']
    def line(*names, more=None):
        q = '&'.join(['trashed=' + urllib.parse.quote(n) for n in names] + ([f'trashed_more={more}'] if more is not None else []))
        page = get(port, '/batch/b1/' + ('?' + q if q else ''))[1].decode('utf-8')
        m = re.findall(r'<p id="bt-trashed" hidden>(.*?)</p>', page)
        assert len(m) <= 1; return m[0] if m else None
    assert line() is None
    assert line('One') == 'Moved to the Trash: One.'
    assert line('One', 'Two') == 'Moved to the Trash: One and Two.'
    assert line('One', 'Two, Part 2', 'Three') == 'Moved to the Trash: One, Two, Part 2 and Three.'   # a comma in a name stays its own
    assert line('One', 'Two', 'Three', more=2) == 'Moved to the Trash: One, Two, Three and 2 more.'   # what trash.js sends
    assert line('One', 'Two', 'Three', 'Four', 'Five') == 'Moved to the Trash: One, Two, Three and 2 more.'
    assert line('One', 'Two', 'Three', more='x') == line('One', 'Two', 'Three', more='1234567') == 'Moved to the Trash: One, Two and Three.'
    assert line('A <b>Book</b> & Co') == 'Moved to the Trash: A &lt;b&gt;Book&lt;/b&gt; &amp; Co.'
    assert line('x' * 300) == 'Moved to the Trash: ' + 'x' * 200 + '.'                             # each name capped, as home's
    assert line('1') == 'Moved to the Trash.' and line(' ') is None

def test_trash_js_names_what_a_batch_move_took():
    t = open(os.path.join(PIPE, 'webapp', 'trash.js'), encoding='utf-8').read()
    assert "location.assign('/?view=batches&trashed=' + encodeURIComponent(p.name || '1'))" in t      # the whole batch
    assert "(p.pdfs || []).filter(x => moved.includes(x.name)).map(x => x.pdf || x.name)" in t
    assert "gone.slice(0, 3).map(n => 'trashed=' + encodeURIComponent(n))" in t and "['trashed_more=' + (gone.length - 3)]" in t
    b = open(os.path.join(PIPE, 'webapp', 'batch.js'), encoding='utf-8').read()
    assert "$('bt-trashed')" in b and "msg(gone.textContent, true, true)" in b
