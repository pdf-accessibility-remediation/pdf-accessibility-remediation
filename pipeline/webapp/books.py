"""webapp/books.py: the books the app offers (the samples folder and the uploads folder), their display names, and
"Add a Book" (an upload into the uploads folder). Read only for samples; uploads are only ever added, never replaced.

    listing(s)              [{key (sha256), name, file, group: sample | added, pages, size, locked, unreadable, path}]
    by_key(s, key)          one book by its sha256, or None (a request names a book by its key, never by a path)
    receive(s, rfile, n, name)   an upload: streamed to uploads/.incoming/<random>.part, hashed while written, then given its
                            final name with os.link (never replaces a file), under uploads/.lock; raises Refused
    hashes(s, paths)        {path: sha256} through runs/.app/sha256-cache.json (path → [size, mtime_ns, sha256]): the cache
                            webapp/runs.py find_original() uses too

The display name (#45, Q6): the PDF's own Title when it looks like a title (not empty, not "untitled", not a file or
program name), else the file name without ".pdf", with "_" and "-" read as spaces. Wherever a book is named, the page also
shows "Source PDF Filename: <file name>" under it (the one file name the pages show; docs/app.md). Titles and page counts
are read once per sha256 into runs/.app/books-cache.json. Reading an untrusted PDF never fails the page: any error falls
back to the file name, and a password-locked PDF is listed as locked.
"""
import os, re, json, fcntl, shutil, hashlib, secrets, unicodedata, datetime, contextlib, threading

PDF_HEAD = b'%PDF-'
NAME_MAX_BYTES = 200
SPARE_BYTES = 100 * 1024 * 1024                  # an upload needs its own size plus this much free space
_lock = threading.Lock()                         # the two cache files, within this process (across processes: replace())

class Refused(Exception):
    """An upload that is refused: (HTTP status, plain words)."""
    def __init__(self, status, words): super().__init__(words); self.status, self.words = status, words

def _load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return None

def _save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = f'{p}.{os.getpid()}.{threading.get_ident()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, indent=0, ensure_ascii=False)
    os.replace(tmp, p)

def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

# ------------------------------------------------------------------ hashes (shared with runs.find_original)
def hashes(s, paths, stop=None):
    """{path: sha256} for the given files, through runs/.app/sha256-cache.json ({path: [size, mtime_ns, sha256]}). stop(path,
    sha) → True ends the walk early (find_original stops at its match). Files that cannot be read are left out."""
    cache_p = os.path.join(s['jobs'], 'sha256-cache.json')
    with _lock: cache = _load(cache_p) or {}
    out, dirty = {}, False
    for p in paths:
        try: st = os.stat(p)
        except OSError: continue
        key = [st.st_size, st.st_mtime_ns]
        c = cache.get(p)
        if not c or c[:2] != key:
            try: c = key + [sha_file(p)]
            except OSError: continue
            cache[p] = c; dirty = True
        out[p] = c[2]
        if stop and stop(p, c[2]): break
    if dirty:
        with _lock:
            cur = _load(cache_p) or {}; cur.update({p: cache[p] for p in out}); _save(cache_p, cur)
    return out

def pdfs_in(root):
    """Every *.pdf under root, dot-folders and dot-files left out (uploads/.incoming holds only .part files anyway)."""
    found = []
    if not os.path.isdir(root): return found
    for d, subs, fs in os.walk(root):
        subs[:] = sorted(x for x in subs if not x.startswith('.'))
        found += [os.path.join(d, f) for f in sorted(fs) if f.lower().endswith('.pdf') and not f.startswith('.')]
    return found

# ------------------------------------------------------------------ names
NOT_TITLE = re.compile(r'^(untitled|title|document|microsoft word\b|adobe\b|pdf\b)|\.(indd|docx?|pdf|qxd|qxp|tiff?|txt|rtf|p65|pm\d|ps|eps|fm|book)\s*$', re.I)

def stem_name(file):
    """The file name without ".pdf", "_" and "-" read as spaces."""
    base = re.sub(r'\.pdf$', '', file, flags=re.I)
    return re.sub(r'\s+', ' ', re.sub(r'[_-]+', ' ', base)).strip() or file

def title_ok(t):
    if not isinstance(t, str): return False
    t = t.strip()
    return 3 <= len(t) <= 300 and sum(c.isalpha() for c in t) >= 3 and not NOT_TITLE.search(t) and not re.fullmatch(r'[\w.-]+\.\w{2,4}', t)

