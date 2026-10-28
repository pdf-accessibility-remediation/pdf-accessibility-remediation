"""review/sessions.py: the review loop's records, with no web server and no HTML (review_workorder.py is its command line).

A finished run keeps its current result at the top of its folder (record.json, review.md, review.html, the PDF). What a
later review needs is kept beside it, in reviews/:

    reviews/basis.json            what every session is checked against: the run id (the review page's browser-draft key),
                                  the pipeline input (path, sha256), the digest's fingerprint (decide.py's run.digest_sha256),
                                  the AI's validated work order's sha256, decided_by
    reviews/_audit/               digest.json, fulltext.json (when the audit that pinned it reproduced the digest), ocr_words/ (books with OCR words);
                                  never the figure crops: they are re-rendered from the input PDF when a review opens
    reviews/workorder.ai.json     the AI's validated work order (written when a review opens; reviewed runs keep it)
    reviews/sessions/NNN.json     one per review: who, when, from which session, every choice (status, value, note, the AI
                                  value it was judged against, the session that set it), what changed since its start,
                                  the review (as review.json had it), the OCR verdict at finish, the version it produced
    reviews/sessions/NNN.workorder.json   the reviewed order that session produced (what apply.py was given)
    reviews/versions/<id>/        an earlier result, moved here when a later one replaced it (<id>: its session, or "ai"
                                  for the result applied without review); its record.json, review.md and PDF are never edited
    reviews/.lock                 while a review is open or being applied (one at a time per run)

The basis check refuses, never re-matches: the input file's sha256, the kept digest's fingerprint and the AI order's
sha256 must all be the ones the run was made with (handoff/fix-ocr-word-replay: ids are only meaningful against the list
they were written for). A choice is carried into a new session only onto the item with the same id and the same AI value.
"""
import os, re, sys, copy, json, uuid, shutil, hashlib, datetime, subprocess, tempfile, time
from . import core

HERE = core.HERE                                           # pipeline/
SINCE = '2026-10-27'                                       # per-decision choices are recorded from this date (branch review-loop)
OUT_FILES = ('record.json', 'review.md', 'review.html', 'han_review.csv')   # a version: these and the remediated PDF

def now(): return datetime.datetime.now().isoformat(timespec='seconds')
def say_(*a): print(*a, flush=True)
def load(p, default=None): return core.load(p, default)
def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True); core.save(p, obj)
def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
def norm(x): return json.loads(json.dumps(x, ensure_ascii=False))
def sid_n(sid): return int(sid) if str(sid).isdigit() else 0
def label(sid): return f'session {int(sid)}' if str(sid).isdigit() else 'the result applied without review' if sid == 'ai' else str(sid)
def from_label(src): return 'the AI\'s decisions' if src in ('ai', None) else 'the recorded summary of an earlier review' if src == 'summary' else label(src)

def P(R):
    """The paths in a run folder's reviews/."""
    b = os.path.join(R, 'reviews')
    return {'dir': b, 'basis': os.path.join(b, 'basis.json'), 'audit': os.path.join(b, '_audit'), 'ai': os.path.join(b, 'workorder.ai.json'),
            'sessions': os.path.join(b, 'sessions'), 'versions': os.path.join(b, 'versions'), 'lock': os.path.join(b, '.lock'),
            'work': os.path.join(b, 'work'), 'promoting': os.path.join(b, 'promoting.json'),
            'items': os.path.join(b, 'review_items.json'), 'draft': os.path.join(b, 'review_decisions.json')}

class Refused(Exception):
    """A check failed: nothing was written."""

# what to do when a run can no longer be reviewed (its audit is not today's): a new run of the book from its saved reply
FALLBACK = ('this run cannot be reviewed again. A new run of the book on today\'s code can be (it is not a review of this '
            'result): python3 review_workorder.py <this run> --replay-to <new run folder> copies its _intake/ and saved reply, '
            'then run the command it prints (INTAKE_REUSE=1 REPLY=… REVIEW=1, no API call)')

def readable(fn, *a):
    """fn(*a) on the kept digest; a digest this version of the review step cannot read is refused, not a traceback."""
    try: return fn(*a)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as e:
        raise Refused(f'the kept digest cannot be read by this version of the review step ({type(e).__name__}: {e}): {FALLBACK}')

# ------------------------------------------------------------------ the basis
def ai_order(rec):
    """The AI's validated work order of a finished run, from its record; None when it cannot be recovered."""
    if rec.get('workorder_ai') is not None: return rec['workorder_ai']
    rv = (rec.get('review') or {}).get('workorder')
    if rv and rv.get('changes'): return None              # changed in review, and the AI's version was not kept
    wo = copy.deepcopy(rec.get('workorder') or {}); wo.pop('reviewed_by', None)
    return wo

def input_of(R, rec, pdf=None):
    """The file the pipeline worked on: _intake/intake.pdf when intake made one, else the original (pdf). Its sha256 must be
    the one the work order was written for."""
    want = ((rec.get('workorder') or {}).get('source') or {}).get('sha256')
    intake = rec.get('intake') or {}
    if (intake.get('result') or {}).get('pdf'):
        p = os.path.join(R, '_intake', 'intake.pdf')
        if not os.path.isfile(p): raise Refused(f'{p} is missing: the intake result this run worked on')
    else:
        if not pdf: raise Refused('this book had no intake result: give --pdf <the original PDF> (its sha256 is checked against the record)')
        p = os.path.abspath(pdf)
        if not os.path.isfile(p): raise Refused(f'no such PDF: {p}')
    got = sha_file(p)
    if want and got != want:
        raise Refused(f'{p} is not the file this run worked on (sha256 {got[:16]}, the work order names {want[:16]})')
    return p, got

def basis(R): return load(P(R)['basis'])

def new_basis(R, inp, inp_sha, digest_path, ai, made_by):
    d = sha_file(digest_path)
    return {'schema': 'reviews/1', 'run_id': uuid.uuid4().hex[:12], 'made': now(), 'made_by': made_by,
            'input': {'path': inp, 'sha256': inp_sha}, 'digest_sha256': d[:16], 'digest_file_sha256': d,
            'workorder_ai_sha256': sha_obj(ai) if ai is not None else None, 'decided_by': (ai or {}).get('decided_by')}

