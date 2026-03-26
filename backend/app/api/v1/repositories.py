"""
Compatibility router for repository endpoints.

The refactored repository implementation is the canonical source of truth.
This module keeps the historical import path stable for `api_router`.
"""

from app.api.v1.refactored_repositories import router

__all__ = ["router"]
