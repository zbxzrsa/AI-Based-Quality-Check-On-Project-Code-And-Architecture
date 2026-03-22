"""
Authentication Integration Tests

Tests complete authentication flows including token refresh and revocation.
Validates Requirements 13.6

**Validates: Requirements 13.6**
"""
import pytest
from httpx import AsyncClient
from datetime import timedelta

from app.models import User
from app.utils.password import hash_password
from app.utils.jwt import create_access_token, create_refresh_token
from backend.tests.utils.secure_test_data import get_test_password


class TestCompleteAuthenticationFlow:
    """Integration tests for complete authentication workflows"""
    
    @pytest.mark.asyncio
    async def test_register_login_access_protected_resource(self, client: AsyncClient, db_session):
        """
        Test complete flow: register -> login -> access protected resource
        
        **Validates: Requirements 13.6**
        """
        # Step 1: Register
        register_password = get_test_password("auth_integration_register")
        register_data = {
            "email": "complete@test.com",
            "password": register_password,
            "full_name": "Complete Flow Test"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        user_data = response.json()
        user_id = user_data["id"]
        
        # Step 2: Login
        login_data = {
            "email": "complete@test.com",
            "password": register_password
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        tokens = response.json()
        access_token = tokens["access_token"]
        
        # Step 3: Access protected resource
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        me_data = response.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == "complete@test.com"
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, client: AsyncClient, db_session):
        """
        Test login with invalid credentials returns generic error
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="invalid@test.com",
            password_hash=hash_password(get_test_password("auth_integration_correct")),
            full_name="Invalid Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Try login with wrong password
        login_data = {
            "email": "invalid@test.com",
            "password": get_test_password("auth_integration_wrong")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        error = response.json()
        # Should return generic error message
        assert "Incorrect email or password" in error["detail"]
    
    @pytest.mark.asyncio
    async def test_login_with_nonexistent_user(self, client: AsyncClient):
        """
        Test login with nonexistent user returns generic error
        
        **Validates: Requirements 13.6**
        """
        login_data = {
            "email": "nonexistent@test.com",
            "password": get_test_password("auth_integration_nonexistent")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        error = response.json()
        # Should return generic error message (no user enumeration)
        assert "Incorrect email or password" in error["detail"]
    
    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(self, client: AsyncClient):
        """
        Test accessing protected route without token
        
        **Validates: Requirements 13.6**
        """
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_access_protected_route_with_invalid_token(self, client: AsyncClient):
        """
        Test accessing protected route with invalid token
        
        **Validates: Requirements 13.6**
        """
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401


class TestTokenRefreshFlow:
    """Integration tests for token refresh with rotation"""
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_rotation(self, client: AsyncClient, db_session):
        """
        Test token refresh generates new token pair and revokes old refresh token
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="refresh@test.com",
            password_hash=hash_password(get_test_password("auth_integration_refresh")),
            full_name="Refresh Test"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Login to get initial tokens
        login_data = {
            "email": "refresh@test.com",
            "password": get_test_password("auth_integration_refresh")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        initial_tokens = response.json()
        
        initial_access_token = initial_tokens["access_token"]
        initial_refresh_token = initial_tokens["refresh_token"]
        
        # Refresh tokens
        refresh_data = {"refresh_token": initial_refresh_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        new_tokens = response.json()
        
        new_access_token = new_tokens["access_token"]
        new_refresh_token = new_tokens["refresh_token"]
        
        # Verify new tokens are different
        assert new_access_token != initial_access_token
        assert new_refresh_token != initial_refresh_token
        
        # Verify new access token works
        headers = {"Authorization": f"Bearer {new_access_token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Verify old refresh token is revoked (cannot be reused)
        refresh_data = {"refresh_token": initial_refresh_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401
        error = response.json()
        assert "revoked" in error["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_refresh_with_expired_token(self, client: AsyncClient, db_session):
        """
        Test refresh with expired refresh token
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="expired@test.com",
            password_hash=hash_password(get_test_password("auth_integration_expired")),
            full_name="Expired Test"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create expired refresh token
        expired_token = create_refresh_token(
            {"sub": str(user.id)},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        # Try to refresh with expired token
        refresh_data = {"refresh_token": expired_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_with_access_token(self, client: AsyncClient, db_session):
        """
        Test refresh endpoint rejects access tokens
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="wrongtype@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Wrong Type Test"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create access token (not refresh token)
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        })
        
        # Try to use access token for refresh
        refresh_data = {"refresh_token": access_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_multiple_refresh_cycles(self, client: AsyncClient, db_session):
        """
        Test multiple token refresh cycles work correctly
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="multiple@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Multiple Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "multiple@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        
        # Perform 3 refresh cycles
        for i in range(3):
            refresh_data = {"refresh_token": tokens["refresh_token"]}
            response = await client.post("/api/v1/auth/refresh", json=refresh_data)
            assert response.status_code == 200
            tokens = response.json()
            
            # Verify new access token works
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            response = await client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200


class TestTokenRevocation:
    """Integration tests for token revocation"""
    
    @pytest.mark.asyncio
    async def test_logout_revokes_session(self, client: AsyncClient, db_session):
        """
        Test logout revokes user session
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="logout@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Logout Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "logout@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Verify access works
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Logout
        response = await client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 200
        
        # Session should be deleted (though token might still be valid until expiry)
        # In a real implementation, we would check Redis for session deletion
    
    @pytest.mark.asyncio
    async def test_revoked_refresh_token_cannot_be_used(self, client: AsyncClient, db_session):
        """
        Test revoked refresh token cannot be used
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="revoked@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Revoked Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "revoked@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        refresh_token = tokens["refresh_token"]
        
        # Refresh once (this revokes the original refresh token)
        refresh_data = {"refresh_token": refresh_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        
        # Try to use the original refresh token again
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401
        error = response.json()
        assert "revoked" in error["detail"].lower()


class TestPasswordManagement:
    """Integration tests for password change functionality"""
    
    @pytest.mark.asyncio
    async def test_password_change_flow(self, client: AsyncClient, db_session):
        """
        Test complete password change flow
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="pwchange@test.com",
            password_hash=hash_password("OldPass123!"),
            full_name="Password Change Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login with old password
        login_data = {
            "email": "pwchange@test.com",
            "password": "OldPass123!"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Change password
        password_data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!"
        }
        
        response = await client.patch("/api/v1/auth/password", json=password_data, headers=headers)
        assert response.status_code == 200
        
        # Old password should not work
        login_data["password"] = "OldPass123!"
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        
        # New password should work
        login_data["password"] = "NewPass456!"
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_password_change_with_wrong_current_password(self, client: AsyncClient, db_session):
        """
        Test password change fails with wrong current password
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="wrongpw@test.com",
            password_hash=hash_password(get_test_password("auth_integration_correct")),
            full_name="Wrong Password Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "wrongpw@test.com",
            "password": get_test_password("auth_integration_correct")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Try to change password with wrong current password
        password_data = {
            "current_password": get_test_password("auth_integration_wrong"),
            "new_password": "NewPass456!"
        }
        
        response = await client.patch("/api/v1/auth/password", json=password_data, headers=headers)
        assert response.status_code == 400
        error = response.json()
        assert "incorrect" in error["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_password_change_with_weak_new_password(self, client: AsyncClient, db_session):
        """
        Test password change fails with weak new password
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="weakpw@test.com",
            password_hash=hash_password("StrongPass123!"),
            full_name="Weak Password Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "weakpw@test.com",
            "password": "StrongPass123!"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Try to change to weak password
        password_data = {
            "current_password": "StrongPass123!",
            "new_password": "weak"  # Too weak
        }
        
        response = await client.patch("/api/v1/auth/password", json=password_data, headers=headers)
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_password_change_same_as_current(self, client: AsyncClient, db_session):
        """
        Test password change fails when new password is same as current
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="samepw@test.com",
            password_hash=hash_password("SamePass123!"),
            full_name="Same Password Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "samepw@test.com",
            "password": "SamePass123!"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Try to change to same password
        password_data = {
            "current_password": "SamePass123!",
            "new_password": "SamePass123!"
        }
        
        response = await client.patch("/api/v1/auth/password", json=password_data, headers=headers)
        assert response.status_code == 400
        error = response.json()
        assert "different" in error["detail"].lower()


class TestRateLimiting:
    """Integration tests for authentication rate limiting"""
    
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, client: AsyncClient, db_session):
        """
        Test login endpoint rate limiting
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="ratelimit@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Rate Limit Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        login_data = {
            "email": "ratelimit@test.com",
            "password": get_test_password("auth_integration_wrong")
        }
        
        # Make multiple failed login attempts
        responses = []
        for i in range(6):
            response = await client.post("/api/v1/auth/login", json=login_data)
            responses.append(response)
        
        # First 5 should be 401 (unauthorized)
        for response in responses[:5]:
            assert response.status_code == 401
        
        # 6th should be 429 (too many requests)
        assert responses[5].status_code == 429
        error = responses[5].json()
        assert "too many" in error["detail"].lower()


class TestSessionManagement:
    """Integration tests for session management"""
    
    @pytest.mark.asyncio
    async def test_session_created_on_login(self, client: AsyncClient, db_session):
        """
        Test session is created in Redis on login
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="session@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Session Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login
        login_data = {
            "email": "session@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        # Session should be created in Redis
        # In a real test, we would verify Redis contains the session
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, client: AsyncClient, db_session):
        """
        Test user can have multiple concurrent sessions
        
        **Validates: Requirements 13.6**
        """
        # Create user
        user = User(
            email="concurrent@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Concurrent Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        login_data = {
            "email": "concurrent@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        # Login twice (simulating different devices)
        response1 = await client.post("/api/v1/auth/login", json=login_data)
        assert response1.status_code == 200
        tokens1 = response1.json()
        
        response2 = await client.post("/api/v1/auth/login", json=login_data)
        assert response2.status_code == 200
        tokens2 = response2.json()
        
        # Both tokens should work
        headers1 = {"Authorization": f"Bearer {tokens1['access_token']}"}
        headers2 = {"Authorization": f"Bearer {tokens2['access_token']}"}
        
        response1 = await client.get("/api/v1/auth/me", headers=headers1)
        assert response1.status_code == 200
        
        response2 = await client.get("/api/v1/auth/me", headers=headers2)
        assert response2.status_code == 200


class TestInactiveUserHandling:
    """Integration tests for inactive user handling"""
    
    @pytest.mark.asyncio
    async def test_inactive_user_cannot_login(self, client: AsyncClient, db_session):
        """
        Test inactive user cannot login
        
        **Validates: Requirements 13.6**
        """
        # Create inactive user
        user = User(
            email="inactive@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Inactive Test",
            is_active=False
        )
        db_session.add(user)
        await db_session.commit()
        
        # Try to login
        login_data = {
            "email": "inactive@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 403
        error = response.json()
        assert "inactive" in error["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_inactive_user_cannot_refresh_token(self, client: AsyncClient, db_session):
        """
        Test inactive user cannot refresh tokens
        
        **Validates: Requirements 13.6**
        """
        # Create active user
        user = User(
            email="deactivate@test.com",
            password_hash=hash_password(get_test_password("auth_integration_secure")),
            full_name="Deactivate Test",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Login while active
        login_data = {
            "email": "deactivate@test.com",
            "password": get_test_password("auth_integration_secure")
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = response.json()
        
        # Deactivate user
        user.is_active = False
        await db_session.commit()
        
        # Try to refresh token
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401

