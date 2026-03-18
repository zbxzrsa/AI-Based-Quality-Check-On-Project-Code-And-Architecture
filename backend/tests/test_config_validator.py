"""
Unit tests for ConfigValidator class.

Tests configuration validation for backend-frontend connectivity:
- Required environment variable validation
- Port conflict detection
- URL format and accessibility validation
- Configuration consistency checks

Validates Requirements: 10.1, 10.2, 10.3, 10.4
"""
import os
from unittest.mock import patch
from app.core.config_validator import ConfigValidator, ValidationResult, get_config_validator
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Constants for testing to avoid hard-coded credentials in literal strings
TEST_PASSWORD = get_test_password("test_password_long")
TEST_SECRET = "test_secret_value_32_chars_long_12345"


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_validation_result_has_errors(self):
        """Test has_errors method"""
        result = ValidationResult(is_valid=False, errors=["error1", "error2"])
        assert result.has_errors() is True
        
        result_no_errors = ValidationResult(is_valid=True, errors=[])
        assert result_no_errors.has_errors() is False
    
    def test_validation_result_has_warnings(self):
        """Test has_warnings method"""
        result = ValidationResult(is_valid=True, warnings=["warning1"])
        assert result.has_warnings() is True
        
        result_no_warnings = ValidationResult(is_valid=True, warnings=[])
        assert result_no_warnings.has_warnings() is False


