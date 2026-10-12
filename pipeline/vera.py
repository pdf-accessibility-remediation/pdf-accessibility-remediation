"""vera.py: runs veraPDF (PDF/UA-1) on one PDF and condenses its report. Read-only; no model calls.

    python vera.py FILE.pdf OUT.json

Writes one entry per failed rule, not one per failure (a scanned book can fail 70,000 checks): its clause, what it
checks, how many checks failed, up to five example objects with their PDF pages, and who can fix it:

    executor   apply.py fixes it by itself, whatever the work order says (flags, links, note IDs, the OCR layer's font)
    model      it needs a decision the work order can carry (alt text, headings, language, untagged content, role map)
    person     nothing in the pipeline fixes it (fonts, tables, list and contents structure, the PDF/UA claim)

audit.py calls it on the original (the "before"); verify.py on the result (the "after"); report.py compares the two.
Needs the veraPDF command-line tool (https://verapdf.org; on a Mac: brew install verapdf) and a Java runtime. Without
it, or with VERAPDF=off, the summary says the check was skipped and the pipeline runs as before. VERAPDF=/path/to/verapdf
picks a copy that is not on the PATH.
"""
import sys, os, re, json, time, shutil, subprocess

EXECUTOR = {'6.2-1', '7.1-10', '7.1-11', '7.9-1', '7.9-2', '7.18.1-2', '7.18.3-1', '7.18.5-1', '7.18.5-2', '7.21.8-1'}
MODEL = {'7.1-3', '7.1-5', '7.1-9'}
PERSON = {'5-1'}                 # the pipeline never claims PDF/UA conformance: that is a person's sign-off
def who(rule, tags):
    if rule in EXECUTOR: return 'executor'
    if rule in MODEL: return 'model'
    if rule in PERSON: return 'person'
    tags = set(tags or [])
    if tags & {'alt-text', 'figure', 'heading'} and not tags & {'annotation', 'table'}: return 'model'
    if 'lang' in tags: return 'model'
    return 'person'

def find():
    v = os.environ.get('VERAPDF', '')
    if v.lower() in ('off', '0', 'no'): return None
    return v if v and os.path.isfile(v) else shutil.which('verapdf')

EX = re.compile(r'\((\d+) (\d+) obj (?:SE\w+ )?([^)]*)\)')
def example(check):
    ctx = check.get('context') or ''
    pg = re.findall(r'pages\[(\d+)\]', ctx)
    objs = EX.findall(ctx)
    o = objs[-1] if objs else None
    return {'obj': f'{o[0]} {o[1]}' if o else None, 'type': o[2] if o else None, 'page': int(pg[-1]) + 1 if pg else None,
            'message': (check.get('errorMessage') or '')[:160]}

def run(path, timeout=1800):
    """The condensed PDF/UA-1 report for one file, or {'skipped': why}."""
    exe = find()
    if exe is None:
        return {'skipped': 'VERAPDF=off' if os.environ.get('VERAPDF', '').lower() in ('off', '0', 'no')
                else 'veraPDF is not installed (brew install verapdf, or set VERAPDF=/path/to/verapdf)'}
    t0 = time.time()
    try:
        p = subprocess.run([exe, '-f', 'ua1', '--format', 'json', '--maxfailuresdisplayed', '5', path],
                           capture_output=True, timeout=timeout)
        rep = json.loads(p.stdout.decode('utf-8', 'replace'))['report']
    except subprocess.TimeoutExpired: return {'skipped': f'veraPDF took longer than {timeout}s'}
    except Exception as e: return {'skipped': f'veraPDF could not be run or read: {type(e).__name__}: {str(e)[:200]}'}
    job = rep['jobs'][0]; vr = job.get('validationResult') or []
    if not vr: return {'skipped': 'veraPDF returned no validation result: ' + json.dumps(job.get('taskException') or job)[:200]}
    det = vr[0]['details']
    version = next((r.get('version') for r in rep.get('buildInformation', {}).get('releaseDetails', []) if r.get('id') == 'core'), None)
    rules = []
    for r in det.get('ruleSummaries') or []:
        if r.get('status') != 'failed': continue
        rule = f'{r["clause"]}-{r["testNumber"]}'
        rules.append({'rule': rule, 'description': r.get('description', '')[:240], 'tags': r.get('tags') or [], 'failed': r.get('failedChecks', 0),
                      'who': who(rule, r.get('tags')), 'examples': [example(c) for c in (r.get('checks') or [])[:5]]})
    rules.sort(key=lambda r: [int(x) if x.isdigit() else 0 for x in re.split(r'[.-]', r['rule'])])
    return {'tool': f'veraPDF {version}' if version else 'veraPDF', 'profile': vr[0].get('profileName'), 'compliant': bool(vr[0].get('compliant')),
            'passed_checks': det.get('passedChecks'), 'failed_checks': det.get('failedChecks'), 'failed_rules': det.get('failedRules'),
            'seconds': round(time.time() - t0, 1), 'rules': rules}

def line(s):
    """One line for the terminal."""
    if s.get('skipped'): return f'veraPDF: skipped ({s["skipped"]})'
    if s['compliant']: return f'{s["tool"]} PDF/UA-1: passes ({s["passed_checks"]:,} checks)'
    by = {}
    for r in s['rules']: by[r['who']] = by.get(r['who'], 0) + 1
    return (f'{s["tool"]} PDF/UA-1: {s["failed_rules"]} rules failing ({s["failed_checks"]:,} checks) · '
            + ' · '.join(f'{k} {by[k]}' for k in ('executor', 'model', 'person') if k in by))

if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit('usage: python vera.py FILE.pdf OUT.json')
    s = run(sys.argv[1])
    json.dump(s, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(line(s))
