"""review/manual.py: the one writer of a run's manual checks (release/checks.json; lib/release.py has the rules), and the
refresh every writer of a finished run's record shares (issue #38). manual_checks.py is its command line; the app's
Manual Checks page (planned) will call the same functions.

    record(R, section, data, shown_sha=None, via=…, wait=…)   check and record one PAC or screen-reader check
    refresh(R, wait=…)                                        recompute the glance and rewrite the Overview, review.html and
                                                              record.json's mirror of release/ (no PDF touched)
    write_run(R, rec)                                         the same, for a caller that already holds the record lock

Every write here runs under the record lock (lib/runlock.py), around the whole read-change-write, and every file is
written whole (a temp file and os.replace). A check is refused while a new version is being made: a session finished
and not yet applied, newer than the current result (sessions.newer(): what Apply applies), reviews/work/ (a re-apply
under way) or reviews/promoting.json (a promotion that did not finish). The PDF on disk is hashed fresh under the lock and must be the one the page showed and the one
record.json describes; a run with no recorded hash (every run made before 2026-11) takes the disk hash at its first
check, after checking it against the current session's own record of its PDF where there is one. If the refresh after
writing a check fails, the check is taken back (release/checks.json as it was) and the error raised.
"""
import os, json, datetime, subprocess
from lib import release as REL, runlock
from . import sessions as S
from .ocr import put_json, put_text

HERE = S.HERE
PROMOTING = 'A new version was being put in place and did not finish. Whoever looks after the app can finish it.'
MAKING = 'A new version of this book is being made. Check it once it is done.'
CHANGED = 'The PDF changed since this page was opened. Check the new version, then record again.'
NOT_DESCRIBED = 'The remediated PDF on disk is not the one this book\'s report describes, so nothing can be recorded for it.'
OUT_OF_STEP = 'This book\'s record is out of step with its review sessions, so nothing can be recorded for it. Whoever looks after the app can check it.'
NOT_LAST_REVIEW = 'The PDF on disk is not the one this book\'s last review produced, so nothing can be recorded for it.'

def now(): return datetime.datetime.now().isoformat(timespec='seconds')

def _head():
    try:
        r = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=HERE, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError): return None
CODE = _head()                                            # read once, when this process loads the code (the app imports this
def code():                                               # module at start): after a `git pull` it still names the code running
    """The git commit this process's code came from: records made by an app started before a `git pull` can be found."""
    return CODE

def ship_words(why):
    """A refusal in Ship's own words (review 22 N1): being_made()'s and the disk checks' texts are written for Record."""
    import re
    m = re.match(r'Session (\d+) is finished and not yet applied', why or '')
    if m: return f'Session {int(m.group(1))} is finished and not yet applied, so this version can\'t be marked as shipped now.'
    return {PROMOTING: 'A new version was being put in place and did not finish, so this version can\'t be marked as shipped now. Whoever looks after the app can finish it.',
            MAKING: 'A new version of this book is being made, so this version can\'t be marked as shipped now.',
            OUT_OF_STEP: 'This book\'s record is out of step with its review sessions, so it can\'t be marked as shipped. Whoever looks after the app can check it.',
            NOT_LAST_REVIEW: 'The PDF on disk is not the one this book\'s last review produced, so it can\'t be marked as shipped.',
            NOT_DESCRIBED: 'The remediated PDF on disk is not the one this book\'s report describes, so it can\'t be marked as shipped.',
            CHANGED: 'The PDF changed since this page was opened. Look at the new version, then mark it as shipped.'}.get(why) or (
           why.replace('so no check can be recorded for it', 'so it can\'t be marked as shipped') if why else why)

