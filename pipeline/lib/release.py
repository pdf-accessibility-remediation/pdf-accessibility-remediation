"""lib/release.py: the accessibility evaluation (PAC 2026 and the screen-reader test; "Manual Checks" in the records and
the code), shipments and the book's status, with no web server and no writing (review/manual.py writes; issue #38).

    rel = load(R)                                  # release/checks.json and release/shipped.json, empty when absent
    ev  = evaluation(rel, sha)                     # both parts on the file with this hash: completed?, issues noted
    ok, text = evaluation_line(rel, cur_sha)       # "Ready to Ship?"'s "Accessibility Evaluation" line
    st  = status(rel, cur_sha, base_ok, newer, session)   # {name, text, newer, issues}: Not Ready, Pending Evaluation, Ready, Shipped
    rec = validate(section, data, ctx)             # a result as it will be recorded; raises Invalid with every problem

The rule (decided 2026-10-31, after testing the page; 13-builder-stage2-revisions-proposal.md): the evaluation is a
report, not a gate on its results. A part is completed for a file when its latest result on that file has, for every item
the checklist asks, one of that item's own choices. A Fail never blocks: it needs a note, and it is counted as an issue
noted in the status ("Ready · 2 issues noted").

Every check and shipment records the sha256 of the remediated PDF it was made on (`pdf.sha256`). A check counts only for
the file with that hash: `cur_sha` is the record's `document.output_sha256` (offline dashboards) or the hash the app read
from disk. Nothing here relies on an apply giving new bytes.

The records (release/checks.json, schema manual-checks/1; /2 is reserved for "Fail, Accepted with a Note"):
    {schema, pac: [check …], screen_reader: [check …]}            newest last; nothing is deleted
    check: {id, recorded, by, via, code, pdf: {sha256, file, session, which, shipment}, fields, items: {key: {result, note}}, notes}
`result` is only what the person saw: pass | fail | na (not_run in an older record's PDF/UA row). Reads fail closed: a
missing item, an unknown result or an unknown item makes that part "could not be read in full" (not completed), never
completed. An `accepted` key (once reserved) is read by the result alone. `state`, "completed" and the issues are worked
out on every read, never trusted from storage. RETIRED items and fields (PAC's PDF/UA check, PAC Version: retired
2026-10-31) are known: never offered, never counted, shown only in an older record's full results.
release/shipped.json: [{n, shipped, by, pdf: {sha256, file, session}, where, note, withdrawn?: {by, date, reason}}]
"""
import os, re, json, hashlib
from lib import dates as D

SCHEMA = 'manual-checks/1'
READ_SCHEMAS = ('manual-checks/1', 'manual-checks/2')
SECTIONS = ('pac', 'screen_reader')
NAME_MAX, FIELD_MAX, NOTE_MAX, NOTES_MAX = 80, 80, 1000, 4000
PAGES = re.compile(r'\d+(-\d+)?(, ?\d+(-\d+)?)*')

