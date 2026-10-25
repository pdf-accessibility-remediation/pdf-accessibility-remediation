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
validation.json, workorder.json, the apply log, the verify JSON; after a REVIEW=1 run also workorder.ai.json,
review.json, review_items.json, review_decisions.json and review_pages/, whose content is in record.json) and the AUDIT_DIR
(digest and figure crops, which are copies of book pages). --keep leaves them all in place.
It only runs after a complete run, so a failed run keeps its working files for debugging.
"""
import sys, os, re, csv, json, shutil, datetime, collections
from lib.sections import line, pdfua, nolink, excerpt, to_sections, render_md, VERSION as SECTIONS_VERSION
from lib.glance import WCAG_NAMES

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
fulltext = load('fulltext.json', base=A, default={}) or {}   # the whole texts the digest shortens (local only, never sent)
vera_before = load('verapdf.json', base=A, default=None)   # veraPDF on the original, from the audit
reply = open(os.path.join(R, 'reply.txt'), encoding='utf-8').read() if os.path.exists(os.path.join(R, 'reply.txt')) else None
timing = load('timing.json', default=None)
attempts = load('attempts.json', default=[])
rv = load('review.json')                              # a person's review of the work order before it was applied (REVIEW=1)
# gaps the reviewer left open with no reason given (a hand edit without --note); an explained gap counts as handled
rv_unexplained = [g for g in (rv or {}).get('gaps') or [] if str(g.get('reason') or '').startswith('hand edit: no reason asked for')]
wo_ai = load('workorder.ai.json') if rv else None     # the AI's version, kept for comparison          # earlier paid calls in this folder whose reply couldn't be used
cost_this = (run.get('usage') or {}).get('cost_usd') or 0
cost_earlier = round(sum(a.get('cost_usd') or 0 for a in attempts), 6)
for need, name in ((wo, 'workorder.json'), (log, PDF + '.log.json'), (ver, PDF + '.verify.json')):
    if not need: sys.exit(f'{name} missing in {R}: run the whole pipeline first (nothing was deleted)')

figs = {f['obj']: f for f in digest.get('figures', [])}
elems = {e['obj']: e for e in digest.get('elements', []) + digest.get('headings', []) + digest.get('heading_candidates', [])}
lists_ = {x['obj']: x for x in digest.get('lists', [])}; tables_ = {x['obj']: x for x in digest.get('tables', [])}
src = digest.get('source', run.get('source', {}))
intake = load('intake.json', base=os.path.join(R, '_intake'))   # intake.py: OCR and auto-tagging of an untagged original
in_src = dict(src)                                     # the file the pipeline worked on (the intake result, when there is one)
if intake and (intake.get('result') or {}).get('pdf'):
    src = {**src, 'file': intake['original']['file'], 'sha256': intake['original']['sha256']}
han = log.get('han_only', [])

# ------------------------------------------------------------------ record.json
record = {
    'schema': 'record/0.1', 'written': datetime.datetime.now().isoformat(timespec='seconds'),
    'document': {'file': src.get('file'), 'output': PDF, 'sha256': src.get('sha256'), 'pages': src.get('pages'),
                 'before': digest.get('document'),
                 **({'pipeline_input': {'file': '_intake/intake.pdf', 'sha256': in_src.get('sha256')}} if src != in_src else {})},
    'intake': intake,
    'run': run, 'workorder': wo, 'validation_dropped': val.get('dropped', []),
    'apply': {'applied': log.get('applied'), 'rejected': log.get('rejected'), 'failed': log.get('failed'),
              'deferred': log.get('deferred'), 'han_only_runs': len(han), 'empty_notes_removed': log.get('empty_notes_removed', []),
              'ocr_words': log.get('ocr_words'),
              **({'offpage': log['offpage']} if any((log.get('offpage') or {}).get(k) for k in ('artifacted', 'left', 'rejected', 'already')) else {}),
              **({'list_rule': log['list_rule']} if any((log.get('list_rule') or {}).get(k) for k in ('flattened', 'kept', 'skipped')) else {}),
              **({'actual_text_checked': log['actual_text_checked']} if log.get('actual_text_checked') else {}),
              **({'font_maps': log['font_maps']} if (log.get('font_maps') or {}).get('fonts') or (log.get('font_maps') or {}).get('skipped') else {}),
              'tabs_set': log.get('tabs_set'), **({'text_rule_guard': log['text_rule_guard']} if log.get('text_rule_guard') else {})},
    'verify': {k: v for k, v in ver.items() if k != 'verapdf'},
    'verapdf': {'before': vera_before, 'after': ver.get('verapdf')}, 'timing_seconds': timing, 'raw_reply': reply, 'environment': log.get('environment'),
    'earlier_attempts': attempts, 'cost_total_usd': round(cost_this + cost_earlier, 6),
    **({'review': {'workorder': rv}} if rv else {}),
    **({'workorder_ai': wo_ai} if rv and wo_ai is not None and rv.get('changes') else {}),
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
try:                                              # a spread (two printed pages per PDF page): intake's "210–211" where the PDF has no label
    for _p, _l in ((json.load(open(os.path.join(R, '_intake', 'intake.json'))).get('spreads') or {}).get('printed') or {}).items():
        if PLAB.get(int(_p), str(_p)) == str(_p): PLAB[int(_p)] = _l
except Exception: pass
NO_PAGE = 'page: not on this tag'                 # a missing page is never printed as "unknown" (the record keeps null)
def pg(n):
    try: n = int(n)
    except (TypeError, ValueError): return NO_PAGE
    lab = PLAB.get(n, '')
    return f'PDF {n}' + (f' (printed {lab})' if lab and lab != str(n) else '')
def pgr(a, b):
    if a == b: return pg(a)
    la, lb = PLAB.get(int(a), ''), PLAB.get(int(b), '')
    return f'PDF {a}–{b}' + ((f' (printed {la} to {lb})' if '–' in la + lb else f' (printed {la}–{lb})') if la and lb and (la != str(a) or lb != str(b)) else '')
def pgs(ns): return ', '.join([pg(n) for n in sorted({n for n in ns if n is not None}, key=int)] + ([NO_PAGE] if any(n is None for n in ns) else []))
def nc(v): return 'not counted' if v is None else v      # a count the verify file left empty
def xl(build, **kw):
    """A line built by build(X), where X(text) is an excerpt of book text (about 100 characters, at a word boundary);
    each excerpt's whole text goes with the line, for review.html's \"show full text\"."""
    f = []; return line(build(lambda t: excerpt(t, f)), full=f, **kw)
def page_ranges(ns):
    """Every page, as collapsed ranges where they exist (\"PDF 12–40 (printed 3–31), PDF 52\")."""
    ps = sorted({int(n) for n in ns if n is not None}); runs = []
    for n in ps:
        if runs and n == runs[-1][1] + 1: runs[-1][1] = n
        else: runs.append([n, n])
    return ', '.join(pgr(a, b) for a, b in runs)
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
# veraPDF, WCAG 2.2 machine profile: before (original) and after (result). Only rules in WCAG scope count toward WCAG;
# every failed rule (PDF/UA-only too) is compared: fixed, still failing, newly failing, or failing more often.
v_before, v_after = vera_before, ver.get('verapdf')
def v_ran(v): return bool(v) and 'not_run' not in v
def v_wcag(v): return {r['id']: r for r in v['rules'] if r['scope'] == 'wcag'} if v_ran(v) else {}
def v_all(v): return {r['id']: r for r in v['rules']} if v_ran(v) else {}
def v_state(v, when):
    if v is None: return f'{when}: not recorded (made before veraPDF was added to the pipeline)'
    if 'not_run' in v: return f'{when}: {v["not_run"]}'
    t_ = v['totals']; return f'{when}: {t_["wcag_failed_rules"]} WCAG rule{"" if t_["wcag_failed_rules"] == 1 else "s"} failed ({t_["wcag_failed_checks"]} checks)'
