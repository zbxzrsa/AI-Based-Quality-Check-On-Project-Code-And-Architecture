"""
Database connection management with retry logic and health checks.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status

from .postgresql import (
    init_postgres,
    close_postgres,
    test_postgres_connection,
    get_db as get_postgres_session,
)
from .neo4j_db import (
    init_neo4j,
    close_neo4j,
    test_neo4j_connection,
    get_neo4j_driver,
    create_indexes as create_neo4j_indexes,
)
from .redis_db import (
    init_redis,
    close_redis,
    test_redis_connection,
    get_redis as get_redis_client,
)
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Global state to track database connections
db_state = {
    "postgres": {"connected": False, "last_check": None, "error": None},
    "neo4j": {"connected": False, "last_check": None, "error": None},
    "redis": {"connected": False, "last_check": None, "error": None},
}

# Retry configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 1  # seconds
RETRY_BACKOFF_FACTOR = 2


def retry_on_failure(max_retries: int = MAX_RETRIES, initial_delay: float = INITIAL_RETRY_DELAY):
    """Decorator for retrying database operations with exponential backoff."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        wait_time = delay * (RETRY_BACKOFF_FACTOR ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                            f"Retrying in {wait_time:.2f} seconds..."
                        )
                        await asyncio.sleep(wait_time)
            
            logger.error(f"All {max_retries} attempts failed. Last error: {str(last_exception)}")
            raise last_exception
        
        return wrapper
    return decorator


class DatabaseManager:
    """Manages database connections and provides health checks."""
    
    @classmethod
    async def initialize_databases(cls):
        """Initialize all database connections with retry logic."""
        await asyncio.gather(
            cls.initialize_postgres(),
            cls.initialize_neo4j(),
            cls.initialize_redis(),
        )
    
    @classmethod
    @retry_on_failure()
    async def initialize_postgres(cls):
        """Initialize PostgreSQL connection."""
        try:
            await init_postgres()
            if await test_postgres_connection():
                db_state["postgres"]["connected"] = True
                db_state["postgres"]["error"] = None
                logger.info("PostgreSQL connection established")
            else:
                raise Exception("PostgreSQL connection test failed")
        except Exception as e:
            db_state["postgres"]["connected"] = False
            db_state["postgres"]["error"] = str(e)
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise
        finally:
            db_state["postgres"]["last_check"] = datetime.now(timezone.utc)
    
    @classmethod
    @retry_on_failure()
    async def initialize_neo4j(cls):
        """Initialize Neo4j connection and create indexes."""
        try:
            await init_neo4j()
            if await test_neo4j_connection():
                await create_neo4j_indexes()
                db_state["neo4j"]["connected"] = True
                db_state["neo4j"]["error"] = None
                logger.info("Neo4j connection established and indexes created")
            else:
                raise Exception("Neo4j connection test failed")
        except Exception as e:
            db_state["neo4j"]["connected"] = False
            db_state["neo4j"]["error"] = str(e)
            logger.error(f"Failed to initialize Neo4j: {e}")
            raise
        finally:
            db_state["neo4j"]["last_check"] = datetime.now(timezone.utc)
    
    @classmethod
    @retry_on_failure()
    async def initialize_redis(cls):
        """Initialize Redis connection."""
        try:
            await init_redis()
            if await test_redis_connection():
                db_state["redis"]["connected"] = True
                db_state["redis"]["error"] = None
                logger.info("Redis connection established")
            else:
                raise Exception("Redis connection test failed")
        except Exception as e:
            db_state["redis"]["connected"] = False
            db_state["redis"]["error"] = str(e)
            logger.error(f"Failed to initialize Redis: {e}")
            raise
        finally:
            db_state["redis"]["last_check"] = datetime.now(timezone.utc)
    
    @classmethod
    async def close_databases(cls):
        """Close all database connections gracefully."""
        try:
            await asyncio.gather(
                close_postgres(),
                close_neo4j(),
                close_redis(),
            )
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
            raise
    
    @classmethod
    def get_database_health(cls) -> Dict[str, Dict[str, Any]]:
        """Get the current health status of all databases."""
        return {
            "postgres": {
                "connected": db_state["postgres"]["connected"],
                "last_check": db_state["postgres"]["last_check"],
                "error": db_state["postgres"]["error"],
            },
            "neo4j": {
                "connected": db_state["neo4j"]["connected"],
                "last_check": db_state["neo4j"]["last_check"],
                "error": db_state["neo4j"]["error"],
            },
            "redis": {
                "connected": db_state["redis"]["connected"],
                "last_check": db_state["redis"]["last_check"],
                "error": db_state["redis"]["error"],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @classmethod
    def get_db_dependencies(cls):
        """Get FastAPI dependencies for database sessions."""
        async def get_postgres():
            if not db_state["postgres"]["connected"]:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="PostgreSQL database is not available",
                )
            async for session in get_postgres_session():
                try:
                    yield session
                finally:
                    await session.close()
        
        async def get_neo4j():
            if not db_state["neo4j"]["connected"]:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Neo4j database is not available",
                )
            return await get_neo4j_driver()
        
        async def get_redis():
            if not db_state["redis"]["connected"]:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Redis is not available",
                )
            return await get_redis_client()
        
        return {
            "postgres": Depends(get_postgres),
            "neo4j": Depends(get_neo4j),
            "redis": Depends(get_redis),
        }


# Initialize database manager
db_manager = DatabaseManager()

# Export database dependencies
get_db = db_manager.get_db_dependencies()["postgres"]
get_neo4j = db_manager.get_db_dependencies()["neo4j"]
get_redis = db_manager.get_db_dependencies()["redis"]
