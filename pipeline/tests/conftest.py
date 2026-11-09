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