v_both = v_ran(v_before) and v_ran(v_after)
VB, VA = v_all(v_before), v_all(v_after)
v_fixed = [k for k in VB if k not in VA] if v_both else []
v_new = [k for k in VA if k not in VB] if v_both else []
v_worse = [k for k in VA if k in VB and VA[k]['failed'] > VB[k]['failed']] if v_both else []
v_still = [k for k in VA if k in VB] if v_both else []
def v_status(k):
    return ('**newly failing**' if k in v_new else '**failing more often**' if k in v_worse else 'still failing' if k in v_still
            else 'fixed' if k in v_fixed else '')
wc = ver.get('wcag')
ow = log.get('ocr_words') or {}; ow_forms = ow.get('by_form') or []; ow_missing = [x for x in ow_forms if not x.get('found')]
ow_run = run.get('ocr_words') or {}
def intake_rows():
    tt = intake.get('text_test') or {}; o = intake.get('ocr') or {}; fl = intake.get('flags') or []
    ns = len([r for r in tt.get('pages', []) if 'cer' in r])
    v, med = tt.get('verdict'), tt.get('median_cer')
    def fpages(what): return sorted({p for f in fl if f['what'] == what for p in f.get('pages') or []})
    rows = [('Text layer agrees with OCR of the page (checklist 1.2)',
             ok(v in ('usable', 'not tested')),
             {'usable': f'usable: median character error {med:.1%} on {ns} sample page{"s" if ns != 1 else ""}' if med is not None else 'usable',
              'not tested': 'no page had a text layer: every page was OCR\'d',
              'doubtful': f'doubtful: median character error {med:.1%} (5–15%): compare a few pages by eye' if med is not None else 'doubtful',
              'unusable': f'unusable (median character error {med:.1%}): FORCE_OCR=1 replaced it with OCR text over page images' if med is not None else 'unusable',
              'not scored': 'not scored (too little text, or mostly CJK, on the sample pages)'}.get(v, v or 'not tested'))]
    ol = intake.get('ocr_layer_test')
    if ol:                                             # an existing OCR layer on scanned pages, read again by a different model
        d, med_o = ol.get('diacritics'), ol.get('median_cer')
        bad = sorted(r['page'] for r in ol.get('pages') or [] if r.get('cer') is not None and r['cer'] > 0.05)
        txt = ({'usable': 'usable', 'doubtful': 'doubtful', 'unusable': 'unusable'}.get(ol.get('verdict'), 'not checked: no sample page could be scored')
               + (f': median character error {med_o:.1%} on {ol.get("scored")} sample pages' if med_o is not None else '')
               + (f'; pages over 5%: {pgs(bad)}' if bad and ol.get('verdict') != 'usable' else '')
               + (f'; diacritics missing from the layer ({d["marked_vowels_ocr"]} marked vowels read, {d["marked_vowels_layer"]} in the layer: '
                  f'{pgs(d.get("pages") or [])})' if d else ''))
        rows.append(('Existing OCR layer agrees with a fresh OCR reading (checklist 1.2, 3.1)', ok(ol.get('verdict') == 'usable' and not d), txt))
    sp = intake.get('spreads')
    if sp:                                             # two printed pages per PDF page: read half by half after auto-tagging
        rr = ((intake.get('checks') or {}).get('spreads_reordered') or {}).get('pages') or {}
        moved = [int(p) for p, v in rr.items() if v.get('switches_before') != v.get('switches_after')]
        rows.append(('One printed page per PDF page (checklist 4.1, 6.1–6.4)', ok(False),
                     f'{len(sp["pages"])} PDF pages hold two printed pages ({pgs(sp["pages"])}); tag tree reordered half by half, '
                     f'{sp.get("order", "left half first")}, on {len(moved)} of them; the rest left in the tagger\'s order'))
    runs = fpages('Words run together')
    if o.get('mode') == 'force':
        rows.append(('Words separated in the text layer (checklist 3.4)', 'OK', 'the original text layer was replaced by OCR text'))
    else:
        rows.append(('Words separated in the text layer (checklist 3.4)', ok(not runs),
                     'yes on every sample page' if not runs else 'fewer word breaks than the printed page on ' + pgs(runs)))
    if o:
        n = len(o.get('pages_with_ocr_text') or [])
        issues = [x for x in ('Low-resolution scans', 'OCR language', 'OCR characters not mapped', 'OCR', 'CJK OCR: needs a person',
                              'OCR text looks like junk', 'Empty text objects left') if any(f['what'] == x for f in fl)]
        rows.append(('OCR text added where pages had none (checklist 3.1)', ok(not issues),
                     (f'{n} page{"s" if n != 1 else ""} ({o.get("mode")} mode, Tesseract {intake["tools"].get("tesseract")}, '
                      f'{(intake.get("language") or {}).get("ocr_lang")})' if n else 'no image-only page held text')
                     + ('; ' + '; '.join(issues).lower() + ' (see "Intake")' if issues else '')))
        if n:
            v = (intake.get('review') or {}).get('ocr_text_approved')
            if isinstance(v, dict):                    # recorded with review_ocr.py
                who = f'{v.get("reviewer")} on {v.get("date")}' + (f' (pages {v["pages"]})' if v.get('pages') else '')
                rows.append(('OCR text reviewed by a person', ok(v.get('verdict') == 'approved'),
                             f'{"approved" if v.get("verdict") == "approved" else "not approved"} by {who}: {v.get("reason")}'))
            else: rows.append(('OCR text reviewed by a person', ok(False), f'machine OCR on {n} page{"s" if n != 1 else ""}: not yet reviewed '
                               '(checklist rule 2; record a verdict with review_ocr.py)'))
    cov = (intake.get('checks') or {}).get('coverage') or {}
    rows.append(('Auto-tagging kept every page as it was', 'OK', f'appearance and text unchanged on all {intake["original"].get("pages")} pages'
                 + (' (OCR\'d pages: text added)' if o else '')))
    return rows
