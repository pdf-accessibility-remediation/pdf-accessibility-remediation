"""webapp/server.py: the app's HTTP server, on 127.0.0.1 only. Python's standard library, no new packages.

Routes (GET; requests must name this server as their host, as review/server.py checks):
    /api/ping                  {app, root, settings}: how a second start finds this one
    /api/setup                 the setup status (webapp/checks.py)
    /api/jobs                  every job (status, place in line); no environments
    /api/job/<id>?from=N       one job and its log from byte N
    /api/run/<run>             a run's state for the panel
    /run/<run>/                the run's review.html with the panel added at serve time (the file is not changed); a run
                               with no review.html: the panel, review.md and a line saying there is no dashboard
    /run/<run>/<file>          the run's own files from a fixed list: review.md, han_review.csv, the remediated PDF named
                               in record.json; the same under reviews/versions/<id>/. Every page has a way back:
                               /run/<run>/review.html goes to the run page; a previous result's review.html gets a bar
                               (previous result, Back to the Current Result, Review Again from This Session); review.md is
                               shown inside a page with links back (?raw=1: the plain file). A PDF opens in the browser's
                               own viewer.
    /batch/<label>/            a batch's summary.html (and summary.md); its <name>/review.html links go to /run/batches/<label>/<name>/
    /app/panel.js|panel.css|palette.css   the panel's own files
POST (JSON from the app's own pages only), each answered 202 {job} or 409 {error} with the reason:
    /api/run/<run>/review      {from: null | "ai" | "003", discard_open}: Review again (a pin job first on an unpinned run)
    /api/run/<run>/apply       Apply the finished session that was not applied
    /api/run/<run>/stop        Stop reviewing: Ctrl+C to the open review page, only before Finish
    /api/run/<run>/discard     Discard the open session: review_workorder.py --discard-open (marked abandoned, kept);
                               refused while its review page is open or past Finish
    /api/run/<run>/ocr         Review OCR text: the OCR-only review page (review_ocr.py --serve), a job that waits on a person
Reserved for later pages (not built): /run/<run>/release, /run/<run>/screen-reader. /run/<run>/ocr stays reserved (404):
OCR text is approved on the review page, or on the OCR-only page, both on the review server.

Every response forbids framing (X-Frame-Options: DENY, CSP frame-ancestors 'none'), so another site cannot show a run
page in a frame and trick a click. HTML pages also get script-src 'self' plus the sha256 of the page's one inline script,
computed when it is served, so a javascript: link or any other script in a report's text never runs.

A run is named by its path under the runs folder (godzone/rv1, batches/d1/clans): the shortest prefix of the request
path that is a folder holding record.json. Every segment is checked (no empty, ".", "..", dot-names or backslashes),
and no request string is ever joined onto a path: each segment (a run's folders, a batch, a previous result's id, a job
id) only picks an entry from the real folder's listing (config.entry). The folder and every file are then resolved
with realpath and must stay inside the runs folder, and a file is served only when its name is in the run's list.
Nothing outside the runs folder is ever served (.env, samples/, pipeline/).
"""
import os, re, json, html, base64, hashlib, traceback, urllib.parse, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from html.parser import HTMLParser
from review.server import local_request
from review import sessions as S
from lib.titles import title_case as TC
from . import config, jobs, runs

FILES = ('review.html', 'review.md', 'han_review.csv')
TYPES = {'.html': 'text/html; charset=utf-8', '.md': 'text/plain; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.pdf': 'application/pdf',
         '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8'}
RESERVED = ('ocr', 'release', 'screen-reader')

def segments(p):
    """The decoded path segments, or None when any is unsafe."""
    segs = [urllib.parse.unquote(x) for x in p.split('/') if x != '']
    for x in segs:
        if x in ('.', '..') or x.startswith('.') or '\\' in x or '\x00' in x or '/' in x: return None
    return segs

def inside(root, p):
    root = os.path.realpath(root); p = os.path.realpath(p)
    return p == root or p.startswith(root + os.sep)

def find_run(runs, segs):
    """(run name, its folder, the remaining segments) for the shortest prefix holding record.json, or None. Each segment
    picks an entry from the folder's own listing (config.entry): the folder is built from names on disk only, then
    resolved and kept inside the runs folder (a symlink out of it is refused)."""
    base = os.path.realpath(runs); d = base
    for i, x in enumerate(segs, 1):
        d = config.entry(d, x)
        if d is None: return None
        d = os.path.realpath(d)
        if not d.startswith(base + os.sep) or not os.path.isdir(d): return None
        if os.path.isfile(os.path.join(d, 'record.json')): return '/'.join(segs[:i]), d, segs[i:]
    return None

