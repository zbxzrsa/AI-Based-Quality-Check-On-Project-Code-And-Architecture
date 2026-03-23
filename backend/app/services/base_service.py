"""
Base service class with common patterns.

This module provides a base class for services following the DRY principle.
"""
from typing import Optional
import httpx
from abc import ABC


class BaseHTTPService(ABC):
    """
    Base class for services that use HTTP clients.
    
    Provides:
    - HTTP client management
    - Context manager support
    - Automatic cleanup
    """
    
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        """
        Initialize service with HTTP client.
        
        Args:
            http_client: Optional HTTP client (creates new one if not provided)
        """
        self._http_client = http_client
        self._owns_client = http_client is None
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self) -> None:
        """Close HTTP client if owned by this service."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.close()
        return False


class BaseService(ABC):
    """
    Base class for services without HTTP clients.
    
    Provides:
    - Context manager support
    - Common initialization patterns
    """
    
    def __init__(self):
        """Initialize base service."""
        pass
    
    async def close(self) -> None:
        """Override in subclass if cleanup needed."""
        pass
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.close()
        return False
