"""
Unit tests for ErrorReporter with sensitive data masking and database error classification

Tests sensitive data masking in error messages, error message formatting,
remediation guidance, and database error classification functionality.

Validates Requirements: 5.1, 5.2, 5.3, 7.1, 7.2, 7.5
"""

import pytest
from datetime import datetime, timezone
from app.core.error_reporter import (
    ErrorReporter,
    SensitiveDataType,
    DatabaseErrorCategory,
    DatabaseErrorInfo,
)
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Constants for testing to avoid hard-coded credentials in literal strings
TEST_PASSWORD = get_test_password("test_password_123")
TEST_API_KEY = get_test_api_key("openai")
TEST_TOKEN = get_test_jwt_secret()[:20]
TEST_JWT_SECRET = get_test_jwt_secret()
TEST_WEBHOOK_SECRET = get_test_api_key("webhook")


class TestSensitiveDataMasking:
    """Test sensitive data masking functionality"""

    def test_mask_password_in_string(self):
        """Test masking of password patterns"""
        # Test password=value pattern
        input_str = f"Connection failed: password={TEST_PASSWORD}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_PASSWORD not in result
        assert "password=***" in result

    def test_mask_password_with_colon(self):
        """Test masking of password: value pattern"""
        input_str = f"Database error: password: {TEST_PASSWORD}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_PASSWORD not in result
        assert "password:" in result
        assert "***" in result

    def test_mask_api_key(self):
        """Test masking of API keys"""
        input_str = f"API Error: {TEST_API_KEY}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_API_KEY[3:] not in result
        assert "sk-***" in result

    def test_mask_github_token(self):
        """Test masking of GitHub tokens"""
        input_str = f"Token: ghp_{TEST_TOKEN}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_TOKEN not in result
        # The token pattern is masked, and "Token:" is also masked by generic token pattern
        assert "***" in result

    def test_mask_generic_token(self):
        """Test masking of generic token patterns"""
        input_str = f"Authorization token={TEST_TOKEN}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_TOKEN not in result
        assert "token=***" in result

    def test_mask_jwt_secret(self):
        """Test masking of JWT secrets"""
        input_str = f"JWT_SECRET={TEST_JWT_SECRET}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_JWT_SECRET not in result
        assert "JWT_SECRET=***" in result

    def test_mask_postgresql_connection_string(self):
        """Test masking of PostgreSQL connection strings"""
        input_str = "postgresql://user:password123@localhost:5432/mydb"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert "password123" not in result
        assert "localhost" in result
        assert "5432" in result
        assert "***" in result

    def test_mask_postgresql_asyncpg_connection_string(self):
        """Test masking of PostgreSQL asyncpg connection strings"""
        input_str = "postgresql+asyncpg://user:secretpass@db.example.com:5432/prod"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert "secretpass" not in result
        assert "db.example.com" in result
        assert "5432" in result

    def test_mask_redis_connection_string(self):
        """Test masking of Redis connection strings"""
        input_str = "redis://:myredispassword@redis-host:6379/0"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert "myredispassword" not in result
        assert "redis-host" in result
        assert "6379" in result

    def test_mask_webhook_secret(self):
        """Test masking of webhook secrets"""
        input_str = f"webhook_secret={TEST_WEBHOOK_SECRET}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_WEBHOOK_SECRET not in result
        assert "webhook_secret=***" in result

    def test_mask_multiple_sensitive_values(self):
        """Test masking multiple sensitive values in one string"""
        input_str = (
            f"Error: password={TEST_PASSWORD} and token={TEST_TOKEN} "
            "and postgresql://user:pass@host:5432/db"
        )
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_PASSWORD not in result
        assert TEST_TOKEN not in result
        assert "pass@" not in result
        assert "password=***" in result
        assert "token=***" in result

    def test_mask_case_insensitive(self):
        """Test that masking is case-insensitive for keywords"""
        input_str = f"PASSWORD={TEST_PASSWORD} Token={TEST_TOKEN}"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert TEST_PASSWORD not in result
        assert TEST_TOKEN not in result

    def test_no_masking_for_non_sensitive_data(self):
        """Test that non-sensitive data is not masked"""
        input_str = "Error occurred at host=localhost port=5432"
        result = ErrorReporter.mask_sensitive_data(input_str)
        assert "localhost" in result
        assert "5432" in result


