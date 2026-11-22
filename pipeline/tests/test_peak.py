"""#167 (whole-book work redone per item), memory (review 02 M4): a step's peak memory, written by the step itself at exit
(lib/peak.py) into PEAK_FILE, the larger value kept when a stage starts several processes; nothing without PEAK_FILE."""
import os, sys, subprocess
PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def step(env, code="from lib import peak; x = bytearray(64 * 2 ** 20)"):
    subprocess.run([sys.executable, '-c', code], cwd=PIPE, env=dict(os.environ, **env), check=True)

def test_peak_written_and_the_larger_kept(tmp_path):
    f = tmp_path / 'pk'
    step({'PEAK_FILE': str(f)})
    a = int(f.read_text()); assert a > 64 * 2 ** 20
    f.write_text(str(10 ** 15)); step({'PEAK_FILE': str(f)})
    assert int(f.read_text()) == 10 ** 15

def test_nothing_without_peak_file(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != 'PEAK_FILE'}
    subprocess.run([sys.executable, '-c', 'from lib import peak'], cwd=PIPE, env=env, check=True)
    assert not list(tmp_path.iterdir())