def being_made(R):
    """Why nothing can be recorded now (a new version is being made, or the record is out of step with the sessions:
    an applied session newer than the record's own, which no apply leaves behind), or None."""
    p = S.P(R)
    if os.path.exists(p['promoting']): return PROMOTING
    rec = S.load(os.path.join(R, 'record.json')) or {}
    cur = S.sid_n(S.current_id(rec))                     # an applied session newer than the record's own: the record lags
    if any(x and x.get('status') == 'applied' and S.sid_n(x.get('id')) > cur for x in S.sessions(R)): return OUT_OF_STEP
    fin = S.newer(R, rec)['finished']                         # newer than the current result: a replaced one never blocks
    if fin: return (f'Session {int(fin["id"])} is finished and not yet applied: its result will replace this version. '
                    'Check the new version once it is applied.')
    if os.path.isdir(p['work']): return MAKING
    return None

def write_run(R, rec, say=print, text=None):
    """For a caller holding R's record lock: record.json's mirror of release/, the glance recomputed (release/ read now),
    and record.json, review.md (its Overview) and review.html written whole. text: review.md's text already changed by
    the caller (a run made before `sections`); otherwise it is read or drawn from record.json `sections`."""
    from lib import glance as G
    import report_html as H
    assert runlock.holding(R), 'write_run needs the record lock'
    rel = REL.load(R, rec); cur = (rec.get('document') or {}).get('output_sha256')
    rec['manual_checks'], rec['release'] = REL.mirror(rel, cur)
    md = os.path.join(R, 'review.md'); labels = None
    try:
        labels = H.labels_of(R, rec)
        if rec.get('sections_version') == 1: text = G.refresh(rec, labels, H.han_pages(R), release=rel)
        else:
            if text is None: text = open(md, encoding='utf-8').read() if os.path.exists(md) else None
            if text is not None:
                rec['glance'] = G.glance(rec, text, labels, H.han_pages(R), release=rel)
                text = G.replace_block(text, G.glance_md(rec['glance']))
                if REL.any_recorded(rel):                    # the evaluation section, in full once a result is recorded (13 §7.2)
                    text = REL.replace_section_md(text, REL.section_md(rel, cur, (rec.get('document') or {}).get('output') or 'the remediated PDF'))
    except Exception as e:
        say(f'note: "Overview" and review.html not refreshed ({type(e).__name__}: {e})'); labels = None
    put_json(os.path.join(R, 'record.json'), rec)
    if text is not None: put_text(md, text)
    if text is not None and labels is not None:
        try: H.review_html(R, rec, text, labels)
        except Exception as e: say(f'note: review.html not refreshed ({type(e).__name__}: {e})')

def adopt_hash(R, rec, disk):
    """A run whose record has no output_sha256 (made before 2026-11): the disk hash, checked against the current session's
    own record of the PDF it produced (reviews/sessions/NNN.json version.pdf_sha256) where there is one."""
    sid = (rec.get('review') or {}).get('session')
    s = S.session(R, sid) if sid else None
    want = ((s or {}).get('version') or {}).get('pdf_sha256')
    if want and want != disk: raise S.Refused(NOT_LAST_REVIEW)
    rec['document']['output_sha256'] = disk
    rec['document']['output_sha256_from'] = f'first check, {now()[:10]}'

