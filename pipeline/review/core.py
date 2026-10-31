"""review/core.py: the review step's logic, with no web server and no HTML (a later front end can call it directly).

    ro    = reading_order(digest, fulltext, wo)      # the original's reading order, for the page's reading-order list
    items = build_items(wo, digest, ro['entries'], ro)   # every decision in the work order, with its context and priority group,
                                                      # and the reading order's findings no decision answers (seen only)
    adds  = addable(wo, digest)                       # what a person can add that the AI did not decide (an H1, an alt, …)
    wo2   = apply_decisions(ai_wo, items, decisions)  # a person's approve / change / reject applied to a copy of the AI's order
    refused = add_entries(wo2, additions, adds, reviewer)   # the person's own decisions added to it
    dropped, gaps = preview(R, wo2)                   # what the check would drop, and what is still missing (no H1, figures without alt)
    changes = diff(ai_wo, wo2)                        # what the person changed, item by item
    finish(R, ai_wo, wo2, reviewer, date, method, …)  # checks the order again, writes review.json and the reviewed workorder.json

The formats a front end needs (also in docs/review-step.md):
  item:      {id, key, kind, label, page, page_label, pages, before, ai, edit, options, context, priority, images}
  addable:   {kind: [{id, kind, target, label, page, page_label, before, default, edit, options, context, images}]}
  decisions: {id: {status: approved | changed | rejected | seen, value?, note?}}
  additions: [{kind, target, value, note?}]
  reading order: {entries: [lib/readorder.py entries], flagged: [{i, first, last, prev, next, hidden_by?, hidden_by_rules?}],
                 late: [{i, first, last, after, hidden_by?, hidden_by_rules?}],
                 flat, detail, page_jumps}
"""
import os, re, sys, copy, json, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import workorder_check, readorder, gaptext  # noqa: E402

LEVELS = sorted(workorder_check.ALLOWED - {'Figure'}, key=lambda t: (not t.startswith('H'), t))
HEADING = {'H1', 'H2', 'H3', 'H4', 'H5', 'H6'}
GROUPS = {1: 'H1 and title', 2: 'Style-wide mappings', 3: 'Heading-level changes', 4: 'Rules that can hide text',
          5: 'Reading order', 6: 'Pages the AI asked about', 7: 'General'}
READING = ('move_section', 'move_to_document_start', 'adopt_orphans')   # decisions that change the reading order
SEEN_ONLY = {'deferrals', 'notes_for_reviewer', 'reading_order'}   # not applied by apply.py: a person marks them seen, with a note
LATE_LISTED = 12                                       # sections named on the "read late" card (the panel lists them all)
PAGE_REF = re.compile(r'PDF (\d+)(?:\s*[–-]\s*(\d+))?')
PAGE_PNG = re.compile(r'(\d+)\.png$')
ADD_KINDS = {'retype': 'Heading or tag change', 'alt': 'Alt text', 'page_figures': 'Alt text', 'tables': 'Table headers',
             'rolemap': 'Style mapping', 'document': 'Document', 'ocr_words': 'OCR words'}
MAPPABLE = workorder_check.ALLOWED - {'Figure'} | {'H'}  # a style mapped to one of these can be given a new level

def save(path, obj):
    """Through a temp file and os.replace, so a stop mid-write never leaves a cut-short JSON file."""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: f.write(json.dumps(obj, ensure_ascii=False, indent=1))
    os.replace(tmp, path)

