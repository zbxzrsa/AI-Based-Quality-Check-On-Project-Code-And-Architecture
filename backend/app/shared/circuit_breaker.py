"""
Circuit Breaker implementation for external dependencies

Prevents cascading failures by stopping requests to failing services
and allowing them time to recover.

Validates Requirements: 7.7
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from .exceptions import CircuitBreakerException


logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Open after N failures
    success_threshold: int = 2  # Close after N successes in half-open
    timeout: int = 60  # Seconds before trying half-open
    window_size: int = 300  # Seconds for failure counting
    
    def __post_init__(self):
        """Validate configuration"""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if self.timeout < 1:
            raise ValueError("timeout must be >= 1")
        if self.window_size < 1:
            raise ValueError("window_size must be >= 1")


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    
    Validates Requirements: 7.7
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the service/dependency
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[float] = None
        self.metrics = CircuitBreakerMetrics()
        self._lock = Lock()
        
        logger.info(
            f"Circuit breaker '{name}' initialized",
            extra={
                'circuit_breaker': name,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'success_threshold': self.config.success_threshold,
                    'timeout': self.config.timeout,
                }
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
            Result of function execution
            
        Raises:
            CircuitBreakerException: If circuit is open
            
        Validates Requirements: 7.7
        """
        with self._lock:
            self.metrics.total_calls += 1
            
            # Check if circuit should transition to half-open
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    self.metrics.rejected_calls += 1
                    raise CircuitBreakerException(
                        f"Circuit breaker '{self.name}' is OPEN",
                        service_name=self.name,
                        failure_count=self.failure_count,
                        details={
                            'opened_at': self.opened_at,
                            'timeout': self.config.timeout,
                        }
                    )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.opened_at is None:
            return True
        return time.time() - self.opened_at >= self.config.timeout
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = datetime.utcnow()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state, go back to open
                self._transition_to_open()
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitBreakerState.OPEN
        self.opened_at = time.time()
        self.success_count = 0
        self.metrics.state_changes += 1
        
        logger.warning(
            f"Circuit breaker '{self.name}' transitioned to OPEN",
            extra={
                'circuit_breaker': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'timeout': self.config.timeout,
            }
        )
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        self.metrics.state_changes += 1
        
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN",
            extra={
                'circuit_breaker': self.name,
                'state': self.state.value,
            }
        )
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        self.metrics.state_changes += 1
        
        logger.info(
            f"Circuit breaker '{self.name}' transitioned to CLOSED",
            extra={
                'circuit_breaker': self.name,
                'state': self.state.value,
            }
        )
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        return self.state
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics"""
        return self.metrics
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self._lock:
            self._transition_to_closed()
            logger.info(f"Circuit breaker '{self.name}' manually reset")


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.
    
    Args:
        name: Name of the service/dependency
        config: Optional configuration (only used if creating new breaker)
        
    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def reset_all_circuit_breakers():
    """Reset all circuit breakers (useful for testing)"""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()


def get_all_circuit_breaker_states() -> Dict[str, Dict[str, Any]]:
    """Get states of all circuit breakers"""
    with _registry_lock:
        return {
            name: {
                'state': breaker.get_state().value,
                'failure_count': breaker.failure_count,
                'metrics': {
                    'total_calls': breaker.metrics.total_calls,
                    'successful_calls': breaker.metrics.successful_calls,
                    'failed_calls': breaker.metrics.failed_calls,
                    'rejected_calls': breaker.metrics.rejected_calls,
                }
            }
            for name, breaker in _circuit_breakers.items()
        }
