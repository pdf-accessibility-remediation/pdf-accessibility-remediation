"""One language tag over several marked-content runs (#150, #161; language_parts version 3), through apply.py and
verify.py. Made-up words on tiny tagged PDFs (tests/langpdf.build_lines), veraPDF off.

A phrase is tagged whole or not at all (review 02 H3, review 04 H3a/H3b): nothing is written into the tree before the
late pass, a refused phrase takes back only its own marks edits, and verify.py checks a phrase's Span exactly (review 02 M2).
"""
import os, sys, json, subprocess
import pikepdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langpdf  # noqa: E402

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PIPE)
from lib import plumb_fix, plpages, langcands, langreq, workorder_check  # noqa: F401,E402


def run(script, *args, env=None):
    r = subprocess.run([sys.executable, os.path.join(PIPE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off', **(env or {})),
                       capture_output=True, text=True, cwd=PIPE)
    assert r.returncode == 0, r.stderr[-2000:]
    return r


def wo_of(forms_rows):
    """forms_rows: [(form, lang, [rows])], a row [page, mcid, first, last] or [page, segments] -> a work order of version 2 or 3."""
    forms, rows = [], []
    for i, (form, lang, rs) in enumerate(forms_rows):
        forms.append({'key': f'unknown|{form}', 'form': form, 'group': 'unknown', 'class': ['unknown'], 'lang': lang,
                      'confidence': 'high', 'why': 'language', 'tag': True, 'places': len(rs)})
        rows += [list(r) + [i] if len(r) == 4 else [r[0], r[1], i] for r in rs]
    return {'language_parts': {'version': 3 if any(len(r) == 3 for r in rows) else 2, 'forms': forms, 'parts': rows}}


def apply_verify(tmp_path, lines, wo, env=None, name='src.pdf'):
    src = langpdf.build_lines(str(tmp_path / name), lines)
    p = tmp_path / 'wo.json'; p.write_text(json.dumps(wo))
    out = str(tmp_path / ('out-' + name))
    run('apply.py', src, p, out, env=env); run('verify.py', src, out)
    return src, out, json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))


def marks(path):
    pdf = pikepdf.open(path)
    return {int(x.operands[1].MCID): dict(x.operands[1]) for x in pikepdf.parse_content_stream(pdf.pages[0])
            if str(x.operator) == 'BDC' and isinstance(x.operands[1], pikepdf.Dictionary) and '/MCID' in x.operands[1]}


def spans(path):
    pdf = pikepdf.open(path); out = []
    def walk(n, d=0):
        if d > 40 or not isinstance(n, pikepdf.Dictionary): return
        if str(n.get('/S', '')) == '/Span' and '/Lang' in n:
            k = n.get('/K'); ks = list(k) if isinstance(k, pikepdf.Array) else [k]
            out.append((str(n.Lang), [int(x) if isinstance(x, int) else int(x.MCID) for x in ks], str(n.P.get('/S')).lstrip('/')))
        k = n.get('/K')
        for x in (list(k) if isinstance(k, pikepdf.Array) else [k]): walk(x, d + 1)
    walk(pdf.Root.StructTreeRoot)
    return out


OCR = [{'text': 'The ', 'lang': 'en-US'}, {'text': 'velunka ', 'lang': 'en-US'}, {'text': 'toramio ', 'lang': 'en-US'},
       {'text': 'pasquet ', 'lang': 'en-US'}, {'text': 'here.', 'lang': 'en-US'}]
PHRASE = [('velunka toramio pasquet', 'haw', [[1, [[1, 0, 7], [2, 0, 7], [3, 0, 6]]]])]


def test_one_span_over_three_whole_runs(tmp_path):
    src, out, log, v = apply_verify(tmp_path, [OCR], wo_of(PHRASE))
    lp = log['language_parts']
    assert lp['phrases'] == 1 and not lp['refused'], lp
    assert spans(out) == [('haw', [1, 2, 3], 'P')]
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0
    assert v['language']['all_match'] and v['language']['spans_written'] == 1, v['language']
    m = marks(out)
    assert all('/Lang' not in m[k] for k in (1, 2, 3)) and str(m[0]['/Lang']) == 'en-US' and str(m[4]['/Lang']) == 'en-US'


