"""test_hanreading.py: words in Chinese characters alone decided by the reading printed beside them (#123), and the
reading kept as evidence for the review page's group approval (#124). Synthetic words and pages only; no network.

    python -m pytest tests/test_hanreading.py -q

#123's checks: a form with a reading at every place is decided locally, with its language; a form with one place
lacking a reading, or readings of two languages, goes to the AI; a word that introduces the characters (a colon,
semicolon or period after it: a publisher's name in a bibliography) is never their reading; the cost estimate leaves
locally decided forms out; a book whose forms are all decided locally sends nothing and needs no
network; the app runs such a step with a $0 cap, and never when the estimate left the step out.
"""
import json, os, sys, subprocess, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402
from test_name_languages import run, load, LAST, answer_all  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import plumb_fix, plpages, langcands, langreq, hanreading as H, costs  # noqa: F401,E402

HEAD = {'source': {'pages': 3}, 'headings': [{'page': 1, 'level': 'H1', 'text': 'Chapter One'}]}

def form(fid, places, cls=('cjk:han_only',), group='cjk'):
    return {'id': fid, 'form': places[0][3], 'group': group, 'class': list(cls),
            'places': [{'page': pg, 'w0': w0, 'w1': w0, 'text': t, 'class': list(cls), 'mcid': 0, 'first': 0, 'last': 0} for pg, w0, _, t in places]}

# ---------------------------------------------------------------- the rule itself (#123)
def test_a_reading_at_every_place_decides_the_form_locally():
    words = {'1': ['the', 'fan', '(fujō', '不浄', ').', 'later', 'fujō', '不浄', 'again']}
    f = form('1', [(1, 3, None, '不浄'), (1, 7, None, '不浄')])
    local, ev, st = H.decide([f], words, HEAD)
    assert local == {'1': {'lang': 'ja', 'confidence': 'high', 'why': 'language', 'rule': 'reading', 'evidence': 'the reading printed beside it: fujō'}}
    assert ev['1']['lang'] == 'ja' and ev['1']['with'] == 2 and st['decided'] == 1 and st['by_language'] == {'ja': 1}

def test_a_word_that_introduces_a_quotation_is_not_its_reading():
    """teika p. 145: "the Wakan rōeishū: 扶桑豈無影乎…" quotes a Chinese couplet; the anthology's title before the colon
    is not its reading. The pipeline's rule (strict) refuses it; the test tools' keys were made without the guard."""
    pw = ['appear', 'in', 'the', 'Wakan', 'rōeishū:', '扶桑豈無影乎', 'Is']
    assert H.beside(pw, 5, 5, 'japan', strict=True) == {} and H.beside(pw, 5, 5, 'japan') == {4: 'ja'}
    assert H.beside(['called', 'Kūkai', ';', '空海'], 3, 3, 'japan', strict=True) == {}           # such punctuation alone, too
    assert H.beside(['(Kūkai', '空海', ')'], 1, 1, 'japan', strict=True) == {0: 'ja'}
    assert H.beside(['youguan', 'gailiang\u201d', '全國生產'], 2, 2, 'china', strict=True) == {1: 'zh'}   # a quoted title's reading
    f = form('1', [(1, 5, None, '扶桑豈無影乎')])
    assert H.decide([f], {'1': pw}, HEAD)[0] == {}

def test_one_place_without_a_reading_goes_to_the_ai():
    words = {'1': ['the', 'fan', '(fujō', '不浄', ').', 'later', 'the', '不浄', 'again']}
    f = form('1', [(1, 3, None, '不浄'), (1, 7, None, '不浄')])
    local, ev, st = H.decide([f], words, HEAD)
    assert local == {} and st['not'] == {'no reading at some place': 1}
    assert ev['1']['lang'] == 'ja' and ev['1']['with'] == 1 and ev['1']['none'] == 1          # still evidence for #124

def test_readings_of_two_languages_go_to_the_ai():
    words = {'1': ['(fujō', '不浄', ')', 'and', '(zhongwen', '不浄', ')']}
    f = form('1', [(1, 1, None, '不浄'), (1, 5, None, '不浄')])
    local, ev, st = H.decide([f], words, HEAD)
    assert local == {} and st['not'] == {'readings of two languages': 1}
    assert ev['1']['lang'] is None and ev['1']['langs'] == ['ja', 'zh']                     # mixed: no language for #124