def version_dir(R, sid):
    """A previous result's folder, reviews/versions/<sid>, picked from that folder's listing; None when it is not there
    or resolves outside it."""
    V = os.path.realpath(os.path.join(R, 'reviews', 'versions'))
    d = config.entry(V, sid)
    if d is None: return None
    d = os.path.realpath(d)
    return d if d.startswith(V + os.sep) and os.path.isdir(d) else None

def batch_dir(runs, label):
    """A batch's folder, runs/batches/<label>, picked from the batches folder's listing, holding summary.html; or None."""
    BB = os.path.realpath(os.path.join(runs, 'batches'))
    B = config.entry(BB, label)
    if B is None: return None
    B = os.path.realpath(B)
    return B if B.startswith(BB + os.sep) and os.path.isfile(os.path.join(B, 'summary.html')) else None

def served(d, runs):
    """{name: path} of the files a run (or a version under reviews/versions/) serves. Every path is resolved and checked
    to be inside the runs folder right where it is used (realpath + startswith)."""
    base = os.path.realpath(runs)
    rec = os.path.realpath(os.path.join(d, 'record.json')); pdf = None
    if rec.startswith(base + os.sep):
        try: pdf = ((json.load(open(rec, encoding='utf-8')).get('document') or {}).get('output'))
        except (OSError, ValueError): pdf = None
    names = list(FILES)
    if isinstance(pdf, str) and pdf.lower().endswith('.pdf') and '/' not in pdf and '\\' not in pdf and not pdf.startswith('.'):
        names.append(pdf)
    out = {}
    for n in names:
        p = os.path.realpath(os.path.join(d, n))
        if p.startswith(base + os.sep) and os.path.isfile(p): out[n] = p
    return out

STATIC = {'panel.js': os.path.join(config.HERE, 'panel.js'), 'panel.css': os.path.join(config.HERE, 'panel.css'),
          'palette.css': os.path.join(config.PIPELINE, 'review', 'palette.css')}
SKIP = '<a class="skip" href="#main">Skip to the content</a>'

FRAME = {'X-Frame-Options': 'DENY', 'Content-Security-Policy': "frame-ancestors 'none'"}   # every response: never in a frame
class Scripts(HTMLParser):
    """The page's inline scripts as the browser sees them (html.parser, not a regex: it handles "</script >" and runs in
    linear time): the exact text of each <script> with no src and no JSON type."""
    def __init__(self):
        super().__init__(convert_charrefs=False); self.found = []; self.cur = None
    def handle_starttag(self, tag, attrs):
        if tag != 'script': return
        a = {k.lower(): (v or '') for k, v in attrs}
        self.cur = None if 'src' in a or a.get('type', '').strip().lower() in ('application/json', 'application/ld+json') else []
    def handle_data(self, data):
        if self.cur is not None: self.cur.append(data)
    def handle_endtag(self, tag):
        if tag == 'script':
            if self.cur is not None: self.found.append(''.join(self.cur))
            self.cur = None

def csp(page):
    """An HTML page's policy: no framing, and scripts only from the app itself plus the page's one inline script by its
    sha256 (review.html and summary.html have exactly one; a JSON data block is not a script). A page with any other
    count of inline scripts gets none allowed. A javascript: link in the report's text never runs."""
    p = Scripts(); p.feed(page); p.close(); inline = p.found
    h = f" 'sha256-{base64.b64encode(hashlib.sha256(inline[0].encode('utf-8')).digest()).decode()}'" if len(inline) == 1 else ''
    return f"frame-ancestors 'none'; script-src 'self'{h}"

def after_body(page, box):
    """box inserted right after the <body …> tag (str.find, not a regex), or at the start when there is none."""
    i = page.lower().find('<body')
    j = page.find('>', i) if i >= 0 else -1
    return page[:j + 1] + box + page[j + 1:] if j >= 0 else box + page

def with_panel(page, run, current=None):
    """review.html as served: the panel's stylesheet, its place (after the page's header, so its h2 follows the page's h1;
    else after the skip link) and its script added. `current`: the session whose result the page shows, so the panel can
    tell when an apply has made a newer one. The file on disk is never changed; opened as a file it is the plain report."""
    box = f'\n<div id="pdfrem-panel" data-run="{html.escape(run)}"' + (f' data-current="{html.escape(str(current))}"' if current else '') + '></div>\n'
    head = '<link rel="stylesheet" href="/app/panel.css">\n'
    i = page.find('</head>'); page = page[:i] + head + page[i:] if i >= 0 else head + page
    if '</header>' in page: page = page.replace('</header>', '</header>' + box, 1)
    elif SKIP in page: page = page.replace(SKIP, SKIP + box, 1)
    else: page = after_body(page, box)
    i = page.rfind('</body>'); js = '<script src="/app/panel.js" defer></script>\n'
    return page[:i] + js + page[i:] if i >= 0 else page + js

