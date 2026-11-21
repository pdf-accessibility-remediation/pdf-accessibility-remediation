"""The review page's dictionary marks (#141, proposal 14; review 15): lib/latinlist.py, the finder recording them on each
place, the language step carrying them to the work order, option A's rows, and the page's two lines. Synthetic pages and
made-up forms only; the committed data (pipeline/data/latin-whitaker.json, latin-phrases.txt) is read as shipped."""
import os, re, sys, json, time, hashlib, argparse, subprocess
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'tests'))
import langpdf  # noqa: E402
from lib import plumb_fix, plpages, langcands, langreq, latinlist, workorder_check, glance as G  # noqa: F401,E402
from review import core  # noqa: E402
from test_review_languages import form, DIGEST  # noqa: E402


# ---------------------------------------------------------------- the list and the phrases
def test_latin_norm_folds_compatibility_forms_and_never_ipa():
    assert latinlist.latin_norm('ﬁdes') == 'fides' and latinlist.latin_norm('ſum') == 'sum'      # review 15, L2 (NFKD)
    assert latinlist.latin_norm('Cæsar') == 'caesar' and latinlist.latin_norm('Iūlius,') == 'iulius' and latinlist.latin_norm('vitro') == 'uitro'
    assert latinlist.latin_norm('diŋ') == '' and latinlist.latin_norm('láɪ') == ''            # an IPA respelling matches nothing


def test_the_tool_uses_the_same_normalizer():
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import dict_measure
    assert dict_measure.latin_norm is latinlist.latin_norm and dict_measure.whitaker_match is latinlist.whitaker_match


def test_whitakers_words_knows_inflected_forms():
    assert latinlist.in_latin('dicta') and latinlist.in_latin('partes tres') and latinlist.in_latin('Gallia est omnis divisa')
    assert not latinlist.in_latin('house') and not latinlist.in_latin('prima house') and not latinlist.in_latin('')


def test_a_phrase_is_whole_longest_first_and_quoted_as_printed():
    words = 'He graduated Magna Cum Laude, then cum laude again; in vitro tests, vitro alone.'.split()
    assert latinlist.phrase_at(words, 3, 3) == 'Magna Cum Laude'                         # the longer phrase, as the book prints it
    assert latinlist.phrase_at(words, 4, 4) == 'Magna Cum Laude'                         # (its comma trimmed)
    assert latinlist.phrase_at(words, 7, 7) == 'cum laude'
    assert latinlist.phrase_at(words, 10, 10) == 'in vitro' and latinlist.phrase_at(words, 9, 10) == 'in vitro'
    assert latinlist.phrase_at(words, 12, 12) is None                                    # "vitro" alone is no phrase
    assert latinlist.phrase_at(words, 5, 6) is None                                      # "then cum": not inside one phrase
    assert latinlist.phrase_at(words, None, None) is None


def test_the_shipped_files_match_the_readme_and_load_quickly():
    readme = open(os.path.join(HERE, 'data', 'README.md'), encoding='utf-8').read()
    for name in ('latin-whitaker.json', 'latin-phrases.txt'):
        sha = hashlib.sha256(open(os.path.join(HERE, 'data', name), 'rb').read()).hexdigest()
        sec = readme[readme.index('## ' + name):]
        assert sha in sec[:sec.find('\n## ', 4) if '\n## ' in sec[4:] else len(sec)], name
    assert os.path.exists(os.path.join(HERE, 'data', 'latin-whitaker.LICENCE'))
    latinlist._W.clear(); t = time.time(); latinlist.in_latin('dicta')
    assert time.time() - t < 1.0
    ps = [l.strip() for l in open(latinlist.PHRASES, encoding='utf-8') if l.strip() and not l.startswith('#')]
    assert len(ps) == 55 and 'raison d' not in ps and 'prima facie' in ps


# ---------------------------------------------------------------- the finder, the step, the work order
RUNS = [{'font': 'F3', 'text': 'The claim was prima facie sound, said Onjōji.'},
        {'font': 'F3', 'text': 'Gallia est omnis divisa in partes tres.'},
        {'font': 'F3', 'text': 'He went to Kyōto and the facie alone.'}]


def places(tmp_path, **kw):
    src = langpdf.build(str(tmp_path / 'm.pdf'), RUNS)
    return src, langcands.book(plpages.Pages(src), doc_lang='en', **kw)


