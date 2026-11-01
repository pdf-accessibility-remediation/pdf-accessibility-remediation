"""lib/release.py: the manual checks (PAC 2026 and sanity checks, the screen-reader check), shipments and the book's
status, with no web server and no writing (review/manual.py writes; issue #38).

    rel = load(R)                                  # release/checks.json and release/shipped.json, empty when absent
    pac = pac_line(rel, cur_sha)                   # (ok, text): "Ready to Ship?"'s "Manual check (PAC)" line
    sr  = sr_line(rel, cur_sha)                    # (False, text) when the current version's screen-reader check failed, else None
    st  = status(rel, cur_sha, ready, newer, session)     # {name, text, newer}: Not Ready, Ready, Shipped, Verified, Needs Rework
    rec = validate(section, data, ctx)             # a check as it will be recorded; raises Invalid with every problem

Every check and shipment records the sha256 of the remediated PDF it was made on (`pdf.sha256`). A check counts only for
the file with that hash: `cur_sha` is the record's `document.output_sha256` (offline dashboards) or the hash the app read
from disk. Nothing here relies on an apply giving new bytes.

The records (release/checks.json, schema manual-checks/1; /2 is reserved for "Fail, Accepted with a Note"):
    {schema, pac: [check …], screen_reader: [check …]}            newest last; nothing is deleted
    check: {id, recorded, by, via, code, pdf: {sha256, file, session, which, shipment}, fields, items: {key: {result, note}}, notes}
`result` is only what the person saw: pass | fail | na (not_run for the PDF/UA item). A later `accepted: {by, date, note}`
on a failed item is reserved. v1 reads fail closed: a blocking item is OK only when its result is pass or na and it has
no `accepted`; any other value counts as Fail. `state`, `ok`, "counts for this version" and "checked before shipping"
are worked out on every read, never trusted from storage.
release/shipped.json: [{n, shipped, by, pdf: {sha256, file, session}, where, note, withdrawn?: {by, date, reason}}]
"""
import os, re, json, hashlib

SCHEMA = 'manual-checks/1'
READ_SCHEMAS = ('manual-checks/1', 'manual-checks/2')
SECTIONS = ('pac', 'screen_reader')
OK_RESULTS = ('pass', 'na')
NAME_MAX, FIELD_MAX, NOTE_MAX, NOTES_MAX = 80, 80, 1000, 4000
PAGES = re.compile(r'\d+(-\d+)?(, ?\d+(-\d+)?)*')

