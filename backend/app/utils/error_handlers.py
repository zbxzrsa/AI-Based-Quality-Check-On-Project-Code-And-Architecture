"""
Unified Error Handling Decorators

Provides reusable decorators for common error handling patterns:
- Retry logic with exponential backoff
- Logging and monitoring
- Error transformation
- Circuit breaker integration
"""
import functools
import logging
import time
from typing import Callable, Optional, Type, Tuple, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: int = logging.WARNING
):
    """
    Decorator for adding retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
        log_level: Logging level for retry attempts
        
    Example:
        @with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        async def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, log_level),
            after=after_log(logger, log_level),
            reraise=True
        )
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def with_error_logging(
    error_message: Optional[str] = None,
    log_level: int = logging.ERROR,
    include_traceback: bool = True
):
    """
    Decorator for logging errors with context.
    
    Args:
        error_message: Custom error message prefix
        log_level: Logging level for errors
        include_traceback: Whether to include full traceback
        
    Example:
        @with_error_logging("Failed to process request")
        async def process_request(data):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                msg = error_message or f"Error in {func.__name__}"
                logger.log(
                    log_level,
                    f"{msg}: {str(e)}",
                    exc_info=include_traceback,
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200]
                    }
                )
                raise
        return wrapper
    return decorator


def with_performance_logging(
    threshold_ms: Optional[int] = None,
    log_level: int = logging.INFO
):
    """
    Decorator for logging function performance.
    
    Args:
        threshold_ms: Only log if execution time exceeds this threshold (milliseconds)
        log_level: Logging level for performance logs
        
    Example:
        @with_performance_logging(threshold_ms=1000)
        async def slow_operation():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                
                if threshold_ms is None or elapsed_ms >= threshold_ms:
                    logger.log(
                        log_level,
                        f"{func.__name__} took {elapsed_ms:.2f}ms",
                        extra={
                            "function": func.__name__,
                            "elapsed_ms": elapsed_ms,
                            "threshold_ms": threshold_ms
                        }
                    )
        return wrapper
    return decorator


def with_error_transformation(
    error_map: dict[Type[Exception], Type[Exception]],
    default_error: Optional[Type[Exception]] = None
):
    """
    Decorator for transforming exceptions.
    
    Args:
        error_map: Dictionary mapping source exception types to target types
        default_error: Default exception type if no mapping found
        
    Example:
        @with_error_transformation({
            ConnectionError: ServiceUnavailableError,
            TimeoutError: ServiceUnavailableError
        })
        async def call_external_service():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Find matching exception type
                for source_type, target_type in error_map.items():
                    if isinstance(e, source_type):
                        raise target_type(str(e)) from e
                
                # Use default error if provided
                if default_error is not None:
                    raise default_error(str(e)) from e
                
                # Re-raise original exception
                raise
        return wrapper
    return decorator


def with_fallback(
    fallback_value: Any = None,
    fallback_func: Optional[Callable] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_error: bool = True
):
    """
    Decorator for providing fallback values on error.
    
    Args:
        fallback_value: Value to return on error
        fallback_func: Function to call for fallback value
        exceptions: Tuple of exception types to catch
        log_error: Whether to log the error
        
    Example:
        @with_fallback(fallback_value=[])
        async def get_items():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                if log_error:
                    logger.error(
                        f"Error in {func.__name__}, using fallback: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__
                        }
                    )
                
                if fallback_func is not None:
                    return await fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(fallback_func) else fallback_func(*args, **kwargs)
                
                return fallback_value
        return wrapper
    return decorator


def with_validation(
    validate_args: Optional[Callable] = None,
    validate_result: Optional[Callable] = None
):
    """
    Decorator for validating function arguments and results.
    
    Args:
        validate_args: Function to validate arguments
        validate_result: Function to validate result
        
    Example:
        def validate_positive(x):
            if x <= 0:
                raise ValueError("Must be positive")
        
        @with_validation(validate_args=lambda x: validate_positive(x))
        async def process_number(x: int):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Validate arguments
            if validate_args is not None:
                validate_args(*args, **kwargs)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Validate result
            if validate_result is not None:
                validate_result(result)
            
            return result
        return wrapper
    return decorator


def combine_decorators(*decorators):
    """
    Combine multiple decorators into one.
    
    Args:
        *decorators: Decorators to combine
        
    Example:
        @combine_decorators(
            with_retry(max_attempts=3),
            with_error_logging("Operation failed"),
            with_performance_logging(threshold_ms=1000)
        )
        async def complex_operation():
            ...
    """
    def decorator(func: Callable):
        for dec in reversed(decorators):
            func = dec(func)
        return func
    return decorator


# Common decorator combinations
def with_resilience(
    max_attempts: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_performance: bool = True
):
    """
    Decorator combining retry, error logging, and performance logging.
    
    Args:
        max_attempts: Maximum number of retry attempts
        exceptions: Tuple of exception types to retry on
        log_performance: Whether to log performance metrics
        
    Example:
        @with_resilience(max_attempts=3, exceptions=(ConnectionError,))
        async def call_api():
            ...
    """
    decorators = [
        with_retry(max_attempts=max_attempts, exceptions=exceptions),
        with_error_logging(include_traceback=True)
    ]
    
    if log_performance:
        decorators.append(with_performance_logging())
    
    return combine_decorators(*decorators)


# Import asyncio for fallback decorator
import asyncio
