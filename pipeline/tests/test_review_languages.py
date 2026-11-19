"""test_review_languages.py: the review page's Languages section (#118, stage D): one row per word form, decided for all its
places at once; group approval only where it qualifies; the decisions counted for the record; the Ready rule's Language
Tags line; a publisher's tag a person removed. Synthetic work orders and pages only.

    python -m pytest tests/test_review_languages.py -q
"""
import os, sys, json, copy
import pikepdf
import pytest
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
    assert rows[0]['current'] == 'fr-FR' and rows[0]['ai'] is None and rows[0]['current_name'] == 'French' and rows[0]['current_written'] is None
    assert core.current_words('Hawaii') == {'current_name': 'Hawaiian', 'current_written': 'Hawaii'}      # review 08, L4: names, never codes
    assert core.current_words('xx-nonsense!') == {'current_name': None, 'current_written': 'xx-nonsense!'}

def test_decisions_apply_to_the_form_and_are_counted():
    w = wo(); items = core.build_items(w, DIGEST); by = {it['label']: it['id'] for it in items if it['kind'] == core.LANG_KIND}
    dec = {by['mappō']: {'status': 'approved', 'bulk': True}, by['地獄']: {'status': 'changed', 'value': 'zh'},
           by['極楽']: {'status': 'changed', 'value': 'ja'}, by['Copyright']: {'status': 'rejected'}}
    out = core.apply_decisions(w, items, dec)
    f = out['language_parts']['forms']
    assert (f[1]['lang'], f[1]['tag']) == ('zh', True) and (f[3]['lang'], f[3]['tag']) == ('ja', True) and f[4]['decided'] == 'remove'
    assert sorted((p['form'], p['lang']) for p in langreq.expand(out['language_parts'])) == [('mappō', 'ja-Latn'), ('地獄', 'zh'), ('極楽', 'ja')]
    lr = core.language_review(items, dec)
    assert lr == {'forms': 4, 'approved': 1, 'changed': 2, 'rejected': 1, 'not_reviewed': 0, 'bulk': 1,
                  'bulk_by': {'all_shown': 1, 'readings': 0, 'printed_reading': 0}, 'local': 0}
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

def test_a_publishers_tag_a_person_kept_is_the_one_read(tmp_path):
    """review 08, M5: the PDF tags a line fr-FR on its element but en-US in its marks; "Keep the Tag" drops the marks' value
    so the kept tag is read, and verify no longer counts it as a conflict."""
    w0 = wo(); items = core.build_items(w0, DIGEST); cid = next(it['id'] for it in items if it['label'] == 'Copyright')
    assert core.apply_decisions(w0, items, {cid: {'status': 'approved'}})['language_parts']['forms'][4]['decided'] == 'kept'
    src = langpdf.build(str(tmp_path / 'k.pdf'), [{'lang': 'en-US', 'span_lang': 'fr-FR', 'text': 'Droits reserves'}])   # lang: the marks'
    lp = {'version': 2, 'forms': [{**form('Droits reserves', 'existing', ['existing'], None, None, current='fr-FR', tag=False, person=True), 'decided': 'kept'}],
          'parts': [[1, 0, 0, 15, 0]]}
    run('verify.py', src, src)
    assert json.load(open(src + '.verify.json'))['language']['publisher_conflicts'] == 1          # before: the marks win
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'language_parts': lp}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, w, out); run('verify.py', src, out)
    assert '/Lang' not in marks(out)[0]
    pdf = pikepdf.open(out); assert str(pdf.Root.StructTreeRoot.K[0].K[0].get('/Lang')) == 'fr-FR'
    v = json.load(open(out + '.verify.json'))
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['language']['publisher_conflicts'] == 0

