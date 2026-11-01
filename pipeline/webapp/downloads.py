"""webapp/downloads.py: a run's versions and their downloads (issue #38, stage 3): the remediated PDF and the record ZIP of
any version, offered at any time, ready or not, each named by its state (lib/release.py download_names).

    versions(R, rec)          [{id, label, session, dir, pdf, sha, state, marked}] newest first: the current version, then
                              each earlier result whose PDF still exists; `removed`: earlier PDFs taken by "Remove Older
                              PDFs" (review/prune.py), kept for "Which Version Is This File?" only
    prepare(R, run, v, what)  the download, opened in one moment under the record lock: {name, ctype, members | fh}
    stream_zip(out, d)        the record ZIP, written to the response as it is built (never kept on disk)

One moment per download (02 S6, 03 §3.6): under the record lock (5 s at most in a request thread) the record and the
version list are read, the names worked out and every member file opened; the lock is then released and the bytes
stream from the open handles. A promotion moves files by rename, which never touches an open handle, so a ZIP never mixes
two versions. A version id comes only from the run's own list: no path is ever built from the request.

The ZIP holds one folder named as the ZIP; every file keeps its own name (01 rec 3): the PDF (stored, never compressed
again), review.html, review.md, han_review.csv when present, evaluation-results.json (the results recorded on this
file's hash) and READ-ME.txt. Never record.json (it holds the AI's raw reply), digests, crops, reviews/, _intake/,
release/drafts.json, dot-files or working files: the list is an allow-list.
"""
import os, json, hashlib, zipfile, datetime
from lib import release as REL, dates as D, runlock
from review import sessions as S, manual as M
from . import config, manualpage as MP

# a download's own words (review 20 L1): never the Record page's "…so no check can be recorded for it"
CHANGED = 'The book\'s PDF has changed since this report was made, so it can\'t be downloaded as this version. Whoever looks after the app can check it.'
MISSING = 'The book\'s remediated PDF is missing, so it can\'t be downloaded. Whoever looks after the app can check it.'
EARLIER_CHANGED = ('The PDF of this earlier version has changed since it was made, so it can\'t be downloaded as that version. '
                   'Whoever looks after the app can check it.')

class Refused(Exception):
    """A download that cannot be given now, in plain words for the page (409), or None words for a plain 404."""

def _version_label(sid):
    return f'Session {int(sid)}' if str(sid).isdigit() else 'the version applied without a review' if sid == 'ai' else f'version {sid}'

def removed(R): return REL.removed(R)

def versions(R, rec, glance=None):
    """The run's versions, newest first. The current version's state is its status (app_glance: the record's hash first,
    a changed file never Ready); an earlier version's is 'earlier version' (K3). An earlier version is listed only while
    its PDF exists; one whose PDF was removed is in `removed` (for the file check)."""
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
        if not pdf or not os.path.isfile(pdf) or n in gone: continue
        out.append({'id': n, 'session': n if str(n).isdigit() else None, 'dir': d, 'pdf': pdf, 'sha': MP.disk_sha(pdf),
                    'state': 'earlier version', 'status_text': None, 'label': f'{_version_label(n)[0].upper() + _version_label(n)[1:]} (earlier version)'})
    return out

MARKED = {REL.NOT_READY: 'not ready', REL.PENDING: 'not ready', REL.READY: 'not shipped', 'earlier version': 'earlier version'}
def marked_line(state):
    """The line beside the picker: what the downloaded files' names say (no file name on the page)."""
    w = MARKED.get(state)
    return f'The downloaded files are marked "{w}".' if w else 'The downloaded files have the published names.'

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
            if ver['id'] == 'current':
                disk = MP.disk_state(R, rec)
                if disk['missing']: raise Refused(MISSING)
                if disk['same'] is False: raise Refused(CHANGED)
                vrec = rec
            else:                                                        # an earlier version: its PDF against its own record (L4)
                vrec = S.load(os.path.join(ver['dir'], 'record.json')) or {}
                want = (vrec.get('document') or {}).get('output_sha256')
                if want and ver['sha'] != want: raise Refused(EARLIER_CHANGED)
            out = (vrec.get('document') or {}).get('output')
            pdf_name, zip_name = REL.download_names(out, ver['session'], ver['state'], next((s.get('n') for s in REL.live_shipments(REL.load(R)) if REL.sha_of(s) == ver['sha']), None))
            if what == 'pdf':
                return {'name': pdf_name, 'ctype': 'application/pdf', 'fh': open(ver['pdf'], 'rb')}
            members = [(out, open(ver['pdf'], 'rb'), zipfile.ZIP_STORED)]
            for n in ('review.html', 'review.md', 'han_review.csv'):
                p = os.path.join(ver['dir'], n)
                if os.path.isfile(p): members.append((n, open(p, 'rb'), zipfile.ZIP_DEFLATED))
            rel = REL.load(R)
            cur_label = _version_label(S.current_id(rec))
            book = MP.book(rec)['title']
            return {'name': zip_name, 'ctype': 'application/zip', 'members': members, 'folder': zip_name[:-4], 'rel': rel, 'version': ver,
                    'pdf_name': out, 'book': book, 'cur_label': cur_label,
                    'applied': MP.version(R, rec)['when'] if ver['id'] == 'current' else _applied(R, ver['id'], vrec)}
    except runlock.Busy as e: raise Refused(str(e))

