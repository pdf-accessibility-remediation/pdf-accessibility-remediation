"""vera.py: run veraPDF (WCAG 2.2 machine profile) on one PDF and sort its failures into WCAG and PDF/UA-only.

    python vera.py FILE.pdf OUT.json     validate FILE.pdf, write the summary to OUT.json
    python vera.py --check               exit 0 if veraPDF runs (or VERAPDF=off), else print why and exit 1

audit.py runs it on the original and verify.py on the result, each in the background while their own checks run:
    job = vera.start(pdf); ...; summary = vera.finish(job)

veraPDF is found from $VERAPDF (path to the `verapdf` launcher), else `verapdf` on PATH; VERAPDF=off skips it.
The profile is pinned in verapdf/WCAG-2-2-Machine.xml; verapdf/rules.json says which success criterion each rule
belongs to, or why it is PDF/UA-only. A rule not listed there counts as WCAG and is listed as unclassified.
"""
import sys, os, re, json, shutil, subprocess, tempfile, time, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, 'verapdf', 'WCAG-2-2-Machine.xml')
RULES = json.load(open(os.path.join(HERE, 'verapdf', 'rules.json'), encoding='utf-8'))['rules']
TIMEOUT = int(os.environ.get('VERAPDF_TIMEOUT', '900'))     # seconds; the largest sample takes under 10
SHOWN = 20                                                  # failed checks veraPDF lists per rule (pages come from these)
SEVERITY = ('critical', 'major', 'minor', 'cosmetic')


def find():
    """(launcher path, None) or (None, reason it can't run)."""
    v = os.environ.get('VERAPDF', '')
    if v == 'off': return None, 'not run: VERAPDF=off'
    path = v or shutil.which('verapdf')
    if not path: return None, 'not run: veraPDF not installed (see README, "Verification with veraPDF")'
    if not (os.path.isfile(path) and os.access(path, os.X_OK)): return None, f'not run: VERAPDF={v} is not an executable file'
    return path, None


def version():
    path, why = find()
    if not path: return None, why
    try: r = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e: return None, f'not run: {path} --version failed ({e})'
    m = re.search(r'veraPDF\s+(\S+)', r.stdout)
    return (f'veraPDF {m.group(1)}', None) if r.returncode == 0 and m else (None, f'not run: {path} --version failed: {" ".join((r.stderr or r.stdout).split())[:200] or "no output"}')


def start(pdf):
    """Start veraPDF on pdf in the background. Returns a job for finish()."""
    path, why = find()
    job = {'pdf': pdf, 'why': why, 't0': time.time()}
    if not path: return job
    job['out'], job['err'] = tempfile.TemporaryFile(), tempfile.TemporaryFile()
    try:
        job['proc'] = subprocess.Popen([path, '-p', PROFILE, '--format', 'json', '--maxfailuresdisplayed', str(SHOWN), os.path.abspath(pdf)],
                                       stdout=job['out'], stderr=job['err'])
    except OSError as e: job['why'] = f'not run: could not start {path} ({e})'
    return job


def finish(job):
    """Wait for the job and return its summary, or {'not_run': reason}."""
    if job.get('why'): return {'not_run': job['why']}
    p = job['proc']
    try: rc = p.wait(timeout=max(1, TIMEOUT - (time.time() - job['t0'])))
    except subprocess.TimeoutExpired:
        p.kill(); p.wait(); return {'not_run': f'not run: veraPDF took longer than {TIMEOUT} s (set VERAPDF_TIMEOUT)'}
    job['out'].seek(0); job['err'].seek(0)
    raw, err = job['out'].read(), job['err'].read().decode('utf-8', 'replace')
    try: rep = json.loads(raw)['report']
    except (ValueError, KeyError):
        last = [l for l in err.splitlines() if l.strip() and 'WARNING' not in l and not re.match(r'\w{3} \d+, \d{4}', l)]
        return {'not_run': f'veraPDF failed (exit {rc}): {(last[-1] if last else "no report written")[:300]}'}
    ms = (rep['jobs'][0].get('processingTime') or {}).get('difference')
    return summarize(rep, job['pdf'], round(ms / 1000, 1) if ms is not None else None)


def run(pdf): return finish(start(pdf))


_PAGE = re.compile(r'pages\[(\d+)\]')
_OBJ = re.compile(r'\((\d+) 0 obj (?:SE|SA|PD)\w*')