class TestMaskConnectionString:
    """Test connection string masking"""

    def test_mask_postgresql_url(self):
        """Test masking PostgreSQL connection URL"""
        url = "postgresql://user:password@localhost:5432/mydb"
        result = ErrorReporter.mask_connection_string(url)
        assert "password" not in result
        assert "localhost" in result
        assert "5432" in result
        assert "***" in result

    def test_mask_postgresql_asyncpg_url(self):
        """Test masking PostgreSQL asyncpg connection URL"""
        url = "postgresql+asyncpg://admin:secretpass@db.example.com:5432/prod"
        result = ErrorReporter.mask_connection_string(url)
        assert "secretpass" not in result
        assert "db.example.com" in result

    def test_mask_redis_url(self):
        """Test masking Redis connection URL"""
        url = "redis://:mypassword@redis.example.com:6379"
        result = ErrorReporter.mask_connection_string(url)
        assert "mypassword" not in result
        assert "redis.example.com" in result
        assert "6379" in result

    def test_mask_mysql_url(self):
        """Test masking MySQL connection URL"""
        url = "mysql+pymysql://user:password@localhost:3306/db"
        result = ErrorReporter.mask_connection_string(url)
        assert "password" not in result
        assert "localhost" in result

    def test_mask_mongodb_url(self):
        """Test masking MongoDB connection URL"""
        url = "mongodb+srv://user:password@cluster.mongodb.net/db"
        result = ErrorReporter.mask_connection_string(url)
        assert "password" not in result
        assert "cluster.mongodb.net" in result

    def test_empty_connection_string(self):
        """Test handling of empty connection string"""
        result = ErrorReporter.mask_connection_string("")
        assert result == ""

    def test_none_connection_string(self):
        """Test handling of None connection string"""
        result = ErrorReporter.mask_connection_string(None)
        assert result is None


class TestMaskValue:
    """Test masking of individual values"""

    def test_mask_password_value(self):
        """Test masking password value"""
        result = ErrorReporter.mask_value("mysecret", SensitiveDataType.PASSWORD)
        assert result == "***"

    def test_mask_jwt_secret_value(self):
        """Test masking JWT secret value"""
        result = ErrorReporter.mask_value(TEST_PASSWORD, SensitiveDataType.JWT_SECRET)
        assert result == "***"

    def test_mask_api_key_with_show_first_last(self):
        """Test masking API key showing first and last characters"""
        result = ErrorReporter.mask_value(
            "sk-1234567890abcdefghijklmnop",
            SensitiveDataType.API_KEY,
            show_first=3,
            show_last=3
        )
        assert result.startswith("sk-")
        assert result.endswith("nop")
        assert "***" in result

    def test_mask_token_with_show_first(self):
        """Test masking token showing first characters"""
        result = ErrorReporter.mask_value(
            "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            SensitiveDataType.TOKEN,
            show_first=3,
            show_last=0
        )
        assert result.startswith("ghp")
        assert "***" in result

    def test_mask_empty_value(self):
        """Test masking empty value"""
        result = ErrorReporter.mask_value("", SensitiveDataType.PASSWORD)
        assert result == "***"


class TestFormatMissingVariableError:
    """Test formatting of missing variable errors"""

    def test_format_missing_jwt_secret(self):
        """Test formatting error for missing JWT_SECRET"""
        result = ErrorReporter.format_missing_variable_error(
            "JWT_SECRET",
            "32+ character hex string"
        )
        assert "JWT_SECRET" in result
        assert "ERROR" in result
        assert "32+ character hex string" in result
        assert "How to fix" in result

    def test_format_missing_password(self):
        """Test formatting error for missing password"""
        result = ErrorReporter.format_missing_variable_error(
            "POSTGRES_PASSWORD",
            "non-empty string"
        )
        assert "POSTGRES_PASSWORD" in result
        assert "ERROR" in result
        assert "non-empty string" in result

    def test_format_with_custom_remediation(self):
        """Test formatting with custom remediation guidance"""
        result = ErrorReporter.format_missing_variable_error(
            "MY_VAR",
            "specific format",
            remediation="Run: generate_value.sh"
        )
        assert "MY_VAR" in result
        assert "generate_value.sh" in result

    def test_format_includes_how_to_fix(self):
        """Test that formatted error includes 'How to fix' section"""
        result = ErrorReporter.format_missing_variable_error("TEST_VAR")
        assert "How to fix" in result


