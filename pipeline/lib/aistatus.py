"""#151 (App: hold the review when AI requests did not finish): one place that says whether a run's AI steps finished.

The language step (name_languages.py) and the page readings (read_pages.py) record how they ended in the run folder's
ai_outcome.json ({"schema": "ai-outcome/1", "language": {why, words, detail, at}, "pages": {…}}), written only through
record() (read, merge, then an atomic replace: the steps run one after another, never at once). `why`:

  started        the paid part began (still there after a crash or a kill: no `finally` ran)
  done           the step ended; its own entries say what is unfinished
  error, lookup  it stopped: an error (a missing prompt, no key, an exception, Ctrl-C), or the model lookup failed
  cap, book      left out for its cost: over its own limit, or the PDF's
  credit         refused for the credit left
  pages_changed  (language) new page readings changed words the language step had answered (a retry's page part)
  forms_changed  (language) the estimate after the work order holds back more word forms than the one shown before it
                 (review 33 F1): not sent with nobody at the keyboard (AUTO=1, every app job); the review holds
  declined       a person answered "no" in the terminal
  saved          a saved reply's decisions were applied (no request)
  not_run        not run by design (a saved reply from elsewhere, DECIDE=none, the step off, nothing to read)

record() never lets not_run or saved replace a refusal (cap, book, credit), and never lets saved replace done, error,
lookup or started (review 26 M1). The file's presence is the marker that a run records outcomes (review 24 M4): a run
without it (stopped for review before this branch) is judged by its request entries alone.

finished() is the one rule for a language request entry, used by name_languages.reusable() (what a retry reuses) and by
unfinished() (what holds): no error; finish 'stop', or cut off with a finished resend; a reply that isn't wholly
unreadable; and an entry whose resend was needed (`resend` set: its unreached forms) only when that resend finished.

    python3 -m lib.aistatus create RUN_DIR
    python3 -m lib.aistatus record RUN_DIR STEP WHY [WORDS]
    python3 -m lib.aistatus refused RUN_DIR STEP ESTIMATE_FILE     a kept refusal in an estimate, recorded (exit 0 if one was)
    python3 -m lib.aistatus held RUN_DIR [AUDIT_DIR]               exit 0 when the review is held; prints why
    python3 -m lib.aistatus retry RUN_DIR [AUDIT_DIR]              prints "pages", "language" or nothing: what a retry sends
    python3 -m lib.aistatus held-count ESTIMATE_FILE              prints how many word forms the estimate holds back (0 if none or unreadable)
"""
import os, sys, json, time, tempfile

NAME = 'ai_outcome.json'
OVERRIDE = 'ai_override.json'
SCHEMA = 'ai-outcome/1'
REFUSALS = ('cap', 'book', 'credit')
FAILED = ('started', 'error', 'lookup')
STEPS = ('language', 'pages')

def _load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None

def _write(p, d):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p) or '.', prefix='.ai_outcome.', suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)

def create(R):
    """A fresh file: this call decides the work order anew (review 25 §2.3, 26 M1)."""
    _write(os.path.join(R, NAME), {'schema': SCHEMA})

def outcomes(R):
    """The file's content, or None when the run records no outcomes (made before #151)."""
    d = _load(os.path.join(R, NAME))
    return d if isinstance(d, dict) and d.get('schema') == SCHEMA else None

