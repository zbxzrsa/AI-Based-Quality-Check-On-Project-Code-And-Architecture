"""
Metadata Fetcher Service for Library Management

This service fetches library metadata from various package registries including
npm, PyPI, and Maven Central. It provides a unified interface for retrieving
library information such as name, version, description, license, and dependencies.
"""

import logging
import time
from typing import Optional, Callable, Awaitable
from urllib.parse import quote

import httpx
from app.schemas.library import LibraryMetadata, Dependency
from app.models.library import RegistryType


logger = logging.getLogger(__name__)


class MetadataFetchError(Exception):
    """Base exception for metadata fetching errors"""
    pass


class NetworkError(MetadataFetchError):
    """Network-related errors during metadata fetching"""
    pass


class PackageNotFoundError(MetadataFetchError):
    """Package not found in registry"""
    pass


class InvalidResponseError(MetadataFetchError):
    """Invalid or malformed response from registry"""
    pass


class AsyncCircuitBreaker:
    """
    Async circuit breaker to prevent cascading failures.
    
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
    
    async def call(self, func: Callable[..., Awaitable], *args, **kwargs):
        """Execute async function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker entering HALF_OPEN state")
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
            logger.info(f"Circuit breaker recovered, state: CLOSED")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures",
                extra={'failure_count': self.failure_count}
            )

class NPMRegistryClient:
    """Client for npm registry API"""
    
    BASE_URL = "https://registry.npmjs.org"
    
    def __init__(self, http_client: httpx.AsyncClient, circuit_breaker: AsyncCircuitBreaker):
        self.http_client = http_client
        self.circuit_breaker = circuit_breaker
    
    async def get_package_info(self, package_name: str) -> dict:
        """
        Fetch package information from npm registry
        
        Args:
            package_name: Name of the npm package
            
        Returns:
            Package information dictionary
            
        Raises:
            NetworkError: If network request fails
            PackageNotFoundError: If package doesn't exist
            InvalidResponseError: If response is malformed
        """
        url = f"{self.BASE_URL}/{quote(package_name, safe='')}"
        
        try:
            response = await self.circuit_breaker.call(
                self._make_request, url
            )
            
            if response.status_code == 404:
                raise PackageNotFoundError(f"Package '{package_name}' not found in npm registry")
            
            if response.status_code != 200:
                raise NetworkError(f"npm registry returned status {response.status_code}")
            
            try:
                return response.json()
            except Exception as e:
                raise InvalidResponseError(f"Invalid JSON response from npm registry: {e}")
                
        except httpx.RequestError as e:
            raise NetworkError(f"Network error accessing npm registry: {e}")
        except Exception as e:
            if isinstance(e, (NetworkError, PackageNotFoundError, InvalidResponseError)):
                raise
            raise NetworkError(f"Unexpected error accessing npm registry: {e}")
    
    async def _make_request(self, url: str) -> httpx.Response:
        """Make HTTP request with timeout"""
        return await self.http_client.get(url, timeout=30.0)
    def extract_metadata(self, package_data: dict, version: Optional[str] = None) -> LibraryMetadata:
        """
        Extract metadata from npm package data
        
        Args:
            package_data: Raw package data from npm registry
            version: Specific version to extract (uses latest if None)
            
        Returns:
            LibraryMetadata object
            
        Raises:
            InvalidResponseError: If required fields are missing
        """
        try:
            # Get the latest version if not specified
            if version is None:
                dist_tags = package_data.get("dist-tags", {})
                version = dist_tags.get("latest")
                if not version:
                    raise InvalidResponseError("No latest version found in npm package data")
            
            # Get version-specific data
            versions = package_data.get("versions", {})
            if version not in versions:
                available_versions = list(versions.keys())
                raise InvalidResponseError(
                    f"Version {version} not found. Available versions: {available_versions[:10]}"
                )
            
            version_data = versions[version]
            
            # Extract basic metadata
            name = package_data.get("name")
            if not name:
                raise InvalidResponseError("Package name not found in npm data")
            
            description = version_data.get("description", "")
            license_info = version_data.get("license", "Unknown")
            
            # Handle license field (can be string or object)
            if isinstance(license_info, dict):
                license_str = license_info.get("type", "Unknown")
            else:
                license_str = str(license_info)
            
            # Extract dependencies
            dependencies = []
            deps = version_data.get("dependencies", {})
            for dep_name, dep_version in deps.items():
                dependencies.append(Dependency(
                    name=dep_name,
                    version=dep_version,
                    is_direct=True
                ))
            
            # Extract optional fields
            homepage = version_data.get("homepage")
            repository = None
            repo_info = version_data.get("repository")
            if isinstance(repo_info, dict):
                repository = repo_info.get("url")
            elif isinstance(repo_info, str):
                repository = repo_info
            
            return LibraryMetadata(
                name=name,
                version=version,
                description=description,
                license=license_str,
                registry_type=RegistryType.NPM,
                dependencies=dependencies,
                homepage=homepage,
                repository=repository
            )
            
        except KeyError as e:
            raise InvalidResponseError(f"Missing required field in npm data: {e}")
        except Exception as e:
            if isinstance(e, InvalidResponseError):
                raise
            raise InvalidResponseError(f"Error extracting npm metadata: {e}")

