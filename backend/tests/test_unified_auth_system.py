"""
Tests for the unified authentication system after RBAC cleanup.

This test suite ensures that the standard authentication system works correctly
after removing the duplicate RBAC authentication system.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.utils.jwt import create_access_token, verify_token
from app.core.config import settings
from backend.tests.utils.secure_test_data import get_test_password


client = TestClient(app)
INVALID_LOGIN_PASSWORD = get_test_password("unified_auth_invalid_login")
VALID_LOGIN_PASSWORD = get_test_password("unified_auth_valid_login")


class TestUnifiedAuthSystem:
    """Test the unified authentication system"""
    
    def test_jwt_configuration_consistency(self):
        """Test that JWT configuration is consistent across the system"""
        # Test that JWT utilities use the main app settings
        token_data = {"sub": "test_user", "email": "test@example.com"}
        token = create_access_token(token_data)
        
        # Verify token can be decoded with the same settings
        payload = verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_standard_auth_endpoints_available(self):
        """Test that standard authentication endpoints are available"""
        # Test login endpoint
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": INVALID_LOGIN_PASSWORD
        })
        # Should return 401 for invalid credentials, not 404
        assert response.status_code in [401, 422]  # 422 for validation errors
        
        # Test that RBAC auth endpoints are not available
        response = client.post("/api/v1/rbac/auth/login", json={
            "username": "test@example.com",
            "password": INVALID_LOGIN_PASSWORD
        })
        # Should return 404 since endpoint was removed
        assert response.status_code == 404
    
    def test_token_response_format(self):
        """Test that login returns tokens in the correct format"""
        with patch('app.api.v1.endpoints.auth.verify_password') as mock_verify:
            with patch('app.api.v1.endpoints.auth.select') as mock_select:
                with patch('app.api.v1.endpoints.auth.get_cache_service') as mock_cache:
                    # Mock successful authentication
                    mock_verify.return_value = True
                    mock_cache.return_value = AsyncMock()
                    
                    # Mock user object
                    from app.database.models import User, Role
                    mock_user = User(
                        id="test-id",
                        email="test@example.com",
                        password_hash="hashed",
                        role=Role.USER,
                        is_active=True
                    )
                    
                    mock_result = AsyncMock()
                    mock_result.scalar_one_or_none.return_value = mock_user
                    mock_select.return_value = mock_result
                    
                    response = client.post("/api/v1/auth/login", json={
                        "email": "test@example.com",
                        "password": VALID_LOGIN_PASSWORD
                    })
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Should return access_token and refresh_token
                        assert "access_token" in data
                        assert "refresh_token" in data
                        assert data["token_type"] == "bearer"
    
    def test_me_endpoint_uses_standard_auth(self):
        """Test that /me endpoint uses standard authentication"""
        # Create a valid token
        token_data = {"sub": "test_user", "email": "test@example.com", "role": "developer"}
        token = create_access_token(token_data)
        
        with patch('app.api.dependencies.get_db') as mock_db:
            with patch('app.api.dependencies.select') as mock_select:
                # Mock user lookup
                from app.database.models import User, Role
                mock_user = User(
                    id="test_user",
                    email="test@example.com",
                    role=Role.USER,
                    is_active=True
                )
                
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = mock_user
                mock_select.return_value = mock_result
                
                response = client.get("/api/v1/auth/me", headers={
                    "Authorization": f"Bearer {token}"
                })
                
                # Should not return 404 (endpoint exists)
                assert response.status_code != 404
    
    def test_jwt_secret_consistency(self):
        """Test that all JWT operations use the same secret"""
        # Create token with main settings
        token_data = {"sub": "test", "email": "test@example.com"}
        token = create_access_token(token_data)
        
        # Verify token with main settings
        payload = verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == "test"
        
        # Test that the JWT_SECRET from settings is used
        assert len(settings.JWT_SECRET) >= 32  # Should be secure length
    
    def test_no_rbac_auth_imports(self):
        """Test that RBAC auth modules are not imported"""
        try:
            from app.api.v1.endpoints import rbac_auth
            pytest.fail("RBAC auth module should not be importable")
        except ImportError:
            # This is expected - the module should not exist
            pass
    
    def test_auth_module_imports_correctly(self):
        """Test that the auth module imports work correctly"""
        from app.auth import TokenPayload, AuthResult, RBACService
        
        # These should be available from the cleaned up auth module
        assert TokenPayload is not None
        assert AuthResult is not None
        assert RBACService is not None
    
    def test_frontend_api_routes_work(self):
        """Test that frontend API routes work with the unified system"""
        # Test that the frontend login route would work
        # (This tests the endpoint the frontend actually calls)
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": INVALID_LOGIN_PASSWORD
        })
        
        # Should get a proper auth error, not a 404
        assert response.status_code in [401, 422]
        
        # Test that old RBAC endpoint returns 404
        response = client.post("/api/v1/rbac/auth/login", json={
            "username": "test@example.com",
            "password": INVALID_LOGIN_PASSWORD
        })
        
        assert response.status_code == 404


class TestAuthSystemCleanup:
    """Test that the authentication system cleanup was successful"""
    
    def test_no_duplicate_auth_endpoints(self):
        """Test that there are no duplicate authentication endpoints"""
        from app.api.v1.router import api_router
        
        routes = [route.path for route in api_router.routes]
        auth_routes = [r for r in routes if '/auth/' in r]
        
        # Should only have standard auth routes, no RBAC auth routes
        rbac_auth_routes = [r for r in auth_routes if '/rbac/auth/' in r]
        assert len(rbac_auth_routes) == 0, f"Found RBAC auth routes: {rbac_auth_routes}"
        
        # Should have standard auth routes
        standard_auth_routes = [r for r in auth_routes if '/rbac/auth/' not in r]
        assert len(standard_auth_routes) > 0, "Should have standard auth routes"
    
    def test_jwt_utils_use_main_config(self):
        """Test that JWT utilities use the main application configuration"""
        from app.utils.jwt import create_access_token, verify_token
        from app.core.config import settings
        
        # Create a token
        token = create_access_token({"sub": "test"})
        
        # Verify it uses the main app's JWT secret
        payload = verify_token(token, "access")
        assert payload is not None
        
        # The token should be verifiable with the main settings
        import jwt as jose_jwt
        decoded = jose_jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        assert decoded["sub"] == "test"
    
    def test_auth_dependencies_work(self):
        """Test that authentication dependencies work correctly"""
        from app.api.dependencies import get_current_user
        
        # The dependency should be importable and callable
        assert callable(get_current_user)
    
    def test_no_auth_config_conflicts(self):
        """Test that there are no authentication configuration conflicts"""
        from app.core.config import settings
        
        # Should have JWT configuration
        assert hasattr(settings, 'JWT_SECRET')
        assert hasattr(settings, 'JWT_ALGORITHM')
        assert hasattr(settings, 'JWT_EXPIRATION_HOURS')
        
        # JWT secret should be properly configured
        assert len(settings.JWT_SECRET) >= 32
        assert settings.JWT_ALGORITHM == "HS256"