class TestFormatConnectionError:
    """Test formatting of connection errors"""

    def test_format_connection_refused_error(self):
        """Test formatting connection refused error"""
        error = Exception("Connection refused")
        result = ErrorReporter.format_connection_error(
            "PostgreSQL",
            error,
            "postgresql://user:pass@localhost:5432/db"
        )
        assert "PostgreSQL" in result
        assert "ERROR" in result
        assert "Connection refused" in result
        assert "Resolution Steps" in result  # Updated to match new format
        assert "pass" not in result  # Password should be masked

    def test_format_authentication_error(self):
        """Test formatting authentication error"""
        error = Exception("FATAL: password authentication failed")
        result = ErrorReporter.format_connection_error(
            "PostgreSQL",
            error
        )
        assert "authentication_failure" in result  # Updated to check for error category
        assert "username and password" in result.lower()  # Check for resolution steps content

    def test_format_timeout_error(self):
        """Test formatting timeout error"""
        error = Exception("Connection timeout after 5s")
        result = ErrorReporter.format_connection_error(
            "Redis",
            error
        )
        assert "timeout" in result.lower()
        assert "network connectivity" in result.lower()

    def test_format_hostname_resolution_error(self):
        """Test formatting hostname resolution error"""
        error = Exception("Cannot resolve hostname")
        result = ErrorReporter.format_connection_error(
            "Neo4j",
            error
        )
        assert "hostname" in result.lower()

    def test_format_optional_service_error(self):
        """Test formatting error for optional service"""
        error = Exception("Connection refused")
        result = ErrorReporter.format_connection_error(
            "Neo4j",
            error,
            is_critical=False
        )
        assert "WARNING" in result
        assert "ERROR" not in result

    def test_masks_connection_string_in_error(self):
        """Test that connection string is masked in error message"""
        error = Exception("Connection failed")
        result = ErrorReporter.format_connection_error(
            "PostgreSQL",
            error,
            "postgresql://user:secretpass@localhost:5432/db"
        )
        assert "secretpass" not in result
        assert "***" in result


class TestFormatValidationError:
    """Test formatting of validation errors"""

    def test_format_validation_error_basic(self):
        """Test basic validation error formatting"""
        result = ErrorReporter.format_validation_error(
            "JWT_SECRET",
            "Must be at least 32 characters"
        )
        assert "JWT_SECRET" in result
        assert "ERROR" in result
        assert "Must be at least 32 characters" in result
        assert "How to fix" in result

    def test_format_validation_error_with_current_value(self):
        """Test validation error with current value"""
        result = ErrorReporter.format_validation_error(
            "BCRYPT_ROUNDS",
            "Must be at least 12",
            current_value="8"
        )
        assert "BCRYPT_ROUNDS" in result
        assert "8" in result

    def test_format_validation_error_masks_sensitive_value(self):
        """Test that sensitive values are masked in validation error"""
        result = ErrorReporter.format_validation_error(
            "POSTGRES_PASSWORD",
            "Cannot be empty",
            current_value="password=mysecretpassword"
        )
        assert "mysecretpassword" not in result
        assert "***" in result

    def test_format_validation_error_with_expected_format(self):
        """Test validation error with expected format"""
        result = ErrorReporter.format_validation_error(
            "POSTGRES_PORT",
            "Invalid port number",
            expected_format="Integer between 1 and 65535"
        )
        assert "Integer between 1 and 65535" in result

    def test_format_validation_error_with_remediation(self):
        """Test validation error with custom remediation"""
        result = ErrorReporter.format_validation_error(
            "MY_SETTING",
            "Invalid value",
            remediation="Set to one of: option1, option2, option3"
        )
        assert "option1" in result


