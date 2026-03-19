"""
Integration tests for the search libraries endpoint

Tests the complete flow from API endpoint to SearchService
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.main import app
from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.schemas.library import LibrarySearchResult
from app.models.library import RegistryType


def setup_test_dependencies(mock_user=None):
    """Helper function to set up test dependencies"""
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock user for authentication if provided
    if mock_user is None:
        from app.models import User, UserRole
        mock_user = User(
            id="test-user-id",
            email="test@example.com",
            role=UserRole.USER,
            is_active=True
        )
    
    # Override dependencies
    async def override_get_db():
        yield mock_db
    
    def override_get_current_user():
        return mock_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    return mock_db, mock_user


def cleanup_test_dependencies():
    """Helper function to clean up test dependencies"""
    app.dependency_overrides.clear()


class TestSearchIntegration:
    """Integration tests for search libraries endpoint"""
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration_success(self):
        """Test complete search flow with mocked SearchService"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock search results
        mock_search_results = [
            LibrarySearchResult(
                name="react",
                description="A JavaScript library for building user interfaces",
                version="18.0.0",
                downloads=1000000,
                uri="npm:react@18.0.0",
                registry_type=RegistryType.NPM
            ),
            LibrarySearchResult(
                name="react-dom",
                description="React package for working with the DOM",
                version="18.0.0",
                downloads=900000,
                uri="npm:react-dom@18.0.0",
                registry_type=RegistryType.NPM
            )
        ]
        
        # Mock the SearchService at the module level
        with patch('app.services.library_management.library_manager.SearchService') as mock_search_service_class:
            mock_search_service = AsyncMock()
            mock_search_service.search.return_value = mock_search_results
            mock_search_service.close.return_value = None
            mock_search_service_class.return_value = mock_search_service
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/search?q=react",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["name"] == "react"
        assert data["results"][0]["registry_type"] == "npm"
        assert data["results"][1]["name"] == "react-dom"
        
        # Verify SearchService was called correctly
        mock_search_service.search.assert_called_once_with(
            query="react",
            registry_type=None,
            limit=20
        )
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration_with_registry_filter(self):
        """Test search with registry filter"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock PyPI search results
        mock_search_results = [
            LibrarySearchResult(
                name="django",
                description="A high-level Python Web framework",
                version="4.2.0",
                downloads=500000,
                uri="pypi:django==4.2.0",
                registry_type=RegistryType.PYPI
            )
        ]
        
        with patch('app.services.library_management.library_manager.SearchService') as mock_search_service_class:
            mock_search_service = AsyncMock()
            mock_search_service.search.return_value = mock_search_results
            mock_search_service.close.return_value = None
            mock_search_service_class.return_value = mock_search_service
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/search?q=django&registry=pypi",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["name"] == "django"
        assert data["results"][0]["registry_type"] == "pypi"
        
        # Verify SearchService was called with registry filter
        mock_search_service.search.assert_called_once_with(
            query="django",
            registry_type=RegistryType.PYPI,
            limit=20
        )
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration_empty_results(self):
        """Test search with no results"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.services.library_management.library_manager.SearchService') as mock_search_service_class:
            mock_search_service = AsyncMock()
            mock_search_service.search.return_value = []
            mock_search_service.close.return_value = None
            mock_search_service_class.return_value = mock_search_service
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/search?q=nonexistentpackage",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration_service_error(self):
        """Test search with SearchService error"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.services.library_management.library_manager.SearchService') as mock_search_service_class:
            mock_search_service = AsyncMock()
            mock_search_service.search.side_effect = Exception("Service error")
            mock_search_service.close.return_value = None
            mock_search_service_class.return_value = mock_search_service
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/search?q=react",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 500
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0
        assert "Internal server error" in data["error"]
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration_limit_enforcement(self):
        """Test that search results are limited to 20 items"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Create 25 mock results to test limit enforcement
        mock_search_results = [
            LibrarySearchResult(
                name=f"package-{i}",
                description=f"Test package {i}",
                version="1.0.0",
                downloads=1000,
                uri=f"npm:package-{i}@1.0.0",
                registry_type=RegistryType.NPM
            )
            for i in range(20)  # SearchService should limit to 20
        ]
        
        with patch('app.services.library_management.library_manager.SearchService') as mock_search_service_class:
            mock_search_service = AsyncMock()
            mock_search_service.search.return_value = mock_search_results
            mock_search_service.close.return_value = None
            mock_search_service_class.return_value = mock_search_service
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/search?q=package",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 20  # Should be limited to 20
        assert len(data["results"]) == 20
        
        # Verify SearchService was called with limit=20
        mock_search_service.search.assert_called_once_with(
            query="package",
            registry_type=None,
            limit=20
        )
    
    @pytest.mark.asyncio
    async def test_search_endpoint_integration_all_registry_types(self):
        """Test search with all supported registry types"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Test each registry type
        registry_tests = [
            ("npm", RegistryType.NPM, "react"),
            ("pypi", RegistryType.PYPI, "django"),
            ("maven", RegistryType.MAVEN, "junit")
        ]
        
        for registry_param, expected_enum, package_name in registry_tests:
            mock_search_results = [
                LibrarySearchResult(
                    name=package_name,
                    description=f"Test {registry_param} package",
                    version="1.0.0",
                    downloads=1000,
                    uri=f"{registry_param}:{package_name}@1.0.0",
                    registry_type=expected_enum
                )
            ]
            
            with patch('app.services.library_management.library_manager.SearchService') as mock_search_service_class:
                mock_search_service = AsyncMock()
                mock_search_service.search.return_value = mock_search_results
                mock_search_service.close.return_value = None
                mock_search_service_class.return_value = mock_search_service
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get(
                        f"/api/v1/libraries/search?q={package_name}&registry={registry_param}",
                        headers={"Authorization": "Bearer fake-token"}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 1
                assert data["results"][0]["registry_type"] == registry_param
                assert data["results"][0]["name"] == package_name
                
                # Verify SearchService was called with correct registry type
                mock_search_service.search.assert_called_once_with(
                    query=package_name,
                    registry_type=expected_enum,
                    limit=20
                )
        
        cleanup_test_dependencies()
