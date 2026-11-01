"""test_evaluation.py: the accessibility evaluation in the report (13-builder-stage2-revisions-proposal.md §5–§8): review.md's
"Accessibility Evaluation" section and its redraw after a Record, review.html's section, card and cards, summary.html's
counts. Synthetic run folders with a one-page synthetic PDF; no model, nothing sent.

    python -m pytest tests/test_evaluation.py -q
"""
import os, re, json
import pytest
import pikepdf
from lib import release as REL, glance as G, sections as SEC
from review import core, manual as M
import report_html as H

SAFE = ['Every page looks the same as the original', 'Published text unchanged', 'All content tagged or marked as decoration',
        'Tag-tree index points only into the tree', 'Fonts: every embedded font program could be read']
PAC = {'by': 'Kim', 'fields': {}, 'items': {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['pac']}}
SR = {'by': 'Lee', 'fields': {'screen_reader': 'NVDA 2026.1'}, 'items': {x['key']: {'result': 'pass'} for x in REL.CHECKLIST['screen_reader']}}
OLD_PAC = ['## Final Check with PAC 2026', '', 'The manual checks are recorded …', '', '- PAC 2026: WCAG Check: …']

def md_lines(after=()):
    rows = [f'| {n} | OK | x |' for n in SAFE] + ['| veraPDF: no rule newly failing or failing more often | **CHECK** | not compared: veraPDF did not run on both files |']
    return (['# Remediation Review: b.pdf', '', 'Result: `b_remediated.pdf`', '', '## Overview', '', 'old overview', '',
             'Automated checks are evidence, not legal sign-off.', '', '## Automated Checks', '', '| Check | Result | Detail |', '|---|---|---|']
            + rows + [''] + OLD_PAC + list(after) + [''])

def make_run(tmp_path, sections, after=()):
    R = tmp_path / 'run'; R.mkdir(parents=True)
    doc = pikepdf.new(); doc.add_blank_page(page_size=(300, 300)); doc.save(str(R / 'b_remediated.pdf'))
    rec = {'document': {'file': 'b.pdf', 'output': 'b_remediated.pdf', 'pages': 1, 'output_sha256': REL.sha_file(str(R / 'b_remediated.pdf'))},
           'verapdf': {'before': {'not_run': 'VERAPDF=off'}, 'after': {'not_run': 'VERAPDF=off'}}}
    L = md_lines(after)
    if sections: rec['sections_version'] = SEC.VERSION; rec['sections'] = SEC.to_sections(L)
    core.save(str(R / 'record.json'), rec)
    (R / 'review.md').write_text('\n'.join(L) + ('' if sections else '\n'), encoding='utf-8')
    return str(R)

def md(R): return open(os.path.join(R, 'review.md'), encoding='utf-8').read()
def outside(text):
    """review.md without its Overview and its evaluation section: what a redraw must leave byte for byte."""
    L = text.split('\n'); out, skip = [], False
    for l in L:
        if l.startswith('## '): skip = l[3:].strip().lower() in ('overview',) + REL.EVAL_HEADINGS
        if not skip: out.append(l)
    return out

# ------------------------------------------------------------------ review.md's section
def test_the_not_recorded_form_names_the_page_and_every_item():
    L = REL.section_md(REL.empty(), 'a' * 64, 'b_remediated.pdf')
    t = '\n'.join(L)
    assert L[0] == '## Accessibility Evaluation' and 'not a legal certification' in t and '"Accessibility Evaluation" page' in t
    assert all(f'- {x["label"]}: {x["help"]}' in L for s in REL.SECTIONS for x in REL.CHECKLIST[s])
    assert 'PDF/UA' not in t and 'Verified' not in t and 'Needs Rework' not in t

