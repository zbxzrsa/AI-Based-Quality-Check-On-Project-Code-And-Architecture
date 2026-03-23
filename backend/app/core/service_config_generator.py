"""
Service Configuration Generator

This module provides service-specific configuration generation, change propagation,
and hot reloading capabilities for the unified configuration management system.

Validates Requirements: 1.4, 1.5
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum

from app.core.configuration_manager import (
    ConfigurationManager,
    ConfigurationChangeEvent,
    ServiceConfig,
    get_configuration_manager
)

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Supported service types"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    API_GATEWAY = "api-gateway"
    AUTH_SERVICE = "auth-service"
    DATABASE = "database"
    CACHE = "cache"
    MONITORING = "monitoring"


@dataclass
class ServiceDefinition:
    """Definition of a service and its configuration requirements"""
    name: str
    service_type: ServiceType
    required_keys: Set[str] = field(default_factory=set)
    optional_keys: Set[str] = field(default_factory=set)
    key_prefixes: List[str] = field(default_factory=list)
    config_file_path: Optional[Path] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    health_check_url: Optional[str] = None
    restart_command: Optional[str] = None


@dataclass
class ConfigurationUpdate:
    """Represents a configuration update for a service"""
    service_name: str
    updated_keys: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    propagation_status: str = "pending"  # pending, success, failed
    error_message: Optional[str] = None


class ServiceConfigGenerator:
    """
    Service Configuration Generator
    
    Provides service-specific configuration generation with:
    - Configuration subsetting logic for individual services
    - Configuration change propagation mechanism
    - Hot reloading capabilities
    - Service dependency management
    
    Validates Requirements: 1.4, 1.5
    """
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """
        Initialize Service Configuration Generator
        
        Args:
            config_manager: Configuration manager instance (uses global if None)
        """
        self.config_manager = config_manager or get_configuration_manager()
        self.service_definitions: Dict[str, ServiceDefinition] = {}
        self.active_services: Dict[str, ServiceConfig] = {}
        self.update_queue: List[ConfigurationUpdate] = []
        self.propagation_callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        
        # Register for configuration changes
        self.config_manager.add_change_listener(self._on_configuration_change)
        
        # Initialize default service definitions
        self._initialize_default_services()
        
        logger.info("Service Configuration Generator initialized")
    
    def _initialize_default_services(self):
        """Initialize default service definitions"""
        # Frontend service
        self.register_service(ServiceDefinition(
            name="frontend",
            service_type=ServiceType.FRONTEND,
            required_keys={
                "NEXT_PUBLIC_API_URL", "NEXTAUTH_URL"
            },
            optional_keys={
                "NEXTAUTH_SECRET", "NODE_ENV", "FRONTEND_PORT"
            },
            key_prefixes=["NEXT_", "NEXTAUTH_"],
            config_file_path=Path("frontend/.env.local"),
            dependencies=["backend"],
            health_check_url="http://localhost:3000/api/health"
        ))
        
        # Backend service
        self.register_service(ServiceDefinition(
            name="backend",
            service_type=ServiceType.BACKEND,
            required_keys={
                "JWT_SECRET", "SECRET_KEY", "POSTGRES_HOST", "POSTGRES_PORT",
                "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
                "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD",
                "REDIS_HOST", "REDIS_PORT"
            },
            optional_keys={
                "REDIS_PASSWORD", "BACKEND_PORT", "DEBUG", "LOG_LEVEL",
                "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
            },
            key_prefixes=["POSTGRES_", "NEO4J_", "REDIS_", "JWT_", "CELERY_"],
            config_file_path=Path("backend/.env"),
            dependencies=["database", "cache"],
            health_check_url="http://localhost:8000/health"
        ))
        
        # API Gateway service
        self.register_service(ServiceDefinition(
            name="api-gateway",
            service_type=ServiceType.API_GATEWAY,
            required_keys={
                "JWT_SECRET", "PORT"
            },
            optional_keys={
                "CORS_ALLOWED_ORIGINS", "RATE_LIMIT_PER_MINUTE", "NODE_ENV",
                "REDIS_URL", "AUTH_SERVICE_URL", "BACKEND_URL"
            },
            key_prefixes=["CORS_", "RATE_LIMIT_", "AUTH_", "CIRCUIT_BREAKER_"],
            dependencies=["auth-service", "backend"],
            health_check_url="http://localhost:3000/health"
        ))
        
        # Auth service
        self.register_service(ServiceDefinition(
            name="auth-service",
            service_type=ServiceType.AUTH_SERVICE,
            required_keys={
                "JWT_SECRET", "SESSION_SECRET", "DATABASE_URL"
            },
            optional_keys={
                "BCRYPT_ROUNDS", "JWT_EXPIRATION_HOURS", "OAUTH_CLIENT_ID",
                "OAUTH_CLIENT_SECRET", "SAML_CERT_PATH", "SAML_KEY_PATH"
            },
            key_prefixes=["JWT_", "OAUTH_", "SAML_"],
            dependencies=["database"],
            health_check_url="http://localhost:3001/health"
        ))
        
        logger.debug(f"Initialized {len(self.service_definitions)} default service definitions")
    
    def register_service(self, service_def: ServiceDefinition) -> None:
        """
        Register a service definition
        
        Args:
            service_def: Service definition to register
            
        Validates Requirements: 1.4
        """
        with self._lock:
            self.service_definitions[service_def.name] = service_def
            logger.info(f"Registered service: {service_def.name} ({service_def.service_type.value})")
    
    def unregister_service(self, service_name: str) -> None:
        """
        Unregister a service definition
        
        Args:
            service_name: Name of service to unregister
        """
        with self._lock:
            if service_name in self.service_definitions:
                del self.service_definitions[service_name]
                logger.info(f"Unregistered service: {service_name}")
            
            if service_name in self.active_services:
                del self.active_services[service_name]
    
    def generate_service_config(self, service_name: str, include_dependencies: bool = True) -> ServiceConfig:
        """
        Generate configuration for a specific service
        
        Args:
            service_name: Name of the service
            include_dependencies: Whether to include dependency configurations
            
        Returns:
            ServiceConfig with filtered configuration
            
        Validates Requirements: 1.4
        """
        logger.debug(f"Generating configuration for service: {service_name}")
        
        with self._lock:
            if service_name not in self.service_definitions:
                raise ValueError(f"Service not registered: {service_name}")
            
            service_def = self.service_definitions[service_name]
            
            # Get base service configuration from manager
            base_config = self.config_manager.get_service_config(
                service_name,
                required_keys=service_def.required_keys,
                optional_keys=service_def.optional_keys
            )
            
            # Add service-specific filtering
            filtered_config = self._filter_service_config(service_def, base_config.config)
            
            # Include dependency configurations if requested
            if include_dependencies:
                dep_configs = self._get_dependency_configs(service_def.dependencies)
                filtered_config.update(dep_configs)
            
            # Create enhanced service config
            service_config = ServiceConfig(
                service_name=service_name,
                config=filtered_config,
                dependencies=service_def.dependencies,
                required_keys=service_def.required_keys,
                optional_keys=service_def.optional_keys
            )
            
            # Cache the configuration
            self.active_services[service_name] = service_config
            
            logger.debug(f"Generated configuration for {service_name} with {len(filtered_config)} keys")
            return service_config
    
    def _filter_service_config(self, service_def: ServiceDefinition, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter configuration based on service definition"""
        filtered_config = {}
        
        # Add keys matching prefixes
        for key, value in base_config.items():
            should_include = False
            
            # Check prefixes
            for prefix in service_def.key_prefixes:
                if key.startswith(prefix):
                    should_include = True
                    break
            
            # Check required/optional keys
            if key in service_def.required_keys or key in service_def.optional_keys:
                should_include = True
            
            # Include service-type specific keys
            if self._is_service_type_key(service_def.service_type, key):
                should_include = True
            
            if should_include:
                filtered_config[key] = value
        
        return filtered_config
    
    def _is_service_type_key(self, service_type: ServiceType, key: str) -> bool:
        """Check if a key is relevant for a specific service type"""
        service_type_keys = {
            ServiceType.FRONTEND: {
                "NODE_ENV", "FRONTEND_PORT", "PUBLIC_URL", "BUILD_PATH"
            },
            ServiceType.BACKEND: {
                "BACKEND_PORT", "DEBUG", "LOG_LEVEL", "ENVIRONMENT",
                "DATABASE_URL", "REDIS_URL"
            },
            ServiceType.API_GATEWAY: {
                "PORT", "NODE_ENV", "TRUST_PROXY", "REQUEST_TIMEOUT"
            },
            ServiceType.AUTH_SERVICE: {
                "PORT", "SESSION_TIMEOUT", "TOKEN_EXPIRY"
            },
            ServiceType.DATABASE: {
                "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "CONNECTION_TIMEOUT"
            },
            ServiceType.CACHE: {
                "CACHE_TTL", "CACHE_MAX_SIZE", "EVICTION_POLICY"
            },
            ServiceType.MONITORING: {
                "METRICS_PORT", "HEALTH_CHECK_INTERVAL", "LOG_RETENTION"
            }
        }
        
        return key in service_type_keys.get(service_type, set())
    
    def _get_dependency_configs(self, dependencies: List[str]) -> Dict[str, Any]:
        """Get configuration for service dependencies"""
        dep_config = {}
        
        for dep_name in dependencies:
            if dep_name in self.service_definitions:
                dep_service_def = self.service_definitions[dep_name]
                
                # Add connection URLs and endpoints for dependencies
                if dep_service_def.service_type == ServiceType.DATABASE:
                    if "POSTGRES" in dep_name.upper():
                        dep_config["DATABASE_URL"] = self.config_manager.configurations.get("DATABASE_URL", {}).value
                    elif "NEO4J" in dep_name.upper():
                        dep_config["NEO4J_URL"] = self.config_manager.configurations.get("NEO4J_URI", {}).value
                
                elif dep_service_def.service_type == ServiceType.CACHE:
                    dep_config["REDIS_URL"] = self.config_manager.configurations.get("REDIS_URL", {}).value
                
                elif dep_service_def.health_check_url:
                    dep_config[f"{dep_name.upper().replace('-', '_')}_URL"] = dep_service_def.health_check_url
        
        return dep_config
    
    def generate_all_service_configs(self) -> Dict[str, ServiceConfig]:
        """
        Generate configurations for all registered services
        
        Returns:
            Dictionary mapping service names to their configurations
            
        Validates Requirements: 1.4
        """
        logger.info("Generating configurations for all services")
        
        all_configs = {}
        
        with self._lock:
            for service_name in self.service_definitions.keys():
                try:
                    config = self.generate_service_config(service_name)
                    all_configs[service_name] = config
                except Exception as e:
                    logger.error(f"Failed to generate config for {service_name}: {e}")
        
        logger.info(f"Generated configurations for {len(all_configs)} services")
        return all_configs
    
    def export_service_config(self, service_name: str, format: str = "env", mask_secrets: bool = True) -> str:
        """
        Export service configuration in specified format
        
        Args:
            service_name: Name of the service
            format: Export format ("env", "json", "yaml")
            mask_secrets: Whether to mask secret values
            
        Returns:
            Configuration in specified format
            
        Validates Requirements: 1.4
        """
        if service_name not in self.active_services:
            self.generate_service_config(service_name)
        
        service_config = self.active_services[service_name]
        config_data = service_config.config
        
        # Mask secrets if requested
        if mask_secrets:
            config_data = self._mask_secrets(config_data)
        
        if format.lower() == "env":
            return self._export_as_env(config_data)
        elif format.lower() == "json":
            return json.dumps(config_data, indent=2)
        elif format.lower() == "yaml":
            import yaml
            return yaml.dump(config_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_as_env(self, config_data: Dict[str, Any]) -> str:
        """Export configuration as .env format"""
        lines = []
        for key, value in sorted(config_data.items()):
            # Handle different value types
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, (int, float)):
                value = str(value)
            elif value is None:
                continue  # Skip None values
            
            # Quote values with spaces or special characters
            if isinstance(value, str) and (' ' in value or any(c in value for c in '!@#$%^&*()')):
                value = f'"{value}"'
            
            lines.append(f"{key}={value}")
        
        return "\n".join(lines)
    
    def _mask_secrets(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask secret values in configuration"""
        secret_keys = {
            'JWT_SECRET', 'SECRET_KEY', 'SESSION_SECRET', 'POSTGRES_PASSWORD',
            'NEO4J_PASSWORD', 'REDIS_PASSWORD', 'GITHUB_TOKEN', 'GITHUB_WEBHOOK_SECRET',
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OAUTH_CLIENT_SECRET', 'NEXTAUTH_SECRET'
        }
        
        masked_config = {}
        for key, value in config_data.items():
            if key in secret_keys and isinstance(value, str) and len(value) > 4:
                masked_config[key] = f"{value[:2]}***{value[-2:]}"
            else:
                masked_config[key] = value
        
        return masked_config
    
    def write_service_config_file(self, service_name: str, force: bool = False) -> bool:
        """
        Write service configuration to its config file
        
        Args:
            service_name: Name of the service
            force: Whether to overwrite existing files
            
        Returns:
            True if file was written successfully
            
        Validates Requirements: 1.4, 1.5
        """
        logger.info(f"Writing configuration file for service: {service_name}")
        
        if service_name not in self.service_definitions:
            logger.error(f"Service not registered: {service_name}")
            return False
        
        service_def = self.service_definitions[service_name]
        if not service_def.config_file_path:
            logger.warning(f"No config file path defined for service: {service_name}")
            return False
        
        config_file = Path(service_def.config_file_path)
        
        # Check if file exists and force is not set
        if config_file.exists() and not force:
            logger.warning(f"Config file exists and force=False: {config_file}")
            return False
        
        try:
            # Generate service configuration
            if service_name not in self.active_services:
                self.generate_service_config(service_name)
            
            # Export as .env format (don't mask secrets for actual config files)
            config_content = self.export_service_config(service_name, format="env", mask_secrets=False)
            
            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration file
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f"# Auto-generated configuration for {service_name}\n")
                f.write(f"# Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# DO NOT EDIT MANUALLY - Changes will be overwritten\n\n")
                f.write(config_content)
            
            logger.info(f"Successfully wrote config file: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write config file for {service_name}: {e}")
            return False
    
    def _on_configuration_change(self, event: ConfigurationChangeEvent) -> None:
        """
        Handle configuration change events
        
        Args:
            event: Configuration change event
            
        Validates Requirements: 1.5
        """
        logger.debug(f"Configuration change detected: {event.key}")
        
        # Find affected services
        affected_services = self._find_affected_services(event.key)
        
        if affected_services:
            logger.info(f"Configuration change affects services: {affected_services}")
            
            # Create update records
            for service_name in affected_services:
                update = ConfigurationUpdate(
                    service_name=service_name,
                    updated_keys={event.key: event.new_value}
                )
                self.update_queue.append(update)
            
            # Propagate changes
            self._propagate_changes(affected_services, event)
    
    def _find_affected_services(self, config_key: str) -> List[str]:
        """Find services affected by a configuration key change"""
        affected_services = []
        
        with self._lock:
            for service_name, service_def in self.service_definitions.items():
                # Check if key is required or optional for this service
                if config_key in service_def.required_keys or config_key in service_def.optional_keys:
                    affected_services.append(service_name)
                    continue
                
                # Check if key matches service prefixes
                for prefix in service_def.key_prefixes:
                    if config_key.startswith(prefix):
                        affected_services.append(service_name)
                        break
                
                # Check if key is relevant for service type
                if self._is_service_type_key(service_def.service_type, config_key):
                    affected_services.append(service_name)
        
        return affected_services
    
    def _propagate_changes(self, affected_services: List[str], event: ConfigurationChangeEvent) -> None:
        """
        Propagate configuration changes to affected services
        
        Args:
            affected_services: List of affected service names
            event: Configuration change event
            
        Validates Requirements: 1.5
        """
        logger.info(f"Propagating configuration changes to {len(affected_services)} services")
        
        for service_name in affected_services:
            try:
                # Regenerate service configuration
                self.generate_service_config(service_name)
                
                # Call registered callbacks
                if service_name in self.propagation_callbacks:
                    for callback in self.propagation_callbacks[service_name]:
                        try:
                            callback(service_name, event)
                        except Exception as e:
                            logger.error(f"Error in propagation callback for {service_name}: {e}")
                
                # Update propagation status
                for update in self.update_queue:
                    if update.service_name == service_name and update.propagation_status == "pending":
                        update.propagation_status = "success"
                
                logger.debug(f"Successfully propagated changes to {service_name}")
                
            except Exception as e:
                logger.error(f"Failed to propagate changes to {service_name}: {e}")
                
                # Update propagation status
                for update in self.update_queue:
                    if update.service_name == service_name and update.propagation_status == "pending":
                        update.propagation_status = "failed"
                        update.error_message = str(e)
    
    def add_propagation_callback(self, service_name: str, callback: Callable) -> None:
        """
        Add a callback for configuration change propagation
        
        Args:
            service_name: Name of the service
            callback: Callback function to call on configuration changes
            
        Validates Requirements: 1.5
        """
        if service_name not in self.propagation_callbacks:
            self.propagation_callbacks[service_name] = []
        
        self.propagation_callbacks[service_name].append(callback)
        logger.debug(f"Added propagation callback for {service_name}")
    
    def remove_propagation_callback(self, service_name: str, callback: Callable) -> None:
        """Remove a propagation callback"""
        if service_name in self.propagation_callbacks:
            if callback in self.propagation_callbacks[service_name]:
                self.propagation_callbacks[service_name].remove(callback)
                logger.debug(f"Removed propagation callback for {service_name}")
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """
        Get status information for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary with service status information
        """
        with self._lock:
            if service_name not in self.service_definitions:
                return {"error": f"Service not registered: {service_name}"}
            
            service_def = self.service_definitions[service_name]
            is_active = service_name in self.active_services
            
            # Get recent updates
            recent_updates = [
                update for update in self.update_queue[-10:]  # Last 10 updates
                if update.service_name == service_name
            ]
            
            return {
                "name": service_name,
                "type": service_def.service_type.value,
                "is_active": is_active,
                "dependencies": service_def.dependencies,
                "required_keys": list(service_def.required_keys),
                "optional_keys": list(service_def.optional_keys),
                "config_file_path": str(service_def.config_file_path) if service_def.config_file_path else None,
                "health_check_url": service_def.health_check_url,
                "recent_updates": len(recent_updates),
                "last_update": recent_updates[-1].timestamp if recent_updates else None
            }
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all registered services"""
        return {
            service_name: self.get_service_status(service_name)
            for service_name in self.service_definitions.keys()
        }
    
    def cleanup_update_queue(self, max_age_hours: int = 24) -> int:
        """
        Clean up old entries from the update queue
        
        Args:
            max_age_hours: Maximum age of updates to keep (in hours)
            
        Returns:
            Number of entries removed
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            original_count = len(self.update_queue)
            self.update_queue = [
                update for update in self.update_queue
                if update.timestamp > cutoff_time
            ]
            removed_count = original_count - len(self.update_queue)
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old update queue entries")
        
        return removed_count


# Global service configuration generator instance
_service_config_generator: Optional[ServiceConfigGenerator] = None


def get_service_config_generator() -> ServiceConfigGenerator:
    """Get the global service configuration generator instance"""
    global _service_config_generator
    if _service_config_generator is None:
        _service_config_generator = ServiceConfigGenerator()
    return _service_config_generator


def generate_service_configuration(service_name: str, include_dependencies: bool = True) -> ServiceConfig:
    """
    Generate configuration for a specific service
    
    Args:
        service_name: Name of the service
        include_dependencies: Whether to include dependency configurations
        
    Returns:
        ServiceConfig with filtered configuration
    """
    generator = get_service_config_generator()
    return generator.generate_service_config(service_name, include_dependencies)


def export_service_configuration(service_name: str, format: str = "env", output_file: Optional[Path] = None) -> str:
    """
    Export service configuration in specified format
    
    Args:
        service_name: Name of the service
        format: Export format ("env", "json", "yaml")
        output_file: Optional file path to write configuration
        
    Returns:
        Configuration in specified format
    """
    generator = get_service_config_generator()
    config_content = generator.export_service_config(service_name, format)
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        logger.info(f"Exported {service_name} configuration to {output_file}")
    
    return config_content