def record(R, section, data, shown_sha=None, via='manual_checks.py', wait=runlock.COMMAND_WAIT, say=print,
           draft_saved_at=None, batch=True):
    """Check and record one check of the current version. Raises S.Refused (the run, the lock, the file) or
    REL.Invalid (the fields, each tied to its field). Returns the check as recorded. Once the refresh has succeeded the
    check stands; the section's draft is then cleared, best effort, leaving a tombstone at `draft_saved_at` (the page's
    last draft time) so an auto-save handled late never brings the recorded answers back. batch=False: the caller
    rebuilds the batch page itself (the app does it after replying)."""
    R = os.path.abspath(R); rj = os.path.join(R, 'record.json')
    if section not in REL.SECTIONS: raise ValueError(f'unknown section {section!r}: pac or screen_reader')
    if not os.path.exists(rj): raise S.Refused('This book has no finished result yet, so there is nothing to check.')
    try:
        with runlock.record_lock(R, wait):
            why = being_made(R)
            if why: raise S.Refused(why)
            rec = S.load(rj); doc = rec.setdefault('document', {})
            out = doc.get('output')
            if not out or not os.path.isfile(os.path.join(R, out)): raise S.Refused('This book\'s remediated PDF is missing.')
            disk = REL.sha_file(os.path.join(R, out))
            if shown_sha and shown_sha != disk: raise S.Refused(CHANGED)
            if not doc.get('output_sha256'): adopt_hash(R, rec, disk)
            elif doc['output_sha256'] != disk: raise S.Refused(NOT_DESCRIBED)
            rel = REL.load(R)
            clean = REL.validate(section, data, {'n_pages': doc.get('pages'), 'found': REL.found(rec),
                                                 'previous': REL.latest(rel, section, disk)})
            xs = rel['checks'][section]
            sid = (rec.get('review') or {}).get('session')
            c = {'id': len(xs) + 1, 'recorded': now(), **clean, 'via': via, 'code': code(),
                 'pdf': {'sha256': disk, 'file': out, 'session': sid if sid else None, 'which': 'current'}}
            cp = REL.paths(R)['checks']
            was = open(cp, encoding='utf-8').read() if os.path.exists(cp) else None
            xs.append(c)
            os.makedirs(REL.paths(R)['dir'], exist_ok=True)
            put_json(cp, rel['checks'])
            try: write_run(R, rec, say)
            except BaseException:                         # the record not written (e.g. an import error): take the check
                if was is None: os.remove(cp)             # back, so a check never stands without the record's hash beside it
                else: put_text(cp, was)
                raise
            try: _clear_draft(R, section, draft_saved_at)  # best effort: a stale draft is harmless, a rolled-back check is not
            except Exception as e: say(f'note: the draft was not cleared ({type(e).__name__}: {e})')
    except runlock.Busy as e: raise S.Refused(str(e))
    if batch: S.rebuild_batch(R, say)                     # after the lock: it reads every book of the batch
    return c

# ------------------------------------------------------------------ drafts (the page's auto-save; they never count)
STALE = 'This check was changed in another tab or window since. Reload the page to see the newest answers.'

def drafts_path(R): return os.path.join(REL.paths(R)['dir'], 'drafts.json')

def load_drafts(R):
    try:
        with open(drafts_path(R), encoding="utf-8") as f: d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (FileNotFoundError, ValueError): return {}

def _clear_draft(R, section, saved_at):
    """Under the record lock: the section's draft replaced by a tombstone; a later auto-save must be newer than it."""
    d = load_drafts(R); cur = d.get(section) or {}
    mark = max(str(saved_at or ''), str(cur.get('saved_at') or ''), str(cur.get('cleared') or ''))
    if not mark and not cur: return
    d[section] = {'cleared': mark}
    put_json(drafts_path(R), d)

def save_draft(R, section, data, saved_at, for_sha, wait=runlock.REQUEST_WAIT):
    """The page's auto-save: release/drafts.json {section: {data, saved_at, for_sha256, by}} written whole under the record
    lock. A saved_at not newer than the stored draft's (or than a recorded check's tombstone) is refused (S.Refused(STALE))
    and nothing is written. The data is cleaned and limited as a check is (REL.Invalid over the limits); nothing is required."""
    R = os.path.abspath(R)
    if section not in REL.SECTIONS: raise ValueError(f'unknown section {section!r}')
    saved_at = str(saved_at or '')
    if not saved_at: raise ValueError('saved_at is missing')
    clean = REL.clean_draft(section, data)
    try:
        with runlock.record_lock(R, wait):
            d = load_drafts(R); cur = d.get(section) or {}
            if saved_at <= max(str(cur.get('saved_at') or ''), str(cur.get('cleared') or '')): raise S.Refused(STALE)
            d[section] = {'data': clean, 'saved_at': saved_at, 'for_sha256': for_sha, 'by': clean.get('by') or None}
            os.makedirs(REL.paths(R)['dir'], exist_ok=True)
            put_json(drafts_path(R), d)
    except runlock.Busy as e: raise S.Refused(str(e))
    return saved_at

