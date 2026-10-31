"""review/ocr.py: a person's verdict on a book's OCR text (sponsor checklist rule 2), and what the review page shows of
that text. No model, nothing sent, and the OCR text itself is never changed (checklist note 3.1).

    needed(intake)                      the gate's condition: intake added OCR text, or flagged the existing OCR layer
    check(fields, intake, pages)        a verdict as it will be recorded; raises ValueError with what is wrong
    record(R, fields, via, held=False)  writes it: the one writer for the review page and review_ocr.py
    section(R)                          the page's OCR Text section: the pages, intake's findings, the verdicts
    Text(pdf)                           a page's text, read once with pdfplumber (the PDF the run worked on)

Three verdicts: "approved" (passes the gate; for pages in a non-Latin script the reviewer must say they read the
language: `reads`), "not approved", and "sent to a language reader" (the gate stays closed; Ready to ship and What needs
a person say "waiting for a language reader"; `to` names who). One verdict per run, the latest wins; earlier ones go to
`history`.

What record() writes, each file whole (a temp file and os.replace): _intake/intake.json, _intake/intake.md, and for a
finished run record.json, review.md (the OCR row and the Overview) and review.html. Two locks: a flock on
_intake/.verdict.lock in every mode (the page and a terminal never interleave), and for a finished run reviews/.lock,
which the caller holds already (held=True: the review page's process) or record() takes (review_ocr.py from a terminal,
refused while a review page is open or an apply runs).
"""
import os, re, sys, json, fcntl, datetime, contextlib, threading
from . import core
from lib.glance import ocr_review_needed as needed, ocr_layer_flagged, ocr_layer_finding, ocr_verdict_row, OCR_ROW, SENT  # noqa: F401

APPROVED, NOT_APPROVED = 'approved', 'not approved'
VERDICTS = (APPROVED, NOT_APPROVED, SENT)
WHO_MAX, REASON_MAX, TO_MAX, READS_MAX = 80, 1000, 120, 80
PAGES = re.compile(r'\d+(-\d+)?(, ?\d+(-\d+)?)*')

# ------------------------------------------------------------------ languages (never guessed: OCR_LANG or the script itself)
NAMES = {'chi_tra': 'Chinese (Traditional)', 'chi_sim': 'Chinese (Simplified)', 'jpn': 'Japanese', 'kor': 'Korean',
         'ara': 'Arabic', 'heb': 'Hebrew', 'rus': 'Russian', 'ukr': 'Ukrainian', 'ell': 'Greek', 'hin': 'Hindi', 'san': 'Sanskrit',
         'tha': 'Thai', 'khm': 'Khmer', 'lao': 'Lao', 'mya': 'Burmese', 'tib': 'Tibetan', 'ben': 'Bengali', 'tam': 'Tamil'}
BCP = {'chi_tra': 'zh-Hant', 'chi_sim': 'zh-Hans', 'jpn': 'ja', 'kor': 'ko', 'eng': 'en', 'fra': 'fr', 'deu': 'de', 'spa': 'es',
       'por': 'pt', 'ita': 'it', 'nld': 'nl', 'haw': 'haw', 'tgl': 'tl', 'ilo': 'ilo', 'vie': 'vi', 'ind': 'id', 'mri': 'mi',
       'smo': 'sm', 'ton': 'to', 'ara': 'ar', 'heb': 'he', 'rus': 'ru', 'ell': 'el', 'tha': 'th'}
SCRIPT_NAMES = {'kana': 'Japanese', 'hangul': 'Korean'}       # kana is Japanese and Hangul Korean (team rule, PR #39); Han is not named
LATIN_NAMES = {'eng': 'English', 'fra': 'French', 'deu': 'German', 'spa': 'Spanish', 'por': 'Portuguese', 'ita': 'Italian',
               'nld': 'Dutch', 'lat': 'Latin', 'haw': 'Hawaiian', 'tgl': 'Tagalog', 'fil': 'Filipino', 'ilo': 'Ilokano',
               'vie': 'Vietnamese', 'ind': 'Indonesian', 'msa': 'Malay', 'mri': 'Māori', 'smo': 'Samoan', 'ton': 'Tongan'}

