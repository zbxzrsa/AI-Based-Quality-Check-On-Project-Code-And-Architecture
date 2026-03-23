"""
Celery task for periodic infrastructure metrics collection

Collects and sends infrastructure metrics to CloudWatch every minute.

Validates Requirements: 7.4, 7.10
"""
import logging
from celery import shared_task
from app.core.infrastructure_metrics import get_metrics_collector


logger = logging.getLogger(__name__)


@shared_task(name="collect_infrastructure_metrics")
def collect_infrastructure_metrics_task():
    """
    Periodic task to collect and send infrastructure metrics to CloudWatch.
    
    This task runs every 60 seconds and collects:
    - CPU usage metrics
    - Memory usage metrics
    - Disk usage metrics
    - Network usage metrics
    
    Validates Requirements: 7.4, 7.10
    """
    try:
        collector = get_metrics_collector()
        
        # Collect and send all system metrics
        success = collector.collect_and_send_all_metrics()
        
        if success:
            logger.info("Infrastructure metrics collected and sent to CloudWatch")
        else:
            logger.warning("Failed to send infrastructure metrics to CloudWatch")
        
        return {
            'success': success,
            'message': 'Infrastructure metrics collection completed'
        }
        
    except Exception as e:
        logger.error(
            f"Error collecting infrastructure metrics: {e}",
            extra={
                'error': str(e),
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(name="collect_database_pool_metrics")
def collect_database_pool_metrics_task():
    """
    Periodic task to collect database connection pool metrics.
    
    Validates Requirement: 7.4
    """
    try:
        from app.database.pool_monitor import get_pool_stats
        
        collector = get_metrics_collector()
        
        # Get PostgreSQL pool stats
        pg_stats = get_pool_stats()
        if pg_stats:
            pool_metrics = collector.collect_connection_pool_metrics(
                pool_name='postgresql',
                size=pg_stats.get('pool_size', 0),
                checked_out=pg_stats.get('checked_out', 0),
                overflow=pg_stats.get('overflow', 0),
                checked_in=pg_stats.get('checked_in', 0)
            )
            
            collector.send_metrics_to_cloudwatch(
                pool_metrics,
                dimensions={'PoolType': 'PostgreSQL'}
            )
            
            logger.info("Database pool metrics collected and sent to CloudWatch")
        
        return {
            'success': True,
            'message': 'Database pool metrics collection completed'
        }
        
    except Exception as e:
        logger.error(
            f"Error collecting database pool metrics: {e}",
            extra={
                'error': str(e),
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(name="collect_cache_metrics")
def collect_cache_metrics_task():
    """
    Periodic task to collect cache metrics (hit/miss ratio, eviction rate).
    
    Validates Requirement: 7.4
    """
    try:
        from app.shared.cache_manager import get_cache_stats
        
        collector = get_metrics_collector()
        
        # Get Redis cache stats
        cache_stats = get_cache_stats()
        if cache_stats:
            cache_metrics = collector.collect_cache_metrics(
                cache_name='redis',
                hits=cache_stats.get('hits', 0),
                misses=cache_stats.get('misses', 0),
                evictions=cache_stats.get('evictions', 0),
                size=cache_stats.get('size', 0)
            )
            
            collector.send_metrics_to_cloudwatch(
                cache_metrics,
                dimensions={'CacheType': 'Redis'}
            )
            
            logger.info("Cache metrics collected and sent to CloudWatch")
        
        return {
            'success': True,
            'message': 'Cache metrics collection completed'
        }
        
    except Exception as e:
        logger.error(
            f"Error collecting cache metrics: {e}",
            extra={
                'error': str(e),
                'error_type': type(e).__name__
            },
            exc_info=True
        )
        return {
            'success': False,
            'error': str(e)
        }
