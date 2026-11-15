"""webapp/logs.py: what the app reads from a job's log. These are the lines the command-line tools already print; the
tests pin each one against its source (tests/test_webapp_panel.py), so a wording change breaks a test, not the page.

    review page: http://localhost:8765/       review/server.py, when the review page is up (the URL the panel opens)
    review recorded: …                        review_workorder.py, after Finish (--serve and --reopen)
    ▶ <step>  /  ✓ <step>: 12.3s              run_api.sh's stage() and review/sessions.py's _run(): a step starts / ends
    done: session 4 is the current result …   review_workorder.py, after a re-apply
    session 4 stays open: …                   review_workorder.py, after Ctrl+C on the review page
    refused: …                                review_workorder.py, any refusal (sessions.Refused)
"""
import re

URL = re.compile(r'^review page: (http://localhost:\d+/)\s*$', re.M)
RECORDED = 'review recorded: '
START = re.compile(r'^▶ (.+?)\s*$')
END = re.compile(r'^\s*✓ (.+?): ([0-9.]+s|\d+m [0-9.]+s)\s*$')
DONE = re.compile(r'^done: (.+? is the current result) in ', re.M)
STAYS_OPEN = re.compile(r'^(session \d+) stays open: ', re.M)
REFUSED = re.compile(r'^refused: (.+)$', re.M)

def review_url(text):
    m = URL.search(text); return m.group(1) if m else None

def steps(text):
    """[{label, state: done | running, time}] in order. A ▶ line with no ✓ before the next ▶ is a note: done, no time."""
    out = []
    for line in text.splitlines():
        m = START.match(line)
        if m:
            if out and out[-1]['state'] == 'running': out[-1]['state'] = 'done'
            out.append({'label': m.group(1), 'state': 'running', 'time': None}); continue
        m = END.match(line)
        if m:
            hit = next((s for s in reversed(out) if s['label'] == m.group(1)), None)
            if hit: hit.update(state='done', time=m.group(2))
            else: out.append({'label': m.group(1), 'state': 'done', 'time': m.group(2)})
    return out

PLAIN = {'apply': 'applying the reviewed decisions', 'verify': 'checking the result', 'report': 'writing the report',
         'intake': 'reading and tagging the PDF', 'audit': 'auditing the PDF', 'cost estimate': 'estimating the cost',
         'reuse saved reply': 'reading the saved reply',
         # every other stage label run_api.sh and review/sessions.py write (Patrick's dakine test, 2026-11-14)
         'OCR language check': 'checking the OCR language', 'veraPDF on the original': 'checking the original with veraPDF',
         'no AI call': 'no AI request (a person decides)', 'page readings via OpenRouter': 'sending to the AI: Hawaiian page readings',
         'language tags via OpenRouter': 'sending to the AI: language tags', 'review': 'preparing the review page',
         "the previous attempt's reply was complete but could not be read": 'reading the saved reply again',
         'the work order was reviewed by a person': 'applying the reviewed decisions',
         'every AI request of the previous attempt finished (a later step failed)': 'reusing the finished AI answers',
         "the previous attempt's reply was complete (a later step failed)": 'reusing the finished AI answer',
         'the previous attempt was stopped while its figure requests were being sent': 'resuming the figure requests',
         'previous attempt logged': 'starting a new AI request after the previous one'}
SAVED_LANG = re.compile(r'^language tags: (?:saved decisions|this run\'s own decisions)')       # a replay: no request
FIGURES = re.compile(r'^figure request (\d+)(?: of (\d+))?$')                                 # pass 2 is figure request 1
NUMBERED = re.compile(r'^(\d+)[a-z]?/(\d+) ')               # 3/5, and 3b/5 or 3c/5 (the optional steps)

AI_STEP = re.compile(r'^(\S+) via OpenRouter$')

def plain(label):
    """A step's label in plain words: "apply (no model)" → "applying the reviewed decisions"; others without their notes
    (a step run_api.sh did not run again reads as the step itself: P13). The AI step names the model the run itself used
    (run_api.sh writes it in the label) by its display name: "3/5 anthropic/claude-sonnet-5.5 via OpenRouter" →
    "sending to the AI (Claude Sonnet 5.5)" (V2, Patrick 2026-11-07)."""
    bare = re.sub(r'\s*\((?:no model|local, no model|no cost)\)', '', NUMBERED.sub('', label)).strip()
    if SAVED_LANG.match(bare): return 'sending to the AI: language tags (saved decisions, no cost)'
    core = bare.split(':')[0].strip()
    f = FIGURES.match(core)
    if f:                                              # "figure request 3 of 4" (passes) → "request 2 of 3" (figure requests)
        n = int(f.group(1)) - 1
        return f'sending to the AI: figures, request {n} of {int(f.group(2)) - 1}' if f.group(2) else f'sending to the AI: figures, request {n}'
    m = AI_STEP.match(core)
    if m:
        from .runs import model_words
        return f'sending to the AI ({model_words(m.group(1))})'
    if core in PLAIN: return PLAIN[core]
    return PLAIN.get(re.sub(r'\s*\(.*\)\s*$', '', core), core)       # P13: a reused step reads as the step itself; a note in parentheses left out

STEPS_OF = {'apply': 3, 'review': 3}                    # a re-apply's steps: apply, verify, report (review/sessions.py reapply)

def now_step(kind, steps):
    """The step running now, as {words, n, total} ("checking the result", 2 of 3), or None."""
    run = [i for i, s in enumerate(steps) if s['state'] == 'running']
    if kind == 'pin' and not steps: return {'words': 're-auditing the run to pin it (free)', 'n': 1, 'total': 1}
    if not run: return None
    i = run[-1]; m = NUMBERED.match(steps[i]['label'])
    if m: return {'words': plain(steps[i]['label']), 'n': int(m.group(1)) + 1, 'total': int(m.group(2)) + 1}
    return {'words': plain(steps[i]['label']), 'n': i + 1, 'total': max(STEPS_OF.get(kind, len(steps)), len(steps))}

def outcome(text):
    """The tool's own last word: a refusal, the re-apply's done line, a session left open; else None."""
    for rx, fmt in ((REFUSED, 'refused: {}'), (DONE, 'done: {}'), (STAYS_OPEN, '{} stays open')):
        ms = list(rx.finditer(text))
        if ms: return fmt.format(ms[-1].group(1).strip())
    return None

def tail(text, n=15):
    """The last n non-empty lines (the page shows the whole log under "details")."""
    lines = [l for l in text.rstrip('\n').splitlines() if l.strip()]
    return lines[-n:]
