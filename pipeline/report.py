"""report.py: the last step. Folds a run's working files into what people keep.

    python report.py RUN_DIR AUDIT_DIR [--keep] [--pdf=NAME.pdf]

The remediated PDF is found by its apply log (<name>.pdf.log.json) in RUN_DIR; --pdf names it
when there could be more than one.

Reads the working files that audit.py, decide.py, apply.py and verify.py left behind and writes:

    review.md        for the human reviewer: what the AI decided, what to check, what was deferred
    record.json      everything vital in one machine-readable file (run, work order, apply and
                     verify results, Claude's raw reply). `apply.py` accepts it as a work order.
    han_review.csv   only when Han-only CJK runs need a ja/zh decision

Then it deletes the working files (request.json, response.json, reply.txt, run.json,
validation.json, workorder.json, the apply log, the verify JSON) and the AUDIT_DIR
(digest and figure crops, which are copies of book pages). --keep leaves them all in place.
It only runs after a complete run, so a failed run keeps its working files for debugging.
"""
import sys, os, csv, json, shutil, datetime

args = [a for a in sys.argv[1:] if not a.startswith('--')]
KEEP = '--keep' in sys.argv
R, A = args[0], args[1]
PDF = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--pdf=')), None)
if not PDF:
    found = sorted(f[:-len('.log.json')] for f in os.listdir(R) if f.lower().endswith('.pdf.log.json'))
    if len(found) != 1: sys.exit(f'expected one remediated PDF with an apply log in {R}, found {len(found)}: pass --pdf=NAME.pdf')
    PDF = found[0]
