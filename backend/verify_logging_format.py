"""
Simple verification script for structured logging format

This script verifies that the logging system outputs JSON format correctly
without running the full test suite.
"""

import json
import logging
import sys
from io import StringIO
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.logging_config import (
    CustomJsonFormatter,
    clear_request_context,
    set_request_context,
)


def verify_json_logging():
    """Verify JSON logging format"""
    logger.info("=" * 70)
    logger.info("  Verifying JSON Structured Logging Format")
    logger.info("=" * 70)

    # Setup formatter
    formatter = CustomJsonFormatter(service_name="test-service")
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)

    # Create string buffer to capture log output
    log_buffer = StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Set request context
    set_request_context(request_id="req-test-123", user_id="user-test-456", correlation_id="corr-test-789")

    # Log a test message
    logger.info("Test log message", extra={"test_field": "test_value"})

    # Get log output
    log_output = log_buffer.getvalue().strip()

    logger.info("\nLog Output:")
    logger.info("-" * 70)
    logger.info(log_output)
    logger.info("-" * 70)

    # Parse JSON
    try:
        log_data = json.loads(log_output)
        logger.info("\n✅ Log output is valid JSON")
    except json.JSONDecodeError:
        logger.info("\n❌ Log output is not valid JSON: {e}")
        return False

    # Verify required fields
    logger.info("\nVerifying Required Fields:")
    logger.info("-" * 70)

    required_fields = {
        "timestamp": "Timestamp",
        "level": "Log level",
        "message": "Log message",
        "logger": "Logger name",
        "service_name": "Service name",
        "request_id": "Request ID",
        "user_id": "User ID",
        "correlation_id": "Correlation ID",
    }

    all_present = True
    for field, _description in required_fields.items():
        if field in log_data:
            log_data[field]
            logger.info("  ✅ {description:20} ({field}): {value}")
        else:
            logger.info("  ❌ {description:20} ({field}): MISSING")
            all_present = False

    # Verify values
    logger.info("\nVerifying Field Values:")
    logger.info("-" * 70)

    checks = [
        (log_data.get("level") == "INFO", "Log level is INFO"),
        (log_data.get("message") == "Test log message", "Message is correct"),
        (log_data.get("service_name") == "test-service", "Service name is correct"),
        (log_data.get("request_id") == "req-test-123", "Request ID is correct"),
        (log_data.get("user_id") == "user-test-456", "User ID is correct"),
        (log_data.get("correlation_id") == "corr-test-789", "Correlation ID is correct"),
        ("test_field" in log_data, "Extra fields are included"),
    ]

    all_correct = True
    for check, _description in checks:
        if check:
            logger.info("  ✅ {description}")
        else:
            logger.info("  ❌ {description}")
            all_correct = False

    # Cleanup
    clear_request_context()
    logger.removeHandler(handler)

    logger.info("\n" + "=" * 70)
    if all_present and all_correct:
        logger.info("✅ JSON STRUCTURED LOGGING VERIFICATION PASSED")
        logger.info("\nStructured logging is correctly configured with:")
        logger.info("  - JSON format output")
        logger.info("  - All required fields (timestamp, level, message, etc.)")
        logger.info("  - Request context tracking (request_id, user_id, correlation_id)")
        logger.info("  - Extra field support")
        logger.info("\nRequirement 7.1 validated: Structured JSON logging")
        logger.info("=" * 70)
        return True
    else:
        logger.info("❌ JSON STRUCTURED LOGGING VERIFICATION FAILED")
        logger.info("=" * 70)
        return False


def verify_log_rotation():
    """Verify log rotation configuration"""
    logger.info("\n" + "=" * 70)
    logger.info("  Verifying Log Rotation Configuration")
    logger.info("=" * 70)

    from logging.handlers import TimedRotatingFileHandler

    from app.core.logging_config import setup_logging

    # Setup logging
    setup_logging(level="INFO", enable_json=True)

    # Find TimedRotatingFileHandler
    root_logger = logging.getLogger()
    rotating_handlers = [h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)]

    if not rotating_handlers:
        logger.info("\n❌ No TimedRotatingFileHandler found")
        return False

    handler = rotating_handlers[0]

    logger.info("\nLog Rotation Configuration:")
    logger.info("-" * 70)
    logger.info("  File: {handler.baseFilename}")
    logger.info("  Rotation: {handler.when}")
    logger.info("  Interval: {handler.interval} seconds")
    logger.info("  Backup Count: {handler.backupCount} days")
    logger.info("  Suffix: {handler.suffix}")

    logger.info("\nVerifying Configuration:")
    logger.info("-" * 70)

    checks = [
        (handler.when == "MIDNIGHT", "Rotation at midnight"),
        (handler.interval == 86400, "Daily rotation (86400 seconds)"),
        (handler.backupCount == 30, "30-day retention"),
        (handler.suffix == "%Y-%m-%d", "Date suffix format"),
    ]

    all_correct = True
    for check, _description in checks:
        if check:
            logger.info("  ✅ {description}")
        else:
            logger.info("  ❌ {description}")
            all_correct = False

    logger.info("\n" + "=" * 70)
    if all_correct:
        logger.info("✅ LOG ROTATION VERIFICATION PASSED")
        logger.info("\nLog rotation is correctly configured:")
        logger.info("  - Daily rotation at midnight")
        logger.info("  - 30-day retention period")
        logger.info("  - Date-based file naming")
        logger.info("\nRequirement 7.6 validated: 30-day log retention")
        logger.info("=" * 70)
        return True
    else:
        logger.info("❌ LOG ROTATION VERIFICATION FAILED")
        logger.info("=" * 70)
        return False


def main():
    """Main verification function"""
    results = []

    # Verify JSON logging
    results.append(verify_json_logging())

    # Verify log rotation
    results.append(verify_log_rotation())

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("  VERIFICATION SUMMARY")
    logger.info("=" * 70)

    if all(results):
        logger.info("\n✅ ALL LOGGING VERIFICATIONS PASSED")
        logger.info("\nStructured logging implementation is complete and correct.")
        return 0
    else:
        logger.info("\n❌ SOME LOGGING VERIFICATIONS FAILED")
        logger.info("\nPlease review the failed checks above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
