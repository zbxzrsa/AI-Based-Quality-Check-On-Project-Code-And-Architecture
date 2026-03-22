"""
Unit tests for JWT service
Tests JWT token generation, validation, and JTI functionality
"""
import os
import base64
import json
import sys
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt

# Add backend directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    get_token_expiry
)
from app.core.config import settings


class TestJWTTokenGeneration:
    """Test JWT token generation with JTI"""
    
    def test_access_token_includes_jti(self):
        """Test that access tokens include a unique JTI"""
        data = {"sub": "test@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        # Decode token to inspect payload
        payload = decode_token(token)
        
        assert payload is not None
        assert "jti" in payload, "Access token must include JTI"
        assert isinstance(payload["jti"], str), "JTI must be a string"
        assert len(payload["jti"]) > 0, "JTI must not be empty"
    
    def test_refresh_token_includes_jti(self):
        """Test that refresh tokens include a unique JTI"""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        # Decode token to inspect payload
        payload = decode_token(token)
        
        assert payload is not None
        assert "jti" in payload, "Refresh token must include JTI"
        assert isinstance(payload["jti"], str), "JTI must be a string"
        assert len(payload["jti"]) > 0, "JTI must not be empty"
    
    def test_jti_is_unique_across_tokens(self):
        """Test that each token gets a unique JTI"""
        data = {"sub": "test@example.com", "user_id": "123"}
        
        # Generate multiple tokens
        token1 = create_access_token(data)
        token2 = create_access_token(data)
        token3 = create_access_token(data)
        
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        payload3 = decode_token(token3)
        
        # All JTIs should be different
        assert payload1["jti"] != payload2["jti"]
        assert payload1["jti"] != payload3["jti"]
        assert payload2["jti"] != payload3["jti"]
    
    def test_jti_is_valid_uuid(self):
        """Test that JTI is a valid UUID string"""
        import uuid
        
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        # Should be able to parse as UUID
        try:
            uuid.UUID(payload["jti"])
        except ValueError:
            pytest.fail("JTI should be a valid UUID string")
    
    def test_access_token_includes_type(self):
        """Test that access tokens include correct type"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload["type"] == "access"
    
    def test_refresh_token_includes_type(self):
        """Test that refresh tokens include correct type"""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        
        assert payload["type"] == "refresh"
    
    def test_access_token_includes_expiration(self):
        """Test that access tokens include expiration"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert "exp" in payload
        assert isinstance(payload["exp"], int)
        
        # Should expire in approximately 15 minutes (default)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp_time - now
        
        # Allow some tolerance (14-16 minutes)
        assert 14 * 60 < delta.total_seconds() < 16 * 60
    
    def test_refresh_token_includes_expiration(self):
        """Test that refresh tokens include expiration"""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        
        assert "exp" in payload
        assert isinstance(payload["exp"], int)
        
        # Should expire in approximately 7 days (default)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp_time - now
        
        # Allow some tolerance (6.9-7.1 days)
        assert 6.9 * 24 * 60 * 60 < delta.total_seconds() < 7.1 * 24 * 60 * 60
    
    def test_custom_expiration_delta(self):
        """Test that custom expiration delta is respected"""
        data = {"sub": "test@example.com"}
        custom_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta=custom_delta)
        payload = decode_token(token)
        
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp_time - now
        
        # Should be approximately 2 hours
        assert 1.9 * 60 * 60 < delta.total_seconds() < 2.1 * 60 * 60
    
    def test_token_includes_original_data(self):
        """Test that token includes all original data"""
        data = {
            "sub": "test@example.com",
            "user_id": "123",
            "role": "admin",
            "email": "test@example.com"
        }
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload["sub"] == data["sub"]
        assert payload["user_id"] == data["user_id"]
        assert payload["role"] == data["role"]
        assert payload["email"] == data["email"]