def test_publisher_language_names_are_converted_listed_or_left(tmp_path):
    """review 08, M4: a language's name written as /Lang becomes its code and is listed; a name whose words look like another
    language ("Hungarian" on a Hawaiian name) stays as written, for a person. Synthetic lines."""
    src = langpdf.build(str(tmp_path / 'n.pdf'), [{'span_lang': 'Hawaiian', 'text': 'Aloha mai kakou e hele ana'},
                                                  {'span_lang': 'Hungarian', 'text': 'Kaleo Mahoe Akana, MD'},
                                                  {'span_lang': 'Japanese', 'text': 'Kyoto temples'},
                                                  {'span_lang': 'Tongan', 'text': 'Malo e lelei, oku ou fiefia'},          # review 10, L1: Polynesian
                                                  {'span_lang': 'Hawaii', 'text': 'Oahu, a Giant Military Base'}])        # review 10, L2: mostly English
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, w, out)
    pdf = pikepdf.open(out); els = pdf.Root.StructTreeRoot.K[0].K
    assert [str(e.get('/Lang')) for e in els] == ['haw', 'Hungarian', 'Japanese', 'to', 'Hawaii']
    lp = json.load(open(out + '.log.json'))['language_parts']
    assert sorted((c['value'], c['code'], c['count']) for c in lp['names_converted']) == [('Hawaiian', 'haw', 1), ('Tongan', 'to', 1)]
    assert {(x['value'], x['why']) for x in lp['names_not_converted']} == {('Hungarian', 'its words look Hawaiian'), ('Japanese', 'its words are in Latin script'),
                                                                          ('Hawaii', 'most of its words are English')}
    assert any('/Lang "Hungarian"' in d['what'] for d in json.load(open(out + '.log.json'))['deferred'])

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

