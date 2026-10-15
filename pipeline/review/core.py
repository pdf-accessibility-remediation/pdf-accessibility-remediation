"""review/core.py: the review step's logic, with no web server and no HTML (a later front end can call it directly).

    items = build_items(wo, digest)                   # every decision in the work order, with its context and priority group
    wo2   = apply_decisions(ai_wo, items, decisions)  # a person's approve / change / reject applied to a copy of the AI's order
    changes = diff(ai_wo, wo2)                        # what the person changed, item by item
    finish(R, ai_wo, wo2, reviewer, date, method, …)  # checks the order again, writes review.json and the reviewed workorder.json

The two formats a front end needs (also in docs/work-order.md):
  item:      {id, key, kind, label, page, page_label, pages, before, ai, edit, options, context, priority, images}
  decisions: {id: {status: approved | changed | rejected | seen, value?, note?}}
"""
import os, re, sys, copy, json, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import workorder_check  # noqa: E402

LEVELS = sorted(workorder_check.ALLOWED - {'Figure'}, key=lambda t: (not t.startswith('H'), t))
HEADING = {'H1', 'H2', 'H3', 'H4', 'H5', 'H6'}
GROUPS = {1: 'H1 and title', 2: 'Style-wide mappings', 3: 'Heading-level changes', 4: 'Rules that can hide text',
          5: 'Pages the AI asked about', 6: 'General'}
SEEN_ONLY = {'deferrals', 'notes_for_reviewer'}       # not applied by apply.py: a person marks them seen, with a note
PAGE_REF = re.compile(r'PDF (\d+)(?:\s*[–-]\s*(\d+))?')

def save(path, obj):
    with open(path, 'w', encoding='utf-8') as f: f.write(json.dumps(obj, ensure_ascii=False, indent=1))

def load(path, default=None):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default

# ------------------------------------------------------------------ items
def build_items(wo, digest):
    N = digest['source']['pages']
    labels = {}
    for row in digest.get('page_map') or []:
        p, lab = (str(row).split('|') + ['', ''])[:2]
        if p.isdigit(): labels[int(p)] = lab
    by_obj = {}
    for k in ('elements', 'heading_candidates', 'headings', 'figures', 'lists', 'tables'):
        for x in digest.get(k) or []: by_obj.setdefault(x['obj'], {**x, '_from': k})
    styles = {s['style']: s for s in digest.get('styles') or []}
    figs = {f['obj']: f for f in digest.get('figures') or []}
    pfigs = {pf['page']: pf for pf in digest.get('page_figures') or []}
    words = {w['id']: w for w in digest.get('ocr_words') or []}
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
        add(f'ocr_words:{it.get("id")}', 'ocr_words', 'OCR words', ['ocr_words', i], it.get('reads'), f'OCR read "{it.get("text")}"',
            page=(w.get('pages') or [None])[0], before=it.get('text'), edit='text', field='reads', count=it.get('count'))
    for i, it in enumerate(wo.get('deferrals') or []):
        ps = [p for p in it.get('pages') or [] if isinstance(p, int)] if isinstance(it, dict) else []
        add(f'deferrals:{i}', 'deferrals', 'Deferred by the AI', ['deferrals', i], it, (it or {}).get('what') or 'Deferral',
            page=min(ps) if ps else None, pages=[min(ps), max(ps)] if ps else None, why=(it or {}).get('why'))
    if wo.get('notes_for_reviewer'):
        refs = sorted({int(m.group(1)) for m in PAGE_REF.finditer(wo['notes_for_reviewer']) if 1 <= int(m.group(1)) <= N})
        add('notes_for_reviewer', 'notes_for_reviewer', 'Deferred by the AI', ['notes_for_reviewer'], wo['notes_for_reviewer'],
            'Note to the reviewer from the AI', page=refs[0] if refs else None, page_refs=refs)
    listed = {'retype', 'rolemap', 'actual_text', 'merges', 'document', 'alt', 'page_figures', 'tables', 'flatten', 'keep_lists',
              'artifacts', 'ocr_words', 'deferrals', 'notes_for_reviewer', 'schema'} | workorder_check.META
    for k, v in wo.items():
        if k not in listed:
            add(f'key:{k}', k, 'Other decisions', [k], v, k)

    # priority groups: fixed rules, no model
    for it in items:
        k, b, ai = it['key'], it['before'], it['ai']
        if k == 'document' and it['id'] == 'document.title': it['priority'] = 1
        elif k in ('retype', 'rolemap') and ('H1' in (b, ai)) and b != ai: it['priority'] = 1
        elif k == 'rolemap': it['priority'] = 2
        elif k == 'retype' and b != ai and (b in HEADING or ai in HEADING): it['priority'] = 3
        elif k == 'artifacts' and it['loc'][1] in ('text_rules', 'untagged'): it['priority'] = 4
        elif k == 'deferrals':
            p = it['pages']
            it['priority'] = 5 if p and (p[1] - p[0] + 1) <= N / 2 else 6
        elif k == 'notes_for_reviewer': it['priority'] = 5 if it['context'].get('page_refs') else 6
    return items

