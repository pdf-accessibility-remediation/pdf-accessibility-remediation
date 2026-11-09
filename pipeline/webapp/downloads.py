"""webapp/downloads.py: a run's versions and their downloads (issue #38, stage 3): the remediated PDF and the record ZIP of
any version, offered at any time, ready or not, each named by its state (lib/release.py download_names).

    versions(R, rec)          [{id, label, session, dir, pdf, sha, state, marked}] newest first: the current version, then
                              each earlier result whose PDF still exists (one whose PDF "Clean Up Space" removed,
                              review/prune.py, is not listed)
    prepare(R, run, v, what)  the download, opened in one moment under the record lock: {name, ctype, members | fh}
    stream_zip(out, d)        the record ZIP, written to the response as it is built (never kept on disk)

One moment per download (02 S6, 03 §3.6): under the record lock (5 s at most in a request thread) the record and the
version list are read, the names worked out and every member file opened; the lock is then released and the bytes
stream from the open handles. A promotion moves files by rename, which never touches an open handle, so a ZIP never mixes
two versions. A version id comes only from the run's own list: no path is ever built from the request.

The ZIP is opened by library staff (Patrick, 2026-11-01): one folder named as the ZIP, holding only the PDF (stored, never
compressed again, under its own name), review.html (the evaluation's results are in it), han_review.csv when the book has
one (review.html sends staff to it; review 30 S1), and READ-ME.txt in plain words. No accessibility statement (Patrick,
2026-11-01: writing one is for the institution that adopts the pipeline; a folder shipped before keeps its files, never
zipped). Never review.md or evaluation-results.json (they stay in the run folder and in release/shipped/NNN/), record.json (it holds the AI's raw reply),
digests, crops, reviews/, _intake/, release/drafts.json, dot-files or working files: the list is an allow-list. The ZIP's
review.html keeps only the links that work inside the ZIP (zip_page()).
"""
import os, re, io, html, hashlib, zipfile, datetime, unicodedata
from lib import release as REL, dates as D, runlock
from review import sessions as S, manual as M
from . import config, manualpage as MP

# a download's own words (review 20 L1): never the Record page's "…so no check can be recorded for it"
CHANGED = 'The book\'s PDF has changed since this report was made, so it can\'t be downloaded as this version. Whoever looks after the app can check it.'
MISSING = 'The book\'s remediated PDF is missing, so it can\'t be downloaded. Whoever looks after the app can check it.'
EARLIER_CHANGED = ('The PDF of this previous version has changed since it was made, so it can\'t be downloaded as that version. '
                   'Whoever looks after the app can check it.')

BAD_NAME = ('This version\'s file name in its record is not a plain file name, so it can\'t be downloaded. '
            'Whoever looks after the app can check it.')

def plain_name(name):
    """A PDF name from a record that is a plain file name in its own folder: no "/" or "\\", no "..", no leading dot, no
    control character. A hand-edited record.json then never makes a ZIP entry or a path outside its folder (35)."""
    return (isinstance(name, str) and bool(name) and '/' not in name and '\\' not in name and '..' not in name
            and not name.startswith('.') and not any(unicodedata.category(c) == 'Cc' for c in name))

class Refused(Exception):
    """A download that cannot be given now, in plain words for the page (409), or None words for a plain 404."""

def _version_label(sid):
    return f'Session {int(sid)}' if str(sid).isdigit() else 'the version applied without a review' if sid == 'ai' else f'version {sid}'

def removed(R): return REL.removed(R)

