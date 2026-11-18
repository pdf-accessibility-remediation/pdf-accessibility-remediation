"""lib/aisend.py: one runner for the AI requests of the three paid steps after the work order (#135, parallel requests):
the figure requests (decide.py, lib/figpasses.py), the language step (name_languages.py) and the page readings
(read_pages.py).

    aisend.cap()                                        AI_PARALLEL: requests in flight at once, per book (default 8; 1 = one at a time)
    aisend.run(jobs, one, cap, on_done, on_stop)        one(job) for every job, at most `cap` at a time, results in job order
    aisend.Budget(limits, planned)                      the money limits a step's retries are checked against, under one lock
    aisend.Record(path, data)                           a step's record: every change under one lock, written atomically
    aisend.call(send, body, key, worst, budget, …)      one request with the one retry rule (language step, page readings)
    aisend.openrouter(api_key, timeout)                 the send function the steps pass in (the caller reads the key)

The retry rule (one for all three steps, from the figure requests' code): a request that fails (an HTTP error, a network
error, no reply in time, or a reply that can't be read) is sent once more, after a pause (60 s after "too many requests"
(429), 20 s otherwise), and only when the retry's worst case fits the room left under every limit the step names (its own
limit and the per-PDF limit): checked and reserved in one locked step. What a cut-off reply gets is the step's own rule
(figure requests and page readings: once more with twice the room; the language step: its undecided forms, once).

An interruption (Ctrl+C in a terminal run, or any exception while waiting) starts no queued request and waits for no call
already sent (the workers are daemon threads): run() hands the requests in flight to on_stop, which records them at their
worst case (their charge is not known), and raises the exception again (review 02, H3).
"""
import os, json, time, queue, socket, threading, urllib.request, urllib.error

DEFAULT_CAP = 8                       # set from the cap sweep and the batch test (handoff/137-language-answers-parallel/14, 16)
PAUSE = {'429': 60}                   # seconds before the one retry, by HTTP status; PAUSE_OTHER otherwise
PAUSE_OTHER = 20

def cap(environ=None):
    """AI_PARALLEL as a whole number of at least 1; DEFAULT_CAP when it is not set or not a number."""
    v = (os.environ if environ is None else environ).get('AI_PARALLEL')
    try: n = int(str(v).strip()) if v not in (None, '') else DEFAULT_CAP
    except ValueError: n = DEFAULT_CAP
    return max(1, n)

def pause(code):
    return PAUSE.get(str(code or ''), PAUSE_OTHER)

_say = threading.Lock()
def locked(say):
    """say() for lines printed from several workers: one line at a time."""
    def f(*a, **k):
        with _say: say(*a, **k)
    return f

# ------------------------------------------------------------------ the runner
def run(jobs, one, cap_, on_done=None, on_stop=None):
    """one(job) for each job, at most cap_ at a time on daemon threads; on_done(job, result) runs in the calling thread as
    each finishes (so the caller's record has one writer for finished requests). Returns the results in job order.
    KeyboardInterrupt or any exception while waiting (or raised by one or on_done): no queued job starts, on_stop(jobs
    started and not finished) is called, and the exception is raised again. With cap_ 1 the jobs run in their order."""
    jobs = list(jobs); n = len(jobs); results = [None] * n
    if not n: return results
    todo, out, lock, stop = queue.Queue(), queue.Queue(), threading.Lock(), threading.Event()
    started, finished = set(), set()
    for i in range(n): todo.put(i)
    def worker():
        while True:
            with lock:                                  # take the next job and mark it started in one step: a stop
                if stop.is_set(): return                # after this point sees it in flight
                try: i = todo.get_nowait()
                except queue.Empty: return
                started.add(i)
            try: out.put((i, one(jobs[i]), None))
            except BaseException as e:
                stop.set(); out.put((i, None, e))           # no worker takes another job: the run is stopping
    threads = [threading.Thread(target=worker, daemon=True, name=f'aisend-{k}') for k in range(min(max(1, cap_), n))]
    try:
        for t in threads: t.start()                     # inside the try: an interruption while they start stops them too
        got = 0
        while got < n:
            try: i, r, e = out.get(timeout=0.25)    # a short wait keeps Ctrl+C prompt in the calling thread
            except queue.Empty: continue
            got += 1
            with lock: finished.add(i)
            if e is not None: raise e
            results[i] = r
            if on_done: on_done(jobs[i], r)
    except BaseException:
        with lock:
            stop.set()
            flying = [jobs[i] for i in sorted(started - finished)]
        if on_stop: on_stop(flying)
        raise
    return results