def audit_env():
    """audit.py's environment: veraPDF (its failed rules are part of the digest) and Java."""
    env = dict(os.environ)
    java = '/opt/homebrew/opt/openjdk@21/bin'
    if os.path.isdir(java) and java not in env.get('PATH', ''): env['PATH'] = java + os.pathsep + env.get('PATH', '')
    return env

def reaudit(inp, out):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'audit.py'), inp, out], cwd=HERE, env=audit_env(),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0 or not os.path.exists(os.path.join(out, 'digest.json')):
        raise Refused(f'the re-audit failed (exit {r.returncode}): ' + (r.stdout or '').strip()[-400:])

def top_up(R, pdf=None, say=say_):
    """A run pinned before --pin kept fulltext.json: add it, only when today's audit reproduces the kept digest byte for
    byte. Writes only reviews/_audit/fulltext.json. Returns what happened, as a sentence."""
    p = P(R); b = basis(R); ft = os.path.join(p['audit'], 'fulltext.json')
    if os.path.exists(ft): return 'already pinned'
    inp = (b.get('input') or {}).get('path')
    if pdf or not inp or not os.path.isfile(inp) or sha_file(inp) != (b.get('input') or {}).get('sha256'):
        inp = input_of(R, load(os.path.join(R, 'record.json')) or {}, pdf)[0]
    tmp = tempfile.mkdtemp(prefix='pin-')
    try:
        say(f'  already pinned, without fulltext.json: re-auditing {os.path.relpath(inp, R) if inp.startswith(R) else inp} (no model)…')
        reaudit(inp, tmp)
        if sha_file(os.path.join(tmp, 'digest.json')) != sha_file(os.path.join(p['audit'], 'digest.json')):
            return 'already pinned; fulltext.json not kept: today\'s audit does not reproduce the kept digest'
        if not os.path.exists(os.path.join(tmp, 'fulltext.json')): return 'already pinned; the audit wrote no fulltext.json'
        shutil.copy2(os.path.join(tmp, 'fulltext.json'), ft)
        return 'already pinned; fulltext.json added'
    finally: shutil.rmtree(tmp, ignore_errors=True)

def pin(R, pdf=None, say=say_):
    """Re-audit a finished run's input, check the digest's fingerprint against the record, and keep the digest, fulltext.json
    (the whole texts review.md quotes) and the OCR word sheets with a basis record. Writes only reviews/basis.json and
    reviews/_audit/{digest.json, fulltext.json, ocr_words/}; never touches record.json, review.md, review.html or the PDF.
    A run already pinned without fulltext.json gets it added (top_up). Returns what happened; raises Refused."""
    R = os.path.abspath(R); p = P(R)
    if os.path.exists(p['basis']) and os.path.exists(os.path.join(p['audit'], 'digest.json')): return top_up(R, pdf, say)
    old = basis(R)                                         # a basis with no digest (a KEEP=1 review run): keep its run id
    rec = load(os.path.join(R, 'record.json'))
    if rec is None: raise Refused(f'{R} is not a finished run (no record.json)')
    want = (rec.get('run') or {}).get('digest_sha256')
    if not want: raise Refused('the record has no digest fingerprint (run.digest_sha256): the audit the AI decided on cannot be checked')
    ai = ai_order(rec)
    if ai is None: raise Refused('the record keeps no copy of the AI\'s work order (reviewed with changes, no workorder_ai)')
    inp, inp_sha = input_of(R, rec, pdf)
    tmp = tempfile.mkdtemp(prefix='pin-')
    try:
        say(f'  re-auditing {os.path.relpath(inp, R) if inp.startswith(R) else inp} (no model)…')
        reaudit(inp, tmp)
        got = sha_file(os.path.join(tmp, 'digest.json'))[:16]
        if got != want:
            raise Refused(f'the audit changed since the AI decided: digest {got}, the record says {want} (audit code, veraPDF or '
                          f'Python); nothing was kept, so {FALLBACK}')
        os.makedirs(p['audit'], exist_ok=True)
        shutil.copy2(os.path.join(tmp, 'digest.json'), os.path.join(p['audit'], 'digest.json'))
        if os.path.exists(os.path.join(tmp, 'fulltext.json')): shutil.copy2(os.path.join(tmp, 'fulltext.json'), os.path.join(p['audit'], 'fulltext.json'))
        if os.path.isdir(os.path.join(tmp, 'ocr_words')): shutil.copytree(os.path.join(tmp, 'ocr_words'), os.path.join(p['audit'], 'ocr_words'))
        b = new_basis(R, inp, inp_sha, os.path.join(p['audit'], 'digest.json'), ai, 'pin')
        if old and old.get('run_id'): b['run_id'] = old['run_id']
        save(p['basis'], b)
        return 'pinned'
    finally: shutil.rmtree(tmp, ignore_errors=True)

