"""test_figure_requests_report.py: what records and review.md say about figure requests (issue #63; handoff/alt-text-passes).

    python -m pytest tests/test_figure_requests_report.py -q

- lib/origin.py: a run's cost covers every request, and both prompts are named; a single request's record is unchanged.
- End to end (the only check of review.md's run-start line and the new block, which compare_runs leaves out): the
  130-figure synthetic book replayed with REPLY= and its answers file beside it, through apply, verify and report.
Synthetic book, network blocked, dummy key: nothing is sent.
"""
import json, shutil
from lib import figpasses as F, origin
from test_figure_requests_run import book, run_api, saved_reply   # noqa: F401  (book is a fixture)

def test_origin_counts_every_request_and_names_both_prompts():
    rec = {'cost_total_usd': 1.84, 'document': {'pages': 377},
           'run': {'model': 'm', 'prompt_file': 'workorder_v10.md', 'started': '2026-11-03T10:00:00', 'passes': [{}] * 6,
                   'figure_passes': {'requests': 5, 'prompt_file': 'figures_v1.md', 'prompt_sha256': 'abc', 'note': {'version': F.NOTE_VERSION}}}}
    ai = origin.summary(rec)
    assert ai['calls'] == 6 and ai['figure_prompt_file'] == 'figures_v1.md'
    cost, instr = origin.words(ai)
    assert cost.endswith('· 6 AI requests') and instr.endswith('Instructions: workorder_v10 + figures_v1')
    one = origin.summary({'cost_total_usd': 0.3, 'document': {'pages': 100}, 'run': {'model': 'm', 'prompt_file': 'workorder_v10.md'}})
    assert 'calls' not in one and 'figure_prompt_file' not in one          # a single request's record does not change

def test_end_to_end_replay_with_figure_requests_to_review_md(book, tmp_path):
    src, A, d = book
    rp = saved_reply(book, tmp_path); R = tmp_path / 'run'; shutil.copytree(A, R / '_audit')
    r = run_api(src, R, REPLY=rp)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    md = (R / 'review.md').read_text(encoding='utf-8'); rec = json.load(open(R / 'record.json'))
    assert 'Figure requests: 130 images in 2 requests (100 with the work order, then 30).' in md
    assert '- Request 2: 30 figures · answered' in md
    assert '| Figure requests: every figure seen by the AI | OK |' in md
    assert rec['raw_reply_passes']['format'] == F.FORMAT and len(rec['workorder']['alt']) == 130
    fig = [(s['key'], it) for s in rec['sections'] for it in s['items'] if it.get('text', '').startswith(('Figure requests:', '- Request'))]
    assert len(fig) == 2 and all(k == 'title' and it.get('entry') is False for k, it in fig)   # under the run line, not counted
    from lib import glance                       # 04 Low: the block's lines are outside what the Overview counts
    secs = [dict(s, items=[it for it in s['items'] if not it.get('text', '').startswith(('Figure requests:', '- Request'))]) for s in rec['sections']]
    assert glance.from_sections(secs) == glance.from_sections(rec['sections'])
