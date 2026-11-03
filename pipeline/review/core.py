"""review/core.py: the review step's logic, with no web server and no HTML (a later front end can call it directly).

    ro    = reading_order(digest, fulltext, wo)      # the original's reading order, for the page's reading-order list
    items = build_items(wo, digest, ro['entries'], ro)   # every decision in the work order, with its context and priority group,
                                                      # and the reading order's findings no decision answers (seen only)
    adds  = addable(wo, digest)                       # what a person can add that the AI did not decide (an H1, an alt, …)
    wo2   = apply_decisions(ai_wo, items, decisions)  # a person's approve / change / reject applied to a copy of the AI's order
    refused = add_entries(wo2, additions, adds, reviewer)   # the person's own decisions added to it
    dropped, gaps = preview(R, wo2)                   # what the check would drop, and what is still missing (no H1, figures without alt)
    probs, gaps = problems(R, ai_wo, items, decisions, additions, adds)   # the same check, each problem on the card it belongs to
    changes = diff(ai_wo, wo2)                        # what the person changed, item by item
    finish(R, ai_wo, wo2, reviewer, date, method, …)  # checks the order again, writes review.json and the reviewed workorder.json
    draft_pdf(R, pdf, ai_wo, wo2, out, …)            # the same check, then apply.py into out (a draft: nothing in R is written)

The formats a front end needs (also in docs/review-step.md):
  item:      {id, key, kind, label, page, page_label, pages, before, ai, edit, options, context, priority, images}
  addable:   {kind: [{id, kind, target, label, page, page_label, before, default, edit, options, context, images}]}
  decisions: {id: {status: approved | changed | rejected | seen, value?, note?}}
  additions: [{kind, target, value, note?}]
  reading order: {entries: [lib/readorder.py entries], flagged: [{i, first, last, prev, next, hidden_by?, hidden_by_rules?}],
                 late: [{i, first, last, after, hidden_by?, hidden_by_rules?}],
                 flat, detail, page_jumps}
"""
import os, re, sys, copy, json, time, shutil, datetime, tempfile, subprocess, threading, unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import workorder_check, readorder, gaptext  # noqa: E402

LEVELS = sorted(workorder_check.ALLOWED - {'Figure'}, key=lambda t: (not t.startswith('H'), t))
HEADING = {'H1', 'H2', 'H3', 'H4', 'H5', 'H6'}
GROUPS = {1: 'H1 and title', 2: 'Style-wide mappings', 3: 'Heading-level changes', 4: 'Rules that can hide text',
          5: 'Reading order', 6: 'Pages the AI asked about', 7: 'General'}
READING = ('move_section', 'move_to_document_start', 'adopt_orphans')   # decisions that change the reading order
MOVES_CONTENT = ('captions',)                         # other keys that move content (a caption into its figure's Div): group 5 too
SEEN_ONLY = {'deferrals', 'notes_for_reviewer', 'reading_order'}   # not applied by apply.py: a person marks them seen, with a note
LATE_LISTED = 12                                       # sections named on the "read late" card (the panel lists them all)
PAGE_REF = re.compile(r'PDF (\d+)(?:\s*[–-]\s*(\d+))?')
PAGE_PNG = re.compile(r'(\d+)\.png$')
ADD_KINDS = {'retype': 'Heading or tag change', 'alt': 'Alt text', 'page_figures': 'Alt text', 'tables': 'Table headers',
             'rolemap': 'Style mapping', 'document': 'Document', 'ocr_words': 'OCR words', 'move_section': 'Section move'}
MAPPABLE = workorder_check.ALLOWED - {'Figure'} | {'H'}  # a style mapped to one of these can be given a new level

def save(path, obj):
    """Through a temp file and os.replace, so a stop mid-write never leaves a cut-short JSON file. The temp file is this
    process and thread's own, so two writers never share one."""
    tmp = f'{path}.{os.getpid()}.{threading.get_ident()}.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f: f.write(json.dumps(obj, ensure_ascii=False, indent=1))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def load(path, default=None):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default

# ------------------------------------------------------------------ session names and notes (plain text a person types)
NAME_MAX, NOTES_MAX = 80, 4000                         # in code points; the page's maxlength (UTF-16 units) is the stricter
BIDI = re.compile(f'[{chr(0x202a)}-{chr(0x202e)}{chr(0x2066)}-{chr(0x2069)}]')   # direction overrides (U+202A–202E, U+2066–2069):
                                                       # they can make a name read differently elsewhere

def clean_text(s, one_line=False):
    """A person's text as kept: CRLF as LF, no control characters but newline and tab, no direction overrides (ZWJ and
    ZWNJ stay: some scripts need them); one_line: every run of white space as one space."""
    s = BIDI.sub('', str(s or '').replace('\r\n', '\n').replace('\r', '\n'))
    s = ''.join(c for c in s if c in '\n\t' or unicodedata.category(c) != 'Cc')
    return ' '.join(s.split()) if one_line else s.strip()

def session_fields(body, sid):
    """(name, notes) from the page's session_name / session_notes, cleaned; a name that is only "Session N" (up to case and
    spacing) or empty is no name. Raises ValueError over the limits."""
    name = clean_text(body.get('session_name'), one_line=True)
    notes = clean_text(body.get('session_notes'))
    if len(name) > NAME_MAX: raise ValueError(f'The session name is {len(name)} characters long; at most {NAME_MAX}.')
    if len(notes) > NOTES_MAX: raise ValueError(f'The session notes are {len(notes):,} characters long; at most {NOTES_MAX:,}.')
    if name.lower() in ('', f'session {int(sid)}' if str(sid).isdigit() else ''): name = ''
    return name or None, notes or None

# ------------------------------------------------------------------ items
def _index(digest):
    """The digest's lists by object, style, page and word id: what the items and the addable targets are looked up in."""
    labels = {}
    for row in digest.get('page_map') or []:
        p, lab = (str(row).split('|') + ['', ''])[:2]
        if p.isdigit(): labels[int(p)] = lab
    by_obj = {}
    for k in ('elements', 'heading_candidates', 'headings', 'figures', 'lists', 'tables'):
        for x in digest.get(k) or []: by_obj.setdefault(x['obj'], {**x, '_from': k})
    sheet_of = {}                                       # word id -> (sheet image, its cell on the sheet, when the audit recorded it)
    for sh in digest.get('ocr_word_sheets') or []:
        for i in range(sh['ids'][0], sh['ids'][1] + 1): sheet_of[i] = (sh['image'], (sh.get('cells') or {}).get(str(i)))
    return (labels, by_obj, {s['style']: s for s in digest.get('styles') or []}, {f['obj']: f for f in digest.get('figures') or []},
            {pf['page']: pf for pf in digest.get('page_figures') or []}, {w['id']: w for w in digest.get('ocr_words') or []}, sheet_of)