class TestFormatErrorReport:
    """Test formatting of comprehensive error reports"""

    def test_format_error_report_with_errors_only(self):
        """Test error report with only errors"""
        errors = [
            "Missing JWT_SECRET",
            "PostgreSQL connection failed"
        ]
        result = ErrorReporter.format_error_report(errors)
        assert "STARTUP VALIDATION FAILED" in result
        assert "Critical Errors:" in result
        assert "Missing JWT_SECRET" in result
        assert "PostgreSQL connection failed" in result

    def test_format_error_report_with_errors_and_warnings(self):
        """Test error report with both errors and warnings"""
        errors = ["Missing JWT_SECRET"]
        warnings = ["Neo4j connection failed (optional)"]
        result = ErrorReporter.format_error_report(errors, warnings)
        assert "Critical Errors:" in result
        assert "Warnings:" in result
        assert "Missing JWT_SECRET" in result
        assert "Neo4j connection failed" in result

    def test_format_error_report_includes_remediation(self):
        """Test that error report includes remediation guidance"""
        errors = ["Missing JWT_SECRET"]
        result = ErrorReporter.format_error_report(errors, include_remediation=True)
        assert "How to fix:" in result
        assert "Application startup aborted" in result

    def test_format_error_report_masks_sensitive_data(self):
        """Test that error report masks sensitive data"""
        errors = [
            f"Connection failed: password={TEST_PASSWORD}",
            f"Token error: token={TEST_TOKEN}"
        ]
        result = ErrorReporter.format_error_report(errors)
        assert TEST_PASSWORD not in result
        assert TEST_TOKEN not in result
        assert "password=***" in result
        assert "token=***" in result

    def test_format_error_report_without_remediation(self):
        """Test error report without remediation section"""
        errors = ["Error 1"]
        result = ErrorReporter.format_error_report(errors, include_remediation=False)
        assert "How to fix:" not in result
        assert "Application startup aborted" not in result


class TestFormatConfigurationSummary:
    """Test formatting of configuration summary"""

    def test_format_configuration_summary_basic(self):
        """Test basic configuration summary formatting"""
        config = {
            "APP_NAME": "MyApp",
            "DEBUG": True,
            "LOG_LEVEL": "INFO"
        }
        result = ErrorReporter.format_configuration_summary(config)
        assert "Configuration Summary:" in result
        assert "APP_NAME: MyApp" in result
        assert "DEBUG: True" in result

    def test_format_configuration_summary_masks_sensitive_keys(self):
        """Test that sensitive keys are masked in summary"""
        config = {
            "APP_NAME": "MyApp",
            "JWT_SECRET": f"jwt_secret={TEST_SECRET}",
            "POSTGRES_PASSWORD": f"password={TEST_PASSWORD}"
        }
        result = ErrorReporter.format_configuration_summary(config)
        assert "APP_NAME: MyApp" in result
        assert TEST_SECRET not in result
        assert TEST_PASSWORD not in result
        assert "JWT_SECRET:" in result
        assert "***" in result

    def test_format_configuration_summary_with_none_values(self):
        """Test configuration summary with None values"""
        config = {
            "OPTIONAL_KEY": None,
            "REQUIRED_KEY": "value"
        }
        result = ErrorReporter.format_configuration_summary(config)
        assert "(not set)" in result
        assert "REQUIRED_KEY: value" in result

    def test_format_configuration_summary_mask_all_values(self):
        """Test configuration summary with all values masked"""
        config = {
            "APP_NAME": "MyApp",
            "DEBUG": True
        }
        result = ErrorReporter.format_configuration_summary(config, mask_all_values=True)
        assert "MyApp" not in result
        assert "True" not in result