# The checklist, once: the Manual Checks page, manual_checks.py, review.md's PAC section and the disclosure read it.
# results: the choices; blocking: a Fail keeps the line closed; pages: asks for the pages checked (fields.pages_checked);
# found: the thing the pipeline counted (Not Applicable then needs a note).
P3 = ('pass', 'fail', 'na')
CHECKLIST = {
    'pac': [
        {'key': 'pac_wcag', 'label': 'PAC 2026: WCAG Check', 'results': ('pass', 'fail'),
         'help': 'PAC 2026\'s WCAG check on this version of the PDF. Anything it fails that the report does not list is a gap in the automated checks.'},
        {'key': 'pac_pdfua', 'label': 'PAC 2026: PDF/UA Check', 'results': ('pass', 'fail', 'not_run'), 'blocking': False, 'optional': True,
         'help': 'PAC 2026\'s PDF/UA check, recorded for the record. It does not decide "Ready to ship?".'},
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
         'help': 'On the pages listed, the text is read in the order it is meant to be read (WCAG 1.3.2).'},
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
FIELDS = {'pac': {'pac_version': ('PAC Version', False)},
          'screen_reader': {'screen_reader': ('Screen Reader and Version', True), 'pdf_reader': ('PDF Reader and Version', False)}}
SECTION_NAMES = {'pac': 'PAC 2026 and Sanity Checks', 'screen_reader': 'Screen-Reader Check'}
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
def day(iso): return str(iso or '')[:10] or 'date not recorded'

def failed(check, section):
    """The blocking items of a check that are not OK, read fail closed: a missing blocking item, a result other than pass
    or na, an `accepted` (not built in v1), or an item this version does not know whose result is not pass or na."""
    items = (check or {}).get('items') or {}
    bad = []
    for spec in CHECKLIST[section]:
        if spec.get('blocking', True) is False: continue
        it = items.get(spec['key'])
        if not (isinstance(it, dict) and it.get('result') in OK_RESULTS and 'accepted' not in it): bad.append(spec['key'])
    bad += [k for k, it in items.items() if k not in SPEC[section] and not (isinstance(it, dict) and it.get('result') in OK_RESULTS and 'accepted' not in it)]
    return bad

def label(section, key): return (SPEC[section].get(key) or {}).get('label') or key

def latest(rel, section, sha):
    """The latest check of a section on the file with this hash (the one that counts for it), or None."""
    if not sha: return None
    return next((c for c in reversed(rel['checks'].get(section) or []) if sha_of(c) == sha), None)

def live_shipments(rel): return [s for s in rel.get('shipped') or [] if not s.get('withdrawn')]

def _session(c):
    s = ((c or {}).get('pdf') or {}).get('session')
    return f'Session {int(s)}' if str(s).isdigit() else None

def _failed_text(c, section):
    bad = failed(c, section)
    return len(bad), ', '.join(label(section, k) for k in bad)

def pac_line(rel, cur):
    """(ok, text) for "Manual check (PAC)": done on this version with no Fail."""
    c = latest(rel, 'pac', cur)
    if c is not None:
        n, names = _failed_text(c, 'pac')
        if n: return False, f'no ({n} item{"" if n == 1 else "s"} failed: {names}; {c.get("by")} on {day(c.get("recorded"))})'
        return True, f'yes ({c.get("by")} on {day(c.get("recorded"))})'
    older = [c for c in rel['checks'].get('pac') or [] if (c.get('pdf') or {}).get('which', 'current') == 'current']
    if older:
        c = older[-1]; s = _session(c)
        return False, f'no (done on an earlier version{", " + s + "," if s else ""} by {c.get("by")} on {day(c.get("recorded"))}; check this version)'
    return False, 'no (not done for this version)'

def sr_line(rel, cur):
    """(False, text) when the latest screen-reader check of the current version failed an item; None otherwise (a
    version never listened to is not held back)."""
    c = latest(rel, 'screen_reader', cur)
    if c is None: return None
    n, names = _failed_text(c, 'screen_reader')
    if not n: return None
    return False, f'no ({n} item{"" if n == 1 else "s"} failed on this version: {names}; {c.get("by")} on {day(c.get("recorded"))})'

NOT_READY, READY, SHIPPED, VERIFIED, NEEDS_REWORK = 'Not Ready', 'Ready', 'Shipped', 'Verified', 'Needs Rework'

def status(rel, cur, ready, newer=None, session=None):
    """{name, text, newer, shipment}. Before any shipment: the current version's Not Ready or Ready. Once a version has
    shipped (and is not withdrawn), the status is about the shipped copy: Shipped, Verified (its latest completed
    screen-reader check has no Fail; "checked before shipping" when that check is older than the shipment, worked out
    here, never stored) or Needs Rework (a Fail). After a shipment, the result's `newer` line names what comes next: a
    session finished and not applied, else one being reviewed (`newer`: {'finished': id, 'open': id}, from
    sessions.newer()), else, when the current file is not the shipped one, whether it is ready to ship (`session`: the
    current version's session)."""
    ships = live_shipments(rel)
    if not ships:
        n = READY if ready else NOT_READY
        return {'name': n, 'text': n, 'newer': None, 'shipment': None}
    s = ships[-1]; ssha = sha_of(s)
    c = latest(rel, 'screen_reader', ssha)
    if c is None: name = text = SHIPPED
    elif failed(c, 'screen_reader'): name = text = NEEDS_REWORK
    else:
        name = VERIFIED
        text = f'{VERIFIED} (checked before shipping, {day(c.get("recorded"))})' if str(c.get('recorded') or '') < str(s.get('shipped') or '') else VERIFIED
    n = newer or {}; line = None
    if str(n.get('finished') or '').isdigit(): line = f'Newer version: Session {int(n["finished"])} finished, not applied'
    elif str(n.get('open') or '').isdigit(): line = f'Newer version: Session {int(n["open"])} being reviewed'
    elif ssha != cur: line = (f'Newer version (Session {int(session)})' if str(session or '').isdigit() else 'Newer version') + f': Ready to Ship? {"Yes" if ready else "No"}'
    return {'name': name, 'text': text, 'newer': line, 'shipment': s.get('n')}

def state(rel, section, c, cur):
    """A check's state, worked out now: counts / failed (on this version) or earlier version."""
    if sha_of(c) != cur: return 'earlier version'
    return 'failed' if failed(c, section) else 'counts'

def mirror(rel, cur):
    """record.json's copy for the archive (never read back for a decision): the latest check of each section with its
    state, and the shipments."""
    out = {'schema': rel['checks'].get('schema', SCHEMA)}
    for s in SECTIONS:
        xs = rel['checks'].get(s) or []
        c = latest(rel, s, cur) or (xs[-1] if xs else None)
        out[s] = dict(c, state=state(rel, s, c, cur)) if c else None
        out[s + '_count'] = len(xs)
    return out, {'shipped': rel.get('shipped') or []}

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
    items = {}; need_pages = False
    prev_bad = set(failed(prev, section)) if prev else set()
    for x in CHECKLIST[section]:
        k, name = x['key'], x['label']
        it = items_in.get(k) if isinstance(items_in.get(k), dict) else {}
        res = it.get('result')
        note = _text(errors, f'items.{k}.note', f'{name}: Notes', it.get('note'), NOTE_MAX, one_line=True)
        if res in (None, ''):
            if x.get('optional'):
                if note: items[k] = {'note': note}
                continue
            choices = ' or '.join(f'"{RESULT_NAMES[r]}"' for r in x['results'])
            errors.append((f'items.{k}.result', f'Choose {choices.replace(" or ", ", ", len(x["results"]) - 2)} for "{name}".')); continue
        if res not in x['results']:
            errors.append((f'items.{k}.result', f'"{name}" can\'t be "{RESULT_NAMES.get(res, res)}".')); continue
        if res == 'fail' and not note:
            errors.append((f'items.{k}.note', f'Add a note to "{name}": a failed item needs one.'))
        elif res == 'na' and x.get('found') in fnd and not note:
            errors.append((f'items.{k}.note', f'Add a note to "{name}": this book has {fnd[x["found"]]}, so say why it does not apply.'))
        elif res == 'pass' and k in prev_bad and not note:
            errors.append((f'items.{k}.note', f'Add a note to "{name}": it failed in the last check of this version, so say what changed.'))
        if x.get('pages') and res in ('pass', 'fail'): need_pages = True
        items[k] = {'result': res, **({'note': note} if note else {})}
    pg = _clean(fields_in.get('pages_checked'), True)
    if need_pages or pg:
        pname = 'Pages Checked'; n = ctx.get('n_pages') or 10 ** 6
        if not pg: errors.append(('fields.pages_checked', f'Enter the pages you checked in "{pname}", for example 5, 9-12.'))
        elif not PAGES.fullmatch(pg): errors.append(('fields.pages_checked', f'"{pname}": give PDF page numbers and ranges, for example 5, 9-12.'))
        else:
            for part in pg.split(','):
                a, _, b = part.strip().partition('-'); a, b = int(a), int(b or a)
                if not 1 <= a <= b <= n:
                    errors.append(('fields.pages_checked', f'"{pname}" {part.strip()}: ' + ('a range goes from the lower page to the higher one, for example 5-9.' if a > b else f'this book has PDF pages 1 to {n:,}.'))); break
            else: fields['pages_checked'] = pg
    notes = _text(errors, 'notes', 'Other Notes', data.get('notes'), NOTES_MAX, one_line=False)
    if errors: raise Invalid(errors)
    return {'by': by, 'fields': fields, 'items': items, **({'notes': notes} if notes else {})}
