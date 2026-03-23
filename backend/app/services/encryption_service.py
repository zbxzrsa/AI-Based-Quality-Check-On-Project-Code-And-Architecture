"""
Data Encryption Service for encrypting sensitive data at rest.

Implements Requirement 8.4: Encrypt all sensitive data at rest using AES-256 encryption

This service provides:
- AES-256-GCM encryption for data at rest
- Key derivation from master key using PBKDF2
- Secure key management with AWS KMS integration
- Field-level encryption for database columns
"""
import os
import base64
import logging
from typing import Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data at rest.
    
    Uses AES-256-GCM for authenticated encryption with:
    - 256-bit keys
    - 96-bit nonces (IVs)
    - 128-bit authentication tags
    
    Validates Requirement 8.4
    """
    
    # AES-256 requires 32-byte keys
    KEY_SIZE = 32
    # GCM recommended nonce size
    NONCE_SIZE = 12
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize encryption service with master key.
        
        Args:
            master_key: 32-byte master encryption key. If None, generates from environment.
        
        Raises:
            ValueError: If master key is invalid
        """
        if master_key is None:
            master_key = self._get_master_key_from_env()
        
        if len(master_key) != self.KEY_SIZE:
            raise ValueError(f"Master key must be exactly {self.KEY_SIZE} bytes")
        
        self.master_key = master_key
        self.aesgcm = AESGCM(master_key)
    
    def _get_master_key_from_env(self) -> bytes:
        """
        Get master encryption key from environment variable.
        
        Returns:
            32-byte master key
        
        Raises:
            ValueError: If ENCRYPTION_KEY is not set or invalid
        """
        key_b64 = os.getenv("ENCRYPTION_KEY")
        
        if not key_b64:
            raise ValueError(
                "ENCRYPTION_KEY environment variable not set. "
                "Generate with: python -c 'import os, base64; logger.info(str(base64.b64encode(os.urandom(32))).decode())'"
            )
        
        try:
            key = base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY format (must be base64): {e}")
        
        if len(key) != self.KEY_SIZE:
            raise ValueError(
                f"ENCRYPTION_KEY must be {self.KEY_SIZE} bytes when decoded, got {len(key)} bytes"
            )
        
        return key
    
    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """
        Encrypt plaintext data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt (string or bytes)
        
        Returns:
            Base64-encoded encrypted data with format: nonce||ciphertext||tag
        
        Validates Requirement 8.4
        """
        # Convert string to bytes
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Generate random nonce (IV)
        nonce = os.urandom(self.NONCE_SIZE)
        
        # Encrypt with AES-256-GCM (includes authentication tag)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)
        
        # Combine nonce + ciphertext for storage
        encrypted_data = nonce + ciphertext
        
        # Encode as base64 for database storage
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data using AES-256-GCM.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
        
        Returns:
            Decrypted plaintext as string
        
        Raises:
            ValueError: If decryption fails (wrong key, corrupted data, or tampered data)
        
        Validates Requirement 8.4
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Extract nonce and ciphertext
            nonce = encrypted_bytes[:self.NONCE_SIZE]
            ciphertext = encrypted_bytes[self.NONCE_SIZE:]
            
            # Decrypt and verify authentication tag
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data - invalid key or corrupted data")
    
    def encrypt_field(self, value: Optional[str]) -> Optional[str]:
        """
        Encrypt a database field value.
        
        Args:
            value: Field value to encrypt (None values are preserved)
        
        Returns:
            Encrypted value or None
        
        Validates Requirement 8.4
        """
        if value is None:
            return None
        return self.encrypt(value)
    
    def decrypt_field(self, encrypted_value: Optional[str]) -> Optional[str]:
        """
        Decrypt a database field value.
        
        Args:
            encrypted_value: Encrypted field value (None values are preserved)
        
        Returns:
            Decrypted value or None
        
        Validates Requirement 8.4
        """
        if encrypted_value is None:
            return None
        return self.decrypt(encrypted_value)
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random 256-bit encryption key.
        
        Returns:
            Base64-encoded 32-byte key suitable for ENCRYPTION_KEY environment variable
        """
        key = os.urandom(EncryptionService.KEY_SIZE)
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (should be stored with encrypted data)
        
        Returns:
            32-byte derived key
        
        Note: This is for password-based encryption. For general data encryption,
        use a randomly generated key instead.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=EncryptionService.KEY_SIZE,
            salt=salt,
            iterations=100000,  # OWASP recommendation
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))


class AWSKMSEncryptionService(EncryptionService):
    """
    Encryption service with AWS KMS integration for key management.
    
    Uses AWS KMS to:
    - Generate and manage data encryption keys (DEKs)
    - Encrypt DEKs with Customer Master Keys (CMKs)
    - Rotate keys automatically
    
    Validates Requirement 8.4
    """
    
    def __init__(self, kms_key_id: Optional[str] = None):
        """
        Initialize KMS encryption service.
        
        Args:
            kms_key_id: AWS KMS key ID or ARN. If None, uses ENCRYPTION_KEY from environment.
        """
        self.kms_key_id = kms_key_id or os.getenv("AWS_KMS_KEY_ID")
        
        if self.kms_key_id:
            # Initialize AWS KMS client
            try:
                import boto3
                self.kms_client = boto3.client('kms')
                logger.info(f"AWS KMS encryption enabled with key: {self.kms_key_id}")
                
                # Generate data encryption key from KMS
                master_key = self._generate_data_key()
            except ImportError:
                logger.warning("boto3 not installed, falling back to environment key")
                master_key = None
            except Exception as e:
                logger.error(f"Failed to initialize AWS KMS: {e}")
                master_key = None
        else:
            logger.info("AWS KMS not configured, using environment key")
            master_key = None
        
        # Initialize parent with master key
        super().__init__(master_key=master_key)
    
    def _generate_data_key(self) -> bytes:
        """
        Generate data encryption key using AWS KMS.
        
        Returns:
            32-byte plaintext data key
        
        Raises:
            Exception: If KMS operation fails
        """
        response = self.kms_client.generate_data_key(
            KeyId=self.kms_key_id,
            KeySpec='AES_256'
        )
        
        # Store encrypted data key for future use
        self.encrypted_data_key = response['CiphertextBlob']
        
        # Return plaintext key for encryption operations
        return response['Plaintext']
    
    def rotate_key(self) -> None:
        """
        Rotate the data encryption key using AWS KMS.
        
        This generates a new DEK and updates the service.
        Existing encrypted data must be re-encrypted with the new key.
        """
        logger.info("Rotating encryption key via AWS KMS")
        new_key = self._generate_data_key()
        self.master_key = new_key
        self.aesgcm = AESGCM(new_key)
        logger.info("Encryption key rotated successfully")


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get global encryption service instance.
    
    Returns:
        Configured encryption service
    
    Validates Requirement 8.4
    """
    global _encryption_service
    
    if _encryption_service is None:
        # Check if AWS KMS is configured
        kms_key_id = os.getenv("AWS_KMS_KEY_ID")
        
        if kms_key_id:
            try:
                _encryption_service = AWSKMSEncryptionService(kms_key_id)
                logger.info("Initialized AWS KMS encryption service")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS KMS, using standard encryption: {e}")
                _encryption_service = EncryptionService()
        else:
            _encryption_service = EncryptionService()
            logger.info("Initialized standard encryption service")
    
    return _encryption_service


def encrypt_sensitive_field(value: Optional[str]) -> Optional[str]:
    """
    Convenience function to encrypt a sensitive field.
    
    Args:
        value: Field value to encrypt
    
    Returns:
        Encrypted value
    
    Validates Requirement 8.4
    """
    return get_encryption_service().encrypt_field(value)


def decrypt_sensitive_field(encrypted_value: Optional[str]) -> Optional[str]:
    """
    Convenience function to decrypt a sensitive field.
    
    Args:
        encrypted_value: Encrypted field value
    
    Returns:
        Decrypted value
    
    Validates Requirement 8.4
    """
    return get_encryption_service().decrypt_field(encrypted_value)
