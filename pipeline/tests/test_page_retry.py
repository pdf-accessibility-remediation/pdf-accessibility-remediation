"""test_page_retry.py: page readings on a retry (#95). A run that read its Hawaiian pages and then failed at a later step is
run again (the same command, or the app's "Try Again"): the pages already read come back at no cost, the pages an
interruption left unread are read under the step's own limits (or, with PAGE_READS=off, listed for a person), and
review.md says what happened. A saved reply from another folder still reads no pages.

    python -m pytest tests/test_page_retry.py -q

run_api.sh end to end on a synthetic scanned page set (no book content), with a fake OpenRouter: a sitecustomize.py on
PYTHONPATH replaces urlopen in every python3 the script starts and logs each AI request. Nothing leaves the machine.
"""
import os, sys, json, subprocess, textwrap
import pikepdf
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = 'anthropic/claude-sonnet-5.5'

FAKE = textwrap.dedent('''
    import os, sys, json, io, signal, urllib.request
    if os.environ.get('FAKE_FAIL_APPLY') and os.path.basename(sys.argv[0] if sys.argv else '') == 'apply.py':
        print('apply.py: failing on purpose (test)'); sys.exit(3)
    class _R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def _urlopen(req, *a, **k):
        if os.environ.get('FAKE_OFFLINE'): raise urllib.error.URLError('offline (test)')
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        if url.endswith('/models'):
            d = {'data': [{'id': %(model)r, 'pricing': {'prompt': '0.000003', 'completion': '0.000015'}, 'context_length': 200000,
                           'architecture': {'input_modalities': ['text', 'image']}, 'top_provider': {'max_completion_tokens': 64000},
                           'supported_parameters': ['max_tokens', 'response_format']}]}
        elif url.endswith('/key'): d = {'data': {'limit_remaining': 100.0}}
        else:
            body = json.loads(req.data); content = body['messages'][-1]['content']
            page = isinstance(content, list) and any(c.get('type') == 'image_url' for c in content)
            log = os.environ['FAKE_LOG']
            n = sum(1 for l in open(log) if l.strip() == 'page') + 1 if os.path.exists(log) else 1
            if page and os.environ.get('FAKE_KILL_ON_PAGE') == str(n):        # the run is interrupted during the page step
                os.kill(os.getppid(), signal.SIGKILL); os._exit(9)
            with open(log, 'a') as f: f.write(('page' if page else 'workorder') + '\\n')
            text = 'Ua hele mai ka wahine i ka hale ʻāina me nā keiki' if page else json.dumps({'document': {'lang': 'en', 'title': 'Synthetic Hawaiian test'}})
            d = {'model': %(model)r, 'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'cost': 0.04 if page else 0.3}}
        return _R(json.dumps(d).encode())
    urllib.request.urlopen = _urlopen
''') % {'model': MODEL}

def scanned_book(path, pages=2):
    """A tagged book whose producer says OCR (the audit's scan test), each page a run of Hawaiian-shape words."""
    words = ('Ua hele mai ka wahine i ka hale aina me na keiki ' * 4).split()
    ops = 'BT /F1 11 Tf 13 TL 72 700 Td ' + ' '.join(f'({w}) Tj ( ) Tj' + (' T*' if i % 8 == 7 else '') for i, w in enumerate(words)) + ' ET'
    pdf = pikepdf.new()
    font = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica, Encoding=pikepdf.Name.WinAnsiEncoding)
    root = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
    doc = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.Document, P=root))
    kids, nums = [], []
    for n in range(pages):
        page = pikepdf.Dictionary(Type=pikepdf.Name.Page, MediaBox=[0, 0, 612, 792], Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
                                  StructParents=n, Contents=pikepdf.Stream(pdf, f'/P <</MCID 0>> BDC {ops} EMC\n'.encode('latin-1')))
        pdf.pages.append(pikepdf.Page(page)); pg = pdf.pages[n].obj
        p_ = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructElem, S=pikepdf.Name.P, P=doc, Pg=pg, K=0))
        kids.append(p_); nums += [n, pikepdf.Array([p_])]
    doc.K = pikepdf.Array(kids); root.K = pikepdf.Array([doc])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array(nums))); root.ParentTreeNextKey = pages
    pdf.Root.StructTreeRoot = root; pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True); pdf.Root.Lang = pikepdf.String('en')
    pdf.docinfo['/Producer'] = 'Synthetic OCR'; pdf.docinfo['/Title'] = 'Synthetic Hawaiian test'
    pdf.save(path)
    return path

