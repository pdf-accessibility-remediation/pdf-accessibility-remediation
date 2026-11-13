"""test_language_parts.py: language tags on words and passages, through apply.py and verify.py (#118, language tagging).

    python -m pytest tests/test_language_parts.py -q

Synthetic pages only (tests/langpdf.py), veraPDF off, the tag-tree check mode on (conftest). Checks:
  - a place inside a run is split out and tagged; a place that is its whole run is tagged as a run;
  - the page looks the same and reads the same text (verify.py), and no index entry dangles;
  - the /Lang inside a run's marks is removed wherever a tag is added, for whole runs too (today's CJK tags), so the
    marks never override the tag (review 02, H1); verify.py's language section finds every Span it should;
  - the work-order check keeps valid parts and drops bad ones (review 02, L2); the audit's candidates line up with the runs.
"""
import os, sys, json, subprocess
import pikepdf, pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, langcands, workorder_check  # noqa: F401,E402

def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off'),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stderr[-2000:]
    return r

def apply_verify(tmp_path, runs, parts, doc_lang='en'):
    src = langpdf.build(str(tmp_path / 'src.pdf'), runs, doc_lang)
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'language_parts': {'parts': parts}}))
    out = str(tmp_path / 'out.pdf')
    run('apply.py', src, wo, out); run('verify.py', src, out)
    return src, out, json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))

def part(page, mcid, first, last, lang): return {'page': page, 'mcid': mcid, 'first': first, 'last': last, 'lang': lang}

def marks(path):
    pdf = pikepdf.open(path)
    return {int(x.operands[1].MCID): dict(x.operands[1]) for x in pikepdf.parse_content_stream(pdf.pages[0])
            if str(x.operator) == 'BDC' and isinstance(x.operands[1], pikepdf.Dictionary) and '/MCID' in x.operands[1]}

def test_split_and_whole_runs_tagged(tmp_path):
    runs = [{'lang': 'en-US', 'text': 'The city of Heiankyo was the capital.'},           # a word inside a run
            {'lang': 'en-US', 'outside': True, 'text': 'He chanted namu amida butsu daily.'},  # a phrase, marks outside BT
            {'lang': 'en-US', 'font': 'F3', 'text': 'mappō'},                                          # a whole run
            {'lang': 'en-US', 'text': 'Plain English text stays as it is.'}]
    parts = [part(1, 0, 12, 19, 'ja-Latn'), part(1, 1, 11, 26, 'ja-Latn'), part(1, 2, 0, 4, 'ja-Latn')]
    src, out, log, v = apply_verify(tmp_path, runs, parts)
    lp = log['language_parts']
    assert lp['split'] == 2 and lp['whole'] == 1 and not lp['refused'], lp
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['index']['dangling'] == 0
    lg = v['language']
    assert lg['spans_written'] == 3 and lg['all_match'], lg
    texts = sorted(s['text'] for s in lp['spans'])
    assert texts == ['Heiankyo', 'mappō', 'namu amida butsu']
    m = marks(out)
    for s in lp['spans']: assert '/Lang' not in m[s['mcid']]                         # H1: the tagged marks name no language
    assert str(m[3]['/Lang']) == 'en-US'                                               # untouched runs keep theirs

def test_today_cjk_tags_lose_the_marks_lang(tmp_path):
    """review 02, H1, on today's rule: a kana run is tagged ja as before, and the en-US inside its marks is removed."""
    runs = [{'lang': 'en-US', 'font': 'F2', 'text': 'Plain text.'}, {'lang': 'en-US', 'text': 'more'}]
    src = langpdf.build(str(tmp_path / 'k.pdf'), runs)
    # make run 1 a kana run: redraw it with the two-byte font's codes for a kana character is not possible (the font has
    # none), so the whole-run path is exercised through an explicit work-order run instead
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'language': {'runs': [{'page': 1, 'mcid': 1, 'lang': 'ja'}]}}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out); run('verify.py', src, out)
    assert '/Lang' not in marks(out)[1] and str(marks(out)[0]['/Lang']) == 'en-US'
    v = json.load(open(out + '.verify.json'))
    assert v['language']['all_match'] and v['language']['spans_written'] == 1
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []

