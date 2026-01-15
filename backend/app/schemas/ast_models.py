"""
Data models for parsed AST elements
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeType(str, Enum):
    """Node type enumeration"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"
    VARIABLE = "variable"
    MODULE = "module"


class Location(BaseModel):
    """Source code location"""
    file_path: str
    start_line: int
    end_line: int
    start_column: Optional[int] = None
    end_column: Optional[int] = None


class ImportNode(BaseModel):
    """Import/dependency node"""
    module_name: str
    imported_names: List[str] = []
    is_from_import: bool = False
    alias: Optional[str] = None
    location: Location


class ParameterNode(BaseModel):
    """Function/method parameter"""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


class FunctionNode(BaseModel):
    """Function or method node"""
    name: str
    parameters: List[ParameterNode] = []
    return_type: Optional[str] = None
    complexity: int = 1
    lines_of_code: int = 0
    nesting_depth: int = 0
    is_async: bool = False
    is_method: bool = False
    decorators: List[str] = []
    docstring: Optional[str] = None
    calls: List[str] = []  # Functions called within this function
    location: Location


class PropertyNode(BaseModel):
    """Class property/attribute"""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_class_variable: bool = False


class ClassNode(BaseModel):
    """Class node"""
    name: str
    methods: List[FunctionNode] = []
    properties: List[PropertyNode] = []
    base_classes: List[str] = []
    decorators: List[str] = []
    docstring: Optional[str] = None
    lines_of_code: int = 0
    location: Location


class ModuleNode(BaseModel):
    """Module/file node"""
    name: str
    file_path: str
    language: str
    imports: List[ImportNode] = []
    classes: List[ClassNode] = []
    functions: List[FunctionNode] = []
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    comment_ratio: float = 0.0


class ParsedFile(BaseModel):
    """Complete parsed file structure"""
    module: ModuleNode
    metrics: Dict[str, Any] = {}
    errors: List[str] = []


class DependencyEdge(BaseModel):
    """Dependency relationship"""
    source: str
    target: str
    type: str  # import, call, inheritance
    weight: float = 1.0


class DependencyGraph(BaseModel):
    """Dependency graph structure"""
    nodes: List[str] = []
    edges: List[DependencyEdge] = []
    metrics: Dict[str, Any] = {}
