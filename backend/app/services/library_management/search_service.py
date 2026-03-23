"""
Search Service for Library Management

This service provides search functionality for libraries across different package registries.
It supports searching npm, PyPI, and other registries with unified result formatting.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Union
from urllib.parse import quote

import httpx
from app.schemas.library import LibrarySearchResult
from app.models.library import RegistryType


logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Base exception for search errors"""
    pass


class NetworkSearchError(SearchError):
    """Network-related errors during search"""
    pass


class InvalidSearchQueryError(SearchError):
    """Invalid search query error"""
    pass


class AsyncCircuitBreaker:
    """
    Async circuit breaker to prevent cascading failures during search operations.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
    
    async def call(self, func, *args, **kwargs):
        """Execute async function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"Search circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info(f"Search circuit breaker recovered, state: CLOSED")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                f"Search circuit breaker opened after {self.failure_count} failures",
                extra={'failure_count': self.failure_count}
            )


class NPMSearchClient:
    """Client for npm registry search API"""
    
    BASE_URL = "https://registry.npmjs.org"
    SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
    
    def __init__(self, http_client: httpx.AsyncClient, circuit_breaker: AsyncCircuitBreaker):
        self.http_client = http_client
        self.circuit_breaker = circuit_breaker
    
    async def search(self, query: str, limit: int = 20) -> List[LibrarySearchResult]:
        """
        Search npm registry for packages
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of LibrarySearchResult objects
            
        Raises:
            NetworkSearchError: If network request fails
            InvalidSearchQueryError: If query is invalid
        """
        if not query or not query.strip():
            raise InvalidSearchQueryError("Search query cannot be empty")
        
        query = query.strip()
        
        # npm search API parameters
        params = {
            "text": query,
            "size": min(limit, 250),  # npm API max is 250
            "from": 0,
            "quality": 0.65,
            "popularity": 0.98,
            "maintenance": 0.5
        }
        
        try:
            response = await self.circuit_breaker.call(
                self._make_search_request, params
            )
            
            if response.status_code != 200:
                raise NetworkSearchError(f"npm search API returned status {response.status_code}")
            
            try:
                data = response.json()
            except Exception as e:
                raise NetworkSearchError(f"Invalid JSON response from npm search API: {e}")
            
            return self._parse_search_results(data, limit)
            
        except httpx.RequestError as e:
            raise NetworkSearchError(f"Network error accessing npm search API: {e}")
        except Exception as e:
            if isinstance(e, (NetworkSearchError, InvalidSearchQueryError)):
                raise
            raise NetworkSearchError(f"Unexpected error during npm search: {e}")
    
    async def _make_search_request(self, params: Dict[str, Any]) -> httpx.Response:
        """Make HTTP search request with timeout"""
        return await self.http_client.get(
            self.SEARCH_URL,
            params=params,
            timeout=30.0
        )
    
    def _parse_search_results(self, data: Dict[str, Any], limit: int) -> List[LibrarySearchResult]:
        """
        Parse npm search API response into LibrarySearchResult objects
        
        Args:
            data: Raw response data from npm search API
            limit: Maximum number of results to return
            
        Returns:
            List of LibrarySearchResult objects
        """
        results = []
        
        try:
            objects = data.get("objects", [])
            
            for item in objects[:limit]:
                package = item.get("package", {})
                
                name = package.get("name", "")
                if not name:
                    continue
                
                description = package.get("description", "")
                version = package.get("version", "")
                
                # Extract download count from score object if available
                downloads = None
                score = item.get("score", {})
                detail = score.get("detail", {})
                if "popularity" in detail:
                    # npm popularity is a normalized score, convert to approximate downloads
                    popularity = detail["popularity"]
                    # This is a rough approximation - in reality you'd need the actual download stats
                    downloads = int(popularity * 1000000) if popularity > 0 else None
                
                # Create URI for the package
                uri = f"npm:{name}@{version}"
                
                result = LibrarySearchResult(
                    name=name,
                    description=description,
                    version=version,
                    downloads=downloads,
                    uri=uri,
                    registry_type=RegistryType.NPM
                )
                
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error parsing npm search results: {e}")
            # Return partial results if parsing fails partway through
        
        return results


