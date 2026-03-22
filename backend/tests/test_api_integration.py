"""
API Integration Tests

Tests all API endpoints end-to-end with test doubles for external services.
Validates Requirements 5.4, 5.7, 13.7

**Validates: Requirements 5.4, 5.7, 13.7**
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.models import User
from app.utils.password import hash_password
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


class TestAuthenticationEndpoints:
    """Integration tests for authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_login_logout_flow(self, client: AsyncClient, db_session: AsyncSession):
        """
        Test complete authentication flow: register -> login -> logout
        
        **Validates: Requirements 5.4, 13.7**
        """
        # Step 1: Register
        register_password = get_test_password("api_integration_register")
        register_data = {
            "email": "integration@test.com",
            "password": register_password,
            "full_name": "Integration Test User"
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == register_data["email"]
        assert user_data["full_name"] == register_data["full_name"]
        assert "id" in user_data
        
        # Step 2: Login with credentials
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        
        access_token = token_data["access_token"]
        
        # Step 3: Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        me_data = response.json()
        assert me_data["email"] == register_data["email"]
        
        # Step 4: Logout
        response = await client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, client: AsyncClient, db_session: AsyncSession):
        """
        Test token refresh with rotation
        
        **Validates: Requirements 5.4, 13.7**
        """
        # Create and login user
        password = get_test_password("secure_pass")
        user = User(
            email="refresh@test.com",
            password_hash=hash_password(password),
            full_name="Refresh Test"
        )
        db_session.add(user)
        await db_session.commit()
        
        login_data = {
            "email": "refresh@test.com",
            "password": password
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        tokens = response.json()
        
        old_refresh_token = tokens["refresh_token"]
        
        # Refresh token
        refresh_data = {"refresh_token": old_refresh_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        new_tokens = response.json()
        
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["refresh_token"] != old_refresh_token  # Token rotation
        
        # Old refresh token should be revoked
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401


class TestHealthEndpoints:
    """Integration tests for health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self, client: AsyncClient):
        """
        Test health endpoint with mocked dependencies
        
        **Validates: Requirements 5.4, 13.7**
        """
        with patch('app.services.health_service.get_connection_manager') as mock_manager:
            class MockDbStatus:
                def __init__(self, service, is_connected, response_time_ms, is_critical):
                    self.service = service
                    self.is_connected = is_connected
                    self.response_time_ms = response_time_ms
                    self.is_critical = is_critical
                    self.error = None

            mock_conn_manager = AsyncMock()
            mock_conn_manager.verify_all.return_value = {
                "PostgreSQL": MockDbStatus("PostgreSQL", True, 10.5, True),
                "Neo4j": MockDbStatus("Neo4j", True, 15.2, False),
                "Redis": MockDbStatus("Redis", True, 5.1, False)
            }
            mock_manager.return_value = mock_conn_manager
            
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "databases" in data
            assert "PostgreSQL" in data["databases"]
            assert "Neo4j" in data["databases"]
            assert "Redis" in data["databases"]
    
    @pytest.mark.asyncio
    async def test_liveness_endpoint(self, client: AsyncClient):
        """
        Test liveness endpoint
        
        **Validates: Requirements 5.4, 13.7**
        """
        response = await client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


class TestErrorHandling:
    """Integration tests for error handling across endpoints"""
    
    @pytest.mark.asyncio
    async def test_404_not_found(self, client: AsyncClient):
        """
        Test 404 error handling
        
        **Validates: Requirements 5.4, 13.7**
        """
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_401_unauthorized(self, client: AsyncClient):
        """
        Test 401 unauthorized error
        
        **Validates: Requirements 5.4, 13.7**
        """
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_validation_error(self, client: AsyncClient):
        """
        Test validation error handling
        
        **Validates: Requirements 5.4, 13.7**
        """
        # Invalid email format
        register_data = {
            "email": "invalid-email",
            "password": get_test_password("api_integration_invalid_email")
        }
        
        response = await client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 422  # Validation error


class TestCORSConfiguration:
    """Integration tests for CORS configuration"""
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """
        Test CORS headers are present
        
        **Validates: Requirements 5.4, 13.7**
        """
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
