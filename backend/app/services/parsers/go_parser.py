"""
Go AST Parser using tree-sitter
"""
from typing import List, Optional, Any
from pathlib import Path

from app.services.parsers.base_parser import BaseASTParser
from app.schemas.ast_models import (
    ParsedFile,
    ModuleNode,
    ClassNode,
    FunctionNode,
    ImportNode,
    ParameterNode,
    Location
)


class GoParser(BaseASTParser):
    """
    Go parser using tree-sitter
    
    Parses Go source code and extracts functions, imports, and dependencies.
    Note: Go doesn't have classes, so class extraction returns empty list.
    """
    
    def __init__(self):
        """Initialize Go parser with tree-sitter"""
        self.language = "go"
        self.parser = None
        self.available = False
        
        try:
            from tree_sitter import Language, Parser
            
            # Try to load Go language
            try:
                from tree_sitter_go import language
                go_language = Language(language())
                self.parser = Parser()
                self.parser.set_language(go_language)
                self.available = True
            except ImportError:
                # Go language bindings not available
                self.available = False
        except ImportError:
            # tree-sitter not available
            self.available = False
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse Go source file"""
        if not self.available:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language=self.language
                ),
                errors=["Parser not available. Install tree-sitter-go: pip install tree-sitter-go"]
            )
        
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Parse with tree-sitter
            tree = self.parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            # Count lines
            total_lines, code_lines, comment_lines, blank_lines = self.count_lines(content)
            
            # Extract elements
            imports = self._extract_imports(root_node, content)
            classes = []  # Go doesn't have classes
            functions = self._extract_functions(root_node, content)
            
            # Create module node
            module = ModuleNode(
                name=Path(file_path).stem,
                file_path=file_path,
                language=self.language,
                imports=imports,
                classes=classes,
                functions=functions,
                lines_of_code=code_lines,
                comment_lines=comment_lines,
                blank_lines=blank_lines,
                comment_ratio=comment_lines / total_lines if total_lines > 0 else 0.0
            )
            
            # Calculate metrics
            metrics = {
                "total_classes": 0,
                "total_functions": len(functions),
                "total_imports": len(imports),
                "avg_complexity": sum(f.complexity for f in functions) / len(functions) if functions else 0,
                "max_complexity": max((f.complexity for f in functions), default=0),
                "max_nesting": max((f.nesting_depth for f in functions), default=0)
            }
            
            return ParsedFile(module=module, metrics=metrics, errors=[])
            
        except Exception as e:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language=self.language
                ),
                errors=[f"Parse error: {str(e)}"]
            )
    
    def _extract_imports(self, root_node: Any, content: str) -> List[ImportNode]:
        """Extract import statements"""
        imports = []
        
        def visit_node(node):
            if node.type == 'import_declaration':
                # Handle import specs
                for child in node.children:
                    if child.type == 'import_spec':
                        # Get import path
                        path_node = None
                        alias_node = None
                        
                        for subchild in child.children:
                            if subchild.type == 'interpreted_string_literal':
                                path_node = subchild
                            elif subchild.type == 'package_identifier':
                                alias_node = subchild
                        
                        if path_node:
                            import_path = self._get_node_text(path_node, content).strip('"')
                            alias = self._get_node_text(alias_node, content) if alias_node else None
                            
                            imports.append(ImportNode(
                                module_name=import_path,
                                imported_names=[import_path.split('/')[-1]],
                                is_from_import=False,
                                alias=alias,
                                location=Location(
                                    file_path="",
                                    start_line=child.start_point[0] + 1,
                                    end_line=child.end_point[0] + 1,
                                    start_column=child.start_point[1],
                                    end_column=child.end_point[1]
                                )
                            ))
                    elif child.type == 'interpreted_string_literal':
                        # Single import without spec
                        import_path = self._get_node_text(child, content).strip('"')
                        imports.append(ImportNode(
                            module_name=import_path,
                            imported_names=[import_path.split('/')[-1]],
                            is_from_import=False,
                            location=Location(
                                file_path="",
                                start_line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                                start_column=node.start_point[1],
                                end_column=node.end_point[1]
                            )
                        ))
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(root_node)
        return imports
    
    def _extract_functions(self, root_node: Any, content: str) -> List[FunctionNode]:
        """Extract function declarations"""
        functions = []
        
        def visit_node(node):
            if node.type == 'function_declaration':
                func = self._parse_function(node, content)
                functions.append(func)
            elif node.type == 'method_declaration':
                func = self._parse_method(node, content)
                functions.append(func)
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(root_node)
        return functions
    
    def _parse_function(self, node: Any, content: str) -> FunctionNode:
        """Parse a function declaration"""
        # Get function name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        name = self._get_node_text(name_node, content) if name_node else "unknown"
        
        # Extract parameters
        parameters = []
        return_type = None
        
        for child in node.children:
            if child.type == 'parameter_list':
                parameters = self._parse_parameters(child, content)
            elif child.type == 'parameter_declaration':
                # Return type
                return_type = self._get_node_text(child, content)
        
        # Calculate complexity
        complexity = self._calculate_complexity(node)
        
        # Calculate nesting depth
        nesting_depth = self._calculate_nesting(node)
        
        # Extract function calls
        calls = self._extract_calls(node, content)
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            return_type=return_type,
            complexity=complexity,
            lines_of_code=node.end_point[0] - node.start_point[0] + 1,
            nesting_depth=nesting_depth,
            is_async=False,  # Go uses goroutines, not async/await
            is_method=False,
            calls=calls,
            location=Location(
                file_path="",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_column=node.start_point[1],
                end_column=node.end_point[1]
            )
        )
    
    def _parse_method(self, node: Any, content: str) -> FunctionNode:
        """Parse a method declaration (function with receiver)"""
        # Get method name
        name_node = None
        for child in node.children:
            if child.type == 'field_identifier':
                name_node = child
                break
        
        name = self._get_node_text(name_node, content) if name_node else "unknown"
        
        # Extract parameters
        parameters = []
        return_type = None
        
        for child in node.children:
            if child.type == 'parameter_list':
                parameters = self._parse_parameters(child, content)
            elif child.type == 'parameter_declaration':
                return_type = self._get_node_text(child, content)
        
        complexity = self._calculate_complexity(node)
        nesting_depth = self._calculate_nesting(node)
        calls = self._extract_calls(node, content)
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            return_type=return_type,
            complexity=complexity,
            lines_of_code=node.end_point[0] - node.start_point[0] + 1,
            nesting_depth=nesting_depth,
            is_async=False,
            is_method=True,
            calls=calls,
            location=Location(
                file_path="",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_column=node.start_point[1],
                end_column=node.end_point[1]
            )
        )
    
    def _parse_parameters(self, params_node: Any, content: str) -> List[ParameterNode]:
        """Parse function parameters"""
        parameters = []
        
        for child in params_node.children:
            if child.type == 'parameter_declaration':
                # Get parameter name and type
                param_name = None
                param_type = None
                
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param_name = self._get_node_text(subchild, content)
                    elif subchild.type in ['type_identifier', 'pointer_type', 'slice_type', 
                                          'array_type', 'map_type', 'interface_type']:
                        param_type = self._get_node_text(subchild, content)
                
                if param_name:
                    parameters.append(ParameterNode(
                        name=param_name,
                        type_annotation=param_type
                    ))
        
        return parameters
    
    def _calculate_complexity(self, node: Any) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        
        def visit(n):
            nonlocal complexity
            # Decision points in Go
            if n.type in ['if_statement', 'for_statement', 'switch_statement',
                         'type_switch_statement', 'select_statement']:
                complexity += 1
            elif n.type == 'case_clause':
                complexity += 1
            elif n.type == 'binary_expression':
                # Check for && and ||
                operator_node = None
                for child in n.children:
                    if child.type in ['&&', '||']:
                        complexity += 1
                        break
            
            # Visit children
            for child in n.children:
                visit(child)
        
        visit(node)
        return complexity
    
    def _calculate_nesting(self, node: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        
        for child in node.children:
            if child.type in ['if_statement', 'for_statement', 'switch_statement',
                            'type_switch_statement', 'select_statement']:
                child_depth = self._calculate_nesting(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _extract_calls(self, node: Any, content: str) -> List[str]:
        """Extract function calls"""
        calls = []
        
        def visit(n):
            if n.type == 'call_expression':
                # Get function name
                for child in n.children:
                    if child.type == 'identifier':
                        calls.append(self._get_node_text(child, content))
                        break
                    elif child.type == 'selector_expression':
                        # For method calls like obj.Method()
                        for subchild in child.children:
                            if subchild.type == 'field_identifier':
                                calls.append(self._get_node_text(subchild, content))
            
            # Visit children
            for child in n.children:
                visit(child)
        
        visit(node)
        return list(set(calls))
    
    def _get_node_text(self, node: Any, content: str) -> str:
        """Get text content of a tree-sitter node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]
    
    # Base class method implementations
    def extract_classes(self, ast_tree) -> List[ClassNode]:
        """Extract classes - Go doesn't have classes"""
        return []
    
    def extract_functions(self, ast_tree) -> List[FunctionNode]:
        """Extract functions - not used with tree-sitter approach"""
        return []
    
    def extract_imports(self, ast_tree) -> List[ImportNode]:
        """Extract imports - not used with tree-sitter approach"""
        return []
    
    def calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity"""
        return self._calculate_complexity(node)
    
    def count_lines(self, content: str) -> tuple[int, int, int, int]:
        """Count lines in Go file"""
        lines = content.split('\n')
        total = len(lines)
        blank = 0
        comment = 0
        code = 0
        
        in_block_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                blank += 1
            elif stripped.startswith('//'):
                comment += 1
            elif stripped.startswith('/*') and stripped.endswith('*/'):
                comment += 1
            elif stripped.startswith('/*'):
                comment += 1
                in_block_comment = True
            elif stripped.endswith('*/'):
                comment += 1
                in_block_comment = False
            elif in_block_comment:
                comment += 1
            else:
                code += 1
        
        return total, code, comment, blank

