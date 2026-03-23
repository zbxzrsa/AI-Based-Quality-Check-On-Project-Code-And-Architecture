"""
Backend Performance Optimizer

Implements advanced performance optimizations including:
- Database query optimization
- Caching strategies
- Async task processing
- Connection pooling
- Response compression
"""

import asyncio
import json
import time
from functools import wraps
from typing import Any, Dict, List, Callable, Union
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Request
import gzip
import logging

from app.database.postgresql import get_db
from app.database.redis_db import get_redis

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Advanced performance optimization utilities"""
    
    def __init__(self):
        self.redis_client = None
        self.metrics = {}
        self.query_cache = {}
    
    async def initialize(self):
        """Initialize performance optimizer"""
        try:
            self.redis_client = await get_redis()
            logger.info("Performance optimizer initialized")
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")

# Global instance
performance_optimizer = PerformanceOptimizer()

def cache_result(
    expiration: int = 300,
    key_prefix: str = "",
    vary_on: List[str] = None
):
    """
    Decorator for caching function results in Redis
    
    Args:
        expiration: Cache expiration time in seconds
        key_prefix: Prefix for cache keys
        vary_on: List of parameter names to include in cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not performance_optimizer.redis_client:
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key_parts = [key_prefix or func.__name__]
            
            if vary_on:
                for param in vary_on:
                    if param in kwargs:
                        cache_key_parts.append(f"{param}:{kwargs[param]}")
            else:
                # Include all args and kwargs in cache key
                cache_key_parts.append(str(hash(str(args) + str(sorted(kwargs.items())))))
            
            cache_key = ":".join(cache_key_parts)
            
            # Try to get from cache
            try:
                cached_result = await performance_optimizer.redis_client.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for {cache_key}")
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # Execute function
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the result
            try:
                serialized_result = json.dumps(result, default=str)
                await performance_optimizer.redis_client.setex(
                    cache_key, expiration, serialized_result
                )
                logger.debug(f"Cached result for {cache_key} (execution: {execution_time:.3f}s)")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator

