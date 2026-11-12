"""webapp/names.py: the names people see, kept by the app only (#45, home interface; Patrick, 2026-11-06). Never written
into a run's record.json or review.html (the run's archive), never in a path, a command or a job's `run`.

    runs/.app/book-names.json   {sha256: {name, at, history: [{name, at}]}}   a book's name, set by a person
    runs/.app/run-names.json    {runs: {"<short name>/<label>": {name, at}}, batches: {label: {name, at}}}
    runs/.app/names.lock        one lock (flock) over every change to both files

    book_name(s, sha, file, title)   the name every page shows: the person's, else the PDF's Title cleaned (a leading
                                     "_tag_" and a trailing " copy" / " copy N" removed), else the file name's stem
    set_book_name(s, sha, name)      a person's name for the book (the home page's "Edit Name")
    label_for(s, name, kind, taken)  the folder label a plain run or batch name becomes: ASCII letters, digits, "-" and "_",
                                     starting with a letter or digit, at most 64; "<kind>-<date>" when nothing is left;
                                     "_2", "_3"… when taken (never "-2": compare_runs.py reads "x" as a prefix of "x-2")
    run_name(s, run) / batch_name(s, label)   the plain name, or None (a run made from the terminal shows its label)
    snapshot(s)                      one request's reads (#93): the three files and the job files, each read at most once;
                                     a page passes it down as nm= (never kept: the next page reads again)

Names are resolved when a page is drawn, so a rename shows everywhere at once; a rename also drops the home page's cache.
"""
import os, re, json, fcntl, datetime, unicodedata, contextlib
from . import books as BK

LABEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
NAME_MAX = 120

def _p(s, f): return os.path.join(s['jobs'], f)

def _load(p):
    try:
        d = json.load(open(p, encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError): return {}

def _save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = f'{p}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)

@contextlib.contextmanager
def locked(s):
    os.makedirs(s['jobs'], exist_ok=True)
    with open(_p(s, 'names.lock'), 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)

def clean_name(raw):
    """A person's name for a book, run or batch: one line, no control or direction characters, at most 120 characters;
    None when nothing is left."""
    n = unicodedata.normalize('NFC', str(raw or ''))
    n = ''.join(c for c in n if unicodedata.category(c) not in ('Cc', 'Cf', 'Zl', 'Zp'))
    n = re.sub(r'\s+', ' ', n).strip()[:NAME_MAX].strip()
    return n or None

def now(): return datetime.datetime.now().isoformat(timespec='seconds')

# ------------------------------------------------------------------ books
TAG = re.compile(r'^_[^_]{1,40}_\s*')                    # "_no template_Da Kine Talk…": a leading tag from the PDF's maker
COPY = re.compile(r'\s+copy(\s+\d+)?\s*$', re.I)         # "… copy", "… copy 2"

def auto_name(title, file):
    """The automatic name: the Title with a leading "_tag_" and a trailing " copy"/" copy N" removed, when it still looks
    like a title; else the file name's stem (conservative: "without INDEX" and the like are left for a person)."""
    t = re.sub(r'\s+', ' ', str(title or '')).strip()
    t = COPY.sub('', TAG.sub('', t)).strip()
    return t if BK.title_ok(t) else BK.stem_name(file or '')

def book_name(s, sha, file, title=None):
    """The one reader of a book's name (every page): the person's name, else auto_name(). A page passes its Snapshot and
    calls its book_name() instead (one read per request)."""
    return Snapshot(s).book_name(sha, file, title)

def set_book_name(s, sha, raw):
    name = clean_name(raw)
    if not name: raise ValueError('Type a name first.')
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha): raise ValueError('There is no such PDF.')
    with locked(s):
        d = _load(_p(s, 'book-names.json'))
        e = d.get(sha) if isinstance(d.get(sha), dict) else {}
        hist = (e.get('history') or []) + ([{'name': e['name'], 'at': e.get('at')}] if e.get('name') else [])
        d[sha] = {'name': name, 'at': now(), 'history': hist}
        _save(_p(s, 'book-names.json'), d)
    # the home page's cache stays (U3): names are applied when the list is read, so a rename never rebuilds it
    return name

