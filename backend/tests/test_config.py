"""
Unit tests for the Settings configuration class.

Tests comprehensive validation for:
- Required field validation (JWT_SECRET, database credentials)
- Optional field handling with sensible defaults
- Security settings validation
- Database URL validation
- Celery configuration validation
- Environment-specific configuration

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""
import os
import pytest
from pydantic import ValidationError
from unittest.mock import patch
from app.core.config import Settings
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Constant for testing to avoid hard-coded passwords in literal strings
TEST_PASSWORD = get_test_password("test_password_value")
TEST_USER = "test_user_name"
TEST_DB = "test_database_db"
TEST_WEBHOOK_SECRET = "whsec_test_secret_12345"


class TestSettingsRequiredFields:
    """Test required field validation (Requirement 1.1, 1.2, 1.3)"""

    def test_missing_jwt_secret_raises_error(self):
        """Test that missing JWT_SECRET raises ValidationError"""
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "JWT_SECRET" in str(exc_info.value)

    def test_empty_jwt_secret_raises_error(self):
        """Test that empty JWT_SECRET raises ValidationError"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "JWT_SECRET" in str(exc_info.value)

    def test_missing_postgres_password_raises_error(self):
        """Test that missing POSTGRES_PASSWORD raises ValidationError"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "POSTGRES_PASSWORD" in str(exc_info.value)

    def test_empty_postgres_password_raises_error(self):
        """Test that empty POSTGRES_PASSWORD raises ValidationError"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "POSTGRES_PASSWORD" in str(exc_info.value)

    def test_missing_neo4j_password_raises_error(self):
        """Test that missing NEO4J_PASSWORD raises ValidationError"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "REDIS_HOST": "localhost",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "NEO4J_PASSWORD" in str(exc_info.value)

    def test_empty_neo4j_password_raises_error(self):
        """Test that empty NEO4J_PASSWORD raises ValidationError"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "",
            "REDIS_HOST": "localhost",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "NEO4J_PASSWORD" in str(exc_info.value)

    def test_all_required_fields_present_succeeds(self):
        """Test that all required fields present allows Settings creation"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            assert settings.JWT_SECRET == "a" * 32
            assert settings.POSTGRES_PASSWORD == TEST_PASSWORD
            assert settings.NEO4J_PASSWORD == TEST_PASSWORD


class TestSettingsOptionalFields:
    """Test optional field handling with sensible defaults (Requirement 1.4)"""

    def test_optional_github_token_defaults_to_none_or_empty(self):
        """Test that GITHUB_TOKEN defaults to None or empty string when not provided"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            # Can be None or empty string
            assert settings.GITHUB_TOKEN is None or settings.GITHUB_TOKEN == ""

    def test_optional_openai_api_key_defaults_to_none_or_empty(self):
        """Test that OPENAI_API_KEY defaults to None or empty string when not provided"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            # Can be None or empty string
            assert settings.OPENAI_API_KEY is None or settings.OPENAI_API_KEY == ""

    def test_optional_celery_broker_url_defaults_to_none_or_empty(self):
        """Test that CELERY_BROKER_URL defaults to None or empty string when not provided"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            # Can be None or empty string
            assert settings.CELERY_BROKER_URL is None or settings.CELERY_BROKER_URL == ""

    def test_optional_redis_password_defaults_to_empty_string(self):
        """Test that REDIS_PASSWORD defaults to empty string when not provided"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            assert settings.REDIS_PASSWORD == ""

    def test_optional_fields_can_be_set(self):
        """Test that optional fields can be set when provided"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "GITHUB_TOKEN": "ghp_test123",
            "OPENAI_API_KEY": "sk-test123",
        }, clear=True):
            settings = Settings()
            assert settings.GITHUB_TOKEN == "ghp_test123"
            assert settings.OPENAI_API_KEY == "sk-test123"


class TestSettingsSecurityValidation:
    """Test security settings validation"""

    def test_bcrypt_rounds_minimum_12_required(self):
        """Test that BCRYPT_ROUNDS must be at least 12"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "BCRYPT_ROUNDS": "11",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "BCRYPT_ROUNDS" in str(exc_info.value)

    def test_bcrypt_rounds_12_is_valid(self):
        """Test that BCRYPT_ROUNDS of 12 is valid"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "BCRYPT_ROUNDS": "12",
        }, clear=True):
            settings = Settings()
            assert settings.BCRYPT_ROUNDS == 12

    def test_validate_security_settings_warns_short_jwt_secret(self):
        """Test that validate_security_settings warns about short JWT_SECRET"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 16,  # Less than 32
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            warnings = settings.validate_security_settings()
            assert any("JWT_SECRET" in w and "32" in w for w in warnings)

    def test_validate_security_settings_no_warnings_for_valid_config(self):
        """Test that validate_security_settings has no warnings for valid config"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "GITHUB_TOKEN": "ghp_test123",
        }, clear=True):
            settings = Settings()
            warnings = settings.validate_security_settings()
            # Should have no warnings for valid config with GitHub token
            assert len(warnings) == 0