def build_items(wo, digest, order=None, ro=None):
    """order: the reading order's entries, for the move preview. ro: the whole reading order (reading_order()); with it,
    each finding no decision answers becomes a card (seen only), and each text rule's card lists what it hides."""
    N = digest['source']['pages']
    labels, by_obj, styles, figs, pfigs, words, sheet_of = _index(digest)
    doc = digest.get('document') or {}
    items = []

    def add(id_, key, kind, loc, ai, label, page=None, before=None, edit=None, field=None, options=None, pages=None, **context):
        if context.get('confidence') is None and isinstance(ai, dict): context['confidence'] = ai.get('confidence')   # any kind of decision can carry one
        context = {k: v for k, v in context.items() if v not in (None, '', [])}
        items.append({'id': id_, 'key': key, 'kind': kind, 'loc': loc, 'field': field, 'ai': ai, 'before': before, 'label': label,
                      'page': page, 'page_label': labels.get(page) if page else None, 'pages': pages, 'edit': edit,
                      'options': options, 'context': context, 'priority': None, 'images': []})

    def level_of(obj):
        x = by_obj.get(obj) or {}
        return x.get('level') or x.get('style')

    for i, it in enumerate(wo.get('retype') or []):
        x = by_obj.get(it.get('obj')) or {}
        add(f'retype:{it.get("obj")}', 'retype', 'Heading or tag change', ['retype', i], it.get('type'), x.get('text') or it.get('obj'),
            page=x.get('page'), before=level_of(it.get('obj')), edit='level', field='type', options=sorted(workorder_check.ALLOWED, key=lambda t: (not t.startswith('H'), t)),
            why=it.get('why'), confidence=it.get('confidence'), obj=it.get('obj'))
    for s, t in (wo.get('rolemap') or {}).items():
        st = styles.get(s) or {}
        pr = st.get('pages') or [None, None]
        add(f'rolemap:{s}', 'rolemap', 'Style mapping', ['rolemap', s], t, f'Every "{s}" element',
            page=pr[0], pages=pr, before=st.get('maps_to'), edit='level', options=LEVELS,
            count=st.get('count'), samples=(st.get('samples') or [])[:4], style=s)
    for i, it in enumerate(wo.get('actual_text') or []):
        x = by_obj.get(it.get('obj')) or {}
        add(f'actual_text:{it.get("obj")}', 'actual_text', 'Spoken text', ['actual_text', i], it.get('text'), x.get('text') or it.get('obj'),
            page=x.get('page'), before=x.get('text'), edit='text', field='text', why=it.get('why'), obj=it.get('obj'))
    for i, it in enumerate(wo.get('merges') or []):
        add(f'merges:{i}', 'merges', 'Heading merge', ['merges', i], it,
            f'Merge "{it.get("style")}" into the {it.get("direction")} {"/".join(it.get("with") or [])}', why=it.get('why'))
    d = wo.get('document') or {}
    for k, v in d.items():
        add(f'document.{k}', 'document', 'Document', ['document', k], v, {'title': 'Title', 'lang': 'Language'}.get(k, k),
            before=doc.get(k), edit={'title': 'text', 'lang': 'lang'}.get(k))
    for i, it in enumerate(wo.get('alt') or []):
        f = figs.get(it.get('obj')) or {}
        add(f'alt:{it.get("obj")}', 'alt', 'Alt text', ['alt', i], it.get('alt'), f'Figure {it.get("obj")}', page=f.get('page'),
            before=f.get('alt'), edit='text', field='alt', figure=f.get('image'), area_pct=f.get('area_pct'), why=it.get('why'),
            confidence=it.get('confidence'), obj=it.get('obj'))
    for i, it in enumerate(wo.get('page_figures') or []):
        pf = pfigs.get(it.get('page')) or {}
        add(f'page_figures:{it.get("page")}', 'page_figures', 'Alt text', ['page_figures', i], it.get('alt'), f'Whole page {it.get("page")} as one figure',
            page=it.get('page'), edit='text', field='alt', figure=pf.get('image'), why=it.get('why'))
    for i, it in enumerate(wo.get('tables') or []):
        x = by_obj.get(it.get('obj')) or {}
        add(f'tables:{it.get("obj")}', 'tables', 'Table headers', ['tables', i],
            {'header_rows': it.get('header_rows', 0), 'header_cols': it.get('header_cols', 0)}, f'Table {it.get("obj")}', page=x.get('page'),
            before={'header_cells': x.get('header_cells')}, edit='table', first_rows=x.get('first_rows'), rows=x.get('rows'), cols=x.get('cols'),
            row_reading={k: it[k] for k in ('title_rows', 'note_rows', 'group_rows', 'repeat_rows') if it.get(k)},
            why=it.get('why'), obj=it.get('obj'))
    for key in ('flatten', 'keep_lists'):
        for i, it in enumerate(wo.get(key) or []):
            x = by_obj.get(it.get('obj')) or {}
            add(f'{key}:{it.get("obj")}', key, 'Lists and tables', [key, i], it,
                f'{x.get("_from", "elements")[:-1].capitalize()} {it.get("obj")}', page=x.get('page'),
                first=x.get('first_items') or x.get('first_rows'), why=it.get('why'))
    a = wo.get('artifacts') or {}
    for i, it in enumerate(a.get('elements') or []):
        f = figs.get(it.get('obj')) or {}
        add(f'artifacts.elements:{it.get("obj")}', 'artifacts', 'Decoration', ['artifacts', 'elements', i], it,
            f'Figure {it.get("obj")} as decoration' + (f' ({it["label"]})' if it.get('label') else ''), page=f.get('page'), figure=f.get('image'))
    for sub in ('text_rules', 'untagged'):
        for i, it in enumerate(a.get(sub) or []):
            pr = it.get('pages') or [None, None]
            add(f'artifacts.{sub}:{i}', 'artifacts', 'Decoration', ['artifacts', sub, i], it,
                it.get('label') or ('Text rule' if sub == 'text_rules' else 'Untagged content'), page=pr[0], pages=pr,
                regex=it.get('regex'), band=it.get('band'), where=it.get('where'), type=it.get('type'))
    for i, it in enumerate(wo.get('ocr_words') or []):
        w = words.get(it.get('id')) or {}
        sheet, cell = sheet_of.get(it.get('id'), (None, None))
        add(f'ocr_words:{it.get("id")}', 'ocr_words', 'OCR words', ['ocr_words', i], it.get('reads'), f'OCR read "{it.get("text")}"',
            page=(w.get('pages') or [None])[0], before=it.get('text'), edit='text', field='reads', count=it.get('count'),
            word=f'word/{it.get("id")}.png' if cell else None, sheet=None if cell else sheet, word_id=it.get('id'))
    for i, it in enumerate(wo.get('deferrals') or []):
        ps = [p for p in it.get('pages') or [] if isinstance(p, int)] if isinstance(it, dict) else []
        add(f'deferrals:{i}', 'deferrals', 'Deferred by the AI', ['deferrals', i], it, (it or {}).get('what') or 'Deferral',
            page=min(ps) if ps else None, pages=[min(ps), max(ps)] if ps else None, why=(it or {}).get('why'))
    mss = [(i, m) for i, m in enumerate(readorder.moves(wo)) if isinstance(m.get('pages'), list) and len(m['pages']) == 2]
    pvs = chain_previews(order, [(m['pages'], m.get('before_page')) for _, m in mss], (ro or {}).get('removed_by'))
    dr = (ro or {}).get('dryrun') or {}
    trials = dr.get('section_moves') or ([dr['section_move']] if dr.get('section_move') else [])
    for k, ((i, ms), pv) in enumerate(zip(mss, pvs)):            # card ids: move_section, then move_section:1, :2
        (a, b), c = ms['pages'], ms.get('before_page')
        add('move_section' if k == 0 else f'move_section:{k}', 'move_section', 'Reading order',
            ['move_section'] if isinstance(wo.get('move_section'), dict) else ['move_section', i], ms,
            f'Section on PDF {a}–{b} read before PDF {c}', page=a if isinstance(a, int) else None,
            pages=[a, b] if all(isinstance(x, int) for x in (a, b)) else None, edit='move', before_page=c, why=ms.get('why'),
            trial=trials[k] if k < len(trials) else None, move_number=k + 1 if len(mss) > 1 else None, **pv)
    for i, o in enumerate(wo.get('move_to_document_start') or []):
        f = figs.get(o) or {}
        add(f'move_to_document_start:{i}', 'move_to_document_start', 'Reading order', ['move_to_document_start', i], o,
            f'{"Figure" if f else "Element"} {o} read first', page=f.get('page') or 1, figure=f.get('image'), area_pct=f.get('area_pct'))
    for i, r in enumerate(wo.get('adopt_orphans') or []):
        ps = r.get('pages') if isinstance(r, dict) else None
        ps = ps if isinstance(ps, list) and len(ps) == 2 and all(isinstance(p, int) for p in ps) else None
        runs = [{'page': u['page'], 'runs': [x['text'] for x in u.get('runs') or [] if x.get('kind') == 'orphan' and (x.get('text') or '').strip()], 'count': u.get('orphan_runs')}
                for u in digest.get('unowned_content') or [] if ps and ps[0] <= u.get('page', 0) <= ps[1] and u.get('orphan_runs')]
        add(f'adopt_orphans:{i}', 'adopt_orphans', 'Reading order', ['adopt_orphans', i], r, (r or {}).get('label') or 'Orphan text',
            page=ps[0] if ps else None, pages=ps, orphans=runs[:6])
    if wo.get('notes_for_reviewer'):
        refs = sorted({int(m.group(1)) for m in PAGE_REF.finditer(wo['notes_for_reviewer']) if 1 <= int(m.group(1)) <= N})
        add('notes_for_reviewer', 'notes_for_reviewer', 'Deferred by the AI', ['notes_for_reviewer'], wo['notes_for_reviewer'],
            'Note to the reviewer from the AI', page=refs[0] if refs else None, page_refs=refs)
    listed = {'retype', 'rolemap', 'actual_text', 'merges', 'document', 'alt', 'page_figures', 'tables', 'flatten', 'keep_lists',
              'artifacts', 'ocr_words', 'deferrals', 'notes_for_reviewer', 'schema', *READING} | workorder_check.META
    if figures_card(ro): listed.add('fix_figure_order')            # the Figures Moved card is that decision
    for k, v in wo.items():
        if k not in listed:
            add(f'key:{k}', k, 'Reading order' if k in MOVES_CONTENT else 'Other decisions', [k], v, k)
    if ro: _order_findings(ro, add, items, wo)

    # priority groups: fixed rules, no model
    for it in items:
        k, b, ai = it['key'], it['before'], it['ai']
        if k == 'document' and it['id'] == 'document.title': it['priority'] = 1
        elif k in ('retype', 'rolemap') and ('H1' in (b, ai)) and b != ai: it['priority'] = 1
        elif k == 'rolemap': it['priority'] = 2
        elif k == 'retype' and b != ai and (b in HEADING or ai in HEADING): it['priority'] = 3
        elif k == 'artifacts' and it['loc'][1] in ('text_rules', 'untagged'): it['priority'] = 4
        elif k in READING or k in MOVES_CONTENT or k == 'reading_order': it['priority'] = 5
        elif k == 'deferrals':
            p = it['pages']
            it['priority'] = 6 if p and (p[1] - p[0] + 1) <= N / 2 else 7
        elif k == 'notes_for_reviewer': it['priority'] = 6 if it['context'].get('page_refs') else 7
    return items

def order(items):
    """Priority items by group, then page (style mappings: most elements first)."""
    def key(it):
        g = it['priority']
        return (g, -(it['context'].get('count') or 0) if g == 2 else 0, it['page'] if it['page'] is not None else 10 ** 9)
    return sorted([it for it in items if it['priority']], key=key)

def page_images(it, N):
    """Page images to show beside an item or an addable target: its page, and the pages either side of a heading decision."""
    ps = [it['page']] if it['page'] else []
    if it['page'] and (it.get('priority') in (1, 3) or it['key'] == 'retype'): ps = [it['page'] - 1, it['page'], it['page'] + 1]
    if it['key'] == 'notes_for_reviewer': ps = it['context'].get('page_refs', [])[:6]
    if it['key'] == 'reading_order': ps = it['context'].get('show_pages', [])[:6]
    if it['key'] in READING and it.get('pages'):
        c = it['context'].get('before_page')
        ps = sorted(set(it['pages'] + ([c - 1, c] if it['key'] == 'move_section' and isinstance(c, int) else [])))[:6]
    return [f'review_pages/page_{p:03d}.png' for p in ps if 1 <= p <= N]