class TestIsSensitiveKey:
    """Test sensitive key detection"""

    def test_detect_password_key(self):
        """Test detection of password keys"""
        assert ErrorReporter._is_sensitive_key("POSTGRES_PASSWORD") is True
        assert ErrorReporter._is_sensitive_key("DB_PASSWORD") is True

    def test_detect_secret_key(self):
        """Test detection of secret keys"""
        assert ErrorReporter._is_sensitive_key("JWT_SECRET") is True
        assert ErrorReporter._is_sensitive_key("SECRET_KEY") is True

    def test_detect_token_key(self):
        """Test detection of token keys"""
        assert ErrorReporter._is_sensitive_key("GITHUB_TOKEN") is True
        assert ErrorReporter._is_sensitive_key("API_TOKEN") is True

    def test_detect_api_key(self):
        """Test detection of API keys"""
        assert ErrorReporter._is_sensitive_key("OPENAI_API_KEY") is True
        assert ErrorReporter._is_sensitive_key("API_KEY") is True

    def test_detect_non_sensitive_key(self):
        """Test that non-sensitive keys are not detected"""
        assert ErrorReporter._is_sensitive_key("APP_NAME") is False
        assert ErrorReporter._is_sensitive_key("DEBUG") is False
        assert ErrorReporter._is_sensitive_key("LOG_LEVEL") is False


class TestCollectErrors:
    """Test error collection and categorization"""

    def test_collect_errors_only(self):
        """Test collecting only errors"""
        error_list = [
            ("error", "Error 1", "Fix 1"),
            ("error", "Error 2", "Fix 2")
        ]
        errors, warnings = ErrorReporter.collect_errors(error_list)
        assert len(errors) == 2
        assert len(warnings) == 0
        assert "Error 1" in errors[0]
        assert "Fix 1" in errors[0]

    def test_collect_warnings_only(self):
        """Test collecting only warnings"""
        error_list = [
            ("warning", "Warning 1", "Fix 1"),
            ("warning", "Warning 2", "Fix 2")
        ]
        errors, warnings = ErrorReporter.collect_errors(error_list)
        assert len(errors) == 0
        assert len(warnings) == 2

    def test_collect_mixed_errors_and_warnings(self):
        """Test collecting mixed errors and warnings"""
        error_list = [
            ("error", "Error 1", "Fix 1"),
            ("warning", "Warning 1", "Fix 2"),
            ("error", "Error 2", None)
        ]
        errors, warnings = ErrorReporter.collect_errors(error_list)
        assert len(errors) == 2
        assert len(warnings) == 1

    def test_collect_errors_without_remediation(self):
        """Test collecting errors without remediation"""
        error_list = [
            ("error", "Error 1", None)
        ]
        errors, warnings = ErrorReporter.collect_errors(error_list)
        assert len(errors) == 1
        assert "Error 1" in errors[0]


class TestBatchReportErrors:
    """Test batch error reporting"""

    def test_batch_report_errors_basic(self):
        """Test basic batch error report"""
        errors = ["Error 1", "Error 2"]
        result = ErrorReporter.batch_report_errors(errors)
        assert "Startup Failed" in result
        assert "2 critical error(s)" in result
        assert "Error 1" in result
        assert "Error 2" in result

    def test_batch_report_errors_with_warnings(self):
        """Test batch error report with warnings"""
        errors = ["Error 1"]
        warnings = ["Warning 1", "Warning 2"]
        result = ErrorReporter.batch_report_errors(errors, warnings)
        assert "1 critical error(s)" in result
        assert "2 warning(s)" in result

    def test_batch_report_errors_masks_sensitive_data(self):
        """Test that batch report masks sensitive data"""
        errors = [f"Connection failed: password={TEST_PASSWORD}"]
        result = ErrorReporter.batch_report_errors(errors)
        assert TEST_PASSWORD not in result
        assert "password=***" in result

    def test_batch_report_errors_custom_service_name(self):
        """Test batch report with custom service name"""
        errors = ["Error 1"]
        result = ErrorReporter.batch_report_errors(errors, service_name="MyService")
        assert "MyService Startup Failed" in result

    def test_batch_report_errors_includes_next_steps(self):
        """Test that batch report includes next steps"""
        errors = ["Error 1"]
        result = ErrorReporter.batch_report_errors(errors)
        assert "Next steps:" in result
        assert "Review the errors" in result
        assert "Fix each issue" in result


