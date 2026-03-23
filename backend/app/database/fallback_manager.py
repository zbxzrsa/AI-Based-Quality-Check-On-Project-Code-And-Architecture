"""
Database Fallback Manager

Provides intelligent fallback mechanisms for database connections,
graceful degradation, and service recovery strategies.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable, TypeVar
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceState(Enum):
    """Service state enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RECOVERING = "recovering"


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior"""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_retry_delay: float = 30.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    health_check_interval: float = 30.0
    enable_caching: bool = True
    cache_ttl: float = 300.0  # 5 minutes


@dataclass
class ServiceHealth:
    """Health information for a service"""
    name: str
    state: ServiceState = ServiceState.UNAVAILABLE
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    error_message: Optional[str] = None
    response_time_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        return self.consecutive_failures >= 5  # Configurable threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'state': self.state.value,
            'last_success': self.last_success,
            'last_failure': self.last_failure,
            'consecutive_failures': self.consecutive_failures,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'success_rate': round(self.success_rate, 2),
            'error_message': self.error_message,
            'response_time_ms': self.response_time_ms,
            'is_circuit_open': self.is_circuit_open
        }


class FallbackCache:
    """Simple in-memory cache for fallback data"""
    
    def __init__(self, default_ttl: float = 300.0):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() - entry['timestamp'] > entry['ttl']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set cached value with TTL"""
        self._cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl or self.default_ttl
        }
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for entry in self._cache.values():
            if current_time - entry['timestamp'] <= entry['ttl']:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_size_bytes': len(json.dumps(self._cache, default=str))
        }


