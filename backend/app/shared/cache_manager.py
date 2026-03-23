"""
Enhanced Redis cache utilities with connection pooling

Provides high-level caching operations with automatic serialization,
connection pooling, and error handling.

Validates Requirements: 7.3, 10.4, 10.5
"""

import json
import logging
import hashlib
from typing import Optional, Any, Dict, List, Callable
from enum import Enum
import redis.asyncio as redis
from functools import wraps

from .exceptions import CacheException


logger = logging.getLogger(__name__)


class CacheKeyPrefix(str, Enum):
    """Standard cache key prefixes"""
    SESSION = "session"
    LLM_RESPONSE = "llm"
    GRAPH_QUERY = "graph"
    PROJECT_PATTERNS = "patterns"
    USER_DATA = "user"
    RATE_LIMIT = "ratelimit"


# Global cache manager instance
_cache_manager: Optional['CacheManager'] = None


def get_cache_manager() -> 'CacheManager':
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def reset_cache_manager():
    """Reset global cache manager instance"""
    global _cache_manager
    _cache_manager = None




def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return get_cache_manager().get_stats()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """Cache decorator for functions"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            cache_manager = get_cache_manager()
            cached_result = await cache_manager.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
    TEMP = "temp"


class CacheKey:
    """Helper for generating consistent cache keys"""
    
    @staticmethod
    def session(user_id: str) -> str:
        """Generate session cache key"""
        return f"{CacheKeyPrefix.SESSION.value}:{user_id}"
    
    @staticmethod
    def llm_response(provider: str, model: str, prompt: str) -> str:
        """Generate LLM response cache key"""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return f"{CacheKeyPrefix.LLM_RESPONSE.value}:{provider}:{model}:{prompt_hash}"
    
    @staticmethod
    def graph_query(project_id: str, query: str) -> str:
        """Generate graph query cache key"""
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        return f"{CacheKeyPrefix.GRAPH_QUERY.value}:{project_id}:{query_hash}"
    
    @staticmethod
    def project_patterns(project_id: str) -> str:
        """Generate project patterns cache key"""
        return f"{CacheKeyPrefix.PROJECT_PATTERNS.value}:{project_id}"
    
    @staticmethod
    def rate_limit(user_id: str, endpoint: str) -> str:
        """Generate rate limit cache key"""
        return f"{CacheKeyPrefix.RATE_LIMIT.value}:{user_id}:{endpoint}"
    
    @staticmethod
    def custom(prefix: str, *parts: str) -> str:
        """Generate custom cache key"""
        return f"{prefix}:{':'.join(parts)}"


class CacheManager:
    """
    Enhanced Redis cache manager with connection pooling.
    
    Validates Requirements: 7.3, 10.4, 10.5
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = True,
        use_redis: bool = True,
    ):
        """
        Initialize cache manager.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            decode_responses: Whether to decode responses to strings
            use_redis: Whether to use Redis or in-memory cache
        """
        self.use_redis = use_redis
        self._stats = {"hits": 0, "misses": 0, "sets": 0}
        self._memory_cache = {}  # In-memory fallback
        
        if use_redis:
            self.pool = redis.ConnectionPool(
                host=host,
                port=port,
                password=password,
                db=db,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=decode_responses,
            )
            self.client: Optional[redis.Redis] = None
        else:
            self.pool = None
            self.client = None
        
        logger.info(
            "Cache manager initialized",
            extra={
                'host': host,
                'port': port,
                'db': db,
                'max_connections': max_connections,
                'use_redis': use_redis,
            }
        )
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.client = redis.Redis(connection_pool=self.pool)
            await self.client.ping()
            logger.info("Cache manager connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheException(
                f"Failed to connect to Redis: {str(e)}",
                operation="connect",
                error_code="CONNECTION_FAILED"
            )
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            await self.pool.disconnect()
            self.client = None
            logger.info("Cache manager disconnected from Redis")
    
    async def set(
        self,
        key: str,
        value: Any,
        expiration: Optional[int] = 3600,
        serialize: bool = True,
        ttl: Optional[int] = None  # Backward compatibility
    ) -> bool:
        """
        Set cache value.
        
        Args:
            key: Cache key
            value: Value to cache
            expiration: Expiration time in seconds (None for no expiration)
            serialize: Whether to JSON serialize the value
            ttl: Alias for expiration (backward compatibility)
            
        Returns:
            True if successful
            
        Raises:
            CacheException: If operation fails
        """
        # Use ttl if provided (backward compatibility)
        if ttl is not None:
            expiration = ttl
        
        self._stats["sets"] += 1
        
        # In-memory fallback
        if not self.use_redis:
            if serialize:
                value = json.dumps(value)
            self._memory_cache[key] = value
            logger.debug(f"Cache set (memory): {key}")
            return True
        
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="set",
                key=key,
                error_code="NOT_INITIALIZED"
            )
        
        try:
            if serialize:
                value = json.dumps(value)
            
            if expiration:
                await self.client.setex(key, expiration, value)
            else:
                await self.client.set(key, value)
            
            logger.debug(f"Cache set: {key}", extra={'key': key, 'expiration': expiration})
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            raise CacheException(
                f"Failed to set cache: {str(e)}",
                operation="set",
                key=key,
                error_code="SET_FAILED"
            )
    
    async def get(
        self,
        key: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """
        Get cache value.
        
        Args:
            key: Cache key
            deserialize: Whether to JSON deserialize the value
            
        Returns:
            Cached value or None if not found
            
        Raises:
            CacheException: If operation fails
        """
        # In-memory fallback
        if not self.use_redis:
            value = self._memory_cache.get(key)
            if value is None:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss (memory): {key}")
                return None
            
            self._stats["hits"] += 1
            logger.debug(f"Cache hit (memory): {key}")
            
            if deserialize:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return value
        
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="get",
                key=key,
                error_code="NOT_INITIALIZED"
            )
        
        try:
            value = await self.client.get(key)
            
            if value is None:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss: {key}", extra={'key': key})
                return None
            
            self._stats["hits"] += 1
            logger.debug(f"Cache hit: {key}", extra={'key': key})
            
            if deserialize:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return value
            
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            raise CacheException(
                f"Failed to get cache: {str(e)}",
                operation="get",
                key=key,
                error_code="GET_FAILED"
            )
    
    async def delete(self, key: str) -> bool:
        """
        Delete cache value.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
            
        Raises:
            CacheException: If operation fails
        """
        # In-memory fallback
        if not self.use_redis:
            deleted = key in self._memory_cache
            if deleted:
                del self._memory_cache[key]
            logger.debug(f"Cache delete (memory): {key}", extra={'key': key, 'deleted': deleted})
            return deleted
        
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="delete",
                key=key,
                error_code="NOT_INITIALIZED"
            )
        
        try:
            result = await self.client.delete(key)
            logger.debug(f"Cache delete: {key}", extra={'key': key, 'deleted': result > 0})
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            raise CacheException(
                f"Failed to delete cache: {str(e)}",
                operation="delete",
                key=key,
                error_code="DELETE_FAILED"
            )
    
    async def exists(self, key: str) -> bool:
        """
        Check if cache key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
            
        Raises:
            CacheException: If operation fails
        """
        # In-memory fallback
        if not self.use_redis:
            return key in self._memory_cache
        
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="exists",
                key=key,
                error_code="NOT_INITIALIZED"
            )
        
        try:
            result = await self.client.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            raise CacheException(
                f"Failed to check cache existence: {str(e)}",
                operation="exists",
                key=key,
                error_code="EXISTS_FAILED"
            )
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment cache value (for counters).
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment
            
        Raises:
            CacheException: If operation fails
        """
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="increment",
                key=key,
                error_code="NOT_INITIALIZED"
            )
        
        try:
            result = await self.client.incrby(key, amount)
            logger.debug(f"Cache increment: {key} by {amount}", extra={'key': key, 'amount': amount})
            return result
            
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            raise CacheException(
                f"Failed to increment cache: {str(e)}",
                operation="increment",
                key=key,
                error_code="INCREMENT_FAILED"
            )
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on existing key.
        
        Args:
            key: Cache key
            seconds: Expiration time in seconds
            
        Returns:
            True if expiration was set
            
        Raises:
            CacheException: If operation fails
        """
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="expire",
                key=key,
                error_code="NOT_INITIALIZED"
            )
        
        try:
            result = await self.client.expire(key, seconds)
            logger.debug(f"Cache expire: {key} in {seconds}s", extra={'key': key, 'seconds': seconds})
            return result
            
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            raise CacheException(
                f"Failed to set cache expiration: {str(e)}",
                operation="expire",
                key=key,
                error_code="EXPIRE_FAILED"
            )
    
    async def get_many(self, keys: List[str], deserialize: bool = True) -> Dict[str, Any]:
        """
        Get multiple cache values.
        
        Args:
            keys: List of cache keys
            deserialize: Whether to JSON deserialize values
            
        Returns:
            Dictionary of key-value pairs (only existing keys)
            
        Raises:
            CacheException: If operation fails
        """
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="get_many",
                error_code="NOT_INITIALIZED"
            )
        
        try:
            values = await self.client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    if deserialize:
                        try:
                            result[key] = json.loads(value)
                        except json.JSONDecodeError:
                            result[key] = value
                    else:
                        result[key] = value
            
            logger.debug(f"Cache get_many: {len(result)}/{len(keys)} hits")
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many failed: {e}")
            raise CacheException(
                f"Failed to get multiple cache values: {str(e)}",
                operation="get_many",
                error_code="GET_MANY_FAILED"
            )
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "session:*")
            
        Returns:
            Number of keys deleted
            
        Raises:
            CacheException: If operation fails
        """
        if not self.client:
            raise CacheException(
                "Cache client not initialized",
                operation="delete_pattern",
                error_code="NOT_INITIALIZED"
            )
        
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.client.delete(*keys)
                logger.info(f"Cache delete_pattern: deleted {deleted} keys matching {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache delete_pattern failed for pattern {pattern}: {e}")
            raise CacheException(
                f"Failed to delete cache pattern: {str(e)}",
                operation="delete_pattern",
                error_code="DELETE_PATTERN_FAILED"
            )
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if self.use_redis and self.pool:
            return {
                'max_connections': self.pool.max_connections,
                'connection_kwargs': {
                    'host': self.pool.connection_kwargs.get('host'),
                    'port': self.pool.connection_kwargs.get('port'),
                    'db': self.pool.connection_kwargs.get('db'),
                }
            }
        return {'use_redis': False, 'memory_cache_size': len(self._memory_cache)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self._stats.copy()
    
    def reset_stats(self):
        """Reset cache statistics"""
        self._stats = {"hits": 0, "misses": 0, "sets": 0}
    
    async def clear(self):
        """Clear all cache entries"""
        if self.use_redis and self.client:
            await self.client.flushdb()
        else:
            self._memory_cache.clear()
        logger.info("Cache cleared")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern (alias for delete_pattern)"""
        return await self.delete_pattern(pattern)
    
    async def invalidate_on_update(self, entity_type: str, entity_id: str) -> int:
        """Invalidate cache entries related to an entity update"""
        patterns = [
            f"{entity_type}:{entity_id}:*",
            f"*:{entity_type}:{entity_id}:*",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} cache entries for {entity_type}:{entity_id}")
        return total_deleted
    
    async def warm_cache(self, loader_func: Callable, keys: List[tuple], ttl: int = 3600):
        """Warm cache with data from loader function"""
        for key_data in keys:
            cache_key = key_data[0]
            loader_args = key_data[1:] if len(key_data) > 1 else ()
            
            # Skip if already cached
            if await self.exists(cache_key):
                continue
            
            # Load and cache data
            try:
                data = await loader_func(*loader_args)
                await self.set(cache_key, data, ttl)
            except Exception as e:
                logger.error(f"Failed to warm cache for key {cache_key}: {e}")
        
        logger.info(f"Cache warming completed for {len(keys)} keys")
    
    async def get_cached_result(self, project_id: str, analysis_type: str) -> Optional[Any]:
        """Get cached analysis result (backward compatibility)"""
        cache_key = f"analysis:{project_id}:{analysis_type}"
        return await self.get(cache_key)
    
    async def set_cached_result(self, project_id: str, analysis_type: str, result: Any, ttl: int = 3600):
        """Set cached analysis result (backward compatibility)"""
        cache_key = f"analysis:{project_id}:{analysis_type}"
        await self.set(cache_key, result, ttl)
