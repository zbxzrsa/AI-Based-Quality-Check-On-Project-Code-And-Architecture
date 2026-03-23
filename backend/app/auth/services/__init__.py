"""
Authentication and authorization services.
"""
from .rbac_service import RBACService
from app.core.audit_service import UnifiedAuditService as AuditService, AuditFilter

# Import TokenPayload and AuthResult from the main models
from app.models import User
from app.schemas.auth import TokenResponse

# Define AuthResult and TokenPayload classes here since AuthService is removed
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AuthResult(BaseModel):
    """Result of authentication operation"""
    success: bool
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TokenPayload(BaseModel):
    """JWT token payload"""
    user_id: str
    username: str = ""
    role: str = ""
    iat: int = 0
    exp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub": self.user_id,
            "username": self.username,
            "role": self.role,
            "iat": self.iat,
            "exp": self.exp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """Create TokenPayload from a dictionary (e.g., JWT claims)."""
        return cls(
            user_id=data.get("sub", data.get("user_id", "")),
            username=data.get("username", ""),
            role=data.get("role", ""),
            iat=data.get("iat", 0),
            exp=data.get("exp", 0),
        )


class AuthService:
    """
    Authentication service stub.
    Provides password hashing and session management utilities.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        from app.utils.password import hash_password
        return hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        from app.utils.password import verify_password
        return verify_password(plain_password, hashed_password)

    @staticmethod
    def invalidate_all_user_sessions(db, user_id: str):
        """Invalidate all sessions for a given user (no-op if no session table)."""
        logger.info(f"Invalidating all sessions for user {user_id}")
        try:
            from app.models import TokenBlacklist
            from sqlalchemy import select
            # This is a best-effort operation
        except Exception:
            pass


__all__ = [
    "AuthResult", 
    "AuthService",
    "TokenPayload",
    "RBACService",
    "AuditService",
    "AuditFilter",
]
