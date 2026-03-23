"""
Neo4j Client with Authentication Resilience

This module provides a dedicated Neo4j client that wraps existing neo4j_db.py
functionality with enhanced authentication failure handling and retry logic.
It integrates with the retry manager to provide robust authentication resilience
and prevents rate limiting through proper backoff strategies.

Validates Requirements: 2.1, 2.2, 2.4, 2.5
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional
from weakref import WeakSet

import neo4j
from neo4j import AsyncDriver, AsyncSession
from neo4j.exceptions import AuthError, ClientError, ServiceUnavailable, TransientError

from .models import DatabaseConfig, ErrorType, DatabaseError
from .retry_manager import RetryManager, OperationType

logger = logging.getLogger(__name__)


class AuthFailureTracker:
    """
    Tracks authentication failures to prevent rate limiting and provide
    intelligent retry strategies for Neo4j authentication issues.
    """
    
    def __init__(self):
        self.failure_count = 0
        self.first_failure_time: Optional[datetime] = None
        self.last_failure_time: Optional[datetime] = None
        self.consecutive_failures = 0
        self.rate_limit_detected = False
        self.last_success_time: Optional[datetime] = None
    
    def record_auth_failure(self, error: AuthError) -> None:
        """Record an authentication failure and update tracking state"""
        now = datetime.now()
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_time = now
        
        if self.first_failure_time is None:
            self.first_failure_time = now
        
        # Detect potential rate limiting
        error_msg = str(error).lower()
        if any(keyword in error_msg for keyword in 
               ['rate limit', 'too many', 'throttle', 'blocked']):
            self.rate_limit_detected = True
            logger.warning(
                "Rate limiting detected in Neo4j authentication",
                extra={
                    'consecutive_failures': self.consecutive_failures,
                    'total_failures': self.failure_count,
                    'error_message': str(error)
                }
            )
    
    def record_auth_success(self) -> None:
        """Record successful authentication and reset failure tracking"""
        self.consecutive_failures = 0
        self.rate_limit_detected = False
        self.last_success_time = datetime.now()
        
        if self.failure_count > 0:
            logger.info(
                "Neo4j authentication recovered after failures",
                extra={
                    'total_failures': self.failure_count,
                    'recovery_time': self.last_success_time.isoformat()
                }
            )
    
    def should_increase_backoff(self) -> bool:
        """Determine if backoff should be increased due to rate limiting"""
        return self.rate_limit_detected or self.consecutive_failures > 2
    
    def get_recommended_delay_multiplier(self) -> float:
        """Get recommended delay multiplier based on failure patterns"""
        if self.rate_limit_detected:
            return 3.0  # Aggressive backoff for rate limiting
        elif self.consecutive_failures > 3:
            return 2.5  # Increased backoff for persistent failures
        elif self.consecutive_failures > 1:
            return 2.0  # Standard exponential backoff
        else:
            return 1.0  # Normal delay


class SessionManager:
    """
    Enhanced session management for Neo4j with proper cleanup and error handling.
    
    Tracks active sessions, provides automatic cleanup, and ensures proper
    resource management even in error conditions.
    """
    
    def __init__(self, client: 'Neo4jClient'):
        self.client = client
        self.active_sessions: WeakSet[AsyncSession] = WeakSet()
        self.session_stats = {
            'created': 0,
            'closed': 0,
            'failed': 0,
            'active_count': 0
        }
        self._cleanup_lock = asyncio.Lock()
    
    @asynccontextmanager
    async def get_session(self, database: Optional[str] = None):
        """
        Context manager for Neo4j sessions with automatic cleanup.
        
        Args:
            database: Optional database name
            
        Yields:
            Neo4j async session
            
        Raises:
            AuthError: If authentication fails
            ServiceUnavailable: If service is unavailable
        """
        session = None
        try:
            # Get session with retry logic
            session = await self.client.retry_manager.execute_with_retry(
                self._create_session,
                OperationType.NEO4J_CONNECTION,
                operation_id=f"session_creation_{id(self)}",
                database=database
            )
            
            # Track active session
            self.active_sessions.add(session)
            self.session_stats['created'] += 1
            self.session_stats['active_count'] = len(self.active_sessions)
            
            logger.debug(
                "Neo4j session created and tracked",
                extra={
                    'database': database or 'default',
                    'active_sessions': self.session_stats['active_count'],
                    'total_created': self.session_stats['created']
                }
            )
            
            yield session
            
        except Exception as e:
            self.session_stats['failed'] += 1
            logger.error(
                "Session creation or usage failed",
                extra={
                    'database': database or 'default',
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'failed_sessions': self.session_stats['failed']
                }
            )
            raise
            
        finally:
            # Ensure session cleanup
            if session is not None:
                await self._close_session_safely(session)
    
    async def _create_session(self, database: Optional[str] = None) -> AsyncSession:
        """
        Create a new Neo4j session.
        
        Args:
            database: Optional database name
            
        Returns:
            Neo4j async session
        """
        driver = await self.client.get_driver()
        session = driver.session(database=database)
        
        logger.debug(
            "Neo4j session created",
            extra={'database': database or 'default'}
        )
        
        return session
    
    async def _close_session_safely(self, session: AsyncSession) -> None:
        """
        Safely close a Neo4j session with error handling.
        
        Args:
            session: Session to close
        """
        try:
            await session.close()
            self.session_stats['closed'] += 1
            self.session_stats['active_count'] = len(self.active_sessions)
            
            logger.debug(
                "Neo4j session closed successfully",
                extra={
                    'closed_sessions': self.session_stats['closed'],
                    'active_sessions': self.session_stats['active_count']
                }
            )
            
        except Exception as e:
            logger.warning(
                "Error closing Neo4j session",
                extra={
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
    
    async def close_all_sessions(self) -> None:
        """
        Close all active sessions with proper error handling.
        """
        async with self._cleanup_lock:
            sessions_to_close = list(self.active_sessions)
            
            if not sessions_to_close:
                logger.debug("No active sessions to close")
                return
            
            logger.info(
                f"Closing {len(sessions_to_close)} active Neo4j sessions",
                extra={'session_count': len(sessions_to_close)}
            )
            
            # Close sessions concurrently
            close_tasks = [
                self._close_session_safely(session)
                for session in sessions_to_close
            ]
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            # Clear the weak set
            self.active_sessions.clear()
            self.session_stats['active_count'] = 0
            
            logger.info(
                "All Neo4j sessions closed",
                extra={
                    'total_created': self.session_stats['created'],
                    'total_closed': self.session_stats['closed'],
                    'total_failed': self.session_stats['failed']
                }
            )
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get session management statistics.
        
        Returns:
            Dictionary containing session statistics
        """
        return {
            **self.session_stats,
            'active_count': len(self.active_sessions)
        }


