"""
Unit Tests for Configuration Manager

Tests the centralized configuration management system including:
- Hierarchical configuration loading
- Configuration validation and type checking
- Precedence rules for conflicting variables
- Service-specific configuration generation
- Hot reloading capabilities

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.core.configuration_manager import (
    ConfigurationManager,
    ConfigurationSource,
    ConfigurationEntry,
    ConfigurationConflict,
    ConfigurationChangeEvent,
    ConfigurationValidator,
    ServiceConfig,
    get_configuration_manager,
)
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Constants for testing to avoid hard-coded credentials in literal strings
TEST_PASSWORD = get_test_password("test_password_long")
TEST_SECRET = "test_secret_value_32_chars_long_12345"
TEST_JWT_SECRET = get_test_jwt_secret()


class TestConfigurationValidator:
    """Test configuration validation functionality"""
    
    def test_validate_port_valid(self):
        """Test port validation with valid values"""
        validator = ConfigurationValidator()
        
        assert validator.validate_port("8000") == 8000
        assert validator.validate_port(3000) == 3000
        assert validator.validate_port("1") == 1
        assert validator.validate_port("65535") == 65535
    
    def test_validate_port_invalid(self):
        """Test port validation with invalid values"""
        validator = ConfigurationValidator()
        
        with pytest.raises(ValueError, match="Invalid port value"):
            validator.validate_port("0")
        
        with pytest.raises(ValueError, match="Invalid port value"):
            validator.validate_port("65536")
        
        with pytest.raises(ValueError, match="Invalid port value"):
            validator.validate_port("not_a_number")
    
    def test_validate_url_valid(self):
        """Test URL validation with valid values"""
        validator = ConfigurationValidator()
        
        valid_urls = [
            "http://localhost:3000",
            "https://api.example.com",
            "bolt://neo4j:7687",
            "redis://localhost:6379"
        ]
        
        for url in valid_urls:
            assert validator.validate_url(url) == url
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid values"""
        validator = ConfigurationValidator()
        
        invalid_urls = [
            "not_a_url",
            "://missing_scheme",
            123,  # Not a string
            ""
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                validator.validate_url(url)
    
    def test_validate_secret_valid(self):
        """Test secret validation with valid values"""
        validator = ConfigurationValidator()
        
        secret = "a" * 32  # 32 character secret
        assert validator.validate_secret(secret) == secret
        
        long_secret = "a" * 64  # Longer secret
        assert validator.validate_secret(long_secret) == long_secret
    
    def test_validate_secret_invalid(self):
        """Test secret validation with invalid values"""
        validator = ConfigurationValidator()
        
        with pytest.raises(ValueError, match="Secret must be at least 32 characters"):
            validator.validate_secret("short")
        
        with pytest.raises(ValueError, match="Secret must be a string"):
            validator.validate_secret(123)
    
    def test_validate_database_url_valid(self):
        """Test database URL validation with valid values"""
        validator = ConfigurationValidator()
        
        valid_urls = [
            f"postgresql://user:{TEST_PASSWORD}@localhost:5432/db",
            "redis://localhost:6379/0",
            f"bolt://neo4j:{TEST_PASSWORD}@localhost:7687",
            "neo4j://localhost:7687"
        ]
        
        for url in valid_urls:
            assert validator.validate_database_url(url) == url
    
    def test_validate_database_url_invalid(self):
        """Test database URL validation with invalid values"""
        validator = ConfigurationValidator()
        
        with pytest.raises(ValueError, match="Invalid database URL"):
            validator.validate_database_url("mysql://localhost:3306/db")
        
        with pytest.raises(ValueError, match="Database URL must be a string"):
            validator.validate_database_url(123)


class TestConfigurationManager:
    """Test Configuration Manager functionality"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with config files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create directory structure
            (project_path / "frontend").mkdir()
            (project_path / "backend").mkdir()
            (project_path / "services").mkdir()
            
            # Create root .env file
            (project_path / ".env").write_text("""
# Global configuration
JWT_SECRET={TEST_JWT_SECRET}
SECRET_KEY={TEST_SECRET}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=test_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD={TEST_PASSWORD}
REDIS_HOST=localhost
REDIS_PORT=6379
ENVIRONMENT=development
""".strip())
            
            # Create frontend .env.local
            (project_path / "frontend" / ".env.local").write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXTAUTH_URL=http://localhost:3000
FRONTEND_PORT=3000
""".strip())
            
            # Create backend .env
            (project_path / "backend" / ".env").write_text("""
POSTGRES_PASSWORD={TEST_PASSWORD}_backend
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD={TEST_PASSWORD}_neo4j
BACKEND_PORT=8000
""".strip())
            
            yield project_path
    
    def test_initialization(self, temp_project_dir):
        """Test Configuration Manager initialization"""
        config_manager = ConfigurationManager(temp_project_dir)
        
        assert config_manager.root_path == temp_project_dir
        assert len(config_manager.configurations) == 0
        assert len(config_manager.conflicts) == 0
        assert not config_manager.watch_enabled
    
    def test_load_configuration_basic(self, temp_project_dir):
        """Test basic configuration loading (Requirement 1.1)"""
        config_manager = ConfigurationManager(temp_project_dir)
        config = config_manager.load_configuration("development")
        
        # Check that configuration was loaded
        assert len(config) > 0
        assert "JWT_SECRET" in config
        assert "POSTGRES_HOST" in config
        assert "NEXT_PUBLIC_API_URL" in config
        
        # Check values from different sources
        assert config["POSTGRES_HOST"] == "localhost"
        assert config["NEXT_PUBLIC_API_URL"] == "http://localhost:8000/api/v1"
    
    def test_hierarchical_loading(self, temp_project_dir):
        """Test hierarchical configuration loading (Requirement 1.1)"""
        config_manager = ConfigurationManager(temp_project_dir)
        config = config_manager.load_configuration("development")
        
        # Check that service-specific config overrides global config
        # POSTGRES_PASSWORD should be from backend/.env (service-specific)
        # not from root .env (global)
        assert config["POSTGRES_PASSWORD"] == f"{TEST_PASSWORD}_backend"
    
    def test_precedence_rules(self, temp_project_dir):
        """Test precedence rules for conflicting variables (Requirement 1.2)"""
        config_manager = ConfigurationManager(temp_project_dir)
        
        # Set environment variable to override file-based config
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "runtime_override_password"}):
            config = config_manager.load_configuration("development")
            
            # Runtime environment variable should win
            assert config["POSTGRES_PASSWORD"] == "runtime_override_password"
            
            # Check that conflict was recorded
            assert len(config_manager.conflicts) > 0
            postgres_conflicts = [c for c in config_manager.conflicts if c.key == "POSTGRES_PASSWORD"]
            assert len(postgres_conflicts) > 0
    
    def test_configuration_validation(self, temp_project_dir):
        """Test configuration validation and type checking (Requirement 1.3)"""
        config_manager = ConfigurationManager(temp_project_dir)
        
        # This should succeed with valid configuration
        config = config_manager.load_configuration("development")
        assert config is not None
        
        # Test validation failure with invalid port
        (temp_project_dir / "test.env").write_text("POSTGRES_PORT=invalid_port")
        config_manager._load_env_file(temp_project_dir / "test.env", ConfigurationSource.GLOBAL)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager._validate_configuration()
    
    def test_service_specific_configuration(self, temp_project_dir):
        """Test service-specific configuration generation (Requirement 1.4)"""
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        # Get frontend-specific configuration
        frontend_config = config_manager.get_service_config("frontend")
        
        assert frontend_config.service_name == "frontend"
        assert "NEXT_PUBLIC_API_URL" in frontend_config.config
        assert "NEXTAUTH_URL" in frontend_config.config
        
        # Backend-specific keys should not be in frontend config
        assert "POSTGRES_PASSWORD" not in frontend_config.config
        
        # Get backend-specific configuration
        backend_config = config_manager.get_service_config("backend")
        
        assert backend_config.service_name == "backend"
        assert "POSTGRES_PASSWORD" in backend_config.config
        assert "NEO4J_URI" in backend_config.config
        
        # Frontend-specific keys should not be in backend config
        assert "NEXTAUTH_URL" not in backend_config.config
    
    def test_configuration_updates(self, temp_project_dir):
        """Test configuration updates and change propagation (Requirement 1.5)"""
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        # Add change listener
        change_events = []
        def change_listener(event: ConfigurationChangeEvent):
            change_events.append(event)
        
        config_manager.add_change_listener(change_listener)
        
        # Update configuration
        updates = {
            "NEW_KEY": "new_value",
            "POSTGRES_HOST": "updated_host"
        }
        
        config_manager.update_configuration(updates)
        
        # Check that configuration was updated
        assert config_manager.configurations["NEW_KEY"].value == "new_value"
        assert config_manager.configurations["POSTGRES_HOST"].value == "updated_host"
        
        # Check that change events were fired
        assert len(change_events) == 2
        
        # Check event details
        new_key_event = next(e for e in change_events if e.key == "NEW_KEY")
        assert new_key_event.old_value is None
        assert new_key_event.new_value == "new_value"
        
        postgres_event = next(e for e in change_events if e.key == "POSTGRES_HOST")
        assert postgres_event.old_value == "localhost"
        assert postgres_event.new_value == "updated_host"
    
    def test_hot_reloading_enable_disable(self, temp_project_dir):
        """Test hot reloading enable/disable functionality"""
        config_manager = ConfigurationManager(temp_project_dir)
        
        # Initially disabled
        assert not config_manager.watch_enabled
        assert config_manager.file_watcher is None
        
        # Enable hot reloading
        config_manager.enable_hot_reloading()
        assert config_manager.watch_enabled
        assert config_manager.file_watcher is not None
        
        # Disable hot reloading
        config_manager.disable_hot_reloading()
        assert not config_manager.watch_enabled
        assert config_manager.file_watcher is None
    
    def test_configuration_summary(self, temp_project_dir):
        """Test configuration summary generation"""
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        summary = config_manager.get_configuration_summary()
        
        assert "total_entries" in summary
        assert "conflicts_resolved" in summary
        assert "sources" in summary
        assert "secret_keys" in summary
        assert "service_configs" in summary
        assert "hot_reloading_enabled" in summary
        
        assert summary["total_entries"] > 0
        assert isinstance(summary["sources"], dict)
    
    def test_export_configuration(self, temp_project_dir):
        """Test configuration export functionality"""
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        # Export all configuration with secrets masked
        masked_config = config_manager.export_configuration(mask_secrets=True)
        
        assert "JWT_SECRET" in masked_config
        assert "***" in masked_config["JWT_SECRET"]  # Should be masked
        
        # Export all configuration without masking
        unmasked_config = config_manager.export_configuration(mask_secrets=False)
        
        assert "JWT_SECRET" in unmasked_config
        assert "***" not in unmasked_config["JWT_SECRET"]  # Should not be masked
    
    def test_secret_masking(self, temp_project_dir):
        """Test secret value masking in logs"""
        config_manager = ConfigurationManager(temp_project_dir)
        
        # Test masking of secret values
        secret_value = "very_secret_password_123"
        masked = config_manager._mask_secret("POSTGRES_PASSWORD", secret_value)
        
        assert masked.startswith("ve")
        assert masked.endswith("23")
        assert "***" in masked
        assert len(masked) < len(secret_value)
        
        # Test non-secret values are not masked
        non_secret = config_manager._mask_secret("POSTGRES_HOST", "localhost")
        assert non_secret == "localhost"
    
    def test_context_manager(self, temp_project_dir):
        """Test Configuration Manager as context manager"""
        with ConfigurationManager(temp_project_dir) as config_manager:
            config_manager.enable_hot_reloading()
            assert config_manager.watch_enabled
        
        # Should be disabled after context exit
        assert not config_manager.watch_enabled
    
    def test_missing_required_configuration(self, temp_project_dir):
        """Test handling of missing required configuration"""
        # Create config file without required keys
        (temp_project_dir / ".env").write_text("OPTIONAL_KEY=value")
        
        config_manager = ConfigurationManager(temp_project_dir)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager.load_configuration("development")
    
    def test_configuration_file_reload(self, temp_project_dir):
        """Test configuration file reloading"""
        config_manager = ConfigurationManager(temp_project_dir)
        config_manager.load_configuration("development")
        
        # Add change listener
        change_events = []
        def change_listener(event: ConfigurationChangeEvent):
            change_events.append(event)
        
        config_manager.add_change_listener(change_listener)
        
        # Modify configuration file
        env_file = temp_project_dir / ".env"
        original_content = env_file.read_text()
        new_content = original_content + "\nNEW_RUNTIME_KEY=new_runtime_value"
        env_file.write_text(new_content)
        
        # Manually trigger reload (simulating file watcher)
        config_manager._reload_configuration_file(str(env_file))
        
        # Check that new configuration was loaded
        assert "NEW_RUNTIME_KEY" in config_manager.configurations
        assert config_manager.configurations["NEW_RUNTIME_KEY"].value == "new_runtime_value"
        
        # Check that change event was fired
        assert len(change_events) > 0
        new_key_events = [e for e in change_events if e.key == "NEW_RUNTIME_KEY"]
        assert len(new_key_events) == 1


