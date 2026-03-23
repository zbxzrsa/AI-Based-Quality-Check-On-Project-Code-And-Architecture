"""
Code Entity Extraction Service

This service extracts code entities (functions, classes, imports) from source files,
calculates complexity metrics, and identifies dependencies between entities.

Implements Requirement 1.2: AST parsing and entity extraction
"""
from typing import List, Dict, Optional

from app.services.parsers.factory import ParserFactory
from app.services.optimized_parser import OptimizedParser
from app.schemas.ast_models import (
    ParsedFile,
    DependencyGraph,
    DependencyEdge
)


class CodeEntity:
    """
    Represents a code entity with its metadata
    """
    def __init__(
        self,
        name: str,
        entity_type: str,
        file_path: str,
        complexity: int = 1,
        lines_of_code: int = 0,
        dependencies: Optional[List[str]] = None
    ):
        self.name = name
        self.entity_type = entity_type  # 'function', 'class', 'method', 'module'
        self.file_path = file_path
        self.complexity = complexity
        self.lines_of_code = lines_of_code
        self.dependencies = dependencies or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "type": self.entity_type,
            "file_path": self.file_path,
            "complexity": self.complexity,
            "lines_of_code": self.lines_of_code,
            "dependencies": self.dependencies
        }


class CodeEntityExtractor:
    """
    Service for extracting code entities from source files
    
    Features:
    - Extract functions, classes, methods from AST
    - Calculate cyclomatic complexity for each entity
    - Identify dependencies between entities (imports, calls, inheritance)
    - Build dependency graphs
    """
    
    def __init__(self, enable_optimization: bool = True):
        """
        Initialize code entity extractor
        
        Args:
            enable_optimization: Enable parallel parsing and caching (default: True)
        """
        self.parser_factory = ParserFactory()
        self.enable_optimization = enable_optimization
        if enable_optimization:
            self.optimized_parser = OptimizedParser()
        else:
            self.optimized_parser = None
    
    def extract_from_file(self, file_path: str, content: Optional[str] = None) -> Dict:
        """
        Extract all code entities from a single file
        
        Args:
            file_path: Path to the source file
            content: Optional file content (if already loaded)
        
        Returns:
            Dictionary containing:
            - entities: List of CodeEntity objects
            - parsed_file: ParsedFile object with full AST
            - metrics: Aggregated metrics
            - errors: List of parsing errors
            - parse_time: Time taken to parse (seconds)
        """
        # Use optimized parser if available
        if self.optimized_parser:
            parsed_file, parse_time = self.optimized_parser.parse_file(file_path, content)
        else:
            # Fallback to direct parser
            parser = self.parser_factory.get_parser_by_filename(file_path)
            if not parser:
                return {
                    "entities": [],
                    "parsed_file": None,
                    "metrics": {},
                    "errors": [f"Unsupported file type: {file_path}"],
                    "parse_time": 0.0
                }
            
            import time
            start_time = time.time()
            parsed_file = parser.parse_file(file_path, content)
            parse_time = time.time() - start_time
        
        if parsed_file.errors:
            return {
                "entities": [],
                "parsed_file": parsed_file,
                "metrics": {},
                "errors": parsed_file.errors,
                "parse_time": parse_time
            }
        
        # Extract entities
        entities = self._extract_entities_from_parsed(parsed_file)
        
        # Calculate aggregated metrics
        metrics = self._calculate_aggregated_metrics(entities, parsed_file)
        
        return {
            "entities": entities,
            "parsed_file": parsed_file,
            "metrics": metrics,
            "errors": [],
            "parse_time": parse_time
        }
    
    def extract_from_files(self, file_paths: List[str], use_parallel: bool = True) -> Dict:
        """
        Extract entities from multiple files and build dependency graph
        
        Args:
            file_paths: List of file paths to analyze
            use_parallel: Use parallel processing (default: True)
        
        Returns:
            Dictionary containing:
            - entities: List of all CodeEntity objects
            - parsed_files: List of ParsedFile objects
            - dependency_graph: DependencyGraph object
            - metrics: Aggregated metrics across all files
            - errors: List of errors by file
            - parse_times: Dictionary of parse times by file
            - total_parse_time: Total time for all parsing
        """
        all_entities = []
        parsed_files = []
        errors_by_file = {}
        parse_times = {}
        
        # Use optimized parallel parsing if available
        if self.optimized_parser and use_parallel and len(file_paths) > 1:
            import time
            start_time = time.time()
            
            # Parse all files in parallel
            results = self.optimized_parser.parse_files_parallel(file_paths)
            
            total_parse_time = time.time() - start_time
            
            # Process results
            for file_path, (parsed_file, parse_time) in results.items():
                parse_times[file_path] = parse_time
                
                if parsed_file.errors:
                    errors_by_file[file_path] = parsed_file.errors
                
                if parsed_file.module:
                    parsed_files.append(parsed_file)
                    entities = self._extract_entities_from_parsed(parsed_file)
                    all_entities.extend(entities)
        else:
            # Sequential processing
            import time
            start_time = time.time()
            
            for file_path in file_paths:
                result = self.extract_from_file(file_path)
                parse_times[file_path] = result.get("parse_time", 0.0)
                
                if result["errors"]:
                    errors_by_file[file_path] = result["errors"]
                
                if result["entities"]:
                    all_entities.extend(result["entities"])
                
                if result["parsed_file"]:
                    parsed_files.append(result["parsed_file"])
            
            total_parse_time = time.time() - start_time
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(parsed_files)
        
        # Calculate cross-file metrics
        metrics = self._calculate_cross_file_metrics(all_entities, dependency_graph)
        
        return {
            "entities": all_entities,
            "parsed_files": parsed_files,
            "dependency_graph": dependency_graph,
            "metrics": metrics,
            "errors": errors_by_file,
            "parse_times": parse_times,
            "total_parse_time": total_parse_time
        }
    
    def _extract_entities_from_parsed(self, parsed_file: ParsedFile) -> List[CodeEntity]:
        """
        Extract CodeEntity objects from a ParsedFile
        """
        entities = []
        module = parsed_file.module
        
        # Extract module-level functions
        for func in module.functions:
            entity = CodeEntity(
                name=func.name,
                entity_type="function",
                file_path=module.file_path,
                complexity=func.complexity,
                lines_of_code=func.lines_of_code,
                dependencies=func.calls
            )
            entities.append(entity)
        
        # Extract classes and their methods
        for cls in module.classes:
            # Add class entity
            class_complexity = sum(method.complexity for method in cls.methods)
            class_entity = CodeEntity(
                name=cls.name,
                entity_type="class",
                file_path=module.file_path,
                complexity=class_complexity,
                lines_of_code=cls.lines_of_code,
                dependencies=cls.base_classes
            )
            entities.append(class_entity)
            
            # Add method entities
            for method in cls.methods:
                method_entity = CodeEntity(
                    name=f"{cls.name}.{method.name}",
                    entity_type="method",
                    file_path=module.file_path,
                    complexity=method.complexity,
                    lines_of_code=method.lines_of_code,
                    dependencies=method.calls
                )
                entities.append(method_entity)
        
        return entities
    
    def _calculate_aggregated_metrics(
        self,
        entities: List[CodeEntity],
        parsed_file: ParsedFile
    ) -> Dict:
        """
        Calculate aggregated metrics for a file
        """
        if not entities:
            return {}
        
        complexities = [e.complexity for e in entities]
        
        return {
            "total_entities": len(entities),
            "total_functions": sum(1 for e in entities if e.entity_type == "function"),
            "total_classes": sum(1 for e in entities if e.entity_type == "class"),
            "total_methods": sum(1 for e in entities if e.entity_type == "method"),
            "avg_complexity": sum(complexities) / len(complexities),
            "max_complexity": max(complexities),
            "min_complexity": min(complexities),
            "total_complexity": sum(complexities),
            "lines_of_code": parsed_file.module.lines_of_code,
            "comment_lines": parsed_file.module.comment_lines,
            "comment_ratio": parsed_file.module.comment_ratio,
            "high_complexity_entities": [
                e.name for e in entities if e.complexity > 10
            ]
        }
    
    def _build_dependency_graph(self, parsed_files: List[ParsedFile]) -> DependencyGraph:
        """
        Build a dependency graph from multiple parsed files
        
        Identifies:
        - Import dependencies (module imports another module)
        - Call dependencies (function calls another function)
        - Inheritance dependencies (class inherits from another class)
        """
        graph = DependencyGraph()
        
        # Create a mapping of module names to parsed files
        module_map = {pf.module.name: pf for pf in parsed_files}
        
        # Add all modules as nodes
        for parsed in parsed_files:
            graph.nodes.append(parsed.module.name)
        
        # Process each file
        for parsed in parsed_files:
            source_module = parsed.module.name
            
            # Add import dependencies
            for imp in parsed.module.imports:
                target_module = imp.module_name
                
                # Check if target is in our analyzed files
                if target_module in module_map:
                    edge = DependencyEdge(
                        source=source_module,
                        target=target_module,
                        type="import",
                        weight=1.0
                    )
                    graph.edges.append(edge)
            
            # Add inheritance dependencies
            for cls in parsed.module.classes:
                for base_class in cls.base_classes:
                    # Try to find which module contains this base class
                    for other_parsed in parsed_files:
                        if other_parsed.module.name == source_module:
                            continue
                        
                        # Check if base class is defined in this module
                        if any(c.name == base_class for c in other_parsed.module.classes):
                            edge = DependencyEdge(
                                source=source_module,
                                target=other_parsed.module.name,
                                type="inheritance",
                                weight=0.8
                            )
                            graph.edges.append(edge)
                            break
            
            # Add call dependencies (simplified heuristic)
            all_functions = parsed.module.functions + [
                method for cls in parsed.module.classes for method in cls.methods
            ]
            
            for func in all_functions:
                for call in func.calls:
                    # Check if this call matches a function in another module
                    for other_parsed in parsed_files:
                        if other_parsed.module.name == source_module:
                            continue
                        
                        # Check if called function exists in other module
                        other_functions = other_parsed.module.functions + [
                            m for c in other_parsed.module.classes for m in c.methods
                        ]
                        
                        if any(f.name == call for f in other_functions):
                            edge = DependencyEdge(
                                source=source_module,
                                target=other_parsed.module.name,
                                type="call",
                                weight=0.5
                            )
                            graph.edges.append(edge)
                            break
        
        # Remove duplicate edges
        unique_edges = []
        seen = set()
        for edge in graph.edges:
            key = (edge.source, edge.target, edge.type)
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)
        
        graph.edges = unique_edges
        
        # Calculate graph metrics
        graph.metrics = self._calculate_graph_metrics(graph)
        
        return graph
    
    def _calculate_graph_metrics(self, graph: DependencyGraph) -> Dict:
        """
        Calculate metrics for the dependency graph
        """
        return {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "import_edges": sum(1 for e in graph.edges if e.type == "import"),
            "call_edges": sum(1 for e in graph.edges if e.type == "call"),
            "inheritance_edges": sum(1 for e in graph.edges if e.type == "inheritance"),
            "avg_dependencies_per_module": (
                len(graph.edges) / len(graph.nodes) if graph.nodes else 0
            )
        }
    
    def _calculate_cross_file_metrics(
        self,
        entities: List[CodeEntity],
        graph: DependencyGraph
    ) -> Dict:
        """
        Calculate metrics across all files
        """
        if not entities:
            return {}
        
        complexities = [e.complexity for e in entities]
        
        return {
            "total_files": len(set(e.file_path for e in entities)),
            "total_entities": len(entities),
            "total_functions": sum(1 for e in entities if e.entity_type == "function"),
            "total_classes": sum(1 for e in entities if e.entity_type == "class"),
            "total_methods": sum(1 for e in entities if e.entity_type == "method"),
            "avg_complexity": sum(complexities) / len(complexities),
            "max_complexity": max(complexities),
            "total_complexity": sum(complexities),
            "high_complexity_entities": [
                {"name": e.name, "complexity": e.complexity, "file": e.file_path}
                for e in entities if e.complexity > 10
            ],
            "graph_metrics": graph.metrics
        }
    
    def get_entity_dependencies(
        self,
        entity_name: str,
        entities: List[CodeEntity]
    ) -> List[str]:
        """
        Get all dependencies for a specific entity
        
        Args:
            entity_name: Name of the entity
            entities: List of all entities
        
        Returns:
            List of dependency names
        """
        for entity in entities:
            if entity.name == entity_name:
                return entity.dependencies
        
        return []
    
    def find_high_complexity_entities(
        self,
        entities: List[CodeEntity],
        threshold: int = 10
    ) -> List[CodeEntity]:
        """
        Find entities with complexity above threshold
        
        Args:
            entities: List of entities to search
            threshold: Complexity threshold (default: 10)
        
        Returns:
            List of high-complexity entities
        """
        return [e for e in entities if e.complexity > threshold]
    
    def get_entities_by_type(
        self,
        entities: List[CodeEntity],
        entity_type: str
    ) -> List[CodeEntity]:
        """
        Filter entities by type
        
        Args:
            entities: List of entities
            entity_type: Type to filter ('function', 'class', 'method')
        
        Returns:
            Filtered list of entities
        """
        return [e for e in entities if e.entity_type == entity_type]

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics from optimized parser
        
        Returns:
            Dictionary with cache statistics
        """
        if self.optimized_parser:
            return self.optimized_parser.get_cache_stats()
        return {"enabled": False}
    
    def get_performance_stats(self) -> Dict:
        """
        Get performance statistics from optimized parser
        
        Returns:
            Dictionary with performance metrics
        """
        if self.optimized_parser:
            return self.optimized_parser.get_performance_stats()
        return {"optimization_enabled": False}
    
    def clear_cache(self) -> None:
        """Clear the parser cache"""
        if self.optimized_parser:
            self.optimized_parser.clear_cache()
    
    def invalidate_cache(self, file_path: str) -> None:
        """
        Invalidate cache for a specific file
        
        Args:
            file_path: Path to the file to invalidate
        """
        if self.optimized_parser:
            self.optimized_parser.invalidate_cache(file_path)