def ocr_codes(intake):
    """The Tesseract languages OCR_LANG named for this book (a person set them), without the _vert models."""
    s = (intake.get('settings') or {}).get('OCR_LANG') or (intake.get('language') or {}).get('ocr_lang') or ''
    return [c for c in dict.fromkeys(x.replace('_vert', '') for x in str(s).split('+') if x)]

def languages(intake, pages):
    """Whether any listed page is in a non-Latin script, and the language names a reviewer confirms reading: from OCR_LANG,
    or kana/Hangul found by the layer test. {non_latin, names, label} (label: what the page asks, never a guess)."""
    cjk = set(((intake.get('cjk_probe') or {}).get('cjk_pages')) or [])
    tested = {p.get('page'): p for p in (intake.get('ocr_layer_test') or {}).get('pages') or []}
    scripts = {str(tested[p].get('script')) for p in pages if p in tested and tested[p].get('script') not in (None, 'latin')}
    codes = [c for c in ocr_codes(intake) if c in NAMES] if (intake.get('ocr') or {}).get('pages_with_ocr_text') else []
    non_latin = bool(cjk & set(pages)) or bool(scripts) or bool(codes)
    names = [NAMES[c] for c in codes] or [SCRIPT_NAMES[s] for s in sorted(scripts) if s in SCRIPT_NAMES]
    return {'non_latin': non_latin, 'names': names,
            'label': ' and '.join(names) if names else 'the language of these pages'} if non_latin else {'non_latin': False, 'names': [], 'label': None}

def language_names(intake):
    """Every language OCR_LANG named, by name (as on the "I read" box), in its order; a code with no name is left out (the
    page shows no codes)."""
    return [n for n in ((NAMES | LATIN_NAMES).get(c) for c in ocr_codes(intake)) if n]

def text_lang(intake):
    """The lang attribute for the OCR text: only when OCR_LANG names one language; (tag or None, why not, in plain words)."""
    codes = ocr_codes(intake)
    if not (intake.get('ocr') or {}).get('pages_with_ocr_text'): return None, 'the book\'s own OCR text does not record its language'
    if len(codes) == 1 and codes[0] in BCP: return BCP[codes[0]], None
    return None, ('it was read as more than one language' if len(codes) > 1 else 'no OCR language was set for this book')

def and_list(xs):
    xs = [str(x) for x in xs]
    return ' and '.join(xs) if len(xs) < 3 else ', '.join(xs[:-1]) + ' and ' + xs[-1]

# ------------------------------------------------------------------ checking a verdict
# Every refusal has two wordings: the terminal's (review_ocr.py, its options named) and the page's (`page`: plain words for
# library staff, no file names or options), which the review server shows.
PAGE_NAMES = {'the reviewer\'s name': 'Your name', 'the reason': 'The reason', 'who it is sent to': '"Sent to"',
              'the language read': 'The language you read'}

def refusal(terminal, page):
    e = ValueError(terminal); e.page = page
    return e

def one_line(name, s, limit, required=False):
    """A person's text that goes into review.md's table row: one line, within the limit, no '|' (it would end the table
    cell) and no '](' (review.html turns [text](link) into a link)."""
    s = core.clean_text(s, one_line=True); who = PAGE_NAMES.get(name, name[:1].upper() + name[1:])
    if required and not s:
        raise refusal(f'{name} is needed', 'Enter your name as the reviewer first.' if name == 'the reviewer\'s name' else f'{who} is needed.')
    if len(s) > limit: raise refusal(f'{name} is {len(s)} characters long; at most {limit}', f'{who} is too long: {len(s):,} characters, at most {limit:,}.')
    if '|' in s: raise refusal(f'{name} cannot contain "|" (it would break review.md\'s table): use another character',
                               f'{who} can\'t contain the character "|". Use another one, such as a comma or a slash.')
    if '](' in s: raise refusal(f'{name} cannot contain "](" (review.html would read it as a link)',
                                f'{who} can\'t contain "](" (a closing square bracket right before an opening parenthesis). Put a space between them.')
    return s

