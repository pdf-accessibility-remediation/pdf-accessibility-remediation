"""manual_checks.py: a finished run's manual checks from the terminal (issue #38; docs/release.md). The app's Manual
Checks page (planned) records through the same code (review/manual.py).

    python3 manual_checks.py <run> --show                       the status, "Ready to ship?", the version and every check
    python3 manual_checks.py <run> --record pac FILE.json       record a PAC 2026 and sanity check of the current version
    python3 manual_checks.py <run> --record screen-reader FILE.json
    python3 manual_checks.py <run> --refresh                    recompute the Overview and review.html (no PDF touched)
    python3 manual_checks.py --template pac|screen-reader       print an empty FILE.json to fill in

FILE.json: {"by": "Kim", "fields": {...}, "items": {"<key>": {"result": "pass|fail|na", "note": "..."}}, "notes": "..."}.
--for-sha SHA records only if the PDF on disk still has that sha256 (the version you checked); --show prints it.
"""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import release as REL
from review import sessions as S, manual as M

SECTION = {'pac': 'pac', 'screen-reader': 'screen_reader', 'screen_reader': 'screen_reader'}

def template(section):
    return {'by': '', 'fields': {k: '' for k in REL.FIELDS[section]} | ({'pages_checked': ''} if any(x.get('pages') for x in REL.CHECKLIST[section]) else {}),
            'items': {x['key']: {'result': '', 'note': ''} for x in REL.CHECKLIST[section]}, 'notes': ''}

def show(R):
    from lib import glance as G
    rec = S.load(os.path.join(R, 'record.json'))
    if rec is None: sys.exit(f'{R}: no record.json (not a finished run)')
    doc = rec.get('document') or {}; out = doc.get('output')
    disk = REL.sha_file(os.path.join(R, out)) if out and os.path.isfile(os.path.join(R, out)) else None
    rel = REL.load(R, rec); g = G.with_release(rec.get('glance') or {'ship': []}, rec, rel)
    sid = (rec.get('review') or {}).get('session')
    print(f'{R}\n  PDF: {out} · sha256 {disk or "file missing"}' + (f' · {S.label(sid)}' if sid else ' · applied without review'))
    if doc.get('output_sha256') and disk and doc['output_sha256'] != disk: print('  WARNING: the PDF on disk is not the one record.json describes')
    if not doc.get('output_sha256'): print('  record.json has no output_sha256 yet: the first --record takes the disk hash')
    print(f'  status: {g["status"]["text"]}' + (f' · {g["status"]["newer"]}' if g['status'].get('newer') else ''))
    print(f'  ready to ship: {"Yes" if g["ready"] else "No"}' + (' (stored glance is older: run --refresh)' if (rec.get('glance') or {}).get('schema') != G.SCHEMA else ''))
    for x in g["ship"]: print(f"    - {G.ship_name(x)}: {x['text']}")
    why = M.being_made(R)
    if why: print(f'  recording is refused now: {why}')
    for sec in REL.SECTIONS:
        for c in rel['checks'].get(sec) or []:
            print(f'  {sec} #{c["id"]}: {c.get("by")} {c.get("recorded")} · {REL.state(rel, sec, c, disk)} · '
                  f'{len(REL.issues(c, sec))} issue(s) · sha256 {REL.sha_of(c)[:12]}')
    for s_ in rel['shipped']: print(f'  shipment {s_.get("n")}: {s_.get("by")} {s_.get("shipped")}' + (' (withdrawn)' if s_.get('withdrawn') else ''))

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run', nargs='?'); ap.add_argument('--show', action='store_true'); ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--record', nargs=2, metavar=('SECTION', 'FILE')); ap.add_argument('--for-sha')
    ap.add_argument('--template', choices=sorted(SECTION))
    a = ap.parse_args()
    if a.template: print(json.dumps(template(SECTION[a.template]), indent=1, ensure_ascii=False)); return
    if not a.run: ap.error('give a run folder')
    R = os.path.abspath(a.run)
    try:
        if a.record:
            sec = SECTION.get(a.record[0])
            if not sec: ap.error('the section is pac or screen-reader')
            data = json.load(open(a.record[1], encoding='utf-8'))
            c = M.record(R, sec, data, shown_sha=a.for_sha, via='manual_checks.py')
            print(f'recorded: {sec} #{c["id"]} by {c["by"]} on the PDF with sha256 {c["pdf"]["sha256"][:12]}…'
                  + (f' · {len(REL.issues(c, sec))} issue(s) noted' if REL.issues(c, sec) else ''))
        elif a.refresh: M.refresh(R); print(f'refreshed: {R}')
        if a.show or not (a.record or a.refresh): show(R)
    except REL.Invalid as e:
        sys.exit('refused:\n' + '\n'.join(f'  {f}: {m}' for f, m in e.errors))
    except (S.Refused, ValueError) as e: sys.exit(f'refused: {e}')

if __name__ == '__main__':
    main()