@pytest.mark.parametrize('sections', [True, False])
def test_a_redraw_replaces_the_section_once_and_leaves_the_rest(tmp_path, sections):
    R = make_run(tmp_path, sections, after=['', '## Notes After', '', 'tail text'] if not sections else ())
    before = md(R)
    M.refresh(R, say=lambda *a: None)
    assert outside(md(R)) == outside(before) and '## Final Check with PAC 2026' in md(R)    # nothing recorded: the old section stays
    evil = 'line one\n## Injected\n- x\n1. y\n> z'
    M.record(R, 'pac', dict(PAC, notes=evil), say=lambda *a: None, batch=False)
    M.record(R, 'screen_reader', dict(SR, items=dict(SR['items'], tables={'result': 'fail', 'note': 'read *row* by_row [x]'})), say=lambda *a: None, batch=False)
    first = md(R); M.refresh(R, say=lambda *a: None)
    assert md(R) == first                                                          # a second redraw changes nothing
    assert first.count('\n## Accessibility Evaluation') == 1 and 'Final Check with PAC 2026' not in first
    assert '\n## Injected' not in first and '> \\## Injected' in first and '> \\- x' in first and '> 1\\. y' in first
    assert 'read \\*row\\* by\\_row \\[x\\]' in first
    assert outside(first) == outside(before)                                        # the rest of review.md, line for line
    assert '**Screen-Reader Test: Completed by Lee on ' in first and '· 10 items · 1 issue noted**' in first
    if sections:
        rec = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
        assert [x['key'] for x in rec['sections']].count('accessibility-evaluation') == 1 and 'injected' not in [x['key'] for x in rec['sections']]
    else: assert first.rstrip().endswith('tail text')                              # the next section, kept after it

def test_an_earlier_version_and_a_retired_row_in_review_md():
    old = {'id': 1, 'recorded': '2026-10-31T18:18:30', 'by': 'Patrick', 'pdf': {'sha256': 'b' * 64, 'session': '005', 'which': 'current'},
           'fields': {'pac_version': '2026.1'}, 'items': dict(PAC['items'], pac_pdfua={'result': 'not_run'})}
    rel = {'checks': {'schema': REL.SCHEMA, 'pac': [old], 'screen_reader': []}, 'shipped': []}
    t = '\n'.join(REL.section_md(rel, 'a' * 64, 'b.pdf'))
    assert '**PAC 2026: Completed on an earlier version (Session 5) by Patrick on October 31, 2026: it does not count for this version**' in t
    assert '| PAC 2026: PDF/UA Check (no longer asked) | Not Run |' in t and 'PAC Version (no longer asked): 2026.1' in t
    assert '**Screen-reader test.** Listen' in t

