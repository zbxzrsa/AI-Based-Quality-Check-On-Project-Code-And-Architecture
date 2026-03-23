"""
Audit Log API Endpoints

This module provides REST API endpoints for querying and exporting audit logs.

Validates Requirements: 15.6, 15.7
"""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import uuid
import io
import logging

from app.database.postgresql import get_db
from app.services.audit_logging_service import AuditLoggingService, AuditEventType, AuditLogEntry as AuditLogModel
from app.api.dependencies import get_current_user

router = APIRouter(tags=["audit-logs"])

# Logger instance
logger = logging.getLogger(__name__)


# ========================================
# Request/Response Models
# ========================================

class AuditLogQueryParams(BaseModel):
    """Query parameters for audit log search"""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    user_email: Optional[str] = Field(None, description="Filter by user email")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    event_category: Optional[str] = Field(None, description="Filter by category (auth, authz, data, admin)")
    action: Optional[str] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    success: Optional[bool] = Field(None, description="Filter by success status")
    start_date: Optional[datetime] = Field(None, description="Filter by start date (ISO 8601)")
    end_date: Optional[datetime] = Field(None, description="Filter by end date (ISO 8601)")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class AuditLogEntry(BaseModel):
    """Audit log entry response model"""
    id: str
    timestamp: str = ""
    event_type: str = "unknown"
    event_category: str = "unknown"
    severity: str = "info"
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    action: str = "unknown"
    description: str = ""
    success: bool = True
    error_message: Optional[str] = None
    previous_state: Optional[dict] = None
    new_state: Optional[dict] = None
    changes: Optional[dict] = None
    metadata: Optional[dict] = None


class AuditLogQueryResponse(BaseModel):
    """Response model for audit log queries"""
    total: int = Field(..., description="Total number of matching logs")
    limit: int = Field(..., description="Maximum results per page")
    offset: int = Field(..., description="Current offset")
    items: List[AuditLogEntry] = Field(..., description="Audit log entries")


class AuditLogExportParams(BaseModel):
    """Parameters for audit log export"""
    format: str = Field("json", description="Export format (json or csv)")
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class IntegrityVerificationResponse(BaseModel):
    """Response model for integrity verification"""
    total_logs: int
    verified: bool
    integrity_status: str
    breaks: List[dict]
    verified_at: str


# ========================================
# API Endpoints
# ========================================

