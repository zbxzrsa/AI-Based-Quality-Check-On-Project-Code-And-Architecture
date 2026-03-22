"""
Tests for password service
Validates bcrypt configuration and password hashing security
"""
import pytest
import re
from app.utils.password import (
    hash_password,
    verify_password,
    validate_password_strength,
    validate_password_config
)
from app.core.config import settings
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


class TestBcryptConfiguration:
    """Test bcrypt configuration (Requirement 2.1)"""
    
    def test_bcrypt_rounds_minimum(self):
        """Test that bcrypt is configured with minimum 12 rounds"""
        # Requirement 2.1: Use bcrypt with minimum 12 salt rounds
        assert settings.BCRYPT_ROUNDS >= 12, "BCRYPT_ROUNDS must be at least 12"
    
    def test_bcrypt_rounds_in_pwd_context(self):
        """Test that pwd_context uses the configured bcrypt rounds"""
        # Verify the rounds are configured by hashing a password
        # and checking the rounds in the resulting hash
        test_password = get_test_password("test_password")
        hashed = hash_password(test_password)
        
        # Bcrypt hash format: $2b$rounds$salt+hash
        # Extract rounds from the hash
        match = re.match(r'\$2[aby]\$(\d+)\$', hashed)
        assert match is not None, "Hash should be in bcrypt format"
        
        rounds_in_hash = int(match.group(1))
        assert rounds_in_hash == settings.BCRYPT_ROUNDS, \
            f"Hash should use {settings.BCRYPT_ROUNDS} rounds, got {rounds_in_hash}"
    
    def test_validate_password_config_success(self):
        """Test that password config validation passes with valid settings"""
        # Should not raise an exception
        validate_password_config()
    
    def test_validate_password_config_failure(self, monkeypatch):
        """Test that password config validation fails with invalid settings"""
        # Temporarily set BCRYPT_ROUNDS to an invalid value
        monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 10)
        
        with pytest.raises(ValueError, match="BCRYPT_ROUNDS must be at least 12"):
            validate_password_config()


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password_creates_valid_hash(self):
        """Test that hash_password creates a valid bcrypt hash"""
        password = get_test_password("test_password")
        hashed = hash_password(password)
        
        # Bcrypt hash should start with $2b$ (or $2a$/$2y$)
        assert hashed.startswith(('$2b$', '$2a$', '$2y$')), \
            "Hash should be in bcrypt format"
        
        # Hash should be 60 characters long
        assert len(hashed) == 60, "Bcrypt hash should be 60 characters"
    
    def test_hash_password_different_salts(self):
        """Test that hashing the same password twice produces different hashes"""
        password = get_test_password("test_password")
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Different salts should produce different hashes
        assert hash1 != hash2, "Same password should produce different hashes (different salts)"
    
    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password"""
        password = get_test_password("test_password")
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True, \
            "Correct password should verify successfully"
    
    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password"""
        password = get_test_password("test_password")
        wrong_password = get_test_password("wrong_password")
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False, \
            "Incorrect password should not verify"
    
    def test_verify_password_handles_invalid_hash(self):
        """Test that verify_password handles invalid hash gracefully"""
        password = get_test_password("test_password")
        invalid_hash = "not_a_valid_hash"
        
        # Should return False, not raise an exception
        assert verify_password(password, invalid_hash) is False, \
            "Invalid hash should return False, not raise exception"
    
    def test_hash_password_with_special_characters(self):
        """Test hashing passwords with special characters"""
        passwords = [
            "P@ssw0rd!",
            "Test#123$",
            "Complex&Pass^123",
            "Unicode™Password®123",
        ]
        
        for password in passwords:
            hashed = hash_password(password)
            assert verify_password(password, hashed) is True, \
                f"Password with special characters should hash and verify: {password}"
    
    def test_hash_password_with_unicode(self):
        """Test hashing passwords with unicode characters"""
        password = get_test_password("unicode_password")  # Russian characters
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True, \
            "Unicode password should hash and verify correctly"