# ------------------------------------------------------------------ reading order
def reading_order(digest, fulltext=None, wo=None):
    """The original's reading order for the page's list: {entries, flagged, flat, detail}. From fulltext.json when the audit
    wrote it there (every container, with what move_section needs), else from the digest's lines (runs audited before
    that: sections only, and no move preview). flat: fewer than two containers, so there is no order to show. page_jumps:
    the original's pages whose text jumps back up a column (the 1.3.2 page check; None for older runs). late: small entries
    read well after their page (readorder.read_late). The work order takes care of some flagged and late entries:
      - every run matched by one of its text rules (one rule, or several together, as a running head's page number and
        its title): hidden_by_rules ([{id, label}]: those rules, by card id), run_rules (each run's rule ids, so the page
        can tell which rejections bring the entry back) and hidden_by (the first rule's label);
      - else made only of its captions style (and figures): captions tie it to its figure, so it is read with the figure
        (tied_by: {id: the captions card, label}). Needs the entry's kid_styles, from audits since they were recorded;
      - else flagged only because of siblings the text rules remove (a stray block read after the book's last section):
        once those are gone it is read in its place (cleared_by: each removed sibling's run_rules).
    removed: the indexes of the entries the text rules remove whole (any entry, flagged or not); removed_by: the same, as
    {entry id: [rule labels]}, for the move preview."""
    es = (fulltext or {}).get('reading_order')
    detail = es is not None
    if es is None: es = readorder.parse_lines(digest.get('reading_order'))
    fl = readorder.out_of_order(es)
    late = readorder.read_late(es, [x['i'] for x in fl])
    trs = ((wo or {}).get('artifacts') or {}).get('text_rules') or []
    labels = {f'artifacts.text_rules:{i}': (r.get('label') if isinstance(r, dict) else None) or 'text rule' for i, r in enumerate(trs)}
    cap = ((wo or {}).get('captions') or {}).get('style') if isinstance((wo or {}).get('captions'), dict) else None
    per = {i: run_rules(e, wo) for i, e in enumerate(es) if wo}
    removed = {i for i, p in per.items() if whole(p)}
    still = {x['i'] for x in readorder.out_of_order([dict(e, skip=True) if i in removed else e for i, e in enumerate(es)])}
    for x in fl + late:
        e = es[x['i']]
        if x['i'] in removed:
            ids = list(dict.fromkeys(i for p in per[x['i']] for i in p))
            x.update(run_rules=per[x['i']], hidden_by_rules=[{'id': i, 'label': labels[i]} for i in ids], hidden_by=labels[ids[0]])
        elif cap and e.get('kid_styles') and set(e['kid_styles']) <= {cap, 'Figure'}:
            x['tied_by'] = {'id': 'key:captions', 'label': f'captions (style “{cap}”) tied to their figures'}
        elif x in fl and x['i'] not in still:              # the removed siblings that put it out of place: read before it but
            i, f0 = x['i'], e['first']                      # printed after it, or read after it but printed before it
            x['cleared_by'] = [per[j] for j in sorted(removed) if es[j].get('parent') == e.get('parent') and es[j].get('first') is not None
                               and ((j < i and es[j]['first'] > f0) or (j > i and es[j]['first'] < f0))]
    removed_by = {es[i]['id']: list(dict.fromkeys(labels[r] for p in per[i] for r in p)) for i in sorted(removed)}
    return {'entries': es, 'flagged': fl, 'late': late, 'removed': sorted(removed), 'removed_by': removed_by, 'flat': len(es) < 2, 'detail': detail,
            'page_jumps': (fulltext or {}).get('page_jumps')}

def reading_order_for(audit_dir, digest, wo):
    """reading_order() from an audit folder's fulltext.json (when there is one), with the review's trial run of the
    executor (dryrun.json, when there is one) as dryrun."""
    ro = reading_order(digest, load(os.path.join(audit_dir, 'fulltext.json')), wo)
    ro['dryrun'] = load(os.path.join(audit_dir, 'dryrun.json'))
    return ro

def run_apply(pdf, wo, out, timeout=1800, env=None, low=False, on_start=None):
    """apply.py on pdf with the work order wo (a dict, written beside out), into out. Returns (exit code, out's log, or
    None when it wrote none). low: at a lower priority (nice 10, where there is nice), so the review page stays quick
    while it runs. on_start(process): the caller keeps the process, to stop it. A run past timeout is killed, and
    subprocess.TimeoutExpired raised."""
    path = os.path.join(os.path.dirname(out), 'workorder.json')
    save(path, wo)
    cmd = [sys.executable, os.path.join(HERE, 'apply.py'), pdf, path, out]
    if low and shutil.which('nice'): cmd = ['nice', '-n', '10'] + cmd
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if on_start: on_start(p)
    try: p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate(); raise
    return p.returncode, load(out + '.log.json')

def dry_run(R, pdf):
    """A trial run of apply.py with the AI's order (R/workorder.ai.json) on a temporary copy, for what the executor does on
    its own: the figures fix_figure_order moves back to their page (worked out with it on, even when the AI turned it off,
    so the card can show what turning it on or off changes); and what became of each of the AI's section moves
    (section_moves: [{made: where apply.py put it} or {refused: why}], in order; section_move: the first, or None when
    there is none). No model, nothing kept but the result: {figure_moves: [{page, label, was_after_page, now_after_page}],
    section_moves, section_move, seconds}, or {figure_moves: None, why}.
    REVIEW_DRYRUN=off skips it."""
    if os.environ.get('REVIEW_DRYRUN') == 'off': return {'figure_moves': None, 'why': 'skipped: REVIEW_DRYRUN=off'}
    print('  working out the figure moves and the section move: a trial run of apply.py on a copy (no model)…', flush=True)
    t, tmp = time.time(), tempfile.mkdtemp(prefix='dryrun-')
    try:
        ai = load(os.path.join(R, 'workorder.ai.json'))
        code, log = run_apply(pdf, {k: v for k, v in (ai or {}).items() if not (k == 'fix_figure_order' and v is False)},
                              os.path.join(tmp, 'out.pdf'))
        if code != 0 or log is None:
            return {'figure_moves': None, 'why': f'the trial run of apply.py stopped (exit {code})'}
        sm = section_moves(log)
        res = {'figure_moves': log.get('figure_moves') or [], 'seconds': round(time.time() - t, 1),
               'section_moves': sm, 'section_move': sm[0] if sm else None}
        print(f'  figure moves: {len(res["figure_moves"])} ({res["seconds"]}s)', flush=True)
        return res
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        return {'figure_moves': None, 'why': f'the trial run of apply.py could not run ({type(e).__name__})'}
    finally: shutil.rmtree(tmp, ignore_errors=True)

def section_moves(log):
    """What became of each section move in an apply.py log, in order: [{made: where it went} or {refused: why}]."""
    whys = [x.get('why') for x in log.get('rejected') or [] if isinstance(x, dict) and x.get('op') == 'move_section']
    return [{'made': m} if m else {'refused': whys.pop(0) if whys else 'refused'} for m in log.get('section_moves') or []]

def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def draft_pdf(R, pdf, ai_wo, wo, out, items=None, decisions=None, additions=None, on_start=None):
    """The review page's Build a Draft PDF: wo (the draft's order, as /save builds it) through the same check Finish uses,
    then apply.py into out, marked as a draft (APPLY_DRAFT=1). Nothing in R is written. Returns {dropped (how many entries
    the check left out: the page lists them from problems(), worded as on the cards), moves ([{card, made | refused}], in
    the executor's order), rejected (apply.py's other refusals), failed, seconds, bytes}. Raises ValueError, in the page's words, when it cannot be built; out is then removed."""
    t = time.time()
    want = (ai_wo.get('source') or {}).get('sha256')
    if not os.path.isfile(pdf or ''): raise ValueError('The book\'s PDF is no longer where the review started, so a draft cannot be built.')
    if want and sha256_file(pdf) != want: raise ValueError('The book\'s PDF has changed since the review started, so a draft cannot be built.')
    wo = copy.deepcopy(wo)
    dropped = check(R, wo)
    for f in (out, out + '.log.json'):
        if os.path.exists(f): os.remove(f)
    try:
        code, log = run_apply(pdf, wo, out, env={**os.environ, 'APPLY_DRAFT': '1'}, low=True, on_start=on_start)
    except (OSError, subprocess.SubprocessError) as e:
        code, log = None, None; err = type(e).__name__
    else: err = None
    if code != 0 or log is None or not os.path.isfile(out):
        for f in (out, out + '.log.json'):
            if os.path.exists(f): os.remove(f)
        if code is not None and code < 0: raise ValueError('The draft was stopped before it was built.')
        raise ValueError('The draft could not be built' + (f' ({err}).' if err else f' (the executor stopped, exit {code}).'))
    # each move apply.py was given, back to its card: the reviewed moves in the executor's order, as the check left them
    specs = move_specs(items, decisions or {}, additions)
    moves = []
    for m, r in zip(readorder.moves(wo), section_moves(log)):
        key = ([_int(p) for p in m.get('pages') or []], _int(m.get('before_page')))
        hit = next((x for x in specs if (x[1], x[2]) == key), None)
        if hit: specs.remove(hit)
        moves.append({'card': hit[0] if hit else None, **r})
    rejected = [x for x in log.get('rejected') or [] if isinstance(x, dict) and x.get('op') != 'move_section']
    return {'dropped': len(dropped), 'moves': moves, 'rejected': rejected, 'failed': log.get('failed') or [],
            'seconds': round(time.time() - t, 1), 'bytes': os.path.getsize(out)}

