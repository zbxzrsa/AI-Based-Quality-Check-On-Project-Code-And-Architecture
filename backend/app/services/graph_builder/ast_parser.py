"""
AST Parser for Python code analysis.

This module provides functionality to parse Python source code into an abstract syntax tree (AST)
and extract relevant information for building a code graph.
"""
import ast
import os
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from pathlib import Path

from .models import (
    NodeType, CodePosition, FileNode, ClassNode, FunctionNode, 
    ImportNode, CallNode, GraphNode, GraphRelationship, RelationshipType
)


class ASTVisitor(ast.NodeVisitor):
    ""
    AST visitor that extracts code structure information for graph building.
    """
    
    def __init__(self, file_path: str, module_name: str):
        self.file_path = file_path
        self.module_name = module_name
        self.nodes: List[GraphNode] = []
        self.relationships: List[GraphRelationship] = []
        self.current_class: Optional[ClassNode] = None
        self.current_function: Optional[FunctionNode] = None
        self.imports: Dict[str, ImportNode] = {}
        self.imported_names: Dict[str, str] = {}  # name -> full module path
        
        # Track function calls within the current scope
        self._function_calls: List[Tuple[str, CodePosition]] = []
    
    def visit_Module(self, node: ast.Module) -> None:
        """Visit a module node."""
        self.generic_visit(node)
    
    def _get_position(self, node: ast.AST) -> CodePosition:
        """Extract position information from an AST node."""
        return CodePosition(
            line=node.lineno,
            col_offset=node.col_offset,
            end_line=getattr(node, 'end_lineno', node.lineno),
            end_col_offset=getattr(node, 'end_col_offset', node.col_offset + 10)  # Default width
        )
    
    def _create_import_node(self, node: ast.Import, name: str, alias: str = None) -> ImportNode:
        """Create an import node from an AST import node."""
        full_name = f"{name}{f' as {alias}' if alias else ''}"
        import_node = ImportNode(
            name=name,
            full_name=full_name,
            file_path=self.file_path,
            position=self._get_position(node),
            properties={
                'module': name,
                'alias': alias,
                'import_type': 'import'
            }
        )
        self.imported_names[alias or name] = name
        return import_node
    
    def visit_Import(self, node: ast.Import) -> None:
        """Handle import statements."""
        for name in node.names:
            import_node = self._create_import_node(node, name.name, name.asname)
            self.nodes.append(import_node)
            self.imports[name.name] = import_node
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle from ... import ... statements."""
        module = node.module or ''
        
        for name in node.names:
            full_name = f"{module}.{name.name}" if module else name.name
            import_node = ImportNode(
                name=name.name,
                full_name=full_name,
                file_path=self.file_path,
                position=self._get_position(node),
                properties={
                    'module': module,
                    'alias': name.asname,
                    'import_type': 'from_import',
                    'level': node.level
                }
            )
            
            self.nodes.append(import_node)
            self.imported_names[name.asname or name.name] = full_name
            self.imports[full_name] = import_node
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions."""
        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle cases like 'module.Class'
                bases.append(self._get_attribute_name(base))
               
        # Create class node
        class_node = ClassNode(
            name=node.name,
            full_name=f"{self.module_name}.{node.name}",
            file_path=self.file_path,
            position=self._get_position(node),
            bases=bases,
            properties={
                'docstring': ast.get_docstring(node),
                'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
            }
        )
        
        # Add to nodes
        self.nodes.append(class_node)
        
        # Add relationship to file
        file_node = FileNode(
            name=os.path.basename(self.file_path),
            full_name=self.file_path,
            file_path=self.file_path
        )
        self.relationships.append(GraphRelationship(
            source=file_node,
            target=class_node,
            rel_type=RelationshipType.DEFINES
        ))
        
        # Process class body
        previous_class = self.current_class
        self.current_class = class_node
        self.generic_visit(node)
        self.current_class = previous_class
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get the name of a decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return self._get_attribute_name(decorator)
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full name of an attribute (e.g., module.Class)."""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function and method definitions."""
        self._process_function(node, is_async=False)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async function and method definitions."""
        self._process_function(node, is_async=True)
    
    def _process_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool) -> None:
        """Process a function or method definition."""
        # Get function arguments
        args = []
        if node.args.args:
            args.extend(arg.arg for arg in node.args.args)
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwonlyargs:
            args.extend(arg.arg for arg in node.args.kwonlyargs)
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        # Get return type annotation
        returns = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                returns = self._get_attribute_name(node.returns)
        
        # Create function node
        is_method = self.current_class is not None
        full_name_parts = []
        if self.current_class:
            full_name_parts.append(self.current_class.full_name)
        full_name_parts.append(node.name)
        full_name = ".".join(full_name_parts)
        
        function_node = FunctionNode(
            name=node.name,
            full_name=full_name,
            file_path=self.file_path,
            position=self._get_position(node),
            args=args,
            returns=returns,
            is_async=is_async,
            is_method=is_method,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
            properties={
                'signature': self._get_function_signature(node, args, returns, is_async)
            }
        )
        
        self.nodes.append(function_node)
        
        # Add relationship to parent (class or module)
        if self.current_class:
            # Method is defined in a class
            self.relationships.append(GraphRelationship(
                source=self.current_class,
                target=function_node,
                rel_type=RelationshipType.DEFINES
            ))
        else:
            # Top-level function
            file_node = FileNode(
                name=os.path.basename(self.file_path),
                full_name=self.file_path,
                file_path=self.file_path
            )
            self.relationships.append(GraphRelationship(
                source=file_node,
                target=function_node,
                rel_type=RelationshipType.DEFINES
            ))
        
        # Process function body
        previous_function = self.current_function
        self.current_function = function_node
        self._function_calls = []  # Reset function calls for this scope
        
        # Visit all nodes in the function body
        for stmt in node.body:
            self.visit(stmt)
        
        # Process function calls found in this function
        for call_name, pos in self._function_calls:
            # Try to resolve the full name of the called function
            full_call_name = self._resolve_name(call_name)
            
            call_node = CallNode(
                name=call_name,
                full_name=full_call_name or call_name,
                file_path=self.file_path,
                position=pos,
                properties={
                    'resolved': full_call_name is not None,
                    'scope': 'method' if self.current_class else 'function',
                    'caller': function_node.full_name
                }
            )
            
            self.nodes.append(call_node)
            self.relationships.append(GraphRelationship(
                source=function_node,
                target=call_node,
                rel_type=RelationshipType.CALLS,
                properties={
                    'position': f"{pos.line}:{pos.col_offset}",
                    'call_type': 'direct'
                }
            ))
        
        self.current_function = previous_function
    
    def _get_function_signature(self, node: ast.FunctionDef, args: List[str], returns: Optional[str], is_async: bool) -> str:
        """Generate a function signature string."""
        prefix = 'async ' if is_async else ''
        params = ', '.join(args)
        return_type = f' -> {returns}' if returns else ''
        return f'{prefix}def {node.name}({params}){return_type}'
    
    def _resolve_name(self, name: str) -> Optional[str]:
        """Resolve a name to its full import path if possible."""
        # Check if it's a direct import
        if name in self.imported_names:
            return self.imported_names[name]
        
        # Check if it's a method call (self.method)
        if '.' in name and self.current_class:
            parts = name.split('.')
            if parts[0] == 'self':
                return f"{self.current_class.full_name}.{'.'.join(parts[1:])}"
        
        # Check if it's a class method call (cls.method)
        if '.' in name and self.current_class and self.current_function and self.current_function.name == 'cls':
            parts = name.split('.')
            if parts[0] == 'cls':
                return f"{self.current_class.full_name}.{'.'.join(parts[1:])}"
        
        # Check if it's a method call on an imported module
        for imp_name, imp_node in self.imports.items():
            if name.startswith(imp_name + '.'):
                return name
        
        # Check if it's a built-in or from the standard library
        if name in dir(__builtins__):
            return f"builtins.{name}"
        
        # Couldn't resolve the name
        return None
    
    def visit_Call(self, node: ast.Call) -> None:
        """Handle function calls."""
        # Get the function name being called
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = self._get_attribute_name(node.func)
        else:
            func_name = "<unknown>"
        
        # Record the function call if we're inside a function
        if self.current_function:
            self._function_calls.append((func_name, self._get_position(node)))
        
        # Continue visiting child nodes
        self.generic_visit(node)


