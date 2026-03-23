"""
Circuit breaker wrapper for Neo4j database operations

Provides circuit breaker protection for all Neo4j database operations
with graceful degradation using cached data.

Validates Requirements: 2.6, 2.7, 12.5, 12.6
"""
import logging
from typing import Optional, Any, Callable
from neo4j import AsyncDriver

from app.services.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerConfig
)
from app.database.neo4j_db import get_neo4j_driver
from app.shared.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class Neo4jCircuitBreakerError(Exception):
    """Raised when Neo4j circuit breaker is open"""
    pass


class Neo4jWithCircuitBreaker:
    """
    Neo4j database wrapper with circuit breaker protection
    
    Wraps Neo4j database operations with circuit breaker pattern
    to prevent cascading failures. Implements graceful degradation
    by returning cached data when circuit is open.
    
    Validates Requirements: 2.6, 2.7, 12.5, 12.6
    """
    
    def __init__(self):
        """Initialize Neo4j wrapper with circuit breaker"""
        self.circuit_breaker = CircuitBreaker(
            name="neo4j_database",
            config=CircuitBreakerConfig(
                failure_threshold=0.5,  # 50% failure rate
                success_threshold=2,
                timeout=60,
                window_size=10
            )
        )
        self.cache = get_cache_manager()
        
        logger.info("Neo4j database wrapper initialized with circuit breaker and caching")
    
    async def get_driver(self) -> AsyncDriver:
        """
        Get Neo4j driver with circuit breaker protection
        
        Returns:
            Neo4j driver instance
            
        Raises:
            Neo4jCircuitBreakerError: If circuit is open
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
        """
        try:
            return await self.circuit_breaker.call_async(get_neo4j_driver)
        except CircuitBreakerOpenError as e:
            logger.error(f"Neo4j circuit breaker is OPEN: {e}")
            raise Neo4jCircuitBreakerError(
                "Neo4j database is temporarily unavailable. Please try again later."
            )
    
    async def execute_read_query(
        self,
        query: str,
        parameters: Optional[dict] = None,
        database: Optional[str] = None
    ) -> list:
        """
        Execute a read query with circuit breaker protection and caching
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (optional)
            
        Returns:
            List of query results (from database or cache)
            
        Raises:
            Neo4jCircuitBreakerError: If circuit is open and no cached data
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
            - 2.7, 12.6: Graceful degradation with cached data
        """
        # Generate cache key from query and parameters
        import hashlib
        cache_key_str = f"neo4j:read:{query}:{str(parameters)}"
        cache_key = f"neo4j:read:{hashlib.md5(cache_key_str.encode()).hexdigest()}"
        
        async def _execute():
            driver = await get_neo4j_driver()
            async with driver.session(database=database) as session:
                result = await session.run(query, parameters or {})
                return [record async for record in result]
        
        try:
            result = await self.circuit_breaker.call_async(_execute)
            # Cache successful result
            self.cache.set(cache_key, result)
            return result
        except CircuitBreakerOpenError as e:
            logger.error(f"Neo4j circuit breaker is OPEN: {e}")
            # Try to return cached data
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.info(f"Returning cached Neo4j query result")
                return cached_data
            # No cached data available
            raise Neo4jCircuitBreakerError(
                "Neo4j database is temporarily unavailable and no cached data is available."
            )
    
    async def execute_write_query(
        self,
        query: str,
        parameters: Optional[dict] = None,
        database: Optional[str] = None
    ) -> Any:
        """
        Execute a write query with circuit breaker protection
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (optional)
            
        Returns:
            Query result summary
            
        Raises:
            Neo4jCircuitBreakerError: If circuit is open
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
        """
        async def _execute():
            driver = await get_neo4j_driver()
            async with driver.session(database=database) as session:
                result = await session.run(query, parameters or {})
                return await result.consume()
        
        try:
            return await self.circuit_breaker.call_async(_execute)
        except CircuitBreakerOpenError as e:
            logger.error(f"Neo4j circuit breaker is OPEN: {e}")
            raise Neo4jCircuitBreakerError(
                "Neo4j database is temporarily unavailable. Please try again later."
            )
    
    async def execute_transaction(
        self,
        transaction_func: Callable,
        database: Optional[str] = None
    ) -> Any:
        """
        Execute a transaction function with circuit breaker protection
        
        Args:
            transaction_func: Async function that takes a transaction object
            database: Database name (optional)
            
        Returns:
            Transaction result
            
        Raises:
            Neo4jCircuitBreakerError: If circuit is open
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
        """
        async def _execute():
            driver = await get_neo4j_driver()
            async with driver.session(database=database) as session:
                return await session.execute_write(transaction_func)
        
        try:
            return await self.circuit_breaker.call_async(_execute)
        except CircuitBreakerOpenError as e:
            logger.error(f"Neo4j circuit breaker is OPEN: {e}")
            raise Neo4jCircuitBreakerError(
                "Neo4j database is temporarily unavailable. Please try again later."
            )
    
    async def verify_connectivity(self) -> bool:
        """
        Verify Neo4j connectivity with circuit breaker protection
        
        Returns:
            True if connection is successful
            
        Raises:
            Neo4jCircuitBreakerError: If circuit is open
            
        Requirements:
            - 2.6, 12.5: Circuit breaker pattern
        """
        async def _verify():
            driver = await get_neo4j_driver()
            await driver.verify_connectivity()
            return True
        
        try:
            return await self.circuit_breaker.call_async(_verify)
        except CircuitBreakerOpenError as e:
            logger.error(f"Neo4j circuit breaker is OPEN: {e}")
            raise Neo4jCircuitBreakerError(
                "Neo4j database is temporarily unavailable. Please try again later."
            )
    
    def get_circuit_breaker_stats(self) -> dict:
        """
        Get circuit breaker statistics
        
        Returns:
            Circuit breaker stats
        """
        return self.circuit_breaker.get_stats()


# Singleton instance
_neo4j_with_cb: Optional[Neo4jWithCircuitBreaker] = None


def get_neo4j_with_circuit_breaker() -> Neo4jWithCircuitBreaker:
    """Get Neo4j wrapper instance with circuit breaker"""
    global _neo4j_with_cb
    if _neo4j_with_cb is None:
        _neo4j_with_cb = Neo4jWithCircuitBreaker()
    return _neo4j_with_cb
