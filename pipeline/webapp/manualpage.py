"""webapp/manualpage.py: the Accessibility Evaluation page (issue #38, stage 2; "Manual Checks" in the records and the code) and
the run page's strip after "Ready to Ship?". The app
serves the page itself; recording and drafts go through review/manual.py (the one writer, also manual_checks.py's), so
the app adds no rule of its own: lib/release.py's checklist and validate() are the one source.

    state(R, run)        the page's data (what it shows; the disk hash once, as data, for Record's shown_sha256)
    page(R, run, msg)    the page's HTML: escaped throughout, its data in a JSON block (<, > and & escaped), /app/manual.js
    strip(R, rec)        the strip's data for /api/run/<run> (webapp/runs.py state(): manual)
    disk_sha(path)       the remediated PDF's sha256 for display only, cached by (path, size, mtime_ns, ino, ctime_ns);
                         Record never uses it: review/manual.py hashes the file afresh under the record lock

Plain words for library staff: no file names, hashes, folder or option names on the page; a version is "the version from
Session 6"; a language is named, never shown as its code.
"""
import os, json, html, threading, urllib.parse
from lib import release as REL, glance as G, langtag, dates as D
from lib.titles import title_case as TC
from review import sessions as S, manual as M            # imported at the app's start: manual.CODE is the running code's

def E(x): return html.escape('' if x is None else str(x))   # every value escaped, whatever its type
_cache, _cache_lock = {}, threading.Lock()

def disk_sha(p):
    """The file's sha256, cached by (path, size, mtime_ns, inode, ctime_ns): for display only."""
    try: st = os.stat(p)
    except OSError: return None
    key = (os.path.realpath(p), st.st_size, st.st_mtime_ns, st.st_ino, st.st_ctime_ns)
    with _cache_lock:
        if key in _cache: return _cache[key]
    h = REL.sha_file(p)
    with _cache_lock:
        for k in [k for k in _cache if k[0] == key[0]]: del _cache[k]
        _cache[key] = h
    return h

def _rec(R): return S.load(os.path.join(R, 'record.json')) or {}

def disk_state(R, rec):
    """{same: True | False | None, sha}: None when the record has no output_sha256 yet (every run made before 2026-11:
    the first Record takes the disk hash, after stage 1's session cross-check), never "changed" for them."""
    out = (rec.get('document') or {}).get('output')
    p = os.path.join(R, out) if out else None
    sha = disk_sha(p) if p and os.path.isfile(p) else None
    want = (rec.get('document') or {}).get('output_sha256')
    return {'same': None if not want or sha is None else sha == want, 'sha': sha, 'missing': sha is None}

def app_sha(R, rec):
    """The current version's hash as the app sees it: the file on disk's (cached), else the record's output_sha256. The
    status, `ready` and status['current'] (Mark as Shipped's gate, stage 4) are worked out against it (review 16 J1)."""
    return disk_state(R, rec)['sha'] or (rec.get('document') or {}).get('output_sha256')

CHANGED_BY_HAND = ('The book\'s PDF has changed since this report was made, so no check can be recorded for it. '
                   'Whoever looks after the app can check it.')
MISSING = 'The book\'s remediated PDF is missing, so no check can be recorded for it. Whoever looks after the app can check it.'

def refusal(R, rec, disk):
    if disk['missing']: return MISSING
    why = M.being_made(R)
    if why: return why
    if disk['same'] is False: return CHANGED_BY_HAND
    if disk['same'] is None and not why:                 # no recorded hash yet: the first Record's adopt_hash check, shown now (G6)
        sid = (rec.get('review') or {}).get('session')
        want = (((S.session(R, sid) if sid else None) or {}).get('version') or {}).get('pdf_sha256')
        if want and disk['sha'] and want != disk['sha']: return M.NOT_LAST_REVIEW
    return None

def version(R, rec):
    """The current version in words: ("the version from Session 6", "applied on October 30, 2026 at 2:02 PM")."""
    sid = S.current_id(rec)
    if str(sid).isdigit():
        s = S.session(R, sid) or {}
        when = s.get('applied') or rec.get('written') or ''
        return {'session': sid, 'label': f'the version from Session {int(sid)}', 'when': _when(when, 'applied')}
    return {'session': None, 'label': 'the version applied without a review', 'when': _when(rec.get('written') or '', 'made')}