def test_glossary_and_bibliography_places_count_for_the_rule_but_not_as_group_evidence():
    """#123 is decided with every place, back matter included (Min, 2026-11-15: leaving it out cut 492 forms to 318 on a
    test book, all of them right; the colon guard refuses the bibliography's real trap). #124's evidence leaves
    bibliography entries out, as the issue asks; a glossary's or an index's reading still counts there."""
    words = {'1': ['(fujō', '不浄', ')'], '2': ['fujō', '不浄', 'impurity'], '3': ['Fujō', '不浄', 'ron', '1980.']}
    for title, kind, page in (('Glossary', 'glossary', 2), ('Bibliography', 'bibliography', 3), ('Index', 'index', 2)):
        d = {'source': {'pages': 3}, 'headings': [{'page': 1, 'level': 'H1', 'text': 'Chapter One'}, {'page': page, 'level': 'H1', 'text': title}]}
        f = form('1', [(1, 1, None, '不浄'), (page, 1, None, '不浄')])
        local, ev, st = H.decide([f], words, d)
        assert local['1']['lang'] == 'ja' and st['backmatter'][0]['kind'] == kind, title
        assert ev['1']['with'] == (1 if kind == 'bibliography' else 2) and ev['1']['back'] == (1 if kind == 'bibliography' else 0)

def test_a_publishers_name_before_a_title_is_not_its_reading():
    """The bibliography's trap ("Tokyo: Kōdansha. 自然と文化…", invented): the publisher's name ends with a period,
    so it introduces the title's characters and never reads them."""
    pw = ['Bunka.', 'Tokyo:', 'Kōdansha.', '自然と文化。']
    assert H.beside(pw, 3, 3, 'japan', strict=True) == {} and H.beside(pw, 3, 3, 'japan') == {2: 'ja'}

def test_kana_in_the_same_phrase_is_evidence_for_group_approval_only():
    """#124 counts kana in the same phrase as the characters (大福もち: the piece that holds them) as a Japanese reading;
    #123's rule, as measured, reads only what is beside the characters, so the form still goes to the AI."""
    words = {'1': ['sweets', 'like', '大福もち', 'and', 'more']}
    f = form('1', [(1, 2, None, '大福')])
    local, ev, st = H.decide([f], words, HEAD)
    assert local == {} and ev['1']['lang'] == 'ja' and ev['1']['reading'] == '大福もち'
    assert H.evidence(f, words, {}, 'japan', False)['lang'] is None                      # without phrase: no reading

def test_back_matter_runs_to_the_next_heading_of_its_level():
    d = {'source': {'pages': 30}, 'headings': [
        {'page': 3, 'level': 'H1', 'text': 'Chapter One'}, {'page': 20, 'level': 'H1', 'text': 'BIBLIOGRAPHY'},
        {'page': 20, 'level': 'H2', 'text': 'Primary Sources'}, {'page': 24, 'level': 'H2', 'text': 'Secondary Sources'},
        {'page': 26, 'level': 'H1', 'text': 'Index'}, {'page': 30, 'level': 'H1', 'text': 'About the Author'}],
        'heading_candidates': [{'page': 12, 'text': 'Glossary of Chinese Characters'}, {'page': 13, 'text': 'A long body heading'}]}
    pages, secs = H.backmatter(d)
    assert [(s['text'], s['kind'], s['pages']) for s in secs] == [('Glossary of Chinese Characters', 'glossary', [12, 13]),
                                                                   ('BIBLIOGRAPHY', 'bibliography', [20, 26]), ('Index', 'index', [26, 30])]
    assert 11 not in pages and pages[12] == {'glossary'} and pages[26] == {'bibliography', 'index'} and 19 not in pages
    assert H.backmatter({'headings': []}) == (None, [])