# The checklist, once: the Manual Checks page, manual_checks.py, review.md's PAC section and the disclosure read it.
# results: the choices; pages: offers the pages checked (fields.pages_checked, optional);
# found: the thing the pipeline counted (Not Applicable then needs a note).
P3 = ('pass', 'fail', 'na')
CHECKLIST = {
    'pac': [
        {'key': 'pac_wcag', 'label': 'PAC 2026: WCAG Check', 'results': ('pass', 'fail'),
         'help': 'PAC 2026\'s WCAG check on this version of the PDF. Anything it fails that the report does not list is a gap in the automated checks.'},
        {'key': 'title_language', 'label': 'Title and Language', 'results': P3,
         'help': 'The title shown in the window is the book\'s title, and the document language is the book\'s main language.'},
        {'key': 'spot_check', 'label': 'Spot-Check of Pages', 'results': P3, 'pages': True,
         'help': 'A few pages compared with the original in PAC\'s structure preview: headings, lists, tables and figures as printed.'},
        {'key': 'colour', 'label': 'Colour Alone', 'results': P3,
         'help': 'No information is given by colour alone (WCAG 1.4.1).'},
        {'key': 'contrast', 'label': 'Contrast', 'results': P3,
         'help': 'Text over images and coloured backgrounds has enough contrast (WCAG 1.4.3; PAC\'s contrast checker).'},
        {'key': 'images_of_text', 'label': 'Images of Text', 'results': P3,
         'help': 'No images of text where real text could be used; on scanned pages the OCR text stands in (WCAG 1.4.5).'},
        {'key': 'needs_person', 'label': 'What Needs a Person', 'results': P3,
         'help': 'Every item the report lists under "For a Person to Check" was looked at.'},
    ],
    'screen_reader': [
        {'key': 'title_announced', 'label': 'Title Announced', 'results': P3,
         'help': 'The screen reader announces the book\'s title when the PDF opens.'},
        {'key': 'languages', 'label': 'Document Language and Passages in Other Languages', 'results': P3,
         'help': 'The text is read in the book\'s language, and passages in another language are pronounced in theirs (WCAG 3.1.1, 3.1.2).'},
        {'key': 'headings', 'label': 'Heading Navigation', 'results': P3,
         'help': 'Moving by heading reaches each part and chapter, at the right level (WCAG 1.3.1, 2.4.6).'},
        {'key': 'reading_order', 'label': 'Reading Order on Sample Pages', 'results': P3, 'pages': True,
         'help': 'On a few sample pages, the text is read in the order it is meant to be read (WCAG 1.3.2).'},
        {'key': 'alt_text', 'label': 'Figure Alt Text', 'results': P3, 'found': 'figures',
         'help': 'Each figure\'s alt text is read, is accurate and gives its purpose; decorative images are skipped (WCAG 1.1.1).'},
        {'key': 'tables', 'label': 'Tables Read with Their Headers', 'results': P3, 'found': 'tables',
         'help': 'Moving through a table, each cell is read with its row or column header (WCAG 1.3.1).'},
        {'key': 'links', 'label': 'Links Say Where They Go', 'results': P3, 'found': 'links',
         'help': 'Each link\'s text, or its description, says where it goes (WCAG 2.4.4).'},
        {'key': 'lists', 'label': 'Lists', 'results': P3, 'found': 'lists',
         'help': 'Lists are announced as lists, with their number of items.'},
        {'key': 'ocr_pages', 'label': 'OCR Pages Read Sensibly', 'results': P3, 'found': 'ocr_pages',
         'help': 'Pages whose text comes from OCR are read as words, not as junk characters.'},
        {'key': 'formulas', 'label': 'Formulas', 'results': P3, 'found': 'formulas',
         'help': 'Each formula is read with the description a person wrote, or is marked for one (math goes to a person).'},
    ],
}
FIELDS = {'pac': {},
          'screen_reader': {'screen_reader': ('Screen Reader and Version', True), 'pdf_reader': ('PDF Reader and Version', False)}}
# retired 2026-10-31 (decision 6): known to every reader, never offered, never counted; an older record shows them in its
# full results, labelled "(no longer asked)"
RETIRED = {'pac': {'items': {'pac_pdfua': {'key': 'pac_pdfua', 'label': 'PAC 2026: PDF/UA Check', 'results': ('pass', 'fail', 'not_run')}},
                   'fields': {'pac_version': 'PAC Version'}},
           'screen_reader': {'items': {}, 'fields': {}}}
SECTION_NAMES = {'pac': 'PAC 2026', 'screen_reader': 'Screen-Reader Test'}
RESULT_NAMES = {'pass': 'Pass', 'fail': 'Fail', 'na': 'Not Applicable', 'not_run': 'Not Run'}
SPEC = {s: {x['key']: x for x in items} for s, items in CHECKLIST.items()}

# ------------------------------------------------------------------ reading
def _json(p, default):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return default

def paths(R):
    d = os.path.join(R, 'release')
    return {'dir': d, 'checks': os.path.join(d, 'checks.json'), 'shipped': os.path.join(d, 'shipped.json')}

def run_dir_of(R):
    """The run folder whose release/ applies: R itself, or for a previous result (R/reviews/versions/<id>/) its run."""
    R = os.path.abspath(R); up = os.path.dirname(R)
    if os.path.basename(up) == 'versions' and os.path.basename(os.path.dirname(up)) == 'reviews': return os.path.dirname(os.path.dirname(up))
    return R