class PyPIRegistryClient:
    """Client for PyPI JSON API"""
    
    BASE_URL = "https://pypi.org/pypi"
    
    def __init__(self, http_client: httpx.AsyncClient, circuit_breaker: AsyncCircuitBreaker):
        self.http_client = http_client
        self.circuit_breaker = circuit_breaker
    
    async def get_package_info(self, package_name: str) -> dict:
        """
        Fetch package information from PyPI
        
        Args:
            package_name: Name of the PyPI package
            
        Returns:
            Package information dictionary
            
        Raises:
            NetworkError: If network request fails
            PackageNotFoundError: If package doesn't exist
            InvalidResponseError: If response is malformed
        """
        url = f"{self.BASE_URL}/{quote(package_name, safe='')}/json"
        
        try:
            response = await self.circuit_breaker.call(
                self._make_request, url
            )
            
            if response.status_code == 404:
                raise PackageNotFoundError(f"Package '{package_name}' not found in PyPI")
            
            if response.status_code != 200:
                raise NetworkError(f"PyPI returned status {response.status_code}")
            
            try:
                return response.json()
            except Exception as e:
                raise InvalidResponseError(f"Invalid JSON response from PyPI: {e}")
                
        except httpx.RequestError as e:
            raise NetworkError(f"Network error accessing PyPI: {e}")
        except Exception as e:
            if isinstance(e, (NetworkError, PackageNotFoundError, InvalidResponseError)):
                raise
            raise NetworkError(f"Unexpected error accessing PyPI: {e}")
    
    async def _make_request(self, url: str) -> httpx.Response:
        """Make HTTP request with timeout"""
        return await self.http_client.get(url, timeout=30.0)
    def extract_metadata(self, package_data: dict, version: Optional[str] = None) -> LibraryMetadata:
        """
        Extract metadata from PyPI package data
        
        Args:
            package_data: Raw package data from PyPI
            version: Specific version to extract (uses latest if None)
            
        Returns:
            LibraryMetadata object
            
        Raises:
            InvalidResponseError: If required fields are missing
        """
        try:
            info = package_data.get("info", {})
            
            # Extract basic metadata
            name = info.get("name")
            if not name:
                raise InvalidResponseError("Package name not found in PyPI data")
            
            # Use specified version or latest
            if version is None:
                version = info.get("version")
                if not version:
                    raise InvalidResponseError("No version found in PyPI package data")
            
            description = info.get("summary", "")
            license_str = info.get("license", "Unknown")
            
            # Extract dependencies (PyPI doesn't provide dependency info in the JSON API)
            # Dependencies would need to be extracted from the package files, which is complex
            # For now, we'll return an empty list and note this limitation
            dependencies = []
            
            # Extract optional fields
            homepage = info.get("home_page")
            project_urls = info.get("project_urls", {})
            repository = None
            
            # Look for repository in project URLs
            if project_urls:
                # Common keys for repository URLs
                repo_keys = ["Repository", "Source", "Source Code", "GitHub", "GitLab"]
                for key in repo_keys:
                    if key in project_urls:
                        repository = project_urls[key]
                        break
            
            # If no specific repo key found, use homepage if it looks like a repo
            if not repository and homepage:
                if any(host in homepage.lower() for host in ["github.com", "gitlab.com", "bitbucket.org"]):
                    repository = homepage
            
            return LibraryMetadata(
                name=name,
                version=version,
                description=description,
                license=license_str,
                registry_type=RegistryType.PYPI,
                dependencies=dependencies,
                homepage=homepage,
                repository=repository
            )
            
        except KeyError as e:
            raise InvalidResponseError(f"Missing required field in PyPI data: {e}")
        except Exception as e:
            if isinstance(e, InvalidResponseError):
                raise
            raise InvalidResponseError(f"Error extracting PyPI metadata: {e}")
class MetadataFetcher:
    """
    Main orchestrator for fetching library metadata from package registries
    """
    
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        """
        Initialize MetadataFetcher
        
        Args:
            http_client: Optional HTTP client (creates new one if None)
        """
        self.http_client = http_client or httpx.AsyncClient()
        self._own_client = http_client is None
        
        # Create circuit breakers for each registry
        self.npm_circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=(NetworkError, httpx.RequestError)
        )
        
        self.pypi_circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=(NetworkError, httpx.RequestError)
        )
        
        # Initialize registry clients
        self.registries = {
            RegistryType.NPM: NPMRegistryClient(self.http_client, self.npm_circuit_breaker),
            RegistryType.PYPI: PyPIRegistryClient(self.http_client, self.pypi_circuit_breaker),
        }
    
    async def fetch_metadata(
        self,
        registry_type: RegistryType,
        package_name: str,
        version: Optional[str] = None
    ) -> LibraryMetadata:
        """
        Fetch metadata from appropriate registry
        
        Args:
            registry_type: Type of package registry (npm, pypi, etc.)
            package_name: Name of the package
            version: Specific version to fetch (uses latest if None)
            
        Returns:
            LibraryMetadata object with package information
            
        Raises:
            MetadataFetchError: If fetching fails for any reason
            ValueError: If registry type is not supported
        """
        if registry_type not in self.registries:
            raise ValueError(f"Unsupported registry type: {registry_type}")
        
        client = self.registries[registry_type]
        
        try:
            logger.info(f"Fetching metadata for {package_name} from {registry_type.value}")
            
            # Fetch raw package data
            package_data = await client.get_package_info(package_name)
            
            # Extract metadata
            metadata = client.extract_metadata(package_data, version)
            
            logger.info(
                f"Successfully fetched metadata for {metadata.name}@{metadata.version} "
                f"from {registry_type.value}"
            )
            
            return metadata
            
        except (NetworkError, PackageNotFoundError, InvalidResponseError) as e:
            logger.error(f"Failed to fetch metadata for {package_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching metadata for {package_name}: {e}")
            raise MetadataFetchError(f"Unexpected error: {e}")
    
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