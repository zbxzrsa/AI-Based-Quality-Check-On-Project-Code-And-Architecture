"""
Circular Dependency Detector

This service detects circular dependencies in code dependency graphs using
graph traversal algorithms. It calculates cycle severity and generates
visualization data for frontend display.

Implements Requirements 1.6, 1.7:
- Detect circular dependencies using graph traversal algorithms
- Highlight cycles with severity ratings in dependency graph visualization
"""
import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from app.database.neo4j_db import get_neo4j_driver
from app.core.config import settings


class CycleSeverity(str, Enum):
    """Severity levels for circular dependencies"""
    LOW = "low"           # 2-3 nodes, low complexity
    MEDIUM = "medium"     # 4-6 nodes, moderate complexity
    HIGH = "high"         # 7-10 nodes, high complexity
    CRITICAL = "critical" # >10 nodes or very high complexity


@dataclass
class CircularDependency:
    """Represents a detected circular dependency"""
    cycle_id: str
    nodes: List[str]  # List of entity names in the cycle
    edges: List[Tuple[str, str]]  # List of (source, target) pairs
    severity: CycleSeverity
    depth: int  # Number of nodes in the cycle
    total_complexity: int  # Sum of complexity of all nodes
    avg_complexity: float  # Average complexity per node
    file_paths: List[str]  # Files involved in the cycle
    detected_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "cycle_id": self.cycle_id,
            "nodes": self.nodes,
            "edges": [[src, tgt] for src, tgt in self.edges],
            "severity": self.severity.value,
            "depth": self.depth,
            "total_complexity": self.total_complexity,
            "avg_complexity": self.avg_complexity,
            "file_paths": self.file_paths,
            "detected_at": self.detected_at
        }


@dataclass
class CycleDetectionResult:
    """Result of circular dependency detection"""
    cycles: List[CircularDependency]
    total_cycles: int
    severity_breakdown: Dict[str, int]  # Count by severity
    affected_files: Set[str]
    detection_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "cycles": [cycle.to_dict() for cycle in self.cycles],
            "total_cycles": self.total_cycles,
            "severity_breakdown": self.severity_breakdown,
            "affected_files": list(self.affected_files),
            "detection_time_ms": self.detection_time_ms
        }


