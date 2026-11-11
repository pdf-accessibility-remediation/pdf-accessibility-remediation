"""test_figure_requests_run.py: figure requests through decide.py (issue #63; handoff/alt-text-passes).

    python -m pytest tests/test_figure_requests_run.py -q

Synthetic books only (no book content): a tagged PDF with 130 small image figures, its audit, and hand-written replies.
Every subprocess run here is a dry run or a replay, with the network blocked (a proxy that refuses) and a dummy key, so
nothing is sent and nothing can be charged: the price falls back to decide.py's assumed one, the credit to "could not
check". The one live run happens in this process, against a fake OpenRouter (urlopen replaced).
- A single-request book gets no new field; a book over the limit plans its figure requests, with the book cap's warning.
- A live run: the first request, a figure request refused once (429) and sent again, the probe, the merge, the saved split.
- A replay uses the recorded split, refuses a missing or mismatched answers file, and marks answers written for a
  different figure list.
- run_api.sh: MAX_USD and BOOK_MAX_USD must be numbers.
The helpers (the book, env, saved_reply, run_api) are used by test_figure_requests_restart.py and _report.py too.
"""
import os, sys, json, shutil, hashlib, subprocess
import pikepdf, pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from lib import figpasses as F

OFFLINE = {'HTTPS_PROXY': 'http://127.0.0.1:9', 'HTTP_PROXY': 'http://127.0.0.1:9', 'https_proxy': 'http://127.0.0.1:9',
           'http_proxy': 'http://127.0.0.1:9', 'NO_PROXY': '', 'no_proxy': ''}

def env(**kw):
    e = dict(os.environ, VERAPDF='off', **OFFLINE, OPENROUTER_API_KEY='test-not-a-key',     # never the real key from .env
             PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
    for k in ('INTAKE_REUSE', 'INTAKE', 'REPLY', 'MAX_USD', 'BOOK_MAX_USD', 'FIGURE_PASSES', 'AUTO', 'ESTIMATE'): e.pop(k, None)
    e.update({k: str(v) for k, v in kw.items()}); return e

def figures_pdf(path, n=130):
    """n pages, each with one line of text and one small raster figure (tagged, with an image of its own)."""
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    nums, ks = pikepdf.Array(), []
    for i in range(n):
        px = bytes([(i * 7 + x) % 256 for x in range(12 * 10 * 3)])
        im = pikepdf.Stream(pdf, px, Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=12, Height=10,
                            ColorSpace=pikepdf.Name.DeviceRGB, BitsPerComponent=8)
        content = (f'/P <</MCID 0>> BDC BT /F1 11 Tf 72 500 Td (Page {i + 1} text.) Tj ET EMC\n'
                   f'/Figure <</MCID 1>> BDC q 120 0 0 100 72 200 cm /Im0 Do Q EMC\n')
        pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 432, 576], StructParents=i,
                         Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font), XObject=pikepdf.Dictionary(Im0=im)),
                         Contents=pikepdf.Stream(pdf, content.encode('latin-1')))))
        pg = pdf.pages[i].obj
        p = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg, K=0))
        f = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Figure, P=doc, Pg=pg, K=1))
        ks += [p, f]; nums.append(i); nums.append(pikepdf.Array([p, f]))
    doc.K = pikepdf.Array(ks); root.K = doc
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=nums))
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.save(path); return path

@pytest.fixture(scope='module')
def book(tmp_path_factory):
    """The 130-figure book, audited once (no model, veraPDF off)."""
    d = tmp_path_factory.mktemp('book'); src = figures_pdf(d / 'figs.pdf'); A = d / '_audit'
    subprocess.run([sys.executable, 'audit.py', str(src), str(A)], cwd=HERE, env=env(), check=True, capture_output=True)
    return src, A, json.load(open(A / 'digest.json', encoding='utf-8'))

def decide(A, R, *args, **kw):
    return subprocess.run([sys.executable, 'decide.py', str(A), str(R), *map(str, args)], cwd=HERE, env=env(**kw), capture_output=True, text=True, timeout=300)

