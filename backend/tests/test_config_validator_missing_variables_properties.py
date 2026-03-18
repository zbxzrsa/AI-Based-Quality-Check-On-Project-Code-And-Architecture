"""
Property-based tests for configuration validation in ConfigValidator.

Tests Property 33: Configuration Validation Reports Missing Variables
**Validates: Requirements 10.2**

These tests verify that for any configuration validation run with missing or
invalid variables, the validation reports each missing/invalid variable with
a specific error message.
"""

import os
from typing import Set
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st, settings

from app.core.config_validator import ConfigValidator
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Test constants for configuration to avoid literal suspicious strings
TEST_PASSWORD = get_test_password("test_password_value")
TEST_USER = "test_user_name"
TEST_DB = "test_database_db"


# Define all required variables for reference
REQUIRED_VARIABLES = {
    "JWT_SECRET",
    "SECRET_KEY",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
    "NEXT_PUBLIC_API_URL",
}


# Test constants for configuration to avoid literal suspicious strings
TEST_PASSWORD = get_test_password("test_password_value")
TEST_USER = "test_user_name"
TEST_DB = "test_database_db"


class TestConfigurationValidationMissingVariablesProperties:
    """Property-based tests for configuration validation missing variable detection"""
    
    @given(
        missing_vars=st.sets(
            st.sampled_from(list(REQUIRED_VARIABLES)),
            min_size=1,
            max_size=len(REQUIRED_VARIABLES)
        )
    )
    @settings(max_examples=100, deadline=10000)
    def test_missing_variables_reported_property(self, missing_vars: Set[str]):
        """
        **Property 33: Configuration Validation Reports Missing Variables**
        **Validates: Requirements 10.2**
        
        For any set of missing required variables, the validation should report
        each missing variable with a specific error message.
        """
        # Create complete valid configuration
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
        
        # Remove the missing variables
        test_config = {k: v for k, v in valid_config.items() if k not in missing_vars}
        
        # Mock settings to return empty/None for missing variables
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes on mock_settings
                for var_name in REQUIRED_VARIABLES:
                    if var_name in test_config:
                        setattr(mock_settings, var_name, test_config[var_name])
                    else:
                        setattr(mock_settings, var_name, None)
                
                # Set default values for port variables if they're present
                if "POSTGRES_PORT" in test_config:
                    mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                else:
                    mock_settings.POSTGRES_PORT = None
                
                if "REDIS_PORT" in test_config:
                    mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                else:
                    mock_settings.REDIS_PORT = None
                
                # Run validation
                validator = ConfigValidator()
                reported_missing = validator.validate_required_vars()
                
                # Property: Each missing variable should be reported
                for var_name in missing_vars:
                    assert var_name in reported_missing, \
                        f"Missing variable {var_name} should be reported in missing list"
                    
                    # Property: Each missing variable should have an error message
                    has_error_message = any(var_name in error for error in validator.result.errors)
                    assert has_error_message, \
                        f"Missing variable {var_name} should have a specific error message"
                
                # Property: Only missing variables should be reported
                for reported_var in reported_missing:
                    assert reported_var in missing_vars, \
                        f"Variable {reported_var} was reported as missing but should be present"
                
                # Property: Number of reported missing variables should match actual missing
                assert len(reported_missing) == len(missing_vars), \
                    f"Expected {len(missing_vars)} missing variables, but got {len(reported_missing)}"
    
    @given(
        empty_vars=st.sets(
            st.sampled_from([v for v in REQUIRED_VARIABLES if "PORT" not in v]),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=10000)
    def test_empty_string_variables_reported_property(self, empty_vars: Set[str]):
        """
        **Property 33: Configuration Validation Reports Missing Variables - Empty Strings**
        **Validates: Requirements 10.2**
        
        For any set of non-port variables with empty string values, the validation
        should report them as missing with specific error messages.
        """
        # Create configuration with some variables as empty strings
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
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }
        
        # Set empty vars to empty strings
        for var_name in empty_vars:
            test_config[var_name] = ""
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes on mock_settings
                for var_name, value in test_config.items():
                    if "PORT" in var_name:
                        setattr(mock_settings, var_name, int(value))
                    else:
                        setattr(mock_settings, var_name, value)
                
                # Run validation
                validator = ConfigValidator()
                reported_missing = validator.validate_required_vars()
                
                # Property: Empty string variables should be reported as missing
                for var_name in empty_vars:
                    assert var_name in reported_missing, \
                        f"Empty variable {var_name} should be reported as missing"
                    
                    # Property: Should have specific error message
                    has_error_message = any(var_name in error for error in validator.result.errors)
                    assert has_error_message, \
                        f"Empty variable {var_name} should have a specific error message"
    
    @given(
        invalid_ports=st.sets(
            st.sampled_from(["POSTGRES_PORT", "REDIS_PORT"]),
            min_size=1,
            max_size=2
        ),
        port_value=st.one_of(
            st.integers(min_value=-1000, max_value=0),  # Negative or zero
            st.integers(min_value=65536, max_value=100000),  # Too large
        )
    )
    @settings(max_examples=100, deadline=10000)
    def test_invalid_port_numbers_reported_property(self, invalid_ports: Set[str], port_value: int):
        """
        **Property 33: Configuration Validation Reports Missing Variables - Invalid Ports**
        **Validates: Requirements 10.2**
        
        For any set of port variables with invalid values (outside 1-65535 range),
        the validation should report them with specific error messages.
        """
        # Create valid configuration
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
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }
        
        # Set invalid port values
        for port_var in invalid_ports:
            test_config[port_var] = str(port_value)
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes on mock_settings
                for var_name, value in test_config.items():
                    if "PORT" in var_name:
                        try:
                            setattr(mock_settings, var_name, int(value))
                        except ValueError:
                            setattr(mock_settings, var_name, -1)
                    else:
                        setattr(mock_settings, var_name, value)
                
                # Run validation
                validator = ConfigValidator()
                validator.validate_required_vars()
                
                # Property: Invalid port numbers should generate error messages
                for port_var in invalid_ports:
                    has_port_error = any(
                        port_var in error and "Invalid port number" in error
                        for error in validator.result.errors
                    )
                    assert has_port_error, \
                        f"Invalid port {port_var}={port_value} should generate an error message"
                    
                    # Property: Error message should mention the invalid value
                    has_value_in_error = any(
                        port_var in error and str(port_value) in error
                        for error in validator.result.errors
                    )
                    assert has_value_in_error, \
                        f"Error message for {port_var} should mention the invalid value {port_value}"
    
    @given(
        jwt_secret_length=st.integers(min_value=1, max_value=31)
    )
    @settings(max_examples=50, deadline=10000)
    def test_short_jwt_secret_warning_property(self, jwt_secret_length: int):
        """
        **Property 33: Configuration Validation Reports Missing Variables - JWT Secret Length**
        **Validates: Requirements 10.2**
        
        For any JWT_SECRET with length less than 32 characters, the validation
        should generate a warning message with the actual length.
        """
        # Create configuration with short JWT secret
        test_config = {
            "JWT_SECRET": "a" * jwt_secret_length,
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
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                for var_name, value in test_config.items():
                    if "PORT" in var_name:
                        setattr(mock_settings, var_name, int(value))
                    else:
                        setattr(mock_settings, var_name, value)
                
                # Run validation
                validator = ConfigValidator()
                validator.validate_required_vars()
                
                # Property: Short JWT_SECRET should generate a warning
                has_jwt_warning = any(
                    "JWT_SECRET" in warning and "32" in warning
                    for warning in validator.result.warnings
                )
                assert has_jwt_warning, \
                    f"JWT_SECRET with length {jwt_secret_length} should generate a warning"
                
                # Property: Warning should mention the actual length
                has_length_in_warning = any(
                    "JWT_SECRET" in warning and str(jwt_secret_length) in warning
                    for warning in validator.result.warnings
                )
                assert has_length_in_warning, \
                    f"Warning should mention the actual JWT_SECRET length {jwt_secret_length}"
    
    @given(
        config_subset=st.sets(
            st.sampled_from(list(REQUIRED_VARIABLES)),
            min_size=0,
            max_size=len(REQUIRED_VARIABLES)
        )
    )
    @settings(max_examples=100, deadline=10000)
    def test_validation_result_consistency_property(self, config_subset: Set[str]):
        """
        **Property 33: Configuration Validation Reports Missing Variables - Result Consistency**
        **Validates: Requirements 10.2**
        
        For any configuration, the validation result should be consistent:
        - is_valid should be False if there are errors
        - has_errors() should match the presence of errors
        - Missing variables list should match error messages
        """
        # Create configuration with only the subset of variables
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
        
        test_config = {k: v for k, v in valid_config.items() if k in config_subset}
        missing_vars = REQUIRED_VARIABLES - config_subset
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set attributes for present variables
                for var_name in REQUIRED_VARIABLES:
                    if var_name in test_config:
                        if "PORT" in var_name:
                            setattr(mock_settings, var_name, int(test_config[var_name]))
                        else:
                            setattr(mock_settings, var_name, test_config[var_name])
                    else:
                        setattr(mock_settings, var_name, None)
                
                # Run validation
                validator = ConfigValidator()
                reported_missing = validator.validate_required_vars()
                
                # Property: has_errors() should be True if there are missing variables
                if len(missing_vars) > 0:
                    assert validator.result.has_errors(), \
                        "has_errors() should be True when variables are missing"
                    assert len(validator.result.errors) > 0, \
                        "errors list should not be empty when variables are missing"
                
                # Property: Number of errors should be at least the number of missing variables
                # (may be more due to format validation errors)
                assert len(validator.result.errors) >= len(missing_vars), \
                    f"Should have at least {len(missing_vars)} errors, got {len(validator.result.errors)}"
                
                # Property: Each reported missing variable should have an error
                for var_name in reported_missing:
                    has_error = any(var_name in error for error in validator.result.errors)
                    assert has_error, \
                        f"Reported missing variable {var_name} should have an error message"
    
    @given(
        missing_count=st.integers(min_value=1, max_value=len(REQUIRED_VARIABLES))
    )
    @settings(max_examples=50, deadline=10000)
    def test_error_message_specificity_property(self, missing_count: int):
        """
        **Property 33: Configuration Validation Reports Missing Variables - Message Specificity**
        **Validates: Requirements 10.2**
        
        For any number of missing variables, each error message should be specific
        and include the variable name and a description of what it's for.
        """
        # Select random variables to be missing
        all_vars = list(REQUIRED_VARIABLES)
        missing_vars = set(all_vars[:missing_count])
        
        # Create configuration without missing variables
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
        
        test_config = {k: v for k, v in valid_config.items() if k not in missing_vars}
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set attributes
                for var_name in REQUIRED_VARIABLES:
                    if var_name in test_config:
                        if "PORT" in var_name:
                            setattr(mock_settings, var_name, int(test_config[var_name]))
                        else:
                            setattr(mock_settings, var_name, test_config[var_name])
                    else:
                        setattr(mock_settings, var_name, None)
                
                # Run validation
                validator = ConfigValidator()
                validator.validate_required_vars()
                
                # Property: Each error message should be specific and descriptive
                for var_name in missing_vars:
                    # Find error message for this variable
                    error_messages = [error for error in validator.result.errors if var_name in error]
                    
                    assert len(error_messages) > 0, \
                        f"Should have at least one error message for {var_name}"
                    
                    # Property: Error message should contain the variable name
                    for error_msg in error_messages:
                        assert var_name in error_msg, \
                            f"Error message should contain variable name {var_name}"
                        
                        # Property: Error message should be descriptive (not just the variable name)
                        assert len(error_msg) > len(var_name) + 10, \
                            f"Error message for {var_name} should be descriptive, not just the variable name"
                        
                        # Property: Error message should indicate it's missing/required
                        has_missing_indicator = any(
                            keyword in error_msg.lower()
                            for keyword in ["missing", "required", "not set", "invalid"]
                        )
                        assert has_missing_indicator, \
                            f"Error message for {var_name} should indicate it's missing or invalid"


# Integration test to verify property test assumptions
def test_configuration_validation_integration():
    """Integration test to verify configuration validation works correctly"""
    # Test with all variables missing
    with patch.dict(os.environ, {}, clear=True):
        with patch('app.core.config_validator.settings') as mock_settings:
            # Set all to None
            for var_name in REQUIRED_VARIABLES:
                setattr(mock_settings, var_name, None)
            
            validator = ConfigValidator()
            missing_vars = validator.validate_required_vars()
            
            # Should report all required variables as missing
            assert len(missing_vars) == len(REQUIRED_VARIABLES), \
                f"Expected {len(REQUIRED_VARIABLES)} missing variables, got {len(missing_vars)}"
            
            # Should have errors
            assert validator.result.has_errors(), "Should have errors when all variables are missing"
            
            # Each missing variable should be in the list
            for var_name in REQUIRED_VARIABLES:
                assert var_name in missing_vars, f"{var_name} should be in missing variables list"
    
    # Test with all variables present
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
        validator = ConfigValidator()
        missing_vars = validator.validate_required_vars()
        
        # Should report no missing variables
        assert len(missing_vars) == 0, "Should have no missing variables with valid config"


# Test fixtures for property tests
@pytest.fixture
def valid_environment():
    """Fixture providing a valid environment configuration"""
    return {
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


@pytest.fixture
def empty_environment():
    """Fixture providing an empty environment configuration"""
    return {}
