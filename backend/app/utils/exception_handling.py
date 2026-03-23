"""
Utility functions for better exception handling
"""
import logging
from typing import TypeVar, Any, Optional
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DetailedException(Exception):
    """
    Base exception class with detailed error information.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize detailed exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_error = original_error
    
    def to_dict(self) -> dict:
        """
        Convert exception to dictionary for API responses.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details
        }


def handle_exception(
    error: Exception,
    context: Optional[dict] = None,
    default_message: str = "An error occurred"
) -> DetailedException:
    """
    Convert any exception to a DetailedException.
    
    Args:
        error: The exception to handle
        context: Additional context about when the error occurred
        default_message: Default message if exception has no message
        
    Returns:
        DetailedException with error information
    """
    if isinstance(error, DetailedException):
        return error
    
    message = getattr(error, 'message', str(error)) or default_message
    error_type = type(error).__name__
    
    error_mapping = {
        # Database errors
        'sqlalchemy.exc.OperationalError': {
            'code': 'DATABASE_OPERATIONAL_ERROR',
            'message': 'Database operation failed',
            'severity': 'high'
        },
        'sqlalchemy.exc.IntegrityError': {
            'code': 'DATABASE_INTEGRITY_ERROR',
            'message': 'Database constraint violation',
            'severity': 'medium'
        },
        'sqlalchemy.exc.ProgrammingError': {
            'code': 'DATABASE_PROGRAMMING_ERROR',
            'message': 'Database programming error',
            'severity': 'high'
        },
        'sqlalchemy.exc.DataError': {
            'code': 'DATABASE_DATA_ERROR',
            'message': 'Invalid data in database',
            'severity': 'medium'
        },
        # Network errors
        'ConnectionError': {
            'code': 'CONNECTION_ERROR',
            'message': 'Connection failed',
            'severity': 'high'
        },
        'TimeoutError': {
            'code': 'TIMEOUT_ERROR',
            'message': 'Operation timed out',
            'severity': 'medium'
        },
        # Value errors
        'ValueError': {
            'code': 'INVALID_VALUE',
            'message': 'Invalid value provided',
            'severity': 'low'
        },
        'KeyError': {
            'code': 'KEY_NOT_FOUND',
            'message': 'Required key not found',
            'severity': 'low'
        },
        # Authentication errors
        'AuthenticationError': {
            'code': 'AUTHENTICATION_FAILED',
            'message': 'Authentication failed',
            'severity': 'high'
        },
        # Authorization errors
        'PermissionError': {
            'code': 'PERMISSION_DENIED',
            'message': 'Permission denied',
            'severity': 'medium'
        },
    }
    
    error_info = error_mapping.get(error_type, {
        'code': 'UNKNOWN_ERROR',
        'message': message,
        'severity': 'medium'
    })
    
    return DetailedException(
        message=error_info['message'],
        error_code=error_info['code'],
        details={
            'original_type': error_type,
            'context': context or {},
            'severity': error_info['severity']
        },
        original_error=error
    )


def with_exception_handling(
    default_message: str = "An error occurred",
    reraise: bool = False
):
    """
    Decorator for handling exceptions in functions.
    
    Args:
        default_message: Default error message
        reraise: Whether to reraise the exception after handling
        
    Usage:
        @with_exception_handling(default_message="Failed to process data")
        def process_data(data):
            # Some logic that might fail
            return processed_data
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                detailed_error = handle_exception(e, default_message=default_message)
                
                if reraise:
                    raise detailed_error
                else:
                    logger.error(f"Handled error: {detailed_error.message}")
                    return None
        
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                detailed_error = handle_exception(e, default_message=default_message)
                
                if reraise:
                    raise detailed_error
                else:
                    logger.error(f"Handled error: {detailed_error.message}")
                    return None
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__'):  # It's a function
            return sync_wrapper
        else:  # Try to detect async function
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
    
    return decorator


@contextmanager
def safe_execute(
    error_context: dict,
    default_value: Any = None,
    reraise: bool = False
):
    """
    Context manager for safe execution of code blocks.
    
    Args:
        error_context: Context information about the operation
        default_value: Value to return on error
        reraise: Whether to reraise exceptions
        
    Usage:
        with safe_execute({'operation': 'database_query'}, default_value=[]) as result:
            data = execute_query()
            result = data
    """
    try:
        yield
    except Exception as e:
        logger.exception(f"Exception in context {error_context}: {e}")
        detailed_error = handle_exception(e, context=error_context)
        
        if reraise:
            raise detailed_error
        
        logger.error(f"Handled error in context: {detailed_error.message}")
        yield default_value


def validate_required_fields(data: dict, required_fields: list[str]) -> None:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Raises:
        DetailedException: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise DetailedException(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            error_code='VALIDATION_ERROR',
            details={'missing_fields': missing_fields}
        )


def validate_field_types(data: dict, field_types: dict[str, type]) -> None:
    """
    Validate that fields have correct types.
    
    Args:
        data: Data dictionary to validate
        field_types: Dictionary mapping field names to expected types
        
    Raises:
        DetailedException: If any field has incorrect type
    """
    type_errors = []
    
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                type_errors.append(f"{field} should be {expected_type.__name__}, got {type(data[field]).__name__}")
    
    if type_errors:
        raise DetailedException(
            message=f"Type validation failed: {', '.join(type_errors)}",
            error_code='VALIDATION_ERROR',
            details={'type_errors': type_errors}
        )


def sanitize_string_input(
    input_string: str,
    max_length: int = 1000,
    allowed_chars: Optional[str] = None
) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length
        allowed_chars: If provided, only allow these characters
        
    Returns:
        Sanitized string
    """
    # Remove excessive whitespace
    sanitized = ' '.join(input_string.split())
    
    # Limit length
    sanitized = sanitized[:max_length]
    
    # Filter characters if allowed_chars is specified
    if allowed_chars:
        sanitized = ''.join(char for char in sanitized if char in allowed_chars)
    
    return sanitized


def safe_float_conversion(
    value: Any,
    default: float = 0.0,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> float:
    """
    Safely convert a value to float with bounds checking.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Converted float value within bounds
    """
    try:
        result = float(value)
        
        if min_value is not None and result < min_value:
            result = min_value
        if max_value is not None and result > max_value:
            result = max_value
            
        return result
    except (ValueError, TypeError):
        return default


def safe_int_conversion(
    value: Any,
    default: int = 0,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> int:
    """
    Safely convert a value to int with bounds checking.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Converted int value within bounds
    """
    try:
        result = int(value)
        
        if min_value is not None and result < min_value:
            result = min_value
        if max_value is not None and result > max_value:
            result = max_value
            
        return result
    except (ValueError, TypeError):
        return default


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exception_types: tuple[type, ...] = (Exception,)
):
    """
    Decorator to retry function on exception.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exception_types: Tuple of exception types to retry on
        
    Usage:
        @retry_on_exception(max_retries=3, exception_types=(ConnectionError,))
        def fetch_data():
            # Function that might fail due to connection issues
            return data
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import asyncio
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exception_types as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__'):
            return sync_wrapper
        else:
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
    
    return decorator
