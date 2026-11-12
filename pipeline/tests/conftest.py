"""conftest.py: puts pipeline/ on sys.path, so the tests import the shared modules as the scripts do (from lib import X).

    cd pipeline && python -m pytest tests -q
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# No test may add to the real cost history (runs/.cost-history.jsonl: lib/costhistory.py). Set here, at import, so it covers a
# paid call driven in this process against the fake OpenRouter as well as every child process. The check at the end proves it.
import tempfile, pytest
_REAL_LEDGER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'runs', '.cost-history.jsonl')
_LEDGER_DIR = tempfile.mkdtemp(prefix='cost-history-')
os.environ['COST_HISTORY'] = os.path.join(_LEDGER_DIR, '.cost-history.jsonl')

# apply.py's check mode (#93 (improve performance: home and batch pages, first-time "Review Again", and PDF pipeline step
# timing), Part 3, C2) for the whole suite, every child process included: wherever apply.py would use its kept tag-tree
# index, it walks again and compares, and stops with the line "TREE INDEX STALE: …" on any difference. Each stop is also
# written to the file below, so a stop inside a trial run, a draft or a pipeline a test only half reads still fails the
# session (review 12 M3). Production runs never set these.
_STALE_LOG = os.path.join(_LEDGER_DIR, 'tree-index-stale.log')
os.environ['APPLY_TREE_CHECK'] = '1'
os.environ['APPLY_TREE_STALE_LOG'] = _STALE_LOG

def _stops():
    return open(_STALE_LOG, encoding='utf-8').read() if os.path.exists(_STALE_LOG) else ''

@pytest.fixture(autouse=True)
def apply_never_used_a_stale_tree_index():
    """Fails the test during which any apply.py it started stopped in the check mode."""
    before = len(_stops())
    yield
    new = _stops()[before:]
    assert not new, 'apply.py stopped in its check mode (TREE INDEX STALE):\n' + new

def pytest_sessionfinish(session, exitstatus):
    """review 14 L3: a stop written after the last test's own check (a draft or trial run still finishing in another
    thread or process when its test ended) fails the session too: the stale log must be empty at the very end."""
    left = _stops()
    if left:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        sys.stderr.write('\napply.py stopped in its check mode (TREE INDEX STALE) during the session:\n' + left)

def _ledger_size():
    return os.path.getsize(_REAL_LEDGER) if os.path.exists(_REAL_LEDGER) else None

@pytest.fixture(autouse=True)
def own_cost_history(tmp_path, monkeypatch):
    """Each test its own ledger, so one test's fake paid calls never enter the 80-call window of the next."""
    monkeypatch.setenv('COST_HISTORY', str(tmp_path / '.cost-history.jsonl'))

@pytest.fixture(scope='session', autouse=True)
def real_cost_history_is_never_written():
    before = _ledger_size()
    yield
    assert _ledger_size() == before, 'a test wrote to the real cost history'
