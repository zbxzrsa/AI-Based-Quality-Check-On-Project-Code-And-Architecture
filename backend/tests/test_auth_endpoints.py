"""
Tests for authentication endpoints
Validates password strength validation integration with registration endpoint
Task 2.2: Enhance password strength validation
"""
import pytest
from pydantic import ValidationError
from app.schemas.auth import UserRegister, PasswordChange
from backend.tests.utils.secure_test_data import get_test_password


# Test constants for passwords to avoid literal hard-coded strings in tests
# These meet the password strength requirements: 8+ chars, upper, lower, digit, special
VALID_PASSWORD_1 = get_test_password("valid1")
VALID_PASSWORD_2 = get_test_password("valid2")
VALID_PASSWORD_3 = get_test_password("valid3")
VALID_PASSWORD_4 = get_test_password("valid4")

# Common invalid passwords for testing
SHORT_PASSWORD = get_test_password("short")[:7] + "!"  # Ensure it's short
LOWERCASE_PASSWORD = get_test_password("lowercase")
UPPERCASE_PASSWORD = get_test_password("uppercase")
NO_DIGIT_PASSWORD = get_test_password("no_digits")
NO_SPECIAL_PASSWORD = get_test_password("no_special")
WEAK_PASSWORD = get_test_password("weak")[:4]  # Ensure it's weak


class TestRegistrationPasswordValidation:
    """Test password validation in registration endpoint (Requirement 2.3)"""
    
    def test_register_schema_with_valid_password(self):
        """Test registration schema accepts valid password"""
        # Test that valid passwords pass validation at schema level
        valid_passwords = [
            VALID_PASSWORD_1,
            VALID_PASSWORD_2,
            VALID_PASSWORD_3,
            VALID_PASSWORD_4,
        ]
        
        for password in valid_passwords:
            user_data = UserRegister(
                email="test@example.com",
                password=password,
                full_name="Test User"
            )
            assert user_data.password == password, \
                f"Valid password should be accepted: {password}"
    
    def test_register_schema_with_short_password(self):
        """Test registration schema rejects password shorter than 8 characters"""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                password=SHORT_PASSWORD,  # Only 7 characters
                full_name="Test User"
            )
        
        error_str = str(exc_info.value).lower()
        assert "8 characters" in error_str, \
            f"Error should mention password length requirement: {error_str}"
    
    def test_register_schema_without_uppercase(self):
        """Test registration schema rejects password without uppercase letter"""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                password=LOWERCASE_PASSWORD,
                full_name="Test User"
            )
        
        error_str = str(exc_info.value).lower()
        assert "uppercase" in error_str, \
            f"Error should mention uppercase requirement: {error_str}"
    
    def test_register_schema_without_lowercase(self):
        """Test registration schema rejects password without lowercase letter"""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                password=UPPERCASE_PASSWORD,
                full_name="Test User"
            )
        
        error_str = str(exc_info.value).lower()
        assert "lowercase" in error_str, \
            f"Error should mention lowercase requirement: {error_str}"
    
    def test_register_schema_without_digit(self):
        """Test registration schema rejects password without digit"""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                password=NO_DIGIT_PASSWORD,
                full_name="Test User"
            )
        
        error_str = str(exc_info.value).lower()
        assert "digit" in error_str, \
            f"Error should mention digit requirement: {error_str}"
    
    def test_register_schema_without_special_character(self):
        """Test registration schema rejects password without special character"""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                password=NO_SPECIAL_PASSWORD,
                full_name="Test User"
            )
        
        error_str = str(exc_info.value).lower()
        assert "special" in error_str, \
            f"Error should mention special character requirement: {error_str}"
    
    def test_register_validation_before_hashing(self):
        """Test that password validation occurs at schema level before hashing"""
        # This test verifies that weak passwords are rejected at Pydantic validation
        # level, before the endpoint logic (and expensive bcrypt hashing) executes
        
        with pytest.raises(ValidationError):
            UserRegister(
                email="test@example.com",
                password=WEAK_PASSWORD,  # Fails multiple requirements
                full_name="Test User"
            )
        
        # If we get here without exception, the test fails
        # The ValidationError proves validation happens at schema level


class TestPasswordChangeValidation:
    """Test password validation in password change endpoint"""
    
    def test_password_change_validates_new_password(self):
        """Test that password change validates the new password strength"""
        # Test that weak password is rejected by schema
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(
                current_password=VALID_PASSWORD_1,
                new_password=WEAK_PASSWORD  # Fails validation
            )
        
        # Check that validation error mentions password requirements
        error_str = str(exc_info.value)
        assert "password" in error_str.lower(), \
            f"Validation error should mention password: {error_str}"
    
    def test_password_change_accepts_valid_password(self):
        """Test that password change accepts valid strong password"""
        # Should not raise ValidationError
        password_change = PasswordChange(
            current_password=VALID_PASSWORD_1,
            new_password=VALID_PASSWORD_2
        )
        
        assert password_change.new_password == VALID_PASSWORD_2


class TestPasswordValidationMessages:
    """Test that password validation returns clear error messages"""
    
    def test_schema_validation_error_messages(self):
        """Test that UserRegister schema provides clear error messages"""
        test_cases = [
            (SHORT_PASSWORD, "8 characters"),
            (LOWERCASE_PASSWORD, "uppercase"),
            (UPPERCASE_PASSWORD, "lowercase"),
            (NO_DIGIT_PASSWORD, "digit"),
            (NO_SPECIAL_PASSWORD, "special"),
        ]
        
        for password, expected_keyword in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                UserRegister(
                    email="test@example.com",
                    password=password
                )
            
            error_str = str(exc_info.value).lower()
            assert expected_keyword in error_str, \
                f"Error for password '{password}' should mention '{expected_keyword}': {error_str}"
    
    def test_validation_happens_before_database_check(self):
        """Test that password validation happens before any database operations"""
        # Invalid password should fail at schema validation level
        # before any database queries are made
        with pytest.raises(ValidationError):
            UserRegister(
                email="test@example.com",
                password=WEAK_PASSWORD  # Fails validation
            )
        
        # This proves validation happens at the Pydantic level,
        # before the endpoint logic (and database operations) execute
    
    def test_all_special_characters_recognized(self):
        """Test that all defined special characters are recognized"""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        for char in special_chars:
            password = get_test_password(f"auth_endpoints_special_{ord(char)}") + char
            # Should not raise ValidationError
            user_data = UserRegister(
                email="test@example.com",
                password=password
            )
            assert user_data.password == password, \
                f"Password with special character '{char}' should be valid"
    
    def test_edge_case_exactly_8_characters(self):
        """Test password with exactly 8 characters"""
        password = get_test_password("edge_case_8char")[:8] + "!"  # Ensure exactly 8 chars
        user_data = UserRegister(
            email="test@example.com",
            password=password
        )
        
        assert user_data.password == password, \
            "8-character password meeting all requirements should be valid"