class TestConfigValidatorRequiredVars:
    """Test required environment variable validation (Requirement 10.2)"""
    
    def test_validate_required_vars_all_present(self):
        """Test validation passes when all required variables are present"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            validator = ConfigValidator()
            missing_vars = validator.validate_required_vars()
            assert len(missing_vars) == 0
            assert len(validator.result.errors) == 0
    
    def test_validate_required_vars_missing_jwt_secret(self):
        """Test validation fails when JWT_SECRET is missing"""
        with patch.dict(os.environ, {
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            # Mock settings to not have JWT_SECRET
            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.JWT_SECRET = ""
                mock_settings.SECRET_KEY = TEST_SECRET
                mock_settings.POSTGRES_HOST = "localhost"
                mock_settings.POSTGRES_PORT = 5432
                mock_settings.POSTGRES_DB = "test"
                mock_settings.POSTGRES_USER = "user"
                mock_settings.POSTGRES_PASSWORD = TEST_PASSWORD
                mock_settings.NEO4J_URI = "bolt://localhost:7687"
                mock_settings.NEO4J_USER = "neo4j"
                mock_settings.NEO4J_PASSWORD = TEST_PASSWORD
                mock_settings.REDIS_HOST = "localhost"
                mock_settings.REDIS_PORT = 6379
                
                validator = ConfigValidator()
                missing_vars = validator.validate_required_vars()
                assert "JWT_SECRET" in missing_vars
                assert any("JWT_SECRET" in error for error in validator.result.errors)
    
    def test_validate_required_vars_missing_postgres_password(self):
        """Test validation fails when POSTGRES_PASSWORD is missing"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            # Mock settings to not have POSTGRES_PASSWORD
            with patch('app.core.config_validator.settings') as mock_settings:
                mock_settings.JWT_SECRET = TEST_SECRET
                mock_settings.SECRET_KEY = TEST_SECRET
                mock_settings.POSTGRES_HOST = "localhost"
                mock_settings.POSTGRES_PORT = 5432
                mock_settings.POSTGRES_DB = "test"
                mock_settings.POSTGRES_USER = "user"
                mock_settings.POSTGRES_PASSWORD = ""
                mock_settings.NEO4J_URI = "bolt://localhost:7687"
                mock_settings.NEO4J_USER = "neo4j"
                mock_settings.NEO4J_PASSWORD = TEST_PASSWORD
                mock_settings.REDIS_HOST = "localhost"
                mock_settings.REDIS_PORT = 6379
                
                validator = ConfigValidator()
                missing_vars = validator.validate_required_vars()
                assert "POSTGRES_PASSWORD" in missing_vars
                assert any("POSTGRES_PASSWORD" in error for error in validator.result.errors)
    
    def test_validate_required_vars_missing_next_public_api_url(self):
        """Test validation fails when NEXT_PUBLIC_API_URL is missing"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        }, clear=True):
            validator = ConfigValidator()
            missing_vars = validator.validate_required_vars()
            assert "NEXT_PUBLIC_API_URL" in missing_vars
            assert any("NEXT_PUBLIC_API_URL" in error for error in validator.result.errors)
    
    def test_validate_variable_formats_short_jwt_secret(self):
        """Test validation warns when JWT_SECRET is too short"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "short",
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            validator = ConfigValidator()
            validator.validate_required_vars()
            assert any("JWT_SECRET" in warning and "32" in warning 
                      for warning in validator.result.warnings)
    
    def test_validate_variable_formats_invalid_port(self):
        """Test validation fails when port number is invalid"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "99999",  # Invalid port
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            validator = ConfigValidator()
            validator.validate_required_vars()
            assert any("POSTGRES_PORT" in error and "99999" in error 
                      for error in validator.result.errors)


class TestConfigValidatorPortConflicts:
    """Test port conflict detection (Requirement 10.3)"""
    
    def test_validate_port_conflicts_no_conflicts(self):
        """Test validation passes when no port conflicts exist"""
        with patch.dict(os.environ, {
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
            "POSTGRES_PORT": "5432",
            "REDIS_PORT": "6379",
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            conflicts = validator.validate_port_conflicts()
            assert len(conflicts) == 0
    
    def test_validate_port_conflicts_backend_frontend_conflict(self):
        """Test validation detects conflict between backend and frontend"""
        with patch.dict(os.environ, {
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "8000",  # Same as backend
            "POSTGRES_PORT": "5432",
            "REDIS_PORT": "6379",
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            conflicts = validator.validate_port_conflicts()
            assert len(conflicts) > 0
            assert any("8000" in conflict for conflict in conflicts)
    
    def test_validate_port_conflicts_database_conflict(self):
        """Test validation detects conflict between databases"""
        with patch.dict(os.environ, {
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
            "POSTGRES_PORT": "5432",
            "REDIS_PORT": "5432",  # Same as PostgreSQL
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            conflicts = validator.validate_port_conflicts()
            assert len(conflicts) > 0
            assert any("5432" in conflict for conflict in conflicts)
    
    def test_validate_backend_port_consistency_mismatch(self):
        """Test validation warns when API URL port doesn't match backend port"""
        with patch.dict(os.environ, {
            "BACKEND_PORT": "8000",
            "NEXT_PUBLIC_API_URL": "http://localhost:9000",  # Different port
            "POSTGRES_PORT": "5432",
            "REDIS_PORT": "6379",
        }, clear=True):
            validator = ConfigValidator()
            validator.validate_port_conflicts()
            assert any("Port mismatch" in warning and "9000" in warning 
                      for warning in validator.result.warnings)
    
    def test_validate_backend_port_consistency_match(self):
        """Test validation passes when API URL port matches backend port"""
        with patch.dict(os.environ, {
            "BACKEND_PORT": "8000",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "POSTGRES_PORT": "5432",
            "REDIS_PORT": "6379",
        }, clear=True):
            validator = ConfigValidator()
            validator.validate_port_conflicts()
            # Should not have port mismatch warning
            assert not any("Port mismatch" in warning 
                          for warning in validator.result.warnings)


