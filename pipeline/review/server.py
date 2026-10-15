"""review/server.py: the review page, served on this computer only (127.0.0.1). Python's standard library, no new packages.

Routes (all call review/core.py; a later front end can replace this file and page.html without touching the pipeline):
    GET  /                       the page, with review_items.json built in
    GET  /review_pages/…  /_audit/figures/…   page images and figure crops (nothing else in the run folder is served)
    POST /save    {reviewer, decisions}                       → saved to review_decisions.json, checked, result returned
    POST /finish  {reviewer, decisions, accept_unreviewed}    → review.json and the reviewed workorder.json; the server stops
"""
import os, json, threading, webbrowser, mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from . import core

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page.html')
SERVED = ('review_pages', os.path.join('_audit', 'figures'))

def serve(R, date, port=8765, open_browser=True):
    R = os.path.abspath(R)
    data = core.load(os.path.join(R, 'review_items.json'))
    ai = core.load(os.path.join(R, 'workorder.ai.json'))
    if data is None or ai is None: raise SystemExit(f'{R} is not waiting for a review (no review_items.json / workorder.ai.json)')
    items = data['items']
    saved = core.load(os.path.join(R, 'review_decisions.json'), {}) or {}
    done = threading.Event(); result = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def send(self, code, body, ctype='application/json; charset=utf-8'):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode('utf-8')
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b)))
            self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            path = self.path.split('?', 1)[0]
            if path in ('/', '/index.html'):
                boot = json.dumps({**data, 'saved': saved, 'date': date}, ensure_ascii=False).replace('</', '<\\/')
                return self.send(200, open(PAGE, encoding='utf-8').read().replace('/*REVIEW_DATA*/null', boot), 'text/html; charset=utf-8')
            rel = os.path.normpath(path.lstrip('/'))
            full = os.path.realpath(os.path.join(R, rel))
            if any(full.startswith(os.path.realpath(os.path.join(R, d)) + os.sep) for d in SERVED) and os.path.isfile(full):
                return self.send(200, open(full, 'rb').read(), mimetypes.guess_type(full)[0] or 'application/octet-stream')
            self.send(404, {'error': 'not found'})

        def do_POST(self):
            try: body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            except ValueError: return self.send(400, {'error': 'not JSON'})
            decisions = body.get('decisions') or {}
            reviewer = (body.get('reviewer') or '').strip()
            if self.path == '/save':
                core.save(os.path.join(R, 'review_decisions.json'), {'reviewer': reviewer, 'decisions': decisions})
                wo = core.apply_decisions(ai, items, decisions)
                dropped = core.check(R, wo)
                return self.send(200, {'saved': True, 'changes': len(core.diff(ai, wo)), 'dropped': dropped,
                                       'unreviewed': len(core.unreviewed(items, decisions))})
            if self.path == '/finish':
                if not reviewer: return self.send(400, {'error': 'Enter your name as the reviewer first.'})
                left = core.unreviewed(items, decisions)
                if left and not body.get('accept_unreviewed'):
                    return self.send(409, {'error': f'{len(left)} items are not reviewed yet.', 'unreviewed': left})
                core.save(os.path.join(R, 'review_decisions.json'), {'reviewer': reviewer, 'decisions': decisions})
                wo = core.apply_decisions(ai, items, decisions)
                try: v = core.finish(R, ai, wo, reviewer, date, 'page', decisions=decisions, items=items)
                except ValueError as e: return self.send(400, {'error': str(e)})
                result.update(v)
                self.send(200, {'finished': True, 'changes': len(v['changes']), 'dropped': v['dropped_on_check'], 'counts': v.get('counts')})
                done.set(); return
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
        print('\nstopped: the review is not finished. Run the same command again to carry on.'); srv.shutdown(); return None
    srv.shutdown()
    return result