class TestPasswordStrengthValidation:
    """Test password strength validation (Requirement 2.3)"""
    
    def test_valid_password(self):
        """Test that valid passwords pass validation"""
        valid_passwords = [
            "TestPass123!",
            "Str0ng@Password",
            "C0mpl3x#Pass",
            "MyP@ssw0rd123",
        ]
        
        for password in valid_passwords:
            is_valid, message = validate_password_strength(password)
            assert is_valid is True, f"Valid password should pass: {password}"
            assert message == "", f"Valid password should have no error message: {password}"
    
    def test_password_too_short(self):
        """Test that passwords shorter than 8 characters fail"""
        short_passwords = [
            "Test1!",
            "Ab1!",
            "Short1!",
        ]
        
        for password in short_passwords:
            is_valid, message = validate_password_strength(password)
            assert is_valid is False, f"Short password should fail: {password}"
            assert "at least 8 characters" in message, \
                f"Error message should mention length: {message}"
    
    def test_password_no_uppercase(self):
        """Test that passwords without uppercase letters fail"""
        password = get_test_password("testpass")
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False, "Password without uppercase should fail"
        assert "uppercase letter" in message, \
            f"Error message should mention uppercase: {message}"
    
    def test_password_no_lowercase(self):
        """Test that passwords without lowercase letters fail"""
        password = get_test_password("testpass_upper")
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False, "Password without lowercase should fail"
        assert "lowercase letter" in message, \
            f"Error message should mention lowercase: {message}"
    
    def test_password_no_digit(self):
        """Test that passwords without digits fail"""
        password = get_test_password("test_no_digit")
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False, "Password without digit should fail"
        assert "digit" in message, \
            f"Error message should mention digit: {message}"
    
    def test_password_no_special_character(self):
        """Test that passwords without special characters fail"""
        password = get_test_password("test_no_special")
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False, "Password without special character should fail"
        assert "special character" in message, \
            f"Error message should mention special character: {message}"
    
    def test_password_edge_case_exactly_8_chars(self):
        """Test password with exactly 8 characters"""
        password = get_test_password("test_short")
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is True, "8-character password meeting all requirements should pass"
        assert message == "", "Valid password should have no error message"
    
    def test_password_with_all_special_chars(self):
        """Test that all defined special characters are recognized"""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        for char in special_chars:
            password = get_test_password(f"special_char_{ord(char)}") + char
            is_valid, message = validate_password_strength(password)
            assert is_valid is True, \
                f"Password with special character '{char}' should be valid"


class TestPasswordSecurity:
    """Test password security features"""
    
    def test_constant_time_comparison(self):
        """Test that password verification uses constant-time comparison"""
        # This is a behavioral test - we can't directly test timing,
        # but we can verify that passlib's verify method is used,
        # which implements constant-time comparison
        
        password = get_test_password("test_password")
        hashed = hash_password(password)
        
        # Both correct and incorrect passwords should complete
        # (passlib handles constant-time internally)
        result1 = verify_password(password, hashed)
        result2 = verify_password("WrongPassword123!", hashed)
        
        assert result1 is True
        assert result2 is False
    
    def test_no_plaintext_in_hash(self):
        """Test that plaintext password is not present in hash"""
        password = get_test_password("test_password")
        hashed = hash_password(password)
        
        # Password should not appear in the hash
        assert password not in hashed, \
            "Plaintext password should not appear in hash"
        
        # Even parts of the password should not be easily identifiable
        assert "TestPassword" not in hashed
        assert "123!" not in hashed
    
    def test_hash_length_consistency(self):
        """Test that all hashes have consistent length"""
        passwords = [
            "Short1!",
            "MediumPassword123!",
            "VeryLongPasswordWithManyCharacters123!@#",
        ]
        
        hashes = [hash_password(p) for p in passwords]
        
        # All bcrypt hashes should be 60 characters
        for hashed in hashes:
            assert len(hashed) == 60, \
                "All bcrypt hashes should be 60 characters regardless of password length"


class TestPasswordConfigurationIntegration:
    """Integration tests for password configuration"""
    
    def test_settings_bcrypt_rounds_used(self):
        """Test that settings.BCRYPT_ROUNDS is actually used"""
        # Hash a password and verify the rounds in the hash match settings
        password = get_test_password("test_password")
        hashed = hash_password(password)
        
        # Extract rounds from hash
        match = re.match(r'\$2[aby]\$(\d+)\$', hashed)
        rounds_in_hash = int(match.group(1))
        
        assert rounds_in_hash == settings.BCRYPT_ROUNDS, \
            f"Hash should use settings.BCRYPT_ROUNDS ({settings.BCRYPT_ROUNDS}), got {rounds_in_hash}"
    
    def test_security_validation_warns_on_low_rounds(self, monkeypatch):
        """Test that security validation warns when rounds are too low"""
        # Set rounds to 10 (below minimum)
        monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 10)
        
        warnings = settings.validate_security_settings()
        
        # Should have a warning about bcrypt rounds
        assert any("BCRYPT_ROUNDS" in warning for warning in warnings), \
            "Should warn about low BCRYPT_ROUNDS"
    
    def test_security_validation_warns_on_high_rounds(self, monkeypatch):
        """Test that security validation warns when rounds are very high"""
        # Set rounds to 25 (very high, may impact performance)
        monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 25)
        
        warnings = settings.validate_security_settings()
        
        # Should have a warning about high bcrypt rounds
        assert any("BCRYPT_ROUNDS" in warning and "high" in warning for warning in warnings), \
            "Should warn about very high BCRYPT_ROUNDS"
    
    def test_no_warnings_with_valid_rounds(self, monkeypatch):
        """Test that no warnings are generated with valid rounds"""
        # Set rounds to 12 (minimum valid)
        monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 12)
        
        warnings = settings.validate_security_settings()
        
        # Should not have warnings about bcrypt rounds
        bcrypt_warnings = [w for w in warnings if "BCRYPT_ROUNDS" in w]
        assert len(bcrypt_warnings) == 0, \
            "Should not warn about BCRYPT_ROUNDS when set to valid value"