class TestJWTTokenValidation:
    """Test JWT token validation"""
    
    def test_valid_access_token_verification(self):
        """Test that valid access tokens are verified correctly"""
        data = {"sub": "test@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        payload = verify_token(token, token_type="access")
        
        assert payload is not None
        assert payload["sub"] == data["sub"]
        assert payload["type"] == "access"
    
    def test_valid_refresh_token_verification(self):
        """Test that valid refresh tokens are verified correctly"""
        data = {"sub": "123"}
        token = create_refresh_token(data)
        
        payload = verify_token(token, token_type="refresh")
        
        assert payload is not None
        assert payload["sub"] == data["sub"]
        assert payload["type"] == "refresh"
    
    def test_token_type_mismatch_rejected(self):
        """Test that tokens with wrong type are rejected"""
        data = {"sub": "test@example.com"}
        access_token = create_access_token(data)
        
        # Try to verify as refresh token
        payload = verify_token(access_token, token_type="refresh")
        
        assert payload is None
    
    def test_refresh_token_rejected_as_access_token(self):
        """Test that refresh tokens cannot be used as access tokens"""
        data = {"sub": "test@example.com", "user_id": "123"}
        refresh_token = create_refresh_token(data)
        
        # Try to verify as access token
        payload = verify_token(refresh_token, token_type="access")
        
        assert payload is None, "Refresh token should not be accepted as access token"
    
    def test_access_token_rejected_as_refresh_token(self):
        """Test that access tokens cannot be used as refresh tokens"""
        data = {"sub": "123"}
        access_token = create_access_token(data)
        
        # Try to verify as refresh token
        payload = verify_token(access_token, token_type="refresh")
        
        assert payload is None, "Access token should not be accepted as refresh token"
    
    def test_token_type_validation_prevents_confusion_attacks(self):
        """Test that token type validation prevents token confusion attacks"""
        # Create both token types with same data
        data = {"sub": "test@example.com", "user_id": "123", "role": "admin"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)
        
        # Verify access token works as access
        access_payload = verify_token(access_token, token_type="access")
        assert access_payload is not None
        assert access_payload["type"] == "access"
        
        # Verify refresh token works as refresh
        refresh_payload = verify_token(refresh_token, token_type="refresh")
        assert refresh_payload is not None
        assert refresh_payload["type"] == "refresh"
        
        # Verify cross-usage is rejected
        assert verify_token(access_token, token_type="refresh") is None
        assert verify_token(refresh_token, token_type="access") is None
    
    def test_token_without_type_field_rejected(self):
        """Test that tokens without type field are rejected"""
        from jose import jwt as jose_jwt
        
        # Manually create a token without type field
        data = {"sub": "test@example.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jose_jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        
        # Should be rejected when verifying
        payload = verify_token(token, token_type="access")
        assert payload is None, "Token without type field should be rejected"
    
    def test_token_with_invalid_type_value_rejected(self):
        """Test that tokens with invalid type values are rejected"""
        from jose import jwt as jose_jwt
        
        # Manually create a token with invalid type
        data = {
            "sub": "test@example.com",
            "type": "invalid_type",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token = jose_jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        
        # Should be rejected when verifying as access or refresh
        assert verify_token(token, token_type="access") is None
        assert verify_token(token, token_type="refresh") is None
    
    def test_multiple_tokens_same_user_different_types(self):
        """Test that same user can have both access and refresh tokens simultaneously"""
        user_data = {"sub": "user123", "email": "user@example.com"}
        
        # Create both token types
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token({"sub": "user123"})
        
        # Both should be valid for their respective types
        access_payload = verify_token(access_token, token_type="access")
        refresh_payload = verify_token(refresh_token, token_type="refresh")
        
        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        
        # But not for the opposite type
        assert verify_token(access_token, token_type="refresh") is None
        assert verify_token(refresh_token, token_type="access") is None
    
    def test_invalid_token_rejected(self):
        """Test that invalid tokens are rejected"""
        invalid_token = "invalid.token.string"
        
        payload = decode_token(invalid_token)
        
        assert payload is None
    
    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected"""
        data = {"sub": "test@example.com"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = decode_token(token)
        
        # Token should be rejected due to expiration
        assert payload is None
    
    def test_tampered_token_rejected(self):
        """Test that tampered tokens are rejected"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        # Tamper with the token
        parts = token.split('.')
        if len(parts) == 3:
            # Modify the payload
            tampered_token = parts[0] + '.modified.' + parts[2]
            
            payload = decode_token(tampered_token)
            
            assert payload is None


class TestJWTUtilityFunctions:
    """Test JWT utility functions"""
    
    def test_get_token_expiry(self):
        """Test getting expiration time from token"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        expiry = get_token_expiry(token)
        
        assert expiry is not None
        assert isinstance(expiry, datetime)
        
        # Should be in the future
        assert expiry > datetime.now()
    
    def test_get_token_expiry_invalid_token(self):
        """Test getting expiry from invalid token returns None"""
        invalid_token = "invalid.token.string"
        
        expiry = get_token_expiry(invalid_token)
        
        assert expiry is None
    
    def test_decode_token_returns_all_fields(self):
        """Test that decode_token returns all token fields including JTI"""
        data = {"sub": "test@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert "sub" in payload
        assert "user_id" in payload
        assert "type" in payload
        assert "exp" in payload
        assert "jti" in payload


class TestJWTAlgorithm:
    """Test JWT algorithm configuration"""

    @staticmethod
    def _decode_jwt_header(token: str) -> dict:
        """Decode JWT header payload without invoking JWT library unverified helpers."""
        header_segment = token.split(".")[0]
        padded = header_segment + "=" * ((4 - len(header_segment) % 4) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
        return json.loads(decoded_bytes.decode("utf-8"))
    
    def test_token_uses_hs256_algorithm(self):
        """Test that tokens use HS256 algorithm"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        header = self._decode_jwt_header(token)
        
        assert header["alg"] == "HS256", "Token must use HS256 algorithm"
    
    def test_token_signature_valid(self):
        """Test that token signature is valid"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        # Should decode successfully with correct secret
        payload = jose_jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        assert payload is not None
        assert payload["sub"] == data["sub"]
    
    def test_token_signature_invalid_with_wrong_secret(self):
        """Test that token signature fails with wrong secret"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        # Should fail with wrong secret
        with pytest.raises(Exception):
            jose_jwt.decode(
                token,
                "wrong_secret_key",
                algorithms=[settings.JWT_ALGORITHM]
            )



class TestJWTTokenRevocation:
    """Test JWT token revocation functionality"""
    
    @pytest.mark.asyncio
    async def test_revoke_token_adds_to_blacklist(self):
        """Test that revoking a token adds JTI to Redis blacklist"""
        from app.utils.jwt import revoke_token, is_token_revoked
        
        jti = "test-jti-12345"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Revoke the token
        await revoke_token(jti, expires_at)
        
        # Check it's in the blacklist
        is_revoked = await is_token_revoked(jti)
        assert is_revoked is True, "Revoked token should be in blacklist"
    
    @pytest.mark.asyncio
    async def test_non_revoked_token_not_in_blacklist(self):
        """Test that non-revoked tokens are not in blacklist"""
        from app.utils.jwt import is_token_revoked
        
        jti = "non-existent-jti-99999"
        
        # Check it's not in the blacklist
        is_revoked = await is_token_revoked(jti)
        assert is_revoked is False, "Non-revoked token should not be in blacklist"
    
    @pytest.mark.asyncio
    async def test_revoked_token_ttl_matches_expiration(self):
        """Test that revoked token TTL matches token expiration"""
        from app.utils.jwt import revoke_token
        from app.database.redis_db import get_redis
        
        jti = "test-jti-ttl-check"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        
        # Revoke the token
        await revoke_token(jti, expires_at)
        
        # Check TTL in Redis
        redis_client = await get_redis()
        key = f"revoked:jti:{jti}"
        ttl = await redis_client.ttl(key)
        
        # TTL should be approximately 60 seconds (allow some tolerance)
        assert 55 <= ttl <= 65, f"TTL should be ~60 seconds, got {ttl}"
    
    @pytest.mark.asyncio
    async def test_expired_token_not_added_to_blacklist(self):
        """Test that already-expired tokens are not added to blacklist"""
        from app.utils.jwt import revoke_token, is_token_revoked
        
        jti = "expired-token-jti"
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Already expired
        
        # Try to revoke the expired token
        await revoke_token(jti, expires_at)
        
        # Should not be in blacklist (no point storing expired tokens)
        is_revoked = await is_token_revoked(jti)
        assert is_revoked is False, "Expired tokens should not be added to blacklist"
    
    @pytest.mark.asyncio
    async def test_verify_token_with_revocation_rejects_revoked_token(self):
        """Test that verify_token_with_revocation rejects revoked tokens"""
        from app.utils.jwt import revoke_token, verify_token_with_revocation
        
        # Create a token
        data = {"sub": "test@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        # Decode to get JTI and expiration
        payload = decode_token(token)
        jti = payload["jti"]
        exp_timestamp = payload["exp"]
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        # Token should be valid before revocation
        verified = await verify_token_with_revocation(token, "access")
        assert verified is not None, "Token should be valid before revocation"
        
        # Revoke the token
        await revoke_token(jti, expires_at)
        
        # Token should be rejected after revocation
        verified = await verify_token_with_revocation(token, "access")
        assert verified is None, "Revoked token should be rejected"
    
    @pytest.mark.asyncio
    async def test_verify_token_with_revocation_accepts_non_revoked_token(self):
        """Test that verify_token_with_revocation accepts non-revoked tokens"""
        from app.utils.jwt import verify_token_with_revocation
        
        # Create a token
        data = {"sub": "test@example.com", "user_id": "123"}
        token = create_access_token(data)
        
        # Token should be valid (not revoked)
        verified = await verify_token_with_revocation(token, "access")
        assert verified is not None, "Non-revoked token should be accepted"
        assert verified["sub"] == data["sub"]
        assert verified["user_id"] == data["user_id"]
    
    @pytest.mark.asyncio
    async def test_verify_token_with_revocation_checks_token_type(self):
        """Test that verify_token_with_revocation still checks token type"""
        from app.utils.jwt import verify_token_with_revocation
        
        # Create an access token
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        # Try to verify as refresh token
        verified = await verify_token_with_revocation(token, "refresh")
        assert verified is None, "Token type mismatch should be rejected"
    
    @pytest.mark.asyncio
    async def test_multiple_tokens_can_be_revoked_independently(self):
        """Test that multiple tokens can be revoked independently"""
        from app.utils.jwt import revoke_token, is_token_revoked
        
        # Create multiple tokens
        data = {"sub": "test@example.com"}
        token1 = create_access_token(data)
        token2 = create_access_token(data)
        token3 = create_access_token(data)
        
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)
        payload3 = decode_token(token3)
        
        jti1 = payload1["jti"]
        jti2 = payload2["jti"]
        jti3 = payload3["jti"]
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Revoke only token1 and token3
        await revoke_token(jti1, expires_at)
        await revoke_token(jti3, expires_at)
        
        # Check revocation status
        assert await is_token_revoked(jti1) is True
        assert await is_token_revoked(jti2) is False
        assert await is_token_revoked(jti3) is True
    
    @pytest.mark.asyncio
    async def test_revoke_token_handles_redis_errors_gracefully(self):
        """Test that revoke_token handles Redis errors without raising"""
        from app.utils.jwt import revoke_token
        from unittest.mock import patch, AsyncMock
        
        jti = "test-error-handling"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Mock Redis to raise an error
        with patch('app.utils.jwt.get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            
            # Should not raise an exception
            try:
                await revoke_token(jti, expires_at)
            except Exception:
                pytest.fail("revoke_token should handle Redis errors gracefully")
    
    @pytest.mark.asyncio
    async def test_is_token_revoked_fails_closed_on_redis_error(self):
        """Test that is_token_revoked returns True (fail closed) on Redis errors"""
        from app.utils.jwt import is_token_revoked
        from unittest.mock import patch, AsyncMock
        
        jti = "test-fail-closed"
        
        # Mock Redis to raise an error
        with patch('app.utils.jwt.get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            
            # Should return True (fail closed for security)
            is_revoked = await is_token_revoked(jti)
            assert is_revoked is True, "Should fail closed on Redis errors"