def run_rules(e, wo):
    """For each run of this one-page entry, the text rules that would mark it as decoration, as apply.py matches it (the
    whole run, the pattern as written or with its spaces optional): [[card id, …], …]. [] when the audit kept no runs."""
    runs = [t.strip() for t in e.get('runs') or [] if t.strip()]
    if not runs: return []
    rules = []
    for i, r in enumerate(((wo or {}).get('artifacts') or {}).get('text_rules') or []):
        ps = r.get('pages') if isinstance(r, dict) else None
        if not (isinstance(ps, list) and len(ps) == 2 and ps[0] <= e['first'] <= ps[1]): continue
        try: rules.append((f'artifacts.text_rules:{i}', [re.compile(r.get('regex', '.*'), re.S), re.compile(gaptext.loosen(r.get('regex', '.*')), re.S)]))
        except re.error: continue
    return [[rid for rid, rx in rules if any(x.fullmatch(t) or x.fullmatch(re.sub(r'\s+', ' ', t)) for x in rx)] for t in runs]

def whole(p):
    """True when the text rules match every run of an entry (run_rules' result): apply.py removes it whole."""
    return bool(p) and all(p)

def removed_ids(entries, wo):
    """The entries the work order's text rules remove whole, as apply.py's artifacts step does before the section move:
    {entry id: [rule labels]}."""
    trs = ((wo or {}).get('artifacts') or {}).get('text_rules') or []
    labels = {f'artifacts.text_rules:{i}': (r.get('label') if isinstance(r, dict) else None) or 'text rule' for i, r in enumerate(trs)}
    out = {}
    for e in entries or []:
        p = run_rules(e, wo) if trs else []
        if whole(p): out[e['id']] = list(dict.fromkeys(labels[i] for ids in p for i in ids))
    return out

def after_rules(order, removed):
    """A copy of the order as the section move finds it in apply.py: each entry the text rules remove (and everything
    under it) holds no pages, and is no longer a first page of its parent's. Marked removed."""
    out, dead = [], set()
    for e in order:
        if e['id'] in removed or e.get('parent') in dead: dead.add(e['id'])
    gone = {}
    for e in order:
        if e['id'] in dead and e.get('parent') not in dead and e.get('first') is not None:
            gone.setdefault(e.get('parent'), []).append(e['first'])
    for e in order:
        if e['id'] in dead: out.append(dict(e, first=None, last=None, skip=True, removed=True, firsts=[])); continue
        fs = list(e.get('firsts') or [])
        for p in gone.get(e['id'], []):
            if p in fs: fs.remove(p)
        out.append(dict(e, firsts=fs) if e['id'] in gone else e)
    return out

def _order_findings(ro, add, items, wo=None):
    """The reading order's findings as cards (seen only, with a note: nothing is applied), for what no decision answers: a
    section read away from its printed place that the work order does not take care of, each page whose text jumps back up
    a column, and one card for the small sections read late. Findings the work order takes care of are listed on the
    cards that do it instead: each text rule's (hides) and the captions decision's (ties)."""
    es = ro.get('entries') or []
    def short(e): return str(e.get('text') or '').strip()[:60] or None
    def settled(x): return x.get('hidden_by_rules') or x.get('tied_by') or x.get('cleared_by')
    by = {}
    for kind, xs in (('away', ro.get('flagged') or []), ('late', ro.get('late') or [])):
        for x in xs:
            row = {'page': x['first'], 'text': short(es[x['i']]), 'late': kind == 'late'}
            for r in x.get('hidden_by_rules') or []: by.setdefault(r['id'], []).append(row)
            for r in {i for p in x.get('cleared_by') or [] for ids in p for i in ids}: by.setdefault(r, []).append(dict(row, cleared=True))
            if x.get('tied_by'): by.setdefault(x['tied_by']['id'], []).append(row)
    for it in items:
        if it['id'] in by: it['context']['ties' if it['key'] == 'captions' else 'hides'] = by[it['id']]
    for x in ro.get('flagged') or []:
        if settled(x): continue
        e = es[x['i']]
        add(f'reading_order:away:{e["id"]}', 'reading_order', 'Reading order check', None,
            {'finding': 'away', 'entry': e['id'], 'pages': [x['first'], x['last']], 'prev': x.get('prev'), 'next': x.get('next')},
            f'{e.get("style") or "Section"} on PDF {x["first"]}' + (f': “{short(e)}”' if short(e) else ''),
            page=x['first'], pages=[x['first'], x['last']], style=e.get('style'), text=short(e), prev=x.get('prev'), next=x.get('next'),
            show_pages=sorted({x['first']} | ({x['prev']} if x.get('prev') is not None else set())))
    for j in ro.get('page_jumps') or []:
        add(f'reading_order:jump:{j["page"]}', 'reading_order', 'Reading order check', None,
            {'finding': 'jump', 'page': j['page'], 'jumps_up': j['jumps_up']}, f'Text on PDF {j["page"]} jumps back up the page',
            page=j['page'], jumps_up=j['jumps_up'], show_pages=[j['page']])
    if figures_card(ro):                                            # the figures fix_figure_order moves: also its decision
        dr = ro['dryrun']; fm = dr.get('figure_moves')
        ps = sorted({m['page'] for m in fm or [] if isinstance(m.get('page'), int)})
        add('reading_order:figures', 'reading_order', 'Reading order check', None,
            {'finding': 'figures', 'count': len(fm) if fm is not None else None, 'pages': ps},
            f'{len(fm)} figures moved to read on their page' if fm is not None else 'Figure moves not worked out',
            page=ps[0] if ps else None, pages=[ps[0], ps[-1]] if ps else None, count_moves=len(fm) if fm is not None else None,
            moves=(fm or [])[:LATE_LISTED], not_worked_out=dr.get('why'), show_pages=ps[:3],
            ai_off=(wo or {}).get('fix_figure_order') is False)
    alls = ro.get('late') or []
    late = [x for x in alls if not settled(x)]
    if late:
        add('reading_order:late', 'reading_order', 'Reading order check', None,
            {'finding': 'late', 'count': len(late), 'pages': [x['first'] for x in late]}, f'{len(late)} small sections read late',
            page=late[0]['first'], pages=[min(x['first'] for x in late), max(x['first'] for x in late)], count_late=len(late),
            removed=sum(1 for x in alls if x.get('hidden_by_rules')), tied=sum(1 for x in alls if x.get('tied_by')),
            late=[{'page': x['first'], 'after': x['after'], 'text': short(es[x['i']])} for x in late[:LATE_LISTED]])

def figures_card(ro):
    """True when the review has a Figures Moved card: a trial run that found figures to move, or could not run (an
    older run has no trial run, and so no card)."""
    dr = (ro or {}).get('dryrun')
    return dr is not None and dr.get('figure_moves') != []

def _under(order, by, e, host):
    """True when entry e lies inside the container host (following each entry's nearest container above it)."""
    p, seen = e.get('parent'), set()
    while p is not None and p not in seen:
        if p == host: return True
        seen.add(p); p = (by.get(p) or {}).get('parent')
    return False

def move_specs(items, decisions, additions):
    """The section moves as reviewed, in the order apply.py makes them: [(card id, pages, before_page)]. The AI's moves
    (as changed, unless rejected), then the ones the reviewer added."""
    out = []
    for it in items or []:
        if it.get('key') != 'move_section': continue
        d = decisions.get(it['id']) or {}
        if d.get('status') == 'rejected': continue
        v = d.get('value') if d.get('status') == 'changed' and isinstance(d.get('value'), dict) else it.get('ai') or {}
        out.append((it['id'], [_int(p) for p in v.get('pages') or []], _int(v.get('before_page'))))
    for a in additions or []:
        v = a.get('value') if isinstance(a, dict) and a.get('kind') == 'move_section' and isinstance(a.get('value'), dict) else None
        if v: out.append((f'add:move_section:{a.get("target")}', [_int(p) for p in v.get('pages') or []], _int(v.get('before_page'))))
    return out

def move_previews(data, decisions, additions, wo):
    """For /save: each reviewed section move's preview, worked out in the order apply.py makes them (each on the order
    the earlier ones leave) and with the reviewed text rules (wo): rejecting a rule brings back the blocks it removed.
    {card id: {pages, before_page, …move_preview}}."""
    specs = move_specs(data.get('items'), decisions, additions)
    es = (data.get('reading_order') or {}).get('entries')
    pvs = chain_previews(es, [(ps, b) for _, ps, b in specs], removed_ids(es, wo))
    return {i: {'pages': ps, 'before_page': b, **pv} for (i, ps, b), pv in zip(specs, pvs)}

def move_preview(order, a, b, before, removed=None):
    """What move_section would do, worked out on the original's tags with the executor's own match (lib/readorder.py):
    {candidates, host_found, moved, moved_pages, host, host_pages, lands_before, siblings_before, siblings_after, flags_before,
    flags_after}. removed ({entry id: [rule labels]}, removed_ids()): the entries the text rules remove first, as apply.py
    does; when they alone make the executor refuse the move, refused_by_rules names those rules. apply.py
    matches again on the tree it edits, which earlier steps may have changed, so this is a preview. Empty when the order
    has no detail (an older run) or the pages are not numbers."""
    return chain_previews(order, [([a, b], before)], removed)[0]

