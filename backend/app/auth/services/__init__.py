"""
Authentication and authorization services.
"""

from datetime import datetime
from typing import Any, Optional

# Define AuthResult and TokenPayload classes here since AuthService is removed
from pydantic import BaseModel
from passlib.context import CryptContext

from app.core.audit_service import AuditFilter
from app.core.audit_service import UnifiedAuditService as AuditService

from app.schemas.auth import TokenResponse

from .rbac_service import RBACService

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenPayload":
        """Backward-compatible payload parser for legacy JWT key names."""
        return cls(
            user_id=data.get("user_id") or data.get("sub"),
            username=data.get("username", ""),
            role=data.get("role", "USER"),
            iat=data.get("iat", 0),
            exp=data.get("exp", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"sub": self.user_id, "username": self.username, "role": self.role, "iat": self.iat, "exp": self.exp}


class AuthService:
    """Backward-compatible auth helpers used by legacy endpoints."""

    @staticmethod
    def hash_password(password: str) -> str:
        return _pwd_context.hash(password)

    @staticmethod
    def invalidate_all_user_sessions(db: Any, user_id: str) -> None:
        # Session invalidation is handled by token revocation in the new flow.
        _ = (db, user_id)


__all__ = [
    "AuthService",
    "AuthResult",
    "TokenPayload",
    "RBACService",
    "AuditService",
    "AuditFilter",
]
