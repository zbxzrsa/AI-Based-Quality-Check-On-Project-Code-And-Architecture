"""
Neo4j graph database connection and query management
"""
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional

from app.core.config import settings

# Global driver instance
neo4j_driver: Optional[AsyncDriver] = None


async def get_neo4j_driver() -> AsyncDriver:
    """Get Neo4j driver instance"""
    global neo4j_driver
    if neo4j_driver is None:
        raise RuntimeError("Neo4j driver not initialized")
    return neo4j_driver


async def init_neo4j():
    """Initialize Neo4j database connection"""
    global neo4j_driver
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=50,
            connection_timeout=30,
        )
        # Verify connectivity
        await neo4j_driver.verify_connectivity()
        print("✅ Neo4j initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Neo4j: {e}")
        raise


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