def empty(): return {'checks': {'schema': SCHEMA, 'pac': [], 'screen_reader': []}, 'shipped': []}

def load(R, rec=None):
    """The run's release/ records; a run with none (every run made before 2026-11) has no checks and no shipments. With
    the record (rec), also `newer`: the ids of the newest finished and open sessions newer than its result
    (review/sessions.py newer(), the one rule), for the status's "Newer version" line."""
    if not R: return empty()
    p = paths(R)
    checks = _json(p['checks'], None) or empty()['checks']
    if checks.get('schema') not in READ_SCHEMAS: raise ValueError(f'{p["checks"]}: schema {checks.get("schema")!r} is not one this version reads')
    for s in SECTIONS: checks.setdefault(s, [])
    out = {'checks': checks, 'shipped': _json(p['shipped'], []) or []}
    if rec is not None:
        from review import sessions as S
        out['newer'] = {k: (v or {}).get('id') for k, v in S.newer(R, rec).items()}
    return out

def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def sha_of(x): return ((x or {}).get('pdf') or {}).get('sha256')
def day(iso): return D.day(iso)

def issues(check, section):
    """The keys of the current checklist's items recorded as Fail (also for a result that cannot be read in full)."""
    items = (check or {}).get('items') or {}
    return [x['key'] for x in CHECKLIST[section] if isinstance(items.get(x['key']), dict) and items[x['key']].get('result') == 'fail']

def complete(check, section):
    """True when every item the checklist asks has one of that item's own choices, and no item is unknown (retired ones
    are known): fail closed, so anything else is "could not be read in full", never completed."""
    items = (check or {}).get('items') or {}
    for x in CHECKLIST[section]:
        it = items.get(x['key'])
        if not (isinstance(it, dict) and it.get('result') in x['results']): return False
    return all(k in SPEC[section] or k in RETIRED[section]['items'] for k in items)

def label(section, key): return (SPEC[section].get(key) or RETIRED[section]['items'].get(key) or {}).get('label') or key

def latest(rel, section, sha):
    """The latest result of a part on the file with this hash (the one that counts for it), or None."""
    if not sha: return None
    return next((c for c in reversed(rel['checks'].get(section) or []) if sha_of(c) == sha), None)

def live_shipments(rel): return [s for s in rel.get('shipped') or [] if not s.get('withdrawn')]

def _session(c):
    s = ((c or {}).get('pdf') or {}).get('session')
    return f'Session {int(s)}' if str(s).isdigit() else None

def part(rel, section, sha):
    """One part on the file with this hash: {state: completed | could not be read | earlier version | not recorded,
    check (the latest on this file, else the latest made on the current version of an earlier file), issues, n_items}."""
    c = latest(rel, section, sha)
    if c is not None:
        return {'state': 'completed' if complete(c, section) else 'could not be read', 'check': c, 'issues': issues(c, section),
                'n_items': sum(1 for k, it in (c.get('items') or {}).items() if k in SPEC[section] and isinstance(it, dict) and it.get('result'))}
    older = [x for x in rel['checks'].get(section) or [] if (x.get('pdf') or {}).get('which', 'current') == 'current']
    if older: return {'state': 'earlier version', 'check': older[-1], 'issues': [], 'n_items': 0}
    return {'state': 'not recorded', 'check': None, 'issues': [], 'n_items': 0}

def evaluation(rel, sha):
    """Both parts on the file with this hash: {pac, screen_reader (each part()), complete, issues (the Fails counted)}."""
    out = {s: part(rel, s, sha) for s in SECTIONS}
    out['complete'] = all(out[s]['state'] == 'completed' for s in SECTIONS)
    out['issues'] = sum(len(out[s]['issues']) for s in SECTIONS)
    return out

def noted(n): return f'{n} issue{"" if n == 1 else "s"} noted'