def _applied(R, vid, vrec):
    """An earlier version's "applied on …" for its read-me: its session's applied time, else its record's."""
    when = (S.session(R, vid) or {}).get('applied') or vrec.get('written')
    return f'applied on {D.when(when)}' if when else None

class _Out:
    """The response stream for zipfile: write only, no seek or tell (zipfile then writes data descriptors)."""
    def __init__(self, w): self.w = w
    def write(self, b): self.w.write(b); return len(b)
    def flush(self): self.w.flush()

def _readme(d, sha):
    ver = d['version']
    if ver['id'] == 'current':
        vline = f'Version: the current version ({_version_label(ver["session"]) if ver["session"] else "applied without a review"})' + (f', {d["applied"]}' if d.get('applied') else '')
        status = f'Status: {ver["status_text"] or ver["state"]}'
    else:                                                        # K3: never a computed Ready on a superseded file
        vline = f'Version: {_version_label(ver["id"])}, an earlier version' + (f', {d["applied"]}' if d.get('applied') else '')
        status = f'Status: earlier version (not the current one; the current version is {d["cur_label"]})'
    n = sum(1 for s in REL.SECTIONS for c in d['rel']['checks'].get(s) or [] if REL.sha_of(c) == sha)
    return '\n'.join([d['book'], '', vline, status,
                      f'Evaluation results recorded on this file: {n} (evaluation-results.json)', '',
                      'Files: ' + ', '.join(m[0] for m in d['members']) + ', evaluation-results.json, READ-ME.txt',
                      f'sha256 of {d["pdf_name"]}: {sha}',
                      'The sha256 identifies this exact file; the evaluation results in evaluation-results.json are tied to it.', '',
                      'Automated checks are evidence, not legal sign-off.',
                      'The evaluation is a record of what a person found, not a legal certification.', '',
                      f'Downloaded on {D.when(datetime.datetime.now().isoformat(timespec="seconds"))}.', ''])

def stream_zip(w, d):
    """Write the record ZIP to the stream `w` from the open handles in d (prepare()); the PDF is hashed as it streams, and
    evaluation-results.json and READ-ME.txt (which name that hash) come last. Closes every handle."""
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
            ev = {'schema': REL.SCHEMA, 'pdf_sha256': sha,
                  **{s: [c for c in d['rel']['checks'].get(s) or [] if REL.sha_of(c) == sha] for s in REL.SECTIONS}}
            for name, text in (('evaluation-results.json', json.dumps(ev, ensure_ascii=False, indent=1)), ('READ-ME.txt', _readme(d, sha))):
                zi = zipfile.ZipInfo(f'{d["folder"]}/{name}', date_time=now); zi.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(zi, text.encode('utf-8'))
    finally:
        for _, fh, _ in d['members']: fh.close()

def known(R, rec, vs=None):
    """For "Which Version Is This File?": [{sha, words}] of every version this run knows: the listed ones (their files on
    disk) and earlier ones whose PDF was removed (their recorded hash). Data only, never shown."""
    vs = vs if vs is not None else versions(R, rec)
    out = []
    for x in vs:
        if not x['sha']: continue
        if x['id'] == 'current':
            out.append({'sha': x['sha'], 'words': f'This is the current version ({_version_label(x["session"]) if x["session"] else "applied without a review"}): {x["status_text"] or x["state"]}.'})
        else: out.append({'sha': x['sha'], 'words': f'This is an earlier version ({_version_label(x["id"])}), not the current one.'})
    for r in removed(R):
        if r.get('sha256'):
            out.append({'sha': r['sha256'], 'words': f'This is an earlier version ({_version_label(r.get("version"))}), not the current one. Its PDF was removed from this computer to free space.'})
    return out