class TestGlobalConfigurationManager:
    """Test global configuration manager functions"""
    
    def test_get_configuration_manager_singleton(self):
        """Test that get_configuration_manager returns singleton"""
        manager1 = get_configuration_manager()
        manager2 = get_configuration_manager()
        
        assert manager1 is manager2
    
    def test_initialize_configuration(self):
        """Test configuration initialization function"""
        with patch('app.core.configuration_manager.get_configuration_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.load_configuration.return_value = {"test": "config"}
            mock_get_manager.return_value = mock_manager
            
            config = initialize_configuration("development", enable_hot_reload=True)
            
            assert config == {"test": "config"}
            mock_manager.load_configuration.assert_called_once_with("development")
            mock_manager.enable_hot_reloading.assert_called_once()


class TestConfigurationChangeEvent:
    """Test configuration change event functionality"""
    
    def test_change_event_creation(self):
        """Test configuration change event creation"""
        event = ConfigurationChangeEvent(
            key="TEST_KEY",
            old_value="old",
            new_value="new",
            source=ConfigurationSource.RUNTIME
        )
        
        assert event.key == "TEST_KEY"
        assert event.old_value == "old"
        assert event.new_value == "new"
        assert event.source == ConfigurationSource.RUNTIME
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0


class TestServiceConfig:
    """Test service configuration functionality"""
    
    def test_service_config_creation(self):
        """Test service configuration creation"""
        config = ServiceConfig(
            service_name="test_service",
            config={"key1": "value1", "key2": "value2"},
            dependencies=["dep1", "dep2"],
            required_keys={"key1"},
            optional_keys={"key2"}
        )
        
        assert config.service_name == "test_service"
        assert config.config == {"key1": "value1", "key2": "value2"}
        assert config.dependencies == ["dep1", "dep2"]
        assert config.required_keys == {"key1"}
        assert config.optional_keys == {"key2"}


class TestConfigurationConflict:
    """Test configuration conflict handling"""
    
    def test_conflict_creation(self):
        """Test configuration conflict creation"""
        entry1 = ConfigurationEntry(
            key="TEST_KEY",
            value="value1",
            source=ConfigurationSource.GLOBAL
        )
        
        entry2 = ConfigurationEntry(
            key="TEST_KEY",
            value="value2",
            source=ConfigurationSource.SERVICE
        )
        
        conflict = ConfigurationConflict(
            key="TEST_KEY",
            conflicts=[entry1, entry2],
            resolved_value="value2",
            resolution_reason="Service config takes precedence"
        )
        
        assert conflict.key == "TEST_KEY"
        assert len(conflict.conflicts) == 2
        assert conflict.resolved_value == "value2"
        assert "precedence" in conflict.resolution_reason.lower()


class TestConfigurationIntegration:
    """Integration tests for configuration management"""
    
    @pytest.fixture
    def complex_project_dir(self):
        """Create a complex project directory for integration testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create directory structure
            (project_path / "frontend").mkdir()
            (project_path / "backend").mkdir()
            (project_path / "services" / "api-gateway").mkdir(parents=True)
            
            # Create multiple environment files with conflicts
            (project_path / ".env").write_text("""
JWT_SECRET={TEST_JWT_SECRET}
SECRET_KEY={TEST_SECRET}
POSTGRES_HOST=global_host
POSTGRES_PORT=5432
POSTGRES_DB=global_db
POSTGRES_USER=global_user
POSTGRES_PASSWORD={TEST_PASSWORD}_global
REDIS_HOST=global_redis
REDIS_PORT=6379
NEO4J_URI=bolt://global_neo4j:7687
NEO4J_USER=global_neo4j_user
NEO4J_PASSWORD={TEST_PASSWORD}_global_neo4j
ENVIRONMENT=development
""".strip())
            
            (project_path / ".env.development").write_text("""
POSTGRES_HOST=dev_host
DEBUG=true
LOG_LEVEL=DEBUG
""".strip())
            
            (project_path / "frontend" / ".env.local").write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET={TEST_SECRET}_frontend
NODE_ENV=development
""".strip())
            
            (project_path / "backend" / ".env").write_text("""
POSTGRES_HOST=backend_host
POSTGRES_PASSWORD={TEST_PASSWORD}_backend_specific
NEO4J_PASSWORD={TEST_PASSWORD}_backend_neo4j
BACKEND_PORT=8000
SECRET_KEY={TEST_SECRET}_backend
""".strip())
            
            yield project_path
    
    def test_full_configuration_loading_with_conflicts(self, complex_project_dir):
        """Test full configuration loading with multiple conflicts"""
        config_manager = ConfigurationManager(complex_project_dir)
        config = config_manager.load_configuration("development")
        
        # Check that all sources were loaded
        assert len(config) > 0
        
        # Check precedence resolution
        # POSTGRES_HOST should be from backend/.env (service level)
        assert config["POSTGRES_HOST"] == "backend_host"
        
        # POSTGRES_PASSWORD should be from backend/.env (service level)
        assert config["POSTGRES_PASSWORD"] == f"{TEST_PASSWORD}_backend_specific"
        
        # DEBUG should be from .env.development (environment level)
        assert config["DEBUG"] == "true"
        
        # NEXT_PUBLIC_API_URL should be from frontend/.env.local (service level)
        assert config["NEXT_PUBLIC_API_URL"] == "http://localhost:8000/api/v1"
        
        # Check that conflicts were recorded
        assert len(config_manager.conflicts) > 0
        
        # Find POSTGRES_HOST conflict
        postgres_conflicts = [c for c in config_manager.conflicts if c.key == "POSTGRES_HOST"]
        assert len(postgres_conflicts) > 0
        
        postgres_conflict = postgres_conflicts[0]
        assert postgres_conflict.resolved_value == "backend_host"
        assert "precedence" in postgres_conflict.resolution_reason.lower()
    
    def test_service_configuration_isolation(self, complex_project_dir):
        """Test that service configurations are properly isolated"""
        config_manager = ConfigurationManager(complex_project_dir)
        config_manager.load_configuration("development")
        
        # Get service-specific configurations
        frontend_config = config_manager.get_service_config("frontend")
        backend_config = config_manager.get_service_config("backend")
        
        # Frontend should have frontend-specific keys
        assert "NEXT_PUBLIC_API_URL" in frontend_config.config
        assert "NEXTAUTH_URL" in frontend_config.config
        assert "NODE_ENV" in frontend_config.config
        
        # Frontend should not have backend-specific secrets
        assert "POSTGRES_PASSWORD" not in frontend_config.config
        assert "SECRET_KEY" not in frontend_config.config
        
        # Backend should have backend-specific keys
        assert "POSTGRES_PASSWORD" in backend_config.config
        assert "SECRET_KEY" in backend_config.config
        assert "NEO4J_PASSWORD" in backend_config.config
        
        # Backend should not have frontend-specific keys
        assert "NEXTAUTH_URL" not in backend_config.config
        assert "NEXTAUTH_SECRET" not in backend_config.config
    
    def test_configuration_validation_comprehensive(self, complex_project_dir):
        """Test comprehensive configuration validation"""
        config_manager = ConfigurationManager(complex_project_dir)
        
        # Should load successfully with valid configuration
        config = config_manager.load_configuration("development")
        assert config is not None
        
        # Test validation of specific types
        assert isinstance(config["POSTGRES_PORT"], int)
        assert config["POSTGRES_PORT"] == 5432
        
        # Test URL validation
        assert config["NEXT_PUBLIC_API_URL"].startswith("http")
        
        # Test secret validation (should not raise errors)
        assert len(config["JWT_SECRET"]) >= 32
        assert len(config["SECRET_KEY"]) >= 32