def chain_previews(order, specs, removed=None):
    """move_preview for several moves [(pages, before_page)], in the order apply.py makes them: each is worked out on the
    order the earlier ones leave (a refused move leaves it as it was); after_moves says how many came before it."""
    if not order or not any('group' in e for e in order): return [{} for _ in specs]
    cur = after_rules(order, removed) if removed else order       # the order apply.py finds: with the rules' blocks gone
    raw, out = order, []                                          # and without, to tell when the rules alone refuse a move
    for k, (ps, before) in enumerate(specs):
        a, b = (list(ps) + [None, None])[:2] if isinstance(ps, list) else (None, None)
        if not all(isinstance(x, int) for x in (a, b, before)): out.append({}); continue
        pv, after = _preview(cur, a, b, before)
        if removed and after is None:
            rpv, _ = _preview(raw, a, b, before)
            if rpv.get('candidates') == 1 and rpv.get('host_found'):
                by = {e['id']: e for e in raw}
                at = (lambda p: a <= p <= b) if pv.get('candidates') != 1 else (lambda p: p == before)   # the section, or where it lands
                near = [i for i in removed if i in by and by[i].get('first') is not None and at(by[i]['first'])]
                pv['refused_by_rules'] = list(dict.fromkeys(l for i in (near or removed) for l in removed[i]))
        if k: pv['after_moves'] = k
        if after is not None:
            cur = after
            if removed: raw = _preview(raw, a, b, before)[1] or raw
        out.append(pv)
    return out

def _preview(order, a, b, before):
    """One move on the order: (the preview, the order after it, or None when the executor would refuse it)."""
    by = {e['id']: e for e in order}
    groups = {}
    for e in order:
        if e.get('group'): groups.setdefault(None if e.get('top') else e.get('under'), []).append(e['id'])
    cand, host = readorder.section_move(None, lambda n: groups.get(n, []), lambda n: by[n].get('firsts') or [],
                                        lambda n: (by[n]['first'], by[n]['last']) if by[n].get('first') is not None else None, a, b, before)
    out = {'candidates': len(cand), 'host_found': host is not None, 'flags_before': len(readorder.out_of_order(order))}
    if len(cand) != 1 or host is None: return out, None
    s = cand[0][0]
    out.update(moved_pages=[by[s]['first'], by[s]['last']], host=by[host]['style'], host_pages=[by[host]['first'], by[host]['last']])
    block = [e for e in order if e['id'] == s or _under(order, by, e, s)]
    ids = {e['id'] for e in block}
    rest = [e for e in order if e['id'] not in ids]
    hi = next(i for i, e in enumerate(rest) if e['id'] == host)
    inside = [i for i in range(hi + 1, len(rest)) if _under(rest, by, rest[i], host)]
    j = next((i for i in inside if rest[i].get('parent') == host and (rest[i].get('first') or 0) >= before), (inside[-1] + 1) if inside else hi + 1)
    shift = by[host]['depth'] + 1 - by[s]['depth']
    moved = [{**e, 'depth': e['depth'] + shift, **({'parent': host, 'under': host, 'top': False} if e['id'] == s else {})} for e in block]
    old = None if by[s].get('top') else by[s].get('under')         # the section it leaves, and the one it joins: their first pages
    def firsts(e):
        fs = list(e.get('firsts') or [])
        if e['id'] == old and by[s].get('first') in fs: fs.remove(by[s]['first'])
        if e['id'] == host and by[s].get('first') is not None: fs.append(by[s]['first'])
        return dict(e, firsts=fs) if e['id'] in (old, host) else e
    after = [firsts(e) for e in rest[:j] + moved + rest[j:]]
    def kids_of(es): return [{k: e.get(k) for k in ('id', 'style', 'first', 'last', 'text')} for e in es if e.get('parent') == host and not e.get('removed')]
    return {**out, 'moved': s, 'lands_before': rest[j]['id'] if j < len(rest) else None,
            'siblings_before': kids_of(order), 'siblings_after': kids_of(after), 'flags_after': len(readorder.out_of_order(after))}, after

def pages_to_render(items, N):
    """Sets every item's page images; returns the priority items' pages, in review order.
    They are not rendered here: the review server renders each page the first time the browser asks for it."""
    for it in items: it['images'] = page_images(it, N)
    want = []
    for it in order(items):
        want += [p for p in (int(PAGE_PNG.search(x).group(1)) for x in it['images']) if p not in want]
    return want

# ------------------------------------------------------------------ addable
def addable(wo, digest, ro=None):
    """What a person can add that the AI did not decide, by kind: targets from the digest lists only, so the checks
    apply to an addition as they do to the AI's decisions. A target the AI already decided is changed on its card instead.
    ro (the reading order): a section move for each section read out of place that the work order does not take care
    of and no move of the AI's covers, while the work order holds fewer than readorder.MAX_MOVES; its preview comes
    after the AI's moves, as apply.py makes them."""
    N = digest['source']['pages']
    labels, by_obj, styles, figs, pfigs, words, sheet_of = _index(digest)
    doc = digest.get('document') or {}
    out = {k: [] for k in ADD_KINDS}

    def add(kind, target, label, page=None, before=None, default=None, edit=None, options=None, **context):
        it = {'id': f'add:{kind}:{target}', 'kind': kind, 'key': kind, 'target': target, 'label': label, 'page': page,
              'page_label': labels.get(page) if page else None, 'before': before, 'default': default, 'edit': edit,
              'options': options, 'context': {k: v for k, v in context.items() if v not in (None, '', [])}}
        it['images'] = page_images(it, N)
        out[kind].append(it)

    decided = {it.get('obj') for it in wo.get('retype') or [] if isinstance(it, dict)}
    levels = sorted(workorder_check.ALLOWED, key=lambda t: (not t.startswith('H'), t))
    for k in ('headings', 'heading_candidates', 'elements'):
        for x in digest.get(k) or []:
            if x['obj'] in decided: continue
            decided.add(x['obj'])
            lv = x.get('level') or (styles.get(x.get('style')) or {}).get('maps_to') or x.get('style')
            add('retype', x['obj'], x.get('text') or x['obj'], page=x.get('page'), before=lv,
                default=lv if lv in workorder_check.ALLOWED else 'P', edit='level', options=levels,
                style=x.get('style'), size=x.get('size'), next=x.get('next'))
    has_alt = {it.get('obj') for it in wo.get('alt') or [] if isinstance(it, dict)}
    decoration = {it.get('obj') for it in (wo.get('artifacts') or {}).get('elements') or [] if isinstance(it, dict)}
    for o, f in figs.items():
        if o in has_alt: continue
        add('alt', o, f'Figure {o}', page=f.get('page'), before=f.get('alt'), default='', edit='text',
            figure=f.get('image'), area_pct=f.get('area_pct'), next=(f.get('next') or {}).get('text'),
            decoration=f'artifacts.elements:{o}' if o in decoration else None)       # the AI hid it: reject that first
    done = {it.get('page') for it in wo.get('page_figures') or [] if isinstance(it, dict)}
    for p, pf in pfigs.items():
        if p not in done: add('page_figures', p, f'Whole page {p} as one figure', page=p, default='', edit='text', figure=pf.get('image'))
    done = {it.get('obj') for k in ('tables', 'flatten') for it in wo.get(k) or [] if isinstance(it, dict)}
    for x in digest.get('tables') or []:
        if x['obj'] not in done:
            add('tables', x['obj'], f'Table {x["obj"]}', page=x.get('page'), before={'header_cells': x.get('header_cells')},
                default={'header_rows': 1, 'header_cols': 0}, edit='table', first_rows=x.get('first_rows'), rows=x.get('rows'), cols=x.get('cols'))
    rm = wo.get('rolemap') or {}
    for s, st in styles.items():
        if s in rm or (st.get('maps_to') or s) not in MAPPABLE: continue
        pr = st.get('pages') or [None, None]
        add('rolemap', s, f'Every "{s}" element', page=pr[0], before=st.get('maps_to'),
            default=st.get('maps_to') if st.get('maps_to') in LEVELS else 'P', edit='level', options=LEVELS,
            count=st.get('count'), samples=(st.get('samples') or [])[:4], style=s)
    d = wo.get('document') or {}
    for k, label, edit in (('title', 'Title', 'text'), ('lang', 'Language', 'lang')):
        if k not in d: add('document', k, label, before=doc.get(k), default=doc.get(k) or '', edit=edit)
    done = {it.get('id') for it in wo.get('ocr_words') or [] if isinstance(it, dict)}
    for i, w in words.items():
        if i in done: continue
        sheet, cell = sheet_of.get(i, (None, None))
        add('ocr_words', i, f'OCR read "{w.get("text")}"', page=(w.get('pages') or [None])[0], before=w.get('text'),
            default=w.get('text'), edit='text', count=w.get('count'),
            word=f'word/{i}.png' if cell else None, sheet=None if cell else sheet, word_id=i)
    es = (ro or {}).get('entries') or []
    have = [(m['pages'], m.get('before_page')) for m in readorder.moves(wo) if isinstance(m.get('pages'), list) and len(m['pages']) == 2]
    if es and len(have) < readorder.MAX_MOVES:
        flagged = {x['i'] for x in ro.get('flagged') or []} | set(ro.get('removed') or [])   # never before a block the rules remove
        for x in ro.get('flagged') or []:
            if x.get('hidden_by_rules') or x.get('tied_by') or x.get('cleared_by'): continue
            if any(isinstance(p[0], int) and isinstance(p[1], int) and p[0] <= x['first'] <= p[1] for p, _ in have): continue   # the AI moves it
            e, b = es[x['i']], suggest_before(es, x['i'], flagged)
            pv = chain_previews(es, have + [([x['first'], x['last']], b)], ro.get('removed_by'))[-1]
            if pv.get('candidates') != 1 or not pv.get('host_found'): continue   # the executor would refuse it: not offered
            add('move_section', e['id'], f'{e.get("style") or "Section"} on PDF {x["first"]}' + (f': “{str(e.get("text")).strip()[:60]}”' if (e.get('text') or '').strip() else ''),
                page=x['first'], before='read ' + ('between PDF {} and PDF {}'.format(x['prev'], x['next']) if x.get('prev') is not None and x.get('next') is not None
                                                   else f'after PDF {x["prev"]}' if x.get('prev') is not None else f'before PDF {x["next"]}'),
                default={'pages': [x['first'], x['last']], 'before_page': b}, edit='move', **pv)
    return {k: v for k, v in out.items() if v}

