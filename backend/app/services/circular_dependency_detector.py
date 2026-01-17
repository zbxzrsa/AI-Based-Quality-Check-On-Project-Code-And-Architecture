"""
Circular Dependency Detection using Python AST

This module analyzes Python source code using the Abstract Syntax Tree (AST) library
to detect circular dependencies between modules. It builds a dependency graph from
import statements and identifies cycles that indicate architectural problems.
"""
import ast
import os
from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict, deque
import networkx as nx


@dataclass
class ModuleDependency:
    """Represents a dependency between two modules"""
    from_module: str
    to_module: str
    import_type: str  # 'import' or 'from_import'
    line_number: int
    imported_items: List[str]


@dataclass
class CircularDependency:
    """Represents a detected circular dependency"""
    cycle: List[str]  # List of module names in the cycle
    cycle_length: int
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    dependencies: List[ModuleDependency]


class CircularDependencyDetector:
    """
    Detects circular dependencies in Python codebases using AST analysis

    This class analyzes import statements in Python files to build a dependency graph
    and identify circular dependencies that violate architectural principles.
    """

    def __init__(self):
        self.dependencies: Dict[str, List[ModuleDependency]] = defaultdict(list)
        self.all_modules: Set[str] = set()
        self.processed_files: Set[str] = set()

    def analyze_project(self, project_root: str, file_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze an entire project for circular dependencies

        Args:
            project_root: Root directory of the project
            file_patterns: List of file patterns to include (default: ['*.py'])

        Returns:
            Analysis results with detected cycles and statistics
        """
        if file_patterns is None:
            file_patterns = ['*.py']

        # Find all Python files
        python_files = self._find_python_files(project_root, file_patterns)

        # Analyze each file
        for file_path in python_files:
            self._analyze_file(file_path)

        # Detect circular dependencies
        cycles = self._detect_cycles()

        # Generate statistics
        stats = self._generate_statistics(cycles)

        return {
            'project_root': project_root,
            'files_analyzed': len(self.processed_files),
            'total_modules': len(self.all_modules),
            'total_dependencies': sum(len(deps) for deps in self.dependencies.values()),
            'circular_dependencies': cycles,
            'cycles_found': len(cycles),
            'statistics': stats
        }

    def _find_python_files(self, project_root: str, patterns: List[str]) -> List[str]:
        """Find all Python files matching the patterns"""
        python_files = []

        for pattern in patterns:
            if pattern == '*.py':
                for root, dirs, files in os.walk(project_root):
                    # Skip common directories
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.venv', 'env']]

                    for file in files:
                        if file.endswith('.py'):
                            python_files.append(os.path.join(root, file))

        return sorted(python_files)

    def _analyze_file(self, file_path: str) -> None:
        """
        Analyze a single Python file for import dependencies

        Args:
            file_path: Path to the Python file
        """
        if file_path in self.processed_files:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Parse the AST
            tree = ast.parse(source_code, filename=file_path)

            # Extract module name from file path
            module_name = self._file_path_to_module_name(file_path)
            self.all_modules.add(module_name)

            # Extract imports
            imports = self._extract_imports(tree, file_path)

            # Store dependencies
            for import_dep in imports:
                self.dependencies[module_name].append(import_dep)

            self.processed_files.add(file_path)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _extract_imports(self, tree: ast.AST, file_path: str) -> List[ModuleDependency]:
        """
        Extract import statements from AST

        Args:
            tree: Parsed AST
            file_path: Source file path

        Returns:
            List of ModuleDependency objects
        """
        dependencies = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle 'import module' statements
                for name in node.names:
                    module_name = self._resolve_module_name(name.name, file_path)
                    if module_name:
                        dep = ModuleDependency(
                            from_module=self._file_path_to_module_name(file_path),
                            to_module=module_name,
                            import_type='import',
                            line_number=node.lineno,
                            imported_items=[name.name]
                        )
                        dependencies.append(dep)

            elif isinstance(node, ast.ImportFrom):
                # Handle 'from module import ...' statements
                if node.module:
                    module_name = self._resolve_module_name(node.module, file_path)
                    if module_name:
                        imported_items = [name.name for name in node.names]
                        dep = ModuleDependency(
                            from_module=self._file_path_to_module_name(file_path),
                            to_module=module_name,
                            import_type='from_import',
                            line_number=node.lineno,
                            imported_items=imported_items
                        )
                        dependencies.append(dep)

        return dependencies

    def _resolve_module_name(self, module_name: str, file_path: str) -> Optional[str]:
        """
        Resolve a module name to its canonical form

        Args:
            module_name: The imported module name
            file_path: Path to the file containing the import

        Returns:
            Resolved module name or None if it can't be resolved
        """
        # Handle relative imports
        if module_name.startswith('.'):
            # Convert relative import to absolute
            current_dir = os.path.dirname(file_path)
            parts = module_name.split('.')
            dots_count = 0

            for part in parts:
                if part == '':
                    dots_count += 1
                else:
                    break

            # Go up the directory tree
            for _ in range(dots_count):
                current_dir = os.path.dirname(current_dir)

            # Build the absolute module path
            remaining_parts = parts[dots_count:]
            if remaining_parts:
                module_path = os.path.join(current_dir, *remaining_parts)
                return self._file_path_to_module_name(module_path + '.py')

        # For absolute imports, try to find the module in the project
        # This is a simplified approach - in a real implementation,
        # you'd use Python's import system or sys.path
        return module_name

    def _file_path_to_module_name(self, file_path: str) -> str:
        """
        Convert a file path to a module name

        Args:
            file_path: File path

        Returns:
            Module name (e.g., 'package.submodule')
        """
        # Remove .py extension
        if file_path.endswith('.py'):
            file_path = file_path[:-3]

        # Convert path separators to dots
        return file_path.replace(os.sep, '.')

    def _detect_cycles(self) -> List[CircularDependency]:
        """
        Detect circular dependencies in the dependency graph

        Returns:
            List of CircularDependency objects
        """
        cycles = []

        # Build the dependency graph
        graph = nx.DiGraph()

        for from_module, deps in self.dependencies.items():
            for dep in deps:
                graph.add_edge(from_module, dep.to_module)

        # Find all simple cycles
        try:
            # Use NetworkX to find cycles
            all_cycles = list(nx.simple_cycles(graph))

            for cycle in all_cycles:
                if len(cycle) >= 2:  # Only consider cycles of 2 or more modules
                    # Get the dependencies involved in this cycle
                    cycle_deps = []
                    for i, module in enumerate(cycle):
                        next_module = cycle[(i + 1) % len(cycle)]
                        # Find the actual dependency
                        if module in self.dependencies:
                            for dep in self.dependencies[module]:
                                if dep.to_module == next_module:
                                    cycle_deps.append(dep)
                                    break

                    # Determine severity based on cycle length
                    if len(cycle) == 2:
                        severity = 'critical'
                    elif len(cycle) <= 4:
                        severity = 'high'
                    elif len(cycle) <= 6:
                        severity = 'medium'
                    else:
                        severity = 'low'

                    cycle_obj = CircularDependency(
                        cycle=cycle,
                        cycle_length=len(cycle),
                        severity=severity,
                        description=self._generate_cycle_description(cycle),
                        dependencies=cycle_deps
                    )
                    cycles.append(cycle_obj)

        except Exception as e:
            print(f"Error detecting cycles: {e}")

        # Sort by severity and cycle length
        cycles.sort(key=lambda x: (self._severity_score(x.severity), x.cycle_length))

        return cycles

    def _severity_score(self, severity: str) -> int:
        """Convert severity string to numeric score for sorting"""
        scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        return scores.get(severity, 0)

    def _generate_cycle_description(self, cycle: List[str]) -> str:
        """Generate a human-readable description of a cycle"""
        cycle_str = ' -> '.join(cycle) + f' -> {cycle[0]}'
        return f"Circular dependency detected: {cycle_str}"

    def _generate_statistics(self, cycles: List[CircularDependency]) -> Dict[str, Any]:
        """Generate statistics about the analysis"""
        if not cycles:
            return {
                'cycle_severity_distribution': {},
                'average_cycle_length': 0,
                'max_cycle_length': 0,
                'most_common_cycle_length': 0
            }

        severity_counts = defaultdict(int)
        cycle_lengths = []

        for cycle in cycles:
            severity_counts[cycle.severity] += 1
            cycle_lengths.append(cycle.cycle_length)

        return {
            'cycle_severity_distribution': dict(severity_counts),
            'average_cycle_length': sum(cycle_lengths) / len(cycle_lengths),
            'max_cycle_length': max(cycle_lengths),
            'most_common_cycle_length': max(set(cycle_lengths), key=cycle_lengths.count)
        }

    def get_cypher_queries_for_cycles(self, cycles: List[CircularDependency], project_id: str) -> List[str]:
        """
        Generate Cypher queries to visualize circular dependencies in Neo4j

        Args:
            cycles: List of detected circular dependencies
            project_id: Project identifier for Neo4j

        Returns:
            List of Cypher queries
        """
        queries = []

        for i, cycle_obj in enumerate(cycles):
            cycle_modules = cycle_obj.cycle  # Get the list of module names

            # Create nodes for the cycle
            cycle_nodes = []
            for j, module in enumerate(cycle_modules):
                node_id = f"{project_id}::{module}"
                node_var = f"m{i}_{j}"
                queries.append(f"""
                MERGE ({node_var}:Module {{
                    moduleId: '{node_id}',
                    name: '{module}',
                    projectId: '{project_id}'
                }})
                """)
                cycle_nodes.append((node_var, module))

            # Create relationships for the cycle
            for j, (node_var, module) in enumerate(cycle_nodes):
                next_node_var, next_module = cycle_nodes[(j + 1) % len(cycle_nodes)]
                queries.append(f"""
                MATCH (a:Module {{moduleId: '{project_id}::{module}'}})
                MATCH (b:Module {{moduleId: '{project_id}::{next_module}'}})
                MERGE (a)-[:DEPENDS_ON {{cycleId: 'cycle_{i}', severity: '{cycle_obj.severity}'}}]->(b)
                """)

        return queries


# FastAPI Background Task Integration
# Import these only when running in FastAPI context to avoid circular imports
try:
    from fastapi import BackgroundTasks, HTTPException
    from app.database.postgresql import get_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Project
    from sqlalchemy import select

    async def detect_circular_dependencies_background(
        project_id: str,
        background_tasks: BackgroundTasks,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        FastAPI endpoint handler for circular dependency detection as a background task

        This prevents timeout issues in GitHub Actions by running the analysis asynchronously.

        Args:
            project_id: Project ID to analyze
            background_tasks: FastAPI BackgroundTasks instance
            db: Database session

        Returns:
            Task initiation response
        """
        # Verify project exists
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Add background task
        background_tasks.add_task(
            _run_circular_dependency_analysis,
            project_id,
            str(project.github_repo_url)  # Convert to string if needed
        )

        return {
            "message": "Circular dependency analysis started",
            "project_id": project_id,
            "status": "running",
            "estimated_duration": "30-60 seconds"
        }

    async def _run_circular_dependency_analysis(project_id: str, repo_url: str) -> None:
        """
        Background task implementation for circular dependency analysis

        Args:
            project_id: Project ID
            repo_url: GitHub repository URL (for future cloning if needed)
        """
        try:
            # Initialize detector
            detector = CircularDependencyDetector()

            # For now, analyze the current backend codebase
            # In production, you'd clone the repo and analyze it
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

            # Run analysis
            results = detector.analyze_project(project_root)

            # Store results in database or cache
            # For now, just print them (in production, save to DB)
            print(f"Circular Dependency Analysis Results for {project_id}:")
            print(f"Files analyzed: {results['files_analyzed']}")
            print(f"Cycles found: {results['cycles_found']}")

            for cycle in results['circular_dependencies']:
                print(f"Cycle ({cycle.severity}): {' -> '.join(cycle.cycle)}")

            # Generate Cypher queries for Neo4j visualization
            if results['circular_dependencies']:
                cypher_queries = detector.get_cypher_queries_for_cycles(
                    results['circular_dependencies'],
                    project_id
                )
                print(f"Generated {len(cypher_queries)} Cypher queries for Neo4j")

        except Exception as e:
            print(f"Error in circular dependency analysis for {project_id}: {e}")

except ImportError:
    # Running in standalone mode, FastAPI not available
    pass


# Example usage and testing
def main():
    """Example usage of the circular dependency detector"""
    detector = CircularDependencyDetector()

    # Analyze the current project
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    results = detector.analyze_project(project_root)

    print("=== Circular Dependency Analysis Results ===")
    print(f"Project root: {results['project_root']}")
    print(f"Files analyzed: {results['files_analyzed']}")
    print(f"Total modules: {results['total_modules']}")
    print(f"Total dependencies: {results['total_dependencies']}")
    print(f"Circular dependencies found: {results['cycles_found']}")

    if results['circular_dependencies']:
        print("\n=== Detected Cycles ===")
        for i, cycle in enumerate(results['circular_dependencies'], 1):
            print(f"{i}. [{cycle.severity.upper()}] {' -> '.join(cycle.cycle)}")
            print(f"   Length: {cycle.cycle_length}")
            print(f"   Description: {cycle.description}")
            print()

        print("=== Cypher Queries for Neo4j ===")
        cypher_queries = detector.get_cypher_queries_for_cycles(
            results['circular_dependencies'],
            "test-project"
        )
        for i, query in enumerate(cypher_queries[:5], 1):  # Show first 5 queries
            print(f"{i}. {query.strip()}")
        if len(cypher_queries) > 5:
            print(f"... and {len(cypher_queries) - 5} more queries")
    else:
        print("✅ No circular dependencies detected!")

    print("\n=== Statistics ===")
    stats = results['statistics']
    print(f"Severity distribution: {stats['cycle_severity_distribution']}")
    print(f"Average cycle length: {stats['average_cycle_length']:.1f}")
    print(f"Maximum cycle length: {stats['max_cycle_length']}")


if __name__ == "__main__":
    main()
