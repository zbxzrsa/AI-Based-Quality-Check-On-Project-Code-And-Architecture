"""
Compatibility router for project invitation endpoints.

The refactored invitation API is the maintained implementation.
This file preserves the historical import path for any internal callers.
"""

from app.api.v1.refactored_invitations import router

__all__ = ["router"]
