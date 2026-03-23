"""
Java AST Parser using tree-sitter
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
    PropertyNode,
    Location
)


class JavaParser(BaseASTParser):
    """
    Java parser using tree-sitter
    
    Parses Java source code and extracts classes, methods, imports, and dependencies.
    """
    
    def __init__(self):
        """Initialize Java parser with tree-sitter"""
        self.language = "java"
        self.parser = None
        self.available = False
        
        try:
            from tree_sitter import Language, Parser
            
            # Try to load Java language
            try:
                from tree_sitter_java import language
                java_language = Language(language())
                self.parser = Parser()
                self.parser.set_language(java_language)
                self.available = True
            except ImportError:
                # Java language bindings not available
                self.available = False
        except ImportError:
            # tree-sitter not available
            self.available = False
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse Java source file"""
        if not self.available:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language=self.language
                ),
                errors=["Parser not available. Install tree-sitter-java: pip install tree-sitter-java"]
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
            classes = self._extract_classes(root_node, content)
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
                "total_classes": len(classes),
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
                # Get the import path
                import_path = self._get_node_text(node, content).strip()
                # Remove 'import' keyword and semicolon
                import_path = import_path.replace('import', '').replace(';', '').strip()
                
                # Check if it's a static import
                is_static = 'static' in import_path
                if is_static:
                    import_path = import_path.replace('static', '').strip()
                
                # Extract module name and imported names
                if '.*' in import_path:
                    # Wildcard import
                    module_name = import_path.replace('.*', '')
                    imported_names = ['*']
                else:
                    # Specific import
                    parts = import_path.rsplit('.', 1)
                    if len(parts) == 2:
                        module_name = parts[0]
                        imported_names = [parts[1]]
                    else:
                        module_name = import_path
                        imported_names = []
                
                imports.append(ImportNode(
                    module_name=module_name,
                    imported_names=imported_names,
                    is_from_import=True,
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
    
    def _extract_classes(self, root_node: Any, content: str) -> List[ClassNode]:
        """Extract class definitions"""
        classes = []
        
        def visit_node(node):
            if node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
                class_node = self._parse_class(node, content)
                classes.append(class_node)
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(root_node)
        return classes
    
    def _parse_class(self, node: Any, content: str) -> ClassNode:
        """Parse a class definition"""
        # Get class name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        name = self._get_node_text(name_node, content) if name_node else "Unknown"
        
        methods = []
        properties = []
        base_classes = []
        decorators = []
        
        # Extract superclass and interfaces
        for child in node.children:
            if child.type == 'superclass':
                # extends clause
                for subchild in child.children:
                    if subchild.type == 'type_identifier':
                        base_classes.append(self._get_node_text(subchild, content))
            elif child.type == 'super_interfaces':
                # implements clause
                for subchild in child.children:
                    if subchild.type == 'type_identifier':
                        base_classes.append(self._get_node_text(subchild, content))
        
        # Extract modifiers (public, private, static, etc.)
        for child in node.children:
            if child.type == 'modifiers':
                modifier_text = self._get_node_text(child, content)
                if modifier_text:
                    decorators.append(modifier_text)
        
        # Extract class body
        body = None
        for child in node.children:
            if child.type in ['class_body', 'interface_body', 'enum_body']:
                body = child
                break
        
        if body:
            for child in body.children:
                if child.type == 'method_declaration':
                    func = self._parse_method(child, content)
                    methods.append(func)
                elif child.type == 'constructor_declaration':
                    func = self._parse_constructor(child, content)
                    methods.append(func)
                elif child.type == 'field_declaration':
                    props = self._parse_field(child, content)
                    properties.extend(props)
        
        # Get docstring (Javadoc comment)
        docstring = self._get_javadoc(node, content)
        
        return ClassNode(
            name=name,
            methods=methods,
            properties=properties,
            base_classes=base_classes,
            decorators=decorators,
            docstring=docstring,
            lines_of_code=node.end_point[0] - node.start_point[0] + 1,
            location=Location(
                file_path="",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_column=node.start_point[1],
                end_column=node.end_point[1]
            )
        )
    
    def _extract_functions(self, root_node: Any, content: str) -> List[FunctionNode]:
        """Extract top-level functions (rare in Java, but possible in some contexts)"""
        # Java typically doesn't have top-level functions, but we'll check anyway
        functions = []
        
        # In Java, all methods are inside classes, so this will typically return empty
        # We keep this for consistency with the base parser interface
        
        return functions
    
    def _parse_method(self, node: Any, content: str) -> FunctionNode:
        """Parse a method declaration"""
        # Get method name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        name = self._get_node_text(name_node, content) if name_node else "unknown"
        
        # Extract parameters
        parameters = []
        for child in node.children:
            if child.type == 'formal_parameters':
                parameters = self._parse_parameters(child, content)
                break
        
        # Get return type
        return_type = None
        for child in node.children:
            if child.type in ['type_identifier', 'void_type', 'integral_type', 'floating_point_type', 
                            'boolean_type', 'generic_type', 'array_type']:
                return_type = self._get_node_text(child, content)
                break
        
        # Extract modifiers
        decorators = []
        for child in node.children:
            if child.type == 'modifiers':
                modifier_text = self._get_node_text(child, content)
                if modifier_text:
                    decorators.append(modifier_text)
        
        # Calculate complexity
        complexity = self._calculate_complexity(node)
        
        # Calculate nesting depth
        nesting_depth = self._calculate_nesting(node)
        
        # Extract function calls
        calls = self._extract_calls(node, content)
        
        # Get docstring
        docstring = self._get_javadoc(node, content)
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            return_type=return_type,
            complexity=complexity,
            lines_of_code=node.end_point[0] - node.start_point[0] + 1,
            nesting_depth=nesting_depth,
            is_async=False,  # Java doesn't have async/await like Python/JS
            is_method=True,
            decorators=decorators,
            docstring=docstring,
            calls=calls,
            location=Location(
                file_path="",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_column=node.start_point[1],
                end_column=node.end_point[1]
            )
        )
    
    def _parse_constructor(self, node: Any, content: str) -> FunctionNode:
        """Parse a constructor declaration"""
        # Get constructor name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        name = self._get_node_text(name_node, content) if name_node else "constructor"
        
        # Extract parameters
        parameters = []
        for child in node.children:
            if child.type == 'formal_parameters':
                parameters = self._parse_parameters(child, content)
                break
        
        # Extract modifiers
        decorators = []
        for child in node.children:
            if child.type == 'modifiers':
                modifier_text = self._get_node_text(child, content)
                if modifier_text:
                    decorators.append(modifier_text)
        
        complexity = self._calculate_complexity(node)
        nesting_depth = self._calculate_nesting(node)
        calls = self._extract_calls(node, content)
        docstring = self._get_javadoc(node, content)
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            return_type=None,  # Constructors don't have return types
            complexity=complexity,
            lines_of_code=node.end_point[0] - node.start_point[0] + 1,
            nesting_depth=nesting_depth,
            is_async=False,
            is_method=True,
            decorators=decorators,
            docstring=docstring,
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
        """Parse method parameters"""
        parameters = []
        
        for child in params_node.children:
            if child.type == 'formal_parameter':
                # Get parameter type
                param_type = None
                param_name = None
                
                for subchild in child.children:
                    if subchild.type in ['type_identifier', 'integral_type', 'floating_point_type',
                                        'boolean_type', 'generic_type', 'array_type']:
                        param_type = self._get_node_text(subchild, content)
                    elif subchild.type == 'identifier':
                        param_name = self._get_node_text(subchild, content)
                
                if param_name:
                    parameters.append(ParameterNode(
                        name=param_name,
                        type_annotation=param_type
                    ))
        
        return parameters
    
    def _parse_field(self, field_node: Any, content: str) -> List[PropertyNode]:
        """Parse field declarations (can have multiple variables)"""
        properties = []
        
        # Get field type
        field_type = None
        for child in field_node.children:
            if child.type in ['type_identifier', 'integral_type', 'floating_point_type',
                            'boolean_type', 'generic_type', 'array_type']:
                field_type = self._get_node_text(child, content)
                break
        
        # Get variable declarators
        for child in field_node.children:
            if child.type == 'variable_declarator':
                # Get variable name
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        var_name = self._get_node_text(subchild, content)
                        properties.append(PropertyNode(
                            name=var_name,
                            type_annotation=field_type,
                            is_class_variable=True
                        ))
        
        return properties
    
    def _calculate_complexity(self, node: Any) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        
        def visit(n):
            nonlocal complexity
            # Decision points in Java
            if n.type in ['if_statement', 'while_statement', 'for_statement', 
                         'enhanced_for_statement', 'do_statement', 'switch_expression',
                         'catch_clause', 'ternary_expression', 'conditional_expression']:
                complexity += 1
            elif n.type == 'binary_expression':
                # Check for && and ||
                operator_text = self._get_node_text(n, "")
                if '&&' in operator_text or '||' in operator_text:
                    complexity += 1
            
            # Visit children
            for child in n.children:
                visit(child)
        
        visit(node)
        return complexity
    
    def _calculate_nesting(self, node: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        
        for child in node.children:
            if child.type in ['if_statement', 'while_statement', 'for_statement',
                            'enhanced_for_statement', 'do_statement', 'try_statement',
                            'synchronized_statement']:
                child_depth = self._calculate_nesting(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _extract_calls(self, node: Any, content: str) -> List[str]:
        """Extract method calls"""
        calls = []
        
        def visit(n):
            if n.type == 'method_invocation':
                # Get method name
                for child in n.children:
                    if child.type == 'identifier':
                        calls.append(self._get_node_text(child, content))
                        break
                    elif child.type == 'field_access':
                        # For chained calls like obj.method()
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                calls.append(self._get_node_text(subchild, content))
            
            # Visit children
            for child in n.children:
                visit(child)
        
        visit(node)
        return list(set(calls))
    
    def _get_javadoc(self, node: Any, content: str) -> Optional[str]:
        """Extract Javadoc comment if present"""
        # Look for comment node before this node
        # This is a simplified version - proper implementation would need to track comments
        return None
    
    def _get_node_text(self, node: Any, content: str) -> str:
        """Get text content of a tree-sitter node"""
        if node is None:
            return ""
        return content[node.start_byte:node.end_byte]
    
    # Base class method implementations
    def extract_classes(self, ast_tree) -> List[ClassNode]:
        """Extract classes - not used with tree-sitter approach"""
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
        """Count lines in Java file"""
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
            elif stripped.startswith('/*') or stripped.startswith('/**'):
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
