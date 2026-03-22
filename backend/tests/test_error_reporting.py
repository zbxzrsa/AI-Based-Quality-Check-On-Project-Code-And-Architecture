"""
Tests for Error Reporting Module

Tests error classification, masking, statistics, and reporting.
"""

import pytest
from datetime import datetime, timezone

from backend.tests.utils.secure_test_data import get_test_api_key, get_test_jwt_secret, get_test_password
from app.core.error_reporting import (
    DatabaseErrorCategory,
    DatabaseErrorInfo,
    ErrorReporter,
    ErrorStatistics,
    ErrorStatisticsManager,
    mask_sensitive_data,
)


class TestDatabaseErrorCategory:
    """Test error category enum"""

    def test_category_values(self):
        """Test all category values exist"""
        assert DatabaseErrorCategory.CONNECTION_TIMEOUT.value == "connection_timeout"
        assert DatabaseErrorCategory.AUTHENTICATION_FAILURE.value == "authentication_failure"
        assert DatabaseErrorCategory.NETWORK_ERROR.value == "network_error"
        assert DatabaseErrorCategory.POOL_EXHAUSTION.value == "pool_exhaustion"


class TestDatabaseErrorInfo:
    """Test DatabaseErrorInfo dataclass"""

    def test_create_error_info(self):
        """Test creating error info"""
        error_info = DatabaseErrorInfo(
            category=DatabaseErrorCategory.CONNECTION_TIMEOUT,
            component="PostgreSQL",
            message="Connection timed out",
            details={"host": "localhost"},
            timestamp=datetime.now(timezone.utc),
            resolution_steps=["Check network", "Increase timeout"],
        )

        assert error_info.category == DatabaseErrorCategory.CONNECTION_TIMEOUT
        assert error_info.component == "PostgreSQL"
        assert error_info.message == "Connection timed out"
        assert len(error_info.resolution_steps) == 2

    def test_error_info_validation(self):
        """Test error info validation"""
        with pytest.raises(ValueError, match="component is required"):
            DatabaseErrorInfo(
                category=DatabaseErrorCategory.NETWORK_ERROR,
                component="",
                message="Error",
                details={},
                timestamp=datetime.now(timezone.utc),
                resolution_steps=[],
            )

    def test_error_info_to_dict(self):
        """Test converting error info to dictionary"""
        error_info = DatabaseErrorInfo(
            category=DatabaseErrorCategory.AUTHENTICATION_FAILURE,
            component="Neo4j",
            message="Auth failed",
            details={},
            timestamp=datetime.now(timezone.utc),
            resolution_steps=["Check credentials"],
        )

        result = error_info.to_dict()
        assert result["category"] == "authentication_failure"
        assert result["component"] == "Neo4j"
        assert result["message"] == "Auth failed"


class TestErrorStatistics:
    """Test error statistics tracking"""

    def test_add_error(self):
        """Test adding errors to statistics"""
        stats = ErrorStatistics()
        error_info = DatabaseErrorInfo(
            category=DatabaseErrorCategory.NETWORK_ERROR,
            component="Redis",
            message="Network error",
            details={},
            timestamp=datetime.now(timezone.utc),
            resolution_steps=[],
        )

        stats.add_error(error_info)

        assert stats.error_counts[DatabaseErrorCategory.NETWORK_ERROR] == 1
        assert stats.component_errors["Redis"] == 1
        assert len(stats.recent_errors) == 1

    def test_multiple_errors(self):
        """Test tracking multiple errors"""
        stats = ErrorStatistics()

        for i in range(5):
            error_info = DatabaseErrorInfo(
                category=DatabaseErrorCategory.CONNECTION_TIMEOUT,
                component="PostgreSQL",
                message=f"Timeout {i}",
                details={},
                timestamp=datetime.now(timezone.utc),
                resolution_steps=[],
            )
            stats.add_error(error_info)

        assert stats.error_counts[DatabaseErrorCategory.CONNECTION_TIMEOUT] == 5
        assert stats.component_errors["PostgreSQL"] == 5

    def test_get_most_frequent_category(self):
        """Test finding most frequent error category"""
        stats = ErrorStatistics()

        # Add errors of different categories
        categories = [
            DatabaseErrorCategory.NETWORK_ERROR,
            DatabaseErrorCategory.NETWORK_ERROR,
            DatabaseErrorCategory.CONNECTION_TIMEOUT,
        ]

        for cat in categories:
            error_info = DatabaseErrorInfo(
                category=cat,
                component="Test",
                message="Error",
                details={},
                timestamp=datetime.now(timezone.utc),
                resolution_steps=[],
            )
            stats.add_error(error_info)

        most_frequent = stats.get_most_frequent_category()
        assert most_frequent == DatabaseErrorCategory.NETWORK_ERROR

    def test_recent_errors_limit(self):
        """Test that recent errors are limited to 50"""
        stats = ErrorStatistics()

        for i in range(60):
            error_info = DatabaseErrorInfo(
                category=DatabaseErrorCategory.NETWORK_ERROR,
                component="Test",
                message=f"Error {i}",
                details={},
                timestamp=datetime.now(timezone.utc),
                resolution_steps=[],
            )
            stats.add_error(error_info)

        assert len(stats.recent_errors) == 50