class TestConfigValidatorURLs:
    """Test URL format and accessibility validation (Requirement 10.4)"""
    
    def test_validate_urls_valid_http_url(self):
        """Test validation passes for valid HTTP URL"""
        with patch.dict(os.environ, {
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            errors = validator.validate_urls()
            # Should not have format errors
            assert not any("Invalid URL format" in error for error in errors)
    
    def test_validate_urls_valid_https_url(self):
        """Test validation passes for valid HTTPS URL"""
        with patch.dict(os.environ, {
            "NEXT_PUBLIC_API_URL": "https://api.example.com",
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            errors = validator.validate_urls()
            # Should not have format errors
            assert not any("Invalid URL format" in error for error in errors)
    
    def test_validate_urls_invalid_url_format(self):
        """Test validation fails for invalid URL format"""
        with patch.dict(os.environ, {
            "NEXT_PUBLIC_API_URL": "not-a-valid-url",
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            errors = validator.validate_urls()
            assert len(errors) > 0
            assert any("Invalid URL format" in error and "NEXT_PUBLIC_API_URL" in error 
                      for error in errors)
    
    def test_validate_urls_neo4j_uri_format(self):
        """Test validation passes for valid Neo4j URI"""
        with patch.dict(os.environ, {
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "NEO4J_URI": "bolt://localhost:7687",
        }, clear=True):
            validator = ConfigValidator()
            errors = validator.validate_urls()
            # Should not have format errors for Neo4j URI
            assert not any("NEO4J_URI" in error and "Invalid URL format" in error 
                          for error in errors)
    
    def test_is_valid_url_format_http(self):
        """Test _is_valid_url_format for HTTP URLs"""
        validator = ConfigValidator()
        assert validator._is_valid_url_format("http://localhost:8000") is True
        assert validator._is_valid_url_format("https://example.com") is True
        assert validator._is_valid_url_format("bolt://localhost:7687") is True
        assert validator._is_valid_url_format("not-a-url") is False
        assert validator._is_valid_url_format("") is False
    
    def test_check_url_accessibility_localhost(self):
        """Test _check_url_accessibility for localhost"""
        validator = ConfigValidator()
        # This test may fail if nothing is running on port 8000
        # We're just testing the method works, not that the service is available
        is_accessible, error = validator._check_url_accessibility("http://localhost:8000")
        # Should return a boolean and optional error message
        assert isinstance(is_accessible, bool)
        if not is_accessible:
            assert error is not None


class TestConfigValidatorValidateAll:
    """Test complete validation (Requirement 10.1)"""
    
    def test_validate_all_success(self):
        """Test validate_all returns success when all checks pass"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
        }, clear=True):
            validator = ConfigValidator()
            result = validator.validate_all()
            assert result.is_valid is True
            assert len(result.errors) == 0
    
    def test_validate_all_failure_missing_vars(self):
        """Test validate_all returns failure when required vars are missing"""
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
        }, clear=True):
            validator = ConfigValidator()
            result = validator.validate_all()
            assert result.is_valid is False
            assert len(result.errors) > 0
    
    def test_validate_all_generates_config_summary(self):
        """Test validate_all generates configuration summary"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
        }, clear=True):
            validator = ConfigValidator()
            result = validator.validate_all()
            assert "environment" in result.config_summary
            assert "backend_port" in result.config_summary
            assert "frontend_port" in result.config_summary
            assert "validation_status" in result.config_summary


class TestConfigValidatorSummary:
    """Test validation summary and reporting"""
    
    def test_get_validation_summary(self):
        """Test get_validation_summary returns complete summary"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            validator = ConfigValidator()
            validator.validate_all()
            summary = validator.get_validation_summary()
            
            assert "is_valid" in summary
            assert "errors" in summary
            assert "warnings" in summary
            assert "config_summary" in summary
            assert "has_errors" in summary
            assert "has_warnings" in summary
    
    def test_format_validation_report(self):
        """Test format_validation_report generates readable report"""
        with patch.dict(os.environ, {
            "JWT_SECRET": TEST_SECRET,
            "SECRET_KEY": TEST_SECRET,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }, clear=True):
            validator = ConfigValidator()
            validator.validate_all()
            report = validator.format_validation_report()
            
            assert "CONFIGURATION VALIDATION REPORT" in report
            assert "Status:" in report
            assert "CONFIGURATION SUMMARY" in report


class TestConfigValidatorFactory:
    """Test factory function"""
    
    def test_get_config_validator(self):
        """Test get_config_validator returns ConfigValidator instance"""
        validator = get_config_validator()
        assert isinstance(validator, ConfigValidator)