def replay_to(R, D):
    """The fallback for a run that can no longer be reviewed: what a new run of the same book needs to reuse this run's
    intake result and saved reply (no API call), as batch_api.sh FROM= does. Writes D/_intake/ (intake.json, intake.pdf),
    and beside D the reply (<D>.reply.txt) and its meta (model, temperature, the OCR-word list it was written for).
    Without the intake copy, run_api.sh would redo OCR and auto-tagging and the reply's ids could name other elements.
    The new run is on today's code: it is not a review of R's result. Returns (reply path, the command to run)."""
    R, D = os.path.abspath(R), os.path.abspath(D)
    rec = load(os.path.join(R, 'record.json'))
    if not rec or not rec.get('raw_reply'): raise Refused(f'{R} has no record.json with a saved reply (raw_reply)')
    if os.path.exists(D) and os.listdir(D): raise Refused(f'{D} is not empty: give a new run folder')
    reply = D.rstrip(os.sep) + '.reply.txt'
    if os.path.exists(reply): raise Refused(f'{reply} exists already')
    from lib import ocrwords
    os.makedirs(D, exist_ok=True)
    old_in = os.path.join(R, '_intake')
    if os.path.exists(os.path.join(old_in, 'intake.json')):
        os.makedirs(os.path.join(D, '_intake'))
        for f in ('intake.json', 'intake.pdf'):
            if os.path.exists(os.path.join(old_in, f)): shutil.copyfile(os.path.join(old_in, f), os.path.join(D, '_intake', f))
    open(reply, 'w', encoding='utf-8').write(rec['raw_reply'])
    run = rec.get('run') or {}
    json.dump({**{k: run[k] for k in ('model', 'temperature') if k in run}, **ocrwords.carried(run)},
              open(reply + '.meta.json', 'w'))
    doc = rec.get('document') or {}
    cmd = (f'INTAKE_REUSE=1 REPLY={reply} REVIEW=1 RUN_DIR={D} bash run_api.sh <the original PDF: {doc.get("file")}, '
           f'sha256 {str(doc.get("sha256"))[:16]}…> <name> {os.path.basename(D)}')
    return reply, cmd

def keep_audit(R, A, ai, inp=None, made_by='report'):
    """report.py's tidy: keep the digest, fulltext.json and the OCR word sheets in reviews/_audit (not the crops), and write
    the basis when there is none yet. inp: the pipeline input's path (run_api.sh passes it; else _intake/intake.pdf)."""
    p = P(R); os.makedirs(p['audit'], exist_ok=True)
    for n in ('digest.json', 'fulltext.json'):
        if os.path.exists(os.path.join(A, n)): shutil.copy2(os.path.join(A, n), os.path.join(p['audit'], n))
    if os.path.isdir(os.path.join(A, 'ocr_words')):
        shutil.rmtree(os.path.join(p['audit'], 'ocr_words'), ignore_errors=True)
        shutil.copytree(os.path.join(A, 'ocr_words'), os.path.join(p['audit'], 'ocr_words'))
    b = basis(R)
    if b is None:
        digest = load(os.path.join(A, 'digest.json')) or {}
        inp = os.path.abspath(inp) if inp else os.path.join(R, '_intake', 'intake.pdf')
        if not os.path.isfile(inp) or sha_file(inp) != (digest.get('source') or {}).get('sha256'): inp = None   # path not known: --pdf when reopened
        b = new_basis(R, inp, (digest.get('source') or {}).get('sha256'), os.path.join(p['audit'], 'digest.json'), ai, made_by)
        save(p['basis'], b)
    return b

def first_basis(R, inp):
    """The first review (REVIEW=1, then --serve): the basis is written when run_api.sh stops for review, so the page's
    browser draft has the run id from the start. The audit is still in R/_audit; report.py moves it later."""
    b = basis(R)
    if b: return b
    ai = load(os.path.join(R, 'workorder.ai.json'))
    b = new_basis(R, os.path.abspath(inp), sha_file(inp), os.path.join(R, '_audit', 'digest.json'), ai, 'review')
    save(P(R)['basis'], b)
    return b

def check_basis(R, rec, pdf=None):
    """Every reopen and re-apply: the input, the kept digest and the AI order must be the ones the run was made with.
    Returns (basis, input path, the AI order). Raises Refused, naming what differs."""
    p = P(R); b = basis(R)
    if b is None: raise Refused('no reviews/basis.json')
    dg = os.path.join(p['audit'], 'digest.json')
    if not os.path.exists(dg): raise Refused('reviews/_audit/digest.json is missing')
    if sha_file(dg)[:16] != b['digest_sha256'] or ((rec.get('run') or {}).get('digest_sha256') not in (None, b['digest_sha256'])):
        raise Refused(f'the kept digest is not the one the AI decided on ({sha_file(dg)[:16]}; basis {b["digest_sha256"]}, '
                      f'record {(rec.get("run") or {}).get("digest_sha256")}): {FALLBACK}')
    want = {(b.get('input') or {}).get('sha256'), ((rec.get('workorder') or {}).get('source') or {}).get('sha256')} - {None}
    own = os.path.join(R, '_intake', 'intake.pdf')        # the run's own intake result first: a run folder can be moved
    inp = os.path.abspath(pdf) if pdf else own if os.path.isfile(own) and sha_file(own) in want else (b.get('input') or {}).get('path')
    if not inp or not os.path.isfile(inp):
        raise Refused('the input PDF is not where the basis says' + (f' ({inp})' if inp else '') + ': give --pdf <the original PDF>')
    got = sha_file(inp)
    if got not in want: raise Refused(f'{inp} is not the file this run worked on (sha256 {got[:16]})')
    if b.get('input', {}).get('path') != inp or not b.get('input', {}).get('sha256'):
        b['input'] = {'path': inp, 'sha256': got}; save(p['basis'], b)
    ai = load(p['ai']) if os.path.exists(p['ai']) else ai_order(rec)
    if ai is None: raise Refused('the AI\'s work order cannot be recovered from the record')
    if b.get('workorder_ai_sha256') and sha_obj(ai) != b['workorder_ai_sha256']:
        raise Refused('the AI\'s work order is not the one the basis recorded: nothing was changed')
    if not os.path.exists(p['ai']): save(p['ai'], ai)
    return b, inp, ai

# ------------------------------------------------------------------ sessions
def sessions(R):
    d = P(R)['sessions']
    if not os.path.isdir(d): return []
    return [load(os.path.join(d, n)) for n in sorted(os.listdir(d)) if re.fullmatch(r'\d{3}\.json', n)]

def session(R, sid): return load(os.path.join(P(R)['sessions'], f'{sid}.json'))
def save_session(R, s): save(os.path.join(P(R)['sessions'], f'{s["id"]}.json'), s)
def next_id(R): return f'{max([sid_n(s["id"]) for s in sessions(R)] + [0]) + 1:03d}'

def current_id(rec):
    """Which session produced a record: review.session; a run reviewed before sessions were kept: 001; else 'ai'."""
    rv = rec.get('review') or {}
    if rv.get('session'): return rv['session']
    return '001' if rv.get('workorder') else 'ai'