def refresh(R, wait=runlock.COMMAND_WAIT, say=print):
    """Recompute a finished run's glance (release/ read now) and rewrite its Overview, review.html and record.json; the
    PDF and every other line of review.md are left as they are. Refused while a promotion is unfinished."""
    R = os.path.abspath(R); rj = os.path.join(R, 'record.json')
    if not os.path.exists(rj): raise S.Refused('This book has no finished result yet.')
    try:
        with runlock.record_lock(R, wait):
            if os.path.exists(S.P(R)['promoting']): raise S.Refused(PROMOTING)
            rec = S.load(rj)
            write_run(R, rec, say)
    except runlock.Busy as e: raise S.Refused(str(e))
    S.rebuild_batch(R, say)
    return rec

# ------------------------------------------------------------------ Mark as Shipped and withdrawal (stage 4)
SHIPPED_BANNER = '<p class="replaced" role="note">Shipped copy (Shipment {n}, {day}). It is kept as it was shipped; the live dashboard is the run\'s own page.</p>'

def _next_number(sd, entries):
    """The next shipment number: one past the highest in shipped.json and among the numbered folders. Never reused (M2)."""
    folders = [int(e.name) for e in os.scandir(sd) if e.is_dir() and e.name.isdigit()] if os.path.isdir(sd) else []
    return max([int(x.get('n') or 0) for x in entries] + folders + [0]) + 1

def _copy_hashing(src, dst):
    import hashlib
    h = hashlib.sha256()
    with open(src, 'rb') as f, open(dst, 'wb') as g:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b); g.write(b)
    return h.hexdigest()

def _fill_shipped(T, R, entry, say=print):
    """The shipped folder's files written after write_run(), so they say Shipped: review.md, review.html (with its "Shipped
    copy" banner, N9), record.json (the local archive only: never served, never zipped; S6, N2), evaluation-results.json,
    the accessibility statement (accessibility-statement.html and .md) and READ-ME.txt, in plain words, with the shipment's
    lines (lib/release.py shipment_lines)."""
    import shutil
    import report_html as H
    from lib import disclosure as DS, dates as D
    rec = S.load(os.path.join(R, 'record.json'))
    sha = entry['pdf']['sha256']
    if os.path.isfile(os.path.join(R, 'review.md')): shutil.copy2(os.path.join(R, 'review.md'), os.path.join(T, 'review.md'))
    if os.path.isfile(os.path.join(R, 'review.html')):
        page = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
        mark = '<main id="main" tabindex="-1">'
        page = page.replace(mark, mark + SHIPPED_BANNER.format(n=entry['n'], day=D.day(entry['shipped'])), 1)
        put_text(os.path.join(T, 'review.html'), page)
    shutil.copy2(os.path.join(R, 'record.json'), os.path.join(T, 'record.json'))
    rel = REL.load(R, rec)
    put_json(os.path.join(T, 'evaluation-results.json'),
             {'schema': REL.SCHEMA, 'pdf_sha256': sha, **{s: [c for c in rel['checks'].get(s) or [] if REL.sha_of(c) == sha] for s in REL.SECTIONS}})
    g = H.glance_of(R, rec)
    doc = (rec.get('verify') or {}).get('doc') or {}
    title = (doc.get('title') or doc.get('xmp_title') or '').strip() or ((rec.get('document') or {}).get('file') or 'this book').removesuffix('.pdf')
    blocks = DS.facts(rec, rel, entry, g)
    put_text(os.path.join(T, REL.STATEMENT_MD), DS.to_md(blocks, title))
    put_text(os.path.join(T, REL.STATEMENT_HTML), DS.to_html(blocks, title))
    pdf = entry['pdf']['file']
    files = [f'{pdf}: the remediated PDF as shipped.',
             'review.html: the report on this version as shipped (what was changed, what was checked, and the accessibility '
             'evaluation\'s results). Open it in a web browser. review.md is the same report as text.']
    if os.path.isfile(os.path.join(T, 'han_review.csv')): files.append('han_review.csv: the Han-only text runs listed for a person who reads the language.')
    files += [f'{REL.STATEMENT_HTML}: the accessibility statement. Open it in a web browser. {REL.STATEMENT_MD} is the same statement as text.',
              'evaluation-results.json: the accessibility evaluation\'s results recorded on this file, for the archive.',
              'record.json: the run\'s full record, kept here for the archive.', 'READ-ME.txt: this file.']
    put_text(os.path.join(T, 'READ-ME.txt'), '\n'.join(
        [title, ''] + REL.shipment_lines(entry) + [f'Status: {(g.get("status") or {}).get("text") or REL.SHIPPED}', '', 'This folder holds:']
        + ['- ' + x for x in files]
        + ['', f'The fingerprint of {pdf}, which identifies this exact file (sha256): {sha}', '',
           'Automated checks are evidence, not legal sign-off.', 'The evaluation is a record of what a person found, not a legal certification.', '']))

