"""glance.py: the "Overview" numbers for one finished run, computed once and shared by review.md, review.html,
summary.html and record.json (`glance`), so no two of them can disagree.

    g = glance(record, review_md, labels=None, han_pages=None)    # a dict; stored in record.json as `glance`
    lines = glance_md(g)                                          # the "## Overview" block of review.md

It reads only what a finished run keeps: record.json and review.md (its "Automated checks" table and its numbered
"For a person to check" sections), so a dashboard can be rebuilt for any finished run. `labels` is the remediated
PDF's page-label table ({page: label}); `han_pages` the PDF pages of the Han-only runs (from han_review.csv).

Definitions (docs/output-files.md):
  ready to ship      the work order approved on the review page, the OCR text approved (when intake added OCR text, or
                     found an existing OCR layer doubtful, unusable or missing diacritics, or could not check it),
                     and the safety checks OK. PAC is the manual check after it; its line is information only.
  needs a person     the AI's deferrals + the executor's deferrals (counted by kind and page) + CHECK rows, leaving out
                     the "Nothing deferred by the executor" row, which only points at that list.
  AI decisions       every entry in the work order (deferrals and notes are not decisions).
  fixed automatically  the executor's own fixes, by kind, with no total (several touch the same links).
"""
import re

SCHEMA = 'glance/0.3'
def with_spread_labels(labels, intake):
    """The page-label table with intake's spread labels ("210–211": two printed pages on one PDF page) on the pages that have no
    label of their own. The one place report.py and report_html.py (a rebuilt dashboard, summary.html) take them from."""
    out = dict(labels or {})
    for p, lab in (((intake or {}).get('spreads') or {}).get('printed') or {}).items():
        if str(out.get(int(p), str(p))) == str(p): out[int(p)] = lab
    return out
def ocr_layer_flagged(intake):
    """Intake's test of an existing OCR layer on scanned pages found it doubtful, unusable or missing diacritics, or could
    not check it (no sample page scored: an unknown layer is not "not needed"): then its OCR text needs a person's
    approval before the book ships, as added OCR text does (decided 2026-10-25). A book with no existing OCR layer has no
    `ocr_layer_test` and is not flagged."""
    ol = (intake or {}).get('ocr_layer_test') or {}
    return ol.get('verdict') in ('doubtful', 'unusable', 'not enough pages scored') or bool(ol.get('diacritics'))
def ocr_layer_finding(intake):
    """A few words on what the OCR-layer test found, for the ready-to-ship line."""
    ol = (intake or {}).get('ocr_layer_test') or {}
    return ' and '.join(x for x in [f'{ol["verdict"]} ({ol["median_cer"]:.0%} character error)' if ol.get('verdict') in ('doubtful', 'unusable') and ol.get('median_cer') is not None else None,
                                    'not checked (no sample page could be scored)' if ol.get('verdict') == 'not enough pages scored' else None,
                                    'missing diacritics' if ol.get('diacritics') else None] if x)   # reads after "the existing OCR layer is"
NO_PAGE = 'page: not on this tag'
SAFETY = [('Every page looks the same as the original', 'pages look the same'),
          ('Published text unchanged', 'text unchanged'),
          ('All content tagged or marked as decoration', 'all content tagged or decoration'),
          ('Tag-tree index points only into the tree', 'tag-tree index points into the tree'),
          ('Fonts: every embedded font program could be read', 'every font readable')]