def test_back_matter_headings_are_named_whole():
    yes = ['BIBLIOGRAPHY', 'Selected Bibliography', 'Works Cited', 'References', 'Glossary', 'Glossary of Chinese Characters',
           'Character Glossary', 'Index of Poems Cited', 'Appendix B: Glossary', 'Sources Consulted', 'List of Characters', 'The Index']
    no = ['Sources of Japanese Tradition', 'References to the dead', 'Index fossils in the strata', 'Notes', 'Introduction', 'Theory of the Index']
    assert all(H.back_heading(t) for t in yes) and not any(H.back_heading(t) for t in no)
    assert [H.kind_of(t) for t in ('Works Cited', 'Index of Poems Cited', 'Character List')] == ['bibliography', 'index', 'glossary']

def test_no_headings_no_group_evidence_and_no_rule_in_a_cjk_document():
    words = {'1': ['(fujō', '不浄', ')']}
    f = form('1', [(1, 1, None, '不浄')])
    local, ev, st = H.decide([f], words, {'headings': []})
    assert local['1']['lang'] == 'ja' and ev == {} and 'no headings' in st['no_evidence']      # the bibliography can't be found
    local, ev, st = H.decide([f], words, HEAD, doc_lang='ja')
    assert local == {} and 'Japanese' in st['off']

def test_only_chinese_characters_alone_are_read():
    words = {'1': ['(fujō', '不浄', ')']}
    f = form('1', [(1, 1, None, '不浄')], cls=('cjk:mixed',))
    assert H.decide([f], words, HEAD)[0] == {}
    f = form('1', [(1, 1, None, '不浄')], group='existing')
    assert H.decide([f], words, HEAD)[0] == {}

def test_a_korean_book_needs_kana_for_japanese_and_a_japanese_book_hangul_for_korean():
    """tools/lang_test.py masked()'s guards: in a book on Korea a Hepburn-looking word beside Han is not Japanese
    evidence (only kana is); in a book on Japan a Revised Romanization word is never Korean evidence."""
    f = form('1', [(1, 1, None, '朝鮮')])
    ev = H.evidence(f, {'1': ['(Chōsen', '朝鮮', ')']}, {}, 'korea', False)
    assert ev['lang'] is None and ev['none'] == 1
    ev = H.evidence(f, {'1': ['(ちょうせん', '朝鮮', ')']}, {}, 'korea', False)
    assert ev['lang'] == 'ja'

# ---------------------------------------------------------------- the language step (name_languages.py)
RUNS = [{'tag': 'H1', 'text': 'Chapter One'},
        {'font': 'F2', 'text': 'The Pure Land (jodo, dōjō 極楽) and the hells 地獄 here.'},
        {'font': 'F2', 'text': 'Chinese texts (Zhongwen 中文) were read; dōjō 極楽 again.'}]

