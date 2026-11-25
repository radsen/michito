import os
import sys
import pytest

# Set test environment flag and in-memory test database URL
os.environ["TESTING"] = "1"
os.environ.setdefault("DATABASE_URL", "sqlite:///file:michito_test?mode=memory&cache=shared&uri=true")

# Ensure workspace root is always on sys.path for test discovery
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


@pytest.fixture(autouse=True)
def isolate_test_ledger(tmp_path, monkeypatch):
    """
    Ensures every automated test executes against a pristine, isolated deduplication ledger.
    Prevents cross-test pollution where accounts discovered in one test block subsequent scenarios.
    """
    test_ledger_path = str(tmp_path / "test_isolated_ledger.json")
    monkeypatch.setenv("TEST_LEDGER_PATH", test_ledger_path)
    if os.path.exists(test_ledger_path):
        os.remove(test_ledger_path)
    yield test_ledger_path
    if os.path.exists(test_ledger_path):
        try:
            os.remove(test_ledger_path)
        except Exception:
            pass