def _when(iso, verb): return f'{verb} on {D.when(iso)}' if str(iso or '').strip() else ''

def ver_label(c, cur):
    if REL.sha_of(c) == cur: return 'this version'
    s = (c.get('pdf') or {}).get('session')
    return f'an earlier version (Session {int(s)})' if str(s or '').isdigit() else 'an earlier version'

def book(rec):
    """The remediated PDF's own title (verify read it from that file), else the original's name without ".pdf"; and its
    language by name."""
    doc = ((rec.get('verify') or {}).get('doc') or {})
    title = (doc.get('title') or doc.get('xmp_title') or '').strip()
    if not title:
        f = (rec.get('document') or {}).get('file') or ''
        title = f[:-4] if f.lower().endswith('.pdf') else f
    lang = doc.get('lang')
    return {'title': title or 'this book', 'lang': langtag.norm(lang) if lang else None, 'lang_name': langtag.name(lang) if lang else None}

def lang_words(b):
    if not b['lang']: return 'not set'
    return b['lang_name'] or 'a language the app can\'t name; it is in the report'

NOUN = {'figures': 'figures', 'tables': 'tables', 'links': 'links', 'lists': 'lists', 'formulas': 'formulas', 'ocr_pages': 'OCR text'}
SECTION_ID = {'pac': 'pac', 'screen_reader': 'screen-reader'}
RECORD_LABEL = {'pac': 'Record the PAC 2026 Results', 'screen_reader': 'Record the Screen-Reader Test Results'}

def state(R, run):
    R = os.path.abspath(R); rec = _rec(R)
    import report_html as H
    rel = REL.load(R, rec); disk = disk_state(R, rec)
    cur = disk['sha'] or (rec.get('document') or {}).get('output_sha256')   # the file on disk (J1); none: the record's
    try: g = G.with_release(H.glance_of(R, rec), rec, rel, cur=cur)
    except Exception: g = G.with_release(rec.get('glance') or {'ship': []}, rec, rel, cur=cur)
    fnd = REL.found(rec); drafts = M.load_drafts(R)
    secs = {}
    for sec in REL.SECTIONS:
        xs = rel['checks'].get(sec) or []
        current = REL.latest(rel, sec, cur)
        earlier = [dict(c, version=ver_label(c, cur), failed=REL.issues(c, sec)) for c in reversed(xs) if c is not current]
        items = []
        for x in REL.CHECKLIST[sec]:
            hint = None
            if x.get('found'):
                hint = f'This book has {fnd[x["found"]]}.' if x['found'] in fnd else f'This book has no {NOUN[x["found"]]}: usually Not Applicable.'
            items.append({'key': x['key'], 'label': x['label'], 'help': x['help'], 'pages': bool(x.get('pages')), 'optional': bool(x.get('optional')),
                          'results': [{'value': r, 'label': REL.RESULT_NAMES[r]} for r in x['results']], 'found': x.get('found') in fnd, 'hint': hint})
        d = drafts.get(sec) or {}
        draft = d if d.get('data') and d.get('for_sha256') == cur else None
        draft_earlier = d if d.get('data') and d.get('for_sha256') != cur else None
        secs[sec] = {'key': sec, 'id': SECTION_ID[sec], 'name': REL.SECTION_NAMES[sec], 'record': RECORD_LABEL[sec],
                     'fields': [{'key': k, 'label': lab, 'required': req} for k, (lab, req) in REL.FIELDS[sec].items()],
                     'items': items,
                     'current': dict(current, state=REL.state(rel, sec, current, cur), failed=REL.issues(current, sec)) if current else None,
                     'earlier': earlier,
                     'draft': {'data': draft['data'], 'saved_at': draft['saved_at']} if draft else None,
                     'draft_earlier': {'data': draft_earlier['data'], 'from': 'an earlier version'} if draft_earlier else None,
                     'tombstone': d.get('cleared'),
                     'failed_last': REL.issues(current, sec) if current else []}
    st = g.get('status') or {}
    base = '/run/' + '/'.join(urllib.parse.quote(x, safe='') for x in run.split('/')) + '/'
    return {'run': run, 'base': base, 'book': book(rec), 'version': version(R, rec), 'sha': disk['sha'], 'disk': {'same': disk['same']},
            'status': st.get('text') or ('Ready' if g.get('ready') else 'Not Ready'), 'status_name': st.get('name'), 'newer': st.get('newer'),
            'ready': {'answer': 'Yes' if g.get('ready') else 'No', 'lines': [{'what': x['what'], 'name': G.ship_name(x), 'ok': x['ok'], 'text': x['text']} for x in g.get('ship') or []]},
            'needs': (g.get('needs_person') or {}).get('total'), 'refusal': refusal(R, rec, disk), 'sections': secs}