ofp = log.get('offpage') or {}
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
    *([('OCR words: every printed spelling attached', ok(not ow_missing and not ow_run.get('not_sent') and not digest.get('ocr_words_not_sent')),
        f'{len(ow_forms)} misread forms given their printed spelling in {sum(x.get("found") or 0 for x in ow_forms)} places'
        + (f' · {len(ow_missing)} not found in the page text' if ow_missing else '')
        + (f' · {ow_run["not_sent"] + digest.get("ocr_words_not_sent", 0)} suspect forms not read by the AI' if ow_run.get('not_sent') or digest.get('ocr_words_not_sent') else ''))]
      if ow_forms or digest.get('ocr_words') else []),
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
     (f'{idx["dangling"]} dangling entries' + (' (' + ', '.join(f'{d["index"]} ' + (f'key {d["key"]}' if 'key' in d else f'"{d.get("id")}"') for d in idx['dangling_examples']) + ')' if idx['dangling'] else '')
      + f' · {idx["stale_entries"]} stale entries (marked content no longer drawn)') if idx else 'not checked'),
    ('No empty tables', ok(stc is not None and not stc.get('empty_tables')),
     (pgs([x['page'] for x in stc['empty_tables']]) if stc.get('empty_tables') else 'none') if stc else 'not checked'),
    ('No empty tags', ok(stc is not None and stc['empty_tags'] == 0),
     f'{stc["empty_tags"]} empty tag' + ('s' if stc['empty_tags'] != 1 else '') + (' (' + pgs([e['page'] for e in stc['empty_tag_examples']]) + (' …' if stc['empty_tags'] > len(stc['empty_tag_examples']) else '') + ')' if stc['empty_tags'] else '') if stc else 'not checked'),
    ('No paragraph holding only figures', ok(stc is not None and not stc['paragraphs_holding_only_figures']),
     (', '.join(f'{pg(x["page"])} ({x["figures"]} figures in {x["tag"]})' for x in by_page(stc['paragraphs_holding_only_figures'])) or 'none') if stc else 'not checked'),
    ('Every caption grouped with its figure', ok(stc is not None and not stc['captions_not_grouped']),
     (', '.join(f'{pg(x["page"])} (caption inside {x["parent"]})' for x in by_page(stc['captions_not_grouped'])) or 'all grouped') if stc else 'not checked'),
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
    *([('Work order reviewed by a person before it was applied',
        ok(not rv.get('dropped_on_check') and not (rv.get('counts') or {}).get('accepted_unreviewed') and not rv_unexplained),
        f'{rv["reviewer"]} on {rv["date"]} · {len(rv.get("changes") or [])} changes'
        + (' · ' + ' · '.join(f'{v} {k.replace("_", " ")}' for k, v in rv['counts'].items() if v) if rv.get('counts') else '')
        + (f' · {len(rv["dropped_on_check"])} edits not accepted by the check' if rv.get('dropped_on_check') else '')
        + (f' · {len(rv["gaps"])} gap{"s" if len(rv["gaps"]) != 1 else ""} left open'
           + (f', {len(rv_unexplained)} without a reason' if rv_unexplained else ', with a reason' if len(rv['gaps']) == 1 else ', with reasons') if rv.get('gaps') else '')
        + ' (see "Work order reviewed by a person")')] if rv else []),
    ('Model reply held one work order', ok(not rb),
     f'{rb["count"]} work orders; the last one (the model\'s final answer) was used, as written (see "The model\'s reply held {rb["count"]} work orders")' if rb else 'one'),
    ('Executor applied every decision', ok(not log.get('rejected') and not log.get('failed')),
     f'{len(log.get("rejected") or [])} rejected · {len(log.get("failed") or [])} failed (listed under "Decisions not applied")'),
    ('Nothing deferred by the executor',
     ok(not log.get('deferred')) if not any(d.get('scope') == 'pdfua' for d in log.get('deferred') or []) else    # review.html: WCAG deferrals only
     line(pdfua(ok(not log.get('deferred')), ok(not [d for d in log['deferred'] if d.get('scope') != 'pdfua']))),
     f'{len(log.get("deferred") or [])} deferred (listed under "Deferred by the executor")'
     if not any(d.get('scope') == 'pdfua' for d in log.get('deferred') or []) else
     line(pdfua(f'{len(log.get("deferred") or [])} deferred (listed under "Deferred by the executor")',
                f'{sum(1 for d in log["deferred"] if d.get("scope") != "pdfua")} deferred' + (' (listed under "Deferred by the executor")' if any(d.get('scope') != 'pdfua' for d in log['deferred']) else '')))),
    ('Fonts: every glyph defined (no .notdef)', ok(not fo.get('only_notdef')),
     '; '.join(f'{x["font"]}: {x["glyph_references"]} undefined glyph references on {x["pages"]} pages' for x in fo.get('only_notdef') or []) or 'none found'),
    ('Fonts: every embedded font program could be read', ok(not fo.get('unreadable')),
     ('; '.join(f'{x["font"]} ({x["pages"]} pages)' for x in fo.get('unreadable')) + ': not checked, so their glyphs may be undefined') if fo.get('unreadable') else 'all read'),
    ('Fonts: embedded and mapped to Unicode', ok(not fo.get('not_embedded') and not fo.get('no_ToUnicode')),
     f'{len(fo.get("not_embedded") or [])} not embedded · {len(fo.get("no_ToUnicode") or [])} without ToUnicode'
     + (f' ({len(fo["no_ToUnicode_not_needed"])} more have none and need none: standard encoding, non-symbolic)' if fo.get('no_ToUnicode_not_needed') else '')),
    *(intake_rows() if intake and intake.get('status') == 'done' else []),
    *([('Text outside the visible page area marked as decoration', ok(not ofp.get('left') and not ofp.get('rejected') and not ver.get('offpage_chars_read_aloud')),
        f'{sum(a["chars"] for a in ofp.get("artifacted") or [])} characters on {len(ofp.get("artifacted") or [])} pages marked as decoration'
        + (f' · {len(ofp["left"])} left as they are' if ofp.get('left') else '') + (f' · {len(ofp["rejected"])} pages not changed' if ofp.get('rejected') else '')
        + f' · {nc(ver.get("offpage_chars_read_aloud"))} characters outside the page still read aloud' + ' (see "Text outside the visible page area")')]
      if ofp.get('artifacted') or ofp.get('left') or ofp.get('rejected') or ver.get('offpage_chars_read_aloud') else []),
    ('Tab order follows the tag structure on pages with links or other annotations', ok((ver.get('tabs_missing') or {}).get('count') == 0),
     f'{nc((ver.get("tabs_missing") or {}).get("count"))} of {nc((ver.get("tabs_missing") or {}).get("pages_with_annotations"))} pages with annotations lack /Tabs /S'
     + (f' (log: {log["tabs_set"]} set by this run)' if log.get('tabs_set') else '')),
    ('Characters with no Unicode value (checklist 3.6)', ok((ver.get('no_unicode_chars') or {}).get('count') == 0),
     f'{nc((ver.get("no_unicode_chars") or {}).get("count"))} read-aloud characters with no Unicode value'
     + (f' on {pgs(ver["no_unicode_chars"]["pages"])}' if (ver.get('no_unicode_chars') or {}).get('count') else '')),
    ('Private-use characters (checklist 3.6)', ok((ver.get('private_use_chars') or {}).get('count') == 0),
     f'{nc((ver.get("private_use_chars") or {}).get("count"))} read-aloud characters with private-use codes'
     + (' (' + ', '.join(f'{r["range"]}: {r["count"]}' for r in ver['private_use_chars']['ranges']) + f') on {len(ver["private_use_chars"]["pages"])} page{"" if len(ver["private_use_chars"]["pages"]) == 1 else "s"}'
        if (ver.get('private_use_chars') or {}).get('count') else '')),
    ('Title and language set', ok(bool(doc.get('title')) and bool(doc.get('lang'))), (f'"{doc["title"]}"' if doc.get('title') else 'title not set') + ' · ' + (doc.get('lang') or 'language not set')),
    ('veraPDF WCAG 2.2 (machine): no WCAG failures', ok(v_ran(v_after) and not v_wcag(v_after)),
     line(v_state(v_before, 'before') + ' → ' + v_state(v_after, 'after'),
          pdfua(f' · {v_after["totals"]["ua_only_failed_rules"]} PDF/UA-only rules not counted' if v_ran(v_after) and v_after['totals']['ua_only_failed_rules'] else ''),
          ' (listed under "veraPDF")' if v_wcag(v_before) or v_wcag(v_after) else '')),
    ('veraPDF: no rule newly failing or failing more often', ok(v_both and not v_new and not v_worse),
     (f'{len(v_fixed)} fixed · {len(v_still)} still failing · {len(v_new)} newly failing' + (f' · {len(v_worse)} failing more often' if v_worse else '')
      + (' (' + ', '.join(v_new + v_worse) + ')' if v_new or v_worse else '')) if v_both else 'not compared: veraPDF did not run on both files'),
    ('Alt text: none like a file name or repeated on many figures (1.1.1)', ok(wc is not None and not wc['alt_text']['flagged']),
     f'{wc["alt_text"]["flagged"]} of {wc["alt_text"]["figures"]} figures flagged' if wc else 'not checked'),
    ('Tables: every table has header cells (1.3.1)', ok(wc is not None and not wc['tables_without_header']),
     (pgs([x['page'] for x in wc['tables_without_header']]) or 'none without') if wc else 'not checked'),
    ('Reading order: no page jumps back up a column (1.3.2)', ok(wc is not None and not wc['reading_order']['flagged_count']),
     f'{wc["reading_order"]["flagged_count"]} of {wc["reading_order"]["pages_checked"]} pages flagged' if wc else 'not checked'),
    ('Title is not a file name or placeholder (2.4.2)', ok(wc is not None and not wc['title_generic']),
     (f'"{doc["title"]}"' if doc.get('title') else 'title not set') if wc else 'not checked'),
    ('Link text: none like "click here" (2.4.4)', ok(wc is not None and not wc['links_generic']),
     f'{len(wc["links_generic"])} generic' if wc else 'not checked'),
    ('Headings: none empty, very long or repeated in a row (2.4.6)', ok(wc is not None and not any(wc['headings'][k] for k in ('empty', 'long', 'repeated'))),
     ' · '.join(f'{len(wc["headings"][k])} {k}' for k in ('empty', 'long', 'repeated')) if wc else 'not checked'),
]
u = run.get('usage') or {}
L = [f'# Remediation review: {src.get("file") or "file name not recorded"}', '', f'Result: `{PDF}`', '',
     f'{nc(src.get("pages"))} pages · run {run.get("started") or "start time not recorded"} · '
     + (f'model `{run["model"]}`' if run.get('model') else 'model not recorded') + ' · '
     + (f'prompt `{run["prompt_file"]}` ({run.get("prompt_sha256") or "hash not recorded"})' if run.get('prompt_file') else 'prompt not recorded') + ' · '
     + (f'cost ${u["cost_usd"]}' if u.get('cost_usd') is not None else 'cost: call did not finish') + ' · '
     + (f'{u["prompt_tokens"]} in / {u["completion_tokens"]} out tokens' if u.get('prompt_tokens') is not None and u.get('completion_tokens') is not None else 'tokens: call did not finish')
     + (f' · plus ${cost_earlier:.3f} for {len(attempts)} earlier call(s) whose reply was cut off or unusable (total ${cost_this + cost_earlier:.3f})' if attempts else ''), '',
     *([f'Intake: {intake.get("summary")}' + (f' · tagged by OpenDataLoader {intake["tools"].get("opendataloader_pdf")}' if intake.get('status') == 'done' else '')
        + (' · the pipeline worked on `_intake/intake.pdf`; the original was not changed' if (intake.get('result') or {}).get('pdf') else ''), ''] if intake else []),
     *([('Libraries: ' + ' · '.join(f'{k} {v}' for k, v in log['environment'].items() if k != 'executable')), ''] if log.get('environment') else []),
     *([('Time: ' + ' · '.join(f'{k.split(" ", 1)[1].split(" (")[0]} {v}s' for k, v in timing.items()) + f' · total {round(sum(timing.values()), 1)}s'), ''] if timing else []),
     'Automated checks are evidence, not legal sign-off. Items marked **CHECK**, and everything under "For a person to check", need a human.', '',
     '## Automated checks', '', '| Check | Result | Detail |', '|---|---|---|']