def test_the_finder_records_both_facts_on_each_place(tmp_path):
    _, c = places(tmp_path)
    by = {(p['form'], p['w0']): p for p in c['places']}
    pf = next(p for (f, _), p in by.items() if f == 'prima facie')
    assert pf.get('latin_list') and pf.get('latin_phrase') == 'prima facie'
    alone = next(p for (f, _), p in by.items() if f == 'facie')
    assert alone.get('latin_list') and 'latin_phrase' not in alone                       # by the place's own words, not the page's
    assert not any(k in next(p for (f, _), p in by.items() if f == 'Onjōji') for k in ('latin_list', 'latin_phrase'))
    assert c['fingerprint'] == langcands.book(plpages.Pages(str(tmp_path / 'm.pdf')), doc_lang='en')['fingerprint']


def test_the_step_finding_the_words_again_keeps_them(tmp_path):
    """review 15 §2.5 (2), M1: a stale audit (or another document language) is found again by name_languages.candidates
    with langcands.book; the places still carry the marks."""
    import name_languages
    src = langpdf.build(str(tmp_path / 'm.pdf'), RUNS)
    A = tmp_path / '_audit'; A.mkdir()
    json.dump({'version': 1, 'places': [], 'words': {}}, open(A / 'lang_candidates.json', 'w'))             # stale: version 1
    args = argparse.Namespace(audit_dir=str(A), pdf=src, grow=True)
    ps, words, doc_lang, how, _ = name_languages.candidates(args, {'document': {'lang': 'en'}})
    assert how != "the audit's"                                                           # found again with langcands.book
    fs ={f['form']: f for f in langreq.forms(ps)}
    assert fs['prima facie'].get('latin_phrase') == 'prima facie' and fs['prima facie'].get('latin_list')
    os.remove(A / 'lang_candidates.json')
    json.dump(langcands.book(plpages.Pages(src), doc_lang='de'), open(A / 'lang_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False)
    ps2, *_ = name_languages.candidates(argparse.Namespace(audit_dir=str(A), pdf=src, grow=False), {'document': {'lang': 'en'}})
    assert any(p.get('latin_phrase') == 'prima facie' for p in ps2)                       # another document language: found again too


def test_the_work_order_carries_them_and_the_check_keeps_them(tmp_path):
    """review 15 §2.5 (3): to_rows writes both keys; workorder_check reports no unknown keys; requests never carry them."""
    _, c = places(tmp_path)
    fs = langreq.forms(c['places'])
    lp = langreq.to_rows(fs, {f['id']: {'lang': None, 'confidence': 'high', 'why': 'english'} for f in fs})
    rec = {f['form']: f for f in lp['forms']}
    assert rec['prima facie']['latin_phrase'] == 'prima facie' and rec['prima facie']['latin_list'] is True
    assert 'latin_phrase' not in rec['facie'] and 'latin_list' not in rec['Onjōji']
    wo = {'language_parts': lp}
    dropped = workorder_check.check_language_parts(wo, 1)
    assert not [d for d in dropped if 'unknown keys' in str(d.get('why'))]
    items = [it for r in langreq.requests({'title': 'T', 'language': 'en'}, fs, c['words']) for it in r['items']]
    assert items and not any(k in it for it in items for k in ('latin_list', 'latin_phrase'))


# ---------------------------------------------------------------- option A: the rows (review 15, M2)
def lp_of(forms):
    return {'version': 2, 'forms': forms, 'parts': [[1, i, 0, 1, i] for i in range(len(forms))]}


def test_a_phrase_form_is_added_to_the_rows():
    forms = [form('mappō', 'marks', ['marks'], 'ja-Latn', 'high'), form('facie', 'unknown', ['unknown'], None, 'high', why='english'),
             form('Kyōto', 'marks', ['marks'], None, None, why='name')]
    forms[1]['latin_phrase'] = 'prima facie'
    assert langreq.to_decide(forms) == [0, 1]
    w = {'language_parts': lp_of(forms)}
    items = core.build_items(w, DIGEST); rows = {it['label']: it for it in items if it['kind'] == core.LANG_KIND}
    assert set(rows) == {'mappō', 'facie'} and core.lang_group(rows['facie']) == core.LANG_UNTAGGED
    assert rows['facie']['ai'] is None and not rows['facie']['context'].get('bulk')     # "Approve All Shown" never covers it
    summ = {g['group']: g for g in core.language_summary(items)['groups']}
    assert summ[core.LANG_UNTAGGED]['bulk'] == 0
    out = core.language_rows(items, core.LANG_UNTAGGED)['rows'][0]
    assert out['latin_phrase'] == 'prima facie' and out['latin_list'] is False
    assert G.n_forms(w) == 2
    rec = {'workorder': w, 'language_status': {'candidates': 3, 'state': 'decided'}}
    assert G.language_line(rec) == (False, 'Not Reviewed (2 word forms to decide on the review page)')


def test_a_phrase_form_never_shrinks_the_every_form_fallback():
    """review 15 §2.5 (1): the AI tagged nothing; one form sits in a phrase; every form is still a row."""
    forms = [form('Kyōto', 'marks', ['marks'], None, None, why='name', tag=False), form('facie', 'unknown', ['unknown'], None, 'high', why='english'),
             form('Fuji', 'latin', ['latin'], None, None, why='name', tag=False)]
    forms[1]['latin_phrase'] = 'prima facie'
    assert langreq.to_decide(forms) == [0, 1, 2]
    w = {'language_parts': lp_of(forms)}
    assert [it['label'] for it in core.build_items(w, DIGEST) if it['kind'] == core.LANG_KIND] == ['Kyōto', 'facie', 'Fuji']
    assert G.n_forms(w) == 3


def test_the_rows_pass_the_confirmation_for_a_latin_answer():
    forms = [form('omnis divisa', 'unknown', ['unknown'], 'la', 'high'), form('mappō', 'marks', ['marks'], 'ja-Latn', 'high')]
    forms[0]['latin_list'] = True; forms[1]['latin_list'] = True
    rows = {r['form']: r for r in core.language_rows(core.build_items({'language_parts': lp_of(forms)}, DIGEST), 'Latin')['rows']}
    assert rows['omnis divisa']['latin_list'] is True and rows['omnis divisa']['latin_phrase'] is None


# ---------------------------------------------------------------- the page's two lines
def test_the_page_shows_each_line_only_where_it_belongs():
    from test_dates import js_runner
    run = js_runner()
    if run is None: pytest.skip('no JavaScript engine (node or jsc) runs here')
    page = open(os.path.join(HERE, 'review', 'page.html'), encoding='utf-8').read()
    def chunk(start, end): i = page.index(start); return page[i:page.index(end, i)]
    cases = [{'ai': 'la', 'latin_list': True},                                        # the confirmation
             {'ai': 'la', 'latin_list': False},                                       # not in the list: nothing, no warning
             {'ai': 'ja-Latn', 'latin_list': True},                                   # another language: nothing
             {'ai': None, 'latin_phrase': 'Prima <Facie>'},                           # the phrase note, quoted as printed (escaped)
             {'ai': 'la', 'latin_phrase': 'prima facie'},                             # tagged Latin: the phrase note is not shown
             {'ai': None, 'current': 'fr', 'latin_phrase': 'prima facie'},           # a publisher's tag: not shown
             {'ai': None, 'latin_list': True},                                        # untagged, no phrase: nothing
             {'ai': None, 'confidence': 'low', 'guess': 'la', 'latin_phrase': 'bona fide'},    # the AI's low guess is Latin (review 17)
             {'ai': None, 'confidence': 'low', 'guess': 'it', 'latin_phrase': 'bona fide'}]    # a low guess of another language
    code = (chunk('const esc = ', '\n') + '\n' + chunk('function langDict(', 'function langRowHtml(')
            + '\nconst cases = ' + json.dumps(cases) + ';\n(typeof print === "function" ? print : console.log)(JSON.stringify(cases.map(langDict)));')
    out = subprocess.run(run + [code], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    got = [re.sub(r'<[^>]+>', '', x) for x in json.loads(out.stdout)]
    assert got == ['Also found in a Latin dictionary.', '', '',
                   'Part of the Latin phrase "Prima &lt;Facie&gt;", used in English text. Decide whether it should be tagged as Latin.',
                   '', '', '',
                   'Part of the Latin phrase "bona fide". Decide whether it should be tagged as Latin.',
                   'Part of the Latin phrase "bona fide", used in English text. Decide whether it should be tagged as Latin.']
    assert "langDict(r) + (r.snippet ?" in page                                          # drawn under the AI's line in every row
