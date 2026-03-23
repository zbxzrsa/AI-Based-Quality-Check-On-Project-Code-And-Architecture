"""
Monitoring endpoints for slow queries and performance metrics
"""
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.database.postgresql import get_db
from app.services.slow_query_monitor import (
    SlowQueryMonitor,
    get_postgres_slow_queries,
    analyze_slow_queries
)
from app.api.dependencies import get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Global slow query monitor
slow_query_monitor = SlowQueryMonitor(slow_threshold_ms=1000.0)


@router.get("/slow-queries")
async def get_slow_queries(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Get slow database queries.
    
    Requires admin or reviewer role.
    
    Args:
        limit: Maximum number of slow queries to return
        
    Returns:
        List of slow queries with details
    """
    # Check permissions
    if current_user.role.value not in ["ADMIN", "REVIEWER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and reviewers can view slow queries"
        )
    
    try:
        async for db in get_db():
            slow_queries = get_postgres_slow_queries(db, limit=limit)
            return {
                "success": True,
                "data": slow_queries,
                "count": len(slow_queries)
            }
    except Exception as e:
        logger.error(f"Failed to retrieve slow queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve slow queries"
        )


@router.get("/slow-queries/stats")
async def get_slow_query_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get slow query statistics and analysis.
    
    Requires admin or reviewer role.
    
    Returns:
        Slow query statistics with recommendations
    """
    if current_user.role.value not in ["ADMIN", "REVIEWER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and reviewers can view query statistics"
        )
    
    try:
        async for db in get_db():
            analysis = analyze_slow_queries(db)
            return {
                "success": True,
                "data": analysis
            }
    except Exception as e:
        logger.error(f"Failed to analyze slow queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze slow queries"
        )


@router.get("/slow-queries/monitor-stats")
async def get_monitor_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics from the slow query monitor.
    
    Requires admin or reviewer role.
    
    Returns:
        Monitor statistics including total slow queries, average time, etc.
    """
    if current_user.role.value not in ["ADMIN", "REVIEWER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and reviewers can view monitor statistics"
        )
    
    try:
        stats = slow_query_monitor.get_slow_query_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get monitor statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitor statistics"
        )


@router.delete("/slow-queries/monitor-stats")
async def clear_monitor_entries(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """
    Clear old slow query monitor entries.
    
    Requires admin role.
    
    Args:
        hours: Number of hours of entries to keep
        
    Returns:
        Success message
    """
    if current_user.role.value != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can clear monitor entries"
        )
    
    try:
        slow_query_monitor.clear_old_entries(hours=hours)
        return {
            "success": True,
            "message": f"Cleared slow query monitor entries older than {hours} hours"
        }
    except Exception as e:
        logger.error(f"Failed to clear monitor entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear monitor entries"
        )


@router.post("/slow-queries/configure-threshold")
async def configure_threshold(
    threshold_ms: float,
    current_user: User = Depends(get_current_user)
):
    """
    Configure the slow query threshold.
    
    Requires admin role.
    
    Args:
        threshold_ms: New threshold in milliseconds
        
    Returns:
        Success message
    """
    if current_user.role.value != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can configure threshold"
        )
    
    if threshold_ms <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be positive"
        )
    
    try:
        global slow_query_monitor
        slow_query_monitor = SlowQueryMonitor(slow_threshold_ms=threshold_ms)
        
        logger.info(f"Slow query threshold updated to {threshold_ms}ms by {current_user.email}")
        
        return {
            "success": True,
            "message": f"Slow query threshold set to {threshold_ms}ms"
        }
    except Exception as e:
        logger.error(f"Failed to configure threshold: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure threshold"
        )