def test_publisher_tag_over_english_marks_is_listed(tmp_path):
    """globalasias's case: the publisher's Span says ja, its marks say en-US. Listed, not counted as apply.py's."""
    runs = [{'lang': 'en-US', 'span_lang': 'ja', 'text': 'shiritori'}]
    src = langpdf.build(str(tmp_path / 'p.pdf'), runs)
    wo = tmp_path / 'wo.json'; wo.write_text('{}'); out = str(tmp_path / 'out.pdf')
    run('apply.py', src, wo, out); run('verify.py', src, out)
    lg = json.load(open(out + '.verify.json'))['language']
    assert lg['publisher_conflicts'] == 1 and lg['all_match'] and lg['spans_written'] == 0

def test_refused_under_actual_text(tmp_path):
    runs = [{'text': 'The city of Heiankyo was the capital.', 'actual_text': 'The city of Heian-kyo was the capital.'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 12, 19, 'ja-Latn')])
    assert log['language_parts']['refused'] == {'under an element with its own spoken or alt text': 1}
    assert v['language']['spans_written'] == 0

def test_differences_font_split(tmp_path):
    runs = [{'font': 'F3', 'lang': 'en-US', 'text': 'Ryōgen wrote of mappō then.'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 16, 20, 'ja-Latn')])
    assert log['language_parts']['split'] == 1, log['language_parts']
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert log['language_parts']['spans'][0]['text'] == 'mappō'

def test_two_places_in_one_run(tmp_path):
    runs = [{'text': 'Both mappo and shingon here.'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 5, 9, 'ja-Latn'), part(1, 0, 15, 21, 'ja-Latn')])
    assert log['language_parts']['split'] == 2 and v['language']['all_match']
    assert sorted(s['text'] for s in log['language_parts']['spans']) == ['mappo', 'shingon']

def test_check_language_parts():
    wo = {'language_parts': {'parts': [part(1, 0, 0, 3, 'ja-Latn'), part(1, 0, 2, 5, 'ja'), part(1, 1, 0, 1, 'jp'),
                                       part(1, 2, 0, 1, 'eng'), part(9, 0, 0, 1, 'ja'), part(1, 3, 4, 2, 'ja'),
                                       part(1, 4, 0, 1, 'iw'), {**part(1, 5, 0, 1, 'ja'), 'extra': 1}, part(1, 6, 0, 1, 'qaa')]}}
    dropped = workorder_check.check_language_parts(wo, 2)
    whys = [d['why'] for d in dropped]
    assert [p['mcid'] for p in wo['language_parts']['parts']] == [0, 6]
    assert any('overlaps' in w for w in whys) and any("'jp'" in w for w in whys) and any('shortest form: en' in w for w in whys)
    assert any('page not in the book' in w for w in whys) and any('not in order' in w for w in whys)
    assert any("'iw'" in w for w in whys) and any('unknown keys' in w for w in whys)

def test_candidates_line_up_with_runs(tmp_path):
    """The audit's places are character indexes that apply.py's split uses as they are."""
    runs = [{'lang': 'en-US', 'font': 'F3', 'text': 'The city of Heiankyo saw ryōgen begin.'},
            {'font': 'F6', 'lang': 'en-US', 'text': 'kokua'},
            {'text': 'He wrote E iho ana o luna here.'}]
    src = langpdf.build(str(tmp_path / 'c.pdf'), runs)
    PL = plpages.Pages(src)
    places, words = langcands.page_places(1, PL.pages[0].chars)
    got = {(p['mcid'], p['text']): p for p in places}
    assert (0, 'ryōgen') in got and 'marks' in got[(0, 'ryōgen')]['class']
    assert got[(1, 'kokua')]['italic'] and got[(1, 'kokua')]['whole']
    assert (2, 'E iho ana o luna') in got and 'hawaiian' in got[(2, 'E iho ana o luna')]['class']
    parts = [{'page': 1, 'mcid': p['mcid'], 'first': p['first'], 'last': p['last'], 'lang': 'qaa'} for p in places]
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'language_parts': {'parts': parts}}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out); run('verify.py', src, out)
    v = json.load(open(out + '.verify.json')); log = json.load(open(out + '.log.json'))
    assert not log['language_parts']['refused'] and v['language']['all_match'] and v['language']['spans_written'] == len(places)
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0