def display_name(title, file):
    t = re.sub(r'\s+', ' ', str(title or '')).strip()
    return t if title_ok(t) else stem_name(file)

def shown_file(name):
    """A file name as a page shows it ("Source PDF Filename:"): control and bidirectional characters removed. The pages
    escape it too."""
    return ''.join(c for c in unicodedata.normalize('NFC', str(name)) if unicodedata.category(c) not in ('Cc', 'Cf'))

def clean_upload_name(raw):
    """An uploaded file's name as it will be kept: NFC, no control or bidirectional characters, no path, no leading dot,
    "#" and "|" (the book list's comment and result marks) as "_", at most 200 bytes, ending in .pdf. None when nothing
    is left."""
    n = unicodedata.normalize('NFC', str(raw or ''))
    n = n.replace('\\', '/').split('/')[-1]
    n = ''.join(c for c in n if unicodedata.category(c) not in ('Cc', 'Cf', 'Zl', 'Zp'))
    n = re.sub(r'[#|]', '_', n).strip().lstrip('.').strip()
    stem = re.sub(r'\.pdf$', '', n, flags=re.I).strip()
    if not stem or not any(c.isalnum() for c in stem): return None
    while len((stem + '.pdf').encode('utf-8')) > NAME_MAX_BYTES: stem = stem[:-1]
    return stem.rstrip() + '.pdf'

# ------------------------------------------------------------------ titles and pages
def read_meta(p):
    """{title, pages, locked, unreadable} of a PDF; never raises (an untrusted file)."""
    try:
        import pikepdf
        try:
            with pikepdf.open(p) as pdf:
                out = {'pages': len(pdf.pages), 'title': None, 'locked': False, 'unreadable': False}
                try:
                    st = pdf.Root.get('/StructTreeRoot')
                    out['tagged'] = bool(st is not None and st.get('/K') is not None)
                except Exception: out['tagged'] = None
                try: out['title'] = str(pdf.docinfo.get('/Title') or '') or None
                except Exception: pass
                if not title_ok(out['title']):
                    try:
                        m = pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False)
                        t = m.get('dc:title')
                        if t: out['title'] = str(t)
                    except Exception: pass
                return out
        except pikepdf.PasswordError: return {'pages': None, 'title': None, 'locked': True, 'unreadable': False}
    except Exception: return {'pages': None, 'title': None, 'locked': False, 'unreadable': True}

def meta(s, sha, path):
    cp = os.path.join(s['jobs'], 'books-cache.json')
    with _lock: c = _load(cp) or {}
    if sha in c: return c[sha]
    m = read_meta(path)
    with _lock:
        cur = _load(cp) or {}; cur[sha] = m; _save(cp, cur)
    return m

# ------------------------------------------------------------------ the list
def listing(s):
    """Every book: the samples first, then the uploads, each in folder order. A book whose content is listed twice (the
    same sha256 in both folders) is shown once, from where it is first found."""
    out, seen = [], set()
    for group, root in (('sample', s['samples']), ('added', s['uploads'])):
        ps = pdfs_in(root)
        hs = hashes(s, ps)
        for p in ps:
            sha = hs.get(p)
            if not sha or sha in seen: continue
            seen.add(sha)
            m = meta(s, sha, p)
            f = os.path.basename(p)
            try: size = os.path.getsize(p)
            except OSError: continue
            out.append({'key': sha, 'name': display_name(m.get('title'), f), 'file': shown_file(f), 'group': group, 'pages': m.get('pages'),
                        'size': size, 'locked': bool(m.get('locked')), 'unreadable': bool(m.get('unreadable')), 'path': p,
                        'folder': os.path.relpath(os.path.dirname(p), root)})
    return out

def by_key(s, key):
    if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key): return None
    return next((b for b in listing(s) if b['key'] == key), None)

def name_of_sha(s, sha, file=None):
    """A book's display name from its sha256 (the books cache), else from its file name."""
    with _lock: c = _load(os.path.join(s['jobs'], 'books-cache.json')) or {}
    m = c.get(sha) or {}
    return display_name(m.get('title'), file or '') if (m or file) else None

def size_words(n):
    return f'{n / 1e6:.1f} MB' if n >= 1e5 else f'{max(1, round(n / 1e3))} KB'

