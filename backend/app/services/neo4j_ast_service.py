"""
Extended Neo4j service with AST and architecture analysis operations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.services.neo4j_service import Neo4jService as BaseNeo4jService
from app.schemas.ast_models import ParsedFile, ClassNode, FunctionNode, DependencyGraph
from app.core.config import settings


class Neo4jASTService(BaseNeo4jService):
    """
    Extended Neo4j service for AST and architecture operations
    """
    
    async def insert_ast_nodes(self, parsed_data: ParsedFile, project_id: str) -> bool:
        """
        Insert parsed AST data into Neo4j graph
        
        Args:
            parsed_data: Parsed file data
            project_id: Project identifier
            
        Returns:
            Success status
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            try:
                # Insert module/file node
                module = parsed_data.module
                
                await session.run("""
                    MATCH (p:Project {projectId: $projectId})
                    MERGE (f:File {fileId: $fileId})
                    SET f.path = $path,
                        f.language = $language,
                        f.linesOfCode = $linesOfCode,
                        f.commentRatio = $commentRatio
                    MERGE (p)-[:CONTAINS {level: 'file'}]->(f)
                """, projectId=project_id,
                     fileId=f"{project_id}::{module.file_path}",
                     path=module.file_path,
                     language=module.language,
                     linesOfCode=module.lines_of_code,
                     commentRatio=module.comment_ratio)
                
                # Insert classes
                for cls in module.classes:
                    await self._insert_class(session, cls, project_id, module.file_path)
                
                # Insert functions
                for func in module.functions:
                    await self._insert_function(session, func, project_id, module.file_path, None)
                
                # Insert imports as dependencies
                for imp in module.imports:
                    file_id = f"{project_id}::{module.file_path}"
                    target_module = imp.module_name
                    
                    await session.run("""
                        MATCH (source:File {fileId: $sourceId})
                        MERGE (target:Module {moduleId: $targetModule})
                        MERGE (source)-[:DEPENDS_ON {type: 'import', weight: 1.0}]->(target)
                    """, sourceId=file_id, targetModule=target_module)
                
                return True
                
            except Exception as e:
                print(f"Error inserting AST nodes: {e}")
                return False
    
    async def _insert_class(
        self,
        session,
        cls: ClassNode,
        project_id: str,
        file_path: str
    ):
        """Insert a class node"""
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
        """, fileId=file_id,
             classId=class_id,
             name=cls.name,
             filePath=file_path,
             startLine=cls.location.start_line,
             endLine=cls.location.end_line,
             linesOfCode=cls.lines_of_code)
        
        # Insert inheritance relationships
        for base in cls.base_classes:
            await session.run("""
                MATCH (c:Class {classId: $classId})
                MERGE (base:Class {name: $baseName})
                MERGE (c)-[:INHERITS_FROM]->(base)
            """, classId=class_id, baseName=base)
        
        # Insert methods
        for method in cls.methods:
            await self._insert_function(session, method, project_id, file_path, class_id)
    
    async def _insert_function(
        self,
        session,
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
        """, functionId=func_id,
             name=func.name,
             parameters=[p.name for p in func.parameters],
             returnType=func.return_type,
             complexity=func.complexity,
             linesOfCode=func.lines_of_code,
             nestingDepth=func.nesting_depth,
             isAsync=func.is_async,
             isMethod=func.is_method)
        
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
    
    async def find_circular_deps(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Find circular dependencies in the project
        
        Returns:
            List of cycles with module names and lengths
        """
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(m:Module)
        MATCH path = (m)-[:DEPENDS_ON*2..10]->(m)
        WITH m, path, nodes(path) AS pathNodes
        RETURN m.name AS startModule,
               [n IN pathNodes | CASE 
                   WHEN n:Module THEN n.name
                   WHEN n:File THEN n.path
                   ELSE 'Unknown'
               END] AS cyclePath,
               length(path) AS cycleLength
        ORDER BY cycleLength DESC
        LIMIT 50
        """
        
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            records = await result.data()
            return records
    
    async def detect_drift(
        self,
        project_id: str,
        baseline_version: str
    ) -> Dict[str, Any]:
        """
        Detect architectural drift by comparing current state with baseline
        
        Returns:
            Drift report with added/removed nodes and relationships
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            # Get baseline snapshot from PostgreSQL (architectural_baselines table)
            # For now, simplified version
            
            # Count current nodes
            current_counts = await session.run("""
                MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(n)
                RETURN labels(n)[0] AS nodeType, count(n) AS count
            """, projectId=project_id)
            
            current_data = await current_counts.data()
            
            # Count current dependencies
            dep_result = await session.run("""
                MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(n)
                MATCH (n)-[r:DEPENDS_ON]->()
                RETURN count(r) AS dependencyCount
            """, projectId=project_id)
            
            dep_data = await dep_result.single()
            
            drift_report = {
                "project_id": project_id,
                "baseline_version": baseline_version,
                "comparison_timestamp": datetime.utcnow().isoformat(),
                "current_nodes": {item['nodeType']: item['count'] for item in current_data},
                "current_dependencies": dep_data['dependencyCount'] if dep_data else 0,
                "drift_detected": False,  # Simplified - would compare with baseline
                "new_dependencies": [],
                "removed_components": [],
                "structural_similarity": 0.95  # Placeholder
            }
            
            return drift_report
    
    async def get_dependency_graph(self, project_id: str) -> Dict[str, Any]:
        """
        Export dependency graph for visualization
        
        Returns:
            Graph data ready for D3.js or other visualization libraries
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            # Get all nodes
            nodes_result = await session.run("""
                MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(n)
                WHERE n:Module OR n:File OR n:Class
                RETURN id(n) AS id,
                       labels(n)[0] AS type,
                       CASE
                           WHEN n:Module THEN n.name
                           WHEN n:File THEN n.path
                           WHEN n:Class THEN n.name
                           ELSE 'Unknown'
                       END AS name
            """, projectId=project_id)
            
            nodes = await nodes_result.data()
            
            # Get all dependencies
            edges_result = await session.run("""
                MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(source)
                MATCH (source)-[r:DEPENDS_ON]->(target)
                RETURN id(source) AS source,
                       id(target) AS target,
                       r.type AS type,
                       r.weight AS weight
            """, projectId=project_id)
            
            edges = await edges_result.data()
            
            return {
                "nodes": nodes,
                "links": edges,  # D3.js uses "links" terminology
                "metadata": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "project_id": project_id
                }
            }
    
    async def calculate_metrics(self, project_id: str) -> Dict[str, Any]:
        """
        Calculate architecture metrics for the project
        
        Returns:
            Comprehensive metrics dictionary
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            # Coupling metrics
            coupling_result = await session.run("""
                MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
                OPTIONAL MATCH (m)-[:DEPENDS_ON]->(out)
                WITH m, count(DISTINCT out) AS efferent
                OPTIONAL MATCH (m)<-[:DEPENDS_ON]-(inc)
                WITH m, efferent, count(DISTINCT inc) AS afferent
                RETURN m.name AS module,
                       afferent,
                       efferent,
                       CASE
                           WHEN afferent + efferent = 0 THEN 0.0
                           ELSE toFloat(efferent) / (afferent + efferent)
                       END AS instability
                ORDER BY instability DESC
            """, projectId=project_id)
            
            coupling_data = await coupling_result.data()
            
            # Complexity metrics
            complexity_result = await session.run("""
                MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(f:Function)
                RETURN avg(f.complexity) AS avgComplexity,
                       max(f.complexity) AS maxComplexity,
                       count(f) AS totalFunctions,
                       sum(f.complexity) AS totalComplexity
            """, projectId=project_id)
            
            complexity_data = await complexity_result.single()
            
            # Component counts
            counts_result = await session.run("""
                MATCH (p:Project {projectId: $projectId})
                OPTIONAL MATCH (p)-[:CONTAINS]->(m:Module)
                OPTIONAL MATCH (p)-[:CONTAINS*]->(c:Class)
                OPTIONAL MATCH (p)-[:CONTAINS*]->(f:Function)
                RETURN count(DISTINCT m) AS modules,
                       count(DISTINCT c) AS classes,
                       count(DISTINCT f) AS functions
            """, projectId=project_id)
            
            counts_data = await counts_result.single()
            
            return {
                "project_id": project_id,
                "component_counts": {
                    "modules": counts_data['modules'] if counts_data else 0,
                    "classes": counts_data['classes'] if counts_data else 0,
                    "functions": counts_data['functions'] if counts_data else 0
                },
                "complexity_metrics": {
                    "average_complexity": complexity_data['avgComplexity'] if complexity_data else 0,
                    "max_complexity": complexity_data['maxComplexity'] if complexity_data else 0,
                    "total_complexity": complexity_data['totalComplexity'] if complexity_data else 0
                },
                "coupling_metrics": coupling_data,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def delete_project_graph(self, project_id: str) -> bool:
        """
        Delete all graph data for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            Success status
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            try:
                await session.run("""
                    MATCH (p:Project {projectId: $projectId})
                    OPTIONAL MATCH (p)-[:CONTAINS*0..]->(child)
                    DETACH DELETE p, child
                """, projectId=project_id)
                return True
            except Exception as e:
                print(f"Error deleting project graph: {e}")
                return False
    
    async def update_node_incremental(
        self,
        node_id: str,
        properties: Dict[str, Any]
    ) -> bool:
        """
        Update an existing node incrementally
        
        Args:
            node_id: Node identifier
            properties: Properties to update
            
        Returns:
            Success status
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            try:
                # Generic update - works for any node type
                set_clause = ", ".join([f"n.{key} = ${key}" for key in properties.keys()])
                
                query = f"""
                MATCH (n)
                WHERE id(n) = $nodeId OR 
                      n.projectId = $nodeId OR
                      n.moduleId = $nodeId OR
                      n.classId = $nodeId OR
                      n.functionId = $nodeId OR
                      n.fileId = $nodeId
                SET {set_clause}
                """
                
                await session.run(query, nodeId=node_id, **properties)
                return True
            except Exception as e:
                print(f"Error updating node: {e}")
                return False
