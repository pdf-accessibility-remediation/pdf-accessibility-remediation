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