POINTER_ROWS = {'Nothing deferred by the executor'}        # a CHECK row that only points at a list counted separately
GATE_ROWS = {'OCR text reviewed by a person', 'Work order reviewed by a person before it was applied'}
META = {'schema', 'source', 'decided_by', 'notes_for_reviewer', 'deferrals', 'reviewed_by'}
# the executor's own fixes (applied whatever the work order says): change-label prefix → what the dashboard calls it
EXECUTOR = [('links: /Contents set', 'links tied and described'), ('links: URL-only description replaced', 'link descriptions that were only a URL'),
            ('notes: Note with /ID', 'note IDs'), ('notes: empty Note tag removed', 'empty notes removed'),
            ('tag tree index:', 'tag-tree index entries'), ('role map: standard tag', 'standard tags un-remapped (7.1-7)'),
            ('structure: empty', 'empty tags removed'), ('artifact: untagged path', 'decorative lines marked'),
            ('tab order:', 'pages given tab order'), ('font map:', 'character codes given Unicode (font maps)'),
            ('fonts: invisible OCR-layer font', 'OCR fonts given defined glyphs'), ('one-item list → paragraph', 'one-item lists turned into paragraphs'),
            ('bookmarks: built', 'bookmarks built'), ('table: header cells given a direction', 'table header directions'),
            ('figure: whole page wrapped', 'whole-page figures wrapped'), ('order: figure moved to its page', 'figures moved to their page'),
            ('document: DisplayDocTitle', 'title shown in the window'), ('document: marked as tagged', 'marked as tagged'),
            ('document: Document root created', 'Document root'), ('document: second Document root merged', 'Document root'),
            ('figure: moved into Document', 'Document root')]
# WCAG rules whose veraPDF description is worded for PDF/UA: the name review.html shows (review.md keeps veraPDF's wording)
WCAG_NAMES = {'7.21.8-1': 'Text drawn with a glyph the font does not define (.notdef)'}
SHORT = {'7.1-3': 'Content neither tagged nor marked as decoration', '7.3-1': 'Figures without alt text',
         '7.21.7-1': 'Characters a font cannot map to Unicode', '7.1-5': 'Styles with no standard tag',
         '7.2-34': 'Untagged or wrongly nested text', '7.18.5-1': 'Links not tagged as Link',
         '7.5-1': 'Table header cells without a direction', '7.1-10': 'Title not shown in the window', '6.2-1': 'Not marked as tagged'}

def slug(title):
    """The anchor GitHub and VS Code give a heading: "### 18. WCAG checks" → "18-wcag-checks"."""
    return re.sub(r'\s', '-', re.sub(r'[^\w\- ]', '', title.strip().lower()))

def parse_md(md):
    """The "Automated checks" rows and the numbered "### N. Title" sections of a review.md."""
    rows, secs, in_checks = [], [], False
    for l in md.split('\n'):
        if l.startswith('## '): in_checks = l.strip() == '## Automated checks'
        m = re.match(r'^### (\d+)\. (.+?)\s*$', l)
        if m: secs.append({'n': int(m.group(1)), 'title': m.group(2), 'anchor': slug(f'{m.group(1)}. {m.group(2)}')})
        if in_checks and l.startswith('| ') and not l.startswith('| Check |') and not l.startswith('|---'):
            cells = l[2:].rstrip(' |').split(' | ', 2)
            if len(cells) == 3: rows.append({'name': cells[0], 'ok': cells[1] == 'OK', 'detail': cells[2]})
    return rows, secs

def pages_text(ps, labels=None):
    """PDF pages for a person: "PDF 149 (printed 140), PDF 152 (printed 143)", or for more than four the count and span."""
    labels = labels or {}
    ps = sorted({int(p) for p in ps or [] if str(p).lstrip('-').isdigit()})
    def one(n):
        lab = str(labels.get(n, labels.get(str(n), '')) or '')
        return f'PDF {n}' + (f' (printed {lab})' if lab and lab != str(n) else '')
    if not ps: return NO_PAGE
    if len(ps) <= 4: return ', '.join(one(n) for n in ps)
    return f'{len(ps)} pages, {one(ps[0])} to {one(ps[-1])}'

def n_decisions(wo):
    n = 0
    for k, v in (wo or {}).items():
        if k in META or v in (None, False, {}, []): continue
        if isinstance(v, list): n += len(v)
        elif isinstance(v, dict): n += sum(len(x) if isinstance(x, (list, dict)) else 1 for x in v.values() if x not in (None, False, {}, []))
        else: n += 1
    return n

def from_sections(secs):
    """rows and sections as parse_md gives them, read from record.json `sections` instead of review.md's text."""
    rows, out = [], []
    for s in secs:
        if s.get('n') is not None: out.append({'n': s['n'], 'title': s['title'].split('. ', 1)[1], 'anchor': s['anchor']})
        if s.get('key') == 'automated-checks':
            for it in s['items']:
                if it['kind'] != 'row': continue
                cells = it['text'][2:].rstrip(' |').split(' | ', 2)
                if len(cells) == 3: rows.append({'name': cells[0], 'ok': cells[1] == 'OK', 'detail': cells[2]})
    return rows, out