def check_pages(s, n):
    """'381-386' or '5, 9-12': the format review_ocr.py has always taken, each page within the book and each range in order."""
    s = core.clean_text(s, one_line=True)
    if not s: return None
    if not PAGES.fullmatch(s): raise refusal(f'pages "{s}": give PDF page numbers and ranges, for example 381-386 or 5, 9-12',
                                             'Pages: give PDF page numbers and ranges, ex. 381-386 or 5, 9-12.')
    for part in s.split(','):
        a, _, b = part.strip().partition('-')
        a, b = int(a), int(b or a)
        if not 1 <= a <= b <= n:
            raise refusal(f'pages "{part.strip()}": the book has PDF pages 1 to {n}' + (' and a range goes up' if a > b else ''),
                          f'Pages {part.strip()}: ' + ('a range goes from the lower page to the higher one, ex. 5-9.' if a > b else f'this book has PDF pages 1 to {n:,}.'))
    return s

def check(fields, intake, n_pages, date=None):
    """The verdict as it is recorded, from the page's or the command line's fields; raises ValueError (with `page`, the
    page's wording)."""
    verdict = str(fields.get('verdict') or '').strip().lower()
    if verdict not in VERDICTS: raise refusal(f'the verdict is one of: {", ".join(VERDICTS)}', 'Choose a verdict first.')
    date = date or datetime.date.today().isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date): raise ValueError('the date must be YYYY-MM-DD')
    v = {'verdict': verdict, 'reviewer': one_line('the reviewer\'s name', fields.get('reviewer'), WHO_MAX, required=True), 'date': date}
    reason = one_line('the reason', fields.get('reason'), REASON_MAX, required=verdict != SENT)
    if reason: v['reason'] = reason
    pages = check_pages(fields.get('pages'), n_pages)
    if pages: v['pages'] = pages
    if verdict == SENT:
        to = one_line('who it is sent to', fields.get('to'), TO_MAX)
        if to: v['to'] = to
    reads = [one_line('the language read', x, READS_MAX) for x in (fields.get('reads') or []) if str(x or '').strip()]
    lang = languages(intake, listed_pages(intake))
    if verdict == APPROVED and lang['non_latin'] and not reads:
        raise refusal(f'these pages are in a non-Latin script: approving needs the reviewer to say they read {lang["label"]}'
                      ' (on the page: the "I read" box; review_ocr.py: --reads)',
                      f'These pages are in a non-Latin script: to approve them, tick "I read {lang["label"]}".')
    if reads: v['reads'] = reads
    return v

def listed_pages(intake):
    """The pages the section lists: OCR text intake added, and the pages the OCR-layer test scored when it flagged the layer."""
    added = ((intake.get('ocr') or {}).get('pages_with_ocr_text')) or []
    tested = [p.get('page') for p in (intake.get('ocr_layer_test') or {}).get('pages') or [] if p.get('page')]
    return sorted(set(added) | (set(tested) if ocr_layer_flagged(intake) else set()))

def showable_pages(intake):
    """Every page Show Another Page can ask for: the listed ones, and with a flagged layer every page intake found an OCR
    layer on. The server serves the text of these pages only."""
    layer = (((intake.get('triage') or {}).get('pages') or {}).get('ocr-layer')) or []
    return sorted(set(listed_pages(intake)) | (set(layer) if ocr_layer_flagged(intake) else set()))

# ------------------------------------------------------------------ writing it
_THREAD = threading.Lock()                               # one writer per process (the review server is threaded)

def put_text(path, text):
    tmp = f'{path}.{os.getpid()}.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f: f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def put_json(path, obj): put_text(path, json.dumps(obj, indent=1, ensure_ascii=False))

@contextlib.contextmanager
def verdict_lock(R):
    """The intake flock: every verdict writer of this run, in any process, one at a time."""
    with _THREAD, open(os.path.join(R, '_intake', '.verdict.lock'), 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)

def n_pages_of(R, intake, rec=None):
    return ((intake.get('original') or {}).get('pages') or ((rec or {}).get('document') or {}).get('pages')
            or ((intake.get('checks') or {}).get('original') or {}).get('pages') or 0)