def small_audit(book, tmp_path, n):
    """The same audit cut to its first n figures: a book whose images all fit."""
    src, A, d = book; B = tmp_path / '_audit_small'; shutil.copytree(A, B)
    d2 = dict(d, figures=d['figures'][:n]); json.dump(d2, open(B / 'digest.json', 'w', encoding='utf-8'), ensure_ascii=False)
    return B

def reply_for(objs, alt='A small coloured block.'):
    return '```json\n' + json.dumps({'alt': [{'obj': o, 'alt': alt} for o in objs]}) + '\n```'

def test_book_has_130_figures_with_images(book):
    assert len([f for f in book[2]['figures'] if f.get('image')]) == 130

# ------------------------------------------------------------------ decide.py
def test_single_request_book_gets_no_new_field(book, tmp_path):
    B = small_audit(book, tmp_path, 40); R = tmp_path / 'r'
    objs = [f['obj'] for f in book[2]['figures'][:40]]
    rp = tmp_path / 'reply.txt'; rp.write_text(reply_for(objs))
    r = decide(B, R, '--response-file', rp); assert r.returncode == 0, r.stderr
    run = json.load(open(R / 'run.json')); val = json.load(open(R / 'validation.json')); wo = json.load(open(R / 'workorder.json'))
    for k in ('passes', 'figure_passes'): assert k not in run
    assert 'passes' not in run['estimate'] and 'requests' not in run['estimate'] and 'figure_pass' not in val['context']
    assert ' with note ' not in wo['decided_by'] and not (R / 'passes.json').exists()
    assert len(wo['alt']) == 40

def test_dry_run_plans_the_figure_requests_and_warns_over_the_book_cap(book, tmp_path):
    R = tmp_path / 'r'; sw = tmp_path / 'sweep.json'
    r = decide(book[1], R, '--dry-run', '--book-max-usd', '0.01', DECIDE_SWEEP=sw); assert r.returncode == 0, r.stderr
    e = json.load(open(R / 'run.json'))['estimate']
    assert e['requests'] == 2 and [p['images'] for p in e['passes']] == [100, 30]
    assert e['worst_case_total_usd'] == pytest.approx(sum(p['worst_case_usd'] for p in e['passes']), abs=1e-3)
    assert 'more than the limit of $0.01 per PDF' in r.stdout and 'BOOK_MAX_USD=' in r.stdout
    q = json.load(open(sw))['requests']
    assert [x['pass'] for x in q] == [1, '2'] and 'normalised' in q[0]

def test_figure_requests_off_is_todays_single_request(book, tmp_path):
    R = tmp_path / 'r'
    r = decide(book[1], R, '--dry-run', '--figure-requests', 'off'); assert r.returncode == 0, r.stderr
    run = json.load(open(R / 'run.json'))
    assert run['images']['not_sent'] == 30 and 'passes' not in run['estimate']
    assert 'their alt text goes to a person' in r.stdout

def saved_reply(book, tmp_path, change=None, meta_extra=None, with_side=True):
    """A saved reply of the 130-figure book made with one figure request: reply.txt, its meta and its answers file."""
    d = book[2]; figs = [f for f in d['figures'] if f.get('image')]
    first, rest = figs[:100], figs[100:]
    res = [{'pass': '2', 'items': rest, 'outcome': 'done', 'reply_text': reply_for([f['obj'] for f in rest], 'Seen in request 2.')}]
    side = F.record(first, [], {'version': F.NOTE_VERSION, 'sha256': 'x'}, res, lambda r: {'model': 'anthropic/claude-sonnet-5.5', 'usage': {'cost_usd': 0.2}})
    if change: change(side)
    rp = tmp_path / 'reply.txt'; rp.write_text(reply_for([f['obj'] for f in first] + [rest[0]['obj']], 'Seen in request 1.'))
    meta = {'model': 'anthropic/claude-sonnet-5.5', 'figure_passes': {'requests': 1, 'fingerprint': F.side_fingerprint(side)}, **(meta_extra or {})}
    (tmp_path / 'reply.txt.meta.json').write_text(json.dumps(meta))
    if with_side: (tmp_path / 'reply.txt.passes.json').write_text(json.dumps(side))
    return rp