def evaluation_line(rel, cur):
    """(ok, text) for "Ready to Ship?"'s "Accessibility Evaluation" line: Completed, with the issues noted, or Not Completed
    with what is missing (13 §5.1)."""
    ev = evaluation(rel, cur)
    if ev['complete']: return True, 'Completed' + (f' ({noted(ev["issues"])})' if ev['issues'] else '')
    missing = []
    for s in SECTIONS:
        p = ev[s]; name = SECTION_NAMES[s]
        if p['state'] == 'not recorded': missing.append((s, 'not recorded'))
        elif p['state'] == 'earlier version':
            ses = _session(p['check'])
            missing.append((s, 'recorded on an earlier version' + (f', {ses}' if ses else '')))
        elif p['state'] == 'could not be read': missing.append((s, 'could not be read in full: record it again'))
    if len(missing) == 2 and all(w == 'not recorded' for _, w in missing): why = 'neither part recorded for this version'
    else: why = '; '.join(f'{SECTION_NAMES[s]}: {w}' for s, w in missing)
    return False, f'Not Completed ({why}' + (f'; {noted(ev["issues"])}' if ev['issues'] else '') + ')'

NOT_READY, PENDING, READY, SHIPPED = 'Not Ready', 'Pending Evaluation', 'Ready', 'Shipped'

def pre_status(rel, sha, base_ok):
    """(name, issues) for a version before shipping: Not Ready (a base requirement unsatisfied), Pending Evaluation (the
    evaluation not completed) or Ready."""
    ev = evaluation(rel, sha)
    return (NOT_READY if not base_ok else READY if ev['complete'] else PENDING), ev['issues']

def with_issues(name, n): return name + (f' · {noted(n)}' if n else '')

def status(rel, cur, base_ok, newer=None, session=None):
    """{name, text, newer, shipment, issues}. Before any shipment: the current version's Not Ready, Pending Evaluation or
    Ready (base_ok: the work order, the OCR text and the safety checks satisfied). Once a version has shipped (and is not
    withdrawn), the status is about the shipped copy: Shipped, with the issues noted on that file. After a shipment, the
    `newer` line names what comes next: a session finished and not applied, else one being reviewed (`newer`:
    {'finished': id, 'open': id}, from sessions.newer()), else, when the current file is not the shipped one, the current
    version's own status (`session`: its session). "· N issues noted" follows any status whose version has Fails.
    `current` is always the current version's own status, {name, issues} (pre_status), before and after any shipment:
    stage 4's Mark as Shipped is gated on current['name'] == 'Ready' (with the disk hash in the app), never on
    glance.ready, which is False after any shipment (review 16 J1)."""
    ships = live_shipments(rel)
    cname, cn = pre_status(rel, cur, base_ok)
    current = {'name': cname, 'issues': cn}
    if not ships:
        return {'name': cname, 'text': with_issues(cname, cn), 'newer': None, 'shipment': None, 'issues': cn, 'current': current}
    s = ships[-1]; ssha = sha_of(s)
    n = evaluation(rel, ssha)['issues']
    nw = newer or {}; line = None
    if str(nw.get('finished') or '').isdigit(): line = f'Newer version: Session {int(nw["finished"])} finished, not applied'
    elif str(nw.get('open') or '').isdigit(): line = f'Newer version: Session {int(nw["open"])} being reviewed'
    elif ssha != cur:
        line = (f'Newer version (Session {int(session)})' if str(session or '').isdigit() else 'Newer version') + f': {with_issues(cname, cn)}'
    return {'name': SHIPPED, 'text': with_issues(SHIPPED, n), 'newer': line, 'shipment': s.get('n'), 'issues': n, 'current': current}

def state(rel, section, c, cur):
    """A result's state, worked out now: completed / could not be read (on this version) or earlier version."""
    if sha_of(c) != cur: return 'earlier version'
    return 'completed' if complete(c, section) else 'could not be read'

def mirror(rel, cur):
    """record.json's copy for the archive (never read back for a decision): the latest result of each part with its
    state and issues, and the shipments."""
    out = {'schema': rel['checks'].get('schema', SCHEMA)}
    for s in SECTIONS:
        xs = rel['checks'].get(s) or []
        c = latest(rel, s, cur) or (xs[-1] if xs else None)
        out[s] = dict(c, state=state(rel, s, c, cur), issues=len(issues(c, s))) if c else None
        out[s + '_count'] = len(xs)
    return out, {'shipped': rel.get('shipped') or []}