def record(R, step, why, words='', detail=''):
    """Record how `step` ended. Never weaker than what is there: a refusal stays against not_run or saved, and saved
    stays out of done, error, lookup and started. Writes nothing when the run records no outcomes and `why` is one of
    run_api.sh's (saved, not_run, declined): an old folder stays old. Returns the outcome kept."""
    p = os.path.join(R, NAME)
    d = outcomes(R)
    if d is None:
        if why in ('saved', 'not_run', 'declined'): return None
        d = {'schema': SCHEMA}
    old = (d.get(step) or {}).get('why')
    if why in ('not_run', 'saved') and old in REFUSALS: return old
    if why == 'saved' and old in ('done',) + FAILED: return old
    d[step] = {'why': why, **({'words': words} if words else {}), **({'detail': detail[:2000]} if detail else {}), 'at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    _write(p, d)
    return why

def outcome(R, step):
    d = outcomes(R)
    return (d or {}).get(step) or {}

# ---------------------------------------------------------------- the language step's entries
def finished(entry, resend=None):
    """One language request entry (language_run.json `requests`), with its resend entry when it had one."""
    if not isinstance(entry, dict) or entry.get('error'): return False
    if entry.get('resend'):                       # its unreached forms needed a resend: finished only when it finished (26 M1)
        return bool(resend) and finished(resend)
    if entry.get('finish') == 'length': return bool(resend) and finished(resend)
    if entry.get('finish') != 'stop': return False
    return not unreadable(entry)

def unreadable(entry):
    """A reply that can't be read at all (no decision list): langreq.parse's whole-reply drop."""
    text = entry.get('text')
    if text is None: return False                 # a finished record keeps no text: its own parse ran when it was written
    try:
        from lib import langreq
        _, dr = langreq.parse(text, set(entry.get('ids') or []))
    except Exception: return False
    return any(e.get('code') == 'unreadable' for e in dr)

def pairs(run):
    """[(original, resend or None)] of a language_run.json."""
    reqs = [r for r in (run or {}).get('requests') or [] if isinstance(r, dict)]
    rs = {r['resend_of_sha256']: r for r in reqs if r.get('resend_of_sha256')}
    return [(r, rs.get(r.get('sha256'))) for r in reqs if not r.get('resend_of_sha256')]

def language_unfinished(run):
    """The request numbers of the step's own estimate (1 … estimate.requests) with no finished entry (review 24 L3)."""
    if not isinstance(run, dict) or (run.get('response_from') and not run.get('own_reply')): return []   # a reply from elsewhere: nothing to resend here
    n = int(((run.get('estimate') or {}).get('requests')) or 0)
    ok = {o.get('n') for o, r in pairs(run) if finished(o, r)}
    seen = {o.get('n') for o, _ in pairs(run)}
    if not n: n = max(seen | {0})
    return [i for i in range(1, n + 1) if i not in ok]

def pages_unfinished(run, listed):
    """Pages the audit lists with no reading that finished (text and finish 'stop')."""
    done = {x.get('page') for x in (run or {}).get('pages') or [] if isinstance(x, dict) and x.get('finish') == 'stop' and (x.get('text') or '').strip()}
    return sorted(p for p in listed if p not in done)

# ---------------------------------------------------------------- the hold
WORDS = {
    'cap': {'language': 'The language suggestions were left out because they could cost more than the limit for language suggestions.',
            'pages': 'The page readings were left out because they could cost more than the limit for page readings.'},
    'book': {'language': 'The language suggestions were left out because they could cost more than this PDF\'s limit.',
             'pages': 'The page readings were left out because they could cost more than this PDF\'s limit.'},
    'credit': 'There was not enough AI credit.',
    'lookup': 'The AI service could not be reached to look up the model.',
    'error': 'The step stopped with an error.',
    'started': 'The step did not run to the end.',
    'pages_changed': 'New page readings changed some words.',
    'forms_changed': 'More word forms were found after the estimate.',
}

def _listed(A):
    return [p['page'] for p in ((_load(os.path.join(A, 'page_reads.json')) or {}).get('pages') or []) if isinstance(p, dict) and 'page' in p] if A else []

def status(R, A=None):
    """{held, steps: {step: {state, why, words, count, retry}}, figures, override, marker}. state: 'unfinished' (failed,
    stopped or partly answered: "Ask the AI Again" can send it), 'left_out' (cap, book: the override only) or 'ok'."""
    A = A or os.path.join(R, '_audit')
    marker = outcomes(R) is not None
    steps = {}
    # the language step
    o = outcome(R, 'language'); why = o.get('why')
    run = _load(os.path.join(R, 'language_run.json'))
    est = _load(os.path.join(R, 'language_estimate.json')) or {}
    st = None
    if why in ('cap', 'book'): st = ('left_out', 0, False)
    elif why == 'credit': st = ('unfinished', len(language_unfinished(run)) or int(est.get('to_send') or 0), True)
    elif why in FAILED: st = ('unfinished', len(language_unfinished(run)) or int(est.get('to_send') or 0), True)
    elif why == 'pages_changed': st = ('unfinished', int((_load(os.path.join(R, 'language_retry_estimate.json')) or {}).get('to_send') or 0), True)
    elif why == 'forms_changed':                     # review 33 F1: requests to send, by the retry's own estimate when made (the review stop)
        st = ('unfinished', int((_load(os.path.join(R, 'language_retry_estimate.json')) or est).get('to_send') or 0), True)
    elif why in ('declined', 'not_run'): st = None
    elif why in ('done', 'saved') or (why is None and run):
        left = language_unfinished(run)               # a saved reply from elsewhere has none; this folder's own replay is judged by its entries (26 M1)
        if left: st = ('unfinished', len(left), True)
    elif why is None and marker and est.get('to_send') and not est.get('refused'):
        st = ('unfinished', int(est['to_send']), True)
    if st: steps['language'] = {'state': st[0], 'why': why or 'done', 'count': st[1], 'retry': st[2],
                                'words': o.get('words') or (WORDS[why][('language')] if why in ('cap', 'book') else WORDS.get(why, ''))}
    # the page readings
    o = outcome(R, 'pages'); why = o.get('why')
    prun = _load(os.path.join(R, 'page_reads_run.json'))
    pest = _load(os.path.join(R, 'page_reads_estimate.json')) or {}
    listed = _listed(A)
    st = None
    if why in ('cap', 'book'): st = ('left_out', len(listed), False)
    elif why in ('credit',) + FAILED: st = ('unfinished', len(pages_unfinished(prun, listed)) or int(pest.get('to_read') or 0), True)
    elif why in ('done', 'saved') or (why is None and prun):
        left = pages_unfinished(prun, listed)
        if left: st = ('unfinished', len(left), True)
    elif why is None and marker and pest.get('to_read') and not pest.get('refused'):
        st = ('unfinished', int(pest['to_read']), True)
    if st: steps['pages'] = {'state': st[0], 'why': why or 'done', 'count': st[1], 'retry': st[2],
                             'words': o.get('words') or (WORDS[why]['pages'] if why in ('cap', 'book') else WORDS.get(why, ''))}
    # figure requests: no retry on this branch (#152 (AI call: resend only the figure requests that did not finish))
    rj = _load(os.path.join(R, 'run.json')) or {}
    failed = (rj.get('figure_passes') or {}).get('failed') or []
    figures = {'state': 'unfinished', 'count': len(failed), 'retry': False} if failed else None
    ov = _load(os.path.join(R, OVERRIDE))
    held = bool(steps or figures) and not (isinstance(ov, dict) and ov.get('by'))
    return {'held': held, 'steps': steps, 'figures': figures, 'override': ov if isinstance(ov, dict) else None, 'marker': marker}

def held_count(est):
    """How many word forms an estimate (or a language record) holds back: 0 for a refused one, which sends nothing."""
    if not isinstance(est, dict) or est.get('refused'): return 0
    h = est.get('held_back')
    try: return int(h if isinstance(h, int) else est.get('held_back_count') or 0)
    except (TypeError, ValueError): return 0

def held_back_words(est, terminal=False, after=False):
    """#159 (Patrick's decision: a warning before money is spent, never a refusal): the sentence for an estimate (or a
    language record) that holds word forms back; None when nothing is held back, or when the estimate left the step out
    (review 31: no warning for a step that is not run). `terminal` adds how to raise the limit for this run in
    run_api.sh's own words; `after` says it in the past tense, for the review page after the run (review 31 L3)."""
    n = held_count(est)
    if not n: return None
    total = int(est.get('forms') or 0) - int(est.get('local') or 0)
    of = f'{n:,} of {total:,} word forms' if total > n else f'{n:,} word form' + ('' if n == 1 else 's')
    lim = est.get('held_back_limit') or {}
    def usd(v): v = float(v or 0); return f'${v:,.0f}' if v == int(v) else f'${v:,.2f}'
    if est.get('held_back_why') == 'forms':
        why = 'they ' + ('were' if after else 'are') + ' more than the set number of word forms'
    elif lim.get('which') == 'book':
        why = 'they ' + ('did not' if after else "don't") + f" fit within the room left in this PDF's limit ({usd(lim.get('usd'))} per PDF)"
    else:
        why = 'they ' + ('did not' if after else "don't") + f" fit within the limit for language suggestions ({usd(lim.get('usd'))})"
    one = n == 1
    if after:
        s = (f'{of} ' + ('was' if one else 'were') + f' not sent to the AI: {why}. ' + ('It is' if one else 'They are')
             + ' not tagged, and the PDF can\'t be Ready until someone accepts that.')
    else:
        s = (f'{of} will not be sent to the AI: {why}. ' + ('It' if one else 'They') + ' will not be tagged, and the PDF can\'t be Ready until someone accepts that.')
    if terminal:
        about = est.get('all_usd_about')
        var = 'LANGUAGE_MAX_FORMS' if est.get('held_back_why') == 'forms' else 'BOOK_MAX_USD' if lim.get('which') == 'book' else 'LANGUAGE_MAX_USD'
        s += (f' To send them all (about ${about:,.2f} in all at most), raise the limit for this run: {var}=…' if about and var != 'LANGUAGE_MAX_FORMS'
              else f' To send more, raise the limit for this run: {var}=…')
    return s

def on_exit(R, step, e):
    """How a step that stops after it started is recorded (review 24 L2), for name_languages.py and read_pages.py: a
    refusal already recorded is never overwritten; a clean exit (SystemExit 0 or None) records nothing; Ctrl-C is an
    error with its own words; anything else is an error. A kill runs nothing and leaves `started`. Returns what it recorded."""
    if outcome(R, step).get('why') != 'started': return None
    if isinstance(e, SystemExit) and e.code in (None, 0): return None
    words = 'The step was stopped before it finished.' if isinstance(e, KeyboardInterrupt) else WORDS['error']
    record(R, step, 'error', words, f'{type(e).__name__}: {e}' if e is not None else 'stopped')
    return words

def set_override(R, by, date=None):
    """A person's choice to review without what is missing ("Review Without the Missing Suggestions", or
    review_workorder.py --override NAME): ai_override.json, with what was missing in plain words. It stays through the
    apply (report.py's tidy keeps it) and is copied into every finished review session (review/core.py finish)."""
    by = (by or '').strip()
    if not by: raise ValueError('a name is required')
    s = status(R)
    d = {'by': by[:120], 'date': date or time.strftime('%Y-%m-%d'), 'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'missing': lines(s)}
    _write(os.path.join(R, OVERRIDE), d)
    return d

def retry_parts(s):
    """What one "Ask the AI Again" sends (review 25 §2.4, two parts): the page readings first when they are unfinished,
    else the language step; None when neither can be sent again."""
    st = s['steps']
    if (st.get('pages') or {}).get('retry'): return 'pages'
    if (st.get('language') or {}).get('retry'): return 'language'
    return None

def lines(s):
    """Plain sentences for the terminal and the review page's refusal: one per held part."""
    def n_(c, one, many): return f'{c:,} {one if c == 1 else many}'
    out = []
    names = {'language': ('Language Suggestions', ('request not finished', 'requests not finished')), 'pages': ('Page Readings', ('page not read', 'pages not read'))}
    for k, v in s['steps'].items():
        title, unit = names[k]
        if v['state'] == 'left_out': out.append(f'{title} Not Made: {v["words"]}')
        else:
            text = v['words'] or 'Some AI requests did not finish.'
            if v['count']: text = text.rstrip('.') + f' ({n_(v["count"], *unit)}).'
            out.append(f'{title} Not Finished: {text}')
    if s['figures']:
        c = s['figures']['count']
        out.append(f'Figure Descriptions Not Finished: {n_(c, "figure request", "figure requests")} did not finish.')
    return out

def _main(argv):
    cmd = argv[0] if argv else ''
    if cmd == 'create': create(argv[1]); return 0
    if cmd == 'record':
        record(argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else ''); return 0
    if cmd == 'refused':
        e = _load(argv[3]) or {}
        ref = e.get('refused') if isinstance(e.get('refused'), dict) else None
        if not ref or ref.get('why') not in ('cap', 'book'): return 1
        record(argv[1], argv[2], ref['why'], ref.get('words') or ''); print(ref.get('words') or ''); return 0
    if cmd == 'held':
        s = status(argv[1], argv[2] if len(argv) > 2 else None)
        for l in lines(s): print(l)
        return 0 if s['held'] else 1
    if cmd == 'retry':
        s = status(argv[1], argv[2] if len(argv) > 2 else None)
        print(retry_parts(s) or ''); return 0
    if cmd == 'held-count':
        print(held_count(_load(argv[1]))); return 0
    print(__doc__); return 2

if __name__ == '__main__': sys.exit(_main(sys.argv[1:]))
