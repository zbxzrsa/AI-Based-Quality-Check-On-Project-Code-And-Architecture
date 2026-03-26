"""
Compatibility re-exports for modules that still import app.core.dependencies.
"""

from app.api.dependencies import (
    check_project_access,
    get_current_active_user,
    get_current_user,
    require_admin,
    require_compliance,
    require_manager,
    require_reviewer,
)

__all__ = [
    "check_project_access",
    "get_current_active_user",
    "get_current_user",
    "require_admin",
    "require_compliance",
    "require_manager",
    "require_reviewer",
]
