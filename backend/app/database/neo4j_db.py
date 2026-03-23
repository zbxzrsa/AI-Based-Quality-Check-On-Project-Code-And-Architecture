"""
Neo4j graph database connection and query management with CI/CD resilience
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
import os
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, AuthError
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings


def is_ci_environment() -> bool:
    """Check if running in CI/CD environment"""
    return bool(os.environ.get('CI') or
                os.environ.get('GITHUB_ACTIONS') or
                os.environ.get('GITLAB_CI') or
                os.environ.get('JENKINS_HOME'))

# Global driver instance
neo4j_driver: Optional[AsyncDriver] = None


class Neo4jDB:
    """
    Wrapper class for Neo4j database connection.
    Used by services that expect a class-based interface.
    """
    def __init__(self, driver: Optional[AsyncDriver] = None):
        self.driver = driver

    def get_session(self, **kwargs):
        """
        Get a Neo4j session.
        Note: This is a placeholder for services using the sync interface.
        """
        if self.driver:
            return self.driver.session(**kwargs)
        raise RuntimeError("Neo4j driver not initialized in Neo4jDB wrapper")


# Connection retry configuration
MAX_RETRIES = int(os.environ.get('NEO4J_MAX_RETRIES', '3'))
RETRY_DELAY = int(os.environ.get('NEO4J_RETRY_DELAY', '2'))


async def get_neo4j_driver() -> AsyncDriver:
    """Get Neo4j driver instance with lazy initialization"""
    global neo4j_driver
    if neo4j_driver is None:
        await init_neo4j()
    return neo4j_driver


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=RETRY_DELAY, min=1, max=10),
    retry=retry_if_exception_type((ServiceUnavailable, ConnectionError, OSError)),
    reraise=True
)
async def init_neo4j():
    """Initialize Neo4j database connection with retry logic"""
    global neo4j_driver

    # If already initialized, verify connectivity
    if neo4j_driver is not None:
        try:
            await neo4j_driver.verify_connectivity()
            return
        except Exception as e:
            logger.warning(f"Neo4j existing driver connectivity check failed: {e}")
            # Driver exists but connection failed, recreate it
            try:
                await neo4j_driver.close()
            except Exception as close_error:
                logger.warning(f"Error closing Neo4j driver: {close_error}")
            neo4j_driver = None

    try:
        logger.info(f"🔌 Connecting to Neo4j at {settings.NEO4J_URI}")

        # Create driver with optimized settings for stability
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10,  # 增加连接池大小
            connection_timeout=30,  # 增加连接超时时间
            connection_acquisition_timeout=15,  # 增加获取连接超时时间
            max_connection_lifetime=300,  # 增加连接生命周期到5分钟
            max_transaction_retry_time=30,  # 增加事务重试时间
            encrypted=False,  # Disable encryption for local development
        )

        # Verify connectivity with timeout and retry
        for attempt in range(3):
            try:
                await asyncio.wait_for(
                    neo4j_driver.verify_connectivity(),
                    timeout=15
                )
                logger.info("✅ Neo4j initialized successfully")
                break
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"Neo4j connectivity check failed (attempt {attempt + 1}/3), retrying...")
                    await asyncio.sleep(5)
                else:
                    raise e

        # Create indexes in background (don't block startup)
        asyncio.create_task(create_indexes())

    except ServiceUnavailable as e:
        error_msg = f"Neo4j service unavailable: {e}"
        logger.error(f"❌ {error_msg}")
        if is_ci_environment():
            logger.info("💡 CI Environment: Ensure Neo4j container is running and healthy")
            logger.info("   Check: docker ps | grep neo4j")
        raise RuntimeError(error_msg) from e

    except AuthError as e:
        error_msg = f"Neo4j authentication failed: {e}"
        logger.error(f"❌ {error_msg}")
        if is_ci_environment():
            logger.info("💡 CI Environment: Check NEO4J_USER and NEO4J_PASSWORD secrets")
        raise RuntimeError(error_msg) from e

    except Exception as e:
        error_msg = f"Failed to initialize Neo4j: {e}"
        logger.error(f"❌ {error_msg}")

        # Provide helpful context for common issues
        if "Connection refused" in str(e):
            logger.info("💡 Connection refused: Ensure Neo4j is running on the specified URI")
        elif "timeout" in str(e).lower():
            logger.info("💡 Timeout: Check network connectivity and Neo4j server load")
        elif "database" in str(e).lower():
            logger.info("💡 Database error: Verify NEO4J_DATABASE setting")

        raise RuntimeError(error_msg) from e


async def close_neo4j():
    """Close Neo4j database connection"""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None
        logger.info("✅ Neo4j connections closed")


async def test_neo4j_connection():
    """Test Neo4j connection"""
    try:
        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run("RETURN 1 AS num")
            record = await result.single()
            assert record["num"] == 1
        logger.info("✅ Neo4j connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        return False


async def create_indexes():
    """Create necessary indexes in Neo4j"""
    driver = await get_neo4j_driver()
    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        # Create indexes for common queries
        await session.run(
            "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.id)"
        )
        await session.run(
            "CREATE INDEX IF NOT EXISTS FOR (n:Function) ON (n.name)"
        )
        await session.run(
            "CREATE INDEX IF NOT EXISTS FOR (n:Class) ON (n.name)"
        )
        await session.run(
            "CREATE INDEX IF NOT EXISTS FOR (n:Module) ON (n.path)"
        )
    logger.info("✅ Neo4j indexes created")
