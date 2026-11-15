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