def with_version(page, run, sid):
    """A previous result's review.html (reviews/versions/<id>/) as served: a bar after its header saying it is a previous
    result, with "Back to the Current Result" and "Review Again from This Session" (webapp/panel.js draws it). The file's
    own "replaced by" note is hidden there (panel.css), and stays in the file."""
    box = f'\n<div id="pdfrem-version" data-run="{html.escape(run)}" data-session="{html.escape(sid)}"></div>\n'
    head = '<link rel="stylesheet" href="/app/panel.css">\n'
    i = page.find('</head>'); page = page[:i] + head + page[i:] if i >= 0 else head + page
    if '</header>' in page: page = page.replace('</header>', '</header>' + box, 1)
    else: page = after_body(page, box)
    i = page.rfind('</body>'); js = '<script src="/app/panel.js" defer></script>\n'
    return page[:i] + js + page[i:] if i >= 0 else page + js

def md_page(text, run, sid, base):
    """review.md inside a page with a way back (the run page; for a previous result, that result's dashboard too) and a
    link to the plain file. The text is shown as written, escaped."""
    which = TC(f'a previous result ({S.label(sid).capitalize()})' if sid else 'the current result')   # TC leaves parentheses as written
    links = [f'<a href="{base}">Back to the Run Page</a>'] + ([f'<a href="review.html">This Previous Result\'s Dashboard</a>'] if sid else []) + \
            ['<a href="review.md?raw=1">The Plain File</a>']
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>review.md: {html.escape(run)}</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css">'
            f'</head><body class="pp-page">\n{SKIP}<header><h1>review.md of {html.escape(run)}: {which}</h1></header>'
            f'<nav class="pp-wrap" aria-label="Pages of this run"><p class="pp pp-bar">' + ' · '.join(links) + '</p></nav>'
            f'<main id="main" tabindex="-1"><pre class="pp-md">{html.escape(text)}</pre></main>'
            f'<script src="/app/panel.js" defer></script></body></html>')                 # panel.js: in-page links move focus