def versions(R, rec, glance=None):
    """The run's versions, newest first. The current version's state is its status (app_glance: the record's hash first,
    a changed file never Ready); an earlier version's is 'earlier version' (K3). An earlier version is listed only while
    its PDF exists; one whose PDF was removed (release/removed.json) is not listed."""
    R = os.path.abspath(R); doc = rec.get('document') or {}
    sid = S.current_id(rec)
    g = glance if glance is not None else MP.app_glance(R, rec, rec.get('glance') or {'ship': []})
    st = g.get('status') or {}
    rel = REL.load(R)
    shipped = {REL.sha_of(s) for s in REL.live_shipments(rel)}
    cur_sha = MP.app_sha(R, rec)
    state = REL.SHIPPED if st.get('name') == REL.SHIPPED and cur_sha in shipped else (st.get('current') or {}).get('name') or st.get('name') or REL.NOT_READY
    out = [{'id': 'current', 'session': sid if str(sid).isdigit() else None, 'dir': R, 'pdf': os.path.join(R, doc.get('output') or ''),
            'sha': cur_sha, 'state': state, 'status_text': st.get('text') if state != REL.SHIPPED else REL.SHIPPED,
            'label': f'Current version ({_version_label(sid)}): {st.get("text") or state}' if str(sid).isdigit()
                     else f'Current version (applied without a review): {st.get("text") or state}'}]
    V = os.path.join(R, 'reviews', 'versions')
    try: names = sorted((e.name for e in os.scandir(V) if e.is_dir() and not e.name.startswith('.')), key=lambda n: (-S.sid_n(n), n))
    except OSError: names = []
    gone = {x.get('version') for x in removed(R)}
    for n in names:
        d = os.path.realpath(config.entry(V, n) or '')
        if not d.startswith(os.path.realpath(V) + os.sep): continue
        vrec = S.load(os.path.join(d, 'record.json')) or {}
        out_name = (vrec.get('document') or {}).get('output')
        pdf = os.path.join(d, out_name) if out_name else None
        if not plain_name(out_name) or not os.path.isfile(pdf) or n in gone: continue   # never a path outside its folder
        out.append({'id': n, 'session': n if str(n).isdigit() else None, 'dir': d, 'pdf': pdf, 'sha': MP.disk_sha(pdf),
                    'state': 'earlier version', 'status_text': None, 'label': f'{_version_label(n)[0].upper() + _version_label(n)[1:]} (previous version)'})
    changed = MP.disk_state(R, rec)['same'] is False
    cleared = bool(REL.cleared(R))
    if cleared: out = []                                      # #45: cleared (or being cleared): only the shipped copies (02 B2, 05 L3)
    for s in reversed(rel.get('shipped') or []):             # shipped copies: listed when the current entry is not them (M7)
        d = _shipped_dir(R, s); f = (s.get('pdf') or {}).get('file')
        if not d or not plain_name(f) or not os.path.isfile(os.path.join(d, f)): continue
        ssha = REL.sha_of(s)
        if not cleared and ssha == cur_sha and not changed and not s.get('withdrawn'): continue
        ses = (s.get('pdf') or {}).get('session')
        out.append({'id': f'shipment-{s.get("n")}', 'session': ses, 'dir': d, 'pdf': os.path.join(d, f), 'sha': ssha, 'shipment': s.get('n'), 'entry': s,
                    'state': 'withdrawn' if s.get('withdrawn') else REL.SHIPPED, 'status_text': None,
                    'label': f'Shipment {s.get("n")}, shipped on {D.day(s.get("shipped"))}' + (f' ({_version_label(ses)})' if str(ses or '').isdigit() else '')
                             + (' (withdrawn)' if s.get('withdrawn') else '')})
    return out

MARKED = {REL.NOT_READY: 'not ready', REL.PENDING: 'not ready', REL.READY: 'not shipped', 'earlier version': 'previous version', 'withdrawn': 'withdrawn'}   # the state key stays
SHIPPED_CHANGED = 'The shipped copy has changed since it was shipped, so it can\'t be downloaded. Whoever looks after the app can check it.'

def _shipped_dir(R, s):
    """A shipment's folder, release/shipped/NNN, from its shipped.json entry (never a path from the request), or None."""
    base = os.path.realpath(os.path.join(R, 'release', 'shipped'))
    d = os.path.realpath(os.path.join(R, 'release', s.get('folder') or f'shipped/{int(s.get("n") or 0):03d}'))
    return d if d.startswith(base + os.sep) and os.path.isdir(d) else None
# on the evaluation page, beside a version that is not the current one (review 29 R1): what is recorded there is the current one's
EARLIER_HERE = 'Results on this page are recorded for the current version only.'