def parse_file(file_path: str, module_name: str = None) -> Tuple[List[GraphNode], List[GraphRelationship]]:
    """
    Parse a Python file and extract its structure as graph nodes and relationships.
    
    Args:
        file_path: Path to the Python file to parse
        module_name: Optional module name (defaults to file name without extension)
        
    Returns:
        Tuple of (nodes, relationships) where nodes is a list of GraphNode instances
        and relationships is a list of GraphRelationship instances.
    """
    if module_name is None:
        module_name = Path(file_path).stem
    
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    return parse_source(source, file_path, module_name)


def parse_source(source: str, file_path: str, module_name: str) -> Tuple[List[GraphNode], List[GraphRelationship]]:
    """
    Parse Python source code and extract its structure as graph nodes and relationships.
    
    Args:
        source: Python source code as a string
        file_path: Path to the source file (for reference)
        module_name: Name of the module
        
    Returns:
        Tuple of (nodes, relationships)
    """
    try:
        tree = ast.parse(source, filename=file_path)
        visitor = ASTVisitor(file_path, module_name)
        visitor.visit(tree)
        
        # Add file node if it doesn't exist
        file_node_exists = any(isinstance(n, FileNode) for n in visitor.nodes)
        if not file_node_exists:
            file_node = FileNode(
                name=os.path.basename(file_path),
                full_name=file_path,
                file_path=file_path
            )
            visitor.nodes.append(file_node)
        
        return visitor.nodes, visitor.relationships
    except Exception as e:
        raise ValueError(f"Error parsing {file_path}: {str(e)}")