def test_the_page_counts_language_forms_for_staff():
    """review 08, L4: numbers with thousands separators, a sidebar entry, and the "Finish Review" dialog counting the word
    forms not decided (the page's own text; checked in a browser on a copy of cadaverous)."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert "function fmtN(x) { return Number(x || 0).toLocaleString('en-US'); }" in page
    assert "<h2>Languages</h2><a href=\"#languages\"><span>Word Forms</span>" in page
    assert '"Language Tags" in "Ready to Ship?" stays Not Reviewed.' in page and "(the PDF\\'s own tags stay as they are)" in page   # review 10, L6

def test_the_ai_decisions_count_leaves_the_word_forms_out():
    """review 12, M2 (Patrick's A): the work order's own decisions only; the word forms named beside them for staff."""
    import test_review_problems as TP
    ai = with_languages()
    assert G.n_decisions(ai) == G.n_decisions(TP.ai_order()) and G.n_forms(ai) == 4             # Kyōto is listed, not decided
    assert G.n_forms(ai) == core.language_summary(core.build_items(ai, DIGEST))['total']           # the section's own total
    assert G.forms_text(2190) == '2,190 word forms under "Languages"'

def test_deciding_word_forms_changes_nothing_in_the_work_order_count(tmp_path):
    """review 12, M2: approving or changing forms adds 0 to "N changed" (a form has no identity in diff)."""
    import test_review_problems as TP
    R, ai, items, _adds = TP.run(tmp_path, with_languages())
    by = {it['label']: it['id'] for it in items if it['kind'] == core.LANG_KIND}
    dec = {by['mappō']: {'status': 'approved'}, by['地獄']: {'status': 'changed', 'value': 'zh'}}
    wo2 = core.apply_decisions(ai, items, dec)
    assert wo2['language_parts'] != ai['language_parts'] and core.diff(ai, wo2) == []
    rv = core.finish(R, ai, wo2, 'Kim', '2026-11-13', 'page', decisions=dec, items=items, gap_default='left open for the test')
    assert rv['changes'] == [] and rv['language']['approved'] == 1

def test_the_polynesian_set_names_rennell_bellona_by_its_code():
    """review 12, note: Rennell-Bellona is mnv; rnl is Ranglong, a Kuki-Chin language."""
    from lib import langtag
    codes = langtag.POLYNESIAN                           # moved from apply.py with name_misfit (review 12, C)
    assert 'mnv' in codes and 'rnl' not in codes and {'mi', 'to', 'sm', 'ty'} <= codes

LANG_INTRO = ("Words and passages in another language found in the PDF. A screen reader switches to a language\\'s voice for the "
              "words tagged with it. Decide each word form: the choice applies to every place it appears. Words in Chinese "
              "characters alone are decided one by one, because the same characters are used in Chinese and Japanese, unless the "
              "reading printed beside them (kana, a Hepburn or pinyin reading, hangul) names the same language: those can be "
              "approved together. Language "
              "tags already in the PDF are also decided one by one, so a person confirms each of them. For Hawaiian, most screen "
              "readers have no Hawaiian voice, so those words are read with the default voice; the tag is still required.")

def test_the_languages_introduction_is_patricks_paragraph():
    """Patrick, 2026-11-13 (review 12, B, without the fold): one paragraph, exactly, the same on every PDF. #124 adds the
    clause on Chinese characters with a matching reading, which can now be approved together."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert f"const LANG_INTRO = '{LANG_INTRO}';" in page and "'<p>' + LANG_INTRO + '</p>'" in page
    assert page.count('LANG_INTRO') == 2                                              # defined once, drawn once, on every PDF
    assert 'Show More' not in page and 'data-lang="more"' not in page                   # review 31: pages replace "Show More"

def test_group_approval_is_on_with_its_two_buttons():
    """#124: group approval is on again. "Approve All Shown" keeps its rules (the shown rows with `bulk`); "Approve
    Characters with Matching Readings" approves every row of the fold the server lists (reading_ids), loaded or not;
    each decision records its button, and the status says so."""
    import re
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert len(re.findall(r'const LANG_BULK = (true|false);', page)) == 1 and 'const LANG_BULK = true;' in page
    i = page.index('data-lang="bulk"'); assert page.rfind('LANG_BULK && g.bulk ?', 0, i) > i - 120     # each button only under the switch
    i = page.index('data-lang="readings"'); assert page.rfind("LANG_BULK && (g.reading_ids || []).length ?", 0, i) > i - 120
    assert '>Approve All on This Page (' in page and '>Approve Characters with Matching Readings (' in page   # review 31: pages
    assert "langSet(r.id, 'approved', undefined, 'all_shown')" in page and "langSet(id, 'approved', undefined, 'readings')" in page
    assert "if (r.bulk && !(state.decisions[r.id] || {}).status)" in page                   # Approve All on This Page: its own rows only
    assert "else if (act === 'clear' || act === 'keep' || act === 'drop') {" in page        # #159: one handler for a row's own choices
    assert "' (in a group approval: matching reading)'" in page and "' (in a group approval)'" in page   # a restored draft says how

def test_the_code_shown_is_the_lang_written(tmp_path):
    """review 12, C (Patrick, 2026-11-13): beside each row, the value that becomes /Lang in the output PDF: an AI row, a
    changed row, and the PDF's own tags kept: a code on an element (fr-FR), a name converted (Hawaiian → haw), a name left
    for a person (Hawaii on mostly English words), and a value in the marks alone (left as written). Synthetic lines."""
    from lib import plpages, langcands
    src = langpdf.build(str(tmp_path / 'c.pdf'), [{'lang': 'en-US', 'text': 'He chanted mappo daily.'},
                                                  {'lang': 'en-US', 'text': 'The city of Heiankyo grew.'},
                                                  {'lang': 'en-US', 'span_lang': 'fr-FR', 'text': 'Droits reserves'},
                                                  {'span_lang': 'Hawaiian', 'text': 'Aloha mai kakou e hele ana'},
                                                  {'span_lang': 'Hawaii', 'text': 'Oahu, a Giant Military Base'},
                                                  {'lang': 'fr-fr', 'text': 'Bonjour tout le monde'}])
    with pikepdf.open(src) as pdf: places = langcands.existing(pdf, plpages.Pages(src), 'en')
    assert {p['form']: p['carried'] for p in places} == {'Droits reserves': 'element', 'Aloha mai kakou e hele ana': 'element',
                                                         'Oahu, a Giant Military Base': 'element', 'Bonjour tout le monde': 'marks'}
    lp = langreq.to_rows(langreq.forms(places), {})
    n = len(lp['forms'])
    lp['forms'] += [form('mappo', 'marks', ['marks'], 'ja-Latn', 'high'), form('Heiankyo', 'marks', ['marks'], 'ja-Latn', 'high')]
    lp['parts'] += [[1, 0, 11, 15, n], [1, 1, 12, 19, n + 1]]
    w = {'language_parts': lp}
    items = core.build_items(w, DIGEST); by = {it['label']: it for it in items if it['kind'] == core.LANG_KIND}
    rows = {r['form']: r for g in core.language_summary(items)['groups'] for r in core.language_rows(items, g['group'])['rows']}
    assert {f: r['written'] for f, r in rows.items()} == {'mappo': 'ja-Latn', 'Heiankyo': 'ja-Latn', 'Droits reserves': 'fr-FR',
                                                         'Aloha mai kakou e hele ana': 'haw', 'Oahu, a Giant Military Base': 'Hawaii',
                                                         'Bonjour tout le monde': 'fr-fr'}
    heads = {g['group']: g['code'] for g in core.language_summary(items)['groups']}
    assert heads == {'Japanese (Romanized)': 'ja-Latn', core.LANG_EXISTING: None}               # several codes: none in the heading
    dec = {it['id']: {'status': 'approved'} for it in by.values()}
    dec[by['Heiankyo']['id']] = {'status': 'changed', 'value': 'ja'}                              # "Tagged as Japanese · ja"
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps(core.apply_decisions(w, items, dec)))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out)
    pdf = pikepdf.open(out); els = list(pdf.Root.StructTreeRoot.K[0].K)
    def spans(e):
        if isinstance(e, pikepdf.Dictionary):
            if e.get('/S') == '/Span' and '/Lang' in e: yield str(e.Lang)
            k = e.get('/K')
            for x in (k if isinstance(k, pikepdf.Array) else []): yield from spans(x)
    assert sorted(x for e in els[:2] for x in spans(e)) == ['ja', 'ja-Latn']                      # the AI row, the changed row
    assert [str(e.get('/Lang')) for e in els[2:5]] == ['fr-FR', 'haw', 'Hawaii']
    assert str(marks(out)[5]['/Lang']) == 'fr-fr'                                                # the marks alone: as written


