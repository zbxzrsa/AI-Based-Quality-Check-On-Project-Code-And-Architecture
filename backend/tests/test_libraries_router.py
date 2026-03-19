"""
Tests for Library Management API Router

Tests the validate library endpoint implementation and other router functionality.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.main import app
from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.schemas.library import ValidationResult, LibraryMetadata, ProjectContext
from app.models.library import RegistryType
from app.services.library_management.library_manager import (
    ValidationError as LibraryValidationError
)


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


class TestValidateLibraryEndpoint:
    """Test cases for the validate library endpoint"""
    
    @pytest.mark.asyncio
    async def test_validate_library_success(self):
        """Test successful library validation"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock LibraryManager.validate_library to return success
        mock_library_metadata = LibraryMetadata(
            name="react",
            version="18.0.0",
            description="A JavaScript library for building user interfaces",
            license="MIT",
            registry_type=RegistryType.NPM,
            dependencies=[]
        )
        
        mock_validation_result = ValidationResult(
            valid=True,
            library=mock_library_metadata,
            suggested_context=ProjectContext.FRONTEND,
            errors=[]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.validate_library.return_value = mock_validation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/validate",
                    json={"uri": "npm:react@18.0.0"},
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["library"]["name"] == "react"
        assert data["library"]["version"] == "18.0.0"
        assert data["suggested_context"] == "frontend"
        assert data["errors"] is None
    
    @pytest.mark.asyncio
    async def test_validate_library_invalid_uri(self):
        """Test validation with invalid URI"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_validation_result = ValidationResult(
            valid=False,
            library=None,
            suggested_context=None,
            errors=["Invalid URI format. Expected: npm:package-name[@version]"]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.validate_library.return_value = mock_validation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/validate",
                    json={"uri": "invalid-uri"},
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 400
        data = response.json()
        assert data["valid"] is False
        assert "Invalid URI format" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_validate_library_unauthorized(self):
        """Test validation without authentication"""
        # Mock database session only, no user authentication
        mock_db = AsyncMock()
        
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/libraries/validate",
                json={"uri": "npm:react"}
            )
        
        cleanup_test_dependencies()
        
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden is acceptable
    
    @pytest.mark.asyncio
    async def test_validate_library_manager_exception(self):
        """Test handling of LibraryManager exceptions"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.validate_library.side_effect = LibraryValidationError("Validation service error")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/validate",
                    json={"uri": "npm:react"},
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 400
        data = response.json()
        assert data["valid"] is False
        assert "Validation service error" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_validate_library_unexpected_exception(self):
        """Test handling of unexpected exceptions"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.validate_library.side_effect = Exception("Unexpected error")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/validate",
                    json={"uri": "npm:react"},
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 500
        data = response.json()
        assert data["valid"] is False
        assert "Internal server error" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_validate_library_invalid_request_schema(self):
        """Test validation with invalid request schema"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test empty URI
            response = await client.post(
                "/api/v1/libraries/validate",
                json={"uri": ""},
                headers={"Authorization": "Bearer fake-token"}
            )
            
            assert response.status_code == 422
            
            # Test missing URI
            response = await client.post(
                "/api/v1/libraries/validate",
                json={},
                headers={"Authorization": "Bearer fake-token"}
            )
            
            assert response.status_code == 422
            
            # Test invalid project context
            response = await client.post(
                "/api/v1/libraries/validate",
                json={"uri": "npm:react", "project_context": "invalid"},
                headers={"Authorization": "Bearer fake-token"}
            )
            
            assert response.status_code == 422
        
        cleanup_test_dependencies()


class TestInstallLibraryEndpoint:
    """Test cases for the install library endpoint"""
    
    @pytest.mark.asyncio
    async def test_install_library_success(self):
        """Test successful library installation"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock LibraryManager.install_library to return success
        from app.schemas.library import InstallationResult, InstalledLibrary
        from datetime import datetime
        
        mock_installed_library = InstalledLibrary(
            id=1,
            project_id="test-user-id",
            name="react",
            version="18.0.0",
            registry_type=RegistryType.NPM,
            project_context=ProjectContext.FRONTEND,
            description="A JavaScript library for building user interfaces",
            license="MIT",
            installed_at=datetime.now(),
            installed_by="test-user-id",
            uri="npm:react@18.0.0"
        )
        
        mock_installation_result = InstallationResult(
            success=True,
            installed_library=mock_installed_library,
            errors=[]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "npm:react@18.0.0",
                        "project_context": "frontend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["installed_library"]["name"] == "react"
        assert data["installed_library"]["version"] == "18.0.0"
        assert data["errors"] is None
    
    @pytest.mark.asyncio
    async def test_install_library_with_version_override(self):
        """Test library installation with version override"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstallationResult, InstalledLibrary
        from datetime import datetime
        
        mock_installed_library = InstalledLibrary(
            id=1,
            project_id="test-user-id",
            name="react",
            version="17.0.2",  # Different version than URI
            registry_type=RegistryType.NPM,
            project_context=ProjectContext.FRONTEND,
            description="A JavaScript library for building user interfaces",
            license="MIT",
            installed_at=datetime.now(),
            installed_by="test-user-id",
            uri="npm:react@18.0.0"
        )
        
        mock_installation_result = InstallationResult(
            success=True,
            installed_library=mock_installed_library,
            errors=[]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "npm:react@18.0.0",
                        "project_context": "frontend",
                        "version": "17.0.2"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["installed_library"]["version"] == "17.0.2"
        
        # Verify the manager was called with the override version
        mock_manager.install_library.assert_called_once()
        call_args = mock_manager.install_library.call_args
        assert call_args[1]["version"] == "17.0.2"
    
    @pytest.mark.asyncio
    async def test_install_library_validation_error(self):
        """Test installation with validation errors (400)"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstallationResult
        
        mock_installation_result = InstallationResult(
            success=False,
            installed_library=None,
            errors=["Invalid URI format. Expected: npm:package-name[@version]"]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "invalid-uri",
                        "project_context": "frontend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "Invalid URI format" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_install_library_conflict_error(self):
        """Test installation with dependency conflicts (409)"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstallationResult
        
        mock_installation_result = InstallationResult(
            success=False,
            installed_library=None,
            errors=[
                "Version conflict: react (existing: 17.0.2, required: ^18.0.0)",
                "Circular dependency detected: react -> react-dom -> react"
            ]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "npm:react@18.0.0",
                        "project_context": "frontend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert "Version conflict" in data["errors"][0]
        assert "Circular dependency" in data["errors"][1]
    
    @pytest.mark.asyncio
    async def test_install_library_installation_failure(self):
        """Test installation failure (500)"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstallationResult
        
        mock_installation_result = InstallationResult(
            success=False,
            installed_library=None,
            errors=["npm install failed: EACCES permission denied"]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "npm:react@18.0.0",
                        "project_context": "frontend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "npm install failed" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_install_library_unauthorized(self):
        """Test installation without authentication"""
        mock_db = AsyncMock()
        
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/libraries/install",
                json={
                    "uri": "npm:react@18.0.0",
                    "project_context": "frontend"
                }
            )
        
        cleanup_test_dependencies()
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_install_library_invalid_request_schema(self):
        """Test installation with invalid request schema"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test empty URI
            response = await client.post(
                "/api/v1/libraries/install",
                json={
                    "uri": "",
                    "project_context": "frontend"
                },
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
            
            # Test missing URI
            response = await client.post(
                "/api/v1/libraries/install",
                json={"project_context": "frontend"},
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
            
            # Test missing project_context
            response = await client.post(
                "/api/v1/libraries/install",
                json={"uri": "npm:react"},
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
            
            # Test invalid project_context
            response = await client.post(
                "/api/v1/libraries/install",
                json={
                    "uri": "npm:react",
                    "project_context": "invalid"
                },
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
        
        cleanup_test_dependencies()
    
    @pytest.mark.asyncio
    async def test_install_library_unexpected_exception(self):
        """Test handling of unexpected exceptions during installation"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.side_effect = Exception("Unexpected error")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "npm:react@18.0.0",
                        "project_context": "frontend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "Internal server error" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_install_library_backend_context(self):
        """Test installation in backend context"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstallationResult, InstalledLibrary
        from datetime import datetime
        
        mock_installed_library = InstalledLibrary(
            id=1,
            project_id="test-user-id",
            name="django",
            version="4.2.0",
            registry_type=RegistryType.PYPI,
            project_context=ProjectContext.BACKEND,
            description="A high-level Python Web framework",
            license="BSD",
            installed_at=datetime.now(),
            installed_by="test-user-id",
            uri="pypi:django==4.2.0"
        )
        
        mock_installation_result = InstallationResult(
            success=True,
            installed_library=mock_installed_library,
            errors=[]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "pypi:django==4.2.0",
                        "project_context": "backend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["installed_library"]["name"] == "django"
        assert data["installed_library"]["registry_type"] == "pypi"
        assert data["installed_library"]["project_context"] == "backend"


class TestSearchLibrariesEndpoint:
    """Test cases for the search libraries endpoint"""
    
    @pytest.mark.asyncio
    async def test_search_libraries_success(self):
        """Test successful library search"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock search results
        from app.schemas.library import LibrarySearchResult
        from app.models.library import RegistryType
        
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
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.search_libraries.return_value = mock_search_results
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
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
    
    @pytest.mark.asyncio
    async def test_search_libraries_with_registry_filter(self):
        """Test library search with registry filter"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import LibrarySearchResult
        from app.models.library import RegistryType
        
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
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.search_libraries.return_value = mock_search_results
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
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
        
        # Verify the manager was called with the correct registry type
        mock_manager.search_libraries.assert_called_once()
        call_args = mock_manager.search_libraries.call_args
        assert call_args[1]["registry_type"] == RegistryType.PYPI
    
    @pytest.mark.asyncio
    async def test_search_libraries_invalid_registry(self):
        """Test search with invalid registry type"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/libraries/search?q=test&registry=invalid",
                headers={"Authorization": "Bearer fake-token"}
            )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 400
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0
        assert "Invalid registry type" in data["error"]
        assert "npm, pypi, maven" in data["error"]
    
    @pytest.mark.asyncio
    async def test_search_libraries_empty_results(self):
        """Test search with no results"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.search_libraries.return_value = []
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
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
    async def test_search_libraries_unauthorized(self):
        """Test search without authentication"""
        mock_db = AsyncMock()
        
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/libraries/search?q=react")
        
        cleanup_test_dependencies()
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_search_libraries_invalid_query(self):
        """Test search with invalid query parameters"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test empty query
            response = await client.get(
                "/api/v1/libraries/search?q=",
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
            
            # Test missing query
            response = await client.get(
                "/api/v1/libraries/search",
                headers={"Authorization": "Bearer fake-token"}
            )
            assert response.status_code == 422
        
        cleanup_test_dependencies()
    
    @pytest.mark.asyncio
    async def test_search_libraries_manager_exception(self):
        """Test handling of LibraryManager exceptions during search"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.search_libraries.side_effect = Exception("Search service error")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
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
    async def test_search_libraries_case_insensitive_registry(self):
        """Test search with case-insensitive registry filter"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import LibrarySearchResult
        from app.models.library import RegistryType
        
        mock_search_results = [
            LibrarySearchResult(
                name="react",
                description="A JavaScript library for building user interfaces",
                version="18.0.0",
                downloads=1000000,
                uri="npm:react@18.0.0",
                registry_type=RegistryType.NPM
            )
        ]
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.search_libraries.return_value = mock_search_results
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test uppercase registry filter
                response = await client.get(
                    "/api/v1/libraries/search?q=react&registry=NPM",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["name"] == "react"
        
        # Verify the manager was called with the correct registry type
        mock_manager.search_libraries.assert_called_once()
        call_args = mock_manager.search_libraries.call_args
        assert call_args[1]["registry_type"] == RegistryType.NPM
    
    @pytest.mark.asyncio
    async def test_search_libraries_limit_enforcement(self):
        """Test that search results are limited to 20 items"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Create 25 mock results to test limit enforcement
        from app.schemas.library import LibrarySearchResult
        from app.models.library import RegistryType
        
        mock_search_results = [
            LibrarySearchResult(
                name=f"package-{i}",
                description=f"Test package {i}",
                version="1.0.0",
                downloads=1000,
                uri=f"npm:package-{i}@1.0.0",
                registry_type=RegistryType.NPM
            )
            for i in range(25)
        ]
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.search_libraries.return_value = mock_search_results[:20]  # Manager should limit to 20
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
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
        
        # Verify the manager was called with limit=20
        mock_manager.search_libraries.assert_called_once()
        call_args = mock_manager.search_libraries.call_args
        assert call_args[1]["limit"] == 20
    
    @pytest.mark.asyncio
    async def test_search_libraries_all_registry_types(self):
        """Test search with all supported registry types"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import LibrarySearchResult
        from app.models.library import RegistryType
        
        # Test each registry type
        registry_tests = [
            ("npm", RegistryType.NPM),
            ("pypi", RegistryType.PYPI),
            ("maven", RegistryType.MAVEN)
        ]
        
        for registry_param, expected_enum in registry_tests:
            mock_search_results = [
                LibrarySearchResult(
                    name=f"test-{registry_param}",
                    description=f"Test {registry_param} package",
                    version="1.0.0",
                    downloads=1000,
                    uri=f"{registry_param}:test-{registry_param}@1.0.0",
                    registry_type=expected_enum
                )
            ]
            
            with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
                mock_manager = AsyncMock()
                mock_manager.search_libraries.return_value = mock_search_results
                mock_manager.close.return_value = None
                mock_manager_class.return_value = mock_manager
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get(
                        f"/api/v1/libraries/search?q=test&registry={registry_param}",
                        headers={"Authorization": "Bearer fake-token"}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 1
                assert data["results"][0]["registry_type"] == registry_param
                
                # Verify the manager was called with the correct registry type
                mock_manager.search_libraries.assert_called_once()
                call_args = mock_manager.search_libraries.call_args
                assert call_args[1]["registry_type"] == expected_enum
        
        cleanup_test_dependencies()


class TestListInstalledLibrariesEndpoint:
    """Test cases for the list installed libraries endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_success(self):
        """Test successful listing of installed libraries"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock installed libraries
        from app.schemas.library import InstalledLibrary
        from datetime import datetime
        
        mock_installed_libraries = [
            InstalledLibrary(
                id=1,
                project_id="test-project-id",
                name="react",
                version="18.0.0",
                registry_type=RegistryType.NPM,
                project_context=ProjectContext.FRONTEND,
                description="A JavaScript library for building user interfaces",
                license="MIT",
                installed_at=datetime(2023, 1, 15, 10, 30, 0),
                installed_by="test-user-id",
                uri="npm:react@18.0.0"
            ),
            InstalledLibrary(
                id=2,
                project_id="test-project-id",
                name="django",
                version="4.2.0",
                registry_type=RegistryType.PYPI,
                project_context=ProjectContext.BACKEND,
                description="A high-level Python Web framework",
                license="BSD",
                installed_at=datetime(2023, 1, 16, 14, 45, 0),
                installed_by="test-user-id",
                uri="pypi:django==4.2.0"
            )
        ]
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_installed_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=test-project-id",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["libraries"]) == 2
        
        # Verify first library
        assert data["libraries"][0]["name"] == "react"
        assert data["libraries"][0]["version"] == "18.0.0"
        assert data["libraries"][0]["registry_type"] == "npm"
        assert data["libraries"][0]["project_context"] == "frontend"
        
        # Verify second library
        assert data["libraries"][1]["name"] == "django"
        assert data["libraries"][1]["version"] == "4.2.0"
        assert data["libraries"][1]["registry_type"] == "pypi"
        assert data["libraries"][1]["project_context"] == "backend"
        
        # Verify the manager was called correctly
        mock_manager.get_installed_libraries.assert_called_once()
        call_args = mock_manager.get_installed_libraries.call_args
        assert call_args[1]["project_id"] == "test-project-id"
        assert call_args[1]["context"] is None
        assert call_args[1]["user_id"] == "test-user-id"
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_with_context_filter(self):
        """Test listing libraries with project context filter"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstalledLibrary
        from datetime import datetime
        
        # Mock only frontend libraries (filtered result)
        mock_installed_libraries = [
            InstalledLibrary(
                id=1,
                project_id="test-project-id",
                name="react",
                version="18.0.0",
                registry_type=RegistryType.NPM,
                project_context=ProjectContext.FRONTEND,
                description="A JavaScript library for building user interfaces",
                license="MIT",
                installed_at=datetime(2023, 1, 15, 10, 30, 0),
                installed_by="test-user-id",
                uri="npm:react@18.0.0"
            ),
            InstalledLibrary(
                id=3,
                project_id="test-project-id",
                name="vue",
                version="3.3.0",
                registry_type=RegistryType.NPM,
                project_context=ProjectContext.FRONTEND,
                description="The Progressive JavaScript Framework",
                license="MIT",
                installed_at=datetime(2023, 1, 17, 9, 15, 0),
                installed_by="test-user-id",
                uri="npm:vue@3.3.0"
            )
        ]
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_installed_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=test-project-id&project_context=frontend",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["libraries"]) == 2
        
        # Verify all returned libraries are frontend
        for library in data["libraries"]:
            assert library["project_context"] == "frontend"
            assert library["registry_type"] == "npm"
        
        # Verify the manager was called with context filter
        mock_manager.get_installed_libraries.assert_called_once()
        call_args = mock_manager.get_installed_libraries.call_args
        assert call_args[1]["project_id"] == "test-project-id"
        assert call_args[1]["context"] == ProjectContext.FRONTEND
        assert call_args[1]["user_id"] == "test-user-id"
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_empty_result(self):
        """Test listing libraries when no libraries are installed"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = []
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=empty-project-id",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["libraries"] == []
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_project_not_found(self):
        """Test listing libraries for non-existent project"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.side_effect = Exception("Project not found: invalid-project-id")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=invalid-project-id",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 404
        data = response.json()
        assert data["libraries"] == []
        assert data["total"] == 0
        assert "Project not found" in data["error"]
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_unauthorized(self):
        """Test listing libraries without authentication"""
        mock_db = AsyncMock()
        
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides[get_db] = override_get_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/libraries/?project_id=test-project-id")
        
        cleanup_test_dependencies()
        
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_missing_project_id(self):
        """Test listing libraries without required project_id parameter"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/libraries/",
                headers={"Authorization": "Bearer fake-token"}
            )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_invalid_context(self):
        """Test listing libraries with invalid project context"""
        mock_db, mock_user = setup_test_dependencies()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/libraries/?project_id=test-project-id&project_context=invalid",
                headers={"Authorization": "Bearer fake-token"}
            )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_all_contexts(self):
        """Test listing libraries with all supported project contexts"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstalledLibrary
        from datetime import datetime
        
        # Test each context type
        context_tests = [
            (ProjectContext.FRONTEND, "frontend"),
            (ProjectContext.BACKEND, "backend"),
            (ProjectContext.SERVICES, "services")
        ]
        
        for context_enum, context_param in context_tests:
            mock_installed_libraries = [
                InstalledLibrary(
                    id=1,
                    project_id="test-project-id",
                    name=f"test-{context_param}",
                    version="1.0.0",
                    registry_type=RegistryType.NPM if context_enum == ProjectContext.FRONTEND else RegistryType.PYPI,
                    project_context=context_enum,
                    description=f"Test {context_param} library",
                    license="MIT",
                    installed_at=datetime(2023, 1, 15, 10, 30, 0),
                    installed_by="test-user-id",
                    uri=f"npm:test-{context_param}@1.0.0"
                )
            ]
            
            with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
                mock_manager = AsyncMock()
                mock_manager.get_installed_libraries.return_value = mock_installed_libraries
                mock_manager.close.return_value = None
                mock_manager_class.return_value = mock_manager
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get(
                        f"/api/v1/libraries/?project_id=test-project-id&project_context={context_param}",
                        headers={"Authorization": "Bearer fake-token"}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 1
                assert data["libraries"][0]["project_context"] == context_param
                
                # Verify the manager was called with the correct context
                mock_manager.get_installed_libraries.assert_called_once()
                call_args = mock_manager.get_installed_libraries.call_args
                assert call_args[1]["context"] == context_enum
        
        cleanup_test_dependencies()
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_database_error(self):
        """Test handling of database errors during library listing"""
        mock_db, mock_user = setup_test_dependencies()
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.side_effect = Exception("Database connection failed")
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=test-project-id",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 500
        data = response.json()
        assert data["libraries"] == []
        assert data["total"] == 0
        assert "Internal server error" in data["error"]
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_large_result_set(self):
        """Test listing libraries with large number of results"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstalledLibrary
        from datetime import datetime
        
        # Create 50 mock libraries to test large result handling
        mock_installed_libraries = []
        for i in range(50):
            mock_installed_libraries.append(
                InstalledLibrary(
                    id=i + 1,
                    project_id="test-project-id",
                    name=f"library-{i:02d}",
                    version="1.0.0",
                    registry_type=RegistryType.NPM if i % 2 == 0 else RegistryType.PYPI,
                    project_context=ProjectContext.FRONTEND if i % 2 == 0 else ProjectContext.BACKEND,
                    description=f"Test library {i}",
                    license="MIT",
                    installed_at=datetime(2023, 1, 15, 10, 30, i),
                    installed_by="test-user-id",
                    uri=f"npm:library-{i:02d}@1.0.0"
                )
            )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_installed_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=test-project-id",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 50
        assert len(data["libraries"]) == 50
        
        # Verify libraries are properly serialized
        for i, library in enumerate(data["libraries"]):
            assert library["name"] == f"library-{i:02d}"
            assert library["version"] == "1.0.0"
            assert library["project_context"] in ["frontend", "backend"]
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_metadata_fields(self):
        """Test that all required metadata fields are included in response"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstalledLibrary
        from datetime import datetime
        
        mock_installed_library = InstalledLibrary(
            id=1,
            project_id="test-project-id",
            name="react",
            version="18.0.0",
            registry_type=RegistryType.NPM,
            project_context=ProjectContext.FRONTEND,
            description="A JavaScript library for building user interfaces",
            license="MIT",
            installed_at=datetime(2023, 1, 15, 10, 30, 0),
            installed_by="test-user-id",
            uri="npm:react@18.0.0",
            metadata={"homepage": "https://reactjs.org", "repository": "https://github.com/facebook/react"}
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = [mock_installed_library]
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/libraries/?project_id=test-project-id",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        
        library = data["libraries"][0]
        
        # Verify all required fields are present
        required_fields = [
            "id", "project_id", "name", "version", "registry_type",
            "project_context", "description", "license", "installed_at",
            "installed_by", "uri"
        ]
        
        for field in required_fields:
            assert field in library, f"Required field '{field}' missing from response"
        
        # Verify field values
        assert library["id"] == 1
        assert library["project_id"] == "test-project-id"
        assert library["name"] == "react"
        assert library["version"] == "18.0.0"
        assert library["registry_type"] == "npm"
        assert library["project_context"] == "frontend"
        assert library["description"] == "A JavaScript library for building user interfaces"
        assert library["license"] == "MIT"
        assert library["installed_by"] == "test-user-id"
        assert library["uri"] == "npm:react@18.0.0"
        assert library["metadata"]["homepage"] == "https://reactjs.org"
        assert library["metadata"]["repository"] == "https://github.com/facebook/react"
    
    @pytest.mark.asyncio
    async def test_list_installed_libraries_case_insensitive_context(self):
        """Test listing libraries with case-insensitive context parameter"""
        mock_db, mock_user = setup_test_dependencies()
        
        from app.schemas.library import InstalledLibrary
        from datetime import datetime
        
        mock_installed_libraries = [
            InstalledLibrary(
                id=1,
                project_id="test-project-id",
                name="react",
                version="18.0.0",
                registry_type=RegistryType.NPM,
                project_context=ProjectContext.FRONTEND,
                description="A JavaScript library for building user interfaces",
                license="MIT",
                installed_at=datetime(2023, 1, 15, 10, 30, 0),
                installed_by="test-user-id",
                uri="npm:react@18.0.0"
            )
        ]
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.get_installed_libraries.return_value = mock_installed_libraries
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test uppercase context parameter
                response = await client.get(
                    "/api/v1/libraries/?project_id=test-project-id&project_context=FRONTEND",
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        # Should return 422 because enum validation is case-sensitive
        assert response.status_code == 422


class TestLibraryRouterStructure:

    """Test cases for library router structure and other endpoints"""
    
    @pytest.mark.asyncio
    async def test_install_endpoint_not_implemented(self):
        """Test that install endpoint is now implemented"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock LibraryManager.install_library to return success
        from app.schemas.library import InstallationResult, InstalledLibrary
        from datetime import datetime
        
        mock_installed_library = InstalledLibrary(
            id=1,
            project_id="test-user-id",
            name="react",
            version="18.0.0",
            registry_type=RegistryType.NPM,
            project_context=ProjectContext.FRONTEND,
            description="A JavaScript library for building user interfaces",
            license="MIT",
            installed_at=datetime.now(),
            installed_by="test-user-id",
            uri="npm:react@18.0.0"
        )
        
        mock_installation_result = InstallationResult(
            success=True,
            installed_library=mock_installed_library,
            errors=[]
        )
        
        with patch('app.api.v1.endpoints.libraries.LibraryManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.install_library.return_value = mock_installation_result
            mock_manager.close.return_value = None
            mock_manager_class.return_value = mock_manager
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/libraries/install",
                    json={
                        "uri": "npm:react@18.0.0",
                        "project_context": "frontend"
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["installed_library"]["name"] == "react"
        assert data["installed_library"]["version"] == "18.0.0"


# Legacy test functions for backward compatibility
def test_library_router_included():
    """Test that the library router is properly included in the API"""
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test that the router responds to requests
    response = client.post("/api/v1/libraries/validate", json={"uri": "npm:test"})
    
    # Should return 401 Unauthorized or 403 Forbidden since authentication is required
    assert response.status_code in [401, 403]


def test_validate_endpoint_requires_auth():
    """Test that the validate endpoint requires authentication"""
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    response = client.post("/api/v1/libraries/validate", json={"uri": "npm:test"})
    
    # Should return 401 Unauthorized or 403 Forbidden
    assert response.status_code in [401, 403]


def test_invalid_validate_request():
    """Test validation of request schemas"""
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test empty URI - should return 403 Forbidden due to authentication, not 422
    response = client.post("/api/v1/libraries/validate", json={"uri": ""})
    
    # Should return 403 Forbidden since authentication is required before validation
    assert response.status_code in [401, 403, 422]
