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
import sys, os, csv, json, shutil, datetime, collections

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
    'verify': ver, 'timing_seconds': timing, 'raw_reply': reply, 'environment': log.get('environment'),
    'earlier_attempts': attempts, 'cost_total_usd': round(cost_this + cost_earlier, 6),
}
json.dump(record, open(os.path.join(R, 'record.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if han:
    with open(os.path.join(R, 'han_review.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['pdf_page', 'printed_page', 'mcid', 'han_text', 'decision (ja / zh / ko / other)', 'note'])
        for h in han: w.writerow([h['page'], h.get('label'), h['mcid'], h['text'], '', ''])

# ------------------------------------------------------------------ review.md
# Every page is cited by its PDF page (what the checker, Acrobat and the executor count), with the printed label from
# the remediated PDF's own page-label table beside it only when there is one and it differs: "PDF 16 (printed 3)".
try:
    import pikepdf as _pk
    with _pk.open(os.path.join(R, PDF)) as _p: PLAB = {i + 1: str(pg_.label) for i, pg_ in enumerate(_p.pages)}
except Exception: PLAB = {}
NO_PAGE = 'page: not on this tag'                 # a missing page is never printed as "unknown" (the record keeps null)
def pg(n):
    try: n = int(n)
    except (TypeError, ValueError): return NO_PAGE
    lab = PLAB.get(n, '')
    return f'PDF {n}' + (f' (printed {lab})' if lab and lab != str(n) else '')
def pgr(a, b):
    if a == b: return pg(a)
    la, lb = PLAB.get(int(a), ''), PLAB.get(int(b), '')
    return f'PDF {a}–{b}' + (f' (printed {la}–{lb})' if la and lb and (la != str(a) or lb != str(b)) else '')
def pgs(ns): return ', '.join([pg(n) for n in sorted({n for n in ns if n is not None}, key=int)] + ([NO_PAGE] if any(n is None for n in ns) else []))
def nc(v): return 'not counted' if v is None else v      # a count the verify file left empty
def on_pg(n): return f'on {pg(n)}' if n is not None else f'({NO_PAGE})'
def by_page(items, key=lambda x: x.get('page')):
    return sorted(items, key=lambda x: (key(x) is None, key(x) or 0))
t = ver.get('tree', {}); hd = ver.get('headings', {}); fg = ver.get('figures', {}); doc = ver.get('doc', {})
def ok(cond): return 'OK' if cond else '**CHECK**'
nt = ver.get('notes') or {}; bm = ver.get('bookmarks') or {}; uo = ver.get('untagged_objects') or {}; fo = ver.get('fonts') or {}
ocr_unread = sorted({x['font'] for x in fo.get('unreadable') or [] if 'OCR' in x['font'] or 'GlyphLess' in x['font']}
              | {x['font'] for x in (log.get('ocr_fonts') or {}).get('left') or [] if 'could not be read' in x.get('why', '')})
pl = log.get('paths') or {}; n_paths = ver.get('untagged_paths', (uo.get('by_kind') or {}).get('path', 0))
pfw = log.get('page_figures') or {}; vpf = {x['page']: x for x in ver.get('page_figures') or []}
pfw_wrapped = pfw.get('wrapped') or []; pfw_left = pfw.get('left') or []
pfw_noalt = [w for w in pfw_wrapped if not vpf.get(w['page'], {}).get('alt', w.get('alt'))]
pfw_bad = [p for p, x in vpf.items() if x.get('figures') != 1 or x.get('untagged_left')]
stc = ver.get('structure'); idx = ver.get('index'); et = log.get('empty_tags') or {}
et_lost = [h for h in et.get('headings') or [] if not h.get('found')]
rb = run.get('reply_blocks')
checks = [
    ('Every page looks the same as the original', ok(ver.get('pixel_pages_differing') == []), f'{len(ver.get("pixel_pages_differing") or [])} pages differ'),
    ('Published text unchanged', ok(ver.get('text_pages_changed') == []), f'{len(ver.get("text_pages_changed") or [])} pages changed'),
    ('All content tagged or marked as decoration', ok(ver.get('untagged_chars') == 0 and not uo.get('total')),
     f'{ver["untagged_chars"] if ver.get("untagged_chars") is not None else "not counted"} untagged characters · {uo["total"] if uo.get("total") is not None else "not counted"} untagged objects'
     + (' (' + ', '.join(f'{v} {k}' for k, v in (uo.get('by_kind') or {}).items()) + ')' if uo.get('total') else '')),
    ('Untagged paths: none left', ok(n_paths == 0),
     f'{n_paths} untagged paths' + (f' · {pl["artifacted"]} rules, borders and lines marked as decoration by this run' if pl.get('artifacted') else '')
     + ('; left: ' + '; '.join(f'{c} {w.split(":")[0]}' for w, c in (pl.get('left') or {}).items()) if pl.get('left') else '')),
    ('Invisible OCR text: every glyph defined', ok(not fo.get('ocr_overlay_undefined') and not ocr_unread and not any(x.get('render_modes') and set(x['render_modes']) == {'3'} for x in fo.get('only_notdef') or [])),
     '; '.join(f'{x["font"]}: {x["glyph_references"]} undefined glyph references on {x["pages"]} pages' for x in fo.get('ocr_overlay_undefined') or [])
     or ('; '.join(f'{x}: its font program could not be read, so it was not checked' for x in ocr_unread))
     or ('; '.join(f'{x["font"]}: blank glyphs added for {x["glyph_references"]} glyph references on {x["pages"]} pages (replay: no page changed)'
                   for x in (log.get('ocr_fonts') or {}).get('replaced') or []) or 'no undefined glyphs in invisible text')),
    ('Page-level figure wrap', ok(not pfw_noalt and not pfw_left and not pfw_bad),
     (pgs([w['page'] for w in pfw_wrapped]) + ' wrapped as one Figure' if pfw_wrapped else 'no page with only an untagged drawing')
     + (' · no alt text yet: ' + '; '.join(f'{pg(w["page"])} is a figure wrap. Write the alt text.' for w in pfw_noalt) if pfw_noalt else '')
     + (' · not wrapped: ' + '; '.join(f'{pg(x["page"])} ({x["why"]})' for x in pfw_left) if pfw_left else '')
     + (f' · check failed on {pgs(pfw_bad)}' if pfw_bad else '')),
    ('Empty tags removed when proven empty', ok(not et.get('kept') and not et_lost),
     f'{len(et.get("removed") or [])} removed' + (f' ({len(et["tables_removed"])} whole empty tables)' if et.get('tables_removed') else '')
     + (f' · {len(et["kept"])} kept: something refers to them or they carry an attribute (listed)' if et.get('kept') else '')
     + (f' · {len(et_lost)} empty heading(s) with no heading text on their page' if et_lost else '') if et else 'not run'),
    ('Tag-tree index points only into the tree', ok(idx is not None and idx['dangling'] == 0),
     (f'{idx["dangling"]} dangling entries' + (' (' + ', '.join(f'{d["index"]} ' + (f'key {d["key"]}' if 'key' in d else f'"{d.get("id")}"') for d in idx['dangling_examples'][:6]) + ')' if idx['dangling'] else '')
      + f' · {idx["stale_entries"]} stale entries (marked content no longer drawn)') if idx else 'not checked'),
    ('No empty tables', ok(stc is not None and not stc.get('empty_tables')),
     (pgs([x['page'] for x in stc['empty_tables']]) if stc.get('empty_tables') else 'none') if stc else 'not checked'),
    ('No empty tags', ok(stc is not None and stc['empty_tags'] == 0),
     f'{stc["empty_tags"]} empty tag' + ('s' if stc['empty_tags'] != 1 else '') + (' (' + pgs([e['page'] for e in stc['empty_tag_examples']]) + (' …' if stc['empty_tags'] > len(stc['empty_tag_examples']) else '') + ')' if stc['empty_tags'] else '') if stc else 'not checked'),
    ('No paragraph holding only figures', ok(stc is not None and not stc['paragraphs_holding_only_figures']),
     (', '.join(f'{pg(x["page"])} ({x["figures"]} figures in {x["tag"]})' for x in by_page(stc['paragraphs_holding_only_figures'])[:10]) or 'none') if stc else 'not checked'),
    ('Every caption grouped with its figure', ok(stc is not None and not stc['captions_not_grouped']),
     (', '.join(f'{pg(x["page"])} (caption inside {x["parent"]})' for x in by_page(stc['captions_not_grouped'])[:10]) or 'all grouped') if stc else 'not checked'),
    ('No link whose only text is a URL', ok(stc is not None and not stc['links_url_only']),
     (f'{len(stc["links_url_only"])}: ' + pgs([x['page'] for x in stc['links_url_only']]) if stc['links_url_only'] else 'none') if stc else 'not checked'),
    ('Tag tree consistent', ok(t.get('parenttree_missing') == 0 and t.get('parenttree_mismatched') == 0),
     f'{nc(t.get("parenttree_missing"))} missing · {nc(t.get("parenttree_mismatched"))} mismatched'),
    ('All marked text reachable from the tag tree', ok(t.get('content_mcids_not_in_tree') == 0), f'{nc(t.get("content_mcids_not_in_tree"))} orphan runs'),
    ('One Document root', ok({k.lstrip('/'): v for k, v in (t.get('root_children') or {}).items()} == {'Document': 1}),
     ', '.join(f'{k.lstrip("/")} {v}' for k, v in (t.get('root_children') or {}).items())),
    ('Every link tied to its text and described', ok(t.get('annotations_unresolved') == 0 and t.get('annotations_without_Contents') == 0 and t.get('stale_OBJRs') == 0),
     f'{nc(t.get("annotations_unresolved"))} unresolved · {nc(t.get("annotations_without_Contents"))} without description · {nc(t.get("stale_OBJRs"))} pointing to no annotation'),
    ('No link nested inside another', ok(t.get('nested_Link_in_Link') == 0), str(t.get('nested_Link_in_Link'))),
    ('Headings: no skipped levels', ok(not hd.get('skipped_levels')), ' · '.join(f'{k} {v}' for k, v in sorted((hd.get('counts') or {}).items()))),
    ('Headings: exactly one H1 (the title)', ok((hd.get('counts') or {}).get('H1') == 1),
     f'{(hd.get("counts") or {}).get("H1", 0)} H1 (several H1s usually mean parts or chapters were not demoted)'),
    ('Figures: none with empty or placeholder alt', ok(fg.get('generic_or_empty') == 0), f'{nc(fg.get("count"))} figures, {nc(fg.get("generic_or_empty"))} placeholder'),
    ('Every Note has a unique ID', ok(not nt or (nt.get('without_ID') == 0 and nt.get('duplicate_ID') == 0 and nt.get('not_in_IDTree') == 0)),
     f'{nt.get("count", 0)} notes · {nt.get("without_ID", 0)} without ID · {nt.get("duplicate_ID", 0)} duplicate · {nt.get("not_in_IDTree", 0)} not in the ID tree'
     + (f' · {len(log.get("empty_notes_removed") or [])} empty Note tags removed' if log.get('empty_notes_removed') else '')),
    ('Bookmarks present (documents over 9 pages)', ok(bm.get('pages', 0) <= 9 or bm.get('items', 0) > 0),
     (f'{bm["items"]} bookmarks' if bm.get('items') is not None else 'bookmarks: not counted') + (f' (built from {log["bookmarks"]["items"]} heading tags)' if (log.get('bookmarks') or {}).get('built') else '')),
    ('Model reply held one work order', ok(not rb),
     f'{rb["count"]} work orders; the last one (the model\'s final answer) was used, as written (see "The model\'s reply held {rb["count"]} work orders")' if rb else 'one'),
    ('Executor applied every decision', ok(not log.get('rejected') and not log.get('failed')),
     f'{len(log.get("rejected") or [])} rejected · {len(log.get("failed") or [])} failed (listed under "Decisions not applied")'),
    ('Nothing deferred by the executor', ok(not log.get('deferred')),
     f'{len(log.get("deferred") or [])} deferred (listed under "Deferred by the executor")'),
    ('Fonts: every glyph defined (no .notdef)', ok(not fo.get('only_notdef')),
     '; '.join(f'{x["font"]}: {x["glyph_references"]} undefined glyph references on {x["pages"]} pages' for x in fo.get('only_notdef') or []) or 'none found'),
    ('Fonts: every embedded font program could be read', ok(not fo.get('unreadable')),
     ('; '.join(f'{x["font"]} ({x["pages"]} pages)' for x in fo.get('unreadable')) + ': not checked, so their glyphs may be undefined') if fo.get('unreadable') else 'all read'),
    ('Fonts: embedded and mapped to Unicode', ok(not fo.get('not_embedded') and not fo.get('no_ToUnicode')),
     f'{len(fo.get("not_embedded") or [])} not embedded · {len(fo.get("no_ToUnicode") or [])} without ToUnicode'
     + (f' ({len(fo["no_ToUnicode_not_needed"])} more have none and need none: standard encoding, non-symbolic)' if fo.get('no_ToUnicode_not_needed') else '')),
    ('Title and language set', ok(bool(doc.get('title')) and bool(doc.get('lang'))), (f'"{doc["title"]}"' if doc.get('title') else 'title not set') + ' · ' + (doc.get('lang') or 'language not set')),
]
u = run.get('usage') or {}
L = [f'# Remediation review: {src.get("file") or "file name not recorded"}', '', f'Result: `{PDF}`', '',
     f'{nc(src.get("pages"))} pages · run {run.get("started") or "start time not recorded"} · '
     + (f'model `{run["model"]}`' if run.get('model') else 'model not recorded') + ' · '
     + (f'prompt `{run["prompt_file"]}` ({run.get("prompt_sha256") or "hash not recorded"})' if run.get('prompt_file') else 'prompt not recorded') + ' · '
     + (f'cost ${u["cost_usd"]}' if u.get('cost_usd') is not None else 'cost: call did not finish') + ' · '
     + (f'{u["prompt_tokens"]} in / {u["completion_tokens"]} out tokens' if u.get('prompt_tokens') is not None and u.get('completion_tokens') is not None else 'tokens: call did not finish')
     + (f' · plus ${cost_earlier:.3f} for {len(attempts)} earlier call(s) whose reply was cut off or unusable (total ${cost_this + cost_earlier:.3f})' if attempts else ''), '',
     *([('Libraries: ' + ' · '.join(f'{k} {v}' for k, v in log['environment'].items() if k != 'executable')), ''] if log.get('environment') else []),
     *([('Time: ' + ' · '.join(f'{k.split(" ", 1)[1].split(" (")[0]} {v}s' for k, v in timing.items()) + f' · total {round(sum(timing.values()), 1)}s'), ''] if timing else []),
     'Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.', '',
     '## Automated checks', '', '| Check | Result | Detail |', '|---|---|---|']
L += [f'| {a} | {b} | {c} |' for a, b, c in checks]

L += ['', '## For a person to check', '']
n = 0
if rb:
    n += 1; L += [f'### {n}. The model\'s reply held {rb["count"]} work orders', '',
                  f'The reply held {rb["count"]} JSON work orders. The last one, the model\'s final answer, was used exactly as written; '
                  'nothing was merged and no earlier one was used. The full reply is in `record.json` (`raw_reply`).', '']
    if rb.get('model_text_before_last'):
        L += ['What the model wrote before the last one:', ''] + ['> ' + x for x in rb['model_text_before_last'].splitlines()] + ['']
    if rb.get('keys_changed_from_previous') is not None:
        L += ['Parts that differ from the one before: ' + (', '.join(f'`{k}`' for k in rb['keys_changed_from_previous']) or 'none') + '. '
              'Compare them in `raw_reply` if the change matters.', '']
if pfw_wrapped or pfw_left:
    n += 1; L += [f'### {n}. Pages wrapped as one Figure ({len(pfw_wrapped)})', '',
                  'Pages with nothing tagged and nothing marked as decoration that hold a drawing (a full-page map, plate or cover). '
                  'Each page was wrapped whole in one Figure; nothing on it was changed or removed.', '']
    for w in by_page(pfw_wrapped):
        a = next((x.get('alt') for x in wo.get('page_figures') or [] if int(x.get('page', -1)) == w['page']), None)
        L.append(f'- {pg(w["page"])}: ' + ('read first in the document. ' if w['after'] == 'start of the document' else f'read after {w["after"]}. ')
                 + (f'Alt text from the AI: "{a}"' if a else f'**{pg(w["page"])} is a figure wrap. Write the alt text.**'))
    for x in by_page(pfw_left):
        L.append(f'- {pg(x["page"])}: not wrapped, left as it is ({x["why"]}).')
    L.append('')
alts = wo.get('alt', [])
if alts:
    n += 1; L += [f'### {n}. Alt text written or changed by the AI ({len(alts)})', '', '| Page | Before | After |', '|---|---|---|']
    for a in by_page(alts, key=lambda a: figs.get(a['obj'], {}).get('page')):
        f = figs.get(a['obj'], {})
        L.append(f'| {pg(f.get("page"))} | {(f.get("alt") or "—")[:160]} | {a["alt"]} |')
    L.append('')
kept = [f for o, f in figs.items() if o not in {a['obj'] for a in alts}
        and o not in {e['obj'] for e in wo.get('artifacts', {}).get('elements', [])}]
if kept:
    n += 1; L += [f'### {n}. Figures that kept their existing alt text ({len(kept)})', '', 'Not changed by the AI. Check they are adequate.', '',
                  '| Page | Alt text |', '|---|---|']
    L += [f'| {pg(f.get("page"))} | {(f.get("alt") or "—")[:200]} |' for f in by_page(kept)]
    L.append('')
ats = wo.get('actual_text', [])
if ats or wo.get('rolemap'):
    n += 1; L += [f'### {n}. Headings', '']
    if wo.get('rolemap'):
        cnt = {s['style']: s['count'] for s in digest.get('styles', [])}
        done = log.get('rolemap')
        if done is None:                              # a log from before the executor recorded this: drop what it refused
            refused = {r['op'].split(' ', 1)[1] for r in log.get('rejected') or [] if r.get('op', '').startswith('rolemap ')}
            done = {k: {'to': v, 'how': 'RoleMap', 'elements': cnt.get(k, 'not counted')} for k, v in wo['rolemap'].items() if k not in refused}
        L += ['Heading levels by style (as applied):', '', '| Style | Level | How | Elements |', '|---|---|---|---:|']
        L += [f'| {k} | {d["to"]} | {d["how"]} | {d["elements"] if d.get("elements") is not None else "not counted"} |' for k, d in done.items()]
        not_done = [k for k in wo['rolemap'] if k not in done]
        if not_done: L += ['', 'Not applied (see "Decisions not applied"): ' + ', '.join(f'`{k}` → {wo["rolemap"][k]}' for k in not_done)]
        L.append('')
    if wo.get('merges'):
        L += ['Merged: ' + '; '.join(f'`{m["style"]}` into the {m["direction"]} `{"/".join(m["with"])}`' for m in wo['merges']), '']
    if ats:
        L += ['Spoken text set by the AI (should match what is printed):', '', '| Page | Text |', '|---|---|']
        L += [f'| {pg(elems.get(a["obj"], {}).get("page"))} | {a["text"]} |' for a in by_page(ats, key=lambda a: elems.get(a['obj'], {}).get('page'))]
        L.append('')
rt = wo.get('retype', [])
if rt:
    n += 1; L += [f'### {n}. Elements retyped by the AI ({len(rt)})', '', 'Check each one is (or is not) a heading as decided.', '',
                  '| Page | Text | Was | Now |', '|---|---|---|---|']
    for r in by_page(rt, key=lambda r: elems.get(r['obj'], {}).get('page')):
        e = elems.get(r['obj'], {})
        L.append(f'| {pg(e.get("page"))} | {(e.get("text") or "(no text)")[:80]} | {e.get("level") or e.get("style") or "(no style)"} | {r["type"]} |')
    L.append('')
fl = wo.get('flatten', [])
kept_tables = [t for o, t in tables_.items() if o not in {f['obj'] for f in fl}]
if fl or kept_tables:
    n += 1; L += [f'### {n}. Lists and tables', '']
    for f in fl:
        x = lists_.get(f['obj']) or tables_.get(f['obj']) or {}
        kind = 'list' if f['obj'] in lists_ else 'table'
        L.append(f'- Flattened {kind} {on_pg(x.get("page"))}: "{" / ".join(x.get("first_items") or x.get("first_rows") or [])[:100]}" ({f.get("why", "")})')
    if kept_tables:
        L += ['', f'Tables kept as tables ({len(kept_tables)}): check header cells and reading order.', '']
        L += [f'- {pg(t.get("page"))}: {t["rows"]} rows × {t["cols"]} columns, {t["header_cells"]} header cells. "{(t.get("first_rows") or [""])[0][:90]}"' for t in by_page(kept_tables)]
    L.append('')
tq = digest.get('text_quality', {})
if tq.get('producer_says_ocr') or (tq.get('pages_with_full_page_image', 0) > 0.5 * (src.get('pages') or 1)):
    n += 1; L += [f'### {n}. Scanned book: the text layer comes from OCR', '',
                  f'{nc(tq.get("pages_with_full_page_image"))} of {nc(src.get("pages"))} pages are full-page images. Screen readers read the OCR text, '
                  f'which may contain recognition errors (suspect-token rate {nc(tq.get("suspect_tokens_per_1000"))} per 1,000). '
                  f'Spot-check these pages against the scan: {pgs(tq.get("worst_pages", []))}. Corrections are an editorial decision.', '']
uc = digest.get('unowned_content', [])
if uc:
    n += 1; tot = digest.get('unowned_content_totals', {})
    L += [f'### {n}. Text a screen reader could not reach (before this run)', '',
          f'{len(uc)} pages had text outside the tag tree: {tot.get("orphan", 0)} orphan runs (marked, but no tag owns them) and '
          f'{tot.get("untagged", 0)} untagged runs. Running heads and page numbers among them can be hidden as decoration; real content '
          f'must be added to the tag tree by a person. After this run: {nc(ver.get("untagged_chars"))} untagged characters, '
          f'{nc(t.get("content_mcids_not_in_tree"))} orphan runs remain.', '', 'Pages (first 25): ' + pgs([x['page'] if isinstance(x, dict) else int(x.split('|')[0]) for x in uc[:25]]), '']
art = wo.get('artifacts', {})
if art.get('elements') or art.get('text_rules') or art.get('untagged'):
    n += 1; L += [f'### {n}. Hidden from screen readers (artifacts)', '']
    if art.get('elements'):
        art_labels = ', '.join(sorted({chr(34) + str(e.get('label') or '(no label given)') + chr(34) for e in art['elements']}))     # the AI's own labels, quoted
        L.append(f'- {len(art["elements"])} decorative elements ({art_labels}) on '
                 + pgs([figs.get(e['obj'], {}).get('page') for e in art['elements']]))
    for r in art.get('text_rules', []):
        L.append(f'- "{r.get("label") or "(no label given)"}": ' + (f'text matching `{r["regex"]}`' if r.get('regex') else f'every {"orphan " if r.get("orphans") else ""}run in the {r.get("band") or "any"} band') + f' on {pgr(r["pages"][0], r["pages"][1])}')
    for r in art.get('untagged', []):
        L.append(f'- "{r.get("label") or "(no label given)"}": untagged text ' + (f'matching `{r["regex"]}`' if r.get('regex') else 'inside Figures') + f' on {pgr(r["pages"][0], r["pages"][1])}')
    L.append('')
moves = []
if wo.get('move_section'): moves.append(f'Section on {pgr(wo["move_section"]["pages"][0], wo["move_section"]["pages"][1])} moved to read before {pg(wo["move_section"]["before_page"])}')
if (log.get('applied') or {}).get('order: figure moved to its page') and not log.get('figure_moves'): moves.append(f'{log["applied"]["order: figure moved to its page"]} figure(s) moved to read on their printed page')
if wo.get('move_to_document_start'): moves.append('Cover figure moved to the start of the document')
for fm in by_page(log.get('figure_moves') or []):
    moves.append(f'Figure on {pg(fm["page"])} moved to read with its page (it read after {pg(fm["was_after_page"])}; now after {pg(fm["now_after_page"])})')
if moves:
    n += 1; L += [f'### {n}. Reading order changes', '', 'Listen through these spots with a screen reader.', ''] + [f'- {m}' for m in moves] + ['']
fx = fo.get('only_notdef') or []; ocr = log.get('ocr_fonts') or {}
if fx or fo.get('not_embedded') or fo.get('no_ToUnicode') or ocr.get('replaced') or ocr.get('left'):
    n += 1; L += [f'### {n}. Fonts', '']
    for x in ocr.get('replaced') or []:
        L.append(f'- **{x["font"]}** (fixed by the pipeline): the invisible OCR layer of the scanned pages used a font whose program held only '
                 f'`.notdef`. Its program was swapped for a blank one in which every character is a defined, empty glyph of the same width '
                 f'({x["font_objects"]} font objects, {x["glyph_references"]} glyph references on {x["pages"]} pages). Same character codes, same '
                 f'ToUnicode map, same widths, still invisible; a replay of {x["pages_replayed"]} pages showed none looking different and no text '
                 'changed. The fix does not make the OCR text accurate: recognition errors stay, so spot-check the OCR text against the scan.')
    for x in ocr.get('left') or []:
        L.append(f'- **{x["font"]}** (OCR layer, not changed' + (f', {x["font_objects"]} font objects' if x.get('font_objects', 1) > 1 else '') + f'): {x["why"]}.')
    if fx or fo.get('not_embedded') or fo.get('no_ToUnicode'):
        L += ([''] if L[-1] else []) + ['The pipeline changes no other font: it never embeds one, replaces a visible one, or rewrites text. These need a person:', '']
    for x in fx:
        hidden = set(x.get('render_modes') or {}) == {'3'}
        L += [f'- **{x["font"]}**: its embedded font program holds only the `.notdef` glyph, so every one of its {x["glyph_references"]} '
              f'glyph references ({x["text_operators"]} text operators on {x["pages"]} pages, from {pgs(x["first_pages"])} …) '
              f'is an undefined character (ISO 14289-1 7.21.8, PDF/UA). '
              + ('It has a ToUnicode map, so the text is extracted and read aloud; adding or changing a map cannot define a glyph, '
                 'so no map was added. ' if x.get('has_ToUnicode') else 'It has no ToUnicode map either. ')
              + ('Its text is invisible (render mode 3): it is the hidden OCR layer laid over words recognized in a scanned image. ' if hidden else '')
              + 'A person must regenerate that text with a font that contains the glyphs (re-run OCR, or replace the font in Acrobat '
                'or another PDF tool), then re-check with PAC. Both change the file, so they are outside this pipeline.']
    if fo.get('not_embedded'):
        L.append(f'- **Not embedded** ({len(fo["not_embedded"])}): {", ".join(fo["not_embedded"])}. PDF/UA requires embedded fonts (7.21.4.1); '
                 'a person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.')
    if fo.get('no_ToUnicode'):
        L.append(f'- **No ToUnicode map** ({len(fo["no_ToUnicode"])}): {", ".join(fo["no_ToUnicode"])}. Text in these fonts may not be read correctly; '
                 'a map can only be added where every character code\'s meaning is certain.')
    L.append('')
if pl.get('artifacted') or pl.get('left'):
    n += 1; L += [f'### {n}. Untagged paths (rules, borders, lines)', '',
                  f'{pl.get("artifacted", 0)} paths drawn outside any tag were marked as decoration'
                  + (f' ({pl["in_forms"]} of them inside shared form XObjects, each edited once)' if pl.get('in_forms') else '')
                  + ': none of them carries text, an image or a link, and none touches untagged text or images.', '']
    if pl.get('underlines'):
        L += ['Strokes directly under text, marked as decoration. An underline can carry meaning (emphasis, a sound in a romanization); '
              'if it does here, that meaning must be given another way (e.g. ActualText or a note):', '']
        L += [f'- {pg(u["page"])}: {u["count"]}' for u in by_page(pl['underlines'])[:30]] + ['']
    if pl.get('left'):
        L += ['Left as they are:', '']
        L += [f'- {c} paths: {w}' + (f' ({pgs((pl.get("left_pages") or {}).get(w, []))})' if (pl.get('left_pages') or {}).get(w) else '')
              for w, c in pl['left'].items()] + ['']
if uo.get('total'):
    n += 1; L += [f'### {n}. Untagged content ({uo["total"]} objects)', '',
                  'Drawn content that is neither tagged nor marked as decoration (a form XObject counts once). Not changed by the pipeline; '
                  'a person decides whether each is real content (tag it) or decoration (artifact it). Pages with the most:', '']
    L += [f'- {pg(p)}: ' + ', '.join(f'{v} {k}' for k, v in c.items()) for p, c in uo.get('top_pages') or []] + ['']
ad = log.get('adopted') or []
if ad:
    n += 1; L += [f'### {n}. Orphan content added to the tag tree ({sum(a["paragraphs"] for a in ad)} paragraphs)', '',
                  'Real content that was marked but in no tag, now read in page order after the last tagged block on its page. Listen through these pages:', '']
    L += [f'- {pg(a["page"])} ("{a["label"]}"): {a["runs"]} runs → {a["paragraphs"]} paragraphs, starting "{a["first"]}"' for a in by_page(ad)] + ['']
ua = log.get('untagged_artifacts') or []
if ua:
    n += 1; L += [f'### {n}. Untagged text marked as decoration ({sum(a["chars"] for a in ua)} characters)', '']
    L += [f'- {pg(a["page"])}: "{a["label"]}" ({a["chars"]} characters)' for a in by_page(ua)] + ['']
ld = log.get('link_descriptions') or []; la = log.get('link_addresses_suspect') or []
if ld or la:
    n += 1; L += [f'### {n}. Links whose description was only a URL ({len(ld)})', '',
                  'The description (what a screen reader announces) was set to the book\'s own sentence around the link, with the URL removed. '
                  'No words were added and the visible URL is unchanged. Replace any of these with a better description if needed.', '']
    if ld:
        L += ['| Page | URL | Description now |', '|---|---|---|']
        L += [f'| {pg(x["page"])} | {x["url"]} | ' + (x['description'] if x.get('description') else f'**still the URL: {x.get("why") or "(no reason recorded)"}**') + ' |' for x in by_page(ld)] + ['']
    if la:
        L += ['Link addresses that look broken (listed, not changed):', '']
        L += [f'- {pg(x["page"])}: `{x["uri"]}`: {x["why"]}' for x in by_page(la)] + ['']
if et.get('removed') or et.get('kept'):
    n += 1; rm_ = et.get('removed') or []
    L += [f'### {n}. Empty tags ({len(rm_)} removed, {len(et.get("kept") or [])} kept)', '',
          'A tag is removed only when proven empty: nothing under it holds content, it carries no Alt, ActualText, E or ID, and nothing '
          'in the file refers to it except its parent. Table cells are never removed one by one; a table goes only when every part is empty.', '']
    if rm_:
        by_t = collections.Counter(x['tag'] for x in rm_)
        L.append('- Removed: ' + ', '.join(f'{c} {t}' for t, c in by_t.most_common()))
        fl = [x for x in rm_ if x.get('from_flatten')]
        if fl: L.append(f'- {len(fl)} of them were empty parts of tables or lists the work order flattened (e.g. cells whose content had been hidden as decoration)')
        for x in by_page([t for t in et.get('tables_removed') or [] if t.get('page') is not None]):
            L.append(f'- {pg(x["page"])}: a whole empty table ({x["parts"]} parts)')
        nopg = collections.Counter(t['parts'] for t in et.get('tables_removed') or [] if t.get('page') is None)
        for parts, c in sorted(nopg.items()):         # e.g. a junk grid drawn by one shared form on many pages: no single page
            L.append(f'- {"a whole empty table" if c == 1 else f"{c} whole empty tables"} ({parts} parts{" each" if c > 1 else ""}), {NO_PAGE}')
    for h in by_page(et.get('headings') or []):
        L.append(f'- {pg(h["page"])}: an empty {h["tag"]} heading tag was removed. ' + (f'Title tagged elsewhere on the page: "{h["found"]}".' if h.get('found')
                 else '**No heading text on this page: the title may be lost. Check the page.**'))
    nt_ = by_page(et.get('notable') or [])
    if nt_: L.append('- Empty ' + ', '.join(f'{x["tag"]} {on_pg(x["page"])}' for x in nt_[:20]) + ' removed (no content under them)')
    for k in by_page(et.get('kept') or []):
        L.append(f'- **Kept, empty: {k["tag"]} {on_pg(k["page"])}**, because ' + '; '.join(k['why'][:4]) + ('…' if len(k['why']) > 4 else '') + '.')
    L.append('')
ic = log.get('index_cleanup') or {}
if ic.get('parenttree') or ic.get('idtree'):
    n += 1; L += [f'### {n}. Tag-tree index entries cleared ({len(ic.get("parenttree") or []) + len(ic.get("idtree") or [])})', '',
                  'Entries that pointed at a tag no longer in the tag tree (left by the source file, or by a tag the run removed). '
                  'Nothing reads such a tag; no page, text or reachable tag changed.', '']
    pt_ = ic.get('parenttree') or []
    if pt_:
        on_pages = [x for x in pt_ if x.get('page')]; other = [x for x in pt_ if not x.get('page')]
        by_pg = collections.defaultdict(list)
        for x in on_pages: by_pg[x['page']].append(x)
        L += [f'- ParentTree, {pg(p)}: ' + ', '.join(f'MCID {x["mcid"]} ({x["tag"]})' for x in xs) for p, xs in sorted(by_pg.items())]
        if other: L.append('- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): ' + ', '.join(f'key {x["key"]}' + (f' MCID {x["mcid"]}' if 'mcid' in x else '') + f' ({x["tag"]})' for x in other))
    if ic.get('idtree'): L.append('- IDTree: ' + ', '.join(f'"{x["id"]}" ({x["tag"]})' for x in ic['idtree']))
    L.append('')
hr = log.get('empty_holders_removed') or []; cg = log.get('captions_grouped') or []
if hr or cg:
    n += 1; L += [f'### {n}. Figure holders', '']
    L += [f'- {pg(x["page"])}: caption grouped with the {x["figures"]} figures in the holder just above it: "{x["caption"]}"' for x in cg]
    L += [f'- {pg(x["page"])}: empty figure-holder paragraph ({x["tag"]}) removed after its figure moved out (proven empty)' for x in hr]
    L.append('')
if stc and (stc['empty_tags'] or stc['paragraphs_holding_only_figures'] or stc['captions_not_grouped'] or stc['links_url_only']):
    n += 1; L += [f'### {n}. Structure left for a person', '']
    if stc['empty_tags']: L.append(f'- {stc["empty_tags"]} empty tags, e.g. ' + ', '.join(f'{e["tag"]} {on_pg(e["page"])}' for e in by_page(stc['empty_tag_examples'])[:8]))
    L += [f'- {pg(x["page"])}: a {x["tag"]} paragraph holds only {x["figures"]} figure(s)' for x in stc['paragraphs_holding_only_figures']]
    L += [f'- {pg(x["page"])}: a caption is not grouped with a figure (it sits inside {x["parent"]})' for x in stc['captions_not_grouped']]
    L += [f'- {pg(x["page"])}: a link\'s description is only its URL ({x["contents"][:80]})' for x in stc['links_url_only']]
    L.append('')
cp = log.get('captions_paired') or []
if cp:
    n += 1; L += [f'### {n}. Captions paired by position ({len(cp)})', '',
                  'Pages with several figures: each caption was tied to the figure right next to it. Check the pairs.', '']
    L += [f'- {pg(c["page"])}: "{c["caption"]}"' for c in by_page(cp)] + ['']
d_ai = wo.get('deferrals', [])
if d_ai or wo.get('notes_for_reviewer'):
    n += 1; L += [f'### {n}. Deferred by the AI', '']
    L += [f'- **{d.get("what") or "(not described)"}**: {d.get("why") or "(no reason given)"}' + (f' [{pgs([p for p in d["pages"] if isinstance(p, int)])}]' if d.get('pages') else '') for d in d_ai]
    if wo.get('notes_for_reviewer'): L += ['', f'Reviewer note from the AI: {wo["notes_for_reviewer"]}']
    L.append('')
d_ex = [d for d in log.get('deferred', []) if d.get('what') != 'Han-only runs (ja vs zh)']
if han or d_ex:
    n += 1; L += [f'### {n}. Deferred by the executor', '']
    if han: L.append(f'- **{len(han)} Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.')
    L += [f'- {d.get("what") or "(not described)"}' + (f' ({pg(d["page"])})' if 'page' in d else '') + (f': {d["why"]}' if 'why' in d else '') for d in d_ex[:40]]
    L.append('')
bad = log.get('rejected', []) + log.get('failed', []) + val.get('dropped', [])
if bad:
    n += 1; L += [f'### {n}. Decisions not applied ({len(bad)})', '', 'Rejected by validation or by the executor; nothing was half-applied.', '']
    import re as _re
    grp = collections.Counter((_re.sub(r'[\d(][\d, )]*', '#', _re.sub(r'PDF \d+(?:–\d+)?(?: \(printed [^)]*\))?', 'PDF', str(b.get('op') or b.get('where') or '(no operation recorded)'))).split(' #')[0],
                               b.get('why') or b.get('error') or '(no reason recorded)') for b in bad)
    if len(bad) > 10:
        L += ['| What | Why | Count |', '|---|---|---:|'] + [f'| {o} | {w[:120]} | {c} |' for (o, w), c in grp.most_common(15)] + ['', 'First examples:', '']
    L += [f'- {json.dumps(b, ensure_ascii=False)[:220]}' for b in bad[:30 if len(bad) > 10 else 60]]
    L.append('')
if n == 0: L.append('Nothing flagged.')

L += ['## What was changed', '', '| Change | Count |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in (log.get('applied') or {}).items()]
# A list line with no page puts the page wording at the end ("- what, page: not on this tag"), never first, and identical
# lines of that kind are written once with a count. Lines that have a page are left exactly as they are.
def _tidy_no_page(lines):
    out, head = [], f'- {NO_PAGE}'
    for l in lines:
        if l.startswith(head + ': ') or l.startswith(head + ' ('):
            rest = l[len(head):]
            label, rest = (rest[2:rest.index('):')] + ': ', rest[rest.index('):') + 3:]) if rest.startswith(' (') and '):' in rest else ('', rest[2:])
            end = '.' if rest.endswith('.') else ''
            l = f'- {label}{rest[:-1] if end else rest}, {NO_PAGE}{end}'
        if l.endswith(NO_PAGE) or l.endswith(NO_PAGE + '.'):
            if out and (out[-1] == l or out[-1].startswith(l + ' (×')):
                prev = out.pop(); n = int(prev[len(l) + 3:-1]) if prev != l else 1
                l = f'{l} (×{n + 1})'
        out.append(l)
    return out
L = _tidy_no_page(L)
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
