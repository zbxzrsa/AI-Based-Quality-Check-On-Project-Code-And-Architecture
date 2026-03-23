"""
Concrete Database Connection Implementations

Implements specific connection classes for PostgreSQL, Neo4j, and Redis
using the unified DatabaseConnection interface.
"""
from typing import Optional
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker
from neo4j import AsyncGraphDatabase, AsyncDriver
import redis.asyncio as redis
from sqlalchemy import text

from app.core.config import settings
from .connection_factory import DatabaseConnection, DatabaseType

logger = logging.getLogger(__name__)


class PostgreSQLConnection(DatabaseConnection[AsyncEngine]):
    """PostgreSQL database connection"""
    
    def __init__(self):
        """Initialize PostgreSQL connection"""
        config = {
            "url": settings.postgres_url,
            "pool_size": 20,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        }
        super().__init__(DatabaseType.POSTGRESQL, config)
        self._session_maker: Optional[async_sessionmaker] = None
    
    async def _create_client(self) -> AsyncEngine:
        """Create PostgreSQL engine"""
        engine = create_async_engine(
            self.config["url"],
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=self.config["pool_size"],
            max_overflow=self.config["max_overflow"],
            pool_timeout=self.config["pool_timeout"],
            pool_recycle=self.config["pool_recycle"],
            pool_use_lifo=True,
        )
        
        # Create session maker
        self._session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        return engine
    
    async def _verify_connection(self) -> bool:
        """Verify PostgreSQL connection"""
        if self._client is None:
            return False
        
        try:
            async with self._client.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")
            return False
    
    async def _close_client(self):
        """Close PostgreSQL engine"""
        if self._client is not None:
            await self._client.dispose()
    
    def get_session_maker(self) -> async_sessionmaker:
        """
        Get session maker for creating database sessions.
        
        Returns:
            Async session maker
            
        Raises:
            RuntimeError: If connection is not initialized
        """
        if self._session_maker is None:
            raise RuntimeError("PostgreSQL session maker not initialized")
        return self._session_maker
    
    async def get_session(self) -> AsyncSession:
        """
        Get a new database session.
        
        Returns:
            Async database session
        """
        session_maker = self.get_session_maker()
        return session_maker()


class Neo4jConnection(DatabaseConnection[AsyncDriver]):
    """Neo4j graph database connection"""
    
    def __init__(self):
        """Initialize Neo4j connection"""
        config = {
            "uri": settings.NEO4J_URI,
            "user": settings.NEO4J_USER,
            "database": settings.NEO4J_DATABASE,
            "max_connection_pool_size": 10,
            "connection_timeout": 15,
            "connection_acquisition_timeout": 10,
            "max_connection_lifetime": 300,
        }
        super().__init__(DatabaseType.NEO4J, config)
    
    async def _create_client(self) -> AsyncDriver:
        """Create Neo4j driver"""
        driver = AsyncGraphDatabase.driver(
            self.config["uri"],
            auth=(self.config["user"], settings.NEO4J_PASSWORD),
            max_connection_pool_size=self.config["max_connection_pool_size"],
            connection_timeout=self.config["connection_timeout"],
            connection_acquisition_timeout=self.config["connection_acquisition_timeout"],
            max_connection_lifetime=self.config["max_connection_lifetime"],
            max_transaction_retry_time=15,
        )
        
        # Verify connectivity with timeout
        await asyncio.wait_for(
            driver.verify_connectivity(),
            timeout=10
        )
        
        # Create indexes in background
        asyncio.create_task(self._create_indexes())
        
        return driver
    
    async def _verify_connection(self) -> bool:
        """Verify Neo4j connection"""
        if self._client is None:
            return False
        
        try:
            async with self._client.session(database=self.config["database"]) as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
                return record["num"] == 1
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return False
    
    async def _close_client(self):
        """Close Neo4j driver"""
        if self._client is not None:
            await self._client.close()
    
    async def _create_indexes(self):
        """Create necessary indexes in Neo4j"""
        if self._client is None:
            return
        
        try:
            async with self._client.session(database=self.config["database"]) as session:
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
                await session.run(
                    "CREATE INDEX IF NOT EXISTS FOR (p:Project) ON (p.projectId)"
                )
        except Exception as e:
            # Don't fail if index creation fails
            import logging
            logging.getLogger(__name__).warning(f"Failed to create Neo4j indexes: {e}")


class RedisConnection(DatabaseConnection[redis.Redis]):
    """Redis cache and session management connection"""
    
    def __init__(self):
        """Initialize Redis connection"""
        config = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "max_connections": 50,
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
        }
        super().__init__(DatabaseType.REDIS, config)
    
    async def _create_client(self) -> redis.Redis:
        """Create Redis client"""
        client = redis.Redis(
            host=self.config["host"],
            port=self.config["port"],
            password=settings.REDIS_PASSWORD,
            db=self.config["db"],
            decode_responses=True,
            max_connections=self.config["max_connections"],
            socket_timeout=self.config["socket_timeout"],
            socket_connect_timeout=self.config["socket_connect_timeout"],
        )
        
        # Test connection
        await client.ping()
        
        return client
    
    async def _verify_connection(self) -> bool:
        """Verify Redis connection"""
        if self._client is None:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    async def _close_client(self):
        """Close Redis client"""
        if self._client is not None:
            await self._client.close()
    
    async def set(self, key: str, value: str, expiration: int = 3600):
        """Set cache value with expiration"""
        client = await self.get_client()
        await client.set(key, value, ex=expiration)
    
    async def get(self, key: str) -> Optional[str]:
        """Get cache value"""
        client = await self.get_client()
        return await client.get(key)
    
    async def delete(self, key: str):
        """Delete cache value"""
        client = await self.get_client()
        await client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if cache key exists"""
        client = await self.get_client()
        return await client.exists(key) > 0


# Global connection instances
_postgresql_connection: Optional[PostgreSQLConnection] = None
_neo4j_connection: Optional[Neo4jConnection] = None
_redis_connection: Optional[RedisConnection] = None


def get_postgresql_connection() -> PostgreSQLConnection:
    """Get PostgreSQL connection instance"""
    global _postgresql_connection
    if _postgresql_connection is None:
        _postgresql_connection = PostgreSQLConnection()
    return _postgresql_connection


def get_neo4j_connection() -> Neo4jConnection:
    """Get Neo4j connection instance"""
    global _neo4j_connection
    if _neo4j_connection is None:
        _neo4j_connection = Neo4jConnection()
    return _neo4j_connection


def get_redis_connection() -> RedisConnection:
    """Get Redis connection instance"""
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = RedisConnection()
    return _redis_connection