def optimize_query(func: Callable) -> Callable:
    """
    Decorator for optimizing database queries
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow queries
            if execution_time > 1.0:  # Log queries taking more than 1 second
                logger.warning(f"Slow query detected: {func.__name__} took {execution_time:.3f}s")
            
            # Store query metrics
            if func.__name__ not in performance_optimizer.metrics:
                performance_optimizer.metrics[func.__name__] = []
            
            performance_optimizer.metrics[func.__name__].append({
                'execution_time': execution_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Keep only last 100 metrics per function
            if len(performance_optimizer.metrics[func.__name__]) > 100:
                performance_optimizer.metrics[func.__name__] = \
                    performance_optimizer.metrics[func.__name__][-100:]
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query error in {func.__name__} after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper

class DatabaseOptimizer:
    """Database-specific optimizations"""
    
    @staticmethod
    @optimize_query
    async def get_projects_with_relations(
        db: AsyncSession, 
        user_id: int, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Optimized query to get projects with all relations in a single query
        Prevents N+1 query problems
        """
        from app.models import Project
        
        # Use selectinload to eagerly load relations
        query = (
            db.query(Project)
            .options(
                selectinload(Project.reviews),
                selectinload(Project.libraries),
                selectinload(Project.team_members)
            )
            .filter(Project.owner_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return [
            {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'reviews_count': len(project.reviews),
                'libraries_count': len(project.libraries),
                'team_members_count': len(project.team_members)
            }
            for project in projects
        ]
    
    @staticmethod
    @optimize_query
    async def get_project_statistics(db: AsyncSession, project_id: int) -> Dict:
        """
        Get project statistics using optimized aggregation queries
        """
        # Use raw SQL for complex aggregations
        stats_query = text("""
            SELECT 
                COUNT(DISTINCT r.id) as review_count,
                COUNT(DISTINCT l.id) as library_count,
                COUNT(DISTINCT tm.id) as team_member_count,
                AVG(r.score) as avg_review_score,
                MAX(r.created_at) as last_review_date
            FROM projects p
            LEFT JOIN reviews r ON p.id = r.project_id
            LEFT JOIN libraries l ON p.id = l.project_id
            LEFT JOIN team_members tm ON p.id = tm.project_id
            WHERE p.id = :project_id
            GROUP BY p.id
        """)
        
        result = await db.execute(stats_query, {"project_id": project_id})
        row = result.fetchone()
        
        if not row:
            return {}
        
        return {
            'review_count': row.review_count or 0,
            'library_count': row.library_count or 0,
            'team_member_count': row.team_member_count or 0,
            'avg_review_score': float(row.avg_review_score) if row.avg_review_score else 0.0,
            'last_review_date': row.last_review_date.isoformat() if row.last_review_date else None
        }

class CacheManager:
    """Advanced caching strategies"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_patterns = {
            'user_projects': 'user:{user_id}:projects',
            'project_stats': 'project:{project_id}:stats',
            'library_metadata': 'library:{library_uri}:metadata',
            'search_results': 'search:{query_hash}:results'
        }
    
    async def get_or_set(
        self, 
        pattern: str, 
        key_vars: Dict[str, Any], 
        fetch_func: Callable,
        ttl: int = 300
    ) -> Any:
        """
        Get from cache or set if not exists
        """
        cache_key = self.cache_patterns[pattern].format(**key_vars)
        
        try:
            # Try to get from cache
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache read error for {cache_key}: {e}")
        
        # Fetch data
        data = await fetch_func()
        
        try:
            # Cache the data
            await self.redis.setex(cache_key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Cache write error for {cache_key}: {e}")
        
        return data
    
    async def invalidate_pattern(self, pattern: str, key_vars: Dict[str, Any]):
        """
        Invalidate cache entries matching a pattern
        """
        cache_key = self.cache_patterns[pattern].format(**key_vars)
        
        try:
            await self.redis.delete(cache_key)
            logger.debug(f"Invalidated cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache invalidation error for {cache_key}: {e}")
    
    async def warm_cache(self, warm_functions: List[Callable]):
        """
        Warm up cache with frequently accessed data
        """
        logger.info("Starting cache warming...")
        
        tasks = []
        for func in warm_functions:
            task = asyncio.create_task(func())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache warming completed: {success_count}/{len(tasks)} successful")

class ResponseOptimizer:
    """Response optimization utilities"""
    
    @staticmethod
    def compress_response(content: Union[str, bytes], min_size: int = 1024) -> bytes:
        """
        Compress response content using gzip
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        if len(content) < min_size:
            return content
        
        return gzip.compress(content)
    
    @staticmethod
    def should_compress(request: Request) -> bool:
        """
        Check if response should be compressed based on Accept-Encoding header
        """
        accept_encoding = request.headers.get('accept-encoding', '')
        return 'gzip' in accept_encoding.lower()

class AsyncTaskOptimizer:
    """Async task processing optimizations"""
    
    @staticmethod
    async def batch_process(
        items: List[Any], 
        process_func: Callable,
        batch_size: int = 10,
        max_concurrent: int = 5
    ) -> List[Any]:
        """
        Process items in batches with concurrency control
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_batch(batch):
            async with semaphore:
                batch_results = await asyncio.gather(
                    *[process_func(item) for item in batch],
                    return_exceptions=True
                )
                return batch_results
        
        # Split items into batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        # Process batches
        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Flatten results
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results

# Middleware for performance monitoring
async def performance_monitoring_middleware(request: Request, call_next):
    """
    Middleware to monitor request performance
    """
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 2.0:  # Log requests taking more than 2 seconds
        logger.warning(f"Slow request: {request.method} {request.url} took {process_time:.3f}s")
    
    # Store metrics
    if 'request_metrics' not in performance_optimizer.metrics:
        performance_optimizer.metrics['request_metrics'] = []
    
    performance_optimizer.metrics['request_metrics'].append({
        'method': request.method,
        'url': str(request.url),
        'process_time': process_time,
        'status_code': response.status_code,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # Keep only last 1000 request metrics
    if len(performance_optimizer.metrics['request_metrics']) > 1000:
        performance_optimizer.metrics['request_metrics'] = \
            performance_optimizer.metrics['request_metrics'][-1000:]
    
    return response

# Utility functions for common optimizations
@cache_result(expiration=600, key_prefix="project_stats")
async def get_cached_project_stats(project_id: int) -> Dict:
    """
    Get project statistics with caching
    """
    async with get_db() as db:
        return await DatabaseOptimizer.get_project_statistics(db, project_id)

@cache_result(expiration=300, key_prefix="user_projects")
async def get_cached_user_projects(user_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    Get user projects with caching
    """
    async with get_db() as db:
        return await DatabaseOptimizer.get_projects_with_relations(db, user_id, limit, offset)

async def get_performance_metrics() -> Dict:
    """
    Get current performance metrics
    """
    return {
        'query_metrics': performance_optimizer.metrics,
        'cache_stats': await get_cache_statistics(),
        'system_info': {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime': time.time() - getattr(performance_optimizer, 'start_time', time.time())
        }
    }

async def get_cache_statistics() -> Dict:
    """
    Get cache statistics from Redis
    """
    if not performance_optimizer.redis_client:
        return {'status': 'unavailable'}
    
    try:
        info = await performance_optimizer.redis_client.info()
        return {
            'status': 'available',
            'used_memory': info.get('used_memory_human', 'unknown'),
            'connected_clients': info.get('connected_clients', 0),
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': (
                info.get('keyspace_hits', 0) / 
                max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
            )
        }
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return {'status': 'error', 'error': str(e)}

# Initialize performance optimizer on startup
async def initialize_performance_optimizer():
    """
    Initialize performance optimizer
    """
    performance_optimizer.start_time = time.time()
    await performance_optimizer.initialize()
    
    # Warm up cache with common queries
    if performance_optimizer.redis_client:
        cache_manager = CacheManager(performance_optimizer.redis_client)
        # Add cache warming functions here
        # await cache_manager.warm_cache([...])
    
    logger.info("Performance optimizer initialized successfully")