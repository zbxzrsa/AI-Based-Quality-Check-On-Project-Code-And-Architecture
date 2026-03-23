"""
Comprehensive Audit Logging Service

This service implements comprehensive audit logging for all security-relevant actions
including authentication attempts, authorization failures, data modifications, and
administrative actions.

Validates Requirements: 1.10, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, DateTime, Text, Index, Boolean, select, and_, func, desc
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import hashlib
import json
import logging

from app.database.postgresql import Base

logger = logging.getLogger(__name__)


class AuditEventType:
    """Audit event type constants"""
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_PASSWORD_CHANGE = "auth.password.change"
    AUTH_PASSWORD_RESET = "auth.password.reset"
    
    # Authorization events
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_PERMISSION_DENIED = "authz.permission.denied"
    AUTHZ_ROLE_INSUFFICIENT = "authz.role.insufficient"
    
    # Data modification events
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # Administrative events
    ADMIN_USER_CREATE = "admin.user.create"
    ADMIN_USER_UPDATE = "admin.user.update"
    ADMIN_USER_DELETE = "admin.user.delete"
    ADMIN_ROLE_ASSIGN = "admin.role.assign"
    ADMIN_ROLE_REVOKE = "admin.role.revoke"
    ADMIN_PROJECT_CREATE = "admin.project.create"
    ADMIN_PROJECT_DELETE = "admin.project.delete"
    ADMIN_CONFIG_CHANGE = "admin.config.change"
    ADMIN_SYSTEM_SETTING = "admin.system.setting"
    
    # Feature flag events
    FEATURE_FLAG_CHANGE = "admin.feature_flag.change"


class AuditLogEntry(Base):
    """
    Immutable audit log table with hash chain for integrity verification
    
    Features:
    - Cryptographic hash chain for tamper detection
    - Complete action context with before/after states
    - User, IP, and user agent tracking
    - Searchable metadata and indexing
    - Compliance framework tagging
    """
    __tablename__ = "audit_log_entries"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Hash chain for immutability
    previous_hash = Column(String(64), nullable=True, index=True)
    current_hash = Column(String(64), nullable=False, unique=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Event classification
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)  # auth, authz, data, admin
    severity = Column(String(20), nullable=False, default="info")  # info, warning, error, critical
    
    # Resource information
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    resource_name = Column(String(500), nullable=True)
    
    # Actor information
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    user_role = Column(String(50), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Request context
    ip_address = Column(INET, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(1000), nullable=True)
    
    # Action details
    action = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    success = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)
    
    # State tracking (for data modifications)
    previous_state = Column(JSONB, nullable=True)
    new_state = Column(JSONB, nullable=True)
    changes = Column(JSONB, nullable=True)  # Computed diff
    
    # Additional context
    event_metadata = Column(JSONB, nullable=True)
    
    # Compliance and retention
    compliance_frameworks = Column(JSONB, nullable=True)  # ["PCI-DSS", "HIPAA", "GDPR"]
    retention_until = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_audit_entry_timestamp_desc', timestamp.desc()),
        Index('idx_audit_entry_user_timestamp', 'user_id', timestamp.desc()),
        Index('idx_audit_entry_event_timestamp', 'event_type', timestamp.desc()),
        Index('idx_audit_entry_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_entry_category_timestamp', 'event_category', timestamp.desc()),
        Index('idx_audit_entry_ip_timestamp', 'ip_address', timestamp.desc()),
    )


class AuditLoggingService:
    """
    Service for managing comprehensive audit logging
    
    This service provides:
    - Logging of all authentication attempts
    - Logging of all authorization failures
    - Logging of all data modifications with before/after values
    - Logging of all administrative actions
    - Immutable audit trail with hash chain
    - Query and export functionality
    """
    
    def __init__(self, db_session: AsyncSession, default_retention_days: int = 2555):
        """
        Initialize audit logging service
        
        Args:
            db_session: Database session
            default_retention_days: Default retention period (7 years = 2555 days)
        """
        self.db = db_session
        self.default_retention_days = default_retention_days
    
    async def log_authentication_attempt(
        self,
        user_email: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        user_id: Optional[uuid.UUID] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """
        Log authentication attempt (login)
        
        Validates Requirement: 15.1
        
        Args:
            user_email: Email of user attempting to authenticate
            success: Whether authentication succeeded
            ip_address: Client IP address
            user_agent: Client user agent string
            user_id: User ID if authentication succeeded
            error_message: Error message if authentication failed
            metadata: Additional context
        
        Returns:
            Created audit log entry
        """
        event_type = AuditEventType.AUTH_LOGIN_SUCCESS if success else AuditEventType.AUTH_LOGIN_FAILURE
        
        return await self._create_log_entry(
            event_type=event_type,
            event_category="auth",
            severity="info" if success else "warning",
            action="login",
            description=f"User {user_email} {'successfully authenticated' if success else 'failed to authenticate'}",
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )
    
    async def log_authorization_failure(
        self,
        user_id: uuid.UUID,
        user_email: str,
        user_role: str,
        resource_type: str,
        resource_id: str,
        attempted_action: str,
        ip_address: str,
        user_agent: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """
        Log authorization failure
        
        Validates Requirement: 15.2
        
        Args:
            user_id: ID of user attempting action
            user_email: Email of user
            user_role: Role of user
            resource_type: Type of resource being accessed
            resource_id: ID of resource
            attempted_action: Action that was attempted
            ip_address: Client IP address
            user_agent: Client user agent
            reason: Reason for denial
            metadata: Additional context
        
        Returns:
            Created audit log entry
        """
        return await self._create_log_entry(
            event_type=AuditEventType.AUTHZ_ACCESS_DENIED,
            event_category="authz",
            severity="warning",
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            action=attempted_action,
            description=f"User {user_email} (role: {user_role}) denied access to {resource_type}:{resource_id} for action '{attempted_action}'. Reason: {reason}",
            success=False,
            error_message=reason,
            metadata=metadata or {},
        )
    
    async def log_data_modification(
        self,
        user_id: uuid.UUID,
        user_email: str,
        user_role: str,
        operation: str,  # create, update, delete
        resource_type: str,
        resource_id: str,
        resource_name: Optional[str],
        previous_state: Optional[Dict[str, Any]],
        new_state: Optional[Dict[str, Any]],
        ip_address: str,
        user_agent: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """
        Log data modification with before/after values
        
        Validates Requirement: 15.3
        
        Args:
            user_id: ID of user performing modification
            user_email: Email of user
            user_role: Role of user
            operation: Type of operation (create, update, delete)
            resource_type: Type of resource modified
            resource_id: ID of resource
            resource_name: Name of resource
            previous_state: State before modification
            new_state: State after modification
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional context
        
        Returns:
            Created audit log entry
        """
        # Compute changes for updates
        changes = None
        if operation == "update" and previous_state and new_state:
            changes = self._compute_changes(previous_state, new_state)
        
        event_type_map = {
            "create": AuditEventType.DATA_CREATE,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
        }
        
        return await self._create_log_entry(
            event_type=event_type_map.get(operation, AuditEventType.DATA_UPDATE),
            event_category="data",
            severity="info",
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            action=f"{operation}_{resource_type}",
            description=f"User {user_email} {operation}d {resource_type} '{resource_name or resource_id}'",
            success=True,
            previous_state=previous_state,
            new_state=new_state,
            changes=changes,
            metadata=metadata or {},
        )
    
    async def log_administrative_action(
        self,
        user_id: uuid.UUID,
        user_email: str,
        user_role: str,
        action: str,
        description: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """
        Log administrative action
        
        Validates Requirement: 15.4
        
        Args:
            user_id: ID of admin user
            user_email: Email of admin
            user_role: Role of admin
            action: Administrative action performed
            description: Human-readable description
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether action succeeded
            error_message: Error message if failed
            metadata: Additional context
        
        Returns:
            Created audit log entry
        """
        return await self._create_log_entry(
            event_type=f"admin.{action}",
            event_category="admin",
            severity="info" if success else "error",
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            description=description,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )
    
    async def _create_log_entry(
        self,
        event_type: str,
        event_category: str,
        action: str,
        description: str,
        severity: str = "info",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_frameworks: Optional[List[str]] = None,
        retention_days: Optional[int] = None,
    ) -> AuditLogEntry:
        """
        Create immutable audit log entry with hash chain
        
        This method:
        1. Retrieves the latest log entry for hash chaining
        2. Creates new log entry with all provided data
        3. Computes cryptographic hash linking to previous entry
        4. Saves to database (append-only)
        
        Args:
            Various audit log fields
        
        Returns:
            Created audit log entry
        """
        try:
            # Get previous log entry for hash chain
            previous_log = await self._get_latest_log()
            previous_hash = previous_log.current_hash if previous_log else None
            
            # Calculate retention date
            retention_days = retention_days or self.default_retention_days
            retention_until = datetime.now(timezone.utc) + timedelta(days=retention_days)
            
            # Create log entry
            log_entry = AuditLogEntry(
                id=uuid.uuid4(),
                previous_hash=previous_hash,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                event_category=event_category,
                severity=severity,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                request_method=request_method,
                request_path=request_path,
                action=action,
                description=description,
                success=success,
                error_message=error_message,
                previous_state=previous_state,
                new_state=new_state,
                changes=changes,
                event_metadata=metadata,
                compliance_frameworks=compliance_frameworks,
                retention_until=retention_until,
            )
            
            # Generate hash for immutability
            log_entry.current_hash = self._generate_hash(log_entry)
            
            # Save to database (append-only)
            self.db.add(log_entry)
            await self.db.commit()
            await self.db.refresh(log_entry)
            
            logger.info(f"Audit log created: {event_type} by {user_email or 'system'}")
            
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {str(e)}")
            await self.db.rollback()
            raise
    
    def _generate_hash(self, log_entry: AuditLogEntry) -> str:
        """
        Generate cryptographic hash for audit log entry
        
        Creates SHA-256 hash of critical fields to detect tampering:
        - Previous hash (creates chain)
        - Timestamp
        - Event details
        - User details
        - Action and description
        - Resource information
        
        Args:
            log_entry: Audit log entry to hash
        
        Returns:
            SHA-256 hash as hex string
        """
        hash_data = {
            "id": str(log_entry.id),
            "previous_hash": log_entry.previous_hash or "",
            "timestamp": log_entry.timestamp.isoformat(),
            "event_type": log_entry.event_type,
            "event_category": log_entry.event_category,
            "resource_type": log_entry.resource_type or "",
            "resource_id": log_entry.resource_id or "",
            "user_id": str(log_entry.user_id) if log_entry.user_id else "",
            "user_email": log_entry.user_email or "",
            "action": log_entry.action,
            "description": log_entry.description,
            "success": log_entry.success,
        }
        
        # Create deterministic JSON string
        hash_string = json.dumps(hash_data, sort_keys=True)
        
        # Generate SHA-256 hash
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    async def _get_latest_log(self) -> Optional[AuditLogEntry]:
        """
        Get the most recent audit log entry for hash chaining
        
        Returns:
            Latest audit log entry or None if no entries exist
        """
        result = await self.db.execute(
            select(AuditLogEntry)
            .order_by(desc(AuditLogEntry.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    def _compute_changes(
        self,
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute changes between previous and new state
        
        Args:
            previous_state: State before modification
            new_state: State after modification
        
        Returns:
            Dictionary of changes with old and new values
        """
        changes = {}
        
        # Find modified and added fields
        for key, new_value in new_state.items():
            old_value = previous_state.get(key)
            if old_value != new_value:
                changes[key] = {
                    "old": old_value,
                    "new": new_value,
                }
        
        # Find removed fields
        for key in previous_state:
            if key not in new_state:
                changes[key] = {
                    "old": previous_state[key],
                    "new": None,
                }
        
        return changes
    
    async def query_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        user_email: Optional[str] = None,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Query audit logs with filters
        
        Validates Requirement: 15.6
        
        Args:
            user_id: Filter by user ID
            user_email: Filter by user email
            event_type: Filter by event type
            event_category: Filter by category (auth, authz, data, admin)
            action: Filter by action
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            ip_address: Filter by IP address
            success: Filter by success status
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            Dictionary with total count and audit log entries
        """
        query = select(AuditLogEntry)
        filters = []
        
        if user_id:
            filters.append(AuditLogEntry.user_id == user_id)
        if user_email:
            filters.append(AuditLogEntry.user_email == user_email)
        if event_type:
            filters.append(AuditLogEntry.event_type == event_type)
        if event_category:
            filters.append(AuditLogEntry.event_category == event_category)
        if action:
            filters.append(AuditLogEntry.action == action)
        if resource_type:
            filters.append(AuditLogEntry.resource_type == resource_type)
        if resource_id:
            filters.append(AuditLogEntry.resource_id == resource_id)
        if ip_address:
            filters.append(AuditLogEntry.ip_address == ip_address)
        if success is not None:
            filters.append(AuditLogEntry.success == success)
        if start_date:
            filters.append(AuditLogEntry.timestamp >= start_date)
        if end_date:
            filters.append(AuditLogEntry.timestamp <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(AuditLogEntry.timestamp)).limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [self._log_to_dict(log) for log in logs],
        }
    
    async def export_logs(
        self,
        format: str = "json",
        **filters
    ) -> str:
        """
        Export audit logs for compliance reporting
        
        Validates Requirement: 15.7
        
        Args:
            format: Export format (json, csv)
            **filters: Query filters (same as query_logs)
        
        Returns:
            Exported data as string
        """
        # Query all matching logs (no pagination for export)
        result = await self.query_logs(limit=1000000, offset=0, **filters)
        
        if format == "json":
            return json.dumps(result, indent=2, default=str)
        elif format == "csv":
            return self._export_to_csv(result["items"])
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_to_csv(self, logs: List[Dict[str, Any]]) -> str:
        """Convert logs to CSV format"""
        import csv
        import io
        
        if not logs:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
        
        return output.getvalue()
    
    def _log_to_dict(self, log: AuditLogEntry) -> Dict[str, Any]:
        """Convert audit log entry to dictionary"""
        return {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "event_type": log.event_type,
            "event_category": log.event_category,
            "severity": log.severity,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "resource_name": log.resource_name,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": log.user_email,
            "user_role": log.user_role,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "user_agent": log.user_agent,
            "action": log.action,
            "description": log.description,
            "success": log.success,
            "error_message": log.error_message,
            "previous_state": log.previous_state,
            "new_state": log.new_state,
            "changes": log.changes,
            "metadata": log.event_metadata,
        }
    
    async def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of audit trail hash chain
        
        Checks:
        1. Each log's hash matches its computed hash
        2. Each log's previous_hash matches the previous log's current_hash
        
        Returns:
            Verification result with status and any breaks found
        """
        # Get all logs in chronological order
        result = await self.db.execute(
            select(AuditLogEntry).order_by(AuditLogEntry.timestamp)
        )
        logs = result.scalars().all()
        
        breaks = []
        previous_hash = None
        
        for log in logs:
            # Verify hash matches
            expected_hash = self._generate_hash(log)
            if log.current_hash != expected_hash:
                breaks.append({
                    "log_id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "reason": "Hash mismatch - log may have been tampered with",
                    "expected_hash": expected_hash,
                    "actual_hash": log.current_hash,
                })
            
            # Verify chain
            if log.previous_hash != previous_hash:
                breaks.append({
                    "log_id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "reason": "Chain break - previous hash doesn't match",
                    "expected_previous": previous_hash,
                    "actual_previous": log.previous_hash,
                })
            
            previous_hash = log.current_hash
        
        return {
            "total_logs": len(logs),
            "verified": len(breaks) == 0,
            "integrity_status": "intact" if len(breaks) == 0 else "compromised",
            "breaks": breaks,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