def marked_line(state):
    """The line beside the picker: what the downloaded files' names say (no file name on the page). Empty for a shipped
    version: the line above the downloads and the version's own label already say it was shipped (Patrick, 2026-11-01)."""
    w = MARKED.get(state)
    return f'The downloaded files are marked "{w}."' if w else ''

def prepare(R, run, v, what, wait=runlock.REQUEST_WAIT):
    """The download of version `v` ('current' or an id from versions()), `what` 'pdf' or 'record', opened in one moment
    under the record lock. Raises Refused (409 words, or None: not found)."""
    R = os.path.abspath(R)
    try:
        with runlock.record_lock(R, wait):
            if os.path.exists(S.P(R)['promoting']): raise Refused(M.PROMOTING)
            rec = S.load(os.path.join(R, 'record.json'))
            if rec is None: raise Refused(None)
            import report_html as H                                     # the current version's state from the full glance
            try: g = MP.app_glance(R, rec, H.glance_of(R, rec))
            except Exception: g = MP.app_glance(R, rec, rec.get('glance') or {'ship': []})
            vs = versions(R, rec, g)
            ver = next((x for x in vs if x['id'] == v), None)
            if ver is None: raise Refused(None)                          # not one of the run's own versions
            if ver['id'] == 'current' and not plain_name((rec.get('document') or {}).get('output')):
                raise Refused(BAD_NAME)                                  # before its file is looked at
            about = None
            if ver.get('shipment'):                                      # a shipped copy: its folder's own files (never its record.json)
                if MP.disk_sha(ver['pdf']) != ver['sha']: raise Refused(SHIPPED_CHANGED)
                vrec = {'document': {'output': (ver['entry'].get('pdf') or {}).get('file')}}
                about = S.load(os.path.join(ver['dir'], 'record.json')) or {}   # its run details for the read-me (never zipped)
            elif ver['id'] == 'current':
                disk = MP.disk_state(R, rec)
                if disk['missing']: raise Refused(MISSING)
                if disk['same'] is False: raise Refused(CHANGED)
                vrec = rec
            else:                                                        # an earlier version: its PDF against its own record (L4)
                vrec = S.load(os.path.join(ver['dir'], 'record.json')) or {}
                want = (vrec.get('document') or {}).get('output_sha256')
                if want and ver['sha'] != want: raise Refused(EARLIER_CHANGED)
            out = (vrec.get('document') or {}).get('output')
            if not plain_name(out): raise Refused(BAD_NAME)               # every version's name, as its record gives it
            pdf_name, zip_name = REL.download_names(out, ver['session'], ver['state'], ver.get('shipment') or next((s.get('n') for s in REL.live_shipments(REL.load(R)) if REL.sha_of(s) == ver['sha']), None))
            if what == 'pdf':
                return {'name': pdf_name, 'ctype': 'application/pdf', 'fh': open(ver['pdf'], 'rb')}
            members = []                                                  # every handle opened here is closed if a later step fails (35)
            try:
                rel = REL.load(R)
                members.append((out, open(ver['pdf'], 'rb'), zipfile.ZIP_STORED))
                han = os.path.join(ver['dir'], 'han_review.csv')              # the Han-only runs a person checks, when the book has them
                names = [out, 'review.html'] + (['han_review.csv'] if os.path.isfile(han) else []) + ['READ-ME.txt']
                p = os.path.join(ver['dir'], 'review.html')
                if os.path.isfile(p):                                         # read now (small): its links are made to fit the ZIP
                    with open(p, encoding='utf-8') as f: page = zip_page(f.read(), names)
                    members.append(('review.html', io.BytesIO(page.encode('utf-8')), zipfile.ZIP_DEFLATED))
                if os.path.isfile(han): members.append(('han_review.csv', open(han, 'rb'), zipfile.ZIP_DEFLATED))
                cur_label = _version_label(S.current_id(rec))
                book = MP.book(rec)['title']
                return {'name': zip_name, 'ctype': 'application/zip', 'members': members, 'folder': zip_name[:-4], 'rel': rel, 'version': ver, 'R': R,
                        'shipments': [s for s in rel.get('shipped') or [] if REL.sha_of(s) == ver['sha']],
                        'pdf_name': out, 'book': book, 'cur_label': cur_label,
                        'applied': MP.version(R, rec)['when'] if ver['id'] == 'current' else _applied(R, ver['id'], vrec),
                        'about': about if ver.get('shipment') else vrec}
            except BaseException:
                for _, fh, _ in members: fh.close()
                raise
    except runlock.Busy as e: raise Refused(str(e))