def folders(tmp_path, runs=RUNS, headings=True):
    src = langpdf.build(str(tmp_path / 'b.pdf'), runs)
    A = tmp_path / '_audit'; A.mkdir()
    json.dump(langcands.book(plpages.Pages(src), doc_lang='en'), open(A / 'lang_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump({'source': {'pages': 1}, 'headings': [{'page': 1, 'level': 'H1', 'text': 'Chapter One'}] if headings else []}, open(A / 'digest.json', 'w'))
    R = tmp_path / 'run'; R.mkdir()
    (R / 'workorder.json').write_text(json.dumps({'document': {'lang': 'en', 'title': 'T'}}))
    return src, A, R

def sent_forms(calls):
    return sorted(it['form'] for c in calls for it in json.loads(json.loads(c)['messages'][1]['content'])['items'])

def test_forms_decided_locally_are_never_sent(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    calls = run(src, A, R, monkeypatch, reply=answer_all('ja'))
    assert LAST['exit'] is None and len(calls) == 1
    assert '極楽' not in sent_forms(calls) and '中文' not in sent_forms(calls) and '地獄' in sent_forms(calls)
    lp = load(R / 'workorder.json')['language_parts']
    by = {f['form']: f for f in lp['forms']}
    assert by['極楽']['rule'] == 'reading' and by['極楽']['lang'] == 'ja' and by['極楽']['tag'] and 'dōjō' in by['極楽']['evidence']
    assert by['中文']['rule'] == 'reading' and by['中文']['lang'] == 'zh'
    assert by['極楽']['reading'] == {'lang': 'ja', 'langs': ['ja'], 'text': 'dōjō', 'with': 2, 'places': 2, 'back': 0}
    assert 'rule' not in by['地獄'] and 'reading' not in by['地獄']                         # no reading: the AI's, as before
    lr = load(R / 'language_run.json')
    assert sorted(lr['local']) == ['cjk|中文', 'cjk|極楽'] and lr['reading_rule']['decided'] == 2
    assert not any(k in lr['decisions'] for k in lr['local'])                              # the AI's decisions only
    assert sorted(p['form'] for p in langreq.expand(lp) if p['form'] in ('極楽', '中文', '地獄')) == ['中文', '地獄', '極楽', '極楽']

def test_the_estimate_leaves_locally_decided_forms_out(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    run(src, A, R, monkeypatch, '--dry-run')
    e = load(R / 'language_estimate.json')
    (tmp_path / 'off').mkdir(); src2, A2, R2 = folders(tmp_path / 'off')
    monkeypatch.setenv('LANG_READING_RULE', 'off')
    run(src2, A2, R2, monkeypatch, '--dry-run')
    e_off = load(R2 / 'language_estimate.json')
    assert e['local'] == 2 and e_off['local'] == 0 and e['forms'] == e_off['forms']
    assert e['sent'] == e_off['sent'] - 2 and e['worst_case_usd'] < e_off['worst_case_usd']

def test_the_rule_can_be_turned_off(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path)
    monkeypatch.setenv('LANG_READING_RULE', 'off')
    calls = run(src, A, R, monkeypatch, reply=answer_all('ja'))
    assert {'極楽', '中文', '地獄'} <= set(sent_forms(calls))
    lr = load(R / 'language_run.json')
    assert lr['local'] == {} and lr['reading_rule']['off'] == 'LANG_READING_RULE=off'
    by = {f['form']: f for f in load(R / 'workorder.json')['language_parts']['forms']}
    assert 'rule' not in by['極楽'] and by['極楽']['reading']['lang'] == 'ja'                  # the evidence stays for #124

def test_no_headings_still_decides_locally_but_keeps_no_evidence(tmp_path, monkeypatch):
    src, A, R = folders(tmp_path, headings=False)
    calls = run(src, A, R, monkeypatch, reply=answer_all('ja'))
    assert not {'極楽', '中文'} & set(sent_forms(calls)) and 'no headings' in load(R / 'language_run.json')['reading_rule']['no_evidence']
    by = {f['form']: f for f in load(R / 'workorder.json')['language_parts']['forms']}
    assert by['極楽']['rule'] == 'reading' and 'reading' not in by['極楽']                     # no evidence: one by one on the review page

def test_every_form_decided_locally_sends_nothing_and_needs_no_network(tmp_path, monkeypatch):
    runs = [{'tag': 'H1', 'text': 'Chapter One'}, {'font': 'F2', 'text': 'The Pure Land (と) 極楽 and texts (Zhongwen 中文).'}]   # kana: tagged locally, never sent
    src, A, R = folders(tmp_path, runs=runs)
    def no_network(*a, **k): raise AssertionError('no request of any kind when nothing is sent')
    for args in (('--dry-run',), ()):
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
        monkeypatch.setattr(sys, 'argv', ['name_languages.py', str(A), str(R), '--pdf', str(src), *args]); monkeypatch.chdir(HERE)
        monkeypatch.setattr(urllib.request, 'urlopen', no_network)
        import runpy
        runpy.run_path(os.path.join(HERE, 'name_languages.py'), run_name='__main__')
    e = load(R / 'language_estimate.json')
    assert e['to_send'] == 0 and e['local'] == 2 and e['worst_case_usd'] == 0
    lr = load(R / 'language_run.json')
    assert lr['cost_usd'] == 0 and lr['requests'] == [] and len(lr['local']) == 2
    assert sorted((p['form'], p['lang']) for p in langreq.expand(load(R / 'workorder.json')['language_parts'])) == [('中文', 'zh'), ('極楽', 'ja')]
    assert costs.language_estimate(str(R)) is None and costs.language_local(str(R)) == 2     # nothing to pay; the app still runs it
    # a retry reusing this run's own record (run_api.sh --reuse), and the record as a saved reply (LANG_REPLY=): the rule's
    # decisions again, never "not run" because the AI decided nothing
    wo = load(R / 'workorder.json'); wo.pop('language_parts'); (R / 'workorder.json').write_text(json.dumps(wo))
    for args in (('--reuse',), ('--response-file', str(R / 'language_run.json'))):
        monkeypatch.setattr(sys, 'argv', ['name_languages.py', str(A), str(R), '--pdf', str(src), *args])
        runpy.run_path(os.path.join(HERE, 'name_languages.py'), run_name='__main__')
        assert sorted(p['form'] for p in langreq.expand(load(R / 'workorder.json')['language_parts'])) == ['中文', '極楽'], args
        assert 'note' not in load(R / 'language_run.json')

def test_a_saved_reply_never_overrides_the_reading_rule(tmp_path, monkeypatch):
    """A saved reply (FROM=, REPLY=) made before #123 answered 極楽 itself: the rule decides it now, the same way every
    time; the saved answers apply to the rest and nothing is counted as vanished."""
    src, A, R = folders(tmp_path)
    saved = {'schema': 'language-run/1', 'decisions': {'cjk|極楽': {'lang': 'zh', 'confidence': 'high', 'why': 'language'},
                                                        'cjk|地獄': {'lang': 'ja', 'confidence': 'high', 'why': 'language'}}}
    (tmp_path / 'saved.json').write_text(json.dumps(saved))
    assert run(src, A, R, monkeypatch, '--response-file', tmp_path / 'saved.json') == []
    lr = load(R / 'language_run.json')
    assert lr['replay']['local_over_saved'] == 1 and lr['replay']['vanished_count'] == 0 and lr['replay']['used'] == 1
    by = {f['form']: f for f in load(R / 'workorder.json')['language_parts']['forms']}
    assert by['極楽']['lang'] == 'ja' and by['極楽']['rule'] == 'reading' and by['地獄']['lang'] == 'ja'

def test_run_api_runs_a_step_with_nothing_to_send_without_asking():
    """run_api.sh asks before the paid step; with every form decided locally there is nothing to pay, so it doesn't ask
    (an answer of no would lose free decisions). The condition it runs, on estimate files."""
    sh = open(os.path.join(HERE, 'run_api.sh'), encoding='utf-8').read()
    cond = sh.split("if python3 -c '", 1)[1].split("'", 1)[0]
    assert 'to_send' in cond and 'local' in cond
    def asks(e, tmp):
        p = os.path.join(tmp, 'e.json'); json.dump(e, open(p, 'w'))
        return subprocess.run([sys.executable, '-c', cond, p]).returncode != 0
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        assert not asks({'to_send': 0, 'local': 3}, t)
        assert asks({'to_send': 2, 'local': 3}, t) and asks({'to_send': 0, 'local': 0}, t) and asks({'to_send': 0}, t)
    assert 'nothing to ask' in sh

# ---------------------------------------------------------------- the app (lib/costs.py, webapp/spend.py)
def test_the_app_runs_a_local_only_step_with_a_zero_cap():
    from webapp import spend
    assert spend.language_env({'language': None, 'bounds': {}, 'language_local': 4, 'left_out': []}) == {'LANG_TAGS': 'on', 'LANGUAGE_MAX_USD': '0.00'}
    assert spend.language_env({'language': None, 'bounds': {}, 'language_local': 0, 'left_out': []}) == {}
    left = [{'kind': 'language', 'words': 'left out'}]
    assert spend.language_env({'language': None, 'bounds': {}, 'language_local': 4, 'left_out': left}) == {}     # left out: off, as before
    with_ai = {'language': {'model': 'anthropic/claude-sonnet-5.5'}, 'bounds': {'LANGUAGE_MAX_USD': 1.5}, 'language_local': 4}
    assert spend.language_env(with_ai)['LANGUAGE_MAX_USD'] == '1.50'

def test_language_local_reads_the_estimate(tmp_path):
    R = str(tmp_path)
    assert costs.language_local(R) == 0
    json.dump({'local': 5, 'to_send': 0, 'worst_case_usd': 0}, open(tmp_path / 'language_estimate.json', 'w'))
    assert costs.language_local(R) == 5
    json.dump({'local': 5, 'to_send': 0, 'refused': {'why': 'cap'}}, open(tmp_path / 'language_estimate.json', 'w'))
    assert costs.language_local(R) == 0
