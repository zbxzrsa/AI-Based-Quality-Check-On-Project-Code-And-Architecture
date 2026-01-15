"""
Neo4j graph database service
Handles code architecture graph operations
"""
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.core.config import settings


class Neo4jService:
    """Service class for Neo4j graph database operations"""
    
    def __init__(self, driver: AsyncDriver):
        self.driver = driver
    
    async def insert_project(
        self,
        project_id: str,
        name: str,
        language: str
    ) -> Dict[str, Any]:
        """Insert a new project node"""
        query = """
        MERGE (p:Project {projectId: $projectId})
        SET p.name = $name,
            p.language = $language,
            p.createdAt = datetime()
        RETURN p
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(
                query,
                projectId=project_id,
                name=name,
                language=language
            )
            record = await result.single()
            return dict(record["p"]) if record else {}
    
    async def insert_module(
        self,
        project_id: str,
        module_id: str,
        name: str,
        path: str,
        module_type: str
    ) -> Dict[str, Any]:
        """Insert a module node and link it to project"""
        query = """
        MATCH (p:Project {projectId: $projectId})
        MERGE (m:Module {moduleId: $moduleId})
        SET m.name = $name,
            m.path = $path,
            m.type = $type
        MERGE (p)-[:CONTAINS {level: 'module'}]->(m)
        RETURN m
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(
                query,
                projectId=project_id,
                moduleId=module_id,
                name=name,
                path=path,
                type=module_type
            )
            record = await result.single()
            return dict(record["m"]) if record else {}
    
    async def find_circular_dependencies(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Find circular dependencies in module graph"""
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
        MATCH path = (m1)-[:DEPENDS_ON*]->(m1)
        WHERE length(path) >1
        RETURN m1.name AS module,
               [n IN nodes(path) | n.name] AS cycle,
               length(path) AS cycleLength
        ORDER BY cycleLength DESC
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            records = await result.data()
            return records
    
    async def calculate_coupling_metrics(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Calculate coupling metrics for all modules"""
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
        OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dependency:Module)
        WITH m, count(DISTINCT dependency) AS ce
        OPTIONAL MATCH (m)<-[:DEPENDS_ON]-(dependent:Module)
        WITH m, ce, count(DISTINCT dependent) AS ca
        WITH m, ca, ce, ca + ce AS totalCoupling
        RETURN m.name AS module,
               ca AS afferentCoupling,
               ce AS efferentCoupling,
               CASE
                   WHEN totalCoupling = 0 THEN 0.0
                   ELSE toFloat(ce) / totalCoupling
               END AS instability
        ORDER BY instability DESC
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            records = await result.data()
            return records
    
    async def find_critical_paths(
        self,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find critical call paths in the codebase"""
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(f:Function)
        WHERE f.complexity > 10
        MATCH (caller)-[c:CALLS]->(f)
        WITH f, sum(c.frequency) AS totalCalls
        RETURN f.name AS functionName,
               f.complexity AS complexity,
               totalCalls AS callFrequency,
               totalCalls * f.complexity AS riskScore
        ORDER BY riskScore DESC
        LIMIT $limit
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id, limit=limit)
            records = await result.data()
            return records
    
    async def detect_architectural_violations(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Detect architectural violations"""
        query = """
        MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->()-[v:VIOLATES]->()
        WHERE v.detectedAt > datetime() - duration({days: 30})
        RETURN v.violationType AS type,
               v.severity AS severity,
               v.description AS description,
               v.detectedAt AS detectedAt
        ORDER BY v.severity DESC, v.detectedAt DESC
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            records = await result.data()
            return records
    
    async def get_project_overview(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Get overview statistics for a project"""
        query = """
        MATCH (p:Project {projectId: $projectId})
        OPTIONAL MATCH (p)-[:CONTAINS]->(m:Module)
        OPTIONAL MATCH (p)-[:CONTAINS*]->(c:Class)
        OPTIONAL MATCH (p)-[:CONTAINS*]->(f:Function)
        RETURN p.name AS project,
               count(DISTINCT m) AS modules,
               count(DISTINCT c) AS classes,
               count(DISTINCT f) AS functions
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, projectId=project_id)
            record = await result.single()
            return dict(record) if record else {}


# Helper function to get Neo4j service instance
async def get_neo4j_service() -> Neo4jService:
    """Get Neo4j service instance with driver"""
    from app.database.neo4j_db import get_neo4j_driver
    driver = await get_neo4j_driver()
    return Neo4jService(driver)