def test_untagged_rows_say_why_in_staff_words():
    """review 14, 2: a low-confidence guess named with its code; an unmapped reason never printed; no reason, no
    parentheses. The rows carry the guess; the page words it (checked in the browser too)."""
    forms = [form('般若', 'cjk', ['cjk:han_only'], 'ja', 'low', why='language', person=True),
             form('不二', 'cjk', ['cjk:han_only'], None, 'medium', why='varies', person=True),
             form('如来', 'cjk', ['cjk:han_only'], None, None, why=None, person=True)]
    w = {'language_parts': {'version': 2, 'forms': forms, 'parts': [[1, 0, 0, 1, 0], [1, 1, 0, 1, 1], [1, 2, 0, 1, 2]]}}
    items = core.build_items(w, DIGEST)
    rows = {r['form']: r for r in core.language_rows(items, core.LANG_UNTAGGED)['rows']}
    assert (rows['般若']['guess'], rows['般若']['guess_name'], rows['般若']['ai']) == ('ja', 'Japanese', None)
    assert rows['不二']['guess'] is None and rows['如来']['guess'] is None and rows['如来']['why'] is None
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert "bits.push('low confidence; its guess: ' + esc(r.guess_name || r.guess));" in page          # a name only (2026-11-14)
    assert "if (LANG_WHY[r.why]) bits.push(LANG_WHY[r.why]);" in page and "|| r.why)" not in page           # never the raw word
    assert "'The AI left it untagged' + (bits.length ? ' (' + bits.join('; ') + ')' : '')" in page

