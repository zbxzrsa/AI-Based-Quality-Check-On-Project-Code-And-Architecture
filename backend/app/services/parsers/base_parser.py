"""
Base AST parser interface
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.schemas.ast_models import (
    ParsedFile,
    ModuleNode,
    ClassNode,
    FunctionNode,
    ImportNode,
    DependencyGraph
)


class BaseASTParser(ABC):
    """
    Abstract base class for AST parsers
    """
    
    @abstractmethod
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """
        Parse a source file and extract structure
        
        Args:
            file_path: Path to the source file
            content: Optional file content (if already loaded)
            
        Returns:
            ParsedFile with all extracted elements
        """
        pass
    
    @abstractmethod
    def extract_classes(self, ast_tree) -> List[ClassNode]:
        """Extract class definitions from AST"""
        pass
    
    @abstractmethod
    def extract_functions(self, ast_tree) -> List[FunctionNode]:
        """Extract function definitions from AST"""
        pass
    
    @abstractmethod
    def extract_imports(self, ast_tree) -> List[ImportNode]:
        """Extract import statements from AST"""
        pass
    
    @abstractmethod
    def calculate_complexity(self, node) -> int:
        """
        Calculate cyclomatic complexity of a code block
        
        Complexity = 1 + number of decision points (if, for, while, and, or, etc.)
        """
        pass
    
    def calculate_nesting_depth(self, node, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        return current_depth
    
    def count_lines(self, content: str) -> tuple[int, int, int]:
        """
        Count lines of code
        
        Returns:
            Tuple of (total_lines, code_lines, comment_lines, blank_lines)
        """
        lines = content.split('\n')
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        
        # This is language-specific, override in subclasses
        return total, total - blank, 0, blank
    
    def build_dependency_graph(self, parsed_files: List[ParsedFile]) -> DependencyGraph:
        """
        Build dependency graph from multiple parsed files
        """
        from app.schemas.ast_models import DependencyEdge
        
        graph = DependencyGraph()
        
        # Add all modules as nodes
        for parsed in parsed_files:
            graph.nodes.append(parsed.module.name)
        
        # Add import dependencies
        for parsed in parsed_files:
            source = parsed.module.name
            
            for imp in parsed.module.imports:
                target = imp.module_name
                if target in graph.nodes:
                    graph.edges.append(DependencyEdge(
                        source=source,
                        target=target,
                        type="import",
                        weight=1.0
                    ))
            
            # Add call dependencies
            for func in parsed.module.functions:
                for call in func.calls:
                    # Simple heuristic: check if call matches any known function
                    for other_parsed in parsed_files:
                        for other_func in other_parsed.module.functions:
                            if call == other_func.name:
                                graph.edges.append(DependencyEdge(
                                    source=source,
                                    target=other_parsed.module.name,
                                    type="call",
                                    weight=0.5
                                ))
        
        return graph
