"""
Health Check Service

Provides comprehensive health status of the application and all dependencies.
Implements Kubernetes-style probes (liveness, readiness).

Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

import logging
import time
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Optional
from enum import Enum

from app.core.config import settings
from app.database.connection_manager import get_connection_manager
from app.core.prometheus_metrics import (
    record_health_check,
    set_dependency_status
)

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status values"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class DatabaseHealth:
    """Health status of a database"""
    name: str
    is_connected: bool
    response_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class ServiceHealth:
    """Health status of a service"""
    name: str
    is_available: bool
    error: Optional[str] = None


@dataclass
class HealthCheckResponse:
    """Response from health check endpoint"""
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str
    timestamp: str
    databases: Dict[str, DatabaseHealth]
    services: Dict[str, ServiceHealth]
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "status": self.status,
            "version": self.version,
            "environment": self.environment,
            "timestamp": self.timestamp,
            "databases": {
                name: asdict(db) for name, db in self.databases.items()
            },
            "services": {
                name: asdict(svc) for name, svc in self.services.items()
            },
        }


@dataclass
class ReadinessCheckResponse:
    """Response from readiness check endpoint"""
    ready: bool
    reason: str
    timestamp: str
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "ready": self.ready,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class LivenessCheckResponse:
    """Response from liveness check endpoint"""
    alive: bool
    timestamp: str
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "alive": self.alive,
            "timestamp": self.timestamp,
        }


class HealthService:
    """
    Service for checking application and dependency health.
    
    Provides:
    - Overall health status (healthy, degraded, unhealthy)
    - Readiness probe (all required dependencies ready)
    - Liveness probe (process running)
    - Detailed database and service status
    
    Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
    """
    
    def __init__(self):
        """Initialize health service"""
        self.connection_manager = get_connection_manager()
    
    async def get_health_status(self) -> HealthCheckResponse:
        """
        Get overall health status of the application.
        Enhanced to include response times for each dependency.
        
        Returns:
            HealthCheckResponse with status and details including response times
            
        Validates Requirements: 12.1, 12.2, 12.3, 12.4, 4.1, 4.4, 4.5
        """
        logger.info("Checking application health...")
        start_time = time.time()
        
        # Check database connections with timeout protection
        try:
            db_status = await asyncio.wait_for(
                self.connection_manager.verify_all(), 
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.warning("Database health check timeout")
            db_status = {}
        except Exception as e:
            logger.error("Database health check failed: %s", str(e))
            db_status = {}
        
        databases = {}
        postgres_connected = False
        any_connected = False
        
        # Always include PostgreSQL status (critical)
        postgres_status = None
        if "PostgreSQL" in db_status:
            postgres_status = db_status["PostgreSQL"]
            databases["PostgreSQL"] = DatabaseHealth(
                name="PostgreSQL",
                is_connected=postgres_status.is_connected,
                response_time_ms=postgres_status.response_time_ms,
                error=postgres_status.error
            )
            postgres_connected = postgres_status.is_connected
            if postgres_connected:
                any_connected = True
        else:
            databases["PostgreSQL"] = DatabaseHealth(
                name="PostgreSQL",
                is_connected=False,
                error="Health check timeout or unavailable"
            )
        
        # Optional services (Neo4j, Redis) - don't affect critical status
        for service_name in ["Neo4j", "Redis"]:
            if service_name in db_status:
                status = db_status[service_name]
                databases[service_name] = DatabaseHealth(
                    name=service_name,
                    is_connected=status.is_connected,
                    response_time_ms=status.response_time_ms,
                    error=status.error
                )
                if status.is_connected:
                    any_connected = True
                    
                # Record dependency status metric
                set_dependency_status(service_name, status.is_connected)
            else:
                databases[service_name] = DatabaseHealth(
                    name=service_name,
                    is_connected=False,
                    error="Service unavailable"
                )
                # Record dependency status metric
                set_dependency_status(service_name, False)
        
        # Check services
        services = {}
        
        # Check Celery if enabled
        if settings.is_celery_enabled():
            celery_available = await self._check_celery_health()
            services["Celery"] = ServiceHealth(
                name="Celery",
                is_available=celery_available,
                error=None if celery_available else "Celery broker unavailable"
            )
            set_dependency_status("Celery", celery_available)
        
        # Check LLM service if enabled
        if settings.LLM_ENABLED:
            llm_available = await self._check_llm_health()
            services["LLM"] = ServiceHealth(
                name="LLM",
                is_available=llm_available,
                error=None if llm_available else "LLM service unavailable"
            )
            set_dependency_status("LLM", llm_available)
        
        # Determine overall health status
        # 只要PostgreSQL连接成功，就认为是健康的（Redis和Neo4j是可选的）
        if postgres_connected:
            health_status = HealthStatus.HEALTHY
        elif any_connected:
            health_status = HealthStatus.DEGRADED
        else:
            health_status = HealthStatus.UNHEALTHY
        
        response = HealthCheckResponse(
            status=health_status.value,
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            databases=databases,
            services=services,
        )
        
        # Record health check duration
        duration = time.time() - start_time
        record_health_check('health', duration)
        
        logger.info(f"Health check: {health_status.value}")
        return response
    
    async def get_readiness_status(self) -> ReadinessCheckResponse:
        """
        Get readiness status (Kubernetes readiness probe).
        Enhanced to check PostgreSQL and migrations.
        
        Returns 200 only if all required dependencies are ready:
        - PostgreSQL connected
        - Migrations applied
        
        Returns:
            ReadinessCheckResponse with ready status
            
        Validates Requirements: 12.5, 4.2
        """
        logger.info("Checking readiness...")
        start_time = time.time()
        
        # Check PostgreSQL connection
        postgres_status = await self.connection_manager.verify_postgres()
        
        if not postgres_status.is_connected:
            error_msg = postgres_status.error or "PostgreSQL not connected"
            response = ReadinessCheckResponse(
                ready=False,
                reason=f"PostgreSQL not connected: {error_msg}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            logger.warning(f"Not ready: PostgreSQL not connected - {error_msg}")
            
            # Record readiness check duration
            duration = time.time() - start_time
            record_health_check('readiness', duration)
            
            return response
        
        # Check migrations (if available)
        try:
            from app.database.migration_manager import get_migration_manager
            migration_manager = get_migration_manager()
            migration_status = await migration_manager.get_migration_status()
            
            if migration_status.pending_count > 0:
                response = ReadinessCheckResponse(
                    ready=False,
                    reason=f"{migration_status.pending_count} pending migrations",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                logger.warning(f"Not ready: {migration_status.pending_count} pending migrations")
                
                # Record readiness check duration
                duration = time.time() - start_time
                record_health_check('readiness', duration)
                
                return response
        except Exception as e:
            logger.warning(f"Could not check migration status: {e}")
            # Don't fail readiness if we can't check migrations
        
        response = ReadinessCheckResponse(
            ready=True,
            reason="All required dependencies ready",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Record readiness check duration
        duration = time.time() - start_time
        record_health_check('readiness', duration)
        
        logger.info("Ready")
        return response
    
    async def get_liveness_status(self) -> LivenessCheckResponse:
        """
        Get liveness status (Kubernetes liveness probe).
        
        Returns 200 if the application process is running.
        This is a simple check that doesn't verify dependencies.
        
        Returns:
            LivenessCheckResponse with alive status
            
        Validates Requirements: 12.6, 4.3
        """
        logger.info("Checking liveness...")
        start_time = time.time()
        
        response = LivenessCheckResponse(
            alive=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Record liveness check duration
        duration = time.time() - start_time
        record_health_check('liveness', duration)
        
        logger.info("Alive")
        return response
    
    async def check_postgres(self) -> DatabaseHealth:
        """
        Check PostgreSQL database health.
        
        Returns:
            DatabaseHealth with PostgreSQL connection status and response time
            
        Validates Requirements: 2.6, 7.5
        """
        logger.info("Checking PostgreSQL health...")
        status = await self.connection_manager.verify_postgres()
        
        return DatabaseHealth(
            name="PostgreSQL",
            is_connected=status.is_connected,
            response_time_ms=status.response_time_ms,
            error=status.error
        )
    
    async def check_neo4j(self) -> DatabaseHealth:
        """
        Check Neo4j database health.
        
        Returns:
            DatabaseHealth with Neo4j connection status and response time
            
        Validates Requirements: 2.6, 7.5
        """
        logger.info("Checking Neo4j health...")
        status = await self.connection_manager.verify_neo4j()
        
        return DatabaseHealth(
            name="Neo4j",
            is_connected=status.is_connected,
            response_time_ms=status.response_time_ms,
            error=status.error
        )
    
    async def check_redis(self) -> DatabaseHealth:
        """
        Check Redis database health.
        
        Returns:
            DatabaseHealth with Redis connection status and response time
            
        Validates Requirements: 2.6, 7.5
        """
        logger.info("Checking Redis health...")
        status = await self.connection_manager.verify_redis()
        
        return DatabaseHealth(
            name="Redis",
            is_connected=status.is_connected,
            response_time_ms=status.response_time_ms,
            error=status.error
        )
    
    async def check_dependency(self, name: str) -> DatabaseHealth:
        """
        Check individual dependency health.
        
        Args:
            name: Name of the dependency to check (PostgreSQL, Neo4j, Redis, Celery, LLM)
            
        Returns:
            DatabaseHealth or ServiceHealth with dependency status
            
        Raises:
            ValueError: If dependency name is not recognized
            
        Validates Requirements: 4.1, 4.4, 4.5
        """
        logger.info(f"Checking dependency: {name}")
        start_time = time.time()
        
        result = None
        
        # Check database dependencies
        if name == "PostgreSQL":
            result = await self.check_postgres()
        elif name == "Neo4j":
            result = await self.check_neo4j()
        elif name == "Redis":
            result = await self.check_redis()
        
        # Check service dependencies
        elif name == "Celery":
            if not settings.is_celery_enabled():
                result = DatabaseHealth(
                    name=name,
                    is_connected=False,
                    response_time_ms=0.0,
                    error="Celery is not enabled"
                )
            else:
                celery_available = await self._check_celery_health()
                result = DatabaseHealth(
                    name=name,
                    is_connected=celery_available,
                    response_time_ms=0.0,
                    error=None if celery_available else "Celery broker unavailable"
                )
        
        elif name == "LLM":
            if not settings.LLM_ENABLED:
                result = DatabaseHealth(
                    name=name,
                    is_connected=False,
                    response_time_ms=0.0,
                    error="LLM service is not enabled"
                )
            else:
                llm_available = await self._check_llm_health()
                result = DatabaseHealth(
                    name=name,
                    is_connected=llm_available,
                    response_time_ms=0.0,
                    error=None if llm_available else "LLM service unavailable"
                )
        
        else:
            raise ValueError(f"Unknown dependency: {name}")
        
        # Record dependency check duration and status
        duration = time.time() - start_time
        record_health_check('dependency', duration)
        set_dependency_status(name, result.is_connected)
        
        return result
    
    async def _check_celery_health(self) -> bool:
        """
        Check if Celery is healthy.
        
        Returns:
            True if Celery is available, False otherwise
        """
        try:
            from app.celery_config import celery_app
            
            # Try to ping the Celery broker
            result = celery_app.control.inspect().ping()
            return result is not None and len(result) > 0
        except Exception as e:
            logger.warning(f"Celery health check failed: {e}")
            return False
    
    async def _check_llm_health(self) -> bool:
        """
        Check if LLM service is healthy.
        
        Returns:
            True if LLM service is available, False otherwise
        """
        try:
            from app.services.llm_service import llm_service
            
            # Check if LLM service is initialized
            return llm_service.is_initialized()
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False


# Global health service instance
_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    """Get or create health service instance"""
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