# ------------------------------------------------------------------ money
class Budget:
    """A step's money limits for its retries (review 02, M1). limits: {name: (cap or None, spent before this step)};
    planned: {request key: worst case reserved and not yet charged}; spent: what this step's calls have cost (a call whose
    charge is not known counts its worst case). Every read and change is under one lock; a reservation leaves `planned`
    and joins `spent` once, when its call comes back (settle)."""
    def __init__(self, limits, planned=None):
        self.limits = dict(limits); self.planned = dict(planned or {}); self.spent = 0.0; self.lock = threading.Lock()
    def _room(self, name, free=0.0):
        c, base = self.limits[name]
        return None if c is None else c - base - self.spent - (sum(self.planned.values()) - free)
    def room(self, names=None):
        with self.lock:
            rs = [r for r in (self._room(k) for k in (names or self.limits)) if r is not None]
        return min(rs) if rs else None
    def settle(self, key, cost):
        """A call of `key` came back: its reservation is released and its cost (the worst case when not known) is spent."""
        with self.lock:
            self.planned.pop(key, None); self.spent += float(cost or 0)
    def release(self, key):
        with self.lock: self.planned.pop(key, None)
    def try_reserve(self, key, worst, names=None, call_cap=None):
        """Reserve `worst` for key's next call when every named limit (all by default) has room for it, the key's own
        reservation freed first: (True, None), or (False, the limit's name, or 'call' over call_cap). One locked step."""
        with self.lock:
            if call_cap is not None and worst > call_cap: return False, 'call'
            free = self.planned.get(key, 0.0)
            for k in (names or self.limits):
                r = self._room(k, free)
                if r is not None and r < worst: return False, k
            self.planned[key] = float(worst)
            return True, None

# ------------------------------------------------------------------ records
class Record:
    """A step's record, owned by one lock (review 02, M1): every change goes through change(fn), which runs fn on the dict
    and writes it atomically (a temporary file, then os.replace), so replies arriving together can't cut the file or lose
    a change. The lock is not re-entrant: fn never calls change or read."""
    def __init__(self, path, data):
        self.path, self.data, self.lock, self.closed = path, data, threading.Lock(), False
    def _write(self):
        tmp = f'{self.path}.tmp{os.getpid()}'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)
    def change(self, fn=None):
        with self.lock:
            if self.closed: return None              # after an interruption: a call still running changes nothing
            r = fn(self.data) if fn else None
            self._write()
            return r
    def close(self, fn=None):
        """The last change (an interruption's record of what was in flight); every later change is ignored."""
        with self.lock:
            if self.closed: return
            if fn: fn(self.data)
            self._write(); self.closed = True
    def read(self, fn):
        with self.lock: return fn(self.data)

def stopped(entries, why='in flight when the run was interrupted; any charge is not known'):
    """The in-flight entries a stop leaves: each kept with its worst case, never as money spent."""
    return [{**e, 'stopped': True, 'note': why} for e in entries]

# ------------------------------------------------------------------ one request with the retry rule
def openrouter(api_key, timeout):
    """send(body) -> {'resp', 'code', 'message', 'timeout', 'seconds'}: one POST to OpenRouter's chat completions."""
    def send(body):
        rq = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(body).encode(),
                                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json',
                                             'X-Title': 'UH PDF remediation prototype'})
        t0 = time.time()
        try:
            with urllib.request.urlopen(rq, timeout=timeout) as r_: return {'resp': json.load(r_), 'seconds': round(time.time() - t0, 1)}
        except urllib.error.HTTPError as e:
            err = e.read().decode('utf-8', 'replace')
            try: msg = (json.loads(err).get('error') or {}).get('message')
            except Exception: msg = err[:300]
            return {'resp': None, 'code': e.code, 'message': msg, 'seconds': round(time.time() - t0, 1)}
        except (TimeoutError, socket.timeout): return {'resp': None, 'timeout': True, 'seconds': round(time.time() - t0, 1)}
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)): return {'resp': None, 'timeout': True, 'seconds': round(time.time() - t0, 1)}
            return {'resp': None, 'code': 'network', 'message': str(e.reason), 'seconds': round(time.time() - t0, 1)}
        except (ValueError, OSError) as e:
            return {'resp': None, 'code': 'network', 'message': str(e)[:300], 'seconds': round(time.time() - t0, 1)}
    return send