# ------------------------------------------------------------------ removed PDFs ("Remove Older PDFs", review/prune.py)
def removed(R):
    """release/removed.json: the earlier versions whose PDF "Remove Older PDFs" took, [{version, sha256, bytes, by, removed}]."""
    return _json(os.path.join(run_dir_of(R), 'release', 'removed.json'), []) or []

# ------------------------------------------------------------------ download names (stage 3)
BASE_BYTES = 150                                            # a file name is at most 255 bytes on macOS and Linux (K2)
_RESERVED = re.compile(r'[<>:"/\\|?*;]')
STATE_WORDS = {NOT_READY: 'not-ready', PENDING: 'not-ready', READY: 'not-shipped'}

def clean_base(output):
    r"""The remediated PDF's name without ".pdf", safe for any computer the file goes to (03 §3.6, review 18 K2): NFC; control
    characters dropped; < > : " / \ | ? * ; replaced by _; no leading or trailing dot or space (a leading dot hides the
    file); at most 150 UTF-8 bytes, cut on a character boundary."""
    import unicodedata
    s = unicodedata.normalize('NFC', str(output or '')).strip(' .')
    if s.lower().endswith('.pdf'): s = s[:-4]
    s = ''.join(c for c in s if unicodedata.category(c)[0] != 'C')
    s = _RESERVED.sub('_', s).strip(' .')
    b = s.encode('utf-8')[:BASE_BYTES]
    s = b.decode('utf-8', 'ignore').strip(' .')
    return s or 'book'

def download_names(output, session, state, shipment=None):
    """(pdf name, zip name) for one version. session: its number (never a session's name), None for a result applied
    without review; state: Not Ready, Pending Evaluation, Ready, Shipped (the shipped copy: the plain name) or
    'earlier version'. A version with no session is never Ready (its work order was not approved), so there is no
    "_no-review_not-shipped" (K4)."""
    base = clean_base(output)
    if state == SHIPPED:
        return f'{base}.pdf', f'{base}_record_shipment-{int(shipment)}.zip' if str(shipment or '').isdigit() else f'{base}_record.zip'
    sess = f'session-{int(session)}' if str(session or '').isdigit() else 'no-review'
    word = 'earlier-version' if state == 'earlier version' else STATE_WORDS.get(state, 'not-ready')
    return f'{base}_{sess}_{word}.pdf', f'{base}_record_{sess}_{word}.zip'

def disposition(name):
    """Content-Disposition for a saved name (RFC 6266 / 5987): an ASCII fallback and the UTF-8 name."""
    import urllib.parse
    ascii_ = ''.join(c if 32 <= ord(c) < 127 and c not in '"\\' else '_' for c in name)
    return f'attachment; filename="{ascii_}"; filename*=UTF-8\'\'{urllib.parse.quote(name, safe="")}'

# ------------------------------------------------------------------ review.md's "Accessibility Evaluation" section
EVAL_HEADINGS = ('accessibility evaluation', 'final check with pac 2026')   # this section's headings, new and older (any case)
EVAL_ANCHORS = ('accessibility-evaluation', 'final-check-with-pac-2026')
_MD_INLINE = re.compile(r'([\\`*_\[\]<>])')
_MD_BLOCK = re.compile(r'^(\s*)(?:([#>+\-*=])|(\d+)([.)]))')

def md_text(s):
    """A person's one-line text in Markdown, read as typed (| and ]( are already refused when it is recorded)."""
    return _MD_INLINE.sub(r'\\\1', str(s or ''))

def md_quote(s):
    """A person's multi-line text as a blockquote: every line escaped, its start too, so no line can begin a heading, list
    or section (a line "## x" would otherwise end the section early or split it)."""
    def esc(m): return m.group(1) + ('\\' + m.group(2) if m.group(2) else m.group(3) + '\\' + m.group(4))   # "1\." (a digit escapes nothing)
    return ['> ' + _MD_BLOCK.sub(esc, md_text(l)) if l.strip() else '>' for l in str(s or '').split('\n')]

