"""
Integration tests for the validate library endpoint

Tests the endpoint with real LibraryManager instances to ensure proper integration.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.main import app
from app.database.postgresql import get_db
from app.api.dependencies import get_current_user
from app.schemas.library import LibraryMetadata, ProjectContext
from app.models.library import RegistryType


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


class TestValidateLibraryIntegration:
    """Integration test cases for the validate library endpoint"""
    
    @pytest.mark.asyncio
    async def test_validate_library_with_mocked_services(self):
        """Test validation with mocked LibraryManager services"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock the individual services that LibraryManager uses
        with patch('app.services.library_management.uri_parser.URIParser') as mock_uri_parser_class:
            with patch('app.services.library_management.metadata_fetcher.MetadataFetcher') as mock_metadata_fetcher_class:
                with patch('app.services.library_management.context_detector.ContextDetector') as mock_context_detector_class:
                    
                    # Set up URI parser mock
                    mock_uri_parser = AsyncMock()
                    mock_parsed_uri = AsyncMock()
                    mock_parsed_uri.registry_type = RegistryType.NPM
                    mock_parsed_uri.package_name = "react"
                    mock_parsed_uri.version = "18.0.0"
                    mock_uri_parser.parse.return_value = mock_parsed_uri
                    mock_uri_parser_class.return_value = mock_uri_parser
                    
                    # Set up metadata fetcher mock
                    mock_metadata_fetcher = AsyncMock()
                    mock_library_metadata = LibraryMetadata(
                        name="react",
                        version="18.0.0",
                        description="A JavaScript library for building user interfaces",
                        license="MIT",
                        registry_type=RegistryType.NPM,
                        dependencies=[]
                    )
                    mock_metadata_fetcher.fetch_metadata.return_value = mock_library_metadata
                    mock_metadata_fetcher.close.return_value = None
                    mock_metadata_fetcher_class.return_value = mock_metadata_fetcher
                    
                    # Set up context detector mock
                    mock_context_detector = AsyncMock()
                    mock_context_detector.detect_and_validate_context.return_value = (
                        ProjectContext.FRONTEND, True, None
                    )
                    mock_context_detector_class.return_value = mock_context_detector
                    
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
    
    @pytest.mark.asyncio
    async def test_validate_library_with_uri_parser_error(self):
        """Test validation when URI parser raises an error"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock the URI parser to raise an error
        with patch('app.services.library_management.uri_parser.URIParser') as mock_uri_parser_class:
            mock_uri_parser = AsyncMock()
            mock_uri_parser.parse.side_effect = ValueError("Invalid URI format")
            mock_uri_parser_class.return_value = mock_uri_parser
            
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
    async def test_validate_library_dependency_injection(self):
        """Test that the LibraryManager dependency is properly injected"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock all the services to ensure they're called
        with patch('app.services.library_management.uri_parser.URIParser') as mock_uri_parser_class:
            with patch('app.services.library_management.metadata_fetcher.MetadataFetcher') as mock_metadata_fetcher_class:
                with patch('app.services.library_management.context_detector.ContextDetector') as mock_context_detector_class:
                    with patch('app.services.library_management.dependency_resolver.DependencyResolver') as mock_dependency_resolver_class:
                        with patch('app.services.library_management.package_installer.PackageInstaller') as mock_package_installer_class:
                            with patch('app.services.library_management.search_service.SearchService') as mock_search_service_class:
                                
                                # Set up all mocks
                                mock_uri_parser = AsyncMock()
                                mock_parsed_uri = AsyncMock()
                                mock_parsed_uri.registry_type = RegistryType.NPM
                                mock_parsed_uri.package_name = "react"
                                mock_parsed_uri.version = "18.0.0"
                                mock_uri_parser.parse.return_value = mock_parsed_uri
                                mock_uri_parser_class.return_value = mock_uri_parser
                                
                                mock_metadata_fetcher = AsyncMock()
                                mock_library_metadata = LibraryMetadata(
                                    name="react",
                                    version="18.0.0",
                                    description="A JavaScript library for building user interfaces",
                                    license="MIT",
                                    registry_type=RegistryType.NPM,
                                    dependencies=[]
                                )
                                mock_metadata_fetcher.fetch_metadata.return_value = mock_library_metadata
                                mock_metadata_fetcher.close.return_value = None
                                mock_metadata_fetcher_class.return_value = mock_metadata_fetcher
                                
                                mock_context_detector = AsyncMock()
                                mock_context_detector.detect_and_validate_context.return_value = (
                                    ProjectContext.FRONTEND, True, None
                                )
                                mock_context_detector_class.return_value = mock_context_detector
                                
                                # Set up other service mocks
                                mock_dependency_resolver_class.return_value = AsyncMock()
                                mock_package_installer_class.return_value = AsyncMock()
                                mock_search_service_class.return_value = AsyncMock()
                                
                                async with AsyncClient(app=app, base_url="http://test") as client:
                                    response = await client.post(
                                        "/api/v1/libraries/validate",
                                        json={"uri": "npm:react@18.0.0"},
                                        headers={"Authorization": "Bearer fake-token"}
                                    )
        
        cleanup_test_dependencies()
        
        # Verify that the LibraryManager was created and used
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        
        # Verify that the services were instantiated (dependency injection worked)
        mock_uri_parser_class.assert_called_once()
        mock_metadata_fetcher_class.assert_called_once()
        mock_context_detector_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_library_with_project_context(self):
        """Test validation with specified project context"""
        mock_db, mock_user = setup_test_dependencies()
        
        # Mock the services
        with patch('app.services.library_management.uri_parser.URIParser') as mock_uri_parser_class:
            with patch('app.services.library_management.metadata_fetcher.MetadataFetcher') as mock_metadata_fetcher_class:
                with patch('app.services.library_management.context_detector.ContextDetector') as mock_context_detector_class:
                    
                    # Set up mocks
                    mock_uri_parser = AsyncMock()
                    mock_parsed_uri = AsyncMock()
                    mock_parsed_uri.registry_type = RegistryType.PYPI
                    mock_parsed_uri.package_name = "django"
                    mock_parsed_uri.version = "4.2.0"
                    mock_uri_parser.parse.return_value = mock_parsed_uri
                    mock_uri_parser_class.return_value = mock_uri_parser
                    
                    mock_metadata_fetcher = AsyncMock()
                    mock_library_metadata = LibraryMetadata(
                        name="django",
                        version="4.2.0",
                        description="A high-level Python Web framework",
                        license="BSD-3-Clause",
                        registry_type=RegistryType.PYPI,
                        dependencies=[]
                    )
                    mock_metadata_fetcher.fetch_metadata.return_value = mock_library_metadata
                    mock_metadata_fetcher.close.return_value = None
                    mock_metadata_fetcher_class.return_value = mock_metadata_fetcher
                    
                    mock_context_detector = AsyncMock()
                    mock_context_detector.validate_context.return_value = (True, None)
                    mock_context_detector_class.return_value = mock_context_detector
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            "/api/v1/libraries/validate",
                            json={
                                "uri": "pypi:django==4.2.0",
                                "project_context": "backend"
                            },
                            headers={"Authorization": "Bearer fake-token"}
                        )
        
        cleanup_test_dependencies()
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["library"]["name"] == "django"
        assert data["library"]["registry_type"] == "pypi"
        assert data["suggested_context"] == "backend"
