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
