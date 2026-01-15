"""
Retry utilities for handling transient failures in external API calls.
"""
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar
from functools import wraps
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff."""
        import random
        
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Add random jitter (±25%)
            delay = delay * (0.75 + random.random() * 0.5)
        
        return delay


def retry_async(
    config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        config: Retry configuration
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    
    Example:
        @retry_async(config=RetryConfig(max_attempts=3))
        async def fetch_data():
            # API call that might fail
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts",
                            extra={
                                'function': func.__name__,
                                'attempts': config.max_attempts,
                                'error': str(e)
                            },
                            exc_info=True
                        )
                        raise
                    
                    # Calculate delay and wait
                    delay = config.get_delay(attempt)
                    
                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {delay:.2f}s",
                        extra={
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'max_attempts': config.max_attempts,
                            'delay': delay,
                            'error': str(e)
                        }
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e)
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_sync(
    config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying synchronous functions with exponential backoff.
    
    Similar to retry_async but for sync functions.
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts",
                            extra={
                                'function': func.__name__,
                                'attempts': config.max_attempts,
                                'error': str(e)
                            },
                            exc_info=True
                        )
                        raise
                    
                    delay = config.get_delay(attempt)
                    
                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {delay:.2f}s",
                        extra={
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'max_attempts': config.max_attempts,
                            'delay': delay,
                            'error': str(e)
                        }
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# Circuit breaker pattern
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info(f"Circuit breaker recovered, state: CLOSED")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures",
                extra={'failure_count': self.failure_count}
            )
