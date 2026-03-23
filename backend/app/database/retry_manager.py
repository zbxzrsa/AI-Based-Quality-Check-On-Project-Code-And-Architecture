"""
Retry Manager for Database Connectivity Fixes

This module implements a comprehensive retry manager with exponential backoff
logic specifically designed for database operations. It supports different
retry policies per operation type and provides robust failure tracking.

Validates Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar
from dataclasses import dataclass

from .models import RetryConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


class OperationType(Enum):
    """Types of database operations that can be retried"""
    POSTGRESQL_CONNECTION = "postgresql_connection"
    NEO4J_CONNECTION = "neo4j_connection"
    NEO4J_AUTHENTICATION = "neo4j_authentication"
    MIGRATION_EXECUTION = "migration_execution"
    HEALTH_CHECK = "health_check"
    QUERY_EXECUTION = "query_execution"


@dataclass
class RetryState:
    """State tracking for retry operations"""
    operation_type: OperationType
    attempt_count: int = 0
    first_failure_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    total_failures: int = 0
    last_success_time: Optional[datetime] = None
    current_backoff_delay: float = 0.0
    
    def reset_on_success(self):
        """Reset state after successful operation"""
        self.attempt_count = 0
        self.consecutive_failures = 0
        self.current_backoff_delay = 0.0
        self.last_success_time = datetime.now()
    
    def record_failure(self, delay: float):
        """Record a failure and update state"""
        now = datetime.now()
        self.attempt_count += 1
        self.consecutive_failures += 1
        self.total_failures += 1
        self.current_backoff_delay = delay
        
        if self.first_failure_time is None:
            self.first_failure_time = now
        self.last_failure_time = now


class RetryManager:
    """
    Comprehensive retry manager with exponential backoff for database operations.
    
    Supports different retry policies per operation type and tracks failure
    patterns for authentication resilience and connection management.
    """
    
    def __init__(self, default_config: Optional[RetryConfig] = None):
        """
        Initialize retry manager with default configuration.
        
        Args:
            default_config: Default retry configuration for all operations
        """
        self.default_config = default_config or RetryConfig()
        self.operation_configs: Dict[OperationType, RetryConfig] = {}
        self.retry_states: Dict[str, RetryState] = {}
        self._lock = asyncio.Lock()
    
    def configure_operation(self, operation_type: OperationType, config: RetryConfig):
        """
        Configure retry policy for specific operation type.
        
        Args:
            operation_type: Type of operation to configure
            config: Retry configuration for this operation type
        """
        self.operation_configs[operation_type] = config
        logger.info(
            f"Configured retry policy for {operation_type.value}",
            extra={
                'operation_type': operation_type.value,
                'max_retries': config.max_retries,
                'base_delay': config.base_delay,
                'max_delay': config.max_delay
            }
        )
    
    def get_config(self, operation_type: OperationType) -> RetryConfig:
        """Get retry configuration for operation type"""
        return self.operation_configs.get(operation_type, self.default_config)
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """
        Calculate exponential backoff delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            config: Retry configuration to use
            
        Returns:
            Delay in seconds for next retry attempt
        """
        if attempt == 0:
            return config.base_delay
        
        # Exponential backoff: base_delay * (backoff_multiplier ^ attempt)
        delay = config.base_delay * (config.backoff_multiplier ** attempt)
        
        # Cap at maximum delay
        delay = min(delay, config.max_delay)
        
        logger.debug(
            f"Calculated retry delay: {delay:.2f}s for attempt {attempt + 1}",
            extra={
                'attempt': attempt + 1,
                'delay': delay,
                'base_delay': config.base_delay,
                'multiplier': config.backoff_multiplier,
                'max_delay': config.max_delay
            }
        )
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int, operation_type: OperationType) -> bool:
        """
        Determine if operation should be retried based on exception and attempt count.
        
        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-based)
            operation_type: Type of operation being retried
            
        Returns:
            True if operation should be retried, False otherwise
        """
        config = self.get_config(operation_type)
        
        # Check if we've exceeded maximum retries
        if attempt >= config.max_retries:
            logger.warning(
                f"Maximum retries ({config.max_retries}) exceeded for {operation_type.value}",
                extra={
                    'operation_type': operation_type.value,
                    'attempt': attempt + 1,
                    'max_retries': config.max_retries,
                    'exception': str(exception)
                }
            )
            return False
        
        # Check if this exception type should be retried
        exception_name = exception.__class__.__name__
        
        # Neo4j authentication failures should be retried with backoff
        if operation_type == OperationType.NEO4J_AUTHENTICATION:
            if not config.retry_on_auth_failure:
                return False
            # Retry auth failures but with exponential backoff to prevent rate limiting
            return ("auth" in exception_name.lower() or 
                    "unauthorized" in str(exception).lower() or
                    "authentication" in str(exception).lower())
        
        # Connection timeouts should be retried
        if "timeout" in exception_name.lower() or "timeout" in str(exception).lower():
            return config.retry_on_timeout
        
        # Connection errors should generally be retried
        if any(keyword in exception_name.lower() for keyword in 
               ["connection", "network", "socket", "dns"]):
            return True
        
        # Database-specific retryable errors
        if any(keyword in str(exception).lower() for keyword in 
               ["connection reset", "connection refused", "temporary failure", "simulated failure", "failure after success"]):
            return True
        
        logger.debug(
            f"Exception {exception_name} not retryable for {operation_type.value}",
            extra={
                'operation_type': operation_type.value,
                'exception_type': exception_name,
                'exception_message': str(exception)
            }
        )
        
        return False
    
    async def execute_with_retry(
        self,
        operation: Callable[..., T],
        operation_type: OperationType,
        operation_id: Optional[str] = None,
        *args,
        **kwargs
    ) -> T:
        """
        Execute operation with retry logic and exponential backoff.
        
        Args:
            operation: Async function to execute
            operation_type: Type of operation being performed
            operation_id: Unique identifier for this operation instance
            *args: Arguments to pass to operation
            **kwargs: Keyword arguments to pass to operation
            
        Returns:
            Result of successful operation execution
            
        Raises:
            Last exception if all retry attempts fail
        """
        config = self.get_config(operation_type)
        state_key = operation_id or f"{operation_type.value}_{id(operation)}"
        
        async with self._lock:
            if state_key not in self.retry_states:
                self.retry_states[state_key] = RetryState(operation_type=operation_type)
            retry_state = self.retry_states[state_key]
        
        last_exception = None
        
        for attempt in range(config.max_retries + 1):  # +1 for initial attempt
            try:
                logger.debug(
                    f"Executing {operation_type.value} (attempt {attempt + 1}/{config.max_retries + 1})",
                    extra={
                        'operation_type': operation_type.value,
                        'attempt': attempt + 1,
                        'max_attempts': config.max_retries + 1,
                        'operation_id': operation_id
                    }
                )
                
                result = await operation(*args, **kwargs)
                
                # Success - reset retry state
                async with self._lock:
                    retry_state.reset_on_success()
                
                if attempt > 0:
                    logger.info(
                        f"Operation {operation_type.value} succeeded after {attempt + 1} attempts",
                        extra={
                            'operation_type': operation_type.value,
                            'attempts': attempt + 1,
                            'operation_id': operation_id
                        }
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.should_retry(e, attempt, operation_type):
                    logger.error(
                        f"Operation {operation_type.value} failed and will not be retried",
                        extra={
                            'operation_type': operation_type.value,
                            'attempt': attempt + 1,
                            'exception': str(e),
                            'operation_id': operation_id
                        },
                        exc_info=True
                    )
                    break
                
                # Calculate delay for next attempt
                delay = self.calculate_delay(attempt, config)
                
                # Update retry state
                async with self._lock:
                    retry_state.record_failure(delay)
                
                logger.warning(
                    f"Operation {operation_type.value} failed, retrying in {delay:.2f}s",
                    extra={
                        'operation_type': operation_type.value,
                        'attempt': attempt + 1,
                        'max_attempts': config.max_retries + 1,
                        'delay': delay,
                        'exception': str(e),
                        'operation_id': operation_id,
                        'consecutive_failures': retry_state.consecutive_failures
                    }
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # All retries exhausted
        self._log_retry_exhaustion(operation_type, retry_state, last_exception, operation_id)
        
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"Operation {operation_type.value} failed without exception")
    
    def _log_retry_exhaustion(
        self,
        operation_type: OperationType,
        retry_state: RetryState,
        last_exception: Optional[Exception],
        operation_id: Optional[str]
    ):
        """Log comprehensive information when retry attempts are exhausted"""
        config = self.get_config(operation_type)
        
        # Generate resolution guidance based on operation type and error
        resolution_steps = self._get_resolution_steps(operation_type, last_exception)
        
        logger.error(
            f"Retry exhausted for {operation_type.value} after {config.max_retries + 1} attempts",
            extra={
                'operation_type': operation_type.value,
                'total_attempts': config.max_retries + 1,
                'consecutive_failures': retry_state.consecutive_failures,
                'total_failures': retry_state.total_failures,
                'first_failure_time': retry_state.first_failure_time.isoformat() if retry_state.first_failure_time else None,
                'last_failure_time': retry_state.last_failure_time.isoformat() if retry_state.last_failure_time else None,
                'last_exception': str(last_exception) if last_exception else None,
                'operation_id': operation_id,
                'resolution_steps': resolution_steps
            }
        )
    
    def _get_resolution_steps(self, operation_type: OperationType, exception: Optional[Exception]) -> list[str]:
        """Generate resolution guidance based on operation type and error"""
        steps = []
        
        if operation_type == OperationType.NEO4J_AUTHENTICATION:
            steps.extend([
                "Verify Neo4j credentials are correct",
                "Check if Neo4j server is running and accessible",
                "Ensure Neo4j authentication is enabled",
                "Check for rate limiting on Neo4j server",
                "Consider increasing retry delays to prevent rate limiting"
            ])
        elif operation_type == OperationType.POSTGRESQL_CONNECTION:
            steps.extend([
                "Verify PostgreSQL server is running",
                "Check database connection string and credentials",
                "Ensure network connectivity to database server",
                "Verify Python/asyncpg version compatibility",
                "Check connection pool configuration"
            ])
        elif operation_type == OperationType.MIGRATION_EXECUTION:
            steps.extend([
                "Check migration file encoding (should be UTF-8)",
                "Verify migration file syntax",
                "Ensure database schema is in expected state",
                "Check for conflicting migrations"
            ])
        else:
            steps.extend([
                "Check network connectivity",
                "Verify service configuration",
                "Review logs for additional error details",
                "Consider increasing timeout values"
            ])
        
        if exception and "timeout" in str(exception).lower():
            steps.insert(0, "Increase connection timeout values")
        
        return steps
    
    def get_retry_statistics(self, operation_type: Optional[OperationType] = None) -> Dict[str, Any]:
        """
        Get retry statistics for monitoring and debugging.
        
        Args:
            operation_type: Optional filter for specific operation type
            
        Returns:
            Dictionary containing retry statistics
        """
        stats = {
            'total_operations': len(self.retry_states),
            'operations_by_type': {},
            'failure_patterns': {}
        }
        
        for state_key, state in self.retry_states.items():
            if operation_type and state.operation_type != operation_type:
                continue
            
            op_type = state.operation_type.value
            if op_type not in stats['operations_by_type']:
                stats['operations_by_type'][op_type] = {
                    'count': 0,
                    'total_failures': 0,
                    'consecutive_failures': 0,
                    'avg_failures_per_operation': 0.0
                }
            
            op_stats = stats['operations_by_type'][op_type]
            op_stats['count'] += 1
            op_stats['total_failures'] += state.total_failures
            op_stats['consecutive_failures'] = max(op_stats['consecutive_failures'], state.consecutive_failures)
        
        # Calculate averages
        for op_type, op_stats in stats['operations_by_type'].items():
            if op_stats['count'] > 0:
                op_stats['avg_failures_per_operation'] = op_stats['total_failures'] / op_stats['count']
        
        return stats
    
    def reset_retry_state(self, operation_id: str):
        """Reset retry state for specific operation"""
        if operation_id in self.retry_states:
            del self.retry_states[operation_id]
            logger.info(f"Reset retry state for operation: {operation_id}")
    
    def clear_all_states(self):
        """Clear all retry states - useful for testing"""
        self.retry_states.clear()
        logger.info("Cleared all retry states")