def test_replay_uses_the_recorded_split(book, tmp_path):
    rp = saved_reply(book, tmp_path); R = tmp_path / 'r'
    r = decide(book[1], R, '--response-file', rp, '--max-images', '50'); assert r.returncode == 0, r.stderr   # today's settings don't matter
    wo = json.load(open(R / 'workorder.json')); val = json.load(open(R / 'validation.json')); run = json.load(open(R / 'run.json'))
    alts = {a['obj']: a['alt'] for a in wo['alt']}
    assert len(alts) == 130 and list(alts.values()).count('Seen in request 2.') == 30
    rest0 = [f for f in book[2]['figures'] if f.get('image')][100]['obj']
    assert alts[rest0] == 'Seen in request 2.'                      # the first request's alt for it was dropped
    assert any(x['why'] == 'decided in figure request 2, which saw the image' for x in val['dropped'])
    assert run['figure_passes']['requests'] == 1 and 'stale' not in run['figure_passes'] and 'passes' not in run
    assert ' with note ' in wo['decided_by'] and len(val['context']['figure_pass']) == 30

def test_replay_with_a_changed_figure_list_drops_that_request(book, tmp_path):
    def change(side): side['passes'][0]['objs'][0][2] += 1                 # one crop recorded at another size
    rp = saved_reply(book, tmp_path, change=change); R = tmp_path / 'r'
    r = decide(book[1], R, '--response-file', rp); assert r.returncode == 0, r.stderr
    wo = json.load(open(R / 'workorder.json')); run = json.load(open(R / 'run.json'))
    assert run['figure_passes']['stale'] == ['2'] and len(wo['alt']) == 100
    d = [x for x in wo['deferrals'] if x['what'] == 'Alt text for 30 figures']
    assert d and 'no longer match' in d[0]['why']

def test_replay_refuses_without_its_answers_file_or_with_figure_requests_off(book, tmp_path):
    rp = saved_reply(book, tmp_path, with_side=False); R = tmp_path / 'r'
    r = decide(book[1], R, '--response-file', rp)
    assert r.returncode != 0 and 'are not beside it' in (r.stderr + r.stdout)
    (tmp_path / 'reply.txt.passes.json').write_text(json.dumps({'format': F.FORMAT, 'first': {'fingerprint': 'x'}, 'passes': []}))
    r = decide(book[1], R, '--response-file', rp)
    assert r.returncode != 0 and 'fingerprint differs' in (r.stderr + r.stdout)
    rp = saved_reply(book, tmp_path)
    r = decide(book[1], R, '--response-file', rp, '--figure-requests', 'off')
    assert r.returncode != 0 and 'not supported' in (r.stderr + r.stdout)

# ------------------------------------------------------------------ a live run, against a fake OpenRouter
class Resp:
    def __init__(self, obj): self.b = json.dumps(obj).encode()
    def read(self, *a): return self.b
    def __enter__(self): return self
    def __exit__(self, *a): return False