@router.get(
    "/",
    response_model=AuditLogQueryResponse,
    summary="Query audit logs",
    description="Query audit logs with filtering by user, action, date range, and other criteria. Requires admin or compliance_officer role.",
)
async def query_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    event_category: Optional[str] = Query(None, description="Filter by category (auth, authz, data, admin)"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Query audit logs with filters
    
    Validates Requirement: 15.6
    
    This endpoint allows administrators and compliance officers to query
    audit logs with various filters including:
    - User (by ID or email)
    - Event type and category
    - Action performed
    - Resource type and ID
    - IP address
    - Success/failure status
    - Date range
    
    Results are paginated and returned in reverse chronological order.
    """
    # Check authorization - only admin and compliance_officer can query audit logs
    if current_user.get("role") not in ["admin", "compliance_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and compliance officers can query audit logs"
        )
    
    # Create audit logging service
    audit_service = AuditLoggingService(db)
    
    # Convert user_id to UUID if provided
    user_id_uuid = None
    if user_id:
        try:
            user_id_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    # Query logs
    result = await audit_service.query_logs(
        user_id=user_id_uuid,
        user_email=user_email,
        event_type=event_type,
        event_category=event_category,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        success=success,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    
    return result


@router.post(
    "/export",
    summary="Export audit logs",
    description="Export audit logs for compliance reporting in JSON or CSV format. Requires admin or compliance_officer role.",
)
async def export_audit_logs(
    export_params: AuditLogExportParams,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export audit logs for compliance reporting
    
    Validates Requirement: 15.7
    
    This endpoint allows administrators and compliance officers to export
    audit logs in JSON or CSV format for compliance reporting and analysis.
    
    Supports the same filtering options as the query endpoint.
    """
    # Check authorization
    if current_user.get("role") not in ["admin", "compliance_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and compliance officers can export audit logs"
        )
    
    # Validate format
    if export_params.format not in ["json", "csv"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid export format. Supported formats: json, csv"
        )
    
    # Create audit logging service
    audit_service = AuditLoggingService(db)
    
    # Convert user_id to UUID if provided
    user_id_uuid = None
    if export_params.user_id:
        try:
            user_id_uuid = uuid.UUID(export_params.user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    # Export logs
    exported_data = await audit_service.export_logs(
        format=export_params.format,
        user_id=user_id_uuid,
        user_email=export_params.user_email,
        event_type=export_params.event_type,
        event_category=export_params.event_category,
        action=export_params.action,
        resource_type=export_params.resource_type,
        resource_id=export_params.resource_id,
        start_date=export_params.start_date,
        end_date=export_params.end_date,
    )
    
    # Determine content type and filename
    if export_params.format == "json":
        media_type = "application/json"
        filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    else:  # csv
        media_type = "text/csv"
        filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(exported_data.encode()),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get(
    "/verify-integrity",
    response_model=IntegrityVerificationResponse,
    summary="Verify audit log integrity",
    description="Verify the integrity of the audit log hash chain. Requires admin role.",
)
async def verify_audit_log_integrity(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Verify integrity of audit trail hash chain
    
    This endpoint verifies that:
    1. Each log entry's hash matches its computed hash
    2. Each log entry's previous_hash matches the previous entry's current_hash
    
    Any breaks in the chain indicate potential tampering.
    
    Only administrators can verify audit log integrity.
    """
    # Check authorization - only admin can verify integrity
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can verify audit log integrity"
        )
    
    # Create audit logging service
    audit_service = AuditLoggingService(db)
    
    # Verify integrity
    result = await audit_service.verify_chain_integrity()
    
    return result


@router.get(
    "/event-types",
    response_model=List[str],
    summary="Get available event types",
    description="Get list of all available audit event types",
)
async def get_event_types(
    current_user: dict = Depends(get_current_user),
):
    """
    Get list of available audit event types
    
    Returns all event type constants that can be used for filtering.
    """
    # Get all event type constants
    event_types = [
        getattr(AuditEventType, attr)
        for attr in dir(AuditEventType)
        if not attr.startswith('_') and isinstance(getattr(AuditEventType, attr), str)
    ]
    
    return sorted(event_types)


@router.get(
    "/statistics",
    summary="Get audit log statistics",
    description="Get statistics about audit logs. Requires admin or compliance_officer role.",
)
async def get_audit_log_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get audit log statistics
    
    Returns statistics including:
    - Total number of logs
    - Logs by event category
    - Logs by success/failure
    - Most active users
    - Most common actions
    """
    # Check authorization
    if current_user.get("role") not in ["admin", "compliance_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and compliance officers can view audit log statistics"
        )
    
    from sqlalchemy import func, select
    
    # Build base query with date filters
    filters = []
    if start_date:
        filters.append(AuditLogModel.timestamp >= start_date)
    if end_date:
        filters.append(AuditLogModel.timestamp <= end_date)
    
    # Total logs
    total_query = select(func.count(AuditLogModel.id))
    if filters:
        total_query = total_query.where(*filters)
    total_result = await db.execute(total_query)
    total_logs = total_result.scalar()
    
    # Logs by category
    category_query = select(
        AuditLogModel.event_category,
        func.count(AuditLogModel.id).label('count')
    ).group_by(AuditLogModel.event_category)
    if filters:
        category_query = category_query.where(*filters)
    category_result = await db.execute(category_query)
    logs_by_category = {row[0]: row[1] for row in category_result}
    
    # Logs by success/failure
    success_query = select(
        AuditLogModel.success,
        func.count(AuditLogModel.id).label('count')
    ).group_by(AuditLogModel.success)
    if filters:
        success_query = success_query.where(*filters)
    success_result = await db.execute(success_query)
    logs_by_success = {row[0]: row[1] for row in success_result}
    
    # Most active users (top 10)
    users_query = select(
        AuditLogModel.user_email,
        func.count(AuditLogModel.id).label('count')
    ).where(AuditLogModel.user_email.isnot(None))
    if filters:
        users_query = users_query.where(*filters)
    users_query = users_query.group_by(AuditLogModel.user_email).order_by(func.count(AuditLogModel.id).desc()).limit(10)
    users_result = await db.execute(users_query)
    most_active_users = [{"email": row[0], "count": row[1]} for row in users_result]
    
    # Most common actions (top 10)
    actions_query = select(
        AuditLogModel.action,
        func.count(AuditLogModel.id).label('count')
    )
    if filters:
        actions_query = actions_query.where(*filters)
    actions_query = actions_query.group_by(AuditLogModel.action).order_by(func.count(AuditLogModel.id).desc()).limit(10)
    actions_result = await db.execute(actions_query)
    most_common_actions = [{"action": row[0], "count": row[1]} for row in actions_result]
    
    return {
        "total_logs": total_logs,
        "logs_by_category": logs_by_category,
        "logs_by_success": {
            "successful": logs_by_success.get(True, 0),
            "failed": logs_by_success.get(False, 0),
        },
        "most_active_users": most_active_users,
        "most_common_actions": most_common_actions,
        "date_range": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        }
    }


# ========================================
# Feature Flag Audit Endpoint
# ========================================

class FeatureFlagChangeLog(BaseModel):
    """Request model for feature flag change logging"""
    flag_name: str = Field(..., description="Name of the feature flag")
    old_value: bool = Field(..., description="Previous value of the flag")
    new_value: bool = Field(..., description="New value of the flag")
    user_id: Optional[str] = Field(None, description="User who made the change")
    timestamp: Optional[datetime] = Field(None, description="Timestamp of the change")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class FeatureFlagAuditResponse(BaseModel):
    """Response model for feature flag audit logging"""
    success: bool = Field(..., description="Whether the log was recorded successfully")
    log_id: str = Field(..., description="ID of the created audit log entry")
    message: str = Field(..., description="Status message")


@router.post(
    "/feature-flags",
    response_model=FeatureFlagAuditResponse,
    summary="Log feature flag state change",
    description="Log feature flag state changes for audit purposes. Records timestamp, user, flag name, old value, and new value.",
    status_code=200,
)
async def log_feature_flag_change(
    change_log: FeatureFlagChangeLog,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Log feature flag state change for audit purposes.

    Validates Requirement: 10.6

    This endpoint logs all feature flag state changes including:
    - Timestamp of the change
    - User identifier who made the change
    - Flag name
    - Old value (previous state)
    - New value (new state)
    - Additional metadata

    The logs are stored in the audit log system and can be queried
    using the audit log query endpoints.

    Args:
        change_log: Feature flag change information
        db: Database session
        current_user: Authenticated user making the request

    Returns:
        FeatureFlagAuditResponse with success status and log ID
    """
    try:
        # Use the provided user_id or fall back to current_user
        user_id = change_log.user_id or current_user.get("id")
        user_email = current_user.get("email", "unknown")

        # Use provided timestamp or current time
        timestamp = change_log.timestamp or datetime.now(timezone.utc)

        # Create audit logging service
        from app.services.audit_logging_service import AuditLoggingService, AuditEventType
        audit_service = AuditLoggingService(db)

        # Prepare metadata
        metadata = change_log.metadata or {}
        metadata.update({
            "flag_name": change_log.flag_name,
            "old_value": change_log.old_value,
            "new_value": change_log.new_value,
            "changed_at": timestamp.isoformat(),
        })

        # Log the feature flag change
        log_id = await audit_service.log_event(
            event_type=AuditEventType.FEATURE_FLAG_CHANGE,
            event_category="admin",
            severity="info",
            user_id=uuid.UUID(user_id) if user_id else None,
            user_email=user_email,
            action="update_feature_flag",
            description=f"Feature flag '{change_log.flag_name}' changed from {change_log.old_value} to {change_log.new_value}",
            resource_type="feature_flag",
            resource_id=change_log.flag_name,
            resource_name=change_log.flag_name,
            success=True,
            previous_state={"enabled": change_log.old_value},
            new_state={"enabled": change_log.new_value},
            changes={"enabled": {"from": change_log.old_value, "to": change_log.new_value}},
            metadata=metadata,
        )

        # Also log to structured logging system
        logger.info(
            "Feature flag state changed",
            extra={
                "event_type": "feature_flag_change",
                "flag_name": change_log.flag_name,
                "old_value": change_log.old_value,
                "new_value": change_log.new_value,
                "user_id": user_id,
                "user_email": user_email,
                "timestamp": timestamp.isoformat(),
                "log_id": str(log_id),
            }
        )

        return FeatureFlagAuditResponse(
            success=True,
            log_id=str(log_id),
            message=f"Feature flag change logged successfully"
        )

    except ValueError as e:
        # Handle invalid UUID or other validation errors
        logger.error(
            "Invalid feature flag change log data",
            extra={
                "error": str(e),
                "flag_name": change_log.flag_name,
            }
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Failed to log feature flag change",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "flag_name": change_log.flag_name,
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to log feature flag change"
        )

