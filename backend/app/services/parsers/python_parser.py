"""
Python AST Parser
Uses Python's built-in ast module
"""
import ast
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


class PythonASTParser(BaseASTParser):
    """
    Python AST parser using built-in ast module
    """
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> ParsedFile:
        """Parse Python source file"""
        try:
            if content is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Parse AST
            tree = ast.parse(content, filename=file_path)
            
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
                language="python",
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
            
        except SyntaxError as e:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language="python"
                ),
                errors=[f"Syntax error at line {e.lineno}: {e.msg}"]
            )
        except Exception as e:
            return ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language="python"
                ),
                errors=[f"Parse error: {str(e)}"]
            )
    
    def extract_classes(self, ast_tree) -> List[ClassNode]:
        """Extract class definitions"""
        classes = []
        
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.ClassDef):
                class_node = self._parse_class(node)
                classes.append(class_node)
        
        return classes
    
    def _parse_class(self, node: ast.ClassDef) -> ClassNode:
        """Parse a class definition"""
        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                func = self._parse_function(item, is_method=True)
                methods.append(func)
        
        # Extract properties
        properties = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign):  # Type-annotated assignment
                prop = PropertyNode(
                    name=item.target.id if isinstance(item.target, ast.Name) else str(item.target),
                    type_annotation=ast.unparse(item.annotation) if item.annotation else None,
                    is_class_variable=True
                )
                properties.append(prop)
        
        # Extract base classes
        base_classes = [ast.unparse(base) for base in node.bases]
        
        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        return ClassNode(
            name=node.name,
            methods=methods,
            properties=properties,
            base_classes=base_classes,
            decorators=decorators,
            docstring=docstring,
            lines_of_code=node.end_lineno - node.lineno + 1 if node.end_lineno else 0,
            location=Location(
                file_path="",  # Set by caller
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                start_column=node.col_offset,
                end_column=node.end_col_offset or node.col_offset
            )
        )
    
    def extract_functions(self, ast_tree) -> List[FunctionNode]:
        """Extract top-level function definitions"""
        functions = []
        
        for node in ast_tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func = self._parse_function(node, is_method=False)
                functions.append(func)
        
        return functions
    
    def _parse_function(self, node, is_method: bool = False) -> FunctionNode:
        """Parse a function definition"""
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param = ParameterNode(
                name=arg.arg,
                type_annotation=ast.unparse(arg.annotation) if arg.annotation else None
            )
            parameters.append(param)
        
        # Extract default values
        defaults = node.args.defaults
        if defaults:
            offset = len(parameters) - len(defaults)
            for i, default in enumerate(defaults):
                parameters[offset + i].default_value = ast.unparse(default)
        
        # Get return type
        return_type = ast.unparse(node.returns) if node.returns else None
        
        # Calculate complexity
        complexity = self.calculate_complexity(node)
        
        # Calculate nesting depth
        nesting_depth = self._calculate_nesting_depth(node)
        
        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]
        
        # Extract function calls
        calls = self._extract_calls(node)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        return FunctionNode(
            name=node.name,
            parameters=parameters,
            return_type=return_type,
            complexity=complexity,
            lines_of_code=node.end_lineno - node.lineno + 1 if node.end_lineno else 0,
            nesting_depth=nesting_depth,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            decorators=decorators,
            docstring=docstring,
            calls=calls,
            location=Location(
                file_path="",
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                start_column=node.col_offset,
                end_column=node.end_col_offset or node.col_offset
            )
        )
    
    def extract_imports(self, ast_tree) -> List[ImportNode]:
        """Extract import statements"""
        imports = []
        
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imp = ImportNode(
                        module_name=alias.name,
                        imported_names=[alias.name],
                        is_from_import=False,
                        alias=alias.asname,
                        location=Location(
                            file_path="",
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            start_column=node.col_offset,
                            end_column=node.end_col_offset or node.col_offset
                        )
                    )
                    imports.append(imp)
            
            elif isinstance(node, ast.ImportFrom):
                imported_names = [alias.name for alias in node.names]
                imp = ImportNode(
                    module_name=node.module or "",
                    imported_names=imported_names,
                    is_from_import=True,
                    location=Location(
                        file_path="",
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        start_column=node.col_offset,
                        end_column=node.end_col_offset or node.col_offset
                    )
                )
                imports.append(imp)
        
        return imports
    
    def calculate_complexity(self, node) -> int:
        """
        Calculate cyclomatic complexity
        Complexity = 1 + number of decision points
        """
        complexity = 1
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or operators
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                complexity += sum(1 for gen in child.generators for if_ in gen.ifs)
        
        return complexity
    
    def _calculate_nesting_depth(self, node, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _extract_calls(self, node) -> List[str]:
        """Extract function calls within a function"""
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        
        return list(set(calls))  # Remove duplicates
    
    def count_lines(self, content: str) -> tuple[int, int, int, int]:
        """Count lines in Python file"""
        lines = content.split('\n')
        total = len(lines)
        blank = 0
        comment = 0
        code = 0
        
        in_multiline_string = False
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                blank += 1
            elif stripped.startswith('#'):
                comment += 1
            elif '"""' in stripped or "'''" in stripped:
                comment += 1
                if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                    in_multiline_string = not in_multiline_string
            elif in_multiline_string:
                comment += 1
            else:
                code += 1
        
        return total, code, comment, blank
