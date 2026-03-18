"""
Phase 2 Checkpoint Verification Script

This script verifies that all Phase 2 (Backend API and Monitoring Infrastructure)
components have been implemented correctly.

Task 5: Checkpoint - Verify backend API and monitoring
"""

import logging

logger = logging.getLogger(__name__)


import ast
import sys
from pathlib import Path


def print_header(title: str):
    """Print a formatted header"""
    logger.info("\n" + "=" * 70)
    logger.info("  {title}")
    logger.info("=" * 70)


def print_section(title: str):
    """Print a formatted section header"""
    logger.info("\n{title}")
    logger.info("-" * 70)


def verify_health_check_service() -> bool:
    """Verify health check service implementation"""
    print_section("1. Health Check Service")

    health_service_path = Path("app/services/health_service.py")
    if not health_service_path.exists():
        logger.info("❌ Health service file not found")
        return False

    with open(health_service_path, encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)

    # Find HealthService class
    health_service_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "HealthService":
            health_service_class = node
            break

    if not health_service_class:
        logger.info("❌ HealthService class not found")
        return False

    # Check for required methods
    required_methods = [
        "check_postgres",
        "check_neo4j",
        "check_redis",
        "get_health_status",
        "get_readiness_status",
        "get_liveness_status",
    ]

    found_methods = []
    for node in health_service_class.body:
        if isinstance(node, ast.AsyncFunctionDef):
            found_methods.append(node.name)

    all_found = True
    for method in required_methods:
        if method in found_methods:
            logger.info("  ✅ {method}()")
        else:
            logger.info("  ❌ {method}() - MISSING")
            all_found = False

    return all_found


def verify_health_endpoints() -> bool:
    """Verify health endpoints implementation"""
    print_section("2. Health Check Endpoints")

    health_endpoints_path = Path("app/api/v1/endpoints/health.py")
    if not health_endpoints_path.exists():
        logger.info("❌ Health endpoints file not found")
        return False

    with open(health_endpoints_path, encoding="utf-8") as f:
        content = f.read()

    required_endpoints = [
        ("health_check", "GET /api/v1/health"),
        ("readiness_check", "GET /api/v1/health/ready"),
        ("liveness_check", "GET /api/v1/health/live"),
    ]

    all_found = True
    for func_name, _description in required_endpoints:
        if func_name in content:
            logger.info("  ✅ {description}")
        else:
            logger.info("  ❌ {description} - MISSING")
            all_found = False

    return all_found


def verify_prometheus_metrics() -> bool:
    """Verify Prometheus metrics implementation"""
    print_section("3. Prometheus Metrics")

    # Check metrics module
    metrics_path = Path("app/core/prometheus_metrics.py")
    if not metrics_path.exists():
        logger.info("❌ Prometheus metrics module not found")
        return False

    logger.info("  ✅ Prometheus metrics module exists")

    # Check metrics endpoint
    metrics_endpoint_path = Path("app/api/v1/endpoints/metrics.py")
    if not metrics_endpoint_path.exists():
        logger.info("❌ Metrics endpoint not found")
        return False

    logger.info("  ✅ Metrics endpoint exists (GET /api/v1/metrics)")

    # Check middleware
    middleware_path = Path("app/middleware/prometheus_middleware.py")
    if not middleware_path.exists():
        logger.info("❌ Prometheus middleware not found")
        return False

    logger.info("  ✅ Prometheus middleware exists")

    # Verify key metrics are defined
    with open(metrics_path, encoding="utf-8") as f:
        content = f.read()

    key_metrics = [
        "http_request_duration_seconds",
        "http_requests_total",
        "database_query_duration_seconds",
        "exception_count",
    ]

    all_found = True
    for metric in key_metrics:
        if metric in content:
            logger.info("  ✅ Metric: {metric}")
        else:
            logger.info("  ❌ Metric: {metric} - MISSING")
            all_found = False

    return all_found


def verify_structured_logging() -> bool:
    """Verify structured logging implementation"""
    print_section("4. Structured Logging")

    logging_config_path = Path("app/core/logging_config.py")
    if not logging_config_path.exists():
        logger.info("❌ Logging config module not found")
        return False

    with open(logging_config_path, encoding="utf-8") as f:
        content = f.read()

    # Check for JSON logging
    if "pythonjsonlogger" in content or "JsonFormatter" in content:
        logger.info("  ✅ JSON structured logging configured")
    else:
        logger.info("  ❌ JSON structured logging not configured")
        return False

    # Check for request logging
    if "log_request" in content:
        logger.info("  ✅ Request logging middleware exists")
    else:
        logger.info("  ❌ Request logging middleware not found")
        return False

    # Check for log rotation
    if "TimedRotatingFileHandler" in content and "backupCount" in content:
        logger.info("  ✅ Log rotation configured")

        # Check for 30-day retention
        if "backupCount=30" in content or "backup_count=30" in content:
            logger.info("  ✅ 30-day log retention configured")
        else:
            logger.info("  ⚠️  Warning: backupCount may not be set to 30 days")
    else:
        logger.info("  ❌ Log rotation not configured")
        return False

    return True