class Neo4jClient:
    """
    Enhanced Neo4j client with authentication resilience and session management.
    
    This client wraps the existing neo4j_db.py functionality while adding:
    - Authentication failure tracking and recovery
    - Integration with retry manager for all operations
    - Proper session management with cleanup
    - Rate limiting prevention through intelligent backoff
    """
    
    def __init__(self, config: DatabaseConfig, retry_manager: RetryManager):
        """
        Initialize Neo4j client with configuration and retry manager.
        
        Args:
            config: Database configuration including Neo4j settings
            retry_manager: Retry manager for handling failures
        """
        self.config = config
        self.retry_manager = retry_manager
        self.auth_tracker = AuthFailureTracker()
        self.session_manager = SessionManager(self)
        self._driver: Optional[AsyncDriver] = None
        self._connection_lock = asyncio.Lock()
        
        # Configure retry manager for Neo4j operations
        self._configure_retry_policies()
    
    def _configure_retry_policies(self) -> None:
        """Configure retry policies for different Neo4j operations"""
        # Authentication-specific retry policy with longer delays
        auth_config = self.config.retry_config
        auth_config.base_delay = 2.0  # Start with 2 seconds for auth failures
        auth_config.max_delay = 120.0  # Allow up to 2 minutes for auth backoff
        auth_config.backoff_multiplier = 2.5  # More aggressive backoff
        
        self.retry_manager.configure_operation(
            OperationType.NEO4J_AUTHENTICATION, 
            auth_config
        )
        
        # Connection retry policy
        connection_config = self.config.retry_config
        self.retry_manager.configure_operation(
            OperationType.NEO4J_CONNECTION,
            connection_config
        )
    
    async def get_driver(self) -> AsyncDriver:
        """
        Get Neo4j driver with authentication retry logic.
        
        Returns:
            Initialized Neo4j driver
            
        Raises:
            AuthError: If authentication fails after all retries
            ServiceUnavailable: If Neo4j service is not available
        """
        async with self._connection_lock:
            if self._driver is not None:
                try:
                    # Verify existing driver connectivity
                    await self._driver.verify_connectivity()
                    return self._driver
                except Exception as e:
                    logger.warning(
                        "Existing Neo4j driver failed connectivity check, recreating",
                        extra={'error': str(e)}
                    )
                    await self._close_driver()
            
            # Create new driver with retry logic
            self._driver = await self.retry_manager.execute_with_retry(
                self._create_driver,
                OperationType.NEO4J_AUTHENTICATION,
                operation_id="neo4j_driver_creation"
            )
            
            return self._driver
    
    async def _create_driver(self) -> AsyncDriver:
        """
        Create Neo4j driver with authentication handling.
        
        Returns:
            Configured Neo4j driver
            
        Raises:
            AuthError: If authentication fails
            ServiceUnavailable: If service is unavailable
        """
        try:
            logger.debug(
                f"Creating Neo4j driver for {self.config.neo4j_uri}",
                extra={'uri': self.config.neo4j_uri}
            )
            
            # Apply backoff multiplier if rate limiting detected
            connection_timeout = self.config.connection_timeout
            if self.auth_tracker.should_increase_backoff():
                multiplier = self.auth_tracker.get_recommended_delay_multiplier()
                connection_timeout = int(connection_timeout * multiplier)
                logger.info(
                    f"Increased connection timeout to {connection_timeout}s due to auth failures",
                    extra={
                        'original_timeout': self.config.connection_timeout,
                        'multiplier': multiplier,
                        'consecutive_failures': self.auth_tracker.consecutive_failures
                    }
                )
            
            driver = neo4j.AsyncGraphDatabase.driver(
                self.config.neo4j_uri,
                auth=self.config.neo4j_auth,
                max_connection_pool_size=self.config.pool_max_size,
                connection_timeout=connection_timeout,
                connection_acquisition_timeout=self.config.connection_timeout,
                max_connection_lifetime=300,  # 5 minutes
                max_transaction_retry_time=30,
            )
            
            # Verify connectivity and authentication
            await driver.verify_connectivity()
            
            # Record successful authentication
            self.auth_tracker.record_auth_success()
            
            logger.info(
                "Neo4j driver created successfully",
                extra={
                    'uri': self.config.neo4j_uri,
                    'pool_size': self.config.pool_max_size,
                    'timeout': connection_timeout
                }
            )
            
            return driver
            
        except AuthError as e:
            self.auth_tracker.record_auth_failure(e)
            logger.error(
                "Neo4j authentication failed",
                extra={
                    'uri': self.config.neo4j_uri,
                    'consecutive_failures': self.auth_tracker.consecutive_failures,
                    'total_failures': self.auth_tracker.failure_count,
                    'error': str(e)
                }
            )
            raise
        
        except ServiceUnavailable as e:
            logger.error(
                "Neo4j service unavailable",
                extra={
                    'uri': self.config.neo4j_uri,
                    'error': str(e)
                }
            )
            raise
        
        except Exception as e:
            logger.error(
                "Unexpected error creating Neo4j driver",
                extra={
                    'uri': self.config.neo4j_uri,
                    'error': str(e),
                    'error_type': type(e).__name__
                },
                exc_info=True
            )
            raise
    
    async def get_session(self, database: Optional[str] = None) -> AsyncSession:
        """
        Get Neo4j session with proper error handling and retry logic.
        
        DEPRECATED: Use session_manager.get_session() context manager instead
        for automatic cleanup and better resource management.
        
        Args:
            database: Optional database name
            
        Returns:
            Neo4j async session
            
        Raises:
            AuthError: If authentication fails
            ServiceUnavailable: If service is unavailable
        """
        logger.warning(
            "Direct get_session() is deprecated. Use session_manager.get_session() context manager instead.",
            extra={'database': database or 'default'}
        )
        
        driver = await self.get_driver()
        
        try:
            session = driver.session(database=database)
            logger.debug(
                "Neo4j session created (deprecated method)",
                extra={'database': database or 'default'}
            )
            return session
            
        except Exception as e:
            logger.error(
                "Failed to create Neo4j session",
                extra={
                    'database': database or 'default',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
            raise
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> neo4j.Result:
        """
        Execute Cypher query with enhanced session management and retry logic.
        
        Args:
            query: Cypher query to execute
            parameters: Query parameters
            database: Optional database name
            
        Returns:
            Query result
            
        Raises:
            AuthError: If authentication fails
            ClientError: If query is invalid
            TransientError: If temporary error occurs
        """
        return await self.retry_manager.execute_with_retry(
            self._execute_query_impl,
            OperationType.QUERY_EXECUTION,
            operation_id=f"query_{hash(query)}",
            query=query,
            parameters=parameters or {},
            database=database
        )
    
    async def _execute_query_impl(
        self,
        query: str,
        parameters: Dict[str, Any],
        database: Optional[str]
    ) -> neo4j.Result:
        """
        Internal implementation of query execution with enhanced session management.
        
        Args:
            query: Cypher query to execute
            parameters: Query parameters
            database: Optional database name
            
        Returns:
            Query result
        """
        async with self.session_manager.get_session(database) as session:
            try:
                logger.debug(
                    "Executing Neo4j query with enhanced session management",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'parameter_count': len(parameters),
                        'database': database or 'default'
                    }
                )
                
                result = await session.run(query, parameters)
                
                logger.debug(
                    "Neo4j query executed successfully",
                    extra={'database': database or 'default'}
                )
                
                return result
                
            except AuthError as e:
                self.auth_tracker.record_auth_failure(e)
                logger.error(
                    "Authentication error during query execution",
                    extra={
                        'consecutive_failures': self.auth_tracker.consecutive_failures,
                        'error': str(e)
                    }
                )
                raise
            
            except (ClientError, TransientError) as e:
                logger.error(
                    "Neo4j query error",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                )
                raise
            
            except Exception as e:
                logger.error(
                    "Unexpected error during query execution",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                raise
    
    async def execute_transaction(
        self,
        transaction_function,
        database: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute transaction with enhanced retry logic and session management.
        
        Args:
            transaction_function: Function to execute in transaction
            database: Optional database name
            **kwargs: Additional arguments for transaction function
            
        Returns:
            Transaction result
        """
        return await self.retry_manager.execute_with_retry(
            self._execute_transaction_impl,
            OperationType.QUERY_EXECUTION,
            operation_id=f"transaction_{id(transaction_function)}",
            transaction_function=transaction_function,
            database=database,
            **kwargs
        )
    
    async def _execute_transaction_impl(
        self,
        transaction_function,
        database: Optional[str],
        **kwargs
    ) -> Any:
        """
        Internal implementation of transaction execution with enhanced session management.
        
        Args:
            transaction_function: Function to execute in transaction
            database: Optional database name
            **kwargs: Additional arguments for transaction function
            
        Returns:
            Transaction result
        """
        async with self.session_manager.get_session(database) as session:
            try:
                logger.debug(
                    "Executing Neo4j transaction with enhanced session management",
                    extra={
                        'function': transaction_function.__name__,
                        'database': database or 'default'
                    }
                )
                
                result = await session.execute_write(transaction_function, **kwargs)
                
                logger.debug(
                    "Neo4j transaction completed successfully",
                    extra={
                        'function': transaction_function.__name__,
                        'database': database or 'default'
                    }
                )
                
                return result
                
            except AuthError as e:
                self.auth_tracker.record_auth_failure(e)
                logger.error(
                    "Authentication error during transaction",
                    extra={
                        'function': transaction_function.__name__,
                        'consecutive_failures': self.auth_tracker.consecutive_failures,
                        'error': str(e)
                    }
                )
                raise
            
            except Exception as e:
                logger.error(
                    "Error during transaction execution",
                    extra={
                        'function': transaction_function.__name__,
                        'database': database or 'default',
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                raise
    
    async def test_connectivity(self) -> bool:
        """
        Test Neo4j connectivity with authentication handling.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with self.session_manager.get_session() as session:
                result = await session.run("RETURN 1 AS test")
                record = await result.single()
                return record and record["test"] == 1
            
        except Exception as e:
            logger.error(
                "Neo4j connectivity test failed",
                extra={'error': str(e), 'error_type': type(e).__name__}
            )
            return False
    
    async def get_auth_statistics(self) -> Dict[str, Any]:
        """
        Get authentication failure statistics for monitoring.
        
        Returns:
            Dictionary containing authentication statistics
        """
        return {
            'total_failures': self.auth_tracker.failure_count,
            'consecutive_failures': self.auth_tracker.consecutive_failures,
            'rate_limit_detected': self.auth_tracker.rate_limit_detected,
            'first_failure_time': (
                self.auth_tracker.first_failure_time.isoformat()
                if self.auth_tracker.first_failure_time else None
            ),
            'last_failure_time': (
                self.auth_tracker.last_failure_time.isoformat()
                if self.auth_tracker.last_failure_time else None
            ),
            'last_success_time': (
                self.auth_tracker.last_success_time.isoformat()
                if self.auth_tracker.last_success_time else None
            )
        }
    
    async def _close_driver(self) -> None:
        """Close the Neo4j driver if it exists"""
        if self._driver is not None:
            try:
                await self._driver.close()
                logger.debug("Neo4j driver closed")
            except Exception as e:
                logger.warning(
                    "Error closing Neo4j driver",
                    extra={'error': str(e)}
                )
            finally:
                self._driver = None
    
    async def close(self) -> None:
        """
        Close all Neo4j connections and clean up resources with enhanced session management.
        """
        # Close all active sessions first
        await self.session_manager.close_all_sessions()
        
        # Then close the driver
        async with self._connection_lock:
            await self._close_driver()
            
        logger.info(
            "Neo4j client closed and all resources cleaned up",
            extra={
                'session_stats': self.session_manager.get_session_statistics(),
                'auth_stats': await self.get_auth_statistics()
            }
        )
    
    def handle_auth_failure(self, exception: AuthError) -> None:
        """
        Handle authentication failure with tracking and logging.
        
        Args:
            exception: Authentication error that occurred
        """
        self.auth_tracker.record_auth_failure(exception)
        
        # Create structured error for reporting
        error = DatabaseError(
            error_type=ErrorType.AUTHENTICATION_FAILURE,
            component="neo4j_client",
            message=f"Neo4j authentication failed: {str(exception)}",
            details={
                'uri': self.config.neo4j_uri,
                'consecutive_failures': self.auth_tracker.consecutive_failures,
                'total_failures': self.auth_tracker.failure_count,
                'rate_limit_detected': self.auth_tracker.rate_limit_detected
            },
            timestamp=datetime.now(),
            resolution_steps=[
                "Verify Neo4j credentials are correct",
                "Check if Neo4j server is running and accessible",
                "Ensure Neo4j authentication is enabled",
                "Check for rate limiting on Neo4j server",
                "Consider increasing retry delays to prevent rate limiting"
            ]
        )
        
        logger.error(
            "Neo4j authentication failure handled",
            extra={
                'error_type': error.error_type.value,
                'consecutive_failures': self.auth_tracker.consecutive_failures,
                'resolution_steps': error.resolution_steps
            }
        )
    
    async def execute_read_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> neo4j.Result:
        """
        Execute read-only Cypher query with enhanced session management.
        
        Args:
            query: Cypher query to execute
            parameters: Query parameters
            database: Optional database name
            
        Returns:
            Query result
        """
        async with self.session_manager.get_session(database) as session:
            try:
                logger.debug(
                    "Executing Neo4j read query",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'parameter_count': len(parameters or {}),
                        'database': database or 'default'
                    }
                )
                
                result = await session.execute_read(
                    lambda tx: tx.run(query, parameters or {})
                )
                
                logger.debug(
                    "Neo4j read query executed successfully",
                    extra={'database': database or 'default'}
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Error during read query execution",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                raise
    
    async def execute_write_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> neo4j.Result:
        """
        Execute write Cypher query with enhanced session management.
        
        Args:
            query: Cypher query to execute
            parameters: Query parameters
            database: Optional database name
            
        Returns:
            Query result
        """
        async with self.session_manager.get_session(database) as session:
            try:
                logger.debug(
                    "Executing Neo4j write query",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'parameter_count': len(parameters or {}),
                        'database': database or 'default'
                    }
                )
                
                result = await session.execute_write(
                    lambda tx: tx.run(query, parameters or {})
                )
                
                logger.debug(
                    "Neo4j write query executed successfully",
                    extra={'database': database or 'default'}
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Error during write query execution",
                    extra={
                        'query_preview': query[:100] + '...' if len(query) > 100 else query,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    exc_info=True
                )
                raise
    
    async def get_client_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive client statistics including session and auth info.
        
        Returns:
            Dictionary containing client statistics
        """
        auth_stats = await self.get_auth_statistics()
        session_stats = self.session_manager.get_session_statistics()
        retry_stats = self.retry_manager.get_retry_statistics(OperationType.NEO4J_CONNECTION)
        
        return {
            'authentication': auth_stats,
            'sessions': session_stats,
            'retries': retry_stats,
            'driver_status': {
                'is_connected': self._driver is not None,
                'uri': self.config.neo4j_uri
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of Neo4j client.
        
        Returns:
            Dictionary containing health check results
        """
        health_info = {
            'status': 'unknown',
            'connectivity': False,
            'authentication': 'unknown',
            'session_management': 'unknown',
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Test basic connectivity
            connectivity_result = await self.test_connectivity()
            health_info['connectivity'] = connectivity_result
            
            if connectivity_result:
                health_info['status'] = 'healthy'
                health_info['authentication'] = 'success'
                health_info['session_management'] = 'operational'
            else:
                health_info['status'] = 'unhealthy'
                health_info['authentication'] = 'failed'
                
        except AuthError as e:
            health_info['status'] = 'unhealthy'
            health_info['authentication'] = 'failed'
            health_info['error'] = f"Authentication error: {str(e)}"
            
        except Exception as e:
            health_info['status'] = 'unhealthy'
            health_info['error'] = f"Health check failed: {str(e)}"
        
        # Add statistics
        health_info['statistics'] = await self.get_client_statistics()
        
        return health_info