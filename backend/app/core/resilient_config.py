"""
Resilient Configuration Manager

Enhanced configuration with graceful degradation, automatic fallbacks,
and intelligent service discovery for improved reliability.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from pydantic import BaseSettings, Field
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration with health checking"""
    host: str
    port: int
    protocol: str = "tcp"
    timeout: float = 5.0
    required: bool = True
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"
    
    async def is_available(self) -> bool:
        """Check if service endpoint is available"""
        try:
            if self.protocol == "tcp":
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout
                )
                writer.close()
                await writer.wait_closed()
                return True
            elif self.protocol == "http":
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://{self.host}:{self.port}",
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        return response.status < 500
        except Exception as e:
            logger.debug(f"Service {self.address} not available: {e}")
            return False


class ResilientSettings(BaseSettings):
    """
    Resilient settings with automatic service discovery and fallbacks
    """
    
    # Application settings
    PROJECT_NAME: str = "AI Code Review Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security settings with fallbacks
    JWT_SECRET: str = Field(default="dev-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Database settings with service discovery
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="ai_code_review")
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    
    NEO4J_URI: str = Field(default="neo4j://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="neo4j")
    NEO4J_DATABASE: str = Field(default="neo4j")
    
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_DB: int = Field(default=0)
    
    # Service discovery settings
    ENABLE_SERVICE_DISCOVERY: bool = Field(default=True)
    SERVICE_DISCOVERY_TIMEOUT: float = Field(default=10.0)
    
    # Graceful degradation settings
    ALLOW_DEGRADED_MODE: bool = Field(default=True)
    REQUIRED_SERVICES: List[str] = Field(default=["postgresql"])
    OPTIONAL_SERVICES: List[str] = Field(default=["neo4j", "redis"])
    
    # Performance settings
    CONNECTION_POOL_SIZE: int = Field(default=20)
    CONNECTION_TIMEOUT: float = Field(default=30.0)
    QUERY_TIMEOUT: float = Field(default=30.0)
    
    # Logging and monitoring
    LOG_LEVEL: str = Field(default="INFO")
    ENABLE_METRICS: bool = Field(default=True)
    METRICS_PORT: int = Field(default=9090)
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service_endpoints = self._discover_services()
        self._available_services = {}
    
    def _discover_services(self) -> Dict[str, ServiceEndpoint]:
        """Discover available services"""
        endpoints = {
            "postgresql": ServiceEndpoint(
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                required=True
            ),
            "neo4j": ServiceEndpoint(
                host=self.NEO4J_URI.split("://")[1].split(":")[0] if "://" in self.NEO4J_URI else "localhost",
                port=7687,
                required=False
            ),
            "redis": ServiceEndpoint(
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                required=False
            )
        }
        
        # Check for Docker containers
        if self._is_docker_available():
            docker_endpoints = self._discover_docker_services()
            endpoints.update(docker_endpoints)
        
        return endpoints
    
    def _is_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _discover_docker_services(self) -> Dict[str, ServiceEndpoint]:
        """Discover services running in Docker containers"""
        docker_endpoints = {}
        
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '\t' in line:
                        name, ports = line.split('\t', 1)
                        
                        # Parse PostgreSQL containers
                        if 'postgres' in name.lower() and '5432' in ports:
                            docker_endpoints["postgresql"] = ServiceEndpoint(
                                host="localhost",
                                port=5432,
                                required=True
                            )
                        
                        # Parse Redis containers
                        if 'redis' in name.lower() and '6379' in ports:
                            docker_endpoints["redis"] = ServiceEndpoint(
                                host="localhost",
                                port=6379,
                                required=False
                            )
                        
                        # Parse Neo4j containers
                        if 'neo4j' in name.lower() and '7687' in ports:
                            docker_endpoints["neo4j"] = ServiceEndpoint(
                                host="localhost",
                                port=7687,
                                required=False
                            )
        
        except Exception as e:
            logger.debug(f"Docker service discovery failed: {e}")
        
        return docker_endpoints
    
    async def check_service_availability(self) -> Dict[str, bool]:
        """Check availability of all configured services"""
        if not self.ENABLE_SERVICE_DISCOVERY:
            return {}
        
        availability = {}
        
        # Check all service endpoints concurrently
        tasks = []
        for service_name, endpoint in self._service_endpoints.items():
            task = asyncio.create_task(
                self._check_service_with_timeout(service_name, endpoint),
                name=f"check_{service_name}"
            )
            tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.SERVICE_DISCOVERY_TIMEOUT
            )
            
            for i, (service_name, _) in enumerate(self._service_endpoints.items()):
                result = results[i]
                if isinstance(result, Exception):
                    availability[service_name] = False
                    logger.warning(f"Service check failed for {service_name}: {result}")
                else:
                    availability[service_name] = result
        
        except asyncio.TimeoutError:
            logger.warning("Service discovery timeout")
            # Mark all services as unavailable on timeout
            availability = {name: False for name in self._service_endpoints.keys()}
        
        self._available_services = availability
        return availability
    
    async def _check_service_with_timeout(self, service_name: str, endpoint: ServiceEndpoint) -> bool:
        """Check individual service with timeout"""
        try:
            is_available = await endpoint.is_available()
            if is_available:
                logger.info(f"✅ {service_name} service available at {endpoint.address}")
            else:
                logger.warning(f"❌ {service_name} service unavailable at {endpoint.address}")
            return is_available
        except Exception as e:
            logger.warning(f"❌ {service_name} service check failed: {e}")
            return False
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get currently available services"""
        return self._available_services.copy()
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a specific service is available"""
        return self._available_services.get(service_name, False)
    
    def can_start_in_degraded_mode(self) -> bool:
        """Check if application can start in degraded mode"""
        if not self.ALLOW_DEGRADED_MODE:
            return False
        
        # Check if all required services are available
        for service in self.REQUIRED_SERVICES:
            if not self.is_service_available(service):
                logger.warning(f"Required service {service} is not available")
                return False
        
        return True
    
    def get_degraded_mode_info(self) -> Dict[str, Any]:
        """Get information about degraded mode status"""
        available = self.get_available_services()
        
        return {
            "degraded_mode": self.ALLOW_DEGRADED_MODE,
            "can_start": self.can_start_in_degraded_mode(),
            "required_services": {
                service: available.get(service, False) 
                for service in self.REQUIRED_SERVICES
            },
            "optional_services": {
                service: available.get(service, False) 
                for service in self.OPTIONAL_SERVICES
            },
            "total_available": sum(available.values()),
            "total_configured": len(self._service_endpoints)
        }
    
    @property
    def postgres_url(self) -> str:
        """PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def get_connection_config(self, service: str) -> Dict[str, Any]:
        """Get connection configuration for a service"""
        configs = {
            "postgresql": {
                "dsn": self.postgres_url,
                "pool_size": self.CONNECTION_POOL_SIZE,
                "timeout": self.CONNECTION_TIMEOUT,
                "available": self.is_service_available("postgresql")
            },
            "neo4j": {
                "uri": self.NEO4J_URI,
                "user": self.NEO4J_USER,
                "password": self.NEO4J_PASSWORD,
                "database": self.NEO4J_DATABASE,
                "timeout": self.CONNECTION_TIMEOUT,
                "available": self.is_service_available("neo4j")
            },
            "redis": {
                "url": self.redis_url,
                "host": self.REDIS_HOST,
                "port": self.REDIS_PORT,
                "password": self.REDIS_PASSWORD,
                "db": self.REDIS_DB,
                "timeout": self.CONNECTION_TIMEOUT,
                "available": self.is_service_available("redis")
            }
        }
        
        return configs.get(service, {})


# Global resilient settings instance
resilient_settings = ResilientSettings()