def fake_openrouter(calls):
    """urlopen for decide.py, in this process: prices and limits for one Claude model, plenty of credit, and replies that
    write alt text for every figure a request was shown; the first figure request is refused once with a 429."""
    import io, re as re_, urllib.error
    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.endswith('/models'):
            return Resp({'data': [{'id': 'anthropic/claude-sonnet-5.5', 'pricing': {'prompt': '0.000002', 'completion': '0.00001'},
                                   'architecture': {'input_modalities': ['text', 'image']}, 'context_length': 1000000,
                                   'top_provider': {'max_completion_tokens': 128000}, 'supported_parameters': ['max_tokens']}]})
        if url.endswith('/key'): return Resp({'data': {'limit_remaining': 100}})
        if url.endswith('/credits'): return Resp({'data': {'total_credits': 100, 'total_usage': 0}})
        body = json.loads(req.data); first = body['messages'][0]['content'].startswith('You are the decision-maker')
        objs = [m.group(1) for c in body['messages'][1]['content'] if c.get('type') == 'text' for m in [re_.match(r'Figure obj "([^"]+)"', c['text'])] if m]
        calls.append({'first': first, 'n': len(objs), 'auth': req.headers.get('Authorization'), 'max_tokens': body['max_tokens'],
                      'data': body['messages'][1]['content'][0].get('text', '')})
        if not first and sum(1 for c in calls if not c['first']) == 1:
            raise urllib.error.HTTPError(url, 429, 'rate limited', {}, io.BytesIO(b'{"error": {"message": "rate limited"}}'))
        wo = {'alt': [{'obj': o, 'alt': ('First: ' if first else 'Figure: ') + o} for o in objs]}
        if first: wo['captions'] = {'style': 'NoSuchStyle'}          # the checks drop it: a figure request must not be told about it (06 L2)
        return Resp({'choices': [{'message': {'content': '```json\n' + json.dumps(wo) + '\n```'}, 'finish_reason': 'stop'}],
                     'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.01}})
    return urlopen

def test_a_live_run_sends_the_figure_requests_and_merges_them(book, tmp_path, monkeypatch):
    """The code that runs only on a live call: the first request, one figure request (a 429, then its retry), the probe,
    the saves along the way, the merge and the saved split. urlopen is replaced in this process; nothing leaves it."""
    import runpy, time, urllib.request
    calls = []
    monkeypatch.setattr(urllib.request, 'urlopen', fake_openrouter(calls)); monkeypatch.setattr(time, 'sleep', lambda s: None)
    for k, v in env().items(): monkeypatch.setenv(k, v)
    R = tmp_path / 'r'
    monkeypatch.setattr(sys, 'argv', ['decide.py', str(book[1]), str(R), '--figure-probe', '5'])
    monkeypatch.chdir(HERE)
    runpy.run_path(os.path.join(HERE, 'decide.py'), run_name='__main__')
    assert [(c['first'], c['n']) for c in calls] == [(True, 100), (False, 30), (False, 30), (False, 5)]
    assert all(c['auth'] == 'Bearer test-not-a-key' for c in calls) and [c['max_tokens'] for c in calls[1:]] == [32000] * 3
    assert all('NoSuchStyle' not in c['data'] for c in calls[1:])                # the context comes from the validated first reply
    run = json.load(open(R / 'run.json')); wo = json.load(open(R / 'workorder.json')); val = json.load(open(R / 'validation.json'))
    fp = run['figure_passes']
    assert fp['state'] == 'merged' and fp['requests'] == 1 and 'in_flight' not in fp and 'failed' not in fp
    assert [p['pass'] for p in run['passes']] == ['1', '2', 'probe'] and len(run['passes'][1]['calls']) == 2
    assert run['usage']['cost_usd'] == pytest.approx(0.03)                        # the 429 was not charged
    assert len(run['passes'][2]['overlap']) == 5 and all(v['probe'].startswith('Figure: ') for v in run['passes'][2]['overlap'].values())
    alts = [a['alt'] for a in wo['alt']]
    assert len(alts) == 130 and sum(a.startswith('Figure: ') for a in alts) == 30   # the probe's answers are never used
    assert len(val['context']['figure_pass']) == 30 and ' with note later-figures/1 + figures_v1.md' in wo['decided_by']
    side = json.load(open(R / 'passes.json'))
    assert side['format'] == F.FORMAT and [p['pass'] for p in side['passes']] == ['2'] and F.side_fingerprint(side) == fp['fingerprint']
    assert side['passes'][0]['call']['retry'] is True


# ------------------------------------------------------------------ run_api.sh
def run_api(src, R, **kw):
    return subprocess.run(['bash', 'run_api.sh', str(src), 'book', 'x'], cwd=HERE, env=env(RUN_DIR=R, INTAKE='off', **kw),
                          capture_output=True, text=True, timeout=600)

@pytest.mark.parametrize('var', ['MAX_USD', 'BOOK_MAX_USD', 'FIGURE_RETRY_MAX_USD', 'FIGURE_RETRY_BOOK_MAX_USD'])
def test_caps_must_be_numbers(book, tmp_path, var):
    r = run_api(book[0], tmp_path / 'r', **{var: '5 dollars'})
    assert r.returncode != 0 and f'{var} must be a number of dollars' in r.stdout
