"""review/server.py: the review page, served on this computer only (127.0.0.1). Python's standard library, no new packages.

Routes (all call review/core.py; a later front end can replace this file and page.html without touching the pipeline):
    GET  /                       the page, with review_items.json built in
    GET  /review_pages/…  /_audit/figures/…  /_audit/ocr_words/…   page images, figure crops, OCR word sheets
                                 (nothing else in the run folder is served: the files are listed when the server starts, and a
                                 request path is only looked up in that list, never joined onto a folder). A page image is
                                 rendered the first time it is asked for.
    GET  /word/<id>.png          one OCR word cut from its word sheet (the image the AI read)
    GET  /result/review.html …   files the caller lists (files=): a reopened review links the run's current result
    POST /save    {reviewer, decisions, additions, saved_at}  → saved to review_decisions.json; returns what the check
                                 would drop, additions refused, and gaps (no H1, figures without alt)
    POST /finish  {…, accept_unreviewed, gaps_ack}            → review.json and the reviewed workorder.json; the server stops.
                                 409 while items are unreviewed or a gap has no reason, unless the body accepts them

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

def serve(R, date, port=8765, open_browser=True, files=None, return_to=None):
    """files: {url: path} served as they are, beside the review's own (review_workorder.py --reopen: the current result).
    return_to: the app's run page, which the page goes to after Finish and links back to."""
    R = os.path.abspath(R)
    if return_to: check_return_to(return_to)
    data = core.load(os.path.join(R, 'review_items.json'))
    ai = core.load(os.path.join(R, 'workorder.ai.json'))
    if data is None or ai is None: raise SystemExit(f'{R} is not waiting for a review (no review_items.json / workorder.ai.json)')
    items = data['items']
    digest = core.load(os.path.join(R, '_audit', 'digest.json'), {}) or {}
    core.pages_to_render(items, data.get('pages', 0))        # also for runs prepared before every card had page images
    if 'addable' not in data: data['addable'] = core.addable(ai, digest); data['add_kinds'] = core.ADD_KINDS
    adds = data['addable']
    saved = core.load(os.path.join(R, 'review_decisions.json'), {}) or {}
    done = threading.Event(); finishing = threading.Event(); result = {}
    render_lock = threading.Lock()                    # pdfium is not thread-safe: one page image at a time
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
        def log_message(self, *a): pass
        def send(self, code, body, ctype='application/json; charset=utf-8'):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode('utf-8')
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Frame-Options', 'DENY'); self.send_header('Content-Security-Policy', "frame-ancestors 'none'")   # never inside another page's frame
            self.end_headers(); self.wfile.write(b)

        def ours(self): return local_request(self, self.server.server_address[1])

        def do_GET(self):
            if not self.ours(): return self.send(403, {'error': 'open the page at the address the terminal printed'})
            path = self.path.split('?', 1)[0]
            if path in ('/', '/index.html'):
                boot = json.dumps({**data, 'saved': saved, 'date': date, 'return_to': return_to}, ensure_ascii=False).replace('</', '<\\/')
                return self.send(200, open(PAGE, encoding='utf-8').read().replace('/*REVIEW_DATA*/null', boot), 'text/html; charset=utf-8')
            if path in page_urls or path in word_urls:
                f = page_image(page_urls[path]) if path in page_urls else word_image(word_urls[path])
                return self.send(200, open(f, 'rb').read(), 'image/png') if f else self.send(404, {'error': 'no such image'})
            if path in static:
                f, ctype = static[path]
                return self.send(200, open(f, 'rb').read(), ctype)
            self.send(404, {'error': 'not found'})

        def do_POST(self):
            if not self.ours(): return self.send(403, {'error': 'not from the review page'})
            if (self.headers.get('Content-Type') or '').split(';')[0].strip().lower() != 'application/json':
                return self.send(415, {'error': 'the review page sends JSON'})
            try: body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            except ValueError: return self.send(400, {'error': 'not JSON'})
            if not isinstance(body, dict): return self.send(400, {'error': 'not a JSON object'})
            decisions = body.get('decisions') if isinstance(body.get('decisions'), dict) else {}
            additions = [a for a in body.get('additions') or [] if isinstance(a, dict)] if isinstance(body.get('additions'), list) else []
            reviewer = str(body.get('reviewer') or '').strip()
            saved_at = str(body.get('saved_at') or '') or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
            def keep(): core.save(os.path.join(R, 'review_decisions.json'),
                                  {'reviewer': reviewer, 'decisions': decisions, 'additions': additions, 'saved_at': saved_at})
            def build():
                wo = core.apply_decisions(ai, items, decisions)
                return wo, core.add_entries(wo, additions, adds, reviewer)
            if self.path == '/save':
                keep()
                wo, refused = build()
                dropped, gaps = core.preview(R, wo)
                return self.send(200, {'saved': True, 'changes': len(core.diff(ai, wo)), 'dropped': dropped, 'refused': refused,
                                       'gaps': gaps, 'unreviewed': len(core.unreviewed(items, decisions))})
            if self.path == '/finish':
                if not reviewer: return self.send(400, {'error': 'Enter your name as the reviewer first.'})
                keep()
                left = core.unreviewed(items, decisions)
                if left and not body.get('accept_unreviewed'):
                    return self.send(409, {'error': f'{len(left)} items are not reviewed yet.', 'unreviewed': left})
                wo, refused = build()
                if refused: return self.send(400, {'error': 'Some of your additions cannot be applied: '
                                                   + '; '.join(f'{r["id"]}: {r["why"]}' for r in refused), 'refused': refused})
                ack = body.get('gaps_ack') if isinstance(body.get('gaps_ack'), dict) else {}
                gaps = [g for g in core.preview(R, wo)[1] if not str(ack.get(g['id']) or '').strip()]
                if gaps: return self.send(409, {'error': f'{len(gaps)} gaps are open.', 'gaps': gaps})
                finishing.set(); ok = False                  # Ctrl+C now waits until the review is recorded (or refused)
                try:
                    try: v = core.finish(R, ai, wo, reviewer, date, 'page', decisions=decisions, items=items, additions=additions, gaps_ack=ack)
                    except ValueError as e: return self.send(400, {'error': str(e)})
                    result.update(v); ok = True
                    self.send(200, {'finished': True, 'changes': len(v['changes']), 'dropped': v['dropped_on_check'], 'counts': v.get('counts'),
                                    'gaps': v.get('gaps') or []})
                finally:
                    if ok: done.set()
                    else: finishing.clear()
                return
            self.send(404, {'error': 'not found'})

    srv = None
    for p in range(port, port + 20):
        try: srv = ThreadingHTTPServer(('127.0.0.1', p), H); break
        except OSError: continue
    if srv is None: raise SystemExit(f'no free port between {port} and {port + 19}: pass --port')
    url = f'http://localhost:{srv.server_address[1]}/'
    print(f'review page: {url}\n  open it in a browser (from WSL, a Windows browser works too). Ctrl+C stops without finishing;'
          ' your choices so far are kept in the browser and in review_decisions.json after each Save.', flush=True)
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        while not done.wait(0.5): pass                 # a short wait, so Ctrl+C is seen
    except KeyboardInterrupt:
        while finishing.is_set() and not done.is_set(): done.wait(0.2)   # Ctrl+C during Finish: let the record be written
        if not done.is_set():
            print('\nstopped: the review is not finished. Run the same command again to carry on.'); srv.shutdown(); return None
        print('\nCtrl+C came while Finish was being recorded: the review is recorded')
    srv.shutdown()
    return result