def _parts(v): return [tuple(x) for x in v.parts] if getattr(v, 'parts', None) else [v]
L += [line(f'| {a} | ', *_parts(b), ' | ', *_parts(c), ' |', key=f'check:{a}') for a, b, c in checks]

L += ['', '## For a person to check', '']
n = 0
if intake and intake.get('status') == 'done':
    n += 1; o = intake.get('ocr') or {}; tt = intake.get('text_test') or {}
    L += [f'### {n}. Intake: OCR and auto-tagging', '',
          'The original had no tags. Local tools prepared it before the model saw it; no model wrote or changed any text. '
          f'Pages: {", ".join(f"{v} {k}" for k, v in (intake.get("triage") or {}).get("counts", {}).items())}.', '']
    if tt.get('pages'):
        L += ['Text-layer test (checklist 1.2): each sample page was OCR\'d at 300 dpi and compared with its text layer.', '',
              '| Page | Character error | Verdict |', '|---|---:|---|']
        L += [f'| {pg(r["page"])} | ' + (f'{r["cer"]:.1%}' if 'cer' in r else '—') + f' | {r["verdict"]}'
              + (f': {r["reason"]}' if r.get('reason') else '')
              + (f' (replaced by {pg(r["replaced_by"])})' if r.get('replaced_by') is not None else '') + ' |' for r in tt['pages']] + ['']
    if o.get('pages_with_ocr_text'):
        L += [line(f'- OCR text added ({o.get("mode")} mode) on ' + pgs(o['pages_with_ocr_text'])
              + '. It is machine output: compare it with the page image before it ships.', key='intake:ocr', pages=o['pages_with_ocr_text'])]
    for r in ((intake.get('checks') or {}).get('after_autotag') or {}).get('reordered') or []:
        L += [f'- Text reordered by auto-tagging on {pg(r["page"])} (same characters, different extraction order; the tag tree sets the reading order). '
              'Moved: ' + '; '.join(f'"{x}"' for x in r['moved'])]
    if o.get('scan_images_marked_decoration'):
        L += ['- The whole-page scan image on ' + pgs(o['scan_images_marked_decoration']) + ' is marked as decoration: it is the page itself, not a figure (checklist 5.1).']
    for f in intake.get('flags') or []:
        L.append(line(f'- **{f["what"]}**: ', nolink(f['why']), f' ({pgs(f["pages"])})' if f.get('pages') else '', pages=f.get('pages')))   # why: general text
    L.append('')
if rv:
    def _v(x): return json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else f'"{x}"' if isinstance(x, str) else str(x)
    n += 1; L += [f'### {n}. Work order reviewed by a person', '',
                  f'{rv["reviewer"]} reviewed the AI\'s work order on {rv["date"]}, before it was applied ({rv.get("method")}). '
                  'The result is what was applied; the AI\'s version is in `record.json` (`workorder_ai`).', '']
    if rv.get('changes'):
        L += ['| Decision | Change | AI | Person |', '|---|---|---|---|']
        L += [f'| {c["where"]}' + (f' `{c["id"]}`' if c.get('id') else '') + f' | {c["change"]} | '
              + (_v(c['ai']) if 'ai' in c else '—') + ' | ' + (_v(c['person']) if 'person' in c else '—') + ' |' for c in rv['changes']]
    else: L.append('No changes: every decision was kept as the AI wrote it.')
    if (rv.get('counts') or {}).get('accepted_unreviewed'):
        L += ['', f'**{rv["counts"]["accepted_unreviewed"]} decisions were accepted without being reviewed.**']
    if rv.get('dropped_on_check'):
        L += ['', 'Edits not accepted by the check (not applied):', ''] + [f'- {d["where"]}: {d["why"]} ({_v(d["item"])})' for d in rv['dropped_on_check']]
    if rv.get('gaps'):
        L += ['', 'Gaps the reviewer left open, with their reason:', ''] + [f'- {g["what"]} Reason: {g["reason"]}' for g in rv['gaps']]
    if rv.get('notes') or rv.get('note'):
        L += ['', 'Reviewer notes:', ''] + ([f'- {rv["note"]}'] if rv.get('note') else []) + [f'- `{k}`: {t}' for k, t in (rv.get('notes') or {}).items()]
    L.append('')
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
        L.append(f'| {pg(f.get("page"))} | {f.get("alt") or "—"} | {a["alt"]} |')
    L.append('')
kept = [f for o, f in figs.items() if o not in {a['obj'] for a in alts}
        and o not in {e['obj'] for e in wo.get('artifacts', {}).get('elements', [])}]
if kept:
    n += 1; L += [f'### {n}. Figures that kept their existing alt text ({len(kept)})', '', 'Not changed by the AI. Check they are adequate.', '',
                  '| Page | Alt text |', '|---|---|']
    L += [f'| {pg(f.get("page"))} | {f.get("alt") or "—"} |' for f in by_page(kept)]
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
                  '| Page | Text | Before | After |', '|---|---|---|---|']
    for r in by_page(rt, key=lambda r: elems.get(r['obj'], {}).get('page')):
        e = elems.get(r['obj'], {})
        t_ = (fulltext.get('elements') or {}).get(r['obj']) or e.get('text')
        L.append(xl(lambda X: f'| {pg(e.get("page"))} | {X(t_) if t_ else "(no text)"} | {e.get("level") or e.get("style") or "(no style)"} | {r["type"]} |'))
    L.append('')
