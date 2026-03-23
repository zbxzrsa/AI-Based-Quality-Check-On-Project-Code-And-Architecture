"""
Configuration validation module for startup checks.

This module validates all configuration settings on application startup
and fails fast if critical configuration is missing or invalid.

Validates Requirement 14.3: Implement configuration validation on startup
"""
import logging
import os
import sys
from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class PortConfig:
    """Port configuration for services."""
    backend_port: int
    frontend_port: int
    postgres_port: int
    redis_port: int
    neo4j_port: int


def get_config_validator(environment: str = "development") -> "ConfigValidator":
    """
    Factory function to create a ConfigValidator instance.
    
    Args:
        environment: Current environment (development, staging, production)
    
    Returns:
        ConfigValidator instance
    """
    return ConfigValidator(environment=environment)


class ConfigValidator:
    """
    Validates application configuration on startup.
    
    Features:
    - Validate required environment variables
    - Validate database connection strings
    - Validate API keys and secrets
    - Validate file paths and permissions
    - Validate numeric ranges
    - Fail fast on critical errors
    
    Validates Requirement 14.3
    """
    
    def __init__(self, environment: str = "development"):
        """
        Initialize configuration validator.
        
        Args:
            environment: Current environment (development, staging, production)
        """
        self.environment = environment
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_production = environment == "production"
    
    def validate_all(self, settings: Any) -> bool:
        """
        Run all validation checks.
        
        Args:
            settings: Settings object to validate
        
        Returns:
            True if validation passes, False otherwise
        
        Raises:
            ConfigValidationError: If critical validation fails
        """
        logger.info(f"Starting configuration validation for environment: {self.environment}")
        
        # Run all validation checks
        self.validate_environment(settings)
        self.validate_security_settings(settings)
        self.validate_database_config(settings)
        self.validate_redis_config(settings)
        self.validate_celery_config(settings)
        self.validate_api_keys(settings)
        self.validate_cors_config(settings)
        self.validate_ssl_config(settings)
        self.validate_encryption_config(settings)
        self.validate_logging_config(settings)
        self.validate_performance_config(settings)
        
        # Report results
        self._report_results()
        
        # Fail fast if there are errors
        if self.errors:
            error_msg = f"Configuration validation failed with {len(self.errors)} error(s)"
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)
        
        logger.info("✓ Configuration validation passed")
        return True
    
    def validate_environment(self, settings: Any):
        """Validate environment-specific settings."""
        # Check environment value
        valid_environments = ["development", "staging", "production"]
        if settings.ENVIRONMENT not in valid_environments:
            self.errors.append(
                f"Invalid ENVIRONMENT: {settings.ENVIRONMENT}. "
                f"Must be one of: {', '.join(valid_environments)}"
            )
        
        # Production-specific checks
        if self.is_production:
            if settings.DEBUG:
                self.errors.append("DEBUG must be False in production")
            
            if settings.LOG_LEVEL == "DEBUG":
                self.warnings.append("LOG_LEVEL is DEBUG in production (should be INFO or WARNING)")
    
    def validate_security_settings(self, settings: Any):
        """Validate security-related settings."""
        # JWT Secret
        if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
            self.errors.append(
                f"JWT_SECRET must be at least 32 characters (current: {len(settings.JWT_SECRET)})"
            )
        
        # Check for default/weak secrets in production
        if self.is_production:
            weak_patterns = ["dev_", "test_", "change_in_production", "your_"]
            
            if any(pattern in settings.JWT_SECRET.lower() for pattern in weak_patterns):
                self.errors.append(
                    "JWT_SECRET appears to be a default/development value in production"
                )
        
        # JWT expiration
        if settings.JWT_EXPIRATION_HOURS > 168:  # 1 week
            self.warnings.append(
                f"JWT_EXPIRATION_HOURS is very long ({settings.JWT_EXPIRATION_HOURS} hours)"
            )
        
        # Bcrypt rounds
        if settings.BCRYPT_ROUNDS < 12:
            self.errors.append(
                f"BCRYPT_ROUNDS must be at least 12 (current: {settings.BCRYPT_ROUNDS})"
            )
        elif settings.BCRYPT_ROUNDS > 20:
            self.warnings.append(
                f"BCRYPT_ROUNDS is very high ({settings.BCRYPT_ROUNDS}) - may impact performance"
            )
    
    def validate_database_config(self, settings: Any):
        """Validate database configuration."""
        # PostgreSQL
        required_postgres = [
            ("POSTGRES_HOST", settings.POSTGRES_HOST),
            ("POSTGRES_DB", settings.POSTGRES_DB),
            ("POSTGRES_USER", settings.POSTGRES_USER),
            ("POSTGRES_PASSWORD", settings.POSTGRES_PASSWORD),
        ]
        
        for name, value in required_postgres:
            if not value:
                self.errors.append(f"{name} is required but not set")
        
        # Port validation
        if not (1 <= settings.POSTGRES_PORT <= 65535):
            self.errors.append(
                f"POSTGRES_PORT must be between 1 and 65535 (current: {settings.POSTGRES_PORT})"
            )
        
        # Neo4j
        required_neo4j = [
            ("NEO4J_URI", settings.NEO4J_URI),
            ("NEO4J_USER", settings.NEO4J_USER),
            ("NEO4J_PASSWORD", settings.NEO4J_PASSWORD),
        ]
        
        for name, value in required_neo4j:
            if not value:
                self.errors.append(f"{name} is required but not set")
        
        # Validate Neo4j URI format
        if settings.NEO4J_URI:
            if not settings.NEO4J_URI.startswith(("bolt://", "neo4j://", "bolt+s://", "neo4j+s://")):
                self.errors.append(
                    f"NEO4J_URI has invalid protocol (must start with bolt:// or neo4j://)"
                )
    
    def validate_redis_config(self, settings: Any):
        """Validate Redis configuration."""
        if not settings.REDIS_HOST:
            self.errors.append("REDIS_HOST is required but not set")
        
        if not (1 <= settings.REDIS_PORT <= 65535):
            self.errors.append(
                f"REDIS_PORT must be between 1 and 65535 (current: {settings.REDIS_PORT})"
            )
        
        # Redis password recommended in production
        if self.is_production and not settings.REDIS_PASSWORD:
            self.warnings.append("REDIS_PASSWORD not set in production (recommended for security)")
    
    def validate_celery_config(self, settings: Any):
        """Validate Celery configuration."""
        # If Celery is configured, validate both URLs
        if settings.CELERY_BROKER_URL or settings.CELERY_RESULT_BACKEND:
            if not settings.CELERY_BROKER_URL:
                self.errors.append("CELERY_BROKER_URL must be set if using Celery")
            
            if not settings.CELERY_RESULT_BACKEND:
                self.errors.append("CELERY_RESULT_BACKEND must be set if using Celery")
    
    def validate_api_keys(self, settings: Any):
        """Validate external API keys."""
        # Check if at least one LLM provider is configured
        has_openai = bool(settings.OPENAI_API_KEY)
        has_anthropic = bool(settings.ANTHROPIC_API_KEY)
        has_ollama = bool(settings.OLLAMA_BASE_URL)
        
        if not (has_openai or has_anthropic or has_ollama):
            self.warnings.append(
                "No LLM provider configured (OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_BASE_URL). "
                "LLM features will be disabled."
            )
        
        # GitHub integration
        if settings.GITHUB_TOKEN and not settings.GITHUB_WEBHOOK_SECRET:
            self.warnings.append(
                "GITHUB_TOKEN is set but GITHUB_WEBHOOK_SECRET is not. "
                "Webhook verification will fail."
            )
    
    def validate_cors_config(self, settings: Any):
        """Validate CORS configuration."""
        # Check for wildcard in production
        if self.is_production and "*" in settings.ALLOWED_ORIGINS:
            self.errors.append(
                "CORS allows all origins (*) in production. This is a security risk."
            )
        
        # Check for localhost in production
        if self.is_production:
            localhost_origins = [
                origin for origin in settings.ALLOWED_ORIGINS
                if "localhost" in origin or "127.0.0.1" in origin
            ]
            if localhost_origins:
                self.warnings.append(
                    f"CORS allows localhost origins in production: {localhost_origins}"
                )
        
        # Check credentials with wildcard
        if settings.CORS_ALLOW_CREDENTIALS and "*" in settings.ALLOWED_ORIGINS:
            self.errors.append(
                "CORS allows credentials with wildcard origin. This is not allowed by browsers."
            )
    
    def validate_ssl_config(self, settings: Any):
        """Validate SSL/TLS configuration."""
        if settings.SSL_ENABLED:
            if not settings.SSL_CERT_FILE:
                self.errors.append("SSL_CERT_FILE is required when SSL_ENABLED is true")
            
            if not settings.SSL_KEY_FILE:
                self.errors.append("SSL_KEY_FILE is required when SSL_ENABLED is true")
            
            # Check if files exist
            if settings.SSL_CERT_FILE:
                cert_path = Path(settings.SSL_CERT_FILE)
                if not cert_path.exists():
                    self.errors.append(f"SSL certificate file not found: {settings.SSL_CERT_FILE}")
            
            if settings.SSL_KEY_FILE:
                key_path = Path(settings.SSL_KEY_FILE)
                if not key_path.exists():
                    self.errors.append(f"SSL key file not found: {settings.SSL_KEY_FILE}")
        
        # Recommend SSL in production
        if self.is_production and not settings.SSL_ENABLED:
            self.warnings.append(
                "SSL/TLS is not enabled in production. "
                "Consider enabling or ensure ALB handles SSL termination."
            )
    
    def validate_encryption_config(self, settings: Any):
        """Validate encryption configuration."""
        if settings.ENCRYPTION_KEY:
            # Check if it looks like base64
            import base64
            try:
                decoded = base64.b64decode(settings.ENCRYPTION_KEY)
                if len(decoded) != 32:
                    self.errors.append(
                        f"ENCRYPTION_KEY must be 32 bytes when decoded (current: {len(decoded)} bytes)"
                    )
            except Exception:
                self.errors.append("ENCRYPTION_KEY is not valid base64")
        
        # Recommend encryption in production
        if self.is_production and not settings.ENCRYPTION_KEY:
            self.warnings.append(
                "ENCRYPTION_KEY not set in production. "
                "Data-at-rest encryption will be disabled."
            )
    
    def validate_logging_config(self, settings: Any):
        """Validate logging configuration."""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if settings.LOG_LEVEL not in valid_log_levels:
            self.errors.append(
                f"Invalid LOG_LEVEL: {settings.LOG_LEVEL}. "
                f"Must be one of: {', '.join(valid_log_levels)}"
            )
    
    def validate_performance_config(self, settings: Any):
        """Validate performance-related configuration."""
        # Rate limiting
        if settings.RATE_LIMIT_PER_MINUTE < 10:
            self.warnings.append(
                f"RATE_LIMIT_PER_MINUTE is very low ({settings.RATE_LIMIT_PER_MINUTE}). "
                "This may impact legitimate users."
            )
        elif settings.RATE_LIMIT_PER_MINUTE > 1000:
            self.warnings.append(
                f"RATE_LIMIT_PER_MINUTE is very high ({settings.RATE_LIMIT_PER_MINUTE}). "
                "Consider reducing for better protection."
            )
    
    def _report_results(self):
        """Report validation results."""
        if self.errors:
            logger.error("=" * 60)
            logger.error("CONFIGURATION VALIDATION ERRORS")
            logger.error("=" * 60)
            for i, error in enumerate(self.errors, 1):
                logger.error(f"{i}. {error}")
            logger.error("=" * 60)
        
        if self.warnings:
            logger.warning("=" * 60)
            logger.warning("CONFIGURATION VALIDATION WARNINGS")
            logger.warning("=" * 60)
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"{i}. {warning}")
            logger.warning("=" * 60)