def decision_list(items, decisions):
    """record.json review.decisions: one row per item, for review.html's per-decision status."""
    out = []
    for it in items:
        d = decisions.get(it['id']) or {}
        st = core._status(it, d) if d.get('status') else 'accepted_unreviewed'
        lab = it['label'] if isinstance(it['label'], str) else json.dumps(it['label'], ensure_ascii=False)
        out.append({'id': it['id'], 'kind': it['kind'], 'label': lab[:90] + ('…' if len(lab) > 90 else ''), 'page': it['page'],
                    'page_label': it.get('page_label'), 'status': st, **({'set_in': d['set_in']} if d.get('set_in') else {}),
                    **({'inferred': True} if d.get('inferred') else {}), **({'note': d['note']} if d.get('note') else {})})
    return out

def summary_row(s):
    """One line of the session table (record.json review.sessions)."""
    rv = s.get('review') or {}
    return {'id': s['id'], 'from': s.get('from'), 'status': s.get('status'), 'reviewer': s.get('reviewer') or rv.get('reviewer'),
            'date': rv.get('date'), 'started': s.get('started'), 'finished': s.get('finished'), 'applied': s.get('applied'),
            'method': s.get('method') or rv.get('method'), 'summary_only': bool(s.get('summary_only')), 'inferred': bool(s.get('inferred')),
            'counts': rv.get('counts'), 'changes': len(rv.get('changes') or []), 'since_start': len(s.get('since_start') or []),
            'carried': s.get('carried'), 'not_carried': len(s.get('not_carried') or []), 'version': (s.get('version') or {}).get('id')}

def summary_text(s):
    """'Session 1 (summary only): 159 approved, 8 seen, no changes; per-decision choices weren't recorded before …'"""
    rv = s.get('review') or {}; c = rv.get('counts') or {}
    parts = [f'{v} {k.replace("_", " ")}' for k, v in c.items() if v] + [(lambda n: f'{n} change{"s" if n != 1 else ""} from the AI')(len(rv['changes'])) if rv.get('changes') else 'no changes']
    return (f'Session {int(s["id"])} (summary only): ' + ', '.join(parts) +
            f'; per-decision choices were not recorded before {SINCE}' + ('' if not s.get('inferred') else ' (rebuilt from the recorded changes and counts, marked inferred)'))

# ------------------------------------------------------------------ a review made before sessions were kept
def _walk(wo, loc):
    x = wo
    for k in loc:
        if isinstance(x, list): x = x[k] if isinstance(k, int) and k < len(x) else None
        elif isinstance(x, dict): x = x.get(k)
        else: return None
    return x

MISSING = object()

def _find_final(ai, final, loc):
    """The final order's entry for the AI's entry at loc (list entries are matched by identity, as core.diff does)."""
    parent_ai, parent_f = _walk(ai, loc[:-1]), _walk(final, loc[:-1])
    if isinstance(parent_ai, list):
        entry = parent_ai[loc[-1]]
        if not isinstance(parent_f, list): return MISSING
        i = core._ident(entry); ia, ib = [core._ident(x) for x in parent_ai], [core._ident(x) for x in parent_f]
        if ia.count(i) == 1 and ib.count(i) <= 1: return parent_f[ib.index(i)] if i in ib else MISSING
        return entry if entry in parent_f else MISSING       # no usable identity: a whole-item match only
    if isinstance(parent_ai, dict):
        if not isinstance(parent_f, dict) or loc[-1] not in parent_f: return MISSING
        return parent_f[loc[-1]]
    return MISSING

ADD_FROM = {'retype': ('obj', 'type'), 'alt': ('obj', 'alt'), 'page_figures': ('page', 'alt'), 'ocr_words': ('id', 'reads')}

def from_summary(ai, final, rv, digest):
    """A review made before sessions were kept: rebuild per-card choices from the final order, then keep them only if the
    rebuilt order gives exactly the recorded changes and counts. Returns (decisions, additions) or None (summary only)."""
    c = rv.get('counts')
    if rv.get('method') != 'page' or not c or c.get('accepted_unreviewed'): return None
    items = core.build_items(ai, digest); adds = core.addable(ai, digest)
    final = copy.deepcopy(final); final.pop('reviewed_by', None)
    decisions = {}
    for it in items:
        if it['key'] in core.SEEN_ONLY: decisions[it['id']] = {'status': 'seen'}; continue
        f = _find_final(ai, final, it['loc'])
        e = _walk(ai, it['loc'])
        if f is MISSING: decisions[it['id']] = {'status': 'rejected'}; continue
        if norm(f) == norm(e): decisions[it['id']] = {'status': 'approved'}; continue
        if not it['edit']: return None
        if it['edit'] == 'table': v = {k: (f or {}).get(k) for k in ('header_rows', 'header_cols')}
        elif it['field']: v = (f or {}).get(it['field']) if isinstance(f, dict) else None
        else: v = f
        decisions[it['id']] = {'status': 'changed', 'value': v}
    additions = []
    for k, (tk, vk) in ADD_FROM.items():
        mine = {core._ident(x) for x in ai.get(k) or []}
        for x in final.get(k) or []:
            if isinstance(x, dict) and core._ident(x) not in mine: additions.append({'kind': k, 'target': x.get(tk), 'value': x.get(vk)})
    mine = {core._ident(x) for x in ai.get('tables') or []}
    additions += [{'kind': 'tables', 'target': x.get('obj'), 'value': {'header_rows': x.get('header_rows'), 'header_cols': x.get('header_cols')}}
                  for x in final.get('tables') or [] if isinstance(x, dict) and core._ident(x) not in mine]
    for k in ('rolemap', 'document'):
        additions += [{'kind': k, 'target': t, 'value': v} for t, v in (final.get(k) or {}).items() if t not in (ai.get(k) or {})]
    for n in (rv.get('notes') or {}):
        if n in decisions: decisions[n]['note'] = rv['notes'][n]
    for a in additions:
        n = (rv.get('notes') or {}).get(f'add:{a["kind"]}:{a["target"]}')
        if n: a['note'] = n
    # the proof: the same changes and counts as recorded
    wo = core.apply_decisions(ai, items, decisions)
    if core.add_entries(wo, additions, adds, rv.get('reviewer') or ''): return None
    from lib import workorder_check
    workorder_check.check(wo, digest, set(), {w['id'] for w in digest.get('ocr_words') or []})
    if norm(core.diff(ai, wo)) != norm(rv.get('changes') or []): return None
    st = [core._status(it, decisions.get(it['id'])) for it in items]
    counts = {s: st.count(s) for s in ('approved', 'changed', 'rejected', 'seen', 'accepted_unreviewed')}
    if additions: counts['added'] = len(additions)
    if counts != c: return None
    return decisions, additions