# ------------------------------------------------------------------ review.html
@pytest.mark.parametrize('sections', [True, False])
def test_review_html_folds_review_md_section_only_while_nothing_is_recorded(tmp_path, sections):
    R = make_run(tmp_path, sections)
    M.refresh(R, say=lambda *a: None)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert 'final-check-with-pac-2026' in h and 'id="mc-h"' not in h               # nothing recorded: no section; the instructions fold
    M.record(R, 'pac', PAC, say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert 'id="mc-h">Accessibility Evaluation</h2>' in h and 'id="accessibility-evaluation"' not in h and 'final-check-with-pac-2026' not in h   # H8
    assert '<strong>PAC 2026:</strong> Completed by Kim on ' in h and '<strong>Screen-Reader Test:</strong> Not completed for this version' in h
    assert 'class="nopen mcopen" data-session="mc-pac" data-html="1" data-title="PAC 2026: Full Results" hidden>View Full Results</button><div class="mcfull">' in h
    assert '@media print { .js .mcfull { display: block; }' in h and "if (b.hasAttribute('data-html')) { nb.innerHTML" in h
    assert "if (b.hasAttribute('data-html')) { var h = d.querySelector('h2'); h.tabIndex = -1; h.focus(); }" in h   # focus: the heading
    assert '<textarea' not in h.split('id="mc-h"')[1].split('</section>')[0] and '<div class="mcfull"><p>Checked By: Kim</p><div class="tw"><table>' in h   # a read-only table

def test_the_card_the_needs_box_and_the_vera_card(tmp_path):
    R = make_run(tmp_path, True)
    M.record(R, 'pac', PAC, say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<h2 id="ship-h">Ready to Ship?</h2>' in h and 'Ready to Ship? No' not in h and 'Status: <strong>Not Ready</strong>' in h
    assert '<div class="card muted"><h3>Needs a Person</h3><div class="big">1</div><p>looked at in the evaluation (Kim, ' in h   # decision 9
    assert '<span class="newly">newly failing: not checked</span> (veraPDF did not run on both files)' in h                     # Q6: said, visibly
    assert '5 of 5 checks OK' in h and 'Not checked' not in h.split('id="st-h"')[1].split('</section>')[0]
    assert '· looked at in the evaluation (Kim, ' in md(R)
    M.record(R, 'pac', dict(PAC, items=dict(PAC['items'], needs_person={'result': 'fail', 'note': 'two left'})), say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<div class="card warn"><h3>Needs a Person</h3><div class="big">1</div><p class="lab">Needs attention</p><p>marked Fail in the evaluation (Kim, ' in h
    g = H.glance_of(R)
    vf = [x for x in g['issues'] if x['text'].startswith('veraPDF:')][0]
    assert vf['rank'] == 1 and g['issues'][0] is vf                                # the finding first (H7)

def test_newly_failing_in_orange_and_a_shipped_book_has_readys_border(tmp_path):
    R = make_run(tmp_path, True)
    rec = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
    tot = lambda n: {'wcag_failed_rules': n, 'wcag_failed_checks': n}
    rec['verapdf'] = {'before': {'rules': [], 'totals': tot(0)}, 'after': {'rules': [{'id': '7.18.1-1', 'scope': 'wcag', 'failed': 1}], 'totals': tot(1)}}
    core.save(os.path.join(R, 'record.json'), rec)
    M.record(R, 'pac', PAC, say=lambda *a: None, batch=False); M.record(R, 'screen_reader', SR, say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<span class="newly">1 newly failing</span>' in h and '<section class="ship" aria-labelledby="ship-h">' in h   # Not Ready: no work order
    core.save(os.path.join(R, 'release', 'shipped.json'), [{'n': 1, 'shipped': '2026-11-02T09:00:00', 'by': 'Lee', 'pdf': {'sha256': rec['document']['output_sha256']}}])
    M.refresh(R, say=lambda *a: None)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<section class="ship yes" aria-labelledby="ship-h">' in h and 'Status: <strong>Shipped</strong>' in h   # Shipped: Ready's border (H9)
    assert H.glance_of(R)['ready'] is False                                        # but counted as Shipped, not Ready
    H.summary_html(str(tmp_path))                                                  # the batch page counts them apart (H9)
    s = open(os.path.join(str(tmp_path), 'summary.html'), encoding='utf-8').read()
    assert '<strong>Ready:</strong> 0 · <strong>Shipped:</strong> 1 · <strong>Pending Evaluation:</strong> 0 · of 1 books' in s
    assert 'Ready to Ship?</th>' not in s and 'not checked:' not in s

# ------------------------------------------------------------------ review 16's J2, J3, J4, J6
def test_j2_unreadable_evaluation_records_never_read_as_ready(tmp_path):
    from webapp import runs
    R = make_run(tmp_path, True); os.makedirs(os.path.join(R, 'release'))
    open(os.path.join(R, 'release', 'checks.json'), 'w').write('{"schema": "manual-checks/9"}')   # a schema this code does not read
    rec = json.load(open(os.path.join(R, 'record.json'), encoding='utf-8'))
    rec['glance'] = {'schema': G.SCHEMA, 'ship': [], 'status': {'name': 'Ready', 'text': 'Ready'}}
    r = runs.ready(R, rec)
    assert r['answer'] == 'No' and r['status'] == 'Not Ready (the evaluation records could not be read)'
    assert r['current'] == 'Not Ready'                                              # L3: the current version's status too, never a KeyError
    os.remove(os.path.join(R, 'release', 'checks.json'))
    rec['glance'] = {'schema': G.SCHEMA, 'ship': [], 'safety': []}
    assert runs.ready(R, rec)['current'] == 'Not Ready'                              # the normal path gives it as well

def test_j3_safety_state_follows_safety_line():
    assert H.safety_state({'safety': [], 'safety_ok': False}) == 'not checked'               # none at all: not checked, never failed
    assert H.safety_state({'safety': [{'what': 'x', 'ok': True}], 'safety_ok': False}) == 'not checked'
    assert H.safety_state({'safety': [{'what': 'x', 'ok': False}], 'safety_ok': False}) == 'failed'
    assert G.safety_line([])[1].startswith('Not Checked (only 0 of the 5')

def test_j4_inline_full_results_wrap_in_a_scroll_box(tmp_path):
    R = make_run(tmp_path, True)
    M.record(R, 'pac', PAC, say=lambda *a: None, batch=False)
    h = open(os.path.join(R, 'review.html'), encoding='utf-8').read()
    assert '<div class="mcfull"><p>Checked By: Kim</p><div class="tw"><table>' in h          # fitTables() covers it, script on or off
    assert '@media (max-width: 600px) { .mcfull td.item { min-width: 6em; width: auto; } }' in h

def test_j6_pages_checked_has_the_field_limit():
    data = dict(PAC, fields={'pages_checked': '1, ' * 40 + '1'})
    with pytest.raises(REL.Invalid) as e: REL.validate('pac', data, {'n_pages': 5})
    assert dict(e.value.errors)['fields.pages_checked'].startswith('"Pages Checked" is too long:')