def ship(R, by, where=None, note=None, shown_sha=None, via='manual_checks.py', wait=runlock.COMMAND_WAIT, say=print, batch=True):
    """Mark the current version as shipped (21 §A, review 22 M1, M2). Everything under the record lock:
    being_made() (in Ship's words); the PDF hashed fresh, equal to what the page showed and to the record (F1's adopt rule
    when the record has none); then the gate, worked out here from the full glance (report_html.glance_of, then
    webapp.manualpage.app_glance and ship_gate: current Ready, the file unchanged, no live shipment of this hash). It never
    reads runs.ready(), which is for display (its review.md path carries no current status).
    The copy: the PDF (hashed while copied) and han_review.csv into release/shipped/NNN.tmp; shipped.json appended
    (`shipped` as local isoformat with seconds, note (a)); write_run(); the Shipped review.md, review.html, record.json,
    evaluation results and the statement written into NNN.tmp; then the rename to NNN, the last step. Any failure before
    or at the rename: NNN.tmp removed, shipped.json restored, and write_run() run again so no page says Shipped.
    Returns the shipment."""
    import shutil
    from review.core import clean_text
    import report_html as H
    from webapp import manualpage as MP
    R = os.path.abspath(R); rj = os.path.join(R, 'record.json')
    by = clean_text(by or '', one_line=True)[:REL.NAME_MAX]
    where = clean_text(where or '', one_line=True)[:REL.FIELD_MAX] or None
    note = clean_text(note or '', one_line=True)[:REL.NOTE_MAX] or None
    if not by: raise S.Refused('Enter your name in "Shipped By".')
    if not os.path.exists(rj): raise S.Refused('This book has no finished result yet, so there is nothing to ship.')
    try:
        with runlock.record_lock(R, wait):
            why = being_made(R)
            if why: raise S.Refused(ship_words(why))
            rec = S.load(rj); doc = rec.setdefault('document', {})
            out = doc.get('output')
            if not out or not os.path.isfile(os.path.join(R, out)): raise S.Refused('This book\'s remediated PDF is missing, so it can\'t be marked as shipped.')
            disk = REL.sha_file(os.path.join(R, out))
            if shown_sha and shown_sha != disk: raise S.Refused(ship_words(CHANGED))
            if not doc.get('output_sha256'): adopt_hash(R, rec, disk)
            elif doc['output_sha256'] != disk: raise S.Refused(ship_words(NOT_DESCRIBED))
            rel = REL.load(R, rec)
            g = MP.app_glance(R, rec, H.glance_of(R, rec), rel)
            gate = MP.ship_gate(R, rec, g, rel)
            if not gate['ok']: raise S.Refused(gate['why'])
            sd = os.path.join(R, 'release', 'shipped'); os.makedirs(sd, exist_ok=True)
            for e in os.scandir(sd):                                  # a leftover from a stop in the middle
                if e.name.endswith('.tmp'): shutil.rmtree(e.path, ignore_errors=True)
            n = _next_number(sd, rel['shipped'])
            final, T = os.path.join(sd, f'{n:03d}'), os.path.join(sd, f'{n:03d}.tmp')
            if os.path.exists(final): raise S.Refused(f'Shipment {n} already has a folder. Whoever looks after the app can check it.')
            os.makedirs(T)
            sp = REL.paths(R)['shipped']; was = open(sp, encoding='utf-8').read() if os.path.exists(sp) else None
            try:
                got = _copy_hashing(os.path.join(R, out), os.path.join(T, out))
                if got != disk: raise S.Refused(ship_words(CHANGED))
                if os.path.isfile(os.path.join(R, 'han_review.csv')): shutil.copy2(os.path.join(R, 'han_review.csv'), os.path.join(T, 'han_review.csv'))
                sid = S.current_id(rec)                               # a run reviewed before sessions were kept is 001, as the dialog says
                sid = sid if str(sid).isdigit() else None
                pac, sr = (REL.latest(rel, s, disk) for s in ('pac', 'screen_reader'))
                entry = {'n': n, 'shipped': now(), 'by': by, **({'where': where} if where else {}), **({'note': note} if note else {}),
                         'pdf': {'sha256': disk, 'file': out, 'session': sid if sid else None}, 'folder': f'shipped/{n:03d}', 'via': via, 'code': code(),
                         'issues': REL.evaluation(rel, disk)['issues'], 'checks': {'pac': (pac or {}).get('id'), 'screen_reader': (sr or {}).get('id')}}
                put_json(sp, (rel['shipped'] or []) + [entry])
                write_run(R, rec, say)
                _fill_shipped(T, R, entry, say)
                os.rename(T, final)                                   # whole or not at all: the last step under the lock
            except BaseException:
                shutil.rmtree(T, ignore_errors=True)
                if was is None:
                    try: os.remove(sp)
                    except FileNotFoundError: pass
                else: put_text(sp, was)
                try: write_run(R, S.load(rj), say)                    # so no page says Shipped (M2)
                except Exception as e: say(f'note: after a failed shipment the pages were not redrawn ({type(e).__name__}: {e}); the next refresh redraws them')
                raise
    except runlock.Busy as e: raise S.Refused(str(e))
    if batch: S.rebuild_batch(R, say)
    return entry