def _applied(R, vid, vrec):
    """An earlier version's "applied on …" for its read-me: its session's applied time, else its record's."""
    when = (S.session(R, vid) or {}).get('applied') or vrec.get('written')
    return f'applied on {D.when(when)}' if when else None

_HEAD_LINK = ' · <a href="review.md">review.md</a> (the record, as text)'      # report_html's header: review.md is not in the ZIP
_A = re.compile(r'<a\b[^>]*?\bhref="([^"]*)"[^>]*>(.*?)</a>', re.S)

def zip_page(page, names):
    """review.html as the ZIP holds it: the header's review.md link dropped, and the accessibility statement's link a page
    written before 2026-11-01 may hold removed with it (no_statement); every other link that would lead outside the ZIP (a
    previous result, a file of the run folder) unwrapped to its text. Links within the page (#…) and to the web stay."""
    page = REL.no_statement(page.replace(_HEAD_LINK, '', 1))
    def fix(m):
        href = html.unescape(m.group(1))
        if href.startswith('#') or re.match(r'https?://', href) or href in names: return m.group(0)
        return m.group(2)
    return _A.sub(fix, page)

class _Out:
    """The response stream for zipfile: write only, no seek or tell (zipfile then writes data descriptors)."""
    def __init__(self, w): self.w = w
    def write(self, b): self.w.write(b); return len(b)
    def flush(self): self.w.flush()

HAN_WORDS = 'han_review.csv: passages in Chinese or Japanese a person needs to check, as a spreadsheet.'   # Patrick, 2026-11-01
FILE_WORDS = {'review.html': 'review.html: the report on this version (what was changed, what was checked, and the results of the '
                              'accessibility evaluation). Open it in a web browser.',
              'han_review.csv': HAN_WORDS,
              'READ-ME.txt': 'READ-ME.txt: this file.'}

SOFTWARE = (('python', 'Python'), ('pikepdf', 'pikepdf'), ('pdfplumber', 'pdfplumber'), ('pypdfium2', 'pypdfium2'), ('pillow', 'Pillow'),
            ('fonttools', 'fontTools'))

def _duration(s):
    """3 min 15 s, 45 s, 1 h 2 min; under half a second, "less than 1 s"."""
    if s < 0.5: return 'less than 1 s'
    s = int(round(s))
    if s < 60: return f'{s} s'
    if s < 3600: return f'{s // 60} min {s % 60} s'
    return f'{s // 3600} h {s % 3600 // 60} min'

def _ocr_tagging(rec):
    """"OCR and Auto-Tagging": what intake did to the original, in plain words (Patrick, 2026-11-01): the pages that are
    pictures with no text (from OCR's own lists: text added, or none added) and the tags (none and tagged automatically,
    a placeholder tagged again, or already tagged). "not recorded" when the record has no intake."""
    i = rec.get('intake') or {}
    if not i: return 'not recorded'
    ts = (i.get('tag_tree') or {}).get('status') or i.get('tag_tree_status')
    if i.get('status') == 'skipped' or ts == 'tagged': return 'not needed: the PDF was already tagged.'
    o = i.get('ocr') or {}
    added, none = len(o.get('pages_with_ocr_text') or []), len(o.get('image_pages_without_text') or [])
    pics = ((i.get('triage') or {}).get('counts') or {}).get('image-only') or (added + none)
    lead = '1 page is a picture with no text' if pics == 1 else f'{pics} pages are pictures with no text'
    if not pics and not added: pages = 'every page has text, so no OCR was needed'
    elif added > pics: pages = f'OCR added text to {added} pages' + (f'; no text was added for {none} that are pictures' if none else '')
    elif not added: pages = lead + (', so no text was added for it' if pics == 1 else ', so no text was added for them')
    elif not none: pages = lead + (', so OCR added its text' if pics == 1 else ', so OCR added their text')
    else: pages = lead + f': OCR added text to {added} of them, and no text was added for the other {none if none > 1 else "one"}'
    auto = any(s.get('step') == 'autotag' and not s.get('error') for s in i.get('steps') or []) or \
        bool((i.get('plan') or {}).get('autotag') and (i.get('result') or {}).get('pdf'))
    if ts == 'placeholder': tags = 'the PDF\'s tags held no text structure, so it was tagged again automatically' if auto else \
                                   'the PDF\'s tags held no text structure, and it was not tagged again'
    else: tags = 'the PDF had no tags and was tagged automatically' if auto else 'the PDF had no tags and was not tagged automatically'
    return f'{pages}; {tags}.'

