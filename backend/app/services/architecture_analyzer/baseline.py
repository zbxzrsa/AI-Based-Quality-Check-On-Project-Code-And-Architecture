"""
Baseline Snapshot Management

This module handles creation, storage, and retrieval of architectural baselines.
A baseline captures the state of the dependency graph at a specific point in time.
"""
import logging
logger = logging.getLogger(__name__)


import json
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from app.database.neo4j_db import get_neo4j_driver
from app.core.config import settings


@dataclass
class ArchitectureBaseline:
    """Represents a snapshot of the architecture at a point in time"""
    baseline_id: str
    project_id: str
    version: str
    timestamp: str
    nodes: List[Dict[str, Any]]  # All nodes with their properties
    relationships: List[Dict[str, Any]]  # All relationships
    metrics: Dict[str, Any]  # Aggregate metrics
    metadata: Dict[str, Any]  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert baseline to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchitectureBaseline":
        """Create baseline from dictionary"""
        return cls(**data)


class BaselineManager:
    """
    Manages architectural baseline snapshots
    
    Features:
    - Create baseline from current graph state
    - Store baselines in database or filesystem
    - Retrieve baselines by ID or version
    - Compare baselines
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize baseline manager
        
        Args:
            storage_path: Optional path for file-based storage (defaults to data/baselines)
        """
        self.storage_path = Path(storage_path or "data/baselines")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def create_baseline(
        self,
        project_id: str,
        version: str,
        description: Optional[str] = None
    ) -> ArchitectureBaseline:
        """
        Create a baseline snapshot of the current architecture
        
        Args:
            project_id: Project identifier
            version: Version label for the baseline (e.g., "v1.0.0", "2024-01-15")
            description: Optional description of the baseline
        
        Returns:
            ArchitectureBaseline object
        """
        driver = await get_neo4j_driver()
        
        # Capture current graph state
        nodes = await self._capture_nodes(driver, project_id)
        relationships = await self._capture_relationships(driver, project_id)
        metrics = await self._calculate_metrics(nodes, relationships)
        
        # Generate baseline ID
        baseline_id = self._generate_baseline_id(project_id, version)
        
        # Create baseline object
        baseline = ArchitectureBaseline(
            baseline_id=baseline_id,
            project_id=project_id,
            version=version,
            timestamp=datetime.utcnow().isoformat(),
            nodes=nodes,
            relationships=relationships,
            metrics=metrics,
            metadata={
                "description": description or f"Baseline for {project_id} version {version}",
                "node_count": len(nodes),
                "relationship_count": len(relationships)
            }
        )
        
        # Store baseline
        await self._store_baseline(baseline)
        
        return baseline
    
    async def get_baseline(
        self,
        project_id: str,
        version: Optional[str] = None,
        baseline_id: Optional[str] = None
    ) -> Optional[ArchitectureBaseline]:
        """
        Retrieve a baseline by version or ID
        
        Args:
            project_id: Project identifier
            version: Version label (optional if baseline_id provided)
            baseline_id: Baseline ID (optional if version provided)
        
        Returns:
            ArchitectureBaseline or None if not found
        """
        if baseline_id:
            return await self._load_baseline_by_id(baseline_id)
        elif version:
            baseline_id = self._generate_baseline_id(project_id, version)
            return await self._load_baseline_by_id(baseline_id)
        else:
            # Get latest baseline for project
            return await self._get_latest_baseline(project_id)
    
    async def list_baselines(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all baselines for a project
        
        Args:
            project_id: Project identifier
        
        Returns:
            List of baseline metadata dictionaries
        """
        baselines = []
        
        # List all baseline files for the project
        for baseline_file in self.storage_path.glob(f"{project_id}_*.json"):
            try:
                with open(baseline_file, 'r') as f:
                    data = json.load(f)
                    baselines.append({
                        "baseline_id": data["baseline_id"],
                        "version": data["version"],
                        "timestamp": data["timestamp"],
                        "node_count": data["metadata"]["node_count"],
                        "relationship_count": data["metadata"]["relationship_count"],
                        "description": data["metadata"].get("description", "")
                    })
            except Exception as e:
                logger.info("Error reading baseline file {baseline_file}: {str(e)}")
        
        # Sort by timestamp (newest first)
        baselines.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return baselines
    
    async def delete_baseline(self, baseline_id: str) -> bool:
        """
        Delete a baseline
        
        Args:
            baseline_id: Baseline ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        baseline_file = self.storage_path / f"{baseline_id}.json"
        
        if baseline_file.exists():
            baseline_file.unlink()
            return True
        
        return False
    
    async def _capture_nodes(
        self,
        driver: Any,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Capture all nodes from the graph
        
        Args:
            driver: Neo4j driver instance
            project_id: Project identifier
        
        Returns:
            List of node dictionaries
        """
        nodes = []
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                query = """
                MATCH (n:CodeEntity)
                WHERE n.project_id = $project_id OR NOT exists(n.project_id)
                RETURN 
                    id(n) as node_id,
                    labels(n) as labels,
                    properties(n) as properties
                """
                
                result = await session.run(query, project_id=project_id)
                
                async for record in result:
                    nodes.append({
                        "node_id": record["node_id"],
                        "labels": record["labels"],
                        "properties": dict(record["properties"])
                    })
        
        except Exception as e:
            logger.info("Error capturing nodes: {str(e)}")
        
        return nodes
    
    async def _capture_relationships(
        self,
        driver: Any,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Capture all relationships from the graph
        
        Args:
            driver: Neo4j driver instance
            project_id: Project identifier
        
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                query = """
                MATCH (source:CodeEntity)-[r]->(target:CodeEntity)
                WHERE (source.project_id = $project_id OR NOT exists(source.project_id))
                  AND (target.project_id = $project_id OR NOT exists(target.project_id))
                RETURN 
                    id(r) as rel_id,
                    id(source) as source_id,
                    id(target) as target_id,
                    type(r) as rel_type,
                    properties(r) as properties,
                    source.name as source_name,
                    target.name as target_name
                """
                
                result = await session.run(query, project_id=project_id)
                
                async for record in result:
                    relationships.append({
                        "rel_id": record["rel_id"],
                        "source_id": record["source_id"],
                        "target_id": record["target_id"],
                        "source_name": record["source_name"],
                        "target_name": record["target_name"],
                        "rel_type": record["rel_type"],
                        "properties": dict(record["properties"])
                    })
        
        except Exception as e:
            logger.info("Error capturing relationships: {str(e)}")
        
        return relationships
    
    async def _calculate_metrics(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metrics for the baseline
        
        Args:
            nodes: List of node dictionaries
            relationships: List of relationship dictionaries
        
        Returns:
            Dictionary of metrics
        """
        # Count nodes by type
        node_types = {}
        total_complexity = 0
        total_loc = 0
        
        for node in nodes:
            props = node["properties"]
            node_type = props.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
            
            total_complexity += props.get("complexity", 0)
            total_loc += props.get("lines_of_code", 0)
        
        # Count relationships by type
        rel_types = {}
        for rel in relationships:
            rel_type = rel["rel_type"]
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
        
        # Calculate average complexity
        avg_complexity = total_complexity / len(nodes) if nodes else 0
        
        return {
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
            "node_types": node_types,
            "relationship_types": rel_types,
            "total_complexity": total_complexity,
            "average_complexity": round(avg_complexity, 2),
            "total_lines_of_code": total_loc
        }
    
    def _generate_baseline_id(self, project_id: str, version: str) -> str:
        """
        Generate a unique baseline ID
        
        Args:
            project_id: Project identifier
            version: Version label
        
        Returns:
            Baseline ID string
        """
        # Create hash of project_id and version for uniqueness
        hash_input = f"{project_id}_{version}".encode()
        hash_suffix = hashlib.md5(hash_input).hexdigest()[:8]
        
        # Clean version string for filename
        clean_version = version.replace("/", "-").replace("\\", "-").replace(" ", "_")
        
        return f"{project_id}_{clean_version}_{hash_suffix}"
    
    async def _store_baseline(self, baseline: ArchitectureBaseline) -> None:
        """
        Store baseline to filesystem
        
        Args:
            baseline: ArchitectureBaseline to store
        """
        baseline_file = self.storage_path / f"{baseline.baseline_id}.json"
        
        try:
            with open(baseline_file, 'w') as f:
                json.dump(baseline.to_dict(), f, indent=2)
        except Exception as e:
            logger.info("Error storing baseline: {str(e)}")
            raise
    
    async def _load_baseline_by_id(
        self,
        baseline_id: str
    ) -> Optional[ArchitectureBaseline]:
        """
        Load baseline from filesystem by ID
        
        Args:
            baseline_id: Baseline ID
        
        Returns:
            ArchitectureBaseline or None if not found
        """
        # Validate baseline_id to prevent path traversal
        if not baseline_id or '..' in baseline_id or '/' in baseline_id or '\\' in baseline_id:
            logger.warning(f"Invalid baseline_id rejected: {baseline_id}")
            return None
            
        baseline_file = self.storage_path / f"{baseline_id}.json"
        
        if not baseline_file.exists():
            return None
        
        try:
            with open(baseline_file, 'r') as f:
                data = json.load(f)
                return ArchitectureBaseline.from_dict(data)
        except Exception as e:
            logger.info(f"Error loading baseline: {str(e)}")
            return None
    
    async def _get_latest_baseline(
        self,
        project_id: str
    ) -> Optional[ArchitectureBaseline]:
        """
        Get the most recent baseline for a project
        
        Args:
            project_id: Project identifier
        
        Returns:
            ArchitectureBaseline or None if no baselines exist
        """
        baselines = await self.list_baselines(project_id)
        
        if not baselines:
            return None
        
        # Get the most recent baseline
        latest = baselines[0]
        return await self._load_baseline_by_id(latest["baseline_id"])
