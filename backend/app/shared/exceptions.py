"""
Custom exceptions for the platform

Provides structured exception hierarchy for better error handling
and reporting across all services.

Validates Requirements: 1.8, 7.6
"""

from typing import Any


class ServiceException(Exception):
    """Base exception for all service errors"""

    def __init__(self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class LLMProviderException(ServiceException):
    """Exception for LLM provider errors"""

    def __init__(
        self,
        message: str,
        provider: str,
        model: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.provider = provider
        self.model = model


class CircuitBreakerException(ServiceException):
    """Exception when circuit breaker is open"""

    def __init__(
        self,
        message: str,
        service_name: str,
        failure_count: int,
        error_code: str | None = "CIRCUIT_OPEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.service_name = service_name
        self.failure_count = failure_count


class CacheException(ServiceException):
    """Exception for cache operations"""

    def __init__(
        self,
        message: str,
        operation: str,
        key: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.operation = operation
        self.key = key


class DatabaseException(ServiceException):
    """Exception for database operations"""

    def __init__(
        self,
        message: str,
        database: str,
        operation: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.database = database
        self.operation = operation


class ValidationException(ServiceException):
    """Exception for validation errors"""

    def __init__(
        self,
        message: str,
        field: str,
        value: Any | None = None,
        error_code: str | None = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.field = field
        self.value = value


class AuthenticationException(ServiceException):
    """Exception for authentication errors"""

    def __init__(self, message: str, error_code: str | None = "AUTH_FAILED", details: dict[str, Any] | None = None):
        super().__init__(message, error_code, details)


class AuthorizationException(ServiceException):
    """Exception for authorization errors"""

    def __init__(
        self,
        message: str,
        resource: str,
        action: str,
        error_code: str | None = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.resource = resource
        self.action = action


class NotFoundException(ServiceException):
    """Exception for resource not found errors"""

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str | None = None,
        error_code: str | None = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictException(ServiceException):
    """Exception for resource conflict errors (e.g., duplicate entries)"""

    def __init__(
        self,
        message: str,
        resource_type: str,
        conflict_field: str | None = None,
        error_code: str | None = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.resource_type = resource_type
        self.conflict_field = conflict_field


class RateLimitException(ServiceException):
    """Exception for rate limiting errors"""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        error_code: str | None = "RATE_LIMIT_EXCEEDED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.retry_after = retry_after


class ExternalServiceException(ServiceException):
    """Exception for external service errors (GitHub, LLM APIs, etc.)"""

    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: int | None = None,
        error_code: str | None = "EXTERNAL_SERVICE_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.service_name = service_name
        self.status_code = status_code


class TimeoutException(ServiceException):
    """Exception for timeout errors"""

    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: float | None = None,
        error_code: str | None = "TIMEOUT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
