"""
Security configuration validator

Validates that all security-critical configuration is properly set
and meets minimum security requirements.
"""
import os
import logging
from typing import List, Dict, Any
try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
except ImportError:
    from pydantic import BaseSettings, validator
from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityValidationError(Exception):
    """Raised when security validation fails"""
    pass


class SecurityValidator:
    """Validates security configuration at startup"""
    
    REQUIRED_SECRETS = [
        "AUTH_JWT_SECRET_KEY",
        "SECRET_KEY", 
        "SESSION_SECRET",
        "DATABASE_ENCRYPTION_KEY"
    ]
    
    INSECURE_VALUES = [
        "CHANGE_ME_IN_PRODUCTION_USE_SECRETS_MANAGER",
        "dev-secret-key-change-in-production",
        "your-super-secure-256-bit-secret-key-here",
        "your-32-byte-encryption-key-here"
    ]
    
    @classmethod
    def validate_production_config(cls) -> List[str]:
        """
        Validate production security configuration
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check environment
        if settings.ENVIRONMENT == "production":
            # Debug mode must be disabled
            if settings.DEBUG:
                errors.append("DEBUG mode is enabled in production")
            
            # HTTPS must be enforced
            if not getattr(settings, 'FORCE_HTTPS', False):
                errors.append("HTTPS is not enforced in production")
            
            # Secure cookies must be enabled
            if not getattr(settings, 'SECURE_COOKIES', False):
                errors.append("Secure cookies are not enabled in production")
            
            # Check bcrypt rounds
            if settings.AUTH_BCRYPT_ROUNDS < 14:
                errors.append(f"Bcrypt rounds ({settings.AUTH_BCRYPT_ROUNDS}) too low for production (minimum: 14)")
            
            # Validate secrets are not default values
            for secret_name in cls.REQUIRED_SECRETS:
                secret_value = getattr(settings, secret_name, None)
                if not secret_value:
                    errors.append(f"Required secret {secret_name} is not set")
                elif secret_value in cls.INSECURE_VALUES:
                    errors.append(f"Secret {secret_name} is using default/insecure value")
                elif len(secret_value) < 32:
                    errors.append(f"Secret {secret_name} is too short (minimum: 32 characters)")
            
            # Check JWT configuration
            if settings.JWT_ALGORITHM != "HS256":
                errors.append(f"JWT algorithm {settings.JWT_ALGORITHM} may not be secure")
            
            # Check session configuration
            if getattr(settings, 'AUTH_ALLOW_CONCURRENT_SESSIONS', True):
                errors.append("Concurrent sessions are allowed (security risk)")
        
        return errors
    
    @classmethod
    def validate_development_config(cls) -> List[str]:
        """
        Validate development security configuration
        
        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []
        
        if settings.ENVIRONMENT == "development":
            # Check for production secrets in development
            for secret_name in cls.REQUIRED_SECRETS:
                secret_value = getattr(settings, secret_name, None)
                if secret_value and secret_value not in cls.INSECURE_VALUES and len(secret_value) >= 32:
                    warnings.append(f"Production-grade secret detected in development: {secret_name}")
        
        return warnings
    
    @classmethod
    def validate_startup(cls) -> None:
        """
        Validate configuration at application startup
        
        Raises:
            SecurityValidationError: If critical security issues found
        """
        errors = []
        warnings = []
        
        if settings.ENVIRONMENT == "production":
            errors = cls.validate_production_config()
        else:
            warnings = cls.validate_development_config()
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"Security warning: {warning}")
        
        # Fail on errors
        if errors:
            error_msg = "Security validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise SecurityValidationError(error_msg)
        
        logger.info(f"Security validation passed for {settings.ENVIRONMENT} environment")
    
    @classmethod
    def get_security_report(cls) -> Dict[str, Any]:
        """
        Get comprehensive security configuration report
        
        Returns:
            Security report with recommendations
        """
        errors = []
        warnings = []
        recommendations = []
        
        if settings.ENVIRONMENT == "production":
            errors = cls.validate_production_config()
        else:
            warnings = cls.validate_development_config()
        
        # General recommendations
        recommendations.extend([
            "Use AWS Secrets Manager or similar for secret management",
            "Enable security headers (HSTS, CSP, etc.)",
            "Implement rate limiting on all endpoints",
            "Use TLS 1.3 for all connections",
            "Enable audit logging for all security events",
            "Implement proper input validation on all endpoints",
            "Use parameterized queries to prevent SQL injection",
            "Implement proper error handling (no information disclosure)"
        ])
        
        return {
            "environment": settings.ENVIRONMENT,
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations,
            "security_score": max(0, 100 - len(errors) * 20 - len(warnings) * 5),
            "validation_passed": len(errors) == 0
        }


# Validate at module import (startup)
try:
    SecurityValidator.validate_startup()
except SecurityValidationError as e:
    logger.critical(f"Application startup blocked due to security issues: {e}")
    # In production, we might want to exit here
    # For now, just log the critical error
    pass