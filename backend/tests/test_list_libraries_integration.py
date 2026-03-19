"""
Integration tests for List Installed Libraries endpoint

Tests the complete integration of the list installed libraries endpoint
with the LibraryManager service and database operations.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from datetime import datetime

from app.main import app
from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.schemas.library import InstalledLibrary
from app.models.library import RegistryType, ProjectContext


def setup_test_dependencies():
    """Helper function to set up test dependencies"""
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock user for authentication
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


class TestListLibrariesIntegration:
    """Integration test cases for the list installed libraries endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_libraries_full_integration(self):
        """Test complete integration flow for listing libraries"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Create realistic mock data
        mock_libraries = [
            InstalledLibrary(
                id=1,
                project_id="project-123",
                name="react",
                version="18.2.0",
                registry_type=RegistryType.NPM,
                project_context=ProjectContext.FRONTEND,
                description="A JavaScript library for building user interfaces",
                license="MIT",
                installed_at=datetime(2023, 6, 15, 10, 30, 0),
                installed_by="user-456",
                uri="npm:react@18.2.0",
                metadata={
                    "homepage": "https://reactjs.org",
                    "repository": "https://github.com/facebook/react",
                    "keywords": ["react", "ui", "javascript"]
                }
            ),
            InstalledLibrary(
                id=2,
                project_id="project-123",
                name="fastapi",
                version="0.104.1",
                registry_type=RegistryType.PYPI,
                project_context=ProjectContext.BACKEND,
                description="FastAPI framework, high performance, easy to learn",
                license="MIT",
                installed_at=datetime(2023, 6, 16, 14, 45, 0),
                installed_by="user-456",
                uri="pypi:fastapi==0.104.1",
                metadata={
                    "homepage": "https://fastapi.tiangolo.com",
                    "repository": "https://github.com/tiangolo/fastapi"
                }
            )
        ]
        
        # Mock the LibraryManager directly since it's created by dependency injection
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=project-123",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "libraries" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["libraries"]) == 2
        
        # Verify first library (React)
        react_lib = data["libraries"][0]
        assert react_lib["name"] == "react"
        assert react_lib["version"] == "18.2.0"
        assert react_lib["registry_type"] == "npm"
        assert react_lib["project_context"] == "frontend"
        assert react_lib["description"] == "A JavaScript library for building user interfaces"
        assert react_lib["license"] == "MIT"
        assert react_lib["installed_by"] == "user-456"
        assert react_lib["uri"] == "npm:react@18.2.0"
        assert react_lib["metadata"]["homepage"] == "https://reactjs.org"
        
        # Verify second library (FastAPI)
        fastapi_lib = data["libraries"][1]
        assert fastapi_lib["name"] == "fastapi"
        assert fastapi_lib["version"] == "0.104.1"
        assert fastapi_lib["registry_type"] == "pypi"
        assert fastapi_lib["project_context"] == "backend"
        assert fastapi_lib["description"] == "FastAPI framework, high performance, easy to learn"
        assert fastapi_lib["license"] == "MIT"
        assert fastapi_lib["installed_by"] == "user-456"
        assert fastapi_lib["uri"] == "pypi:fastapi==0.104.1"
        
        # Verify manager was called correctly
        mock_manager.get_installed_libraries.assert_called_once_with(
            project_id="project-123",
            context=None,
            user_id="test-user-id"
        )
    
    @pytest.mark.asyncio
    async def test_list_libraries_with_context_filter_integration(self):
        """Test integration with project context filtering"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock only backend libraries (filtered result)
        mock_libraries = [
            InstalledLibrary(
                id=2,
                project_id="project-123",
                name="fastapi",
                version="0.104.1",
                registry_type=RegistryType.PYPI,
                project_context=ProjectContext.BACKEND,
                description="FastAPI framework, high performance, easy to learn",
                license="MIT",
                installed_at=datetime(2023, 6, 16, 14, 45, 0),
                installed_by="user-456",
                uri="pypi:fastapi==0.104.1"
            ),
            InstalledLibrary(
                id=3,
                project_id="project-123",
                name="sqlalchemy",
                version="2.0.23",
                registry_type=RegistryType.PYPI,
                project_context=ProjectContext.BACKEND,
                description="Database Abstraction Library",
                license="MIT",
                installed_at=datetime(2023, 6, 17, 9, 15, 0),
                installed_by="user-456",
                uri="pypi:sqlalchemy==2.0.23"
            )
        ]
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=project-123&project_context=backend",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        
        # Verify all libraries are backend context
        for library in data["libraries"]:
            assert library["project_context"] == "backend"
            assert library["registry_type"] == "pypi"
        
        # Verify manager was called with context filter
        mock_manager.get_installed_libraries.assert_called_once_with(
            project_id="project-123",
            context=ProjectContext.BACKEND,
            user_id="test-user-id"
        )
    
    @pytest.mark.asyncio
    async def test_list_libraries_empty_project_integration(self):
        """Test integration with empty project (no libraries installed)"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = []
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=empty-project",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["libraries"] == []
        
        # Verify manager was called
        mock_manager.get_installed_libraries.assert_called_once_with(
            project_id="empty-project",
            context=None,
            user_id="test-user-id"
        )
    
    @pytest.mark.asyncio
    async def test_list_libraries_database_error_integration(self):
        """Test integration with database errors"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.side_effect = Exception("Database connection timeout")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=project-123",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert data["libraries"] == []
        assert data["total"] == 0
        assert "Internal server error" in data["error"]
    
    @pytest.mark.asyncio
    async def test_list_libraries_authentication_integration(self):
        """Test integration with authentication system"""
        # Don't set up authentication - test unauthenticated request
        mock_db = AsyncMock()
        
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/libraries/?project_id=project-123")
        
        cleanup_test_dependencies()
        
        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_list_libraries_parameter_validation_integration(self):
        """Test integration with request parameter validation"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test missing required project_id parameter
            response = await client.get(
                "/api/v1/libraries/",
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
            
            # Test invalid project_context parameter
            response = await client.get(
                "/api/v1/libraries/?project_id=test&project_context=invalid",
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
        
        cleanup_test_dependencies()
    
    @pytest.mark.asyncio
    async def test_list_libraries_large_dataset_integration(self):
        """Test integration with large number of libraries"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Create 100 mock libraries
        mock_libraries = []
        for i in range(100):
            mock_libraries.append(
                InstalledLibrary(
                    id=i + 1,
                    project_id="large-project",
                    name=f"library-{i:03d}",
                    version="1.0.0",
                    registry_type=RegistryType.NPM if i % 2 == 0 else RegistryType.PYPI,
                    project_context=ProjectContext.FRONTEND if i % 2 == 0 else ProjectContext.BACKEND,
                    description=f"Test library number {i}",
                    license="MIT",
                    installed_at=datetime(2023, 6, 15, 10, 30, i % 60),
                    installed_by="user-456",
                    uri=f"npm:library-{i:03d}@1.0.0" if i % 2 == 0 else f"pypi:library-{i:03d}==1.0.0"
                )
            )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=large-project",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        # Verify response handles large dataset
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100
        assert len(data["libraries"]) == 100
        
        # Verify first and last libraries
        assert data["libraries"][0]["name"] == "library-000"
        assert data["libraries"][99]["name"] == "library-099"
        
        # Verify mixed registry types and contexts
        npm_count = sum(1 for lib in data["libraries"] if lib["registry_type"] == "npm")
        pypi_count = sum(1 for lib in data["libraries"] if lib["registry_type"] == "pypi")
        assert npm_count == 50
        assert pypi_count == 50
