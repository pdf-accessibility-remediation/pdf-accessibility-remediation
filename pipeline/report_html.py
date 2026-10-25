"""report_html.py: the offline dashboards beside review.md and summary.md. No model, nothing sent, no internet.

    python3 report_html.py RUN_DIR [RUN_DIR ...]     review.html for each finished run (report.py runs this itself)
    python3 report_html.py --summary BATCH_DIR       summary.html for a batch, plus review.html for each of its books

Every number comes from the run's `glance` in record.json (lib/glance.py), the same numbers as review.md's
"Overview"; a run made before glance existed gets it computed from its record.json and review.md. Each page is one
file: the CSS is inlined (colours from review/palette.css, copied from the review page's), there are no external scripts,
and it reads in full without JavaScript. JavaScript only adds the issue filter, the keyboard page strip and sorting.
The pages quote book text as review.md does, so they stay under runs/ and are never committed.
"""
import sys, os, re, json, csv, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import glance as G  # noqa: E402
from lib import sections as S  # noqa: E402

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
th, td { border: 1px solid var(--line); padding: 4px 8px; text-align: left; vertical-align: top; overflow-wrap: normal; word-break: normal; }
th { white-space: nowrap; }
.tw { overflow-x: auto; max-width: 100%; margin: 0 0 8px; } .tw > table { margin: 0; } .tw:focus { outline: 3px solid var(--accent); outline-offset: 2px; }
a.pg { white-space: nowrap; }
th { background: var(--bg); } td.num, th.num { text-align: right; white-space: nowrap; }
.chart { display: grid; grid-template-columns: minmax(120px, max-content) 1fr; gap: 4px 10px; align-items: center; margin: 6px 0 8px; font-size: 13px; }
.bar { height: 12px; background: var(--line); border-radius: 3px; overflow: hidden; } .bar i { display: block; height: 100%; background: var(--accent); }
.bar i.after { background: var(--change); }
.tag { display: inline-block; font-size: 12px; font-weight: 600; padding: 0 6px; border-radius: 4px; border: 1px solid var(--line); white-space: nowrap; }
.tag { color: var(--ink); background: var(--line); border-color: transparent; }   /* sources: soft grey pills, like the item badges */
.tag.safety { color: var(--reject); background: transparent; border-color: var(--reject); }   /* a failed safety check: the strip's red */
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--change); margin-right: 6px; vertical-align: middle; }
li.need { list-style: none; position: relative; } li.need > .dot { position: absolute; left: -1.05em; top: .5em; margin: 0; }   /* the dot is the bullet */
.key { font-size: 13px; color: var(--ink); margin: 4px 0 10px; }
.tag.ok { color: var(--ok); background: transparent; border-color: var(--ok); }
.strip { display: flex; flex-wrap: wrap; gap: 2px; padding: 6px; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; }
.strip:focus { outline: 3px solid var(--accent); outline-offset: 2px; }
.cell { width: 9px; height: 18px; background: var(--line); border-radius: 2px; }
.cell.person { background: var(--change); }
.cell.safety { background: repeating-linear-gradient(45deg, var(--reject) 0 3px, var(--panel) 3px 5px); }
.cell.active { outline: 2px dotted var(--ink); outline-offset: 1px; }
.cell.pinned { outline: 2px solid var(--accent); outline-offset: 2px; }
#stripinfo { min-height: 1.5em; margin: 6px 0 2px; font-size: 14px; } #strippreview { min-height: 1.5em; margin: 0 0 6px; font-size: 14px; }
.sw { display: inline-block; width: 9px; height: 18px; background: var(--line); border-radius: 2px; vertical-align: middle; margin: 0 10px 0 4px; }
.sw.pinned { outline: 2px solid var(--accent); outline-offset: 2px; } .sw.active { outline: 2px dotted var(--ink); outline-offset: 1px; }
.legend .sw { margin: 0 6px 0 16px; }
.legend { font-size: 13px; color: var(--muted); } .legend .cell { display: inline-block; vertical-align: middle; margin: 0 4px 0 10px; }
details.sec { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; margin: 0 0 8px; padding: 0 12px; }
details.sec > summary { cursor: pointer; padding: 8px 0; } details.sec > summary h3 { display: inline; font-size: 15px; margin: 0; }
details.sec > summary .count { display: inline-block; margin-left: 8px; padding: 0 8px; border-radius: 999px; background: var(--line); color: var(--ink); font-size: 12px; font-weight: 600; }
details.sec > summary .count.need { background: transparent; border: 1.5px solid var(--change); color: var(--change); }
details.sec[open] > summary { border-bottom: 1px solid var(--line); margin-bottom: 8px; }
code { font-size: 13px; background: var(--bg); padding: 0 3px; border-radius: 3px; }
.filter { margin: 6px 0; } select, button { font: inherit; color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 3px 8px; }
th button { border: 0; background: none; padding: 0; font-weight: 700; cursor: pointer; text-align: left; }
.note { color: var(--muted); font-size: 13px; }
details.fold { margin-top: 6px; font-size: 13px; } details.fold summary { cursor: pointer; color: var(--accent); }
details.fold.plain summary { color: var(--muted); }          /* all five passed: a plain toggle, still with its arrow */
ul.checks { list-style: none; padding-left: 4px; margin: 4px 0 0; }
h2.inline { display: inline; font-size: 15px; border: 0; margin: 0; padding: 0; }
.nw { white-space: nowrap; }
.secsearch { margin: 4px 0 8px; } .secsearch input { width: min(320px, 100%); }
span.fulltext { display: block; margin: 4px 0 2px; } span.fulltext[hidden] { display: none; }
span.fulltext .ftp { display: block; margin: 4px 0; padding-left: 10px; border-left: 2px solid var(--line); }
button.ftb { font: inherit; font-size: 13px; color: var(--accent); background: none; border: 0; padding: 0 4px; margin-left: 4px; cursor: pointer; white-space: nowrap;
             display: inline-block; min-height: 24px; min-width: 24px; line-height: 24px; vertical-align: baseline; }   /* WCAG 2.5.8 target size */
