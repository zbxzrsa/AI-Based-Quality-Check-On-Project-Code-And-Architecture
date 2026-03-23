"""
Performance Monitoring API Endpoints

Provides real-time performance metrics and optimization insights:
- System performance metrics
- Database performance statistics
- Cache performance data
- API response time analytics
- Performance recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any, Optional, Annotated
import psutil
import time
from datetime import datetime

from app.database.postgresql import get_db
from app.database.optimizations import DatabaseOptimizer
from app.shared.cache_manager import CacheManager
from app.core.performance_optimizer import performance_optimizer

router = APIRouter(prefix="/performance", tags=["performance"])

@router.get("/metrics")
async def get_performance_metrics(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict[str, Any]:
    """Get comprehensive performance metrics"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database metrics
        db_optimizer = DatabaseOptimizer()
        
        # Get database connection pool status
        pool_status = await db_optimizer.optimize_connection_pool(pool_size=10)
        
        # Cache metrics
        cache_stats = cache_manager.get_cache_stats()
        cache_memory = await cache_manager.get_memory_usage()
        
        # API performance metrics (from performance optimizer)
        api_metrics = performance_optimizer.get_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": memory.available,
                "memory_total": memory.total,
                "disk_usage": disk.percent,
                "disk_free": disk.free,
                "disk_total": disk.total,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            },
            "database": {
                "connection_pool": pool_status,
                "active_connections": pool_status.get("checked_out_connections", 0),
                "pool_utilization": pool_status.get("pool_utilization", "0%"),
            },
            "cache": {
                "stats": cache_stats,
                "memory_usage": cache_memory,
                "hit_rate": cache_stats.get("hit_rate", 0),
                "total_requests": cache_stats.get("total_requests", 0)
            },
            "api": {
                "total_requests": len(api_metrics),
                "avg_response_time": sum(m.get("duration", 0) for m in api_metrics) / len(api_metrics) if api_metrics else 0,
                "error_rate": len([m for m in api_metrics if m.get("status", 200) >= 400]) / len(api_metrics) if api_metrics else 0,
                "requests_per_minute": len([m for m in api_metrics if m.get("timestamp", 0) > time.time() - 60])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/database/slow-queries")
async def get_slow_queries(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20
) -> Dict[str, Any]:
    """Get slow database queries for optimization"""
    try:
        db_optimizer = DatabaseOptimizer()
        analysis = await db_optimizer.analyze_query_performance(db)
        
        return {
            "slow_queries": analysis.get("slow_queries", [])[:limit],
            "recommendations": analysis.get("recommendations", []),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get slow queries: {str(e)}")

@router.get("/database/indexes")
async def get_index_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict[str, Any]:
    """Get database index recommendations"""
    try:
        db_optimizer = DatabaseOptimizer()
        
        # Apply performance indexes
        index_result = await db_optimizer.apply_performance_indexes(db)
        
        return {
            "index_status": index_result,
            "recommendations": [
                "Consider adding composite indexes for frequently queried column combinations",
                "Monitor index usage and remove unused indexes",
                "Use partial indexes for filtered queries",
                "Consider covering indexes for read-heavy queries"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index recommendations: {str(e)}")

@router.post("/database/maintenance")
async def run_database_maintenance(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict[str, Any]:
    """Run database maintenance tasks"""
    try:
        db_optimizer = DatabaseOptimizer()
        
        # Run maintenance in background
        background_tasks.add_task(db_optimizer.run_maintenance_tasks, db)
        
        return {
            "status": "maintenance_scheduled",
            "message": "Database maintenance tasks have been scheduled",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule maintenance: {str(e)}")

@router.get("/cache/stats")
async def get_cache_statistics() -> Dict[str, Any]:
    """Get detailed cache performance statistics"""
    try:
        stats = cache_manager.get_cache_stats()
        memory_usage = await cache_manager.get_memory_usage()
        
        return {
            "performance": stats,
            "memory": memory_usage,
            "recommendations": _generate_cache_recommendations(stats),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache statistics: {str(e)}")

@router.post("/cache/warm")
async def warm_cache(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Warm cache with frequently accessed data"""
    try:
        from app.shared.cache_manager import warm_project_cache, warm_library_cache, warm_analytics_cache
        
        warm_functions = [warm_project_cache, warm_library_cache, warm_analytics_cache]
        
        # Run cache warming in background
        background_tasks.add_task(cache_manager.warm_cache, warm_functions)
        
        return {
            "status": "cache_warming_scheduled",
            "message": "Cache warming has been scheduled",
            "functions": len(warm_functions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to warm cache: {str(e)}")

@router.delete("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None
) -> Dict[str, Any]:
    """Clear cache entries (optionally by pattern)"""
    try:
        if pattern:
            deleted = await cache_manager.delete_pattern(pattern)
            message = f"Deleted {deleted} cache entries matching pattern: {pattern}"
        else:
            # Clear all cache (use with caution)
            deleted = await cache_manager.delete_pattern("*")
            message = f"Deleted {deleted} cache entries"
        
        return {
            "status": "cache_cleared",
            "message": message,
            "deleted_count": deleted,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/recommendations")
async def get_performance_recommendations(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict[str, Any]:
    """Get AI-powered performance optimization recommendations"""
    try:
        recommendations = []
        
        # System recommendations
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        if cpu_percent > 80:
            recommendations.append({
                "type": "critical",
                "category": "system",
                "title": "High CPU Usage",
                "description": f"CPU usage is {cpu_percent:.1f}%, consider scaling or optimization",
                "impact": "high",
                "effort": "high",
                "action": "Scale horizontally or optimize CPU-intensive operations"
            })
        
        if memory.percent > 85:
            recommendations.append({
                "type": "critical",
                "category": "system",
                "title": "High Memory Usage",
                "description": f"Memory usage is {memory.percent:.1f}%, risk of out-of-memory errors",
                "impact": "high",
                "effort": "medium",
                "action": "Optimize memory usage and implement garbage collection tuning"
            })
        
        # Database recommendations
        db_optimizer = DatabaseOptimizer()
        pool_status = await db_optimizer.optimize_connection_pool(pool_size=10)
        
        utilization = float(pool_status.get("pool_utilization", "0%").replace("%", ""))
        if utilization > 80:
            recommendations.append({
                "type": "warning",
                "category": "database",
                "title": "High Database Connection Pool Usage",
                "description": f"Connection pool utilization is {utilization:.1f}%",
                "impact": "medium",
                "effort": "low",
                "action": "Increase connection pool size or optimize query patterns"
            })
        
        # Cache recommendations
        cache_stats = cache_manager.get_cache_stats()
        if cache_stats.get("hit_rate", 0) < 0.5:
            recommendations.append({
                "type": "warning",
                "category": "cache",
                "title": "Low Cache Hit Rate",
                "description": f"Cache hit rate is {cache_stats.get('hit_rate', 0)*100:.1f}%",
                "impact": "medium",
                "effort": "low",
                "action": "Review cache TTL settings and cache key patterns"
            })
        
        return {
            "recommendations": recommendations,
            "total_count": len(recommendations),
            "critical_count": len([r for r in recommendations if r["type"] == "critical"]),
            "warning_count": len([r for r in recommendations if r["type"] == "warning"]),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.get("/health")
async def performance_health_check() -> Dict[str, Any]:
    """Health check for performance monitoring system"""
    try:
        # Check system health
        cpu_ok = psutil.cpu_percent(interval=1) < 90
        memory_ok = psutil.virtual_memory().percent < 90
        disk_ok = psutil.disk_usage('/').percent < 90
        
        # Check cache health
        cache_ok = cache_manager.redis_client is not None
        
        overall_health = all([cpu_ok, memory_ok, disk_ok, cache_ok])
        
        return {
            "status": "healthy" if overall_health else "degraded",
            "checks": {
                "cpu": "ok" if cpu_ok else "high",
                "memory": "ok" if memory_ok else "high", 
                "disk": "ok" if disk_ok else "high",
                "cache": "ok" if cache_ok else "unavailable"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def _generate_cache_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate cache optimization recommendations"""
    recommendations = []
    
    hit_rate = stats.get("hit_rate", 0)
    if hit_rate < 0.3:
        recommendations.append("Very low cache hit rate - review caching strategy")
    elif hit_rate < 0.5:
        recommendations.append("Low cache hit rate - consider increasing TTL or cache warming")
    
    error_rate = stats.get("errors", 0) / max(stats.get("total_requests", 1), 1)
    if error_rate > 0.05:
        recommendations.append("High cache error rate - check Redis connection and memory")
    
    if not recommendations:
        recommendations.append("Cache performance is optimal")
    
    return recommendations