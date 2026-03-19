"""
Enterprise RBAC Authentication Module for Backend.

This module provides role-based access control (RBAC) functionality including:
- User authentication and authorization
- JWT token management
- Session management
- Role-based permissions
- Project-level access control
- Audit logging
"""

from .middleware import (
    AuthMiddleware,
    get_current_user,
    require_permission,
    require_project_access,
    require_role,
    security,
)
from .models import (
    ROLE_PERMISSIONS,
    AuditLog,
    Permission,
    Project,
    ProjectAccess,
    Role,
    Session,
    User,
)
from .services import (
    AuditFilter,
    AuditService,
    AuthService,
    AuthResult,
    RBACService,
    TokenPayload,
)

__all__ = [
    # Models
    "User",
    "Session",
    "Project",
    "ProjectAccess",
    "AuditLog",
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    # Services
    "AuthService",
    "AuthResult",
    "TokenPayload",
    "RBACService",
    "AuditService",
    "AuditFilter",
    # Middleware
    "AuthMiddleware",
    "security",
    "get_current_user",
    "require_role",
    "require_permission",
    "require_project_access",
]
