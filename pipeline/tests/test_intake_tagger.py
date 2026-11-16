"""intake's auto-tagger call (#129, tagger memory): the machine-wide slots, the heap option, and the out-of-memory stop.
No Java here: the real convert path with a forced low heap is an intake_cases --full case."""
import subprocess, threading, time
import intake


def test_out_of_memory_is_found_in_stderr_not_in_the_tail():
    stderr = 'Picked up JAVA_TOOL_OPTIONS: -XX:MaxRAMPercentage=40\nException in thread "main" java.lang.OutOfMemoryError: Java heap space\n' + '\tat x.y(Z.java:1)\n' * 200
    e = subprocess.CalledProcessError(1, ['java', '-jar', 'x.jar'], output='', stderr=stderr)
    assert 'OutOfMemoryError' not in str(e)                       # what intake used to read
    err, oom = intake.tagger_error(e)
    assert oom is True and len(err) <= 600 and 'OutOfMemoryError' not in err   # found in the full text, not the tail
    assert intake.tagger_error(subprocess.CalledProcessError(1, ['java'], stderr='java.io.IOException: bad xref'))[1] is False


def test_java_options_keep_a_persons_setting_first(monkeypatch):
    monkeypatch.delenv('JAVA_TOOL_OPTIONS', raising=False)
    assert intake.tagger_java_options() == '-XX:MaxRAMPercentage=40'
    monkeypatch.setenv('JAVA_TOOL_OPTIONS', '-Xmx10g')
    assert intake.tagger_java_options() == '-Xmx10g -XX:MaxRAMPercentage=40'     # -Xmx wins over the percentage in Java
    monkeypatch.delenv('JAVA_TOOL_OPTIONS')
    assert intake.tagger_java_options(1467) == '-XX:MaxRAMPercentage=50'          # a book over 1,000 pages: alone, 50%


def test_a_third_tagger_waits_for_a_free_slot(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, 'TAGGER_LOCKS', str(tmp_path)); monkeypatch.setattr(intake, 'TAGGER_SLOTS', 2)
    held, release, got = [], threading.Event(), {}

    def hold():
        with intake.tagger_slot() as s:
            held.append(s['slot']); release.wait(5)
    ts = [threading.Thread(target=hold) for _ in range(2)]
    for t in ts: t.start()
    for _ in range(100):
        if len(held) == 2: break
        time.sleep(0.02)
    assert sorted(held) == [0, 1]

    def third():
        with intake.tagger_slot() as s: got.update(s)
    t3 = threading.Thread(target=third); t3.start(); time.sleep(0.3)
    assert not got                                                 # both slots busy: still waiting
    release.set(); t3.join(10)
    for t in ts: t.join(5)
    assert got and got['waited'] > 0


def test_a_long_book_waits_until_it_can_run_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, 'TAGGER_LOCKS', str(tmp_path)); monkeypatch.setattr(intake, 'TAGGER_SLOTS', 2)
    release, got, held = threading.Event(), {}, threading.Event()

    def short():
        with intake.tagger_slot(300):
            held.set(); release.wait(5)
    t1 = threading.Thread(target=short); t1.start(); held.wait(5)

    def long_():
        with intake.tagger_slot(1467) as s: got.update(s)
    t2 = threading.Thread(target=long_); t2.start(); time.sleep(0.3)
    assert not got                                                 # one short book is tagging: the long one waits
    release.set(); t2.join(10); t1.join(5)
    assert got['slot'] == 'all' and got['waited'] > 0


def test_a_tagger_that_outlives_its_intake_keeps_the_slot(tmp_path, monkeypatch):
    """Review 04 M2: the lock goes when intake dies (SIGKILL), but its tagger child may still run: the slot stays busy
    while the process recorded in the slot file is alive (a `sleep` stands in for the Java tagger)."""
    import os, signal, sys
    monkeypatch.setattr(intake, 'TAGGER_LOCKS', str(tmp_path)); monkeypatch.setattr(intake, 'TAGGER_SLOTS', 1)
    holder = subprocess.Popen([sys.executable, '-c', (
        'import sys, subprocess, time; sys.path.insert(0, %r); import intake\n'
        'intake.TAGGER_LOCKS = %r; intake.TAGGER_SLOTS = 1\n'
        'with intake.tagger_slot() as s:\n'
        '    kid = subprocess.Popen(["sleep", "30"]); intake.tagger_record(s, [kid.pid]); print(kid.pid, flush=True); time.sleep(60)\n'
    ) % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), str(tmp_path))], stdout=subprocess.PIPE, text=True)
    kid = int(holder.stdout.readline())
    try:
        assert intake._take_slot(str(tmp_path / 'slot0.lock')) is None            # held by the holder
        holder.send_signal(signal.SIGKILL); holder.wait(5)
        assert intake._proc_command(kid) == 'sleep'                               # its child still runs
        assert intake._take_slot(str(tmp_path / 'slot0.lock')) is None            # so the slot is still busy
        os.kill(kid, signal.SIGKILL)
        for _ in range(50):
            if intake._proc_command(kid) is None: break
            time.sleep(0.05)
        f = intake._take_slot(str(tmp_path / 'slot0.lock'))                       # the child is gone: free again
        assert f is not None and f.read() == ''
        f.close()
    finally:
        for p in (holder.pid, kid):
            try: os.kill(p, signal.SIGKILL)
            except ProcessLookupError: pass


