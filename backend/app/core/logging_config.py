"""
Structured logging configuration for the application

Provides:
- JSON logging for log aggregation (Requirement 7.1)
- CloudWatch Logs integration (Requirement 7.2)
- Structured fields: timestamp, level, message, request_id, user_id, service_name
- Request context middleware for correlation IDs
- Startup diagnostics and summary
- Request/response logging
- Exception logging with context
- Sensitive data masking
- 30-day log retention in CloudWatch (Requirement 7.10)
- Local file log rotation with 30-day retention (Requirement 7.6)

Validates Requirements: 7.1, 7.2, 7.6, 7.10, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
"""
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger.json import JsonFormatter

from app.core.error_reporter import ErrorReporter
from app.core.cloudwatch_handler import (
    CloudWatchConfig,
    create_cloudwatch_handler,
    get_cloudwatch_status
)


# Context variables for request tracking (Requirement 7.1)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CustomJsonFormatter(JsonFormatter):
    """
    Custom JSON formatter with structured fields for log aggregation.
    
    Includes standard fields (Requirement 7.1):
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - message: Log message
    - logger: Logger name
    - service_name: Service identifier
    - request_id: Request correlation ID
    - user_id: Authenticated user ID (if available)
    - correlation_id: Distributed tracing correlation ID
    
    Validates Requirement 7.1
    """
    
    def __init__(self, *args, service_name: str = "backend-api", **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO 8601 format (Requirement 7.1)
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level (Requirement 7.1)
        log_record['level'] = record.levelname
        
        # Add logger name (Requirement 7.1)
        log_record['logger'] = record.name
        
        # Add service name (Requirement 7.1)
        log_record['service_name'] = self.service_name
        
        # Add request context from ContextVars (Requirement 7.1)
        request_id = request_id_var.get()
        if request_id:
            log_record['request_id'] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_record['user_id'] = user_id
        
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_record['correlation_id'] = correlation_id
        
        # Add extra fields from log record (Requirement 7.1)
        if hasattr(record, 'user_id') and not user_id:
            log_record['user_id'] = record.user_id
        if hasattr(record, 'request_id') and not request_id:
            log_record['request_id'] = record.request_id
        if hasattr(record, 'correlation_id') and not correlation_id:
            log_record['correlation_id'] = record.correlation_id
        if hasattr(record, 'duration'):
            log_record['duration_ms'] = record.duration
        if hasattr(record, 'status_code'):
            log_record['status_code'] = record.status_code
        if hasattr(record, 'method'):
            log_record['method'] = record.method
        if hasattr(record, 'url'):
            log_record['url'] = record.url
        if hasattr(record, 'client_ip'):
            log_record['client_ip'] = record.client_ip


def setup_logging(
    level: str = "INFO",
    enable_json: bool = True,
    service_name: str = "backend-api",
    enable_cloudwatch: bool = True,
    cloudwatch_config: Optional[CloudWatchConfig] = None
) -> None:
    """
    Setup application logging with structured JSON format and CloudWatch integration.
    
    Configures logging to output structured JSON logs suitable for aggregation
    in centralized logging systems (CloudWatch, ELK stack).
    
    Local file logging uses TimedRotatingFileHandler with:
    - Daily rotation at midnight (UTC)
    - 30-day retention (Requirement 7.6)
    - Automatic cleanup of old log files
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Whether to use JSON formatting (Requirement 7.1)
        service_name: Service identifier for multi-service deployments
        enable_cloudwatch: Whether to enable CloudWatch Logs (Requirement 7.2)
        cloudwatch_config: CloudWatch configuration (uses defaults if None)
        
    Validates Requirements: 7.1, 7.2, 7.6, 7.10, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
    """
    log_level = getattr(logging, level.upper())
    
    # Get service name from environment or use default
    service_name = os.getenv('SERVICE_NAME', service_name)
    
    # Create formatter (Requirement 7.1)
    if enable_json:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s',
            service_name=service_name
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler (stdout for container environments)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler with rotation (Requirement 7.6)
    # Rotates daily and keeps 30 days of logs
    log_dir = os.getenv('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'app.log')
    
    file_handler = TimedRotatingFileHandler(
        filename=log_file_path,
        when='midnight',  # Rotate at midnight
        interval=1,  # Rotate every 1 day
        backupCount=30,  # Keep 30 days of logs (Requirement 7.6)
        encoding='utf-8',
        utc=True  # Use UTC for rotation timing
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    # Set suffix for rotated files (e.g., app.log.2024-01-15)
    file_handler.suffix = "%Y-%m-%d"
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Add CloudWatch handler (Requirement 7.2, 7.10)
    cloudwatch_handler = None
    if enable_cloudwatch:
        cloudwatch_handler = create_cloudwatch_handler(
            config=cloudwatch_config,
            log_level=log_level
        )
        if cloudwatch_handler:
            # Use JSON formatter for CloudWatch
            cloudwatch_handler.setFormatter(formatter)
            root_logger.addHandler(cloudwatch_handler)
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            'log_level': level,
            'json_enabled': enable_json,
            'service_name': service_name,
            'cloudwatch_enabled': cloudwatch_handler is not None,
            'log_file': log_file_path,
            'log_rotation': 'daily',
            'log_retention_days': 30
        }
    )
    
    # Log CloudWatch status
    if enable_cloudwatch:
        cw_status = get_cloudwatch_status(cloudwatch_config)
        if cw_status['connected']:
            logger.info(
                "CloudWatch Logs integration enabled",
                extra={
                    'log_group': cw_status['log_group'],
                    'log_stream': cw_status['log_stream'],
                    'region': cw_status['region'],
                    'retention_days': cw_status['retention_days']
                }
            )
        else:
            logger.warning(
                "CloudWatch Logs integration failed",
                extra={'error': cw_status['error']}
            )


def log_startup_summary(
    app_name: str,
    version: str,
    environment: str,
    config_file: str,
    database_status: Dict[str, Any],
    features_enabled: Dict[str, bool],
    security_warnings: Optional[list] = None
) -> None:
    """
    Log comprehensive startup summary.
    
    Args:
        app_name: Application name
        version: Application version
        environment: Environment (development, staging, production)
        config_file: Configuration file path
        database_status: Dictionary of database connection statuses
        features_enabled: Dictionary of enabled/disabled features
        security_warnings: Optional list of security warnings
        
    Validates Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
    """
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("APPLICATION STARTUP SUMMARY")
    logger.info("=" * 70)
    
    # Application info
    logger.info(f"Application: {app_name}")
    logger.info(f"Version: {version}")
    logger.info(f"Environment: {environment}")
    logger.info(f"Configuration file: {config_file}")
    
    # Database status
    logger.info("\nDatabase Status:")
    for db_name, status in database_status.items():
        if isinstance(status, dict):
            is_connected = status.get('is_connected', False)
            response_time = status.get('response_time_ms', 0)
            status_str = f"✅ ({response_time:.0f}ms)" if is_connected else "❌"
        else:
            status_str = str(status)
        logger.info(f"  {db_name}: {status_str}")
    
    # Features status
    logger.info("\nFeatures:")
    for feature_name, is_enabled in features_enabled.items():
        status_str = "✅ enabled" if is_enabled else "⚠️  disabled"
        logger.info(f"  {feature_name}: {status_str}")
    
    # Security warnings
    if security_warnings:
        logger.warning("\nSecurity Warnings:")
        for warning in security_warnings:
            logger.warning(f"  ⚠️  {warning}")
    
    # API documentation
    logger.info("\nAPI Documentation:")
    logger.info("  Swagger UI: http://localhost:8000/docs")
    logger.info("  ReDoc: http://localhost:8000/redoc")
    logger.info("  OpenAPI JSON: http://localhost:8000/openapi.json")
    
    # Health check endpoints
    logger.info("\nHealth Check Endpoints:")
    logger.info("  Overall health: GET /health")
    logger.info("  Readiness probe: GET /health/ready")
    logger.info("  Liveness probe: GET /health/live")
    
    logger.info("=" * 70)
    logger.info("✅ Application startup complete")
    logger.info("=" * 70)


# Create logger instance
logger = logging.getLogger(__name__)


# Request context management functions (Requirement 7.1)
def set_request_context(request_id: Optional[str] = None, user_id: Optional[str] = None, correlation_id: Optional[str] = None) -> None:
    """
    Set request context for structured logging.
    
    This function sets context variables that will be automatically included
    in all log messages within the current request context.
    
    Args:
        request_id: Unique request identifier
        user_id: Authenticated user identifier
        correlation_id: Distributed tracing correlation ID
        
    Validates Requirement 7.1
    """
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if correlation_id:
        correlation_id_var.set(correlation_id)


def clear_request_context() -> None:
    """
    Clear request context after request completion.
    
    Validates Requirement 7.1
    """
    request_id_var.set(None)
    user_id_var.set(None)
    correlation_id_var.set(None)


def get_request_context() -> Dict[str, Optional[str]]:
    """
    Get current request context.
    
    Returns:
        Dictionary with request_id, user_id, and correlation_id
        
    Validates Requirement 7.1
    """
    return {
        'request_id': request_id_var.get(),
        'user_id': user_id_var.get(),
        'correlation_id': correlation_id_var.get()
    }


# Request logging middleware (Requirement 7.1)
async def log_request(request, call_next):
    """
    Middleware to log HTTP requests and responses with structured context.
    
    Automatically captures and logs:
    - Request ID (generated UUID)
    - User ID (from authenticated user)
    - Correlation ID (from X-Correlation-ID header or generated)
    - HTTP method and URL
    - Client IP address
    - Response status code
    - Request duration in milliseconds
    
    Validates Requirement 7.1
    """
    import time
    from uuid import uuid4
    
    # Generate or extract request ID (Requirement 7.1)
    request_id = request.headers.get('X-Request-ID', str(uuid4()))
    request.state.request_id = request_id
    
    # Extract or generate correlation ID for distributed tracing (Requirement 7.1)
    correlation_id = request.headers.get('X-Correlation-ID', str(uuid4()))
    request.state.correlation_id = correlation_id
    
    # Extract user ID from request state (set by auth middleware)
    user_id = None
    if hasattr(request.state, 'user') and request.state.user:
        user_id = str(request.state.user.id) if hasattr(request.state.user, 'id') else None
    
    # Set request context for all logs in this request (Requirement 7.1)
    set_request_context(
        request_id=request_id,
        user_id=user_id,
        correlation_id=correlation_id
    )
    
    # Log request start (Requirement 7.1)
    logger.info(
        "Request started",
        extra={
            'request_id': request_id,
            'correlation_id': correlation_id,
            'user_id': user_id,
            'method': request.method,
            'url': str(request.url),
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('User-Agent'),
        }
    )
    
    # Process request
    start_time = time.time()
    try:
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log response (Requirement 7.1)
        logger.info(
            "Request completed",
            extra={
                'request_id': request_id,
                'correlation_id': correlation_id,
                'user_id': user_id,
                'status_code': response.status_code,
                'duration': duration,
            }
        )
        
        # Add correlation headers to response for distributed tracing
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Correlation-ID'] = correlation_id
        
        return response
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        
        # Log error (Requirement 7.1)
        logger.error(
            "Request failed",
            extra={
                'request_id': request_id,
                'correlation_id': correlation_id,
                'user_id': user_id,
                'duration': duration,
                'error': str(e),
                'error_type': type(e).__name__,
            },
            exc_info=True
        )
        raise
    finally:
        # Clear request context after request completion
        clear_request_context()


# Error logging (Requirement 7.1)
def log_exception(exc: Exception, context: Dict[str, Any] = None):
    """
    Log exception with structured context.
    
    Includes:
    - Exception type and message
    - Full stack trace
    - Request context (request_id, user_id, correlation_id)
    - Additional context provided by caller
    
    Args:
        exc: Exception to log
        context: Additional context dictionary
        
    Validates Requirement 7.1
    """
    extra = context or {}
    extra['exception_type'] = type(exc).__name__
    extra['exception_message'] = str(exc)
    
    # Add request context
    request_context = get_request_context()
    extra.update(request_context)
    
    logger.error(
        "Exception occurred",
        extra=extra,
        exc_info=True
    )


def mask_sensitive_in_logs(message: str) -> str:
    """
    Mask sensitive data in log messages.
    
    Applies masking rules to remove or obscure:
    - Passwords
    - API keys
    - Tokens
    - Connection strings with credentials
    - JWT secrets
    - Database URLs with passwords
    - Webhook secrets
    
    Args:
        message: Log message that may contain sensitive data
        
    Returns:
        Log message with sensitive data masked
        
    Validates Requirements: 1.6, 7.5, 7.6
    """
    if not message:
        return message
    
    return ErrorReporter.mask_sensitive_data(message)


def log_database_status(
    database_status: Dict[str, Any],
    logger_instance: Optional[logging.Logger] = None
) -> None:
    """
    Log database connection status with detailed information.
    
    Logs:
    - Connection status for each database (PostgreSQL, Neo4j, Redis)
    - Response times for successful connections
    - Error messages for failed connections (masked)
    - Overall database health summary
    
    Args:
        database_status: Dictionary mapping database names to status info
        logger_instance: Optional logger instance (uses module logger if not provided)
        
    Validates Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
    """
    if logger_instance is None:
        logger_instance = logging.getLogger(__name__)
    
    logger_instance.info("Database Connection Status:")
    logger_instance.info("-" * 50)
    
    all_connected = True
    critical_connected = True
    
    for db_name, status in database_status.items():
        if isinstance(status, dict):
            is_connected = status.get('is_connected', False)
            response_time = status.get('response_time_ms', 0)
            error = status.get('error', None)
            is_critical = status.get('is_critical', True)
            
            if is_connected:
                logger_instance.info(
                    f"  {db_name}: ✅ Connected ({response_time:.0f}ms)"
                )
            else:
                all_connected = False
                if is_critical:
                    critical_connected = False
                
                # Mask sensitive data in error message
                masked_error = mask_sensitive_in_logs(error) if error else "Unknown error"
                
                if is_critical:
                    logger_instance.error(
                        f"  {db_name}: ❌ Failed - {masked_error}"
                    )
                else:
                    logger_instance.warning(
                        f"  {db_name}: ⚠️  Failed - {masked_error}"
                    )
        else:
            # Handle ConnectionStatus objects
            status_obj = status
            if hasattr(status_obj, 'is_connected'):
                if status_obj.is_connected:
                    logger_instance.info(
                        f"  {status_obj.service}: ✅ Connected ({status_obj.response_time_ms:.0f}ms)"
                    )
                else:
                    all_connected = False
                    if status_obj.is_critical:
                        critical_connected = False
                    
                    masked_error = mask_sensitive_in_logs(status_obj.error) if status_obj.error else "Unknown error"
                    
                    if status_obj.is_critical:
                        logger_instance.error(
                            f"  {status_obj.service}: ❌ Failed - {masked_error}"
                        )
                    else:
                        logger_instance.warning(
                            f"  {status_obj.service}: ⚠️  Failed - {masked_error}"
                        )
    
    logger_instance.info("-" * 50)
    
    # Log summary
    if all_connected:
        logger_instance.info("✅ All databases connected")
    elif critical_connected:
        logger_instance.warning("⚠️  Some optional databases unavailable, but critical databases connected")
    else:
        logger_instance.error("❌ Critical database(s) unavailable")