class TestMasking:
    """Test sensitive data masking"""

    def test_mask_password(self):
        """Test masking passwords"""
        test_password = get_test_password("error_reporting_mask")
        text = f"password={test_password} and other text"
        masked = mask_sensitive_data(text)
        assert test_password not in masked
        assert "***" in masked

    def test_mask_api_key(self):
        """Test masking API keys"""
        test_api_key = get_test_api_key("error_reporting")
        text = f"api_key={test_api_key}"
        masked = mask_sensitive_data(text)
        assert test_api_key not in masked

    def test_mask_token(self):
        """Test masking tokens"""
        test_token = get_test_jwt_secret()[:20]
        text = f"token={test_token}"
        masked = mask_sensitive_data(text)
        assert test_token not in masked

    def test_mask_database_url(self):
        """Test masking database URLs"""
        test_password = get_test_password("error_reporting_db_url")
        text = f"postgresql://user:{test_password}@localhost:5432/db"
        masked = mask_sensitive_data(text)
        assert test_password not in masked
        assert "***" in masked

    def test_no_masking_needed(self):
        """Test text without sensitive data"""
        text = "This is a normal error message"
        masked = mask_sensitive_data(text)
        assert masked == text


class TestErrorReporter:
    """Test error reporter functionality"""

    def test_classify_timeout_error(self):
        """Test classifying timeout errors"""
        reporter = ErrorReporter()

        error = TimeoutError("Connection timed out after 30s")
        category = reporter.classify_error(error)

        assert category == DatabaseErrorCategory.CONNECTION_TIMEOUT

    def test_classify_auth_error(self):
        """Test classifying authentication errors"""
        reporter = ErrorReporter()

        error = PermissionError("Access denied for user")
        category = reporter.classify_error(error)

        assert category == DatabaseErrorCategory.AUTHENTICATION_FAILURE

    def test_classify_network_error(self):
        """Test classifying network errors"""
        reporter = ErrorReporter()

        error = ConnectionError("Network unreachable")
        category = reporter.classify_error(error)

        assert category == DatabaseErrorCategory.NETWORK_ERROR

    def test_report_error(self):
        """Test reporting an error"""
        reporter = ErrorReporter()

        error = TimeoutError("Connection timeout")
        error_info = reporter.report_error(
            error=error,
            component="PostgreSQL",
            context={"query": "SELECT * FROM users"},
        )

        assert error_info.category == DatabaseErrorCategory.CONNECTION_TIMEOUT
        assert error_info.component == "PostgreSQL"
        assert "timeout" in error_info.message.lower()
        assert len(error_info.resolution_steps) > 0

    def test_get_statistics(self):
        """Test getting error statistics"""
        reporter = ErrorReporter()

        # Report some errors
        for i in range(3):
            error = ConnectionError(f"Network error {i}")
            reporter.report_error(error, component="Redis")

        stats = reporter.get_statistics()
        assert stats is not None

    def test_get_recent_errors(self):
        """Test getting recent errors"""
        reporter = ErrorReporter()

        # Report some errors
        for i in range(5):
            error = TimeoutError(f"Timeout {i}")
            reporter.report_error(error, component="PostgreSQL")

        recent = reporter.get_recent_errors(limit=3)
        assert len(recent) <= 3


class TestErrorStatisticsManager:
    """Test global statistics manager"""

    def test_singleton_pattern(self):
        """Test that error_stats is a global instance"""
        from app.core.error_reporting import error_stats

        assert isinstance(error_stats, ErrorStatisticsManager)

    def test_add_and_retrieve_error(self):
        """Test adding and retrieving errors"""
        manager = ErrorStatisticsManager()

        error_info = DatabaseErrorInfo(
            category=DatabaseErrorCategory.POOL_EXHAUSTION,
            component="PostgreSQL",
            message="Pool exhausted",
            details={},
            timestamp=datetime.now(timezone.utc),
            resolution_steps=["Increase pool size"],
        )

        manager.add_error(error_info)
        count = manager.get_error_count_by_category(DatabaseErrorCategory.POOL_EXHAUSTION)

        assert count == 1

    def test_clear_statistics(self):
        """Test clearing statistics"""
        manager = ErrorStatisticsManager()

        error_info = DatabaseErrorInfo(
            category=DatabaseErrorCategory.NETWORK_ERROR,
            component="Test",
            message="Error",
            details={},
            timestamp=datetime.now(timezone.utc),
            resolution_steps=[],
        )

        manager.add_error(error_info)
        manager.clear_statistics()

        stats = manager.get_statistics()
        assert len(stats.error_counts) == 0

    def test_to_dict(self):
        """Test exporting statistics to dictionary"""
        manager = ErrorStatisticsManager()

        error_info = DatabaseErrorInfo(
            category=DatabaseErrorCategory.CONFIGURATION_ERROR,
            component="Config",
            message="Invalid config",
            details={},
            timestamp=datetime.now(timezone.utc),
            resolution_steps=[],
        )

        manager.add_error(error_info)
        result = manager.to_dict()

        assert "error_counts" in result
        assert "configuration_error" in result["error_counts"]
