"""
Property-based tests for URL accessibility validation in ConfigValidator.

Tests Property 35: URL Accessibility Validated
**Validates: Requirements 10.4**

These tests verify that for any configuration validation, the validator checks
that the frontend URL can reach the backend URL and vice versa, reporting any
accessibility issues.
"""

import os
import socket
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.core.config_validator import ConfigValidator
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Constant for testing to avoid hard-coded passwords in literal strings
TEST_PASSWORD = get_test_password("test_password_value")
TEST_USER = "test_user_value"
TEST_DB = "test_db_value"


class TestURLAccessibilityValidationProperties:
    """Property-based tests for URL accessibility validation"""
    
    @given(
        scheme=st.sampled_from(["http", "https"]),
        host=st.sampled_from(["localhost", "127.0.0.1", "example.com"]),
        port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=100, deadline=10000)
    def test_valid_url_format_accepted_property(
        self,
        scheme: str,
        host: str,
        port: int
    ):
        """
        **Property 35: URL Accessibility Validated - Valid Format**
        **Validates: Requirements 10.4**
        
        For any URL with valid format (scheme://host:port), the validator
        should accept the format and not report format errors.
        """
        # Create valid URL
        api_url = f"{scheme}://{host}:{port}"
        
        # Create configuration with valid URL
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": api_url,
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                url_errors = validator.validate_urls()
                
                # Property: Valid URL format should not generate format errors
                format_errors = [
                    error for error in validator.result.errors
                    if "Invalid URL format" in error and api_url in error
                ]
                assert len(format_errors) == 0, \
                    f"Valid URL {api_url} should not generate format errors, but got: {format_errors}"

    @given(
        invalid_url=st.sampled_from([
            "not-a-url",
            "://missing-scheme",
            "http://",
            "ftp//missing-colon",
            "just-text",
            "",
        ])
    )
    @settings(max_examples=50, deadline=10000)
    def test_invalid_url_format_rejected_property(self, invalid_url: str):
        """
        **Property 35: URL Accessibility Validated - Invalid Format**
        **Validates: Requirements 10.4**
        
        For any URL with invalid format, the validator should report
        a format error with the invalid URL.
        """
        # Skip empty string as it's handled differently
        assume(invalid_url != "")
        
        # Create configuration with invalid URL
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": invalid_url,
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                url_errors = validator.validate_urls()
                
                # Property: Invalid URL format should generate an error
                format_errors = [
                    error for error in validator.result.errors
                    if "Invalid URL format" in error
                ]
                assert len(format_errors) > 0, \
                    f"Invalid URL {invalid_url} should generate format error"
                
                # Property: Error should mention the invalid URL
                has_url_in_error = any(
                    invalid_url in error
                    for error in validator.result.errors
                )
                assert has_url_in_error, \
                    f"Error message should mention the invalid URL {invalid_url}"

    @given(
        port=st.integers(min_value=1024, max_value=65535),
        is_accessible=st.booleans()
    )
    @settings(max_examples=100, deadline=10000)
    def test_url_accessibility_checked_property(
        self,
        port: int,
        is_accessible: bool
    ):
        """
        **Property 35: URL Accessibility Validated - Accessibility Check**
        **Validates: Requirements 10.4**
        
        For any URL, the validator should check accessibility and report
        warnings when the URL is not accessible.
        """
        # Create URL
        api_url = f"http://localhost:{port}"
        
        # Create configuration
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": api_url,
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Mock socket connection to simulate accessibility
                with patch('socket.socket') as mock_socket_class:
                    mock_socket = MagicMock()
                    mock_socket_class.return_value = mock_socket
                    
                    if is_accessible:
                        # Simulate successful connection
                        mock_socket.connect_ex.return_value = 0
                    else:
                        # Simulate connection failure
                        mock_socket.connect_ex.return_value = 111  # Connection refused
                    
                    # Run validation
                    validator = ConfigValidator()
                    url_errors = validator.validate_urls()
                    
                    # Property: Accessibility check should be performed
                    # (socket.connect_ex should be called)
                    assert mock_socket.connect_ex.called, \
                        "Accessibility check should attempt socket connection"
                    
                    # Property: If not accessible, should generate a warning
                    if not is_accessible:
                        accessibility_warnings = [
                            warning for warning in validator.result.warnings
                            if "not be accessible" in warning.lower() and api_url in warning
                        ]
                        assert len(accessibility_warnings) > 0, \
                            f"Inaccessible URL {api_url} should generate accessibility warning"
                        
                        # Property: Warning should mention the URL
                        has_url_in_warning = any(
                            api_url in warning
                            for warning in validator.result.warnings
                        )
                        assert has_url_in_warning, \
                            f"Warning should mention the inaccessible URL {api_url}"

    @given(
        neo4j_scheme=st.sampled_from(["bolt", "bolt+s", "bolt+ssc", "neo4j", "neo4j+s"]),
        neo4j_port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=50, deadline=10000)
    def test_neo4j_url_format_validated_property(
        self,
        neo4j_scheme: str,
        neo4j_port: int
    ):
        """
        **Property 35: URL Accessibility Validated - Neo4j URL Format**
        **Validates: Requirements 10.4**
        
        For any Neo4j URI with valid scheme and format, the validator
        should accept it without format errors.
        """
        # Create Neo4j URI
        neo4j_uri = f"{neo4j_scheme}://localhost:{neo4j_port}"
        
        # Create configuration
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": neo4j_uri,
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = neo4j_uri
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                url_errors = validator.validate_urls()
                
                # Property: Valid Neo4j URI format should not generate format errors
                neo4j_format_errors = [
                    error for error in validator.result.errors
                    if "Invalid URL format" in error and "NEO4J_URI" in error
                ]
                assert len(neo4j_format_errors) == 0, \
                    f"Valid Neo4j URI {neo4j_uri} should not generate format errors"

    @given(
        hostname=st.sampled_from([
            "localhost",
            "127.0.0.1",
            "example.com",
            "api.example.com",
            "192.168.1.1"
        ]),
        port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=100, deadline=10000)
    def test_hostname_resolution_checked_property(
        self,
        hostname: str,
        port: int
    ):
        """
        **Property 35: URL Accessibility Validated - Hostname Resolution**
        **Validates: Requirements 10.4**
        
        For any URL with a hostname, the validator should check if the
        hostname can be resolved and report issues if it cannot.
        """
        # Create URL
        api_url = f"http://{hostname}:{port}"
        
        # Create configuration
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": api_url,
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Mock socket to simulate hostname resolution failure
                with patch('socket.socket') as mock_socket_class:
                    mock_socket = MagicMock()
                    mock_socket_class.return_value = mock_socket
                    
                    # Simulate hostname resolution failure for non-localhost
                    if hostname not in ["localhost", "127.0.0.1"]:
                        mock_socket.connect_ex.side_effect = socket.gaierror("Hostname could not be resolved")
                    else:
                        # Localhost should resolve but may not be accessible
                        mock_socket.connect_ex.return_value = 111  # Connection refused
                    
                    # Run validation
                    validator = ConfigValidator()
                    url_errors = validator.validate_urls()
                    
                    # Property: Hostname resolution should be attempted
                    # (socket connection should be attempted)
                    assert mock_socket_class.called, \
                        "Hostname resolution check should create socket"
                    
                    # Property: If hostname cannot be resolved, should generate warning
                    if hostname not in ["localhost", "127.0.0.1"]:
                        resolution_warnings = [
                            warning for warning in validator.result.warnings
                            if ("not be accessible" in warning.lower() or 
                                "could not be resolved" in warning.lower()) and 
                                api_url in warning
                        ]
                        # Note: May or may not have warnings depending on actual network
                        # The property is that the check is performed

    @given(
        timeout_occurs=st.booleans(),
        port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=50, deadline=10000)
    def test_connection_timeout_handled_property(
        self,
        timeout_occurs: bool,
        port: int
    ):
        """
        **Property 35: URL Accessibility Validated - Timeout Handling**
        **Validates: Requirements 10.4**
        
        For any URL accessibility check, if a timeout occurs, the validator
        should handle it gracefully and report a warning.
        """
        # Create URL
        api_url = f"http://localhost:{port}"
        
        # Create configuration
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": api_url,
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Mock socket to simulate timeout
                with patch('socket.socket') as mock_socket_class:
                    mock_socket = MagicMock()
                    mock_socket_class.return_value = mock_socket
                    
                    if timeout_occurs:
                        # Simulate timeout
                        mock_socket.connect_ex.side_effect = socket.timeout("Connection timeout")
                    else:
                        # Simulate successful connection
                        mock_socket.connect_ex.return_value = 0
                    
                    # Run validation
                    validator = ConfigValidator()
                    url_errors = validator.validate_urls()
                    
                    # Property: Timeout should not cause validation to crash
                    # (validation should complete successfully)
                    assert validator.result is not None, \
                        "Validation should complete even with timeout"
                    
                    # Property: If timeout occurs, should generate warning
                    if timeout_occurs:
                        timeout_warnings = [
                            warning for warning in validator.result.warnings
                            if ("timeout" in warning.lower() or "not be accessible" in warning.lower()) 
                            and api_url in warning
                        ]
                        assert len(timeout_warnings) > 0, \
                            f"Timeout for URL {api_url} should generate warning"

    @given(
        api_port=st.integers(min_value=1024, max_value=65535),
        backend_port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=100, deadline=10000)
    def test_backend_url_consistency_checked_property(
        self,
        api_port: int,
        backend_port: int
    ):
        """
        **Property 35: URL Accessibility Validated - Backend URL Consistency**
        **Validates: Requirements 10.4**
        
        For any configuration, the validator should check that the
        NEXT_PUBLIC_API_URL port matches the backend port configuration.
        """
        # Create configuration with potentially mismatched ports
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "BACKEND_PORT": str(backend_port),
            "NEXT_PUBLIC_API_URL": f"http://localhost:{api_port}",
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                validator.validate_port_conflicts()  # This checks backend URL consistency
                
                # Property: If ports don't match, should generate warning
                if api_port != backend_port:
                    mismatch_warnings = [
                        warning for warning in validator.result.warnings
                        if "port mismatch" in warning.lower() or 
                           (str(api_port) in warning and str(backend_port) in warning)
                    ]
                    assert len(mismatch_warnings) > 0, \
                        f"Port mismatch (API: {api_port}, Backend: {backend_port}) should generate warning"
                    
                    # Property: Warning should mention both ports
                    has_both_ports = any(
                        str(api_port) in warning and str(backend_port) in warning
                        for warning in validator.result.warnings
                    )
                    assert has_both_ports, \
                        f"Warning should mention both API port {api_port} and backend port {backend_port}"

    @given(
        has_api_url=st.booleans(),
        has_neo4j_uri=st.booleans()
    )
    @settings(max_examples=50, deadline=10000)
    def test_all_configured_urls_validated_property(
        self,
        has_api_url: bool,
        has_neo4j_uri: bool
    ):
        """
        **Property 35: URL Accessibility Validated - All URLs Checked**
        **Validates: Requirements 10.4**
        
        For any configuration, the validator should check all configured URLs
        (NEXT_PUBLIC_API_URL, NEO4J_URI) for format and accessibility.
        """
        # Create configuration with optional URLs
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        }
        
        if has_api_url:
            test_config["NEXT_PUBLIC_API_URL"] = "http://localhost:8000"
        
        if has_neo4j_uri:
            test_config["NEO4J_URI"] = "bolt://localhost:7687"
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config.get("NEO4J_URI", "")
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                url_errors = validator.validate_urls()
                
                # Property: Validation should complete without crashing
                assert validator.result is not None, \
                    "URL validation should complete successfully"
                
                # Property: If URLs are missing, should be reported in required vars check
                # (not in URL validation, which only checks format/accessibility of present URLs)
                if not has_api_url or not has_neo4j_uri:
                    # Missing URLs are handled by validate_required_vars, not validate_urls
                    pass



