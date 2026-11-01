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
import os, datetime, subprocess
from lib import release as REL, runlock
from . import sessions as S
from .ocr import put_json, put_text

HERE = S.HERE
PROMOTING = 'A new version was being put in place and did not finish. Whoever looks after the app can finish it.'
MAKING = 'A new version of this book is being made. Check it once it is done.'
CHANGED = 'The PDF changed since this page was opened. Check the new version, then record again.'
NOT_DESCRIBED = 'The remediated PDF on disk is not the one this book\'s report describes, so nothing can be recorded for it.'
NOT_LAST_REVIEW = 'The PDF on disk is not the one this book\'s last review produced, so nothing can be recorded for it.'

def now(): return datetime.datetime.now().isoformat(timespec='seconds')

def code():
    """The git commit this writer runs on (records made by an app started before a `git pull` can be found)."""
    try:
        r = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=HERE, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError): return None

def being_made(R):
    """Why nothing can be recorded now (a new version is being made), or None."""
    p = S.P(R)
    if os.path.exists(p['promoting']): return PROMOTING
    fin = S.newer(R)['finished']                         # newer than the current result: a replaced one never blocks
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

def record(R, section, data, shown_sha=None, via='manual_checks.py', wait=runlock.COMMAND_WAIT, say=print):
    """Check and record one check of the current version. Raises S.Refused (the run, the lock, the file) or
    REL.Invalid (the fields, each tied to its field). Returns the check as recorded."""
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
    except runlock.Busy as e: raise S.Refused(str(e))
    S.rebuild_batch(R, say)                               # after the lock: it reads every book of the batch
    return c

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
