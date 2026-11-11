"""review/server.py: the review page, served on this computer only (127.0.0.1). Python's standard library, no new packages.

Routes (all call review/core.py; a later front end can replace this file and page.html without touching the pipeline):
    GET  /                       the page, with review_items.json built in
    GET  /review_pages/…  /_audit/figures/…  /_audit/ocr_words/…   page images, figure crops, OCR word sheets
                                 (nothing else in the run folder is served: the files are listed when the server starts, and a
                                 request path is only looked up in that list, never joined onto a folder). A page image is
                                 rendered the first time it is asked for.
    GET  /word/<id>.png          one OCR word cut from its word sheet (the image the AI read)
    GET  /result/review.html …   files the caller lists (files=): a reopened review links the run's current result
    POST /save    {reviewer, decisions, additions, session_name, session_notes, saved_at}  → saved to review_decisions.json;
                                 returns problems (core.problems: what the check would drop and additions refused, each with
                                 the card it belongs to) and gaps (no H1, figures without alt): the Finish dialog's check.
                                 Refused once Finish has started
    POST /keep    the same body → saved to review_decisions.json only: the page's auto-save, about a second after each
                                 change (the browser's copy stays as a backup); refused once Finish has started; a draft
                                 older than the one on disk (saved_at) is not written. Returns problems and the gaps still open,
                                 so each field is marked as it is saved.
                                 /save and /keep also return each section move as reviewed (the AI's, changed or not, and added ones): its preview, in the
                                 order the executor makes them and with the reviewed text rules (move_previews: {card id: preview})
    POST /draft   the same body as /keep → kept as /keep does, then a draft PDF built from it in the background (202):
                                 the same check as Finish, then apply.py, into this server's own temporary folder (removed
                                 when the server stops; nothing in the run folder or reviews/ is written). One at a time;
                                 refused once Finish has started
    GET  /draft                  the draft's state: {state: idle | building | ready | failed, elapsed | seconds, basis (the
                                 saved_at it was built from), result: {problems (as /keep's, for this draft), moves, rejected,
                                 failed, dropped}, error}
    GET  /draft.pdf              the draft, once ready, as <book>_draft.pdf (a download). Always the one fixed file
    POST /finish  {…, accept_unreviewed, gaps_ack}            → review.json and the reviewed workorder.json; the server stops.
                                 Not finished yet: 200 with needs: "invalid" (and problems) while a card's choice would be
                                 dropped (problems' unplaced never blocks), needs: "unreviewed" (and the list) while
                                 items are unreviewed, or needs: "gaps" while a gap has no reason, unless the body accepts
                                 them (a normal step of the flow, so not an HTTP error the browser logs)
    GET  /ocr/text/<n>.json      the text of PDF page n, for the OCR Text section: only pages the section can show
                                 (review/ocr.py showable_pages), from an exact-path list made at start
    POST /ocr-verdict {verdict, reviewer, reason, pages, reads, to, close}  → review/ocr.py record(): written at once, on its
                                 own (not with Finish), dated the day it is recorded. close (OCR-only mode, Finish OCR Review):
                                 the server stops once it is written
    POST /close                  OCR-only mode (review_ocr.py --serve): Close Without a Verdict, the server stops

Every request passes a gate: once the server is stopping (Ctrl+C, Stop, Finish done) a new one is refused, and serve()
returns only after every request already inside has ended (a request that stalls gives up after 30 s, the handler's
socket timeout), so a write is never cut off between its files, and no page
image is still being rendered by PDFium when the process ends (that crashed it on exit, code 139).

Modes: the work-order review (review_items.json in R; the first review serves the run folder, a reopen serves
reviews/), and the OCR-only page (data= given, no decisions). run_dir is the run folder (for the OCR verdict and text).

Requests must come from the page itself: the Host must be this server's, and a POST must be JSON from the same origin,
so another web page open in the browser cannot submit a review (a plain form or a no-cors fetch cannot send JSON). Every
response forbids framing (X-Frame-Options: DENY, CSP frame-ancestors 'none'), so another page cannot show this one in a
frame and trick a click on Finish.
"""
import os, re, json, time, shutil, datetime, tempfile, threading, webbrowser, mimetypes, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from . import core
from lib import runlock

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html')
SERVED = ('figures', 'ocr_words')                     # folders under _audit/ whose files the page shows

