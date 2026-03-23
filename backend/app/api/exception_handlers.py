"""
FastAPI exception handlers for standardized error responses

Provides global exception handling with:
- Standardized error response format
- Full stack trace logging with request context
- Appropriate HTTP status code mapping
- Security-conscious error messages

Validates Requirements: 2.5, 12.1, 12.2, 12.3
"""

import logging
import traceback
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.shared.exceptions import (
    ServiceException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    DatabaseException,
    LLMProviderException,
    CircuitBreakerException,
    CacheException,
    NotFoundException,
    ConflictException,
    RateLimitException,
    ExternalServiceException,
    TimeoutException,
)


logger = logging.getLogger(__name__)


def get_request_context(request: Request) -> Dict[str, Any]:
    """
    Extract comprehensive request context for logging
    
    Includes:
    - Request ID for tracing
    - User ID if authenticated
    - HTTP method and endpoint
    - Query parameters
    - Client information (IP, user agent)
    - Request headers (sanitized)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with comprehensive request context information
        
    Validates Requirements: 12.2
    """
    context = {
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_host": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    
    # Add request ID if available
    if hasattr(request.state, "request_id"):
        context["request_id"] = request.state.request_id
    
    # Add user ID if authenticated
    if hasattr(request.state, "user_id"):
        context["user_id"] = request.state.user_id
    elif hasattr(request.state, "user"):
        # Try to extract user ID from user object
        user = request.state.user
        if hasattr(user, "id"):
            context["user_id"] = user.id
        elif isinstance(user, dict) and "id" in user:
            context["user_id"] = user["id"]
    
    # Add selected headers (sanitized - no auth tokens)
    safe_headers = {}
    for header_name in ["content-type", "accept", "referer", "origin"]:
        if header_name in request.headers:
            safe_headers[header_name] = request.headers[header_name]
    
    if safe_headers:
        context["headers"] = safe_headers
    
    # Add URL scheme and host
    context["url"] = str(request.url)
    context["scheme"] = request.url.scheme
    context["host"] = request.url.hostname
    
    return context


def create_error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """
    Create standardized error response
    
    Args:
        status_code: HTTP status code
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details (optional)
        request_id: Request ID for tracing (optional)
        
    Returns:
        JSONResponse with standardized error format
    """
    content = {
        "error": {
            "message": message,
            "code": error_code,
            "status": status_code,
        }
    }
    
    if details:
        content["error"]["details"] = details
        
    if request_id:
        content["error"]["request_id"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content=content,
    )


async def service_exception_handler(
    request: Request, 
    exc: ServiceException
) -> JSONResponse:
    """
    Handle custom service exceptions
    
    Maps service exceptions to appropriate HTTP status codes and
    returns standardized error responses. Logs exceptions with full
    stack traces and comprehensive request context.
    
    Validates Requirements: 12.1, 12.2, 12.3
    """
    # Map exception types to status codes
    status_code_map = {
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        AuthorizationException: status.HTTP_403_FORBIDDEN,
        NotFoundException: status.HTTP_404_NOT_FOUND,
        ConflictException: status.HTTP_409_CONFLICT,
        ValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
        RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
        TimeoutException: status.HTTP_504_GATEWAY_TIMEOUT,
        DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        LLMProviderException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        CircuitBreakerException: status.HTTP_503_SERVICE_UNAVAILABLE,
        CacheException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ExternalServiceException: status.HTTP_502_BAD_GATEWAY,
    }
    
    # Get status code for exception type
    status_code = status_code_map.get(type(exc), status.HTTP_400_BAD_REQUEST)
    
    # Get comprehensive request context (Requirement 12.2)
    request_context = get_request_context(request)
    
    # Get full stack trace (Requirement 12.2)
    stack_trace = traceback.format_exc()
    
    # Build structured log data for JSON logging (Requirement 12.2)
    log_data = {
        "exception_type": exc.__class__.__name__,
        "exception_module": exc.__class__.__module__,
        "error_code": exc.error_code,
        "error_message": exc.message,
        "error_details": exc.details,
        "status_code": status_code,
        "request_context": request_context,
        "stack_trace": stack_trace,
    }
    
    # Add exception-specific fields
    if isinstance(exc, LLMProviderException):
        log_data["llm_provider"] = exc.provider
        log_data["llm_model"] = exc.model
    elif isinstance(exc, CircuitBreakerException):
        log_data["service_name"] = exc.service_name
        log_data["failure_count"] = exc.failure_count
    elif isinstance(exc, DatabaseException):
        log_data["database"] = exc.database
        log_data["operation"] = exc.operation
    elif isinstance(exc, AuthorizationException):
        log_data["resource"] = exc.resource
        log_data["action"] = exc.action
    elif isinstance(exc, ExternalServiceException):
        log_data["service_name"] = exc.service_name
        log_data["service_status_code"] = exc.status_code
    elif isinstance(exc, TimeoutException):
        log_data["operation"] = exc.operation
        log_data["timeout_seconds"] = exc.timeout_seconds
    
    # Log exception with full context (Requirement 12.2)
    logger.error(
        f"Service exception: {exc.__class__.__name__}: {exc.message}",
        extra=log_data,
        exc_info=True,  # Include full stack trace
    )
    
    # Add retry-after header for rate limit exceptions
    headers = {}
    if isinstance(exc, RateLimitException) and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    
    response = create_error_response(
        status_code=status_code,
        message=exc.message,
        error_code=exc.error_code or "SERVICE_ERROR",
        details=exc.details if exc.details else None,
        request_id=request_context.get("request_id"),
    )
    
    # Add custom headers if any
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    
    return response


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI/Pydantic validation errors
    
    Converts validation errors to standardized error format.
    Logs validation errors with full request context.
    
    Validates Requirements: 2.9, 12.2, 12.3
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    # Get comprehensive request context (Requirement 12.2)
    request_context = get_request_context(request)
    
    # Get stack trace for debugging
    stack_trace = traceback.format_exc()
    
    # Log validation error with full context (Requirement 12.2)
    logger.warning(
        f"Validation error: {len(errors)} field(s) failed validation",
        extra={
            "exception_type": "RequestValidationError",
            "validation_errors": errors,
            "error_count": len(errors),
            "request_context": request_context,
            "stack_trace": stack_trace,
        },
    )
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        error_code="VALIDATION_ERROR",
        details={"errors": errors},
        request_id=request_context.get("request_id"),
    )


