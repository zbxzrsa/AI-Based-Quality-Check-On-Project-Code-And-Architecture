"""
Dependency Resolver Service for Library Management

This service analyzes dependencies and detects conflicts when adding new libraries.
It parses existing dependency files, compares versions using semantic versioning rules,
detects circular dependencies, and suggests compatible versions.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from packaging import version
from packaging.specifiers import SpecifierSet, InvalidSpecifier

from app.schemas.library import LibraryMetadata, Dependency, ConflictAnalysis, ConflictInfo
from app.models.library import ProjectContext, RegistryType


logger = logging.getLogger(__name__)


class DependencyResolverError(Exception):
    """Base exception for dependency resolution errors"""
    pass


class FileParsingError(DependencyResolverError):
    """Error parsing dependency files"""
    pass


class VersionConflictError(DependencyResolverError):
    """Version conflict detected"""
    pass


class CircularDependencyError(DependencyResolverError):
    """Circular dependency detected"""
    pass


class DependencyResolver:
    """
    Service to analyze dependencies and detect conflicts when adding new libraries.
    
    This service provides methods to:
    - Parse existing dependency files (package.json, requirements.txt)
    - Compare library dependencies with existing dependencies
    - Detect version conflicts using semantic versioning rules
    - Detect circular dependencies in the dependency tree
    - Suggest compatible versions that satisfy all constraints
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize DependencyResolver
        
        Args:
            project_root: Root directory of the project (defaults to current working directory)
        """
        self.project_root = Path(project_root or ".")
        logger.debug(f"DependencyResolver initialized with project root: {self.project_root}")
    
    async def check_conflicts(
        self,
        library: LibraryMetadata,
        project_context: ProjectContext
    ) -> ConflictAnalysis:
        """
        Check for version conflicts with existing dependencies.
        
        This method:
        1. Parses the existing dependency file for the project context
        2. Compares the library's dependencies with existing dependencies
        3. Detects version conflicts using semantic versioning rules
        4. Checks for circular dependencies
        5. Generates suggestions for resolving conflicts
        
        Args:
            library: Library metadata containing dependencies to check
            project_context: Target project context (backend, frontend, services)
            
        Returns:
            ConflictAnalysis with conflicts list, suggestions, and circular dependency info
            
        Raises:
            DependencyResolverError: If dependency analysis fails
            
        Examples:
            >>> resolver = DependencyResolver()
            >>> library = LibraryMetadata(name="react", version="18.0.0", ...)
            >>> analysis = await resolver.check_conflicts(library, ProjectContext.FRONTEND)
            >>> analysis.has_conflicts
            False
        """
        try:
            logger.info(
                f"Checking conflicts for {library.name}@{library.version} "
                f"in {project_context.value} context"
            )
            
            # Parse existing dependencies
            existing_deps = await self._parse_existing_dependencies(project_context)
            
            # Check for version conflicts
            conflicts = self._detect_version_conflicts(library, existing_deps)
            
            # Check for circular dependencies
            circular_deps = self.detect_circular_dependencies(library, existing_deps)
            
            # Generate suggestions
            suggestions = self._generate_conflict_suggestions(conflicts, library)
            
            has_conflicts = len(conflicts) > 0 or circular_deps is not None
            
            analysis = ConflictAnalysis(
                has_conflicts=has_conflicts,
                conflicts=conflicts,
                suggestions=suggestions,
                circular_dependencies=circular_deps
            )
            
            logger.info(
                f"Conflict analysis complete: {len(conflicts)} conflicts, "
                f"circular deps: {circular_deps is not None}"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error checking conflicts for {library.name}: {e}")
            raise DependencyResolverError(f"Failed to analyze dependencies: {e}")
    
    async def _parse_existing_dependencies(
        self,
        project_context: ProjectContext
    ) -> Dict[str, str]:
        """
        Parse existing dependencies from the appropriate configuration file.
        
        Args:
            project_context: Project context to determine which file to parse
            
        Returns:
            Dictionary mapping package names to version specifiers
            
        Raises:
            FileParsingError: If dependency file cannot be parsed
        """
        try:
            if project_context == ProjectContext.FRONTEND:
                return await self._parse_package_json()
            elif project_context == ProjectContext.BACKEND:
                return await self._parse_requirements_txt()
            elif project_context == ProjectContext.SERVICES:
                return await self._parse_package_json("services/package.json")
            else:
                raise ValueError(f"Unsupported project context: {project_context}")
                
        except Exception as e:
            logger.error(f"Error parsing dependencies for {project_context.value}: {e}")
            raise FileParsingError(f"Failed to parse dependency file: {e}")
    
    async def _parse_package_json(self, file_path: str = "frontend/package.json") -> Dict[str, str]:
        """
        Parse dependencies from package.json file.
        
        Args:
            file_path: Path to package.json file relative to project root
            
        Returns:
            Dictionary mapping package names to version specifiers
            
        Raises:
            FileParsingError: If package.json cannot be parsed
        """
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            logger.warning(f"package.json not found at {full_path}")
            return {}
        
        try:
            def read_json():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            package_data = await asyncio.to_thread(read_json)
            
            dependencies = {}
            
            # Merge dependencies and devDependencies
            for dep_type in ['dependencies', 'devDependencies', 'peerDependencies']:
                if dep_type in package_data:
                    dependencies.update(package_data[dep_type])
            
            logger.debug(f"Parsed {len(dependencies)} dependencies from {file_path}")
            return dependencies
            
        except json.JSONDecodeError as e:
            raise FileParsingError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise FileParsingError(f"Error reading {file_path}: {e}")
    
    async def _parse_requirements_txt(self, file_path: str = "backend/requirements.txt") -> Dict[str, str]:
        """
        Parse dependencies from requirements.txt file.
        
        Args:
            file_path: Path to requirements.txt file relative to project root
            
        Returns:
            Dictionary mapping package names to version specifiers
            
        Raises:
            FileParsingError: If requirements.txt cannot be parsed
        """
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            logger.warning(f"requirements.txt not found at {full_path}")
            return {}
        
        try:
            def read_requirements():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.readlines()
            
            lines = await asyncio.to_thread(read_requirements)
            
            dependencies = {}
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Skip -e (editable) installs and other pip options
                if line.startswith('-'):
                    continue
                
                # Parse package specification
                # Supports formats: package==1.0.0, package>=1.0.0, package~=1.0.0, etc.
                match = re.match(r'^([a-zA-Z0-9_.-]+)([><=!~]+.*)?', line)
                
                if match:
                    package_name = match.group(1)
                    version_spec = match.group(2) or ""
                    dependencies[package_name] = version_spec
                else:
                    logger.warning(f"Could not parse requirement line {line_num}: {line}")
            
            logger.debug(f"Parsed {len(dependencies)} dependencies from {file_path}")
            return dependencies
            
        except Exception as e:
            raise FileParsingError(f"Error reading {file_path}: {e}")
    
    def _detect_version_conflicts(
        self,
        library: LibraryMetadata,
        existing_deps: Dict[str, str]
    ) -> List[ConflictInfo]:
        """
        Detect version conflicts between library dependencies and existing dependencies.
        
        Args:
            library: Library metadata with dependencies to check
            existing_deps: Dictionary of existing package names to version specifiers
            
        Returns:
            List of ConflictInfo objects describing conflicts
        """
        conflicts = []
        
        # Check each dependency of the new library
        for dep in library.dependencies:
            if dep.name in existing_deps:
                existing_version = existing_deps[dep.name]
                required_version = dep.version
                
                # Check if versions are compatible
                if not self._are_versions_compatible(existing_version, required_version, library.registry_type):
                    conflict = ConflictInfo(
                        package=dep.name,
                        existing_version=existing_version,
                        required_version=required_version
                    )
                    conflicts.append(conflict)
                    
                    logger.warning(
                        f"Version conflict detected for {dep.name}: "
                        f"existing {existing_version} vs required {required_version}"
                    )
        
        return conflicts
    
    def _are_versions_compatible(
        self,
        existing_version: str,
        required_version: str,
        registry_type: RegistryType
    ) -> bool:
        """
        Check if two version specifiers are compatible.
        
        Args:
            existing_version: Version specifier from existing dependencies
            required_version: Version specifier from new library
            registry_type: Registry type to determine version format
            
        Returns:
            True if versions are compatible, False otherwise
        """
        try:
            if registry_type == RegistryType.NPM:
                return self._are_npm_versions_compatible(existing_version, required_version)
            elif registry_type in [RegistryType.PYPI, RegistryType.MAVEN]:
                return self._are_python_versions_compatible(existing_version, required_version)
            else:
                logger.warning(f"Unknown registry type for version comparison: {registry_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error comparing versions {existing_version} vs {required_version}: {e}")
            return False
    
    def _are_npm_versions_compatible(self, existing: str, required: str) -> bool:
        """
        Check if npm version specifiers are compatible.
        
        npm uses semantic versioning with specifiers like:
        - ^1.2.3 (compatible with 1.x.x, >= 1.2.3)
        - ~1.2.3 (compatible with 1.2.x, >= 1.2.3)
        - >=1.2.3 (greater than or equal to 1.2.3)
        - 1.2.3 (exact version)
        
        Args:
            existing: Existing version specifier
            required: Required version specifier
            
        Returns:
            True if compatible, False otherwise
        """
        try:
            # Remove leading/trailing whitespace
            existing = existing.strip()
            required = required.strip()
            
            # If either is exact version, check if they match
            if not any(c in existing for c in '^~><>=') and not any(c in required for c in '^~><>='):
                return existing == required
            
            # For complex version ranges, we'll use a simplified compatibility check
            # In a production system, you'd want to use a proper semver library
            
            # Extract base versions (remove specifiers)
            existing_base = re.sub(r'^[^0-9]*', '', existing)
            required_base = re.sub(r'^[^0-9]*', '', required)
            
            if not existing_base or not required_base:
                return False
            
            # Parse version numbers
            existing_parts = existing_base.split('.')
            required_parts = required_base.split('.')
            
            # Pad with zeros if needed
            while len(existing_parts) < 3:
                existing_parts.append('0')
            while len(required_parts) < 3:
                required_parts.append('0')
            
            # For caret (^) compatibility: major version must match
            if existing.startswith('^') or required.startswith('^'):
                return existing_parts[0] == required_parts[0]
            
            # For tilde (~) compatibility: major.minor must match
            if existing.startswith('~') or required.startswith('~'):
                return existing_parts[0] == required_parts[0] and existing_parts[1] == required_parts[1]
            
            # For other cases, assume compatible if major versions match
            return existing_parts[0] == required_parts[0]
            
        except Exception as e:
            logger.error(f"Error comparing npm versions {existing} vs {required}: {e}")
            return False
    
    def _are_python_versions_compatible(self, existing: str, required: str) -> bool:
        """
        Check if Python version specifiers are compatible using packaging library.
        
        Args:
            existing: Existing version specifier (e.g., ">=1.2.0", "==1.2.3")
            required: Required version specifier
            
        Returns:
            True if compatible, False otherwise
        """
        try:
            # Handle exact versions (no operators)
            if not any(op in existing for op in ['==', '>=', '<=', '>', '<', '~=', '!=']):
                existing = f"=={existing}"
            if not any(op in required for op in ['==', '>=', '<=', '>', '<', '~=', '!=']):
                required = f"=={required}"
            
            # Create specifier sets
            existing_spec = SpecifierSet(existing)
            required_spec = SpecifierSet(required)
            
            # Check if there's any overlap between the specifiers
            # This is a simplified check - in practice, you'd want more sophisticated logic
            
            # If both are exact versions, they must match
            if existing.startswith('==') and required.startswith('=='):
                return existing == required
            
            # For other cases, we'll check if the required version satisfies existing constraints
            # Extract version from required specifier for testing
            required_version_match = re.search(r'([0-9]+(?:\.[0-9]+)*)', required)
            if required_version_match:
                test_version = required_version_match.group(1)
                return version.Version(test_version) in existing_spec
            
            return True  # Assume compatible if we can't determine otherwise
            
        except (InvalidSpecifier, version.InvalidVersion) as e:
            logger.error(f"Invalid version specifier: {e}")
            return False
        except Exception as e:
            logger.error(f"Error comparing Python versions {existing} vs {required}: {e}")
            return False
    
    def detect_circular_dependencies(
        self,
        library: LibraryMetadata,
        existing_deps: List[Dependency]
    ) -> Optional[List[str]]:
        """
        Detect circular dependencies in the dependency tree.
        
        This method builds a dependency graph and uses depth-first search
        to detect cycles that would include the new library.
        
        Args:
            library: Library metadata to check for circular dependencies
            existing_deps: List of existing dependencies
            
        Returns:
            List of package names forming a circular dependency chain, or None if no cycles
            
        Examples:
            >>> resolver = DependencyResolver()
            >>> library = LibraryMetadata(name="A", dependencies=[Dependency(name="B", version="1.0")])
            >>> existing = [Dependency(name="B", version="1.0"), Dependency(name="C", version="1.0")]
            >>> # If B depends on A, this would return ["A", "B", "A"]
            >>> resolver.detect_circular_dependencies(library, existing)
        """
        try:
            # Build dependency graph
            graph = self._build_dependency_graph(library, existing_deps)
            
            # Use DFS to detect cycles starting from the new library
            visited = set()
            rec_stack = set()
            
            def dfs(node: str, path: List[str]) -> Optional[List[str]]:
                """Depth-first search to detect cycles"""
                if node in rec_stack:
                    # Found a cycle - return the cycle path
                    cycle_start = path.index(node)
                    return path[cycle_start:] + [node]
                
                if node in visited:
                    return None
                
                visited.add(node)
                rec_stack.add(node)
                
                # Check all dependencies of this node
                for dep in graph.get(node, []):
                    cycle = dfs(dep, path + [node])
                    if cycle:
                        return cycle
                
                rec_stack.remove(node)
                return None
            
            # Start DFS from the new library
            cycle = dfs(library.name, [])
            
            if cycle:
                logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")
                return cycle
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting circular dependencies: {e}")
            return None
    
    def _build_dependency_graph(
        self,
        library: LibraryMetadata,
        existing_deps: List[Dependency]
    ) -> Dict[str, List[str]]:
        """
        Build a dependency graph from library and existing dependencies.
        
        Args:
            library: New library to add to the graph
            existing_deps: Existing dependencies
            
        Returns:
            Dictionary mapping package names to lists of their dependencies
        """
        graph = {}
        
        # Add new library's dependencies
        graph[library.name] = [dep.name for dep in library.dependencies]
        
        # Add existing dependencies
        # Note: We don't have dependency information for existing packages,
        # so we'll create a simplified graph. In a real implementation,
        # you'd need to fetch dependency information for existing packages.
        for dep in existing_deps:
            if dep.name not in graph:
                graph[dep.name] = []
        
        return graph
    
    def suggest_compatible_version(
        self,
        library_name: str,
        constraints: List[str]
    ) -> Optional[str]:
        """
        Suggest a version that satisfies all given constraints.
        
        This method analyzes version constraints and attempts to find
        a version that satisfies all of them.
        
        Args:
            library_name: Name of the library
            constraints: List of version constraints (e.g., [">=1.0.0", "<2.0.0"])
            
        Returns:
            Suggested version string, or None if no compatible version found
            
        Examples:
            >>> resolver = DependencyResolver()
            >>> resolver.suggest_compatible_version("react", ["^17.0.0", ">=17.0.2"])
            "17.0.2"
        """
        try:
            if not constraints:
                return None
            
            logger.debug(f"Finding compatible version for {library_name} with constraints: {constraints}")
            
            # For npm packages, use npm-style version resolution
            if self._looks_like_npm_constraint(constraints[0]):
                return self._suggest_npm_version(constraints)
            else:
                return self._suggest_python_version(constraints)
                
        except Exception as e:
            logger.error(f"Error suggesting compatible version for {library_name}: {e}")
            return None
    
    def _looks_like_npm_constraint(self, constraint: str) -> bool:
        """Check if a constraint looks like an npm version constraint"""
        return any(constraint.strip().startswith(prefix) for prefix in ['^', '~']) or \
               not any(op in constraint for op in ['==', '>=', '<=', '~='])
    
    def _suggest_npm_version(self, constraints: List[str]) -> Optional[str]:
        """
        Suggest npm version that satisfies all constraints.
        
        Args:
            constraints: List of npm version constraints
            
        Returns:
            Suggested version or None
        """
        try:
            # This is a simplified implementation
            # In practice, you'd want to use a proper npm semver library
            
            # Find the most restrictive constraint
            exact_versions = []
            range_constraints = []
            
            for constraint in constraints:
                constraint = constraint.strip()
                if not any(c in constraint for c in '^~><>='):
                    # Exact version
                    exact_versions.append(constraint)
                else:
                    range_constraints.append(constraint)
            
            # If we have exact versions, they must all match
            if exact_versions:
                if len(set(exact_versions)) == 1:
                    return exact_versions[0]
                else:
                    return None  # Conflicting exact versions
            
            # For range constraints, return a reasonable default
            # This is highly simplified - real implementation would be much more complex
            if range_constraints:
                # Extract base version from first constraint
                first_constraint = range_constraints[0]
                version_match = re.search(r'([0-9]+(?:\.[0-9]+)*)', first_constraint)
                if version_match:
                    return version_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error suggesting npm version: {e}")
            return None
    
    def _suggest_python_version(self, constraints: List[str]) -> Optional[str]:
        """
        Suggest Python version that satisfies all constraints.
        
        Args:
            constraints: List of Python version constraints
            
        Returns:
            Suggested version or None
        """
        try:
            # Combine all constraints into a single specifier set
            combined_constraints = ",".join(constraints)
            spec_set = SpecifierSet(combined_constraints)
            
            # This is a simplified approach - in practice, you'd query
            # the package registry for available versions and find the
            # latest one that satisfies all constraints
            
            # For now, extract a reasonable version from the constraints
            for constraint in constraints:
                version_match = re.search(r'([0-9]+(?:\.[0-9]+)*)', constraint)
                if version_match:
                    candidate_version = version_match.group(1)
                    try:
                        if version.Version(candidate_version) in spec_set:
                            return candidate_version
                    except version.InvalidVersion:
                        continue
            
            return None
            
        except (InvalidSpecifier, version.InvalidVersion) as e:
            logger.error(f"Invalid version constraint: {e}")
            return None
        except Exception as e:
            logger.error(f"Error suggesting Python version: {e}")
            return None
    
    def _generate_conflict_suggestions(
        self,
        conflicts: List[ConflictInfo],
        library: LibraryMetadata
    ) -> List[str]:
        """
        Generate suggestions for resolving version conflicts.
        
        Args:
            conflicts: List of detected conflicts
            library: Library being added
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        if not conflicts:
            return suggestions
        
        for conflict in conflicts:
            # Suggest upgrading existing dependency
            suggestions.append(
                f"Upgrade {conflict.package} from {conflict.existing_version} "
                f"to {conflict.required_version}"
            )
            
            # Suggest finding compatible library version
            suggestions.append(
                f"Find a version of {library.name} that's compatible with "
                f"{conflict.package} {conflict.existing_version}"
            )
        
        # General suggestions
        if len(conflicts) > 1:
            suggestions.append(
                "Consider updating multiple dependencies to resolve all conflicts"
            )
        
        suggestions.append(
            "Review dependency requirements and consider using dependency resolution tools"
        )
        
        return suggestions