"""
Custom SQLAlchemy types for encrypted database fields.

Implements Requirement 8.4: Encrypt all sensitive data at rest using AES-256 encryption

This module provides SQLAlchemy custom types that automatically encrypt/decrypt
data when reading from and writing to the database.
"""
import logging
logger = logging.getLogger(__name__)

from typing import Optional
from sqlalchemy import TypeDecorator, Text
from sqlalchemy.engine import Dialect


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type for encrypted string fields.
    
    Automatically encrypts data on write and decrypts on read.
    Stores encrypted data as TEXT in the database.
    
    Usage:
        class User(Base):
            __tablename__ = "users"
            api_key = Column(EncryptedString(255))
    
    Validates Requirement 8.4
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, length: Optional[int] = None, *args, **kwargs):
        """
        Initialize encrypted string type.
        
        Args:
            length: Maximum length of plaintext (for documentation only)
        """
        self.length = length
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """
        Encrypt value before storing in database.
        
        Args:
            value: Plaintext value to encrypt
            dialect: Database dialect
        
        Returns:
            Encrypted value or None
        """
        if value is None:
            return None
        
        # Import here to avoid circular dependency
        from app.services.encryption_service import get_encryption_service
        
        encryption_service = get_encryption_service()
        return encryption_service.encrypt(value)
    
    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """
        Decrypt value after reading from database.
        
        Args:
            value: Encrypted value from database
            dialect: Database dialect
        
        Returns:
            Decrypted plaintext or None
        """
        if value is None:
            return None
        
        # Import here to avoid circular dependency
        from app.services.encryption_service import get_encryption_service
        
        encryption_service = get_encryption_service()
        try:
            return encryption_service.decrypt(value)
        except Exception:
            # If decryption fails, return None (could be unencrypted legacy data)
            return None


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy type for encrypted text fields (longer content).
    
    Similar to EncryptedString but for TEXT columns.
    
    Usage:
        class User(Base):
            __tablename__ = "users"
            private_notes = Column(EncryptedText)
    
    Validates Requirement 8.4
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        
        from app.services.encryption_service import get_encryption_service
        
        encryption_service = get_encryption_service()
        return encryption_service.encrypt(value)
    
    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """Decrypt value after reading from database."""
        if value is None:
            return None
        
        from app.services.encryption_service import get_encryption_service
        
        encryption_service = get_encryption_service()
        try:
            return encryption_service.decrypt(value)
        except Exception:
            return None


def encrypt_existing_field(session, model_class, field_name: str) -> int:
    """
    Encrypt existing plaintext data in a database field.
    
    This is a migration helper to encrypt existing data when adding
    encryption to an existing field.
    
    Args:
        session: SQLAlchemy session
        model_class: Model class containing the field
        field_name: Name of the field to encrypt
    
    Returns:
        Number of records encrypted
    
    Example:
        from app.models import User
        from app.database.postgresql import get_db
        
        async with get_db() as session:
            count = encrypt_existing_field(session, User, "api_key")
            logger.info("Encrypted {count} records")
    
    Validates Requirement 8.4
    """
    from app.services.encryption_service import get_encryption_service
    
    encryption_service = get_encryption_service()
    
    # Get all records with non-null field values
    records = session.query(model_class).filter(
        getattr(model_class, field_name).isnot(None)
    ).all()
    
    count = 0
    for record in records:
        plaintext = getattr(record, field_name)
        
        # Skip if already encrypted (check for base64 format)
        if plaintext and not plaintext.startswith("gAAAAA"):  # AES-GCM encrypted data pattern
            try:
                encrypted = encryption_service.encrypt(plaintext)
                setattr(record, field_name, encrypted)
                count += 1
            except Exception as e:
                logger.info("Failed to encrypt record {record.id}: {e}")
    
    session.commit()
    return count