def test_form_mcid_that_shares_a_number_is_never_tagged(tmp_path):
    """pdfplumber lists text drawn in a form XObject under the form's own MCIDs; one may share its number with a page run
    (#118 stress run, sojourners). A place on it is refused, and the page run with that number is left alone."""
    src = langpdf.build(str(tmp_path / 'f.pdf'), [{'lang': 'en-US', 'text': 'Plain page text.'}])
    pdf = pikepdf.open(src); page = pdf.pages[0]
    form = pdf.make_stream(b'/P <</MCID 0>> BDC BT /F1 11 Tf 72 600 Td (kalo) Tj ET EMC',
                           Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, 612, 792],
                           Resources=pikepdf.Dictionary(Font=page.obj.Resources.Font))
    page.obj.Resources.XObject = pikepdf.Dictionary(Fm1=form)
    page.obj.Contents = pdf.make_stream(page.obj.Contents.read_bytes() + b'\nq /Fm1 Do Q')
    src2 = str(tmp_path / 'f2.pdf'); pdf.save(src2)
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'language_parts': {'parts': [part(1, 0, 0, 3, 'haw')]}}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src2, wo, out)
    log = json.load(open(out + '.log.json'))
    assert log['language_parts']['spans'] == [] and sum(log['language_parts']['refused'].values()) == 1
    assert str(marks(out)[0]['/Lang']) == 'en-US'

def test_cjk_rule_never_tags_a_form_run_under_a_page_runs_number(tmp_path):
    """op_language's CJK rule (and a work order's explicit runs) check the run the same way: text drawn in a form
    XObject under MCID 0 must not get a page run 0 tagged (#118, 04 §6 item 1)."""
    src = langpdf.build(str(tmp_path / 'f.pdf'), [{'lang': 'en-US', 'text': 'Plain page text.'}])
    pdf = pikepdf.open(src); page = pdf.pages[0]
    form = pdf.make_stream(b'/P <</MCID 0>> BDC BT /F1 11 Tf 72 600 Td (kana) Tj ET EMC',
                           Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, 612, 792],
                           Resources=pikepdf.Dictionary(Font=page.obj.Resources.Font))
    page.obj.Resources.XObject = pikepdf.Dictionary(Fm1=form)
    page.obj.Contents = pdf.make_stream(page.obj.Contents.read_bytes() + b'\nq /Fm1 Do Q')
    src2 = str(tmp_path / 'f2.pdf'); pdf.save(src2)
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'language': {'runs': [{'page': 1, 'mcid': 0, 'lang': 'ja'}]}}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src2, wo, out)
    log = json.load(open(out + '.log.json'))
    assert log['language_parts']['spans'] == [] and log['language_parts']['refused'] == {'characters do not line up with the run': 1}
    assert str(marks(out)[0]['/Lang']) == 'en-US'
    res = pikepdf.open(out)
    assert not any(str(k.get('/S')) == '/Span' for k in res.Root.StructTreeRoot.K[0].K)

# ---- review 06, H1: the local rule comes first on runs the language step touches
def lang_of_span_over(out, text):
    """The /Lang of the Span whose marked content holds exactly `text` (pdfplumber), or None."""
    from lib import plumb_fix, plpages  # noqa: F401
    by = {}
    for c in plpages.Pages(out).pages[0].chars:
        if c.get('mcid') is not None: by.setdefault(c['mcid'], []).append(c['text'])
    pdf = pikepdf.open(out); st = pdf.Root.StructTreeRoot
    arr = st.ParentTree.Nums[1]
    for m, t in by.items():
        el = arr[m] if m < len(arr) else None
        while el is not None and isinstance(el, pikepdf.Dictionary) and '/Lang' not in el: el = el.get('/P')
        if ''.join(t) == text and el is not None and '/Lang' in el: return str(el.Lang)
    return None