class TestDatabaseErrorClassification:
    """Test database error classification functionality"""

    def test_classify_connection_timeout_error(self):
        """Test classification of connection timeout errors"""
        error = Exception("Connection timeout after 30 seconds")
        category = ErrorReporter.classify_database_error(error, "PostgreSQL")
        assert category == DatabaseErrorCategory.CONNECTION_TIMEOUT

    def test_classify_authentication_failure_error(self):
        """Test classification of authentication failure errors"""
        error = Exception("FATAL: password authentication failed")
        category = ErrorReporter.classify_database_error(error, "PostgreSQL")
        assert category == DatabaseErrorCategory.AUTHENTICATION_FAILURE

    def test_classify_encoding_error(self):
        """Test classification of encoding errors"""
        error = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        category = ErrorReporter.classify_database_error(error, "MigrationManager")
        assert category == DatabaseErrorCategory.ENCODING_ERROR

    def test_classify_compatibility_error(self):
        """Test classification of compatibility errors"""
        error = Exception("asyncpg version 0.25.0 is incompatible with Python 3.13")
        category = ErrorReporter.classify_database_error(error, "PostgreSQL")
        assert category == DatabaseErrorCategory.COMPATIBILITY_ERROR

    def test_classify_pool_exhaustion_error(self):
        """Test classification of pool exhaustion errors"""
        error = Exception("Connection pool exhausted, max connections reached")
        category = ErrorReporter.classify_database_error(error, "PostgreSQL")
        assert category == DatabaseErrorCategory.POOL_EXHAUSTION

    def test_classify_network_error(self):
        """Test classification of network errors"""
        error = Exception("Connection refused by host")
        category = ErrorReporter.classify_database_error(error, "Neo4j")
        assert category == DatabaseErrorCategory.NETWORK_ERROR

    def test_classify_configuration_error(self):
        """Test classification of configuration errors"""
        error = Exception("Invalid configuration parameter: missing required field")
        category = ErrorReporter.classify_database_error(error, "ConfigValidator")
        assert category == DatabaseErrorCategory.CONFIGURATION_ERROR

    def test_classify_migration_error(self):
        """Test classification of migration errors"""
        error = Exception("Migration failed: table 'users' already exists")
        category = ErrorReporter.classify_database_error(error, "MigrationManager")
        assert category == DatabaseErrorCategory.MIGRATION_ERROR

    def test_classify_health_check_error(self):
        """Test classification of health check errors"""
        error = Exception("Health check failed: database not responding")
        category = ErrorReporter.classify_database_error(error, "HealthService")
        assert category == DatabaseErrorCategory.HEALTH_CHECK_ERROR

    def test_classify_default_to_network_error(self):
        """Test that unknown errors default to network error"""
        error = Exception("Some unknown database error")
        category = ErrorReporter.classify_database_error(error, "Unknown")
        assert category == DatabaseErrorCategory.NETWORK_ERROR


class TestDatabaseErrorInfo:
    """Test database error info creation and handling"""

    def test_create_database_error_info(self):
        """Test creation of structured database error info"""
        error = Exception("Connection timeout")
        error_info = ErrorReporter.create_database_error_info(
            error, "PostgreSQL", {"host": "localhost", "password": f"password={TEST_PASSWORD}"}
        )
        
        assert error_info.component == "PostgreSQL"
        assert error_info.category == DatabaseErrorCategory.CONNECTION_TIMEOUT
        assert "Connection timeout" in error_info.message
        # Check that password is masked in connection_params
        if error_info.connection_params:
            params_str = str(error_info.connection_params)
            assert TEST_PASSWORD not in params_str  # Should be masked
            assert "***" in params_str  # Should contain masking
        assert len(error_info.resolution_steps) > 0
        assert isinstance(error_info.timestamp, datetime)

    def test_create_database_error_info_with_error_code(self):
        """Test creation of database error info with error code"""
        error = Exception("Authentication failed")
        error_info = ErrorReporter.create_database_error_info(
            error, "Neo4j", error_code="AUTH001"
        )
        
        assert error_info.error_code == "AUTH001"
        assert error_info.category == DatabaseErrorCategory.AUTHENTICATION_FAILURE

    def test_database_error_info_validation(self):
        """Test validation of database error info"""
        with pytest.raises(ValueError, match="component is required"):
            DatabaseErrorInfo(
                category=DatabaseErrorCategory.NETWORK_ERROR,
                component="",
                message="Test error",
                details={},
                timestamp=datetime.now(timezone.utc),
                resolution_steps=[]
            )

        with pytest.raises(ValueError, match="message is required"):
            DatabaseErrorInfo(
                category=DatabaseErrorCategory.NETWORK_ERROR,
                component="Test",
                message="",
                details={},
                timestamp=datetime.now(timezone.utc),
                resolution_steps=[]
            )


