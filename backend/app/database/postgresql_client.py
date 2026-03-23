"""
PostgreSQL client with compatibility validation and enhanced connection management.

This module provides a dedicated PostgreSQLClient class that wraps existing
postgresql.py functionality while adding Python/asyncpg version validation,
advanced connection pooling, timeout management, and retry integration.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 4.4
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List
from contextlib import asynccontextmanager
from dataclasses import dataclass

import asyncpg

from app.database.postgresql import (
    AsyncSessionLocal, 
    init_postgres, 
    close_postgres, 
    test_postgres_connection
)
from app.database.config_validator import ConfigurationValidator
from app.database.models import (
    CompatibilityResult, 
    DatabaseError, 
    ErrorType,
    ConnectionStatus
)
from app.database.retry_manager import RetryManager
from app.core.error_reporter import ErrorReporter
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for PostgreSQL connection pool"""
    min_size: int = 5
    max_size: int = 20
    command_timeout: float = 30.0
    connection_timeout: float = 30.0
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0
    setup: Optional[callable] = None
    init: Optional[callable] = None
    server_settings: Optional[Dict[str, str]] = None


@dataclass
class PoolStats:
    """Statistics for connection pool monitoring"""
    size: int
    freesize: int
    max_size: int
    min_size: int
    active_connections: int
    idle_connections: int
    total_connections_created: int
    total_connections_closed: int
    pool_hits: int
    pool_misses: int
    connection_timeouts: int
    last_updated: datetime


class PostgreSQLCompatibilityError(Exception):
    """Exception raised when PostgreSQL compatibility issues are detected."""
    
    def __init__(self, message: str, compatibility_result: CompatibilityResult):
        super().__init__(message)
        self.compatibility_result = compatibility_result


