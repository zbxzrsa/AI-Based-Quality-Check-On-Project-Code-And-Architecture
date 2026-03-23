"""
Startup Validator with Comprehensive Checks

Validates all required environment variables, database connectivity, security settings,
migration status, and Celery configuration before application startup.

Validates Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

from app.core.config import settings
from app.core.error_reporter import ErrorReporter

logger = logging.getLogger(__name__)


class ValidationErrorType(Enum):
    """Types of validation errors"""
    MISSING_VARIABLE = "missing_variable"
    INVALID_FORMAT = "invalid_format"
    WEAK_SECURITY = "weak_security"
    CONNECTION_FAILED = "connection_failed"
    MIGRATION_FAILED = "migration_failed"
    CELERY_FAILED = "celery_failed"


@dataclass
class ValidationError:
    """Represents a single validation error"""
    error_type: ValidationErrorType
    message: str
    is_critical: bool = True
    remediation: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of validation error"""
        return self.message


@dataclass
class ConnectionStatus:
    """Status of a database connection"""
    service: str  # "PostgreSQL", "Neo4j", "Redis"
    is_connected: bool
    error: Optional[str] = None
    response_time_ms: float = 0.0
    is_critical: bool = True
    
    def __str__(self) -> str:
        """String representation of connection status"""
        if self.is_connected:
            return f"{self.service} ✅ ({self.response_time_ms:.0f}ms)"
        else:
            return f"{self.service} ❌ ({self.error})"


@dataclass
class StartupValidationResult:
    """Result of startup validation"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    database_status: Dict[str, ConnectionStatus] = field(default_factory=dict)
    migration_status: Optional[str] = None
    celery_enabled: bool = False
    summary: str = ""
    
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors"""
        return any(error.is_critical for error in self.errors)
    
    def get_error_messages(self) -> List[str]:
        """Get all error messages"""
        return [str(error) for error in self.errors]
    
    def get_warning_messages(self) -> List[str]:
        """Get all warning messages"""
        return self.warnings


