"""review_workorder.py: a person reviews the AI's work order before apply.py uses it. No model, nothing sent.

    REVIEW=1 bash run_api.sh <original.pdf> <name> <label>         # stops after the AI's decisions (runs --prepare itself)
    python3 review_workorder.py <run_dir> --serve [--port 8765]    # the review page: approve, change or reject each decision,
                                                                   # and add what the AI left out (an H1, alt text, …)
    bash run_api.sh <original.pdf> <name> <label>                  # same label: applies the reviewed work order

    python3 review_workorder.py <run_dir> --prepare --pdf <file.pdf>   # review_items.json and page images (run_api.sh does this)
    python3 review_workorder.py <run_dir> --reviewer NAME [--note TEXT] # instead of the page: workorder.json was edited by hand

A finished run can be reviewed again (review/sessions.py keeps every session and every earlier result in reviews/):
    python3 review_workorder.py <run_dir> --reopen [--from 001|ai] [--pdf <original.pdf>] [--no-apply] [--discard-open]
                                    # the page, preloaded with the latest (or the named) session's choices; Finish re-applies
                                    # the reviewed order at once (no AI call): a new remediated PDF, review.md and review.html
    python3 review_workorder.py <run_dir> --sessions     # every session: who, when, from where, what changed, which is current
    python3 review_workorder.py <run_dir> --discard-open # the open session marked abandoned (kept); the current result stays
    python3 review_workorder.py <run_dir> --apply        # re-apply the latest finished session (after --no-apply or a failed apply)
    python3 review_workorder.py <run_dir> --pin [--pdf <original.pdf>]   # once, for runs made before every run kept its digest:
                                    # re-audit, check the digest's fingerprint against the record, keep the digest (free)
    python3 review_workorder.py <run_dir> --replay-to <new run folder>   # a run whose audit is not today's (pin refused):
                                    # copy its _intake/ and saved reply for a new run of the book on today's code (not a review)

--return-to URL (with --serve or --reopen; the app, app.py, passes it): after Finish the review page goes to that page,
and it links back to it. Only http://127.0.0.1:<port>/… or http://localhost:<port>/… is accepted.

The AI's version stays in workorder.ai.json. Either way the reviewed order goes through the same checks as the AI's
(workorder_check.py), and review.json records who reviewed it, when, and every change. report.py folds it into
record.json (review.workorder) and review.md. A later review replaces the earlier one; the earlier one is kept under history.
Gaps left in the reviewed order (no H1, figures without alt) are recorded with the reviewer's reason: on the page the
reviewer gives one; for a hand edit the --note is the reason.
"""
import sys, os, json, argparse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review import core, sessions, server  # noqa: E402