def load(path, default=None):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default

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
    ms = wo.get('move_section')
    if isinstance(ms, dict) and isinstance(ms.get('pages'), list) and len(ms['pages']) == 2:
        (a, b), c = ms['pages'], ms.get('before_page')
        add('move_section', 'move_section', 'Reading order', ['move_section'], ms, f'Section on PDF {a}–{b} read before PDF {c}',
            page=a if isinstance(a, int) else None, pages=[a, b] if all(isinstance(x, int) for x in (a, b)) else None, edit='move',
            before_page=c, why=ms.get('why'), **move_preview(order, a, b, c))
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
    for k, v in wo.items():
        if k not in listed:
            add(f'key:{k}', k, 'Other decisions', [k], v, k)
    if ro: _order_findings(ro, add, items)

    # priority groups: fixed rules, no model
    for it in items:
        k, b, ai = it['key'], it['before'], it['ai']
        if k == 'document' and it['id'] == 'document.title': it['priority'] = 1
        elif k in ('retype', 'rolemap') and ('H1' in (b, ai)) and b != ai: it['priority'] = 1
        elif k == 'rolemap': it['priority'] = 2
        elif k == 'retype' and b != ai and (b in HEADING or ai in HEADING): it['priority'] = 3
        elif k == 'artifacts' and it['loc'][1] in ('text_rules', 'untagged'): it['priority'] = 4
        elif k in READING or k == 'reading_order': it['priority'] = 5
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
    read well after their page (readorder.read_late). A flagged or late entry every run of which one of the work order's
    text rules would hide gets hidden_by_rules ([{id, label}]: every such rule, by its card id) and hidden_by (the first
    one's label)."""
    es = (fulltext or {}).get('reading_order')
    detail = es is not None
    if es is None: es = readorder.parse_lines(digest.get('reading_order'))
    fl = readorder.out_of_order(es)
    late = readorder.read_late(es, [x['i'] for x in fl])
    for x in fl + late:
        rs = hidden_rules(es[x['i']], wo)
        if rs: x['hidden_by_rules'] = rs; x['hidden_by'] = rs[0]['label']
    return {'entries': es, 'flagged': fl, 'late': late, 'flat': len(es) < 2, 'detail': detail, 'page_jumps': (fulltext or {}).get('page_jumps')}

def reading_order_for(audit_dir, digest, wo):
    """reading_order() from an audit folder's fulltext.json (when there is one)."""
    return reading_order(digest, load(os.path.join(audit_dir, 'fulltext.json')), wo)

def hidden_rules(e, wo):
    """Every text rule that would mark every run of this one-page entry as decoration, as apply.py matches it (the whole
    run, the pattern as written or with its spaces optional): [{id: its card id, label}]. Only for entries the audit kept
    the runs of."""
    runs = [t.strip() for t in e.get('runs') or [] if t.strip()]
    if not runs: return []
    out = []
    for i, r in enumerate(((wo or {}).get('artifacts') or {}).get('text_rules') or []):
        ps = r.get('pages') if isinstance(r, dict) else None
        if not (isinstance(ps, list) and len(ps) == 2 and ps[0] <= e['first'] <= ps[1]): continue
        try: rx = [re.compile(r.get('regex', '.*'), re.S), re.compile(gaptext.loosen(r.get('regex', '.*')), re.S)]
        except re.error: continue
        if all(any(x.fullmatch(t) or x.fullmatch(re.sub(r'\s+', ' ', t)) for x in rx) for t in runs):
            out.append({'id': f'artifacts.text_rules:{i}', 'label': r.get('label') or 'text rule'})
    return out

def _order_findings(ro, add, items):
    """The reading order's findings as cards (seen only, with a note: nothing is applied), for what no decision answers: a
    section read away from its printed place that no text rule hides, each page whose text jumps back up a column, and one
    card for the small sections read late. Findings a text rule hides are listed on that rule's card instead (hides)."""
    es = ro.get('entries') or []
    def short(e): return str(e.get('text') or '').strip()[:60] or None
    hides = {}
    for kind, xs in (('away', ro.get('flagged') or []), ('late', ro.get('late') or [])):
        for x in xs:
            for r in x.get('hidden_by_rules') or []:
                hides.setdefault(r['id'], []).append({'page': x['first'], 'text': short(es[x['i']]), 'late': kind == 'late'})
    for it in items:
        if it['id'] in hides: it['context']['hides'] = hides[it['id']]
    for x in ro.get('flagged') or []:
        if x.get('hidden_by_rules'): continue
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
    late = [x for x in ro.get('late') or [] if not x.get('hidden_by_rules')]
    if late:
        add('reading_order:late', 'reading_order', 'Reading order check', None,
            {'finding': 'late', 'count': len(late), 'pages': [x['first'] for x in late]}, f'{len(late)} small sections read late',
            page=late[0]['first'], pages=[min(x['first'] for x in late), max(x['first'] for x in late)], count_late=len(late),
            late=[{'page': x['first'], 'after': x['after'], 'text': short(es[x['i']])} for x in late[:LATE_LISTED]])

def _under(order, by, e, host):
    """True when entry e lies inside the container host (following each entry's nearest container above it)."""
    p, seen = e.get('parent'), set()
    while p is not None and p not in seen:
        if p == host: return True
        seen.add(p); p = (by.get(p) or {}).get('parent')
    return False

def changed_move(wo, data, decisions):
    """The preview for a section move the reviewer changed, worked out the same way as the AI's (for /save), or None."""
    ms = wo.get('move_section')
    if (decisions.get('move_section') or {}).get('status') != 'changed' or not isinstance(ms, dict) or len(ms.get('pages') or []) != 2: return None
    return {'pages': ms['pages'], 'before_page': ms.get('before_page'),
            **move_preview((data.get('reading_order') or {}).get('entries'), ms['pages'][0], ms['pages'][1], ms.get('before_page'))}

def move_preview(order, a, b, before):
    """What move_section would do, worked out on the original's tags with the executor's own match (lib/readorder.py):
    {candidates, host_found, moved, moved_pages, host, host_pages, lands_before, siblings_before, siblings_after, flags_before,
    flags_after}. apply.py
    matches again on the tree it edits, which earlier steps may have changed, so this is a preview. Empty when the order
    has no detail (an older run) or the pages are not numbers."""
    if not order or not all(isinstance(x, int) for x in (a, b, before)) or not any('group' in e for e in order): return {}
    by = {e['id']: e for e in order}
    groups = {}
    for e in order:
        if e.get('group'): groups.setdefault(None if e.get('top') else e.get('under'), []).append(e['id'])
    cand, host = readorder.section_move(None, lambda n: groups.get(n, []), lambda n: by[n].get('firsts') or [],
                                        lambda n: (by[n]['first'], by[n]['last']) if by[n].get('first') is not None else None, a, b, before)
    out = {'candidates': len(cand), 'host_found': host is not None, 'flags_before': len(readorder.out_of_order(order))}
    if len(cand) != 1 or host is None: return out
    s = cand[0][0]
    out.update(moved_pages=[by[s]['first'], by[s]['last']], host=by[host]['style'], host_pages=[by[host]['first'], by[host]['last']])
    block = [e for e in order if e['id'] == s or _under(order, by, e, s)]
    ids = {e['id'] for e in block}
    rest = [e for e in order if e['id'] not in ids]
    hi = next(i for i, e in enumerate(rest) if e['id'] == host)
    inside = [i for i in range(hi + 1, len(rest)) if _under(rest, by, rest[i], host)]
    j = next((i for i in inside if rest[i].get('parent') == host and (rest[i].get('first') or 0) >= before), (inside[-1] + 1) if inside else hi + 1)
    shift = by[host]['depth'] + 1 - by[s]['depth']
    moved = [{**e, 'depth': e['depth'] + shift, **({'parent': host} if e['id'] == s else {})} for e in block]
    after = rest[:j] + moved + rest[j:]
    def kids_of(es): return [{k: e.get(k) for k in ('id', 'style', 'first', 'last', 'text')} for e in es if e.get('parent') == host]
    return {**out, 'moved': s, 'lands_before': rest[j]['id'] if j < len(rest) else None,
            'siblings_before': kids_of(order), 'siblings_after': kids_of(after), 'flags_after': len(readorder.out_of_order(after))}

def pages_to_render(items, N):
    """Sets every item's page images; returns the priority items' pages, in review order.
    They are not rendered here: the review server renders each page the first time the browser asks for it."""
    for it in items: it['images'] = page_images(it, N)
    want = []
    for it in order(items):
        want += [p for p in (int(PAGE_PNG.search(x).group(1)) for x in it['images']) if p not in want]
    return want

# ------------------------------------------------------------------ addable
def addable(wo, digest):
    """What a person can add that the AI did not decide, by kind: targets from the digest lists only, so the checks
    apply to an addition as they do to the AI's decisions. A target the AI already decided is changed on its card instead."""
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
    return {k: v for k, v in out.items() if v}

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
    ro = reading_order_for(os.path.join(R, '_audit'), digest, ai)
    items = build_items(ai, digest, ro['entries'], ro)
    pages_to_render(items, digest['source']['pages'])
    first = sorted({int(PAGE_PNG.search(x).group(1)) for it in items if it['priority'] == 1 for x in it['images']})
    render_pages(pdf, first, os.path.join(R, 'review_pages'))
    data = {'book': digest['source'].get('file'), 'run': os.path.basename(os.path.normpath(R)), 'pages': digest['source']['pages'],
            'pdf': os.path.abspath(pdf), 'groups': GROUPS, 'levels': LEVELS, 'add_kinds': ADD_KINDS, 'items': items,
            'addable': addable(ai, digest), 'reading_order': ro}
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
              'adopt_orphans', 'move_to_document_start'):
        if k in wo and wo[k] in ([], {}) and ai_wo.get(k): del wo[k]       # a key with every item rejected is left out, as the AI would
    return wo