LONG = [{'text': 'These words are all made up: velunk', 'lang': 'en-US'}, {'text': 'a', 'lang': 'en-US'},
        {'text': ' and more words come here today.', 'lang': 'en-US'}]


def test_partial_first_and_last_segments_are_split_and_joined_under_one_span(tmp_path):
    src = langpdf.build_lines(str(tmp_path / 'f.pdf'), [LONG])
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf)
    p = next(p for p in c['places'] if p['form'] == 'velunka')
    wo = wo_of([('velunka', 'haw', [[1, p['segments']]])])
    src, out, log, v = apply_verify(tmp_path, [LONG], wo)
    sp = spans(out)
    assert len(sp) == 1 and sp[0][0] == 'haw' and sp[0][1][-1] == 1 and len(sp[0][1]) == 2, sp
    assert v['language']['all_match'] and v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['index']['dangling'] == 0
    m = marks(out)
    assert all('/Lang' not in m[k] for k in sp[0][1])


def test_a_phrase_under_two_elements_is_refused_whole_and_listed_once(tmp_path):
    line = [dict(x) for x in OCR]; line[2]['parent'] = 'P1'
    src, out, log, v = apply_verify(tmp_path, [line], wo_of(PHRASE))
    lp = log['language_parts']
    assert spans(out) == [] and lp['refused'] == {'its words sit under different tags': 1} and len(lp['refused_places']) == 1
    assert all(str(marks(out)[k]['/Lang']) == 'en-US' for k in (1, 2, 3))


def test_a_lost_entry_refuses_an_all_whole_runs_phrase_and_takes_back_its_marks_edits(tmp_path):
    src, out, log, v = apply_verify(tmp_path, [OCR], wo_of(PHRASE), env={'APPLY_TEST_LOSE_ENTRY': '1'})
    assert spans(out) == [] and 'phrases' not in log['language_parts']
    assert all(str(marks(out)[k]['/Lang']) == 'en-US' for k in (1, 2, 3))             # no run left with its /Lang taken and no Span
    assert v['language']['all_match']


def test_a_forced_pixel_failure_on_the_last_segment_refuses_the_whole_phrase(tmp_path):
    src = langpdf.build_lines(str(tmp_path / 'f.pdf'), [LONG])
    with pikepdf.open(src) as pdf: c = langcands.book(plpages.Pages(src), doc_lang='en', pdf=pdf)
    segs = next(p for p in c['places'] if p['form'] == 'velunka')['segments']
    src, out, log, v = apply_verify(tmp_path, [LONG], wo_of([('velunka', 'haw', [[1, segs]])]), env={'APPLY_TEST_PIXEL_FAIL_RUN': '1:0'})
    lp = log['language_parts']
    assert spans(out) == [] and lp['refused'] == {'the page would look different': 1}, lp
    m = marks(out)
    assert all(str(m[k]['/Lang']) == 'en-US' for k in (0, 1, 2)) and len(m) == 3        # the content as it was: no split kept
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == []


def test_a_persons_removal_and_a_local_tag_stay_beside_a_refused_phrase(tmp_path):
    """review 04 H3b: on the page of a refused phrase, a publisher's tag a person removed is still removed, and a run the
    local rule tags whole (hangul: ko) still loses the /Lang in its marks."""
    line = OCR + [{'text': ' oui', 'lang': 'fr'}, {'text': ' 한국어', 'font': 'F2', 'lang': 'en-US'}]
    wo = wo_of(PHRASE)
    lp = wo['language_parts']
    lp['forms'].append({'key': 'existing|oui|fr', 'form': 'oui', 'group': 'existing', 'class': ['existing'], 'current': 'fr',
                        'lang': None, 'tag': False, 'decided': 'remove', 'places': 1})
    lp['parts'].append([1, 5, 0, 3, 1])
    src, out, log, v = apply_verify(tmp_path, [line], wo, env={'APPLY_TEST_LOSE_ENTRY': '1'})
    m = marks(out)
    assert spans(out) == [('ko', [6], 'P')]                  # the phrase refused; the local Korean tag written
    assert '/Lang' not in m[5] and '/Lang' not in m[6]       # the removal, and the local tag's marks edit, both kept
    assert all(str(m[k]['/Lang']) == 'en-US' for k in (1, 2, 3))
    assert log['language_parts'].get('existing_removed') == 1


