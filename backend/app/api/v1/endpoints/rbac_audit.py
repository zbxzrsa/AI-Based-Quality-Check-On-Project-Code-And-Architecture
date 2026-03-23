"""
RBAC Audit Log endpoints.
"""
from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgresql import get_db
from app.auth import (
    Permission,
    AuditService,
    AuditFilter,
    TokenPayload,
    require_permission,
)


router = APIRouter()


# Response Models
class AuditLogResponse(BaseModel):
    """Audit log response model."""
    id: str
    timestamp: str
    user_id: str
    username: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: str
    user_agent: Optional[str]
    success: bool
    error_message: Optional[str]


@router.get("/logs", response_model=List[AuditLogResponse])
async def query_audit_logs(
    current_user: Annotated[TokenPayload, Depends(require_permission(Permission.VIEW_USER))],
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip")
):
    """
    Query audit logs with filters (Admin only).
    
    Requires VIEW_USER permission (Admin only).
    
    Query parameters:
    - **user_id**: Filter by user ID
    - **action**: Filter by action type
    - **start_date**: Filter by start date (ISO format)
    - **end_date**: Filter by end date (ISO format)
    - **success**: Filter by success status (true/false)
    - **limit**: Maximum number of logs to return (1-1000, default 100)
    - **offset**: Number of logs to skip (for pagination)
    """
    # Parse dates if provided
    start_datetime = None
    end_datetime = None
    
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (e.g., 2024-01-01T00:00:00Z)"
            )
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (e.g., 2024-01-01T23:59:59Z)"
            )
    
    # Create filter
    filter = AuditFilter(
        user_id=user_id,
        action=action,
        start_date=start_datetime,
        end_date=end_datetime,
        success=success,
        limit=limit,
        offset=offset
    )
    
    # Query logs
    logs = AuditService.query_logs(db, filter)
    
    return [
        AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            user_id=log.user_id,
            username=log.username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            success=log.success,
            error_message=log.error_message
        )
        for log in logs
    ]


@router.get("/logs/user/{user_id}", response_model=List[AuditLogResponse])
async def get_user_audit_logs(
    user_id: str,
    current_user: Annotated[TokenPayload, Depends(require_permission(Permission.VIEW_USER))],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return")
):
    """
    Get audit logs for a specific user (Admin only).
    
    Requires VIEW_USER permission (Admin only).
    
    Query parameters:
    - **limit**: Maximum number of logs to return (1-1000, default 100)
    """
    logs = AuditService.get_user_logs(db, user_id, limit)
    
    return [
        AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            user_id=log.user_id,
            username=log.username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            success=log.success,
            error_message=log.error_message
        )
        for log in logs
    ]