def glance(record, md, labels=None, han_pages=None, sections=None):
    labels = {int(k): v for k, v in (labels or {}).items() if str(k).isdigit()}
    rows, secs = from_sections(sections) if sections is not None else parse_md(md)
    keymap = {}
    for s_ in sections or []:
        for it in s_['items']:
            if it.get('key') and it.get('id') and it['key'] not in keymap: keymap[it['key']] = it['id']
    byname = {r['name']: r for r in rows}
    def sec(*words):
        for s in secs:
            if any(w.lower() in s['title'].lower() for w in words): return s
        return None
    def where(s): return {'n': s['n'], 'title': s['title'], 'anchor': s['anchor']} if s else {'n': None, 'title': 'Automated checks', 'anchor': 'automated-checks'}
    wo, ap, ve = record.get('workorder') or {}, record.get('apply') or {}, record.get('verify') or {}
    intake = record.get('intake') or {}; rv = (record.get('review') or {}).get('workorder')
    vb, va = ((record.get('verapdf') or {}).get(k) for k in ('before', 'after'))

    # ---- ready to ship
    if rv and rv.get('method') == 'page':
        unexpl = [x for x in rv.get('gaps') or [] if str(x.get('reason') or '').startswith('hand edit: no reason asked for')]
        why = ([f'{(rv.get("counts") or {}).get("accepted_unreviewed")} decisions accepted without review'] if (rv.get('counts') or {}).get('accepted_unreviewed') else []) \
            + ([f'{len(rv["dropped_on_check"])} edits dropped by the check'] if rv.get('dropped_on_check') else []) \
            + ([f'{len(unexpl)} gaps left without a reason'] if unexpl else [])
        wo_ok = not why
        wo_txt = f'yes ({rv.get("reviewer")} on {rv.get("date")})' if wo_ok else f'no (reviewed by {rv.get("reviewer")} on {rv.get("date")}: {", ".join(why)})'
    elif rv:
        wo_ok, wo_txt = False, f'no (reviewed by hand edit by {rv.get("reviewer")} on {rv.get("date")}, not on the review page)'
    else:
        wo_ok, wo_txt = False, 'no (run without REVIEW=1)'
    pend = (record.get('review') or {}).get('pending') or {}
    if pend.get('status') == 'finished':                # a later review is signed off but not applied: the PDF on disk is older
        wo_ok, wo_txt = False, (f'no (the latest review, session {int(pend["session"])} by {pend.get("reviewer")}, is finished but not applied: '
                                'run review_workorder.py <run> --apply)')
    ocr_pages = (intake.get('ocr') or {}).get('pages_with_ocr_text') or []
    v = (intake.get('review') or {}).get('ocr_text_approved')
    flagged = ocr_layer_flagged(intake)                 # an existing OCR layer that step A flagged needs the approval too
    if ocr_pages or flagged:
        if isinstance(v, dict):
            ocr_ok = v.get('verdict') == 'approved'
            ocr_txt = f'{"yes" if ocr_ok else "no"} ({v.get("verdict")} by {v.get("reviewer")} on {v.get("date")})'
        else: ocr_ok, ocr_txt = False, ('no (not yet reviewed: ' + '; '.join(x for x in [f'OCR text on {pages_text(ocr_pages, labels)}' if ocr_pages else None,
                                         f'the existing OCR layer is {ocr_layer_finding(intake)}' if flagged else None] if x) + ')')
    else:
        ocr_ok, s = True, sec('the text layer comes from OCR')
        ocr_txt = 'not needed (intake added no OCR text' + (f'; the publisher\'s text layer is OCR, see §{s["n"]})' if s else ')')
    saf = [{'what': label, 'ok': byname[name]['ok']} for name, label in SAFETY if name in byname]
    saf_ok = bool(saf) and all(x['ok'] for x in saf)
    ship = [{'what': 'Work order approved on the review page', 'ok': wo_ok, 'text': wo_txt},
            {'what': 'OCR text approved', 'ok': ocr_ok, 'text': ocr_txt},
            {'what': 'Safety checks', 'ok': saf_ok, 'text': 'OK' if saf_ok else ('failed: ' + ', '.join(x['what'] for x in saf if not x['ok']) if saf else 'not checked')},
            {'what': 'Manual check (PAC)', 'ok': None, 'text': 'not run'}]
    ready = wo_ok and ocr_ok and saf_ok

    # ---- issues: everything that needs a person, ranked (0 safety, 1 ship conditions, 2 CHECK rows, 3 executor, 4 AI)
    issues = []
    def add(rank, kind, text, pages, s, count=1, find=None, key=None):
        x = {'rank': rank, 'kind': kind, 'text': text, 'pages': sorted({int(p) for p in pages or [] if str(p).lstrip('-').isdigit()}),
             'where': where(s), 'count': count, 'find': find}       # find: the start of its own line (for runs made before `sections`)
        if keymap.get(key): x['item'] = keymap[key]                 # item: the id of its own line in record.json `sections`
        elif kind in ('check', 'safety', 'ship') and keymap.get(f'check:{rowname}'): x['item'] = keymap[f'check:{rowname}']   # else: its checks row
        issues.append(x)
    wc = ve.get('wcag') or {}
    vrules = {r['id']: r for r in (va or {}).get('rules') or []} if isinstance(va, dict) else {}
    brules = {r['id']: r for r in (vb or {}).get('rules') or []} if isinstance(vb, dict) else {}
    n_check = 0
    rowname = None
    for r in rows:
        if r['ok'] or r['name'] in POINTER_ROWS: continue
        n_check += 1; name, det = r['name'], r['detail']; rowname = name
        found = [int(x) for x in re.findall(r'PDF (\d+)', det)]
        if name in dict(SAFETY): add(0, 'safety', f'{name}: {det}', found, None, find=f'| {name} |', key=f'check:{name}')
        elif name == 'veraPDF: no rule newly failing or failing more often': add(0, 'safety', f'veraPDF: {det}', [], sec('veraPDF'))
        elif name == 'OCR text reviewed by a person':
            add(1, 'ship', 'OCR text ' + ('not approved' if isinstance(v, dict) else 'not yet reviewed'), ocr_pages, sec('Intake'), find='- OCR text added', key='intake:ocr')
        elif name in GATE_ROWS: add(1, 'ship', f'{name}: {det}', [], sec('Work order reviewed'))
        elif name.startswith('veraPDF WCAG'):
            wr = [x for x in vrules.values() if x.get('scope') == 'wcag']
            for x in wr or [None]:
                if x is None: add(2, 'check', f'veraPDF: {det}', [], sec('veraPDF')); continue
                tail = f' (veraPDF {x["id"]}, {x["failed"]} check{"" if x["failed"] == 1 else "s"})'
                add(2, 'check', (SHORT.get(x['id']) or WCAG_NAMES.get(x['id']) or x.get('description') or x['id']) + tail, x.get('pages') or [], sec('veraPDF'), find=f' {x["id"]}', key=f'vera:{x["id"]}')
                if x['id'] not in SHORT: issues[-1]['text_md'] = (x.get('description') or x['id'])[:70] + tail   # review.md's short form
        elif name.startswith('Reading order'):
            fl = (wc.get('reading_order') or {}).get('flagged') or []
            add(2, 'check', f'Reading order jumps back up a column ({sum(x.get("jumps_up") or 0 for x in fl)} jumps)', [x['page'] for x in fl], sec('WCAG checks veraPDF'), find='- 1.3.2 ', key='wcag:1.3.2')
        elif name.startswith('Figures: none with empty'):
            if '7.3-1' in vrules: continue             # counted, but listed once: as veraPDF's 7.3-1 below
            m = re.search(r'(\d+) placeholder', det); k = int(m.group(1)) if m else None
            add(2, 'check', f'{k if k is not None else "Some"} figures without alt text, or with placeholder alt', (vrules.get('7.3-1') or {}).get('pages') or [],
                sec('veraPDF') if '7.3-1' in vrules else sec('Alt text'))
        else:
            s = (sec('Fonts') if name.startswith(('Fonts', 'Characters with no Unicode', 'Private-use')) else
                 sec('Headings') if name.startswith('Headings: no skipped') or name.startswith('Headings: exactly') else
                 sec('WCAG checks veraPDF') if re.search(r'\((1\.1\.1|1\.3\.1|2\.4\.\d)\)$', name) else
                 sec('Decisions not applied') if name.startswith('Executor applied') else
                 sec('OCR words') if name.startswith('OCR words') else
                 sec('Intake') if name.startswith(('Text layer', 'Words separated', 'OCR text added', 'Auto-tagging', 'Existing OCR layer',
                                                   'One printed page')) else
                 sec('Text outside') if name.startswith('Text outside') else
                 sec('Empty tags') if 'empty tag' in name.lower() else
                 sec('Structure left', 'Captions') if 'caption' in name.lower() else
                 sec('Links') if 'link' in name.lower() else None)
            hint = (('- **No ToUnicode map**' if re.search(r'[1-9]\d* without ToUnicode', det) else '- **Not embedded**')
                    if name == 'Fonts: embedded and mapped to Unicode' else None)
            add(2, 'check', f'{name}: {re.sub(r"[*`]", "", det)}', found, s, find=hint if s else f'| {name} |',
                key=({'- **No ToUnicode map**': 'fonts:no_tounicode', '- **Not embedded**': 'fonts:not_embedded'}.get(hint) if hint
                     else f'wcag:{wsc.group(1)}' if (wsc := re.search(r'\((1\.1\.1|1\.3\.1|2\.4\.\d)\)$', name))
                     else 'intake:ocr' if name.startswith('OCR text added') else f'check:{name}'))
    han_n = ap.get('han_only_runs') or 0
    groups = {}
    for d in ap.get('deferred') or []:
        if d.get('what') == 'Han-only runs (ja vs zh)' or d.get('scope') == 'pdfua': continue    # WCAG only: a PDF/UA-only deferral is not counted
        groups.setdefault(d.get('what') or 'not described', []).append(d.get('page'))
    n_exec = 0
    s_ex = sec('Deferred by the executor')
    if han_n:
        hp = han_pages or []; n_exec += 1
        add(3, 'executor', f'{han_n} Han-only runs need Japanese or Chinese (han_review.csv)', hp, s_ex, han_n, find='Han-only CJK runs', key='exec:han')
    for what, ps in groups.items():
        real = [p for p in ps if p is not None]; n_exec += len(set(real)) + (1 if len(real) < len(ps) and not real else 0)
        txt = f'{len(ps)} captions not grouped: several figures on the page' if what == 'caption' else (what if len(ps) == 1 else f'{what} ({len(ps)})')
        add(3, 'executor', txt, real, s_ex, len(ps), find='- caption (' if what == 'caption' else f'- {what}', key=f'exec:{what}')
    d_ai = wo.get('deferrals') or []
    s_ai = sec('Deferred by the AI')
    for i_, d in enumerate(d_ai):
        t = re.sub(r'\*\*', '', str(d.get('what') or 'not described')).strip()           # in full: the AI's sentence as written
        add(4, 'ai', t, [p for p in d.get('pages') or [] if isinstance(p, int)], s_ai, find='- ' + t[:60], key=f'ai:{i_}')
    issues.sort(key=lambda x: x['rank'])
    for x in issues: x['pages_text'] = pages_text(x['pages'], labels) if x['pages'] else ''

    # ---- the other headline numbers
    fixed = {}
    for k, c in (ap.get('applied') or {}).items():
        for pre, label in EXECUTOR:
            if k.startswith(pre):
                if pre == 'font map:':
                    m = re.match(r'font map: (\d+)', k); c = int(m.group(1)) if m else c
                fixed[label] = fixed.get(label, 0) + (c if isinstance(c, int) else 1); break
    if (ap.get('offpage') or {}).get('artifacted'):
        fixed['characters outside the page marked as decoration'] = sum(a.get('chars') or 0 for a in ap['offpage']['artifacted'])
    def ran(x): return isinstance(x, dict) and 'not_run' not in x and x.get('rules') is not None
    vg = {'ran_before': ran(vb), 'ran_after': ran(va)}
    if ran(vb): vg.update(before_rules=vb['totals']['wcag_failed_rules'], before_checks=vb['totals']['wcag_failed_checks'])
    if ran(va): vg.update(after_rules=va['totals']['wcag_failed_rules'], after_checks=va['totals']['wcag_failed_checks'])
    if ran(vb) and ran(va):
        wv = {k: x for k, x in vrules.items() if x.get('scope') == 'wcag'}                         # WCAG only
        vg['newly_failing'] = sorted([k for k in wv if k not in brules] + [k for k in wv if k in brules and wv[k]['failed'] > brules[k]['failed']])
        who = {}
        for when, rs in (('before', brules), ('after', vrules)):
            for x in rs.values():
                if x.get('scope') != 'wcag': continue
                w = {'executor': 'the pipeline', 'model': 'the AI', 'person': 'a person'}.get(x.get('who'), x.get('who') or 'not classified')
                who.setdefault(w, {'before': 0, 'after': 0})[when] += 1
        vg['by_who'] = who
    if not ran(va): vg['not_run'] = (va or {}).get('not_run') if isinstance(va, dict) else 'not recorded'
    page_level, page_notes = {}, {}
    bad_pages = set((ve.get('pixel_pages_differing') or []) + (ve.get('text_pages_changed') or []))
    for p in bad_pages: page_level[p] = 'safety'; page_notes.setdefault(p, []).append('page changed by this run (safety check)')
    for x in issues:
        for p in x['pages']:
            page_level.setdefault(p, 'safety' if x['rank'] == 0 else 'person'); page_notes.setdefault(p, []).append(x['text'])
    reviewed = None
    if rv: reviewed = {'reviewer': rv.get('reviewer'), 'date': rv.get('date'), 'method': rv.get('method'), 'changed': len(rv.get('changes') or []),
                       **({'session': record['review']['session']} if (record.get('review') or {}).get('session') else {})}
    return {'schema': SCHEMA, 'ready': ready, 'ship': ship, 'safety': saf, 'safety_ok': saf_ok,
            'needs_person': {'total': len(d_ai) + n_exec + n_check, 'ai_deferrals': len(d_ai), 'executor_deferrals': n_exec, 'check_rows': n_check},
            'ai_decisions': {'count': n_decisions(wo), 'reviewed': reviewed},
            'fixed_automatically': [{'what': k, 'count': c} for k, c in fixed.items()],
            'verapdf': vg, 'issues': issues, 'sections': secs, 'checks': rows,
            'pages': (record.get('document') or {}).get('pages'),
            'page_level': {str(k): v for k, v in sorted(page_level.items())}, 'page_notes': {str(k): v for k, v in sorted(page_notes.items())}}

