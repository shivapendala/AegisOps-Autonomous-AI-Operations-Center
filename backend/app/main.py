import os
import sys

# Ensure root directory and backend directory are on PYTHONPATH
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, ".."))
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))

for path in [_root_dir, _backend_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.main import app, create_app

__all__ = ["app", "create_app"]
