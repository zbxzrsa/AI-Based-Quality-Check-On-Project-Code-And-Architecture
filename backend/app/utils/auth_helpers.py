"""
Authentication and authorization helper utilities.

This module provides reusable auth check functions following the DRY principle.
"""
from typing import Optional
from fastapi import HTTPException, status, Request

from app.models import User


def require_self_or_admin(
    current_user: User,
    target_user_id: str,
    error_message: str = "You can only access your own data"
) -> None:
    """
    Verify user is accessing their own data or is an admin.
    
    Args:
        current_user: Currently authenticated user
        target_user_id: ID of the user being accessed
        error_message: Custom error message
        
    Raises:
        HTTPException: 403 if user is not authorized
    """
    if str(current_user.id) != target_user_id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message
        )


def require_admin(
    current_user: User,
    error_message: str = "Admin privileges required"
) -> None:
    """
    Verify user has admin role.
    
    Args:
        current_user: Currently authenticated user
        error_message: Custom error message
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message
        )


def require_active_user(
    user: User,
    error_message: str = "User account is not active"
) -> None:
    """
    Verify user account is active.
    
    Args:
        user: User to check
        error_message: Custom error message
        
    Raises:
        HTTPException: 403 if user is not active
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message
        )


def require_email_confirmed(
    user: User,
    error_message: str = "Email must be confirmed to perform this action"
) -> None:
    """
    Verify user email is confirmed.
    
    Args:
        user: User to check
        error_message: Custom error message
        
    Raises:
        HTTPException: 403 if email not confirmed
    """
    if not user.email_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message
        )


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Supports X-Forwarded-For header for proxied requests.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address or "0.0.0.0" if unavailable
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def get_user_agent(request: Request) -> str:
    """
    Extract user agent from request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User agent string or "unknown" if unavailable
    """
    return request.headers.get("user-agent", "unknown")


def require_role(
    current_user: User,
    allowed_roles: list[str],
    error_message: Optional[str] = None
) -> None:
    """
    Verify user has one of the allowed roles.
    
    Args:
        current_user: Currently authenticated user
        allowed_roles: List of allowed role values
        error_message: Custom error message
        
    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    if current_user.role.value not in allowed_roles:
        msg = error_message or f"One of these roles required: {', '.join(allowed_roles)}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg
        )
