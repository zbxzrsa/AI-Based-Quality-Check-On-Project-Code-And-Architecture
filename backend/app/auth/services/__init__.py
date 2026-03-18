"""
Authentication and authorization services.
"""

from datetime import datetime
from typing import Any, Optional

# Define AuthResult and TokenPayload classes here since AuthService is removed
from pydantic import BaseModel

from app.core.audit_service import AuditFilter
from app.core.audit_service import UnifiedAuditService as AuditService

# Import TokenPayload and AuthResult from the main models
from app.database.models import User
from app.schemas.auth import TokenResponse

from .rbac_service import RBACService


class AuthResult(BaseModel):
    """Result of authentication operation"""

    success: bool
    token: str | None = None
    refresh_token: str | None = None
    user: dict[str, Any] | None = None
    error: str | None = None


class TokenPayload(BaseModel):
    """JWT token payload"""

    user_id: str
    username: str
    role: str
    iat: int
    exp: int

    def to_dict(self) -> dict[str, Any]:
        return {"sub": self.user_id, "username": self.username, "role": self.role, "iat": self.iat, "exp": self.exp}


__all__ = [
    "AuthResult",
    "TokenPayload",
    "RBACService",
    "AuditService",
    "AuditFilter",
]
