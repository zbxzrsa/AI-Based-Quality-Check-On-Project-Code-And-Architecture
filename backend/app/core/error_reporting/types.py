"""
Error Types Module

Defines error categories, data classes, and type definitions.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class DatabaseErrorCategory(Enum):
    """Categories of database connectivity errors for classification"""

    CONNECTION_TIMEOUT = "connection_timeout"
    AUTHENTICATION_FAILURE = "authentication_failure"
    ENCODING_ERROR = "encoding_error"
    COMPATIBILITY_ERROR = "compatibility_error"
    POOL_EXHAUSTION = "pool_exhaustion"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    MIGRATION_ERROR = "migration_error"
    HEALTH_CHECK_ERROR = "health_check_error"


@dataclass
class DatabaseErrorInfo:
    """Structured database error information with classification"""

    category: DatabaseErrorCategory
    component: str
    message: str
    details: dict[str, Any]
    timestamp: datetime
    resolution_steps: list[str]
    error_code: str | None = None
    connection_params: dict[str, str] | None = None

    def __post_init__(self):
        """Validate database error info"""
        if not self.component:
            raise ValueError("component is required")
        if not self.message:
            raise ValueError("message is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "category": self.category.value,
            "component": self.component,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "resolution_steps": self.resolution_steps,
            "error_code": self.error_code,
            "connection_params": self.connection_params,
        }
