"""
JavaScript/TypeScript AST Parser
Uses tree-sitter for parsing
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


class JavaScriptParser(BaseASTParser):
    """
    JavaScript/TypeScript parser using tree-sitter
    
    Supports both JavaScript and TypeScript through tree-sitter's
    language-specific parsers.
    """
    
    def __init__(self, language: str = "javascript"):
        """
        Initialize parser with specified language
        
        Args:
            language: Either "javascript" or "typescript"
        """
        self.language = language.lower()
        self.parser = None
        self.tree_sitter = None
        self.available = False
        
        try:
            from tree_sitter import Language, Parser
            self.tree_sitter = __import__('tree_sitter')
            
            # Try to load the language
            # Note: This requires tree-sitter language bindings to be built
            # For now, we'll use a fallback to esprima if tree-sitter languages aren't available
            try:
                if self.language == "typescript":
                    # Try to load TypeScript language
                    from tree_sitter_typescript import language_typescript
                    ts_language = Language(language_typescript())
                    self.parser = Parser()
                    self.parser.set_language(ts_language)
                    self.available = True
                else:
                    # Try to load JavaScript language
                    from tree_sitter_javascript import language
                    js_language = Language(language())
                    self.parser = Parser()
                    self.parser.set_language(js_language)
                    self.available = True
            except ImportError:
                # Fallback to esprima if tree-sitter languages not available
                try:
                    import esprima
                    self.esprima = esprima
                    self.available = True
                    self.use_esprima = True
                except ImportError:
                    self.esprima = None
                    self.use_esprima = False
                    self.available = False
        except ImportError:
            # Try esprima as fallback
            try:
                import esprima
                self.esprima = esprima
                self.available = True
                self.use_esprima = True
            except ImportError:
                self.esprima = None
                self.use_esprima = False
                self.available = False
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse JavaScript/TypeScript source file"""
        if not self.available:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language=self.language
                ),
                errors=["Parser not available. Install tree-sitter or esprima: pip install tree-sitter esprima"]
            )
        
        # Use esprima fallback if tree-sitter not available
        if hasattr(self, 'use_esprima') and self.use_esprima:
            return self._parse_with_esprima(file_path, content)
        
        # Use tree-sitter parser
        return self._parse_with_tree_sitter(file_path, content)
    
    def _parse_with_tree_sitter(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse using tree-sitter"""
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Parse with tree-sitter
            tree = self.parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node
            
            # Count lines
            total_lines, code_lines, comment_lines, blank_lines = self.count_lines(content)
            
            # Extract elements using tree-sitter
            imports = self._extract_imports_tree_sitter(root_node, content)
            classes = self._extract_classes_tree_sitter(root_node, content)
            functions = self._extract_functions_tree_sitter(root_node, content)
            
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
    
    def _parse_with_esprima(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse using esprima (fallback)"""
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Parse AST
            tree = self.esprima.parseScript(content, {
                'loc': True,
                'range': True,
                'comment': True,
                'tolerant': True  # Continue parsing even with errors
            })
            
            # Count lines
            total_lines, code_lines, comment_lines, blank_lines = self.count_lines(content)
            
            # Extract elements using esprima methods
            imports = self._extract_imports_esprima(tree)
            classes = self._extract_classes_esprima(tree)
            functions = self._extract_functions_esprima(tree)
            
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
    
    # Tree-sitter extraction methods
    def _extract_imports_tree_sitter(self, root_node: Any, content: str) -> List[ImportNode]:
        """Extract imports using tree-sitter"""
        imports = []
        
        def visit_node(node):
            if node.type == 'import_statement':
                # Extract module name from source
                source_node = node.child_by_field_name('source')
                if source_node:
                    module_name = self._get_node_text(source_node, content).strip('"\'')
                    
                    # Extract imported names
                    imported_names = []
                    import_clause = node.child_by_field_name('import_clause')
                    if import_clause:
                        for child in import_clause.children:
                            if child.type == 'identifier':
                                imported_names.append(self._get_node_text(child, content))
                            elif child.type == 'named_imports':
                                for spec in child.children:
                                    if spec.type == 'import_specifier':
                                        name_node = spec.child_by_field_name('name')
                                        if name_node:
                                            imported_names.append(self._get_node_text(name_node, content))
                    
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
    
    def _extract_classes_tree_sitter(self, root_node: Any, content: str) -> List[ClassNode]:
        """Extract classes using tree-sitter"""
        classes = []
        
        def visit_node(node):
            if node.type == 'class_declaration':
                class_node = self._parse_class_tree_sitter(node, content)
                classes.append(class_node)
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(root_node)
        return classes
    
    def _parse_class_tree_sitter(self, node: Any, content: str) -> ClassNode:
        """Parse a class using tree-sitter"""
        # Get class name
        name_node = node.child_by_field_name('name')
        name = self._get_node_text(name_node, content) if name_node else "Unknown"
        
        methods = []
        properties = []
        base_classes = []
        
        # Extract heritage (base classes)
        heritage = node.child_by_field_name('heritage')
        if heritage:
            for child in heritage.children:
                if child.type == 'identifier':
                    base_classes.append(self._get_node_text(child, content))
        
        # Extract class body
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                if child.type == 'method_definition':
                    func = self._parse_method_tree_sitter(child, content)
                    methods.append(func)
                elif child.type in ['field_definition', 'public_field_definition']:
                    prop_name_node = child.child_by_field_name('property')
                    if prop_name_node:
                        properties.append(PropertyNode(
                            name=self._get_node_text(prop_name_node, content),
                            is_class_variable=True
                        ))
        
        return ClassNode(
            name=name,
            methods=methods,
            properties=properties,
            base_classes=base_classes,
            location=Location(
                file_path="",
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_column=node.start_point[1],
                end_column=node.end_point[1]
            )
        )
    
    def _extract_functions_tree_sitter(self, root_node: Any, content: str) -> List[FunctionNode]:
        """Extract top-level functions using tree-sitter"""
        functions = []
        
        # Only get direct children that are functions
        for child in root_node.children:
            if child.type in ['function_declaration', 'function']:
                func = self._parse_function_tree_sitter(child, content)
                functions.append(func)
        
        return functions
    
    def _parse_function_tree_sitter(self, node: Any, content: str) -> FunctionNode:
        """Parse a function using tree-sitter"""
        # Get function name
        name_node = node.child_by_field_name('name')
        name = self._get_node_text(name_node, content) if name_node else "anonymous"
        
        # Extract parameters
        parameters = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in ['identifier', 'required_parameter', 'optional_parameter']:
                    param_name = self._get_node_text(child, content)
                    # Remove type annotations if present
                    if ':' in param_name:
                        param_name = param_name.split(':')[0].strip()
                    parameters.append(ParameterNode(name=param_name))
        
        # Calculate complexity
        complexity = self._calculate_complexity_tree_sitter(node)
        
        # Calculate nesting depth
        nesting_depth = self._calculate_nesting_tree_sitter(node)
        
        # Extract function calls
        calls = self._extract_calls_tree_sitter(node, content)
        
        # Check if async
        is_async = False
        for child in node.children:
            if child.type == 'async':
                is_async = True
                break
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            complexity=complexity,
            nesting_depth=nesting_depth,
            is_async=is_async,
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
    
    def _parse_method_tree_sitter(self, node: Any, content: str) -> FunctionNode:
        """Parse a method using tree-sitter"""
        # Get method name
        name_node = node.child_by_field_name('name')
        name = self._get_node_text(name_node, content) if name_node else "unknown"
        
        # Extract parameters
        parameters = []
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in ['identifier', 'required_parameter', 'optional_parameter']:
                    param_name = self._get_node_text(child, content)
                    if ':' in param_name:
                        param_name = param_name.split(':')[0].strip()
                    parameters.append(ParameterNode(name=param_name))
        
        complexity = self._calculate_complexity_tree_sitter(node)
        nesting_depth = self._calculate_nesting_tree_sitter(node)
        calls = self._extract_calls_tree_sitter(node, content)
        
        # Check if async
        is_async = False
        for child in node.children:
            if child.type == 'async':
                is_async = True
                break
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            complexity=complexity,
            nesting_depth=nesting_depth,
            is_async=is_async,
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
    
    def _calculate_complexity_tree_sitter(self, node: Any) -> int:
        """Calculate cyclomatic complexity using tree-sitter"""
        complexity = 1
        
        def visit(n):
            nonlocal complexity
            # Decision points
            if n.type in ['if_statement', 'while_statement', 'for_statement', 
                         'for_in_statement', 'switch_case', 'catch_clause',
                         'conditional_expression', 'ternary_expression']:
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
    
    def _calculate_nesting_tree_sitter(self, node: Any, current_depth: int = 0) -> int:
        """Calculate nesting depth using tree-sitter"""
        max_depth = current_depth
        
        for child in node.children:
            if child.type in ['if_statement', 'while_statement', 'for_statement',
                            'for_in_statement', 'try_statement', 'with_statement']:
                child_depth = self._calculate_nesting_tree_sitter(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _extract_calls_tree_sitter(self, node: Any, content: str) -> List[str]:
        """Extract function calls using tree-sitter"""
        calls = []
        
        def visit(n):
            if n.type == 'call_expression':
                function_node = n.child_by_field_name('function')
                if function_node:
                    if function_node.type == 'identifier':
                        calls.append(self._get_node_text(function_node, content))
                    elif function_node.type == 'member_expression':
                        property_node = function_node.child_by_field_name('property')
                        if property_node:
                            calls.append(self._get_node_text(property_node, content))
            
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
        """Extract classes - delegates to appropriate implementation"""
        if hasattr(self, 'use_esprima') and self.use_esprima:
            return self._extract_classes_esprima(ast_tree)
        return []
    
    def extract_functions(self, ast_tree) -> List[FunctionNode]:
        """Extract functions - delegates to appropriate implementation"""
        if hasattr(self, 'use_esprima') and self.use_esprima:
            return self._extract_functions_esprima(ast_tree)
        return []
    
    def extract_imports(self, ast_tree) -> List[ImportNode]:
        """Extract imports - delegates to appropriate implementation"""
        if hasattr(self, 'use_esprima') and self.use_esprima:
            return self._extract_imports_esprima(ast_tree)
        return []
    
    def calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity"""
        if hasattr(self, 'use_esprima') and self.use_esprima:
            return self._calculate_complexity_esprima(node)
        return 1
    
    # Esprima extraction methods (fallback)
    def _extract_classes_esprima(self, ast_tree) -> List[ClassNode]:
        """Extract class definitions"""
        classes = []
        
        def visit_node(node):
            if isinstance(node, dict):
                if node.get('type') == 'ClassDeclaration':
                    class_node = self._parse_class_esprima(node)
                    classes.append(class_node)
                
                # Recursively visit children
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        visit_node(value)
            elif isinstance(node, list):
                for item in node:
                    visit_node(item)
        
        visit_node(ast_tree.toDict())
        return classes
    
    def _parse_class_esprima(self, node: dict) -> ClassNode:
        """Parse a class definition"""
        name = node.get('id', {}).get('name', 'Unknown')
        
        methods = []
        properties = []
        
        # Extract class body
        body = node.get('body', {}).get('body', [])
        for item in body:
            if item.get('type') == 'MethodDefinition':
                func = self._parse_function_from_method_esprima(item)
                methods.append(func)
            elif item.get('type') == 'PropertyDefinition':
                prop = PropertyNode(
                    name=item.get('key', {}).get('name', 'unknown'),
                    is_class_variable=item.get('static', False)
                )
                properties.append(prop)
        
        # Extract base class
        base_classes = []
        if node.get('superClass'):
            base_name = node['superClass'].get('name', 'Unknown')
            base_classes.append(base_name)
        
        loc = node.get('loc', {})
        
        return ClassNode(
            name=name,
            methods=methods,
            properties=properties,
            base_classes=base_classes,
            location=Location(
                file_path="",
                start_line=loc.get('start', {}).get('line', 1),
                end_line=loc.get('end', {}).get('line', 1)
            )
        )
    
    def _extract_functions_esprima(self, ast_tree) -> List[FunctionNode]:
        """Extract top-level function definitions"""
        functions = []
        
        def visit_node(node, depth=0):
            if isinstance(node, dict):
                node_type = node.get('type')
                
                # Only get top-level functions
                if depth == 1 and node_type == 'FunctionDeclaration':
                    func = self._parse_function_esprima(node)
                    functions.append(func)
                
                # Visit children
                if node_type == 'Program':
                    for item in node.get('body', []):
                        visit_node(item, depth + 1)
        
        visit_node(ast_tree.toDict())
        return functions
    
    def _parse_function_esprima(self, node: dict) -> FunctionNode:
        """Parse a function declaration"""
        name = node.get('id', {}).get('name', 'anonymous')
        
        # Extract parameters
        parameters = []
        for param in node.get('params', []):
            param_name = param.get('name', 'unknown')
            parameters.append(ParameterNode(name=param_name))
        
        # Calculate complexity
        complexity = self._calculate_complexity_esprima(node)
        
        # Extract function calls
        calls = self._extract_calls_esprima(node)
        
        loc = node.get('loc', {})
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            complexity=complexity,
            is_async=node.get('async', False),
            is_method=False,
            calls=calls,
            location=Location(
                file_path="",
                start_line=loc.get('start', {}).get('line', 1),
                end_line=loc.get('end', {}).get('line', 1)
            )
        )
    
    def _parse_function_from_method_esprima(self, node: dict) -> FunctionNode:
        """Parse a method definition"""
        name = node.get('key', {}).get('name', 'unknown')
        func_node = node.get('value', {})
        
        # Extract parameters
        parameters = []
        for param in func_node.get('params', []):
            param_name = param.get('name', 'unknown')
            parameters.append(ParameterNode(name=param_name))
        
        complexity = self._calculate_complexity_esprima(func_node)
        calls = self._extract_calls_esprima(func_node)
        
        loc = node.get('loc', {})
        
        return FunctionNode(
            name=name,
            parameters=parameters,
            complexity=complexity,
            is_async=func_node.get('async', False),
            is_method=True,
            calls=calls,
            location=Location(
                file_path="",
                start_line=loc.get('start', {}).get('line', 1),
                end_line=loc.get('end', {}).get('line', 1)
            )
        )
    
    def _extract_imports_esprima(self, ast_tree) -> List[ImportNode]:
        """Extract import statements"""
        imports = []
        
        def visit_node(node):
            if isinstance(node, dict):
                node_type = node.get('type')
                
                if node_type == 'ImportDeclaration':
                    module_name = node.get('source', {}).get('value', '')
                    imported_names = []
                    
                    for spec in node.get('specifiers', []):
                        if spec.get('type') == 'ImportSpecifier':
                            imported_names.append(spec.get('imported', {}).get('name', ''))
                        elif spec.get('type') == 'ImportDefaultSpecifier':
                            imported_names.append('default')
                    
                    loc = node.get('loc', {})
                    imports.append(ImportNode(
                        module_name=module_name,
                        imported_names=imported_names,
                        is_from_import=True,
                        location=Location(
                            file_path="",
                            start_line=loc.get('start', {}).get('line', 1),
                            end_line=loc.get('end', {}).get('line', 1)
                        )
                    ))
                
                # Recursively visit children
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        visit_node(value)
            elif isinstance(node, list):
                for item in node:
                    visit_node(item)
        
        visit_node(ast_tree.toDict())
        return imports
    
    def _calculate_complexity_esprima(self, node) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        
        def visit(n):
            nonlocal complexity
            if isinstance(n, dict):
                node_type = n.get('type')
                
                # Decision points
                if node_type in ['IfStatement', 'ConditionalExpression', 'WhileStatement',
                                'ForStatement', 'ForInStatement', 'ForOfStatement',
                                'CaseClause', 'CatchClause']:
                    complexity += 1
                elif node_type == 'LogicalExpression':
                    if n.get('operator') in ['&&', '||']:
                        complexity += 1
                
                # Visit children
                for value in n.values():
                    if isinstance(value, (dict, list)):
                        visit(value)
            elif isinstance(n, list):
                for item in n:
                    visit(item)
        
        visit(node)
        return complexity
    
    def _extract_calls_esprima(self, node) -> List[str]:
        """Extract function calls"""
        calls = []
        
        def visit(n):
            if isinstance(n, dict):
                if n.get('type') == 'CallExpression':
                    callee = n.get('callee', {})
                    if callee.get('type') == 'Identifier':
                        calls.append(callee.get('name', ''))
                    elif callee.get('type') == 'MemberExpression':
                        prop = callee.get('property', {})
                        if prop.get('type') == 'Identifier':
                            calls.append(prop.get('name', ''))
                
                # Visit children
                for value in n.values():
                    if isinstance(value, (dict, list)):
                        visit(value)
            elif isinstance(n, list):
                for item in n:
                    visit(item)
        
        visit(node)
        return list(set(calls))
    
    def count_lines(self, content: str) -> tuple[int, int, int, int]:
        """Count lines in JavaScript file"""
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
            elif '/*' in stripped and '*/' in stripped:
                comment += 1
            elif '/*' in stripped:
                comment += 1
                in_block_comment = True
            elif '*/' in stripped:
                comment += 1
                in_block_comment = False
            elif in_block_comment:
                comment += 1
            else:
                code += 1
        
        return total, code, comment, blank
