"""
Redis cache and session management
"""
import logging
import asyncio
logger = logging.getLogger(__name__)

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
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=settings.REDIS_DB,
            decode_responses=True,
            max_connections=10,  # 减少最大连接数
            socket_timeout=10,  # 增加socket超时时间
            socket_connect_timeout=10,  # 增加连接超时时间
            retry_on_timeout=True,
            health_check_interval=60,  # 增加健康检查间隔
        )
        # Test connection with retry
        for attempt in range(3):
            try:
                await redis_client.ping()
                logger.info("✅ Redis initialized")
                return
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"Redis ping failed (attempt {attempt + 1}/3), retrying...")
                    await asyncio.sleep(2)
                else:
                    raise e
    except Exception as e:
        logger.error("❌ Failed to initialize Redis: %s", str(e))
        raise


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("✅ Redis connections closed")


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
        logger.info("✅ Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
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