def order(items):
    """Priority items by group, then page (style mappings: most elements first)."""
    def key(it):
        g = it['priority']
        return (g, -(it['context'].get('count') or 0) if g == 2 else 0, it['page'] if it['page'] is not None else 10 ** 9)
    return sorted([it for it in items if it['priority']], key=key)

def pages_to_render(items, N, limit=80):
    """Pages to show beside the priority items: the item's page, and the pages either side of a heading decision."""
    want = []
    for it in order(items):
        ps = [it['page']] if it['page'] else []
        if it['priority'] in (1, 3) and it['page']: ps = [it['page'] - 1, it['page'], it['page'] + 1]
        if it['key'] == 'notes_for_reviewer': ps = it['context'].get('page_refs', [])[:6]
        ps = [p for p in ps if 1 <= p <= N]
        it['images'] = [f'review_pages/page_{p:03d}.png' for p in ps]
        want += [p for p in ps if p not in want]
    return want[:limit]

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
    """Write review_items.json and the page images. Runs when run_api.sh stops for review."""
    ai = load(os.path.join(R, 'workorder.ai.json'))
    digest = load(os.path.join(R, '_audit', 'digest.json'))
    if ai is None or digest is None: sys.exit(f'{R} has no workorder.ai.json or _audit/digest.json: run run_api.sh with REVIEW=1 first')
    items = build_items(ai, digest)
    pages = pages_to_render(items, digest['source']['pages'])
    render_pages(pdf, pages, os.path.join(R, 'review_pages'))
    have = set(os.listdir(os.path.join(R, 'review_pages')))
    for it in items: it['images'] = [x for x in it['images'] if os.path.basename(x) in have]
    data = {'book': digest['source'].get('file'), 'run': os.path.basename(os.path.normpath(R)), 'pages': digest['source']['pages'],
            'groups': GROUPS, 'levels': LEVELS, 'items': items}
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
            elif it['field']: parent[last][it['field']] = v
            else: parent[last] = v
    for loc in sorted(drop, key=lambda l: [str(x) if not isinstance(x, int) else f'{x:09d}' for x in l], reverse=True):
        parent = wo
        for k in loc[:-1]: parent = parent[k]
        if isinstance(parent, list): del parent[loc[-1]]
        else: parent.pop(loc[-1], None)
    for k in ('retype', 'alt', 'page_figures', 'tables', 'actual_text', 'merges', 'flatten', 'keep_lists', 'ocr_words'):
        if k in wo and wo[k] == [] and ai_wo.get(k): del wo[k]             # a key with every item rejected is left out, as the AI would
    return wo

def unreviewed(items, decisions):
    return [it['id'] for it in items if not (decisions.get(it['id']) or {}).get('status')]

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
    """The decide.py checks on a reviewed order, with the images that were really sent to the model."""
    digest = load(os.path.join(R, '_audit', 'digest.json'))
    ctx = (load(os.path.join(R, 'validation.json'), {}) or {}).get('context')
    if ctx is None:                      # a run from before decide.py saved this: assume every image and word sheet was sent
        print('note: validation.json has no context (older run): the check assumes every figure image and word sheet was sent')
        ctx = {'not_sent': [], 'words_sent': [w['id'] for w in digest.get('ocr_words') or []]}
    return workorder_check.check(wo, digest, set(ctx['not_sent']), set(ctx['words_sent']))

def finish(R, ai_wo, wo, reviewer, date, method, decisions=None, items=None, note=None):
    if not (reviewer or '').strip(): raise ValueError('a reviewer name is needed')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date or ''): raise ValueError('the date must be YYYY-MM-DD')
    if (wo.get('source') or {}).get('sha256') != (ai_wo.get('source') or {}).get('sha256'):
        raise ValueError('source.sha256 differs from the AI\'s work order: leave "source" as it was')
    dropped = check(R, wo)
    decisions = decisions or {}
    statuses = [((decisions.get(it['id']) or {}).get('status') or 'accepted_unreviewed') for it in items or []]
    counts = {s: statuses.count(s) for s in ('approved', 'changed', 'rejected', 'seen', 'accepted_unreviewed')} if items else None
    changes = diff(ai_wo, wo)
    v = {'reviewer': reviewer.strip(), 'date': date, 'recorded': datetime.datetime.now().isoformat(timespec='seconds'), 'method': method,
         'changes': changes, 'dropped_on_check': dropped,
         **({'counts': counts} if counts else {}),
         **({'notes': {k: d['note'] for k, d in decisions.items() if (d or {}).get('note')}} if decisions else {}),
         **({'note': note} if note else {})}
    old = load(os.path.join(R, 'review.json'))
    if old: v['history'] = old.pop('history', []) + [old]
    wo['reviewed_by'] = f'{v["reviewer"]} on {date}'
    save(os.path.join(R, 'workorder.json'), wo)
    save(os.path.join(R, 'review.json'), v)
    return v