button.ftb .tri::before { content: "▸"; display: inline-block; width: 1em; }      /* closed */
button.ftb[aria-expanded="true"] .tri::before { content: "▾"; }                    /* open */
.hit { outline: 3px solid var(--accent); outline-offset: 1px; }
@media (max-width: 640px) { main { padding: 10px; } .chart { grid-template-columns: 1fr; } }
"""
E = html.escape

PAGE_REF = re.compile(r'(?<![\w/])PDF (\d+)(?!\d|\.\d)(?:–(\d+))?( \(printed [^)<]*\))?')   # whole word; not "veraPDF 1.30.3" or "PDF 2.0"
def _pg_link(m):
    a, b, printed = m.group(1), m.group(2), m.group(3) or ''
    if not b: return f'<a class="pg" href="#pg-{a}">{m.group(0)}</a>'
    return (f'<a class="pg" href="#pg-{a}">PDF {a}</a>–<a class="pg" href="#pg-{b}" aria-label="PDF {b}">{b}</a>{printed}')   # a range: each end
def page_links(h):
    """Every page reference ("PDF 152 (printed 143)", "PDF 381–386") in HTML text becomes a link to that page's cell in the
    page strip; in a range, each end links to its own page. Text already inside a link is left alone."""
    return ''.join(seg if seg.startswith('<a ') else PAGE_REF.sub(_pg_link, seg) for seg in re.split(r'(<a [^>]*>.*?</a>)', h))
def page_refs(text):
    """Every page a text names, a range counting all its pages (for "Mentioned in")."""
    out = set()
    for m in PAGE_REF.finditer(text):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        out.update(range(a, b + 1) if 0 <= b - a <= 2000 else (a, b))
    return out

def inline(t, links=True):
    """One line of review.md text as HTML: escaped first, then `code`, **bold**, [links](relative, #anchor or http) and
    page references (links to the page strip)."""
    t = E(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[([^\]]+)\]\(((?:#|https?://|[\w./-]+)[^)\s]*)\)', lambda m: f'<a href="{E(m.group(2))}">{m.group(1)}</a>', t)
    return page_links(t) if links else t

NOWRAP = re.compile(r'^(?:\*\*CHECK\*\*|CHECK|OK|FAILED.*|—|not counted|not run|page: not on this tag'
                    r'|[\d.,%$ –+/-]+'                                          # numbers, counts, WCAG criteria ("1.3.1, 4.1.2")
                    r'|(?:ISO 14289-1 )?\d+(?:\.\d+)*-\d+(?: \(unclassified\))?'   # veraPDF rule IDs ("7.2-34")
                    r'|PDF \d+(?:–\d+)?(?: \(printed [^)]*\))?)$')                  # one page reference
def td(c):
    """A table cell: status, number, rule-ID and single-page cells don't wrap; text cells wrap between words only."""
    return f'<td{" class=\"nw\"" if NOWRAP.match(c.strip()) else ""}>{inline(c)}</td>'

def full_toggle(it):
    """The whole text of an item's excerpts (record.json `sections` → `full`), as a block below the line. Without JavaScript
    it is simply shown; with it, it starts hidden and an inline "show full text" button (aria-expanded, aria-controls) opens it.
    Spans, not divs or paragraphs, so the block is valid inside a paragraph, list item or table cell."""
    fs = [f for _, f in it.get('full') or []]
    if not fs or not it.get('id'): return ''
    return (f'<span class="fulltext" id="{E(it["id"])}-full">' + ''.join(f'<span class="ftp">{inline(f, False)}</span>' for f in fs) + '</span>')

def item_inline(it, skip=0):
    """An item's text as HTML (WCAG only), its first `skip` characters (a list marker) left out; parts marked "nolink"
    keep their page references as plain text (they name another book's pages)."""
    out = []
    for t, links in S.parts_wcag(it):
        if skip: t, skip = t[skip:], max(0, skip - len(t))
        out.append(inline(t, links))
    return ''.join(out)

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
            out.append('<div class="tw"><table>')
            for k, r in enumerate(body):
                cells = [c.strip() for c in r.strip().strip('|').split(' | ')]
                if head and k == 0: out.append('<tr>' + ''.join(f'<th scope="col">{inline(c)}</th>' for c in cells) + '</tr>')
                else: out.append(f'<tr{nid(r)}>' + ''.join(td(c) for c in cells) + '</tr>')
            out.append('</table></div>'); continue
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
        with pikepdf.open(os.path.join(R, rec['document']['output'])) as p: labels = {i + 1: str(pg.label) for i, pg in enumerate(p.pages)}
    except Exception: labels = {}
    return G.with_spread_labels(labels, rec.get('intake'))     # the same spread labels as report.py

def han_pages(R):
    p = os.path.join(R, 'han_review.csv')
    if not os.path.exists(p): return []
    with open(p, encoding='utf-8') as f: return [int(r['pdf_page']) for r in csv.DictReader(f) if str(r.get('pdf_page') or '').isdigit()]

def glance_of(R, rec=None, labels=None):
    """The run's glance: from record.json, or computed from record.json and review.md for a run made before it existed."""
    rec = rec or json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
    if rec.get('glance', {}).get('schema') == G.SCHEMA: return rec['glance']
    if rec.get('sections_version') == S.VERSION:
        return G.glance(rec, None, labels if labels is not None else labels_of(R, rec), han_pages(R), sections=rec['sections'])
    md = open(os.path.join(R, 'review.md'), encoding='utf-8').read()
    return G.glance(rec, md, labels if labels is not None else labels_of(R, rec), han_pages(R))

def need_items(secs):
    """{section anchor: [item ids]} of what needs a person, counted exactly as the Overview counts it (lib/glance.py):
    CHECK rows (not "Nothing deferred by the executor", which only points at that list), every deferral by the AI, and the
    executor's deferrals by kind and page (all Han-only runs: 1; a kind on several pages: its first item on each page; a
    kind with no page: its first item). PDF/UA-only deferrals are not counted."""
    out = {}
    for x in secs:
        k, ids = x.get('key'), []
        if k == 'automated-checks':
            for it in x['items']:
                cells = it['text'][2:].rstrip(' |').split(' | ', 2) if it['kind'] == 'row' else []
                if len(cells) == 3 and cells[1] != 'OK' and cells[0] not in G.POINTER_ROWS: ids.append(it['id'])
        elif k == 'deferred-by-the-ai':
            ids = [it['id'] for it in x['items'] if (it.get('key') or '').startswith('ai:')]
        elif k == 'deferred-by-the-executor':
            exe = [it for it in x['items'] if (it.get('key') or '').startswith('exec:') and it.get('scope') != 'pdfua']
            paged = {it['key'] for it in exe if it.get('pages')}; seen = set()
            for it in exe:
                if it['key'] == 'exec:han': ids.append(it['id']); continue
                marks = [(it['key'], q) for q in it.get('pages') or []] if it['key'] in paged else [(it['key'], None)]
                new = [m for m in marks if m not in seen]
                if new: ids.append(it['id']); seen.update(new)
        if ids: out[x['anchor']] = ids
    return out

def items_html(items, need=()):
    """A section's items (record.json `sections`) as HTML, WCAG only: an item marked "pdfua" is left out, and so is each
    PDF/UA-only part of a line. Every item keeps its id, so a link can land on it; an item in `need` gets a "Needs a
    person" tag. Returns (html, [(id, text)])."""
    out, listed, i = [], [], 0
    DOT = '<span class="dot" aria-hidden="true"></span><span class="vh">Needs a person: </span>'
    items = [it for it in items if it.get('scope') != 'pdfua']
    def cells(t): return [c.strip() for c in t.strip().strip('|').split(' | ')]
    def idattr(it):
        if not it.get('id'): return ''
        listed.append((it['id'], ''.join(t for t, links in S.parts_wcag(it) if links)))   # no-link parts: not this book's pages
        return f' id="{E(it["id"])}"' + (' data-entry="no"' if it.get('entry') is False else '')   # a note: filtered, but not counted
    while i < len(items):
        it = items[i]; k = it['kind']
        if k in ('head', 'row', 'sep'):
            out.append('<div class="tw"><table>')
            while i < len(items) and items[i]['kind'] in ('head', 'row', 'sep'):
                x = items[i]; i += 1
                if x['kind'] == 'sep': continue
                if x['kind'] == 'head': out.append('<tr>' + ''.join(f'<th scope="col">{inline(c)}</th>' for c in cells(S.text_wcag(x))) + '</tr>')
                else:
                    raw = cells(S.text_wcag(x)); cs = [td(c) for c in raw]
                    if x.get('full'):                       # the toggle goes into the cell that holds the first excerpt
                        k_ = next((j for j, c in enumerate(raw) if any(e in c for e, _ in x['full'])), len(cs) - 1)
                        cs[k_] = cs[k_][:-5] + full_toggle(x) + '</td>'
                    if x.get('id') in need: k_ = cs[0].index('>') + 1; cs[0] = cs[0][:k_] + DOT + cs[0][k_:]
                    out.append(f'<tr{idattr(x)}>' + ''.join(cs) + '</tr>')
            out.append('</table></div>'); continue
        if k == 'li':
            out.append('<ul>')
            while i < len(items) and items[i]['kind'] == 'li':
                x = items[i]; i += 1; nd = x.get('id') in need
                out.append(f'<li{idattr(x)}{" class=\"need\"" if nd else ""}>{DOT if nd else ""}{item_inline(x, 2)}{full_toggle(x)}</li>')
            out.append('</ul>'); continue
        if k == 'quote': out.append(f'<blockquote{idattr(it)}>{item_inline(it, 2)}{full_toggle(it)}</blockquote>')
        elif k == 'p' and S.text_wcag(it).strip(): out.append(f'<p{idattr(it)}>{item_inline(it)}{full_toggle(it)}</p>')
        i += 1
    return '\n'.join(out), listed

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

SEARCH_MIN = 20                       # a section with this many items or more gets a search box
KIND = {'safety': 'Safety', 'ship': 'Ship condition', 'check': 'Automated check', 'executor': 'Deferred by the executor', 'ai': 'Deferred by the AI'}

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
    if rec.get('sections_version') == S.VERSION:         # drawn from record.json `sections`: the same data as review.md
        secs = rec['sections']; blocks = []; need = need_items(secs)
        start = next((k for k, x in enumerate(secs) if x.get('key') == 'automated-checks'), len(secs))
        for x in secs[start:]:
            if x['level'] == 3 and not any(it['kind'] != 'blank' and it.get('scope') != 'pdfua' for it in x['items']): continue   # only PDF/UA-only lines
            b = {'title': x['title'], 'h2': x['level'] == 2, 'anchor': x['anchor'], 'lines': [it['text'] for it in x['items']]}
            b['need'] = len(need.get(x['anchor'], [])); b['html'], b['items'] = items_html(x['items'], set(need.get(x['anchor'], [])))
            b['entries'] = sum(it.get('n_entries', 1) for it in x['items']  # a grouped line counts the entries it holds
                               if it['kind'] in ('li', 'row') and it.get('id') and it.get('scope') != 'pdfua' and it.get('entry') is not False)
            blocks.append(b)
        title = next((x for x in secs if x.get('key') == 'title'), {'items': []})
        run_details = [S.text_wcag(it) for it in title['items'] if it['kind'] != 'blank' and not it['text'].startswith('Automated checks are evidence')]
    else:                                                # a run made before `sections`: read review.md
        start = next((k for k, l in enumerate(lines) if l == '## Automated checks'), len(lines))
        blocks, cur = [], None
        for l in lines[start:]:
            m3 = re.match(r'^### (\d+)\. (.+?)\s*$', l)
            if l.startswith('## ') or m3:
                cur = {'title': l[3:].strip() if not m3 else f'{m3.group(1)}. {m3.group(2)}', 'h2': not m3, 'lines': []}; blocks.append(cur)
            elif cur is not None: cur['lines'].append(l)
        for b in blocks:
            b['anchor'] = G.slug(b['title']); b['html'], b['items'] = md_html(wcag_only(b['lines']), b['anchor'])
        head = lines[1:next((k for k, l in enumerate(lines) if l in ('## Overview', '## At a glance', '## Automated checks')), len(lines))]
        run_details = [l for l in head if l.strip() and not l.startswith('Automated checks are evidence')]
    by_anchor = {b['anchor']: b for b in blocks}
    def item_for(x):
        if x.get('item'): return x['item']               # from record.json `sections`: the id of its own line
        b = by_anchor.get(x['where']['anchor']); f = x.get('find')
        if not b or not f: return None
        f = _plain(f)
        return next((iid for iid, raw in b['items'] if f in _plain(raw)), None)

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
    safety_fold = (f'<details class="fold{"" if saf_bad else " plain"}"{" open" if saf_bad else ""}><summary>The {len(saf)} safety checks</summary><ul class="checks">'
                   + ''.join(f'<li>{"<strong>FAILED ✘</strong>" if not x["ok"] else "OK ✔"} {E(x["what"])}</li>' for x in saf) + '</ul></details>') if saf else ''
    cards = [('Safety', 'good' if g['safety_ok'] else 'bad', 'OK' if g['safety_ok'] else ('Failed' if saf else 'Not checked'),
              f'{len(saf) - len(saf_bad)} of {len(saf)} checks OK', safety_fold),
             ('Needs a person', 'warn' if np_['total'] else 'good', str(np_['total']),
              f'{np_["ai_deferrals"]} deferred by the AI · {np_["executor_deferrals"]} deferred by the executor · {np_["check_rows"]} automated check{"" if np_["check_rows"] == 1 else "s"}', ''),
             ('AI decisions', 'good' if g['ship'][0]['ok'] else 'warn', f'{ad["count"]:,}',
              (f'approved by {ad["reviewed"]["reviewer"]} on {ad["reviewed"]["date"]}' if ad.get('reviewed') and g['ship'][0]['ok']
               else 'reviewed, not signed off' if ad.get('reviewed') else 'Not reviewed by a person'), ''),
             ('veraPDF (WCAG rules)', ('good' if vg.get('after_rules') == 0 else 'warn') if vg.get('ran_after') else 'warn',
              (f'{vg.get("before_rules", "–")} → {vg["after_rules"]}' if vg.get('ran_after') else 'Not run'),
              (f'{vg.get("before_checks", 0):,} → {vg["after_checks"]:,} failed checks · {len(vg.get("newly_failing") or [])} newly failing' if vg.get('ran_after') else (vg.get('not_run') or '')), '')]
    def lab(cls, big):
        t = {"good": "OK", "muted": "OK", "bad": "Failed", "warn": "Needs attention"}[cls]
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
            B.append(f'<div class="filter" hidden id="filterbox"><label for="kind">Show </label><select id="kind"><option value="">All sources ({len(iss)})</option>'
                     + ''.join(f'<option value="{k}">{E(KIND[k])} ({sum(1 for x in iss if x["kind"] == k)})</option>' for k in kinds)
                     + '</select> <span id="shown" aria-live="polite"></span></div>')
        B.append('<div class="tw"><table id="issues"><tr><th scope="col">Issue</th><th scope="col">Source</th><th scope="col">Pages</th><th scope="col">Details</th></tr>')
        for x in iss:
            w = x['where']; iid = item_for(x)
            hb = next((b for b in blocks if iid and any(i_ == iid for i_, _ in b['items'])), None) or by_anchor.get(w['anchor'])   # where it lands
            hn = re.match(r'(\d+)\. ', hb['title']) if hb else None
            link = (f'<a href="#{E(hb["anchor"] if hb else w["anchor"])}"' + (f' data-item="{E(iid)}"' if iid else '')
                    + f'>{"§" + hn.group(1) + " " if hn else ""}Details<span class="vh">: {E(x["text"])}'
                    + (f' (in {E(hb["title"])})' if hb and not hn else '') + '</span></a>')
            B.append(f'<tr data-kind="{x["kind"]}"><td>{E(x["text"])}</td><td><span class="tag {x["kind"]}">{E(KIND[x["kind"]])}</span></td>'
                     f'<td>{page_links(E(x["pages_text"])) or "see the details"}</td><td class="nw">{link}</td></tr>')
        B.append('</table></div>')
    else: B.append('<p>Nothing needs a person.</p>')
    B.append('</section>')
    # ---- page strip (one Tab stop with JavaScript), and the plain list that works without it; descriptions in full
    n_pages = int(g.get('pages') or 0); lv, notes = g['page_level'], g['page_notes']
    mentions = {}                        # page → the sections that name it, with the first such item in each
    for b in blocks:
        for iid, text in b['items']:
            for p in page_refs(text):
                if not any(x[1] == b['anchor'] for x in mentions.get(p, [])): mentions.setdefault(p, []).append((iid, b['anchor'], b['title']))
    if n_pages:
        B.append('<section aria-labelledby="pg-h"><h2 id="pg-h">Pages</h2><p class="legend">Each cell is one page, in order.'
                 '<span class="cell safety"></span>safety check failed<span class="cell person"></span>needs a person<span class="cell"></span>nothing listed'
                 '<span class="sw pinned"></span>pinned<span class="sw active"></span>preview</p>')
        B.append('<div class="strip" id="strip" aria-hidden="true">' + ''.join(
            f'<span class="cell {lv.get(str(p), "")}" id="pg-{p}" data-p="{p}" data-l="{E(pgl(p))}" data-lv="{lv.get(str(p), "")}"'
            f' data-n="{E(" · ".join(notes.get(str(p), [])))}" title="{E(pgl(p))}"></span>' for p in range(1, n_pages + 1)) + '</div>'
            '<div id="stripinfo" aria-live="polite"></div><div id="strippreview" aria-live="polite"></div><div id="stripstatus" class="vh" role="status"></div>'
            '<script type="application/json" id="mentions">' + json.dumps({p: [[i, t] for i, _, t in v] for p, v in mentions.items()}).replace('</', '<\\/') + '</script>')
        listed = sorted(lv, key=int)
        B.append(f'<details id="pagelist"><summary>Pages with something listed ({len(listed)})</summary><ul>'
                 + ''.join(f'<li><a class="pg" href="#pg-{p}">{E(pgl(p))}</a>: {"safety check failed: " if lv[p] == "safety" else ""}{E("; ".join(notes.get(p, [])))}</li>' for p in listed) + '</ul></details></section>')
    # ---- review.md's sections, collapsible, in the same order (WCAG only)
    B.append('<section aria-labelledby="secs-h"><h2 id="secs-h">Details</h2>'
             '<p class="key"><span class="dot" aria-hidden="true"></span>needs a person</p>')
    for b in blocks:
        if b['h2'] and b['title'] == 'For a person to check':
            if any(x.strip() for x in b['lines']): B.append('<h2>For a person to check</h2>')
            continue
        n_items = b['entries'] if 'entries' in b else len(re.findall(r'<(?:li|tr) id=', b['html']))   # real entries: rows and list items, not notes
        cnt = f'{n_items} item{"" if n_items == 1 else "s"}' if n_items else ''
        nn = b.get('need') or 0                                       # the Overview's definition, see need_items()
        needb = (f'<span class="vh"> · </span><span class="count need"><span aria-hidden="true">{nn}</span>'
                 f'<span class="vh">{nn} need{"s" if nn == 1 else ""} a person</span></span>') if nn else ''
        opened = ''                                                   # every section starts closed
        search = (f'<div class="secsearch" hidden><label for="q-{E(b["anchor"])}">Search this section</label> '
                  f'<input type="search" id="q-{E(b["anchor"])}"> <span class="found note" aria-live="polite"></span></div>') if n_items >= SEARCH_MIN else ''
        shown_t = re.sub(r' \((\d+)\)$', '', b['title']) if re.search(r' \((\d+)\)$', b['title']) and int(re.search(r'\((\d+)\)$', b['title']).group(1)) == n_items else b['title']
        B.append(f'<details class="sec" id="{E(b["anchor"])}"{opened}><summary><h3>{E(shown_t)}</h3>' + (f'<span class="count">{E(cnt)}</span>' if cnt else '') + needb + '</summary>'
                 + search + b['html'] + '</details>')
    B.append('</section></main>')
    script = r"""
(function () {
  // one highlight at a time: a Details or page link marks where it landed; the next click elsewhere clears it
  function clearHit() { var h = document.querySelector('.hit'); if (h) h.classList.remove('hit'); }
  function land(el) {
    clearHit();
    for (var d = el.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
    el.setAttribute('tabindex', '-1'); el.classList.add('hit'); el.scrollIntoView({block: 'center'}); el.focus({preventScroll: true});
  }
  // a table's box scrolls sideways on a narrow screen; only then is it a Tab stop (and named), so it can be scrolled by keyboard
  function tableName(w) {               // the box's name: its section's heading (numbered when the section has several tables)
    var sec = w.closest('details.sec') || w.closest('section'), hd = sec && sec.querySelector('h2, h3');
    var name = (hd ? hd.textContent.trim() : 'Table'), all = sec ? sec.querySelectorAll('.tw') : [w];
    return (all.length > 1 ? name + ', table ' + (Array.prototype.indexOf.call(all, w) + 1) : name) + ' (scrolls sideways)';
  }
  function fitTables() {
    Array.prototype.forEach.call(document.querySelectorAll('.tw'), function (w) {
      if (w.scrollWidth > w.clientWidth + 1) { w.tabIndex = 0; w.setAttribute('role', 'region'); w.setAttribute('aria-label', tableName(w)); }
      else { w.removeAttribute('tabindex'); w.removeAttribute('role'); w.removeAttribute('aria-label'); }
    });
  }
  fitTables(); window.addEventListener('resize', fitTables); document.addEventListener('toggle', fitTables, true);
  var t = document.getElementById('issues'), box = document.getElementById('filterbox');
  if (t && box) {
    box.hidden = false; var sel = document.getElementById('kind'), shown = document.getElementById('shown');
    sel.addEventListener('change', function () {
      var n = 0; Array.prototype.forEach.call(t.querySelectorAll('tr[data-kind]'), function (r) {
        var on = !sel.value || r.getAttribute('data-kind') === sel.value; r.hidden = !on; if (on) n++; });
      shown.textContent = n + ' shown';
    });
  }
  // the page strip: one Tab stop. Hover and the arrow keys preview a page; a click or Enter pins it (its details stay, and
  // while pinned, a preview shows on its own line below); clicking the pinned cell, clicking outside the strip, or Escape unpins
  var s = document.getElementById('strip'), info = document.getElementById('stripinfo'), pre = document.getElementById('strippreview'),
      ann = document.getElementById('stripstatus'), mj = document.getElementById('mentions'), mentions = mj ? JSON.parse(mj.textContent) : {};
  var cells = s ? s.querySelectorAll('.cell') : [], cur = 0, pinned = -1;
  function label(i) { return cells[i].getAttribute('data-l'); }
  function fill(el, i, lead) {          // a page's details: what needs a person, and each section that names it, linked to the item
    el.textContent = '';
    if (lead) {                         // a swatch like the cell's outline; the word stays for screen readers
      var sw = document.createElement('span'); sw.className = 'sw ' + (lead === 'Pinned' ? 'pinned' : 'active'); sw.setAttribute('aria-hidden', 'true'); el.appendChild(sw);
      var v = document.createElement('span'); v.className = 'vh'; v.textContent = lead + ' '; el.appendChild(v);
    }
    var c = cells[i], n = c.getAttribute('data-n'), m = mentions[c.getAttribute('data-p')] || [];
    var base = label(i) + ': ' + (n || 'nothing needs a person'), stop = /[.!?]$/.test(base) ? '' : '.';   // no doubled full stop
    el.appendChild(document.createTextNode(base + stop + (m.length ? ' Mentioned in: ' : '')));
    m.forEach(function (x, k) {
      var a = document.createElement('a'); a.href = '#' + x[0]; a.textContent = x[1]; el.appendChild(a);
      el.appendChild(document.createTextNode(k < m.length - 1 ? ' · ' : '.'));
    });
  }
  function setActive(i) {
    cells[cur].classList.remove('active'); cells[cur].removeAttribute('aria-selected'); cur = i;
    cells[i].classList.add('active'); cells[i].setAttribute('aria-selected', 'true'); s.setAttribute('aria-activedescendant', cells[i].id);
  }
  function preview(i) {
    setActive(i);
    if (pinned < 0) fill(info, i, '');
    else if (i !== pinned) fill(pre, i, 'Preview');
    else pre.textContent = '';
  }
  function optLabel(i) {
    var lv = cells[i].getAttribute('data-lv');
    cells[i].setAttribute('aria-label', label(i) + ': ' + (lv === 'safety' ? 'safety check failed' : lv === 'person' ? 'needs a person' : 'nothing listed')
                          + (i === pinned ? ', pinned' : ''));
  }
  function pin(i) {
    var was = pinned; pinned = i;
    if (was >= 0) { cells[was].classList.remove('pinned'); optLabel(was); }
    cells[i].classList.add('pinned'); optLabel(i); setActive(i); fill(info, i, 'Pinned'); pre.textContent = '';
    ann.textContent = label(i) + ' pinned';
  }
  function unpin() {
    if (pinned < 0) return;
    var i = pinned; pinned = -1; cells[i].classList.remove('pinned'); optLabel(i); pre.textContent = ''; fill(info, cur, '');
    ann.textContent = label(i) + ' unpinned';
  }
  function goPage(c) {                  // from a page link: that page, pinned, with everything listed for it
    pin(Array.prototype.indexOf.call(cells, c)); s.scrollIntoView({block: 'center'}); s.focus({preventScroll: true});
  }
  if (s) {
    s.removeAttribute('aria-hidden'); s.setAttribute('role', 'listbox'); s.setAttribute('tabindex', '0');
    s.setAttribute('aria-label', 'Pages, one per cell: arrow keys to move, Enter to pin a page, Escape to unpin');
    Array.prototype.forEach.call(cells, function (c, i) {
      c.setAttribute('role', 'option'); c.removeAttribute('title'); optLabel(i);
      c.addEventListener('mouseenter', function () { preview(i); });
      c.addEventListener('click', function () { if (pinned === i) unpin(); else pin(i); s.focus({preventScroll: true}); });
    });
    s.addEventListener('mouseleave', function () { if (pinned >= 0) pre.textContent = ''; });
    s.addEventListener('focus', function () { preview(cur); });
    s.addEventListener('keydown', function (e) {
      var k = e.key, i = cur, row = Math.max(1, Math.round(s.clientWidth / 11));
      if (k === 'Enter' || k === ' ') { e.preventDefault(); if (pinned === cur) unpin(); else pin(cur); return; }
      if (k === 'Escape') { if (pinned >= 0) { e.preventDefault(); unpin(); } return; }
      if (k === 'ArrowRight') i++; else if (k === 'ArrowLeft') i--; else if (k === 'ArrowDown') i += row; else if (k === 'ArrowUp') i -= row;
      else if (k === 'Home') i = 0; else if (k === 'End') i = cells.length - 1; else return;
      e.preventDefault(); preview(Math.max(0, Math.min(cells.length - 1, i)));
    });
  }
  document.addEventListener('click', function (e) {
    var inStrip = s && (s.contains(e.target) || info.contains(e.target) || pre.contains(e.target));
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    var el = a && document.getElementById(a.getAttribute('data-item') || a.getAttribute('href').slice(1));
    if (s && !inStrip && !(el && el.classList.contains('cell'))) unpin();     // a click outside the strip unpins
    if (!el) { if (!(s && s.contains(e.target))) clearHit(); return; }
    e.preventDefault(); if (el.classList.contains('cell')) { clearHit(); goPage(el); } else land(el);
    history.replaceState(null, '', '#' + el.id);
  });
  if (location.hash) {
    var h = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (h) { if (h.classList.contains('cell')) goPage(h); else land(h); }
  }
})();
(function () {
  // "show full text": the block starts hidden; an inline button at the end of the excerpt opens and closes it
  function setOpen(btn, open) {
    var blk = document.getElementById(btn.getAttribute('aria-controls'));
    blk.hidden = !open; btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.querySelector('.lab').textContent = open ? 'hide full text' : 'show full text';
  }
  Array.prototype.forEach.call(document.querySelectorAll('span.fulltext'), function (blk) {
    var b = document.createElement('button'); b.type = 'button'; b.className = 'ftb'; b.setAttribute('aria-controls', blk.id);
    b.innerHTML = '<span class="tri" aria-hidden="true"></span><span class="lab"></span>';
    blk.parentNode.insertBefore(b, blk); setOpen(b, false);
    b.addEventListener('click', function () { setOpen(b, b.getAttribute('aria-expanded') !== 'true'); });
  });
  // search inside a long section: rows and list items that do not contain the words are hidden; the count is read out.
  // An item that matches only in its hidden full text shows that text (clearing the search leaves it open)
  function shownText(it) {
    var c = it.cloneNode(true); Array.prototype.forEach.call(c.querySelectorAll('span.fulltext, button.ftb'), function (x) { x.remove(); });
    return c.textContent.toLowerCase();
  }
  Array.prototype.forEach.call(document.querySelectorAll('.secsearch'), function (box) {
    box.hidden = false;
    var q = box.querySelector('input'), out = box.querySelector('.found'), items = box.parentNode.querySelectorAll('li[id], tr[id]');
    var total = box.parentNode.querySelectorAll('li[id]:not([data-entry="no"]), tr[id]:not([data-entry="no"])').length;   // as the badge counts
    q.addEventListener('input', function () {
      var v = q.value.trim().toLowerCase(), n = 0, notes = 0;
      Array.prototype.forEach.call(items, function (it) {
        var on = !v || it.textContent.toLowerCase().indexOf(v) >= 0; it.hidden = !on;
        if (on) { if (it.getAttribute('data-entry') === 'no') notes++; else n++; }
        if (v && on && shownText(it).indexOf(v) < 0)
          Array.prototype.forEach.call(it.querySelectorAll('button.ftb'), function (b) {
            var blk = document.getElementById(b.getAttribute('aria-controls'));
            if (blk && blk.textContent.toLowerCase().indexOf(v) >= 0) setOpen(b, true);
          });
      });
      out.textContent = v ? n + ' of ' + total + ' shown' + (notes ? ', and ' + notes + ' note' + (notes === 1 ? '' : 's') : '') : '';
    });
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
         '<div class="tw"><table id="books"><thead><tr>' + ''.join(f'<th scope="col"{" class=\"num\"" if n else ""} data-k="{k}"{" aria-sort=\"descending\"" if k == "needs" else ""}>{E(t)}</th>'
                                                  for t, k, n in (('Book', 'name', 0), ('Ready to ship?', 'ready', 0), ('Needs a person', 'needs', 1), ('AI decisions', 'ai', 1),
                                                                  ('Safety', 'safety', 0), ('veraPDF WCAG rules', 'va', 1), ('Cost', 'cost', 1), ('Pages', 'pages', 1))) + '</tr></thead><tbody>']
    for r in rows:
        if not r['done']:
            B.append(f'<tr><td>{E(r["name"])}</td><td colspan="7">{E(r["status"])}</td></tr>'); continue
        B.append(f'<tr><td data-v="{E(r["name"])}"><a href="{E(r["name"])}/review.html">{E(r["name"])}</a></td>'
                 f'<td data-v="{int(r["ready"])}"><span class="tag{" ok" if r["ready"] else ""}">{"Yes" if r["ready"] else "No"}</span>'
                 f'{"" if r["reviewed"] else " <span class=note>(not reviewed)</span>"}</td>'
                 f'<td class="num" data-v="{r["needs"]}">{r["needs"]} <span class="bar" style="display:inline-block;width:80px;vertical-align:middle" aria-hidden="true"><i style="width:{100 * r["needs"] / mx:.0f}%"></i></span>'
                 f'<br><span class="note">{r["np"]["ai_deferrals"]} AI · {r["np"]["executor_deferrals"]} executor · {r["np"]["check_rows"]} automated check{"" if r["np"]["check_rows"] == 1 else "s"}</span></td>'
                 f'<td class="num" data-v="{r["ai"]}">{r["ai"]:,}</td>'
                 f'<td data-v="{int(r["safety"])}"><span class="tag {"ok" if r["safety"] else "safety"}">{"OK" if r["safety"] else "Failed"}</span></td>'
                 f'<td class="num" data-v="{r["va"] if r["va"] is not None else -1}">' + (f'{r["vb"] if r["vb"] is not None else "–"} → {r["va"]}' if r['va'] is not None else 'not run')
                 + (f' <strong>({r["new"]} new)</strong>' if r['new'] else '') + '</td>'
                 f'<td class="num" data-v="{r["cost"] or 0}">' + (f'${r["cost"]:.3f}' if r['cost'] is not None else 'call did not finish') + '</td>'
                 f'<td class="num" data-v="{r["pages"] or 0}">{r["pages"] or "not counted"}</td></tr>')
    B.append('</tbody></table></div></main>')
    script = r"""
(function () {
  function fitTables() {               // the table's box scrolls sideways on a narrow screen: only then is it a Tab stop
    Array.prototype.forEach.call(document.querySelectorAll('.tw'), function (w) {
      if (w.scrollWidth > w.clientWidth + 1) { w.tabIndex = 0; w.setAttribute('role', 'region'); w.setAttribute('aria-label', 'Books (scrolls sideways)'); }
      else { w.removeAttribute('tabindex'); w.removeAttribute('role'); w.removeAttribute('aria-label'); }
    });
  }
  fitTables(); window.addEventListener('resize', fitTables);
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
