"""test_failures.py: every way a run can stop (#45, 01 §3.4 and 03 §9) explained in plain words: one synthetic run folder
and log per row, and every matched string pinned against the tool that prints it, so a change of wording breaks a test,
not the page. No book, no model.

    python -m pytest tests/test_failures.py -q
"""
import os, sys, json, re
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # pipeline/
sys.path.insert(0, HERE)
from webapp import failures as F, jobs  # noqa: E402
from test_webapp import setup, settings  # noqa: E402,F401

def src(rel): return open(os.path.join(HERE, rel), encoding='utf-8').read()

@pytest.mark.parametrize('row', [r for r in F.ROWS if r[3]], ids=lambda r: r[0])
def test_every_matched_string_is_in_its_source(row):
    f, text = row[3]
    assert text in src(f), (row[0], f, text)

@pytest.mark.parametrize('row', F.ROWS, ids=lambda r: r[0])
def test_card_words_never_quote_a_tool(row):
    """Headline, meaning and what to do: plain words; variables, commands and file names stay in "Details" (03 §9)."""
    for w in (row[4], row[5] or '', row[6] or ''):
        assert not re.search(r'=|\.py\b|\.sh\b|\.json\b|_[a-z]|\bOPENROUTER\b|FORCE_OCR|RETRY', w), (row[0], w)

def case(t, s, kind='estimate', status='failed', exit=1, log='', intake=None, run=None, files=(), env=None):
    R = t / 'runs' / 'bk' / 'l1'; R.mkdir(parents=True, exist_ok=True)
    if intake is not None: (R / '_intake').mkdir(exist_ok=True); (R / '_intake' / 'intake.json').write_text(json.dumps(intake))
    if run is not None: (R / 'run.json').write_text(json.dumps(run))
    for f in files: (R / f).write_text('{}')
    j = {'id': f'20261105-000000-{len(os.listdir(t / "runs" / "bk"))}-{kind}', 'kind': kind, 'run': 'bk/l1', 'status': status, 'exit': exit, 'env_set': env or {}}
    os.makedirs(jobs.folder(s['jobs']), exist_ok=True)
    open(jobs.log_path(s['jobs'], j['id']), 'w').write(log); jobs.save(s['jobs'], j)
    return F.explain(s, str(R), j)

