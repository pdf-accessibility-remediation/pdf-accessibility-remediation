"""lib/runlock.py: the record lock: one writer at a time of a finished run's record.json, review.md, review.html and
release/, across threads and processes (the app and the review server are threaded HTTP servers).

    with record_lock(R, wait=REQUEST_WAIT):     # read, change and write the run's files inside
        ...

Each holder opens <run>/.record.lock itself and takes flock(LOCK_EX | LOCK_NB), retried every 0.1 s for `wait` seconds
(REQUEST_WAIT in a request thread, COMMAND_WAIT on the command line and in jobs), then Busy. Two threads or two
processes each have their own open file, so flock keeps them apart; no in-process counter lets anyone skip it.

Not re-entrant: no writer calls another while holding it (checked 2026-10-31: ocr.record, sessions.mark_pending,
sessions.promote, review/manual.py), so taking it twice in one thread is a bug and raises RuntimeError. The mark is kept
per thread and per run (realpath).

Lock order, never the reverse: reviews/.lock (O_EXCL: refuses, never waits) → _intake/.verdict.lock → <run>/.record.lock.
runs/.app/dispatch.lock is never held while taking the record lock, and the record lock never while taking it.
"""
import os, time, fcntl, threading, contextlib

NAME = '.record.lock'
REQUEST_WAIT, COMMAND_WAIT = 5, 120
BUSY = 'Another change to this book is being saved. Try again in a moment.'
_mine = threading.local()

class Busy(Exception):
    """The lock stayed taken for the whole wait: nothing was written."""

def _held():
    s = getattr(_mine, 'runs', None)
    if s is None: s = _mine.runs = set()
    return s

def holding(R):
    """True while this thread holds R's record lock."""
    return os.path.realpath(R) in _held()

@contextlib.contextmanager
def record_lock(R, wait=COMMAND_WAIT):
    key = os.path.realpath(R); held = _held()
    if key in held: raise RuntimeError(f'record lock taken twice in one thread ({key})')
    with open(os.path.join(key, NAME), 'a') as f:
        end = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.monotonic() >= end: raise Busy(BUSY)
                time.sleep(0.1)
        held.add(key)
        try: yield
        finally:
            held.discard(key)
            fcntl.flock(f, fcntl.LOCK_UN)
