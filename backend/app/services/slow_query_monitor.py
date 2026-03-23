"""
Slow query monitoring service for PostgreSQL
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SlowQueryMonitor:
    """
    Monitor and log slow database queries
    """
    
    def __init__(self, slow_threshold_ms: float = 1000.0):
        """
        Initialize slow query monitor.
        
        Args:
            slow_threshold_ms: Threshold in milliseconds to consider a query as slow
        """
        self.slow_threshold_ms = slow_threshold_ms
        self.slow_queries: list[Dict[str, Any]] = []
        self.max_log_entries = 100
    
    def is_slow_query(self, query_time_ms: float) -> bool:
        """
        Check if query execution time exceeds threshold.
        
        Args:
            query_time_ms: Query execution time in milliseconds
            
        Returns:
            True if query is considered slow
        """
        return query_time_ms > self.slow_threshold_ms
    
    def log_slow_query(
        self,
        query: str,
        query_time_ms: float,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log a slow query with details.
        
        Args:
            query: SQL query that was slow
            query_time_ms: Query execution time in milliseconds
            params: Query parameters (sanitized)
            context: Additional context (endpoint, user_id, etc.)
        """
        slow_query_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_time_ms": query_time_ms,
            "query": self._sanitize_query(query),
            "params": self._sanitize_params(params) if params else None,
            "context": context or {}
        }
        
        self.slow_queries.append(slow_query_entry)
        
        # Keep only recent entries
        if len(self.slow_queries) > self.max_log_entries:
            self.slow_queries.pop(0)
        
        # Log the slow query
        logger.warning(
            "Slow query detected",
            extra={
                "query_time_ms": query_time_ms,
                "threshold_ms": self.slow_threshold_ms,
                "query": slow_query_entry["query"],
                "context": context
            }
        )
    
    def _sanitize_query(self, query: str) -> str:
        """
        Sanitize query to remove sensitive data and limit length.
        
        Args:
            query: Original SQL query
            
        Returns:
            Sanitized query string
        """
        # Remove excessive whitespace
        query = ' '.join(query.split())
        
        # Limit query length
        max_length = 500
        if len(query) > max_length:
            query = query[:max_length] + "..."
        
        return query
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters to remove sensitive data.
        
        Args:
            params: Original parameters
            
        Returns:
            Sanitized parameters
        """
        sanitized = {}
        sensitive_keys = ['password', 'token', 'secret', 'key', 'credit_card']
        
        for key, value in params.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = str(value)[:100]  # Limit value length
        
        return sanitized
    
    def get_slow_query_stats(self) -> Dict[str, Any]:
        """
        Get statistics about slow queries.
        
        Returns:
            Dictionary with slow query statistics
        """
        if not self.slow_queries:
            return {
                "total_slow_queries": 0,
                "avg_query_time_ms": 0,
                "max_query_time_ms": 0,
                "min_query_time_ms": 0
            }
        
        query_times = [q["query_time_ms"] for q in self.slow_queries]
        
        return {
            "total_slow_queries": len(self.slow_queries),
            "avg_query_time_ms": sum(query_times) / len(query_times),
            "max_query_time_ms": max(query_times),
            "min_query_time_ms": min(query_times),
            "recent_slow_queries": self.slow_queries[-10:]  # Last 10 slow queries
        }
    
    def clear_old_entries(self, hours: int = 24):
        """
        Clear slow query entries older than specified hours.
        
        Args:
            hours: Number of hours to keep entries
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        self.slow_queries = [
            q for q in self.slow_queries
            if datetime.fromisoformat(q["timestamp"]) > cutoff_time
        ]
        
        logger.info(f"Cleared slow query entries older than {hours} hours")


# Global slow query monitor instance
slow_query_monitor = SlowQueryMonitor(slow_threshold_ms=1000.0)


def setup_postgres_slow_query_logging(db: AsyncSession):
    """
    Configure PostgreSQL to log slow queries.
    
    Args:
        db: Database session
    """
    try:
        # Enable slow query logging
        # Set threshold to 1 second
        db.execute(text("SET log_min_duration_statement = 1000"))
        
        # Log query duration
        db.execute(text("SET log_duration = on"))
        
        # Log query plans for slow queries
        db.execute(text("SET log_statement = 'mod'"))
        
        logger.info("PostgreSQL slow query logging configured successfully")
        
    except Exception as e:
        logger.error(f"Failed to configure PostgreSQL slow query logging: {e}")


def get_postgres_slow_queries(db: AsyncSession, limit: int = 50) -> list[Dict[str, Any]]:
    """
    Retrieve slow queries from PostgreSQL statistics.
    
    Args:
        db: Database session
        limit: Maximum number of queries to return
        
    Returns:
        List of slow query information
    """
    try:
        # Query pg_stat_statements for slow queries
        result = db.execute(text("""
            SELECT
                query,
                calls,
                total_exec_time / 1000 as total_exec_time_ms,
                mean_exec_time / 1000 as mean_exec_time_ms,
                max_exec_time / 1000 as max_exec_time_ms,
                rows
            FROM pg_stat_statements
            WHERE mean_exec_time > 1000
            ORDER BY total_exec_time DESC
            LIMIT :limit
        """), {"limit": limit})
        
        slow_queries = []
        for row in result:
            slow_queries.append({
                "query": row.query,
                "calls": row.calls,
                "total_exec_time_ms": row.total_exec_time_ms,
                "mean_exec_time_ms": row.mean_exec_time_ms,
                "max_exec_time_ms": row.max_exec_time_ms,
                "rows": row.rows
            })
        
        return slow_queries
        
    except Exception as e:
        logger.error(f"Failed to retrieve slow queries from PostgreSQL: {e}")
        return []


def analyze_slow_queries(db: AsyncSession) -> Dict[str, Any]:
    """
    Analyze slow queries and provide recommendations.
    
    Args:
        db: Database session
        
    Returns:
        Analysis results with recommendations
    """
    slow_queries = get_postgres_slow_queries(db, limit=100)
    
    if not slow_queries:
        return {
            "status": "no_slow_queries",
            "message": "No slow queries detected",
            "recommendations": []
        }
    
    # Analyze patterns
    analysis = {
        "status": "slow_queries_found",
        "total_slow_queries": len(slow_queries),
        "slowest_query": slow_queries[0] if slow_queries else None,
        "top_5_slowest": slow_queries[:5],
        "recommendations": []
    }
    
    # Generate recommendations
    for query in slow_queries[:10]:
        # Check for missing indexes
        if "SELECT" in query["query"] and "WHERE" in query["query"]:
            if query["mean_exec_time_ms"] > 2000:
                analysis["recommendations"].append({
                    "type": "missing_index",
                    "query": query["query"][:100] + "...",
                    "message": "Consider adding index on WHERE clause columns",
                    "severity": "high"
                })
        
        # Check for full table scans
        if query["rows"] > 10000 and query["mean_exec_time_ms"] > 1000:
            analysis["recommendations"].append({
                "type": "full_table_scan",
                "query": query["query"][:100] + "...",
                "message": "Possible full table scan detected",
                "severity": "medium"
            })
    
    return analysis
