"""
Input validation and sanitization utilities

This module provides comprehensive validation and sanitization functions
to prevent SQL injection, XSS attacks, and other security vulnerabilities.

Requirements:
- 2.9: Validate all input data using Pydantic schemas
- 2.10: Sanitize all user input to prevent SQL injection and XSS attacks
- 8.7: Validate and sanitize all user input to prevent injection attacks
"""
import re
import bleach
from typing import Optional, List
from urllib.parse import urlparse
import html


# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'code', 'pre', 'blockquote'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'code': ['class'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def sanitize_html(text: str, strip: bool = False) -> str:
    """
    Sanitize HTML content to prevent XSS attacks
    
    Args:
        text: HTML content to sanitize
        strip: If True, strip all HTML tags. If False, allow safe tags.
        
    Returns:
        Sanitized HTML string
        
    Requirements:
        - 2.10: Sanitize user input to prevent XSS attacks
        - 8.7: Prevent injection attacks
    """
    if not text:
        return ""
    
    if strip:
        # Strip all HTML tags
        return bleach.clean(text, tags=[], strip=True)
    
    # Allow safe HTML tags and attributes
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a plain text string by escaping HTML entities
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length (optional)
        
    Returns:
        Sanitized string with HTML entities escaped
        
    Requirements:
        - 2.10: Sanitize user input to prevent XSS attacks
    """
    if not text:
        return ""
    
    # Escape HTML entities
    sanitized = html.escape(text)
    
    # Truncate if max_length specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
    """
    Validate URL format and scheme
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        
    Returns:
        True if URL is valid, False otherwise
        
    Requirements:
        - 2.9: Validate all input data
    """
    if not url:
        return False
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    try:
        parsed = urlparse(url)
        
        # Check if scheme is allowed
        if parsed.scheme not in allowed_schemes:
            return False
        
        # Check if netloc (domain) exists
        if not parsed.netloc:
            return False
        
        return True
    except Exception:
        return False


def validate_github_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate GitHub repository URL
    
    Args:
        url: GitHub URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements:
        - 2.9: Validate all input data
    """
    if not url:
        return False, "URL cannot be empty"
    
    # HTTPS format: https://github.com/{owner}/{repo}.git
    https_pattern = r'^https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?$'
    
    # SSH format: git@github.com:{owner}/{repo}.git
    ssh_pattern = r'^git@github\.com:[\w\-\.]+/[\w\-\.]+(?:\.git)?$'
    
    if not (re.match(https_pattern, url) or re.match(ssh_pattern, url)):
        return False, (
            "Invalid GitHub URL format. Expected formats:\n"
            "  - HTTPS: https://github.com/owner/repo.git\n"
            "  - SSH: git@github.com:owner/repo.git"
        )
    
    return True, None


def validate_email_format(email: str) -> bool:
    """
    Validate email format (basic validation)
    
    Note: Use Pydantic's EmailStr for comprehensive validation
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid, False otherwise
    """
    if not email:
        return False
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifier (table name, column name)
    
    Note: This should only be used for dynamic identifiers.
    Always prefer parameterized queries for values.
    
    Args:
        identifier: SQL identifier to sanitize
        
    Returns:
        Sanitized identifier
        
    Raises:
        ValueError: If identifier contains invalid characters
        
    Requirements:
        - 2.10: Prevent SQL injection attacks
        - 8.7: Prevent injection attacks
    """
    if not identifier:
        raise ValueError("SQL identifier cannot be empty")
    
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValueError(
            f"Invalid SQL identifier: {identifier}. "
            "Only alphanumeric characters and underscores are allowed."
        )
    
    return identifier


def validate_file_path(path: str, allow_absolute: bool = False) -> tuple[bool, Optional[str]]:
    """
    Validate file path to prevent directory traversal attacks
    
    Args:
        path: File path to validate
        allow_absolute: Whether to allow absolute paths
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Requirements:
        - 8.7: Prevent injection attacks
    """
    if not path:
        return False, "Path cannot be empty"
    
    # Check for directory traversal attempts
    if '..' in path:
        return False, "Path cannot contain '..' (directory traversal)"
    
    # Check for null bytes
    if '\x00' in path:
        return False, "Path cannot contain null bytes"
    
    # Check for absolute paths if not allowed
    if not allow_absolute and path.startswith('/'):
        return False, "Absolute paths are not allowed"
    
    return True, None


def validate_json_field(value: str, max_length: int = 10000) -> tuple[bool, Optional[str]]:
    """
    Validate JSON field content
    
    Args:
        value: JSON string to validate
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return True, None
    
    if len(value) > max_length:
        return False, f"JSON field exceeds maximum length of {max_length}"
    
    # Check for potential injection patterns
    dangerous_patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onclick=',
    ]
    
    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_lower):
            return False, "JSON field contains potentially dangerous content"
    
    return True, None


def validate_integer_range(value: int, min_value: Optional[int] = None, 
                          max_value: Optional[int] = None) -> tuple[bool, Optional[str]]:
    """
    Validate integer is within specified range
    
    Args:
        value: Integer to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if min_value is not None and value < min_value:
        return False, f"Value must be at least {min_value}"
    
    if max_value is not None and value > max_value:
        return False, f"Value must be at most {max_value}"
    
    return True, None


def validate_string_length(value: str, min_length: Optional[int] = None,
                          max_length: Optional[int] = None) -> tuple[bool, Optional[str]]:
    """
    Validate string length
    
    Args:
        value: String to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    length = len(value) if value else 0
    
    if min_length is not None and length < min_length:
        return False, f"String must be at least {min_length} characters"
    
    if max_length is not None and length > max_length:
        return False, f"String must be at most {max_length} characters"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
        
    Requirements:
        - 8.7: Prevent injection attacks
    """
    if not filename:
        return "unnamed"
    
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Only allow alphanumeric, dash, underscore, and dot
    filename = re.sub(r'[^\w\-\.]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename or "unnamed"
