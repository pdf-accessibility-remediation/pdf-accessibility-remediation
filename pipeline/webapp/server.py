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
    /api/run/<run>/stop-other  Stop the Other Review: Ctrl+C to a review page the app did not start (the lock's holder)
    /api/run/<run>/discard     Discard the open session: review_workorder.py --discard-open (marked abandoned, kept);
                               refused while its review page is open or past Finish
    /api/run/<run>/ocr         Review OCR Text: the OCR-only review page (review_ocr.py --serve), a job that waits on a person
    /api/run/<run>/bring-back  {file, by, note}: Bring Back an Edited PDF: handedit.py import of a PDF in uploads/.edited/
                               (sent by /upload), as a new run that stops for its review (no AI call); {resume: label} starts
                               an edited copy brought back but never run; refused before anything runs
    /api/run/<run>/upload      the edited PDF's own bytes (Content-Type application/pdf, X-Pdfrem-Upload: 1, its name in
                               X-File-Name), at most upload_max_mb: saved in uploads/.edited/ (never listed as a book) under
                               a cleaned name, 200 {file, sha256, size}
    /run/<run>/checks          the Manual Checks page (webapp/manualpage.py); GET /api/run/<run>/checks its data;
    POST /api/run/<run>/checks/draft and /checks/record: through review/manual.py in this process (no job), 200, 400 with
                               each problem tied to its field, or 409 with the refusal in its own words
Every POST's Content-Length must be digits and at most MAX_BODY (65,536), checked before reading. /run/<run>/ocr stays reserved (404):
OCR text is approved on the review page, or on the OCR-only page, both on the review server.

Every response forbids framing (X-Frame-Options: DENY, CSP frame-ancestors 'none'), so another site cannot show a run
page in a frame and trick a click. HTML pages also get script-src 'self' plus the sha256 of the page's one inline script,
computed when it is served, so a javascript: link or any other script in a report's text never runs.