class TestSettingsDatabaseValidation:
    """Test database URL validation"""

    def test_validate_database_urls_no_errors_for_valid_config(self):
        """Test that validate_database_urls returns no errors for valid config"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            errors = settings.validate_database_urls()
            assert len(errors) == 0

    def test_postgres_url_property_formats_correctly(self):
        """Test that postgres_url property formats connection string correctly"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            expected = f"postgresql+asyncpg://{TEST_USER}:{TEST_PASSWORD}@localhost:5432/{TEST_DB}"
            assert settings.postgres_url == expected

    def test_redis_url_without_password(self):
        """Test that redis_url formats correctly without password"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "",
        }, clear=True):
            settings = Settings()
            expected = "redis://localhost:6379/0"
            assert settings.redis_url == expected

    def test_redis_url_with_password(self):
        """Test that redis_url formats correctly with password"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": get_test_password("test_redis_password"),
        }, clear=True):
            settings = Settings()
            expected = f"redis://:{get_test_password('test_redis_password')}@localhost:6379/0"
            assert settings.redis_url == expected


class TestSettingsCeleryValidation:
    """Test Celery configuration validation"""

    def test_celery_broker_without_result_backend_succeeds_with_empty_strings(self):
        """Test that CELERY_BROKER_URL without CELERY_RESULT_BACKEND succeeds when both are empty"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "CELERY_BROKER_URL": "",
        }, clear=True):
            # Should succeed because empty string is falsy
            settings = Settings()
            assert settings.CELERY_BROKER_URL == ""

    def test_celery_result_backend_without_broker_succeeds_with_empty_strings(self):
        """Test that CELERY_RESULT_BACKEND without CELERY_BROKER_URL succeeds when both are empty"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "CELERY_RESULT_BACKEND": "",
        }, clear=True):
            # Should succeed because empty string is falsy
            settings = Settings()
            assert settings.CELERY_RESULT_BACKEND == ""

    def test_celery_both_urls_set_succeeds(self):
        """Test that both CELERY_BROKER_URL and CELERY_RESULT_BACKEND set succeeds"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "CELERY_BROKER_URL": "redis://localhost:6379/0",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
        }, clear=True):
            settings = Settings()
            assert settings.CELERY_BROKER_URL == "redis://localhost:6379/0"
            assert settings.CELERY_RESULT_BACKEND == "redis://localhost:6379/1"

    def test_is_celery_enabled_returns_true_when_configured(self):
        """Test that is_celery_enabled returns True when both URLs are set"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "CELERY_BROKER_URL": "redis://localhost:6379/0",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
        }, clear=True):
            settings = Settings()
            assert settings.is_celery_enabled() is True

    def test_is_celery_enabled_returns_false_when_not_configured(self):
        """Test that is_celery_enabled returns False when URLs not set"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            assert settings.is_celery_enabled() is False


class TestSettingsEnvironmentSpecific:
    """Test environment-specific configuration (Requirement 1.5)"""

    def test_environment_development_is_valid(self):
        """Test that ENVIRONMENT=development is valid"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ENVIRONMENT": "development",
        }, clear=True):
            settings = Settings()
            assert settings.ENVIRONMENT == "development"

    def test_environment_staging_is_valid(self):
        """Test that ENVIRONMENT=staging is valid"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ENVIRONMENT": "staging",
        }, clear=True):
            settings = Settings()
            assert settings.ENVIRONMENT == "staging"

    def test_environment_production_is_valid(self):
        """Test that ENVIRONMENT=production is valid"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ENVIRONMENT": "production",
        }, clear=True):
            settings = Settings()
            assert settings.ENVIRONMENT == "production"

    def test_invalid_environment_raises_error(self):
        """Test that invalid ENVIRONMENT value raises ValidationError"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ENVIRONMENT": "invalid",
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "ENVIRONMENT" in str(exc_info.value)

    def test_get_environment_specific_defaults_development(self):
        """Test that get_environment_specific_defaults returns development defaults"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ENVIRONMENT": "development",
        }, clear=True):
            settings = Settings()
            defaults = settings.get_environment_specific_defaults()
            assert defaults["DEBUG"] is True
            assert defaults["LOG_LEVEL"] == "DEBUG"

    def test_get_environment_specific_defaults_production(self):
        """Test that get_environment_specific_defaults returns production defaults"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ENVIRONMENT": "production",
        }, clear=True):
            settings = Settings()
            defaults = settings.get_environment_specific_defaults()
            assert defaults["DEBUG"] is False
            assert defaults["LOG_LEVEL"] == "WARNING"


class TestSettingsIntegrationFeatures:
    """Test integration feature detection methods"""

    def test_is_github_integration_enabled_true(self):
        """Test that is_github_integration_enabled returns True when configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "GITHUB_TOKEN": "ghp_test123",
            "GITHUB_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET,
        }, clear=True):
            settings = Settings()
            assert settings.is_github_integration_enabled() is True

    def test_is_github_integration_enabled_false(self):
        """Test that is_github_integration_enabled returns False when not configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            assert settings.is_github_integration_enabled() is False

    def test_is_openai_enabled_true(self):
        """Test that is_openai_enabled returns True when configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "OPENAI_API_KEY": "sk-test123",
        }, clear=True):
            settings = Settings()
            assert settings.is_openai_enabled() is True

    def test_is_openai_enabled_false(self):
        """Test that is_openai_enabled returns False when not configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
        }, clear=True):
            settings = Settings()
            assert settings.is_openai_enabled() is False

    def test_is_anthropic_enabled_true(self):
        """Test that is_anthropic_enabled returns True when configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "ANTHROPIC_API_KEY": "sk-test123",
        }, clear=True):
            settings = Settings()
            assert settings.is_anthropic_enabled() is True

    def test_is_ollama_enabled_true(self):
        """Test that is_ollama_enabled returns True when configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "a" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }, clear=True):
            settings = Settings()
            assert settings.is_ollama_enabled() is True