class TestErrorStatistics:
    """Test error statistics tracking functionality"""

    def setup_method(self):
        """Reset error statistics before each test"""
        ErrorReporter.reset_error_statistics()

    def test_error_statistics_tracking(self):
        """Test that error statistics are tracked correctly"""
        # Create some test errors
        error1 = Exception("Connection timeout")
        error_info1 = ErrorReporter.create_database_error_info(error1, "PostgreSQL")
        
        error2 = Exception("Authentication failed")
        error_info2 = ErrorReporter.create_database_error_info(error2, "Neo4j")
        
        error3 = Exception("Another timeout")
        error_info3 = ErrorReporter.create_database_error_info(error3, "PostgreSQL")
        
        # Add errors to statistics
        stats = ErrorReporter.get_error_statistics()
        stats.add_error(error_info1)
        stats.add_error(error_info2)
        stats.add_error(error_info3)
        
        # Check statistics
        assert stats.error_counts[DatabaseErrorCategory.CONNECTION_TIMEOUT] == 2
        assert stats.error_counts[DatabaseErrorCategory.AUTHENTICATION_FAILURE] == 1
        assert stats.component_errors["PostgreSQL"] == 2
        assert stats.component_errors["Neo4j"] == 1
        assert len(stats.recent_errors) == 3

    def test_most_frequent_category(self):
        """Test identification of most frequent error category"""
        stats = ErrorReporter.get_error_statistics()
        
        # Add multiple timeout errors
        for _ in range(3):
            error = Exception("timeout")
            error_info = ErrorReporter.create_database_error_info(error, "PostgreSQL")
            stats.add_error(error_info)
        
        # Add one auth error
        error = Exception("authentication failed")
        error_info = ErrorReporter.create_database_error_info(error, "Neo4j")
        stats.add_error(error_info)
        
        assert stats.get_most_frequent_category() == DatabaseErrorCategory.CONNECTION_TIMEOUT

    def test_most_problematic_component(self):
        """Test identification of most problematic component"""
        stats = ErrorReporter.get_error_statistics()
        
        # Add multiple PostgreSQL errors
        for _ in range(3):
            error = Exception("some error")
            error_info = ErrorReporter.create_database_error_info(error, "PostgreSQL")
            stats.add_error(error_info)
        
        # Add one Neo4j error
        error = Exception("another error")
        error_info = ErrorReporter.create_database_error_info(error, "Neo4j")
        stats.add_error(error_info)
        
        assert stats.get_most_problematic_component() == "PostgreSQL"

    def test_error_statistics_report_formatting(self):
        """Test formatting of error statistics report"""
        # Add some test errors
        error1 = Exception("Connection timeout")
        error_info1 = ErrorReporter.create_database_error_info(error1, "PostgreSQL")
        
        error2 = Exception("Authentication failed")
        error_info2 = ErrorReporter.create_database_error_info(error2, "Neo4j")
        
        stats = ErrorReporter.get_error_statistics()
        stats.add_error(error_info1)
        stats.add_error(error_info2)
        
        report = ErrorReporter.format_error_statistics_report()
        
        assert "Database Error Statistics Report" in report
        assert "connection_timeout" in report
        assert "authentication_failure" in report
        assert "PostgreSQL" in report
        assert "Neo4j" in report

    def test_empty_error_statistics_report(self):
        """Test error statistics report when no errors recorded"""
        report = ErrorReporter.format_error_statistics_report()
        assert "No database errors recorded" in report

    def test_reset_error_statistics(self):
        """Test resetting error statistics"""
        # Add an error
        error = Exception("test error")
        error_info = ErrorReporter.create_database_error_info(error, "PostgreSQL")
        stats = ErrorReporter.get_error_statistics()
        stats.add_error(error_info)
        
        assert len(stats.error_counts) > 0
        
        # Reset statistics
        ErrorReporter.reset_error_statistics()
        new_stats = ErrorReporter.get_error_statistics()
        
        assert len(new_stats.error_counts) == 0
        assert len(new_stats.component_errors) == 0
        assert len(new_stats.recent_errors) == 0