# the parts of a run's computer time (record.json timing_seconds, by run_api.sh's step labels; review/sessions.py reapply)
PARTS = (('intake', ('0/5',)), ('audit', ('1/5',)), ('AI request', ('2/5', '3/5')), ('preparing the review', ('review:',)),
         ('applying and checks', ('4/5',)))

def _runtime(rec):
    """"Total runtime": the computer's time across the whole run, its parts in parentheses, never the time a person spent
    reviewing (Patrick, 2026-11-01). A part with no time kept says "not recorded", and the total then says "at least". An
    AI call made by this run that kept only its own seconds (run.seconds) counts with those; a reused answer is named."""
    t = {k: v for k, v in (rec.get('timing_seconds') or {}).items() if isinstance(v, (int, float))}
    run = rec.get('run') or {}
    parts, missing, total = [], False, 0.0
    for name, pre in PARTS:
        got = [v for k, v in t.items() if k.startswith(pre)]
        if not got and (name == 'preparing the review' or (name == 'intake' and not rec.get('intake'))): continue   # not part of this run
        if not got and name == 'AI request' and isinstance(run.get('seconds'), (int, float)) and not run.get('response_from'): got = [run['seconds']]
        label = 'AI request (a previous answer reused)' if name == 'AI request' and run.get('response_from') else name
        if not got: parts.append(f'{label} not recorded'); missing = True; continue
        total += sum(got); parts.append(f'{label} {_duration(sum(got))}')
    total += sum(v for k, v in t.items() if not any(k.startswith(x) for _, pre in PARTS for x in pre))
    if not total: return 'Total runtime: not recorded'
    return f'Total runtime: {"at least " if missing else ""}{_duration(total)} ({", ".join(parts)}); the review time is not counted.'

def about_lines(rec):
    """The run details of a version's own record, for staff: pages, when it was remediated, the AI call (the original one for a
    reused reply: lib/origin.py), what OCR and auto-tagging did, the computer's total time and the software. No hashes or
    file names."""
    from lib import origin
    run = rec.get('run') or {}; doc = rec.get('document') or {}
    ai = origin.summary(rec); cost, model = origin.words(ai)
    if ai.get('cost_usd') is not None:
        cost = origin.money(ai['cost_usd']) + (f', from the original AI request on {D.day(ai["date"])}' if ai.get('reused') and ai.get('date') else '')
    per = origin.money(ai['cost_per_page_usd']) if ai.get('cost_per_page_usd') is not None else 'not recorded'
    env = rec.get('environment') or {}
    soft = ', '.join(f'{name} {env[k]}' for k, name in SOFTWARE if env.get(k))
    return [f'Pages: {doc["pages"]}' if doc.get('pages') else 'Pages: not counted',
            f'Remediated: {D.when(run.get("started"), "not recorded")}',
            f'AI model: {model}',
            f'AI cost: {cost} · Cost per page: {per}',
            f'OCR and Auto-Tagging: {_ocr_tagging(rec)}',
            _runtime(rec),
            f'Software: {soft}' if soft else 'Software: not recorded']

def shown(name):
    from . import books as BK
    return BK.shown_file(name)

