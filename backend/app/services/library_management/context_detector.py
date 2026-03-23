"""
Context Detector Service for Library Management

This service detects the appropriate project context for libraries based on
registry type and validates that the target context has the required
configuration files.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional

from app.models.library import RegistryType, ProjectContext


logger = logging.getLogger(__name__)


class ContextDetectionError(Exception):
    """Base exception for context detection errors"""
    pass


class ConfigurationFileNotFoundError(ContextDetectionError):
    """Configuration file not found for the specified context"""
    pass


class ContextDetector:
    """
    Service to detect appropriate project context for libraries and validate
    that the target context has the required configuration files.
    
    This service maps registry types to project contexts and ensures that
    the necessary package manager configuration files exist.
    """
    
    # Mapping from registry type to default project context
    REGISTRY_CONTEXT_MAP = {
        RegistryType.NPM: ProjectContext.FRONTEND,
        RegistryType.PYPI: ProjectContext.BACKEND,
        RegistryType.MAVEN: ProjectContext.BACKEND,  # Java backend services
    }
    
    # Configuration files required for each project context
    CONTEXT_CONFIG_FILES = {
        ProjectContext.FRONTEND: "frontend/package.json",
        ProjectContext.BACKEND: "backend/requirements.txt",
        ProjectContext.SERVICES: "services/package.json",  # For Node.js services
    }
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize ContextDetector
        
        Args:
            project_root: Root directory of the project (defaults to current working directory)
        """
        self.project_root = Path(project_root or os.getcwd())
        logger.debug(f"ContextDetector initialized with project root: {self.project_root}")
    
    def detect_context(self, registry_type: RegistryType) -> ProjectContext:
        """
        Detect the appropriate project context based on registry type.
        
        This method maps package registry types to their typical project contexts:
        - npm packages → FRONTEND context
        - PyPI packages → BACKEND context  
        - Maven packages → BACKEND context
        
        Args:
            registry_type: The type of package registry (npm, pypi, maven)
            
        Returns:
            ProjectContext enum value indicating the suggested context
            
        Raises:
            ValueError: If registry type is not supported
            
        Examples:
            >>> detector = ContextDetector()
            >>> detector.detect_context(RegistryType.NPM)
            ProjectContext.FRONTEND
            >>> detector.detect_context(RegistryType.PYPI)
            ProjectContext.BACKEND
        """
        if registry_type not in self.REGISTRY_CONTEXT_MAP:
            raise ValueError(f"Unsupported registry type: {registry_type}")
        
        context = self.REGISTRY_CONTEXT_MAP[registry_type]
        
        logger.info(
            f"Detected context {context.value} for registry type {registry_type.value}"
        )
        
        return context
    
    def validate_context(self, context: ProjectContext) -> Tuple[bool, Optional[str]]:
        """
        Validate that the specified project context has the required configuration file.
        
        This method checks for the existence of package manager configuration files:
        - FRONTEND context requires frontend/package.json
        - BACKEND context requires backend/requirements.txt
        - SERVICES context requires services/package.json
        
        Args:
            context: The project context to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if context is valid, False otherwise
            - error_message: Descriptive error message if invalid, None if valid
            
        Examples:
            >>> detector = ContextDetector()
            >>> valid, error = detector.validate_context(ProjectContext.FRONTEND)
            >>> valid
            True  # if frontend/package.json exists
            >>> error
            None
            
            >>> valid, error = detector.validate_context(ProjectContext.BACKEND)
            >>> valid
            False  # if backend/requirements.txt doesn't exist
            >>> error
            'Configuration file not found: backend/requirements.txt'
        """
        if context not in self.CONTEXT_CONFIG_FILES:
            return False, f"Unsupported project context: {context}"
        
        config_file_path = self.CONTEXT_CONFIG_FILES[context]
        full_path = self.project_root / config_file_path
        
        logger.debug(f"Validating context {context.value}, checking file: {full_path}")
        
        if not full_path.exists():
            error_msg = f"Configuration file not found: {config_file_path}"
            logger.warning(f"Context validation failed: {error_msg}")
            return False, error_msg
        
        if not full_path.is_file():
            error_msg = f"Configuration path exists but is not a file: {config_file_path}"
            logger.warning(f"Context validation failed: {error_msg}")
            return False, error_msg
        
        logger.info(f"Context {context.value} validated successfully")
        return True, None
    
    def get_config_file_path(self, context: ProjectContext) -> str:
        """
        Get the configuration file path for a given project context.
        
        Args:
            context: The project context
            
        Returns:
            Relative path to the configuration file
            
        Raises:
            ValueError: If context is not supported
        """
        if context not in self.CONTEXT_CONFIG_FILES:
            raise ValueError(f"Unsupported project context: {context}")
        
        return self.CONTEXT_CONFIG_FILES[context]
    
    def get_absolute_config_path(self, context: ProjectContext) -> Path:
        """
        Get the absolute path to the configuration file for a given project context.
        
        Args:
            context: The project context
            
        Returns:
            Absolute Path object to the configuration file
            
        Raises:
            ValueError: If context is not supported
        """
        config_file_path = self.get_config_file_path(context)
        return self.project_root / config_file_path
    
    def detect_and_validate_context(
        self, 
        registry_type: RegistryType
    ) -> Tuple[ProjectContext, bool, Optional[str]]:
        """
        Detect context for registry type and validate it in one operation.
        
        This is a convenience method that combines context detection and validation.
        
        Args:
            registry_type: The type of package registry
            
        Returns:
            Tuple of (context, is_valid, error_message)
            - context: The detected project context
            - is_valid: True if context is valid, False otherwise
            - error_message: Descriptive error message if invalid, None if valid
            
        Examples:
            >>> detector = ContextDetector()
            >>> context, valid, error = detector.detect_and_validate_context(RegistryType.NPM)
            >>> context
            ProjectContext.FRONTEND
            >>> valid
            True  # if frontend/package.json exists
        """
        try:
            context = self.detect_context(registry_type)
            is_valid, error_message = self.validate_context(context)
            
            return context, is_valid, error_message
            
        except ValueError as e:
            logger.error(f"Error in detect_and_validate_context: {e}")
            # Return a default context with error
            return ProjectContext.BACKEND, False, str(e)
    
    def list_available_contexts(self) -> dict:
        """
        List all available project contexts and their validation status.
        
        Returns:
            Dictionary mapping context names to their validation status
            
        Examples:
            >>> detector = ContextDetector()
            >>> detector.list_available_contexts()
            {
                'frontend': {'valid': True, 'config_file': 'frontend/package.json'},
                'backend': {'valid': False, 'config_file': 'backend/requirements.txt', 'error': 'File not found'},
                'services': {'valid': True, 'config_file': 'services/package.json'}
            }
        """
        contexts = {}
        
        for context in ProjectContext:
            is_valid, error_message = self.validate_context(context)
            config_file = self.get_config_file_path(context)
            
            context_info = {
                'valid': is_valid,
                'config_file': config_file
            }
            
            if error_message:
                context_info['error'] = error_message
            
            contexts[context.value] = context_info
        
        return contexts
    
    def suggest_alternative_contexts(
        self, 
        registry_type: RegistryType
    ) -> list[ProjectContext]:
        """
        Suggest alternative contexts if the default context is not valid.
        
        Args:
            registry_type: The type of package registry
            
        Returns:
            List of alternative project contexts that are valid
        """
        primary_context = self.detect_context(registry_type)
        alternatives = []
        
        # Check all contexts except the primary one
        for context in ProjectContext:
            if context != primary_context:
                is_valid, _ = self.validate_context(context)
                if is_valid:
                    alternatives.append(context)
        
        logger.info(
            f"Found {len(alternatives)} alternative contexts for {registry_type.value}: "
            f"{[ctx.value for ctx in alternatives]}"
        )
        
        return alternatives