# ------------------------------------------------------------------ Add a Book
@contextlib.contextmanager
def _uploads_lock(U):
    os.makedirs(U, exist_ok=True)
    with open(os.path.join(U, '.lock'), 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)

def limit_bytes(s): return int(s.get('upload_max_mb') or 1024) * 1024 * 1024

def receive(s, rfile, length, raw_name):
    """Keep one uploaded PDF in the uploads folder. length: the request's checked Content-Length. Returns the new book's
    listing entry; raises Refused (the original on the person's computer is only ever read by their browser)."""
    U = s['uploads']
    name = clean_upload_name(raw_name)
    if not name: raise Refused(400, 'This file has no usable name. Rename it, then add it again.')
    if length > limit_bytes(s): raise Refused(413, f'This file is larger than the limit of {limit_bytes(s) // (1024 * 1024 * 1024) or 1} GB.')
    os.makedirs(os.path.join(U, '.incoming'), exist_ok=True)
    if shutil.disk_usage(U).free < length + SPARE_BYTES: raise Refused(507, 'There isn\'t enough space on this computer to add this book.')
    tmp = os.path.join(U, '.incoming', secrets.token_hex(8) + '.part')
    h = hashlib.sha256(); got = 0; head = b''
    try:
        with open(tmp, 'xb') as f:
            while got < length:
                b = rfile.read(min(1 << 20, length - got))
                if not b: break
                if len(head) < 1024: head += b[:1024 - len(head)]
                h.update(b); f.write(b); got += len(b)
        if got != length: raise Refused(400, 'The upload stopped before the whole file arrived. Try again.')
        if PDF_HEAD not in head: raise Refused(415, 'This file isn\'t a PDF.')
        sha = h.hexdigest()
        with _uploads_lock(U):
            for b in listing(s):                                   # the same content already there: say where
                if b['key'] == sha:
                    raise Refused(409, f'This book is already in the list as "{b["name"]}" ({"a sample book" if b["group"] == "sample" else "an added book"}).')
            stem, n = name[:-4], 1
            while True:
                final = os.path.join(U, name if n == 1 else f'{stem}-{n}.pdf')
                try: os.link(tmp, final); break                    # never replaces a file
                except FileExistsError: n += 1
            m = read_meta(final)
            with _lock:
                cp = os.path.join(s['jobs'], 'books-cache.json'); cur = _load(cp) or {}; cur[sha] = m; _save(cp, cur)
            side = {'original_name': shown_file(raw_name), 'file': os.path.basename(final), 'bytes': got, 'sha256': sha,
                    'added': datetime.datetime.now().isoformat(timespec='seconds'), 'pages': m.get('pages')}
            sp = final[:-4] + '.json'
            try:
                with open(sp, 'x', encoding='utf-8') as f: json.dump(side, f, indent=1, ensure_ascii=False)
            except FileExistsError: pass                          # a sidecar of that name is someone's own file: left as it is
        hashes(s, [final])
        return next(b for b in listing(s) if b['key'] == sha)
    finally:
        try: os.remove(tmp)
        except OSError: pass

# ------------------------------------------------------------------ OCR languages (New Run, New Batch)
# Each choice is shown only when every Tesseract pack it names is installed. English is the default; nothing is guessed.
OCR_CHOICES = [('eng', 'English'), ('chi_tra+eng', 'Chinese (Traditional) and English'), ('chi_sim+eng', 'Chinese (Simplified) and English'),
               ('jpn+eng', 'Japanese and English'), ('jpn_vert+jpn+eng', 'Japanese (vertical text) and English'), ('kor+eng', 'Korean and English'),
               ('vie+eng', 'Vietnamese and English'), ('tgl+eng', 'Tagalog and English'), ('fra+eng', 'French and English'),
               ('deu+eng', 'German and English'), ('spa+eng', 'Spanish and English')]

def ocr_choices(installed):
    have = set(installed or [])
    return [(v, n) for v, n in OCR_CHOICES if all(x in have for x in v.split('+'))] or [('eng', 'English')]

def installed_langs(s):
    from . import checks, config
    rc, t = checks._run(['tesseract', '--list-langs'], config.child_env(s), timeout=30)
    return [l.strip().split('/')[-1] for l in (t or '').splitlines()[1:] if l.strip()] if rc == 0 else []
