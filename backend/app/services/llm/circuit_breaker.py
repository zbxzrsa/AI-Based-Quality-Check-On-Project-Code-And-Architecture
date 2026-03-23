"""
Circuit Breaker Pattern Implementation

Implements circuit breaker pattern for external service calls
to prevent cascading failures.

Validates Requirements: 2.6, 12.5
"""

import logging
import time
# Import consolidated enums from common library
from common.shared.enums import CircuitBreakerState as CircuitState
from typing import Callable, Any, Optional
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: float = 0.5  # 50% failure rate
    success_threshold: int = 2  # Successes needed to close from half-open
    timeout: int = 60  # Seconds before trying half-open
    window_size: int = 10  # Number of recent calls to track


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    
    Tracks failure rates and opens circuit when threshold is exceeded.
    Automatically attempts recovery after timeout period.
    
    Validates Requirements: 2.6, 12.5
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker identifier
            config: Optional configuration (uses defaults if not provided)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.recent_calls: list[bool] = []  # True = success, False = failure
        self._lock = Lock()
        
        logger.info(
            f"Circuit breaker '{name}' initialized",
            extra={
                "circuit_breaker": name,
                "failure_threshold": self.config.failure_threshold,
                "timeout": self.config.timeout
            }
        )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function execution fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function execution fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN"
                    )
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise
    
    def _record_success(self):
        """Record successful call"""
        with self._lock:
            self.recent_calls.append(True)
            if len(self.recent_calls) > self.config.window_size:
                self.recent_calls.pop(0)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            
            logger.debug(
                f"Circuit breaker '{self.name}' recorded success",
                extra={
                    "circuit_breaker": self.name,
                    "state": self.state.value,
                    "success_count": self.success_count
                }
            )
    
    def _record_failure(self):
        """Record failed call"""
        with self._lock:
            self.recent_calls.append(False)
            if len(self.recent_calls) > self.config.window_size:
                self.recent_calls.pop(0)
            
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                # Only check failure rate if we have enough calls
                if self._has_enough_calls():
                    failure_rate = self._calculate_failure_rate()
                    if failure_rate >= self.config.failure_threshold:
                        self._transition_to_open()
            
            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure",
                extra={
                    "circuit_breaker": self.name,
                    "state": self.state.value,
                    "failure_count": self.failure_count,
                    "failure_rate": self._calculate_failure_rate()
                }
            )
    
    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate"""
        if not self.recent_calls:
            return 0.0
        
        failures = sum(1 for success in self.recent_calls if not success)
        return failures / len(self.recent_calls)
    
    def _has_enough_calls(self) -> bool:
        """Check if we have enough calls to calculate failure rate"""
        return len(self.recent_calls) >= self.config.window_size
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.timeout
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.success_count = 0
        
        logger.error(
            f"Circuit breaker '{self.name}' transitioned to OPEN",
            extra={
                "circuit_breaker": self.name,
                "failure_rate": self._calculate_failure_rate(),
                "failure_threshold": self.config.failure_threshold
            }
        )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN",
            extra={"circuit_breaker": self.name}
        )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.recent_calls.clear()
        
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to CLOSED",
            extra={"circuit_breaker": self.name}
        )
    
    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "failure_rate": self._calculate_failure_rate(),
                "recent_calls": len(self.recent_calls)
            }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self._lock:
            self._transition_to_closed()
            logger.info(
                f"Circuit breaker '{self.name}' manually reset",
                extra={"circuit_breaker": self.name}
            )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass
