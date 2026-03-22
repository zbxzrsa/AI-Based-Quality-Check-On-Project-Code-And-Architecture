"""
Shared enums used across authentication, repositories, resilience and analysis.
"""

from enum import Enum


class Role(str, Enum):
    """System roles supported by the application."""

    ADMIN = "ADMIN"
    USER = "USER"


class Permission(str, Enum):
    """RBAC permissions used by API and services."""

    CREATE_USER = "CREATE_USER"
    DELETE_USER = "DELETE_USER"
    UPDATE_USER = "UPDATE_USER"
    VIEW_USER = "VIEW_USER"
    CREATE_PROJECT = "CREATE_PROJECT"
    DELETE_PROJECT = "DELETE_PROJECT"
    UPDATE_PROJECT = "UPDATE_PROJECT"
    VIEW_PROJECT = "VIEW_PROJECT"
    MODIFY_CONFIG = "MODIFY_CONFIG"
    VIEW_CONFIG = "VIEW_CONFIG"
    EXPORT_REPORT = "EXPORT_REPORT"


class RepositoryStatus(str, Enum):
    """Repository lifecycle status."""

    PENDING = "pending"
    VALIDATING = "validating"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


class RepositoryURLFormat(str, Enum):
    """Supported repository URL formats."""

    HTTPS = "https"
    SSH = "ssh"


class CircuitBreakerState(str, Enum):
    """Circuit breaker finite states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class Severity(str, Enum):
    """Issue severity levels used by analysis pipelines."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Convert arbitrary severity string to enum with safe default."""
        normalized = (value or "").strip().lower()
        mapping = {
            "critical": cls.CRITICAL,
            "crit": cls.CRITICAL,
            "high": cls.HIGH,
            "major": cls.HIGH,
            "medium": cls.MEDIUM,
            "med": cls.MEDIUM,
            "low": cls.LOW,
            "minor": cls.LOW,
            "info": cls.INFO,
            "informational": cls.INFO,
        }
        return mapping.get(normalized, cls.MEDIUM)
