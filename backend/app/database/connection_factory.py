"""
Unified Database Connection Factory

Provides a consistent interface for managing database connections
across PostgreSQL, Neo4j, and Redis with common patterns for:
- Connection initialization
- Connection testing
- Connection closing
- Error handling
- Retry logic
"""
from typing import Optional, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseType(str, Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    NEO4J = "neo4j"
    REDIS = "redis"


class ConnectionStatus(str, Enum):
    """Connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class DatabaseConnection(ABC, Generic[T]):
    """
    Abstract base class for database connections.
    
    Provides common patterns for connection management:
    - Lazy initialization
    - Connection pooling
    - Health checks
    - Graceful shutdown
    - Error handling
    """
    
    def __init__(self, db_type: DatabaseType, config: Dict[str, Any]):
        """
        Initialize database connection.
        
        Args:
            db_type: Type of database
            config: Database configuration
        """
        self.db_type = db_type
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._client: Optional[T] = None
        self._lock = asyncio.Lock()
    
    @property
    def client(self) -> Optional[T]:
        """Get the underlying database client"""
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is established"""
        return self.status == ConnectionStatus.CONNECTED and self._client is not None
    
    @abstractmethod
    async def _create_client(self) -> T:
        """
        Create database client instance.
        
        Returns:
            Database client
        """
        pass
    
    @abstractmethod
    async def _verify_connection(self) -> bool:
        """
        Verify connection is working.
        
        Returns:
            True if connection is healthy
        """
        pass
    
    @abstractmethod
    async def _close_client(self):
        """Close database client"""
        pass
    
    async def initialize(self, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize database connection with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        async with self._lock:
            if self.is_connected:
                logger.info(f"{self.db_type.value} already connected")
                return
            
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Initializing {self.db_type.value} connection...")
            
            for attempt in range(1, max_retries + 1):
                try:
                    self._client = await self._create_client()
                    
                    # Verify connection
                    if await self._verify_connection():
                        self.status = ConnectionStatus.CONNECTED
                        logger.info(f"✅ {self.db_type.value} initialized successfully")
                        return
                    else:
                        raise RuntimeError("Connection verification failed")
                
                except Exception as e:
                    logger.warning(
                        f"❌ {self.db_type.value} connection attempt {attempt}/{max_retries} failed: {e}"
                    )
                    
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay * attempt)
                    else:
                        self.status = ConnectionStatus.ERROR
                        raise RuntimeError(
                            f"Failed to initialize {self.db_type.value} after {max_retries} attempts"
                        ) from e
    
    async def close(self):
        """Close database connection"""
        async with self._lock:
            if self._client is not None:
                try:
                    await self._close_client()
                    logger.info(f"✅ {self.db_type.value} connection closed")
                except Exception as e:
                    logger.error(f"Error closing {self.db_type.value} connection: {e}")
                finally:
                    self._client = None
                    self.status = ConnectionStatus.DISCONNECTED
    
    async def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection is healthy
        """
        try:
            if not self.is_connected:
                logger.warning(f"{self.db_type.value} not connected")
                return False
            
            result = await self._verify_connection()
            if result:
                logger.info(f"✅ {self.db_type.value} connection test successful")
            else:
                logger.error(f"❌ {self.db_type.value} connection test failed")
            return result
        
        except Exception as e:
            logger.error(f"❌ {self.db_type.value} connection test failed: {e}")
            return False
    
    async def get_client(self) -> T:
        """
        Get database client with lazy initialization.
        
        Returns:
            Database client
            
        Raises:
            RuntimeError: If connection is not initialized
        """
        if not self.is_connected:
            await self.initialize()
        
        if self._client is None:
            raise RuntimeError(f"{self.db_type.value} client not initialized")
        
        return self._client
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get connection status information.
        
        Returns:
            Status dictionary
        """
        return {
            "database": self.db_type.value,
            "status": self.status.value,
            "connected": self.is_connected,
            "config": {
                k: v for k, v in self.config.items()
                if k not in ['password', 'api_key', 'secret']
            }
        }


class DatabaseConnectionManager:
    """
    Manages multiple database connections.
    
    Provides centralized management for all database connections
    with support for:
    - Parallel initialization
    - Health monitoring
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize connection manager"""
        self._connections: Dict[DatabaseType, DatabaseConnection] = {}
    
    def register(self, connection: DatabaseConnection):
        """
        Register a database connection.
        
        Args:
            connection: Database connection to register
        """
        self._connections[connection.db_type] = connection
        logger.info(f"Registered {connection.db_type.value} connection")
    
    def get(self, db_type: DatabaseType) -> Optional[DatabaseConnection]:
        """
        Get a registered connection.
        
        Args:
            db_type: Type of database
            
        Returns:
            Database connection or None
        """
        return self._connections.get(db_type)
    
    async def initialize_all(self, parallel: bool = True):
        """
        Initialize all registered connections.
        
        Args:
            parallel: Whether to initialize in parallel
        """
        if parallel:
            tasks = [
                conn.initialize()
                for conn in self._connections.values()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any failures
            for conn, result in zip(self._connections.values(), results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to initialize {conn.db_type.value}: {result}"
                    )
        else:
            for conn in self._connections.values():
                try:
                    await conn.initialize()
                except Exception as e:
                    logger.error(
                        f"Failed to initialize {conn.db_type.value}: {e}"
                    )
    
    async def close_all(self):
        """Close all registered connections"""
        tasks = [
            conn.close()
            for conn in self._connections.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def test_all(self) -> Dict[DatabaseType, bool]:
        """
        Test all registered connections.
        
        Returns:
            Dictionary mapping database type to test result
        """
        results = {}
        for db_type, conn in self._connections.items():
            results[db_type] = await conn.test_connection()
        return results
    
    def get_status_all(self) -> Dict[str, Any]:
        """
        Get status of all connections.
        
        Returns:
            Status dictionary
        """
        return {
            db_type.value: conn.get_status()
            for db_type, conn in self._connections.items()
        }


# Global connection manager instance
_connection_manager: Optional[DatabaseConnectionManager] = None


def get_connection_manager() -> DatabaseConnectionManager:
    """
    Get global connection manager instance.
    
    Returns:
        Connection manager
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = DatabaseConnectionManager()
    return _connection_manager
