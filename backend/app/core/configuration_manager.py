"""
Unified Configuration Management System

This module implements a centralized configuration management system that consolidates
all environment variables from multiple sources (.env, frontend/.env.local, backend/.env, etc.)
into a hierarchical configuration system with validation, type checking, and hot reloading.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


logger = logging.getLogger(__name__)


class ConfigurationSource(Enum):
    """Configuration source types with precedence order (higher = more priority)"""
    GLOBAL = 1          # Root .env file
    ENVIRONMENT = 2     # Environment-specific files (.env.development, etc.)
    SERVICE = 3         # Service-specific files (frontend/.env.local, backend/.env)
    RUNTIME = 4         # Runtime overrides (environment variables, CLI args)


@dataclass
class ConfigurationEntry:
    """Represents a single configuration entry with metadata"""
    key: str
    value: Any
    source: ConfigurationSource
    source_file: Optional[str] = None
    is_secret: bool = False
    validation_rules: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    last_updated: float = field(default_factory=time.time)


@dataclass
class ConfigurationConflict:
    """Represents a configuration conflict between sources"""
    key: str
    conflicts: List[ConfigurationEntry]
    resolved_value: Any
    resolution_reason: str


@dataclass
class ServiceConfig:
    """Service-specific configuration subset"""
    service_name: str
    config: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    required_keys: Set[str] = field(default_factory=set)
    optional_keys: Set[str] = field(default_factory=set)


class ConfigurationChangeEvent:
    """Event fired when configuration changes"""
    def __init__(self, key: str, old_value: Any, new_value: Any, source: ConfigurationSource):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source
        self.timestamp = time.time()


class ConfigurationValidator:
    """Validates configuration values and types"""
    
    @staticmethod
    def validate_port(value: Any) -> int:
        """Validate port number"""
        try:
            port = int(value)
            if not (1 <= port <= 65535):
                raise ValueError(f"Port must be between 1 and 65535, got {port}")
            return port
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid port value: {value}") from e
    
    @staticmethod
    def validate_url(value: Any) -> str:
        """Validate URL format"""
        if not isinstance(value, str):
            raise ValueError(f"URL must be a string, got {type(value)}")
        
        from urllib.parse import urlparse
        try:
            parsed = urlparse(value)
            if not parsed.scheme or not (parsed.netloc or parsed.path):
                raise ValueError(f"Invalid URL format: {value}")
            return value
        except Exception as e:
            raise ValueError(f"Invalid URL: {value}") from e
    
    @staticmethod
    def validate_secret(value: Any, min_length: int = 32) -> str:
        """Validate secret/password strength"""
        if not isinstance(value, str):
            raise ValueError(f"Secret must be a string, got {type(value)}")
        
        if len(value) < min_length:
            raise ValueError(f"Secret must be at least {min_length} characters, got {len(value)}")
        
        return value
    
    @staticmethod
    def validate_database_url(value: Any) -> str:
        """Validate database connection URL"""
        if not isinstance(value, str):
            raise ValueError(f"Database URL must be a string, got {type(value)}")
        
        # Basic validation for common database URL patterns
        valid_schemes = ['postgresql', 'postgresql+asyncpg', 'redis', 'bolt', 'neo4j']
        
        try:
            parsed = urlparse(value)
            if parsed.scheme not in valid_schemes:
                raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
            return value
        except Exception as e:
            raise ValueError(f"Invalid database URL: {value}") from e


class ConfigurationFileWatcher(FileSystemEventHandler):
    """Watches configuration files for changes"""
    
    def __init__(self, config_manager: 'ConfigurationManager'):
        self.config_manager = config_manager
        self.debounce_time = 1.0  # 1 second debounce
        self.pending_changes = {}
        self.timer_lock = threading.Lock()
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix in ['.env', '.local'] or file_path.name.startswith('.env'):
            logger.info(f"Configuration file changed: {file_path}")
            self._debounce_reload(str(file_path))
    
    def _debounce_reload(self, file_path: str):
        """Debounce file reload to avoid multiple rapid reloads"""
        with self.timer_lock:
            # Cancel existing timer for this file
            if file_path in self.pending_changes:
                self.pending_changes[file_path].cancel()
            
            # Schedule new reload
            timer = threading.Timer(
                self.debounce_time,
                lambda: self.config_manager._reload_configuration_file(file_path)
            )
            self.pending_changes[file_path] = timer
            timer.start()


class ConfigurationManager:
    """
    Centralized Configuration Manager
    
    Implements hierarchical configuration loading from multiple sources with:
    - Configuration validation and type checking
    - Precedence rules for conflicting variables
    - Service-specific configuration generation
    - Hot reloading capabilities
    - Configuration change propagation
    
    Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """
        Initialize Configuration Manager
        
        Args:
            root_path: Root path of the project (defaults to current working directory)
        """
        self.root_path = root_path or Path.cwd()
        self.configurations: Dict[str, ConfigurationEntry] = {}
        self.conflicts: List[ConfigurationConflict] = []
        self.change_listeners: List[Callable[[ConfigurationChangeEvent], None]] = []
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.validator = ConfigurationValidator()
        self.file_watcher: Optional[Observer] = None
        self.watch_enabled = False
        self._lock = threading.RLock()
        
        # Define secret keys that should be masked in logs
        self.secret_keys = {
            'JWT_SECRET', 'SECRET_KEY', 'SESSION_SECRET', 'POSTGRES_PASSWORD',
            'NEO4J_PASSWORD', 'REDIS_PASSWORD', 'GITHUB_TOKEN', 'GITHUB_WEBHOOK_SECRET',
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OAUTH_CLIENT_SECRET'
        }
        
        # Define validation rules for common configuration keys
        self.validation_rules = {
            'POSTGRES_PORT': {'validator': 'port', 'required': True},
            'REDIS_PORT': {'validator': 'port', 'required': True},
            'FRONTEND_PORT': {'validator': 'port', 'required': False, 'default': 3000},
            'BACKEND_PORT': {'validator': 'port', 'required': False, 'default': 8000},
            'JWT_SECRET': {'validator': 'secret', 'min_length': 32, 'required': True},
            'SECRET_KEY': {'validator': 'secret', 'min_length': 32, 'required': True},
            'POSTGRES_PASSWORD': {'validator': 'secret', 'min_length': 8, 'required': True},
            'NEO4J_PASSWORD': {'validator': 'secret', 'min_length': 8, 'required': True},
            'NEXT_PUBLIC_API_URL': {'validator': 'url', 'required': True},
            'NEO4J_URI': {'validator': 'database_url', 'required': True},
            'DATABASE_URL': {'validator': 'database_url', 'required': False},
            'REDIS_URL': {'validator': 'database_url', 'required': False},
        }
        
        logger.info(f"Configuration Manager initialized with root path: {self.root_path}")
    
    def load_configuration(self, environment: str = "development") -> Dict[str, Any]:
        """
        Load configuration from all sources with hierarchical precedence
        
        Args:
            environment: Target environment (development, staging, production)
            
        Returns:
            Consolidated configuration dictionary
            
        Validates Requirements: 1.1, 1.2
        """
        logger.info(f"Loading configuration for environment: {environment}")
        
        with self._lock:
            # Clear existing configuration
            self.configurations.clear()
            self.conflicts.clear()
            
            # Load configurations in precedence order (lowest to highest priority)
            self._load_global_config()
            self._load_environment_config(environment)
            self._load_service_configs()
            self._load_runtime_config()
            
            # Resolve conflicts and apply precedence rules
            self._resolve_conflicts()
            
            # Validate configuration
            validation_errors = self._validate_configuration()
            if validation_errors:
                logger.error(f"Configuration validation failed: {validation_errors}")
                raise ValueError(f"Configuration validation failed: {validation_errors}")
            
            # Generate final configuration dictionary
            final_config = {key: entry.value for key, entry in self.configurations.items()}
            
            logger.info(f"Configuration loaded successfully with {len(final_config)} entries")
            return final_config
    
    def _load_global_config(self):
        """Load global configuration from root .env file"""
        global_env_path = self.root_path / ".env"
        if global_env_path.exists():
            logger.debug(f"Loading global config from: {global_env_path}")
            self._load_env_file(global_env_path, ConfigurationSource.GLOBAL)
    
    def _load_environment_config(self, environment: str):
        """Load environment-specific configuration"""
        env_files = [
            self.root_path / f".env.{environment}",
            self.root_path / f".env.{environment}.local",
        ]
        
        for env_file in env_files:
            if env_file.exists():
                logger.debug(f"Loading environment config from: {env_file}")
                self._load_env_file(env_file, ConfigurationSource.ENVIRONMENT)
    
    def _load_service_configs(self):
        """Load service-specific configurations"""
        service_configs = [
            ("frontend", self.root_path / "frontend" / ".env.local"),
            ("frontend", self.root_path / "frontend" / ".env"),
            ("backend", self.root_path / "backend" / ".env"),
            ("services", self.root_path / "services" / ".env"),
        ]
        
        for service_name, config_path in service_configs:
            if config_path.exists():
                logger.debug(f"Loading {service_name} config from: {config_path}")
                self._load_env_file(config_path, ConfigurationSource.SERVICE)
    
    def _load_runtime_config(self):
        """Load runtime configuration from environment variables"""
        logger.debug("Loading runtime configuration from environment variables")
        
        for key, value in os.environ.items():
            # Skip empty values
            if not value:
                continue
            
            # Create configuration entry
            entry = ConfigurationEntry(
                key=key,
                value=value,
                source=ConfigurationSource.RUNTIME,
                source_file="environment",
                is_secret=key in self.secret_keys
            )
            
            # Check for conflicts
            if key in self.configurations:
                existing_entry = self.configurations[key]
                if existing_entry.value != value:
                    logger.debug(f"Runtime override for {key}: {self._mask_secret(key, existing_entry.value)} -> {self._mask_secret(key, value)}")
            
            self.configurations[key] = entry
    
    def _load_env_file(self, file_path: Path, source: ConfigurationSource):
        """Load configuration from a .env file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Skip empty values
                        if not value:
                            continue
                        
                        # Create configuration entry
                        entry = ConfigurationEntry(
                            key=key,
                            value=value,
                            source=source,
                            source_file=str(file_path),
                            is_secret=key in self.secret_keys,
                            validation_rules=self.validation_rules.get(key)
                        )
                        
                        # Check for conflicts
                        if key in self.configurations:
                            existing_entry = self.configurations[key]
                            if existing_entry.value != value:
                                logger.debug(f"Configuration conflict for {key}: {self._mask_secret(key, existing_entry.value)} ({existing_entry.source.name}) vs {self._mask_secret(key, value)} ({source.name})")
                        
                        self.configurations[key] = entry
                        
        except Exception as e:
            logger.error(f"Error loading configuration file {file_path}: {e}")
            raise
    
    def _resolve_conflicts(self):
        """Resolve configuration conflicts using precedence rules"""
        logger.debug("Resolving configuration conflicts")
        
        # Group configurations by key to find conflicts
        key_groups: Dict[str, List[ConfigurationEntry]] = {}
        for entry in self.configurations.values():
            if entry.key not in key_groups:
                key_groups[entry.key] = []
            key_groups[entry.key].append(entry)
        
        # Resolve conflicts for keys with multiple values
        for key, entries in key_groups.items():
            if len(entries) > 1:
                # Sort by source precedence (higher precedence wins)
                entries.sort(key=lambda e: e.source.value, reverse=True)
                
                # The first entry (highest precedence) wins
                winner = entries[0]
                
                # Create conflict record
                conflict = ConfigurationConflict(
                    key=key,
                    conflicts=entries,
                    resolved_value=winner.value,
                    resolution_reason=f"Precedence rule: {winner.source.name} > others"
                )
                self.conflicts.append(conflict)
                
                # Update configuration with winner
                self.configurations[key] = winner
                
                logger.debug(f"Resolved conflict for {key}: chose {self._mask_secret(key, winner.value)} from {winner.source.name}")
    
    def _validate_configuration(self) -> List[str]:
        """
        Validate configuration values and types
        
        Returns:
            List of validation errors
            
        Validates Requirements: 1.3
        """
        logger.debug("Validating configuration")
        errors = []
        
        for key, entry in self.configurations.items():
            if entry.validation_rules:
                try:
                    validator_name = entry.validation_rules.get('validator')
                    if validator_name:
                        validator_method = getattr(self.validator, f'validate_{validator_name}', None)
                        if validator_method:
                            # Apply validation
                            if validator_name == 'secret':
                                min_length = entry.validation_rules.get('min_length', 32)
                                validated_value = validator_method(entry.value, min_length)
                            else:
                                validated_value = validator_method(entry.value)
                            
                            # Update entry with validated value
                            entry.value = validated_value
                        else:
                            logger.warning(f"Unknown validator: {validator_name} for key {key}")
                
                except ValueError as e:
                    error_msg = f"Validation failed for {key}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        # Check for required keys
        required_keys = {key for key, rules in self.validation_rules.items() if rules.get('required', False)}
        missing_keys = required_keys - set(self.configurations.keys())
        
        for missing_key in missing_keys:
            error_msg = f"Required configuration key missing: {missing_key}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return errors
    
    def get_service_config(self, service_name: str, required_keys: Optional[Set[str]] = None, optional_keys: Optional[Set[str]] = None) -> ServiceConfig:
        """
        Generate service-specific configuration subset
        
        Args:
            service_name: Name of the service
            required_keys: Set of required configuration keys for this service
            optional_keys: Set of optional configuration keys for this service
            
        Returns:
            ServiceConfig with filtered configuration
            
        Validates Requirements: 1.4
        """
        logger.debug(f"Generating service config for: {service_name}")
        
        with self._lock:
            # Define service-specific key patterns
            service_patterns = {
                'frontend': {
                    'prefixes': ['NEXT_', 'NEXTAUTH_', 'NODE_ENV'],
                    'keys': {'NEXT_PUBLIC_API_URL', 'BACKEND_URL', 'FRONTEND_PORT'}
                },
                'backend': {
                    'prefixes': ['POSTGRES_', 'NEO4J_', 'REDIS_', 'JWT_', 'SECRET_', 'CELERY_'],
                    'keys': {'DATABASE_URL', 'REDIS_URL', 'BACKEND_PORT', 'ENVIRONMENT', 'DEBUG', 'LOG_LEVEL'}
                },
                'api-gateway': {
                    'prefixes': ['JWT_', 'CORS_', 'RATE_LIMIT_'],
                    'keys': {'PORT', 'NODE_ENV', 'REDIS_URL'}
                }
            }
            
            # Get service-specific patterns
            patterns = service_patterns.get(service_name, {'prefixes': [], 'keys': set()})
            
            # Filter configuration for this service
            service_config = {}
            
            # Add keys matching prefixes
            for key, entry in self.configurations.items():
                should_include = False
                
                # Check prefixes
                for prefix in patterns['prefixes']:
                    if key.startswith(prefix):
                        should_include = True
                        break
                
                # Check specific keys
                if key in patterns['keys']:
                    should_include = True
                
                # Check required/optional keys
                if required_keys and key in required_keys:
                    should_include = True
                if optional_keys and key in optional_keys:
                    should_include = True
                
                if should_include:
                    service_config[key] = entry.value
            
            # Create ServiceConfig object
            config = ServiceConfig(
                service_name=service_name,
                config=service_config,
                required_keys=required_keys or set(),
                optional_keys=optional_keys or set()
            )
            
            # Cache service config
            self.service_configs[service_name] = config
            
            logger.debug(f"Generated service config for {service_name} with {len(service_config)} keys")
            return config
    
    def update_configuration(self, updates: Dict[str, Any], source: ConfigurationSource = ConfigurationSource.RUNTIME) -> None:
        """
        Update configuration values and propagate changes
        
        Args:
            updates: Dictionary of key-value pairs to update
            source: Source of the updates
            
        Validates Requirements: 1.5
        """
        logger.info(f"Updating configuration with {len(updates)} changes from {source.name}")
        
        with self._lock:
            change_events = []
            
            for key, new_value in updates.items():
                old_value = self.configurations.get(key)
                old_val = old_value.value if old_value else None
                
                # Create new configuration entry
                entry = ConfigurationEntry(
                    key=key,
                    value=new_value,
                    source=source,
                    source_file="runtime_update",
                    is_secret=key in self.secret_keys,
                    validation_rules=self.validation_rules.get(key)
                )
                
                # Validate new value
                if entry.validation_rules:
                    try:
                        validator_name = entry.validation_rules.get('validator')
                        if validator_name:
                            validator_method = getattr(self.validator, f'validate_{validator_name}', None)
                            if validator_method:
                                if validator_name == 'secret':
                                    min_length = entry.validation_rules.get('min_length', 32)
                                    entry.value = validator_method(entry.value, min_length)
                                else:
                                    entry.value = validator_method(entry.value)
                    except ValueError as e:
                        logger.error(f"Validation failed for {key}: {e}")
                        raise
                
                # Update configuration
                self.configurations[key] = entry
                
                # Create change event
                change_event = ConfigurationChangeEvent(key, old_val, new_value, source)
                change_events.append(change_event)
                
                logger.debug(f"Updated {key}: {self._mask_secret(key, old_val)} -> {self._mask_secret(key, new_value)}")
            
            # Propagate changes to listeners
            self._propagate_changes(change_events)
    
    def _propagate_changes(self, change_events: List[ConfigurationChangeEvent]):
        """Propagate configuration changes to registered listeners"""
        logger.debug(f"Propagating {len(change_events)} configuration changes")
        
        for event in change_events:
            for listener in self.change_listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.error(f"Error in configuration change listener: {e}")
    
    def add_change_listener(self, listener: Callable[[ConfigurationChangeEvent], None]):
        """Add a configuration change listener"""
        self.change_listeners.append(listener)
        logger.debug(f"Added configuration change listener: {listener.__name__}")
    
    def remove_change_listener(self, listener: Callable[[ConfigurationChangeEvent], None]):
        """Remove a configuration change listener"""
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)
            logger.debug(f"Removed configuration change listener: {listener.__name__}")
    
    def enable_hot_reloading(self):
        """
        Enable hot reloading of configuration files
        
        Validates Requirements: 1.5
        """
        if self.watch_enabled:
            logger.warning("Hot reloading is already enabled")
            return
        
        logger.info("Enabling configuration hot reloading")
        
        # Create file watcher
        self.file_watcher = Observer()
        event_handler = ConfigurationFileWatcher(self)
        
        # Watch root directory for .env files
        self.file_watcher.schedule(event_handler, str(self.root_path), recursive=False)
        
        # Watch service directories
        service_dirs = [
            self.root_path / "frontend",
            self.root_path / "backend",
            self.root_path / "services"
        ]
        
        for service_dir in service_dirs:
            if service_dir.exists():
                self.file_watcher.schedule(event_handler, str(service_dir), recursive=False)
        
        # Start watching
        self.file_watcher.start()
        self.watch_enabled = True
        
        logger.info("Configuration hot reloading enabled")
    
    def disable_hot_reloading(self):
        """Disable hot reloading of configuration files"""
        if not self.watch_enabled:
            return
        
        logger.info("Disabling configuration hot reloading")
        
        if self.file_watcher:
            self.file_watcher.stop()
            self.file_watcher.join()
            self.file_watcher = None
        
        self.watch_enabled = False
        logger.info("Configuration hot reloading disabled")
    
    def _reload_configuration_file(self, file_path: str):
        """Reload configuration from a specific file"""
        logger.info(f"Reloading configuration from: {file_path}")
        
        try:
            # Determine source type based on file path
            path = Path(file_path)
            
            if path.name == ".env":
                source = ConfigurationSource.GLOBAL
            elif "frontend" in str(path):
                source = ConfigurationSource.SERVICE
            elif "backend" in str(path):
                source = ConfigurationSource.SERVICE
            else:
                source = ConfigurationSource.ENVIRONMENT
            
            # Load the file
            old_config = dict(self.configurations)
            self._load_env_file(path, source)
            
            # Find changes
            changes = {}
            for key, entry in self.configurations.items():
                if key not in old_config or old_config[key].value != entry.value:
                    changes[key] = entry.value
            
            if changes:
                logger.info(f"Configuration reloaded with {len(changes)} changes")
                
                # Create change events
                change_events = []
                for key, new_value in changes.items():
                    old_value = old_config.get(key)
                    old_val = old_value.value if old_value else None
                    
                    change_event = ConfigurationChangeEvent(key, old_val, new_value, source)
                    change_events.append(change_event)
                
                # Propagate changes
                self._propagate_changes(change_events)
            else:
                logger.debug("No configuration changes detected")
                
        except Exception as e:
            logger.error(f"Error reloading configuration file {file_path}: {e}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        with self._lock:
            return {
                'total_entries': len(self.configurations),
                'conflicts_resolved': len(self.conflicts),
                'sources': {
                    source.name: len([e for e in self.configurations.values() if e.source == source])
                    for source in ConfigurationSource
                },
                'secret_keys': len([e for e in self.configurations.values() if e.is_secret]),
                'service_configs': list(self.service_configs.keys()),
                'hot_reloading_enabled': self.watch_enabled
            }
    
    def export_configuration(self, service_name: Optional[str] = None, mask_secrets: bool = True) -> Dict[str, Any]:
        """
        Export configuration for external use
        
        Args:
            service_name: If specified, export only service-specific configuration
            mask_secrets: Whether to mask secret values
            
        Returns:
            Configuration dictionary
        """
        with self._lock:
            if service_name and service_name in self.service_configs:
                config = self.service_configs[service_name].config
            else:
                config = {key: entry.value for key, entry in self.configurations.items()}
            
            if mask_secrets:
                masked_config = {}
                for key, value in config.items():
                    if key in self.secret_keys:
                        masked_config[key] = self._mask_secret(key, value)
                    else:
                        masked_config[key] = value
                return masked_config
            
            return config
    
    def _mask_secret(self, key: str, value: Any) -> str:
        """Mask secret values for logging"""
        if key in self.secret_keys and isinstance(value, str) and len(value) > 4:
            return f"{value[:2]}***{value[-2:]}"
        return str(value)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.disable_hot_reloading()


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_configuration_manager() -> ConfigurationManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def initialize_configuration(environment: str = "development", enable_hot_reload: bool = False) -> Dict[str, Any]:
    """
    Initialize the global configuration system
    
    Args:
        environment: Target environment
        enable_hot_reload: Whether to enable hot reloading
        
    Returns:
        Loaded configuration dictionary
    """
    config_manager = get_configuration_manager()
    config = config_manager.load_configuration(environment)
    
    if enable_hot_reload:
        config_manager.enable_hot_reloading()
    
    return config