def _readme(d, sha):
    """READ-ME.txt in plain words for library staff (Patrick, 2026-11-01): the source PDF's name, the version, its status,
    its shipments (21 §B: "Shipment 1, shipped on … by …", "Withdrawn on … by …: …"), the run details
    (about_lines) and what each file is. No hash: staff never compare one by hand (Patrick, 2026-11-01)."""
    ver = d['version']
    if ver['id'] == 'current':
        vline = f'Version: the current version ({_version_label(ver["session"]) if ver["session"] else "applied without a review"})' + (f', {d["applied"]}' if d.get('applied') else '')
        status = f'Status: {ver["status_text"] or ver["state"]}'
    elif ver.get('shipment'):
        vline = f'Version: a shipped copy' + (f' ({_version_label(ver["session"])})' if ver.get('session') else '')
        status = 'Status: Withdrawn' if ver['entry'].get('withdrawn') else 'Status: Shipped'
    else:                                                        # K3: never a computed Ready on a superseded file
        vline = f'Version: {_version_label(ver["id"])}, a previous version' + (f', {d["applied"]}' if d.get('applied') else '')
        status = f'Status: previous version (not the current one; the current version is {d["cur_label"]})'
    ships = [ver['entry']] if ver.get('shipment') else d.get('shipments') or []
    n = sum(1 for s in REL.SECTIONS for c in d['rel']['checks'].get(s) or [] if REL.sha_of(c) == sha)
    files = [f'{d["pdf_name"]}: the remediated PDF of this version.'] + [FILE_WORDS[m[0]] for m in d['members'][1:]] + [FILE_WORDS['READ-ME.txt']]
    about = d.get('about') or {}
    src = (about.get('document') or {}).get('file')
    return '\n'.join([d['book'], f'Source PDF: {shown(src) if src else "not recorded"}', '', vline, status] + [x for s in ships for x in REL.shipment_lines(s)]
                      + [f'Accessibility evaluation results recorded on this file: {n}' + (' (in review.html)' if n else ''), '']
                      + about_lines(about) + ['', 'This folder holds:'] + ['- ' + x for x in files]
                      + ['', 'Automated checks are evidence, not legal sign-off.',
                         'The evaluation is a record of what a person found, not a legal certification.', '',
                         f'Downloaded on {D.when(datetime.datetime.now().isoformat(timespec="seconds"))}.', ''])

def stream_zip(w, d):
    """Write the record ZIP to the stream `w` from the open handles in d (prepare()); the PDF is hashed as it streams (the
    read-me counts the evaluation results recorded for that file; it no longer names the hash), and READ-ME.txt comes
    last. Closes every handle."""
    now = datetime.datetime.now().timetuple()[:6]
    h = hashlib.sha256()
    try:
        with zipfile.ZipFile(_Out(w), 'w') as zf:
            for i, (name, fh, kind) in enumerate(d['members']):
                zi = zipfile.ZipInfo(f'{d["folder"]}/{name}', date_time=now); zi.compress_type = kind
                with zf.open(zi, 'w', force_zip64=True) as dst:
                    for b in iter(lambda: fh.read(1 << 20), b''):
                        if i == 0: h.update(b)
                        dst.write(b)
            sha = h.hexdigest()
            zi = zipfile.ZipInfo(f'{d["folder"]}/READ-ME.txt', date_time=now); zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, _readme(d, sha).encode('utf-8'))
    finally:
        for _, fh, _ in d['members']: fh.close()

def note_download(d):
    """#45: after the record ZIP's last byte was written to the response, release/downloads.json gets one line when the ZIP
    is of a live shipment's file (clearing's gate reads it). Appended under the record lock, taken for the write only, so
    two downloads can finish together. "Downloaded" means the app sent every byte; whether the person kept it is not known."""
    from review.ocr import put_json
    R, ver = d.get('R'), d.get('version') or {}
    if not R: return None
    with runlock.record_lock(R, runlock.REQUEST_WAIT):
        rel = REL.load(R)
        live = next((s for s in REL.live_shipments(rel) if REL.sha_of(s) == ver.get('sha')), None)
        if not live: return None
        p = os.path.join(R, 'release', 'downloads.json')
        try: log = REL._json(p, [])
        except (OSError, ValueError): log = []
        e = {'what': 'record', 'version': ver.get('id'), 'sha256': ver.get('sha'), 'shipment': live.get('n'), 'complete': True,
             'at': datetime.datetime.now().isoformat(timespec='seconds')}
        put_json(p, (log if isinstance(log, list) else []) + [e])
        return e
