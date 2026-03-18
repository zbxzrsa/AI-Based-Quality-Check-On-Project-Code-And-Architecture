"""
Data models for parsed AST elements
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel


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
    start_column: int | None = None
    end_column: int | None = None


class ImportNode(BaseModel):
    """Import/dependency node"""

    module_name: str
    imported_names: list[str] = []
    is_from_import: bool = False
    alias: str | None = None
    location: Location


class ParameterNode(BaseModel):
    """Function/method parameter"""

    name: str
    type_annotation: str | None = None
    default_value: str | None = None


class FunctionNode(BaseModel):
    """Function or method node"""

    name: str
    parameters: list[ParameterNode] = []
    return_type: str | None = None
    complexity: int = 1
    lines_of_code: int = 0
    nesting_depth: int = 0
    is_async: bool = False
    is_method: bool = False
    decorators: list[str] = []
    docstring: str | None = None
    calls: list[str] = []  # Functions called within this function
    location: Location


class PropertyNode(BaseModel):
    """Class property/attribute"""

    name: str
    type_annotation: str | None = None
    default_value: str | None = None
    is_class_variable: bool = False


class ClassNode(BaseModel):
    """Class node"""

    name: str
    methods: list[FunctionNode] = []
    properties: list[PropertyNode] = []
    base_classes: list[str] = []
    decorators: list[str] = []
    docstring: str | None = None
    lines_of_code: int = 0
    location: Location


class ModuleNode(BaseModel):
    """Module/file node"""

    name: str
    file_path: str
    language: str
    imports: list[ImportNode] = []
    classes: list[ClassNode] = []
    functions: list[FunctionNode] = []
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    comment_ratio: float = 0.0


class ParsedFile(BaseModel):
    """Complete parsed file structure"""

    module: ModuleNode
    metrics: dict[str, Any] = {}
    errors: list[str] = []


class DependencyEdge(BaseModel):
    """Dependency relationship"""

    source: str
    target: str
    type: str  # import, call, inheritance
    weight: float = 1.0


class DependencyGraph(BaseModel):
    """Dependency graph structure"""

    nodes: list[str] = []
    edges: list[DependencyEdge] = []
    metrics: dict[str, Any] = {}
