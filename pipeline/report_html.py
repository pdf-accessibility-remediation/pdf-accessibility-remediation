"""report_html.py: the offline dashboards beside review.md and summary.md. No model, nothing sent, no internet.

    python3 report_html.py RUN_DIR [RUN_DIR ...]     review.html for each finished run (report.py runs this itself)
    python3 report_html.py --summary BATCH_DIR       summary.html for a batch, plus review.html for each of its books

Every number comes from the run's `glance` in record.json (lib/glance.py), the same numbers as review.md's
"At a glance"; a run made before glance existed gets it computed from its record.json and review.md. Each page is one
file: the CSS is inlined (colours from review/palette.css, copied from the review page's), there are no external scripts,
and it reads in full without JavaScript. JavaScript only adds the issue filter, the keyboard page strip and sorting.
The pages quote book text as review.md does, so they stay under runs/ and are never committed.
"""
import sys, os, re, json, csv, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import glance as G  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE = open(os.path.join(HERE, 'review', 'palette.css'), encoding='utf-8').read()
CSS = PALETTE + """
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
a { color: var(--accent); }
.vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.skip { position: absolute; left: -999px; } .skip:focus { left: 8px; top: 8px; background: var(--panel); padding: 4px 8px; z-index: 9; }
header.top { background: var(--panel); border-bottom: 1px solid var(--line); padding: 12px 16px; }
header.top h1 { font-size: 19px; margin: 0 0 4px; overflow-wrap: anywhere; }
.meta { color: var(--muted); font-size: 13px; }
main { max-width: 1200px; margin: 0 auto; padding: 16px; }
h2 { font-size: 17px; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 1px solid var(--line); }
.ship { background: var(--panel); border: 1px solid var(--line); border-left: 6px solid var(--reject); border-radius: 8px; padding: 10px 14px; }
.ship.yes { border-left-color: var(--ok); }
.ship h2 { margin: 0 0 6px; font-size: 17px; border: 0; padding: 0; } .ship p { margin: 6px 0 0; } .ship ul { margin: 0; padding-left: 20px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 14px 0; }
.card { background: var(--panel); border: 1px solid var(--line); border-top: 5px solid var(--line); border-radius: 8px; padding: 10px 14px; }
.card.good { border-top-color: var(--ok); } .card.bad { border-top-color: var(--reject); } .card.warn { border-top-color: var(--change); }
.card h3 { font-size: 13px; margin: 0; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.card .big { font-size: 26px; font-weight: 650; margin: 2px 0; } .card .lab { font-weight: 600; } .card p { margin: 2px 0; font-size: 13px; color: var(--muted); }
table { border-collapse: collapse; width: 100%; background: var(--panel); font-size: 14px; }
th, td { min-width: 3.5em; border: 1px solid var(--line); padding: 4px 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: var(--bg); } td.num, th.num { text-align: right; white-space: nowrap; }
.chart { display: grid; grid-template-columns: minmax(120px, max-content) 1fr; gap: 4px 10px; align-items: center; margin: 6px 0 8px; font-size: 13px; }
.bar { height: 12px; background: var(--line); border-radius: 3px; overflow: hidden; } .bar i { display: block; height: 100%; background: var(--accent); }
.bar i.after { background: var(--change); }
.tag { display: inline-block; font-size: 12px; font-weight: 600; padding: 0 6px; border-radius: 4px; border: 1px solid var(--line); white-space: nowrap; }
.tag.safety { color: var(--reject); border-color: var(--reject); } .tag.ship, .tag.check { color: var(--change); border-color: var(--change); }
.tag.ok { color: var(--ok); border-color: var(--ok); }
.strip { display: flex; flex-wrap: wrap; gap: 2px; padding: 6px; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; }
.strip:focus { outline: 3px solid var(--accent); outline-offset: 2px; }
.cell { width: 9px; height: 18px; background: var(--line); border-radius: 2px; }
.cell.person { background: var(--change); }
.cell.safety { background: repeating-linear-gradient(45deg, var(--reject) 0 3px, var(--panel) 3px 5px); }
.cell.active { outline: 2px solid var(--ink); outline-offset: 1px; }
#stripinfo { min-height: 1.5em; margin: 6px 0; font-size: 14px; }
.legend { font-size: 13px; color: var(--muted); } .legend .cell { display: inline-block; vertical-align: middle; margin: 0 4px 0 10px; }
details.sec { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin: 0 0 8px; padding: 0 12px; }
details.sec > summary { cursor: pointer; padding: 8px 0; } details.sec > summary h3 { display: inline; font-size: 15px; margin: 0; }
details.sec > summary .count { color: var(--muted); font-size: 13px; margin-left: 8px; }
details.sec[open] > summary { border-bottom: 1px solid var(--line); margin-bottom: 8px; }
code { font-size: 13px; background: var(--bg); padding: 0 3px; border-radius: 3px; }
.filter { margin: 6px 0; } select, button { font: inherit; color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 3px 8px; }
th button { border: 0; background: none; padding: 0; font-weight: 700; cursor: pointer; text-align: left; }
.note { color: var(--muted); font-size: 13px; }
details.fold { margin-top: 6px; font-size: 13px; } details.fold summary { cursor: pointer; color: var(--accent); }
ul.checks { list-style: none; padding-left: 4px; margin: 4px 0 0; }
h2.inline { display: inline; font-size: 15px; border: 0; margin: 0; padding: 0; }
h3.sub { font-size: 15px; margin: 12px 0 4px; }
.nw { white-space: nowrap; }
.hit, :target { outline: 3px solid var(--accent); outline-offset: 1px; }
@media (max-width: 640px) { main { padding: 10px; } .chart { grid-template-columns: 1fr; } }
"""
E = html.escape