# ------------------------------------------------------------------ the strip (run page), from /api/run/<run>
def strip(R, rec):
    """The strip's data: one line per section, the live status (with the card's, to say when they differ), the disk
    check and any refusal. Cheap: the cached disk hash and the stored glance with release/ worked out now."""
    R = os.path.abspath(R); rel = REL.load(R, rec); disk = disk_state(R, rec)
    cur = disk['sha'] or (rec.get('document') or {}).get('output_sha256')   # the file on disk (J1)
    out = {}
    for sec in REL.SECTIONS:
        p = REL.part(rel, sec, cur); c = p['check']
        words = {'completed': lambda: f'completed on this version ({c.get("by")}, {D.day(c.get("recorded"))})' + (f' · {REL.noted(len(p["issues"]))}' if p['issues'] else ''),
                 'could not be read': lambda: 'could not be read in full: record it again',
                 'earlier version': lambda: 'completed on an earlier version: evaluate this version',
                 'not recorded': lambda: 'not completed'}[p['state']]()
        out[sec] = {'name': REL.SECTION_NAMES[sec], 'id': SECTION_ID[sec], 'words': words, 'ok': p['state'] == 'completed'}
    g0 = rec.get('glance') or {}
    try: live = G.with_release(g0 if g0.get('ship') else {'ship': []}, rec, rel, cur=cur).get('status') or {}
    except (KeyError, TypeError, ValueError): live = {}
    card = (g0.get('status') or {})
    return {'sections': out, 'status': live.get('text'), 'newer': live.get('newer'),
            'card_status': card.get('text'), 'card_newer': card.get('newer'),
            'disk_same': disk['same'], 'refusal': refusal(R, rec, disk)}

# ------------------------------------------------------------------ the page's HTML
def _json_block(obj):
    """JSON safe inside <script type="application/json">: <, > and & escaped, so a note holding "</script>" stays text."""
    return json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

def _fid(p, field): return f'{p}-{field.replace(".", "-")}'

def _result_table(sec_key, c):
    rows = []; items = c.get('items') or {}
    for x in REL.CHECKLIST[sec_key] + list(REL.RETIRED[sec_key]['items'].values()):
        retired = x['key'] in REL.RETIRED[sec_key]['items']
        if retired and x['key'] not in items: continue                 # an older record's retired row: shown as recorded
        it = items.get(x['key']) or {}
        res = REL.RESULT_NAMES.get(it.get('result'), 'Not answered')
        bold = it.get('result') == 'fail'
        rows.append(f'<tr><th scope="row" class="mc-item-c">{E(x["label"])}{" (no longer asked)" if retired else ""}</th>'
                    f'<td class="mc-res">{"<strong>" + E(res) + "</strong>" if bold else E(res)}</td><td class="mc-note">{E(it.get("note") or "")}</td></tr>')
    f = c.get('fields') or {}
    fields = [f'{E(lab)}: {E(f[k])}' for k, (lab, _) in REL.FIELDS[sec_key].items() if f.get(k)] \
        + [f'{E(lab)} (no longer asked): {E(f[k])}' for k, lab in REL.RETIRED[sec_key]['fields'].items() if f.get(k)]
    if f.get('pages_checked'): fields.append(f'Pages Checked: {E(f["pages_checked"])}')
    return ((f'<p>{" · ".join(fields)}</p>' if fields else '') +
            '<div class="mc-tw"><table><thead><tr><th scope="col">Item</th><th scope="col">Result</th><th scope="col">Notes</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div>' + (f'<p><strong>Other Notes:</strong></p><p class="mc-pre">{E(c["notes"])}</p>' if c.get('notes') else ''))

