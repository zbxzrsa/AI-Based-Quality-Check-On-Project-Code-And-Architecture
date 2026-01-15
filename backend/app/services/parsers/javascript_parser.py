"""
JavaScript/TypeScript AST Parser
Uses esprima for parsing
"""
import json
from typing import List, Optional
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
    JavaScript/TypeScript parser using esprima
    """
    
    def __init__(self):
        try:
            import esprima
            self.esprima = esprima
            self.available = True
        except ImportError:
            self.esprima = None
            self.available = False
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse JavaScript/TypeScript source file"""
        if not self.available:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language="javascript"
                ),
                errors=["esprima not installed. Install with: pip install esprima"]
            )
        
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Parse AST
            tree = self.esprima.parseScript(content, {
                'loc': True,
                'range': True,
                'comment': True
            })
            
            # Count lines
            total_lines, code_lines, comment_lines, blank_lines = self.count_lines(content)
            
            # Extract elements
            imports = self.extract_imports(tree)
            classes = self.extract_classes(tree)
            functions = self.extract_functions(tree)
            
            # Create module node
            module = ModuleNode(
                name=Path(file_path).stem,
                file_path=file_path,
                language="javascript",
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
                "max_complexity": max((f.complexity for f in functions), default=0)
            }
            
            return ParsedFile(module=module, metrics=metrics, errors=[])
            
        except Exception as e:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language="javascript"
                ),
                errors=[f"Parse error: {str(e)}"]
            )
    
    def extract_classes(self, ast_tree) -> List[ClassNode]:
        """Extract class definitions"""
        classes = []
        
        def visit_node(node):
            if isinstance(node, dict):
                if node.get('type') == 'ClassDeclaration':
                    class_node = self._parse_class(node)
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
    
    def _parse_class(self, node: dict) -> ClassNode:
        """Parse a class definition"""
        name = node.get('id', {}).get('name', 'Unknown')
        
        methods = []
        properties = []
        
        # Extract class body
        body = node.get('body', {}).get('body', [])
        for item in body:
            if item.get('type') == 'MethodDefinition':
                func = self._parse_function_from_method(item)
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
    
    def extract_functions(self, ast_tree) -> List[FunctionNode]:
        """Extract top-level function definitions"""
        functions = []
        
        def visit_node(node, depth=0):
            if isinstance(node, dict):
                node_type = node.get('type')
                
                # Only get top-level functions
                if depth == 1 and node_type == 'FunctionDeclaration':
                    func = self._parse_function(node)
                    functions.append(func)
                
                # Visit children
                if node_type == 'Program':
                    for item in node.get('body', []):
                        visit_node(item, depth + 1)
        
        visit_node(ast_tree.toDict())
        return functions
    
    def _parse_function(self, node: dict) -> FunctionNode:
        """Parse a function declaration"""
        name = node.get('id', {}).get('name', 'anonymous')
        
        # Extract parameters
        parameters = []
        for param in node.get('params', []):
            param_name = param.get('name', 'unknown')
            parameters.append(ParameterNode(name=param_name))
        
        # Calculate complexity
        complexity = self.calculate_complexity(node)
        
        # Extract function calls
        calls = self._extract_calls(node)
        
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
    
    def _parse_function_from_method(self, node: dict) -> FunctionNode:
        """Parse a method definition"""
        name = node.get('key', {}).get('name', 'unknown')
        func_node = node.get('value', {})
        
        # Extract parameters
        parameters = []
        for param in func_node.get('params', []):
            param_name = param.get('name', 'unknown')
            parameters.append(ParameterNode(name=param_name))
        
        complexity = self.calculate_complexity(func_node)
        calls = self._extract_calls(func_node)
        
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
    
    def extract_imports(self, ast_tree) -> List[ImportNode]:
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
    
    def calculate_complexity(self, node) -> int:
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
    
    def _extract_calls(self, node) -> List[str]:
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