A run is named by its path under the runs folder (teika/rv1, batches/d1/fishers): the shortest prefix of the request
path that is a folder holding record.json. Every segment is checked (no empty, ".", "..", dot-names or backslashes),
and no request string is ever joined onto a path: each segment (a run's folders, a batch, a previous result's id, a job
id) only picks an entry from the real folder's listing (config.entry). The folder and every file are then resolved
with realpath and must stay inside the runs folder, and a file is served only when its name is in the run's list.
Nothing outside the runs folder is ever served (.env, samples/, pipeline/).
"""
import os, re, json, html, base64, hashlib, tempfile, threading, traceback, urllib.parse, datetime
from http.server import BaseHTTPRequestHandler
from html.parser import HTMLParser
from review.server import local_request, Server
from review import sessions as S
from lib.titles import title_case as TC
from . import config, jobs, runs, manualpage as MP, downloads as DL, home as HM, books as BK, newrun as NR, batches as BT, names as NMS
RUNS_MOD = runs                                       # find_run's own `runs` is the runs folder
from review import manual as M
from lib import release as REL, runlock

FILES = ('review.html', 'review.md', 'han_review.csv')
TYPES = {'.html': 'text/html; charset=utf-8', '.md': 'text/plain; charset=utf-8', '.csv': 'text/csv; charset=utf-8', '.pdf': 'application/pdf',
         '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8'}
RESERVED = ('ocr',)                                          # /run/<run>/checks is the Manual Checks page (#38)
UPLOAD_IDLE = 60                                               # seconds an upload may send nothing before it is dropped
MAX_BODY = 65536                                              # a POST body: digits only in Content-Length, at most this

def segments(p):
    """The decoded path segments, or None when any is unsafe."""
    segs = [urllib.parse.unquote(x) for x in p.split('/') if x != '']
    for x in segs:
        if x in ('.', '..') or x.startswith('.') or '\\' in x or '\x00' in x or '/' in x: return None
    return segs

def inside(root, p):
    root = os.path.realpath(root); p = os.path.realpath(p)
    return p == root or p.startswith(root + os.sep)

def find_run(runs, segs, waiting=False, pending=None):
    """(run name, its folder, the remaining segments) for the shortest prefix holding record.json, or None. Each segment
    picks an entry from the folder's own listing (config.entry): the folder is built from names on disk only, then
    resolved and kept inside the runs folder (a symlink out of it is refused). waiting: a run stopped for its first
    review (runs.waiting()) counts too; only the run page, its state and its review, apply and stop actions ask for it.
    pending: a callable(folder) → True for a run started from the home page that has no result yet (runs.pending): only
    the run page, its state and its estimate, spend, dismiss and retry actions ask for it."""
    base = os.path.realpath(runs); d = base; names = []
    for i, x in enumerate(segs, 1):
        d = config.entry(d, x)
        if d is None: return None
        names.append(os.path.basename(d))                # the run's name from the folder's own listing, never the request's
        d = os.path.realpath(d)                          #   text (CodeQL py/path-injection: every later path is built from it)
        if not d.startswith(base + os.sep) or not os.path.isdir(d): return None
        if os.path.isfile(os.path.join(d, 'record.json')) or (waiting and RUNS_MOD.waiting(d)) or (pending and pending(d)): return '/'.join(names), d, segs[i:]
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
    """A batch's folder, runs/batches/<label>, picked from the batches folder's listing; or None. (From #45 the batch page
    works before summary.html exists.)"""
    BB = os.path.realpath(os.path.join(runs, 'batches'))
    B = config.entry(BB, label)
    if B is None: return None
    B = os.path.realpath(B)
    return B if B.startswith(BB + os.sep) and os.path.isdir(B) else None

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
          'manual.js': os.path.join(config.HERE, 'manual.js'), 'home.js': os.path.join(config.HERE, 'home.js'), 'batch.js': os.path.join(config.HERE, 'batch.js'),
          'trash.js': os.path.join(config.HERE, 'trash.js'), 'shared.js': os.path.join(config.HERE, 'shared.js'), 'palette.css': os.path.join(config.PIPELINE, 'review', 'palette.css')}
SKIP = '<a class="skip" href="#main">Skip to the content</a>'

FRAME = {'X-Frame-Options': 'DENY', 'Content-Security-Policy': "frame-ancestors 'none'"}   # every response: never in a frame
# an error in the app itself, as the page says it; the details (and where they are) are in runs/.app/server.log only
ERROR_500 = 'The app hit an error and couldn\'t do this. Try again; if it happens again, tell whoever looks after the app.'
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

def with_panel(page, run, current=None, waiting=False):
    """review.html as served: the panel's stylesheet, its place (after the page's header, so its h2 follows the page's h1;
    else after the skip link) and its script added. `current`: the session whose result the page shows, so the panel can
    tell when an apply has made a newer one. The file on disk is never changed; opened as a file it is the plain report."""
    box = f'\n<div id="pdfrem-panel" data-run="{html.escape(run)}"' + (f' data-current="{html.escape(str(current))}"' if current else '') + \
          (' data-waiting="1"' if waiting else '') + '></div>\n'
    head = '<link rel="stylesheet" href="/app/panel.css">\n'
    i = page.find('</head>'); page = page[:i] + head + page[i:] if i >= 0 else head + page
    if '</header>' in page: page = page.replace('</header>', '</header>' + box, 1)
    elif SKIP in page: page = page.replace(SKIP, SKIP + box, 1)
    else: page = after_body(page, box)
    page = with_strip(page, run)
    i = page.rfind('</body>'); js = '<script src="/app/panel.js" defer></script>\n'
    return page[:i] + js + page[i:] if i >= 0 else page + js

SHIP_CARD = 'aria-labelledby="ship-h"'
def with_strip(page, run):
    """The Manual Checks strip's place, right after the "Ready to Ship?" card's own section (str.find: the card holds no
    nested section, and book text in it is escaped); a page with no card gets none here, and panel.js puts the strip at
    the end of the Run Actions panel instead."""
    i = page.find(SHIP_CARD)
    j = page.find('</section>', i) if i >= 0 else -1
    if j < 0: return page
    box = f'\n<div id="pdfrem-checks" data-run="{html.escape(run)}"></div>\n'
    return page[:j + len('</section>')] + box + page[j + len('</section>'):]

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

APPBAR_MARK = 'aria-label="App"'
def with_appbar(page):
    """Every HTML page the app serves carries the app bar (the way home), right after its skip link, else right after
    <body>; a page that has one already is left as it is."""
    if APPBAR_MARK in page or 'data-home="1"' in page[:2000]: return page          # the home page has none (P1)
    bar = HM.appbar()
    if SKIP in page: return page.replace(SKIP, SKIP + bar, 1)
    return after_body(page, bar)

def make(s, setup, code=None):
    """The server, bound to 127.0.0.1:port (no fallback: a busy port is an error the caller reports). The panel's files are
    read once, here, so the pages always match the code this server runs, even if the files on disk change under it;
    `code` is the fingerprint of that code (config.code_fingerprint), which /api/ping reports."""
    J = s['jobs']
    def applog(msg):                                   # a writer's note (a draft not cleared, G3): runs/.app/server.log
        with open(os.path.join(J, 'server.log'), 'a', encoding='utf-8') as f: f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")} {msg}\n')
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
            if ctype.startswith('text/html') and isinstance(body, str): body = with_appbar(body)
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
                self.send(500, {'error': ERROR_500})

        def do_POST(self):
            try: self.post()
            except BrokenPipeError: pass
            except Exception:
                with open(os.path.join(J, 'server.log'), 'a', encoding='utf-8') as f: f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")} POST {self.path}\n{traceback.format_exc()}\n')
                self.send(500, {'error': ERROR_500})

        def post(self):
            if not self.ours(): return self.send(403, {'error': 'not from the app\'s own pages'})
            p = urllib.parse.urlsplit(self.path).path
            if p == '/api/upload': return self.upload()
            if p.startswith('/api/run/') and p.endswith('/upload'): return self.upload_edited(segments(p[len('/api/run/'):]))
            if not self.json_ok(): return
            body = self.body
            if p == '/api/book/name':                             # a book's name, as a person sets it (webapp/names.py)
                b = BK.by_key(s, str(body.get('key') or ''))
                if not b: return self.send(409, {'error': 'This PDF\'s file has changed or is gone. Reload the page.'})
                try: n = NMS.set_book_name(s, b['key'], body.get('name'))
                except ValueError as e: return self.send(409, {'error': str(e)})
                return self.send(202, {'name': n, 'location': '/?renamed=' + b['key']})
            if p == '/api/credit':                                # U8: "Check Credit Again": a credit read (free, nothing of a book is sent)
                from . import spend as SPD
                d = SPD.check_credit(s)
                return self.send(200, {'usd': d['usd'], 'why': d['why'], 'words': None if d['usd'] is not None else SPD.credit_words(s)})
            if p == '/api/rename/batch-pdf':                      # T2: a batch PDF's "Edit Name": its display name, by sha256 (never a file or folder)
                B = batch_dir(s['runs'], str(body.get('label') or ''))
                bk = next((b for b in (BT.books_of(s, os.path.basename(B)) if B else []) if b.get('name') == str(body.get('book') or '')), None)
                if not bk or not bk.get('key'): return self.send(409, {'error': 'This PDF is no longer in the batch. Reload the page.'})
                try: n = NMS.set_book_name(s, bk['key'], body.get('name'))
                except ValueError as e: return self.send(409, {'error': str(e)})
                return self.send(200, {'name': n})
            if p in ('/api/rename/run', '/api/rename/batch'):    # My Workspace's "Edit Name" (Q4): the plain name only, never the folder
                if p == '/api/rename/run':
                    run = str(body.get('run') or '')
                    if run.startswith('batches/') or run not in dict(HM.run_folders(s['runs'])):
                        return self.send(409, {'error': 'This run is no longer in the list. Reload the page.'})
                    n = NMS.set_run_name(s, run, body.get('name'))
                else:
                    B = batch_dir(s['runs'], str(body.get('label') or ''))
                    if not B: return self.send(409, {'error': 'This batch is no longer in the list. Reload the page.'})
                    n = NMS.set_run_name(s, os.path.basename(B), body.get('name'), kind='batches')
                if not n: return self.send(409, {'error': 'Type a name first.'})
                return self.send(200, {'name': n})
            if p == '/api/batch/new':                             # New Batch: one free estimate job per book, then the batch page
                try: js = BT.start(s, setup, body.get('books') if isinstance(body.get('books'), list) else [], body.get('label'))
                except (ValueError, FileExistsError) as e: return self.send(409, {'error': str(e) if isinstance(e, ValueError) else 'A batch with this name already exists.'})
                jobs.tick(J, s)
                return self.send(202, {'jobs': len(js), 'location': f'/batch/{urllib.parse.quote(js[0]["run"].split("/")[1], safe="")}/'})
            if p == '/api/batch/new-later':                       # S7: "Save Batch for Later": the PDFs move in, no estimates
                try: BT.start(s, setup, body.get('books') if isinstance(body.get('books'), list) else [], body.get('label'), estimate=False)
                except (ValueError, FileExistsError) as e: return self.send(409, {'error': str(e) if isinstance(e, ValueError) else 'A batch with this name already exists.'})
                return self.send(202, {'location': '/?view=batches'})
            if p.startswith('/api/batch/'):
                bs = segments(p[len('/api/batch/'):])
                if not bs or len(bs) != 2 or bs[1] not in ('spend', 'again', 'dismiss', 'language', 'start', 'save', 'remove') or not batch_dir(s['runs'], bs[0]):
                    return self.send(404, {'error': 'no such batch'})
                label = os.path.basename(batch_dir(s['runs'], bs[0]))
                try:
                    if bs[1] == 'dismiss': return self.send(200, {'dismissed': jobs.dismiss(J, f'batches/{label}')})
                    if bs[1] == 'save': BT.save_name(s, label, body.get('label')); return self.send(202, {'location': '/?view=batches'})   # S7
                    if bs[1] == 'remove':                         # S7: back to the upload list while the batch hasn't started
                        BT.remove_saved(s, label, str(body.get('book') or '')); return self.send(200, {'removed': True})
                    if bs[1] == 'start':                          # S7: "Get the Estimates" on a saved batch
                        js = BT.start_saved(s, setup, label, body.get('label')); jobs.tick(J, s)
                        return self.send(202, {'jobs': len(js), 'location': f'/batch/{urllib.parse.quote(label, safe="")}/'})
                    if bs[1] == 'language' and body.get('all') is True:   # R10: "Use for All Waiting PDFs"
                        r = BT.answer_all(s, label, str(body.get('lang') or ''))
                        jobs.tick(J, s)
                        return self.send(202, {'answered': len(r['jobs']), 'left': r['left']})
                    if bs[1] == 'language':                       # D4: a PDF's "Language of the Scanned Pages", on its row
                        book = str(body.get('book') or '')
                        if any(jobs.related(x['run'], f'batches/{label}/{book}') and x['status'] in jobs.ACTIVE for x in jobs.all_jobs(J)):
                            return self.send(409, {'error': 'This PDF is being worked on: try again when it stops.'})
                        j = BT.answer_language(s, label, book, str(body.get('lang') or ''))
                    elif bs[1] == 'spend': j = BT.spend(s, label, body)
                    else: j = BT.again(s, label)[0]
                except ValueError as e: return self.send(409, {'error': str(e)})
                jobs.tick(J, s)
                return self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id']))})
            if p in ('/api/trash/plan', '/api/trash/move'):       # Move to Trash (#45 D8): what goes, then the move
                from . import trash as TR
                what = body.get('what')
                try:
                    if what == 'run': f = TR.plan_run if p.endswith('plan') else TR.move_run; r = f(s, str(body.get('run') or ''))
                    elif what == 'batch':
                        names = body.get('names') if isinstance(body.get('names'), list) else None
                        bd = batch_dir(s['runs'], str(body.get('label') or ''))
                        if not bd: return self.send(409, {'error': 'There is no such batch.'})
                        f = TR.plan_batch if p.endswith('plan') else TR.move_batch; r = f(s, os.path.basename(bd), [str(x) for x in names] if names is not None else None)
                    elif what == 'pdf': f = TR.plan_pdf if p.endswith('plan') else TR.move_pdf; r = f(s, str(body.get('key') or ''))
                    else: return self.send(409, {'error': 'Nothing to move.'})
                except TR.Refused as e: return self.send(409, {'error': str(e)})
                if p.endswith('move'): applog(f'moved to the Trash: {what} {body.get("run") or body.get("label") or body.get("key")} → {r.get("moved")}')
                return self.send(200, r)
            if p == '/api/new/estimate':                          # New Run: the free estimate job, then its run page
                try: j = NR.start_estimate(s, setup, str(body.get('book') or ''), body.get('run_name'), from_run=str(body.get('run') or '') or None)
                except ValueError as e: return self.send(409, {'error': str(e)})
                jobs.tick(J, s)
                return self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id'])), 'location': HM.run_href(j['run'])})
            segs = segments(p[len('/api/run/'):]) if p.startswith('/api/run/') else None
            if segs and len(segs) >= 3 and segs[-2] == 'checks' and segs[-1] in ('draft', 'record'):   # two-segment actions: the run is segs[:-2]
                return self.checks_post(segs[:-2], segs[-1], body)
            PEND = ('spend', 'estimate', 'dismiss', 'retry', 'language')
            if not segs or len(segs) < 2 or segs[-1] not in ('review', 'apply', 'stop', 'stop-other', 'discard', 'ocr', 'remove-older-pdfs', 'ship', 'replay', 'clear', 'bring-back') + PEND:
                return self.send(404, {'error': 'not found'})
            hit = find_run(s['runs'], segs[:-1], waiting=segs[-1] in ('review', 'apply', 'stop'), pending=(lambda d: runs.pending(s, d)) if segs[-1] in PEND else None)
            if not hit or hit[2]: return self.send(404, {'error': 'no such run'})
            run, R, _ = hit
            if segs[-1] in PEND:                                # a run started from the home page, before its result
                if not runs.pending(s, R): return self.send(409, {'error': 'This run has moved on: reload the page.'})
                try:
                    if segs[-1] == 'dismiss':
                        n = jobs.dismiss(J, run); return self.send(200, {'dismissed': n})
                    if segs[-1] == 'spend': j = NR.start_spend(s, run, R, body)
                    elif segs[-1] == 'estimate': j = NR.again_estimate(s, run, R)
                    elif segs[-1] == 'language': j = NR.answer_language(s, run, R, str(body.get('lang') or ''))   # D4
                    else: j = NR.start_rerun(s, run, R) if NR.retry_kind(R) == 'rerun' else NR.again_estimate(s, run, R)
                except ValueError as e: return self.send(409, {'error': str(e)})
                jobs.tick(J, s)
                return self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id']))})
            if segs[-1] == 'replay':                            # New Run from the Saved Reply (free)
                try: j = NR.start_replay(s, run, R, body.get('label'))
                except (ValueError, S.Refused) as e: return self.send(409, {'error': str(e)})
                jobs.tick(J, s)
                return self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id'])), 'location': HM.run_href(j['run'])})
            if runs.waiting(R):                                 # stopped for its first review: open the review page, apply, stop
                try:
                    if segs[-1] == 'review': j = runs.start_first_review(s, run, R, self.server.server_address[1], app_pid=os.getpid())
                    elif segs[-1] == 'apply': j = runs.start_first_apply(s, run, R)
                    else: j = runs.stop_review(s, run, R); return self.send(200, {'stopped': j['id']})
                except ValueError as e: return self.send(409, {'error': str(e)})
                jobs.tick(J, s)
                return self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id']))})
            if segs[-1] == 'ship':                              # Mark as Shipped, in this process, through review/manual.py ship()
                try: e = M.ship(R, str(body.get('by') or ''), str(body.get('note') or ''), shown_sha=body.get('shown_sha256') or None,
                                via='page', wait=runlock.REQUEST_WAIT, say=lambda *a: applog(f'{run}: ' + ' '.join(str(x) for x in a)), batch=False)
                except S.Refused as x: return self.send(409, {'error': str(x)})
                self.send(200, {'shipped': {'n': e['n'], 'shipped': e['shipped']}})
                threading.Thread(target=S.rebuild_batch, args=(R, lambda *a: None), daemon=True).start()
                return
            if segs[-1] not in ('clear', 'stop', 'stop-other') and REL.cleared(R):   # a cleared book is read only (#45): its own words first
                return self.send(409, {'error': S.CLEARED})
            if segs[-1] == 'clear':                             # "Clear This Book's Files" (#45): review/clear.py, its locks and its gate
                from review import clear as CL
                def busy():                                     # read under the dispatch lock while reviews/.lock is held (03 §10)
                    with jobs.locked(J): return jobs.busy(J, run, R)
                try: c = CL.clear(R, str(body.get('by') or ''), str(body.get('confirm') or ''), busy=busy, wait=runlock.REQUEST_WAIT)
                except S.Refused as e: return self.send(409, {'error': str(e)})
                applog(f'{run}: cleared by {c.get("by")}: {len(c.get("files") or [])} files, {c.get("freed_bytes")} bytes')
                return self.send(200, {'cleared': {'files': len(c.get('files') or []), 'bytes': c.get('freed_bytes'), 'shipment': c.get('shipment')}, 'location': '/'})
            if segs[-1] == 'remove-older-pdfs':                 # "Clean Up Space", in this process, through review/prune.py (its locks, its refusals)
                from review import prune
                chosen = body.get('chosen') if isinstance(body.get('chosen'), list) else []
                try: done = prune.remove(R, chosen, str(body.get('by') or ''), wait=runlock.REQUEST_WAIT,
                                         say=lambda *a: applog(f'{run}: ' + ' '.join(str(x) for x in a)))
                except S.Refused as e: return self.send(409, {'error': str(e)})
                return self.send(200, {'removed': len(done), 'bytes': sum(x['bytes'] for x in done)})
            try:
                if segs[-1] == 'review':
                    src = body.get('from')
                    j = runs.start_review(s, run, R, self.server.server_address[1], None if src in (None, '', 'latest') else str(src),
                                          bool(body.get('discard_open')), app_pid=os.getpid())
                elif segs[-1] == 'apply': j = runs.start_apply(s, run, R)
                elif segs[-1] == 'ocr': j = runs.start_ocr(s, run, R, self.server.server_address[1], app_pid=os.getpid())
                elif segs[-1] == 'discard': j = runs.start_discard(s, run, R)
                elif segs[-1] == 'bring-back':
                    j = (runs.resume_bring_back(s, run, R, str(body['resume'])) if body.get('resume') else
                         runs.start_bring_back(s, run, R, body.get('file'), body.get('by'), body.get('note')))
                elif segs[-1] == 'stop-other': return self.send(200, {'stopped': runs.stop_other(s, run, R)})
                else: j = runs.stop_review(s, run, R); return self.send(200, {'stopped': j['id']})
            except ValueError as e: return self.send(409, {'error': str(e)})
            jobs.tick(J, s)                                   # start it now if a place is free, rather than within the second
            self.send(202, {'job': runs.job_view(s, jobs.load(J, j['id']))})

        def upload_edited(self, segs):
            """Bring Back an Edited PDF's file: the PDF's own bytes (application/pdf, the app's X-Pdfrem-Upload header, its
            name in X-File-Name), streamed into the uploads folder's .edited/ (never listed as a book: webapp/books.py skips
            dot-folders) under a cleaned name (books.clean_upload_name), at most upload_max_mb. A new name for a different
            file, the same name for the same one."""
            self.close_connection = True                     # a refused body is never read to its end
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/pdf':
                return self.send(415, {'error': 'Choose a PDF.'})
            if self.headers.get('X-Pdfrem-Upload') != '1': return self.send(403, {'error': 'not from the app\'s own pages'})
            hit = find_run(s['runs'], segs[:-1]) if segs and len(segs) >= 2 else None
            if not hit or hit[2] or runs.waiting(hit[1]): return self.send(404, {'error': 'no such run'})
            if self.headers.get('Transfer-Encoding'): return self.send(411, {'error': 'the request has no valid length'})
            n = (self.headers.get('Content-Length') or '').strip()
            if not n.isdecimal() or not n.isascii(): return self.send(411, {'error': 'the request has no valid length'})
            n = int(n)
            if n > BK.limit_bytes(s): return self.send(413, {'error': f'The PDF is larger than the limit of {BK.limit_bytes(s) // (1 << 30) or 1} GB.'})
            try: name = BK.clean_upload_name(urllib.parse.unquote(self.headers.get('X-File-Name') or '', errors='strict'))
            except UnicodeDecodeError: name = None
            name = name or 'edited.pdf'
            head = self.rfile.read(min(n, 5))
            if head != b'%PDF-': return self.send(400, {'error': 'This is not a PDF.'})
            d = runs.edited_dir(s); os.makedirs(d, exist_ok=True)
            self.connection.settimeout(UPLOAD_IDLE)          # a browser that stops sending never holds a half-written file
            fd, part = tempfile.mkstemp(prefix='.upload-', suffix='.part', dir=d)
            try:
                h, got = hashlib.sha256(head), len(head)
                with os.fdopen(fd, 'wb') as f:
                    f.write(head)
                    while got < n:
                        b = self.rfile.read(min(1 << 20, n - got))
                        if not b: break
                        f.write(b); h.update(b); got += len(b)
                if got < n: return self.send(400, {'error': 'The upload stopped before the end of the file.'})
                sha = h.hexdigest(); stem, k = name[:-4], 1
                while True:                                  # the same file keeps its name; another file never replaces one
                    q = os.path.join(d, name)
                    if not os.path.exists(q): os.replace(part, q); break
                    if os.path.isfile(q) and REL.sha_file(q) == sha: break
                    k += 1; name = f'{stem}-{k}.pdf'
                applog(f'{hit[0]}: uploaded {name} ({got} bytes)')
                return self.send(200, {'file': name, 'sha256': sha, 'size': got})
            except TimeoutError: return self.send(400, {'error': 'The upload stopped before the end of the file.'})
            except OSError as e:
                try: return self.send(500, {'error': f'The PDF could not be saved ({e.strerror or e}).'})
                except OSError: return None                  # the browser has gone (Cancel): nothing to answer
            finally:
                if os.path.exists(part): os.remove(part)

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
                hit = find_run(s['runs'], segs, waiting=True, pending=lambda d: runs.pending(s, d)) if segs else None
                if hit and runs.waiting(hit[1]):
                    return self.send(200, runs.waiting_state(s, hit[0], hit[1])) if not hit[2] else self.send(404, {'error': 'no such run'})
                if hit and runs.pending(s, hit[1]):
                    return self.send(200, runs.pending_state(s, hit[0], hit[1])) if not hit[2] else self.send(404, {'error': 'no such run'})
                if hit and hit[2] == ['checks']: return self.send(200, MP.state(hit[1], hit[0]))   # the Manual Checks page's data
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
                    if BT.saved(s, os.path.basename(B)):                 # S7, T4: a saved batch opens its pop-up on the home page
                        return self.redirect('/?view=batches&open=' + urllib.parse.quote(os.path.basename(B), safe=''))
                    return self.send(200, BT.page(s, os.path.basename(B), closed=self.nav_closed()), 'text/html; charset=utf-8')   # the batch page (#45)
                if rest == ['summary.html']:                     # the batch dashboard, with the app bar (#45: every page links home)
                    f = os.path.realpath(os.path.join(B, 'summary.html'))
                    if not f.startswith(RUNS + os.sep) or not os.path.isfile(f): return self.send(404, {'error': 'not found'})
                    return self.send(200, self.text(f), 'text/html; charset=utf-8')
                if rest == ['summary.md']: return self.file(os.path.join(B, 'summary.md'))
                if len(rest) >= 1 and find_run(s['runs'], ['batches', segs[0], rest[0]], waiting=True, pending=lambda d: runs.pending(s, d)):
                    return self.redirect('/run/' + '/'.join(urllib.parse.quote(x) for x in ['batches', segs[0], rest[0]]) + '/')
                return self.send(404, {'error': 'not found'})
            if p.startswith('/run/'):
                segs = segments(p[len('/run/'):])
                if segs is None: return self.send(404, {'error': 'not found'})
                if len(segs) == 3 and segs[0] == 'batches' and segs[2] in ('summary.html', 'summary.md'):    # a review.html's ../summary.html: the dashboard
                    return self.redirect(f'/batch/{urllib.parse.quote(segs[1])}/' + segs[2])
                hit = find_run(s['runs'], segs, waiting=True, pending=lambda d: runs.pending(s, d))
                if not hit: return self.send(404, {'error': 'no such run'})
                run, R, rest = hit
                if runs.waiting(R) or runs.pending(s, R):                                  # before its first result: its page only
                    if rest: return self.send(404, {'error': 'not found'})
                    if not p.endswith('/'): return self.redirect(p + '/')
                    return self.send(200, self.in_batch(run, waiting_page(run, R, s)), 'text/html; charset=utf-8')
                if not rest:
                    if not p.endswith('/'): return self.redirect(p + '/')
                    return self.run_page(run, R)
                if len(rest) == 1 and rest[0] in RESERVED: return self.send(404, {'error': 'this page is not built yet'})
                if rest == ['download']:                                                   # a version's PDF or record ZIP (stage 3)
                    return self.download(run, R, q)
                if rest == ['checks']:                                                     # the Manual Checks page
                    if not os.path.isfile(os.path.join(R, 'record.json')): return self.send(404, {'error': 'no such run'})
                    if p.endswith('/'):                                    # …/checks/ → …/checks: its relative "checks?recorded=" (34 F1)
                        return self.redirect(p.rstrip('/') + ('?' + url.query if url.query else ''))
                    rc = (q.get('recorded') or [''])[0]
                    return self.send(200, MP.page(R, run, rc if rc in REL.SECTIONS else None), 'text/html; charset=utf-8')
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
                        return self.send(200, with_version(REL.no_statement(t), run, sid), 'text/html; charset=utf-8')
                    return self.send(200, md_page(t, run, sid, base), 'text/html; charset=utf-8')   # review.md with a way back
                return self.file(f)
            if p in ('/new', '/new-batch'): return self.redirect('/')   # T4: New Run and New Batch are pop-ups on the home page
            if p == '/api/form':                                  # T4: a pop-up's contents (webapp/shared.js puts them in a dialog)
                what = (q.get('what') or [''])[0]
                if what == 'run': h = NR.form_part(s, (q.get('book') or [''])[0], (q.get('run') or [''])[0] or None)
                elif what == 'batch':
                    sv = (q.get('saved') or [''])[0]
                    if sv and not (batch_dir(s['runs'], sv) and BT.saved(s, os.path.basename(batch_dir(s['runs'], sv)))):
                        return self.send(409, {'error': 'This batch has started or is gone. Reload the page.'})
                    h = BT.form_part(s, q.get('book') or [], saved=os.path.basename(batch_dir(s['runs'], sv)) if sv else None)
                else: return self.send(404, {'error': 'no such form'})
                return self.send(200, {'html': h})
            if p == '/book': return self.redirect('/')            # the name page went away (Q1, Q3): Edit Name is on the home page
            if p.startswith('/api/batch/'):
                bs = segments(p[len('/api/batch/'):])
                B = batch_dir(s['runs'], bs[0]) if bs and len(bs) == 1 else None
                if not B: return self.send(404, {'error': 'no such batch'})
                return self.send(200, BT.state(s, os.path.basename(B)))
            if p == '/':
                return self.send(200, HM.page(s, (q.get('q') or [''])[0], (q.get('n') or ['25'])[0], test=bool(s.get('test_reply_dir')),
                                              added=(q.get('added') or [None])[0], bn=(q.get('bn') or ['25'])[0],
                                              renamed=(q.get('renamed') or [None])[0], view=(q.get('view') or ['runs'])[0],
                                              group=(q.get('group') or [''])[0], trashed=bool(q.get('trashed'))), 'text/html; charset=utf-8')
            self.send(404, {'error': 'not found'})

        def json_ok(self):
            """A JSON POST's own checks (type, a digits-only length within MAX_BODY, a JSON object): self.body, or the
            refusal sent and False."""
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
                self.send(415, {'error': 'the app\'s pages send JSON'}); return False
            n = (self.headers.get('Content-Length') or '').strip()   # checked before reading: rfile.read(-1) would wait for the
            if not n.isdecimal() or not n.isascii(): self.send(411, {'error': 'the request has no valid length'}); return False   # client
            if int(n) > MAX_BODY: self.send(413, {'error': 'The request is too large.'}); return False
            try: body = json.loads(self.rfile.read(int(n)) or b'{}')
            except ValueError: self.send(400, {'error': 'not JSON'}); return False
            if not isinstance(body, dict): self.send(400, {'error': 'not a JSON object'}); return False
            self.body = body; return True

        def upload(self):
            """POST /api/upload: "Add a Book". The PDF itself is the body (Python 3.13 has no form parser), so four checks
            come first, each required: Content-Type application/pdf, the app's own X-Pdfrem-Upload header (a browser must ask
            first, and the app answers no such question), local_request (in post()), and a digits-only Content-Length at
            most upload_max_mb (no chunked bodies). A stalled sender ends the request after 60 s."""
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/pdf':
                return self.send(415, {'error': 'This file isn\'t a PDF.'})
            if self.headers.get('X-Pdfrem-Upload') != '1': return self.send(403, {'error': 'not from the app\'s own pages'})
            if self.headers.get('Transfer-Encoding'): return self.send(411, {'error': 'the request has no valid length'})
            n = (self.headers.get('Content-Length') or '').strip()
            if not n.isdecimal() or not n.isascii(): return self.send(411, {'error': 'the request has no valid length'})
            if int(n) > BK.limit_bytes(s):
                self.close_connection = True
                return self.send(413, {'error': f'This file is larger than the limit of {BK.limit_bytes(s) // (1 << 30) or 1} GB.'})
            try: name = urllib.parse.unquote(self.headers.get('X-Pdfrem-Filename') or '', errors='strict')
            except UnicodeDecodeError: name = ''
            self.connection.settimeout(60)
            try: b = BK.receive(s, self.rfile, int(n), name)
            except BK.Refused as e:
                self.close_connection = True
                return self.send(e.status, {'error': e.words})
            except (TimeoutError, OSError):
                self.close_connection = True
                return self.send(400, {'error': 'The upload stopped before the whole file arrived. Try again.'})
            applog(f'book added: {b["file"]} ({b["key"][:16]})')
            self.send(201, {'book': {k: b[k] for k in ('key', 'name', 'file', 'pages', 'size', 'group', 'locked', 'unreadable')}})

        def checks_post(self, rsegs, act, body):
            """POST …/checks/draft and …/checks/record: through review/manual.py, the one writer (the record lock, 5 s at most)."""
            hit = find_run(s['runs'], rsegs)
            if not hit or hit[2]: return self.send(404, {'error': 'no such run'})
            run, R, _ = hit
            sec = body.get('section')
            if sec not in REL.SECTIONS: return self.send(400, {'error': 'unknown section'})
            try:
                if act == 'draft':
                    at = M.save_draft(R, sec, body.get('data'), str(body.get('saved_at') or ''), body.get('for_sha256'), wait=runlock.REQUEST_WAIT)
                    return self.send(200, {'saved_at': at})
                c = M.record(R, sec, body.get('data'), shown_sha=body.get('shown_sha256') or None, via='page', wait=runlock.REQUEST_WAIT,
                             say=lambda *a: applog(f'{run}: ' + ' '.join(str(x) for x in a)), draft_saved_at=body.get('draft_saved_at'), batch=False)
            except REL.Invalid as e: return self.send(400, {'errors': [{'field': f, 'message': m} for f, m in e.errors]})
            except S.Refused as e: return self.send(409, {'error': str(e)})
            except ValueError as e: return self.send(400, {'error': str(e)})
            self.send(200, {'recorded': {'id': c['id'], 'section': sec}})
            threading.Thread(target=S.rebuild_batch, args=(R, lambda *a: None), daemon=True).start()   # after the reply (F7)

        def download(self, run, R, q):
            """GET /run/<run>/download?what=pdf|record&v=current|<version id>: the version is one of the run's own
            (webapp/downloads.py versions()); everything is opened in one moment under the record lock, then streamed."""
            if not os.path.isfile(os.path.join(R, 'record.json')): return self.send(404, {'error': 'no such run'})
            what, v = (q.get('what') or [''])[0], (q.get('v') or ['current'])[0]
            base = '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/'
            if what not in ('pdf', 'record'): return self.send(404, refused_page('There is no such download.', base), 'text/html; charset=utf-8')
            try: d = DL.prepare(R, run, v, what)
            except DL.Refused as e:
                why = e.args[0] if e.args else None
                return self.send(409 if why else 404, refused_page(why or 'This version of the book is not available to download.', base), 'text/html; charset=utf-8')
            self.send_response(200)
            self.send_header('Content-Type', d['ctype']); self.send_header('Content-Disposition', REL.disposition(d['name']))
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', FRAME['X-Frame-Options']); self.send_header('Content-Security-Policy', FRAME['Content-Security-Policy'])
            if what == 'pdf':
                fh = d['fh']
                try:
                    self.send_header('Content-Length', str(os.fstat(fh.fileno()).st_size)); self.end_headers()
                    for b in iter(lambda: fh.read(1 << 20), b''): self.wfile.write(b)
                finally: fh.close()
            else:
                self.end_headers()                       # HTTP/1.0, no Content-Length: the end of the stream ends the body
                DL.stream_zip(self.wfile, d)
                self.wfile.flush()
                try: DL.note_download(d)                 # every byte written: the download is recorded (#45, clearing's gate)
                except Exception as e: applog(f'{run}: download not recorded ({type(e).__name__}: {e})')

        def run_page(self, run, R):
            f = os.path.join(R, 'review.html')
            rec = os.path.realpath(os.path.join(R, 'record.json'))
            cur = S.current_id((runs.load(rec) if rec.startswith(RUNS + os.sep) else None) or {})
            f = os.path.realpath(f)                                                  # checked inside the runs folder first
            t = self.text(f) if f.startswith(RUNS + os.sep) and os.path.isfile(f) else None
            if t is not None: return self.send(200, self.in_batch(run, with_panel(with_app_header(card_border(REL.no_statement(t), R), s, run, R), run, cur)), 'text/html; charset=utf-8')
            return self.send(200, self.in_batch(run, no_dashboard(run, R, cur, s)), 'text/html; charset=utf-8')

        def in_batch(self, run, page):
            """A book's page inside a batch (runs/batches/<label>/<name>) gets the batch's side column."""
            sg = run.split('/')
            if len(sg) != 3 or sg[0] != 'batches': return page
            try: return BT.with_nav(with_appbar(page), s, sg[1], sg[2], closed=self.nav_closed())
            except Exception: return page

        def nav_closed(self):
            """The side list's open or closed choice, from the cookie batch.js sets (D7: the page is served already laid out,
            so switching PDFs does not shift it); None when no choice was made (a narrow screen then starts closed)."""
            m = re.search(r'(?:^|;\s*)pdfrem_bn=(open|closed)\b', self.headers.get('Cookie') or '')
            return None if not m else m.group(1) == 'closed'

    return Server(('127.0.0.1', s['port']), H)

def card_border(page, R):
    """review.html as the run page serves it: while the PDF on disk is not the one the record describes (changed by hand, a
    Ready book's or a shipped one's), the "Ready to Ship?" card loses its green border, as the strip says (review 22 N8, 24,
    26 Q1). review.html on disk is not rebuilt for it: opened as a file it keeps the border until it is next rebuilt."""
    green = '<section class="ship yes" aria-labelledby="ship-h">'
    if green not in page: return page
    rec = runs.load(os.path.join(R, 'record.json')) or {}
    try: changed = MP.disk_state(R, rec)['same'] is False
    except (OSError, ValueError, KeyError, TypeError): return page
    return page.replace(green, '<section class="ship" aria-labelledby="ship-h">', 1) if changed else page

def app_header(s, run, R, pages=None):
    """The run page's header as the app shows it (P7, Patrick 2026-11-06; Patrick's test 2026-11-07, Q6, Q8): at the top of
    the screen, the PDF's display name and "Source PDF:", then the run's details on one line (runs.details: Run Name, pages,
    when it ran, the AI and its cost); for a PDF in a batch, "Assigned to the batch "<name>"" with "Open the Batch Page";
    "Home Page" on the right, inside the header (the app bar's own nav, so with_appbar adds none). No codes or file names
    beyond "Source PDF:". review.html on disk keeps its own header."""
    name, file = runs.book_of(s, run, R)
    sg = run.split('/')
    inb = len(sg) == 3 and sg[0] == 'batches'             # S3: a batch PDF's buttons are on its batch line (with_nav adds the list's)
    batch = (f'<div class="pp-hd-batch"><span>Assigned to the batch "{html.escape(NMS.shown_run(s, run))}"</span>{HM.appbar()}</div>') if inb else ''
    src_bar = not inb and bool(file)                     # U3: no list button here, so "Home Page" ends the "Source PDF:" line
    return (f'<header class="top pp-head pp-hd{"" if inb else " pp-run-hd"}">{HM.title_row(html.escape(name), bar=not inb and not file)}'
            + (f'<div class="mc-book pp-hd-src"><span class="hm-file">Source PDF: {html.escape(file)}</span>{HM.appbar() if src_bar else ""}</div>' if file else '')
            + '<p class="pp-hd-det">' + ' · '.join(html.escape(x) for x in runs.details(s, run, R, pages)) + f'</p>{batch}</header>')

def with_app_header(page, s, run, R):
    """review.html as served, with its own header (a file name, the prompt, the model, the run label) replaced by app_header()."""
    a = page.find('<header class="top">'); b = page.find('</header>', a)
    if a < 0 or b < 0: return page
    m = re.search(r'· (\d[\d,]*) pages ·', page[a:b])
    page = page[:a] + app_header(s, run, R, m.group(1) if m else None) + page[b + len('</header>'):]
    return re.sub(r'<title>[^<]*</title>', lambda _: f'<title>{html.escape(runs.book_of(s, run, R)[0])}</title>', page, count=1)

def no_dashboard(run, R, current=None, s=None):
    """A run with no review.html (older runs): the panel, the review.md link and a line saying there is no dashboard.
    No rebuild: report_html.py would write into the run."""
    rm = os.path.realpath(os.path.join(R, 'review.md'))           # checked inside the run folder before isfile
    md = '<p><a class="pp-btn" href="review.md">Open the Report</a> <span class="pp-note">what a person should check</span></p>' if rm.startswith(os.path.realpath(R) + os.sep) and os.path.isfile(rm) else ''
    return with_panel(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                      f'<title>{html.escape(runs.book_of(s, run, R)[0] if s else run)}</title><link rel="stylesheet" href="/app/palette.css"></head><body class="pp-page">\n{SKIP}'
                      + (app_header(s, run, R) if s else f'<header><h1>{html.escape(run)}</h1></header>') + '<main id="main" tabindex="-1">'
                      f'<p>This run has no dashboard: it was made before the dashboards, or without one.</p>{md}</main></body></html>', run, current)

def waiting_page(run, R, s=None):
    """A run before its first result: stopped for its first review (REVIEW=1: the panel's "Open the Review Page," then
    "Apply"), or started from the home page and estimating, ready to Spend, running, stopped or failed (the panel follows
    it). The book is named by its display name with "Source PDF:" under it, and the Run Name."""
    name, file = runs.book_of(s, run, R) if s else (runs.waiting_title(run, R), '')
    head = app_header(s, run, R) if s else f'<header><h1>{html.escape(name)}</h1></header>'
    return with_panel(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                      f'<title>{html.escape(name)}</title><link rel="stylesheet" href="/app/palette.css"></head><body class="pp-page">\n{SKIP}'
                      f'{head}<main id="main" tabindex="-1"></main></body></html>',
                      run, waiting=True)

def refused_page(message, base):
    """A download that cannot be given now: its reason in plain words, and a way back (the person followed a link)."""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Download Not Available</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css">'
            f'</head><body class="pp-page">\n{SKIP}<header><h1>Download Not Available</h1></header><main id="main" tabindex="-1"><div class="pp">'
            f'<p>{html.escape(message)}</p><p><a class="pp-btn" href="{html.escape(base)}">Back to the Run Page</a></p></div></main></body></html>')
