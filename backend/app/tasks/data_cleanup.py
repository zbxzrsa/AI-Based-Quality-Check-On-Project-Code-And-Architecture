"""
Celery tasks for automated data lifecycle management

This module implements scheduled cleanup tasks for:
- Analysis results (90-day retention)
- Architectural baselines (1-year retention)
- Expired user sessions (30-day retention)

All cleanup operations are logged to the audit log.

Validates Requirements: 11.1, 11.8
"""
from celery import shared_task
import logging

from app.database.postgresql import get_db
from app.services.data_lifecycle_service import DataLifecycleService

logger = logging.getLogger(__name__)


@shared_task(
    name="app.tasks.data_cleanup.cleanup_old_analysis_results",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def cleanup_old_analysis_results(self, dry_run: bool = False):
    """
    Celery task to cleanup old analysis results
    
    This task runs daily at 2 AM UTC (configured in celery_config.py)
    and deletes analysis results older than 90 days.
    
    Validates Requirement: 11.1 (Delete analysis results older than 90 days)
    
    Args:
        dry_run: If True, only count records without deleting
    
    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Starting cleanup_old_analysis_results task (dry_run={dry_run})")
    
    try:
        # Create async session and run cleanup
        import asyncio
        
        async def run_cleanup():
            async for session in get_db():
                try:
                    service = DataLifecycleService(session)
                    result = await service.cleanup_old_analysis_results(dry_run=dry_run)
                    return result
                finally:
                    await session.close()
        
        # Run async cleanup in event loop
        result = asyncio.run(run_cleanup())
        
        logger.info(f"Cleanup task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        # Retry the task
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.data_cleanup.cleanup_old_architectural_baselines",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def cleanup_old_architectural_baselines(self, dry_run: bool = False, keep_current: bool = True):
    """
    Celery task to cleanup old architectural baselines
    
    This task runs weekly and deletes architectural baselines older than 1 year,
    while preserving baselines marked as current.
    
    Args:
        dry_run: If True, only count records without deleting
        keep_current: If True, keep baselines marked as current
    
    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Starting cleanup_old_architectural_baselines task (dry_run={dry_run})")
    
    try:
        import asyncio
        
        async def run_cleanup():
            async for session in get_db():
                try:
                    service = DataLifecycleService(session)
                    result = await service.cleanup_old_architectural_baselines(
                        dry_run=dry_run,
                        keep_current=keep_current
                    )
                    return result
                finally:
                    await session.close()
        
        result = asyncio.run(run_cleanup())
        
        logger.info(f"Cleanup task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.data_cleanup.cleanup_expired_sessions",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def cleanup_expired_sessions(self, dry_run: bool = False):
    """
    Celery task to cleanup expired user sessions
    
    This task runs daily and deletes user sessions older than 30 days.
    
    Args:
        dry_run: If True, only count records without deleting
    
    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Starting cleanup_expired_sessions task (dry_run={dry_run})")
    
    try:
        import asyncio
        
        async def run_cleanup():
            async for session in get_db():
                try:
                    service = DataLifecycleService(session)
                    result = await service.cleanup_expired_sessions(dry_run=dry_run)
                    return result
                finally:
                    await session.close()
        
        result = asyncio.run(run_cleanup())
        
        logger.info(f"Cleanup task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.data_cleanup.verify_audit_log_retention",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def verify_audit_log_retention(self):
    """
    Celery task to verify audit log retention policy
    
    This task runs weekly to verify that audit logs are being retained
    according to the 7-year retention policy.
    
    Validates Requirement: 11.8 (Retain audit logs for 7 years)
    
    Returns:
        Dictionary with verification statistics
    """
    logger.info("Starting verify_audit_log_retention task")
    
    try:
        import asyncio
        
        async def run_verification():
            async for session in get_db():
                try:
                    service = DataLifecycleService(session)
                    result = await service.verify_audit_log_retention()
                    return result
                finally:
                    await session.close()
        
        result = asyncio.run(run_verification())
        
        logger.info(f"Verification task completed: {result}")
        
        # Log warning if issues found
        if result.get("status") == "warning":
            logger.warning(f"Audit log retention issues detected: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Verification task failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.data_cleanup.get_cleanup_statistics",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def get_cleanup_statistics(self):
    """
    Celery task to get data cleanup statistics
    
    This task can be run on-demand to get statistics about data
    eligible for cleanup across all data types.
    
    Returns:
        Dictionary with statistics for each data type
    """
    logger.info("Starting get_cleanup_statistics task")
    
    try:
        import asyncio
        
        async def run_stats():
            async for session in get_db():
                try:
                    service = DataLifecycleService(session)
                    result = await service.get_cleanup_statistics()
                    return result
                finally:
                    await session.close()
        
        result = asyncio.run(run_stats())
        
        logger.info(f"Statistics task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Statistics task failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name="app.tasks.data_cleanup.process_scheduled_account_deletions",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def process_scheduled_account_deletions(self, dry_run: bool = False):
    """
    Celery task to process scheduled account deletions
    
    This task runs daily and processes account deletion requests that have
    reached their scheduled completion date (30 days after request).
    
    Validates Requirement: 11.7 (Delete all personal data within 30 days)
    Validates Requirement: 15.10 (GDPR compliance - right to be forgotten)
    
    Args:
        dry_run: If True, only count records without deleting
    
    Returns:
        Dictionary with deletion statistics
    """
    logger.info(f"Starting process_scheduled_account_deletions task (dry_run={dry_run})")
    
    try:
        import asyncio
        from sqlalchemy import text
        from datetime import datetime, timezone
        
        async def run_deletions():
            async for session in get_db():
                try:
                    now = datetime.now(timezone.utc)
                    
                    # Find deletion requests ready to be processed
                    find_query = text("""
                        SELECT user_id, requested_at, scheduled_completion_date, reason
                        FROM user_deletion_requests
                        WHERE status = 'pending'
                        AND scheduled_completion_date <= :now
                    """)
                    
                    result = await session.execute(find_query, {"now": now})
                    pending_deletions = result.fetchall()
                    
                    if not pending_deletions:
                        logger.info("No account deletions ready to process")
                        return {
                            "status": "success",
                            "processed_count": 0,
                            "dry_run": dry_run
                        }
                    
                    if dry_run:
                        logger.info(f"DRY RUN: Would process {len(pending_deletions)} account deletions")
                        return {
                            "status": "dry_run",
                            "would_process_count": len(pending_deletions),
                            "dry_run": True
                        }
                    
                    processed_count = 0
                    failed_count = 0
                    
                    for deletion in pending_deletions:
                        user_id = deletion.user_id
                        
                        try:
                            logger.info(f"Processing account deletion for user {user_id}")
                            
                            # Delete user's projects (cascade will handle related data)
                            delete_projects = text("""
                                DELETE FROM projects WHERE owner_id = :user_id
                            """)
                            await session.execute(delete_projects, {"user_id": user_id})
                            
                            # Delete user's pull requests
                            delete_prs = text("""
                                DELETE FROM pull_requests WHERE author_id = :user_id
                            """)
                            await session.execute(delete_prs, {"user_id": user_id})
                            
                            # Delete user's sessions
                            delete_sessions = text("""
                                DELETE FROM sessions WHERE user_id = :user_id
                            """)
                            await session.execute(delete_sessions, {"user_id": user_id})
                            
                            # Delete user's tokens
                            delete_tokens = text("""
                                DELETE FROM token_blacklist WHERE user_id = :user_id
                            """)
                            await session.execute(delete_tokens, {"user_id": user_id})
                            
                            # Delete user's project access records
                            delete_access = text("""
                                DELETE FROM project_accesses WHERE user_id = :user_id
                            """)
                            await session.execute(delete_access, {"user_id": user_id})
                            
                            # Finally, delete the user record
                            delete_user = text("""
                                DELETE FROM users WHERE id = :user_id
                            """)
                            await session.execute(delete_user, {"user_id": user_id})
                            
                            # Mark deletion as completed
                            update_deletion = text("""
                                UPDATE user_deletion_requests
                                SET status = 'completed',
                                    completed_at = :completed_at
                                WHERE user_id = :user_id
                            """)
                            await session.execute(
                                update_deletion,
                                {"user_id": user_id, "completed_at": now}
                            )
                            
                            await session.commit()
                            
                            processed_count += 1
                            logger.info(f"Successfully deleted account for user {user_id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to delete account for user {user_id}: {str(e)}")
                            await session.rollback()
                            failed_count += 1
                            
                            # Mark deletion as failed
                            try:
                                update_failed = text("""
                                    UPDATE user_deletion_requests
                                    SET status = 'failed'
                                    WHERE user_id = :user_id
                                """)
                                await session.execute(update_failed, {"user_id": user_id})
                                await session.commit()
                            except Exception as update_error:
                                logger.error(f"Failed to update deletion status: {str(update_error)}")
                    
                    return {
                        "status": "success",
                        "processed_count": processed_count,
                        "failed_count": failed_count,
                        "total_pending": len(pending_deletions),
                        "dry_run": False
                    }
                    
                finally:
                    await session.close()
        
        result = asyncio.run(run_deletions())
        
        logger.info(f"Account deletion task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Account deletion task failed: {str(e)}")
        raise self.retry(exc=e)
