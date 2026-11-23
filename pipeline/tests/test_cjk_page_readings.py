"""test_cjk_page_readings.py: AI readings of scanned CJK pages (#119), from the audit to the output PDF. Synthetic PDFs only
(an OCRmyPDF-shaped invisible layer built here: one text object per line, a Type0 font with a ToUnicode map); no
Tesseract, no network (read_pages.py runs against a fake OpenRouter).

    python -m pytest tests/test_cjk_page_readings.py -q

Checks: a CJK page's reading is matched to the OCR's lines and written into each word's hidden text (a dropped character
kept, a line read as junk filled by order), with verify.py allowing exactly those changes and the page image unchanged;
a page whose lines don't match is left alone as a draft for a person; the audit lists scanned pages with CJK as kind cjk;
read_pages.py reads them with the CJK model and prompt, never keeps a refusal, and marks their readings kind cjk.
"""
import pytest
import io, json, os, runpy, subprocess, sys, urllib.request
import pikepdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from test_decide_allowance import Resp  # noqa: E402

MODELS = ['anthropic/claude-sonnet-5.5', 'google/gemini-3.8-flash', 'google/gemini-4-carbon']
def fake(calls, reply):
    """OpenRouter for these tests: the model list (Claude and Gemini, images in), the key, and each chat request answered
    by reply(body, n); calls gets each request body."""
    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.endswith('/models'):
            return Resp({'data': [{'id': m, 'pricing': {'prompt': '0.000001', 'completion': '0.000004'}, 'architecture': {'input_modalities': ['text', 'image']},
                                   'context_length': 1000000, 'top_provider': {'max_completion_tokens': 64000},
                                   'supported_parameters': ['max_tokens', 'temperature'] + (['reasoning'] if m.startswith('google/') else [])} for m in MODELS]})
        if url.endswith('/key'): return Resp({'data': {'limit_remaining': 100}})
        if url.endswith('/credits'): return Resp({'data': {'total_credits': 100, 'total_usage': 0}})
        calls.append(req.data); return Resp(reply(json.loads(req.data), len(calls)))
    return urlopen

LINES = [['大韓民國의', '首都', '서울에는'],          # the OCR as read: line 2 is Latin noise, line 3 dropped 文
         ['날', 'MEE', '소뻐으로'],
         ['漢字는', '오랫동안', '公式', '書에']]
READING = '大韓民國의 首都 서울에는\n날 博物館과 公園으로\n漢字는 오랫동안 公式 文書에'

