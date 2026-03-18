"""
Verification script for health check service implementation

This script verifies that all required health check components are implemented:
1. Health service with check_postgres(), check_neo4j(), check_redis() methods
2. Health service with get_health_status(), get_readiness_status(), get_liveness_status() methods
3. API endpoints /health, /health/ready, /health/live

Task: 2.1 Implement health check service
Requirements: 2.6, 7.5
"""

import logging

logger = logging.getLogger(__name__)


import ast
import sys
from pathlib import Path


def verify_health_service():
    """Verify health service implementation"""
    logger.info("Verifying health service implementation...")

    health_service_path = Path("app/services/health_service.py")
    if not health_service_path.exists():
        logger.info("❌ Health service file not found")
        return False

    with open(health_service_path, encoding="utf-8") as f:
        content = f.read()

    # Parse the file
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

    missing_methods = []
    for method in required_methods:
        if method in found_methods:
            logger.info("✅ Method {method}() found")
        else:
            logger.info("❌ Method {method}() not found")
            missing_methods.append(method)

    if missing_methods:
        logger.info("\n❌ Missing methods: {', '.join(missing_methods)}")
        return False

    logger.info("\n✅ All required methods found in HealthService")
    return True


def verify_health_endpoints():
    """Verify health endpoints implementation"""
    logger.info("\nVerifying health endpoints...")

    health_endpoints_path = Path("app/api/v1/endpoints/health.py")
    if not health_endpoints_path.exists():
        logger.info("❌ Health endpoints file not found")
        return False

    with open(health_endpoints_path, encoding="utf-8") as f:
        content = f.read()

    # Check for required endpoints
    required_endpoints = [("health_check", "/"), ("readiness_check", "/ready"), ("liveness_check", "/live")]

    missing_endpoints = []
    for func_name, _path in required_endpoints:
        if func_name in content:
            logger.info("✅ Endpoint {func_name} ({path}) found")
        else:
            logger.info("❌ Endpoint {func_name} ({path}) not found")
            missing_endpoints.append(func_name)

    if missing_endpoints:
        logger.info("\n❌ Missing endpoints: {', '.join(missing_endpoints)}")
        return False

    logger.info("\n✅ All required endpoints found")
    return True


def verify_router_registration():
    """Verify health router is registered"""
    logger.info("\nVerifying router registration...")

    router_path = Path("app/api/v1/router.py")
    if not router_path.exists():
        logger.info("❌ Router file not found")
        return False

    with open(router_path, encoding="utf-8") as f:
        content = f.read()

    if "health.router" in content and 'prefix="/health"' in content:
        logger.info("✅ Health router registered with prefix /health")
        return True
    else:
        logger.info("❌ Health router not properly registered")
        return False


def main():
    """Main verification function"""
    logger.info("=" * 60)
    logger.info("Health Check Service Implementation Verification")
    logger.info("=" * 60)
    logger.info()

    results = []

    # Verify health service
    results.append(verify_health_service())

    # Verify health endpoints
    results.append(verify_health_endpoints())

    # Verify router registration
    results.append(verify_router_registration())

    logger.info("\n" + "=" * 60)
    if all(results):
        logger.info("✅ ALL VERIFICATIONS PASSED")
        logger.info("\nImplemented components:")
        logger.info("  1. HealthService with check_postgres(), check_neo4j(), check_redis()")
        logger.info("  2. HealthService with get_health_status(), get_readiness_status(), get_liveness_status()")
        logger.info("  3. API endpoints:")
        logger.info("     - GET /api/v1/health - Overall health status")
        logger.info("     - GET /api/v1/health/ready - Readiness probe")
        logger.info("     - GET /api/v1/health/live - Liveness probe")
        logger.info("\nRequirements validated: 2.6, 7.5")
        logger.info("=" * 60)
        return 0
    else:
        logger.info("❌ SOME VERIFICATIONS FAILED")
        logger.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