def inline(t):
    """One line of review.md text as HTML: escaped first, then `code`, **bold** and [links](relative, #anchor or http)."""
    t = E(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    return re.sub(r'\[([^\]]+)\]\(((?:#|https?://|[\w./-]+)[^)\s]*)\)', lambda m: f'<a href="{E(m.group(2))}">{m.group(1)}</a>', t)

def md_html(lines, prefix=None):
    """The subset of Markdown review.md uses: tables, bullet lists, paragraphs, inline code, bold and links. With a prefix,
    every list item and table row gets its own id (prefix-1, prefix-2, …) so a link can land on it; returns (html, items)
    where items are (id, the line as written)."""
    out, items, i = [], [], 0
    def nid(raw):
        if not prefix: return ''
        items.append((f'{prefix}-{len(items) + 1}', raw)); return f' id="{E(items[-1][0])}"'
    while i < len(lines):
        l = lines[i]
        if l.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'): rows.append(lines[i]); i += 1
            head = len(rows) > 1 and re.match(r'^\|[-:| ]+\|$', rows[1].strip())
            body = [r for r in rows if not re.match(r'^\|[-:| ]+\|$', r.strip())]
            out.append('<table>')
            for k, r in enumerate(body):
                cells = [c.strip() for c in r.strip().strip('|').split(' | ')]
                if head and k == 0: out.append('<tr>' + ''.join(f'<th scope="col">{inline(c)}</th>' for c in cells) + '</tr>')
                else: out.append(f'<tr{nid(r)}>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
            out.append('</table>'); continue
        if l.startswith('- '):
            out.append('<ul>')
            while i < len(lines) and lines[i].startswith('- '): out.append(f'<li{nid(lines[i])}>{inline(lines[i][2:])}</li>'); i += 1
            out.append('</ul>'); continue
        if l.strip(): out.append(f'<p>{inline(l)}</p>')
        i += 1
    return '\n'.join(out), items

def page(title, body, script=''):
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{E(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<a class="skip" href="#main">Skip to the content</a>\n{body}\n'
            + (f'<script>\n{script}\n</script>\n' if script else '') + '</body>\n</html>\n')

def labels_of(R, rec):
    try:
        import pikepdf
        with pikepdf.open(os.path.join(R, rec['document']['output'])) as p: return {i + 1: str(pg.label) for i, pg in enumerate(p.pages)}
    except Exception: return {}

def han_pages(R):
    p = os.path.join(R, 'han_review.csv')
    if not os.path.exists(p): return []
    with open(p, encoding='utf-8') as f: return [int(r['pdf_page']) for r in csv.DictReader(f) if str(r.get('pdf_page') or '').isdigit()]

def glance_of(R, rec=None, labels=None):
    """The run's glance: from record.json, or computed from record.json and review.md for a run made before it existed."""
    rec = rec or json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
    if rec.get('glance', {}).get('schema') == G.SCHEMA: return rec['glance']
    md = open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    return G.glance(rec, md, labels if labels is not None else labels_of(R, rec), han_pages(R))

# review.html reports WCAG only: review.md (the record) keeps the PDF/UA-only rules and wording, the page leaves them out
WCAG_ONLY = [(re.compile(r'\s*·\s*\d+ PDF/UA-only rules? not counted'), ''), (re.compile(r' \(ISO 14289-1 [\d.]+(?:-\d+)?, PDF/UA\)'), ''),
             (re.compile(r'PDF/UA requires embedded fonts \([\d.]+\); a person'), 'A person'), (re.compile(r'ISO 14289-1 (\d)'), r'\1'),
             (re.compile(r'Rules that only PDF/UA requires are listed apart and do not count\. '), ''),
             (re.compile(r'Not yet classified as WCAG or PDF/UA-only'), 'Not yet classified as WCAG')]
def wcag_only(lines):
    out, skip = [], False
    for l in lines:
        if l.startswith('PDF/UA-only, not required for WCAG'): skip = True; continue
        if skip:
            if l.startswith('- ') or not l.strip(): continue
            skip = False
        for rx, to in WCAG_ONLY: l = rx.sub(to, l)
        out.append(l)
    return out

def _plain(t): return re.sub(r'[*`]', '', t)

KIND = {'safety': 'Safety', 'ship': 'Ship condition', 'check': 'CHECK row', 'executor': 'Deferred by the executor', 'ai': 'Deferred by the AI'}

def review_html(R, rec=None, md=None, labels=None):
    rec = rec or json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
    md = md if md is not None else open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    labels = labels if labels is not None else labels_of(R, rec)
    g = glance_of(R, rec, labels)
    doc, run = rec.get('document') or {}, rec.get('run') or {}
    book = doc.get('file') or 'file name not recorded'
    def pgl(n):
        lab = labels.get(int(n), '')
        return f'PDF {n}' + (f' (printed {lab})' if lab and lab != str(n) else '')
    lines = md.split('\n')
    # review.md's sections, each with an id per item, so "Details" can land on the very item
    start = next((k for k, l in enumerate(lines) if l == '## Automated checks'), len(lines))
    blocks, cur = [], None
    for l in lines[start:]:
        m3 = re.match(r'^### (\d+)\. (.+?)\s*$', l)
        if l.startswith('## ') or m3:
            cur = {'title': l[3:].strip() if not m3 else f'{m3.group(1)}. {m3.group(2)}', 'h2': not m3, 'lines': []}; blocks.append(cur)
        elif cur is not None: cur['lines'].append(l)
    for b in blocks:
        b['anchor'] = G.slug(b['title']); b['html'], b['items'] = md_html(wcag_only(b['lines']), b['anchor'])
    by_anchor = {b['anchor']: b for b in blocks}
    def item_for(x):
        b = by_anchor.get(x['where']['anchor']); f = x.get('find')
        if not b or not f: return None
        f = _plain(f)
        return next((iid for iid, raw in b['items'] if f in _plain(raw)), None)
    head = lines[1:next((k for k, l in enumerate(lines) if l in ('## At a glance', '## Automated checks')), len(lines))]
    run_details = [l for l in head if l.strip() and not l.startswith('Automated checks are evidence')]

    B = [f'<header class="top"><h1>Review: {E(book)}</h1><div class="meta">'
         + ' · '.join(E(x) for x in [f'run {os.path.basename(os.path.dirname(os.path.normpath(R)))}/{os.path.basename(os.path.normpath(R))}', f'{doc.get("pages") or "pages not counted"} pages',
                                      f'model {run.get("model") or "not recorded"}', f'prompt {run.get("prompt_file") or "not recorded"}',
                                      f'cost ${rec.get("cost_total_usd"):.3f}' if rec.get('cost_total_usd') is not None else 'cost: call did not finish',
                                      f'run {run.get("started") or "start time not recorded"}'])
         + ' · <a href="review.md">review.md</a> (the record, as text)</div></header>', '<main id="main">']
    # ---- ready to ship
    B.append(f'<section class="ship{" yes" if g["ready"] else ""}" aria-labelledby="ship-h"><h2 id="ship-h">Ready to ship? {"Yes" if g["ready"] else "No"}</h2><ul>'
             + ''.join(f'<li>{E(s["what"])}: <strong>{E(s["text"])}</strong></li>' for s in g['ship']) + '</ul>')
    if not g['ship'][0]['ok']:
        B.append('<p class="note">The review page is the final sign-off. To review this book\'s AI decisions there, run it again with its saved reply '
                 'and <code>REVIEW=1</code>, then <code>python3 review_workorder.py &lt;run&gt; --serve</code> (docs: review-step.md, "Sign-off").</p>')
    B.append('</section>')
    # ---- four cards; the safety card holds its checks in a fold (open, failed first, when one fails)
    np_, ad, vg = g['needs_person'], g['ai_decisions'], g['verapdf']
    saf = sorted(g['safety'], key=lambda x: x['ok']); saf_bad = [x for x in saf if not x['ok']]
    safety_fold = (f'<details class="fold"{" open" if saf_bad else ""}><summary>The {len(saf)} safety checks</summary><ul class="checks">'
                   + ''.join(f'<li>{"<strong>FAILED ✘</strong>" if not x["ok"] else "OK ✔"} {E(x["what"])}</li>' for x in saf) + '</ul></details>') if saf else ''
    cards = [('Safety', 'good' if g['safety_ok'] else 'bad', 'OK' if g['safety_ok'] else ('Failed' if saf else 'Not checked'),
              f'{len(saf) - len(saf_bad)} of {len(saf)} checks OK', safety_fold),
             ('Needs a person', 'warn' if np_['total'] else 'good', str(np_['total']),
              f'{np_["ai_deferrals"]} deferred by the AI · {np_["executor_deferrals"]} deferred by the executor · {np_["check_rows"]} CHECK rows', ''),
             ('AI decisions', 'good' if g['ship'][0]['ok'] else 'warn', f'{ad["count"]:,}',
              (f'approved by {ad["reviewed"]["reviewer"]} on {ad["reviewed"]["date"]}' if ad.get('reviewed') and g['ship'][0]['ok']
               else 'reviewed, not signed off' if ad.get('reviewed') else 'Not reviewed by a person'), ''),
             ('veraPDF (WCAG rules)', ('good' if vg.get('after_rules') == 0 else 'warn') if vg.get('ran_after') else 'warn',
              (f'{vg.get("before_rules", "–")} → {vg["after_rules"]}' if vg.get('ran_after') else 'Not run'),
              (f'{vg.get("before_checks", 0):,} → {vg["after_checks"]:,} failed checks · {len(vg.get("newly_failing") or [])} newly failing' if vg.get('ran_after') else (vg.get('not_run') or '')), '')]
    def lab(cls, big):
        t = {"good": "OK", "bad": "Failed", "warn": "Needs attention"}[cls]
        return '' if t.lower() == big.lower() else f'<p class="lab">{E(t)}</p>'
    B.append('<section aria-labelledby="st-h"><h2 id="st-h" class="vh">Status</h2><div class="cards">' + ''.join(
        f'<div class="card {cls}"><h3>{E(t)}</h3><div class="big">{E(big)}</div>{lab(cls, big)}<p>{E(sub)}</p>{extra}</div>'
        for t, cls, big, sub, extra in cards) + '</div></section>')
    if g['fixed_automatically']:
        B.append('<p><strong>Fixed automatically (no AI):</strong> ' + ' · '.join(E(f'{x["what"]} {x["count"]:,}') for x in sorted(g['fixed_automatically'], key=lambda x: -x['count'])) + '</p>')
    B.append('<p class="note">Automated checks are evidence, not sign-off. PAC 2026 is the final manual check.</p>')
    if run_details:
        B.append('<details class="sec" id="run-details"><summary><h2 class="inline">Run details</h2></summary><ul>'
                 + ''.join(f'<li>{inline(l)}</li>' for l in run_details) + '</ul></details>')
    # ---- issues, in full; "Details" opens the folded section at the very item (without JavaScript: the section)
    iss = g['issues']
    B.append(f'<section aria-labelledby="iss-h"><h2 id="iss-h">What needs a person ({len(iss)})</h2>')
    if iss:
        kinds = [k for k in KIND if any(x['kind'] == k for x in iss)]
        if len(kinds) > 1:
            B.append('<div class="filter" hidden id="filterbox"><label for="kind">Show </label><select id="kind"><option value="">all sources</option>'
                     + ''.join(f'<option value="{k}">{E(KIND[k])}</option>' for k in kinds) + '</select> <span id="shown" aria-live="polite"></span></div>')
        B.append('<table id="issues"><tr><th scope="col">Issue</th><th scope="col">Source</th><th scope="col">Pages</th><th scope="col" class="nw">Details</th></tr>')
        for x in iss:
            w = x['where']; iid = item_for(x)
            link = (f'<a href="#{E(w["anchor"])}"' + (f' data-item="{E(iid)}"' if iid else '') + f'>Details<span class="vh">: {E(x["text"])}</span></a>'
                    + (f' <span class="note">(§{w["n"]})</span>' if w['n'] else ''))
            B.append(f'<tr data-kind="{x["kind"]}"><td>{E(x["text"])}</td><td><span class="tag {x["kind"]}">{E(KIND[x["kind"]])}</span></td>'
                     f'<td>{E(x["pages_text"]) or "see the details"}</td><td class="nw">{link}</td></tr>')
        B.append('</table>')
    else: B.append('<p>Nothing needs a person.</p>')
    B.append('</section>')
    # ---- counts: a chart (hidden when it would have one bar) with its table
    B.append('<section aria-labelledby="ch-h"><h2 id="ch-h">Counts</h2>')
    if vg.get('by_who'):
        mx = max([1] + [v[k] for v in vg['by_who'].values() for k in ('before', 'after')])
        B.append('<h3 class="sub">veraPDF WCAG rules failing, by who fixes them</h3><div class="chart" aria-hidden="true">')
        for w, v in vg['by_who'].items():
            B.append(f'<span>{E(w)}: before</span><div class="bar"><i style="width:{100 * v["before"] / mx:.0f}%"></i></div>'
                     f'<span>{E(w)}: after</span><div class="bar"><i class="after" style="width:{100 * v["after"] / mx:.0f}%"></i></div>')
        B.append('</div><table><tr><th scope="col">Who fixes</th><th scope="col" class="num">Before</th><th scope="col" class="num">After</th></tr>'
                 + ''.join(f'<tr><td>{E(w)}</td><td class="num">{v["before"]}</td><td class="num">{v["after"]}</td></tr>' for w, v in vg['by_who'].items()) + '</table>')
    by_kind = {k: sum(1 for x in iss if x['kind'] == k) for k in KIND}
    by_kind = {k: v for k, v in by_kind.items() if v}
    if by_kind:
        mx = max(by_kind.values())
        B.append('<h3 class="sub">What needs a person, by source</h3>')
        if len(by_kind) > 1:
            B.append('<div class="chart" aria-hidden="true">' + ''.join(f'<span>{E(KIND[k])}</span><div class="bar"><i style="width:{100 * v / mx:.0f}%"></i></div>' for k, v in by_kind.items()) + '</div>')
        B.append('<table><tr><th scope="col">Source</th><th scope="col" class="num">Items</th></tr>'
                 + ''.join(f'<tr><td>{E(KIND[k])}</td><td class="num">{v}</td></tr>' for k, v in by_kind.items()) + '</table>')
    B.append('</section>')
    # ---- page strip (one Tab stop with JavaScript), and the plain list that works without it; descriptions in full
    n_pages = int(g.get('pages') or 0); lv, notes = g['page_level'], g['page_notes']
    if n_pages:
        B.append('<section aria-labelledby="pg-h"><h2 id="pg-h">Pages</h2><p class="legend">Each cell is one page, in order.'
                 '<span class="cell safety"></span>safety check failed<span class="cell person"></span>needs a person<span class="cell"></span>nothing listed</p>')
        B.append('<div class="strip" id="strip" aria-hidden="true">' + ''.join(
            f'<span class="cell {lv.get(str(p), "")}" id="pg-{p}" data-p="{p}" data-l="{E(pgl(p))}" data-lv="{lv.get(str(p), "")}"'
            f' data-n="{E(" · ".join(notes.get(str(p), [])))}" title="{E(pgl(p))}"></span>' for p in range(1, n_pages + 1)) + '</div>'
            '<div id="stripinfo" aria-live="polite"></div>')
        listed = sorted(lv, key=int)
        B.append(f'<details id="pagelist"><summary>Pages with something listed ({len(listed)})</summary><ul>'
                 + ''.join(f'<li>{E(pgl(p))}: {"safety check failed: " if lv[p] == "safety" else ""}{E("; ".join(notes.get(p, [])))}</li>' for p in listed) + '</ul></details></section>')
    # ---- review.md's sections, collapsible, in the same order (WCAG only)
    B.append('<section aria-labelledby="secs-h"><h2 id="secs-h">Details (the sections of review.md)</h2>')
    for b in blocks:
        if b['h2'] and b['title'] == 'For a person to check':
            if any(x.strip() for x in b['lines']): B.append('<h2>For a person to check</h2>')
            continue
        n_items = len(b['items'])
        if b['title'] == 'Automated checks':
            cnt = f'{sum(1 for _, r in b["items"] if "**CHECK**" in r)} CHECK of {n_items}'
        else: cnt = f'{n_items} item{"" if n_items == 1 else "s"}' if n_items else ''
        opened = ' open' if b['title'] == 'Automated checks' and any('**CHECK**' in r for _, r in b['items']) else ''
        B.append(f'<details class="sec" id="{E(b["anchor"])}"{opened}><summary><h3>{E(b["title"])}</h3><span class="count">{E(cnt)}</span></summary>'
                 + b['html'] + '</details>')
    B.append('</section></main>')
    script = r"""
(function () {
  // a link to an item inside a folded section opens every fold around it, then lands on the item
  function land(el) {
    for (var d = el.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
    el.setAttribute('tabindex', '-1'); el.classList.add('hit'); el.scrollIntoView({block: 'center'}); el.focus({preventScroll: true});
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a) return;
    var el = document.getElementById(a.getAttribute('data-item') || a.getAttribute('href').slice(1)); if (!el) return;
    e.preventDefault(); land(el); history.replaceState(null, '', '#' + el.id);
  });
  if (location.hash) { var h = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (h) land(h); }
  var t = document.getElementById('issues'), box = document.getElementById('filterbox');
  if (t && box) {
    box.hidden = false; var sel = document.getElementById('kind'), shown = document.getElementById('shown');
    sel.addEventListener('change', function () {
      var n = 0; Array.prototype.forEach.call(t.querySelectorAll('tr[data-kind]'), function (r) {
        var on = !sel.value || r.getAttribute('data-kind') === sel.value; r.hidden = !on; if (on) n++; });
      shown.textContent = n + ' shown';
    });
  }
  // the page strip: one Tab stop; arrow keys, Home and End move between pages; the page's issues are read out
  var s = document.getElementById('strip'), info = document.getElementById('stripinfo');
  if (!s) return;
  var cells = s.querySelectorAll('.cell'), cur = 0;
  s.removeAttribute('aria-hidden'); s.setAttribute('role', 'listbox'); s.setAttribute('tabindex', '0');
  s.setAttribute('aria-label', 'Pages, one per cell: use the arrow keys');
  Array.prototype.forEach.call(cells, function (c, i) {
    c.setAttribute('role', 'option'); c.removeAttribute('title');
    var lv = c.getAttribute('data-lv');
    c.setAttribute('aria-label', c.getAttribute('data-l') + ': ' + (lv === 'safety' ? 'safety check failed' : lv === 'person' ? 'needs a person' : 'nothing listed'));
    c.addEventListener('mouseenter', function () { show(i); }); c.addEventListener('click', function () { show(i); s.focus(); });
  });
  function show(i) {
    cells[cur].classList.remove('active'); cells[cur].removeAttribute('aria-selected'); cur = i;
    var c = cells[i]; c.classList.add('active'); c.setAttribute('aria-selected', 'true'); s.setAttribute('aria-activedescendant', c.id);
    var n = c.getAttribute('data-n'); info.textContent = c.getAttribute('data-l') + ': ' + (n || 'nothing listed');
  }
  s.addEventListener('focus', function () { show(cur); });
  s.addEventListener('keydown', function (e) {
    var k = e.key, i = cur, row = Math.max(1, Math.round(s.clientWidth / 11));
    if (k === 'ArrowRight') i++; else if (k === 'ArrowLeft') i--; else if (k === 'ArrowDown') i += row; else if (k === 'ArrowUp') i -= row;
    else if (k === 'Home') i = 0; else if (k === 'End') i = cells.length - 1; else return;
    e.preventDefault(); show(Math.max(0, Math.min(cells.length - 1, i)));
  });
})();"""
    out = os.path.join(R, 'review.html')
    open(out, 'w', encoding='utf-8').write(page(f'Review: {book}', '\n'.join(B), script))
    return out

def summary_html(Bdir):
    """summary.html for a batch folder: one row per book, most work first; each book's review.html is (re)built."""
    rows = []
    for name in sorted(os.listdir(Bdir)):
        R = os.path.join(Bdir, name)
        if not os.path.isdir(R): continue
        rp = os.path.join(R, 'record.json')
        if os.path.exists(rp):
            rec = json.load(open(rp, encoding='utf-8')); labels = labels_of(R, rec); g = glance_of(R, rec, labels)
            if not os.path.exists(os.path.join(R, 'review.html')): review_html(R, rec, None, labels)
            vg = g['verapdf']
            rows.append({'name': name, 'done': True, 'ready': g['ready'], 'needs': g['needs_person']['total'], 'np': g['needs_person'],
                         'ai': g['ai_decisions']['count'], 'reviewed': g['ship'][0]['ok'], 'safety': g['safety_ok'],
                         'vb': vg.get('before_rules'), 'va': vg.get('after_rules'), 'new': len(vg.get('newly_failing') or []),
                         'cost': rec.get('cost_total_usd'), 'pages': (rec.get('document') or {}).get('pages')})
        elif os.path.exists(os.path.join(R, '_intake', 'intake.json')):
            ij = json.load(open(os.path.join(R, '_intake', 'intake.json'), encoding='utf-8'))
            rows.append({'name': name, 'done': False, 'status': f'{ij.get("status") or "not finished"}: {ij.get("summary") or ""}'})
    rows.sort(key=lambda r: (not r['done'], -(r.get('needs') or 0)))
    mx = max([1] + [r['needs'] for r in rows if r['done']])
    label = os.path.basename(os.path.normpath(Bdir))
    B = [f'<header class="top"><h1>Batch {E(label)}</h1><div class="meta">{len(rows)} books · <a href="summary.md">summary.md</a> (cost, time and model per book)'
         ' · each book name opens its dashboard</div></header><main id="main">',
         f'<p><strong>Ready to ship:</strong> {sum(1 for r in rows if r.get("ready"))} of {len(rows)} · '
         f'<strong>Needs a person:</strong> {sum(r.get("needs") or 0 for r in rows):,} items · '
         f'<strong>Safety checks failed:</strong> {sum(1 for r in rows if r["done"] and not r["safety"])} books</p>',
         '<p class="note">Sorted by "Needs a person", most work first. Automated checks are evidence, not sign-off.</p>',
         '<table id="books"><thead><tr>' + ''.join(f'<th scope="col"{" class=\"num\"" if n else ""} data-k="{k}"{" aria-sort=\"descending\"" if k == "needs" else ""}>{E(t)}</th>'
                                                  for t, k, n in (('Book', 'name', 0), ('Ready to ship?', 'ready', 0), ('Needs a person', 'needs', 1), ('AI decisions', 'ai', 1),
                                                                  ('Safety', 'safety', 0), ('veraPDF WCAG rules', 'va', 1), ('Cost', 'cost', 1), ('Pages', 'pages', 1))) + '</tr></thead><tbody>']
    for r in rows:
        if not r['done']:
            B.append(f'<tr><td>{E(r["name"])}</td><td colspan="7">{E(r["status"])}</td></tr>'); continue
        B.append(f'<tr><td data-v="{E(r["name"])}"><a href="{E(r["name"])}/review.html">{E(r["name"])}</a></td>'
                 f'<td data-v="{int(r["ready"])}"><span class="tag {"ok" if r["ready"] else "check"}">{"Yes" if r["ready"] else "No"}</span>'
                 f'{"" if r["reviewed"] else " <span class=note>(not reviewed)</span>"}</td>'
                 f'<td class="num" data-v="{r["needs"]}">{r["needs"]} <span class="bar" style="display:inline-block;width:80px;vertical-align:middle" aria-hidden="true"><i style="width:{100 * r["needs"] / mx:.0f}%"></i></span>'
                 f'<br><span class="note">{r["np"]["ai_deferrals"]} AI · {r["np"]["executor_deferrals"]} executor · {r["np"]["check_rows"]} CHECK</span></td>'
                 f'<td class="num" data-v="{r["ai"]}">{r["ai"]:,}</td>'
                 f'<td data-v="{int(r["safety"])}"><span class="tag {"ok" if r["safety"] else "safety"}">{"OK" if r["safety"] else "Failed"}</span></td>'
                 f'<td class="num" data-v="{r["va"] if r["va"] is not None else -1}">' + (f'{r["vb"] if r["vb"] is not None else "–"} → {r["va"]}' if r['va'] is not None else 'not run')
                 + (f' <strong>({r["new"]} new)</strong>' if r['new'] else '') + '</td>'
                 f'<td class="num" data-v="{r["cost"] or 0}">' + (f'${r["cost"]:.3f}' if r['cost'] is not None else 'call did not finish') + '</td>'
                 f'<td class="num" data-v="{r["pages"] or 0}">{r["pages"] or "not counted"}</td></tr>')
    B.append('</tbody></table></main>')
    script = r"""
(function () {
  var t = document.getElementById('books'); if (!t) return;
  var ths = t.querySelectorAll('th');
  Array.prototype.forEach.call(ths, function (th, col) {
    var b = document.createElement('button'); b.type = 'button'; b.textContent = th.textContent; th.textContent = ''; th.appendChild(b);
    b.addEventListener('click', function () {
      var desc = th.getAttribute('aria-sort') !== 'descending';
      Array.prototype.forEach.call(ths, function (h) { h.removeAttribute('aria-sort'); });
      th.setAttribute('aria-sort', desc ? 'descending' : 'ascending');
      var body = t.tBodies[0], rs = Array.prototype.slice.call(body.rows);
      rs.sort(function (a, b) {
        var x = a.cells[col] && a.cells[col].getAttribute('data-v'), y = b.cells[col] && b.cells[col].getAttribute('data-v');
        if (x === null) return 1; if (y === null) return -1;
        var nx = parseFloat(x), ny = parseFloat(y), c = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
        return desc ? -c : c;
      });
      rs.forEach(function (r) { body.appendChild(r); });
    });
  });
})();"""
    out = os.path.join(Bdir, 'summary.html')
    open(out, 'w', encoding='utf-8').write(page(f'Batch {label}', '\n'.join(B), script))
    return out

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == '--summary':
        for d in a[1:]: print(f'summary: {summary_html(d)}')
    else:
        for d in a: print(f'dashboard: {review_html(d)}')