def test_a_form_with_no_ai_answer_says_so():
    """#137 (dropped language answers): a form with no AI decision reads "No AI answer (…)", with the run's reason in staff
    words (review 02, L3), never "The AI left it untagged"; a deliberate null keeps that wording. The page's own function
    is run through a JavaScript engine (as test_dates.py does)."""
    import json, subprocess
    from test_dates import js_runner
    forms = [form('mappō', 'marks', ['marks'], None, None, why=None, person=True), form('如来', 'cjk', ['cjk:han_only'], None, None, why=None, person=True)]
    forms[0]['no_answer'] = 'echo'
    w = {'language_parts': {'version': 2, 'forms': forms, 'parts': [[1, 0, 0, 1, 0], [1, 1, 0, 1, 1]]}}
    rows = {r['form']: r for r in core.language_rows(core.build_items(w, DIGEST), core.LANG_UNTAGGED)['rows']}
    assert rows['mappō']['no_answer'] == 'echo' and rows['如来']['no_answer'] is None
    run = js_runner()
    if run is None: pytest.skip('no JavaScript engine (node or jsc) runs here')
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    def chunk(start, end): i = page.index(start); return page[i:page.index(end, i)]
    code = (chunk('const esc = ', '\n') + '\n' + chunk('const LANG_WHY = ', 'function langRowHtml(')
            + '\nconst cases = ' + json.dumps([{'no_answer': c} for c in ('echo', 'tag', 'invalid', 'not_answered', 'cut_off', 'failed')]
                                              + [{}, {'confidence': 'medium', 'why': 'name'}, {'confidence': 'low', 'why': 'language', 'guess': 'ja', 'guess_name': 'Japanese'}])
            + ';\n(typeof print === "function" ? print : console.log)(JSON.stringify(cases.map(langUntagged)));')
    out = subprocess.run(run + [code], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == [
        'No AI answer (its reply could not be matched to this word)', 'No AI answer (the AI gave a language that cannot be written into the PDF)',
        'No AI answer (its answer was not in the expected form)', 'No AI answer (the reply skipped this word)',
        'No AI answer (the AI’s reply stopped before this word)', 'No AI answer (its request did not finish)', 'No AI answer',
        'The AI left it untagged (a name)', 'The AI left it untagged (low confidence; its guess: Japanese)']

def test_the_status_sits_under_the_form_outside_its_language():
    """review 14, 4-6: "label: value" under the word form, outside the lang-attributed element, with role status; Kept and
    Removed for a publisher's tag; "Change Language" with no ellipsis; the same column edge on every row."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    i = page.index('<div class="lang-left"><div class="lang-form" lang="')                        # column 1 of the row (round 24)
    seg = page[i:i + 400]
    assert seg.index('</div>') < seg.index('lang-status') and 'role=\"status\"' in seg       # closed before the status
    for w in ("'Tagged: '", "'Removed: '", "'Kept: '", "'Approved: '", "'Left untagged'", "'Not reviewed'"): assert w in page
    assert 'Tagged as' not in page and 'Tag kept' not in page and 'Tag removed' not in page
    assert "'<option value=\"\">Change Language</option>'" in page and 'Change Language…' not in page
    assert '.lang-row[data-status] { border-left-color: var(--accent); }' in page and 'border-left: 4px solid transparent' in page

def test_the_language_line_is_not_applicable_only_without_candidates():
    """Round 18 (Patrick, 2026-11-14): with word forms found but none decided, the line reads Not Done with the reason and
    blocks Ready; Not Applicable only when the audit found none; a record from before has no status and reads as before."""
    def line(state, n): return G.language_line({'language_status': {'candidates': n, 'state': state}})
    assert line('off', 0) == (True, 'Not Applicable') and line('not_run', 0) == (True, 'Not Applicable')
    assert line('off', 12) == (False, 'Not Done (the language step was turned off)')
    assert line('left_out_book', 12) == (False, 'Not Done (the language step was left out: over the limit per PDF)')
    assert line('left_out_cap', 12) == (False, 'Not Done (the language step was left out: over its own limit)')
    assert line('failed', 12) == (False, 'Not Done (the language step did not finish)')
    assert line('not_run', 12) == (False, 'Not Done (the language step was not run)')
    assert G.language_line({}) == (True, 'Not Applicable')                                 # a record made before round 18
    assert line('off', None) == (False, 'Not Done (not checked)') and line('not_run', None) == (False, 'Not Done (not checked)')   # fail closed
    rec = {'workorder': wo(), 'language_status': {'candidates': 5, 'state': 'decided'}}
    assert G.language_line(rec) == (False, 'Not Reviewed (4 word forms to decide on the review page)')

def test_when_the_ai_tagged_nothing_a_person_confirms_each_form():
    """Patrick, 2026-11-14 (review 22, point 1): the step ran and no form has a tag or goes to a person; the forms are rows
    under "Left Untagged by the AI" and the line reads Not Reviewed until each is decided, then Approved; never Not
    Applicable."""
    forms = [form('Kyōto', 'marks', ['marks'], None, None, why='name', tag=False), form('Fuji', 'latin', ['latin'], None, None, why='name', tag=False)]
    w = {'language_parts': {'version': 2, 'forms': forms, 'parts': [[1, 0, 0, 4, 0], [1, 1, 0, 3, 1]]}}
    items = core.build_items(w, DIGEST); rows = [it for it in items if it['kind'] == core.LANG_KIND]
    assert [it['label'] for it in rows] == ['Kyōto', 'Fuji'] and {core.lang_group(it) for it in rows} == {core.LANG_UNTAGGED}
    rec = {'workorder': w, 'language_status': {'candidates': 2, 'state': 'decided'}}
    assert G.language_line(rec) == (False, 'Not Reviewed (2 word forms the AI left untagged to confirm on the review page)')
    assert G.n_forms(w) == 2 == core.language_summary(items)['total']
    dec = {it['id']: {'status': 'approved'} for it in rows}
    rec['language_review'] = {**core.language_review(items, dec), 'reviewer': 'Kim', 'date': '2026-11-14'}
    assert G.language_line(rec) == (True, 'Approved (Kim on November 14, 2026)')
    w2 = wo(); assert [it['label'] for it in core.build_items(w2, DIGEST) if it['kind'] == core.LANG_KIND] == ['mappō', '地獄', '極楽', 'Copyright']   # unchanged otherwise


def test_no_check_line_when_nothing_is_wrong():
    """Patrick, 2026-11-14: the line beside "Finish Review" says nothing when there is no problem."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert "parts.length ? parts.join(' · ') : '';" in page and 'All choices can be applied' not in page


def test_codes_only_in_the_status_and_the_list():
    """Patrick, 2026-11-14: the language code shows only in each row's status and in the "Change Language" list, not in
    the fold headings, the AI's line, the guess or the PDF's own tags line."""
    import re
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert len(re.findall(r'langCode\(', page)) == 2                                 # its definition and the status's val()
    assert "const val = (name, code) => esc(name || code || '') + langCode(name ? code : '');" in page
    assert "'>' + esc(x.name) + ' · ' + esc(x.code) + '</option>'" in page             # the list keeps "Japanese · ja"

def test_rows_have_one_bottom_line():
    """Patrick, round 24 (correcting round 23): no fixed-width button area. "Change Language" sits beside the last button
    (normal button spacing); the text block starts at the list's edge on that row; rows within a fold line up (a subgrid on
    the fold's list), the edge may differ between folds; at phone width the row stacks."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert '--lang-btn-w' not in page and 'lang-top' not in page
    assert '.lang-list { display: grid; grid-template-columns: max-content minmax(0, 1fr); column-gap: 6px; }' in page
    assert 'grid-template-columns: subgrid;' in page and '.lang-left { grid-column: 1; grid-row: 1; min-width: 0; contain: inline-size; }' in page
    assert '.lang-info { grid-column: 2; grid-row: 1;' in page and '.lang-btns { grid-column: 1; grid-row: 2; display: flex; gap: 6px;' in page
    assert '.lang-acts { grid-column: 2; grid-row: 2; display: flex; flex-wrap: wrap; align-items: center; gap: 6px;' in page
    i = page.index("'<div class=\"lang-btns\">"); j = page.index("'<div class=\"lang-acts\">' +"); k = page.index('<select data-lang="change"')
    assert i < j < k                                              # the buttons, then the list (and "Clear Choice") in column 2
    assert '.lang-list { display: block; } .lang-row { display: flex; flex-direction: column;' in page   # stacked at phone width

def test_a_decided_row_has_clear_choice():
    """Patrick, 2026-11-14: "Clear Choice" at the bottom right of a decided row only; clearing deletes the row's choice,
    the same as never decided (the whole draft is saved, so it stays deleted)."""
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    assert '(d.status ? \'<button type="button" class="lang-clear" data-lang="clear"' in page and '>Clear Choice</button>' in page
    assert "if (act === 'clear') delete state.decisions[id];" in page and "const id = b.closest('.lang-row').dataset.id;" in page


ARG_MAX_LINUX = 100_000      # under Linux's 128 KB limit on one argument (MAX_ARG_STRLEN): CI runs there

def _pager_js(cases, folder):
    """review 31 (Patrick's pages): the page's own langPager, langNote and langBar run through a JavaScript engine. The
    program carries every id of each language (4,722 here), so it is run from a file in `folder`, never as one argument."""
    import subprocess
    from test_dates import js_runner, js_file_cmd
    if js_runner() is None: pytest.skip('no JavaScript engine (node or jsc) runs here')
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    def chunk(start, end): i = page.index(start); return page[i:page.index(end, i)]
    code = (chunk('const esc = ', '\n') + '\n' + chunk('function fmtN(', '\n') + '\n'
            + 'const LANG_BULK = true; const state = {decisions: {}}; const LANGS = {groups: [], page: 100};\n'
            + 'function langReadingLeft(g) { return g.reading_ids || []; } function langRuleLeft(g) { return g.rule_ids || []; }\n'
            + chunk('const langRows = {};', '// The section') + chunk('function langBar(g) {', 'function langFold(g) {')
            + '\nconst cases = ' + json.dumps(cases) + ';\nLANGS.groups = cases.map(c => c.g);\n'
            + 'const out = cases.map(c => { langPage[c.g.group] = c.p; langRows[c.g.group] = c.rows || []; Object.assign(state.decisions, c.dec || {}); '
            + 'return {pager: langPager(c.g, "t"), note: langNote(c.g), bar: langBar(c.g)}; });\n'
            + '(typeof print === "function" ? print : console.log)(JSON.stringify(out));')
    cmd = js_file_cmd(code, folder)
    assert len(code) > ARG_MAX_LINUX or len(cases) == 1                     # the cases that broke CI are this large
    assert max(len(a.encode()) for a in cmd) < ARG_MAX_LINUX and sum(len(a.encode()) + 1 for a in cmd) < ARG_MAX_LINUX
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)

def test_pages_come_in_blocks_of_ten_with_arrows_only_where_a_block_is(tmp_path):
    """review 31, Patrick's pages: numbered buttons in fixed blocks of ten; "<" and ">" only where a block is in that
    direction, opening its first page; ten pages or fewer show their numbers alone; the page shown is aria-current."""
    import re
    def g(name, n, **kw): return {'group': name, 'count': n, 'bulk': 1, 'ids': [f'{name}{i}' for i in range(n)], **kw}
    out = _pager_js([{'g': g('A', 4722), 'p': 45}, {'g': g('B', 4722), 'p': 1}, {'g': g('C', 1000), 'p': 3},
                     {'g': g('D', 1001), 'p': 11}, {'g': g('E', 4722, reading_ids=['E1'], rule_ids=['E2']), 'p': 12}], tmp_path)
    def shown(h):
        return [(m.group(2) or '') + ('*' if 'aria-current' in m.group(1) else '') for m in re.finditer(r'<button type="button"([^>]*)>([^<]*)</button>', h)]
    a, b, c, d, e = (x['pager'] for x in out)
    assert shown(a) == ['&lt;', '41', '42', '43', '44', '45*', '46', '47', '48', '...', 'Go']                    # 41–48: no ">"
    assert 'data-page="31" aria-label="Previous Pages" title="Previous Pages">&lt;' in a
    assert shown(b) == ['1*'] + [str(n) for n in range(2, 11)] + ['&gt;', '...', 'Go'] and 'data-page="11" aria-label="Next Pages"' in b
    assert shown(c) == [str(n) + ('*' if n == 3 else '') for n in range(1, 11)] + ['...', 'Go']               # ten pages: numbers alone
    assert shown(d) == ['&lt;', '11*', '...', 'Go']
    assert shown(e)[:2] == ['&lt;', '11'] and '12*' in shown(e) and '&gt;' in shown(e)
    assert 'aria-label="Page 45" aria-current="page">45<' in a and 'aria-label="Go to Page" title="Go to Page">...<' in a
    assert '<label for="lang-gi-0t">Go to Page</label>' in a and 'aria-describedby="lang-ge-0t"' in a and 'aria-controls="lang-go-0t"' in a
    assert 'id="lang-gi-1t"' in b                                                                             # ids per fold
    assert out[0]['note'] == '<p class="lang-meta lang-note">"Approve All on This Page" approves only the word forms on this page.</p>'
    assert out[4]['note'].endswith('"Approve Characters with Matching Readings" and "Approve Forms Decided by Their Printed Reading" '
                                   'approve every matching word form of this language, on every page.</p>')

def test_the_fold_counts_the_whole_language_and_approves_one_page(tmp_path):
    """review 31: the bar's "not reviewed" counts every word form of the language (the server's ids), not the page's;
    "Approve All on This Page" counts the page's own rows."""
    ids = [f'language:marks|w{i}' for i in range(250)]
    rows = [{'id': i, 'bulk': True} for i in ids[100:200]]
    dec = {i: {'status': 'approved'} for i in ids[:30]}
    out = _pager_js([{'g': {'group': 'Pali', 'count': 250, 'bulk': 200, 'ids': ids}, 'p': 2, 'rows': rows, 'dec': dec}], tmp_path)
    assert '>Approve All on This Page (100)</button>' in out[0]['bar'] and '220 of 250 not reviewed' in out[0]['bar']

def test_the_summary_sends_every_id_and_the_page_size():
    """review 31: language_summary gives each fold all its row ids, in the order the pages show them, and LANG_PAGE."""
    forms = [form(f'mapp{i}ō', 'marks', ['marks'], 'ja-Latn', 'high') for i in range(3)]
    w = {'language_parts': {'version': 2, 'forms': forms, 'parts': [[1, i, 0, 1, i] for i in range(3)]}}
    items = core.build_items(w, DIGEST)
    s = core.language_summary(items)
    g = s['groups'][0]
    assert s['page'] == core.LANG_PAGE == 100
    assert g['ids'] == [r['id'] for r in core.language_rows(items, g['group'])['rows']]