INTAKE = '▶ 0/5 intake (local, no model)\n'
AUDIT = INTAKE + '  ✓ 0/5 intake (local, no model): 1.0s\n▶ 1/5 audit (no model)\n'
EST = AUDIT + '  ✓ 1/5 audit (no model): 2.0s\n▶ 2/5 cost estimate (no model)\n'
CALL = EST + '  ✓ 2/5 cost estimate (no model): 1.0s\n▶ 3/5 anthropic/claude-x via OpenRouter\n'
TB = 'Traceback (most recent call last):\n  File "/x/pipeline/decide.py", line 327, in <module>\nurllib.error.URLError: <urlopen error timed out>\n'
CASES = [
    ('B1', dict(log='no such PDF: /x/a.pdf\n')), ('B2', dict(log='veraPDF is needed for the WCAG checks: …\n')),
    ('B3', dict(log='/r already holds a finished run: choose another run label\n')),
    ('B4', dict(log="the AI's work order in /r is waiting for a review. Finish it first:\n")),
    ('B7', dict(log='MAX_USD must be a number of dollars: x\n')),
    ('C1', dict(log=INTAKE, exit=3, intake={'status': 'stopped', 'summary': 'the PDF needs a password to open; a person must supply an unlocked copy'})),
    ('C2', dict(log=INTAKE, exit=3, intake={'status': 'stopped', 'summary': 'PDF 2.0', 'flags': [{'what': 'Not supported yet: PDF 2.0', 'why': 'x'}]})),
    ('C2', dict(log=AUDIT + 'audit: stopped: namespaced tags\n', exit=3, intake={'status': 'done'})),
    ('C3', dict(log=INTAKE, exit=3, intake={'status': 'stopped', 'summary': 'no page has text or a page image: nothing to tag'})),
    ('C4', dict(log=INTAKE, exit=3, intake={'status': 'stopped', 'summary': 'text layer unusable (median CER 40%): flagged; FORCE_OCR=1 would OCR every page'})),
    ('C5', dict(log=INTAKE, exit=3, intake={'status': 'stopped', 'summary': "CJK text on pages to be OCR'd (3, 4): set OCR_LANG and run again"})),
    ('C6', dict(log=INTAKE, intake={'status': 'failed', 'summary': 'the PDF could not be opened (bad xref)'})),
    ('C7', dict(log=INTAKE, intake={'status': 'failed', 'summary': 'Tesseract is not installed: brew install tesseract tesseract-lang'})),
    ('C8', dict(log=INTAKE, intake={'status': 'failed', 'summary': 'OCR changed pages it should not have (appearance [3], text []): stopped'})),
    ('C9', dict(log=INTAKE, intake={'status': 'failed', 'summary': 'auto-tagging failed: java died'})),
    ('C10', dict(log=INTAKE + 'Traceback (most recent call last):\nKeyError: x\n', intake={'status': None})),
    ('D3', dict(log=AUDIT + 'Traceback (most recent call last):\nValueError: x\n', intake={'status': 'done'})),
    ('E2', dict(log=EST + 'refusing: the request needs about 300,000 tokens (input estimate + room for the reply), over m\'s 200,000-token context window\n')),
    ('E9', dict(log=EST + 'boom\n')),
    ('F0', dict(kind='spend', log=CALL + "could not reach OpenRouter to look up the model: <urlopen error>\n")),
    ('F1', dict(kind='spend', log=CALL + 'refusing: this call could cost up to $0.54, more than the limit of $0.01 per AI call. To run it, raise the limit for this run: MAX_USD=1 bash run_api.sh …\n', run={'estimate': {}})),
    ('F1b', dict(kind='spend', log=CALL + "refusing before any call: this PDF's 7 requests could cost up to $6.20, more than the limit of $5.00 per PDF. To run it, raise the limit for this run: BOOK_MAX_USD=7 bash run_api.sh …\n", run={'estimate': {}})),
    ('F2', dict(kind='spend', log=CALL + 'refusing: $0.10 credit available, this run could cost up to $0.54 (OpenRouter would answer 402). Add credit\n', run={})),
    ('F3', dict(kind='spend', log=CALL + 'no OPENROUTER_API_KEY: put it in PDFREMPROTO1/.env\n', run={})),
    ('F4', dict(kind='spend', log=CALL + 'OpenRouter error 400: m rejected the temperature setting (0)\n', run={})),
    ('F5a', dict(kind='spend', log=CALL, run={'error': {'code': 429, 'message': 'rate limited'}})),
    ('F5', dict(kind='spend', log=CALL, run={'error': {'code': 502, 'message': 'bad gateway'}, 'usage': {'cost_usd': 0.01}})),
    ('F7', dict(kind='spend', log=CALL + TB, run={})),
    ('F8m', dict(kind='spend', log=CALL + 'the reply was cut off at 128,000 output tokens\n', run={'finish_reason': 'length', 'usage': {'cost_usd': 1.4}, 'estimate': {'max_tokens': 128000}, 'model_limits': {'max_completion_tokens': 128000}})),
    ('F8', dict(kind='spend', log=CALL + 'the reply was cut off at 48,000 output tokens\n', run={'finish_reason': 'length', 'usage': {'cost_usd': 0.7}})),
    ('F8', dict(kind='spend', log=CALL + 'the reply was cut off at 48,000 output tokens\n', run={'finish_reason': 'length', 'usage': {'cost_usd': 0.7}, 'estimate': {'max_tokens': 48000}, 'model_limits': {'max_completion_tokens': 128000}})),   # the model's maximum is known and not reached
    ('E2m', dict(log=EST + "refusing: m writes at most 128,000 output tokens, and the previous attempt was already cut off at that length, so another attempt would be cut off too. Choose another model\n")),
    ('F9', dict(kind='spend', log=CALL + 'could not parse a JSON work order from reply.txt (x)\n', run={'finish_reason': 'stop'})),
    ('B6', dict(kind='rerun', log=EST + '', run={})),
    ('G1', dict(kind='spend', log=CALL + '  ✓ 3/5 x: 1s\n▶ review: page images (no model)\nTraceback (most recent call last):\nOSError: x\n', run={})),
    ('H1', dict(kind='rerun', log=CALL + '▶ 4/5 apply (no model)\nwork order was written for a different file (sha256 mismatch)\n', env={'REVIEW': '1'})),
    ('H2', dict(kind='rerun', log=CALL + '▶ 4/5 apply (no model)\n  ✓ 4/5 apply (no model): 1s\n▶ 5/5 report\nexpected one remediated PDF\n', env={'REVIEW': '1'})),
    ('I1', dict(status='interrupted', exit=None, log=AUDIT)),
    ('I2', dict(kind='spend', status='interrupted', exit=None, log=CALL)),
    ('I3', dict(kind='spend', status='interrupted', exit=None, log=CALL, files=('response.json', 'workorder.json'))),
    ('I2', dict(kind='spend', status='interrupted', exit=None, log=CALL, files=('response.json',))),   # a reply half written: not "costs nothing" (05 M3)
    ('J1', dict(exit=127, log='could not start: no such file\n')),
]

@pytest.mark.parametrize('code,kw', CASES, ids=[f'{c}-{i}' for i, (c, _) in enumerate(CASES)])
def test_each_row(setup, code, kw):
    s = settings(setup)
    f = case(setup, s, **kw)
    assert f and f['code'] == code, (code, f and f['code'])
    assert f['headline'] and not f['headline'].endswith('.') and f['details']['log'] and f['details']['step']

def test_details_hold_the_tools_words(setup):
    s = settings(setup)
    f = case(setup, s, log=INTAKE, exit=3, intake={'status': 'stopped', 'summary': 'text layer unusable (median CER 40%): flagged; FORCE_OCR=1 would OCR every page'})
    assert f['details']['line'].startswith('text layer unusable') and 'FORCE_OCR=1' in f['details']['command'] and f['details']['exit'] == 3
    assert f['details']['record'].endswith(os.path.join('_intake', 'intake.json')) and f['next'] == []          # Q7: no "OCR Every Page Instead"
    f = case(setup, s, kind='spend', log=CALL, run={'error': {'code': 502, 'message': 'bad gateway'}, 'usage': {'cost_usd': 0.0123}})
    assert f['details']['line'] == 'OpenRouter error 502: bad gateway (cost reported: $0.0123)'
    f = case(setup, s, kind='spend', log=CALL + TB, run={})
    assert 'URLError' in f['details']['line'] and 'decide.py:327' in f['details']['line']

def test_a_finished_or_running_job_has_no_failure(setup):
    s = settings(setup)
    assert case(setup, s, status='done', exit=0, log=EST) is None
    assert F.explain(s, str(setup), None) is None

def test_force_ocr_is_not_a_job_variable():
    from webapp import config
    assert 'FORCE_OCR' not in config.JOB_ENV
