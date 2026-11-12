import os
import sys

# Set test environment flag and in-memory test database URL
os.environ["TESTING"] = "1"
os.environ.setdefault("DATABASE_URL", "sqlite:///file:michito_test?mode=memory&cache=shared&uri=true")

# Ensure workspace root is always on sys.path for test discovery
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