def _struct_pages(pdf, objnums):
    """Object numbers of structure elements -> first page each one draws on (None if it draws nothing)."""
    if not objnums: return {}
    import pikepdf
    out = {}
    with pikepdf.open(pdf) as doc:
        pidx = {p.obj.objgen: i + 1 for i, p in enumerate(doc.pages)}
        def first_page(o, depth=0):
            if depth > 40 or not isinstance(o, pikepdf.Dictionary): return None
            pg = o.get('/Pg')
            if pg is not None and pg.objgen in pidx: return pidx[pg.objgen]
            k = o.get('/K')
            for kid in (k if isinstance(k, pikepdf.Array) else [k] if k is not None else []):
                r = first_page(kid, depth + 1)
                if r: return r
            return None
        for n in objnums:
            try: out[n] = first_page(doc.get_object((n, 0)))
            except Exception: out[n] = None      # an object veraPDF names but pikepdf can't resolve: no page shown
    return out


def summarize(rep, pdf, seconds):
    job = rep['jobs'][0]
    res = job.get('validationResult') or []
    res = res[0] if isinstance(res, list) and res else res
    if not res or job.get('taskException') or res.get('jobEndStatus') not in (None, 'normal'):
        why = (job.get('taskException') or {}).get('exceptionMessage') or (res or {}).get('jobEndStatus') or 'no validation result'
        return {'not_run': f'veraPDF could not validate the file: {str(why)[:300]}'}
    tool = next((f'veraPDF {r["version"]}' for r in rep.get('buildInformation', {}).get('releaseDetails', []) if r.get('id') == 'apps'), 'veraPDF')
    rules, objs = [], set()
    for rs in res['details'].get('ruleSummaries') or []:
        if rs.get('status', rs.get('ruleStatus', '')).lower() != 'failed': continue
        rid = f'{rs["clause"]}-{rs["testNumber"]}'
        cls = RULES.get(rid)
        pages, rule_objs = set(), set()
        for c in rs.get('checks') or []:
            ctx = c.get('context', '')
            m = _PAGE.search(ctx)
            if m: pages.add(int(m.group(1)) + 1)
            else:
                o = _OBJ.findall(ctx)
                if o: rule_objs.add(int(o[-1]))
        objs |= rule_objs
        msgs = [c.get('errorMessage') for c in rs.get('checks') or [] if c.get('errorMessage')]
        rules.append({'id': rid, 'spec': 'WCAG 2.2' if 'WCAG' in rs.get('specification', '') else 'ISO 14289-1',
                      'description': rs.get('description', ''), 'severity': next((t for t in SEVERITY if t in (rs.get('tags') or [])), None),
                      'failed': rs.get('failedChecks', 0), 'shown': len(rs.get('checks') or []),
                      'scope': cls['scope'] if cls else 'wcag', 'wcag': cls.get('wcag', []) if cls else [],
                      'why': cls.get('why') if cls else None, 'unclassified': cls is None,
                      'pages': sorted(pages), '_objs': sorted(rule_objs), 'example': msgs[0][:240] if msgs else None})
    obj_page = _struct_pages(pdf, objs)
    for r in rules:
        r['pages'] = sorted(set(r['pages']) | {obj_page[o] for o in r.pop('_objs') if obj_page.get(o)})
    rules.sort(key=lambda r: (r['scope'] != 'wcag', SEVERITY.index(r['severity']) if r['severity'] in SEVERITY else 9, -r['failed']))
    w = [r for r in rules if r['scope'] == 'wcag']; u = [r for r in rules if r['scope'] != 'wcag']
    return {'tool': tool, 'profile': res.get('profileName', os.path.basename(PROFILE)),
            'profile_sha256': hashlib.sha256(open(PROFILE, 'rb').read()).hexdigest()[:12], 'seconds': seconds,
            'compliant': bool(res.get('compliant')),
            'passed_rules': res['details'].get('passedRules'), 'failed_rules': res['details'].get('failedRules'),
            'totals': {'wcag_failed_rules': len(w), 'wcag_failed_checks': sum(r['failed'] for r in w),
                       'ua_only_failed_rules': len(u), 'ua_only_failed_checks': sum(r['failed'] for r in u),
                       'unclassified': [r['id'] for r in rules if r['unclassified']]},
            'rules': rules}


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        v, why = version()
        if v: print(v); sys.exit(0)
        print(why); sys.exit(0 if why == 'not run: VERAPDF=off' else 1)
    if len(sys.argv) != 3: sys.exit(__doc__)
    s = run(sys.argv[1])
    json.dump(s, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    t = s.get('totals')
    print(s['not_run'] if 'not_run' in s else f'{s["tool"]}: {t["wcag_failed_rules"]} WCAG rules failed ({t["wcag_failed_checks"]} checks) · '
          f'{t["ua_only_failed_rules"]} PDF/UA-only rules failed' + (f' · {s["seconds"]} s' if s['seconds'] is not None else ''))