class Run:
    def __init__(self, tmp_path, pages=2):
        self.t = tmp_path; (tmp_path / 'fake').mkdir(); (tmp_path / 'fake' / 'sitecustomize.py').write_text(FAKE)
        self.src = scanned_book(str(tmp_path / 'book.pdf'), pages); self.R = tmp_path / 'run'; self.log = tmp_path / 'requests.log'
    def __call__(self, R=None, **extra):
        env = dict(os.environ, PYTHONPATH=str(self.t / 'fake'), FAKE_LOG=str(self.log), VERAPDF='off', RUN_DIR=str(R or self.R), INTAKE='off',
                   AUTO='1', LANG_TAGS='off', OPENROUTER_API_KEY='test-not-a-key', COST_HISTORY=str(self.t / 'ledger.jsonl'),
                   RUNS_DIR=str(self.t / 'runs'), PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', ''))
        for k in ('REPLY', 'FROM', 'REVIEW', 'PAGE_READS', 'FAKE_FAIL_APPLY', 'FAKE_KILL_ON_PAGE', 'FAKE_OFFLINE', 'KEEP'): env.pop(k, None)
        env.update(extra)
        return subprocess.run(['bash', 'run_api.sh', self.src, 'book', 'r95'], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    def requests(self): return open(self.log).read().split() if self.log.exists() else []
    def mark(self): self.n = len(self.requests())
    def new(self): return self.requests()[self.n:]

def rec(R): return json.load(open(R / 'record.json'))
def page_row(R):
    return next(l for l in open(R / 'review.md', encoding='utf-8') if l.startswith('| Page readings') and '**CHECK**' in l)

def test_a_retry_after_a_later_step_failed_applies_the_pages_with_no_new_request(tmp_path):
    run = Run(tmp_path)
    r = run(FAKE_FAIL_APPLY='1')
    assert r.returncode != 0 and run.requests() == ['workorder', 'page', 'page'], r.stdout[-2000:]
    run.mark(); r = run()
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert run.new() == [] and 'every page was read before: their readings are kept (no cost, no AI request)' in r.stdout
    x = rec(run.R)
    assert len(x['workorder']['page_readings']) == 2 and len(x['apply']['page_readings']) == 2
    assert x['page_reads']['cost_usd'] == 0.08 and x['cost_total_usd'] == 0.38                  # the pages counted once
    assert '2 of 2 mostly Hawaiian pages read by the AI' in page_row(run.R) and 'not read' not in page_row(run.R)

def test_a_retry_after_an_interruption_reads_only_the_missing_pages(tmp_path):
    run = Run(tmp_path)
    r = run(FAKE_KILL_ON_PAGE='2')                                            # killed while reading page 2
    assert r.returncode != 0 and run.requests() == ['workorder', 'page']
    run.mark(); r = run()
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert run.new() == ['page'] and '(1 already read)' in r.stdout                            # page 2 only, page 1 reused
    x = rec(run.R)
    assert sorted(p['page'] for p in x['workorder']['page_readings']) == [1, 2] and len(x['apply']['page_readings']) == 2
    assert x['page_reads']['cost_usd'] == 0.08 and x['cost_total_usd'] == 0.38

def test_try_again_in_the_app_lists_the_unread_pages_for_a_person(tmp_path):
    """The app's "Try Again" is a free rerun job: PAGE_READS=off, no new estimate, so nothing new is read. The page read
    before is applied; the one never read is listed for a person."""
    run = Run(tmp_path)
    run(FAKE_KILL_ON_PAGE='2')
    run.mark(); r = run(PAGE_READS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert run.new() == []
    x = rec(run.R)
    assert [p['page'] for p in x['workorder']['page_readings']] == [1] and len(x['apply']['page_readings']) == 1
    row = page_row(run.R)
    assert '1 of 2 mostly Hawaiian pages read by the AI' in row and 'not read by the AI: PDF 2; a person checks them against the scan' in row

def test_the_merged_path_puts_back_pages_its_work_order_lost(tmp_path):
    """A book whose figure requests all finished retries on the merged path, which keeps workorder.json as it was. If the
    run stopped before read_pages.py wrote its readings there, they come back from page_reads_run.json, even in the
    app's "Try Again" (PAGE_READS=off), with no request."""
    run = Run(tmp_path)
    run(FAKE_FAIL_APPLY='1')
    rj = json.load(open(run.R / 'run.json')); rj['figure_passes'] = {'state': 'merged'}; json.dump(rj, open(run.R / 'run.json', 'w'))
    wo = json.load(open(run.R / 'workorder.json')); wo.pop('page_readings'); json.dump(wo, open(run.R / 'workorder.json', 'w'))
    run.mark(); r = run(PAGE_READS='off')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert 'applying its work order, no new AI request' in r.stdout and run.new() == []
    x = rec(run.R)
    assert len(x['workorder']['page_readings']) == 2 and len(x['apply']['page_readings']) == 2

def test_a_retry_with_nothing_left_to_read_needs_no_network(tmp_path):
    run = Run(tmp_path)
    run(FAKE_FAIL_APPLY='1')
    run.mark(); r = run(FAKE_OFFLINE='1')
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert run.new() == [] and len(rec(run.R)['apply']['page_readings']) == 2

def test_a_reply_from_another_folder_reads_no_pages(tmp_path):
    run = Run(tmp_path)
    run(FAKE_FAIL_APPLY='1')
    other = tmp_path / 'other'
    run.mark(); r = run(R=other, REPLY=str(run.R / 'response.json'))
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert run.new() == [] and 'page_readings' not in rec(other)['workorder']
    assert 'they were not read by the AI' in page_row(other)

def test_review_md_says_read_and_paid_for_when_none_was_applied(tmp_path):
    """Pages read and paid for whose readings never reached the work order (an older run, or a step that lost them): never
    "not read"."""
    run = Run(tmp_path)
    run(FAKE_FAIL_APPLY='1')
    wo = json.load(open(run.R / 'workorder.json')); wo.pop('page_readings')
    json.dump(wo, open(run.R / 'workorder.json', 'w'))
    (run.R / 'response.json').rename(run.R / 'response.saved.json')          # no retry path: apply what workorder.json holds
    r = subprocess.run([sys.executable, 'apply.py', str(run.R / 'intake.pdf') if (run.R / 'intake.pdf').exists() else run.src, str(run.R / 'workorder.json'),
                        str(run.R / 'out.pdf')], cwd=HERE, capture_output=True, text=True, env=dict(os.environ, VERAPDF='off'))
    assert r.returncode == 0, r.stderr[-2000:]
    subprocess.run([sys.executable, 'verify.py', run.src, str(run.R / 'out.pdf')], cwd=HERE, capture_output=True, env=dict(os.environ, VERAPDF='off'))
    r = subprocess.run([sys.executable, 'report.py', str(run.R), str(run.R / '_audit'), f'--pdf={run.R / "out.pdf"}', f'--input={run.src}', '--keep'],
                       cwd=HERE, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    row = page_row(run.R)
    assert '2 of 2 mostly Hawaiian pages were read and paid for, but their readings were not applied: see the run log' in row and 'were not read' not in row