def test_a_kana_run_keeps_its_ja_when_the_ai_tags_part_of_it(tmp_path):
    runs = [{'font': 'F2', 'lang': 'en-US', 'text': '地獄と極楽'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 0, 1, 'ja')])           # 地獄: the same language as the run's
    lp = log['language_parts']
    assert lp['whole'] == 1 and lp['split'] == 0 and lp['dropped_by_local_rule'] == 1
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert '/Lang' not in marks(out)[0]

def test_a_part_in_another_language_is_split_under_the_runs_span(tmp_path):
    runs = [{'font': 'F2', 'lang': 'en-US', 'text': '地獄と極楽'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 3, 4, 'zh')])           # 極楽 said to be Chinese
    lp = log['language_parts']
    assert lp['whole'] == 1 and lp['split'] == 1
    whole = next(s for s in lp['spans'] if s['whole'])
    assert whole['lang'] == 'ja' and len(whole['mcids']) == 2 and whole['text'] == '地獄と極楽'
    assert v['language']['all_match'] and v['language']['spans_written'] == 2, v['language']
    assert lang_of_span_over(out, '極楽') == 'zh' and lang_of_span_over(out, '地獄と') == 'ja'
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0

def test_han_the_ai_left_untagged_goes_back_on_the_deferred_list(tmp_path):
    runs = [{'font': 'F2', 'lang': 'en-US', 'text': '地獄 極楽 中文'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 0, 1, 'ja')])           # only 地獄 tagged
    assert [h['mcid'] for h in log['han_only']] == [0]
    (tmp_path / 'b').mkdir()
    src2, out2, log2, v2 = apply_verify(tmp_path / 'b', runs, [part(1, 0, 0, 1, 'ja'), part(1, 0, 3, 4, 'ja'), part(1, 0, 6, 7, 'zh')])
    assert log2['han_only'] == []                                                     # every Han place tagged: nothing left

def test_a_path_inside_the_run_does_not_open_the_form_mcid_guard(tmp_path):
    """review 06, M1: the page's run 0 draws a rule inside its marks (the split would refuse it for that), and a form on
    the page draws kana under its own MCID 0. The count check still sees the page run's own characters only, so the CJK
    tag (here an explicit run) is refused instead of landing on the English run."""
    src = langpdf.build(str(tmp_path / 'p.pdf'), [{'lang': 'en-US', 'body': ['(Plain page text.) Tj', 'ET', '72 700 m 300 700 l S', 'BT /F1 11 Tf 72 690 Td', '(more) Tj'], 'outside': True}])
    pdf = pikepdf.open(src); page = pdf.pages[0]
    form = pdf.make_stream(b'/P <</MCID 0>> BDC BT /F1 11 Tf 72 600 Td (kana) Tj ET EMC',
                           Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, 612, 792],
                           Resources=pikepdf.Dictionary(Font=page.obj.Resources.Font))
    page.obj.Resources.XObject = pikepdf.Dictionary(Fm1=form)
    page.obj.Contents = pdf.make_stream(page.obj.Contents.read_bytes() + b'\nq /Fm1 Do Q')
    src2 = str(tmp_path / 'p2.pdf'); pdf.save(src2)
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'language': {'runs': [{'page': 1, 'mcid': 0, 'lang': 'ja'}]}}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src2, wo, out)
    log = json.load(open(out + '.log.json'))
    assert log['language_parts']['spans'] == [] and log['language_parts']['refused'] == {'characters do not line up with the run': 1}

def test_a_run_whose_entry_moved_keeps_the_page_whole(tmp_path, monkeypatch):
    """review 06, M6: when a run's tag entry can't be found at the late pass, its page keeps its content (only the marks
    edits are written), its places are refused with a reason, and the other pages go on."""
    monkeypatch.setenv('APPLY_TEST_LOSE_ENTRY', '1')
    runs = [{'lang': 'en-US', 'text': 'The city of Heiankyo was the capital.'}]
    src, out, log, v = apply_verify(tmp_path, runs, [part(1, 0, 12, 19, 'ja-Latn')])
    lp = log['language_parts']
    assert lp['split'] == 0 and lp['refused'] == {"the run's tag entry moved before the split was written": 1}
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0
    assert not any(f['op'].startswith('fix_language_parts') for f in log['failed'])