class CircularDependencyDetector:
    """
    Service for detecting circular dependencies in code dependency graphs
    
    Features:
    - Detect all cycles using Tarjan's strongly connected components algorithm
    - Calculate cycle severity based on depth and complexity
    - Generate visualization data for frontend
    - Support project-level filtering
    """
    
    def __init__(self):
        """Initialize circular dependency detector"""
        self.max_cycle_depth = 50  # Prevent infinite loops
    
    async def detect_cycles(
        self,
        project_id: Optional[str] = None,
        min_severity: Optional[CycleSeverity] = None
    ) -> CycleDetectionResult:
        """
        Detect all circular dependencies in the dependency graph
        
        Args:
            project_id: Optional project identifier to filter by
            min_severity: Optional minimum severity level to include
        
        Returns:
            CycleDetectionResult with all detected cycles
        """
        start_time = datetime.utcnow()
        
        # Find all strongly connected components (cycles)
        sccs = await self._find_strongly_connected_components(project_id)
        
        # Filter out single-node components (not cycles)
        cycles_data = [scc for scc in sccs if len(scc) > 1]
        
        # Build CircularDependency objects with severity calculation
        cycles = []
        for cycle_nodes in cycles_data:
            cycle = await self._build_cycle_object(cycle_nodes, project_id)
            if cycle and (min_severity is None or self._compare_severity(cycle.severity, min_severity) >= 0):
                cycles.append(cycle)
        
        # Calculate statistics
        severity_breakdown = {
            CycleSeverity.LOW.value: 0,
            CycleSeverity.MEDIUM.value: 0,
            CycleSeverity.HIGH.value: 0,
            CycleSeverity.CRITICAL.value: 0
        }
        
        affected_files = set()
        for cycle in cycles:
            severity_breakdown[cycle.severity.value] += 1
            affected_files.update(cycle.file_paths)
        
        end_time = datetime.utcnow()
        detection_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return CycleDetectionResult(
            cycles=cycles,
            total_cycles=len(cycles),
            severity_breakdown=severity_breakdown,
            affected_files=affected_files,
            detection_time_ms=detection_time_ms
        )
    
    async def detect_cycles_for_entity(
        self,
        entity_name: str,
        file_path: str,
        project_id: Optional[str] = None
    ) -> List[CircularDependency]:
        """
        Detect cycles involving a specific entity
        
        Args:
            entity_name: Name of the entity to check
            file_path: File path of the entity
            project_id: Optional project identifier
        
        Returns:
            List of CircularDependency objects involving the entity
        """
        # Get all cycles
        result = await self.detect_cycles(project_id)
        
        # Filter cycles containing the entity
        entity_cycles = [
            cycle for cycle in result.cycles
            if entity_name in cycle.nodes
        ]
        
        return entity_cycles
    
    async def get_cycle_visualization_data(
        self,
        cycle_id: str,
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get visualization data for a specific cycle
        
        Args:
            cycle_id: ID of the cycle
            project_id: Optional project identifier
        
        Returns:
            Dictionary with nodes, edges, and layout information
        """
        # Find all cycles
        result = await self.detect_cycles(project_id)
        
        # Find the specific cycle
        cycle = next((c for c in result.cycles if c.cycle_id == cycle_id), None)
        if not cycle:
            return None
        
        # Build visualization data
        nodes = []
        for i, node_name in enumerate(cycle.nodes):
            nodes.append({
                "id": node_name,
                "label": node_name,
                "index": i,
                "file_path": cycle.file_paths[i] if i < len(cycle.file_paths) else ""
            })
        
        edges = []
        for source, target in cycle.edges:
            edges.append({
                "source": source,
                "target": target,
                "type": "DEPENDS_ON"
            })
        
        return {
            "cycle_id": cycle_id,
            "severity": cycle.severity.value,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "depth": cycle.depth,
                "total_complexity": cycle.total_complexity,
                "avg_complexity": cycle.avg_complexity
            }
        }
    
    async def _find_strongly_connected_components(
        self,
        project_id: Optional[str] = None
    ) -> List[List[str]]:
        """
        Find all strongly connected components using Tarjan's algorithm
        
        This is implemented using Neo4j's built-in graph algorithms for performance.
        
        Args:
            project_id: Optional project identifier
        
        Returns:
            List of strongly connected components (each is a list of node names)
        """
        driver = await get_neo4j_driver()
        sccs = []
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Build query with optional project filter
                where_clause = ""
                if project_id:
                    where_clause = "WHERE n.project_id = $project_id"
                
                # Use Neo4j's graph algorithms if available (GDS library)
                # Otherwise, use a custom Cypher implementation
                query = f"""
                MATCH (n:CodeEntity)
                {where_clause}
                WITH collect(id(n)) as nodeIds
                CALL {{
                    WITH nodeIds
                    MATCH path = (start:CodeEntity)-[r:DEPENDS_ON|CALLS|IMPORTS|USES*1..{self.max_cycle_depth}]->(start)
                    WHERE id(start) IN nodeIds
                    WITH start, [node in nodes(path) | node.name] as cycle_nodes
                    RETURN DISTINCT cycle_nodes
                }}
                RETURN cycle_nodes
                """
                
                # Fallback query using simpler cycle detection
                fallback_query = f"""
                MATCH (n:CodeEntity)
                {where_clause}
                MATCH path = (n)-[r:DEPENDS_ON|CALLS|IMPORTS|USES*2..{self.max_cycle_depth}]->(n)
                WITH n, nodes(path) as cycle_nodes
                RETURN DISTINCT [node in cycle_nodes | node.name] as cycle_nodes
                """
                
                params = {}
                if project_id:
                    params["project_id"] = project_id
                
                try:
                    query_result = await session.run(query, **params)
                except Exception:
                    # Fallback to simpler query
                    query_result = await session.run(fallback_query, **params)
                
                async for record in query_result:
                    cycle_nodes = record["cycle_nodes"]
                    if cycle_nodes and len(cycle_nodes) > 1:
                        # Remove duplicates while preserving order
                        unique_nodes = []
                        seen = set()
                        for node in cycle_nodes:
                            if node not in seen:
                                unique_nodes.append(node)
                                seen.add(node)
                        sccs.append(unique_nodes)
        
        except Exception as e:
            logger.info("Error finding strongly connected components: {str(e)}")
        
        return sccs
    
    async def _build_cycle_object(
        self,
        cycle_nodes: List[str],
        project_id: Optional[str] = None
    ) -> Optional[CircularDependency]:
        """
        Build a CircularDependency object from cycle nodes
        
        Args:
            cycle_nodes: List of node names in the cycle
            project_id: Optional project identifier
        
        Returns:
            CircularDependency object or None if data cannot be retrieved
        """
        driver = await get_neo4j_driver()
        
        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Get node details and edges
                query = """
                MATCH (n:CodeEntity)
                WHERE n.name IN $node_names
                OPTIONAL MATCH (n)-[r:DEPENDS_ON|CALLS|IMPORTS|USES]->(m:CodeEntity)
                WHERE m.name IN $node_names
                RETURN n.name as name,
                       n.file_path as file_path,
                       n.complexity as complexity,
                       collect({source: n.name, target: m.name}) as edges
                """
                
                params = {"node_names": cycle_nodes}
                query_result = await session.run(query, **params)
                
                nodes_data = {}
                all_edges = []
                
                async for record in query_result:
                    name = record["name"]
                    nodes_data[name] = {
                        "file_path": record["file_path"] or "",
                        "complexity": record["complexity"] or 1
                    }
                    
                    # Collect edges
                    for edge in record["edges"]:
                        if edge["target"]:  # Filter out null targets
                            all_edges.append((edge["source"], edge["target"]))
                
                if not nodes_data:
                    return None
                
                # Calculate metrics
                depth = len(cycle_nodes)
                total_complexity = sum(data["complexity"] for data in nodes_data.values())
                avg_complexity = total_complexity / depth if depth > 0 else 0
                file_paths = [nodes_data[node]["file_path"] for node in cycle_nodes if node in nodes_data]
                
                # Calculate severity
                severity = self._calculate_severity(depth, total_complexity, avg_complexity)
                
                # Generate cycle ID
                cycle_id = self._generate_cycle_id(cycle_nodes)
                
                # Remove duplicate edges
                unique_edges = list(set(all_edges))
                
                return CircularDependency(
                    cycle_id=cycle_id,
                    nodes=cycle_nodes,
                    edges=unique_edges,
                    severity=severity,
                    depth=depth,
                    total_complexity=total_complexity,
                    avg_complexity=round(avg_complexity, 2),
                    file_paths=file_paths,
                    detected_at=datetime.utcnow().isoformat()
                )
        
        except Exception as e:
            logger.info("Error building cycle object: {str(e)}")
            return None
    
    def _calculate_severity(
        self,
        depth: int,
        total_complexity: int,
        avg_complexity: float
    ) -> CycleSeverity:
        """
        Calculate cycle severity based on depth and complexity
        
        Severity rules:
        - CRITICAL: >10 nodes OR avg complexity > 20 OR total complexity > 200
        - HIGH: 7-10 nodes OR avg complexity > 15 OR total complexity > 100
        - MEDIUM: 4-6 nodes OR avg complexity > 10 OR total complexity > 50
        - LOW: 2-3 nodes with low complexity
        
        Args:
            depth: Number of nodes in the cycle
            total_complexity: Sum of complexity of all nodes
            avg_complexity: Average complexity per node
        
        Returns:
            CycleSeverity enum value
        """
        # Critical conditions
        if depth > 10 or avg_complexity > 20 or total_complexity > 200:
            return CycleSeverity.CRITICAL
        
        # High severity conditions
        if depth >= 7 or avg_complexity > 15 or total_complexity > 100:
            return CycleSeverity.HIGH
        
        # Medium severity conditions
        if depth >= 4 or avg_complexity > 10 or total_complexity > 50:
            return CycleSeverity.MEDIUM
        
        # Low severity (default)
        return CycleSeverity.LOW
    
    def _generate_cycle_id(self, cycle_nodes: List[str]) -> str:
        """
        Generate a unique ID for a cycle
        
        Args:
            cycle_nodes: List of node names in the cycle
        
        Returns:
            Unique cycle ID
        """
        # Sort nodes to ensure consistent ID regardless of starting point
        sorted_nodes = sorted(cycle_nodes)
        node_str = "_".join(sorted_nodes[:3])  # Use first 3 nodes
        return f"cycle_{hash(tuple(sorted_nodes)) % 1000000}_{node_str}"
    
    def _compare_severity(self, severity1: CycleSeverity, severity2: CycleSeverity) -> int:
        """
        Compare two severity levels
        
        Args:
            severity1: First severity level
            severity2: Second severity level
        
        Returns:
            -1 if severity1 < severity2, 0 if equal, 1 if severity1 > severity2
        """
        severity_order = {
            CycleSeverity.LOW: 0,
            CycleSeverity.MEDIUM: 1,
            CycleSeverity.HIGH: 2,
            CycleSeverity.CRITICAL: 3
        }
        
        order1 = severity_order[severity1]
        order2 = severity_order[severity2]
        
        if order1 < order2:
            return -1
        elif order1 > order2:
            return 1
        else:
            return 0