async def global_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle all unhandled exceptions
    
    Catches any exception not handled by specific handlers and returns
    a standardized error response. Logs full stack trace with comprehensive
    request context for debugging and monitoring.
    
    Validates Requirements: 12.1, 12.2, 12.3
    """
    # Get comprehensive request context (Requirement 12.2)
    request_context = get_request_context(request)
    
    # Get full stack trace (Requirement 12.2)
    stack_trace = traceback.format_exc()
    
    # Build structured log data for JSON logging (Requirement 12.2)
    log_data = {
        "exception_type": exc.__class__.__name__,
        "exception_module": exc.__class__.__module__,
        "exception_message": str(exc),
        "request_context": request_context,
        "stack_trace": stack_trace,
    }
    
    # Add exception attributes if available
    if hasattr(exc, "__dict__"):
        # Filter out private attributes and methods
        exc_attrs = {
            k: v for k, v in exc.__dict__.items() 
            if not k.startswith("_") and not callable(v)
        }
        if exc_attrs:
            log_data["exception_attributes"] = exc_attrs
    
    # Log exception with full context (Requirement 12.2)
    logger.error(
        f"Unhandled exception: {exc.__class__.__name__}: {str(exc)}",
        extra=log_data,
        exc_info=True,  # Include full stack trace
    )
    
    # Return generic error message (don't expose internal details)
    # Requirement 2.5: Return standardized error response with HTTP 500
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An internal server error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        details={"type": exc.__class__.__name__} if logger.level == logging.DEBUG else None,
        request_id=request_context.get("request_id"),
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with FastAPI app
    
    Args:
        app: FastAPI application instance
    """
    # Register custom service exception handler
    app.add_exception_handler(ServiceException, service_exception_handler)
    
    # Register validation exception handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Register global exception handler (catch-all)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("Exception handlers registered successfully")
