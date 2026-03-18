"""
Dependency Injection Container

This module implements a simple DI container for managing service dependencies.
遵循依赖倒置原则 (DIP)，高层模块不依赖低层模块，而是依赖抽象接口。
"""
from typing import Type, TypeVar, Dict, Any, Optional, Callable
from functools import lru_cache

from app.domain.repositories import (
    IUserRepository,
    IProjectRepository,
    IPullRequestRepository,
    ICodeReviewRepository,
)
from app.domain.services import (
    IGitHubService,
    ILLMService,
    ICacheService,
    IGraphService,
)

T = TypeVar("T")


class DIContainer:
    """
    Simple dependency injection container.
    
    Usage:
        # Register implementations
        container.register(IGitHubService, GitHubService)
        container.register(ILLMService, OpenAIProvider)
        
        # Resolve dependencies
        github_service = container.resolve(IGitHubService)
    """
    
    def __init__(self):
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def register(
        self,
        interface: Type[T],
        implementation: Type[T],
        singleton: bool = True,
    ) -> None:
        """
        Register a service implementation.
        
        Args:
            interface: Abstract interface (e.g., IGitHubService)
            implementation: Concrete implementation class
            singleton: If True, return same instance every time
        """
        self._services[interface] = implementation
        if singleton:
            self._singletons[interface] = None
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Register a pre-created instance (useful for testing).
        """
        self._services[interface] = lambda: instance
        self._singletons[interface] = instance
    
    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[[], T],
        singleton: bool = False,
    ) -> None:
        """
        Register a factory function for creating instances.
        
        Args:
            interface: Abstract interface
            factory: Callable that returns an instance
            singleton: If True, cache the created instance
        """
        self._services[interface] = factory
        if singleton:
            self._singletons[interface] = None
    
    def resolve(self, interface: Type[T], **kwargs) -> T:
        """
        Resolve a dependency.
        
        Args:
            interface: Abstract interface to resolve
            **kwargs: Additional arguments to pass to constructor
            
        Returns:
            Instance of the registered implementation
            
        Raises:
            KeyError: If interface is not registered
        """
        if interface not in self._services:
            raise KeyError(f"No implementation registered for {interface}")
        
        # Check for singleton
        if interface in self._singletons and self._singletons[interface] is not None:
            return self._singletons[interface]
        
        # Create instance
        factory = self._services[interface]
        instance = factory(**kwargs)
        
        # Cache singleton
        if interface in self._singletons:
            self._singletons[interface] = instance
        
        return instance
    
    def clear_singletons(self) -> None:
        """Clear all cached singleton instances (useful for testing)."""
        for key in self._singletons:
            self._singletons[key] = None


@lru_cache()
def get_container() -> DIContainer:
    """
    Get the global DI container instance.
    
    This function uses lru_cache to ensure the same container
    is used throughout the application lifecycle.
    """
    container = DIContainer()
    _register_default_services(container)
    return container


def _register_default_services(container: DIContainer) -> None:
    """
    Register default service implementations.
    
    In a real application, these would be imported from infrastructure layer.
    """
    # Repository implementations (placeholder - would be imported from infrastructure)
    # container.register(IUserRepository, PostgreSQLUserRepository)
    # container.register(IProjectRepository, PostgreSQLProjectRepository)
    
    # External service implementations (placeholder)
    # container.register(IGitHubService, GitHubService)
    # container.register(ILLMService, OpenAIProvider)
    # container.register(ICacheService, RedisCacheService)
    # container.register(IGraphService, Neo4jGraphService)
    pass


def reset_container() -> None:
    """Reset the container (useful for testing)."""
    get_container.cache_clear()