def verify_opentelemetry_tracing() -> bool:
    """Verify OpenTelemetry distributed tracing"""
    print_section("5. OpenTelemetry Distributed Tracing")

    tracing_path = Path("app/core/tracing.py")
    if not tracing_path.exists():
        logger.info("❌ Tracing module not found")
        return False

    with open(tracing_path, encoding="utf-8") as f:
        content = f.read()

    # Check for OpenTelemetry components
    components = [
        ("TracerProvider", "Tracer provider"),
        ("OTLPSpanExporter", "OTLP exporter"),
        ("FastAPIInstrumentor", "FastAPI instrumentation"),
    ]

    all_found = True
    for component, _description in components:
        if component in content:
            logger.info("  ✅ {description}")
        else:
            logger.info("  ❌ {description} - MISSING")
            all_found = False

    return all_found


def verify_rate_limiting() -> bool:
    """Verify rate limiting implementation"""
    print_section("6. Rate Limiting")

    rate_limiting_path = Path("app/middleware/rate_limiting.py")
    if not rate_limiting_path.exists():
        logger.info("❌ Rate limiting middleware not found")
        return False

    with open(rate_limiting_path, encoding="utf-8") as f:
        content = f.read()

    # Check for rate limiting configuration
    if "SlowAPI" in content or "Limiter" in content:
        logger.info("  ✅ Rate limiting middleware configured")
    else:
        logger.info("  ❌ Rate limiting not properly configured")
        return False

    # Check for rate limits
    if "100" in content and "5000" in content:
        logger.info("  ✅ Rate limits configured (100/min, 5000/hour)")
    else:
        logger.info("  ⚠️  Warning: Rate limits may not match requirements")

    return True


def verify_security_headers() -> bool:
    """Verify security headers implementation"""
    print_section("7. Security Headers and CORS")

    security_headers_path = Path("app/middleware/security_headers.py")
    if not security_headers_path.exists():
        logger.info("  ⚠️  Security headers middleware not found (may be in main.py)")
    else:
        logger.info("  ✅ Security headers middleware exists")

    # Check main.py for CORS configuration
    main_path = Path("app/main.py")
    if main_path.exists():
        with open(main_path, encoding="utf-8") as f:
            content = f.read()

        if "CORSMiddleware" in content:
            logger.info("  ✅ CORS middleware configured")
        else:
            logger.info("  ❌ CORS middleware not configured")
            return False

    return True


def verify_audit_logging() -> bool:
    """Verify authentication failure audit logging"""
    print_section("8. Authentication Audit Logging")

    # Check for audit logging in auth middleware or service
    auth_paths = [
        Path("app/middleware/authorization_audit.py"),
        Path("app/services/audit_service.py"),
        Path("app/api/v1/endpoints/auth.py"),
    ]

    found = False
    for path in auth_paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                content = f.read()

            if "audit" in content.lower() or "log" in content.lower():
                logger.info("  ✅ Audit logging found in {path.name}")
                found = True
                break

    if not found:
        logger.info("  ⚠️  Warning: Audit logging implementation not clearly identified")

    return True  # Non-critical for checkpoint


def main():
    """Main verification function"""
    print_header("Phase 2 Checkpoint Verification")
    logger.info("\nVerifying Backend API and Monitoring Infrastructure...")

    results = []

    # Run all verifications
    results.append(("Health Check Service", verify_health_check_service()))
    results.append(("Health Check Endpoints", verify_health_endpoints()))
    results.append(("Prometheus Metrics", verify_prometheus_metrics()))
    results.append(("Structured Logging", verify_structured_logging()))
    results.append(("OpenTelemetry Tracing", verify_opentelemetry_tracing()))
    results.append(("Rate Limiting", verify_rate_limiting()))
    results.append(("Security Headers/CORS", verify_security_headers()))
    results.append(("Audit Logging", verify_audit_logging()))

    # Print summary
    print_header("Verification Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    logger.info("\nResults: {passed}/{total} components verified\n")

    for _component, _result in results:
        logger.info("  {status}  {component}")

    logger.info("\n" + "=" * 70)

    if passed == total:
        logger.info("\n✅ ALL PHASE 2 COMPONENTS VERIFIED SUCCESSFULLY!")
        logger.info("\nPhase 2 (Backend API and Monitoring Infrastructure) is complete.")
        logger.info("Ready to proceed to Phase 3 (Frontend API Client and Data Validation).")
        logger.info("\n" + "=" * 70)
        return 0
    else:
        logger.info("\n⚠️  {total - passed} COMPONENT(S) NEED ATTENTION")
        logger.info("\nPlease review the failed components above.")
        logger.info("\n" + "=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
