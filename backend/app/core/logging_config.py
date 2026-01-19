"""
Structured logging configuration for the application
"""
import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict
from pythonjsonlogger.json import JsonFormatter


class CustomJsonFormatter(JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        if hasattr(record, 'duration'):
            log_record['duration_ms'] = record.duration


def setup_logging(level: str = "INFO", enable_json: bool = True) -> None:
    """
    Setup application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Whether to use JSON formatting
    """
    log_level = getattr(logging, level.upper())
    
    # Create formatter
    if enable_json:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler (optional)
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


# Create logger instance
logger = logging.getLogger(__name__)

# Request logging middleware
async def log_request(request, call_next):
    """
    Middleware to log HTTP requests and responses
    """
    import time
    from uuid import uuid4
    
    # Generate request ID
    request_id = str(uuid4())
    request.state.request_id = request_id
    
    # Log request
    logger.info(
        "Request started",
        extra={
            'request_id': request_id,
            'method': request.method,
            'url': str(request.url),
            'client_ip': request.client.host if request.client else None,
        }
    )
    
    # Process request
    start_time = time.time()
    try:
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                'request_id': request_id,
                'status_code': response.status_code,
                'duration': duration,
            }
        )
        
        return response
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        
        # Log error
        logger.error(
            "Request failed",
            extra={
                'request_id': request_id,
                'duration': duration,
                'error': str(e),
            },
            exc_info=True
        )
        raise


# Error logging
def log_exception(exc: Exception, context: Dict[str, Any] = None):
    """Log exception with context"""
    extra = context or {}
    extra['exception_type'] = type(exc).__name__
    extra['exception_message'] = str(exc)
    
    logger.error(
        "Exception occurred",
        extra=extra,
        exc_info=True
    )
