"""
Unit Tests for Service Configuration Generator

Tests the service-specific configuration generation, change propagation,
and hot reloading capabilities.

Validates Requirements: 1.4, 1.5
"""

import json
import time
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.configuration_manager import (
    ConfigurationManager,
    ConfigurationChangeEvent,
    ConfigurationSource,
    ServiceConfig
)

TEST_USER = "postgres"
TEST_PASSWORD = "postgres_password_12345678"
TEST_DB = "ai_code_review"
TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_service_config_generator"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def make_test_dir(prefix: str) -> Path:
    path = TEST_TMP_ROOT / f"{prefix}_{time.time_ns()}"
    path.mkdir(parents=True, exist_ok=True)
    return path
from app.core.service_config_generator import (
    ServiceConfigGenerator,
    ServiceDefinition,
    ServiceType,
    ConfigurationUpdate,
    get_service_config_generator,
    generate_service_configuration,
    export_service_configuration
)


class TestServiceDefinition:
    """Test ServiceDefinition functionality"""
    
    def test_service_definition_creation(self):
        """Test service definition creation"""
        service_def = ServiceDefinition(
            name="test_service",
            service_type=ServiceType.BACKEND,
            required_keys={"KEY1", "KEY2"},
            optional_keys={"KEY3"},
            key_prefixes=["TEST_"],
            config_file_path=Path("test/.env"),
            dependencies=["database"],
            health_check_url="http://localhost:8000/health"
        )
        
        assert service_def.name == "test_service"
        assert service_def.service_type == ServiceType.BACKEND
        assert service_def.required_keys == {"KEY1", "KEY2"}
        assert service_def.optional_keys == {"KEY3"}
        assert service_def.key_prefixes == ["TEST_"]
        assert service_def.config_file_path == Path("test/.env")
        assert service_def.dependencies == ["database"]
        assert service_def.health_check_url == "http://localhost:8000/health"


class TestConfigurationUpdate:
    """Test ConfigurationUpdate functionality"""
    
    def test_configuration_update_creation(self):
        """Test configuration update creation"""
        update = ConfigurationUpdate(
            service_name="test_service",
            updated_keys={"KEY1": "value1", "KEY2": "value2"}
        )
        
        assert update.service_name == "test_service"
        assert update.updated_keys == {"KEY1": "value1", "KEY2": "value2"}
        assert update.propagation_status == "pending"
        assert update.error_message is None
        assert isinstance(update.timestamp, float)