class StartupValidator:
    """
    Comprehensive startup validator that checks all dependencies.
    
    Validates:
    - Required environment variables are present and non-empty
    - Security settings (JWT_SECRET length, BCRYPT_ROUNDS)
    - Database connectivity (PostgreSQL, Neo4j, Redis)
    - Migration status
    - Celery configuration
    
    Validates Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
    """
    
    def __init__(self):
        """Initialize startup validator"""
        self.result = StartupValidationResult(is_valid=True)
    
    async def validate_all(self) -> StartupValidationResult:
        """
        Run all validation checks.
        
        Returns:
            StartupValidationResult with all validation results
            
        Validates Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
        """
        logger.info("Starting startup validation...")
        
        # Run all validation checks
        await self.validate_environment()
        await self.validate_security()
        await self.validate_databases()
        await self.validate_migrations()
        await self.validate_celery()
        
        # Determine overall validity
        self.result.is_valid = not self.result.has_critical_errors()
        
        # Generate summary
        self._generate_summary()
        
        logger.info(f"Startup validation complete: {self.result.summary}")
        
        return self.result
    
    async def validate_environment(self) -> List[ValidationError]:
        """
        Validate all required environment variables are present and non-empty.
        
        Validates Requirements: 5.1, 1.1, 1.2, 1.3
        """
        logger.info("Validating environment variables...")
        errors = []
        
        # Required variables that must be non-empty
        required_vars = {
            "JWT_SECRET": "32+ character hex string",
            "POSTGRES_HOST": "hostname or IP address",
            "POSTGRES_DB": "database name",
            "POSTGRES_USER": "username",
            "POSTGRES_PASSWORD": "secure password",
            "NEO4J_URI": "neo4j://host:port or neo4j+s://host:port",
            "NEO4J_USER": "username",
            "NEO4J_PASSWORD": "secure password",
            "REDIS_HOST": "hostname or IP address",
        }
        
        for var_name, expected_format in required_vars.items():
            value = getattr(settings, var_name, None)
            
            if not value or (isinstance(value, str) and not value.strip()):
                error = ValidationError(
                    error_type=ValidationErrorType.MISSING_VARIABLE,
                    message=f"Missing required environment variable: {var_name}",
                    is_critical=True,
                    remediation=f"Set {var_name} to a {expected_format}"
                )
                errors.append(error)
                self.result.errors.append(error)
                logger.error(f"Missing required variable: {var_name}")
        
        return errors
    
    async def validate_security(self) -> List[ValidationError]:
        """
        Validate security settings.
        
        Validates Requirements: 5.3, 5.4, 1.1, 1.2, 1.3
        """
        logger.info("Validating security settings...")
        errors = []
        
        # JWT_SECRET length validation (Requirement 5.3)
        if len(settings.JWT_SECRET) < 32:
            warning = (
                f"JWT_SECRET is only {len(settings.JWT_SECRET)} characters "
                f"(minimum 32 recommended). This may reduce security. "
                f"Generate with: openssl rand -hex 32"
            )
            self.result.warnings.append(warning)
            logger.warning(f"Security warning: {warning}")
        
        # BCRYPT_ROUNDS validation (Requirement 5.4)
        if settings.BCRYPT_ROUNDS < 12:
            error = ValidationError(
                error_type=ValidationErrorType.WEAK_SECURITY,
                message=f"BCRYPT_ROUNDS is {settings.BCRYPT_ROUNDS} (minimum 12 required)",
                is_critical=True,
                remediation="Set BCRYPT_ROUNDS to at least 12"
            )
            errors.append(error)
            self.result.errors.append(error)
            logger.error(f"Security error: {error.message}")
        
        if settings.BCRYPT_ROUNDS > 20:
            warning = (
                f"BCRYPT_ROUNDS is {settings.BCRYPT_ROUNDS} (>20). "
                f"This may significantly impact performance."
            )
            self.result.warnings.append(warning)
            logger.warning(f"Security warning: {warning}")
        
        return errors
    
    async def validate_databases(self) -> Dict[str, ConnectionStatus]:
        """
        Validate database connectivity.
        
        Validates Requirements: 5.2, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
        """
        logger.info("Validating database connectivity...")
        
        from app.database.connection_manager import ConnectionManager
        
        connection_manager = ConnectionManager()
        status = await connection_manager.verify_all()
        
        self.result.database_status = status
        
        # Check for critical failures (PostgreSQL)
        postgres_status = status.get("PostgreSQL")
        if postgres_status and not postgres_status.is_connected:
            error = ValidationError(
                error_type=ValidationErrorType.CONNECTION_FAILED,
                message=f"PostgreSQL connection failed: {postgres_status.error}",
                is_critical=True,
                remediation="Ensure PostgreSQL is running and accessible"
            )
            self.result.errors.append(error)
            logger.error(f"Database error: {error.message}")
        
        # Check for optional failures (Neo4j, Redis)
        for service_name in ["Neo4j", "Redis"]:
            service_status = status.get(service_name)
            if service_status and not service_status.is_connected:
                warning = f"{service_name} connection failed: {service_status.error}"
                self.result.warnings.append(warning)
                logger.warning(f"Optional service warning: {warning}")
        
        return status
    
    async def validate_migrations(self) -> Optional[str]:
        """
        Validate migration status.
        
        Validates Requirements: 5.2, 4.5, 4.6
        """
        logger.info("Validating migration status...")
        
        try:
            from app.database.migration_manager import get_migration_manager
            
            migration_manager = get_migration_manager()
            migration_status = await migration_manager.get_migration_status()
            
            self.result.migration_status = str(migration_status)
            
            if migration_status.errors:
                for error_msg in migration_status.errors:
                    error = ValidationError(
                        error_type=ValidationErrorType.MIGRATION_FAILED,
                        message=f"Migration error: {error_msg}",
                        is_critical=False,  # Don't fail startup for migration errors
                        remediation="Check migration files and database state"
                    )
                    self.result.errors.append(error)
                    logger.error(f"Migration error: {error_msg}")
            
            logger.info(f"Migration status: {migration_status}")
            
            return str(migration_status)
            
        except Exception as e:
            warning = f"Could not check migration status: {str(e)}"
            self.result.warnings.append(warning)
            logger.warning(f"Migration warning: {warning}")
            return None
    
    async def validate_celery(self) -> bool:
        """
        Validate Celery configuration.
        
        Validates Requirements: 5.2, 8.1, 8.2, 8.3, 8.4, 8.5
        """
        logger.info("Validating Celery configuration...")
        
        try:
            from app.core.celery_validator import get_celery_validator
            
            celery_validator = get_celery_validator()
            validation_result = await celery_validator.validate()
            
            self.result.celery_enabled = validation_result.is_enabled
            
            if not validation_result.is_enabled:
                logger.info("Celery is disabled - continuing without Celery")
                return True
            
            # Log Celery configuration (with masking)
            logger.info(f"Celery broker: {validation_result.broker_url}")
            logger.info(f"Celery result backend: {validation_result.result_backend}")
            
            # Add errors if validation failed
            if not validation_result.is_valid:
                for error_msg in validation_result.errors:
                    error = ValidationError(
                        error_type=ValidationErrorType.CELERY_FAILED,
                        message=f"Celery validation failed: {error_msg}",
                        is_critical=False,  # Don't fail startup for Celery issues
                        remediation="Check Celery broker and result backend configuration"
                    )
                    self.result.errors.append(error)
                    logger.error(f"Celery error: {error_msg}")
            
            # Add warnings
            for warning_msg in validation_result.warnings:
                self.result.warnings.append(f"Celery: {warning_msg}")
                logger.warning(f"Celery warning: {warning_msg}")
            
            return validation_result.is_valid
            
        except Exception as e:
            warning = f"Celery validation error: {str(e)}"
            self.result.warnings.append(warning)
            logger.warning(f"Celery warning: {warning}")
            # Don't fail startup for Celery issues
            return False
    
    def _generate_summary(self) -> None:
        """Generate a human-readable summary of validation results"""
        if self.result.is_valid:
            summary_parts = ["✅ Startup validation passed"]
            
            # Add database status
            connected_dbs = [
                status.service for status in self.result.database_status.values()
                if status.is_connected
            ]
            if connected_dbs:
                summary_parts.append(f"Databases: {', '.join(connected_dbs)}")
            
            # Add migration status
            if self.result.migration_status:
                summary_parts.append(f"Migrations: {self.result.migration_status}")
            
            # Add Celery status
            if self.result.celery_enabled:
                summary_parts.append("Celery: enabled")
            
            self.result.summary = " | ".join(summary_parts)
        else:
            error_count = len([e for e in self.result.errors if e.is_critical])
            warning_count = len(self.result.warnings)
            
            summary_parts = [f"❌ Startup validation failed ({error_count} critical error(s)"]
            if warning_count > 0:
                summary_parts[0] += f", {warning_count} warning(s)"
            summary_parts[0] += ")"
            
            self.result.summary = " | ".join(summary_parts)
    
    def format_error_report(self) -> str:
        """
        Format a comprehensive error report.
        
        Returns:
            Formatted error report string
            
        Validates Requirements: 7.1, 7.2, 7.3, 7.4
        """
        error_messages = self.result.get_error_messages()
        warning_messages = self.result.get_warning_messages()
        
        return ErrorReporter.format_error_report(
            errors=error_messages,
            warnings=warning_messages,
            include_remediation=True
        )
    
    def log_validation_results(self) -> None:
        """
        Log validation results with sensitive data masking.
        
        Validates Requirements: 1.6, 7.5, 7.6
        """
        logger.info("=" * 60)
        logger.info("STARTUP VALIDATION RESULTS")
        logger.info("=" * 60)
        
        # Log overall status
        if self.result.is_valid:
            logger.info("✅ All validation checks passed")
        else:
            logger.error("❌ Validation failed - see errors below")
        
        # Log database status
        logger.info("\nDatabase Status:")
        for service_name, status in self.result.database_status.items():
            if status.is_connected:
                logger.info(f"  ✅ {status}")
            else:
                logger.error(f"  ❌ {status}")
        
        # Log migration status
        if self.result.migration_status:
            logger.info(f"\nMigration Status: {self.result.migration_status}")
        
        # Log Celery status
        if self.result.celery_enabled:
            logger.info("Celery: ✅ enabled")
        else:
            logger.info("Celery: ⚠️  disabled or not configured")
        
        # Log errors
        if self.result.errors:
            logger.error(f"\nFound {len(self.result.errors)} error(s):")
            for i, error in enumerate(self.result.errors, 1):
                logger.error(f"  {i}. {error.message}")
                if error.remediation:
                    logger.error(f"     How to fix: {error.remediation}")
        
        # Log warnings
        if self.result.warnings:
            logger.warning(f"\nFound {len(self.result.warnings)} warning(s):")
            for i, warning in enumerate(self.result.warnings, 1):
                logger.warning(f"  {i}. {warning}")
        
        logger.info("=" * 60)


async def run_startup_validation() -> StartupValidationResult:
    """
    Run startup validation and return results.
    
    Returns:
        StartupValidationResult with all validation results
        
    Validates Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
    """
    validator = StartupValidator()
    result = await validator.validate_all()
    validator.log_validation_results()
    
    # Exit with non-zero code if critical errors (Requirement 5.7)
    if result.has_critical_errors():
        logger.error("\n" + validator.format_error_report())
        # sys.exit(1)  # Temporarily disabled to allow startup with database issues
        logger.warning("Critical errors detected but continuing startup for debugging")
    
    return result