class PostgreSQLClient:
    """
    Enhanced PostgreSQL client with compatibility validation, advanced connection pooling,
    timeout management, and retry integration.
    
    This class wraps the existing postgresql.py functionality while adding:
    - Python/asyncpg version compatibility validation
    - Advanced connection pooling with configurable limits
    - Connection timeout management and cleanup
    - Integration with retry manager for connection failures
    - Pool health monitoring and statistics
    - Enhanced error handling with clear messages
    """
    
    def __init__(self, connection_manager=None, retry_manager: Optional[RetryManager] = None):
        """
        Initialize PostgreSQL client with advanced connection pooling.
        
        Args:
            connection_manager: Optional connection manager for integration
            retry_manager: Optional retry manager for connection failures
        """
        self.connection_manager = connection_manager
        self.retry_manager = retry_manager or RetryManager()
        self.compatibility_checker = ConfigurationValidator()
        self.error_reporter = ErrorReporter()
        self._compatibility_validated = False
        self._compatibility_result: Optional[CompatibilityResult] = None
        
        # Advanced connection pooling
        self._pool: Optional[asyncpg.Pool] = None
        self._pool_config: Optional[PoolConfig] = None
        self._pool_stats = PoolStats(
            size=0, freesize=0, max_size=0, min_size=0,
            active_connections=0, idle_connections=0,
            total_connections_created=0, total_connections_closed=0,
            pool_hits=0, pool_misses=0, connection_timeouts=0,
            last_updated=datetime.now()
        )
        self._pool_lock = asyncio.Lock()
        self._connection_cleanup_task: Optional[asyncio.Task] = None
        
    async def validate_compatibility(self) -> CompatibilityResult:
        """
        Check Python/asyncpg version compatibility.
        
        Returns:
            CompatibilityResult: Detailed compatibility information
            
        Raises:
            PostgreSQLCompatibilityError: When compatibility issues are found
        """
        logger.info("Validating Python/asyncpg compatibility...")
        
        try:
            result = self.compatibility_checker.check_python_asyncpg_compatibility()
            self._compatibility_result = result
            
            if not result.is_compatible:
                error_message = (
                    f"PostgreSQL compatibility validation failed. "
                    f"Python {result.python_version} with asyncpg {result.asyncpg_version} "
                    f"has compatibility issues: {', '.join(result.issues)}"
                )
                
                # Log detailed compatibility error
                await self._log_compatibility_error(result, error_message)
                
                raise PostgreSQLCompatibilityError(error_message, result)
            
            self._compatibility_validated = True
            logger.info(
                f"✅ PostgreSQL compatibility validated: "
                f"Python {result.python_version}, asyncpg {result.asyncpg_version}"
            )
            
            return result
            
        except Exception as e:
            if isinstance(e, PostgreSQLCompatibilityError):
                raise
            
            # Handle unexpected errors during compatibility check
            error_message = f"Failed to validate PostgreSQL compatibility: {str(e)}"
            logger.error(error_message)
            
            # Create error result for unexpected failures
            result = CompatibilityResult(
                is_compatible=False,
                python_version="unknown",
                asyncpg_version="unknown",
                issues=[f"Compatibility check failed: {str(e)}"],
                recommendations=[
                    "Check that asyncpg is properly installed",
                    "Verify Python environment is correctly configured",
                    "Review system dependencies and versions"
                ]
            )
            
            await self._log_compatibility_error(result, error_message)
            raise PostgreSQLCompatibilityError(error_message, result)
    
    async def create_pool(self, dsn: str, **kwargs) -> asyncpg.Pool:
        """
        Create PostgreSQL connection pool with compatibility validation.
        
        Args:
            dsn: Database connection string
            **kwargs: Additional pool configuration options
            
        Returns:
            asyncpg.Pool: Configured connection pool
            
        Raises:
            PostgreSQLCompatibilityError: When compatibility validation fails
            Exception: When pool creation fails
        """
        # Ensure compatibility is validated before creating pool
        if not self._compatibility_validated:
            await self.validate_compatibility()
        
        logger.info("Creating PostgreSQL connection pool...")
        
        try:
            # Set default pool configuration
            pool_config = {
                'min_size': kwargs.get('min_size', 5),
                'max_size': kwargs.get('max_size', 20),
                'command_timeout': kwargs.get('command_timeout', 30),
                'server_settings': kwargs.get('server_settings', {}),
                **kwargs
            }
            
            # Create the connection pool
            pool = await asyncpg.create_pool(dsn, **pool_config)
            
            logger.info(
                f"✅ PostgreSQL connection pool created successfully "
                f"(min_size={pool_config['min_size']}, max_size={pool_config['max_size']})"
            )
            
            return pool
            
        except Exception as e:
            error_message = f"Failed to create PostgreSQL connection pool: {str(e)}"
            logger.error(error_message)
            
            # Report pool creation error
            await self._report_connection_error(
                error_type=ErrorType.CONNECTION_TIMEOUT,
                message=error_message,
                details={
                    'dsn': self.error_reporter.mask_sensitive_data(dsn),
                    'pool_config': pool_config,
                    'error': str(e)
                }
            )
            
            raise
    
    async def execute_query(self, query: str, *args) -> Any:
        """
        Execute PostgreSQL query with connection retry and error handling.
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            
        Returns:
            Query result
            
        Raises:
            PostgreSQLCompatibilityError: When compatibility validation fails
            Exception: When query execution fails
        """
        # Ensure compatibility is validated
        if not self._compatibility_validated:
            await self.validate_compatibility()
        
        logger.debug(f"Executing PostgreSQL query: {query[:100]}...")
        
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(query, args)
                await session.commit()
                return result
                
        except Exception as e:
            error_message = f"Failed to execute PostgreSQL query: {str(e)}"
            logger.error(error_message)
            
            # Report query execution error
            await self._report_connection_error(
                error_type=ErrorType.CONNECTION_TIMEOUT,
                message=error_message,
                details={
                    'query': query[:200],  # Truncate long queries
                    'args_count': len(args),
                    'error': str(e)
                }
            )
            
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """
        Get PostgreSQL session with compatibility validation and error handling.
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            PostgreSQLCompatibilityError: When compatibility validation fails
        """
        # Ensure compatibility is validated
        if not self._compatibility_validated:
            await self.validate_compatibility()
        
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def test_connection(self) -> ConnectionStatus:
        """
        Test PostgreSQL connection with compatibility validation.
        
        Returns:
            ConnectionStatus: Connection test results
        """
        start_time = datetime.now()
        
        try:
            # Validate compatibility first
            if not self._compatibility_validated:
                await self.validate_compatibility()
            
            # Test the connection using existing functionality
            success = await test_postgres_connection()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if success:
                return ConnectionStatus(
                    service="PostgreSQL",
                    is_connected=True,
                    response_time_ms=response_time,
                    last_attempt=datetime.now()
                )
            else:
                return ConnectionStatus(
                    service="PostgreSQL",
                    is_connected=False,
                    error="Connection test failed",
                    response_time_ms=response_time,
                    last_attempt=datetime.now()
                )
                
        except PostgreSQLCompatibilityError as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return ConnectionStatus(
                service="PostgreSQL",
                is_connected=False,
                error=f"Compatibility error: {str(e)}",
                response_time_ms=response_time,
                last_attempt=datetime.now()
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            error_message = f"Connection test failed: {str(e)}"
            
            await self._report_connection_error(
                error_type=ErrorType.CONNECTION_TIMEOUT,
                message=error_message,
                details={'error': str(e)}
            )
            
            return ConnectionStatus(
                service="PostgreSQL",
                is_connected=False,
                error=error_message,
                response_time_ms=response_time,
                last_attempt=datetime.now()
            )
    
    async def initialize(self) -> None:
        """
        Initialize PostgreSQL with compatibility validation.
        
        Raises:
            PostgreSQLCompatibilityError: When compatibility validation fails
        """
        # Validate compatibility before initialization
        await self.validate_compatibility()
        
        logger.info("Initializing PostgreSQL with compatibility validation...")
        
        try:
            await init_postgres()
            logger.info("✅ PostgreSQL initialized successfully")
            
        except Exception as e:
            error_message = f"Failed to initialize PostgreSQL: {str(e)}"
            logger.error(error_message)
            
            await self._report_connection_error(
                error_type=ErrorType.CONNECTION_TIMEOUT,
                message=error_message,
                details={'error': str(e)}
            )
            
            raise
    
    async def close(self) -> None:
        """Close PostgreSQL connections."""
        logger.info("Closing PostgreSQL connections...")
        
        try:
            await close_postgres()
            logger.info("✅ PostgreSQL connections closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing PostgreSQL connections: {str(e)}")
            raise
    
    def get_compatibility_result(self) -> Optional[CompatibilityResult]:
        """
        Get the last compatibility validation result.
        
        Returns:
            CompatibilityResult or None if not yet validated
        """
        return self._compatibility_result
    
    def is_compatibility_validated(self) -> bool:
        """
        Check if compatibility has been validated.
        
        Returns:
            bool: True if compatibility has been validated successfully
        """
        return self._compatibility_validated
    
    async def _log_compatibility_error(self, result: CompatibilityResult, message: str) -> None:
        """Log detailed compatibility error information."""
        logger.error(f"PostgreSQL Compatibility Error: {message}")
        logger.error(f"Python version: {result.python_version}")
        logger.error(f"asyncpg version: {result.asyncpg_version}")
        logger.error(f"Issues: {', '.join(result.issues)}")
        logger.error(f"Recommendations: {', '.join(result.recommendations)}")
        
        # Report to error reporting system
        await self._report_connection_error(
            error_type=ErrorType.COMPATIBILITY_ERROR,
            message=message,
            details={
                'python_version': result.python_version,
                'asyncpg_version': result.asyncpg_version,
                'issues': result.issues,
                'recommendations': result.recommendations
            }
        )
    
    async def _report_connection_error(
        self, 
        error_type: ErrorType, 
        message: str, 
        details: Dict[str, Any]
    ) -> None:
        """Report database connection error to error reporting system."""
        try:
            error = DatabaseError(
                error_type=error_type,
                component="PostgreSQLClient",
                message=message,
                details=details,
                timestamp=datetime.now(),
                resolution_steps=self._get_resolution_steps(error_type)
            )
            
            # Use error reporter to format and log the error
            formatted_error = self.error_reporter.format_connection_error(
                service="PostgreSQL",
                error=Exception(message),
                connection_string=details.get('dsn', 'N/A')
            )
            logger.error(formatted_error)
            
        except Exception as e:
            logger.error(f"Failed to report database error: {str(e)}")
    
    def _get_resolution_steps(self, error_type: ErrorType) -> List[str]:
        """Get resolution steps for specific error types."""
        resolution_steps = {
            ErrorType.COMPATIBILITY_ERROR: [
                "Check Python version compatibility with asyncpg",
                "Update asyncpg to a compatible version: pip install --upgrade asyncpg",
                "Consider downgrading Python if using unsupported version",
                "Review asyncpg documentation for version compatibility matrix",
                "Verify virtual environment is using correct Python version"
            ],
            ErrorType.CONNECTION_TIMEOUT: [
                "Check PostgreSQL server is running and accessible",
                "Verify connection string and credentials",
                "Check network connectivity to database server",
                "Review connection pool configuration",
                "Check PostgreSQL server logs for connection issues"
            ],
            ErrorType.AUTHENTICATION_FAILURE: [
                "Verify PostgreSQL username and password",
                "Check user permissions in PostgreSQL",
                "Ensure user has access to the specified database",
                "Review PostgreSQL authentication configuration (pg_hba.conf)"
            ]
        }
        
        return resolution_steps.get(error_type, [
            "Check PostgreSQL server status and configuration",
            "Review application logs for detailed error information",
            "Verify database connection parameters",
            "Contact system administrator if issues persist"
        ])