def _form(st, s, p):
    """The section's form: filled from its draft (same version) when there is one; manual.js keeps it saved."""
    d = (s.get('draft') or {}).get('data') or {}
    fv = d.get('fields') or {}; iv = d.get('items') or {}
    out = [f'<form id="{p}-form" class="mc-form" data-section="{s["key"]}" novalidate>',
           f'<div id="{p}-errs" class="mc-errsum" tabindex="-1" role="group" aria-labelledby="{p}-errs-h" hidden></div>']
    def field(key, label, required, value, hint=None):
        fid = _fid(p, key); req = '' if required else ' <span class="mc-opt">(optional)</span>'
        return (f'<div class="mc-field"><label for="{fid}">{E(TC(label))}{req}</label>' + (f'<p class="mc-help" id="{fid}-help">{E(hint)}</p>' if hint else '') +
                f'<input type="text" id="{fid}" data-field="{E(key)}" value="{E(value or "")}" autocomplete="{"name" if key == "by" else "off"}"'
                + (' aria-required="true"' if required else '') + f' aria-describedby="{fid}-err' + (f' {fid}-help' if hint else '') + '">'
                f'<p class="mc-err" id="{fid}-err" hidden></p></div>')
    out.append(field('by', 'Checked By', True, d.get('by')))
    for f in s['fields']:
        out.append(field(f'fields.{f["key"]}', f['label'], f['required'], fv.get(f['key'])))
    failed_last = set(s.get('failed_last') or [])
    for it in s['items']:
        k = it['key']; base = _fid(p, f'items.{k}'); v = iv.get(k) or {}
        legend = E(it['label']) + (' <span class="mc-opt">(optional)</span>' if it['optional'] else '')
        h = [f'<fieldset class="mc-item" id="{base}-result" data-item="{E(k)}" aria-describedby="{base}-help{" " + base + "-hint" if it["hint"] else ""}{" " + base + "-last" if k in failed_last else ""} {base}-result-err">',
             f'<legend>{legend}</legend><p class="mc-help" id="{base}-help">{E(it["help"])}</p>']
        if it['hint']: h.append(f'<p class="mc-hint" id="{base}-hint">{E(it["hint"])}</p>')
        if k in failed_last: h.append(f'<p class="mc-hint" id="{base}-last">This item failed in the last results recorded for this version: say in its notes what changed.</p>')
        if k == 'title_language':
            b = st['book']
            h.append(f'<p class="mc-hint">Title: <span{(" lang=" + chr(34) + E(b["lang"]) + chr(34)) if b["lang"] else ""}>{E(b["title"])}</span> · Language: {E(lang_words(b))}</p>')
        if k == 'needs_person':
            n = st.get('needs'); h.append(f'<p class="mc-hint">The report lists {E(n if n is not None else "some")} item{"" if n == 1 else "s"}: '
                                          f'<a href="{E(st["base"])}#iss-h">the report\'s list</a>.</p>')
        h.append('<div class="mc-radios">' + ''.join(
            f'<label><input type="radio" name="{base}-r" value="{E(r["value"])}" data-item="{E(k)}"{" checked" if v.get("result") == r["value"] else ""}> {E(r["label"])}</label>'
            for r in it['results']) + '</div>')
        h.append(f'<p class="mc-err" id="{base}-result-err" hidden></p>')
        if it['pages']:
            pid = _fid(p, 'fields.pages_checked')
            h.append(f'<div class="mc-field"><label for="{pid}">Pages Checked <span class="mc-opt">(optional)</span></label><p class="mc-help" id="{pid}-help">PDF page numbers and ranges, for example 5, 9-12.</p>'
                     f'<input type="text" id="{pid}" data-field="fields.pages_checked" value="{E(fv.get("pages_checked") or "")}" autocomplete="off" aria-describedby="{pid}-err {pid}-help">'
                     f'<p class="mc-err" id="{pid}-err" hidden></p></div>')
        nid = f'{base}-note'
        h.append(f'<div class="mc-field"><label for="{nid}">Notes <span class="mc-opt" data-req-for="{E(k)}">(optional)</span></label>'
                 f'<textarea id="{nid}" data-note="{E(k)}" rows="2" aria-describedby="{nid}-err">{E(v.get("note") or "")}</textarea>'
                 f'<p class="mc-err" id="{nid}-err" hidden></p></div></fieldset>')
        out.append(''.join(h))
    if s['key'] == 'screen_reader':
        nid = _fid(p, 'notes')
        out.append(f'<div class="mc-field"><label for="{nid}">Other Notes <span class="mc-opt">(optional)</span></label>'
                   f'<textarea id="{nid}" data-field="notes" rows="4" aria-describedby="{nid}-err">{E(d.get("notes") or "")}</textarea><p class="mc-err" id="{nid}-err" hidden></p></div>')
    dis = ' disabled aria-describedby="mc-refusal"' if st.get('refusal') else ''
    out.append(f'<div class="mc-actions"><button type="submit" class="pp-primary"{dis}>{E(s["record"])}</button>'
               f'<span class="mc-save" id="{p}-save"></span></div></form>')
    return ''.join(out)

