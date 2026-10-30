"""webapp/jobrun.py: runs one job's command and records its end. Started by jobs.py in a new session (its own process group).

    python3 webapp/jobrun.py <jobs folder> <job id>

The command writes straight into the job's log (its stdout and stderr are the log file), so it never depends on this
process staying alive to print. Ctrl+C sent to the group reaches the command as Ctrl+C; this process only waits (it has
a do-nothing handler, not SIG_IGN, because an ignored signal would be inherited across exec) and then writes the exit.
"""
import os, sys, signal, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webapp import jobs  # noqa: E402

def main():
    J, jid = sys.argv[1], sys.argv[2]
    signal.signal(signal.SIGINT, lambda *a: None)
    job = jobs.load(J, jid)
    with open(jobs.log_path(J, jid), 'ab') as log:
        log.write(f'job {jid}: {" ".join(job["argv"])}\n'.encode()); log.flush()
        try: p = subprocess.Popen(job['argv'], cwd=jobs.PIPELINE, env=job['env'], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        except OSError as e:
            log.write(f'could not start: {e}\n'.encode())
            jobs.update(J, jid, status='failed', exit=127, ended=jobs.now()); return
    jobs.update(J, jid, child_pid=p.pid)
    rc = p.wait()
    jobs.update(J, jid, status='done' if rc == 0 else 'failed', exit=rc, ended=jobs.now())

if __name__ == '__main__':
    main()
