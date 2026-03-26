"""
Data models for parsed AST elements.

This module also preserves a light compatibility layer for older parsers
that still emit legacy field names.
"""
from pydantic import BaseModel, Field, ConfigDict, model_validator
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
    metrics: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    raw_ast: Dict[str, Any] = Field(default_factory=dict)


class DependencyEdge(BaseModel):
    """Dependency relationship"""
    source: str
    target: str
    type: str  # import, call, inheritance
    weight: float = 1.0


class DependencyGraph(BaseModel):
    """Dependency graph structure"""
    nodes: List[str] = Field(default_factory=list)
    edges: List[DependencyEdge] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Import(ImportNode):
    """Backward-compatible import model."""

    model_config = ConfigDict(populate_by_name=True)

    module_name: str = Field(alias="module")
    imported_names: List[str] = Field(default_factory=list)
    is_from_import: bool = False
    alias: Optional[str] = None
    location: Location = Field(
        default_factory=lambda: Location(file_path="", start_line=1, end_line=1)
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_import(cls, data: Any) -> Any:
        if isinstance(data, dict):
            coerced = dict(data)
            if "module" in coerced and "module_name" not in coerced:
                coerced["module_name"] = coerced["module"]
            if "is_external" in coerced and "imported_names" not in coerced:
                module_name = coerced.get("module_name", "")
                coerced["imported_names"] = [module_name] if module_name else []
            return coerced
        return data

    @property
    def module(self) -> str:
        return self.module_name

    @property
    def is_external(self) -> bool:
        return not self.is_from_import


class Function(FunctionNode):
    """Backward-compatible function model."""

    model_config = ConfigDict(populate_by_name=True)

    parameters: List[ParameterNode] = Field(default_factory=list)
    location: Location = Field(
        default_factory=lambda: Location(file_path="", start_line=1, end_line=1)
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_function(cls, data: Any) -> Any:
        if isinstance(data, dict):
            coerced = dict(data)
            if "calls_to" in coerced and "calls" not in coerced:
                coerced["calls"] = coerced["calls_to"]
            if "start_line" in coerced or "end_line" in coerced:
                coerced.setdefault(
                    "location",
                    {
                        "file_path": "",
                        "start_line": coerced.pop("start_line", 1),
                        "end_line": coerced.pop("end_line", 1),
                    },
                )
            legacy_params = coerced.get("parameters")
            if legacy_params and isinstance(legacy_params, list):
                coerced["parameters"] = [
                    param if isinstance(param, ParameterNode)
                    else ParameterNode(
                        name=param.get("name", ""),
                        type_annotation=param.get("type"),
                        default_value=param.get("default"),
                    )
                    for param in legacy_params
                ]
            return coerced
        return data


class Class(ClassNode):
    """Backward-compatible class model."""

    model_config = ConfigDict(populate_by_name=True)

    methods: List[FunctionNode] = Field(default_factory=list)
    properties: List[PropertyNode] = Field(default_factory=list)
    location: Location = Field(
        default_factory=lambda: Location(file_path="", start_line=1, end_line=1)
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_class(cls, data: Any) -> Any:
        if isinstance(data, dict):
            coerced = dict(data)
            if "bases" in coerced and "base_classes" not in coerced:
                coerced["base_classes"] = coerced["bases"]
            if "attributes" in coerced and "properties" not in coerced:
                legacy_properties = coerced["attributes"] or []
                coerced["properties"] = [
                    prop if isinstance(prop, PropertyNode)
                    else PropertyNode(
                        name=prop.get("name", ""),
                        type_annotation=prop.get("type"),
                        default_value=prop.get("default"),
                        is_class_variable=not prop.get("is_property", False),
                    )
                    for prop in legacy_properties
                ]
            if "start_line" in coerced or "end_line" in coerced:
                coerced.setdefault(
                    "location",
                    {
                        "file_path": "",
                        "start_line": coerced.pop("start_line", 1),
                        "end_line": coerced.pop("end_line", 1),
                    },
                )
            coerced.pop("is_abstract", None)
            return coerced
        return data


class Module(ModuleNode):
    """Backward-compatible module model."""

    model_config = ConfigDict(populate_by_name=True)

    file_path: str = Field(alias="path")
    imports: List[ImportNode] = Field(default_factory=list)
    classes: List[ClassNode] = Field(default_factory=list)
    functions: List[FunctionNode] = Field(default_factory=list)
    comment_lines: int = 0
    blank_lines: int = 0

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_module(cls, data: Any) -> Any:
        if isinstance(data, dict):
            coerced = dict(data)
            if "path" in coerced and "file_path" not in coerced:
                coerced["file_path"] = coerced["path"]
            coerced.pop("file_id", None)
            return coerced
        return data