def validate_configuration(settings: Any) -> bool:
    """
    Validate configuration on application startup.
    
    Args:
        settings: Settings object to validate
    
    Returns:
        True if validation passes
    
    Raises:
        ConfigValidationError: If validation fails
    
    Example:
        from app.core.config import settings
        from app.core.config_validator import validate_configuration
        
        # Validate on startup
        validate_configuration(settings)
    """
    validator = ConfigValidator(environment=settings.ENVIRONMENT)
    return validator.validate_all(settings)


def validate_required_env_vars(required_vars: List[str]) -> Dict[str, bool]:
    """
    Check if required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
    
    Returns:
        Dictionary mapping variable names to whether they are set
    
    Example:
        missing = validate_required_env_vars([
            "POSTGRES_PASSWORD",
            "JWT_SECRET",
            "OPENAI_API_KEY"
        ])
        
        if not all(missing.values()):
            logger.info("Missing required environment variables")
    """
    results = {}
    for var in required_vars:
        value = os.environ.get(var)
        results[var] = bool(value and value.strip())
    return results


def check_database_connectivity(settings: Any) -> Dict[str, bool]:
    """
    Check connectivity to all databases.
    
    Args:
        settings: Settings object with database configuration
    
    Returns:
        Dictionary mapping database names to connectivity status
    
    Example:
        connectivity = check_database_connectivity(settings)
        if not connectivity['postgresql']:
            logger.error("Cannot connect to PostgreSQL")
    """
    results = {
        'postgresql': False,
        'neo4j': False,
        'redis': False
    }
    
    # PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            connect_timeout=5
        )
        conn.close()
        results['postgresql'] = True
        logger.info("✓ PostgreSQL connectivity check passed")
    except Exception as e:
        logger.error(f"✗ PostgreSQL connectivity check failed: {e}")
    
    # Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        driver.verify_connectivity()
        driver.close()
        results['neo4j'] = True
        logger.info("✓ Neo4j connectivity check passed")
    except Exception as e:
        logger.error(f"✗ Neo4j connectivity check failed: {e}")
    
    # Redis
    try:
        import redis
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=settings.REDIS_DB,
            socket_connect_timeout=5
        )
        r.ping()
        results['redis'] = True
        logger.info("✓ Redis connectivity check passed")
    except Exception as e:
        logger.error(f"✗ Redis connectivity check failed: {e}")
    
    return results