def finished(R, a):
    """A finished run: --pin, --sessions, --reopen, --apply."""
    S = sessions
    sys.stdout.reconfigure(line_buffering=True)          # in order with the apply, verify and report steps' own output
    rec = core.load(os.path.join(R, 'record.json'))
    if a.prepare or a.serve or a.reviewer:
        sys.exit(f'{R} is a finished run: to review it again, python3 review_workorder.py {os.path.relpath(R)} --reopen')
    try:
        if a.pin:
            print(f'{R}: {S.pin(R, a.pdf)}'); return
        if a.replay_to:
            reply, cmd = S.replay_to(R, a.replay_to)
            print(f'written: {os.path.abspath(a.replay_to)}/_intake/ (if this run had one), {reply} and its .meta.json\n'
                  f'a new run of the book on today\'s code (not a review of {R}): from pipeline/, run\n  {cmd}'); return
        if a.sessions:
            ss = S.sessions(R); cur = S.current_id(rec)
            if not ss: print('no review sessions' + (f' kept (reviewed before sessions were kept: --reopen records it as session 1)' if (rec.get('review') or {}).get('workorder') else ' (never reviewed)'))
            for x in ss:
                r = S.summary_row(x)
                if x.get('status') == 'open': r.update(S.name_notes(core.load(S.P(R)['draft']), x['id']))   # as last saved
                print(f'{x["id"]}{" (current)" if x["id"] == cur else ""}{" " + json.dumps(r["name"], ensure_ascii=False) if r.get("name") else ""}'
                      f'{" (notes)" if r.get("notes") else ""}  {r["status"]:<9} {r["reviewer"] or "-":<12} {r["date"] or "-":<10} '
                      f'from {S.from_label(r["from"])}'
                      + (f' · carried: {r["carried"]} from {S.from_label(r["from"])}' if r.get('carried') else '')
                      + f' · {r["changes"]} change{"s" if r["changes"] != 1 else ""} from the AI' + (f' · {r["since_start"]} set or changed in this session' if r['since_start'] else '')
                      + (' · summary only' if r['summary_only'] and not r['inferred'] else ' · inferred from the summary' if r['inferred'] else ''))
            vs = sorted(os.listdir(S.P(R)['versions'])) if os.path.isdir(S.P(R)['versions']) else []
            print(f'current result: {S.label(cur)}' + (f' · earlier results in reviews/versions/: {", ".join(vs)}' if vs else '')); return
        if a.discard_open and not a.reopen:                  # on its own: the open session marked abandoned, nothing else
            with S.Lock(R, 'discard'):
                ids = S.discard_open(R)
            print(f'discarded: {", ".join(S.label(i) for i in ids)} (kept in reviews/sessions/ as abandoned); the current result '
                  f'({S.label(S.current_id(rec))}) is unchanged'); return
        if not (a.reopen or a.apply): sys.exit('a finished run: give --reopen, --apply, --sessions, --pin, --replay-to or --discard-open')
        with S.Lock(R, 'reopen' if a.reopen else 'apply'):
            if os.path.exists(S.P(R)['promoting']): print('completing an interrupted promotion'); S.promote(R, None, None); rec = core.load(os.path.join(R, 'record.json'))
            if S.basis(R) is None or not os.path.exists(os.path.join(S.P(R)['audit'], 'digest.json')):
                print('this run has no reviews/basis.json yet: pinning it first (free re-audit)'); print(S.pin(R, a.pdf))
            if a.apply:
                fin = [x for x in S.sessions(R) if x.get('status') == 'finished']
                if not fin: sys.exit('no finished session waiting to be applied (see --sessions)')
                return apply_now(R, fin[-1], a)
            s = S.open_session(R, rec, a.src, a.pdf, a.discard_open)
            if s.get('not_carried'):
                print(f'  {len(s["not_carried"])} earlier choices not carried (the decision is not the same): ' + ', '.join(x['id'] for x in s['not_carried'][:8]))
            print(f'{S.label(s["id"])} from {S.from_label(s["from"])}'
                  + (f': {s.get("carried", 0)} choices preloaded' if s['from'] != 'ai' else ''))
            v = server.serve(S.P(R)['dir'], a.date, a.port, open_browser=not a.no_browser,
                             files={'/result/review.html': os.path.join(R, 'review.html'), '/result/review.md': os.path.join(R, 'review.md')},
                             return_to=a.return_to)
            if not v:
                print(f'{S.label(s["id"])} stays open: run the same command again to carry on'); return
            s = S.finish_session(R, s, rec)
            print(f'review recorded: {S.label(s["id"])} · {v["reviewer"]} on {v["date"]} · {len(v["changes"])} changes from the AI · '
                  f'{len(s["since_start"])} set or changed in this session · {len(v["dropped_on_check"])} dropped by the check')
            if a.no_apply:
                S.mark_pending(R, s)
                print(f'not applied yet (ready to ship says No until it is): python3 review_workorder.py {os.path.relpath(R)} --apply'); return
            apply_now(R, s, a)
    except S.Refused as e: sys.exit(f'refused: {e}')

