"""
Connection Pool Types and Data Classes

Defines data structures for connection pool management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any


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
    pool_stats: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """String representation of connection status"""
        if self.is_connected:
            pool_info = ""
            if self.pool_stats:
                pool_info = f" [Pool: {self.pool_stats.get('active', 0)}/{self.pool_stats.get('max_size', 0)}]"
            return f"{self.service} OK ({self.response_time_ms:.0f}ms){pool_info}"
        else:
            error_msg = self.error if self.error else "Unknown error"
            retry_info = f" (retry {self.retry_count})" if self.retry_count > 0 else ""
            return f"{self.service} FAILED ({error_msg}){retry_info}"


@dataclass
class PoolConfiguration:
    """Configuration for database connection pools"""
    min_size: int = 5
    max_size: int = 20
    connection_timeout: float = 30.0
    command_timeout: float = 30.0
    max_queries: int = 50000
    max_inactive_connection_lifetime: float = 300.0
    pool_recycle_time: float = 3600.0
    health_check_interval: float = 60.0

    def __post_init__(self):
        """Validate pool configuration"""
        if self.min_size < 0:
            raise ValueError("min_size must be non-negative")
        if self.max_size <= 0:
            raise ValueError("max_size must be positive")
        if self.max_size < self.min_size:
            raise ValueError("max_size must be >= min_size")
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")


@dataclass
class PoolStats:
    """Statistics for connection pool monitoring"""
    service: str
    size: int = 0
    freesize: int = 0
    max_size: int = 0
    min_size: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    failed_connections: int = 0
    last_health_check: Optional[datetime] = None
    avg_response_time_ms: float = 0.0
    peak_connections: int = 0

    @property
    def utilization(self) -> float:
        """Calculate pool utilization percentage"""
        if self.max_size == 0:
            return 0.0
        return (self.active_connections / self.max_size) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "service": self.service,
            "size": self.size,
            "freesize": self.freesize,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "utilization": round(self.utilization, 2),
            "peak_connections": self.peak_connections,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
        }