def record(R, fields, via, held=False, session=None, date=None, say=print):
    """Check and record a verdict. held: the caller holds reviews/.lock (the review page's own process); otherwise a
    finished run's lock is taken here, and refused while another process holds it. Returns (verdict, record.json or None).
    Raises ValueError (the fields) or sessions.Refused (the lock)."""
    from . import sessions as S
    R = os.path.abspath(R); ij = os.path.join(R, '_intake', 'intake.json'); rj = os.path.join(R, 'record.json')
    if not os.path.exists(ij): raise ValueError(f'no _intake/intake.json in {R}: this book had no intake (already tagged?)')
    finished = os.path.exists(rj)
    made = not os.path.isdir(S.P(R)['dir'])                # a run with no reviews/ yet (never pinned): leave none behind
    lock = S.Lock(R, 'ocr verdict') if finished and not held else None
    try:
        with verdict_lock(R):
            intake = json.load(open(ij, encoding='utf-8'))
            if not needed(intake):
                raise ValueError('this book has no OCR text to review (intake added none, and its existing OCR layer was checked and not flagged)')
            rec = json.load(open(rj, encoding='utf-8')) if finished else None
            v = check(fields, intake, n_pages_of(R, intake, rec) or 10 ** 6, date)
            v.update(via=via, **({'session': session} if session else {}), recorded=datetime.datetime.now().isoformat(timespec='seconds'))
            write(R, intake, rec, v, say)
            return v, rec
    finally:
        if lock:
            lock.release()
            if made:
                try: os.rmdir(S.P(R)['dir'])
                except OSError: pass                       # something else was put there meanwhile: keep it

def write(R, intake, rec, v, say=print):
    """review_ocr.py's write path (unchanged in what it writes), with every file written whole."""
    def put(r):
        rv = r.setdefault('review', {})
        old = rv.get('ocr_text_approved')
        if isinstance(old, dict): rv.setdefault('history', []).append(old)
        rv['ocr_text_approved'] = v; rv.pop('approved_by', None)
    put(intake)
    md_intake = None
    try:                                               # intake.md beside it shows the verdict too
        import intake as I
        intake['glance'] = I.intake_glance(intake)
        tmp = os.path.join(R, '_intake', f'intake.md.{os.getpid()}.tmp')
        I.write_md(intake, tmp); md_intake = tmp
    except Exception as e: say(f'note: intake.md not rewritten ({e})')
    put_json(os.path.join(R, '_intake', 'intake.json'), intake)
    if md_intake: os.replace(md_intake, os.path.join(R, '_intake', 'intake.md'))
    if rec is not None and isinstance(rec.get('intake'), dict): put(rec['intake']); rec['intake']['glance'] = intake.get('glance')
    md = os.path.join(R, 'review.md'); text = None; labels = None
    from lib import glance as G
    import report_html as H
    if rec is not None and rec.get('sections_version') == 1:     # review.md is drawn from record.json `sections`: change the row there
        good, words = ocr_verdict_row(v)
        row = next((it for x in rec['sections'] for it in x['items'] if it.get('key') == f'check:{OCR_ROW}'), None)
        if row is not None: row['text'] = f'| {OCR_ROW} | {"OK" if good else "**CHECK**"} | {words} |'; row.pop('parts', None)
        else: say('note: review.md has no OCR review row; record.json and intake.json were updated')
        try:
            labels = H.labels_of(R, rec)
            text = G.refresh(rec, labels, H.han_pages(R))
        except Exception as e: say(f'note: "Overview" and review.html not refreshed ({type(e).__name__}: {e})'); text = None
    elif rec is not None and os.path.exists(md):
        good, words = ocr_verdict_row(v)
        lines = open(md, encoding='utf-8').read().split('\n'); hit = False
        for i, l in enumerate(lines):
            if l.startswith(f'| {OCR_ROW} |'): lines[i] = f'| {OCR_ROW} | {"OK" if good else "**CHECK**"} | {words} |'; hit = True
        if not hit: say('note: review.md has no OCR review row; record.json and intake.json were updated')
        text = '\n'.join(lines)
        try:                                           # older runs: refresh the glance in review.md's text
            labels = H.labels_of(R, rec)
            rec['glance'] = G.glance(rec, text, labels, H.han_pages(R))
            text = G.replace_block(text, G.glance_md(rec['glance']))
        except Exception as e: say(f'note: "Overview" and review.html not refreshed ({type(e).__name__}: {e})'); labels = None
    if rec is not None: put_json(os.path.join(R, 'record.json'), rec)
    if text is not None: put_text(md, text)
    if rec is not None and text is not None and labels is not None:
        try: H.review_html(R, rec, text, labels)               # written whole by report_html
        except Exception as e: say(f'note: review.html not refreshed ({type(e).__name__}: {e})')

