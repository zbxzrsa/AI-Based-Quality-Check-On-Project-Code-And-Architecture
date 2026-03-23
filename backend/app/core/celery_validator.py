"""
Celery Configuration Validator

Validates Celery configuration and verifies broker/backend connectivity.

Validates Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings
from app.core.error_reporter import ErrorReporter

logger = logging.getLogger(__name__)


@dataclass
class CeleryValidationResult:
    """Result of Celery validation"""
    is_valid: bool
    is_enabled: bool
    broker_url: Optional[str] = None
    result_backend: Optional[str] = None
    broker_connected: bool = False
    backend_connected: bool = False
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def __str__(self) -> str:
        """String representation"""
        if not self.is_enabled:
            return "Celery: Disabled (optional)"
        
        status = "✅" if self.is_valid else "❌"
        broker_status = "✅" if self.broker_connected else "❌"
        backend_status = "✅" if self.backend_connected else "❌"
        
        return (
            f"Celery {status}\n"
            f"  Broker: {broker_status}\n"
            f"  Backend: {backend_status}"
        )


class CeleryValidator:
    """
    Validates Celery configuration and connectivity.
    
    Validates:
    - CELERY_BROKER_URL is configured and reachable
    - CELERY_RESULT_BACKEND is configured and reachable
    - Handles Celery disabled gracefully
    - Logs Celery configuration with masking
    
    Validates Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    
    CONNECTION_TIMEOUT = 5
    
    async def validate(self) -> CeleryValidationResult:
        """
        Validate Celery configuration.
        
        Returns:
            CeleryValidationResult with validation status
            
        Validates Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
        """
        logger.info("Validating Celery configuration...")
        
        # Check if Celery is enabled
        if not settings.is_celery_enabled():
            logger.info("Celery is disabled (optional)")
            return CeleryValidationResult(
                is_valid=True,
                is_enabled=False,
                warnings=["Celery is disabled - background tasks will not work"]
            )
        
        # Celery is enabled, validate configuration
        errors = []
        warnings = []
        broker_connected = False
        backend_connected = False
        
        # Validate broker URL
        if not settings.CELERY_BROKER_URL:
            errors.append("CELERY_BROKER_URL is not configured")
        else:
            logger.info(f"Validating Celery broker: {ErrorReporter.mask_connection_string(settings.CELERY_BROKER_URL)}")
            broker_connected = await self._verify_broker()
            if not broker_connected:
                errors.append("Celery broker is not reachable")
        
        # Validate result backend URL
        if not settings.CELERY_RESULT_BACKEND:
            errors.append("CELERY_RESULT_BACKEND is not configured")
        else:
            logger.info(f"Validating Celery result backend: {ErrorReporter.mask_connection_string(settings.CELERY_RESULT_BACKEND)}")
            backend_connected = await self._verify_backend()
            if not backend_connected:
                errors.append("Celery result backend is not reachable")
        
        is_valid = len(errors) == 0
        
        result = CeleryValidationResult(
            is_valid=is_valid,
            is_enabled=True,
            broker_url=ErrorReporter.mask_connection_string(settings.CELERY_BROKER_URL or ""),
            result_backend=ErrorReporter.mask_connection_string(settings.CELERY_RESULT_BACKEND or ""),
            broker_connected=broker_connected,
            backend_connected=backend_connected,
            errors=errors,
            warnings=warnings,
        )
        
        if is_valid:
            logger.info("Celery configuration is valid")
        else:
            logger.error(f"Celery validation failed: {', '.join(errors)}")
        
        return result
    
    async def _verify_broker(self) -> bool:
        """
        Verify Celery broker connectivity.
        
        Returns:
            True if broker is reachable, False otherwise
            
        Validates Requirement: 8.1
        """
        try:
            if not settings.CELERY_BROKER_URL:
                return False
            
            # Try to connect to the broker
            if settings.CELERY_BROKER_URL.startswith("redis://"):
                return await self._verify_redis_broker()
            elif settings.CELERY_BROKER_URL.startswith("amqp://"):
                return await self._verify_amqp_broker()
            else:
                logger.warning(f"Unknown broker type: {settings.CELERY_BROKER_URL}")
                return False
        
        except Exception as e:
            logger.error(f"Broker verification failed: {e}")
            return False
    
    async def _verify_backend(self) -> bool:
        """
        Verify Celery result backend connectivity.
        
        Returns:
            True if backend is reachable, False otherwise
            
        Validates Requirement: 8.2
        """
        try:
            if not settings.CELERY_RESULT_BACKEND:
                return False
            
            # Try to connect to the backend
            if settings.CELERY_RESULT_BACKEND.startswith("redis://"):
                return await self._verify_redis_backend()
            elif settings.CELERY_RESULT_BACKEND.startswith("db+"):
                return await self._verify_db_backend()
            else:
                logger.warning(f"Unknown backend type: {settings.CELERY_RESULT_BACKEND}")
                return False
        
        except Exception as e:
            logger.error(f"Backend verification failed: {e}")
            return False
    
    async def _verify_redis_broker(self) -> bool:
        """Verify Redis broker connectivity"""
        try:
            import redis
            
            # Parse Redis URL
            url = settings.CELERY_BROKER_URL
            # Format: redis://[:password]@host:port/db
            
            redis_client = redis.Redis.from_url(
                url,
                socket_connect_timeout=self.CONNECTION_TIMEOUT,
                socket_timeout=self.CONNECTION_TIMEOUT,
                decode_responses=True
            )
            
            redis_client.ping()
            redis_client.close()
            
            logger.info("Celery Redis broker is reachable")
            return True
        
        except Exception as e:
            logger.error(f"Celery Redis broker verification failed: {e}")
            return False
    
    async def _verify_redis_backend(self) -> bool:
        """Verify Redis result backend connectivity"""
        try:
            
            # Parse Redis URL
            url = settings.CELERY_RESULT_BACKEND
            # Format: redis://[:password]@host:port/db
            
            redis_client = redis.Redis.from_url(
                url,
                socket_connect_timeout=self.CONNECTION_TIMEOUT,
                socket_timeout=self.CONNECTION_TIMEOUT,
                decode_responses=True
            )
            
            redis_client.ping()
            redis_client.close()
            
            logger.info("Celery Redis result backend is reachable")
            return True
        
        except Exception as e:
            logger.error(f"Celery Redis result backend verification failed: {e}")
            return False
    
    async def _verify_amqp_broker(self) -> bool:
        """Verify AMQP broker connectivity"""
        try:
            import pika
            
            # Parse AMQP URL
            url = settings.CELERY_BROKER_URL
            # Format: amqp://user:password@host:port/vhost
            
            connection = pika.BlockingConnection(
                pika.URLParameters(url)
            )
            connection.close()
            
            logger.info("Celery AMQP broker is reachable")
            return True
        
        except Exception as e:
            logger.error(f"Celery AMQP broker verification failed: {e}")
            return False
    
    async def _verify_db_backend(self) -> bool:
        """Verify database result backend connectivity"""
        try:
            from sqlalchemy import create_engine, text
            
            # Parse database URL
            url = settings.CELERY_RESULT_BACKEND
            
            engine = create_engine(
                url,
                connect_args={"timeout": self.CONNECTION_TIMEOUT},
                echo=False
            )
            
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.commit()
            
            engine.dispose()
            
            logger.info("Celery database result backend is reachable")
            return True
        
        except Exception as e:
            logger.error(f"Celery database result backend verification failed: {e}")
            return False


# Global Celery validator instance
_celery_validator: Optional[CeleryValidator] = None


def get_celery_validator() -> CeleryValidator:
    """Get or create Celery validator instance"""
    global _celery_validator
    if _celery_validator is None:
        _celery_validator = CeleryValidator()
    return _celery_validator
