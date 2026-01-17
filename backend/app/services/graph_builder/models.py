"""
Graph builder data models and type definitions.
"""
from typing import Dict, List, Optional, Set, Union
from enum import Enum
from pydantic import BaseModel


class NodeType(str, Enum):
    """Types of nodes in the code graph."""
    MODULE = "Module"
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    IMPORT = "Import"
    CALL = "Call"


class RelationshipType(str, Enum):
    """Types of relationships in the code graph."""
    DEFINES = "DEFINES"
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    USES = "USES"


class CodePosition(BaseModel):
    """Position of a code element in the source file."""
    line: int
    col_offset: int
    end_line: int
    end_col_offset: int


class GraphNode(BaseModel):
    """Base class for all graph nodes."""
    node_type: NodeType
    name: str
    full_name: str
    file_path: str
    position: Optional[CodePosition] = None
    properties: Dict[str, str] = {}
    
    def to_cypher_properties(self) -> str:
        """Convert properties to Cypher property map string."""
        props = {
            'name': self.name,
            'full_name': self.full_name,
            'file_path': self.file_path,
            'type': self.node_type.value,
            **{k: v for k, v in self.properties.items() if v is not None}
        }
        
        if self.position:
            props.update({
                'line': self.position.line,
                'col_offset': self.position.col_offset,
                'end_line': self.position.end_line,
                'end_col_offset': self.position.end_col_offset,
            })
        
        return ', '.join(f'{k}: ${k}' for k in props)


class GraphRelationship(BaseModel):
    """Represents a relationship between two nodes in the graph."""
    source: GraphNode
    target: GraphNode
    rel_type: RelationshipType
    properties: Dict[str, str] = {}
    
    def to_cypher(self) -> str:
        """Convert relationship to Cypher pattern."""
        rel_props = f' {{{self._format_properties()}}}' if self.properties else ''
        return f"-[:{self.rel_type.value}{rel_props}]->"
    
    def _format_properties(self) -> str:
        """Format properties for Cypher query."""
        return ', '.join(f'{k}: "{v}"' for k, v in self.properties.items())


class FileNode(GraphNode):
    """Represents a source code file."""
    node_type: NodeType = NodeType.FILE


class ClassNode(GraphNode):
    """Represents a class definition."""
    node_type: NodeType = NodeType.CLASS
    bases: List[str] = []


class FunctionNode(GraphNode):
    """Represents a function or method definition."""
    node_type: NodeType = NodeType.FUNCTION
    args: List[str] = []
    returns: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    decorators: List[str] = []
    docstring: Optional[str] = None


class ImportNode(GraphNode):
    """Represents an import statement."""
    node_type: NodeType = NodeType.IMPORT
    alias: Optional[str] = None
    module: Optional[str] = None
    names: List[str] = []
    level: int = 0


class CallNode(GraphNode):
    """Represents a function or method call."""
    node_type: NodeType = NodeType.CALL
    args: List[str] = []
    keywords: Dict[str, str] = {}


class GraphUpdateResult(BaseModel):
    """Result of a graph update operation."""
    nodes_created: int = 0
    nodes_updated: int = 0
    relationships_created: int = 0
    relationships_updated: int = 0
    errors: List[str] = []
    
    def __add__(self, other: 'GraphUpdateResult') -> 'GraphUpdateResult':
        return GraphUpdateResult(
            nodes_created=self.nodes_created + other.nodes_created,
            nodes_updated=self.nodes_updated + other.nodes_updated,
            relationships_created=self.relationships_created + other.relationships_created,
            relationships_updated=self.relationships_updated + other.relationships_updated,
            errors=self.errors + other.errors
        )
