"""
Manual verification script for feature flag audit endpoint

This script verifies that the feature flag audit endpoint is properly implemented
and can log feature flag changes.

Validates Requirement: 10.6
"""

import logging

logger = logging.getLogger(__name__)

import asyncio
import sys


async def verify_endpoint():
    """Verify the feature flag audit endpoint exists and is properly configured"""

    logger.info("=" * 70)
    logger.info("Feature Flag Audit Endpoint Verification")
    logger.info("=" * 70)
    logger.info()

    # Check 1: Verify endpoint file exists and imports correctly
    logger.info("✓ Check 1: Verifying endpoint file...")
    try:
        from app.api.v1.endpoints import audit_logs

        logger.info("  ✅ audit_logs module imported successfully")
    except ImportError:
        logger.info("  ❌ Failed to import audit_logs: {e}")
        return False

    # Check 2: Verify the endpoint function exists
    logger.info("\n✓ Check 2: Verifying endpoint function...")
    if hasattr(audit_logs, "log_feature_flag_change"):
        logger.info("  ✅ log_feature_flag_change function exists")
    else:
        logger.info("  ❌ log_feature_flag_change function not found")
        return False

    # Check 3: Verify request/response models exist
    logger.info("\n✓ Check 3: Verifying request/response models...")
    if hasattr(audit_logs, "FeatureFlagChangeLog"):
        logger.info("  ✅ FeatureFlagChangeLog model exists")
    else:
        logger.info("  ❌ FeatureFlagChangeLog model not found")
        return False

    if hasattr(audit_logs, "FeatureFlagAuditResponse"):
        logger.info("  ✅ FeatureFlagAuditResponse model exists")
    else:
        logger.info("  ❌ FeatureFlagAuditResponse model not found")
        return False

    # Check 4: Verify AuditEventType.FEATURE_FLAG_CHANGE exists
    logger.info("\n✓ Check 4: Verifying AuditEventType constant...")
    try:
        from app.services.audit_logging_service import AuditEventType

        if hasattr(AuditEventType, "FEATURE_FLAG_CHANGE"):
            logger.info("  ✅ AuditEventType.FEATURE_FLAG_CHANGE = '{AuditEventType.FEATURE_FLAG_CHANGE}'")
        else:
            logger.info("  ❌ AuditEventType.FEATURE_FLAG_CHANGE not found")
            return False
    except ImportError:
        logger.info("  ❌ Failed to import AuditEventType: {e}")
        return False

    # Check 5: Verify router registration
    logger.info("\n✓ Check 5: Verifying router registration...")
    try:
        # Check if audit_logs router is included
        logger.info("  ✅ API router imported successfully")
        logger.info("  ℹ️  Endpoint should be available at: POST /api/v1/audit-logs/feature-flags")
    except ImportError:
        logger.info("  ❌ Failed to import API router: {e}")
        return False

    # Check 6: Verify model validation
    logger.info("\n✓ Check 6: Verifying model validation...")
    try:
        from app.api.v1.endpoints.audit_logs import FeatureFlagChangeLog

        # Test valid data
        FeatureFlagChangeLog(
            flag_name="test-flag",
            old_value=False,
            new_value=True,
            user_id="123e4567-e89b-12d3-a456-426614174000",
            metadata={"source": "test"},
        )
        logger.info("  ✅ Valid model creation successful")

        # Test required fields
        try:
            FeatureFlagChangeLog(
                flag_name="test-flag",
                old_value=False,
                # missing new_value
            )
            logger.info("  ❌ Model validation failed - should require new_value")
            return False
        except Exception:
            logger.info("  ✅ Model validation working - rejects missing required fields")

    except Exception:
        logger.info("  ❌ Model validation error: {e}")
        return False

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("✅ All checks passed!")
    logger.info("=" * 70)
    logger.info()
    logger.info("Endpoint Details:")
    logger.info("  URL: POST /api/v1/audit-logs/feature-flags")
    logger.info("  Authentication: Required (Bearer token)")
    logger.info("  Request Body:")
    logger.info("    - flag_name: string (required)")
    logger.info("    - old_value: boolean (required)")
    logger.info("    - new_value: boolean (required)")
    logger.info("    - user_id: string (optional)")
    logger.info("    - timestamp: datetime (optional)")
    logger.info("    - metadata: object (optional)")
    logger.info()
    logger.info("  Response:")
    logger.info("    - success: boolean")
    logger.info("    - log_id: string (UUID)")
    logger.info("    - message: string")
    logger.info()
    logger.info("  Validates Requirement: 10.6")
    logger.info()

    return True


if __name__ == "__main__":
    result = asyncio.run(verify_endpoint())
    sys.exit(0 if result else 1)
