"""
Database Connection Status Tracking

Classes for tracking and reporting database connection status.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStatus:
    """Status of a database connection"""
    service: str  # "PostgreSQL", "Neo4j", "Redis"
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
            return f"{self.service} ✅ ({self.response_time_ms:.0f}ms){pool_info}"
        else:
            error_msg = self.error if self.error else "Unknown error"
            retry_info = f" (retry {self.retry_count})" if self.retry_count > 0 else ""
            return f"{self.service} ❌ ({error_msg}){retry_info}"