def any_recorded(rel): return any(rel['checks'].get(s) for s in SECTIONS)

def _part_md(rel, section, cur):
    p = part(rel, section, cur); c = p['check']; name = SECTION_NAMES[section]
    if p['state'] == 'not recorded': return None
    ses = _session(c)
    head = {'completed': f'Completed by {c.get("by")} on {day(c.get("recorded"))} · {p["n_items"]} items'
                         + (f' · {noted(len(p["issues"]))}' if p['issues'] else ''),
            'could not be read': f'Recorded by {c.get("by")} on {day(c.get("recorded"))}, but it could not be read in full: record it again',
            'earlier version': f'Completed on an earlier version{" (" + ses + ")" if ses else ""} by {c.get("by")} on {day(c.get("recorded"))}: '
                               'it does not count for this version'}[p['state']]
    L = [f'**{name}: {md_text(head)}**' + (f' (the version from {ses})' if ses and p['state'] != 'earlier version' else ''), '']
    f = c.get('fields') or {}
    bits = [f'Checked by {md_text(c.get("by"))}'] + [f'{lab}: {md_text(f[k])}' for k, (lab, _) in FIELDS[section].items() if f.get(k)] \
        + [f'{lab} (no longer asked): {md_text(f[k])}' for k, lab in RETIRED[section]['fields'].items() if f.get(k)] \
        + ([f'Pages checked: {md_text(f["pages_checked"])}'] if f.get('pages_checked') else [])
    L += [' · '.join(bits), '', '| Item | Result | Notes |', '|---|---|---|']
    items = c.get('items') or {}
    for x in CHECKLIST[section] + list(RETIRED[section]['items'].values()):
        if x['key'] in RETIRED[section]['items'] and x['key'] not in items: continue
        it = items.get(x['key']) or {}
        lab = x['label'] + (' (no longer asked)' if x['key'] in RETIRED[section]['items'] else '')
        L.append(f'| {lab} | {RESULT_NAMES.get(it.get("result"), "Not answered")} | {md_text(it.get("note"))} |')
    if c.get('notes'): L += ['', 'Other notes:', ''] + md_quote(c['notes'])
    n = len(rel['checks'].get(section) or []) - 1
    if n > 0: L += ['', f'{n} earlier result{"" if n == 1 else "s"} kept in the record (`release/checks.json`).']
    return L

def section_md(rel, cur, pdf):
    """review.md's "## Accessibility Evaluation" section: how to do it, and each part's latest result in full once one is
    recorded (13 §7.2). pdf: the remediated PDF's file name."""
    def items(section): return [f'- {x["label"]}: {x["help"]}' for x in CHECKLIST[section]]
    L = ['## Accessibility Evaluation', '',
         f'A person evaluates this version of `{pdf}` with PAC 2026 and a screen reader, on the app\'s "Accessibility Evaluation" page '
         '(or with manual_checks.py; docs/release.md). Both parts are needed for "Ready to ship?". A Fail is recorded with its note and '
         'does not hold the book back. Each result is recorded against this version of the PDF (its sha256): after a new apply it no '
         'longer counts. The evaluation is a record of what a person found, not a legal certification.', '']
    pac = _part_md(rel, 'pac', cur)
    L += pac + [''] if pac else [
        f'**PAC 2026.** Open `{pdf}` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it '
        'fails that is not listed above is a gap in the automated checks: note it in the issue tracker. Each item is Pass, Fail or '
        'Not Applicable, with notes:', ''] + items('pac') + ['']
    sr = _part_md(rel, 'screen_reader', cur)
    L += sr if sr else ['**Screen-reader test.** Listen with a screen reader and record which one and its version:', ''] + items('screen_reader')
    return L

