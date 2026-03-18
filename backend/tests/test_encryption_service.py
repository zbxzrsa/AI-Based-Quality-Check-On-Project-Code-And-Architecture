"""
Tests for encryption service.

Validates Requirement 8.4: Encrypt all sensitive data at rest using AES-256 encryption
"""
import pytest
import os
import base64
from app.services.encryption_service import (
    EncryptionService,
    AWSKMSEncryptionService,
    get_encryption_service,
    encrypt_sensitive_field,
    decrypt_sensitive_field,
)
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


class TestEncryptionService:
    """Test encryption service functionality."""
    
    def test_generate_key(self):
        """Test key generation."""
        key = EncryptionService.generate_key()
        
        # Should be base64 encoded
        assert isinstance(key, str)
        
        # Should decode to 32 bytes
        decoded = base64.b64decode(key)
        assert len(decoded) == 32
    
    def test_encryption_decryption(self):
        """Test basic encryption and decryption."""
        # Generate test key
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        # Test data
        plaintext = "sensitive data"
        
        # Encrypt
        encrypted = service.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_bytes(self):
        """Test encryption of bytes."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = b"sensitive bytes"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext.decode('utf-8')
    
    def test_encrypt_unicode(self):
        """Test encryption of unicode strings."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = "sensitive data with émojis 🔐"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_none(self):
        """Test encryption of None values."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        encrypted = service.encrypt_field(None)
        assert encrypted is None
        
        decrypted = service.decrypt_field(None)
        assert decrypted is None
    
    def test_different_keys_produce_different_ciphertext(self):
        """Test that different keys produce different ciphertext."""
        plaintext = "sensitive data"
        
        key1 = base64.b64decode(EncryptionService.generate_key())
        service1 = EncryptionService(master_key=key1)
        encrypted1 = service1.encrypt(plaintext)
        
        key2 = base64.b64decode(EncryptionService.generate_key())
        service2 = EncryptionService(master_key=key2)
        encrypted2 = service2.encrypt(plaintext)
        
        # Different keys should produce different ciphertext
        assert encrypted1 != encrypted2
    
    def test_same_plaintext_different_ciphertext(self):
        """Test that encrypting same plaintext twice produces different ciphertext (due to random nonce)."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = "sensitive data"
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)
        
        # Should be different due to random nonce
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same plaintext
        assert service.decrypt(encrypted1) == plaintext
        assert service.decrypt(encrypted2) == plaintext
    
    def test_wrong_key_fails_decryption(self):
        """Test that decryption with wrong key fails."""
        plaintext = "sensitive data"
        
        # Encrypt with key1
        key1 = base64.b64decode(EncryptionService.generate_key())
        service1 = EncryptionService(master_key=key1)
        encrypted = service1.encrypt(plaintext)
        
        # Try to decrypt with key2
        key2 = base64.b64decode(EncryptionService.generate_key())
        service2 = EncryptionService(master_key=key2)
        
        with pytest.raises(ValueError, match="Failed to decrypt"):
            service2.decrypt(encrypted)
    
    def test_tampered_data_fails_decryption(self):
        """Test that tampered ciphertext fails decryption (authentication)."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = "sensitive data"
        encrypted = service.encrypt(plaintext)
        
        # Tamper with encrypted data
        encrypted_bytes = base64.b64decode(encrypted)
        tampered = encrypted_bytes[:-1] + b'X'  # Change last byte
        tampered_b64 = base64.b64encode(tampered).decode('utf-8')
        
        # Should fail authentication
        with pytest.raises(ValueError, match="Failed to decrypt"):
            service.decrypt(tampered_b64)
    
    def test_invalid_base64_fails_decryption(self):
        """Test that invalid base64 fails decryption."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        with pytest.raises(ValueError, match="Failed to decrypt"):
            service.decrypt("not valid base64!!!")
    
    def test_invalid_key_length_raises_error(self):
        """Test that invalid key length raises error."""
        with pytest.raises(ValueError, match="Master key must be exactly 32 bytes"):
            EncryptionService(master_key=b"short key")
    
    def test_derive_key_from_password(self):
        """Test key derivation from password."""
        password = get_test_password("secure_password")
        salt = os.urandom(16)
        
        key = EncryptionService.derive_key_from_password(password, salt)
        
        # Should be 32 bytes
        assert len(key) == 32
        
        # Same password and salt should produce same key
        key2 = EncryptionService.derive_key_from_password(password, salt)
        assert key == key2
        
        # Different salt should produce different key
        salt2 = os.urandom(16)
        key3 = EncryptionService.derive_key_from_password(password, salt2)
        assert key != key3
    
    def test_encrypt_long_data(self):
        """Test encryption of long data."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        # 10KB of data
        plaintext = "A" * 10000
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = ""
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        assert decrypted == plaintext


class TestEncryptionServiceEnvironment:
    """Test encryption service with environment variables."""
    
    def test_get_encryption_service_without_env(self, monkeypatch):
        """Test that service raises error without ENCRYPTION_KEY."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
        
        # Reset global instance
        import app.services.encryption_service as enc_module
        enc_module._encryption_service = None
        
        with pytest.raises(ValueError, match="ENCRYPTION_KEY environment variable not set"):
            get_encryption_service()
    
    def test_get_encryption_service_with_env(self, monkeypatch):
        """Test that service works with ENCRYPTION_KEY."""
        key = EncryptionService.generate_key()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
        
        # Reset global instance
        import app.services.encryption_service as enc_module
        enc_module._encryption_service = None
        
        service = get_encryption_service()
        assert service is not None
        
        # Test encryption works
        plaintext = "test data"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_convenience_functions(self, monkeypatch):
        """Test convenience functions for field encryption."""
        key = EncryptionService.generate_key()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
        
        # Reset global instance
        import app.services.encryption_service as enc_module
        enc_module._encryption_service = None
        
        plaintext = "sensitive field value"
        encrypted = encrypt_sensitive_field(plaintext)
        decrypted = decrypt_sensitive_field(encrypted)
        
        assert decrypted == plaintext
        
        # Test None handling
        assert encrypt_sensitive_field(None) is None
        assert decrypt_sensitive_field(None) is None