fl = wo.get('flatten', [])
kept_tables = [t for o, t in tables_.items() if o not in {f['obj'] for f in fl}]
if fl or kept_tables:
    n += 1; L += [f'### {n}. Lists and tables', '']
    for f in fl:
        x = lists_.get(f['obj']) or tables_.get(f['obj']) or {}
        kind = 'list' if f['obj'] in lists_ else 'table'
        t_ = " / ".join((fulltext.get('lists' if kind == 'list' else 'tables') or {}).get(f['obj']) or x.get("first_items") or x.get("first_rows") or [])
        L.append(xl(lambda X: f'- Flattened {kind} {on_pg(x.get("page"))}: "{X(t_)}" ({f.get("why", "")})'))
    for x in log.get('tables') or []:
        L.append(f'- Header cells marked by the AI {on_pg(x.get("page"))}: {x["header_rows"]} header row(s), {x["header_cols"]} header column(s), '
                 f'{x["cells_to_TH"]} cells changed to header cells. Check they are the real headers.')
    if kept_tables:
        L += ['', f'Tables kept as tables ({len(kept_tables)}): check header cells and reading order.', '']
        L += [xl(lambda X: f'- {pg(t.get("page"))}: {t["rows"]} rows × {t["cols"]} columns, {t["header_cells"]} header cells. '
                 f'"{X(((fulltext.get("tables") or {}).get(t["obj"]) or t.get("first_rows") or [""])[0])}"') for t in by_page(kept_tables)]
    L.append('')
tq = digest.get('text_quality', {})
if tq.get('producer_says_ocr') or (tq.get('pages_with_full_page_image', 0) > 0.5 * (src.get('pages') or 1)):
    n += 1; L += [f'### {n}. Scanned book: the text layer comes from OCR', '',
                  f'{nc(tq.get("pages_with_full_page_image"))} of {nc(src.get("pages"))} pages are full-page images. Screen readers read the OCR text, '
                  f'which may contain recognition errors (suspect-token rate {nc(tq.get("suspect_tokens_per_1000"))} per 1,000). '
                  f'Spot-check these pages against the scan: {pgs(tq.get("worst_pages", []))}. '
                  + ('Misread words the AI could read from the scan are listed under "OCR words given their printed spelling"; other errors stay. '
                     if ow_forms else '') + 'Corrections to the text itself are an editorial decision.', '']
dw = {w['text']: w for w in digest.get('ocr_words') or []}
if ow_forms or digest.get('ocr_words'):
    n += 1; checked = ow_run.get('sent', len(dw))
    L += [f'### {n}. OCR words given their printed spelling ({len(ow_forms)} forms, {sum(x.get("found") or 0 for x in ow_forms)} places)', '',
          'The OCR misread these words, mostly letters with diacritics (ā or ū read as "ii"). The AI read each word from a crop of the scan. '
          'Screen readers now speak the printed spelling, and copying gives it (ActualText); the OCR text underneath is unchanged, '
          'so a text search still finds the OCR spelling. Apps that ignore ActualText (Preview and other PDFKit readers, some checkers) '
          'still show the OCR spelling. Check each reading against the scan on its first page.', '']
    if ow_forms:
        L += ['| OCR text | Printed (AI\'s reading) | Places | First pages |', '|---|---|---:|---|']
        L += [f'| {x["text"]} | {x["reads"]} | ' + (str(x['found']) if x.get('found') else '**not found**')
              + f' | {pgs(dw.get(x["text"], {}).get("pages") or [])} |' for x in sorted(ow_forms, key=lambda x: -(x.get('found') or 0))]
        L.append('')
    L.append(line(f'- {checked} suspect forms were checked by the AI; {max(0, checked - len(ow_forms))} were judged correct as the OCR read them, or unreadable '
             '(e.g. "Hawaii"), and left alone.', entry=False))
    if ow_missing: L.append(line(f'- **{len(ow_missing)} forms with a reading were not found in the page text** (split across text operators, or drawn inside a form): '
                            + ', '.join(x['text'] for x in ow_missing) + '. A person checks these.', entry=False))
    unread = (ow_run.get('not_sent') or 0) + (digest.get('ocr_words_not_sent') or 0)
    if unread: L.append(line(f'- **{unread} suspect forms were not read by the AI** (over the image limit, or past the audit\'s cap). A person checks them against the scan.', entry=False))
    L.append('')
uc = digest.get('unowned_content', [])
if uc:
    n += 1; tot = digest.get('unowned_content_totals', {})
    L += [f'### {n}. Text a screen reader could not reach (before this run)', '',
          f'{len(uc)} pages had text outside the tag tree: {tot.get("orphan", 0)} orphan runs (marked, but no tag owns them) and '
          f'{tot.get("untagged", 0)} untagged runs. Running heads and page numbers among them can be hidden as decoration; real content '
          f'must be added to the tag tree by a person. After this run: {nc(ver.get("untagged_chars"))} untagged characters, '
          f'{nc(t.get("content_mcids_not_in_tree"))} orphan runs remain.', '', line('Pages: ' + page_ranges([x['page'] if isinstance(x, dict) else int(x.split('|')[0]) for x in uc]),
               pages=[x['page'] if isinstance(x, dict) else int(x.split('|')[0]) for x in uc]), '']
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
        L += [line(f'- **{x["font"]}**: its embedded font program holds only the `.notdef` glyph, so every one of its {x["glyph_references"]} '
              f'glyph references ({x["text_operators"]} text operators on {x["pages"]} pages, from {pgs(x["first_pages"])} …) '
              f'is an undefined character', pdfua(' (ISO 14289-1 7.21.8, PDF/UA)'), '. '
              + ('It has a ToUnicode map, so the text is extracted and read aloud; adding or changing a map cannot define a glyph, '
                 'so no map was added. ' if x.get('has_ToUnicode') else 'It has no ToUnicode map either. ')
              + ('Its text is invisible (render mode 3): it is the hidden OCR layer laid over words recognized in a scanned image. ' if hidden else '')
              + 'A person must regenerate that text with a font that contains the glyphs (re-run OCR, or replace the font in Acrobat '
                'or another PDF tool), then re-check with PAC. Both change the file, so they are outside this pipeline.', pages=x['first_pages'])]
    if fo.get('not_embedded'):
        L.append(line(f'- **Not embedded** ({len(fo["not_embedded"])}): {", ".join(fo["not_embedded"])}. ', pdfua('PDF/UA requires embedded fonts (7.21.4.1); a', 'A'),
                      ' person must embed them with a PDF tool (e.g. Acrobat Preflight) and check that no page changes.', key='fonts:not_embedded'))
    if fo.get('no_ToUnicode'):
        L.append(line(f'- **No ToUnicode map** ({len(fo["no_ToUnicode"])}): {", ".join(fo["no_ToUnicode"])}. Text in these fonts may not be read correctly; '
                 'a map can only be added where every character code\'s meaning is certain.', key='fonts:no_tounicode'))
    L.append('')
