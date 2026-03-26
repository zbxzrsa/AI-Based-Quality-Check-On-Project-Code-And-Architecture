"""
Backend-local compatibility package for the shared ``common`` module tree.

When the backend is executed with its own directory as the working directory,
Python cannot normally see the repository-level ``common`` package. We extend
the package search path here so imports like ``common.shared.enums`` continue
to resolve without requiring manual PYTHONPATH configuration.
"""

from __future__ import annotations

from pathlib import Path


_repo_common = Path(__file__).resolve().parents[2] / "common"

if _repo_common.exists():
    __path__.append(str(_repo_common))