class Server(ThreadingHTTPServer):
    """The default listen queue is 5. While PDFium renders the first page images the accept loop stalls, a page full of
    cards overflows the queue, and the browser gets a reset connection: a broken thumbnail until something asks again."""
    request_queue_size = 128

def local_request(handler, port):
    """The request names this server as its host (no DNS rebinding) and, if it says where it comes from, the page.
    Shared with the app (webapp/server.py)."""
    hosts = {f'localhost:{port}', f'127.0.0.1:{port}'}
    origin = handler.headers.get('Origin')
    return handler.headers.get('Host') in hosts and (origin is None or origin in {f'http://{h}' for h in hosts})

def when(stamp):
    """A draft's saved_at as a moment: the browser's ISO time (2026-10-31T12:51:59.343Z) or the server's (…+00:00)."""
    return datetime.datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))

def check_return_to(url):
    """--return-to: an http URL on this computer (127.0.0.1 or localhost, with a port), so the page never sends the reviewer
    elsewhere. Returns the URL; raises ValueError."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'http' or u.hostname not in ('127.0.0.1', 'localhost') or u.username or u.password or not u.port or u.netloc not in (f'127.0.0.1:{u.port}', f'localhost:{u.port}'):
        raise ValueError(f'only http://127.0.0.1:<port>/… or http://localhost:<port>/… is accepted, not {url!r}')
    return url

DRAFT_PREFIX = 'review-draft-'

def sweep_drafts():
    """Remove the draft folders of review servers that ended without removing their own (killed): each holds the pid
    of the server that made it. A folder whose pid file can't be read is left alone."""
    top = tempfile.gettempdir()
    for n in os.listdir(top):
        d = os.path.join(top, n)
        if not n.startswith(DRAFT_PREFIX) or not os.path.isdir(d) or os.path.islink(d): continue
        try: pid = int(open(os.path.join(d, 'pid'), encoding='utf-8').read().strip())
        except (OSError, ValueError): continue
        try: os.kill(pid, 0); continue                 # still running
        except ProcessLookupError: pass
        except (PermissionError, OverflowError): continue
        shutil.rmtree(d, ignore_errors=True)

def draft_name(book):
    """The draft's download name: the book's file name with _draft.pdf, and nothing a header could misread."""
    stem = os.path.splitext(os.path.basename(str(book or '')))[0]
    stem = re.sub(r'[^\w.\- ]+', '_', stem).strip(' ._') or 'book'
    return f'{stem}_draft.pdf'