class TestServiceConfigGenerator:
    """Test Service Configuration Generator functionality"""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager"""
        mock_manager = MagicMock(spec=ConfigurationManager)
        mock_manager.configurations = {
            "JWT_SECRET": MagicMock(value="jwt_secret_32_characters_long_test"),
            "SECRET_KEY": MagicMock(value="secret_key_32_characters_long_test"),
            "POSTGRES_HOST": MagicMock(value="localhost"),
            "POSTGRES_PORT": MagicMock(value=5432),
            "POSTGRES_PASSWORD": MagicMock(value="postgres_password_12345678"),
            "NEXT_PUBLIC_API_URL": MagicMock(value="http://localhost:8000/api/v1"),
            "NEXTAUTH_URL": MagicMock(value="http://localhost:3000"),
            "REDIS_HOST": MagicMock(value="localhost"),
            "REDIS_PORT": MagicMock(value=6379),
            "NEO4J_URI": MagicMock(value="bolt://localhost:7687"),
            "DATABASE_URL": MagicMock(value=f"postgresql://{TEST_USER}:{TEST_PASSWORD}@localhost:5432/{TEST_DB}"),
            "REDIS_URL": MagicMock(value="redis://localhost:6379/0")
        }
        
        # Mock get_service_config method
        def mock_get_service_config(service_name, required_keys=None, optional_keys=None):
            all_config = {key: entry.value for key, entry in mock_manager.configurations.items()}
            
            # Filter based on service type
            if service_name == "frontend":
                filtered_config = {
                    k: v for k, v in all_config.items()
                    if k.startswith("NEXT") or k in ["NODE_ENV", "FRONTEND_PORT"]
                }
            elif service_name == "backend":
                filtered_config = {
                    k: v for k, v in all_config.items()
                    if k.startswith(("POSTGRES_", "NEO4J_", "REDIS_", "JWT_", "SECRET_"))
                    or k in ["DATABASE_URL", "REDIS_URL", "BACKEND_PORT"]
                }
            else:
                filtered_config = all_config
            
            return ServiceConfig(
                service_name=service_name,
                config=filtered_config,
                required_keys=required_keys or set(),
                optional_keys=optional_keys or set()
            )
        
        mock_manager.get_service_config.side_effect = mock_get_service_config
        return mock_manager
    
    def test_initialization(self, mock_config_manager):
        """Test Service Configuration Generator initialization"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        assert generator.config_manager == mock_config_manager
        assert len(generator.service_definitions) > 0  # Should have default services
        assert "frontend" in generator.service_definitions
        assert "backend" in generator.service_definitions
        assert "api-gateway" in generator.service_definitions
        assert "auth-service" in generator.service_definitions
    
    def test_register_service(self, mock_config_manager):
        """Test service registration"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        service_def = ServiceDefinition(
            name="custom_service",
            service_type=ServiceType.BACKEND,
            required_keys={"CUSTOM_KEY"},
            optional_keys={"OPTIONAL_KEY"}
        )
        
        generator.register_service(service_def)
        
        assert "custom_service" in generator.service_definitions
        assert generator.service_definitions["custom_service"] == service_def
    
    def test_unregister_service(self, mock_config_manager):
        """Test service unregistration"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Register a service first
        service_def = ServiceDefinition(
            name="temp_service",
            service_type=ServiceType.BACKEND
        )
        generator.register_service(service_def)
        
        # Verify it's registered
        assert "temp_service" in generator.service_definitions
        
        # Unregister it
        generator.unregister_service("temp_service")
        
        # Verify it's removed
        assert "temp_service" not in generator.service_definitions
    
    def test_generate_service_config_frontend(self, mock_config_manager):
        """Test frontend service configuration generation (Requirement 1.4)"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        config = generator.generate_service_config("frontend")
        
        assert config.service_name == "frontend"
        assert isinstance(config.config, dict)
        
        # Should contain frontend-specific keys
        assert "NEXT_PUBLIC_API_URL" in config.config
        assert "NEXTAUTH_URL" in config.config
        
        # Should not contain backend secrets
        assert "POSTGRES_PASSWORD" not in config.config
        assert "JWT_SECRET" not in config.config
    
    def test_generate_service_config_backend(self, mock_config_manager):
        """Test backend service configuration generation (Requirement 1.4)"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        config = generator.generate_service_config("backend")
        
        assert config.service_name == "backend"
        assert isinstance(config.config, dict)
        
        # Should contain backend-specific keys
        assert "JWT_SECRET" in config.config
        assert "SECRET_KEY" in config.config
        assert "POSTGRES_HOST" in config.config
        assert "POSTGRES_PASSWORD" in config.config
        
        # Should not contain frontend-specific keys
        assert "NEXTAUTH_URL" not in config.config
    
    def test_generate_service_config_with_dependencies(self, mock_config_manager):
        """Test service configuration generation with dependencies"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        config = generator.generate_service_config("backend", include_dependencies=True)
        
        assert config.service_name == "backend"
        assert len(config.dependencies) > 0
        
        # Should include dependency-related configuration
        assert isinstance(config.config, dict)
    
    def test_generate_all_service_configs(self, mock_config_manager):
        """Test generating configurations for all services"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        all_configs = generator.generate_all_service_configs()
        
        assert isinstance(all_configs, dict)
        assert len(all_configs) > 0
        
        # Should contain default services
        assert "frontend" in all_configs
        assert "backend" in all_configs
        
        # Each config should be a ServiceConfig instance
        for service_name, config in all_configs.items():
            assert isinstance(config, ServiceConfig)
            assert config.service_name == service_name
    
    def test_export_service_config_env_format(self, mock_config_manager):
        """Test exporting service configuration in .env format"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Generate config first
        generator.generate_service_config("frontend")
        
        # Export as .env format
        env_content = generator.export_service_config("frontend", format="env")
        
        assert isinstance(env_content, str)
        assert "NEXT_PUBLIC_API_URL=" in env_content
        assert "NEXTAUTH_URL=" in env_content
        
        # Should be in key=value format
        lines = env_content.strip().split('\n')
        for line in lines:
            if line and not line.startswith('#'):
                assert '=' in line
    
    def test_export_service_config_json_format(self, mock_config_manager):
        """Test exporting service configuration in JSON format"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Generate config first
        generator.generate_service_config("backend")
        
        # Export as JSON format
        json_content = generator.export_service_config("backend", format="json")
        
        assert isinstance(json_content, str)
        
        # Should be valid JSON
        parsed_json = json.loads(json_content)
        assert isinstance(parsed_json, dict)
        assert "JWT_SECRET" in parsed_json
    
    def test_export_service_config_with_secret_masking(self, mock_config_manager):
        """Test exporting service configuration with secret masking"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Generate config first
        generator.generate_service_config("backend")
        
        # Export with secret masking
        masked_content = generator.export_service_config("backend", format="json", mask_secrets=True)
        parsed_json = json.loads(masked_content)
        
        # Secrets should be masked
        if "JWT_SECRET" in parsed_json:
            assert "***" in parsed_json["JWT_SECRET"]
        if "SECRET_KEY" in parsed_json:
            assert "***" in parsed_json["SECRET_KEY"]
    
    def test_write_service_config_file(self, mock_config_manager):
        """Test writing service configuration to file (Requirement 1.4, 1.5)"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        temp_dir = make_test_dir("write_service_config")
        config_file = temp_dir / "test.env"

        # Update service definition with config file path
        service_def = generator.service_definitions["frontend"]
        service_def.config_file_path = config_file

        # Write config file
        success = generator.write_service_config_file("frontend", force=True)

        assert success
        assert config_file.exists()

        # Check file content
        content = config_file.read_text()
        assert "NEXT_PUBLIC_API_URL=" in content
        assert "# Auto-generated configuration" in content

        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_configuration_change_propagation(self, mock_config_manager):
        """Test configuration change propagation (Requirement 1.5)"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Track propagation calls
        propagation_calls = []
        
        def test_callback(service_name, event):
            propagation_calls.append((service_name, event.key, event.new_value))
        
        # Add callback for frontend service
        generator.add_propagation_callback("frontend", test_callback)
        
        # Simulate configuration change
        change_event = ConfigurationChangeEvent(
            key="NEXT_PUBLIC_API_URL",
            old_value="http://localhost:8000/api/v1",
            new_value="http://localhost:9000/api/v1",
            source=ConfigurationSource.RUNTIME
        )
        
        # Trigger change handler
        generator._on_configuration_change(change_event)
        
        # Check that callback was called
        assert len(propagation_calls) > 0
        assert propagation_calls[0][0] == "frontend"
        assert propagation_calls[0][1] == "NEXT_PUBLIC_API_URL"
        assert propagation_calls[0][2] == "http://localhost:9000/api/v1"
    
    def test_find_affected_services(self, mock_config_manager):
        """Test finding services affected by configuration changes"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Test frontend-specific key
        affected = generator._find_affected_services("NEXT_PUBLIC_API_URL")
        assert "frontend" in affected
        assert "backend" not in affected
        
        # Test backend-specific key
        affected = generator._find_affected_services("POSTGRES_PASSWORD")
        assert "backend" in affected
        assert "frontend" not in affected
        
        # Test shared key (JWT_SECRET)
        affected = generator._find_affected_services("JWT_SECRET")
        assert "backend" in affected
        assert "api-gateway" in affected
    
    def test_service_status(self, mock_config_manager):
        """Test getting service status information"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Generate config to make service active
        generator.generate_service_config("frontend")
        
        status = generator.get_service_status("frontend")
        
        assert status["name"] == "frontend"
        assert status["type"] == "frontend"
        assert status["is_active"] is True
        assert isinstance(status["dependencies"], list)
        assert isinstance(status["required_keys"], list)
        assert isinstance(status["optional_keys"], list)
    
    def test_get_all_service_status(self, mock_config_manager):
        """Test getting status for all services"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        all_status = generator.get_all_service_status()
        
        assert isinstance(all_status, dict)
        assert len(all_status) > 0
        
        # Should contain default services
        assert "frontend" in all_status
        assert "backend" in all_status
        
        # Each status should have required fields
        for service_name, status in all_status.items():
            assert status["name"] == service_name
            assert "type" in status
            assert "is_active" in status
    
    def test_cleanup_update_queue(self, mock_config_manager):
        """Test cleaning up old update queue entries"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Add some old updates
        old_update = ConfigurationUpdate(
            service_name="test_service",
            updated_keys={"KEY": "value"}
        )
        old_update.timestamp = time.time() - (25 * 3600)  # 25 hours ago
        
        recent_update = ConfigurationUpdate(
            service_name="test_service",
            updated_keys={"KEY": "value"}
        )
        
        generator.update_queue = [old_update, recent_update]
        
        # Clean up entries older than 24 hours
        removed_count = generator.cleanup_update_queue(max_age_hours=24)
        
        assert removed_count == 1
        assert len(generator.update_queue) == 1
        assert generator.update_queue[0] == recent_update
    
    def test_service_type_key_detection(self, mock_config_manager):
        """Test service type specific key detection"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Test frontend keys
        assert generator._is_service_type_key(ServiceType.FRONTEND, "NODE_ENV")
        assert generator._is_service_type_key(ServiceType.FRONTEND, "FRONTEND_PORT")
        assert not generator._is_service_type_key(ServiceType.FRONTEND, "POSTGRES_HOST")
        
        # Test backend keys
        assert generator._is_service_type_key(ServiceType.BACKEND, "BACKEND_PORT")
        assert generator._is_service_type_key(ServiceType.BACKEND, "DEBUG")
        assert not generator._is_service_type_key(ServiceType.BACKEND, "FRONTEND_PORT")
        
        # Test API gateway keys
        assert generator._is_service_type_key(ServiceType.API_GATEWAY, "PORT")
        assert generator._is_service_type_key(ServiceType.API_GATEWAY, "REQUEST_TIMEOUT")
    
    def test_invalid_service_name(self, mock_config_manager):
        """Test handling of invalid service names"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        with pytest.raises(ValueError, match="Service not registered"):
            generator.generate_service_config("nonexistent_service")
    
    def test_unsupported_export_format(self, mock_config_manager):
        """Test handling of unsupported export formats"""
        generator = ServiceConfigGenerator(mock_config_manager)
        
        # Generate config first
        generator.generate_service_config("frontend")
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            generator.export_service_config("frontend", format="xml")


class TestGlobalServiceConfigGenerator:
    """Test global service configuration generator functions"""
    
    def test_get_service_config_generator_singleton(self):
        """Test that get_service_config_generator returns singleton"""
        generator1 = get_service_config_generator()
        generator2 = get_service_config_generator()
        
        assert generator1 is generator2
    
    @patch('app.core.service_config_generator.get_service_config_generator')
    def test_generate_service_configuration(self, mock_get_generator):
        """Test generate_service_configuration function"""
        mock_generator = MagicMock()
        mock_config = ServiceConfig(
            service_name="test_service",
            config={"KEY": "value"}
        )
        mock_generator.generate_service_config.return_value = mock_config
        mock_get_generator.return_value = mock_generator
        
        result = generate_service_configuration("test_service", include_dependencies=False)
        
        assert result == mock_config
        mock_generator.generate_service_config.assert_called_once_with("test_service", False)
    
    @patch('app.core.service_config_generator.get_service_config_generator')
    def test_export_service_configuration(self, mock_get_generator):
        """Test export_service_configuration function"""
        mock_generator = MagicMock()
        mock_content = "KEY=value\nANOTHER_KEY=another_value"
        mock_generator.export_service_config.return_value = mock_content
        mock_get_generator.return_value = mock_generator
        
        result = export_service_configuration("test_service", format="env")
        
        assert result == mock_content
        mock_generator.export_service_config.assert_called_once_with("test_service", "env")
    
    @patch('app.core.service_config_generator.get_service_config_generator')
    def test_export_service_configuration_with_file(self, mock_get_generator):
        """Test export_service_configuration function with file output"""
        mock_generator = MagicMock()
        mock_content = "KEY=value\nANOTHER_KEY=another_value"
        mock_generator.export_service_config.return_value = mock_content
        mock_get_generator.return_value = mock_generator
        
        temp_dir = make_test_dir("export_service_config")
        output_file = temp_dir / "config.env"

        result = export_service_configuration("test_service", format="env", output_file=output_file)

        assert result == mock_content
        assert output_file.exists()
        assert output_file.read_text() == mock_content
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestServiceConfigIntegration:
    """Integration tests for service configuration generation"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with config files"""
        project_path = make_test_dir("integration_project")

        # Create directory structure
        (project_path / "frontend").mkdir()
        (project_path / "backend").mkdir()

        # Create root .env file
        (project_path / ".env").write_text("""
JWT_SECRET=jwt_secret_32_characters_long_test
SECRET_KEY=secret_key_32_characters_long_test
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_PASSWORD=postgres_password_12345678
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=neo4j_password_12345678
REDIS_HOST=localhost
REDIS_PORT=6379
""".strip())

        # Create frontend .env.local
        (project_path / "frontend" / ".env.local").write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=nextauth_secret_32_characters_long