class PyPISearchClient:
    """Client for PyPI search functionality"""
    
    # PyPI doesn't have a built-in search API anymore, so we'll use a third-party service
    # or implement a simple name-based search using the JSON API
    BASE_URL = "https://pypi.org/pypi"
    
    def __init__(self, http_client: httpx.AsyncClient, circuit_breaker: AsyncCircuitBreaker):
        self.http_client = http_client
        self.circuit_breaker = circuit_breaker
    
    async def search(self, query: str, limit: int = 20) -> List[LibrarySearchResult]:
        """
        Search PyPI for packages
        
        Note: PyPI removed their search API, so this implementation uses a simplified
        approach that tries exact name matches and common variations.
        In a production system, you might want to integrate with a third-party
        search service or maintain your own search index.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of LibrarySearchResult objects
            
        Raises:
            NetworkSearchError: If network request fails
            InvalidSearchQueryError: If query is invalid
        """
        if not query or not query.strip():
            raise InvalidSearchQueryError("Search query cannot be empty")
        
        query = query.strip().lower()
        results = []
        
        # Try exact match first
        try:
            exact_result = await self._try_package_name(query)
            if exact_result:
                results.append(exact_result)
        except Exception as e:
            logger.debug(f"Exact match failed for '{query}': {e}")
        
        # Try common variations if we don't have enough results
        if len(results) < limit:
            variations = self._generate_name_variations(query)
            
            for variation in variations[:limit - len(results)]:
                try:
                    result = await self._try_package_name(variation)
                    if result and result.name not in [r.name for r in results]:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Variation '{variation}' failed: {e}")
                    continue
        
        return results[:limit]
    
    def _generate_name_variations(self, query: str) -> List[str]:
        """
        Generate common package name variations for PyPI search
        
        Args:
            query: Original search query
            
        Returns:
            List of name variations to try
        """
        variations = []
        
        # Common PyPI package naming patterns
        variations.extend([
            query.replace("-", "_"),  # hyphens to underscores
            query.replace("_", "-"),  # underscores to hyphens
            f"python-{query}",        # python- prefix
            f"py-{query}",           # py- prefix
            f"{query}-python",       # -python suffix
            f"{query}2",             # version suffix
            f"{query}3",             # version suffix
        ])
        
        # Remove duplicates and original query
        variations = list(set(variations))
        if query in variations:
            variations.remove(query)
        
        return variations
    
    async def _try_package_name(self, package_name: str) -> Optional[LibrarySearchResult]:
        """
        Try to fetch package information for a specific name
        
        Args:
            package_name: Package name to try
            
        Returns:
            LibrarySearchResult if package exists, None otherwise
        """
        url = f"{self.BASE_URL}/{quote(package_name, safe='')}/json"
        
        try:
            response = await self.circuit_breaker.call(
                self._make_request, url
            )
            
            if response.status_code == 404:
                return None
            
            if response.status_code != 200:
                logger.debug(f"PyPI returned status {response.status_code} for {package_name}")
                return None
            
            try:
                data = response.json()
            except Exception as e:
                logger.debug(f"Invalid JSON response for {package_name}: {e}")
                return None
            
            return self._parse_package_info(data)
            
        except httpx.RequestError as e:
            logger.debug(f"Network error for {package_name}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error for {package_name}: {e}")
            return None
    
    async def _make_request(self, url: str) -> httpx.Response:
        """Make HTTP request with timeout"""
        return await self.http_client.get(url, timeout=30.0)
    
    def _parse_package_info(self, data: Dict[str, Any]) -> Optional[LibrarySearchResult]:
        """
        Parse PyPI package info into LibrarySearchResult
        
        Args:
            data: Raw package data from PyPI JSON API
            
        Returns:
            LibrarySearchResult object or None if parsing fails
        """
        try:
            info = data.get("info", {})
            
            name = info.get("name", "")
            if not name:
                return None
            
            description = info.get("summary", "")
            version = info.get("version", "")
            
            # PyPI doesn't provide download counts in the JSON API
            # You'd need to use the PyPI Stats API or similar service
            downloads = None
            
            # Create URI for the package
            uri = f"pypi:{name}=={version}"
            
            return LibrarySearchResult(
                name=name,
                description=description,
                version=version,
                downloads=downloads,
                uri=uri,
                registry_type=RegistryType.PYPI
            )
            
        except Exception as e:
            logger.debug(f"Error parsing PyPI package info: {e}")
            return None


