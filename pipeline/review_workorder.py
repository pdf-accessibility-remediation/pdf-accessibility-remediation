"""review_workorder.py: a person reviews the AI's work order before apply.py uses it. No model, nothing sent.

    REVIEW=1 bash run_api.sh <original.pdf> <name> <label>         # stops after the AI's decisions (runs --prepare itself)
    python3 review_workorder.py <run_dir> --serve [--port 8765]    # the review page: approve, change or reject each decision
    bash run_api.sh <original.pdf> <name> <label>                  # same label: applies the reviewed work order

    python3 review_workorder.py <run_dir> --prepare --pdf <file.pdf>   # review_items.json and page images (run_api.sh does this)
    python3 review_workorder.py <run_dir> --reviewer NAME [--note TEXT] # instead of the page: workorder.json was edited by hand

The AI's version stays in workorder.ai.json. Either way the reviewed order goes through the same checks as the AI's
(workorder_check.py), and review.json records who reviewed it, when, and every change. report.py folds it into
record.json (review.workorder) and review.md. A later review replaces the earlier one; the earlier one is kept under history.
"""
import sys, os, json, argparse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review import core  # noqa: E402

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run_dir')
    ap.add_argument('--prepare', action='store_true', help='write review_items.json and the page images')
    ap.add_argument('--pdf', help='with --prepare: the PDF the pipeline works on (the original, or _intake/intake.pdf)')
    ap.add_argument('--serve', action='store_true', help='open the review page on this computer')
    ap.add_argument('--port', type=int, default=8765); ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--reviewer', help='without --serve: record a review of a hand-edited workorder.json')
    ap.add_argument('--note'); ap.add_argument('--date', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    R = os.path.abspath(a.run_dir)
    ai_path = os.path.join(R, 'workorder.ai.json')
    if os.path.exists(os.path.join(R, 'record.json')):
        sys.exit(f'{R} is a finished run: the work order was already applied (the review is in record.json). '
                 'To review again, start a new run label with REVIEW=1')
    if not os.path.exists(ai_path): sys.exit(f'{R} is not waiting for a review: run run_api.sh with REVIEW=1 first (no workorder.ai.json)')
    ai = core.load(ai_path)
    rerun = f'bash run_api.sh <original.pdf> <name> {os.path.basename(R)}   (the same command as before, without REVIEW=1)'

    if a.prepare:
        if not a.pdf or not os.path.isfile(a.pdf): sys.exit('--prepare needs --pdf <the PDF the pipeline works on>')
        d = core.prepare(R, a.pdf)
        n = sum(1 for it in d['items'] if it['priority'])
        print(f'review ready: {len(d["items"])} decisions, {n} to check first · page images are made as the reviewer scrolls to them')
        return
    if a.serve:
        if not os.path.exists(os.path.join(R, 'review_items.json')): sys.exit('no review_items.json: run with --prepare --pdf <file.pdf> first')
        from review import server
        v = server.serve(R, a.date, a.port, open_browser=not a.no_browser)
        if v: print(f'review recorded: {v["reviewer"]} on {v["date"]} · {len(v["changes"])} changes · '
                    f'{len(v["dropped_on_check"])} dropped by the check\nnext: {rerun}')
        return
    if not a.reviewer: sys.exit('give --serve for the review page, or --reviewer NAME to record a hand-edited workorder.json')
    try: wo = json.load(open(os.path.join(R, 'workorder.json'), encoding='utf-8'))
    except json.JSONDecodeError as e: sys.exit(f'workorder.json is not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}')
    try: v = core.finish(R, ai, wo, a.reviewer, a.date, 'hand-edit', note=a.note)
    except ValueError as e: sys.exit(str(e))
    for c in v['changes']: print(f'  {c["change"]}: {c["where"]}' + (f' [{c["id"]}]' if c.get('id') else ''))
    for d in v['dropped_on_check']: print(f'  dropped by the check: {d["where"]}: {d["why"]}')
    print(f'review recorded: {v["reviewer"]} on {v["date"]} · {len(v["changes"])} changes · {len(v["dropped_on_check"])} dropped by the check\nnext: {rerun}')

if __name__ == '__main__':
    main()