def apply_now(R, s, a):
    S = sessions
    if ((core.load(os.path.join(R, 'record.json')) or {}).get('review') or {}).get('pending'):
        S.mark_pending(R, None)                   # the current record goes to versions/ as it was
    s = S.reapply(R, s, a.pdf)
    print(f'done: {S.label(s["id"])} is the current result in {R}')

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run_dir')
    ap.add_argument('--prepare', action='store_true', help='write review_items.json and the page images')
    ap.add_argument('--pdf', help='with --prepare: the PDF the pipeline works on (the original, or _intake/intake.pdf)')
    ap.add_argument('--serve', action='store_true', help='open the review page on this computer')
    ap.add_argument('--port', type=int, default=8765); ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--reviewer', help='without --serve: record a review of a hand-edited workorder.json')
    ap.add_argument('--note'); ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--reopen', action='store_true', help='a finished run: review it again, with the earlier choices preloaded')
    ap.add_argument('--from', dest='src', help='with --reopen: the session to start from (001, 002, …), or ai for the AI\'s decisions')
    ap.add_argument('--no-apply', action='store_true', help='with --reopen: stop after Finish (re-apply later with --apply)')
    ap.add_argument('--discard-open', action='store_true', help='with --reopen --from: mark an open session abandoned (it is kept); '
                    'on its own: only that, no new session')
    ap.add_argument('--apply', action='store_true', help='re-apply the latest finished session')
    ap.add_argument('--sessions', action='store_true', help='list the review sessions of a run')
    ap.add_argument('--pin', action='store_true', help='keep a finished run\'s digest after checking its fingerprint (free re-audit)')
    ap.add_argument('--replay-to', metavar='DIR', help='a run that can no longer be reviewed: prepare a new run of the book in DIR '
                    'from its intake and saved reply (no API call), and print the command')
    ap.add_argument('--return-to', metavar='URL', help='with --serve or --reopen: the page the review page goes to after Finish, and '
                    'links back to (the app\'s run page; http://127.0.0.1:<port>/… or http://localhost:<port>/… only)')
    a = ap.parse_args()
    clash = [f for f, on in (('--apply', a.apply), ('--pin', a.pin), ('--sessions', a.sessions), ('--replay-to', a.replay_to)) if on]
    if a.discard_open and clash:                         # alone, or with --reopen --from: never silently one of the two
        sys.exit(f'--discard-open goes on its own (or with --reopen --from), not with {", ".join(clash)}')
    if a.return_to:
        try: server.check_return_to(a.return_to)
        except ValueError as e: sys.exit(f'--return-to: {e}')
    R = os.path.abspath(a.run_dir)
    ai_path = os.path.join(R, 'workorder.ai.json')
    if os.path.exists(os.path.join(R, 'record.json')):
        return finished(R, a)
    if a.reopen or a.apply or a.sessions or a.pin or a.replay_to: sys.exit(f'{R} is not a finished run (no record.json)')
    if not os.path.exists(ai_path): sys.exit(f'{R} is not waiting for a review: run run_api.sh with REVIEW=1 first (no workorder.ai.json)')
    ai = core.load(ai_path)
    rerun = f'bash run_api.sh <original.pdf> <name> {os.path.basename(R)}   (the same command as before, without REVIEW=1)'

    if a.prepare:
        if not a.pdf or not os.path.isfile(a.pdf): sys.exit('--prepare needs --pdf <the PDF the pipeline works on>')
        d = core.prepare(R, a.pdf)
        b = sessions.first_basis(R, a.pdf)                 # the run id: the page's browser draft is this run's alone
        d['session'] = {'key': f'{b["run_id"]}:001', 'id': '001', 'first': True, 'name_default': 'Session 1'}
        core.save(os.path.join(R, 'review_items.json'), d)
        n = sum(1 for it in d['items'] if it['priority'])
        print(f'review ready: {len(d["items"])} decisions, {n} to check first · page images are made as the reviewer scrolls to them')
        return
    if a.serve:
        if not os.path.exists(os.path.join(R, 'review_items.json')): sys.exit('no review_items.json: run with --prepare --pdf <file.pdf> first')
        d = core.load(os.path.join(R, 'review_items.json'))
        if not (d.get('session') or {}).get('key') and os.path.isfile(d.get('pdf') or ''):   # prepared before runs had an id
            b = sessions.first_basis(R, d['pdf'])
            d['session'] = {'key': f'{b["run_id"]}:001', 'id': '001', 'first': True, 'name_default': 'Session 1'}
            core.save(os.path.join(R, 'review_items.json'), d)
        v = server.serve(R, a.date, a.port, open_browser=not a.no_browser, return_to=a.return_to)
        if v: print(f'review recorded: {v["reviewer"]} on {v["date"]} · {len(v["changes"])} changes · '
                    f'{len(v["dropped_on_check"])} dropped by the check · {len(v.get("gaps") or [])} gaps left open\nnext: {rerun}')
        return
    if not a.reviewer: sys.exit('give --serve for the review page, or --reviewer NAME to record a hand-edited workorder.json')
    try: wo = json.load(open(os.path.join(R, 'workorder.json'), encoding='utf-8'))
    except json.JSONDecodeError as e: sys.exit(f'workorder.json is not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}')
    gap_default = f'hand edit: --note says: {a.note}' if a.note else 'hand edit: no reason asked for'
    try: v = core.finish(R, ai, wo, a.reviewer, a.date, 'hand-edit', note=a.note, gap_default=gap_default)
    except ValueError as e: sys.exit(str(e))
    for c in v['changes']: print(f'  {c["change"]}: {c["where"]}' + (f' [{c["id"]}]' if c.get('id') else ''))
    for d in v['dropped_on_check']: print(f'  dropped by the check: {d["where"]}: {d["why"]}')
    for g in v.get('gaps') or []: print(f'  warning, left open: {g["what"]}')
    print(f'review recorded: {v["reviewer"]} on {v["date"]} · {len(v["changes"])} changes · {len(v["dropped_on_check"])} dropped by the check\nnext: {rerun}')

if __name__ == '__main__':
    main()
