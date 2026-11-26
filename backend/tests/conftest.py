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
    Ensures every automated test executes against a pristine, isolated deduplication ledger
    and directs all generated artifacts into an isolated temporary outputs directory.
    Prevents cross-test pollution and stops outputs/ directory disk bloat.
    """
    test_ledger_path = str(tmp_path / "test_isolated_ledger.json")
    test_outputs_dir = str(tmp_path / "test_outputs")
    os.makedirs(test_outputs_dir, exist_ok=True)
    monkeypatch.setenv("TEST_LEDGER_PATH", test_ledger_path)
    monkeypatch.setenv("MICHITO_OUTPUTS_DIR", test_outputs_dir)
    if os.path.exists(test_ledger_path):
        os.remove(test_ledger_path)
    yield test_ledger_path
    if os.path.exists(test_ledger_path):
        try:
            os.remove(test_ledger_path)
        except Exception:
            pass