def cjk_layer(path, lines=LINES, producer='Synthetic OCR', sizes=None):
    """An OCRmyPDF 17 shaped page: an image-free page whose OCR layer is a form XObject drawn once, each line its own
    BT … ET, each word its own Tj in render mode 3 with a Type0 Identity-H font (single-code ToUnicode, CIDToGIDMap
    stream, /W), each word in its own marked content under one P."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    chars = sorted({c for line in lines for w in line for c in w + ' '})
    names = ['.notdef'] + [f'g{k}' for k in range(1, len(chars) + 1)]
    fb = FontBuilder(1000, isTTF=True); fb.setupGlyphOrder(names); fb.setupCharacterMap({})
    pen = TTGlyphPen(None); pen.moveTo((0, 0)); pen.lineTo((0, 500)); pen.lineTo((400, 500)); pen.closePath(); box = pen.glyph()
    fb.setupGlyf({n: box for n in names}); fb.setupHorizontalMetrics({n: (1000, 0) for n in names}); fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({'familyName': 'TestCJKOCR', 'styleName': 'Regular'}); fb.setupOS2(); fb.setupPost()
    buf = io.BytesIO(); fb.font.save(buf)
    pdf = pikepdf.new()
    codes = {ch: k + 1 for k, ch in enumerate(chars)}
    tu = ('/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo\n<</Registry (Adobe)\n/Ordering (UCS)\n/Supplement 0\n>> def\n'
          '/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n'
          f'{len(codes)} beginbfchar\n' + ''.join(f'<{c:04X}> <{ch.encode("utf-16-be").hex().upper()}>\n' for ch, c in codes.items()) +
          'endbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n')
    desc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.FontDescriptor, FontName=pikepdf.Name('/TestCJKOCR'), Flags=4, FontBBox=[0, -200, 1000, 800],
                                                ItalicAngle=0, Ascent=800, Descent=-200, CapHeight=700, StemV=80, FontFile2=pdf.make_stream(buf.getvalue())))
    cid = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.CIDFontType2, BaseFont=pikepdf.Name('/TestCJKOCR'),
                                               CIDSystemInfo=pikepdf.Dictionary(Registry=pikepdf.String('Adobe'), Ordering=pikepdf.String('Identity'), Supplement=0),
                                               FontDescriptor=desc, DW=1000, W=pikepdf.Array([1, pikepdf.Array([1000] * len(chars))]),
                                               CIDToGIDMap=pdf.make_stream(b''.join(k.to_bytes(2, 'big') for k in range(len(chars) + 1)))))
    font = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type0, BaseFont=pikepdf.Name('/TestCJKOCR'),
                                                Encoding=pikepdf.Name('/Identity-H'), DescendantFonts=pikepdf.Array([cid]), ToUnicode=pdf.make_stream(tu.encode())))
    hexw = lambda w: ''.join(f'{codes[ch]:04X}' for ch in w)
    body, k = [], 0
    for n, line in enumerate(lines):
        words = []
        for w in line:
            words.append(f'100 Tz /P <</MCID {k}>> BDC <{hexw(w + " ")}> Tj EMC 60 0 Td'); k += 1
        body.append(f'BT 3 Tr 72 {700 - 30 * n} Td /F1 {(sizes or {}).get(n, 11)} Tf ' + ' '.join(words) + ' ET')   # sizes: {line: font size}
    fx = pdf.make_indirect(pikepdf.Stream(pdf, '\n'.join(body).encode())); fx.Type = pikepdf.Name.XObject; fx.Subtype = pikepdf.Name.Form
    fx.BBox = [0, 0, 612, 792]; fx.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)); fx.StructParents = 1
    page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 612, 792], Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(OCR=fx)), StructParents=0,
                              Contents=pikepdf.Stream(pdf, b'q /OCR Do Q\n'))
    pdf.pages.append(pikepdf.Page(page)); pg = pdf.pages[0].obj
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    p_ = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg))
    p_.K = pikepdf.Array([pikepdf.Dictionary(Type=pikepdf.Name.MCR, MCID=i, Pg=pg, Stm=fx) for i in range(k)])
    doc.K = pikepdf.Array([p_]); root.K = pikepdf.Array([doc])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([1, pikepdf.Array([p_] * k)]))); root.ParentTreeNextKey = 2
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('ko')
    pdf.docinfo['/Producer'] = producer; pdf.docinfo['/Title'] = 'Synthetic CJK OCR test'
    pdf.save(path, deterministic_id=True)
    return path

def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *map(str, args)], env=dict(os.environ, VERAPDF='off'), capture_output=True, text=True, cwd=HERE)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return r

def page_text(path):
    import pypdfium2
    return pypdfium2.PdfDocument(path)[0].get_textpage().get_text_range()

def apply_reading(tmp_path, reading=READING, **extra):
    src = cjk_layer(str(tmp_path / 'ocr.pdf'))
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'page_readings': [{'page': 1, 'text': reading, 'kind': 'cjk', **extra}]}, ensure_ascii=False))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out); run('verify.py', src, out)
    return src, out, json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))

def test_a_cjk_reading_is_written_into_each_lines_words(tmp_path):
    src, out, log, v = apply_reading(tmp_path)
    r = log['page_readings'][0]
    assert r['kind'] == 'cjk' and r['lines'] == 3 and r['matched'] == 3 and r['share'] == 1.0 and not r.get('draft')
    assert ['MEE', '博物館과'] in r['changes'] and ['書에', '文書에'] in r['changes']     # junk line filled by order; 文 kept
    t = page_text(out)
    assert '博物館과' in t and '公園으로' in t and '文書에' in t and 'MEE' not in t and '大韓民國의' in t
    assert r['rewritten'] == r['operators'] and r['spans'] == 0                     # rewritten in place: Acrobat reads it
    assert v['pixel_pages_differing'] == [] and v['text_pages_changed'] == [] and v['ocr_text_rewritten']['words'] == r['changed']
    assert any('CJK pages read by the AI' in d['what'] for d in log['deferred'])

def test_a_page_whose_lines_do_not_match_is_a_draft_for_a_person(tmp_path):
    src, out, log, v = apply_reading(tmp_path, reading='全く別の行\nまた別の行\nさらに別の行\n四つ目')
    r = log['page_readings'][0]
    assert r['draft'] and r['changed'] == 0 and r['share'] < 0.7
    assert page_text(out) == page_text(src)                                         # nothing attached
    assert any(d['what'].startswith('CJK OCR: needs a person') and d['pages'] == [1] for d in log['deferred'])
    assert v['text_pages_changed'] == []

DRAFT = '全く別の行\nまた別の行\nさらに別の行\n四つ目'

def test_a_draft_a_reader_approved_is_attached_as_spoken_text(tmp_path):
    src = cjk_layer(str(tmp_path / 'ocr.pdf'))
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'page_readings': [{'page': 1, 'text': DRAFT, 'kind': 'cjk'}]}, ensure_ascii=False))
    out = str(tmp_path / 'out.pdf')
    r_ = subprocess.run([sys.executable, os.path.join(HERE, 'apply.py'), src, str(wo), out], capture_output=True, text=True, cwd=HERE,
                        env=dict(os.environ, VERAPDF='off', APPLY_CJK_CHECKED='1'))
    assert r_.returncode == 0, r_.stderr[-2000:]
    run('verify.py', src, out)
    log, v = json.load(open(out + '.log.json')), json.load(open(out + '.verify.json'))
    r = log['page_readings'][0]
    assert r['checked_draft'] and not r.get('draft') and r['share'] < 0.7 and r['changed'] > 0
    assert r['spans'] == r['operators'] and r['rewritten'] == 0                    # spoken text only: the OCR text is unchanged
    import pikepdf
    with pikepdf.open(out) as p:
        xo = next(x for x in p.pages[0].Resources.XObject.values() if x.get('/Subtype') == '/Form')
        acts = [str(i.operands[1].ActualText) for i in pikepdf.parse_content_stream(xo) if str(i.operator) == 'BDC' and '/ActualText' in i.operands[1]]
    assert ''.join(''.join(acts).split()) == ''.join(DRAFT.split())                 # the reader's text, in order (4 lines over 3: two joined)
    assert v['pixel_pages_differing'] == []
    assert not any(d['what'].startswith('CJK OCR: needs a person') for d in log['deferred'])

def test_a_draft_is_left_alone_without_the_approval(tmp_path):
    src, out, log, v = apply_reading(tmp_path, reading=DRAFT, checked_by='person')   # a flag in the order is not an approval
    assert log['page_readings'][0]['draft'] and page_text(out) == page_text(src)

def test_the_ocr_verdict_approves_draft_pages_only_with_i_read():
    from review import ocr as O
    intake = {'ocr': {'pages_with_ocr_text': [1, 2]}}
    base = {'verdict': 'approved', 'reviewer': 'Kim', 'reason': 'read against the scans', 'reads': ['Japanese']}
    v = O.check({**base, 'cjk_drafts': [2]}, intake, 10, '2026-11-22', drafts=[2, 5])
    assert v['cjk_drafts'] == [2]
    for f, why in (({**base, 'cjk_drafts': [3]}, 'not a CJK draft page'), ({**base, 'reads': [], 'cjk_drafts': [2]}, 'reads'),
                   ({**base, 'verdict': 'not approved', 'cjk_drafts': [2]}, 'approved')):
        with pytest.raises(ValueError, match=why): O.check(f, intake, 10, '2026-11-22', drafts=[2, 5])
    assert 'cjk_drafts' not in O.check(base, intake, 10, '2026-11-22', drafts=[2])
    rv = lambda v: {'review': {'ocr_text_approved': v}}
    assert O.cjk_checked(rv({'verdict': 'approved', 'reads': ['Japanese'], 'cjk_drafts': [2, 5]})) == [2, 5]
    assert O.cjk_checked(rv({'verdict': 'not approved', 'reads': ['Japanese'], 'cjk_drafts': [2]})) == []
    assert O.cjk_checked(rv({'verdict': 'approved', 'cjk_drafts': [2]})) == [] and O.cjk_checked({}) == []

def test_the_ocr_section_lists_the_runs_drafts_with_their_readings():
    from review import ocr as O
    rec = {'apply': {'page_readings': [{'page': 2, 'kind': 'cjk', 'draft': True, 'share': 0.2}, {'page': 3, 'kind': 'cjk', 'share': 1.0},
                                       {'page': 4, 'kind': 'cjk', 'checked_draft': True, 'share': 0.1}, {'page': 5, 'draft': True}]},
           'workorder': {'page_readings': [{'page': 2, 'text': '甲', 'kind': 'cjk'}, {'page': 3, 'text': '乙', 'kind': 'cjk'},
                                           {'page': 4, 'text': '丙', 'kind': 'cjk'}, {'page': 5, 'text': 'hā'}]}}
    assert O.cjk_drafts(rec) == [{'page': 2, 'reading': '甲', 'share': 0.2, 'attached': False}, {'page': 4, 'reading': '丙', 'share': 0.1, 'attached': True}]
    assert O.cjk_drafts(None) == []

def test_the_audit_lists_scanned_pages_with_cjk_as_kind_cjk(tmp_path):
    src = cjk_layer(str(tmp_path / 'ocr.pdf'), lines=LINES * 3)                     # 20+ CJK characters, producer says OCR
    A = tmp_path / '_audit'; run('audit.py', src, A)
    pr = json.load(open(A / 'page_reads.json'))
    assert [(p['page'], p['kind']) for p in pr['pages']] == [(1, 'cjk')] and (A / pr['pages'][0]['image']).exists()
    src2 = cjk_layer(str(tmp_path / 'born.pdf'), lines=LINES * 3, producer='Microsoft Word')   # not a scan: never read
    A2 = tmp_path / '_audit2'; run('audit.py', src2, A2)
    assert json.load(open(A2 / 'page_reads.json'))['pages'] == []

def read_pages(tmp_path, monkeypatch, pages, reply):
    """read_pages.py in this process against a fake OpenRouter; pages: [(page, kind)]."""
    from PIL import Image
    A = tmp_path / '_audit'; (A / 'page_reads').mkdir(parents=True); R = tmp_path / 'run'; R.mkdir()
    listed = []
    for page, kind in pages:
        Image.new('L', (200, 260), 255).save(A / 'page_reads' / f'page_{page:04d}.png')
        listed.append({'page': page, 'label': None, 'kind': kind, 'image': f'page_reads/page_{page:04d}.png', **({'cjk': 120} if kind == 'cjk' else {'share': 0.9})})
    (A / 'page_reads.json').write_text(json.dumps({'pages': listed})); (A / 'digest.json').write_text(json.dumps({'source': {'sha256': 'x'}}))
    (R / 'workorder.json').write_text(json.dumps({'document': {'title': 'T'}}))
    (R / 'run.json').write_text(json.dumps({'model': 'anthropic/claude-sonnet-5.5'}))
    calls = []
    monkeypatch.setattr(urllib.request, 'urlopen', fake(calls, reply))
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key'); monkeypatch.setenv('COST_HISTORY', str(tmp_path / 'ledger.jsonl'))
    monkeypatch.setenv('AI_PARALLEL', '1')
    monkeypatch.setattr(sys, 'argv', ['read_pages.py', str(A), str(R)]); monkeypatch.chdir(HERE)
    try: runpy.run_path(os.path.join(HERE, 'read_pages.py'), run_name='__main__')
    except SystemExit as e: assert not e.code or e.code == 0, e.code
    return R, [json.loads(c) for c in calls]

def test_cjk_pages_are_read_with_their_own_model_and_prompt(tmp_path, monkeypatch):
    def reply(body, n):
        txt = READING if 'Chinese, Japanese or Korean' in json.dumps(body, ensure_ascii=False) else 'Ua hele mai ka wahine'
        return {'choices': [{'message': {'content': txt}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 900, 'completion_tokens': 300, 'cost': 0.002}}
    R, bodies = read_pages(tmp_path, monkeypatch, [(1, 'cjk'), (2, 'haw')], reply)
    models = sorted(b['model'] for b in bodies)
    assert models == ['anthropic/claude-sonnet-5.5', 'google/gemini-3.8-flash']
    cjk_body = next(b for b in bodies if b['model'] == 'google/gemini-3.8-flash')
    assert 'Chinese, Japanese or Korean' in cjk_body['messages'][0]['content'][1]['text'] and cjk_body['provider'] == {'data_collection': 'deny'}
    wo = json.load(open(R / 'workorder.json'))
    assert wo['page_readings'] == [{'page': 1, 'text': READING, 'kind': 'cjk'}, {'page': 2, 'text': 'Ua hele mai ka wahine'}]
    rec = json.load(open(R / 'page_reads_run.json'))
    assert {p['page']: p.get('kind') for p in rec['pages']} == {1: 'cjk', 2: None} and rec['models']['cjk']['model'] == 'google/gemini-3.8-flash'

def test_a_refusal_is_paid_for_but_never_used(tmp_path, monkeypatch):
    def reply(body, n):
        return {'choices': [{'message': {'content': "I can't transcribe this page. Reproducing it would mean copying copyrighted material."}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 900, 'completion_tokens': 40, 'cost': 0.001}}
    R, _ = read_pages(tmp_path, monkeypatch, [(1, 'cjk')], reply)
    rec = json.load(open(R / 'page_reads_run.json'))
    assert rec['pages'][0]['finish'] == 'refused' and rec['cost_usd'] == 0.001
    assert 'page_readings' not in json.load(open(R / 'workorder.json'))

def test_the_cjk_model_can_be_set_apart(tmp_path, monkeypatch):
    def reply(body, n):
        return {'choices': [{'message': {'content': READING}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 900, 'completion_tokens': 300, 'cost': 0.002}}
    monkeypatch.setenv('PAGE_READS_CJK_MODEL', 'google/gemini-4-carbon')
    _, bodies = read_pages(tmp_path, monkeypatch, [(1, 'cjk')], reply)
    assert [b['model'] for b in bodies] == ['google/gemini-4-carbon']

# ---------------------------------------------------------------- the whole chain, run_api.sh with a fake OpenRouter
FAKE = '''
import os, sys, json, io, urllib.request
class _R(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
def _urlopen(req, *a, **k):
    url = req.full_url if hasattr(req, 'full_url') else str(req)
    if url.endswith('/models'):
        d = {'data': [{'id': m, 'pricing': {'prompt': '0.000002', 'completion': '0.00001'}, 'context_length': 1000000,
                       'architecture': {'input_modalities': ['text', 'image']}, 'top_provider': {'max_completion_tokens': 64000},
                       'supported_parameters': ['max_tokens', 'temperature', 'reasoning']} for m in ('anthropic/claude-sonnet-5.5', 'google/gemini-3.8-flash')]}
    elif url.endswith('/key'): d = {'data': {'limit_remaining': 100.0}}
    elif url.endswith('/credits'): d = {'data': {'total_credits': 100, 'total_usage': 0}}
    else:
        body = json.loads(req.data)
        with open(os.environ['FAKE_LOG'], 'a') as f: f.write(body['model'] + chr(10))
        text = os.environ['FAKE_READING'] if body['model'].startswith('google/') else json.dumps({'document': {'lang': 'ko', 'title': 'Synthetic CJK OCR test'}})
        d = {'model': body['model'], 'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1000, 'completion_tokens': 200, 'cost': 0.002}}
    return _R(json.dumps(d).encode())
urllib.request.urlopen = _urlopen
'''

def test_the_whole_chain_reads_a_cjk_scan_and_says_so_in_review_md(tmp_path):
    (tmp_path / 'fake').mkdir(); (tmp_path / 'fake' / 'sitecustomize.py').write_text(FAKE)
    src = cjk_layer(str(tmp_path / 'book.pdf'), lines=LINES * 3)
    reading = '\n'.join([READING] * 3)
    env = dict(os.environ, PYTHONPATH=str(tmp_path / 'fake'), FAKE_LOG=str(tmp_path / 'requests.log'), FAKE_READING=reading, VERAPDF='off',
               RUN_DIR=str(tmp_path / 'run'), INTAKE='off', AUTO='1', LANG_TAGS='off', OPENROUTER_API_KEY='test-not-a-key',
               COST_HISTORY=str(tmp_path / 'ledger.jsonl'), RUNS_DIR=str(tmp_path / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    for k in ('REPLY', 'FROM', 'REVIEW', 'PAGE_READS', 'PAGE_READS_CJK_MODEL', 'KEEP'): env.pop(k, None)
    r = subprocess.run(['bash', 'run_api.sh', src, 'book', 'c119'], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert open(tmp_path / 'requests.log').read().split() == ['anthropic/claude-sonnet-5.5', 'google/gemini-3.8-flash']
    assert '1 CJK page · google/gemini-3.8-flash' in r.stdout
    R = tmp_path / 'run'; rec = json.load(open(R / 'record.json'))
    pr = rec['apply']['page_readings'][0]
    assert pr['kind'] == 'cjk' and pr['matched'] == 9 and pr['changed'] > 0 and not pr.get('draft')
    out = next(p for p in os.listdir(R) if p.endswith('_remediated.pdf'))
    t = page_text(str(R / out))
    assert t.count('博物館과') == 3 and 'MEE' not in t
    md = open(R / 'review.md', encoding='utf-8').read()
    assert 'CJK page readings: a person who reads the language checked each page read by the AI' in md
    assert '1 of 1 scanned CJK pages read by the AI' in md and '. CJK Pages Read by the AI (1 pages' in md
    assert 'mostly Hawaiian' not in md                                               # the Hawaiian row stays away


def test_each_word_keeps_its_own_space(tmp_path):
    """Two OCR boxes of one printed word keep the space between them: dropping it made pdfium drop characters whose box
    overlaps the next word's (a real OCRmyPDF layer, 2026-11-22). Every character of the reading is there."""
    src = cjk_layer(str(tmp_path / 'ocr.pdf'), lines=[['大韓民國의', '首都'], ['날', '博物', '館과', '公園으로']])
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'page_readings': [{'page': 1, 'text': '大韓民國의 首都\n날 博物館과 公園으로', 'kind': 'cjk'}]}, ensure_ascii=False))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out); run('verify.py', src, out)
    assert json.load(open(out + '.log.json'))['page_readings'][0]['changed'] == 0          # the OCR read every word right
    assert '博物 館과' in page_text(out)

