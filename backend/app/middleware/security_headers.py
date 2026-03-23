"""
Security headers middleware for FastAPI application.

Implements security response headers to protect against common web vulnerabilities:
- X-Content-Type-Options: Prevent MIME type sniffing
- X-Frame-Options: Prevent clickjacking attacks
- X-XSS-Protection: Enable browser XSS protection
- Strict-Transport-Security: Enforce HTTPS connections
- Content-Security-Policy: Control resource loading

Validates Requirement 8.5
"""
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses.
    
    Security headers protect against:
    - MIME type sniffing attacks (X-Content-Type-Options)
    - Clickjacking attacks (X-Frame-Options)
    - Cross-site scripting (X-XSS-Protection)
    - Man-in-the-middle attacks (Strict-Transport-Security)
    - Unauthorized resource loading (Content-Security-Policy)
    """
    
    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
        environment: str = "development",
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application instance
            enable_hsts: Enable Strict-Transport-Security header
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            enable_csp: Enable Content-Security-Policy header
            environment: Application environment (development, staging, production)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp
        self.environment = environment
        
        logger.info(
            f"Security headers middleware initialized: "
            f"HSTS={enable_hsts}, CSP={enable_csp}, env={environment}"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        # Browsers will not try to guess the MIME type, reducing exposure to drive-by downloads
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        # Prevents the page from being embedded in iframes on other domains
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable browser XSS filter
        # Modern browsers have built-in XSS protection, this enables it
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict-Transport-Security: Enforce HTTPS
        # Only add in production to avoid issues with local development
        if self.enable_hsts and self.environment == "production":
            # includeSubDomains: Apply to all subdomains
            # preload: Allow inclusion in browser HSTS preload lists
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )
        
        # Content-Security-Policy: Control resource loading
        if self.enable_csp:
            # Restrictive CSP policy:
            # - default-src 'self': Only load resources from same origin
            # - script-src 'self' 'unsafe-inline': Allow inline scripts (needed for some frameworks)
            # - style-src 'self' 'unsafe-inline': Allow inline styles (needed for some frameworks)
            # - img-src 'self' data: https:: Allow images from same origin, data URIs, and HTTPS
            # - font-src 'self' data:: Allow fonts from same origin and data URIs
            # - connect-src 'self': Only allow API calls to same origin
            # - frame-ancestors 'none': Prevent embedding in iframes (redundant with X-Frame-Options)
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers["Content-Security-Policy"] = csp_policy
        
        # Referrer-Policy: Control referrer information
        # strict-origin-when-cross-origin: Send full URL for same-origin, only origin for cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy: Control browser features
        # Disable potentially dangerous features like geolocation, camera, microphone
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response


def configure_security_headers(
    app: FastAPI,
    enable_hsts: bool = True,
    hsts_max_age: int = 31536000,
    enable_csp: bool = True,
    environment: str = "development",
) -> None:
    """
    Configure security headers middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
        enable_hsts: Enable Strict-Transport-Security header (default: True)
        hsts_max_age: HSTS max-age in seconds (default: 1 year)
        enable_csp: Enable Content-Security-Policy header (default: True)
        environment: Application environment (default: development)
    
    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> configure_security_headers(
        ...     app,
        ...     enable_hsts=True,
        ...     hsts_max_age=31536000,
        ...     enable_csp=True,
        ...     environment="production"
        ... )
    
    Validates Requirement 8.5
    """
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,
        hsts_max_age=hsts_max_age,
        enable_csp=enable_csp,
        environment=environment,
    )
    
    logger.info("Security headers middleware configured")
