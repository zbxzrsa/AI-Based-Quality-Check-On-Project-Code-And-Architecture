"""
Audit logging helper utilities.

This module provides reusable audit logging functions following the DRY principle.
"""
from typing import Optional, Any
from uuid import UUID
from fastapi import Request
from sqlalchemy.orm import Session

from app.models import User
from app.services.audit_logging_service import AuditService


def log_action_sync(
    db: Session,
    current_user: User,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Any,
    success: bool = True,
    metadata: Optional[dict] = None
) -> None:
    """
    Log an audit action (sync version).
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        request: FastAPI request object
        action: Action being performed (e.g., "CREATE_USER", "DELETE_PROJECT")
        resource_type: Type of resource (e.g., "User", "Project")
        resource_id: ID of the resource
        success: Whether the action succeeded
        metadata: Additional metadata to log
    """
    ip_address = request.client.host if request.client else "0.0.0.0"
    
    AuditService.log_action(
        db=db,
        user_id=current_user.user_id,
        username=current_user.username,
        action=action,
        ip_address=ip_address,
        success=success,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata
    )


async def log_action_async(
    audit_service: AuditService,
    current_user: User,
    request: Request,
    action: str,
    resource_type: str,
    resource_id: UUID,
    success: bool = True,
    metadata: Optional[dict] = None
) -> None:
    """
    Log an audit action (async version).
    
    Args:
        audit_service: Audit logging service instance
        current_user: Currently authenticated user
        request: FastAPI request object
        action: Action being performed
        resource_type: Type of resource
        resource_id: ID of the resource
        success: Whether the action succeeded
        metadata: Additional metadata to log
    """
    ip_address = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")
    
    await audit_service.log_data_access(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role.value,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        metadata=metadata
    )