def startup_validation(settings: Any, check_connectivity: bool = True):
    """
    Comprehensive startup validation.
    
    This function should be called during application startup to validate
    all configuration and fail fast if critical issues are found.
    
    Args:
        settings: Settings object to validate
        check_connectivity: Whether to check database connectivity
    
    Raises:
        ConfigValidationError: If validation fails
        SystemExit: If critical connectivity issues are found
    
    Example:
        from app.core.config_validator import startup_validation
        
        # In main.py or app startup
        startup_validation(settings)
    """
    logger.info("=" * 60)
    logger.info("STARTING APPLICATION CONFIGURATION VALIDATION")
    logger.info("=" * 60)
    
    # Validate configuration
    try:
        validate_configuration(settings)
    except ConfigValidationError as e:
        logger.critical(f"Configuration validation failed: {e}")
        logger.critical("Application cannot start with invalid configuration")
        sys.exit(1)
    
    # Check database connectivity if requested
    if check_connectivity:
        logger.info("\nChecking database connectivity...")
        connectivity = check_database_connectivity(settings)
        
        # Fail if critical databases are unreachable
        if not connectivity['postgresql']:
            logger.critical("Cannot connect to PostgreSQL - application cannot start")
            sys.exit(1)
        
        if not connectivity['redis']:
            logger.critical("Cannot connect to Redis - application cannot start")
            sys.exit(1)
        
        if not connectivity['neo4j']:
            logger.warning("Cannot connect to Neo4j - graph features will be disabled")
    
    logger.info("=" * 60)
    logger.info("✓ CONFIGURATION VALIDATION COMPLETE")
    logger.info("=" * 60)
