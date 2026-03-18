"""
Infrastructure - Cache Service Implementation

Redis-based cache service implementation using dependency inversion.
"""
from typing import Optional, Dict, Any, List
import json

from app.domain.services import ICacheService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCacheService(ICacheService):
    """
    Redis cache service implementation.
    
    Implements ICacheService interface following DIP.
    Business logic depends on abstraction, not this concrete implementation.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize cache service.
        
        Args:
            redis_client: Optional Redis client. If not provided, will try to get from settings.
        """
        self._client = redis_client
        self._connected = False
    
    async def _get_client(self):
        """Get Redis client, lazy initialization"""
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self._connected = True
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._connected = False
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            client = await self._get_client()
            if not self._connected:
                return None
            return await client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value with TTL"""
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            await client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def enqueue_pr_analysis(self, pr_id: str, data: Dict[str, Any]) -> bool:
        """Enqueue PR analysis task to Redis queue"""
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            
            queue_name = "pr_analysis_queue"
            message = json.dumps({"pr_id": pr_id, "data": data})
            await client.rpush(queue_name, message)
            return True
        except Exception as e:
            logger.error(f"Redis enqueue error: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: Dict[str, Any], ttl: int = 300) -> bool:
        """Set JSON value"""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Redis set_json error: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