def make(s, setup, code=None):
    """The server, bound to 127.0.0.1:port (no fallback: a busy port is an error the caller reports). The panel's files are
    read once, here, so the pages always match the code this server runs, even if the files on disk change under it;
    `code` is the fingerprint of that code (config.code_fingerprint), which /api/ping reports."""
    J = s['jobs']
    RUNS = os.path.realpath(s['runs'])                   # every file the server reads for a request is inside this folder
    assets ={n: (open(p, 'rb').read(), TYPES.get(os.path.splitext(p)[1].lower(), 'application/octet-stream')) for n, p in STATIC.items()}
    code = code or config.code_fingerprint()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def headers_(self, ctype, length, policy=None):
            self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(length))
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', FRAME['X-Frame-Options'])
            self.send_header('Content-Security-Policy', policy or FRAME['Content-Security-Policy'])
        def send(self, code, body, ctype='application/json; charset=utf-8', extra=None):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode('utf-8')
            self.send_response(code); self.headers_(ctype, len(b), csp(b.decode('utf-8', 'replace')) if ctype.startswith('text/html') else None)
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.end_headers(); self.wfile.write(b)
        def file(self, p):
            rp = os.path.realpath(p)                     # only files inside the runs folder, checked here, where they are opened
            if not rp.startswith(RUNS + os.sep) or not os.path.isfile(rp): return self.send(404, {'error': 'not found'})
            ctype = TYPES.get(os.path.splitext(rp)[1].lower(), 'application/octet-stream')
            policy = csp(open(rp, encoding='utf-8', errors='replace').read()) if ctype.startswith('text/html') else None
            self.send_response(200); self.headers_(ctype, os.path.getsize(rp), policy); self.end_headers()
            with open(rp, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''): self.wfile.write(b)
        def text(self, p):
            """A served file's text, for a page built around it; None when it is not inside the runs folder."""
            rp = os.path.realpath(p)
            if not rp.startswith(RUNS + os.sep): return None
            return open(rp, encoding='utf-8', errors='replace').read()
        def redirect(self, to): self.send(302, b'', 'text/plain', {'Location': to})
        def ours(self): return local_request(self, self.server.server_address[1])

        def do_GET(self):
            try: self.get()
            except BrokenPipeError: pass
            except Exception:
                with open(os.path.join(J, 'server.log'), 'a', encoding='utf-8') as f: f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")} GET {self.path}\n{traceback.format_exc()}\n')
                self.send(500, {'error': 'the app hit an error: see runs/.app/server.log'})

        def do_POST(self):
            try: self.post()
            except BrokenPipeError: pass
            except Exception:
                with open(os.path.join(J, 'server.log'), 'a', encoding='utf-8') as f: f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")} POST {self.path}\n{traceback.format_exc()}\n')
                self.send(500, {'error': 'the app hit an error: see runs/.app/server.log'})

        def post(self):
            if not self.ours(): return self.send(403, {'error': 'not from the app\'s own pages'})
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
                return self.send(415, {'error': 'the app\'s pages send JSON'})
            try: body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            except ValueError: return self.send(400, {'error': 'not JSON'})
            if not isinstance(body, dict): return self.send(400, {'error': 'not a JSON object'})
            p = urllib.parse.urlsplit(self.path).path
            segs = segments(p[len('/api/run/'):]) if p.startswith('/api/run/') else None
            if not segs or len(segs) < 2 or segs[-1] not in ('review', 'apply', 'stop', 'discard', 'ocr'): return self.send(404, {'error': 'not found'})
            hit = find_run(s['runs'], segs[:-1])
            if not hit or hit[2]: return self.send(404, {'error': 'no such run'})
            run, R, _ = hit
            try:
                if segs[-1] == 'review':
                    src = body.get('from')
                    j = runs.start_review(s, run, R, self.server.server_address[1], None if src in (None, '', 'latest') else str(src),
                                          bool(body.get('discard_open')), app_pid=os.getpid())
                elif segs[-1] == 'apply': j = runs.start_apply(s, run, R)
                elif segs[-1] == 'ocr': j = runs.start_ocr(s, run, R, self.server.server_address[1], app_pid=os.getpid())
                elif segs[-1] == 'discard': j = runs.start_discard(s, run, R)
                else: j = runs.stop_review(s, run, R); return self.send(200, {'stopped': j['id']})
            except ValueError as e: return self.send(409, {'error': str(e)})
            jobs.tick(J, s)                                   # start it now if a place is free, rather than within the second
            self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id']))})

        def get(self):
            if not self.ours(): return self.send(403, {'error': f'open the app at http://127.0.0.1:{self.server.server_address[1]}/'})
            url = urllib.parse.urlsplit(self.path); q = urllib.parse.parse_qs(url.query)
            p = url.path
            if p == '/api/ping': return self.send(200, {'app': 'pdfrem', 'root': config.ROOT, 'settings': s['sha'], 'code': code})
            if p == '/api/setup': return self.send(200, setup)
            if p == '/api/jobs':                             # the newest first, up to ?limit= (default 50, at most 500)
                lim = (q.get('limit') or ['50'])[0]                   # isdecimal: '²' is a digit but not a number int() reads
                lim = min(int(lim), 500) if lim.isdecimal() and len(lim) <= 4 and int(lim) > 0 else 50
                return self.send(200, [runs.job_view(s, j) for j in reversed(jobs.all_jobs(J)[-lim:])])
            if p.startswith('/api/job/'):
                jid = p[len('/api/job/'):]
                job = jobs.load(J, jid) if re.fullmatch(r'[0-9A-Za-z_-]+', jid or '') else None
                if not job: return self.send(404, {'error': 'no such job'})
                off = (q.get('from') or ['0'])[0]
                return self.send(200, runs.job_view(s, job, with_text=True, offset=int(off) if off.isdecimal() and len(off) <= 12 else 0))
            if p.startswith('/api/run/'):
                segs = segments(p[len('/api/run/'):])
                hit = find_run(s['runs'], segs) if segs else None
                if not hit or hit[2]: return self.send(404, {'error': 'no such run'})
                return self.send(200, runs.state(s, hit[0], hit[1]))
            if p.startswith('/app/') and p[len('/app/'):] in assets: return self.send(200, *assets[p[len('/app/'):]])
            if p.startswith('/batch/'):
                segs = segments(p[len('/batch/'):])
                if not segs: return self.send(404, {'error': 'no such batch'})
                B = batch_dir(s['runs'], segs[0])
                if not B: return self.send(404, {'error': 'no such batch'})
                rest = segs[1:]
                if not rest:
                    if not p.endswith('/'): return self.redirect(p + '/')
                    return self.file(os.path.join(B, 'summary.html'))
                if rest in (['summary.html'], ['summary.md']):
                    return self.file(os.path.join(B, 'summary.html' if rest[0] == 'summary.html' else 'summary.md'))
                if len(rest) >= 1 and find_run(s['runs'], ['batches', segs[0], rest[0]]):
                    return self.redirect('/run/' + '/'.join(urllib.parse.quote(x) for x in ['batches', segs[0], rest[0]]) + '/')
                return self.send(404, {'error': 'not found'})
            if p.startswith('/run/'):
                segs = segments(p[len('/run/'):])
                if segs is None: return self.send(404, {'error': 'not found'})
                if len(segs) == 3 and segs[0] == 'batches' and segs[2] in ('summary.html', 'summary.md'):    # a review.html's ../summary.html
                    return self.redirect(f'/batch/{urllib.parse.quote(segs[1])}/' + ('' if segs[2] == 'summary.html' else 'summary.md'))
                hit = find_run(s['runs'], segs)
                if not hit: return self.send(404, {'error': 'no such run'})
                run, R, rest = hit
                if not rest:
                    if not p.endswith('/'): return self.redirect(p + '/')
                    return self.run_page(run, R)
                if len(rest) == 1 and rest[0] in RESERVED: return self.send(404, {'error': 'this page is not built yet'})
                d, name, sid = R, rest[-1], None
                if len(rest) == 4 and rest[:2] == ['reviews', 'versions']:
                    d, sid = version_dir(R, rest[2]), rest[2]
                    if d is None: return self.send(404, {'error': 'not found'})
                elif len(rest) != 1: return self.send(404, {'error': 'not found'})
                f = served(d, s['runs']).get(name)
                if not f or not inside(R, f): return self.send(404, {'error': 'not found'})
                base = '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/'
                if name == 'review.html' and sid is None: return self.redirect(base)      # the run page, with the panel
                if name in ('review.html', 'review.md') and not (name == 'review.md' and (q.get('raw') or [''])[0] == '1'):
                    t = self.text(f)
                    if t is None: return self.send(404, {'error': 'not found'})
                    if name == 'review.html':                                              # a previous result: its bar
                        return self.send(200, with_version(t, run, sid), 'text/html; charset=utf-8')
                    return self.send(200, md_page(t, run, sid, base), 'text/html; charset=utf-8')   # review.md with a way back
                return self.file(f)
            if p == '/': return self.send(200, home_stub(s), 'text/html; charset=utf-8')
            self.send(404, {'error': 'not found'})

        def run_page(self, run, R):
            f = os.path.join(R, 'review.html')
            rec = os.path.realpath(os.path.join(R, 'record.json'))
            cur = S.current_id((runs.load(rec) if rec.startswith(RUNS + os.sep) else None) or {})
            f = os.path.realpath(f)                                                  # checked inside the runs folder first
            t = self.text(f) if f.startswith(RUNS + os.sep) and os.path.isfile(f) else None
            if t is not None: return self.send(200, with_panel(t, run, cur), 'text/html; charset=utf-8')
            return self.send(200, no_dashboard(run, R, cur), 'text/html; charset=utf-8')

    return ThreadingHTTPServer(('127.0.0.1', s['port']), H)

def no_dashboard(run, R, current=None):
    """A run with no review.html (older runs): the panel, the review.md link and a line saying there is no dashboard.
    No rebuild: report_html.py would write into the run."""
    rm = os.path.realpath(os.path.join(R, 'review.md'))           # checked inside the run folder before isfile
    md = '<p><a href="review.md">review.md</a>: what a person should check.</p>' if rm.startswith(os.path.realpath(R) + os.sep) and os.path.isfile(rm) else ''
    return with_panel(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                      f'<title>{html.escape(run)}</title><link rel="stylesheet" href="/app/palette.css"></head><body class="pp-page">\n{SKIP}'
                      f'<header><h1>{html.escape(run)}</h1></header><main id="main" tabindex="-1">'
                      f'<p>This run has no dashboard (review.html): it was made before the dashboards, or without one.</p>{md}</main></body></html>', run, current)

def home_stub(s):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>PDF Remediation</title></head><body><main>'
            '<h1>PDF Remediation</h1><p>Open a run: <code>python3 app.py ../runs/&lt;name&gt;/&lt;label&gt;</code>. '
            'The home page with books and runs comes in a later version.</p></main></body></html>')