def replace_section_md(md, lines):
    """review.md's text (a run made before `sections`) with its evaluation section (either heading, any case) replaced by
    `lines`, up to the next "## " heading or the end; appended at the end when it has none."""
    L = md.split('\n')
    i = next((k for k, l in enumerate(L) if l.startswith('## ') and l[3:].strip().lower() in EVAL_HEADINGS), None)
    if i is None:
        while L and L[-1] == '': L.pop()
        return '\n'.join(L + [''] + lines + [''])
    j = next((k for k in range(i + 1, len(L)) if L[k].startswith('## ')), len(L))
    tail = L[j:] if j < len(L) else ['']
    return '\n'.join(L[:i] + lines + ([''] if j < len(L) else []) + tail)

# ------------------------------------------------------------------ what the pipeline found (Not Applicable needs a note)
def found(record):
    """{item key: what was found, in words} from record.json: an item the pipeline found something for needs a note to be
    Not Applicable."""
    record = record or {}
    types = (((record.get('verify') or {}).get('tree') or {}).get('types') or {})
    ocr = ((record.get('intake') or {}).get('ocr') or {}).get('pages_with_ocr_text') or []
    out = {}
    def n(k, one, many):
        c = types.get(k) or 0
        if c: return f'{c:,} {one if c == 1 else many}'
    for key, k, one, many in (('figures', 'Figure', 'figure', 'figures'), ('tables', 'Table', 'table', 'tables'),   # keyed as CHECKLIST's `found`
                              ('links', 'Link', 'link', 'links'), ('lists', 'L', 'list', 'lists'), ('formulas', 'Formula', 'formula', 'formulas')):
        t = n(k, one, many)
        if t: out[key] = t
    if ocr: out['ocr_pages'] = f'OCR text on {len(ocr):,} page{"" if len(ocr) == 1 else "s"}'
    return out

# ------------------------------------------------------------------ checking a check before it is recorded
class Invalid(ValueError):
    """Every problem with a check, each tied to its field: [(field, message)] in `errors`."""
    def __init__(self, errors):
        self.errors = errors
        super().__init__(' '.join(m for _, m in errors))

def _clean(s, one_line):
    from review.core import clean_text
    return clean_text(s, one_line=one_line)

def _text(errors, field, name, s, limit, required=False, one_line=True, msg=None):
    s = _clean(s, one_line)
    if required and not s: errors.append((field, msg or f'Enter "{name}".')); return None
    if len(s) > limit: errors.append((field, f'"{name}" is too long: {len(s):,} characters, at most {limit:,}.'))
    elif '|' in s: errors.append((field, f'"{name}" can\'t contain the character "|". Use another one, such as a comma or a slash.'))
    elif '](' in s: errors.append((field, f'"{name}" can\'t contain "](" (a closing square bracket right before an opening parenthesis). Put a space between them.'))
    return s or None

