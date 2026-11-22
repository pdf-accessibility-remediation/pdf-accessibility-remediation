"""lib/peak.py: each pipeline step's peak memory, measured in its own process (#167, review 02 M4).

Imported by the step scripts run_api.sh times (intake, audit, decide, apply, verify, the language and page-reading steps,
vera, review_workorder). When PEAK_FILE is set (run_api.sh's stage() sets it for each step), the process writes its peak
resident memory in bytes there at exit, keeping the larger of what is already in the file (a stage may start several
processes). Nothing happens without PEAK_FILE. ru_maxrss is bytes on macOS and kilobytes on Linux: normalised here.
"""
import os, sys, atexit, resource


def peak_bytes():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r) if sys.platform == 'darwin' else int(r) * 1024


def _record():
    p = os.environ.get('PEAK_FILE')
    if not p: return
    try:
        try: old = int(open(p).read().strip() or 0)
        except (OSError, ValueError): old = 0
        with open(p, 'w') as f: f.write(str(max(old, peak_bytes())))
    except OSError:
        pass


atexit.register(_record)