if pl.get('artifacted') or pl.get('left'):
    n += 1; L += [f'### {n}. Untagged paths (rules, borders, lines)', '',
                  f'{pl.get("artifacted", 0)} paths drawn outside any tag were marked as decoration'
                  + (f' ({pl["in_forms"]} of them inside shared form XObjects, each edited once)' if pl.get('in_forms') else '')
                  + ': none of them carries text, an image or a link, and none touches untagged text or images.', '']
    if pl.get('underlines'):
        L += ['Strokes directly under text, marked as decoration. An underline can carry meaning (emphasis, a sound in a romanization); '
              'if it does here, that meaning must be given another way (e.g. ActualText or a note):', '']
        L += [f'- {pg(u["page"])}: {u["count"]}' for u in by_page(pl['underlines'])] + ['']
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
    L += [xl(lambda X: f'- {pg(a["page"])} ("{a["label"]}"): {a["runs"]} runs → {a["paragraphs"]} paragraphs, starting "{X(a["first"])}"') for a in by_page(ad)] + ['']
if ofp.get('artifacted') or ofp.get('left') or ofp.get('rejected') or ofp.get('already'):
    art = ofp.get('artifacted') or []
    n += 1; L += [f'### {n}. Text outside the visible page area ({sum(a["chars"] for a in art)} characters marked as decoration)', '',
                  'Text that lies entirely outside the page\'s visible area (CropBox) is seen by nobody on screen or in print but is read '
                  'by a screen reader, so it is marked as decoration (artifact). No text or drawing was changed.', '']
    small = [a for a in art if len(a.get('lines') or []) <= 1]
    if small:
        ex = next((a['lines'][0] for a in small if a.get('lines')), '')
        L += [xl(lambda X: f'- {len(small)} pages with a short off-page line (a printer\'s slug or similar), e.g. "{X(ex)}": {pgs([a["page"] for a in small])}')]
    for a in by_page([a for a in art if len(a.get('lines') or []) > 1]):
        L += [f'- {pg(a["page"])}: {a["chars"]} characters, for example a cover spread cropped to the front cover. '
              'Whoever writes this page\'s alt text should know what the hidden part says:', '']
        L += [xl(lambda X: f'  > {X(x)}') for x in a['lines']] + ['']
    for a in by_page(ofp.get('already') or []):
        L += [f'- {pg(a["page"])}: {a["chars"]} characters outside the visible area were already marked as decoration (by the '
              'auto-tagger or the source file), for example a cover spread cropped to the front cover. Whoever writes this '
              'page\'s alt text should know what the hidden part says:', '']
        L += [xl(lambda X: f'  > {X(x)}') for x in a['lines']] + ['']
    for x in by_page(ofp.get('left') or []):
        L.append(xl(lambda X: f'- **Left as it is** on {pg(x["page"])}: {x["why"]}: "{X(x["text"])}"'))
    for x in by_page(ofp.get('rejected') or []):
        L.append(f'- **Page not changed** {pg(x["page"])}: {x["why"]}')
    L.append('')
atc = log.get('actual_text_checked') or {}
if atc.get('accepted_different') or atc.get('rejected'):
    n += 1; L += [f'### {n}. Spoken text (ActualText) checked against the print ({len(atc.get("accepted_different") or [])} accepted with differences, '
                  f'{len(atc.get("rejected") or [])} rejected)', '',
                  'A spoken text may differ from the printed characters only in spacing, letter case and line-end hyphens (sponsor rule 1). '
                  'Accepted ones that differ are listed so a person can listen to them; rejected ones added or changed words or punctuation.', '']
    L += [xl(lambda X: f'- Accepted, {pg(x["page"])}: printed "{X(x["printed"])}" → spoken "{x["spoken"]}"') for x in by_page(atc.get('accepted_different') or [])]
    L += [xl(lambda X: f'- **Rejected**, {pg(x["page"])}: printed "{X(x["printed"])}" → spoken "{x["spoken"]}"') for x in by_page(atc.get('rejected') or [])] + ['']
tg = log.get('text_rule_guard') or []
if tg:
    n += 1; L += [f'### {n}. Text a running-head or page-number rule matched but left visible ({len(tg)})', '',
                  'A rule for the top or bottom band hides a run only when everything else on that line is matched too. These runs matched '
                  'the rule but share their line with other text (for example a note number in the first line of body text), so they were '
                  'left as they are.', '']
    L += [xl(lambda X: f'- {pg(x["page"])}: rule "{x["rule"]}" matched "{X(x["text"])}" on the line "{X(x["line"])}"') for x in by_page(tg)]
    L.append('')
fm = log.get('font_maps') or {}
if fm.get('fonts') or fm.get('skipped'):
    n += 1; L += [f'### {n}. Font maps corrected (checklist 3.6)', '']
    if fm.get('skipped'): L += [f'- {fm["skipped"]}']
    L += ['Characters the font mapped to the wrong Unicode value now read as the printed glyph: private-use digits as 0–9, a three-em '
          'dash glyph as three em dashes. Each glyph was confirmed by rendering it alone; only the font\'s map changed, never the page.', '']
    L += [f'- {x["font"]}: {x["passed"]} of {x["checked"]} confirmed and corrected' + (f', {len(x["failed"])} not changed' if x['failed'] else '')
          + (' (' + ', '.join(f'code {c} → "{t}"' for c, t in x['fixed'].items()) + ')' if x['fixed'] else '') for x in fm.get('fonts') or []]
    L += [f'- **For a person:** {x["font"]} code {x["code"]} (glyph {x["glyph"]}): the name says {x["expected"]}, rendering read "{x["read"]}" '
          f'({x.get("confidence", "")}%); left as {x["mapped_to"]}' for x in fm.get('review') or []] + ['']
lr = (log.get('list_rule') or {})
if lr.get('flattened') or lr.get('kept') or lr.get('skipped'):
    fl = lr.get('flattened') or []
    n += 1; L += [f'### {n}. One-item lists turned into paragraphs by rule ({len(fl)})', '',
                  'A list with one item whose label is not a list marker (the auto-tagger took a paragraph\'s first word or a year for a label) '
                  'was made one paragraph, label and text together. Listen to a few; a real one-item list can be kept with `keep_lists`.', '']
    L += [xl(lambda X: f'- {pg(x["page"])}: label "{x["label"]}": "{X(x.get("text", ""))}"') for x in by_page(fl)]
    L += [f'- Kept as a list (work order): {pg(x["page"])} "{x["label"]}"' for x in by_page(lr.get('kept') or [])]
    L += [line(f'- Not changed: {pg(x["page"])} "{x["label"]}": {x["why"]}', entry=False) for x in by_page(lr.get('skipped') or [])] + ['']
ua = log.get('untagged_artifacts') or []
if ua:
    n += 1; L += [f'### {n}. Untagged text marked as decoration ({sum(a["chars"] for a in ua)} characters)', '']
    L += [f'- {pg(a["page"])}: "{a["label"]}" ({a["chars"]} characters)' for a in by_page(ua)] + ['']
