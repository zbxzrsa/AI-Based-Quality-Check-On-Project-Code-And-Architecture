"""
Context Builder for Agentic AI Service

Queries Neo4j graph database for relevant code context and builds
optimized context for LLM token limits.

Validates Requirements: 3.2
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.database.neo4j_client import Neo4jClient


logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context that can be retrieved"""
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    DEPENDENCY = "dependency"
    CALLER = "caller"
    CALLEE = "callee"


@dataclass
class CodeContext:
    """Represents code context retrieved from graph database"""
    context_type: ContextType
    name: str
    file_path: str
    content: Optional[str] = None
    dependencies: List[str] = None
    dependents: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.dependents is None:
            self.dependents = []
        if self.metadata is None:
            self.metadata = {}


class ContextBuilder:
    """
    Builds code context from Neo4j graph database for LLM analysis.
    
    Queries graph relationships to provide relevant context about:
    - File dependencies and imports
    - Function call chains
    - Class hierarchies and relationships
    - Related code patterns
    
    Optimizes context size to fit within LLM token limits.
    
    Validates Requirements: 3.2
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        max_context_tokens: int = 4000,
        max_depth: int = 2
    ):
        """
        Initialize context builder.
        
        Args:
            neo4j_client: Neo4j client for graph queries
            max_context_tokens: Maximum tokens for context (default 4000)
            max_depth: Maximum depth for relationship traversal (default 2)
        """
        self.neo4j_client = neo4j_client
        self.max_context_tokens = max_context_tokens
        self.max_depth = max_depth
        
        # Approximate tokens per character (rough estimate)
        self.chars_per_token = 4
        self.max_context_chars = max_context_tokens * self.chars_per_token
    
    async def build_context_for_file(
        self,
        file_path: str,
        repository: str,
        include_dependencies: bool = True,
        include_dependents: bool = False
    ) -> Dict[str, Any]:
        """
        Build context for a specific file.
        
        Args:
            file_path: Path to the file
            repository: Repository name
            include_dependencies: Include files this file depends on
            include_dependents: Include files that depend on this file
            
        Returns:
            Dictionary containing file context
        """
        try:
            logger.debug(
                f"Building context for file: {file_path}",
                extra={
                    'file_path': file_path,
                    'repository': repository,
                    'include_dependencies': include_dependencies,
                    'include_dependents': include_dependents
                }
            )
            
            context = {
                'file_path': file_path,
                'repository': repository,
                'dependencies': [],
                'dependents': [],
                'functions': [],
                'classes': [],
                'imports': []
            }
            
            # Query file node
            file_query = """
            MATCH (f:File {path: $file_path, repository: $repository})
            RETURN f.path as path, f.language as language, f.size as size
            """
            
            result = await self.neo4j_client.execute_read_query(
                file_query,
                {'file_path': file_path, 'repository': repository}
            )
            
            records = [record async for record in result]
            if not records:
                logger.warning(f"File not found in graph: {file_path}")
                return context
            
            file_record = records[0]
            context['language'] = file_record.get('language')
            context['size'] = file_record.get('size')
            
            # Get dependencies if requested
            if include_dependencies:
                context['dependencies'] = await self._get_file_dependencies(
                    file_path, repository
                )
            
            # Get dependents if requested
            if include_dependents:
                context['dependents'] = await self._get_file_dependents(
                    file_path, repository
                )
            
            # Get functions in file
            context['functions'] = await self._get_file_functions(
                file_path, repository
            )
            
            # Get classes in file
            context['classes'] = await self._get_file_classes(
                file_path, repository
            )
            
            # Get imports
            context['imports'] = await self._get_file_imports(
                file_path, repository
            )
            
            logger.info(
                f"Context built for file: {file_path}",
                extra={
                    'dependencies_count': len(context['dependencies']),
                    'dependents_count': len(context['dependents']),
                    'functions_count': len(context['functions']),
                    'classes_count': len(context['classes'])
                }
            )
            
            return context
            
        except Exception as e:
            logger.error(
                f"Error building context for file: {file_path}",
                extra={'error': str(e), 'file_path': file_path},
                exc_info=True
            )
            raise

    async def build_context_for_function(
        self,
        function_name: str,
        file_path: str,
        repository: str,
        include_callers: bool = True,
        include_callees: bool = True
    ) -> Dict[str, Any]:
        """
        Build context for a specific function.
        
        Args:
            function_name: Name of the function
            file_path: Path to file containing function
            repository: Repository name
            include_callers: Include functions that call this function
            include_callees: Include functions called by this function
            
        Returns:
            Dictionary containing function context
        """
        try:
            logger.debug(
                f"Building context for function: {function_name}",
                extra={
                    'function_name': function_name,
                    'file_path': file_path,
                    'repository': repository
                }
            )
            
            context = {
                'function_name': function_name,
                'file_path': file_path,
                'repository': repository,
                'callers': [],
                'callees': [],
                'parameters': [],
                'return_type': None
            }
            
            # Query function node
            function_query = """
            MATCH (f:Function {name: $function_name, file_path: $file_path, repository: $repository})
            RETURN f.name as name, f.parameters as parameters, 
                   f.return_type as return_type, f.complexity as complexity,
                   f.line_start as line_start, f.line_end as line_end
            """
            
            result = await self.neo4j_client.execute_read_query(
                function_query,
                {
                    'function_name': function_name,
                    'file_path': file_path,
                    'repository': repository
                }
            )
            
            records = [record async for record in result]
            if not records:
                logger.warning(f"Function not found in graph: {function_name}")
                return context
            
            func_record = records[0]
            context['parameters'] = func_record.get('parameters', [])
            context['return_type'] = func_record.get('return_type')
            context['complexity'] = func_record.get('complexity')
            context['line_start'] = func_record.get('line_start')
            context['line_end'] = func_record.get('line_end')
            
            # Get callers if requested
            if include_callers:
                context['callers'] = await self._get_function_callers(
                    function_name, file_path, repository
                )
            
            # Get callees if requested
            if include_callees:
                context['callees'] = await self._get_function_callees(
                    function_name, file_path, repository
                )
            
            logger.info(
                f"Context built for function: {function_name}",
                extra={
                    'callers_count': len(context['callers']),
                    'callees_count': len(context['callees'])
                }
            )
            
            return context
            
        except Exception as e:
            logger.error(
                f"Error building context for function: {function_name}",
                extra={'error': str(e), 'function_name': function_name},
                exc_info=True
            )
            raise
    
    async def build_context_for_class(
        self,
        class_name: str,
        file_path: str,
        repository: str,
        include_inheritance: bool = True,
        include_methods: bool = True
    ) -> Dict[str, Any]:
        """
        Build context for a specific class.
        
        Args:
            class_name: Name of the class
            file_path: Path to file containing class
            repository: Repository name
            include_inheritance: Include parent and child classes
            include_methods: Include class methods
            
        Returns:
            Dictionary containing class context
        """
        try:
            logger.debug(
                f"Building context for class: {class_name}",
                extra={
                    'class_name': class_name,
                    'file_path': file_path,
                    'repository': repository
                }
            )
            
            context = {
                'class_name': class_name,
                'file_path': file_path,
                'repository': repository,
                'parent_classes': [],
                'child_classes': [],
                'methods': [],
                'attributes': []
            }
            
            # Query class node
            class_query = """
            MATCH (c:Class {name: $class_name, file_path: $file_path, repository: $repository})
            RETURN c.name as name, c.attributes as attributes,
                   c.line_start as line_start, c.line_end as line_end
            """
            
            result = await self.neo4j_client.execute_read_query(
                class_query,
                {
                    'class_name': class_name,
                    'file_path': file_path,
                    'repository': repository
                }
            )
            
            records = [record async for record in result]
            if not records:
                logger.warning(f"Class not found in graph: {class_name}")
                return context
            
            class_record = records[0]
            context['attributes'] = class_record.get('attributes', [])
            context['line_start'] = class_record.get('line_start')
            context['line_end'] = class_record.get('line_end')
            
            # Get inheritance if requested
            if include_inheritance:
                context['parent_classes'] = await self._get_parent_classes(
                    class_name, file_path, repository
                )
                context['child_classes'] = await self._get_child_classes(
                    class_name, file_path, repository
                )
            
            # Get methods if requested
            if include_methods:
                context['methods'] = await self._get_class_methods(
                    class_name, file_path, repository
                )
            
            logger.info(
                f"Context built for class: {class_name}",
                extra={
                    'parent_classes_count': len(context['parent_classes']),
                    'child_classes_count': len(context['child_classes']),
                    'methods_count': len(context['methods'])
                }
            )
            
            return context
            
        except Exception as e:
            logger.error(
                f"Error building context for class: {class_name}",
                extra={'error': str(e), 'class_name': class_name},
                exc_info=True
            )
            raise

    async def optimize_context_for_llm(
        self,
        context: Dict[str, Any],
        priority_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Optimize context to fit within LLM token limits.
        
        Prioritizes most relevant information and truncates less important data.
        
        Args:
            context: Raw context dictionary
            priority_fields: Fields to prioritize (keep first)
            
        Returns:
            Optimized context dictionary
        """
        if priority_fields is None:
            priority_fields = ['file_path', 'function_name', 'class_name', 'dependencies']
        
        # Estimate current size
        import json
        context_str = json.dumps(context)
        current_chars = len(context_str)
        
        if current_chars <= self.max_context_chars:
            logger.debug("Context within token limits, no optimization needed")
            return context
        
        logger.info(
            f"Optimizing context: {current_chars} chars -> {self.max_context_chars} chars",
            extra={
                'current_chars': current_chars,
                'max_chars': self.max_context_chars,
                'reduction_needed': current_chars - self.max_context_chars
            }
        )
        
        optimized = {}
        remaining_chars = self.max_context_chars
        
        # Add priority fields first
        for field in priority_fields:
            if field in context and remaining_chars > 0:
                field_str = json.dumps({field: context[field]})
                field_chars = len(field_str)
                
                if field_chars <= remaining_chars:
                    optimized[field] = context[field]
                    remaining_chars -= field_chars
        
        # Add remaining fields if space available
        for field, value in context.items():
            if field not in optimized and remaining_chars > 0:
                field_str = json.dumps({field: value})
                field_chars = len(field_str)
                
                if field_chars <= remaining_chars:
                    optimized[field] = value
                    remaining_chars -= field_chars
                elif isinstance(value, list) and value:
                    # Truncate lists to fit
                    truncated_list = []
                    for item in value:
                        item_str = json.dumps(item)
                        if len(item_str) <= remaining_chars:
                            truncated_list.append(item)
                            remaining_chars -= len(item_str)
                        else:
                            break
                    if truncated_list:
                        optimized[field] = truncated_list
                        optimized[f"{field}_truncated"] = True
        
        logger.info(
            f"Context optimized: {len(optimized)} fields retained",
            extra={'fields_retained': list(optimized.keys())}
        )
        
        return optimized
    
    # Helper methods for querying graph relationships
    
    async def _get_file_dependencies(
        self,
        file_path: str,
        repository: str
    ) -> List[str]:
        """Get files that this file depends on"""
        query = """
        MATCH (f:File {path: $file_path, repository: $repository})-[:IMPORTS|DEPENDS_ON]->(dep:File)
        RETURN DISTINCT dep.path as dependency
        LIMIT 20
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {'file_path': file_path, 'repository': repository}
        )
        
        return [record['dependency'] async for record in result]
    
    async def _get_file_dependents(
        self,
        file_path: str,
        repository: str
    ) -> List[str]:
        """Get files that depend on this file"""
        query = """
        MATCH (dep:File)-[:IMPORTS|DEPENDS_ON]->(f:File {path: $file_path, repository: $repository})
        RETURN DISTINCT dep.path as dependent
        LIMIT 20
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {'file_path': file_path, 'repository': repository}
        )
        
        return [record['dependent'] async for record in result]
    
    async def _get_file_functions(
        self,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get functions defined in file"""
        query = """
        MATCH (f:File {path: $file_path, repository: $repository})-[:CONTAINS]->(func:Function)
        RETURN func.name as name, func.parameters as parameters, 
               func.complexity as complexity
        LIMIT 50
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {'file_path': file_path, 'repository': repository}
        )
        
        return [
            {
                'name': record['name'],
                'parameters': record.get('parameters', []),
                'complexity': record.get('complexity')
            }
            async for record in result
        ]
    
    async def _get_file_classes(
        self,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get classes defined in file"""
        query = """
        MATCH (f:File {path: $file_path, repository: $repository})-[:CONTAINS]->(c:Class)
        RETURN c.name as name, c.attributes as attributes
        LIMIT 50
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {'file_path': file_path, 'repository': repository}
        )
        
        return [
            {
                'name': record['name'],
                'attributes': record.get('attributes', [])
            }
            async for record in result
        ]
    
    async def _get_file_imports(
        self,
        file_path: str,
        repository: str
    ) -> List[str]:
        """Get imports in file"""
        query = """
        MATCH (f:File {path: $file_path, repository: $repository})-[:IMPORTS]->(imp:File)
        RETURN DISTINCT imp.path as import_path
        LIMIT 30
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {'file_path': file_path, 'repository': repository}
        )
        
        return [record['import_path'] async for record in result]

    async def _get_function_callers(
        self,
        function_name: str,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get functions that call this function"""
        query = """
        MATCH (caller:Function)-[:CALLS]->(f:Function {name: $function_name, file_path: $file_path, repository: $repository})
        RETURN caller.name as name, caller.file_path as file_path
        LIMIT 20
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {
                'function_name': function_name,
                'file_path': file_path,
                'repository': repository
            }
        )
        
        return [
            {
                'name': record['name'],
                'file_path': record['file_path']
            }
            async for record in result
        ]
    
    async def _get_function_callees(
        self,
        function_name: str,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get functions called by this function"""
        query = """
        MATCH (f:Function {name: $function_name, file_path: $file_path, repository: $repository})-[:CALLS]->(callee:Function)
        RETURN callee.name as name, callee.file_path as file_path
        LIMIT 20
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {
                'function_name': function_name,
                'file_path': file_path,
                'repository': repository
            }
        )
        
        return [
            {
                'name': record['name'],
                'file_path': record['file_path']
            }
            async for record in result
        ]
    
    async def _get_parent_classes(
        self,
        class_name: str,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get parent classes (inheritance)"""
        query = """
        MATCH (c:Class {name: $class_name, file_path: $file_path, repository: $repository})-[:INHERITS]->(parent:Class)
        RETURN parent.name as name, parent.file_path as file_path
        LIMIT 10
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {
                'class_name': class_name,
                'file_path': file_path,
                'repository': repository
            }
        )
        
        return [
            {
                'name': record['name'],
                'file_path': record['file_path']
            }
            async for record in result
        ]
    
    async def _get_child_classes(
        self,
        class_name: str,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get child classes (inheritance)"""
        query = """
        MATCH (child:Class)-[:INHERITS]->(c:Class {name: $class_name, file_path: $file_path, repository: $repository})
        RETURN child.name as name, child.file_path as file_path
        LIMIT 10
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {
                'class_name': class_name,
                'file_path': file_path,
                'repository': repository
            }
        )
        
        return [
            {
                'name': record['name'],
                'file_path': record['file_path']
            }
            async for record in result
        ]
    
    async def _get_class_methods(
        self,
        class_name: str,
        file_path: str,
        repository: str
    ) -> List[Dict[str, Any]]:
        """Get methods of a class"""
        query = """
        MATCH (c:Class {name: $class_name, file_path: $file_path, repository: $repository})-[:HAS_METHOD]->(m:Function)
        RETURN m.name as name, m.parameters as parameters, m.complexity as complexity
        LIMIT 30
        """
        
        result = await self.neo4j_client.execute_read_query(
            query,
            {
                'class_name': class_name,
                'file_path': file_path,
                'repository': repository
            }
        )
        
        return [
            {
                'name': record['name'],
                'parameters': record.get('parameters', []),
                'complexity': record.get('complexity')
            }
            async for record in result
        ]


def create_context_builder(
    neo4j_client: Neo4jClient,
    max_context_tokens: int = 4000,
    max_depth: int = 2
) -> ContextBuilder:
    """
    Factory function to create ContextBuilder instance.
    
    Args:
        neo4j_client: Neo4j client for graph queries
        max_context_tokens: Maximum tokens for context
        max_depth: Maximum depth for relationship traversal
        
    Returns:
        Configured ContextBuilder instance
    """
    return ContextBuilder(
        neo4j_client=neo4j_client,
        max_context_tokens=max_context_tokens,
        max_depth=max_depth
    )
