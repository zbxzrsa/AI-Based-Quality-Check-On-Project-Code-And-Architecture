"""
AST Insert Service

Handles insertion of parsed AST data into Neo4j graph database.
Separated from Neo4jASTService for single responsibility.
"""
import logging
logger = logging.getLogger(__name__)

from typing import Optional
from neo4j import AsyncSession

from app.schemas.ast_models import ParsedFile, ClassNode, FunctionNode
from app.core.config import settings


class ASTInsertService:
    """
    Service for inserting AST nodes into Neo4j.
    
    Responsibilities:
    - Insert module/file nodes
    - Insert class nodes with inheritance
    - Insert function/method nodes
    - Insert import dependencies
    """
    
    def __init__(self, driver):
        """
        Initialize AST insert service.
        
        Args:
            driver: Neo4j async driver
        """
        self.driver = driver
    
    async def insert_ast_nodes(
        self,
        parsed_data: ParsedFile,
        project_id: str
    ) -> bool:
        """
        Insert parsed AST data into Neo4j graph.
        
        Args:
            parsed_data: Parsed file data
            project_id: Project identifier
            
        Returns:
            Success status
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            try:
                module = parsed_data.module
                
                # Insert module/file node
                await self._insert_module(session, module, project_id)
                
                # Insert classes
                for cls in module.classes:
                    await self._insert_class(session, cls, project_id, module.file_path)
                
                # Insert functions
                for func in module.functions:
                    await self._insert_function(
                        session, func, project_id, module.file_path, None
                    )
                
                # Insert imports as dependencies
                await self._insert_imports(session, module, project_id)
                
                return True
                
            except Exception as e:
                logger.info("Error inserting AST nodes: {e}")
                return False
    
    async def _insert_module(
        self,
        session: AsyncSession,
        module,
        project_id: str
    ):
        """Insert module/file node"""
        await session.run("""
            MATCH (p:Project {projectId: $projectId})
            MERGE (f:File {fileId: $fileId})
            SET f.path = $path,
                f.language = $language,
                f.linesOfCode = $linesOfCode,
                f.commentRatio = $commentRatio
            MERGE (p)-[:CONTAINS {level: 'file'}]->(f)
        """, 
            projectId=project_id,
            fileId=f"{project_id}::{module.file_path}",
            path=module.file_path,
            language=module.language,
            linesOfCode=module.lines_of_code,
            commentRatio=module.comment_ratio
        )
    
    async def _insert_class(
        self,
        session: AsyncSession,
        cls: ClassNode,
        project_id: str,
        file_path: str
    ):
        """Insert a class node with inheritance"""
        class_id = f"{project_id}::{file_path}::{cls.name}"
        file_id = f"{project_id}::{file_path}"
        
        # Insert class
        await session.run("""
            MATCH (f:File {fileId: $fileId})
            MERGE (c:Class {classId: $classId})
            SET c.name = $name,
                c.filePath = $filePath,
                c.startLine = $startLine,
                c.endLine = $endLine,
                c.linesOfCode = $linesOfCode
            MERGE (f)-[:CONTAINS {level: 'class'}]->(c)
        """,
            fileId=file_id,
            classId=class_id,
            name=cls.name,
            filePath=file_path,
            startLine=cls.location.start_line,
            endLine=cls.location.end_line,
            linesOfCode=cls.lines_of_code
        )
        
        # Insert inheritance relationships
        for base in cls.base_classes:
            await session.run("""
                MATCH (c:Class {classId: $classId})
                MERGE (base:Class {name: $baseName})
                MERGE (c)-[:INHERITS_FROM]->(base)
            """, classId=class_id, baseName=base)
        
        # Insert methods
        for method in cls.methods:
            await self._insert_function(
                session, method, project_id, file_path, class_id
            )
    
    async def _insert_function(
        self,
        session: AsyncSession,
        func: FunctionNode,
        project_id: str,
        file_path: str,
        class_id: Optional[str]
    ):
        """Insert a function/method node"""
        func_id = f"{project_id}::{file_path}::{func.name}"
        if class_id:
            func_id = f"{class_id}::{func.name}"
        
        # Insert function
        await session.run("""
            MERGE (fn:Function {functionId: $functionId})
            SET fn.name = $name,
                fn.parameters = $parameters,
                fn.returnType = $returnType,
                fn.complexity = $complexity,
                fn.linesOfCode = $linesOfCode,
                fn.nestingDepth = $nestingDepth,
                fn.isAsync = $isAsync,
                fn.isMethod = $isMethod
        """,
            functionId=func_id,
            name=func.name,
            parameters=[p.name for p in func.parameters],
            returnType=func.return_type,
            complexity=func.complexity,
            linesOfCode=func.lines_of_code,
            nestingDepth=func.nesting_depth,
            isAsync=func.is_async,
            isMethod=func.is_method
        )
        
        # Link to class or file
        if class_id:
            await session.run("""
                MATCH (c:Class {classId: $classId})
                MATCH (fn:Function {functionId: $functionId})
                MERGE (c)-[:CONTAINS {level: 'method'}]->(fn)
            """, classId=class_id, functionId=func_id)
        else:
            file_id = f"{project_id}::{file_path}"
            await session.run("""
                MATCH (f:File {fileId: $fileId})
                MATCH (fn:Function {functionId: $functionId})
                MERGE (f)-[:CONTAINS {level: 'function'}]->(fn)
            """, fileId=file_id, functionId=func_id)
        
        # Insert function calls
        for call in func.calls:
            await session.run("""
                MATCH (caller:Function {functionId: $callerId})
                MERGE (callee:Function {name: $calleeName})
                MERGE (caller)-[c:CALLS]->(callee)
                SET c.frequency = coalesce(c.frequency, 0) + 1,
                    c.callType = 'direct'
            """, callerId=func_id, calleeName=call)
    
    async def _insert_imports(
        self,
        session: AsyncSession,
        module,
        project_id: str
    ):
        """Insert import dependencies"""
        from app.services.layer_classifier import layer_classifier
        
        file_id = f"{project_id}::{module.file_path}"
        
        for imp in module.imports:
            target_module = imp.module_name
            
            # Classify target module
            layer_type, layer_rank = layer_classifier.classify_module(target_module)
            
            await session.run("""
                MATCH (source:File {fileId: $sourceId})
                MERGE (target:Module {moduleId: $targetModule})
                SET target.name = $targetModule,
                    target.layerType = $layerType,
                    target.layerRank = $layerRank
                MERGE (source)-[:DEPENDS_ON {type: 'import', weight: 1.0}]->(target)
            """,
                sourceId=file_id,
                targetModule=target_module,
                layerType=layer_type,
                layerRank=layer_rank
            )