# ------------------------------------------------------------------ the page's OCR Text section
def differ(cer, other=''):
    """A character error rate in words, against `other` when given; it can pass 100% when the two texts hardly match."""
    return f'{cer:.0%} of its characters differ' + (f' from {other}' if other else '') if cer < 1 else 'almost none of its characters match' + (f' {other}' if other else '')

def plain_reason(t):
    """Why the layer test could not score a page, in plain words (intake's own reason, with its terms replaced)."""
    r = str(t.get('reason') or 'no reason recorded')
    if r.startswith('Tesseract model'): return 'the OCR language needed to check it is not installed on this computer'
    if t.get('marks'): return 'a new OCR reading missed the accent marks that the book\'s OCR text has, so the two cannot be compared fairly'
    return r.replace('in the OCR layer', 'in its OCR text').replace('Greek letters', 'Greek letters on it')

def layer_words(ol):
    """The intro's sentence on a flagged existing OCR layer (the review.md wording, ocr_layer_finding, stays as it is)."""
    scored, sample, v = ol.get('scored'), ol.get('sample'), ol.get('verdict')
    on = f' on {scored} of {sample} sample pages' if scored is not None and sample else ''
    if v in ('doubtful', 'unusable'):
        s = (f'The book came with its own OCR text. During intake it was compared with a new OCR reading{on}: it looks {v}'
             + (f' ({"about " if ol["median_cer"] < 1 else ""}{differ(ol["median_cer"])})' if ol.get('median_cer') is not None else '') + '.')
    elif v == 'not enough pages scored':
        s = (f'The book came with its own OCR text, which could not be checked during intake: '
             + (f'only {scored} of {sample} sample pages could be compared with a new OCR reading.' if scored is not None and sample else 'too few sample pages could be compared with a new OCR reading.'))
    else: s = 'The book came with its own OCR text.'
    if ol.get('diacritics'): s += ' It is missing accent marks on letters (ex. ā, ō) that a new OCR reading found.'
    return s

def ship_line(rec):
    """What "Ready to ship?" says now, and its OCR line, from a record's glance; None without a record."""
    g = (rec or {}).get('glance') or {}
    ocr = next((x for x in g.get('ship') or [] if x.get('what') == 'OCR text approved'), None)
    return {'ready': bool(g.get('ready')), 'ocr': (ocr or {}).get('text')} if g else None