class DatabaseFallbackManager:
    """
    Manages database connection fallbacks and graceful degradation
    """
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.services: Dict[str, ServiceHealth] = {}
        self.cache = FallbackCache(self.config.cache_ttl)
        self.fallback_handlers: Dict[str, Callable] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
    
    def register_service(self, name: str, health_check: Optional[Callable] = None) -> None:
        """Register a service for fallback management"""
        self.services[name] = ServiceHealth(name=name)
        
        if health_check:
            self.fallback_handlers[name] = health_check
        
        logger.info(f"Registered service '{name}' for fallback management")
    
    def register_fallback_handler(self, service: str, handler: Callable) -> None:
        """Register a fallback handler for a service"""
        self.fallback_handlers[service] = handler
        logger.info(f"Registered fallback handler for service '{service}'")
    
    async def start_monitoring(self) -> None:
        """Start background health monitoring"""
        if self._running:
            return
        
        self._running = True
        self._health_check_task = asyncio.create_task(
            self._health_monitor_loop(),
            name="fallback_health_monitor"
        )
        logger.info("Started fallback health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background health monitoring"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped fallback health monitoring")
    
    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop"""
        while self._running:
            try:
                await self._check_all_services_health()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _check_all_services_health(self) -> None:
        """Check health of all registered services"""
        for service_name, health_check in self.fallback_handlers.items():
            try:
                await self._check_service_health(service_name, health_check)
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                self._record_failure(service_name, str(e))
    
    async def _check_service_health(self, service_name: str, health_check: Callable) -> None:
        """Check health of a specific service"""
        start_time = time.time()
        
        try:
            # Execute health check with timeout
            result = await asyncio.wait_for(health_check(), timeout=10.0)
            
            response_time = (time.time() - start_time) * 1000
            
            if result:
                self._record_success(service_name, response_time)
            else:
                self._record_failure(service_name, "Health check returned False")
                
        except asyncio.TimeoutError:
            self._record_failure(service_name, "Health check timeout")
        except Exception as e:
            self._record_failure(service_name, str(e))
    
    def _record_success(self, service_name: str, response_time: float) -> None:
        """Record successful service interaction"""
        if service_name not in self.services:
            self.services[service_name] = ServiceHealth(name=service_name)
        
        health = self.services[service_name]
        health.last_success = time.time()
        health.consecutive_failures = 0
        health.total_requests += 1
        health.successful_requests += 1
        health.response_time_ms = response_time
        health.error_message = None
        
        # Update state based on performance
        if response_time < 100:  # Fast response
            health.state = ServiceState.HEALTHY
        elif response_time < 1000:  # Acceptable response
            health.state = ServiceState.HEALTHY
        else:  # Slow response
            health.state = ServiceState.DEGRADED
        
        logger.debug(f"Service {service_name} success: {response_time:.1f}ms")
    
    def _record_failure(self, service_name: str, error_message: str) -> None:
        """Record failed service interaction"""
        if service_name not in self.services:
            self.services[service_name] = ServiceHealth(name=service_name)
        
        health = self.services[service_name]
        health.last_failure = time.time()
        health.consecutive_failures += 1
        health.total_requests += 1
        health.error_message = error_message
        
        # Update state based on failure count
        if health.consecutive_failures >= self.config.circuit_breaker_threshold:
            health.state = ServiceState.UNAVAILABLE
        else:
            health.state = ServiceState.DEGRADED
        
        logger.warning(f"Service {service_name} failure: {error_message}")
    
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_operation: Callable[[], T],
        fallback_operation: Optional[Callable[[], T]] = None,
        cache_key: Optional[str] = None
    ) -> T:
        """
        Execute operation with fallback and caching support
        
        Args:
            service_name: Name of the service
            primary_operation: Primary operation to execute
            fallback_operation: Fallback operation if primary fails
            cache_key: Optional cache key for result caching
            
        Returns:
            Result from primary or fallback operation
            
        Raises:
            Exception: If both primary and fallback operations fail
        """
        # Check if service is available
        if not self.is_service_available(service_name):
            logger.warning(f"Service {service_name} unavailable, trying fallback")
            return await self._execute_fallback(
                service_name, fallback_operation, cache_key
            )
        
        # Try primary operation with retry logic
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                result = await primary_operation()
                
                response_time = (time.time() - start_time) * 1000
                self._record_success(service_name, response_time)
                
                # Cache successful result
                if cache_key and self.config.enable_caching:
                    self.cache.set(cache_key, result)
                
                return result
                
            except Exception as e:
                self._record_failure(service_name, str(e))
                
                if attempt < self.config.max_retries:
                    # Calculate retry delay with exponential backoff
                    delay = min(
                        self.config.retry_delay * (self.config.backoff_multiplier ** attempt),
                        self.config.max_retry_delay
                    )
                    logger.warning(
                        f"Service {service_name} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Service {service_name} failed after {attempt + 1} attempts")
                    break
        
        # Primary operation failed, try fallback
        return await self._execute_fallback(service_name, fallback_operation, cache_key)
    
    async def _execute_fallback(
        self,
        service_name: str,
        fallback_operation: Optional[Callable[[], T]],
        cache_key: Optional[str]
    ) -> T:
        """Execute fallback operation or return cached data"""
        
        # Try cached data first
        if cache_key and self.config.enable_caching:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached data for {service_name}")
                return cached_result
        
        # Try fallback operation
        if fallback_operation:
            try:
                logger.info(f"Executing fallback for {service_name}")
                result = await fallback_operation()
                
                # Cache fallback result
                if cache_key and self.config.enable_caching:
                    self.cache.set(cache_key, result, ttl=60.0)  # Shorter TTL for fallback data
                
                return result
                
            except Exception as e:
                logger.error(f"Fallback operation failed for {service_name}: {e}")
        
        # No fallback available
        raise RuntimeError(
            f"Service {service_name} unavailable and no fallback configured"
        )
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is currently available"""
        if service_name not in self.services:
            return True  # Assume available if not monitored
        
        health = self.services[service_name]
        
        # Check circuit breaker
        if health.is_circuit_open:
            # Check if circuit breaker timeout has passed
            if health.last_failure:
                time_since_failure = time.time() - health.last_failure
                if time_since_failure > self.config.circuit_breaker_timeout:
                    # Reset circuit breaker
                    health.consecutive_failures = 0
                    health.state = ServiceState.RECOVERING
                    logger.info(f"Circuit breaker reset for {service_name}")
                    return True
            return False
        
        return health.state in [ServiceState.HEALTHY, ServiceState.DEGRADED, ServiceState.RECOVERING]
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Get health information for a service"""
        return self.services.get(service_name)
    
    def get_all_services_health(self) -> Dict[str, ServiceHealth]:
        """Get health information for all services"""
        return self.services.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        total_services = len(self.services)
        healthy_services = sum(
            1 for health in self.services.values()
            if health.state == ServiceState.HEALTHY
        )
        degraded_services = sum(
            1 for health in self.services.values()
            if health.state == ServiceState.DEGRADED
        )
        unavailable_services = sum(
            1 for health in self.services.values()
            if health.state == ServiceState.UNAVAILABLE
        )
        
        # Calculate overall system health
        if unavailable_services == 0:
            if degraded_services == 0:
                overall_status = "healthy"
            else:
                overall_status = "degraded"
        else:
            if healthy_services + degraded_services > unavailable_services:
                overall_status = "degraded"
            else:
                overall_status = "unhealthy"
        
        return {
            "overall_status": overall_status,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "unavailable_services": unavailable_services,
            "services": {
                name: health.to_dict()
                for name, health in self.services.items()
            },
            "cache_stats": self.cache.get_stats(),
            "monitoring_active": self._running
        }
    
    @asynccontextmanager
    async def service_context(self, service_name: str):
        """Context manager for service operations with automatic health tracking"""
        start_time = time.time()
        
        try:
            yield
            # Success
            response_time = (time.time() - start_time) * 1000
            self._record_success(service_name, response_time)
            
        except Exception as e:
            # Failure
            self._record_failure(service_name, str(e))
            raise
    
    async def reset_service_health(self, service_name: str) -> None:
        """Reset health status for a service"""
        if service_name in self.services:
            health = self.services[service_name]
            health.consecutive_failures = 0
            health.state = ServiceState.RECOVERING
            health.error_message = None
            logger.info(f"Reset health status for service {service_name}")
    
    async def force_service_recovery(self, service_name: str) -> None:
        """Force a service into recovery mode"""
        if service_name in self.services:
            health = self.services[service_name]
            health.consecutive_failures = 0
            health.state = ServiceState.RECOVERING
            health.error_message = None
            logger.info(f"Forced recovery for service {service_name}")


# Global fallback manager instance
fallback_manager = DatabaseFallbackManager()


# Convenience functions
async def execute_with_fallback(
    service_name: str,
    primary_operation: Callable[[], T],
    fallback_operation: Optional[Callable[[], T]] = None,
    cache_key: Optional[str] = None
) -> T:
    """Convenience function for executing operations with fallback"""
    return await fallback_manager.execute_with_fallback(
        service_name, primary_operation, fallback_operation, cache_key
    )


def register_service_fallback(service_name: str, health_check: Optional[Callable] = None) -> None:
    """Convenience function for registering service fallbacks"""
    fallback_manager.register_service(service_name, health_check)


async def start_fallback_monitoring() -> None:
    """Start fallback monitoring"""
    await fallback_manager.start_monitoring()


async def stop_fallback_monitoring() -> None:
    """Stop fallback monitoring"""
    await fallback_manager.stop_monitoring()