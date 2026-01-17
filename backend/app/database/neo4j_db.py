"""
Neo4j graph database connection and query management with CI/CD resilience
"""
import asyncio
import os
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, AuthError, ClientError
from typing import Optional, Dict, Any
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
        except Exception:
            # Driver exists but connection failed, recreate it
            try:
                await neo4j_driver.close()
            except Exception:
                pass  # Ignore close errors
            neo4j_driver = None

    try:
        print(f"🔌 Connecting to Neo4j at {settings.NEO4J_URI}")

        # Create driver with optimized settings for CI/CD
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10,  # Reduced for CI environments
            connection_timeout=15,  # Reduced timeout for faster failures
            connection_acquisition_timeout=10,
            max_connection_lifetime=300,  # 5 minutes
            max_transaction_retry_time=15,
        )

        # Verify connectivity with timeout
        await asyncio.wait_for(
            neo4j_driver.verify_connectivity(),
            timeout=10
        )

        print("✅ Neo4j initialized successfully")

        # Create indexes in background (don't block startup)
        asyncio.create_task(create_indexes())

    except ServiceUnavailable as e:
        error_msg = f"Neo4j service unavailable: {e}"
        print(f"❌ {error_msg}")
        if is_ci_environment():
            print("💡 CI Environment: Ensure Neo4j container is running and healthy")
            print(f"   Check: docker ps | grep neo4j")
        raise RuntimeError(error_msg) from e

    except AuthError as e:
        error_msg = f"Neo4j authentication failed: {e}"
        print(f"❌ {error_msg}")
        if is_ci_environment():
            print("💡 CI Environment: Check NEO4J_USER and NEO4J_PASSWORD secrets")
        raise RuntimeError(error_msg) from e

    except Exception as e:
        error_msg = f"Failed to initialize Neo4j: {e}"
        print(f"❌ {error_msg}")

        # Provide helpful context for common issues
        if "Connection refused" in str(e):
            print("💡 Connection refused: Ensure Neo4j is running on the specified URI")
        elif "timeout" in str(e).lower():
            print("💡 Timeout: Check network connectivity and Neo4j server load")
        elif "database" in str(e).lower():
            print("💡 Database error: Verify NEO4J_DATABASE setting")

        raise RuntimeError(error_msg) from e


async def close_neo4j():
    """Close Neo4j database connection"""
    global neo4j_driver
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None
        print("✅ Neo4j connections closed")


async def test_neo4j_connection():
    """Test Neo4j connection"""
    try:
        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run("RETURN 1 AS num")
            record = await result.single()
            assert record["num"] == 1
        print("✅ Neo4j connection successful")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
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
    print("✅ Neo4j indexes created")