def suggest_before(es, i, flagged=()):
    """The page to read entry i before, to put it back in its printed place: the first page of the earliest sibling that
    reads in page order and starts after it (None when it belongs at the end). flagged: indexes to pass over (siblings
    out of place, and those the text rules remove)."""
    e = es[i]
    later = [x['first'] for j, x in enumerate(es) if j != i and j not in flagged and x.get('parent') == e.get('parent')
             and not x.get('skip') and x.get('first') is not None and x['first'] > e['first']]
    return min(later) if later else None

def render_pages(pdf, pages, out_dir, scale=1.0):
    import pypdfium2 as pdfium
    os.makedirs(out_dir, exist_ok=True)
    doc = pdfium.PdfDocument(pdf)
    try:
        for p in pages:
            path = os.path.join(out_dir, f'page_{p:03d}.png')
            if not os.path.exists(path): doc[p - 1].render(scale=scale).to_pil().save(path)
    finally: doc.close()

def prepare(R, pdf):
    """Write review_items.json, and render the pages of the first group so the page opens with them. Runs when run_api.sh
    stops for review. Every other page image is rendered by the server as the reviewer scrolls to it."""
    ai = load(os.path.join(R, 'workorder.ai.json'))
    digest = load(os.path.join(R, '_audit', 'digest.json'))
    if ai is None or digest is None: sys.exit(f'{R} has no workorder.ai.json or _audit/digest.json: run run_api.sh with REVIEW=1 first')
    save(os.path.join(R, '_audit', 'dryrun.json'), dry_run(R, pdf))
    ro = reading_order_for(os.path.join(R, '_audit'), digest, ai)
    items = build_items(ai, digest, ro['entries'], ro)
    pages_to_render(items, digest['source']['pages'])
    first = sorted({int(PAGE_PNG.search(x).group(1)) for it in items if it['priority'] == 1 for x in it['images']})
    render_pages(pdf, first, os.path.join(R, 'review_pages'))
    data = {'book': digest['source'].get('file'), 'run': os.path.basename(os.path.normpath(R)), 'pages': digest['source']['pages'],
            'pdf': os.path.abspath(pdf), 'groups': GROUPS, 'levels': LEVELS, 'add_kinds': ADD_KINDS, 'items': items,
            'addable': addable(ai, digest, ro), 'reading_order': ro}
    save(os.path.join(R, 'review_items.json'), data)
    return data

# ------------------------------------------------------------------ decisions
def apply_decisions(ai_wo, items, decisions):
    """A copy of the AI's work order with a person's decisions applied. Unreviewed and approved items stay as the AI wrote them."""
    wo = copy.deepcopy(ai_wo)
    drop = []
    for it in items:
        d = decisions.get(it['id']) or {}
        st = d.get('status')
        if it['id'] == 'reading_order:figures':          # the figures card decides fix_figure_order: reject flips the AI's choice
            if st == 'rejected':
                if it['context'].get('ai_off'): wo.pop('fix_figure_order', None)      # on again (the default)
                else: wo['fix_figure_order'] = False
            continue
        if it['key'] == 'fix_figure_order' and st == 'rejected': wo['fix_figure_order'] = False; continue   # on unless false
        if it['loc'] is None: continue                   # a reading-order finding: not in the work order
        if st == 'rejected' and it['key'] not in SEEN_ONLY: drop.append(it['loc'])
        elif st == 'changed' and it['edit']:
            v = d.get('value')
            parent = wo
            for k in it['loc'][:-1]: parent = parent[k]
            last = it['loc'][-1]
            if it['edit'] == 'table':
                for f in ('header_rows', 'header_cols'):
                    try: parent[last][f] = int((v or {}).get(f, parent[last].get(f, 0)))
                    except (TypeError, ValueError): parent[last][f] = (v or {}).get(f)
            elif it['edit'] == 'move':                  # {pages: [a, b], before_page}: whole numbers, else left for the check to refuse
                v = v or {}
                def num(x):
                    try: return int(x)
                    except (TypeError, ValueError): return x
                ps = v.get('pages') if isinstance(v.get('pages'), list) else parent[last].get('pages')
                parent[last] = {**parent[last], 'pages': [num(x) for x in ps], 'before_page': num(v.get('before_page', parent[last].get('before_page')))}
            elif it['field']: parent[last][it['field']] = v
            else: parent[last] = v
    for loc in sorted(drop, key=lambda l: [str(x) if not isinstance(x, int) else f'{x:09d}' for x in l], reverse=True):
        parent = wo
        for k in loc[:-1]: parent = parent[k]
        if isinstance(parent, list): del parent[loc[-1]]
        else: parent.pop(loc[-1], None)
    for k in ('retype', 'alt', 'page_figures', 'tables', 'actual_text', 'merges', 'flatten', 'keep_lists', 'ocr_words', 'document', 'rolemap',
              'adopt_orphans', 'move_to_document_start', 'move_section'):
        if k in wo and wo[k] in ([], {}) and ai_wo.get(k): del wo[k]       # a key with every item rejected is left out, as the AI would
    return wo

def _int(v):
    try: return int(v)
    except (TypeError, ValueError): return v                # left as it is: the check refuses it with its reason

def add_entries(wo, additions, adds, reviewer='', mark=False):
    """The person's own decisions added to wo (in place), each in the shape the AI writes. Returns what was refused:
    [{id, why}]. Only targets listed by addable() are taken, and never one that wo already decides. mark: each added
    entry carries _card (its add: id), for problems() to name the card a dropped entry came from."""
    by_id = {it['id']: it for v in (adds or {}).values() for it in v}
    why = f'added by {reviewer.strip()} in review' if (reviewer or '').strip() else 'added in review'
    refused, seen = [], set()
    for a in additions or []:
        a = a if isinstance(a, dict) else {}
        aid = f'add:{a.get("kind")}:{a.get("target")}'
        t, v = by_id.get(aid), a.get('value')
        def no(reason): refused.append({'id': aid, 'why': reason})
        if t is None: no('not something the review can add (a decision the AI made is changed on its card)'); continue
        if aid in seen: no('added twice'); continue
        seen.add(aid)
        k, target = t['kind'], t['target']
        tag = {'_card': aid} if mark else {}
        if k == 'retype':
            if any(it.get('obj') == target for it in wo.get('retype') or []): no('already decided: change it on its card'); continue
            wo.setdefault('retype', []).append({'obj': target, 'type': v, 'why': why, **tag})
        elif k == 'alt':
            if any(it.get('obj') == target for it in (wo.get('artifacts') or {}).get('elements') or []):
                no('the AI marked this figure as decoration: reject that decision first'); continue
            if any(it.get('obj') == target for it in wo.get('alt') or []): no('already decided: change it on its card'); continue
            wo.setdefault('alt', []).append({'obj': target, 'alt': v, 'why': why, **tag})
        elif k == 'page_figures':
            wo.setdefault('page_figures', []).append({'page': target, 'alt': v, 'why': why, **tag})
        elif k == 'tables':
            v = v if isinstance(v, dict) else {}
            wo.setdefault('tables', []).append({'obj': target, 'header_rows': _int(v.get('header_rows', 0)),
                                                'header_cols': _int(v.get('header_cols', 0)), 'why': why, **tag})
        elif k == 'rolemap': wo.setdefault('rolemap', {})[target] = v
        elif k == 'document': wo.setdefault('document', {})[target] = v
        elif k == 'ocr_words': wo.setdefault('ocr_words', []).append({'id': target, 'reads': v, **tag})
        elif k == 'move_section':                       # after the AI's moves; the check refuses overlaps with its reason
            have = readorder.moves(wo)
            if len(have) >= readorder.MAX_MOVES: no(f'a work order holds at most {readorder.MAX_MOVES} section moves: change or reject one on its card first'); continue
            v = v if isinstance(v, dict) else {}
            wo['move_section'] = have + [{'pages': [_int(p) for p in (v.get('pages') or [])], 'before_page': _int(v.get('before_page')), 'why': why, **tag}]
    return refused

def unreviewed(items, decisions):
    return [it['id'] for it in items if not (decisions.get(it['id']) or {}).get('status')]

# ------------------------------------------------------------------ gaps
def _level(style, wo, styles):
    st = styles.get(style) or {}
    return (wo.get('rolemap') or {}).get(style) or st.get('maps_to') or style

