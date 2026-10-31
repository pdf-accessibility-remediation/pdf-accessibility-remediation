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
                                 returns what the check would drop, additions refused, and gaps (no H1, figures without alt)
    POST /keep    the same body → saved to review_decisions.json only (the page sends it when the session name or notes
                                 lose focus, so they survive a closed tab and a new port); refused once Finish has started
    POST /finish  {…, accept_unreviewed, gaps_ack}            → review.json and the reviewed workorder.json; the server stops.
                                 Not finished yet, but nothing wrong: 200 with needs: "unreviewed" (and the list) while
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
import os, json, datetime, threading, webbrowser, mimetypes, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from . import core

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html')
SERVED = ('figures', 'ocr_words')                     # folders under _audit/ whose files the page shows

def local_request(handler, port):
    """The request names this server as its host (no DNS rebinding) and, if it says where it comes from, the page.
    Shared with the app (webapp/server.py)."""
    hosts = {f'localhost:{port}', f'127.0.0.1:{port}'}
    origin = handler.headers.get('Origin')
    return handler.headers.get('Host') in hosts and (origin is None or origin in {f'http://{h}' for h in hosts})

def check_return_to(url):
    """--return-to: an http URL on this computer (127.0.0.1 or localhost, with a port), so the page never sends the reviewer
    elsewhere. Returns the URL; raises ValueError."""
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'http' or u.hostname not in ('127.0.0.1', 'localhost') or u.username or u.password or not u.port or u.netloc not in (f'127.0.0.1:{u.port}', f'localhost:{u.port}'):
        raise ValueError(f'only http://127.0.0.1:<port>/… or http://localhost:<port>/… is accepted, not {url!r}')
    return url

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
    write_lock = threading.Lock()                     # every write of this server, one at a time (Save, Keep and Finish race on a blur)
    gate = threading.Condition(); inside = {'n': 0, 'closed': False}   # POSTs under way; closed: the server is stopping

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
    ocr_wo = wo if ocr_only else ai
    def ocr_section(): return O.section(run_dir, digest, ocr_wo)
    intake = core.load(os.path.join(run_dir, '_intake', 'intake.json')) or {}
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
                boot = json.dumps({**data, 'saved': saved, 'date': date, 'return_to': return_to, 'ocr': ocr_section()},
                                  ensure_ascii=False).replace('</', '<\\/')
                return self.send(200, open(PAGE, encoding='utf-8').read().replace('/*REVIEW_DATA*/null', boot), 'text/html; charset=utf-8')
            if path in text_urls:                      # the OCR text of a page the section can show; any other number: 404
                n = text_urls[path]
                try: return self.send(200, {'page': n, 'text': page_text(n)})
                except Exception as e: return self.send(500, {'error': f'the text of PDF {n} could not be read ({type(e).__name__})'})
            if path in page_urls or path in word_urls:
                f = page_image(page_urls[path]) if path in page_urls else word_image(word_urls[path])
                return self.send(200, open(f, 'rb').read(), 'image/png') if f else self.send(404, {'error': 'no such image'})
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
                    try: v, _ = O.record(run_dir, fields, via='page', held=lock_held, session=None if ocr_only else sid)   # today's date
                    except S.Refused:                      # the run's review lock, held by another process
                        return self.send(400, {'error': 'Another review of this book is open, so the verdict was not recorded. Close it, then try again.'})
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
            if ocr_only or self.path not in ('/save', '/keep', '/finish'): return self.send(404, {'error': 'not found'})
            try: name, notes = core.session_fields(body, sid)
            except ValueError as e: return self.send(400, {'error': str(e)})
            def keep():                                  # the caller holds write_lock
                core.save(os.path.join(R, 'review_decisions.json'),
                          {'reviewer': reviewer, 'decisions': decisions, 'additions': additions,
                           **({'session_name': name} if name else {}), **({'session_notes': notes} if notes else {}), 'saved_at': saved_at})
            def build():
                wo = core.apply_decisions(ai, items, decisions)
                return wo, core.add_entries(wo, additions, adds, reviewer)
            if self.path == '/keep':
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started: nothing more is kept.'})
                    keep()
                return self.send(200, {'kept': True})
            if self.path == '/save':
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started: nothing more is saved.'})
                    keep()
                wo, refused = build()
                dropped, gaps = core.preview(R, wo)
                return self.send(200, {'saved': True, 'changes': len(core.diff(ai, wo)), 'dropped': dropped, 'refused': refused,
                                       'gaps': gaps, 'unreviewed': len(core.unreviewed(items, decisions))})
            if self.path == '/finish':
                if not reviewer: return self.send(400, {'error': 'Enter your name as the reviewer first.'})
                with write_lock:
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started already.'})
                    keep()
                left = core.unreviewed(items, decisions)
                if left and not body.get('accept_unreviewed'):
                    return self.send(200, {'finished': False, 'needs': 'unreviewed', 'error': f'{len(left)} items are not reviewed yet.', 'unreviewed': left})
                wo, refused = build()
                if refused: return self.send(400, {'error': 'Some of your additions cannot be applied: '
                                                   + '; '.join(f'{r["id"]}: {r["why"]}' for r in refused), 'refused': refused})
                ack = body.get('gaps_ack') if isinstance(body.get('gaps_ack'), dict) else {}
                gaps = [g for g in core.preview(R, wo)[1] if not str(ack.get(g['id']) or '').strip()]
                if gaps: return self.send(200, {'finished': False, 'needs': 'gaps', 'error': f'{len(gaps)} gaps are open.', 'gaps': gaps})
                with write_lock:                             # a Keep or Save after this point is refused
                    if finishing.is_set() or done.is_set(): return self.send(409, {'error': 'Finish has started already.'})
                    finishing.set(); ok = False              # Ctrl+C now waits until the review is recorded (or refused)
                    try:
                        keep()                               # the last word of the page, with the Finish dialog's name and notes
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
        try: srv = ThreadingHTTPServer(('127.0.0.1', p), H); break
        except OSError: continue
    if srv is None: raise SystemExit(f'no free port between {port} and {port + 19}: pass --port')
    url = f'http://localhost:{srv.server_address[1]}/'
    print(f'review page: {url}\n  open it in a browser (from WSL, a Windows browser works too). ' +
          ('Finish OCR Review records the verdict and closes it; Ctrl+C or Close Without a Verdict closes it with none.' if ocr_only else
           'Ctrl+C stops without finishing; your choices so far are kept in the browser and in review_decisions.json after each Save.'), flush=True)
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        while not done.wait(0.5): pass                 # a short wait, so Ctrl+C is seen
    except KeyboardInterrupt:
        close_gate()                                   # a Finish or a verdict under way is written whole first
        srv.shutdown()
        if page_text: page_text.close()
        if not done.is_set() or ocr_only:
            print('\nstopped: ' + ('the OCR review page is closed.' if ocr_only else 'the review is not finished. Run the same command again to carry on.'))
            return None
        print('\nCtrl+C came while Finish was being recorded: the review is recorded')
        return result
    close_gate()                                       # a request that came in as the page closed: let it end
    srv.shutdown()
    if page_text: page_text.close()
    return result