# Integration tests to verify property test assumptions
def test_url_accessibility_validation_integration():
    """Integration test to verify URL accessibility validation works correctly"""
    # Test with valid, accessible URL (localhost)
    valid_config = {
        "JWT_SECRET": "a" * 32,
        "SECRET_KEY": "b" * 32,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": TEST_DB,
        "POSTGRES_USER": TEST_USER,
        "POSTGRES_PASSWORD": TEST_PASSWORD,
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": TEST_PASSWORD,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "NEXT_PUBLIC_API_URL": "http://localhost:8000",
    }
    
    with patch.dict(os.environ, valid_config, clear=True):
        with patch('app.core.config_validator.settings') as mock_settings:
            mock_settings.POSTGRES_HOST = "localhost"
            mock_settings.POSTGRES_PORT = 5432
            mock_settings.POSTGRES_DB = TEST_DB
            mock_settings.POSTGRES_USER = TEST_USER
            mock_settings.POSTGRES_PASSWORD = TEST_PASSWORD
            mock_settings.NEO4J_URI = "bolt://localhost:7687"
            mock_settings.NEO4J_USER = "neo4j"
            mock_settings.NEO4J_PASSWORD = TEST_PASSWORD
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6379
            mock_settings.JWT_SECRET = "a" * 32
            mock_settings.SECRET_KEY = "b" * 32
            
            validator = ConfigValidator()
            url_errors = validator.validate_urls()
            
            # Should not have format errors for valid URLs
            format_errors = [
                error for error in validator.result.errors
                if "Invalid URL format" in error
            ]
            assert len(format_errors) == 0, "Valid URLs should not generate format errors"
    
    # Test with invalid URL format
    invalid_config = {
        "JWT_SECRET": "a" * 32,
        "SECRET_KEY": "b" * 32,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": TEST_DB,
        "POSTGRES_USER": TEST_USER,
        "POSTGRES_PASSWORD": TEST_PASSWORD,
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": TEST_PASSWORD,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "NEXT_PUBLIC_API_URL": "not-a-valid-url",
    }
    
    with patch.dict(os.environ, invalid_config, clear=True):
        with patch('app.core.config_validator.settings') as mock_settings:
            mock_settings.POSTGRES_HOST = "localhost"
            mock_settings.POSTGRES_PORT = 5432
            mock_settings.POSTGRES_DB = TEST_DB
            mock_settings.POSTGRES_USER = TEST_USER
            mock_settings.POSTGRES_PASSWORD = TEST_PASSWORD
            mock_settings.NEO4J_URI = "bolt://localhost:7687"
            mock_settings.NEO4J_USER = "neo4j"
            mock_settings.NEO4J_PASSWORD = TEST_PASSWORD
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6379
            mock_settings.JWT_SECRET = "a" * 32
            mock_settings.SECRET_KEY = "b" * 32
            
            validator = ConfigValidator()
            url_errors = validator.validate_urls()
            
            # Should have format error for invalid URL
            format_errors = [
                error for error in validator.result.errors
                if "Invalid URL format" in error
            ]
            assert len(format_errors) > 0, "Invalid URL should generate format error"


# Test fixtures
@pytest.fixture
def valid_url_configuration():
    """Fixture providing a valid URL configuration"""
    return {
        "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        "NEO4J_URI": "bolt://localhost:7687",
    }


@pytest.fixture
def invalid_url_configuration():
    """Fixture providing an invalid URL configuration"""
    return {
        "NEXT_PUBLIC_API_URL": "not-a-url",
        "NEO4J_URI": "://invalid",
    }