ld = log.get('link_descriptions') or []; la = log.get('link_addresses_suspect') or []
if ld or la:
    n += 1; L += [f'### {n}. Links whose description was only a URL ({len(ld)}'
                  + (f', and {len(la)} address{"" if len(la) == 1 else "es"} that look{"s" if len(la) == 1 else ""} broken' if la else '') + ')', '',
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
    if nt_: L.append('- Empty ' + ', '.join(f'{x["tag"]} {on_pg(x["page"])}' for x in nt_) + ' removed (no content under them)')
    for k in by_page(et.get('kept') or []):
        L.append(f'- **Kept, empty: {k["tag"]} {on_pg(k["page"])}**, because ' + '; '.join(k['why']) + '.')
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
        L += [line(f'- ParentTree, {pg(p)}: ' + ', '.join(f'MCID {x["mcid"]} ({x["tag"]})' for x in xs), n_entries=len(xs)) for p, xs in sorted(by_pg.items())]
        if other: L.append(line('- ParentTree, entries not tied to page content (annotations, forms, or keys nothing uses): ' + ', '.join(f'key {x["key"]}' + (f' MCID {x["mcid"]}' if 'mcid' in x else '') + f' ({x["tag"]})' for x in other), n_entries=len(other)))
    if ic.get('idtree'): L.append(line('- IDTree: ' + ', '.join(f'"{x["id"]}" ({x["tag"]})' for x in ic['idtree']), n_entries=len(ic['idtree'])))
    L.append('')
hr = log.get('empty_holders_removed') or []; cg = log.get('captions_grouped') or []
if hr or cg:
    n += 1; L += [f'### {n}. Figure holders', '']
    L += [xl(lambda X: f'- {pg(x["page"])}: caption grouped with the {x["figures"]} figures in the holder just above it: "{X(x["caption"])}"') for x in cg]
    L += [f'- {pg(x["page"])}: empty figure-holder paragraph ({x["tag"]}) removed after its figure moved out (proven empty)' for x in hr]
    L.append('')
if stc and (stc['empty_tags'] or stc['paragraphs_holding_only_figures'] or stc['captions_not_grouped'] or stc['links_url_only']):
    n += 1; L += [f'### {n}. Structure left for a person', '']
    if stc['empty_tags']: L.append(f'- {stc["empty_tags"]} empty tag{"" if stc["empty_tags"] == 1 else "s"}: ' + ', '.join(f'{e["tag"]} {on_pg(e["page"])}' for e in by_page(stc['empty_tag_examples'])))
    L += [f'- {pg(x["page"])}: a {x["tag"]} paragraph holds only {x["figures"]} figure(s)' for x in stc['paragraphs_holding_only_figures']]
    L += [f'- {pg(x["page"])}: a caption is not grouped with a figure (it sits inside {x["parent"]})' for x in stc['captions_not_grouped']]
    L += [f'- {pg(x["page"])}: a link\'s description is only its URL ({x["contents"]})' for x in stc['links_url_only']]
    L.append('')
cp = log.get('captions_paired') or []
if cp:
    n += 1; L += [f'### {n}. Captions paired by position ({len(cp)})', '',
                  'Pages with several figures: each caption was tied to the figure right next to it. Check the pairs.', '']
    L += [xl(lambda X: f'- {pg(c["page"])}: "{X(c["caption"])}"') for c in by_page(cp)] + ['']
vw_afterefore, vw_after = v_wcag(v_before), v_wcag(v_after)
v_ua = [r for r in v_after['rules'] if r['scope'] != 'wcag'] if v_ran(v_after) else []
if vw_afterefore or vw_after or v_ua or (v_after and not v_ran(v_after)):
    WHO = {'executor': 'the pipeline', 'model': 'the AI', 'person': 'a person'}
    RF = log.get('rule_fixes') or {}
    def who_split():                       # one sentence from the "Who fixes" column: WCAG rules failing before, by who can act; after
        if not v_ran(v_before): before = 'Before: veraPDF did not run on the original.'
        else:
            grp = collections.Counter(r.get('who') for r in vw_afterefore.values())
            other = sum(v for k, v in grp.items() if k not in ('model', 'executor', 'person'))
            nb = len(vw_afterefore)
            before = (f'Before: {nb} rule{"" if nb == 1 else "s"} failing (the AI can act on {grp["model"]}, the pipeline on {grp["executor"]}, '
                      f'only a person on {grp["person"]}' + (f', {other} not classified' if other else '') + ').')
        return before + (f' After: {len(vw_after)}.' if v_ran(v_after) else ' After: veraPDF did not run on the result.')
    def who_cell(rid, r):                  # who can fix it, and what the pipeline changed for it in this run
        w = WHO.get(r.get('who'), 'not recorded') + (f' (`{r["key"]}`)' if r.get('who') == 'model' and r.get('key') else '')
        n_ = (RF.get(rid) or RF.get({'7.5-2': '7.5-1'}.get(rid, '')) or {}).get('changed')
        return w + (f'; the pipeline changed {n_}' if n_ and r.get('who') != 'executor' else f' ({n_} changed)' if n_ else '')
    n += 1; L += [f'### {n}. veraPDF (WCAG 2.2 machine profile), before and after', '',
                  (f'{v_after["tool"]}, profile "{v_after["profile"]}" ({v_after["profile_sha256"]}). ' if v_ran(v_after) else v_state(v_after, 'After') + '. ')
                  + 'Counts are failed checks; pages are from the first checks veraPDF lists for each rule, so a rule may fail on more pages. ',
                  # the intro is one line: rebuild it with its PDF/UA sentence as a PDF/UA part
                  ]
    L[-1] = line(L[-1], pdfua('Rules that only PDF/UA requires are listed apart and do not count. '), '"Who fixes" is who can act on the rule: the pipeline by itself, '
                 'the AI through the work order, or only a person. **Newly failing** means this run broke something the original passed. '
                 + who_split())
    L.append('')
    if vw_afterefore or vw_after:
        L += ['| Rule | WCAG | What it checks | Who fixes | Before | After | Status | Pages (after, else before) |', '|---|---|---|---|---:|---:|---|---|']
        for rid in sorted(set(vw_afterefore) | set(vw_after), key=lambda r: (r not in vw_after, -(vw_after.get(r) or vw_afterefore.get(r))['failed'],
                                                                 [int(x) for x in re.findall(r'\d+', r)])):   # ties: by rule number, so runs compare
            r = vw_after.get(rid) or vw_afterefore[rid]
            before = vw_afterefore[rid]['failed'] if rid in vw_afterefore else (0 if v_ran(v_before) else 'not run')
            desc = r['description'].replace('|', '/')
            L.append(line('| ', pdfua(f'{r["spec"]} '), f'{rid}{" (unclassified)" if r["unclassified"] else ""} | {", ".join(r["wcag"]) or "not mapped"} | ',
                     pdfua(desc, WCAG_NAMES[rid]) if rid in WCAG_NAMES else desc,
                     f'{" e.g. " + chr(34) + r["example"].replace('|', '/') + chr(34) if r.get("example") and rid in vw_after else ""} | {who_cell(rid, r)} | {before} | {vw_after[rid]["failed"] if rid in vw_after else (0 if v_ran(v_after) else "not run")} | {v_status(rid)} | '
                     + (pgs(r['pages']) if r['pages'] else NO_PAGE) + ' |', key=f'vera:{rid}', pages=r['pages']))
        L.append('')
    if v_new: L += [f'**Newly failing after this run: {", ".join(v_new)}.** The run made these; look at them first.', '']
    nokey = sorted({rid for rid, r in {**vw_afterefore, **vw_after}.items() if r.get('who') == 'model' and not r.get('key')})
    if nokey: L += [f'The AI was told about these rules without a work-order key to fix them (add one to `KEY` in `pipeline/vera.py`): {", ".join(nokey)}.', '']
    if v_ran(v_after) and v_after['totals']['unclassified']:
        L += [line('Not yet classified as WCAG', pdfua(' or PDF/UA-only'), f' (counted as WCAG until someone adds them to `pipeline/verapdf/rules.json`): {", ".join(v_after["totals"]["unclassified"])}.'), '']
    if v_ua:
        L += [line('PDF/UA-only, not required for WCAG (not counted):', scope='pdfua'), line('', scope='pdfua')]
        L += [line(f'- {r["id"]}: {r["why"]} ({r["failed"]} checks' + (f', {pgs(r["pages"])}' if r['pages'] else '') + ')'
              + (f', {v_status(r["id"])}' if v_status(r['id']) else ''), scope='pdfua') for r in v_ua]
        if v_both and [k for k in v_fixed if VB[k]['scope'] != 'wcag']:
            L.append(line('- fixed by this run: ' + ', '.join(k for k in v_fixed if VB[k]['scope'] != 'wcag'), scope='pdfua'))
        L.append('')
if wc and (wc['alt_text']['flagged'] or wc['tables_without_header'] or wc['reading_order']['flagged_count'] or wc['title_generic']
           or wc['links_generic'] or any(wc['headings'][k] for k in ('empty', 'long', 'repeated'))):
    n += 1; L += [f'### {n}. WCAG checks veraPDF does not make', '', 'Each item is something to look at, not a proven failure.', '']
    L += [line(f'- 1.1.1 {pg(x["page"])}: alt text "{x["alt"]}": {x["why"]}', key='wcag:1.1.1', pages=[x['page']]) for x in by_page(wc['alt_text']['examples'])]
    L += [line(f'- 1.3.1 {pg(x["page"])}: a table with no header cells (TH). Mark the header row or column, or flatten it if it is not a real table.', key='wcag:1.3.1', pages=[x['page']]) for x in by_page(wc['tables_without_header'])]
    if wc['reading_order']['flagged_count']:
        L.append(line(f'- 1.3.2 the reading order jumps back up the same column on {wc["reading_order"]["flagged_count"]} page{"" if wc["reading_order"]["flagged_count"] == 1 else "s"}. Listen through them with a screen reader '
                 '(or the PAC screen-reader preview): ' + ', '.join(f'{pg(x["page"])} ({x["jumps_up"]} jumps)' for x in by_page(wc['reading_order']['flagged'])),
                 key='wcag:1.3.2', pages=[x['page'] for x in wc['reading_order']['flagged']]))
    if wc['title_generic']: L.append(line(f'- 2.4.2 the title "{doc.get("title")}" looks like a file name or a placeholder. Use the book\'s real title.', key='wcag:2.4.2'))
    L += [xl(lambda X: f'- 2.4.4 {pg(x["page"])}: link text "{X(x["text"])}" does not say where the link goes', key='wcag:2.4.4', pages=[x['page']]) for x in by_page(wc['links_generic'])]
    L += [line(f'- 2.4.6 {pg(x["page"])}: a heading with no text', key='wcag:2.4.6', pages=[x['page']]) for x in by_page(wc['headings']['empty'])]
    L += [xl(lambda X: f'- 2.4.6 {pg(x["page"])}: a {x["chars"]}-character heading ("{X(x["text"])}"): probably body text tagged as a heading', key='wcag:2.4.6', pages=[x['page']]) for x in by_page(wc['headings']['long'])]
    L += [xl(lambda X: f'- 2.4.6 {pg(x["page"])}: the heading "{X(x["text"])}" twice in a row', key='wcag:2.4.6', pages=[x['page']]) for x in by_page(wc['headings']['repeated'])]
    L.append('')
d_ai = wo.get('deferrals', [])
if d_ai or wo.get('notes_for_reviewer'):
    n += 1; L += [f'### {n}. Deferred by the AI', '']
    L += [line(f'- **{d.get("what") or "(not described)"}**: {d.get("why") or "(no reason given)"}' + (f' [{pgs([p for p in d["pages"] if isinstance(p, int)])}]' if d.get('pages') else ''),
               key=f'ai:{i}', pages=[p for p in d.get('pages') or [] if isinstance(p, int)]) for i, d in enumerate(d_ai)]
    if wo.get('notes_for_reviewer'): L += ['', f'Reviewer note from the AI: {wo["notes_for_reviewer"]}']
    L.append('')
d_ex = [d for d in log.get('deferred', []) if d.get('what') != 'Han-only runs (ja vs zh)']
if han or d_ex:
    n += 1; L += [f'### {n}. Deferred by the executor', '']
    if han: L.append(line(f'- **{len(han)} Han-only CJK runs** need a Japanese / Chinese decision: fill in `han_review.csv`.', key='exec:han', pages=[h['page'] for h in han]))
    L += [line(f'- {d.get("what") or "(not described)"}' + (f' ({pg(d["page"])})' if 'page' in d else '') + (f': {d["why"]}' if 'why' in d else ''),
               key=f'exec:{d.get("what") or "not described"}', pages=[d.get('page')], scope=d.get('scope')) for d in d_ex]
    L.append('')
bad = log.get('rejected', []) + log.get('failed', []) + val.get('dropped', [])
if bad:
    n += 1; L += [f'### {n}. Decisions not applied ({len(bad)})', '', 'Rejected by validation or by the executor; nothing was half-applied.', '']
    import re as _re
    grp = collections.Counter((_re.sub(r'[\d(][\d, )]*', '#', _re.sub(r'PDF \d+(?:–\d+)?(?: \(printed [^)]*\))?', 'PDF', str(b.get('op') or b.get('where') or '(no operation recorded)'))).split(' #')[0],
                               b.get('why') or b.get('error') or '(no reason recorded)') for b in bad)
    if len(bad) > 10:
        L += ['| What | Why | Count |', '|---|---|---:|'] + [line(f'| {o} | {w.replace("|", "/")} | {c} |', entry=False) for (o, w), c in grp.most_common()] + ['', 'Each one:', '']
    L += [f'- {json.dumps(b, ensure_ascii=False)}' for b in bad]
    L.append('')
if n == 0: L.append('Nothing flagged.')

L += ['## What was changed', '', '| Change | Count |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in (log.get('applied') or {}).items()]
L += ['', '## Final check with PAC 2026', '',
      f'Open `{PDF}` in PAC 2026 (https://pac.pdf-accessibility.org/en, Windows) and run its WCAG check. Anything it fails that is not '
      'listed above is a gap in the automated checks: note it in the issue tracker.', '',
      'No automated check here covers these WCAG 2.2 AA criteria; check them by hand, with PAC\'s screen-reader and structure previews:', '',
      '- 1.1.1: alt text is accurate and gives the figure\'s purpose; decorative images are artifacts',
      '- 1.3.1 / 1.3.2: headings, lists and tables match what is printed, and the reading order makes sense',
      '- 1.4.1: no information is given by colour alone',
      '- 1.4.3: contrast of text over images and coloured backgrounds (PAC\'s contrast checker)',
      '- 1.4.5: no images of text where real text could be used (scanned pages: the OCR layer stands in)',
      '- 2.4.6: headings describe their section',
      '- 3.1.2: passages in another language carry their language (see `han_review.csv` if present)']
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
# review.md as data: sections of items (record.json `sections`); review.md and review.html are both drawn from them.
# "Overview" is computed once from them (lib/glance.py), kept in record.json, and placed before the evidence line.
from lib import glance as G
record['glance'] = G.glance(record, None, PLAB, [h['page'] for h in han], sections=to_sections(L))
at = next((k for k, l in enumerate(L) if l.startswith('Automated checks are evidence, not legal sign-off')), len(L))
L[at:at] = G.glance_md(record['glance'])
record['sections_version'] = SECTIONS_VERSION; record['sections'] = to_sections(L)
json.dump(record, open(os.path.join(R, 'record.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
md = '\n'.join(render_md(record['sections'])) + '\n'
open(os.path.join(R, 'review.md'), 'w', encoding='utf-8').write(md)
try:
    import report_html
    report_html.review_html(R, record, md, PLAB)
except Exception as e: print(f'note: review.html not written ({type(e).__name__}: {e})')

# ------------------------------------------------------------------ tidy
if not KEEP:
    for name in ('request.json', 'response.json', 'reply.txt', 'run.json', 'validation.json', 'workorder.json',
                 PDF + '.log.json', PDF + '.verify.json', 'verify.txt', 'error.txt', 'timing.json', 'attempts.json',
                 'workorder.ai.json', 'review.json', 'review_items.json', 'review_decisions.json'):
        p = os.path.join(R, name)
        if os.path.exists(p): os.remove(p)
    if os.path.isdir(A) and os.path.exists(os.path.join(A, 'digest.json')): shutil.rmtree(A)
    if os.path.isdir(os.path.join(R, 'review_pages')): shutil.rmtree(os.path.join(R, 'review_pages'))   # page images: copies of book pages
print(f'review: {os.path.join(R, "review.md")} · record: {os.path.join(R, "record.json")}' + (f' · han_review.csv ({len(han)} rows)' if han else '')
      + ('' if KEEP else ' · working files removed'))