def test_furigana_read_as_its_own_line_is_blanked(tmp_path):
    """Japanese with furigana: the OCR read the small kana above the line as a line of its own (drawn at a much smaller
    size); the reading leaves furigana out, so that line is not paired, and its words are blanked: a screen reader
    reads 今日 once, not 今日きょう."""
    lines = [['きょう', 'かぜ'], ['今日は', '朝から', '風が', '強く'], ['山の', '上には'], ['白い', '雲が']]
    src = cjk_layer(str(tmp_path / 'ocr.pdf'), lines=lines, sizes={0: 5})
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'page_readings': [{'page': 1, 'text': '今日は朝から風が強く\n山の上には\n白い雲が', 'kind': 'cjk'}]}, ensure_ascii=False))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out); run('verify.py', src, out)
    r = json.load(open(out + '.log.json'))['page_readings'][0]
    t = page_text(out)
    assert r['furigana_lines'] == 1 and 'きょう' not in t and 'かぜ' not in t and '今日は' in t
    v = json.load(open(out + '.verify.json')); assert v['text_pages_changed'] == [] and v['pixel_pages_differing'] == []

def test_a_small_line_that_is_not_kana_is_kept(tmp_path):
    lines = [['注1', '出典'], ['今日は', '朝から'], ['山の', '上には'], ['白い', '雲が']]          # a footnote: small, not kana
    src = cjk_layer(str(tmp_path / 'ocr.pdf'), lines=lines, sizes={0: 5})
    wo = tmp_path / 'wo.json'; wo.write_text(json.dumps({'page_readings': [{'page': 1, 'text': '今日は朝から\n山の上には\n白い雲が', 'kind': 'cjk'}]}, ensure_ascii=False))
    out = str(tmp_path / 'out.pdf'); run('apply.py', src, wo, out)
    assert json.load(open(out + '.log.json'))['page_readings'][0]['furigana_lines'] == 0 and '出典' in page_text(out)

