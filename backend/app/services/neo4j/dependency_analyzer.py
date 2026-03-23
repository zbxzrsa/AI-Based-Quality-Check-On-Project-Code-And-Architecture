"""
Dependency Analyzer Service

Handles dependency analysis including circular dependencies,
layer violations, and coupling metrics.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.config import settings


class DependencyAnalyzer:
    """
    Service for analyzing dependencies in the code graph.
    
    Responsibilities:
    - Detect circular dependencies
    - Detect layer violations
    - Calculate coupling metrics
    - Find dependency paths
    """
    
    def __init__(self, driver):
        """
        Initialize dependency analyzer.
        
        Args:
            driver: Neo4j async driver
        """
        self.driver = driver
    
    async def find_circular_dependencies(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find circular dependencies in the project.
        
        Args:
            project_id: Project identifier
            
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
    
    async def detect_direct_cycles(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Detect only direct 2-hop cyclic dependencies (most critical).
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of direct cycles
        """
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(a:Module)
        MATCH (a)-[:DEPENDS_ON]->(b:Module)
        MATCH (b)-[:DEPENDS_ON]->(a)
        RETURN a.name AS module_a,
               b.name AS module_b,
               'DIRECT_CYCLE' AS type,
               'CRITICAL' AS severity
        """
        
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            return await result.data()
    
    async def detect_layer_violations(
        self,
        project_id: str,
        layer_definitions: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect layer violations (e.g., Controller directly to Repository).
        
        Args:
            project_id: Project identifier
            layer_definitions: Optional custom layer definitions
            
        Returns:
            List of layer violations
        """
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(source:Module)
        MATCH (source)-[:DEPENDS_ON]->(target:Module)
        WHERE source.layerType IS NOT NULL 
          AND target.layerType IS NOT NULL
          AND source.layerRank > target.layerRank + 1
        RETURN source.name AS source_module,
               source.layerType AS source_type,
               target.name AS target_module,
               target.layerType AS target_type,
               [source.name, target.name] AS violation_path,
               'layer_skip' AS violation_type,
               'HIGH' AS severity
        """
        
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            return await result.data()
    
    async def calculate_coupling_metrics(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Calculate coupling metrics for all modules.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Coupling metrics including efferent, afferent, and instability
        """
        query = """
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
        """
        
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            coupling_data = await result.data()
            
            return {
                'modules': coupling_data,
                'summary': {
                    'total_modules': len(coupling_data),
                    'avg_instability': sum(m['instability'] for m in coupling_data) / len(coupling_data) if coupling_data else 0,
                    'high_instability_count': sum(1 for m in coupling_data if m['instability'] > 0.7)
                }
            }
    
    async def find_longest_dependency_paths(
        self,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find longest dependency paths (refactoring candidates).
        
        Args:
            project_id: Project identifier
            limit: Maximum number of paths to return
            
        Returns:
            List of longest dependency paths
        """
        query = f"""
        MATCH (p:Project {{projectId: $projectId}})-[:CONTAINS*]->(start:Module)
        MATCH path = (start)-[:DEPENDS_ON*3..]->(end:Module)
        WHERE start <> end
        RETURN [n IN nodes(path) | n.name] AS path_modules,
               length(path) AS path_length,
               start.name AS start_module,
               end.name AS end_module
        ORDER BY path_length DESC
        LIMIT {limit}
        """
        
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            return await result.data()
    
    async def get_dependency_graph(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Export dependency graph for visualization.
        
        Args:
            project_id: Project identifier
            
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
                "links": edges,
                "metadata": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "project_id": project_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