class SearchService:
    """
    Main search service for library management
    
    This service provides unified search functionality across multiple package registries
    including npm, PyPI, and potentially others. It handles circuit breaking, rate limiting,
    and result aggregation.
    """
    
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        """
        Initialize SearchService
        
        Args:
            http_client: Optional HTTP client (creates new one if None)
        """
        self.http_client = http_client or httpx.AsyncClient()
        self._own_client = http_client is None
        
        # Create circuit breakers for each registry
        self.npm_circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=(NetworkSearchError, httpx.RequestError)
        )
        
        self.pypi_circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=(NetworkSearchError, httpx.RequestError)
        )
        
        # Initialize search clients
        self.search_clients = {
            RegistryType.NPM: NPMSearchClient(self.http_client, self.npm_circuit_breaker),
            RegistryType.PYPI: PyPISearchClient(self.http_client, self.pypi_circuit_breaker),
        }
    
    async def search(
        self,
        query: str,
        registry_type: Optional[RegistryType] = None,
        limit: int = 20
    ) -> List[LibrarySearchResult]:
        """
        Search for libraries across registries
        
        Args:
            query: Search query string (package name or keywords)
            registry_type: Optional registry filter (searches all if None)
            limit: Maximum number of results to return (default: 20)
            
        Returns:
            List of LibrarySearchResult objects
            
        Raises:
            SearchError: If search fails for any reason
            InvalidSearchQueryError: If query is invalid
            
        Examples:
            >>> service = SearchService()
            >>> results = await service.search("react")
            >>> len(results)
            20
            >>> results[0].name
            'react'
            >>> results[0].registry_type
            RegistryType.NPM
        """
        try:
            logger.info(f"Searching libraries: query='{query}', registry={registry_type}, limit={limit}")
            
            # Validate query
            if not query or not query.strip():
                raise InvalidSearchQueryError("Search query cannot be empty or whitespace")
            
            query = query.strip()
            
            # Validate limit
            if limit <= 0:
                raise InvalidSearchQueryError("Limit must be greater than 0")
            
            limit = min(limit, 100)  # Cap at 100 to prevent abuse
            
            # Determine which registries to search
            registries_to_search = []
            if registry_type:
                if registry_type in self.search_clients:
                    registries_to_search = [registry_type]
                else:
                    raise InvalidSearchQueryError(f"Unsupported registry type: {registry_type}")
            else:
                registries_to_search = list(self.search_clients.keys())
            
            # Search each registry concurrently
            search_tasks = []
            for registry in registries_to_search:
                client = self.search_clients[registry]
                # Distribute limit across registries
                registry_limit = limit if len(registries_to_search) == 1 else limit // len(registries_to_search) + 1
                task = self._search_registry(client, registry, query, registry_limit)
                search_tasks.append(task)
            
            # Wait for all searches to complete
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Aggregate results
            all_results = []
            for i, result in enumerate(search_results):
                registry = registries_to_search[i]
                
                if isinstance(result, Exception):
                    logger.warning(f"Search failed for {registry.value}: {result}")
                    continue
                
                if isinstance(result, list):
                    all_results.extend(result)
                    logger.debug(f"Found {len(result)} results from {registry.value}")
            
            # Sort results by relevance (exact matches first, then by name)
            all_results.sort(key=lambda r: (
                0 if r.name.lower() == query.lower() else 1,  # Exact matches first
                r.name.lower()  # Then alphabetical
            ))
            
            # Limit final results
            final_results = all_results[:limit]
            
            logger.info(f"Search completed: found {len(final_results)} results for '{query}'")
            
            return final_results
            
        except InvalidSearchQueryError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise SearchError(f"Library search failed: {str(e)}")
    
    async def _search_registry(
        self,
        client: Union[NPMSearchClient, PyPISearchClient],
        registry: RegistryType,
        query: str,
        limit: int
    ) -> List[LibrarySearchResult]:
        """
        Search a specific registry with error handling
        
        Args:
            client: Search client for the registry
            registry: Registry type being searched
            query: Search query
            limit: Maximum results for this registry
            
        Returns:
            List of search results from this registry
        """
        try:
            results = await client.search(query, limit)
            logger.debug(f"Registry {registry.value} returned {len(results)} results")
            return results
        except (NetworkSearchError, InvalidSearchQueryError) as e:
            logger.warning(f"Search error in {registry.value}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching {registry.value}: {e}")
            return []
    
    async def close(self):
        """Close HTTP client if we own it"""
        if self._own_client and self.http_client:
            await self.http_client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()