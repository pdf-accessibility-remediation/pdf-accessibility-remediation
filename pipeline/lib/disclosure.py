"""lib/disclosure.py: the accessibility statement written when a version ships (issue #38, stage 4; 21 §C, review 22
M3–M5, N6, N7). One set of facts, drawn two ways: disclosure.md and disclosure.html, written once into
release/shipped/NNN/ and never rewritten (it describes what shipped).

    blocks = facts(rec, rel, shipment, glance)    # [(heading or None, [lines])]: the statement as data
    md, html = to_md(blocks, title), to_html(blocks, title)

What it claims, and only when the record supports it:
  - what the AI decided and what people did with it, by kind: approved as proposed, changed, rejected, added by a person
    (review.decisions and review.workorder.counts); an older reviewed run with no per-decision record gives the totals,
    and a run with neither says the split was not recorded (M3);
  - the text: "No AI wrote or changed the book's printed text", then, only when they apply, the AI's readings of OCR
    words given as spoken text, the local OCR pages and who approved them, or the publisher's OCR layer (M4);
  - the model, the instructions and the date of the call only for a real call; a replayed reply says "those of an
    earlier call, not recorded for this run" (M5);
  - veraPDF's before and after, or "not checked" (N6).
Every name and note is the person's text as typed: escaped in the HTML (html.escape) and in the Markdown (release.md_text,
md_quote) (N7). The wording is a draft, marked so on the page: to be agreed with the sponsors.
"""
import html as _html
from lib import release as REL, dates as D

DRAFT = 'Draft wording: to be agreed with the sponsors.'
STATUS_WORDS = {'approved': 'approved as proposed', 'seen': 'approved as proposed', 'changed': 'changed by a person', 'rejected': 'rejected by a person',
                'accepted_unreviewed': 'not reviewed'}

def _n(x): return int(x) if isinstance(x, int) else len(x or [])

def decisions(rec):
    """[(kind, {approved, changed, rejected, ...})], totals, added, note: the AI's decisions and what people did with them."""
    rv = rec.get('review') or {}; wo = rv.get('workorder') or {}
    ds = rv.get('decisions') or []
    added = (wo.get('counts') or {}).get('added') or sum(1 for c in wo.get('changes') or [] if isinstance(c, dict) and c.get('change') == 'added')
    if ds:
        by = {}
        for d in ds:
            if d.get('kind') == 'Deferred by the AI': continue                        # a deferral is not a decision
            w = STATUS_WORDS.get(d.get('status'), d.get('status') or 'not recorded')
            by.setdefault(d.get('kind') or 'Other decisions', {}).setdefault(w, 0); by[d.get('kind') or 'Other decisions'][w] += 1
        return sorted(by.items()), None, added, None
    c = wo.get('counts')
    if c:                                                                              # an older reviewed run: totals only
        tot = {STATUS_WORDS.get(k, k): 0 for k in ('approved', 'changed', 'rejected')}
        for k, v in c.items():
            if k in STATUS_WORDS and v: tot[STATUS_WORDS[k]] = tot.get(STATUS_WORDS[k], 0) + v
        return [], {k: v for k, v in tot.items() if v}, added, 'Counted from the review\'s totals; this run did not record each decision\'s kind.'
    return [], None, added, 'Counted from the applied work order; the split between the AI and a person was not recorded for this run.'

def applied(rec):
    """(entries in the applied work order, entries the executor could not apply)."""
    from lib.glance import n_decisions
    ap = rec.get('apply') or {}
    return n_decisions(rec.get('workorder') or {}), sum(_n(ap.get(k)) for k in ('rejected', 'failed', 'deferred'))

def text_lines(rec):
    """M4: what is true of the book's text on this run."""
    out = ['No AI wrote or changed the book\'s printed text.']
    ow = ((rec.get('apply') or {}).get('ocr_words') or {}).get('forms') or 0
    if ow: out.append(f'For {ow} word{"" if ow == 1 else "s"} the OCR misread, an AI\'s reading is given as spoken text only; each is listed for a person in the report.')
    intake = rec.get('intake') or {}
    pages = (intake.get('ocr') or {}).get('pages_with_ocr_text') or []
    from lib.glance import ocr_layer_flagged
    v = (intake.get('review') or {}).get('ocr_text_approved')
    if pages or ocr_layer_flagged(intake):
        who = f', approved by {v.get("reviewer")} on {D.day(v.get("date"))}' if isinstance(v, dict) and v.get('verdict') == 'approved' else ''
        out.append((f'On {len(pages)} scanned page{"" if len(pages) == 1 else "s"} the text is local OCR (not corrected)' if pages
                    else 'The text layer on scanned pages is OCR (not corrected)') + who + '.')
    elif intake.get('ocr_layer_test'):
        out.append('The publisher\'s text layer on scanned pages is OCR; it was checked and kept as published.')
    return out

def model_lines(rec):
    """M5: the model, the instructions and the call's date only for a real call."""
    run = rec.get('run') or {}
    if run.get('response_from') or not run.get('model'):
        return ['Model and instructions: those of an earlier call, not recorded for this run.']
    p = f'{run.get("prompt_file")}' + (f' ({str(run.get("prompt_sha256"))[:16]})' if run.get('prompt_sha256') else '') if run.get('prompt_file') else 'not recorded'
    return [f'Model: {run["model"]}. Instructions: {p}. Decided on {D.day(run.get("started"))}.']