def adopt_summary(R, rec, ai, digest):
    """Session 001 for a run reviewed before sessions were kept: its recorded review, with per-card choices when they can
    be rebuilt exactly (marked inferred), else the summary only."""
    rv = (rec.get('review') or {}).get('workorder')
    s = {'id': '001', 'from': 'summary', 'summary_only': True, 'status': 'applied', 'started': None, 'finished': rv.get('recorded'),
         'applied': rec.get('written'), 'reviewer': rv.get('reviewer'), 'method': rv.get('method'), 'review': rv,
         'version': {'id': '001', 'pdf_sha256': None}, 'decisions': {}, 'additions': []}
    got = from_summary(ai, rec.get('workorder') or {}, rv, digest)
    if got:
        items = core.build_items(ai, digest); by = {it['id']: it for it in items}
        s['inferred'] = True
        s['decisions'] = {k: {**d, 'ai': by[k]['ai'], 'set_in': '001', 'inferred': True} for k, d in got[0].items()}
        s['additions'] = got[1]
    save_session(R, s)
    return s

# ------------------------------------------------------------------ opening a session
def carry(items, src):
    """The choices of an earlier session that land on today's items: same id, same AI value. Returns (carried, not carried)."""
    by = {it['id']: it for it in items}
    carried, missed = {}, []
    for k, d in (src or {}).items():
        it = by.get(k)
        if it is None: missed.append({'id': k, 'why': 'no such decision in this review'}); continue
        if norm(it['ai']) != norm(d.get('ai')): missed.append({'id': k, 'why': 'the AI value is not the one this choice was made for'}); continue
        carried[k] = d
    return carried, missed

def page_decisions(ds):
    """The page's own format: {status, value?, note?} (set_in, ai and inferred stay in the session record)."""
    return {k: {x: d[x] for x in ('status', 'value', 'note') if x in d} for k, d in ds.items()}

def ocr_info(R, rec):
    """The OCR verdict for the page's banner: the current one (one per run, the latest wins) and each session's snapshot."""
    intake = load(os.path.join(R, '_intake', 'intake.json')) or rec.get('intake') or {}
    from lib.glance import ocr_layer_flagged
    needed = bool((intake.get('ocr') or {}).get('pages_with_ocr_text')) or ocr_layer_flagged(intake)
    cur = (intake.get('review') or {}).get('ocr_text_approved')
    if not needed and not cur: return None
    return {'needed': needed, 'current': cur if isinstance(cur, dict) else None,
            'snapshots': [{'session': s['id'], 'verdict': s.get('ocr_verdict')} for s in sessions(R) if 'ocr_verdict' in s]}

def render_figures(inp, digest, out):
    """The figure crops the review page shows, re-rendered from the input PDF as audit.py makes them (crops are not kept)."""
    import pypdfium2 as pdfium
    from lib import plpages
    want = {}
    for f in (digest.get('figures') or []) + (digest.get('page_figures') or []):
        img = f.get('image')
        if not img or not f.get('page'): continue
        whole = img.endswith('_page.png') or f in (digest.get('page_figures') or [])
        if whole or f.get('bbox_pt'): want[img] = (f['page'], None if whole else f['bbox_pt'])
    if not want: return 0
    os.makedirs(os.path.join(out, 'figures'), exist_ok=True)
    PL = plpages.Pages(inp); doc = pdfium.PdfDocument(inp); renders = {}
    try:
        for img, (pg, box) in want.items():
            path = os.path.join(out, img)
            if os.path.exists(path): continue
            if pg not in renders: renders[pg] = doc[pg - 1].render(scale=2).to_pil()
            im = renders[pg]; vx0, vt, vx1, vb = PL.pages[pg - 1].vis
            box = box or [vx0, vt, vx1, vb]
            x0, t, x1, b = max(box[0], vx0), max(box[1], vt), min(box[2], vx1), min(box[3], vb)
            if x1 <= x0 or b <= t: continue
            x0, t, x1, b = [v * 2 for v in (x0 - vx0, t - vt, x1 - vx0, b - vt)]
            c = im.crop((max(0, x0 - 4), max(0, t - 4), min(im.width, x1 + 4), min(im.height, b + 4)))
            if max(c.size) > 800: c.thumbnail((800, 800))
            c.convert('RGB').save(path)
    finally: doc.close()
    return len(want)

def tidy_open(R):
    """Remove an open session's working files (the draft is kept in the session record first)."""
    p = P(R)
    for n in ('review_items.json', 'review_decisions.json', 'review.json', 'workorder.json'):
        if os.path.exists(os.path.join(p['dir'], n)): os.remove(os.path.join(p['dir'], n))
    for d in (os.path.join(p['dir'], 'review_pages'), os.path.join(p['audit'], 'figures')):
        shutil.rmtree(d, ignore_errors=True)