def test_verify_catches_a_run_moved_out_of_the_phrase_span(tmp_path):
    src, out, log, v = apply_verify(tmp_path, [OCR], wo_of(PHRASE))
    with pikepdf.open(out, allow_overwriting_input=True) as pdf:
        st = pdf.Root.StructTreeRoot; arr = st.ParentTree.Nums[1]
        sp = arr[3]; par = sp.P
        sp.K = pikepdf.Array([1, 2]); par.K.append(3)
        arr[3] = par                                           # run 3 now sits under the P that carries no language
        pdf.save(out)
    run('verify.py', src, out)
    lg = json.load(open(out + '.verify.json'))['language']
    assert not lg['all_match'] and lg['mismatch_examples'][0]['why'] in ('its runs sit under different tags', 'its tag holds other runs')


def test_rows_of_both_shapes_read_alike_everywhere():
    lp = wo_of(PHRASE + [('mappō', 'ja-Latn', [[1, 4, 0, 4]])])['language_parts']
    assert list(langreq.rows(lp)) == [(1, [[1, 0, 7], [2, 0, 7], [3, 0, 6]], 0), (1, [[4, 0, 4]], 1)]
    got = langreq.expand(lp)
    assert got[0]['segments'] == [[1, 0, 7], [2, 0, 7], [3, 0, 6]] and got[0]['mcid'] == 1 and 'segments' not in got[1]
    wo = {'language_parts': json.loads(json.dumps(lp))}
    assert workorder_check.check_language_parts(wo, 1) == [] and len(wo['language_parts']['parts']) == 2


def test_the_check_drops_bad_segmented_rows_with_their_reasons():
    lp = wo_of(PHRASE)['language_parts']
    lp['parts'] += [[1, [[1, 3, 2], [2, 0, 1]], 0], [1, [[1, 0, 1], [1, 2, 3]], 0], [1, [[5, 0, 1]], 0], [1, [[9, 0, 1], [10, 0, 1]], 7],
                    [1, 1, 2, 4, 0]]
    wo = {'language_parts': lp}
    why = [d['why'] for d in workorder_check.check_language_parts(wo, 1)]
    assert why == ['run or character indexes not in order', 'a run appears twice in one place', 'segments not lists of three whole numbers',
                   'no such form', 'overlaps another part in the same run']


def test_version_2_rows_are_written_and_checked_as_before():
    fs = [{'id': '1', 'form': 'mappō', 'group': 'marks', 'class': ['marks'], 'places': [{'page': 1, 'mcid': 2, 'first': 0, 'last': 4}]}]
    lp = langreq.to_rows(fs, {'1': {'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language'}})
    assert json.dumps(lp, ensure_ascii=False) == json.dumps({'version': 2, 'forms': [{
        'key': 'marks|mappō', 'form': 'mappō', 'group': 'marks', 'class': ['marks'], 'lang': 'ja-Latn', 'confidence': 'high', 'why': 'language',
        'tag': True, 'places': 1}], 'parts': [[1, 2, 0, 4, 0]]}, ensure_ascii=False)
    bad = {'language_parts': {'version': 2, 'forms': lp['forms'], 'parts': [[1, 2, 0], [2, 2, 0, 4, 0], [1, -1, 0, 4, 0], [1, 2, 0, 4, 3], [1, 2, 0, 4, 0], [1, 2, 3, 5, 0]]}}
    assert [d['why'] for d in workorder_check.check_language_parts(bad, 1)] == ['not five whole numbers', 'page not in the book',
                                                                                 'run or character indexes not in order', 'no such form',
                                                                                 'overlaps another part in the same run']


def test_no_module_reads_language_rows_by_their_length_or_version():
    import re as _re
    bad = []
    for root, _d, files in os.walk(PIPE):
        if '.venv' in root or os.sep + 'tests' in root or '__pycache__' in root: continue
        for f in files:
            if not f.endswith('.py') or f == 'langreq.py': continue
            t = open(os.path.join(root, f), encoding='utf-8').read()
            for pat in (r"len\(r_?\) == 5", r"get\('version'\) [!=]= 2"):
                for mm in _re.finditer(pat, t):
                    line = t[:mm.start()].count('\n') + 1
                    if 'language' in t[max(0, mm.start() - 400):mm.end() + 400]: bad.append(f'{f}:{line}')
    assert bad == [], bad