def facts(rec, rel, ship, glance):
    """The statement as data: [(heading or None, [lines])]. Every value from a person is kept as typed (escaped when drawn)."""
    doc = rec.get('document') or {}; sha = (ship.get('pdf') or {}).get('sha256')
    ses = (ship.get('pdf') or {}).get('session')
    ver = f'the version from Session {int(ses)}' if str(ses or '').isdigit() else 'the version applied without a review'
    B = [(None, [DRAFT]),
         ('This File', [f'{doc.get("output") or "the remediated PDF"}, {ver}, shipped on {D.day(ship.get("shipped"))} by {ship.get("by")} (shipment {ship.get("n")}).']
          + ([f'Published at: {ship["where"]}.'] if ship.get('where') else []) + ([f'Note: {ship["note"]}'] if ship.get('note') else [])
          + [f'sha256: {sha}, which identifies this exact file.']),
         ('How It Was Made Accessible', ['The PDF was remediated by a semi-automated pipeline toward WCAG 2.1 AA. Local software measured the document '
                                         'and made the mechanical fixes. An AI model made a limited set of decisions, and a person reviewed them '
                                         'before they were applied.'] + text_lines(rec))]
    kinds, totals, added, note = decisions(rec)
    lines = []
    for k, c in kinds: lines.append(f'{k}: ' + ', '.join(f'{v} {w}' for w, v in c.items()))
    if totals: lines.append('In all: ' + ', '.join(f'{v} {w}' for w, v in totals.items()))
    if added: lines.append(f'Added by a person: {added}')
    n_app, n_not = applied(rec)
    lines.append(f'Entries applied: {n_app - n_not}' + (f' ({n_not} the software could not apply)' if n_not else ''))
    if note: lines.append(note)
    B.append(('What the AI Decided and What People Did', lines + model_lines(rec)))
    rv = (rec.get('review') or {}).get('workorder') or {}
    sess = (rec.get('review') or {}).get('session')
    people = [f'The AI\'s decisions: reviewed on the review page by {rv.get("reviewer")} on {D.day(rv.get("date"))}'
              + (f' (Session {int(sess)})' if str(sess or '').isdigit() else '') + '.' if rv else 'The AI\'s decisions: not reviewed by a person.']
    ocr_line = next((x['text'] for x in glance.get('ship') or [] if x.get('what') == 'OCR text approved'), None)
    if ocr_line: people.append(f'OCR text: {ocr_line}')
    issues = []
    for s in REL.SECTIONS:
        p = REL.part(rel, s, sha); c = p['check']
        if p['state'] != 'completed' or not c: continue
        f = c.get('fields') or {}
        extra = f' ({f["screen_reader"]})' if f.get('screen_reader') else ''
        people.append(f'{REL.SECTION_NAMES[s]}: completed by {c.get("by")} on {D.day(c.get("recorded"))}{extra} · {p["n_items"]} items'
                      + (f' · {REL.noted(len(p["issues"]))}' if p['issues'] else ''))
        issues += [f'{REL.SECTION_NAMES[s]}, {REL.label(s, k)}: {((c.get("items") or {}).get(k) or {}).get("note") or ""}' for k in p['issues']]
    B.append(('What People Reviewed and Approved', people))
    B.append(('Issues Noted (kept for a person to fix)', issues or ['No issues were noted in the evaluation.']))
    vg = glance.get('verapdf') or {}
    vline = (f'veraPDF (WCAG 2.2 machine checks): {vg.get("before_rules")} rules failing before → {vg.get("after_rules")} after; '
             f'{len(vg.get("newly_failing") or [])} newly failing.' if vg.get('ran_before') and vg.get('ran_after')
             else 'veraPDF (WCAG 2.2 machine checks): not checked (it did not run on both files).')
    B.append(('Automated Checks', ['Five safety checks (pages unchanged, text unchanged, all content tagged or marked as decoration, the tag tree\'s '
                                   'index, every font readable): ' + ('passed.' if glance.get('safety_ok') else 'not all passed.'),
                                   vline, 'Automated checks are evidence, not legal sign-off.']))
    B.append(('What This Statement Is Not', ['The accessibility evaluation is a record of what a person found, not a legal certification.']))
    B.append(('Contact', ['To be agreed with the sponsors.']))
    return B

def to_md(blocks, title):
    L = [f'# Accessibility Statement: {REL.md_text(title)}', '']
    for h, lines in blocks:
        if h: L += [f'## {h}', '']
        for l in lines:
            L += REL.md_quote(l) if '\n' in l else [REL.md_text(l)]
            L.append('')
    return '\n'.join(L).rstrip('\n') + '\n'

CSS = (':root{color-scheme:light dark;--bg:#fff;--ink:#1d1d1b;--muted:#5f5f5a;--line:#d9d9d4}'
       '@media (prefers-color-scheme:dark){:root{--bg:#1f1f1e;--ink:#ecece8;--muted:#a3a39c;--line:#3a3a37}}'
       'body{background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif;max-width:52em;margin:0 auto;padding:16px}'
       'h1{font-size:22px}h2{font-size:18px;border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:24px}'
       '.draft{color:var(--muted);font-style:italic}p{overflow-wrap:anywhere;white-space:pre-wrap}')

def to_html(blocks, title):
    E = _html.escape
    B = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Accessibility Statement: {E(title)}</title><style>{CSS}</style></head><body><main><h1>Accessibility Statement: {E(title)}</h1>']
    for h, lines in blocks:
        if h: B.append(f'<h2>{E(h)}</h2>')
        for l in lines: B.append(f'<p{" class=\"draft\"" if l == DRAFT else ""}>{E(l)}</p>')
    B.append('</main></body></html>')
    return '\n'.join(B) + '\n'