def open_session(R, rec, src=None, pdf=None, discard_open=False, say=say_):
    """Open a review of a finished run: a new session preloaded from src ('ai', an earlier session id, or None: the latest
    finished or applied one), or the open one carried on. Writes reviews/review_items.json (with the page's session
    block) and reviews/review_decisions.json for review/server.py. Returns the session record."""
    p = P(R)
    b, inp, ai = check_basis(R, rec, pdf)
    digest = load(os.path.join(p['audit'], 'digest.json'))
    readable(core.build_items, ai, digest); readable(core.addable, ai, digest)   # before anything is written
    ss = sessions(R)
    if not ss and (rec.get('review') or {}).get('workorder'):
        s1 = readable(adopt_summary, R, rec, ai, digest); ss = [s1]
        say('  ' + summary_text(s1))
    op = [s for s in ss if s.get('status') == 'open']
    if op and src is None and not discard_open:
        s = op[-1]; say(f'  carrying on with the open {label(s["id"])} (started {s.get("started")})')
    else:
        for s in op:
            if not discard_open: raise Refused(f'{label(s["id"])} is open: run --reopen without --from to carry on with it, or add --discard-open')
            s['draft'] = load(p['draft']); s['status'] = 'abandoned'; s['abandoned'] = now(); save_session(R, s); tidy_open(R)
            say(f'  {label(s["id"])} marked abandoned (kept in reviews/sessions/{s["id"]}.json)')
        done = [s for s in sessions(R) if s.get('status') in ('finished', 'applied')]
        if src is None: src = done[-1]['id'] if done else 'ai'
        if src != 'ai':
            src = f'{int(src):03d}' if str(src).isdigit() else src
            if not any(s['id'] == src for s in done): raise Refused(f'no finished session {src} (see --sessions)')
        s = {'id': next_id(R), 'from': src, 'status': 'open', 'started': now(), 'basis': {k: b.get(k) for k in ('run_id', 'digest_sha256', 'workorder_ai_sha256')},
             'input_sha256': b['input']['sha256']}
        data = readable(core.prepare, p['dir'], inp)
        items = data['items']; s['items_sha256'] = sha_obj([[it['id'], it['ai']] for it in items])
        start, additions, gaps_ack, missed = {}, [], {}, []
        if src != 'ai':
            sv = session(R, src)
            start, missed = carry(items, sv.get('decisions'))
            additions = copy.deepcopy(sv.get('additions') or [])
            gaps_ack = {g['id']: g['reason'] for g in (sv.get('review') or {}).get('gaps') or [] if g.get('reason')}
        s.update(start=start, start_additions=additions, carried=len(start), not_carried=missed, gaps_ack=gaps_ack)
        save_session(R, s)
        save(p['draft'], {'reviewer': '', 'decisions': page_decisions(start), 'additions': additions,
                          'saved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')})
    data = load(p['items'])
    if data is None: data = readable(core.prepare, p['dir'], inp)
    render_figures(inp, digest, p['audit'])
    src_s = session(R, s['from']) if s['from'] not in ('ai', None) else None
    data['run'] = os.path.relpath(R, os.path.dirname(HERE))
    data['session'] = {'key': f'{b["run_id"]}:{s["id"]}', 'id': s['id'], 'from': s['from'],
                       'from_text': ('the AI\'s decisions' if s['from'] == 'ai' else
                                     (summary_text(src_s) if src_s and src_s.get('summary_only') else label(s['from']).capitalize())),
                       'carried': s.get('carried', 0), 'not_carried': s.get('not_carried') or [], 'gaps_ack': s.get('gaps_ack') or {},
                       'set_in': {k: d.get('set_in') for k, d in (s.get('start') or {}).items() if d.get('set_in')},
                       'inferred': {k: d['status'] for k, d in (s.get('start') or {}).items() if d.get('inferred')},
                       'current': label(current_id(rec)), 'result': 'result/review.html', 'ocr': ocr_info(R, rec), 'reopened': True}
    save(p['items'], data)
    return s

def finish_session(R, s, rec):
    """After the page's Finish: the session record gets every choice (with the session that set it), what changed since
    its start, the review and the OCR verdict; the reviewed order is kept as NNN.workorder.json."""
    p = P(R)
    v = load(os.path.join(p['dir'], 'review.json'))
    draft = load(p['draft']) or {}; items = (load(p['items']) or {}).get('items') or []
    start = s.get('start') or {}; got = draft.get('decisions') or {}
    dec, since = {}, []
    for it in items:
        d, st = got.get(it['id']) or {}, start.get(it['id'])
        if not d.get('status'):
            if st: since.append({'id': it['id'], 'was': page_decisions({0: st})[0], 'now': None})
            continue
        same = st is not None and all(st.get(x) == d.get(x) for x in ('status', 'value', 'note'))
        dec[it['id']] = {**{x: d[x] for x in ('status', 'value', 'note') if x in d}, 'ai': it['ai'],
                         'set_in': st['set_in'] if same and st.get('set_in') else s['id'], **({'inferred': True} if same and st.get('inferred') else {})}
        if not same: since.append({'id': it['id'], 'was': page_decisions({0: st})[0] if st else None, 'now': page_decisions({0: d})[0]})
    adds = draft.get('additions') or []
    if norm(adds) != norm(s.get('start_additions') or []): since.append({'id': 'additions', 'was': len(s.get('start_additions') or []), 'now': len(adds)})
    intake = load(os.path.join(R, '_intake', 'intake.json'))
    s.update(status='finished', finished=now(), reviewer=v.get('reviewer'), method=v.get('method'), review=v, decisions=dec, additions=adds,
             since_start=since, carried=sum(1 for d in dec.values() if d['set_in'] != s['id']),
             ocr_verdict=((intake or {}).get('review') or {}).get('ocr_text_approved') if intake else None)
    shutil.move(os.path.join(p['dir'], 'workorder.json'), os.path.join(p['sessions'], f'{s["id"]}.workorder.json'))
    s['workorder_sha256'] = sha_obj(load(os.path.join(p['sessions'], f'{s["id"]}.workorder.json')))
    save_session(R, s)
    tidy_open(R)
    return s

