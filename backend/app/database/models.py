"""
Database connectivity models and configuration classes.

This module defines the core data models for database configuration,
retry policies, health status, and error handling used throughout
the database connectivity fixes.

Validates Requirements: 7.1, 7.2, 7.4, 7.5
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ========================================
# Configuration Models
# ========================================

@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on_timeout: bool = True
    retry_on_auth_failure: bool = True
    
    def __post_init__(self):
        """Validate retry configuration parameters"""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.backoff_multiplier <= 1:
            raise ValueError("backoff_multiplier must be greater than 1")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")


@dataclass
class DatabaseConfig:
    """Configuration for database connections and pooling"""
    postgresql_dsn: str
    neo4j_uri: str
    neo4j_auth: Tuple[str, str]
    connection_timeout: int = 30
    pool_min_size: int = 5
    pool_max_size: int = 20
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    
    def __post_init__(self):
        """Validate database configuration parameters"""
        if not self.postgresql_dsn:
            raise ValueError("postgresql_dsn is required")
        if not self.neo4j_uri:
            raise ValueError("neo4j_uri is required")
        if not self.neo4j_auth or len(self.neo4j_auth) != 2:
            raise ValueError("neo4j_auth must be a tuple of (username, password)")
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
        if self.pool_min_size < 0:
            raise ValueError("pool_min_size must be non-negative")
        if self.pool_max_size <= 0:
            raise ValueError("pool_max_size must be positive")
        if self.pool_max_size < self.pool_min_size:
            raise ValueError("pool_max_size must be >= pool_min_size")


# ========================================
# Health Status Models
# ========================================

class HealthState(Enum):
    """Health status states for database components"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthStatus:
    """Health status information for a database component"""
    component: str
    status: HealthState
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time_ms: Optional[float] = None
    
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.status == HealthState.HEALTHY
    
    def is_available(self) -> bool:
        """Check if component is available (healthy or degraded)"""
        return self.status in (HealthState.HEALTHY, HealthState.DEGRADED)


@dataclass
class OverallHealthStatus:
    """Overall health status aggregating multiple components"""
    status: HealthState
    components: Dict[str, HealthStatus]
    timestamp: datetime
    summary: str
    
    def is_healthy(self) -> bool:
        """Check if overall system is healthy"""
        return self.status == HealthState.HEALTHY
    
    def get_unhealthy_components(self) -> List[str]:
        """Get list of unhealthy component names"""
        return [
            name for name, health in self.components.items()
            if health.status == HealthState.UNHEALTHY
        ]


@dataclass
class CompatibilityResult:
    """Result of Python/asyncpg version compatibility check"""
    is_compatible: bool
    python_version: str
    asyncpg_version: str
    issues: List[str]
    recommendations: List[str]
    
    def __post_init__(self):
        """Validate compatibility result"""
        if not self.python_version:
            raise ValueError("python_version is required")
        if not self.asyncpg_version:
            raise ValueError("asyncpg_version is required")


# ========================================
# Error Models
# ========================================

class ErrorType(Enum):
    """Types of database connectivity errors"""
    CONNECTION_TIMEOUT = "connection_timeout"
    AUTHENTICATION_FAILURE = "authentication_failure"
    ENCODING_ERROR = "encoding_error"
    COMPATIBILITY_ERROR = "compatibility_error"
    POOL_EXHAUSTION = "pool_exhaustion"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"


@dataclass
class DatabaseError:
    """Structured database error information"""
    error_type: ErrorType
    component: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    resolution_steps: List[str]
    
    def __post_init__(self):
        """Validate database error"""
        if not self.component:
            raise ValueError("component is required")
        if not self.message:
            raise ValueError("message is required")


# ========================================
# Migration Models
# ========================================

@dataclass
class ValidationResult:
    """Result of migration file validation"""
    is_valid: bool
    file_path: str
    encoding: str
    errors: List[str]
    warnings: List[str]
    
    def has_errors(self) -> bool:
        """Check if validation found errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if validation found warnings"""
        return len(self.warnings) > 0


@dataclass
class MigrationResult:
    """Result of migration execution"""
    success: bool
    migration_file: str
    execution_time_ms: float
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class EncodingFixResult:
    """Result of encoding fix attempt"""
    success: bool
    original_encoding: str
    fixed_encoding: str
    backup_created: bool
    error_message: Optional[str] = None


# ========================================
# Connection Status Models
# ========================================

@dataclass
class ConnectionStatus:
    """Status of a database connection"""
    service: str
    is_connected: bool
    error: Optional[str] = None
    response_time_ms: float = 0.0
    is_critical: bool = True
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    
    def __str__(self) -> str:
        """String representation of connection status"""
        if self.is_connected:
            return f"{self.service} ✅ ({self.response_time_ms:.0f}ms)"
        else:
            error_msg = self.error if self.error else "Unknown error"
            retry_info = f" (retry {self.retry_count})" if self.retry_count > 0 else ""
            return f"{self.service} ❌ ({error_msg}){retry_info}"


# ========================================
# Utility Functions
# ========================================

def get_python_version() -> str:
    """Get current Python version string"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def create_database_config_from_settings(settings) -> DatabaseConfig:
    """Create DatabaseConfig from application settings"""
    return DatabaseConfig(
        postgresql_dsn=settings.sync_postgres_url,
        neo4j_uri=settings.NEO4J_URI,
        neo4j_auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        connection_timeout=getattr(settings, 'DB_CONNECTION_TIMEOUT', 30),
        pool_min_size=getattr(settings, 'DB_POOL_MIN_SIZE', 5),
        pool_max_size=getattr(settings, 'DB_POOL_MAX_SIZE', 20),
        retry_config=RetryConfig(
            max_retries=getattr(settings, 'DB_MAX_RETRIES', 3),
            base_delay=getattr(settings, 'DB_RETRY_BASE_DELAY', 1.0),
            max_delay=getattr(settings, 'DB_RETRY_MAX_DELAY', 60.0),
            backoff_multiplier=getattr(settings, 'DB_RETRY_BACKOFF_MULTIPLIER', 2.0),
        )
    )