# ------------------------------------------------------------------ runs and batches
def fold(name):
    """A plain name folded to a label: ASCII letters, digits, "-" and "_"; other characters become "-"."""
    a = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode()
    a = re.sub(r'[^A-Za-z0-9_-]+', '-', a)
    a = re.sub(r'-{2,}', '-', a).lstrip('-_').rstrip('-_')
    return a[:64].rstrip('-_')

def label_for(name, kind, taken):
    """The folder label for a plain name. taken(label) → True when a folder or a job already has it."""
    base = fold(name) or f'{kind}-{datetime.datetime.now():%Y-%m-%d-%H%M}'
    if not LABEL.fullmatch(base): base = f'{kind}-{base}'[:64]
    n, lab = 1, base
    while taken(lab):
        n += 1; suf = f'_{n}'; lab = base[:64 - len(suf)] + suf
    return lab

def set_run_name(s, run, raw, kind='runs'):
    name = clean_name(raw)
    if not name: return None
    with locked(s):
        d = _load(_p(s, 'run-names.json'))
        d.setdefault(kind, {})[run] = {'name': name, 'at': now()}
        _save(_p(s, 'run-names.json'), d)
    # the home page's cache stays (U3): names are applied when the list is read
    return name

def run_name(s, run):
    """A run's plain name, or None. A batch's book is named by its batch."""
    return Snapshot(s).run_name(run)

def batch_name(s, label):
    return Snapshot(s).batch_name(label)

def shown_run(s, run):
    """The name a page shows for a run: its plain name, else (made from the terminal) its label; a batch's book shows its
    batch's name."""
    return Snapshot(s).shown_run(run)

# ------------------------------------------------------------------ one request's reads (#93)
def snapshot(s):
    """A new Snapshot for one request (see the class)."""
    return Snapshot(s)

class Snapshot:
    """One request's reads (#93, fix 2): book-names.json, run-names.json and books-cache.json, and the app's job files, each
    read at most once, on first use (and Tesseract's languages asked once), with the same rules as the module functions below. A page makes one, passes it down
    (`nm=`), and drops it with the request: it is never kept in the settings or in a module, so a rename shows on the next
    page, and the single uses (a button's answer, a form) read fresh every time. A rename made while a page is being drawn
    shows in all of its rows or in none of them.

    books-cache.json is written through (review 02 M1): books.meta() reads it here and, when it writes a missing Title,
    updates this copy too, so a row drawn after the PDF list sees the Title the list just wrote."""
    def __init__(self, s): self.s, self._books, self._runs, self._cache, self._jobs, self._langs = s, None, None, None, None, None
    def books(self):
        if self._books is None: self._books = _load(_p(self.s, 'book-names.json'))
        return self._books
    def runs_(self):
        if self._runs is None: self._runs = _load(_p(self.s, 'run-names.json'))
        return self._runs
    def cache(self):
        """books-cache.json ({sha256: {title, pages, …}}), read once."""
        if self._cache is None: self._cache = BK._load(_p(self.s, 'books-cache.json')) or {}
        return self._cache
    def put(self, sha, m):
        """books.meta() wrote this entry to the file: this request sees it too."""
        self.cache()[sha] = m
    def jobs(self):
        """The app's jobs (webapp/jobs.py all_jobs), read once."""
        if self._jobs is None:
            from . import jobs as JB
            self._jobs = JB.all_jobs(self.s['jobs'])
        return self._jobs
    def langs(self):
        """Tesseract's installed languages (books.installed_langs: one `tesseract --list-langs`), asked once (review 04 M-A)."""
        if self._langs is None:
            from . import books as BK
            self._langs = BK.installed_langs(self.s)
        return self._langs
    def book_name(self, sha, file, title=None):
        if sha:
            e = self.books().get(sha)
            if isinstance(e, dict) and e.get('name'): return e['name']
            if title is None: title = (self.cache().get(sha) or {}).get('title')
        return auto_name(title, file)
    def run_name(self, run):
        e = (self.runs_().get('runs') or {}).get(run)
        return e.get('name') if isinstance(e, dict) else None
    def batch_name(self, label):
        e = (self.runs_().get('batches') or {}).get(label)
        return e.get('name') if isinstance(e, dict) else None
    def shown_run(self, run):
        p = run.split('/')
        if p[0] == 'batches' and len(p) >= 2: return self.batch_name(p[1]) or p[1]
        return self.run_name(run) or p[-1]