def withdraw(R, n, by, reason, wait=runlock.COMMAND_WAIT, say=print):
    """Mark shipment n withdrawn (command line only; 01 rec 11, review 22 N4): `withdrawn: {by, date (local isoformat with
    seconds), reason}`; nothing is deleted. Refused for an unknown or already withdrawn n, or without a name and a reason."""
    from review.core import clean_text
    R = os.path.abspath(R)
    by = clean_text(by or '', one_line=True)[:REL.NAME_MAX]; reason = clean_text(reason or '', one_line=True)[:REL.NOTE_MAX]
    if not by or not reason: raise S.Refused('A withdrawal needs a name (--by) and a reason (--reason).')
    try:
        with runlock.record_lock(R, wait):
            rel = REL.load(R); xs = rel['shipped'] or []
            s = next((x for x in xs if str(x.get('n')) == str(n)), None)
            if s is None: raise S.Refused(f'There is no Shipment {n}.')
            if s.get('withdrawn'): raise S.Refused(f'Shipment {n} is already withdrawn.')
            s['withdrawn'] = {'by': by, 'date': now(), 'reason': reason}
            put_json(REL.paths(R)['shipped'], xs)
            write_run(R, S.load(os.path.join(R, 'record.json')), say)
    except runlock.Busy as e: raise S.Refused(str(e))
    S.rebuild_batch(R, say)
    return s