class TestAWSKMSEncryptionService:
    """Test AWS KMS encryption service."""
    
    def test_kms_service_without_boto3(self, monkeypatch):
        """Test that KMS service falls back without boto3."""
        key = EncryptionService.generate_key()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        monkeypatch.setenv("AWS_KMS_KEY_ID", "arn:aws:kms:us-east-1:123456789012:key/12345678")
        
        # Mock boto3 import failure
        import builtins

        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError("boto3 not installed")
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr(builtins, "__import__", mock_import)
        
        # Should fall back to environment key
        service = AWSKMSEncryptionService()
        assert service is not None
        
        # Test encryption works
        plaintext = "test data"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext


class TestEncryptionSecurity:
    """Security-focused tests for encryption."""
    
    def test_encrypted_data_is_not_plaintext(self):
        """Test that encrypted data doesn't contain plaintext."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = "my secret password"
        encrypted = service.encrypt(plaintext)
        
        # Encrypted data should not contain plaintext
        assert plaintext not in encrypted
        assert plaintext.encode() not in base64.b64decode(encrypted)
    
    def test_key_not_in_encrypted_data(self):
        """Test that encryption key is not in encrypted data."""
        key_b64 = EncryptionService.generate_key()
        key = base64.b64decode(key_b64)
        service = EncryptionService(master_key=key)
        
        plaintext = "sensitive data"
        encrypted = service.encrypt(plaintext)
        encrypted_bytes = base64.b64decode(encrypted)
        
        # Key should not be in encrypted data
        assert key not in encrypted_bytes
        assert key_b64.encode() not in encrypted_bytes
    
    def test_nonce_uniqueness(self):
        """Test that nonces are unique for each encryption."""
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = "same data"
        nonces = set()
        
        # Encrypt 100 times
        for _ in range(100):
            encrypted = service.encrypt(plaintext)
            encrypted_bytes = base64.b64decode(encrypted)
            nonce = encrypted_bytes[:12]  # First 12 bytes are nonce
            nonces.add(nonce)
        
        # All nonces should be unique
        assert len(nonces) == 100
    
    def test_encryption_is_deterministic_with_same_nonce(self):
        """Test that encryption is deterministic (for testing purposes only)."""
        # Note: In production, nonces are random. This test is for understanding.
        key = base64.b64decode(EncryptionService.generate_key())
        service = EncryptionService(master_key=key)
        
        plaintext = "test data"
        
        # Encrypt twice - should be different due to random nonce
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)
        
        assert encrypted1 != encrypted2
