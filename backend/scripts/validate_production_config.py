import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Production Configuration Validator

This script validates that the application is properly configured for production deployment.
It checks for:
- Debug mode is disabled
- All required secrets are set
- Sensitive endpoints are disabled
- Security settings are enforced
- Performance parameters are optimized

Usage:
    python scripts/validate_production_config.py
"""

import os
import sys


class ProductionConfigValidator:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed_checks: list[str] = []

    def check_environment(self) -> bool:
        """Check ENVIRONMENT setting"""
        env = os.getenv("ENVIRONMENT", "").lower()
        if env != "production":
            self.errors.append(f"ENVIRONMENT must be 'production', got '{env}'")
            return False
        self.passed_checks.append("✓ ENVIRONMENT=production")
        return True

    def check_debug_disabled(self) -> bool:
        """Check DEBUG is disabled"""
        debug = os.getenv("DEBUG", "false").lower()
        if debug != "false":
            self.errors.append("DEBUG must be false in production")
            return False
        self.passed_checks.append("✓ DEBUG=false")
        return True

    def check_log_level(self) -> bool:
        """Check LOG_LEVEL is WARNING or ERROR"""
        log_level = os.getenv("LOG_LEVEL", "").upper()
        if log_level not in ["WARNING", "ERROR", "CRITICAL"]:
            self.warnings.append(f"LOG_LEVEL should be WARNING+ in production, got {log_level}")
            return False
        self.passed_checks.append(f"✓ LOG_LEVEL={log_level}")
        return True

    def check_reload_disabled(self) -> bool:
        """Check auto-reload is disabled"""
        reload = os.getenv("RELOAD", "false").lower()
        if reload != "false":
            self.errors.append("RELOAD must be false in production")
            return False
        self.passed_checks.append("✓ RELOAD=false")
        return True

    def check_required_secrets(self) -> bool:
        """Check all required secrets are set"""
        required_secrets = [
            "SECRET_KEY",
            "JWT_SECRET",
            "SESSION_SECRET",
            "POSTGRES_PASSWORD",
            "NEO4J_PASSWORD",
            "REDIS_PASSWORD",
            "ENCRYPTION_KEY",
        ]

        missing = []
        for secret in required_secrets:
            value = os.getenv(secret, "").strip()
            if not value:
                missing.append(secret)
            elif value.startswith("dev_") or value == "postgres" or value.startswith("localhost"):
                self.errors.append(f"{secret} contains development value: {value[:20]}...")
                missing.append(secret)

        if missing:
            self.errors.append(f"Missing or invalid required secrets: {', '.join(missing)}")
            return False

        self.passed_checks.append(f"✓ All {len(required_secrets)} required secrets are set")
        return True

    def check_database_url(self) -> bool:
        """Check database URLs are not localhost"""
        postgres_host = os.getenv("POSTGRES_HOST", "")
        neo4j_uri = os.getenv("NEO4J_URI", "")
        redis_host = os.getenv("REDIS_HOST", "")

        if "localhost" in postgres_host or "127.0.0.1" in postgres_host:
            self.errors.append(f"POSTGRES_HOST points to localhost: {postgres_host}")
            return False

        if "localhost" in neo4j_uri or "127.0.0.1" in neo4j_uri:
            self.errors.append(f"NEO4J_URI points to localhost: {neo4j_uri}")
            return False

        if "localhost" in redis_host or "127.0.0.1" in redis_host:
            self.errors.append(f"REDIS_HOST points to localhost: {redis_host}")
            return False

        self.passed_checks.append("✓ All database hosts are remote")
        return True

    def check_api_docs_disabled(self) -> bool:
        """Check API documentation URLs are disabled in code"""
        # This is checked in application code, warn user
        env = os.getenv("ENVIRONMENT", "")
        if env == "production":
            self.warnings.append("Verify: API documentation endpoints (/docs, /redoc) are disabled in FastAPI app")
            self.passed_checks.append("⚠ API docs should be disabled in code")
            return True
        return False

    def check_cors_configured(self) -> bool:
        """Check CORS is properly configured"""
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if not cors_origins:
            self.errors.append("CORS_ORIGINS not set")
            return False

        if cors_origins.strip() == "*":
            self.errors.append("CORS_ORIGINS cannot be '*' in production")
            return False

        if "localhost" in cors_origins or "127.0.0.1" in cors_origins:
            self.errors.append(f"CORS_ORIGINS contains localhost: {cors_origins}")
            return False

        self.passed_checks.append(f"✓ CORS restricted to: {cors_origins[:50]}...")
        return True

    def check_rate_limiting(self) -> bool:
        """Check rate limiting is configured"""
        rate_limit = os.getenv("RATE_LIMIT_PER_MINUTE", "")
        try:
            limit = int(rate_limit)
            if limit > 500:
                self.warnings.append(f"RATE_LIMIT_PER_MINUTE is very high: {limit}")
            self.passed_checks.append(f"✓ RATE_LIMIT_PER_MINUTE={limit}")
            return True
        except (ValueError, TypeError):
            self.errors.append("RATE_LIMIT_PER_MINUTE not set or invalid")
            return False

    def check_performance_params(self) -> bool:
        """Check performance parameters are production-grade"""
        issues = []

        # Check workers
        try:
            workers = int(os.getenv("WORKERS", "0"))
            if workers < 4:
                issues.append(f"WORKERS={workers} is too low (recommend 4-16)")
        except ValueError:
            issues.append("WORKERS not set or invalid")

        # Check pool size
        try:
            pool_size = int(os.getenv("DB_POOL_SIZE", "0"))
            if pool_size < 10:
                issues.append(f"DB_POOL_SIZE={pool_size} is too low (recommend 20+)")
        except ValueError:
            issues.append("DB_POOL_SIZE not set or invalid")

        # Check Celery concurrency
        try:
            celery_conc = int(os.getenv("CELERY_WORKER_CONCURRENCY", "0"))
            if celery_conc < 4:
                issues.append(f"CELERY_WORKER_CONCURRENCY={celery_conc} is too low (recommend 8+)")
        except ValueError:
            issues.append("CELERY_WORKER_CONCURRENCY not set or invalid")

        if issues:
            for issue in issues:
                self.warnings.append(issue)
            return False

        self.passed_checks.append("✓ Performance parameters are optimized")
        return True

    def check_monitoring_enabled(self) -> bool:
        """Check monitoring is enabled"""
        enable_metrics = os.getenv("ENABLE_METRICS", "false").lower()
        enable_tracing = os.getenv("ENABLE_TRACING", "false").lower()
        enable_cloudwatch = os.getenv("ENABLE_CLOUDWATCH", "false").lower()

        if enable_metrics != "true":
            self.warnings.append("ENABLE_METRICS not enabled")

        if enable_tracing != "true":
            self.warnings.append("ENABLE_TRACING not enabled")

        if enable_cloudwatch != "true":
            self.warnings.append("ENABLE_CLOUDWATCH not enabled")

        self.passed_checks.append("✓ Monitoring configuration verified")
        return True

    def check_ssl_tls(self) -> bool:
        """Check SSL/TLS configuration"""
        # In production, SSL should be terminated at ALB/Nginx
        ssl_enabled = os.getenv("SSL_ENABLED", "false").lower()
        if ssl_enabled == "true":
            self.warnings.append("SSL_ENABLED=true - Ensure SSL is properly configured or disabled at ALB")

        self.passed_checks.append("✓ SSL/TLS configuration verified")
        return True

    def validate(self) -> bool:
        """Run all validation checks"""
        logger.info("\n" + "=" * 70)
        logger.info("PRODUCTION CONFIGURATION VALIDATOR")
        logger.info("=" * 70 + "\n")

        checks = [
            self.check_environment,
            self.check_debug_disabled,
            self.check_log_level,
            self.check_reload_disabled,
            self.check_required_secrets,
            self.check_database_url,
            self.check_api_docs_disabled,
            self.check_cors_configured,
            self.check_rate_limiting,
            self.check_performance_params,
            self.check_monitoring_enabled,
            self.check_ssl_tls,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"Exception in {check.__name__}: {str(e)}")

        # Print results
        logger.info("PASSED CHECKS:")
        for check in self.passed_checks:
            logger.info("  {check}")

        if self.warnings:
            logger.info("\nWARNINGS:")
            for _warning in self.warnings:
                logger.info("  ⚠️  {warning}")

        if self.errors:
            logger.info("\nERRORS (BLOCKING):")
            for _error in self.errors:
                logger.info("  ❌ {error}")
            logger.info("\n" + "=" * 70)
            logger.info("VALIDATION FAILED - Fix errors before deploying to production")
            logger.info("=" * 70 + "\n")
            return False

        logger.info("\n" + "=" * 70)
        logger.info("✅ ALL PRODUCTION CONFIGURATION CHECKS PASSED")
        logger.info("=" * 70 + "\n")
        return True


def main():
    validator = ProductionConfigValidator()

    if validator.validate():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