def _n(x): return f'{x:,}'
def glance_md(g, html_name='review.html', top=5):
    """The "## Overview" block (a list of lines) for review.md (called "At a glance" before 2026-10-21)."""
    L = ['## Overview', '', f'[Open the dashboard]({html_name})', '', f'**Ready to ship?** {"Yes" if g["ready"] else "No"}']
    L += [f'- {s["what"]}: {s["text"]}' for s in g['ship']] + ['']
    if g['safety']:
        L.append('**Safety checks:** ' + ' · '.join(f'{"OK ✔" if x["ok"] else "FAILED ✘"} {x["what"]}' for x in g['safety']) + '  ')
    np_ = g['needs_person']
    L.append(f'**Needs a person:** {np_["total"]} ({np_["ai_deferrals"]} deferred by the AI · {np_["executor_deferrals"]} deferred by the executor · '
             f'{np_["check_rows"]} CHECK row{"" if np_["check_rows"] == 1 else "s"})  ')
    ad = g['ai_decisions']; r = ad.get('reviewed')
    L.append(f'**AI decisions:** {_n(ad["count"])} in the work order, ' + (
        f'approved by {r["reviewer"]} on {r["date"]} ({r["changed"]} changed)' if r and g['ship'][0]['ok'] else
        f'reviewed by {r["reviewer"]} on {r["date"]} ({r["changed"]} changed), not signed off (see "Ready to ship?")' if r else
        'applied without review by a person') + '  ')
    if g['fixed_automatically']:
        L.append('**Fixed automatically (no AI):** ' + ' · '.join(f'{x["what"]} {_n(x["count"])}' for x in sorted(g['fixed_automatically'], key=lambda x: -x['count'])) + '  ')
    vg = g['verapdf']
    if vg.get('ran_after'):
        def rc(r, c): return f'{r} WCAG rule{"" if r == 1 else "s"} failing'
        L.append('**veraPDF (WCAG 2.2 machine checks):** '
                 + (f'{rc(vg["before_rules"], 0)} before ({_n(vg["before_checks"])} check{"" if vg["before_checks"] == 1 else "s"}) → ' if vg.get('ran_before') else 'not run on the original → ')
                 + f'{vg["after_rules"]} after ({_n(vg["after_checks"])} check{"" if vg["after_checks"] == 1 else "s"})'
                 + (f' · {len(vg["newly_failing"])} newly failing' if 'newly_failing' in vg else ''))
    else: L.append(f'**veraPDF (WCAG 2.2 machine checks):** {vg.get("not_run") or "not run"}')
    L += ['', 'Automated checks are evidence, not sign-off.', '']
    iss = g['issues']
    if iss:
        L += ['| Top issues | Pages | Where |', '|---|---|---|']
        for x in iss[:top]:
            w = x['where']; ref = f'[§{w["n"]}](#{w["anchor"]})' if w['n'] else f'[{w["title"]}](#{w["anchor"]})'
            t = x.get('text_md') or (x['text'] if x['kind'] != 'ai' or len(x['text']) <= 110 else x['text'][:108].rstrip() + '…')   # review.md keeps its short form
            L.append(f'| {t.replace("|", "/")} | {x["pages_text"] or "see " + ("§" + str(w["n"]) if w["n"] else w["title"])} | {ref} |')
        if len(iss) > top:
            rest = iss[top:]; ns = sorted({x['where']['n'] for x in rest if x['where']['n']})
            L.append(f'| … and {len(rest)} more | | ' + (', '.join(f'§{n}' for n in ns) or 'Automated checks') + ' |')
    else: L.append('Nothing needs a person.')
    return L + ['']