def test_hawaiian_lines_on_page_read_pages_are_tagged_whole(tmp_path):
    """L6 of 03: on a page read whole (page readings), an element whose words are mostly Hawaiian-shape gets /Lang haw on
    itself; an English line, and a page not read, stay as they are."""
    src = langpdf.build(str(tmp_path / 'h.pdf'), [{'text': 'Ua hele mai ka wahine i ka hale'}, {'text': 'The house stood on the hill above the bay'}])
    w = tmp_path / 'wo.json'; w.write_text(json.dumps({'page_readings': [{'page': 1, 'text': 'Ua hele mai ka wahine i ka hale The house stood on the hill above the bay'}]}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, w, out); run('verify.py', src, out)
    P = pikepdf.open(out); els = P.Root.StructTreeRoot.K[0].K
    assert str(els[0].get('/Lang')) == 'haw' and '/Lang' not in els[1]
    v = json.load(open(out + '.verify.json')); assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []
    assert v['language']['haw_elements'] == 1 and v['language']['all_match']                 # review 08, H2: verify counts them
    el = json.load(open(out + '.log.json'))['haw_elements']['elements']
    assert len(el) == 1 and el[0]['page'] == 1 and el[0]['text'].startswith('Ua hele mai')   # listed for the Hawaiian reader
    w.write_text(json.dumps({}))
    out2 = str(tmp_path / 'out2.pdf'); run('apply.py', src, w, out2)
    P2 = pikepdf.open(out2); assert '/Lang' not in P2.Root.StructTreeRoot.K[0].K[0]

def test_the_letter_guard_keeps_other_pacific_languages_untagged(tmp_path):
    """review 08, H2: a line with a word outside the English list that uses a letter Hawaiian lacks (te, whare, fiefia) is
    not Hawaiian, though most of its words have Hawaiian shape; a word the page reading corrected (an OCR misreading with
    rn for m) is read as the reading has it. Sentences written for the test (the reviewer's), not from any book."""
    lines = [{'text': 'He maunga he awa he moana. Ko te whare nui o te iwi.'},          # Māori
             {'text': 'Malo e lelei. Oku ou fiefia ke u alu ki he fale.'},                # Tongan (marks left out: Helvetica)
             {'text': 'He mea rnaikai loa ia no ka poe o ka aina.'}]                      # Hawaiian, with an OCR misreading
    src = langpdf.build(str(tmp_path / 'g.pdf'), lines)
    w = tmp_path / 'wo.json'
    w.write_text(json.dumps({'page_readings': [{'page': 1, 'text': ' '.join(l['text'] for l in lines).replace('rnaikai', 'maikaʻi')}]}))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, w, out)
    P = pikepdf.open(out); els = P.Root.StructTreeRoot.K[0].K
    assert [str(e.get('/Lang', '')) for e in els] == ['', '', 'haw']
    log = json.load(open(out + '.log.json'))['haw_elements']
    assert log['tagged'] == 1 and log['ruled_out'] == 2

def test_the_letter_guard_on_words_and_pages():
    from lib import ocrwords, pagereads
    assert [ocrwords.not_hawaiian_letters(x) for x in ('te', 'whare', 'fiefia', 'ngangi', 'hale', 'kākou', 'kakoü', 'Häwaii', 'the', 'sulphates')] == \
        [True, True, True, True, False, False, False, False, False, True]
    haw = 'Aloha mai kākou. E hele ana au i ka hale kūʻai. He mea maikaʻi loa ia no ka poʻe o ka ʻāina.'.split() * 6
    mao = 'Kei te pēhea koe? Kia ora koe e hoa. He maunga, he awa, he moana. Ko te whare nui o te iwi.'.split() * 6
    assert pagereads.hawaiian_page(haw)[1] == 0 and pagereads.hawaiian_page(mao)[1] >= pagereads.FOREIGN_MAX
    assert pagereads.hawaiian_page(mao)[0] >= pagereads.SHARE_MIN          # the shape test alone would select it