def gaps(wo, digest):
    """What is still missing once the order is applied: [{id, what, add?}]. A warning, not a block: the reviewer can
    add what is missing, or finish and say why. add is {kind, target} for the add form."""
    labels, by_obj, styles, figs, pfigs, words, sheet_of = _index(digest)
    out = []
    # H1s: every element of a style at H1, then the retypes moving single elements on or off H1
    h1 = {s: st.get('count') or 0 for s, st in styles.items() if _level(s, wo, styles) == 'H1'}
    n, moved = sum(h1.values()), []
    for it in wo.get('retype') or []:
        x = by_obj.get(it.get('obj')) or {}
        was = _level(x.get('style'), wo, styles) if x.get('style') else None
        if was == 'H1' and it.get('type') != 'H1': n -= 1
        if was != 'H1' and it.get('type') == 'H1': n += 1; moved.append(f'"{(x.get("text") or it.get("obj"))[:60]}" (PDF p. {x.get("page")})')
    where = [f'every "{s}" element ({c})' for s, c in h1.items() if c] + moved
    if n < 1:
        out.append({'id': 'h1', 'what': 'No H1: once this review is applied, no element is a level-1 heading (the book title). '
                    'Add one under Heading or tag change.', 'add': {'kind': 'retype'}})
    elif n > 1:
        out.append({'id': 'h1', 'what': f'About {n} H1s: ' + '; '.join(where) + '. A book should have one, the title.'})
    # figures that end up with no alt and are not marked as decoration
    alt = {it.get('obj') for it in wo.get('alt') or [] if str(it.get('alt') or '').strip()}
    deco = {it.get('obj') for it in (wo.get('artifacts') or {}).get('elements') or []}
    bare = [o for o, f in figs.items() if not str(f.get('alt') or '').strip() and o not in alt and o not in deco]
    if bare:
        out.append({'id': 'figures_without_alt', 'what': f'{len(bare)} figure{"s" if len(bare) != 1 else ""} with no alt text '
                    'and not marked as decoration: ' + ', '.join(f'{o} (PDF p. {figs[o].get("page")})' for o in bare[:12])
                    + (f' and {len(bare) - 12} more' if len(bare) > 12 else ''), 'add': {'kind': 'alt', 'target': bare[0]}, 'objs': bare})
    done = {it.get('page') for it in wo.get('page_figures') or [] if str(it.get('alt') or '').strip()}
    left = [p for p in pfigs if p not in done]
    if left:
        out.append({'id': 'page_figures_without_alt', 'what': f'{len(left)} whole-page figure{"s" if len(left) != 1 else ""} '
                    'with no alt text: PDF p. ' + ', '.join(map(str, left[:12])) + (f' and {len(left) - 12} more' if len(left) > 12 else ''),
                    'add': {'kind': 'page_figures', 'target': left[0]}})
    return out

# ------------------------------------------------------------------ diff
def _ident(x):
    if isinstance(x, dict):
        for k in ('obj', 'id', 'page', 'label', 'style', 'what'):
            if x.get(k) is not None: return f'{k} {x[k]}'
    return json.dumps(x, ensure_ascii=False, sort_keys=True)

def diff(ai, final, where=''):
    """What changed from the AI's order to the reviewed one: [{where, id, change: changed|removed|added, ai, person}]."""
    out = []
    if isinstance(ai, dict) and isinstance(final, dict):
        for k in list(ai) + [k for k in final if k not in ai]:
            if not where and k in workorder_check.META: continue
            w = f'{where}.{k}' if where else k
            if k not in final: out.append({'where': w, 'change': 'removed', 'ai': ai[k]})
            elif k not in ai: out.append({'where': w, 'change': 'added', 'person': final[k]})
            elif ai[k] != final[k]:
                if isinstance(ai[k], (dict, list)) and type(ai[k]) is type(final[k]): out += diff(ai[k], final[k], w)
                else: out.append({'where': w, 'change': 'changed', 'ai': ai[k], 'person': final[k]})
        return out
    if isinstance(ai, list) and isinstance(final, list):
        ia, ib = [_ident(x) for x in ai], [_ident(x) for x in final]
        if len(set(ia)) != len(ia) or len(set(ib)) != len(ib):         # no usable identity: compare whole items
            ia = [json.dumps(x, ensure_ascii=False, sort_keys=True) for x in ai]; ib = [json.dumps(x, ensure_ascii=False, sort_keys=True) for x in final]
        A, B = dict(zip(ia, ai)), dict(zip(ib, final))
        for i in ia:
            if i not in B: out.append({'where': where, 'id': i, 'change': 'removed', 'ai': A[i]})
            elif A[i] != B[i]:
                fields = [k for k in set(A[i]) | set(B[i]) if A[i].get(k) != B[i].get(k)] if isinstance(A[i], dict) and isinstance(B[i], dict) else None
                out.append({'where': where, 'id': i, 'change': 'changed',
                            'ai': {k: A[i].get(k) for k in fields} if fields else A[i], 'person': {k: B[i].get(k) for k in fields} if fields else B[i]})
        out += [{'where': where, 'id': i, 'change': 'added', 'person': B[i]} for i in ib if i not in A]
        return out
    return [] if ai == final else [{'where': where, 'change': 'changed', 'ai': ai, 'person': final}]

# ------------------------------------------------------------------ check and finish
def check(R, wo):
    """The decide.py checks on a reviewed order. The rules about images the model never saw (alt text for a figure
    over --max-images, a reading of an OCR word whose sheet was not sent) are for the model, not for a person, who
    sees the page: they are off here. The AI's own unseen decisions were already dropped by decide.py."""
    digest = load(os.path.join(R, '_audit', 'digest.json'))
    order = (load(os.path.join(R, '_audit', 'fulltext.json')) or {}).get('reading_order')   # the order the page's findings use
    return workorder_check.check(wo, digest, set(), {w['id'] for w in digest.get('ocr_words') or []}, order)

def card_of(items, entry):
    """The id of the card a dropped entry ({where, item, why}) came from, or None: the items under the same key (and field),
    then the one whose target is named in the dropped entry."""
    parts = str(entry.get('where') or '').split('.')
    same = [it for it in items if it['loc'] and it['loc'][0] == parts[0] and (len(parts) < 2 or len(it['loc']) < 2 or str(it['loc'][1]) == parts[1])]
    if len(same) == 1: return same[0]['id']
    text = json.dumps(entry.get('item'), ensure_ascii=False)
    hits = [it for it in same if it['id'].partition(':')[2] and (json.dumps(it['id'].partition(':')[2], ensure_ascii=False) in text
                                                                 or json.dumps(it.get('ai'), ensure_ascii=False) == text)]
    return hits[0]['id'] if len(hits) == 1 else None

def preview(R, wo):
    """What the check would drop from wo, and the gaps left after it, without changing wo."""
    wo = copy.deepcopy(wo)
    dropped = check(R, wo)
    return dropped, gaps(wo, load(os.path.join(R, '_audit', 'digest.json')))

# ------------------------------------------------------------------ problems: the check's verdict, card by card
# What to do about each reason the check (lib/workorder_check.py) or add_entries gives, for the page: sentence case, no
# file names. Keyed by the reason with its numbers as N (_key); {pages} is the book's page count, {moves} the most
# section moves a work order may hold. A reason with no entry is shown as it is (test_review_core pins that none is missing).
FIX = {
    'unknown key': 'The pipeline does not know this decision, so it cannot be applied. Reject it.',
    'unknown obj': 'This points at something the audit did not find in the book. Reject it.',
    'not a single-run figure listed in the digest': 'Only a figure drawn as one image can be hidden as decoration. Reject this choice.',
    'bad regex': 'The text pattern is not valid, so the rule cannot be applied. Reject it.',
    'band must be top, bottom or any': 'The rule must say top, bottom or anywhere on the page. Reject it.',
    'bad page range': 'The pages must be two page numbers from 1 to {pages}. Reject this choice.',
    'needs regex or where: in_figure': 'The rule says neither what text it hides nor that the text is inside a figure. Reject it.',
    'unknown style': 'The book has no such style. Reject this choice.',
    'target not allowed': 'Choose one of the tags in the list.',
    'type not allowed': 'Choose one of the tags in the list.',
    'not a figure or empty alt': 'Write alt text that says what the figure shows. If it needs none, reject this choice instead.',
    'its image was not sent (over --max-images), so the alt was written unseen': 'The AI wrote this without seeing the figure. Look at it and write the alt text.',
    'not PDF page numbers in range': 'Use page numbers from 1 to {pages}.',
    'not a page listed in page_figures': 'The audit did not find this page as a whole-page figure. Reject this choice.',
    'empty alt': 'Write alt text that says what the page shows. If it needs none, reject this choice instead.',
    'its page image was not sent (over --max-images), so the alt was written unseen': 'The AI wrote this without seeing the page. Look at it and write the alt text.',
    'unknown id': 'The audit found no such word. Reject this choice.',
    'its word sheet was not sent': 'The AI did not see this word. Look at the image and type what it says.',
    'empty': 'Type the word as it is printed, or reject this choice to keep the OCR text.',
    'not one word': 'Type one word, with no spaces, of at most 80 characters.',
    'same as the OCR text': 'This is what the OCR already reads. Type the corrected word, or reject this choice.',
    'too different from the OCR text to be a misreading of it': 'This is too different from what the OCR read to be a misreading of it. Check the word in the image.',
    'not a list or table listed in the digest': 'The audit found no such list or table. Reject this choice.',
    'not a table listed in the digest': 'The audit found no such table. Reject this choice.',
    'also flattened': 'This table is also set to be flattened. Keep one of the two choices and reject the other.',
    'header_rows and header_cols must be whole numbers 0-3': 'Choose 0 to 3 header rows and 0 to 3 header columns.',
    'title_rows and note_rows must be whole numbers 0-3': 'The table\'s title and note rows must be 0 to 3. Reject this choice.',
    'group_rows and repeat_rows must list row numbers in the table': 'Some rows named here are not in the table. Reject this choice.',
    'no header rows or columns': 'Choose at least one header row or column. If the table has no headers, reject this choice.',
    'the same table twice': 'This table is decided twice. Keep one choice and reject or remove the other.',
    'not a BCP 47 language tag': 'Choose a language from the list, or choose Other and type a language tag such as en-US or haw.',
    'not a list the one-item rule would flatten': 'Nothing would flatten this list, so there is nothing to keep. Reject this choice.',
    'unknown style or direction': 'The book has no such style. Reject this choice.',
    'no such style': 'The book has no such style. Reject this choice.',
    'unknown styles': 'Some styles named here are not in the book. Reject this choice.',
    'bad page': 'Use a page number from 1 to {pages}.',
    'bad pages': 'Use page numbers from 1 to {pages}: the first and last pages of the section, and the page it is read before.',
    'the audit finds no section read out of place in these pages or where it lands':
        'Nothing is read out of place in these pages, or where the section would land. Check the page numbers.',
    'more than N section moves': 'At most {moves} sections can be moved. Reject one of the moves.',
    'its pages overlap another section move': 'These pages overlap another section move. Change the pages of one, or reject one.',
    'it lands inside the pages of another section move': 'This would be read in the middle of another moved section. Change where one of them is read, or reject one.',
    'not something the review can add (a decision the AI made is changed on its card)': 'This can no longer be added. Remove it, and change the choice on its card instead.',
    'added twice': 'This is added twice. Remove one.',
    'already decided: change it on its card': 'The AI already decided this. Remove this addition and change the AI\'s choice on its card.',
    'the AI marked this figure as decoration: reject that decision first': 'The AI marked this figure as decoration. Reject that choice first, or remove this alt text.',
    'a work order holds at most N section moves: change or reject one on its card first': 'At most {moves} sections can be moved. Change or reject one of the other moves first.',
}
CONFLICT = {'also flattened', 'the same table twice', 'more than N section moves', 'its pages overlap another section move',
            'it lands inside the pages of another section move', 'added twice', 'already decided: change it on its card',
            'the AI marked this figure as decoration: reject that decision first',
            'a work order holds at most N section moves: change or reject one on its card first'}   # choices that clash, not one bad value

