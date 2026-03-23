"""
XSS Prevention Utilities

This module provides comprehensive XSS prevention through:
1. HTML sanitization using bleach
2. Output encoding
3. Context-aware escaping
4. Safe rendering helpers

Requirements:
- 2.10: Sanitize all user input to prevent XSS attacks
- 8.7: Validate and sanitize all user input to prevent injection attacks
"""
import bleach
import html
import json
import re
from typing import Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


# Allowed HTML tags for different contexts
ALLOWED_TAGS_STRICT = []  # No HTML allowed

ALLOWED_TAGS_BASIC = [
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'code', 'pre'
]

ALLOWED_TAGS_RICH = [
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'code', 'pre', 'blockquote', 'hr',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'img', 'span', 'div'
]

# Allowed attributes for tags
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'span': ['class'],
    'div': ['class'],
}

# Allowed protocols for URLs
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


class XSSProtection:
    """
    XSS Protection utility class
    
    Provides context-aware sanitization and escaping methods.
    
    Requirements:
        - 2.10: Prevent XSS attacks
        - 8.7: Prevent injection attacks
    """
    
    @staticmethod
    def sanitize_html(
        text: str,
        level: str = 'basic',
        strip: bool = False
    ) -> str:
        """
        Sanitize HTML content based on security level
        
        Args:
            text: HTML content to sanitize
            level: Security level ('strict', 'basic', 'rich')
            strip: If True, strip all HTML tags
            
        Returns:
            Sanitized HTML string
            
        Requirements:
            - 2.10: Sanitize user input to prevent XSS
        """
        if not text:
            return ""
        
        if strip:
            return bleach.clean(text, tags=[], strip=True)
        
        # Select allowed tags based on level
        if level == 'strict':
            allowed_tags = ALLOWED_TAGS_STRICT
        elif level == 'rich':
            allowed_tags = ALLOWED_TAGS_RICH
        else:  # basic
            allowed_tags = ALLOWED_TAGS_BASIC
        
        # Sanitize HTML
        sanitized = bleach.clean(
            text,
            tags=allowed_tags,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True
        )
        
        # Additional sanitization: remove javascript: URLs
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove data: URLs (except for images if rich level)
        if level != 'rich':
            sanitized = re.sub(r'data:', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escape HTML entities
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        if not text:
            return ""
        
        return html.escape(text)
    
    @staticmethod
    def escape_javascript(text: str) -> str:
        """
        Escape text for safe inclusion in JavaScript
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for JavaScript
        """
        if not text:
            return ""
        
        # Use JSON encoding for safe JavaScript escaping
        return json.dumps(text)[1:-1]  # Remove surrounding quotes
    
    @staticmethod
    def escape_url(url: str) -> str:
        """
        Escape URL for safe inclusion in HTML attributes
        
        Args:
            url: URL to escape
            
        Returns:
            Escaped URL
        """
        if not url:
            return ""
        
        # Parse URL to validate
        try:
            parsed = urlparse(url)
            
            # Block javascript: and data: URLs
            if parsed.scheme.lower() in ('javascript', 'data', 'vbscript'):
                logger.warning(f"Blocked dangerous URL scheme: {parsed.scheme}")
                return ""
            
            # Only allow safe protocols
            if parsed.scheme and parsed.scheme.lower() not in ALLOWED_PROTOCOLS:
                logger.warning(f"Blocked non-allowed URL scheme: {parsed.scheme}")
                return ""
            
            return html.escape(url)
        except Exception as e:
            logger.error(f"URL parsing error: {e}")
            return ""
    
    @staticmethod
    def sanitize_json(data: Any) -> Any:
        """
        Sanitize JSON data by escaping string values
        
        Args:
            data: JSON data (dict, list, or primitive)
            
        Returns:
            Sanitized JSON data
        """
        if isinstance(data, dict):
            return {
                key: XSSProtection.sanitize_json(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [XSSProtection.sanitize_json(item) for item in data]
        elif isinstance(data, str):
            # Escape HTML in string values
            return html.escape(data)
        else:
            return data
    
    @staticmethod
    def sanitize_markdown(text: str) -> str:
        """
        Sanitize Markdown content
        
        Allows Markdown syntax but prevents XSS through HTML injection.
        
        Args:
            text: Markdown text to sanitize
            
        Returns:
            Sanitized Markdown
        """
        if not text:
            return ""
        
        # First, escape any HTML tags
        sanitized = html.escape(text)
        
        # Then unescape Markdown-safe characters
        # This allows Markdown syntax while preventing HTML injection
        markdown_chars = ['*', '_', '`', '#', '-', '+', '>', '|', '[', ']', '(', ')']
        for char in markdown_chars:
            escaped = html.escape(char)
            sanitized = sanitized.replace(escaped, char)
        
        return sanitized
    
    @staticmethod
    def validate_safe_url(url: str) -> bool:
        """
        Validate that URL is safe (no XSS vectors)
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is safe, False otherwise
        """
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Block dangerous schemes
            dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
            if parsed.scheme.lower() in dangerous_schemes:
                return False
            
            # Only allow safe protocols
            if parsed.scheme and parsed.scheme.lower() not in ALLOWED_PROTOCOLS:
                return False
            
            # Check for encoded dangerous patterns
            url_lower = url.lower()
            dangerous_patterns = [
                'javascript:',
                'data:text/html',
                'vbscript:',
                '<script',
                'onerror=',
                'onclick=',
                'onload=',
            ]
            
            for pattern in dangerous_patterns:
                if pattern in url_lower:
                    return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent XSS and path traversal
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed"
        
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Remove HTML tags
        filename = bleach.clean(filename, tags=[], strip=True)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Only allow safe characters
        filename = re.sub(r'[^\w\-\.]', '_', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename or "unnamed"


def sanitize_user_input(
    text: str,
    context: str = 'html',
    level: str = 'basic'
) -> str:
    """
    Sanitize user input based on context
    
    Args:
        text: User input to sanitize
        context: Context ('html', 'javascript', 'url', 'markdown', 'plain')
        level: Security level for HTML context
        
    Returns:
        Sanitized text
        
    Requirements:
        - 2.10: Sanitize all user input
        - 8.7: Context-aware sanitization
    """
    if not text:
        return ""
    
    xss = XSSProtection()
    
    if context == 'html':
        return xss.sanitize_html(text, level=level)
    elif context == 'javascript':
        return xss.escape_javascript(text)
    elif context == 'url':
        return xss.escape_url(text)
    elif context == 'markdown':
        return xss.sanitize_markdown(text)
    elif context == 'plain':
        return xss.escape_html(text)
    else:
        # Default to strict HTML escaping
        return xss.escape_html(text)


def create_safe_response(data: Dict[str, Any], sanitize: bool = True) -> Dict[str, Any]:
    """
    Create a safe API response with sanitized data
    
    Args:
        data: Response data
        sanitize: Whether to sanitize string values
        
    Returns:
        Sanitized response data
        
    Requirements:
        - 2.10: Sanitize output to prevent XSS
    """
    if not sanitize:
        return data
    
    return XSSProtection.sanitize_json(data)


# Export public API
__all__ = [
    'XSSProtection',
    'sanitize_user_input',
    'create_safe_response',
    'ALLOWED_TAGS_STRICT',
    'ALLOWED_TAGS_BASIC',
    'ALLOWED_TAGS_RICH',
]