def load(name, base=R, default=None):
    p = os.path.join(base, name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default
run = load('run.json', default={}); wo = load('workorder.json', default={}); val = load('validation.json', default={'dropped': []})
log = load(PDF + '.log.json', default={}); ver = load(PDF + '.verify.json', default={})
digest = load('digest.json', base=A, default={})
reply = open(os.path.join(R, 'reply.txt'), encoding='utf-8').read() if os.path.exists(os.path.join(R, 'reply.txt')) else None
timing = load('timing.json', default=None)
attempts = load('attempts.json', default=[])          # earlier paid calls in this folder whose reply couldn't be used
cost_this = (run.get('usage') or {}).get('cost_usd') or 0
cost_earlier = round(sum(a.get('cost_usd') or 0 for a in attempts), 6)
for need, name in ((wo, 'workorder.json'), (log, PDF + '.log.json'), (ver, PDF + '.verify.json')):
    if not need: sys.exit(f'{name} missing in {R}: run the whole pipeline first (nothing was deleted)')

figs = {f['obj']: f for f in digest.get('figures', [])}
elems = {e['obj']: e for e in digest.get('elements', []) + digest.get('headings', []) + digest.get('heading_candidates', [])}
lists_ = {x['obj']: x for x in digest.get('lists', [])}; tables_ = {x['obj']: x for x in digest.get('tables', [])}
src = digest.get('source', run.get('source', {}))
han = log.get('han_only', [])

# ------------------------------------------------------------------ record.json
record = {
    'schema': 'record/0.1', 'written': datetime.datetime.now().isoformat(timespec='seconds'),
    'document': {'file': src.get('file'), 'output': PDF, 'sha256': src.get('sha256'), 'pages': src.get('pages'),
                 'before': digest.get('document')},
    'run': run, 'workorder': wo, 'validation_dropped': val.get('dropped', []),
    'apply': {'applied': log.get('applied'), 'rejected': log.get('rejected'), 'failed': log.get('failed'),
              'deferred': log.get('deferred'), 'han_only_runs': len(han), 'empty_notes_removed': log.get('empty_notes_removed', [])},
    'verify': ver, 'timing_seconds': timing, 'raw_reply': reply,
    'earlier_attempts': attempts, 'cost_total_usd': round(cost_this + cost_earlier, 6),
}
json.dump(record, open(os.path.join(R, 'record.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if han:
    with open(os.path.join(R, 'han_review.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['pdf_page', 'printed_page', 'mcid', 'han_text', 'decision (ja / zh / ko / other)', 'note'])
        for h in han: w.writerow([h['page'], h.get('label'), h['mcid'], h['text'], '', ''])

# ------------------------------------------------------------------ review.md
t = ver.get('tree', {}); hd = ver.get('headings', {}); fg = ver.get('figures', {}); doc = ver.get('doc', {})
def ok(cond): return 'OK' if cond else '**CHECK**'
nt = ver.get('notes') or {}
checks = [
    ('Every page looks the same as the original', ok(ver.get('pixel_pages_differing') == []), f'{len(ver.get("pixel_pages_differing") or [])} pages differ'),
    ('Published text unchanged', ok(ver.get('text_pages_changed') == []), f'{len(ver.get("text_pages_changed") or [])} pages changed'),
    ('All content tagged or marked as decoration', ok(ver.get('untagged_chars') == 0), f'{ver.get("untagged_chars")} untagged characters'),
    ('Tag tree consistent', ok(t.get('parenttree_missing') == 0 and t.get('parenttree_mismatched') == 0),
     f'{t.get("parenttree_missing")} missing · {t.get("parenttree_mismatched")} mismatched'),
    ('All marked text reachable from the tag tree', ok(t.get('content_mcids_not_in_tree') == 0), f'{t.get("content_mcids_not_in_tree")} orphan runs'),
    ('One Document root', ok({k.lstrip('/'): v for k, v in (t.get('root_children') or {}).items()} == {'Document': 1}),
     ', '.join(f'{k.lstrip("/")} {v}' for k, v in (t.get('root_children') or {}).items())),
    ('Every link tied to its text and described', ok(t.get('annotations_unresolved') == 0 and t.get('annotations_without_Contents') == 0 and t.get('stale_OBJRs') == 0),
     f'{t.get("annotations_unresolved")} unresolved · {t.get("annotations_without_Contents")} without description · {t.get("stale_OBJRs")} pointing to no annotation'),
    ('No link nested inside another', ok(t.get('nested_Link_in_Link') == 0), str(t.get('nested_Link_in_Link'))),
    ('Headings: no skipped levels', ok(not hd.get('skipped_levels')), ' · '.join(f'{k} {v}' for k, v in sorted((hd.get('counts') or {}).items()))),
    ('Figures: none with empty or placeholder alt', ok(fg.get('generic_or_empty') == 0), f'{fg.get("count")} figures, {fg.get("generic_or_empty")} placeholder'),
    ('Every Note has a unique ID', ok(not nt or (nt.get('without_ID') == 0 and nt.get('duplicate_ID') == 0 and nt.get('not_in_IDTree') == 0)),
     f'{nt.get("count", 0)} notes · {nt.get("without_ID", 0)} without ID · {nt.get("duplicate_ID", 0)} duplicate · {nt.get("not_in_IDTree", 0)} not in the ID tree'
     + (f' · {len(log.get("empty_notes_removed") or [])} empty Note tags removed' if log.get('empty_notes_removed') else '')),
    ('Title and language set', ok(bool(doc.get('title')) and bool(doc.get('lang'))), f'"{doc.get("title")}" · {doc.get("lang")}'),
]
u = run.get('usage') or {}
L = [f'# Remediation review: {src.get("file")}', '', f'Result: `{PDF}`', '',
     f'{src.get("pages")} pages · run {run.get("started", "?")} · model `{run.get("model")}` · prompt `{run.get("prompt_file")}` ({run.get("prompt_sha256")}) · '
     f'cost ${u.get("cost_usd") if u.get("cost_usd") is not None else "?"} · {u.get("prompt_tokens")} in / {u.get("completion_tokens")} out tokens'
     + (f' · plus ${cost_earlier:.3f} for {len(attempts)} earlier call(s) whose reply was cut off or unusable (total ${cost_this + cost_earlier:.3f})' if attempts else ''), '',
     *([('Time: ' + ' · '.join(f'{k.split(" ", 1)[1].split(" (")[0]} {v}s' for k, v in timing.items()) + f' · total {round(sum(timing.values()), 1)}s'), ''] if timing else []),
     'Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.', '',
     '## Automated checks', '', '| Check | Result | Detail |', '|---|---|---|']
L += [f'| {a} | {b} | {c} |' for a, b, c in checks]

L += ['', '## For a person to check', '']
n = 0
alts = wo.get('alt', [])
if alts:
    n += 1; L += [f'### {n}. Alt text written or changed by the AI ({len(alts)})', '', '| Page | Before | After |', '|---|---|---|']
    for a in alts:
        f = figs.get(a['obj'], {})
        L.append(f'| {f.get("label") or f.get("page", "?")} | {(f.get("alt") or "—")[:160]} | {a["alt"]} |')
    L.append('')
kept = [f for o, f in figs.items() if o not in {a['obj'] for a in alts}
        and o not in {e['obj'] for e in wo.get('artifacts', {}).get('elements', [])}]
if kept:
    n += 1; L += [f'### {n}. Figures that kept their existing alt text ({len(kept)})', '', 'Not changed by the AI. Check they are adequate.', '',
                  '| Page | Alt text |', '|---|---|']
    L += [f'| {f.get("label") or f.get("page")} | {(f.get("alt") or "—")[:200]} |' for f in kept]
    L.append('')
ats = wo.get('actual_text', [])
if ats or wo.get('rolemap'):
    n += 1; L += [f'### {n}. Headings', '']
    if wo.get('rolemap'):
        cnt = {s['style']: s['count'] for s in digest.get('styles', [])}
        L += ['Heading levels by style:', '', '| Style | Level | Elements |', '|---|---|---:|']
        L += [f'| {k} | {v} | {cnt.get(k, "?")} |' for k, v in wo['rolemap'].items()]
        L.append('')
    if wo.get('merges'):
        L += ['Merged: ' + '; '.join(f'`{m["style"]}` into the {m["direction"]} `{"/".join(m["with"])}`' for m in wo['merges']), '']
    if ats:
        L += ['Spoken text set by the AI (should match what is printed):', '', '| Page | Text |', '|---|---|']
        L += [f'| {elems.get(a["obj"], {}).get("label", "?")} | {a["text"]} |' for a in ats]
        L.append('')
rt = wo.get('retype', [])
if rt:
    n += 1; L += [f'### {n}. Elements retyped by the AI ({len(rt)})', '', 'Check each one is (or is not) a heading as decided.', '',
                  '| Page | Text | Was | Now |', '|---|---|---|---|']
    for r in rt:
        e = elems.get(r['obj'], {})
        L.append(f'| {e.get("label") or e.get("page", "?")} | {(e.get("text") or "?")[:80]} | {e.get("level") or e.get("style", "?")} | {r["type"]} |')
    L.append('')
fl = wo.get('flatten', [])
kept_tables = [t for o, t in tables_.items() if o not in {f['obj'] for f in fl}]
if fl or kept_tables:
    n += 1; L += [f'### {n}. Lists and tables', '']
    for f in fl:
        x = lists_.get(f['obj']) or tables_.get(f['obj']) or {}
        kind = 'list' if f['obj'] in lists_ else 'table'
        L.append(f'- Flattened {kind} on page {x.get("label") or x.get("page", "?")}: "{" / ".join(x.get("first_items") or x.get("first_rows") or [])[:100]}" ({f.get("why", "")})')
    if kept_tables:
        L += ['', f'Tables kept as tables ({len(kept_tables)}): check header cells and reading order.', '']
        L += [f'- Page {t.get("label") or t.get("page")}: {t["rows"]} rows × {t["cols"]} columns, {t["header_cells"]} header cells. "{(t.get("first_rows") or [""])[0][:90]}"' for t in kept_tables]
    L.append('')
tq = digest.get('text_quality', {})
if tq.get('producer_says_ocr') or (tq.get('pages_with_full_page_image', 0) > 0.5 * (src.get('pages') or 1)):
    n += 1; L += [f'### {n}. Scanned book: the text layer comes from OCR', '',
                  f'{tq.get("pages_with_full_page_image")} of {src.get("pages")} pages are full-page images. Screen readers read the OCR text, '
                  f'which may contain recognition errors (suspect-token rate {tq.get("suspect_tokens_per_1000")} per 1,000). '
                  f'Spot-check these pages against the scan: {", ".join(str(p) for p in tq.get("worst_pages", []))}. Corrections are an editorial decision.', '']
uc = digest.get('unowned_content', [])
if uc:
    n += 1; tot = digest.get('unowned_content_totals', {})
    L += [f'### {n}. Text a screen reader could not reach (before this run)', '',
          f'{len(uc)} pages had text outside the tag tree: {tot.get("orphan", 0)} orphan runs (marked, but no tag owns them) and '
          f'{tot.get("untagged", 0)} untagged runs. Running heads and page numbers among them can be hidden as decoration; real content '
          f'must be added to the tag tree by a person. After this run: {ver.get("untagged_chars")} untagged characters, '
          f'{t.get("content_mcids_not_in_tree")} orphan runs remain.', '', 'Pages (first 25): ' + ', '.join(str(x['page']) if isinstance(x, dict) else x.split('|')[0] for x in uc[:25]), '']
art = wo.get('artifacts', {})
if art.get('elements') or art.get('text_rules'):
    n += 1; L += [f'### {n}. Hidden from screen readers (artifacts)', '']
    if art.get('elements'):
        pages = sorted({figs.get(e['obj'], {}).get('label') or '?' for e in art['elements']}, key=str)
        L.append(f'- {len(art["elements"])} decorative elements ({", ".join(sorted({e.get("label", "?") for e in art["elements"]}))}) on pages {", ".join(pages)}')
    for r in art.get('text_rules', []):
        L.append(f'- {r.get("label")}: text matching `{r.get("regex")}` on PDF pages {r["pages"][0]}–{r["pages"][1]}')
    L.append('')
moves = []
if wo.get('move_section'): moves.append(f'Section on PDF pages {wo["move_section"]["pages"][0]}–{wo["move_section"]["pages"][1]} moved to read before page {wo["move_section"]["before_page"]}')
if (log.get('applied') or {}).get('order: figure moved to its page'): moves.append(f'{log["applied"]["order: figure moved to its page"]} figure(s) moved to read on their printed page')
if wo.get('move_to_document_start'): moves.append('Cover figure moved to the start of the document')
if moves:
    n += 1; L += [f'### {n}. Reading order changes', '', 'Listen through these spots with a screen reader.', ''] + [f'- {m}' for m in moves] + ['']
d_ai = wo.get('deferrals', [])
if d_ai or wo.get('notes_for_reviewer'):
    n += 1; L += [f'### {n}. Deferred by the AI', '']
    L += [f'- **{d.get("what")}**: {d.get("why")}' for d in d_ai]
    if wo.get('notes_for_reviewer'): L += ['', f'Reviewer note from the AI: {wo["notes_for_reviewer"]}']
    L.append('')
d_ex = [d for d in log.get('deferred', []) if d.get('what') != 'Han-only runs (ja vs zh)']
if han or d_ex:
    n += 1; L += [f'### {n}. Deferred by the executor', '']
    if han: L.append(f'- **{len(han)} Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.')
    L += [f'- {d.get("what")}' + (f' (page {d["page"]})' if 'page' in d else '') + (f': {d["why"]}' if 'why' in d else '') for d in d_ex[:40]]
    L.append('')
bad = log.get('rejected', []) + log.get('failed', []) + val.get('dropped', [])
if bad:
    n += 1; L += [f'### {n}. Decisions not applied ({len(bad)})', '', 'Rejected by validation or by the executor; nothing was half-applied.', '']
    L += [f'- {json.dumps(b, ensure_ascii=False)[:220]}' for b in bad[:60]]
    L.append('')
if n == 0: L.append('Nothing flagged.')

L += ['## What was changed', '', '| Change | Count |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in (log.get('applied') or {}).items()]
open(os.path.join(R, 'review.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ tidy
if not KEEP:
    for name in ('request.json', 'response.json', 'reply.txt', 'run.json', 'validation.json', 'workorder.json',
                 PDF + '.log.json', PDF + '.verify.json', 'verify.txt', 'error.txt', 'timing.json', 'attempts.json'):
        p = os.path.join(R, name)
        if os.path.exists(p): os.remove(p)
    if os.path.isdir(A) and os.path.exists(os.path.join(A, 'digest.json')): shutil.rmtree(A)
print(f'review: {os.path.join(R, "review.md")} · record: {os.path.join(R, "record.json")}' + (f' · han_review.csv ({len(han)} rows)' if han else '')
      + ('' if KEEP else ' · working files removed'))
