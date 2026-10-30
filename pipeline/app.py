"""app.py: the pipeline in the browser, on this computer only (127.0.0.1). One start command; the terminal then stays idle.

    python3 app.py [<run folder>] [--port N] [--config FILE] [--no-browser]

Opens the run's page (its review.html, with buttons that run the same commands as review_workorder.py). Settings:
webapp/settings.json < webapp/settings.local.json (this machine; git-ignored) < --config FILE < an exported VERAPDF
(docs/app.md). The app checks its setup first and does not start without the Python libraries, veraPDF or Java.

If an app with the same settings already answers on the port, its page is opened and this command ends. --port N starts
a separate one on purpose. Ctrl+C stops the app: running jobs carry on and finish (their state is on disk); queued jobs
wait for the next start; a review page this app opened gets Ctrl+C too, as in a terminal (its session stays open), unless
it is past Finish (then it is applying, and is left to finish).
"""
import os, sys, json, signal, argparse, threading, webbrowser, urllib.request, urllib.parse, datetime, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from webapp import config, checks, jobs, server  # noqa: E402

def ping(port):
    """The app answering on port: its ping, or None when nothing answers; 'other' when something else does."""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/ping', timeout=2) as r: d = json.load(r)
        return d if isinstance(d, dict) and d.get('app') == 'pdfrem' else 'other'
    except urllib.error.HTTPError: return 'other'
    except (OSError, ValueError): return None

def interrupted(*a): raise KeyboardInterrupt

def dispatcher(s, stop):
    while not stop.wait(1.0):
        try: jobs.tick(s['jobs'], s)
        except Exception:
            with open(os.path.join(s['jobs'], 'server.log'), 'a', encoding='utf-8') as f: f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")} dispatcher\n{traceback.format_exc()}\n')

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run_dir', nargs='?', help='a run folder (under the runs folder) to open')
    ap.add_argument('--port', type=int); ap.add_argument('--config'); ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()
    try: s = config.load(a.config)
    except config.Bad as e: sys.exit(f'the app cannot start: {e}')
    if a.port: s['port'] = a.port
    target = '/'
    if a.run_dir:
        R = os.path.realpath(a.run_dir)
        if not server.inside(s['runs'], R) or not os.path.isfile(os.path.join(R, 'record.json')):
            sys.exit(f'{a.run_dir} is not a finished run under {s["runs"]} (no record.json there)')
        target = '/run/' + '/'.join(urllib.parse.quote(x) for x in os.path.relpath(R, os.path.realpath(s['runs'])).split(os.sep)) + '/'
    url = f'http://127.0.0.1:{s["port"]}'
    code = config.code_fingerprint()                             # the code on disk now: the server keeps this one
    other = ping(s['port'])
    if isinstance(other, dict):
        if other.get('root') == config.ROOT and other.get('settings') == s['sha']:
            if other.get('code') != code:                        # its pages and routes would not match the code on disk
                sys.exit(f'the running app is older than the code on disk: stop it and start again (it answers at {url}/)')
            print(f'the app is already running at {url}/' + ('' if a.no_browser else ': opening it'))
            if not a.no_browser: webbrowser.open(url + target)
            return
        sys.exit(f'another app answers at {url}/ with other settings (or from another checkout, {other.get("root")}): start this one with --port N')
    if other == 'other': sys.exit(f'port {s["port"]} is in use by another program: start the app with --port N')
    items = checks.check(s)
    for x in items:
        print(f'  {"ready  " if x["ok"] else "MISSING" if x["required"] else "missing"}  {x["name"]}: {x["detail"]}' + (f'\n           fix: {x["fix"]}' if x['fix'] else ''))
    miss = checks.required_missing(items)
    if miss: sys.exit(f'the app cannot start: {", ".join(x["name"] for x in miss)} missing (fix above)')
    os.makedirs(s['jobs'], exist_ok=True)
    jobs.recover(s['jobs'])
    try: srv = server.make(s, items, code)
    except OSError as e: sys.exit(f'the app cannot listen on 127.0.0.1:{s["port"]} ({e}): start it with --port N')
    signal.signal(signal.SIGINT, signal.default_int_handler)     # Ctrl+C works even when started from a script
    signal.signal(signal.SIGTERM, interrupted)                    # a plain kill stops it the same way
    stop = threading.Event(); t = threading.Thread(target=dispatcher, args=(s, stop), daemon=True); t.start()
    print(f'the app: {url}{target}\n  Ctrl+C stops it; running jobs carry on and finish, queued ones wait for the next start.', flush=True)
    if not a.no_browser:
        try: webbrowser.open(url + target)
        except Exception: pass
    try: srv.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt: print('\nthe app stopped')
    finally:
        stop.set(); srv.server_close()
        close_reviews(s)

def close_reviews(s):
    """At stop: Ctrl+C to the review pages this app started that are still before Finish, as Ctrl+C in a terminal (the
    session stays open). One past Finish is applying and is left to finish (decided from disk, never from the log)."""
    for j in jobs.all_jobs(s['jobs']):
        if j['kind'] != 'review' or j['status'] != 'running' or j.get('app_pid') != os.getpid(): continue
        ok, why = jobs.interrupt(s['jobs'], j['id'], s['runs'])
        print(f'  {j["run"]}: ' + ('review page closed; its session stays open (Review again carries on with it)' if ok else f'left as it is: {why}'))

if __name__ == '__main__':
    main()