def serve(R, date, port=8765, open_browser=True, files=None, return_to=None, run_dir=None, lock_held=False, data=None, wo=None):
    """files: {url: path} served as they are, beside the review's own (review_workorder.py --reopen: the current result).
    return_to: the app's run page, which the page goes to after Finish and links back to. run_dir: the run folder (default
    R). lock_held: this process holds the run's reviews/.lock (a reopen, the OCR-only page). data (with wo, the work order
    whose OCR-word readings the OCR section shows): the OCR-only page, which has no decisions."""
    from . import ocr as O, sessions as S
    R = os.path.abspath(R); run_dir = os.path.abspath(run_dir or R)
    if return_to: check_return_to(return_to)
    ocr_only = data is not None
    if ocr_only: ai = None
    else:
        data = core.load(os.path.join(R, 'review_items.json'))
        ai = core.load(os.path.join(R, 'workorder.ai.json'))
        if data is None or ai is None: raise SystemExit(f'{R} is not waiting for a review (no review_items.json / workorder.ai.json)')
    items = data['items']
    digest = core.load(os.path.join(R, '_audit', 'digest.json'), {}) or {}
    if ocr_only and not digest: digest = core.load(os.path.join(S.P(run_dir)['audit'], 'digest.json'), {}) or {}   # the kept digest, if any
    core.pages_to_render(items, data.get('pages', 0))        # also for runs prepared before every card had page images
    if not ocr_only and 'addable' not in data: data['addable'] = core.addable(ai, digest); data['add_kinds'] = core.ADD_KINDS
    adds = data['addable']
    saved = core.load(os.path.join(R, 'review_decisions.json'), {}) or {}
    done = threading.Event(); finishing = threading.Event(); result = {}
    render_lock = threading.Lock()                    # pdfium is not thread-safe: one page image at a time
    write_lock = threading.Lock()                     # every write of this server, one at a time (auto-save, the Finish check and Finish can race)
    gate = threading.Condition(); inside = {'n': 0, 'closed': False}   # POSTs under way; closed: the server is stopping
    draft = {'state': 'idle'}; draft_lock = threading.Lock(); draft_proc = {}   # Build a Draft PDF: its state, and apply.py while it runs
    draft_dir = None
    if not ocr_only:
        sweep_drafts()
        draft_dir = tempfile.mkdtemp(prefix=DRAFT_PREFIX)
        with open(os.path.join(draft_dir, 'pid'), 'w', encoding='utf-8') as f: f.write(str(os.getpid()))
    draft_pdf = os.path.join(draft_dir, 'draft.pdf') if draft_dir else None

    def stop_draft():
        """Stop a draft being built and remove the draft folder: the server is stopping."""
        with draft_lock: draft['stopping'] = True; p = draft_proc.get('p')
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(5)
            except Exception: p.kill()
        if draft_dir: shutil.rmtree(draft_dir, ignore_errors=True)

    def first_check():
        """15 (page changes in one step): what /keep answers for the saved choices the page starts from (its problems, the gaps
        and each move's preview), so the line beside Finish and the cards' marks come with the page; None on the OCR-only
        page, or when it can't be worked out (the page's first save then brings it, as before)."""
        if ocr_only: return None
        try:
            d = saved.get('decisions') if isinstance(saved.get('decisions'), dict) else {}
            a = [x for x in saved.get('additions') or [] if isinstance(x, dict)] if isinstance(saved.get('additions'), list) else []
            rv = str(saved.get('reviewer') or '').strip()
            wo = core.apply_decisions(ai, items, d); core.add_entries(wo, a, adds, rv)   # as /keep's build()
            probs, gaps = core.problems(R, ai, items, d, a, adds, rv, set_in)
            return {'problems': probs, 'gaps': gaps, 'move_previews': core.move_previews(data, d, a, wo)}
        except Exception: return None

    sizes = {}
    def img_sizes():
        """15: {address: [width, height]} of every image the page can show, so each image's box is set before it arrives
        and no card grows when it loads: a page image already rendered by its file, one not rendered yet by its PDF page's
        size (pdfium renders it at that size, scale 1), the figure crops and word sheets by their files. Worked out once."""
        if sizes: return sizes
        from PIL import Image
        def dim(f):
            try:
                with Image.open(f) as im: return list(im.size)
            except Exception: return None
        doc = None
        with render_lock:                             # pdfium is not thread-safe: page images render in other threads
            try:
                for n in range(1, data.get('pages', 0) + 1):
                    f = os.path.join(R, 'review_pages', f'page_{n:03d}.png')
                    if os.path.exists(f): d = dim(f)
                    else:
                        if doc is None:
                            import pypdfium2 as pdfium
                            doc = pdfium.PdfDocument(data['pdf']) if os.path.isfile(data.get('pdf') or '') else False
                        d = [round(x) for x in doc[n - 1].get_size()] if doc else None
                    if d: sizes[f'review_pages/page_{n:03d}.png'] = d
            except Exception: pass
            finally:
                if doc: doc.close()
        for u, (f, ct) in static.items():
            if u.startswith('/_audit/') and ct.startswith('image/') and (d := dim(f)): sizes[u[1:]] = d
        return sizes or {'': [0, 0]}

    FIRST_TEXTS = 2                                   # the OCR pages whose text comes with the page: the first screen's
    def first_texts(oc):
        """15: {page: text} of the first OCR pages the OCR Text section shows (oc: ocr_section()), so they never read "Loading
        the text…" when the page opens; every other page's text is asked for when it scrolls near, as before."""
        out, can = {}, set(text_urls.values())
        for n in [p.get('page') for p in (oc or {}).get('pages') or [] if p.get('page') in can][:FIRST_TEXTS]:
            try: out[n] = page_text(n) or '(no text on this page)'
            except Exception: pass
        return out

    def draft_state():
        with draft_lock:
            d = {k: v for k, v in draft.items() if k not in ('started', 'stopping')}
            if draft['state'] == 'building': d['elapsed'] = round(time.time() - draft['started'], 1)
            return d

    def enter():
        with gate:
            if inside['closed']: return False
            inside['n'] += 1; return True

    def leave():
        with gate: inside['n'] -= 1; gate.notify_all()

    def close_gate():
        """No new POST from now on; returns once every POST under way has ended (its files all written, or refused)."""
        with gate:
            inside['closed'] = True
            while inside['n']: gate.wait(0.2)
    sid = (data.get('session') or {}).get('id') or '001'
    set_in = (data.get('session') or {}).get('set_in') or {}   # choices carried from an earlier session (a reopen)
    if not ocr_only: data['languages'] = core.languages()     # the language list (for runs prepared before it too)
    ocr_wo = wo if ocr_only else ai
    def ocr_section(): return O.section(run_dir, digest, ocr_wo)
    intake = core.load(os.path.join(run_dir, '_intake', 'intake.json')) or {}
    original = (intake.get('original') or {}).get('file')
    if original: data['book'] = original                # the book's own file name, not intake.pdf (the copy the decisions were made on)
    page_text = O.Text(data.get('pdf')) if O.needed(intake) and os.path.isfile(data.get('pdf') or '') else None
    text_urls = {f'/ocr/text/{n}.json': n for n in O.showable_pages(intake)} if page_text else {}
    cells = {i: (sh['image'], sh['cells'][str(i)]) for sh in digest.get('ocr_word_sheets') or [] if sh.get('cells')
             for i in range(sh['ids'][0], sh['ids'][1] + 1) if str(i) in sh['cells']}
    # what GET serves, keyed by URL. The file and its content type come from our own listing, never from the request
    static = {f'/_audit/{d}/{n}': (os.path.join(R, '_audit', d, n), mimetypes.guess_type(n)[0] or 'application/octet-stream')
              for d in SERVED if os.path.isdir(os.path.join(R, '_audit', d))
              for n in os.listdir(os.path.join(R, '_audit', d)) if os.path.isfile(os.path.join(R, '_audit', d, n))}
    static.update({u: (f, mimetypes.guess_type(f)[0] or 'application/octet-stream') for u, f in (files or {}).items() if os.path.isfile(f)})
    page_urls = {f'/review_pages/page_{n:03d}.png': n for n in range(1, data.get('pages', 0) + 1)}
    word_urls = {f'/word/{i}.png': i for i in cells}

    def page_image(n):
        """Path of PDF page n's image, rendered now if this is the first time it is asked for. None if it can't be made."""
        path = os.path.join(R, 'review_pages', f'page_{n:03d}.png')
        if os.path.exists(path): return path
        if not (1 <= n <= data.get('pages', 0)) or not os.path.isfile(data.get('pdf') or ''): return None
        with render_lock:
            if not os.path.exists(path):
                try: core.render_pages(data['pdf'], [n], os.path.dirname(path))
                except Exception: return None
        return path

    def word_image(i):
        """Path of OCR word i cut from its word sheet; None for an audit that did not record where words sit."""
        path = os.path.join(R, 'review_pages', f'word_{i:04d}.png')
        if os.path.exists(path): return path
        if i not in cells: return None
        sheet, (x, y, w, h) = cells[i]
        from PIL import Image
        with render_lock:
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with Image.open(os.path.join(R, '_audit', sheet)) as im: im.crop((x, y, x + w, y + h)).save(path)
        return path

    class H(BaseHTTPRequestHandler):
        timeout = 30                                  # a request that stalls (headers but no body) gives up, so Stop never waits forever
        def log_message(self, *a): pass
        def send(self, code, body, ctype='application/json; charset=utf-8'):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode('utf-8')
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Frame-Options', 'DENY'); self.send_header('Content-Security-Policy', "frame-ancestors 'none'")   # never inside another page's frame
            self.end_headers(); self.wfile.write(b)

        def ours(self): return local_request(self, self.server.server_address[1])

        def do_GET(self):                              # through the gate too: a page image PDFium is still rendering when the
            if not enter(): return self.send(503, {'error': 'The review page is closing.'})   # process ends crashes it (exit 139)
            try: self.get()
            finally: leave()

        def get(self):
            if not self.ours(): return self.send(403, {'error': 'This page opens only at the address it was started at: use the link on the run page.'})
            path = self.path.split('?', 1)[0]
            if path in ('/', '/index.html'):
                oc = ocr_section()
                boot = json.dumps({**data, 'saved': saved, 'date': date, 'return_to': return_to, 'ocr': oc,
                                   'check': first_check(), 'draft': None if ocr_only else draft_state(), 'ocr_text': first_texts(oc),
                                   'img_sizes': img_sizes()},
                                  ensure_ascii=False).replace('</', '<\\/')
                return self.send(200, open(PAGE, encoding='utf-8').read().replace('/*REVIEW_DATA*/null', boot), 'text/html; charset=utf-8')
            if path in text_urls:                      # the OCR text of a page the section can show; any other number: 404
                n = text_urls[path]
                try: return self.send(200, {'page': n, 'text': page_text(n)})
                except Exception as e: return self.send(500, {'error': f'the text of PDF {n} could not be read ({type(e).__name__})'})
            if path in page_urls or path in word_urls:
                f = page_image(page_urls[path]) if path in page_urls else word_image(word_urls[path])
                return self.send(200, open(f, 'rb').read(), 'image/png') if f else self.send(404, {'error': 'no such image'})
            if path == '/draft' and draft_dir: return self.send(200, draft_state())
            if path == '/draft.pdf' and draft_dir:
                with draft_lock: ready = draft['state'] == 'ready'
                if not ready or not os.path.isfile(draft_pdf): return self.send(404, {'error': 'There is no draft PDF yet: select Build a Draft PDF.'})
                with open(draft_pdf, 'rb') as f:              # streamed: a long book's draft can be hundreds of MB
                    self.send_response(200); self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Length', str(os.fstat(f.fileno()).st_size))
                    self.send_header('Content-Disposition', f'attachment; filename="{draft_name(data.get("book") or data.get("pdf"))}"')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Frame-Options', 'DENY'); self.send_header('Content-Security-Policy', "frame-ancestors 'none'")
                    self.end_headers(); shutil.copyfileobj(f, self.wfile, 1 << 20)
                return
            if path in static:
                f, ctype = static[path]
                return self.send(200, open(f, 'rb').read(), ctype)
            self.send(404, {'error': 'not found'})

        def do_POST(self):
            if not enter(): return self.send(503, {'error': 'The review page is closing.'})
            try: self.post()
            finally: leave()

        def post(self):
            if not self.ours(): return self.send(403, {'error': 'not from the review page'})
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
                return self.send(415, {'error': 'the review page sends JSON'})
            try: body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            except ValueError: return self.send(400, {'error': 'not JSON'})
            except TimeoutError: self.close_connection = True; return   # the body never came (timeout): nothing is written
            if not isinstance(body, dict): return self.send(400, {'error': 'not a JSON object'})
            decisions = body.get('decisions') if isinstance(body.get('decisions'), dict) else {}
            additions = [a for a in body.get('additions') or [] if isinstance(a, dict)] if isinstance(body.get('additions'), list) else []
            reviewer = str(body.get('reviewer') or '').strip()
            saved_at = str(body.get('saved_at') or '') or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
            if self.path == '/ocr-verdict':                # on its own, at once; never during or after Finish
                if not ocr_section(): return self.send(400, {'error': 'This book has no OCR text to review.'})
                fields = {k: body.get(k) for k in ('verdict', 'reviewer', 'reason', 'pages', 'to')}
                fields['reads'] = [str(x) for x in body.get('reads') or []] if isinstance(body.get('reads'), list) else []
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'The page is finishing: record the verdict from the run page.'})
                    try: v, _ = O.record(run_dir, fields, via='page', held=lock_held, session=None if ocr_only else sid,   # today's date
                                         wait=runlock.REQUEST_WAIT)
                    except S.Refused as e:                 # the record lock stayed busy, or the run's review lock is another process's
                        return self.send(400, {'error': runlock.BUSY if str(e) == runlock.BUSY else
                                               'Another review of this book is open, so the verdict was not recorded. Close it, then try again.'})
                    except ValueError as e:                # the page's own wording (review_ocr.py keeps the terminal's)
                        return self.send(400, {'error': getattr(e, 'page', None) or str(e)[:1].upper() + str(e)[1:]})
                    closing = ocr_only and body.get('close') is True   # Finish OCR Review: recorded, then the page closes
                    self.send(200, {'recorded': v, 'ocr': ocr_section(), 'closed': closing})
                    if closing: done.set()
                return
            if self.path == '/close':
                if not ocr_only: return self.send(404, {'error': 'not found'})
                with write_lock: done.set()
                return self.send(200, {'closed': True})
            if ocr_only or self.path not in ('/save', '/keep', '/finish', '/draft'): return self.send(404, {'error': 'not found'})
            try: name, notes = core.session_fields(body, sid)
            except ValueError as e: return self.send(400, {'error': str(e)})
            def keep(last_word=False):                   # the caller holds write_lock
                """The draft to review_decisions.json. An auto-save or check whose draft is older than the one on disk
                (saved_at, the browser's clock) is skipped, so a request handled late never puts an older draft back;
                Finish's own keep() is the session's last word and always writes. Returns whether it wrote."""
                if not last_word:
                    on = (core.load(os.path.join(R, 'review_decisions.json'), {}) or {}).get('saved_at')
                    try:
                        if on and when(saved_at) < when(on): return False
                    except (ValueError, TypeError): pass       # a stamp that can't be read or compared: write, as before
                core.save(os.path.join(R, 'review_decisions.json'),
                          {'reviewer': reviewer, 'decisions': decisions, 'additions': additions,
                           **({'session_name': name} if name else {}), **({'session_notes': notes} if notes else {}), 'saved_at': saved_at})
                return True
            def build():
                wo = core.apply_decisions(ai, items, decisions)
                return wo, core.add_entries(wo, additions, adds, reviewer)
            def checked():                              # the check's verdict card by card, and the gaps left after it
                return core.problems(R, ai, items, decisions, additions, adds, reviewer, set_in)
            if self.path == '/keep':
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started: nothing more is kept.'})
                    wrote = keep()
                wo = build()[0]
                probs, gaps = checked()                          # each card's problems and the gaps still open, for the line beside Finish
                return self.send(200, {'kept': wrote, **({} if wrote else {'older': True}), 'problems': probs, 'gaps': gaps,   # older: a newer draft is on disk
                                       'move_previews': core.move_previews(data, decisions, additions, wo)})   # each move card's preview
            if self.path == '/draft':                       # Build a Draft PDF: kept as /keep does, then built in the background
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started: no draft can be built now.'})
                    with draft_lock:
                        if draft['state'] == 'building': return self.send(409, {'error': 'A draft is being built already.'})
                    keep()                                   # before the state changes: a keep that fails leaves no build "under way"
                    with draft_lock: draft.clear(); draft.update(state='building', started=time.time(), basis=saved_at)
                try: wo = build()[0]; probs = checked()[0]   # what is left out, worded as on the cards (core.problems)
                except Exception as e:
                    with draft_lock: draft.update(state='failed', error=f'The draft could not be started ({type(e).__name__}).')
                    return self.send(500, draft_state())
                def started(p):                              # a stop that came before apply.py started stops it too
                    with draft_lock:
                        if draft.get('stopping'): p.terminate()
                        else: draft_proc['p'] = p
                def run():
                    try:
                        res = core.draft_pdf(R, data.get('pdf'), ai, wo, draft_pdf, items=items, decisions=decisions,
                                             additions=additions, on_start=started)
                        with draft_lock: draft.update(state='ready', seconds=res.pop('seconds'), result={**res, 'problems': probs})
                    except Exception as e:                   # ValueError: the page's own words
                        with draft_lock: draft.update(state='failed', error=str(e) if isinstance(e, ValueError) else f'The draft could not be built ({type(e).__name__}).')
                    finally:
                        with draft_lock:
                            draft_proc.pop('p', None)
                            if draft.get('stopping'): draft.update(state='failed', error='The review page closed.')
                threading.Thread(target=run, daemon=True).start()
                return self.send(202, draft_state())
            if self.path == '/save':                        # the Finish dialog's check (it saves the draft too; auto-save uses /keep)
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started: nothing more is saved.'})
                    keep()
                wo = build()[0]
                probs, gaps = checked()
                return self.send(200, {'saved': True, 'changes': len(core.diff(ai, wo)), 'problems': probs,
                                       'gaps': gaps, 'unreviewed': len(core.unreviewed(items, decisions)),
                                       'move_previews': core.move_previews(data, decisions, additions, wo)})
            if self.path == '/finish':
                if not reviewer: return self.send(400, {'error': 'Enter your name as the reviewer first.'})
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started already.'})
                    keep()
                probs, open_gaps = checked()
                if probs['fields'] or probs['conflicts']:      # anything that would be dropped and that a card can fix: not yet
                    return self.send(200, {'finished': False, 'needs': 'invalid', 'error': 'Some choices cannot be applied yet.', 'problems': probs})
                left = core.unreviewed(items, decisions)
                if left and not body.get('accept_unreviewed'):
                    return self.send(200, {'finished': False, 'needs': 'unreviewed', 'error': f'{len(left)} items are not reviewed yet.', 'unreviewed': left})
                wo, refused = build()
                if refused: return self.send(400, {'error': 'Some of your additions cannot be applied: '
                                                   + '; '.join(f'{r["id"]}: {r["why"]}' for r in refused), 'refused': refused})
                ack = body.get('gaps_ack') if isinstance(body.get('gaps_ack'), dict) else {}
                gaps = [g for g in open_gaps if not str(ack.get(g['id']) or '').strip()]
                if gaps: return self.send(200, {'finished': False, 'needs': 'gaps', 'error': f'{len(gaps)} gaps are open.', 'gaps': gaps})
                with write_lock:                             # an auto-save or a check after this point is refused
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started already.'})
                    finishing.set(); ok = False              # Ctrl+C now waits until the review is recorded (or refused)
                    try:
                        keep(last_word=True)                 # the last word of the page, with the Finish dialog's name and notes
                        try: v = core.finish(R, ai, wo, reviewer, date, 'page', decisions=decisions, items=items, additions=additions, gaps_ack=ack)
                        except ValueError as e: return self.send(400, {'error': str(e)})
                        result.update(v); ok = True
                        self.send(200, {'finished': True, 'changes': len(v['changes']), 'dropped': v['dropped_on_check'], 'counts': v.get('counts'),
                                        'gaps': v.get('gaps') or []})
                    finally:
                        if ok: done.set()
                        else: finishing.clear()
                return

    srv = None
    for p in range(port, port + 20):
        try: srv = Server(('127.0.0.1', p), H); break
        except OSError: continue
    if srv is None: raise SystemExit(f'no free port between {port} and {port + 19}: pass --port')
    url = f'http://localhost:{srv.server_address[1]}/'
    print(f'review page: {url}\n  open it in a browser (from WSL, a Windows browser works too). ' +
          ('Finish OCR Review records the verdict and closes it; Ctrl+C or Close Without a Verdict closes it with none.' if ocr_only else
           'Ctrl+C stops without finishing; your choices are saved to review_decisions.json as you make them, and kept in the browser.'), flush=True)
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        while not done.wait(0.5): pass                 # a short wait, so Ctrl+C is seen
    except KeyboardInterrupt:
        close_gate()                                   # a Finish or a verdict under way is written whole first
        srv.shutdown(); stop_draft()                   # a draft being built is stopped, never waited for
        if page_text: page_text.close()
        if not done.is_set() or ocr_only:
            print('\nstopped: ' + ('the OCR review page is closed.' if ocr_only else 'the review is not finished. Run the same command again to carry on.'))
            return None
        print('\nCtrl+C came while Finish was being recorded: the review is recorded')
        return result
    close_gate()                                       # a request that came in as the page closed: let it end
    srv.shutdown(); stop_draft()
    if page_text: page_text.close()
    return result