# ------------------------------------------------------------------ the record's view of the sessions
def first_session(R, A, PDF):
    """report.py, first review (REVIEW=1): session 001 from the run folder's review files, moved into reviews/. Returns
    the record's review block, or None when this run had no review."""
    v = load(os.path.join(R, 'review.json'))
    if v is None: return None
    p = P(R); draft = load(os.path.join(R, 'review_decisions.json')) or {}
    data = load(os.path.join(R, 'review_items.json')) or {}
    items = data.get('items') or []
    if basis(R) is None:
        inp = data.get('pdf') if data.get('pdf') and os.path.isfile(data['pdf']) else None
        if inp: first_basis(R, inp)
    again = [x for x in sessions(R) if (x.get('review') or {}).get('recorded') == v.get('recorded')]   # report.py run again
    sid = again[0]['id'] if again else next_id(R)
    s = {'id': sid, 'from': 'ai', 'started': (basis(R) or {}).get('made')}
    got = draft.get('decisions') or {}
    by = {it['id']: it for it in items}
    dec = {k: {**{x: d[x] for x in ('status', 'value', 'note') if x in d}, 'ai': by[k]['ai'], 'set_in': sid}
           for k, d in got.items() if (d or {}).get('status') and k in by}
    intake = load(os.path.join(R, '_intake', 'intake.json'))
    s.update(status='applied', finished=v.get('recorded'), applied=now(), reviewer=v.get('reviewer'), method=v.get('method'), review=v,
             decisions=dec, additions=draft.get('additions') or [], carried=0, since_start=[],
             ocr_verdict=((intake or {}).get('review') or {}).get('ocr_text_approved') if intake else None,
             version={'id': sid, 'pdf_sha256': sha_file(os.path.join(R, PDF)) if os.path.exists(os.path.join(R, PDF)) else None},
             basis={k: (basis(R) or {}).get(k) for k in ('run_id', 'digest_sha256', 'workorder_ai_sha256')})
    if os.path.exists(os.path.join(R, 'workorder.json')):
        os.makedirs(p['sessions'], exist_ok=True)
        shutil.copy2(os.path.join(R, 'workorder.json'), os.path.join(p['sessions'], f'{sid}.workorder.json'))
        s['workorder_sha256'] = sha_obj(load(os.path.join(R, 'workorder.json')))
    s.pop('start', None)
    save_session(R, s)
    return {'session': sid, 'sessions': [summary_row(x) for x in sessions(R)], 'decisions': decision_list(items, dec) if items else None,
            'run_id': (basis(R) or {}).get('run_id'), 'run': os.path.relpath(R, HERE)}

def keep_first(R, A):
    """report.py's tidy after a first review: the AI's order goes to reviews/ (the review files are in the session)."""
    p = P(R)
    if os.path.exists(os.path.join(R, 'workorder.ai.json')):
        os.makedirs(p['dir'], exist_ok=True); shutil.copy2(os.path.join(R, 'workorder.ai.json'), p['ai'])

# ------------------------------------------------------------------ the lock
class Lock:
    """reviews/.lock: one review (open, or being applied) per run. A lock left by a process that has ended is taken over."""
    def __init__(self, R, what):
        self.path = P(R)['lock']; os.makedirs(os.path.dirname(self.path), exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, 'w') as f: json.dump({'pid': os.getpid(), 'since': now(), 'what': what}, f)
                return
            except FileExistsError:
                old = load(self.path) or {}
                try: os.kill(int(old.get('pid')), 0); alive = True
                except (OSError, TypeError, ValueError): alive = False
                if alive: raise Refused(f'another review of this run is running (process {old.get("pid")}, {old.get("what")}, since {old.get("since")})')
                os.remove(self.path)
        raise Refused('could not take the review lock')
    def release(self):
        try: os.remove(self.path)
        except FileNotFoundError: pass
    def __enter__(self): return self
    def __exit__(self, *a): self.release()

# ------------------------------------------------------------------ re-apply and promotion
def fulltext_for(R, inp, say=say_):
    """fulltext.json for review.md's whole texts: kept for runs made on this branch; for a pinned run, taken from a fresh
    audit only when that audit is the same as the kept one (else review.md quotes the digest's shortened texts)."""
    p = P(R); ft = os.path.join(p['audit'], 'fulltext.json')
    if os.path.exists(ft): return True
    tmp = tempfile.mkdtemp(prefix='fulltext-')
    try:
        say('  fulltext.json not kept with this run: re-auditing the input for it (no model)…')
        try: reaudit(inp, tmp)
        except Refused as e: say(f'  note: {e}'); return False
        if sha_file(os.path.join(tmp, 'digest.json')) != sha_file(os.path.join(p['audit'], 'digest.json')):
            say('  note: today\'s audit differs from the kept one: review.md quotes the digest\'s shortened texts'); return False
        shutil.copy2(os.path.join(tmp, 'fulltext.json'), ft); return True
    finally: shutil.rmtree(tmp, ignore_errors=True)

def _run(args, say, what, quiet=False):
    t = time.time(); say(f'▶ {what}')
    r = subprocess.run([sys.executable] + args, cwd=HERE, env=audit_env(), stdout=subprocess.DEVNULL if quiet else None)
    d = time.time() - t
    if r.returncode != 0: raise Refused(f'{what} failed (exit {r.returncode}): the current result is unchanged; the session stays finished (run --apply again)')
    say(f'  ✓ {what}: {d:.1f}s'); return round(d, 1)