def _int(v):
    try: return int(v)
    except (TypeError, ValueError): return v                # left as it is: the check refuses it with its reason

def add_entries(wo, additions, adds, reviewer=''):
    """The person's own decisions added to wo (in place), each in the shape the AI writes. Returns what was refused:
    [{id, why}]. Only targets listed by addable() are taken, and never one that wo already decides."""
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
        if k == 'retype':
            if any(it.get('obj') == target for it in wo.get('retype') or []): no('already decided: change it on its card'); continue
            wo.setdefault('retype', []).append({'obj': target, 'type': v, 'why': why})
        elif k == 'alt':
            if any(it.get('obj') == target for it in (wo.get('artifacts') or {}).get('elements') or []):
                no('the AI marked this figure as decoration: reject that decision first'); continue
            if any(it.get('obj') == target for it in wo.get('alt') or []): no('already decided: change it on its card'); continue
            wo.setdefault('alt', []).append({'obj': target, 'alt': v, 'why': why})
        elif k == 'page_figures':
            wo.setdefault('page_figures', []).append({'page': target, 'alt': v, 'why': why})
        elif k == 'tables':
            v = v if isinstance(v, dict) else {}
            wo.setdefault('tables', []).append({'obj': target, 'header_rows': _int(v.get('header_rows', 0)),
                                                'header_cols': _int(v.get('header_cols', 0)), 'why': why})
        elif k == 'rolemap': wo.setdefault('rolemap', {})[target] = v
        elif k == 'document': wo.setdefault('document', {})[target] = v
        elif k == 'ocr_words': wo.setdefault('ocr_words', []).append({'id': target, 'reads': v})
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
    return workorder_check.check(wo, digest, set(), {w['id'] for w in digest.get('ocr_words') or []})

def preview(R, wo):
    """What the check would drop from wo, and the gaps left after it, without changing wo."""
    wo = copy.deepcopy(wo)
    dropped = check(R, wo)
    return dropped, gaps(wo, load(os.path.join(R, '_audit', 'digest.json')))

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