def replace_block(md, block_lines):
    """review.md with its "## Overview" block (or an older run's "## At a glance") replaced, or inserted before the evidence
    line above "## Automated checks"."""
    lines = md.split('\n')
    old = next((h for h in ('## Overview', '## At a glance') if h in lines), None)
    if old:                                            # take the old block out: up to the evidence line or the next section
        i = lines.index(old)
        j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith('## ')
                  or lines[k].startswith('Automated checks are evidence, not legal sign-off')), len(lines))
        lines = lines[:i] + lines[j:]
    anchor = next((k for k, l in enumerate(lines) if l.startswith('Automated checks are evidence, not legal sign-off')), None)
    if anchor is None: anchor = next((k for k, l in enumerate(lines) if l == '## Automated checks'), len(lines))
    return '\n'.join(lines[:anchor] + block_lines + lines[anchor:])

def refresh(record, labels=None, han_pages=None):
    """For a run with record.json `sections`: recompute the glance from them and put the new "Overview" block in place
    (the lines after it, the evidence line and the blank, are kept). Returns review.md's text, drawn from the sections."""
    from lib import sections as S
    secs = record['sections']
    record['glance'] = glance(record, None, labels, han_pages, sections=secs)
    new = next(x for x in S.to_sections(glance_md(record['glance'])) if x['key'] == 'overview')
    for k, x in enumerate(secs):
        if x.get('key') in ('overview', 'at-a-glance'):          # 'at-a-glance': runs made before the rename
            tail = next((j for j, it in enumerate(x['items']) if it['text'].startswith('Automated checks are evidence, not legal sign-off')), len(x['items']))
            new['items'] = new['items'] + x['items'][tail:]
            secs[k] = new; break
    return '\n'.join(S.render_md(secs)) + '\n'
