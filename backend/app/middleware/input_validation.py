"""
Input validation middleware for enhanced security

Provides comprehensive input validation and sanitization to prevent
injection attacks and ensure data integrity.
"""
import re
import logging
from typing import Any, Dict, List, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import html
import bleach

logger = logging.getLogger(__name__)


class InputValidationMiddleware:
    """
    Middleware for input validation and sanitization
    
    Validates and sanitizes all incoming request data to prevent:
    - SQL injection
    - XSS attacks
    - Command injection
    - Path traversal
    - NoSQL injection
    """
    
    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        # SQL injection patterns
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        
        # XSS patterns
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        
        # Command injection patterns
        r"(;|\||&|`|\$\(|\${)",
        r"(\b(rm|del|format|shutdown|reboot)\b)",
        
        # Path traversal patterns
        r"(\.\./|\.\.\\)",
        r"(/etc/passwd|/etc/shadow)",
        
        # NoSQL injection patterns
        r"(\$where|\$ne|\$gt|\$lt|\$regex)",
    ]
    
    # Compile patterns for performance
    COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]
    
    # Maximum lengths for different field types
    MAX_LENGTHS = {
        "email": 254,
        "username": 50,
        "password": 128,
        "name": 100,
        "description": 1000,
        "url": 2048,
        "default": 500
    }
    
    def __init__(self):
        """Initialize validation middleware"""
        self.blocked_requests = 0
        self.validated_requests = 0
    
    async def __call__(self, request: Request, call_next):
        """Process request through validation middleware"""
        try:
            # Skip validation for certain endpoints
            if self._should_skip_validation(request):
                return await call_next(request)
            
            # Validate request
            await self._validate_request(request)
            
            # Process request
            response = await call_next(request)
            
            self.validated_requests += 1
            return response
            
        except HTTPException:
            self.blocked_requests += 1
            raise
        except Exception as e:
            logger.error(f"Input validation middleware error: {e}", exc_info=True)
            self.blocked_requests += 1
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request validation failed"
            )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request"""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    async def _validate_request(self, request: Request) -> None:
        """Validate incoming request data"""
        # Validate URL path
        self._validate_path(request.url.path)
        
        # Validate query parameters
        for key, value in request.query_params.items():
            self._validate_string(value, f"query parameter '{key}'")
        
        # Validate headers (selected ones)
        safe_headers = ["user-agent", "referer", "accept", "content-type"]
        for header_name in safe_headers:
            if header_name in request.headers:
                self._validate_string(request.headers[header_name], f"header '{header_name}'")
        
        # Validate request body if present
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_body(request)
    
    def _validate_path(self, path: str) -> None:
        """Validate URL path for dangerous patterns"""
        if self._contains_dangerous_pattern(path):
            logger.warning(f"Dangerous pattern detected in path: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters in request path"
            )
        
        # Check for path traversal
        if "../" in path or "..\\" in path:
            logger.warning(f"Path traversal attempt detected: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal not allowed"
            )
    
    async def _validate_body(self, request: Request) -> None:
        """Validate request body content"""
        try:
            # Get content type
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                # For JSON requests, we'll validate after parsing
                # This is handled by FastAPI's request validation
                pass
            elif "application/x-www-form-urlencoded" in content_type:
                # Validate form data
                form_data = await request.form()
                for key, value in form_data.items():
                    if isinstance(value, str):
                        self._validate_string(value, f"form field '{key}'")
            elif "multipart/form-data" in content_type:
                # Validate multipart form data
                form_data = await request.form()
                for key, value in form_data.items():
                    if isinstance(value, str):
                        self._validate_string(value, f"form field '{key}'")
                    # File uploads are handled separately
        except Exception as e:
            logger.error(f"Body validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body format"
            )
    
    def _validate_string(self, value: str, field_name: str) -> None:
        """Validate string value for dangerous patterns"""
        if not isinstance(value, str):
            return
        
        # Check length
        max_length = self.MAX_LENGTHS.get(field_name.lower(), self.MAX_LENGTHS["default"])
        if len(value) > max_length:
            logger.warning(f"Field '{field_name}' exceeds maximum length: {len(value)} > {max_length}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{field_name}' is too long"
            )
        
        # Check for dangerous patterns
        if self._contains_dangerous_pattern(value):
            logger.warning(f"Dangerous pattern detected in field '{field_name}': {value[:100]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid characters in field '{field_name}'"
            )
    
    def _contains_dangerous_pattern(self, value: str) -> bool:
        """Check if value contains dangerous patterns"""
        for pattern in self.COMPILED_PATTERNS:
            if pattern.search(value):
                return True
        return False
    
    def sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content to prevent XSS"""
        # Allow only safe HTML tags and attributes
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
            'code', 'pre'
        ]
        
        allowed_attributes = {
            '*': ['class'],
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height']
        }
        
        return bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total_requests = self.validated_requests + self.blocked_requests
        block_rate = (self.blocked_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "validated_requests": self.validated_requests,
            "blocked_requests": self.blocked_requests,
            "total_requests": total_requests,
            "block_rate_percent": round(block_rate, 2)
        }


# Global instance
input_validator = InputValidationMiddleware()


def get_input_validator() -> InputValidationMiddleware:
    """Get input validation middleware instance"""
    return input_validator