def section(R, digest=None, wo=None):
    """The OCR Text section's data for run folder R, or None when the book needs no OCR approval. digest and wo (the
    work order, for its OCR-word readings) are optional: without them the section lists no OCR words."""
    from . import sessions as S
    intake = core.load(os.path.join(R, '_intake', 'intake.json'))
    if not intake or not needed(intake): return None
    rec = core.load(os.path.join(R, 'record.json'))
    o = intake.get('ocr') or {}; ol = intake.get('ocr_layer_test') or {}; cj = intake.get('cjk_probe') or {}
    added = o.get('pages_with_ocr_text') or []; flagged = ocr_layer_flagged(intake)
    words = {p['page']: p for p in o.get('per_page') or [] if isinstance(p, dict)}
    junk = o.get('junk') or {}
    tested = {p.get('page'): p for p in ol.get('pages') or []}
    vertical = set((cj.get('vertical_trial') or {}).get('vertical_pages') or [])
    spreads = set(((intake.get('spreads') or {}).get('pages')) or [])
    readings = {w.get('id'): w.get('reads') for w in (wo or {}).get('ocr_words') or [] if isinstance(w, dict)}
    by_page = {}
    for w in (digest or {}).get('ocr_words') or []:
        for p in w.get('pages') or []:
            by_page.setdefault(p, []).append({'id': w['id'], 'text': w.get('text'), 'count': w.get('count'), 'reads': readings.get(w['id'])})

    # in plain words for library staff (no file names, codes or tool names); examples after "ex."
    def findings(p):
        f = []
        if p in added:
            w = words.get(p) or {}
            if w.get('words') is not None: f.append(f'{w["words"]:,} words read by OCR')
            j = junk.get(str(p)) or {}
            if j.get('junk'): f.append(f'{j["junk"]} of {j.get("tokens")} words and symbols look like junk ({j.get("share", 0):.0%})'
                                      + (', ex. ' + ' '.join(j.get('examples')[:6]) if j.get('examples') else ''))
            n = (cj.get('cjk_characters') or {}).get(str(p))
            if n: f.append(f'{n:,} Chinese, Japanese or Korean characters')
        if flagged and p in tested:
            t = tested[p]
            if t.get('verdict') == 'not scored': f.append(f'the book\'s own OCR text could not be checked on this page: {plain_reason(t)}')
            elif t.get('verdict'):
                f.append(f'the book\'s own OCR text looks {t["verdict"]}' + (f' ({differ(t["cer"], "a new OCR reading")})' if t.get('cer') is not None else ''))
            if t.get('marked_vowels_ocr'):
                f.append(f'{t["marked_vowels_ocr"]} letters with accent marks (ex. ā, ō) in a new OCR reading, {t.get("marked_vowels_layer") or 0} in the book\'s OCR text')
            if t.get('confident_words_missing'): f.append(f'{t["confident_words_missing"]:.0%} of the words a new OCR reading was sure of are missing from the book\'s OCR text')
            if t.get('layer_read_with') == 'pdfium':
                f.append('the check read this page\'s text with a different tool from the one that shows it here, so the two can differ slightly')
        if p in vertical: f.append('text set vertically')
        if p in spreads: f.append('two printed pages on this PDF page')
        return f

    pages = listed_pages(intake)
    lang, lang_why = text_lang(intake)
    av = (intake.get('review') or {}).get('ocr_text_approved')
    what = []
    if added:
        names = language_names(intake)
        what.append(f'During intake, OCR added text to {len(added)} page{"s" if len(added) != 1 else ""}'
                    + (f', read as {and_list(names)}' if names else '') + '.')
    if flagged: what.append(layer_words(ol))
    pics = o.get('image_pages_without_text') or []
    if pics:
        shown = pics[:12] + ([f'{len(pics) - 12} more'] if len(pics) > 12 else [])
        what.append(f'PDF {and_list(shown)} {"is a picture" if len(pics) == 1 else "are pictures"} with no text.')
    snaps = [{'session': s['id'], 'verdict': s.get('ocr_verdict')} for s in S.sessions(R) if 'ocr_verdict' in s] if rec else []
    return {'what': what, 'pages': [{'page': p, 'source': 'intake OCR' if p in added else 'existing OCR layer', 'findings': findings(p),
                                     'words': by_page.get(p, [])} for p in pages],
            'showable': showable_pages(intake), 'flagged': flagged,
            'words_by_page': {str(p): ws for p, ws in by_page.items() if p in set(showable_pages(intake)) - set(pages)},   # for Show Another Page
            'languages': languages(intake, pages), 'lang': lang, 'lang_why': lang_why,
            'current': av if isinstance(av, dict) else None, 'history': [h for h in (intake.get('review') or {}).get('history') or [] if isinstance(h, dict)],
            'snapshots': snaps, 'finished': rec is not None, 'ship': ship_line(rec), 'verdicts': list(VERDICTS),
            'limits': {'reviewer': WHO_MAX, 'reason': REASON_MAX, 'to': TO_MAX}}

class Text:
    """Page texts of the PDF the run worked on (its input: _intake/intake.pdf for intake runs; apply never changes text, so
    it is the text that ships), read with pdfplumber, one open document, one page at a time, each read once."""
    def __init__(self, pdf):
        self.pdf, self.doc, self.cache, self.lock = pdf, None, {}, threading.Lock()
    def __call__(self, n):
        with self.lock:
            if n not in self.cache:
                if self.doc is None:
                    sys.path.insert(0, core.HERE)
                    from lib import plumb_fix  # noqa: F401  (before pdfplumber reads a page)
                    import pdfplumber
                    self.doc = pdfplumber.open(self.pdf)
                p = self.doc.pages[n - 1]
                try: self.cache[n] = p.extract_text() or ''
                finally: p.close()
            return self.cache[n]
    def close(self):
        if self.doc is not None: self.doc.close()