def test_finishing_a_review_passes_the_approved_drafts_to_apply(tmp_path, monkeypatch):
    from review import sessions as S, core
    R = str(tmp_path / 'run'); p = S.P(R); os.makedirs(p['sessions']); os.makedirs(os.path.join(R, '_intake'))
    core.save(os.path.join(R, 'record.json'), {'document': {'output': 'b_remediated.pdf'}})
    core.save(os.path.join(R, '_intake', 'intake.json'), {'review': {'ocr_text_approved': {'verdict': 'approved', 'reads': ['Japanese'], 'cjk_drafts': [4, 9]}}})
    core.save(os.path.join(p['sessions'], '003.workorder.json'), {'source': {'sha256': 'abc'}}); core.save(p['ai'], {})
    monkeypatch.setattr(S, 'check_basis', lambda R, rec, pdf: ({'input': {'sha256': 'abc'}}, 'in.pdf', {}))
    monkeypatch.setattr(S, 'fulltext_for', lambda *a: None)
    seen = {}
    def fake_run(args, say, what, quiet=False, env=None):
        seen['env'] = env; raise S.Refused('stop here')
    monkeypatch.setattr(S, '_run', fake_run)
    with pytest.raises(S.Refused, match='stop here'): S.reapply(R, {'id': '003', 'review': {}}, say=lambda *a: None)
    assert seen['env'] == {'APPLY_CJK_CHECKED': '4,9'}
