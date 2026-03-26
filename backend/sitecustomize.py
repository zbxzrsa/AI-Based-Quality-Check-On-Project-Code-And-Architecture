"""
Backend startup path bootstrap.

When Python is launched from the backend directory, this module is imported
automatically by the interpreter. We use it to add the repository root to
``sys.path`` so shared packages such as ``common`` remain importable without
requiring callers to set PYTHONPATH manually.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
repo_root_str = str(REPO_ROOT)

if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)