""".strip())

        yield project_path
        shutil.rmtree(project_path, ignore_errors=True)
    
    def test_end_to_end_service_configuration(self, temp_project_dir):
        """Test end-to-end service configuration generation"""
        # Create configuration manager with real project
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        # Create service config generator
        generator = ServiceConfigGenerator(config_manager)
        
        # Generate frontend configuration
        frontend_config = generator.generate_service_config("frontend")
        
        assert frontend_config.service_name == "frontend"
        assert "NEXT_PUBLIC_API_URL" in frontend_config.config
        assert "NEXTAUTH_URL" in frontend_config.config
        assert "NEXTAUTH_SECRET" in frontend_config.config
        
        # Backend secrets should not be in frontend config
        assert "POSTGRES_PASSWORD" not in frontend_config.config
        
        # Generate backend configuration
        backend_config = generator.generate_service_config("backend")
        
        assert backend_config.service_name == "backend"
        assert "JWT_SECRET" in backend_config.config
        assert "POSTGRES_HOST" in backend_config.config
        assert "POSTGRES_PASSWORD" in backend_config.config
        
        # Frontend secrets should not be in backend config
        assert "NEXTAUTH_SECRET" not in backend_config.config
    
    def test_configuration_change_propagation_integration(self, temp_project_dir):
        """Test configuration change propagation in integration scenario"""
        # Create configuration manager with real project
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        # Create service config generator
        generator = ServiceConfigGenerator(config_manager)
        
        # Generate initial configurations
        generator.generate_service_config("frontend")
        generator.generate_service_config("backend")
        
        # Track changes
        change_events = []
        
        def track_changes(service_name, event):
            change_events.append((service_name, event.key, event.new_value))
        
        generator.add_propagation_callback("frontend", track_changes)
        generator.add_propagation_callback("backend", track_changes)
        
        # Update configuration through manager
        config_manager.update_configuration({
            "NEXT_PUBLIC_API_URL": "http://localhost:9000/api/v1",
            "JWT_SECRET": "new_jwt_secret_32_characters_long_test"
        })
        
        # Check that changes were propagated
        assert len(change_events) > 0
        
        # Frontend should receive NEXT_PUBLIC_API_URL change
        frontend_changes = [e for e in change_events if e[0] == "frontend"]
        assert any(e[1] == "NEXT_PUBLIC_API_URL" for e in frontend_changes)
        
        # Backend should receive JWT_SECRET change
        backend_changes = [e for e in change_events if e[0] == "backend"]
        assert any(e[1] == "JWT_SECRET" for e in backend_changes)
