"""
Integration tests for the Install Library endpoint

Tests the complete install library workflow including LibraryManager integration.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from datetime import datetime

from app.main import app
from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.schemas.library import (
    InstallationResult, 
    InstalledLibrary, 
    ProjectContext
)
from app.models.library import RegistryType
from app.services.library_management.library_manager import LibraryManager


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


class TestInstallLibraryIntegration:
    """Integration tests for install library endpoint"""
    
    @pytest.mark.asyncio
    async def test_install_npm_library_complete_workflow(self):
        """Test complete npm library installation workflow"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock the complete LibraryManager workflow
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
        
        # Mock LibraryManager and its methods
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result) as mock_install:
                with patch.object(LibraryManager, 'close', return_value=None) as mock_close:
                    
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
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["installed_library"]["name"] == "react"
        assert data["installed_library"]["version"] == "18.0.0"
        assert data["installed_library"]["registry_type"] == "npm"
        assert data["installed_library"]["project_context"] == "frontend"
        assert data["errors"] is None
        
        # Verify LibraryManager was called correctly
        mock_install.assert_called_once()
        call_args = mock_install.call_args
        assert call_args[1]["uri"] == "npm:react@18.0.0"
        assert call_args[1]["context"] == ProjectContext.FRONTEND
        assert call_args[1]["user_id"] == "test-user-id"
        assert call_args[1]["project_id"] == "test-user-id"
    
    @pytest.mark.asyncio
    async def test_install_pypi_library_complete_workflow(self):
        """Test complete PyPI library installation workflow"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_installed_library = InstalledLibrary(
            id=2,
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
        
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result) as mock_install:
                with patch.object(LibraryManager, 'close', return_value=None):
                    
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
    
    @pytest.mark.asyncio
    async def test_install_library_with_dependency_conflicts(self):
        """Test installation with dependency conflicts returns 409"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_installation_result = InstallationResult(
            success=False,
            installed_library=None,
            errors=[
                "Version conflict: react (existing: 17.0.2, required: ^18.0.0)",
                "Incompatible peer dependency: react-dom requires react@^18.0.0"
            ]
        )
        
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result):
                with patch.object(LibraryManager, 'close', return_value=None):
                    
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
        
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert data["success"] is False
        assert "Version conflict" in data["errors"][0]
        assert "Incompatible peer dependency" in data["errors"][1]
    
    @pytest.mark.asyncio
    async def test_install_library_package_not_found(self):
        """Test installation with package not found returns 400"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_installation_result = InstallationResult(
            success=False,
            installed_library=None,
            errors=["Package not found: nonexistent-package does not exist in npm registry"]
        )
        
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result):
                with patch.object(LibraryManager, 'close', return_value=None):
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            "/api/v1/libraries/install",
                            json={
                                "uri": "npm:nonexistent-package@1.0.0",
                                "project_context": "frontend"
                            },
                            headers={"Authorization": "Bearer fake-token"}
                        )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 400  # Bad Request
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["errors"][0].lower()
    
    @pytest.mark.asyncio
    async def test_install_library_installation_failure(self):
        """Test installation failure returns 500"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_installation_result = InstallationResult(
            success=False,
            installed_library=None,
            errors=["npm install failed: EACCES permission denied, mkdir '/usr/local/lib/node_modules'"]
        )
        
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result):
                with patch.object(LibraryManager, 'close', return_value=None):
                    
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
        
        assert response.status_code == 500  # Internal Server Error
        data = response.json()
        assert data["success"] is False
        assert "npm install failed" in data["errors"][0]
    
    @pytest.mark.asyncio
    async def test_install_library_with_version_override_integration(self):
        """Test installation with version override parameter"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_installed_library = InstalledLibrary(
            id=3,
            project_id="test-user-id",
            name="lodash",
            version="4.17.20",  # Override version
            registry_type=RegistryType.NPM,
            project_context=ProjectContext.FRONTEND,
            description="A modern JavaScript utility library",
            license="MIT",
            installed_at=datetime.now(),
            installed_by="test-user-id",
            uri="npm:lodash@4.17.21"  # Original URI version
        )
        
        mock_installation_result = InstallationResult(
            success=True,
            installed_library=mock_installed_library,
            errors=[]
        )
        
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result) as mock_install:
                with patch.object(LibraryManager, 'close', return_value=None):
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            "/api/v1/libraries/install",
                            json={
                                "uri": "npm:lodash@4.17.21",
                                "project_context": "frontend",
                                "version": "4.17.20"  # Override version
                            },
                            headers={"Authorization": "Bearer fake-token"}
                        )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["installed_library"]["version"] == "4.17.20"
        
        # Verify the manager was called with the override version
        mock_install.assert_called_once()
        call_args = mock_install.call_args
        assert call_args[1]["version"] == "4.17.20"
    
    @pytest.mark.asyncio
    async def test_install_library_logging_and_audit_trail(self):
        """Test that installation operations are properly logged"""
        mock_db, mock_user = setup_test_dependencies()
        
        mock_installed_library = InstalledLibrary(
            id=4,
            project_id="test-user-id",
            name="express",
            version="4.18.0",
            registry_type=RegistryType.NPM,
            project_context=ProjectContext.BACKEND,  # Using backend for Node.js server
            description="Fast, unopinionated, minimalist web framework",
            license="MIT",
            installed_at=datetime.now(),
            installed_by="test-user-id",
            uri="npm:express@4.18.0"
        )
        
        mock_installation_result = InstallationResult(
            success=True,
            installed_library=mock_installed_library,
            errors=[]
        )
        
        with patch('app.services.library_management.library_repository.LibraryRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            
            with patch.object(LibraryManager, 'install_library', return_value=mock_installation_result) as mock_install:
                with patch.object(LibraryManager, 'close', return_value=None):
                    with patch('app.api.v1.endpoints.libraries.logger') as mock_logger:
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            response = await client.post(
                                "/api/v1/libraries/install",
                                json={
                                    "uri": "npm:express@4.18.0",
                                    "project_context": "backend"
                                },
                                headers={"Authorization": "Bearer fake-token"}
                            )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        
        # Verify logging calls were made
        assert mock_logger.info.call_count >= 2  # At least start and success logs
        
        # Check that the logs contain expected information
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Installing library URI" in log for log in log_calls)
        assert any("Library installation successful" in log for log in log_calls)