def failed_reply(resp):
    """A 200 reply that is a failure, never an answer: an error object beside the choices, one inside the first choice,
    or finish_reason "error" (OpenRouter's word for a provider failing mid-reply). Returns {code, message}, or None."""
    if not isinstance(resp, dict) or not resp.get('choices'): return None
    ch = resp['choices'][0] if isinstance(resp['choices'][0], dict) else {}
    er = resp.get('error') or ch.get('error')
    if er or ch.get('finish_reason') == 'error':
        er = er if isinstance(er, dict) else {'message': str(er or '')}
        return {'code': str(er.get('code') or 'error'), 'message': str(er.get('message') or 'the AI service reported an error in its reply')}
    return None

def _read_call(out, worst):
    """One call's outcome: {usage, cost, finish, text, error?, worst_usd?} from a send() result."""
    resp = out.get('resp'); u = (resp or {}).get('usage') or {}
    c = {'seconds': out.get('seconds'), 'cost': u.get('cost'), 'input_tokens': u.get('prompt_tokens'), 'output_tokens': u.get('completion_tokens')}
    if out.get('timeout'):
        c.update(error={'code': 'timeout', 'message': 'no reply in time; any charge is not known'}, worst_usd=round(worst, 4)); return c
    if resp is None or not (resp.get('choices') or []) or failed_reply(resp):
        er = failed_reply(resp) or (resp or {}).get('error') or {}
        c['error'] = {'code': str(out.get('code') or er.get('code') or '?'), 'message': str(out.get('message') or er.get('message') or '')[:300]}
        return c
    ch = resp['choices'][0]; text = (ch.get('message') or {}).get('content') or ''
    if isinstance(text, list): text = ''.join(p.get('text', '') for p in text)
    c.update(finish=ch.get('finish_reason'), text=text)
    return c

def call(send, body, key, worst, budget, *, label, say=print, sleep=None, readable=None, names=None, on_retry=None, retry=True):
    """Send body (key: its reservation in budget, reserved before the call by the step's up-front check); once more after a
    failure or an unreadable reply (readable(text) False), after pause(), when budget.try_reserve has room for `worst`
    under every named limit. Each call settles its reservation once: its reported cost, or its worst case when its charge
    is not known (no reply in time). Each call records sent_at and finished_at (epoch seconds). Returns {'calls': [...], 'final': the last call, 'cost_usd': known cost,
    'worst_usd': unknown charges at their worst case}. retry=False: one call, never sent again (a doubled retry)."""
    sleep = sleep or time.sleep; calls = []; known = unknown = 0.0
    for attempt in ((1, 2) if retry else (1,)):
        t0 = time.time(); out = send(body); t1 = time.time()
        c = _read_call(out, worst); c.update(attempt=attempt, sent_at=round(t0, 3), finished_at=round(t1, 3))   # wall clock (epoch s):
        # comparable across processes, so the requests out at once can be counted over several PDFs run side by side
        if c.get('worst_usd'): unknown += worst; budget.settle(key, worst)
        else: known += float(c.get('cost') or 0); budget.settle(key, c.get('cost'))
        calls.append(c)
        failed = 'error' in c or (c.get('finish') != 'length' and readable is not None and not readable(c.get('text') or ''))
        if not failed or attempt == 2 or not retry: break
        why = (c['error']['message'] or f'OpenRouter {c["error"]["code"]}') if 'error' in c else 'the reply could not be read'
        ok, no = budget.try_reserve(key, worst, names)
        if not ok:
            c['why'] = f'{why}; not sent again: the {no} limit has no room for it'; say(f'  {label}: {c["why"]}'); break
        wait = pause(c.get('error', {}).get('code'))
        c['why'] = f'{why}; sent once more after {wait} s'
        if on_retry: on_retry(key, known, unknown + worst)
        say(f'  {label}: {why}; trying once more in {wait} s'); sleep(wait)
    return {'calls': calls, 'final': calls[-1], 'cost_usd': round(known, 6), 'worst_usd': round(unknown, 4)}
