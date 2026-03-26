"""
Data Lifecycle Management Service

This service implements data retention policies and cleanup operations for:
- Analysis results (90-day retention)
- Audit logs (7-year retention for compliance)

Validates Requirements: 11.1, 11.8
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid

from app.services.audit_logging_service import AuditLoggingService

logger = logging.getLogger(__name__)


class DataRetentionPolicy:
    """Data retention policy configuration"""
    
    # Analysis results retention: 90 days
    ANALYSIS_RESULTS_RETENTION_DAYS = 90
    
    # Audit logs retention: 7 years (2555 days)
    AUDIT_LOGS_RETENTION_DAYS = 2555
    
    # Architectural baselines retention: 1 year
    ARCHITECTURAL_BASELINES_RETENTION_DAYS = 365
    
    # User sessions retention: 30 days
    USER_SESSIONS_RETENTION_DAYS = 30


class DataLifecycleService:
    """
    Service for managing data lifecycle and retention policies
    
    This service provides:
    - Automated cleanup of expired analysis results
    - Enforcement of audit log retention policies
    - Cleanup of old architectural baselines
    - Cleanup of expired user sessions
    - Audit logging of all deletion operations
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize data lifecycle service
        
        Args:
            db_session: Database session
        """
        self.db = db_session
        self.audit_service = AuditLoggingService(db_session)

    async def _table_exists(self, table_name: str) -> bool:
        """Check whether a database table exists in the current schema."""
        table_check = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """)
        result = await self.db.execute(table_check, {"table_name": table_name})
        return bool(result.scalar())

    @staticmethod
    def _cleanup_result(
        *,
        status: str,
        deleted_count: int = 0,
        cutoff_date: Optional[datetime] = None,
        retention_days: Optional[int] = None,
        dry_run: bool = False,
        would_delete_count: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a consistent cleanup response payload."""
        result: Dict[str, Any] = {
            "status": status,
            "deleted_count": deleted_count,
            "dry_run": dry_run,
        }
        if cutoff_date is not None:
            result["cutoff_date"] = cutoff_date.isoformat()
        if retention_days is not None:
            result["retention_days"] = retention_days
        if would_delete_count is not None:
            result["would_delete_count"] = would_delete_count
        if reason is not None:
            result["reason"] = reason
        return result

    async def _get_table_stats(
        self,
        *,
        table_name: str,
        timestamp_column: str,
        retention_days: int,
        expired_condition: Optional[str] = None,
        empty_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return basic retention statistics for a table, or a skipped payload if absent."""
        if not await self._table_exists(table_name):
            stats: Dict[str, Any] = {
                "status": "skipped",
                "reason": f"{table_name}_table_not_found",
                "retention_days": retention_days,
            }
            if empty_note:
                stats["note"] = empty_note
            return stats

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        expired_sql = expired_condition or f"{timestamp_column} < :cutoff"
        query = text(f"""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE {expired_sql}) as expired,
                MIN({timestamp_column}) as oldest,
                MAX({timestamp_column}) as newest
            FROM {table_name}
        """)
        result = await self.db.execute(query, {"cutoff": cutoff})
        row = result.fetchone()

        stats = {
            "status": "success",
            "total": row.total,
            "expired": row.expired,
            "oldest": row.oldest.isoformat() if row.oldest else None,
            "newest": row.newest.isoformat() if row.newest else None,
            "retention_days": retention_days,
        }
        if empty_note:
            stats["note"] = empty_note
        return stats
    
    async def cleanup_old_analysis_results(
        self,
        retention_days: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Delete analysis results older than retention period
        
        Validates Requirement: 11.1 (Delete analysis results older than 90 days)
        
        Args:
            retention_days: Number of days to retain (default: 90)
            dry_run: If True, only count records without deleting
        
        Returns:
            Dictionary with cleanup statistics
        """
        retention_days = retention_days or DataRetentionPolicy.ANALYSIS_RESULTS_RETENTION_DAYS
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        logger.info(f"Starting analysis results cleanup (retention: {retention_days} days, cutoff: {cutoff_date})")
        
        try:
            if not await self._table_exists("analysis_results"):
                logger.info("Analysis results table does not exist, skipping cleanup")
                return self._cleanup_result(
                    status="skipped",
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=dry_run,
                    reason="analysis_results_table_not_found",
                )

            # Count records to be deleted
            count_query = text("""
                SELECT COUNT(*) 
                FROM analysis_results 
                WHERE created_at < :cutoff_date
            """)
            count_result = await self.db.execute(count_query, {"cutoff_date": cutoff_date})
            total_count = count_result.scalar()
            
            if total_count == 0:
                logger.info("No analysis results to cleanup")
                return self._cleanup_result(
                    status="success",
                    deleted_count=0,
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=dry_run,
                )
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {total_count} analysis results")
                return self._cleanup_result(
                    status="dry_run",
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=True,
                    would_delete_count=total_count,
                )
            
            # Get sample of records being deleted for audit log
            sample_query = text("""
                SELECT id, project_id, analysis_type, created_at
                FROM analysis_results 
                WHERE created_at < :cutoff_date
                LIMIT 10
            """)
            sample_result = await self.db.execute(sample_query, {"cutoff_date": cutoff_date})
            sample_records = sample_result.fetchall()
            
            # Delete old analysis results
            delete_query = text("""
                DELETE FROM analysis_results 
                WHERE created_at < :cutoff_date
            """)
            delete_result = await self.db.execute(delete_query, {"cutoff_date": cutoff_date})
            deleted_count = delete_result.rowcount
            
            await self.db.commit()
            
            # Log deletion to audit log
            await self._log_cleanup_operation(
                operation="cleanup_analysis_results",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
                retention_days=retention_days,
                sample_records=[
                    {
                        "id": str(record.id),
                        "project_id": str(record.project_id),
                        "analysis_type": record.analysis_type,
                        "created_at": record.created_at.isoformat()
                    }
                    for record in sample_records
                ]
            )
            
            logger.info(f"Successfully deleted {deleted_count} analysis results older than {retention_days} days")
            
            return self._cleanup_result(
                status="success",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
                retention_days=retention_days,
                dry_run=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to cleanup analysis results: {str(e)}")
            await self.db.rollback()
            raise
    
    async def cleanup_old_architectural_baselines(
        self,
        retention_days: Optional[int] = None,
        dry_run: bool = False,
        keep_current: bool = True
    ) -> Dict[str, Any]:
        """
        Delete old architectural baselines older than retention period
        
        Args:
            retention_days: Number of days to retain (default: 365)
            dry_run: If True, only count records without deleting
            keep_current: If True, keep baselines marked as current
        
        Returns:
            Dictionary with cleanup statistics
        """
        retention_days = retention_days or DataRetentionPolicy.ARCHITECTURAL_BASELINES_RETENTION_DAYS
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        logger.info(f"Starting architectural baselines cleanup (retention: {retention_days} days)")
        
        try:
            if not await self._table_exists("architectural_baselines"):
                logger.info("Architectural baselines table does not exist, skipping cleanup")
                return self._cleanup_result(
                    status="skipped",
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=dry_run,
                    reason="architectural_baselines_table_not_found",
                )

            # Build query with optional current baseline exclusion
            if keep_current:
                count_query = text("""
                    SELECT COUNT(*) 
                    FROM architectural_baselines 
                    WHERE created_at < :cutoff_date AND is_current = false
                """)
            else:
                count_query = text("""
                    SELECT COUNT(*) 
                    FROM architectural_baselines 
                    WHERE created_at < :cutoff_date
                """)
            
            count_result = await self.db.execute(count_query, {"cutoff_date": cutoff_date})
            total_count = count_result.scalar()
            
            if total_count == 0:
                logger.info("No architectural baselines to cleanup")
                return self._cleanup_result(
                    status="success",
                    deleted_count=0,
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=dry_run,
                )
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {total_count} architectural baselines")
                return self._cleanup_result(
                    status="dry_run",
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=True,
                    would_delete_count=total_count,
                )
            
            # Delete old baselines
            if keep_current:
                delete_query = text("""
                    DELETE FROM architectural_baselines 
                    WHERE created_at < :cutoff_date AND is_current = false
                """)
            else:
                delete_query = text("""
                    DELETE FROM architectural_baselines 
                    WHERE created_at < :cutoff_date
                """)
            
            delete_result = await self.db.execute(delete_query, {"cutoff_date": cutoff_date})
            deleted_count = delete_result.rowcount
            
            await self.db.commit()
            
            # Log deletion to audit log
            await self._log_cleanup_operation(
                operation="cleanup_architectural_baselines",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
                retention_days=retention_days
            )
            
            logger.info(f"Successfully deleted {deleted_count} architectural baselines")
            
            return self._cleanup_result(
                status="success",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
                retention_days=retention_days,
                dry_run=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to cleanup architectural baselines: {str(e)}")
            await self.db.rollback()
            raise
    
    async def cleanup_expired_sessions(
        self,
        retention_days: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Delete expired user sessions older than retention period
        
        Args:
            retention_days: Number of days to retain (default: 30)
            dry_run: If True, only count records without deleting
        
        Returns:
            Dictionary with cleanup statistics
        """
        retention_days = retention_days or DataRetentionPolicy.USER_SESSIONS_RETENTION_DAYS
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        logger.info(f"Starting expired sessions cleanup (retention: {retention_days} days)")
        
        try:
            if not await self._table_exists("sessions"):
                logger.info("Sessions table does not exist, skipping cleanup")
                return self._cleanup_result(
                    status="skipped",
                    deleted_count=0,
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=dry_run,
                    reason="sessions_table_not_found",
                )
            
            # Count expired sessions
            count_query = text("""
                SELECT COUNT(*) 
                FROM sessions 
                WHERE created_at < :cutoff_date
            """)
            count_result = await self.db.execute(count_query, {"cutoff_date": cutoff_date})
            total_count = count_result.scalar()
            
            if total_count == 0:
                logger.info("No expired sessions to cleanup")
                return self._cleanup_result(
                    status="success",
                    deleted_count=0,
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=dry_run,
                )
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {total_count} expired sessions")
                return self._cleanup_result(
                    status="dry_run",
                    cutoff_date=cutoff_date,
                    retention_days=retention_days,
                    dry_run=True,
                    would_delete_count=total_count,
                )
            
            # Delete expired sessions
            delete_query = text("""
                DELETE FROM sessions 
                WHERE created_at < :cutoff_date
            """)
            delete_result = await self.db.execute(delete_query, {"cutoff_date": cutoff_date})
            deleted_count = delete_result.rowcount
            
            await self.db.commit()
            
            # Log deletion to audit log
            await self._log_cleanup_operation(
                operation="cleanup_expired_sessions",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
                retention_days=retention_days
            )
            
            logger.info(f"Successfully deleted {deleted_count} expired sessions")
            
            return self._cleanup_result(
                status="success",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
                retention_days=retention_days,
                dry_run=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            await self.db.rollback()
            raise
    
    async def verify_audit_log_retention(self) -> Dict[str, Any]:
        """
        Verify audit logs are being retained according to policy
        
        Validates Requirement: 11.8 (Retain audit logs for 7 years)
        
        Note: Audit logs should NOT be deleted automatically. This method
        only verifies the retention_until dates are set correctly.
        
        Returns:
            Dictionary with verification statistics
        """
        logger.info("Verifying audit log retention policy")
        
        try:
            # Check oldest audit log
            oldest_query = text("""
                SELECT MIN(timestamp) as oldest_timestamp,
                       MIN(retention_until) as oldest_retention
                FROM audit_log_entries
            """)
            oldest_result = await self.db.execute(oldest_query)
            oldest_row = oldest_result.fetchone()
            
            # Check if any logs have incorrect retention dates
            incorrect_retention_query = text("""
                SELECT COUNT(*) 
                FROM audit_log_entries
                WHERE retention_until < timestamp + INTERVAL '7 years'
            """)
            incorrect_result = await self.db.execute(incorrect_retention_query)
            incorrect_count = incorrect_result.scalar()
            
            # Get total audit log count
            total_query = text("SELECT COUNT(*) FROM audit_log_entries")
            total_result = await self.db.execute(total_query)
            total_count = total_result.scalar()
            
            verification_result = {
                "status": "verified",
                "total_audit_logs": total_count,
                "oldest_log_timestamp": oldest_row.oldest_timestamp.isoformat() if oldest_row.oldest_timestamp else None,
                "oldest_retention_date": oldest_row.oldest_retention.isoformat() if oldest_row.oldest_retention else None,
                "logs_with_incorrect_retention": incorrect_count,
                "retention_policy_days": DataRetentionPolicy.AUDIT_LOGS_RETENTION_DAYS,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
            
            if incorrect_count > 0:
                logger.warning(f"Found {incorrect_count} audit logs with incorrect retention dates")
                verification_result["status"] = "warning"
            
            logger.info(f"Audit log retention verification complete: {total_count} logs, oldest from {oldest_row.oldest_timestamp}")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Failed to verify audit log retention: {str(e)}")
            raise
    
    async def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about data eligible for cleanup
        
        Returns:
            Dictionary with statistics for each data type
        """
        try:
            stats = {}

            stats["analysis_results"] = await self._get_table_stats(
                table_name="analysis_results",
                timestamp_column="created_at",
                retention_days=DataRetentionPolicy.ANALYSIS_RESULTS_RETENTION_DAYS,
            )

            stats["architectural_baselines"] = await self._get_table_stats(
                table_name="architectural_baselines",
                timestamp_column="created_at",
                retention_days=DataRetentionPolicy.ARCHITECTURAL_BASELINES_RETENTION_DAYS,
                expired_condition="created_at < :cutoff AND is_current = false",
            )

            stats["expired_sessions"] = await self._get_table_stats(
                table_name="sessions",
                timestamp_column="created_at",
                retention_days=DataRetentionPolicy.USER_SESSIONS_RETENTION_DAYS,
            )

            if await self._table_exists("audit_log_entries"):
                audit_query = text("""
                    SELECT
                        COUNT(*) as total,
                        MIN(timestamp) as oldest,
                        MAX(timestamp) as newest
                    FROM audit_log_entries
                """)
                audit_result = await self.db.execute(audit_query)
                audit_row = audit_result.fetchone()

                stats["audit_logs"] = {
                    "status": "success",
                    "total": audit_row.total,
                    "oldest": audit_row.oldest.isoformat() if audit_row.oldest else None,
                    "newest": audit_row.newest.isoformat() if audit_row.newest else None,
                    "retention_days": DataRetentionPolicy.AUDIT_LOGS_RETENTION_DAYS,
                    "note": "Audit logs are never automatically deleted"
                }
            else:
                stats["audit_logs"] = {
                    "status": "skipped",
                    "reason": "audit_log_entries_table_not_found",
                    "retention_days": DataRetentionPolicy.AUDIT_LOGS_RETENTION_DAYS,
                    "note": "Audit logs are never automatically deleted"
                }
            
            stats["generated_at"] = datetime.now(timezone.utc).isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cleanup statistics: {str(e)}")
            raise
    
    async def _log_cleanup_operation(
        self,
        operation: str,
        deleted_count: int,
        cutoff_date: datetime,
        retention_days: int,
        sample_records: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Log cleanup operation to audit log
        
        Args:
            operation: Type of cleanup operation
            deleted_count: Number of records deleted
            cutoff_date: Cutoff date used for deletion
            retention_days: Retention period in days
            sample_records: Sample of deleted records for audit trail
        """
        try:
            await self.audit_service.log_administrative_action(
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # System user
                user_email="system@data-lifecycle",
                user_role="system",
                action=operation,
                description=f"Automated data cleanup: deleted {deleted_count} records older than {retention_days} days (cutoff: {cutoff_date.isoformat()})",
                resource_type="data_lifecycle",
                resource_id=operation,
                ip_address="127.0.0.1",
                user_agent="DataLifecycleService/1.0",
                success=True,
                metadata={
                    "operation": operation,
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "retention_days": retention_days,
                    "sample_records": sample_records or []
                }
            )
        except Exception as e:
            logger.error(f"Failed to log cleanup operation to audit log: {str(e)}")
            # Don't raise - cleanup succeeded even if audit logging failed