class TestDatabaseErrorLogging:
    """Test database error logging functionality"""

    def setup_method(self):
        """Reset error statistics before each test"""
        ErrorReporter.reset_error_statistics()

    def test_log_database_error(self, caplog):
        """Test logging of database errors"""
        
        error = Exception("Connection timeout")
        error_info = ErrorReporter.create_database_error_info(error, "PostgreSQL")
        
        # Log the error
        ErrorReporter.log_database_error(error_info)
        
        # Check that error was logged
        assert "Database error in PostgreSQL" in caplog.text
        assert "Connection timeout" in caplog.text

    def test_log_database_error_with_details(self, caplog):
        """Test logging of database errors with details"""
        error = Exception("Authentication failed")
        error_info = ErrorReporter.create_database_error_info(
            error, "Neo4j", {"username": "user", "password": TEST_PASSWORD}
        )
        
        # Log the error with details
        ErrorReporter.log_database_error(error_info, include_details=True)
        
        # Check that error was logged but sensitive data was masked
        assert "Database error in Neo4j" in caplog.text
        assert TEST_PASSWORD not in caplog.text  # Password should be masked

    def test_format_database_connection_error(self):
        """Test comprehensive database connection error formatting"""
        error = Exception("Connection refused")
        result = ErrorReporter.format_database_connection_error(
            "PostgreSQL",
            error,
            f"postgresql://user:{TEST_PASSWORD}@localhost:5432/db",
            is_critical=True,
            retry_count=2
        )
        
        assert "ERROR: Cannot connect to PostgreSQL" in result
        assert "Error Category: network_error" in result
        assert "Retry Attempts: 2" in result
        assert "password" not in result  # Should be masked
        assert "Resolution Steps:" in result
        assert len(result.split("Resolution Steps:")[1].strip()) > 0  # Has resolution steps


class TestResolutionSteps:
    """Test resolution steps generation"""

    def test_connection_timeout_resolution_steps(self):
        """Test resolution steps for connection timeout errors"""
        steps = ErrorReporter._get_resolution_steps(
            DatabaseErrorCategory.CONNECTION_TIMEOUT, "PostgreSQL"
        )
        
        assert len(steps) > 0
        assert any("PostgreSQL" in step for step in steps)
        assert any("network" in step.lower() for step in steps)

    def test_authentication_failure_resolution_steps(self):
        """Test resolution steps for authentication failure errors"""
        steps = ErrorReporter._get_resolution_steps(
            DatabaseErrorCategory.AUTHENTICATION_FAILURE, "Neo4j"
        )
        
        assert len(steps) > 0
        assert any("Neo4j" in step for step in steps)
        assert any("password" in step.lower() for step in steps)

    def test_encoding_error_resolution_steps(self):
        """Test resolution steps for encoding errors"""
        steps = ErrorReporter._get_resolution_steps(
            DatabaseErrorCategory.ENCODING_ERROR, "MigrationManager"
        )
        
        assert len(steps) > 0
        assert any("utf-8" in step.lower() for step in steps)
        assert any("encoding" in step.lower() for step in steps)

    def test_default_resolution_steps(self):
        """Test default resolution steps for unknown categories"""
        # Create a mock category that doesn't exist in the base_steps dict
        class MockCategory:
            value = "unknown_category"
        
        steps = ErrorReporter._get_resolution_steps(MockCategory(), "TestComponent")
        
        assert len(steps) > 0
        assert any("TestComponent" in step for step in steps)
        assert any("administrator" in step.lower() for step in steps)
