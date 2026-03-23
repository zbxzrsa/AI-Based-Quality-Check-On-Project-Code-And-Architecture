"""
Graph Builder Service

This service creates and updates code entity nodes and dependency relationships
in the Neo4j graph database. It provides batch operations for performance optimization.

Implements Requirement 1.3: Update Graph_Database with new dependencies
"""
import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from app.database.neo4j_db import get_neo4j_driver
from app.core.config import settings
from app.services.code_entity_extractor import CodeEntity
from app.schemas.ast_models import DependencyGraph
from .models import (
    GraphUpdateResult
)


class GraphBuilderService:
    """
    Service for building and updating code dependency graphs in Neo4j
    
    Features:
    - Create/update code entity nodes (functions, classes, modules)
    - Create dependency relationships (imports, calls, inheritance)
    - Batch operations for performance
    - Transaction management for consistency
    """
    
    def __init__(self):
        """Initialize graph builder service"""
        self.batch_size = 1000  # Process in batches of 1000 for performance
    
    async def create_or_update_entity_node(
        self,
        entity: CodeEntity,
        project_id: Optional[str] = None
    ) -> GraphUpdateResult:
        """
        Create or update a single code entity node in Neo4j
        
        Args:
            entity: CodeEntity object to create/update
            project_id: Optional project identifier
        
        Returns:
            GraphUpdateResult with operation statistics
        """
        driver = await get_neo4j_driver()
        result = GraphUpdateResult()
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Determine node label based on entity type
                label = self._get_node_label(entity.entity_type)
                
                # Build properties
                properties = {
                    "name": entity.name,
                    "type": entity.entity_type,
                    "file_path": entity.file_path,
                    "complexity": entity.complexity,
                    "lines_of_code": entity.lines_of_code,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                if project_id:
                    properties["project_id"] = project_id
                
                # Use MERGE to create or update
                query = f"""
                MERGE (n:{label} {{name: $name, file_path: $file_path}})
                ON CREATE SET n += $properties, n.created_at = $timestamp
                ON MATCH SET n += $properties
                RETURN n, 
                       CASE WHEN n.created_at = $timestamp THEN 'created' ELSE 'updated' END as operation
                """
                
                query_result = await session.run(
                    query,
                    name=entity.name,
                    file_path=entity.file_path,
                    properties=properties,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                record = await query_result.single()
                if record:
                    if record["operation"] == "created":
                        result.nodes_created = 1
                    else:
                        result.nodes_updated = 1
        
        except Exception as e:
            result.errors.append(f"Error creating/updating entity {entity.name}: {str(e)}")
        
        return result
    
    async def create_or_update_entity_nodes_batch(
        self,
        entities: List[CodeEntity],
        project_id: Optional[str] = None
    ) -> GraphUpdateResult:
        """
        Create or update multiple code entity nodes in batches
        
        Args:
            entities: List of CodeEntity objects
            project_id: Optional project identifier
        
        Returns:
            GraphUpdateResult with aggregated statistics
        """
        driver = await get_neo4j_driver()
        total_result = GraphUpdateResult()
        
        # Process in batches for performance
        for i in range(0, len(entities), self.batch_size):
            batch = entities[i:i + self.batch_size]
            
            try:
                async with driver.session(database=settings.NEO4J_DATABASE) as session:
                    # Build batch data
                    batch_data = []
                    for entity in batch:
                        properties = {
                            "name": entity.name,
                            "type": entity.entity_type,
                            "file_path": entity.file_path,
                            "complexity": entity.complexity,
                            "lines_of_code": entity.lines_of_code,
                            "updated_at": datetime.utcnow().isoformat()
                        }
                        
                        if project_id:
                            properties["project_id"] = project_id
                        
                        batch_data.append({
                            "name": entity.name,
                            "file_path": entity.file_path,
                            "label": self._get_node_label(entity.entity_type),
                            "properties": properties
                        })
                    
                    # Execute batch operation
                    query = """
                    UNWIND $batch as item
                    CALL {
                        WITH item
                        CALL apoc.merge.node(
                            [item.label],
                            {name: item.name, file_path: item.file_path},
                            item.properties,
                            item.properties
                        ) YIELD node
                        RETURN node
                    }
                    RETURN count(*) as count
                    """
                    
                    # Fallback query if APOC is not available
                    fallback_query = """
                    UNWIND $batch as item
                    MERGE (n:CodeEntity {name: item.name, file_path: item.file_path})
                    ON CREATE SET n += item.properties, n.created_at = $timestamp
                    ON MATCH SET n += item.properties
                    RETURN count(*) as count
                    """
                    
                    async with session.begin_transaction() as tx:
                        try:
                            try:
                                query_result = await tx.run(
                                    query,
                                    batch=batch_data,
                                    timestamp=datetime.utcnow().isoformat()
                                )
                            except Exception:
                                # Fallback if APOC is not available
                                query_result = await tx.run(
                                    fallback_query,
                                    batch=batch_data,
                                    timestamp=datetime.utcnow().isoformat()
                                )
                            
                            record = await query_result.single()
                            await tx.commit()
                            
                            if record:
                                # Approximate: assume half created, half updated
                                total_result.nodes_created += len(batch) // 2
                                total_result.nodes_updated += len(batch) - (len(batch) // 2)
                        except Exception as e:
                            await tx.rollback()
                            raise e
            
            except Exception as e:
                total_result.errors.append(f"Error in batch {i//self.batch_size}: {str(e)}")
        
        return total_result
    
    async def create_dependency_relationship(
        self,
        source_entity: CodeEntity,
        target_entity: CodeEntity,
        relationship_type: str = "DEPENDS_ON",
        properties: Optional[Dict[str, Any]] = None
    ) -> GraphUpdateResult:
        """
        Create a dependency relationship between two entities
        
        Args:
            source_entity: Source code entity
            target_entity: Target code entity
            relationship_type: Type of relationship (DEPENDS_ON, CALLS, IMPORTS, INHERITS)
            properties: Optional relationship properties
        
        Returns:
            GraphUpdateResult with operation statistics
        """
        driver = await get_neo4j_driver()
        result = GraphUpdateResult()
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build relationship properties
                rel_props = properties or {}
                rel_props["created_at"] = datetime.utcnow().isoformat()
                
                # Create relationship
                query = """
                MATCH (source:CodeEntity {name: $source_name, file_path: $source_file})
                MATCH (target:CodeEntity {name: $target_name, file_path: $target_file})
                MERGE (source)-[r:%s]->(target)
                ON CREATE SET r += $properties
                RETURN r, 
                       CASE WHEN r.created_at = $timestamp THEN 'created' ELSE 'existing' END as operation
                """ % relationship_type
                
                query_result = await session.run(
                    query,
                    source_name=source_entity.name,
                    source_file=source_entity.file_path,
                    target_name=target_entity.name,
                    target_file=target_entity.file_path,
                    properties=rel_props,
                    timestamp=rel_props["created_at"]
                )
                
                record = await query_result.single()
                if record:
                    if record["operation"] == "created":
                        result.relationships_created = 1
                    else:
                        result.relationships_updated = 1
        
        except Exception as e:
            result.errors.append(
                f"Error creating relationship {source_entity.name} -> {target_entity.name}: {str(e)}"
            )
        
        return result
    
    async def create_dependency_relationships_batch(
        self,
        relationships: List[Tuple[CodeEntity, CodeEntity, str, Optional[Dict]]],
        project_id: Optional[str] = None
    ) -> GraphUpdateResult:
        """
        Create multiple dependency relationships in batches
        
        Args:
            relationships: List of tuples (source, target, rel_type, properties)
            project_id: Optional project identifier
        
        Returns:
            GraphUpdateResult with aggregated statistics
        """
        driver = await get_neo4j_driver()
        total_result = GraphUpdateResult()
        
        # Process in batches
        for i in range(0, len(relationships), self.batch_size):
            batch = relationships[i:i + self.batch_size]
            
            try:
                async with driver.session(database=settings.NEO4J_DATABASE) as session:
                    # Build batch data
                    batch_data = []
                    for source, target, rel_type, props in batch:
                        rel_props = props or {}
                        rel_props["created_at"] = datetime.utcnow().isoformat()
                        
                        if project_id:
                            rel_props["project_id"] = project_id
                        
                        batch_data.append({
                            "source_name": source.name,
                            "source_file": source.file_path,
                            "target_name": target.name,
                            "target_file": target.file_path,
                            "rel_type": rel_type,
                            "properties": rel_props
                        })
                    
                    # Execute batch operation
                    query = """
                    UNWIND $batch as item
                    MATCH (source:CodeEntity {name: item.source_name, file_path: item.source_file})
                    MATCH (target:CodeEntity {name: item.target_name, file_path: item.target_file})
                    CALL apoc.merge.relationship(
                        source,
                        item.rel_type,
                        {},
                        item.properties,
                        target,
                        {}
                    ) YIELD rel
                    RETURN count(*) as count
                    """
                    
                    # Fallback query if APOC is not available
                    fallback_query = """
                    UNWIND $batch as item
                    MATCH (source:CodeEntity {name: item.source_name, file_path: item.source_file})
                    MATCH (target:CodeEntity {name: item.target_name, file_path: item.target_file})
                    MERGE (source)-[r:DEPENDS_ON]->(target)
                    ON CREATE SET r += item.properties
                    RETURN count(*) as count
                    """
                    
                    async with session.begin_transaction() as tx:
                        try:
                            try:
                                query_result = await tx.run(query, batch=batch_data)
                            except Exception:
                                # Fallback if APOC is not available
                                query_result = await tx.run(fallback_query, batch=batch_data)
                            
                            record = await query_result.single()
                            if record:
                                total_result.relationships_created += record["count"]
                            
                            await tx.commit()
                        except Exception as e:
                            await tx.rollback()
                            raise e
            
            except Exception as e:
                total_result.errors.append(f"Error in relationship batch {i//self.batch_size}: {str(e)}")
        
        return total_result
    
    async def build_dependency_graph_from_entities(
        self,
        entities: List[CodeEntity],
        dependency_graph: DependencyGraph,
        project_id: Optional[str] = None
    ) -> GraphUpdateResult:
        """
        Build complete dependency graph from entities and dependency information
        
        Args:
            entities: List of code entities
            dependency_graph: Dependency graph with edges
            project_id: Optional project identifier
        
        Returns:
            GraphUpdateResult with aggregated statistics
        """
        total_result = GraphUpdateResult()
        
        # Step 1: Create all entity nodes in batch
        nodes_result = await self.create_or_update_entity_nodes_batch(entities, project_id)
        total_result = total_result + nodes_result
        
        # Step 2: Build relationships from dependency graph
        relationships = []
        
        # Create entity lookup by name
        entity_map = {e.name: e for e in entities}
        
        for edge in dependency_graph.edges:
            source = entity_map.get(edge.source)
            target = entity_map.get(edge.target)
            
            if source and target:
                rel_type = self._map_edge_type_to_relationship(edge.type)
                properties = {
                    "weight": edge.weight,
                    "edge_type": edge.type
                }
                relationships.append((source, target, rel_type, properties))
        
        # Step 3: Create relationships in batch
        if relationships:
            rels_result = await self.create_dependency_relationships_batch(relationships, project_id)
            total_result = total_result + rels_result
        
        return total_result
    
    async def update_entity_metrics(
        self,
        entity_name: str,
        file_path: str,
        metrics: Dict[str, Any]
    ) -> GraphUpdateResult:
        """
        Update metrics for an existing entity
        
        Args:
            entity_name: Name of the entity
            file_path: File path of the entity
            metrics: Dictionary of metrics to update
        
        Returns:
            GraphUpdateResult with operation statistics
        """
        driver = await get_neo4j_driver()
        result = GraphUpdateResult()
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                query = """
                MATCH (n:CodeEntity {name: $name, file_path: $file_path})
                SET n += $metrics, n.metrics_updated_at = $timestamp
                RETURN n
                """
                
                query_result = await session.run(
                    query,
                    name=entity_name,
                    file_path=file_path,
                    metrics=metrics,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                record = await query_result.single()
                if record:
                    result.nodes_updated = 1
                else:
                    result.errors.append(f"Entity not found: {entity_name} in {file_path}")
        
        except Exception as e:
            result.errors.append(f"Error updating metrics for {entity_name}: {str(e)}")
        
        return result
    
    async def delete_entities_by_file(
        self,
        file_path: str,
        project_id: Optional[str] = None
    ) -> GraphUpdateResult:
        """
        Delete all entities associated with a file
        
        Args:
            file_path: Path to the file
            project_id: Optional project identifier
        
        Returns:
            GraphUpdateResult with operation statistics
        """
        driver = await get_neo4j_driver()
        result = GraphUpdateResult()
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build query with optional project filter
                where_clause = "n.file_path = $file_path"
                if project_id:
                    where_clause += " AND n.project_id = $project_id"
                
                query = f"""
                MATCH (n:CodeEntity)
                WHERE {where_clause}
                DETACH DELETE n
                RETURN count(n) as deleted_count
                """
                
                params = {"file_path": file_path}
                if project_id:
                    params["project_id"] = project_id
                
                query_result = await session.run(query, **params)
                record = await query_result.single()
                
                if record:
                    # Count as nodes updated (deleted)
                    result.nodes_updated = record["deleted_count"]
        
        except Exception as e:
            result.errors.append(f"Error deleting entities for file {file_path}: {str(e)}")
        
        return result
    
    async def get_entity_dependencies(
        self,
        entity_name: str,
        file_path: str,
        depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get dependencies for an entity up to specified depth
        
        Args:
            entity_name: Name of the entity
            file_path: File path of the entity
            depth: Depth of dependency traversal (default: 1)
        
        Returns:
            List of dependency dictionaries
        """
        driver = await get_neo4j_driver()
        dependencies = []
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                query = """
                MATCH path = (source:CodeEntity {name: $name, file_path: $file_path})
                             -[r*1..%d]->(target:CodeEntity)
                RETURN target.name as name,
                       target.type as type,
                       target.file_path as file_path,
                       length(path) as distance,
                       [rel in relationships(path) | type(rel)] as relationship_types
                """ % depth
                
                query_result = await session.run(
                    query,
                    name=entity_name,
                    file_path=file_path
                )
                
                async for record in query_result:
                    dependencies.append({
                        "name": record["name"],
                        "type": record["type"],
                        "file_path": record["file_path"],
                        "distance": record["distance"],
                        "relationship_types": record["relationship_types"]
                    })
        
        except Exception as e:
            logger.info("Error getting dependencies for {entity_name}: {str(e)}")
        
        return dependencies
    
    def _get_node_label(self, entity_type: str) -> str:
        """
        Map entity type to Neo4j node label
        
        Args:
            entity_type: Entity type string
        
        Returns:
            Neo4j node label
        """
        label_map = {
            "function": "Function",
            "class": "Class",
            "method": "Method",
            "module": "Module",
            "file": "File"
        }
        return label_map.get(entity_type.lower(), "CodeEntity")
    
    def _map_edge_type_to_relationship(self, edge_type: str) -> str:
        """
        Map dependency edge type to Neo4j relationship type
        
        Args:
            edge_type: Edge type from dependency graph
        
        Returns:
            Neo4j relationship type
        """
        rel_map = {
            "import": "IMPORTS",
            "call": "CALLS",
            "inheritance": "INHERITS",
            "uses": "USES"
        }
        return rel_map.get(edge_type.lower(), "DEPENDS_ON")
