"""
URI Parser Service for Library Management

This service parses and validates library URIs from various package registries
including npm, PyPI, and Maven.

Supported URI formats:
- npm: npm:package-name[@version], https://npmjs.com/package/name[/v/version]
- PyPI: pypi:package-name[==version], https://pypi.org/project/name[/version]
- Maven: maven:group:artifact[:version]
"""

import re
from typing import Optional, Tuple
from app.schemas.library import ParsedURI
from app.models.library import RegistryType


class URIParser:
    """
    Parse and validate library URIs from various package registries.
    
    This class provides methods to parse library URIs into structured components
    (registry type, package name, version) and validate URI formats.
    """
    
    # Regex patterns for different registry types
    # Each registry type has multiple patterns to support different URI formats
    PATTERNS = {
        RegistryType.NPM: [
            # npm:package-name[@version]
            # Supports scoped packages: npm:@scope/package-name[@version]
            re.compile(
                r'^npm:(@?[a-z0-9-]+(?:/[a-z0-9-]+)?)(?:@(.+))?$',
                re.IGNORECASE
            ),
            # https://npmjs.com/package/name[/v/version]
            # https://www.npmjs.com/package/name[/v/version]
            re.compile(
                r'^https?://(?:www\.)?npmjs\.com/package/(@?[a-z0-9-]+(?:/[a-z0-9-]+)?)(?:/v/(.+))?$',
                re.IGNORECASE
            ),
        ],
        RegistryType.PYPI: [
            # pypi:package-name[==version]
            # PyPI allows letters, numbers, hyphens, underscores, and periods
            re.compile(
                r'^pypi:([a-z0-9-_.]+)(?:==(.+))?$',
                re.IGNORECASE
            ),
            # https://pypi.org/project/name[/version]
            re.compile(
                r'^https?://pypi\.org/project/([a-z0-9-_.]+)(?:/(.+))?$',
                re.IGNORECASE
            ),
        ],
        RegistryType.MAVEN: [
            # maven:group:artifact[:version]
            # Maven coordinates use dots for group IDs and hyphens for artifact IDs
            re.compile(
                r'^maven:([a-z0-9.-]+):([a-z0-9-]+)(?::(.+))?$',
                re.IGNORECASE
            ),
        ],
    }
    
    def parse(self, uri: str) -> ParsedURI:
        """
        Parse a library URI and extract its components.
        
        Args:
            uri: The library URI to parse (e.g., "npm:react@18.0.0")
            
        Returns:
            ParsedURI object containing registry_type, package_name, version, and raw_uri
            
        Raises:
            ValueError: If the URI format is invalid or unrecognized
            
        Examples:
            >>> parser = URIParser()
            >>> result = parser.parse("npm:react@18.0.0")
            >>> result.registry_type
            RegistryType.NPM
            >>> result.package_name
            'react'
            >>> result.version
            '18.0.0'
        """
        if not uri or not uri.strip():
            raise ValueError("URI cannot be empty or whitespace")
        
        uri = uri.strip()
        
        # Try to match against each registry type's patterns
        for registry_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = pattern.match(uri)
                if match:
                    groups = match.groups()
                    
                    # Extract package name and version based on registry type
                    if registry_type == RegistryType.MAVEN:
                        # Maven has group:artifact:version format
                        group_id = groups[0]
                        artifact_id = groups[1]
                        package_name = f"{group_id}:{artifact_id}"
                        version = groups[2] if len(groups) > 2 else None
                    else:
                        # npm and PyPI have package_name and version
                        package_name = groups[0]
                        version = groups[1] if len(groups) > 1 else None
                    
                    return ParsedURI(
                        registry_type=registry_type,
                        package_name=package_name,
                        version=version,
                        raw_uri=uri
                    )
        
        # No pattern matched - URI is invalid
        raise ValueError(
            f"Invalid URI format: '{uri}'. "
            f"Expected formats: "
            f"npm:package-name[@version], "
            f"pypi:package-name[==version], "
            f"maven:group:artifact[:version], "
            f"or https://npmjs.com/package/name, "
            f"https://pypi.org/project/name"
        )
    
    def validate_format(self, uri: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a library URI format without fully parsing it.
        
        This method checks if the URI matches any known registry pattern
        and returns a boolean indicating validity along with an optional
        error message if invalid.
        
        Args:
            uri: The library URI to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if URI format is valid, False otherwise
            - error_message: Descriptive error message if invalid, None if valid
            
        Examples:
            >>> parser = URIParser()
            >>> valid, error = parser.validate_format("npm:react@18.0.0")
            >>> valid
            True
            >>> error
            None
            
            >>> valid, error = parser.validate_format("invalid:format")
            >>> valid
            False
            >>> error
            'Invalid URI format...'
        """
        if not uri or not uri.strip():
            return False, "URI cannot be empty or whitespace"
        
        try:
            self.parse(uri)
            return True, None
        except ValueError as e:
            return False, str(e)
    
    def get_registry_type(self, uri: str) -> Optional[RegistryType]:
        """
        Determine the registry type from a URI without full parsing.
        
        This is a convenience method that returns just the registry type,
        useful for quick registry identification.
        
        Args:
            uri: The library URI to analyze
            
        Returns:
            RegistryType if URI is valid, None if invalid
            
        Examples:
            >>> parser = URIParser()
            >>> parser.get_registry_type("npm:react")
            RegistryType.NPM
            >>> parser.get_registry_type("pypi:django")
            RegistryType.PYPI
        """
        try:
            parsed = self.parse(uri)
            return parsed.registry_type
        except ValueError:
            return None