def wait_for(cond, limit=5.0):
    """Polls cond until it is true or limit seconds pass (a condition, not a fixed sleep); returns its last value."""
    t = time.time()
    while not (v := cond()) and time.time() - t < limit: time.sleep(0.02)
    return v


def test_the_watcher_records_the_taggers_process(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, 'TAGGER_LOCKS', str(tmp_path)); monkeypatch.setattr(intake, 'TAGGER_SLOTS', 1)
    with intake.tagger_slot() as s:
        stop = threading.Event(); w = threading.Thread(target=intake._tagger_children, args=(stop, s), daemon=True); w.start()
        kid = subprocess.Popen(['sleep', '5']); t0 = time.time()
        assert wait_for(lambda: f'{kid.pid} sleep' in (tmp_path / 'slot0.lock').read_text())
        assert time.time() - t0 < 1.0                                             # review 06 M1: within the fast polling, not a second later
        stop.set(); w.join(3); kid.kill(); kid.wait()
    assert (tmp_path / 'slot0.lock').read_text() == ''                            # cleared when the slot is given back


def test_a_kill_within_half_a_second_leaves_the_slot_busy(tmp_path, monkeypatch):
    """Review 06 M1 (W1): intake SIGKILLed 0.3 s after its tagger child started: the child was already recorded, so the slot
    stays busy while the child lives (before, the watcher recorded once a second and the slot was free)."""
    import os, signal, sys
    monkeypatch.setattr(intake, 'TAGGER_LOCKS', str(tmp_path)); monkeypatch.setattr(intake, 'TAGGER_SLOTS', 1)
    holder = subprocess.Popen([sys.executable, '-c', (
        'import sys, subprocess, threading, time; sys.path.insert(0, %r); import intake\n'
        'intake.TAGGER_LOCKS = %r; intake.TAGGER_SLOTS = 1\n'
        'with intake.tagger_slot() as s:\n'
        '    stop = threading.Event(); threading.Thread(target=intake._tagger_children, args=(stop, s), daemon=True).start()\n'
        '    kid = subprocess.Popen(["sleep", "30"]); print(kid.pid, flush=True); time.sleep(60)\n'
    ) % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), str(tmp_path))], stdout=subprocess.PIPE, text=True)
    kid = int(holder.stdout.readline())
    try:
        time.sleep(0.3); holder.send_signal(signal.SIGKILL); holder.wait(5)
        assert intake._proc_command(kid) == 'sleep'                               # its child still runs
        assert intake._take_slot(str(tmp_path / 'slot0.lock')) is None            # recorded in time: the slot is busy
        assert 'process' in intake.BUSY[str(tmp_path / 'slot0.lock')] and str(kid) in intake.BUSY[str(tmp_path / 'slot0.lock')]   # L8: named
    finally:
        for p in (holder.pid, kid):
            try: os.kill(p, signal.SIGKILL)
            except ProcessLookupError: pass


def test_a_failing_pgrep_does_not_end_the_watcher(tmp_path, monkeypatch):
    """Review 06 M1 (W3): one pass that raises is logged and the loop goes on, so the child is still recorded."""
    monkeypatch.setattr(intake, 'TAGGER_LOCKS', str(tmp_path)); monkeypatch.setattr(intake, 'TAGGER_SLOTS', 1)
    real, calls, said = subprocess.run, [], []
    def flaky(argv, *a, **k):
        if argv and argv[0] == 'pgrep':
            calls.append(1)
            if len(calls) <= 2: raise OSError('pgrep is not available')
        return real(argv, *a, **k)
    monkeypatch.setattr(intake.subprocess, 'run', flaky)
    with intake.tagger_slot() as s:
        stop = threading.Event(); w = threading.Thread(target=intake._tagger_children, args=(stop, s, said.append), daemon=True); w.start()
        kid = subprocess.Popen(['sleep', '5'])
        try:
            assert wait_for(lambda: f'{kid.pid} sleep' in (tmp_path / 'slot0.lock').read_text())
            assert w.is_alive() and len(calls) >= 3
            assert len(said) == 1 and 'OSError' in said[0]                        # logged once, not once a pass
        finally:
            stop.set(); w.join(3); kid.kill(); kid.wait()