def message(st, recorded):
    """After Record: what was recorded and what it changed (the page reloads with ?recorded=<section>); "Review Again" after
    any result with a Fail (2026-10-31: a Fail never blocks, it is kept for a person to fix)."""
    s = (st['sections'] or {}).get(recorded)
    if not s or not s.get('current'): return None
    other = 'screen_reader' if recorded == 'pac' else 'pac'
    oc = (st['sections'].get(other) or {}).get('current')
    done = bool(oc) and oc.get('state') == 'completed'
    n = len(s['current'].get('failed') or [])
    t = (f'{REL.SECTION_NAMES[recorded]} results recorded for this version. '
         + ('"Accessibility Evaluation" is now satisfied.' if done and s['current'].get('state') == 'completed' else
            f'"Accessibility Evaluation" is satisfied once {"PAC 2026" if other == "pac" else "the Screen-Reader Test"} is recorded for this version too.')
         + (f' {REL.noted(n).capitalize()}: {"it is" if n == 1 else "they are"} kept in the report for a person to fix.' if n else ''))
    return t, bool(n)

def page(R, run, recorded=None):
    st = state(R, run); p_of = {'pac': 'pac', 'screen_reader': 'sr'}
    msg = message(st, recorded) if recorded in REL.SECTIONS else None
    b = st['book']; lang = f' lang="{E(b["lang"])}"' if b['lang'] else ''
    ready = st['ready']; why = [x for x in ready['lines'] if not x['ok']]
    B = [f'<header><h1>Accessibility Evaluation</h1><p class="mc-book">PDF Title: <span{lang}>{E(b["title"])}</span></p></header>',
         f'<nav class="pp-wrap" aria-label="This page"><p class="pp pp-bar mc-nav"><a class="pp-btn" href="{E(st["base"])}">Back to the Run Page</a></p></nav>',
         '<main id="main" tabindex="-1"><div class="pp mc">']
    if msg:
        B.append(f'<div id="mc-msg" class="pp-msg pp-okmsg" tabindex="-1"><span class="pp-msg-t">{E(msg[0])}</span>'
                 + ('<button type="button" id="mc-review" class="pp-primary">Review Again</button>' if msg[1] else '') + '</div>')
    v = st['version']
    B.append(f'<p>These results are recorded for {E(v["label"])}' + (f', {E(v["when"])}' if v['when'] else '') + '.</p>'
             '<p class="mc-help">Complete the evaluation after the last review is applied: a new version needs its own evaluation.</p>'
             f'<p class="mc-status">Overall Status: <strong>{E(st["status"])}</strong>' + (f' · {E(st["newer"])}' if st.get('newer') else '')
             + (f' · Unsatisfied Requirements: {E(", ".join(x["name"] for x in why))}' if st.get('status_name') == REL.NOT_READY and why else '') + '</p>'
             '<p class="mc-help">Every item needs a result, and a Fail needs a note. A Fail does not hold the book back: it is kept in the report, '
             'with its note, for a person to fix later.</p>')
    if st['refusal']: B.append(f'<p id="mc-refusal" class="mc-refusal">{E(st["refusal"])} Your answers are still saved as you type.</p>')
    for key in REL.SECTIONS:
        s = st['sections'][key]; p = p_of[key]
        B.append(f'<section id="{s["id"]}" class="mc-sec" aria-labelledby="{p}-h"><h2 id="{p}-h" tabindex="-1">{E(s["name"])}</h2>')
        c = s['current']
        if c:
            n = len(c['failed'] or [])
            words = {'completed': 'Completed for this version' + (f', with {REL.noted(n)}' if n else ''),
                     'could not be read': 'Could not be read in full: record it again'}.get(c['state'], c['state'])
            B.append(f'<h3>Current Results: {E(c.get("by"))}, {E(D.day(c.get("recorded")))}</h3><p>{E(words)}.</p>' + _result_table(key, c))
        if s['earlier']:                                 # its own h3, so the h4s below sit under it (review 12 G2)
            ne = len(s['earlier'])
            B.append(f'<h3>Earlier Results ({ne})</h3><details class="mc-earlier"><summary>Show the {ne} Earlier Result{"" if ne == 1 else "s"}</summary>')
            for i, e in enumerate(s['earlier']):
                B.append(f'<h4>{E(e.get("by"))}, {E(D.day(e.get("recorded")))}: on {E(e["version"])}</h4>' + _result_table(key, e)
                         + (f'<p><button type="button" data-start="{E(key)}:{i}">Start from These Notes</button></p>' if e['version'] != 'this version' else ''))
            B.append('</details>')
        if s['draft_earlier']:
            B.append(f'<p class="mc-hint">Your unfinished results were started on {E(s["draft_earlier"]["from"])}. Their answers are not used for this version. '
                     f'<button type="button" data-start="{E(key)}:draft">Start from These Notes</button></p>')
        B.append(f'<h3>{"Record New Results" if c else "Record the Results"}</h3>'
                 + ('<p class="mc-help">New results for this version replace the current ones as the ones that count; the earlier ones stay in the record.</p>' if c else '')
                 + _form(st, s, p) + '</section>')
    B.append('</div></main><div id="mc-live" class="pp-sr" role="status" aria-live="polite" aria-atomic="true"></div>'
             '<div id="mc-alert" class="pp-sr" role="alert"></div>')
    data = {k: st[k] for k in ('run', 'base', 'sha')}
    data['sections'] = {k: {'id': v['id'], 'p': p_of[k], 'draft_saved_at': (v['draft'] or {}).get('saved_at'), 'tombstone': v['tombstone'],
                            'items': [{'key': i['key'], 'found': i['found']} for i in v['items']], 'failed_last': v['failed_last'],
                            'starts': [{'by': e.get('by'), 'fields': e.get('fields') or {}, 'items': {ik: {'note': (iv or {}).get('note') or ''} for ik, iv in (e.get('items') or {}).items()},
                                        'notes': e.get('notes') or ''} for e in v['earlier']],
                            'start_draft': (v['draft_earlier'] or {}).get('data'), 'has_draft': bool(v['draft'])} for k, v in st['sections'].items()}
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Accessibility Evaluation: {E(b["title"])}</title><link rel="stylesheet" href="/app/palette.css"><link rel="stylesheet" href="/app/panel.css"></head>'
            '<body class="pp-page mc-page"><a class="skip" href="#main">Skip to the content</a>' + ''.join(B) +
            f'<script type="application/json" id="mc-data">{_json_block(data)}</script><script src="/app/manual.js" defer></script></body></html>')
