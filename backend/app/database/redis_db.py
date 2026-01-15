"""
Redis cache and session management
"""
import redis.asyncio as redis
from typing import Optional

from app.core.config import settings

# Global Redis client
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return redis_client


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        # Test connection
        await redis_client.ping()
        print("✅ Redis initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Redis: {e}")
        raise


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        print("✅ Redis connections closed")


async def test_redis_connection():
    """Test Redis connection"""
    try:
        client = await get_redis()
        # Test set and get
        test_key = "test:connection"
        await client.set(test_key, "success", ex=10)
        value = await client.get(test_key)
        assert value == "success"
        await client.delete(test_key)
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


async def cache_set(key: str, value: str, expiration: int = 3600):
    """Set cache value with expiration"""
    client = await get_redis()
    await client.set(key, value, ex=expiration)


async def cache_get(key: str) -> Optional[str]:
    """Get cache value"""
    client = await get_redis()
    return await client.get(key)


async def cache_delete(key: str):
    """Delete cache value"""
    client = await get_redis()
    await client.delete(key)


async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    client = await get_redis()
    return await client.exists(key) > 0