def validate(section, data, ctx=None):
    """The check as it will be recorded (by, fields, items, notes), or Invalid with every problem. ctx: n_pages (the
    book's PDF pages), found (found(record)), previous (the latest check of this section on the same file, if any)."""
    if section not in SECTIONS: raise Invalid([('section', f'unknown section {section!r}')])
    ctx = ctx or {}; data = data if isinstance(data, dict) else {}
    errors = []; spec = SPEC[section]; fnd = ctx.get('found') or {}; prev = ctx.get('previous')
    by = _text(errors, 'by', 'Checked By', data.get('by'), NAME_MAX, True, msg='Enter your name in "Checked By".')
    fields_in = data.get('fields') if isinstance(data.get('fields'), dict) else {}
    fields = {}
    for k, (name, req) in FIELDS[section].items():
        v = _text(errors, f'fields.{k}', name, fields_in.get(k), FIELD_MAX, req)
        if v: fields[k] = v
    for k in fields_in:
        if k not in FIELDS[section] and k != 'pages_checked': errors.append((f'fields.{k}', f'unknown field {k!r}'))
    items_in = data.get('items') if isinstance(data.get('items'), dict) else {}
    for k in items_in:
        if k not in spec: errors.append((f'items.{k}', f'unknown item {k!r}'))
    items = {}
    prev_bad = set(issues(prev, section)) if prev else set()    # a Pass after a Fail on the same file still needs a note (S3)
    for x in CHECKLIST[section]:
        k, name = x['key'], x['label']
        it = items_in.get(k) if isinstance(items_in.get(k), dict) else {}
        res = it.get('result')
        note = _text(errors, f'items.{k}.note', f'{name}: Notes', it.get('note'), NOTE_MAX, one_line=True)
        if res in (None, ''):
            choices = ' or '.join(f'"{RESULT_NAMES[r]}"' for r in x['results'])
            errors.append((f'items.{k}.result', f'Choose {choices.replace(" or ", ", ", len(x["results"]) - 2)} for "{name}".')); continue
        if res not in x['results']:
            errors.append((f'items.{k}.result', f'"{name}" can\'t be "{RESULT_NAMES.get(res, res)}".')); continue
        if res == 'fail' and not note:
            errors.append((f'items.{k}.note', f'Add a note to "{name}": a failed item needs one.'))
        elif res == 'na' and x.get('found') in fnd and not note:
            errors.append((f'items.{k}.note', f'Add a note to "{name}": this book has {fnd[x["found"]]}, so say why it does not apply.'))
        elif res == 'pass' and k in prev_bad and not note:
            errors.append((f'items.{k}.note', f'Add a note to "{name}": it failed in the last results recorded for this version, so say what changed.'))
        items[k] = {'result': res, **({'note': note} if note else {})}
    pg = _clean(fields_in.get('pages_checked'), True)
    if pg:                                                       # optional (2026-10-31); checked when given
        pname = 'Pages Checked'; n = ctx.get('n_pages') or 10 ** 6
        if len(pg) > FIELD_MAX: errors.append(('fields.pages_checked', f'"{pname}" is too long: {len(pg):,} characters, at most {FIELD_MAX:,}.'))   # J6
        elif not PAGES.fullmatch(pg): errors.append(('fields.pages_checked', f'"{pname}": give PDF page numbers and ranges, for example 5, 9-12.'))
        else:
            for piece in pg.split(','):
                a, _, b = piece.strip().partition('-'); a, b = int(a), int(b or a)
                if not 1 <= a <= b <= n:
                    errors.append(('fields.pages_checked', f'"{pname}" {piece.strip()}: ' + ('a range goes from the lower page to the higher one, for example 5-9.' if a > b else f'this book has PDF pages 1 to {n:,}.'))); break
            else: fields['pages_checked'] = pg
    notes = _text(errors, 'notes', 'Other Notes', data.get('notes'), NOTES_MAX, one_line=False)
    if errors: raise Invalid(errors)
    return {'by': by, 'fields': fields, 'items': items, **({'notes': notes} if notes else {})}

def clean_draft(section, data):
    """A half-filled check as a draft keeps it: cleaned and limited as validate() limits a check, no field required, a
    result kept only when it is one the item offers. Raises Invalid with the fields over the limits."""
    if section not in SECTIONS: raise Invalid([('section', f'unknown section {section!r}')])
    data = data if isinstance(data, dict) else {}
    errors = []; spec = SPEC[section]
    out = {'by': _text(errors, 'by', 'Checked By', data.get('by'), NAME_MAX) or ''}
    fin = data.get('fields') if isinstance(data.get('fields'), dict) else {}
    out['fields'] = {k: _text(errors, f'fields.{k}', name, fin.get(k), FIELD_MAX) or '' for k, (name, _) in FIELDS[section].items()}
    if any(x.get('pages') for x in CHECKLIST[section]): out['fields']['pages_checked'] = _text(errors, 'fields.pages_checked', 'Pages Checked', fin.get('pages_checked'), FIELD_MAX) or ''
    iin = data.get('items') if isinstance(data.get('items'), dict) else {}
    out['items'] = {}
    for k, x in spec.items():
        it = iin.get(k) if isinstance(iin.get(k), dict) else {}
        res = it.get('result') if it.get('result') in x['results'] else ''
        out['items'][k] = {'result': res, 'note': _text(errors, f'items.{k}.note', f'{x["label"]}: Notes', it.get('note'), NOTE_MAX) or ''}
    out['notes'] = _text(errors, 'notes', 'Other Notes', data.get('notes'), NOTES_MAX, one_line=False) or ''
    if errors: raise Invalid(errors)
    return out
