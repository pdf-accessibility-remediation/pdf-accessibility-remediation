"""lib/origin.py: the AI call behind a run's work order (sponsor checklist 11.5; Patrick, 2026-11-01). The real cost is shown
always: a run that made the call is its own origin; a run that reused a saved reply (FROM=, REPLY=, a review's re-apply)
carries the original call's cost, model, prompt and date, marked as from that call, while its own spending stays $0
(cost_total_usd, unchanged).

    of_record(rec, here=None)  {cost_usd, model, prompt_file, prompt_sha256, date} of the call, or None when none is found
    carried(rec)               what a saved reply takes with it into a later reuse ({'original_call': …} or {})
    summary(rec, here=None)    record.json `ai_call`: the call, its cost per page, and whether this run reused it
    words(ai)                  the call in plain words for a person: (cost line, model and instructions line)

A run with no call at all (decide.py --no-model, run.no_model: a PDF edited by hand, brought back for review) is $0 and
says so; it has no model or prompt to show.

Order: run.original_call (written by decide.py from a reply's meta); then a real call's own fields (cost_total_usd, else
run.usage.cost_usd for records from 2026-10-03); then, for a replay, the reply's meta file and a record beside the reply
whose raw_reply is the same text and which made a real call. A replay's own $0 is never read as the original's cost.
A run that made figure requests (issue #63) counts them all in its cost, and adds `calls`, the figure requests' prompt
and the first request's note (figure_calls), so a replay of a replay still names both prompts.
"""
import os, json, glob

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # pipeline/: response_from is written relative to it

def _load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None

def _real(rec):
    """The call this record made itself, or None (a replay, or a record with no cost at all)."""
    run = rec.get('run') or {}
    if run.get('response_from'): return None
    cost = rec.get('cost_total_usd') if rec.get('cost_total_usd') is not None else (run.get('usage') or {}).get('cost_usd')
    if cost is None: return None
    return {'cost_usd': cost, 'model': run.get('model'), 'prompt_file': run.get('prompt_file'),
            'prompt_sha256': run.get('prompt_sha256'), 'date': run.get('started'), **figure_calls(run)}

def figure_calls(run):
    """A run that made figure requests (issue #63): how many requests the cost covers, the figure requests' prompt and the
    note the first request was given; {} for a single request, so its records don't change."""
    fp = run.get('figure_passes') or {}
    if not fp: return {}
    return {'calls': len(run.get('passes') or []) or 1 + (fp.get('requests') or 0), 'figure_prompt_file': fp.get('prompt_file'),
            'figure_prompt_sha256': fp.get('prompt_sha256'), 'note': fp.get('note')}

def find(response_from, raw_reply, here=None):
    """A replay's original call from where it is kept: the reply's meta file, else a record beside the reply (its own
    folder or one level down) that holds the same reply text and made the call."""
    if not response_from: return None
    p = response_from if os.path.isabs(response_from) else os.path.normpath(os.path.join(here or HERE, response_from))
    meta = _load(p + '.meta.json') or {}
    if isinstance(meta.get('original_call'), dict): return meta['original_call']
    if not raw_reply: return None
    d = os.path.dirname(p)
    for q in [os.path.join(d, 'record.json')] + sorted(glob.glob(os.path.join(d, '*', 'record.json'))):
        r = _load(q)
        if not isinstance(r, dict) or r.get('raw_reply') != raw_reply: continue
        got = (r.get('run') or {}).get('original_call') or _real(r)
        if got: return got
    return None

def of_record(rec, here=None):
    run = rec.get('run') or {}
    if isinstance(run.get('original_call'), dict): return run['original_call']
    return _real(rec) or find(run.get('response_from'), rec.get('raw_reply'), here)

def carried(rec):
    """For a meta file written beside a saved reply (batch_api.sh FROM=, review_workorder.py --replay-to, regression.py
    --seed): the original call, so a replay of a replay still names it."""
    oc = of_record(rec)
    return {'original_call': oc} if oc else {}

def summary(rec, here=None):
    """record.json `ai_call`: the stored one when the record has it, else worked out now (a record made before)."""
    if isinstance(rec.get('ai_call'), dict): return rec['ai_call']
    if (rec.get('run') or {}).get('no_model'):           # decide.py --no-model (a PDF edited by hand): there was no call
        return {'cost_usd': 0, 'cost_per_page_usd': 0, 'model': None, 'prompt_file': None, 'prompt_sha256': None,
                'date': None, 'reused': False, 'no_model': rec['run']['no_model']}
    oc = of_record(rec, here) or {}
    pages = (rec.get('document') or {}).get('pages')
    cost = oc.get('cost_usd')
    # a replay's run.model is already the reply's own (decide.py takes it from the meta); its prompt_file is today's, never shown
    return {'cost_usd': cost, 'cost_per_page_usd': round(cost / pages, 6) if cost is not None and pages else None,
            'model': oc.get('model') or (rec.get('run') or {}).get('model'), 'prompt_file': oc.get('prompt_file'), 'prompt_sha256': oc.get('prompt_sha256'),
            'date': oc.get('date'), 'reused': bool((rec.get('run') or {}).get('response_from')),
            **{k: oc[k] for k in ('calls', 'figure_prompt_file', 'figure_prompt_sha256', 'note') if oc.get(k) is not None}}

def money(x):
    """$0.256, or $0.0006 for an amount under a cent (a cost per page)."""
    return f'${x:.3f}' if x >= 0.01 or x == 0 else f'${x:.4f}'

def words(ai):
    """(cost words, model words) for a person. Cost: "$0.256 ($0.0006 per page)", with "from the original call on October 26,
    2026" when this run reused the reply; "not recorded" when no original cost is known."""
    from lib import dates as D
    if ai.get('no_model'): return '$0: no AI call', 'none: ' + ai['no_model'].removeprefix('no AI call: ')
    if ai.get('cost_usd') is None: cost = 'not recorded'
    else:
        cost = money(ai['cost_usd']) + (f' ({money(ai["cost_per_page_usd"])} per page)' if ai.get('cost_per_page_usd') is not None else '')
        if ai.get('reused'): cost += f', from the original AI request on {D.day(ai.get("date"))}' if ai.get('date') else ', from the original AI request'
        if (ai.get('calls') or 1) > 1: cost += f' · {ai["calls"]} AI requests'
    instr = (ai.get('prompt_file') or '').removesuffix('.md') or 'not recorded'
    if ai.get('figure_prompt_file'): instr += ' + ' + ai['figure_prompt_file'].removesuffix('.md')
    return cost, f'{ai.get("model") or "not recorded"} · Instructions: {instr}'
