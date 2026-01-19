"""
Immutable Audit Trail System
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
import hashlib
import json
from app.database.postgresql import Base


class AuditLog(Base):
    """
    Immutable audit log table
    
    Features:
    - Cryptographic hash chain for immutability
    - Complete action context
    - User and IP tracking
    - Searchable metadata
    """
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Chain hash (links to previous log entry)
    previous_hash = Column(String(64), nullable=True)
    current_hash = Column(String(64), nullable=False)
    
    # Event details
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    event_type = Column(String(50), nullable=False)  # create, update, delete, access, etc.
    resource_type = Column(String(50), nullable=False)  # user, project, pr, etc.
    resource_id = Column(String(100), nullable=False)
    
    # Actor details
    user_id = Column(UUID(as_uuid=True), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "login", "create_project"
    description = Column(Text, nullable=False)
    
    # Before/after state
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    
    # Additional context
    metadata = Column(JSON, nullable=True)
    
    # Compliance
    compliance_frameworks = Column(JSON, nullable=True)  # ["PCI-DSS", "HIPAA"]
    retention_period_days = Column(Integer, default=2555)  # 7 years default
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_action', 'action'),
    )


class AuditTrailService:
    """Service for managing immutable audit trail"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        description: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_frameworks: Optional[list] = None,
    ) -> AuditLog:
        """
        Create immutable audit log entry
        
        Args:
            event_type: Type of event (create, update, delete, access)
            resource_type: Type of resource (user, project, pr)
            resource_id: ID of the resource
            action: Specific action performed
            description: Human-readable description
            user_id: ID of user performing action
            user_email: Email of user
            user_role: Role of user
            ip_address: Client IP address
            user_agent: Client user agent
            previous_state: State before action
            new_state: State after action
            metadata: Additional context
            compliance_frameworks: Applicable frameworks
            
        Returns:
            Created audit log entry
        """
        # Get previous log entry for hash chain
        previous_log = await self._get_latest_log()
        previous_hash = previous_log.current_hash if previous_log else None
        
        # Create log entry
        log_entry = AuditLog(
            previous_hash=previous_hash,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            description=description,
            previous_state=previous_state,
            new_state=new_state,
            metadata=metadata,
            compliance_frameworks=compliance_frameworks,
        )
        
        # Generate hash
        log_entry.current_hash = self._generate_hash(log_entry)
        
        # Save to database
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        
        return log_entry
    
    def _generate_hash(self, log_entry: AuditLog) -> str:
        """
        Generate cryptographic hash for audit log entry
        
        Creates SHA-256 hash of:
        - Previous hash (for chain)
        - Timestamp
        - Event details
        - User details
        - Action and description
        """
        hash_data = {
            "previous_hash": log_entry.previous_hash or "",
            "timestamp": log_entry.timestamp.isoformat(),
            "event_type": log_entry.event_type,
            "resource_type": log_entry.resource_type,
            "resource_id": log_entry.resource_id,
            "user_id": str(log_entry.user_id) if log_entry.user_id else "",
            "action": log_entry.action,
            "description": log_entry.description,
        }
        
        # Create deterministic JSON string
        hash_string = json.dumps(hash_data, sort_keys=True)
        
        # Generate SHA-256 hash
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    async def _get_latest_log(self) -> Optional[AuditLog]:
        """Get the most recent audit log entry"""
        from sqlalchemy import desc
        
        result = await self.db.execute(
            select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of audit trail hash chain
        
        Returns:
            Verification result with status and any breaks
        """
        from sqlalchemy import select
        
        # Get all logs in chronological order
        result = await self.db.execute(
            select(AuditLog).order_by(AuditLog.timestamp)
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
                    "reason": "Hash mismatch",
                })
            
            # Verify chain
            if log.previous_hash != previous_hash:
                breaks.append({
                    "log_id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "reason": "Chain break",
                })
            
            previous_hash = log.current_hash
        
        return {
            "total_logs": len(logs),
            "verified": len(breaks) == 0,
            "breaks": breaks,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    
    async def search_logs(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search audit logs with filters
        
        Returns:
            Matching audit log entries
        """
        from sqlalchemy import select, and_
        
        query = select(AuditLog)
        filters = []
        
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        if resource_id:
            filters.append(AuditLog.resource_id == resource_id)
        if event_type:
            filters.append(AuditLog.event_type == event_type)
        if action:
            filters.append(AuditLog.action == action)
        if start_date:
            filters.append(AuditLog.timestamp >= start_date)
        if end_date:
            filters.append(AuditLog.timestamp <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Apply pagination
        query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [self._log_to_dict(log) for log in logs],
        }
    
    def _log_to_dict(self, log: AuditLog) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        return {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "event_type": log.event_type,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "user_email": log.user_email,
            "user_role": log.user_role,
            "ip_address": log.ip_address,
            "action": log.action,
            "description": log.description,
            "metadata": log.metadata,
        }