def _key(why): return re.sub(r'(more than|at most) \d+', r'\1 N', str(why))

def fix(why, pages):
    """What to do about a reason, for the page."""
    t = FIX.get(_key(why))
    return t.format(pages=pages, moves=readorder.MAX_MOVES) if t else str(why)[:1].upper() + str(why)[1:] + '.'

def languages():
    """The language list for the page's Language field: [[tag, name], …] by name, from lib/langtag.py's names, with
    English (US) and (UK) beside English. A tag not in it is typed under Other."""
    from lib import langtag
    named = {**langtag.NAMES, 'en-US': 'English (US)', 'en-GB': 'English (UK)'}
    return sorted(([t, n] for t, n in named.items()), key=lambda x: x[1])

def problems(R, ai_wo, items, decisions, additions, adds, reviewer='', set_in=None):
    """The check's verdict on the reviewed order, card by card, and the gaps left after it: ({fields, conflicts, unplaced}, gaps).
    The order is built as for Finish (apply_decisions, add_entries), each entry marked with its card first, then checked.
      fields:    [{card, why, fix, origin, parts?}]  a card whose own value fails a rule (parts: which of a move's page boxes)
      conflicts: [{cards, why, fix, origin}]         choices that clash (two moves overlap, an addition the AI already decided)
      unplaced:  [{where, why, fix}]                 what the check drops that no card holds: left out, as before; never blocks Finish
    origin: review (changed or added in this review), earlier (set in an earlier session: set_in), ai (the AI's choice, untouched)."""
    digest = load(os.path.join(R, '_audit', 'digest.json'))
    N = digest['source']['pages']
    marked = copy.deepcopy(ai_wo)
    for it in items:
        x = marked
        try:
            for k in it['loc'] or [None]: x = x[k]
        except (KeyError, IndexError, TypeError): x = None
        if isinstance(x, dict): x['_card'] = it['id']
    wo = apply_decisions(marked, items, decisions)
    refused = add_entries(wo, additions, adds, reviewer, mark=True)
    ids = {it['id'] for it in items} | {f'add:{a.get("kind")}:{a.get("target")}' for a in additions or [] if isinstance(a, dict)}
    moves, tables = list(readorder.moves(wo)), list(wo.get('tables') or [])
    dropped = check(R, wo)

    def card(d):
        it, w = d.get('item'), str(d.get('where') or '')
        if isinstance(it, dict) and it.get('_card'): return it['_card']
        if w.startswith('document.'): return next((c for c in (w, f'add:document:{w[9:]}') if c in ids), None)
        if w == 'rolemap' and isinstance(it, dict) and len(it) == 1:
            s = next(iter(it)); return next((c for c in (f'rolemap:{s}', f'add:rolemap:{s}') if c in ids), None)
        return card_of(items, d)

    def origin(c):
        if c.startswith('add:'): return 'review'
        if (decisions.get(c) or {}).get('status') == 'changed': return 'earlier' if c in (set_in or {}) else 'review'
        return 'ai'

    def page_ok(p): return isinstance(p, int) and not isinstance(p, bool) and 1 <= p <= N

    def pages(m):
        ps = m.get('pages') if isinstance(m, dict) else None
        return ps if isinstance(ps, list) and len(ps) == 2 and all(page_ok(p) for p in ps) and page_ok(m.get('before_page')) else None

    def others(why, it):
        """The other cards a clash names."""
        if why in ('its pages overlap another section move', 'it lands inside the pages of another section move'):
            (a, b), c = it['pages'], it['before_page']
            return [m.get('_card') for m in moves if m is not it and pages(m) and (
                (a <= m['pages'][1] and m['pages'][0] <= b) if why.startswith('its') else
                (m['pages'][0] <= c <= m['pages'][1] or a <= m['before_page'] <= b))]
        if why.startswith('more than'): return [m.get('_card') for m in moves if m is not it]
        if why == 'the same table twice': return [t.get('_card') for t in tables if t is not it and t.get('obj') == it.get('obj')]
        if why == 'also flattened': return [f'flatten:{it.get("obj")}']
        return []

    out = {'fields': [], 'conflicts': [], 'unplaced': []}
    for d in dropped:
        why, c = d['why'], card(d)
        if c is None or c not in ids:
            out['unplaced'].append({'where': d.get('where'), 'why': why, 'fix': fix(why, N)}); continue
        if _key(why) in CONFLICT:
            cs = list(dict.fromkeys([x for x in others(why, d['item']) if x in ids] + [c]))
            out['conflicts'].append({'cards': cs, 'why': why, 'fix': fix(why, N), 'origin': origin(c)}); continue
        p = {'card': c, 'why': why, 'fix': fix(why, N), 'origin': origin(c)}
        if why == 'bad pages' and isinstance(d['item'], dict):        # which of the move's boxes is wrong
            ps = d['item'].get('pages') if isinstance(d['item'].get('pages'), list) and len(d['item']['pages']) == 2 else None
            p['parts'] = ([f for f, v in zip(('a', 'b'), ps) if not page_ok(v)] if ps else ['a', 'b']) + ([] if page_ok(d['item'].get('before_page')) else ['before_page'])
        out['fields'].append(p)
    for r in refused:
        aid, why = r['id'], r['why']
        kind, _, target = aid[4:].partition(':')
        if _key(why) in CONFLICT:
            other = ([f'{kind}:{target}'] if why.startswith('already decided') else [f'artifacts.elements:{target}'] if 'decoration' in why
                     else [m.get('_card') for m in moves] if why.startswith('a work order') else [])
            out['conflicts'].append({'cards': list(dict.fromkeys([x for x in other if x in ids] + [aid])), 'why': why, 'fix': fix(why, N), 'origin': 'review'})
        else: out['fields'].append({'card': aid, 'why': why, 'fix': fix(why, N), 'origin': 'review'})
    return out, gaps(wo, digest)

def _status(it, d):
    st = (d or {}).get('status') or 'accepted_unreviewed'
    if st == 'changed' and (d.get('value') == it['ai'] or not it['edit']): return 'approved'   # "changed" to the AI's own value
    return st

def finish(R, ai_wo, wo, reviewer, date, method, decisions=None, items=None, note=None, additions=None, gaps_ack=None, gap_default=None):
    """gaps_ack: {gap id: the reviewer's reason for leaving it open}; gap_default: the reason for any gap not in it."""
    if not (reviewer or '').strip(): raise ValueError('a reviewer name is needed')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date or ''): raise ValueError('the date must be YYYY-MM-DD')
    if (wo.get('source') or {}).get('sha256') != (ai_wo.get('source') or {}).get('sha256'):
        raise ValueError('source.sha256 differs from the AI\'s work order: leave "source" as it was')
    dropped = check(R, wo)
    open_gaps = []
    for g in gaps(wo, load(os.path.join(R, '_audit', 'digest.json'))):
        reason = str((gaps_ack or {}).get(g['id']) or gap_default or '').strip()
        if not reason: raise ValueError(f'say why this is left open, or add what is missing: {g["what"]}')
        open_gaps.append({'id': g['id'], 'what': g['what'], 'reason': reason})
    decisions = decisions or {}
    statuses = [_status(it, decisions.get(it['id'])) for it in items or []]
    counts = {s: statuses.count(s) for s in ('approved', 'changed', 'rejected', 'seen', 'accepted_unreviewed')} if items else None
    if counts is not None and additions: counts['added'] = len(additions)
    notes = {k: d['note'] for k, d in decisions.items() if (d or {}).get('note')}
    notes.update({f'add:{a["kind"]}:{a["target"]}': a['note'] for a in additions or [] if a.get('note')})
    changes = diff(ai_wo, wo)
    v = {'reviewer': reviewer.strip(), 'date': date, 'recorded': datetime.datetime.now().isoformat(timespec='seconds'), 'method': method,
         'changes': changes, 'dropped_on_check': dropped,
         **({'counts': counts} if counts else {}),
         **({'gaps': open_gaps} if open_gaps else {}),
         **({'notes': notes} if notes else {}),
         **({'note': note} if note else {})}
    old = load(os.path.join(R, 'review.json'))
    if old: v['history'] = old.pop('history', []) + [old]
    wo['reviewed_by'] = f'{v["reviewer"]} on {date}'
    save(os.path.join(R, 'workorder.json'), wo)
    save(os.path.join(R, 'review.json'), v)
    return v
