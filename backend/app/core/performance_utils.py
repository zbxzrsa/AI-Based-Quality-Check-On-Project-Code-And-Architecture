"""
Performance Optimization Utilities

This module provides performance optimization utilities for the application.
"""

import functools
import time
from collections.abc import Callable
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter.

    Usage:
        limiter = RateLimiter(max_calls=100, period=60)

        @limiter
        async def my_function():
            ...
    """

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self._calls: list = []

    def _clean_old_calls(self) -> None:
        """Remove calls outside the current period"""
        cutoff = time.time() - self.period
        self._calls = [call_time for call_time in self._calls if call_time > cutoff]

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            self._clean_old_calls()
            if len(self._calls) >= self.max_calls:
                wait_time = self.period - (time.time() - self._calls[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit exceeded, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    self._clean_old_calls()
            self._calls.append(time.time())
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            self._clean_old_calls()
            if len(self._calls) >= self.max_calls:
                wait_time = self.period - (time.time() - self._calls[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit exceeded, waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    self._clean_old_calls()
            self._calls.append(time.time())
            return func(*args, **kwargs)

        if functools.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


class Cache:
    """
    Simple in-memory cache with TTL support.

    Usage:
        cache = Cache(ttl=300)

        @cache
        async def fetch_data(key):
            return await expensive_operation(key)
    """

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._cache: dict = {}

    def _is_expired(self, entry: dict) -> bool:
        """Check if cache entry is expired"""
        return time.time() - entry["timestamp"] > self.ttl

    def get(self, key: str) -> Any | None:
        """Get value from cache"""
        if key in self._cache:
            entry = self._cache[key]
            if not self._is_expired(entry):
                return entry["value"]
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        self._cache[key] = {
            "value": value,
            "timestamp": time.time(),
        }

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            cached = self.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            self.set(cache_key, result)
            logger.debug(f"Cache miss: {cache_key}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            cached = self.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            result = func(*args, **kwargs)
            self.set(cache_key, result)
            logger.debug(f"Cache miss: {cache_key}")

            return result

        if functools.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


def timing(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.

    Usage:
        @timing
        async def my_function():
            ...
    """

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} took {elapsed:.3f}s")
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} took {elapsed:.3f}s")
        return result

    if functools.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry failed function calls.

    Usage:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        async def unstable_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {current_delay}s: {e}"
                        )
                        import asyncio

                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts")

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {current_delay}s: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts")

            raise last_exception

        if functools.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        @breaker
        async def unstable_function():
            ...
    """

    def __init__(self, failure_threshold: int = 5, timeout: float = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self._failures = 0
        self._last_failure_time: float | None = None
        self._state = "closed"  # closed, open, half-open

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self._state == "closed":
            return True

        if self._state == "open":
            if time.time() - self._last_failure_time > self.timeout:
                self._state = "half-open"
                return True
            return False

        return True  # half-open

    def _record_success(self) -> None:
        """Record successful call"""
        self._failures = 0
        self._state = "closed"

    def _record_failure(self) -> None:
        """Record failed call"""
        self._failures += 1
        self._last_failure_time = time.time()

        if self._failures >= self.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker opened after {self._failures} failures")

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self._should_allow_request():
                raise RuntimeError("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                self._record_success()
                return result
            except Exception:
                self._record_failure()
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self._should_allow_request():
                raise RuntimeError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception:
                self._record_failure()
                raise

        if functools.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


# Global instances for common use cases
default_cache = Cache(ttl=300)
default_rate_limiter = RateLimiter(max_calls=100, period=60)
default_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)


import asyncio
