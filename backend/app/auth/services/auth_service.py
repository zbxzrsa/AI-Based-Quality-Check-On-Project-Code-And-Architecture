"""
Compatibility shim for legacy imports of app.auth.services.auth_service.
"""

from . import AuthResult, AuthService, TokenPayload

__all__ = ["AuthResult", "AuthService", "TokenPayload"]
