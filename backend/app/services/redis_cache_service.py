"""
Redis caching service
Implements caching strategies for the AI code review platform
"""
import json
import hashlib
from typing import Any, Optional, Dict, List
from datetime import timedelta
import redis.asyncio as redis

from app.database.redis_db import get_redis


class RedisCacheService:
    """Redis caching service with multiple cache patterns"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.metrics = {
            "hits": 0,
            "misses": 0
        }
    
    # ================================================
    # SESSION MANAGEMENT
    # ================================================
    
    async def set_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Store user session data
        Key pattern: session:{user_id}
        TTL: 24 hours (default)
        """
        key = f"session:{user_id}"
        try:
            serialized_data = json.dumps(session_data)
            await self.redis.set(key, serialized_data, ex=ttl)
            return True
        except Exception as e:
            print(f"Error setting session: {e}")
            return False
    
    async def get_session(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve user session data
        Returns None if session expired or doesn't exist
        """
        key = f"session:{user_id}"
        try:
            data = await self.redis.get(key)
            if data:
                self.metrics["hits"] += 1
                return json.loads(data)
            self.metrics["misses"] += 1
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            self.metrics["misses"] += 1
            return None
    
    async def delete_session(
        self,
        user_id: str
    ) -> bool:
        """Delete user session (logout)"""
        key = f"session:{user_id}"
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    async def extend_session(
        self,
        user_id: str,
        ttl: int = 86400
    ) -> bool:
        """Extend session TTL (refresh on activity)"""
        key = f"session:{user_id}"
        try:
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            print(f"Error extending session: {e}")
            return False
    
    # ================================================
    # ANALYSIS RESULTS CACHE
    # ================================================
    
    async def set_analysis_result(
        self,
        pr_id: str,
        result_data: Dict[str, Any],
        ttl: int = 604800  # 7 days
    ) -> bool:
        """
        Cache code review analysis results
        Key pattern: analysis:{pr_id}
        TTL: 7 days
        """
        key = f"analysis:{pr_id}"
        try:
            serialized_data = json.dumps(result_data)
            await self.redis.set(key, serialized_data, ex=ttl)
            return True
        except Exception as e:
            print(f"Error caching analysis result: {e}")
            return False
    
    async def get_analysis_result(
        self,
        pr_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis results"""
        key = f"analysis:{pr_id}"
        try:
            data = await self.redis.get(key)
            if data:
                self.metrics["hits"] += 1
                return json.loads(data)
            self.metrics["misses"] += 1
            return None
        except Exception as e:
            print(f"Error retrieving analysis result: {e}")
            self.metrics["misses"] += 1
            return None
    
    async def invalidate_analysis(
        self,
        pr_id: str
    ) -> bool:
        """Invalidate cached analysis (when PR is updated)"""
        key = f"analysis:{pr_id}"
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Error invalidating analysis: {e}")
            return False
    
    # ================================================
    # GRAPH QUERY CACHE
    # ================================================
    
    def _generate_query_hash(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate hash for query caching"""
        query_str = query
        if parameters:
            query_str += json.dumps(parameters, sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()[:16]
    
    async def set_graph_query_result(
        self,
        project_id: str,
        query: str,
        parameters: Optional[Dict[str, Any]],
        result_data: Any,
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """
        Cache Neo4j graph query results
        Key pattern: graph:{project_id}:{query_hash}
        TTL: 1 hour
        """
        query_hash = self._generate_query_hash(query, parameters)
        key = f"graph:{project_id}:{query_hash}"
        try:
            serialized_data = json.dumps(result_data)
            await self.redis.set(key, serialized_data, ex=ttl)
            return True
        except Exception as e:
            print(f"Error caching graph query: {e}")
            return False
    
    async def get_graph_query_result(
        self,
        project_id: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Retrieve cached graph query results"""
        query_hash = self._generate_query_hash(query, parameters)
        key = f"graph:{project_id}:{query_hash}"
        try:
            data = await self.redis.get(key)
            if data:
                self.metrics["hits"] += 1
                return json.loads(data)
            self.metrics["misses"] += 1
            return None
        except Exception as e:
            print(f"Error retrieving graph query: {e}")
            self.metrics["misses"] += 1
            return None
    
    async def invalidate_project_cache(
        self,
        project_id: str
    ) -> int:
        """Invalidate all cached queries for a project"""
        pattern = f"graph:{project_id}:*"
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Error invalidating project cache: {e}")
            return 0
    
    # ================================================
    # TASK QUEUE
    # ================================================
    
    async def enqueue_pr_analysis(
        self,
        pr_id: str,
        task_data: Dict[str, Any]
    ) -> bool:
        """
        Add PR analysis task to queue
        List: queue:pr_analysis
        """
        queue_key = "queue:pr_analysis"
        try:
            task_json = json.dumps({
                "pr_id": pr_id,
                **task_data
            })
            await self.redis.rpush(queue_key, task_json)
            return True
        except Exception as e:
            print(f"Error enqueueing task: {e}")
            return False
    
    async def dequeue_pr_analysis(
        self,
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Remove and return task from queue (blocking)
        Timeout in seconds
        """
        queue_key = "queue:pr_analysis"
        try:
            result = await self.redis.blpop(queue_key, timeout=timeout)
            if result:
                _, task_json = result
                return json.loads(task_json)
            return None
        except Exception as e:
            print(f"Error dequeuing task: {e}")
            return None
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        queue_key = "queue:pr_analysis"
        try:
            return await self.redis.llen(queue_key)
        except Exception as e:
            print(f"Error getting queue length: {e}")
            return 0
    
    # ================================================
    # RATE LIMITING
    # ================================================
    
    async def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        max_requests: int = 60,
        window: int = 60  # 1 minute window
    ) -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit
        Key pattern: ratelimit:{user_id}:{endpoint}
        TTL: 1 minute
        
        Returns: (allowed: bool, remaining: int)
        """
        key = f"ratelimit:{user_id}:{endpoint}"
        try:
            # Get current count
            current = await self.redis.get(key)
            
            if current is None:
                # First request in window
                await self.redis.set(key, 1, ex=window)
                return True, max_requests - 1
            
            current_count = int(current)
            
            if current_count >= max_requests:
                # Rate limit exceeded
                return False, 0
            
            # Increment counter
            await self.redis.incr(key)
            return True, max_requests - current_count - 1
            
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            # On error, allow the request (fail open)
            return True, max_requests
    
    async def reset_rate_limit(
        self,
        user_id: str,
        endpoint: str
    ) -> bool:
        """Reset rate limit for user"""
        key = f"ratelimit:{user_id}:{endpoint}"
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Error resetting rate limit: {e}")
            return False
    
    # ================================================
    # DISTRIBUTED LOCKING
    # ================================================
    
    async def acquire_lock(
        self,
        resource: str,
        lock_id: str,
        timeout: int = 30
    ) -> bool:
        """
        Acquire distributed lock
        Key pattern: lock:{resource}
        TTL: timeout seconds
        
        Returns: True if lock acquired, False otherwise
        """
        key = f"lock:{resource}"
        try:
            # SET NX (set if not exists) with expiration
            result = await self.redis.set(
                key,
                lock_id,
                nx=True,
                ex=timeout
            )
            return bool(result)
        except Exception as e:
            print(f"Error acquiring lock: {e}")
            return False
    
    async def release_lock(
        self,
        resource: str,
        lock_id: str
    ) -> bool:
        """
        Release distributed lock
        Only releases if lock_id matches (prevents releasing other's locks)
        """
        key = f"lock:{resource}"
        try:
            # Lua script for atomic check-and-delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = await self.redis.eval(lua_script, 1, key, lock_id)
            return bool(result)
        except Exception as e:
            print(f"Error releasing lock: {e}")
            return False
    
    async def extend_lock(
        self,
        resource: str,
        lock_id: str,
        timeout: int = 30
    ) -> bool:
        """Extend lock TTL if still owned by lock_id"""
        key = f"lock:{resource}"
        try:
            # Lua script for atomic check-and-extend
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = await self.redis.eval(lua_script, 1, key, lock_id, timeout)
            return bool(result)
        except Exception as e:
            print(f"Error extending lock: {e}")
            return False
    
    # ================================================
    # CACHE METRICS
    # ================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache hit/miss metrics"""
        total = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / total if total > 0 else 0
        
        return {
            "hits": self.metrics["hits"],
            "misses": self.metrics["misses"],
            "total_requests": total,
            "hit_rate": round(hit_rate * 100, 2)
        }
    
    def reset_metrics(self):
        """Reset metrics counters"""
        self.metrics = {"hits": 0, "misses": 0}


# Helper function to get Redis cache service
async def get_cache_service() -> RedisCacheService:
    """Get Redis cache service instance"""
    redis_client = await get_redis()
    return RedisCacheService(redis_client)
