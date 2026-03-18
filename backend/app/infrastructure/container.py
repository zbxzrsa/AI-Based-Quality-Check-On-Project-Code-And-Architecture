"""
Dependency Injection Container with Auto-Wiring

This module implements a DI container that supports auto-wiring
and constructor injection for Clean Architecture.
"""
from typing import Type, TypeVar, Dict, Callable, Optional, Any, get_type_hints
from dataclasses import dataclass
from functools import lru_cache
import inspect

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ServiceDescriptor:
    """Descriptor for a registered service"""
    implementation: Type
    factory: Optional[Callable] = None
    singleton: bool = True
    instance: Optional[Any] = None


class DIContainer:
    """
    Dependency Injection Container with auto-wiring support.
    
    Features:
    - Singleton and transient services
    - Auto-wiring based on type hints
    - Factory functions
    - Dependency resolution
    
    Usage:
        # Register services
        container = DIContainer()
        container.register(IGitHubService, GitHubService)
        
        # Resolve with auto-wiring
        service = container.resolve(GitHubService)
        
        # Or use as dependency
        async def get_github(
            github_service: IGitHubService = Depends(container)
        ):
            ...
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register(
        self,
        interface: Type[T],
        implementation: Type[T] = None,
        singleton: bool = True,
    ) -> None:
        """
        Register a service.
        
        Args:
            interface: Abstract interface (e.g., IGitHubService)
            implementation: Concrete implementation class (if different from interface)
            singleton: If True, return same instance every time
        """
        impl = implementation or interface
        self._services[interface] = ServiceDescriptor(
            implementation=impl,
            singleton=singleton,
        )
        logger.debug(f"Registered service: {interface} -> {impl} (singleton={singleton})")
    
    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """
        Register a pre-created singleton instance.
        
        Args:
            interface: Interface type
            instance: Pre-created instance
        """
        self._services[interface] = ServiceDescriptor(
            implementation=type(instance),
            singleton=True,
            instance=instance,
        )
        logger.debug(f"Registered singleton instance: {interface}")
    
    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[[], T],
        singleton: bool = False,
    ) -> None:
        """
        Register a factory function.
        
        Args:
            interface: Interface type
            factory: Callable that returns an instance
            singleton: If True, cache the created instance
        """
        self._services[interface] = ServiceDescriptor(
            implementation=type(factory()),
            factory=factory,
            singleton=singleton,
        )
        logger.debug(f"Registered factory: {interface}")
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Alias for register_singleton"""
        self.register_singleton(interface, instance)
    
    def resolve(self, interface: Type[T], **kwargs) -> T:
        """
        Resolve a dependency with auto-wiring.
        
        Args:
            interface: Interface to resolve
            **kwargs: Additional arguments to pass to constructor
            
        Returns:
            Instance of the registered implementation
            
        Raises:
            KeyError: If interface is not registered
        """
        if interface not in self._services:
            raise KeyError(f"No implementation registered for {interface}")
        
        descriptor = self._services[interface]
        
        # Return cached singleton
        if descriptor.singleton and descriptor.instance is not None:
            return descriptor.instance
        
        # Use factory if registered
        if descriptor.factory:
            instance = descriptor.factory()
        else:
            # Auto-wire constructor
            instance = self._auto_wire(descriptor.implementation, **kwargs)
        
        # Cache singleton
        if descriptor.singleton:
            descriptor.instance = instance
        
        return instance
    
    def _auto_wire(self, cls: Type[T], **kwargs) -> T:
        """
        Auto-wire constructor arguments based on type hints.
        
        Args:
            cls: Class to instantiate
            **kwargs: Additional arguments
            
        Returns:
            Instantiated class
        """
        try:
            hints = get_type_hints(cls.__init__)
        except Exception:
            hints = {}
        
        deps = {}
        sig = inspect.signature(cls.__init__)
        
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            
            if param_name in kwargs:
                deps[param_name] = kwargs[param_name]
            elif param_name in hints:
                param_type = hints[param_name]
                try:
                    deps[param_name] = self.resolve(param_type)
                except KeyError:
                    if param.default is inspect.Parameter.empty:
                        raise ValueError(
                            f"Cannot resolve dependency '{param_name}' for {cls}"
                        )
            elif param.default is not inspect.Parameter.empty:
                continue
            else:
                raise ValueError(f"Cannot resolve dependency '{param_name}' for {cls}")
        
        return cls(**deps)
    
    def create_scope(self) -> "DIScope":
        """Create a new dependency scope"""
        return DIScope(self)
    
    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._factories.clear()


class DIScope:
    """Dependency injection scope for request-level services"""
    
    def __init__(self, container: DIContainer):
        self._container = container
        self._scoped_instances: Dict[Type, Any] = {}
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve a service within this scope"""
        if interface not in self._scoped_instances:
            self._scoped_instances[interface] = self._container.resolve(interface)
        return self._scoped_instances[interface]
    
    def clear(self) -> None:
        """Clear scoped instances"""
        self._scoped_instances.clear()


class Depends:
    """
    Dependency injection helper for FastAPI.
    
    Usage:
        async def get_github(
            github: IGitHubService = Depends(container, IGitHubService)
        ):
            return github
    """
    
    def __init__(
        self,
        container: DIContainer = None,
        interface: Type = None,
        **kwargs
    ):
        self.container = container
        self.interface = interface
        self.kwargs = kwargs
    
    def __call__(self) -> Any:
        if self.container and self.interface:
            return self.container.resolve(self.interface, **self.kwargs)
        return None


@lru_cache()
def get_container() -> DIContainer:
    """
    Get the global DI container instance.
    
    Usage:
        container = get_container()
        container.register(IGitHubService, GitHubService)
        
        # In FastAPI:
        @app.get("/repos")
        async def get_repos(
            github: IGitHubService = Depends(lambda: get_container().resolve(IGitHubService))
        ):
            ...
    """
    container = DIContainer()
    _register_default_services(container)
    return container


def _register_default_services(container: DIContainer) -> None:
    """
    Register default service implementations.
    
    In production, import and register actual implementations:
    
        from app.infrastructure.external.github import GitHubService
        from app.infrastructure.external.cache import RedisCacheService
        from app.infrastructure.graph import Neo4jGraphService
        
        container.register(IGitHubService, GitHubService)
        container.register(ICacheService, RedisCacheService)
        container.register(IGraphService, Neo4jGraphService)
    """
    # Placeholder registrations - will be replaced with actual implementations
    logger.info("DI Container initialized with default services")


def reset_container() -> None:
    """Reset the container (useful for testing)"""
    get_container.cache_clear()