def reapply(R, s, pdf=None, say=say_):
    """Apply session s's reviewed order to the run's input (no AI call), verify, report, and make it the current version.
    The current version is moved to reviews/versions/<its id>/ only after all three succeed."""
    R = os.path.abspath(R); p = P(R)
    rec = load(os.path.join(R, 'record.json'))
    b, inp, ai = check_basis(R, rec, pdf)
    wo_path = os.path.join(p['sessions'], f'{s["id"]}.workorder.json')
    wo = load(wo_path)
    if wo is None or (s.get('workorder_sha256') and sha_obj(wo) != s['workorder_sha256']): raise Refused(f'{wo_path} is missing or not the one the session recorded')
    if (wo.get('source') or {}).get('sha256') != b['input']['sha256']: raise Refused('the reviewed order was written for another file (source.sha256)')
    out = (rec.get('document') or {}).get('output')
    if not out: raise Refused('the record does not name its remediated PDF (document.output)')
    W = p['work']; shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy2(wo_path, os.path.join(W, 'workorder.json'))
    save(os.path.join(W, 'review.json'), s['review'])
    shutil.copy2(p['ai'], os.path.join(W, 'workorder.ai.json'))
    fulltext_for(R, inp, say)
    t = {'4/5 apply (no model)': _run(['apply.py', inp, os.path.join(W, 'workorder.json'), os.path.join(W, out)], say, 'apply (no model)')}
    t['4/5 verify (no model)'] = _run(['verify.py', inp, os.path.join(W, out)], say, 'verify (no model)', quiet=True)
    save(os.path.join(W, 'timing.json'), t)
    items = readable(core.build_items, ai, load(os.path.join(p['audit'], 'digest.json')))
    s2 = dict(s, status='applied')
    info = {'session': s['id'], 'sessions': [summary_row(x if x['id'] != s['id'] else s2) for x in sessions(R)],
            'decisions': decision_list(items, s.get('decisions') or {}), 'run_id': b['run_id'], 'run': os.path.relpath(R, HERE)}
    save(os.path.join(W, 'review_session.json'), info)
    _run(['report.py', W, p['audit'], '--keep', f'--pdf={out}', f'--from-record={os.path.join(R, "record.json")}',
          f'--intake={os.path.join(R, "_intake")}'], say, 'report')
    for n in os.listdir(W):                              # a version is its outputs only
        if n not in OUT_FILES and n != out: (shutil.rmtree if os.path.isdir(os.path.join(W, n)) else os.remove)(os.path.join(W, n))
    promote(R, s['id'], out, say)
    s = session(R, s['id'])
    s.update(status='applied', applied=now(), version={'id': s['id'], 'pdf_sha256': sha_file(os.path.join(R, out))})
    save_session(R, s)
    rebuild_batch(R, say)
    return s

def promote(R, sid, out, say=say_):
    """The new result (reviews/work/) becomes the top level; the old one goes to reviews/versions/<its id>/. A marker
    (promoting.json) lets an interrupted promotion be completed: a record.json is at the top level at every moment."""
    p = P(R)
    m = load(p['promoting'])
    if m is None:
        old = load(os.path.join(R, 'record.json'))
        m = {'to': sid, 'from': current_id(old), 'out': out, 'stage': 'save old'}; save(p['promoting'], m)
    V = os.path.join(p['versions'], m['from'])
    if m['stage'] == 'save old':
        os.makedirs(V, exist_ok=True)
        if not os.path.exists(os.path.join(V, 'record.json')): shutil.copy2(os.path.join(R, 'record.json'), os.path.join(V, 'record.json'))
        for n in (m['out'],) + OUT_FILES[1:]:
            if os.path.exists(os.path.join(R, n)) and not os.path.exists(os.path.join(V, n)): shutil.move(os.path.join(R, n), os.path.join(V, n))
        m['stage'] = 'move new'; save(p['promoting'], m)
    if m['stage'] == 'move new':
        W = p['work']
        for n in (m['out'],) + OUT_FILES[1:]:
            if os.path.exists(os.path.join(W, n)): shutil.move(os.path.join(W, n), os.path.join(R, n))
        if os.path.exists(os.path.join(W, 'record.json')): os.replace(os.path.join(W, 'record.json'), os.path.join(R, 'record.json'))
        m['stage'] = 'banner'; save(p['promoting'], m)
    if m['stage'] == 'banner':
        try: replaced_banner(V, m['from'], m['to'], R)
        except Exception as e: say(f'  note: the replaced version\'s review.html was not rebuilt ({type(e).__name__}: {e})')
        shutil.rmtree(p['work'], ignore_errors=True)
        os.remove(p['promoting'])
    say(f'  current result: {label(m["to"])}; {label(m["from"])} kept in reviews/versions/{m["from"]}/')

def replaced_banner(V, old, new, R):
    import report_html as H
    rec = load(os.path.join(V, 'record.json'))
    rel = os.path.relpath(os.path.join(R, 'review.html'), V)
    H.review_html(V, rec, None, None, banner=f'This result ({label(old)}) was replaced by {label(new)}. '
                                             f'<a href="{rel}">Open the current result</a>.')

def rebuild_batch(R, say=say_):
    """A book in a batch folder: rebuild the batch's summary.html (summary.md stays the batch run's own record)."""
    B = os.path.dirname(R)
    if os.path.exists(os.path.join(B, 'summary.html')):
        try:
            import report_html as H; H.summary_html(B); say(f'  {os.path.join(B, "summary.html")} rebuilt')
        except Exception as e: say(f'  note: summary.html not rebuilt ({type(e).__name__}: {e})')

def mark_pending(R, s):
    """record.json review.pending: a session that is open, or finished and not applied (ready to ship then says No), and the
    Overview and review.html refreshed. None clears it."""
    rj = os.path.join(R, 'record.json'); rec = load(rj)
    if rec is None: return
    rv = rec.setdefault('review', {})
    if s is None: rv.pop('pending', None)
    else: rv['pending'] = {'session': s['id'], 'status': s['status'], 'since': s.get('finished') or s.get('started'), 'reviewer': s.get('reviewer')}
    if not rv: rec.pop('review')
    try:
        from lib import glance as G
        import report_html as H
        labels = H.labels_of(R, rec)
        if rec.get('sections_version') == 1:
            text = G.refresh(rec, labels, H.han_pages(R))
            open(os.path.join(R, 'review.md'), 'w', encoding='utf-8').write(text)
        else:
            text = open(os.path.join(R, 'review.md'), encoding='utf-8').read()
            rec['glance'] = G.glance(rec, text, labels, H.han_pages(R))
            text = G.replace_block(text, G.glance_md(rec['glance'])); open(os.path.join(R, 'review.md'), 'w', encoding='utf-8').write(text)
        json.dump(rec, open(rj, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        H.review_html(R, rec, text, labels)
    except Exception as e:
        json.dump(rec, open(rj, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'note: "Overview" and review.html not refreshed ({type(e).__name__}: {e})')
