"""test_review_languages.py: the review page's Languages section (#118, stage D): one row per word form, decided for all its
places at once; group approval only where it qualifies; the decisions counted for the record; the Ready rule's Language
Tags line; a publisher's tag a person removed. Synthetic work orders and pages only.

    python -m pytest tests/test_review_languages.py -q
"""
import os, sys, json, copy
import pikepdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
from test_language_parts import run, marks  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from review import core  # noqa: E402
from lib import glance as G, langreq  # noqa: E402

DIGEST = {'source': {'pages': 3, 'file': 'b.pdf'}}

def form(form, group, cls, lang=None, conf=None, why='language', tag=None, person=None, current=None, places=1):
    return {'key': f'{group}|{form}', 'form': form, 'group': group, 'class': cls, 'lang': lang, 'confidence': conf, 'why': why,
            'tag': bool(lang and conf in ('high', 'medium')) if tag is None else tag, **({'person': True} if person else {}),
            **({'current': current} if current else {}), 'places': places}

def wo():
    forms = [form('mappō', 'marks', ['marks'], 'ja-Latn', 'high'),
             form('地獄', 'cjk', ['cjk:han_only'], 'ja', 'high'),
             form('Kyōto', 'marks', ['marks'], None, None, why='name'),                      # Latin-script name: listed, not decided
             form('極楽', 'cjk', ['cjk:han_only'], None, 'low', why='unsure', person=True),   # non-Latin left untagged: a person decides
             form('Copyright', 'existing', ['existing'], 'en', 'high', current='fr-FR', tag=False, person=True)]
    return {'language_parts': {'version': 2, 'forms': forms, 'parts': [[1, 0, 5, 9, 0], [2, 3, 0, 1, 1], [1, 1, 0, 4, 2], [2, 4, 0, 1, 3], [3, 0, 0, 8, 4]]}}

def test_rows_per_form_and_the_summary():
    items = core.build_items(wo(), DIGEST)
    ls = [it for it in items if it['kind'] == core.LANG_KIND]
    assert [it['label'] for it in ls] == ['mappō', '地獄', '極楽', 'Copyright']                       # Kyōto is not a row
    s = core.language_summary(items)
    groups = {g['group']: g for g in s['groups']}
    assert set(groups) == {'Japanese (Romanized)', 'Japanese', core.LANG_UNTAGGED, core.LANG_EXISTING}
    assert groups['Japanese (Romanized)']['bulk'] == 1 and groups['Japanese']['bulk'] == 0               # never Chinese characters alone
    assert all(x['code'] != 'qaa' for x in s['names'])
    rows = core.language_rows(items, core.LANG_EXISTING)['rows']
    assert rows[0]['current'] == 'fr-FR' and rows[0]['ai'] is None

def test_decisions_apply_to_the_form_and_are_counted():
    w = wo(); items = core.build_items(w, DIGEST); by = {it['label']: it['id'] for it in items if it['kind'] == core.LANG_KIND}
    dec = {by['mappō']: {'status': 'approved', 'bulk': True}, by['地獄']: {'status': 'changed', 'value': 'zh'},
           by['極楽']: {'status': 'changed', 'value': 'ja'}, by['Copyright']: {'status': 'rejected'}}
    out = core.apply_decisions(w, items, dec)
    f = out['language_parts']['forms']
    assert (f[1]['lang'], f[1]['tag']) == ('zh', True) and (f[3]['lang'], f[3]['tag']) == ('ja', True) and f[4]['decided'] == 'remove'
    assert sorted((p['form'], p['lang']) for p in langreq.expand(out['language_parts'])) == [('mappō', 'ja-Latn'), ('地獄', 'zh'), ('極楽', 'ja')]
    lr = core.language_review(items, dec)
    assert lr == {'forms': 4, 'approved': 1, 'changed': 2, 'rejected': 1, 'not_reviewed': 0, 'bulk': 1}
    lr2 = core.language_review(items, {by['mappō']: {'status': 'approved'}})
    assert lr2['not_reviewed'] == 3

def test_the_ready_rule_reads_the_language_review():
    rec = {'workorder': wo()}
    assert G.language_line({}) == (True, 'Not Applicable')
    assert G.language_line(rec) == (False, 'Not Reviewed (4 word forms to decide on the review page)')
    rec['language_review'] = {'forms': 4, 'not_reviewed': 1, 'reviewer': 'Kim', 'date': '2026-11-13'}
    assert G.language_line(rec) == (False, 'Not Reviewed (1 word form to decide on the review page)')
    rec['language_review']['not_reviewed'] = 0
    assert G.language_line(rec) == (True, 'Approved (Kim on November 13, 2026)')

def test_a_publishers_tag_a_person_removed_is_gone(tmp_path):
    """sands's case: the PDF tags an English line fr-FR on its element and in its marks; a person chose "Remove the Tag"."""
    src = langpdf.build(str(tmp_path / 's.pdf'), [{'lang': 'fr-FR', 'span_lang': 'fr-FR', 'text': 'Copyright notice'}])
    lp = {'version': 2, 'forms': [{**form('Copyright notice', 'existing', ['existing'], None, None, current='fr-FR', tag=False, person=True), 'decided': 'remove'}],
          'parts': [[1, 0, 0, 15, 0]]}
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'language_parts': lp}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, w, out); run('verify.py', src, out)
    assert '/Lang' not in marks(out)[0]
    pdf = pikepdf.open(out); assert '/Lang' not in pdf.Root.StructTreeRoot.K[0].K[0]
    v = json.load(open(out + '.verify.json'))
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['language']['publisher_conflicts'] == 0

def with_languages():
    import test_review_problems as TP
    return {**TP.ai_order(), 'language_parts': wo()['language_parts']}

def test_the_check_accepts_the_review_pages_marker(tmp_path):
    """review 08, M1: problems() marks each entry with its card before the check; a language form must not come back as
    "left out" for that marker."""
    import test_review_problems as TP
    p = TP.probs(tmp_path, {}, ai=with_languages())
    assert p['unplaced'] == [] and p['fields'] == [] and p['conflicts'] == []

def test_language_rows_stay_out_of_the_work_orders_counts(tmp_path):
    """review 08, M2: "Work Order Approval" counts the work order's cards only; the Language Tags line owns the forms."""
    import test_review_problems as TP
    R, ai, items, _adds = TP.run(tmp_path, with_languages())
    cards = [it for it in items if it['kind'] != core.LANG_KIND]; assert cards
    rv = core.finish(R, ai, core.apply_decisions(ai, items, {}), 'Kim', '2026-11-13', 'page', decisions={}, items=items,
                     gap_default='left open for the test')
    assert sum(rv['counts'].values()) == len(cards) and rv['counts']['accepted_unreviewed'] == len(cards)
    assert rv['language']['not_reviewed'] == 4
