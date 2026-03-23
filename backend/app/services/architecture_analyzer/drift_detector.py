"""
Architectural Drift Detector

This module detects architectural drift by comparing the current graph state
against a baseline snapshot. It calculates drift metrics and assigns severity levels.

Implements Requirement 1.9: ISO/IEC 25010 compliance verification
"""
import logging
logger = logging.getLogger(__name__)


from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from app.database.neo4j_db import get_neo4j_driver
from app.core.config import settings
from .baseline import BaselineManager, ArchitectureBaseline


class DriftSeverity(str, Enum):
    """Severity levels for architectural drift"""
    LOW = "low"           # <10% drift
    MEDIUM = "medium"     # 10-25% drift
    HIGH = "high"         # 25-50% drift
    CRITICAL = "critical" # >50% drift


@dataclass
class DriftMetrics:
    """Metrics describing architectural drift"""
    new_dependencies: int
    removed_dependencies: int
    modified_relationships: int
    new_nodes: int
    removed_nodes: int
    modified_nodes: int
    total_changes: int
    drift_percentage: float
    complexity_delta: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class DriftDetail:
    """Detailed information about a specific drift"""
    change_type: str  # "added", "removed", "modified"
    entity_type: str  # "node", "relationship"
    entity_name: str
    details: Dict[str, Any]
    impact: str  # Description of impact


@dataclass
class DriftResult:
    """Result of drift detection analysis"""
    project_id: str
    baseline_version: str
    current_timestamp: str
    severity: DriftSeverity
    metrics: DriftMetrics
    details: List[DriftDetail]
    summary: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "project_id": self.project_id,
            "baseline_version": self.baseline_version,
            "current_timestamp": self.current_timestamp,
            "severity": self.severity.value,
            "metrics": self.metrics.to_dict(),
            "details": [asdict(d) for d in self.details],
            "summary": self.summary,
            "recommendations": self.recommendations
        }


class DriftDetector:
    """
    Detects architectural drift by comparing current state to baseline
    
    Features:
    - Compare current graph to baseline snapshot
    - Detect new, removed, and modified dependencies
    - Calculate drift metrics and percentages
    - Assign severity levels based on drift magnitude
    - Generate actionable recommendations
    """
    
    def __init__(self, baseline_manager: Optional[BaselineManager] = None):
        """
        Initialize drift detector
        
        Args:
            baseline_manager: Optional BaselineManager instance
        """
        self.baseline_manager = baseline_manager or BaselineManager()
    
    async def detect_drift(
        self,
        project_id: str,
        baseline_version: Optional[str] = None
    ) -> DriftResult:
        """
        Detect architectural drift against a baseline
        
        Args:
            project_id: Project identifier
            baseline_version: Optional baseline version (uses latest if not specified)
        
        Returns:
            DriftResult with metrics and details
        """
        # Get baseline
        baseline = await self.baseline_manager.get_baseline(
            project_id=project_id,
            version=baseline_version
        )
        
        if not baseline:
            raise ValueError(
                f"No baseline found for project {project_id}" +
                (f" version {baseline_version}" if baseline_version else "")
            )
        
        # Get current state
        driver = await get_neo4j_driver()
        current_nodes = await self._get_current_nodes(driver, project_id)
        current_relationships = await self._get_current_relationships(driver, project_id)
        
        # Compare and calculate drift
        drift_details = []
        
        # Detect node changes
        node_changes = self._compare_nodes(baseline.nodes, current_nodes)
        drift_details.extend(node_changes)
        
        # Detect relationship changes
        rel_changes = self._compare_relationships(
            baseline.relationships,
            current_relationships
        )
        drift_details.extend(rel_changes)
        
        # Calculate metrics
        metrics = self._calculate_drift_metrics(
            baseline,
            current_nodes,
            current_relationships,
            drift_details
        )
        
        # Assign severity
        severity = self._calculate_severity(metrics)
        
        # Generate summary and recommendations
        summary = self._generate_summary(metrics, severity)
        recommendations = self._generate_recommendations(metrics, severity, drift_details)
        
        return DriftResult(
            project_id=project_id,
            baseline_version=baseline.version,
            current_timestamp=datetime.utcnow().isoformat(),
            severity=severity,
            metrics=metrics,
            details=drift_details,
            summary=summary,
            recommendations=recommendations
        )
    
    async def _get_current_nodes(
        self,
        driver: Any,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get current nodes from graph"""
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
            logger.info("Error getting current nodes: {str(e)}")
        
        return nodes
    
    async def _get_current_relationships(
        self,
        driver: Any,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get current relationships from graph"""
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
            logger.info("Error getting current relationships: {str(e)}")
        
        return relationships
    
    def _compare_nodes(
        self,
        baseline_nodes: List[Dict[str, Any]],
        current_nodes: List[Dict[str, Any]]
    ) -> List[DriftDetail]:
        """
        Compare baseline and current nodes to detect changes
        
        Args:
            baseline_nodes: Nodes from baseline
            current_nodes: Current nodes
        
        Returns:
            List of DriftDetail objects
        """
        details = []
        
        # Create lookup maps by name and file_path
        baseline_map = {
            (n["properties"].get("name"), n["properties"].get("file_path")): n
            for n in baseline_nodes
        }
        current_map = {
            (n["properties"].get("name"), n["properties"].get("file_path")): n
            for n in current_nodes
        }
        
        baseline_keys = set(baseline_map.keys())
        current_keys = set(current_map.keys())
        
        # Detect new nodes
        new_keys = current_keys - baseline_keys
        for key in new_keys:
            node = current_map[key]
            name = node["properties"].get("name", "unknown")
            details.append(DriftDetail(
                change_type="added",
                entity_type="node",
                entity_name=name,
                details={
                    "node_type": node["properties"].get("type", "unknown"),
                    "file_path": node["properties"].get("file_path", ""),
                    "complexity": node["properties"].get("complexity", 0)
                },
                impact=f"New code entity '{name}' added to the architecture"
            ))
        
        # Detect removed nodes
        removed_keys = baseline_keys - current_keys
        for key in removed_keys:
            node = baseline_map[key]
            name = node["properties"].get("name", "unknown")
            details.append(DriftDetail(
                change_type="removed",
                entity_type="node",
                entity_name=name,
                details={
                    "node_type": node["properties"].get("type", "unknown"),
                    "file_path": node["properties"].get("file_path", "")
                },
                impact=f"Code entity '{name}' removed from the architecture"
            ))
        
        # Detect modified nodes
        common_keys = baseline_keys & current_keys
        for key in common_keys:
            baseline_node = baseline_map[key]
            current_node = current_map[key]
            
            # Compare complexity
            baseline_complexity = baseline_node["properties"].get("complexity", 0)
            current_complexity = current_node["properties"].get("complexity", 0)
            
            if baseline_complexity != current_complexity:
                name = current_node["properties"].get("name", "unknown")
                complexity_delta = current_complexity - baseline_complexity
                details.append(DriftDetail(
                    change_type="modified",
                    entity_type="node",
                    entity_name=name,
                    details={
                        "property": "complexity",
                        "baseline_value": baseline_complexity,
                        "current_value": current_complexity,
                        "delta": complexity_delta
                    },
                    impact=f"Complexity of '{name}' changed by {complexity_delta:+d}"
                ))
        
        return details
    
    def _compare_relationships(
        self,
        baseline_rels: List[Dict[str, Any]],
        current_rels: List[Dict[str, Any]]
    ) -> List[DriftDetail]:
        """
        Compare baseline and current relationships to detect changes
        
        Args:
            baseline_rels: Relationships from baseline
            current_rels: Current relationships
        
        Returns:
            List of DriftDetail objects
        """
        details = []
        
        # Create lookup maps by (source_name, target_name, rel_type)
        baseline_map = {
            (r["source_name"], r["target_name"], r["rel_type"]): r
            for r in baseline_rels
        }
        current_map = {
            (r["source_name"], r["target_name"], r["rel_type"]): r
            for r in current_rels
        }
        
        baseline_keys = set(baseline_map.keys())
        current_keys = set(current_map.keys())
        
        # Detect new relationships
        new_keys = current_keys - baseline_keys
        for key in new_keys:
            source, target, rel_type = key
            details.append(DriftDetail(
                change_type="added",
                entity_type="relationship",
                entity_name=f"{source} -> {target}",
                details={
                    "source": source,
                    "target": target,
                    "relationship_type": rel_type
                },
                impact=f"New dependency: {source} now depends on {target}"
            ))
        
        # Detect removed relationships
        removed_keys = baseline_keys - current_keys
        for key in removed_keys:
            source, target, rel_type = key
            details.append(DriftDetail(
                change_type="removed",
                entity_type="relationship",
                entity_name=f"{source} -> {target}",
                details={
                    "source": source,
                    "target": target,
                    "relationship_type": rel_type
                },
                impact=f"Dependency removed: {source} no longer depends on {target}"
            ))
        
        # Note: We don't check for "modified" relationships since they're typically
        # identified by their endpoints and type. Property changes would be rare.
        
        return details
    
    def _calculate_drift_metrics(
        self,
        baseline: ArchitectureBaseline,
        current_nodes: List[Dict[str, Any]],
        current_relationships: List[Dict[str, Any]],
        drift_details: List[DriftDetail]
    ) -> DriftMetrics:
        """
        Calculate drift metrics
        
        Args:
            baseline: Baseline snapshot
            current_nodes: Current nodes
            current_relationships: Current relationships
            drift_details: List of detected changes
        
        Returns:
            DriftMetrics object
        """
        # Count changes by type
        new_nodes = sum(1 for d in drift_details 
                       if d.change_type == "added" and d.entity_type == "node")
        removed_nodes = sum(1 for d in drift_details 
                           if d.change_type == "removed" and d.entity_type == "node")
        modified_nodes = sum(1 for d in drift_details 
                            if d.change_type == "modified" and d.entity_type == "node")
        
        new_dependencies = sum(1 for d in drift_details 
                              if d.change_type == "added" and d.entity_type == "relationship")
        removed_dependencies = sum(1 for d in drift_details 
                                  if d.change_type == "removed" and d.entity_type == "relationship")
        modified_relationships = sum(1 for d in drift_details 
                                    if d.change_type == "modified" and d.entity_type == "relationship")
        
        total_changes = len(drift_details)
        
        # Calculate drift percentage
        baseline_total = len(baseline.nodes) + len(baseline.relationships)
        current_total = len(current_nodes) + len(current_relationships)
        
        if baseline_total > 0:
            drift_percentage = (total_changes / baseline_total) * 100
        else:
            drift_percentage = 0.0
        
        # Calculate complexity delta
        baseline_complexity = baseline.metrics.get("total_complexity", 0)
        current_complexity = sum(
            n["properties"].get("complexity", 0) for n in current_nodes
        )
        complexity_delta = current_complexity - baseline_complexity
        
        return DriftMetrics(
            new_dependencies=new_dependencies,
            removed_dependencies=removed_dependencies,
            modified_relationships=modified_relationships,
            new_nodes=new_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            total_changes=total_changes,
            drift_percentage=round(drift_percentage, 2),
            complexity_delta=complexity_delta
        )
    
    def _calculate_severity(self, metrics: DriftMetrics) -> DriftSeverity:
        """
        Calculate drift severity based on metrics
        
        Severity rules:
        - CRITICAL: >50% drift
        - HIGH: 25-50% drift
        - MEDIUM: 10-25% drift
        - LOW: <10% drift
        
        Args:
            metrics: DriftMetrics object
        
        Returns:
            DriftSeverity enum value
        """
        drift_pct = metrics.drift_percentage
        
        if drift_pct > 50:
            return DriftSeverity.CRITICAL
        elif drift_pct > 25:
            return DriftSeverity.HIGH
        elif drift_pct > 10:
            return DriftSeverity.MEDIUM
        else:
            return DriftSeverity.LOW
    
    def _generate_summary(
        self,
        metrics: DriftMetrics,
        severity: DriftSeverity
    ) -> str:
        """
        Generate a human-readable summary of the drift
        
        Args:
            metrics: DriftMetrics object
            severity: DriftSeverity level
        
        Returns:
            Summary string
        """
        summary_parts = [
            f"Architectural drift detected with {severity.value.upper()} severity.",
            f"Total changes: {metrics.total_changes} ({metrics.drift_percentage}% drift)."
        ]
        
        if metrics.new_dependencies > 0:
            summary_parts.append(f"{metrics.new_dependencies} new dependencies added.")
        
        if metrics.removed_dependencies > 0:
            summary_parts.append(f"{metrics.removed_dependencies} dependencies removed.")
        
        if metrics.new_nodes > 0:
            summary_parts.append(f"{metrics.new_nodes} new code entities added.")
        
        if metrics.removed_nodes > 0:
            summary_parts.append(f"{metrics.removed_nodes} code entities removed.")
        
        if metrics.complexity_delta != 0:
            direction = "increased" if metrics.complexity_delta > 0 else "decreased"
            summary_parts.append(
                f"Overall complexity {direction} by {abs(metrics.complexity_delta)}."
            )
        
        return " ".join(summary_parts)
    
    def _generate_recommendations(
        self,
        metrics: DriftMetrics,
        severity: DriftSeverity,
        drift_details: List[DriftDetail]
    ) -> List[str]:
        """
        Generate actionable recommendations based on drift analysis
        
        Args:
            metrics: DriftMetrics object
            severity: DriftSeverity level
            drift_details: List of drift details
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Severity-based recommendations
        if severity == DriftSeverity.CRITICAL:
            recommendations.append(
                "CRITICAL: Architecture has drifted significantly (>50%). "
                "Consider creating a new baseline or conducting an architecture review."
            )
        elif severity == DriftSeverity.HIGH:
            recommendations.append(
                "HIGH: Substantial architectural changes detected. "
                "Review changes for alignment with architectural goals."
            )
        elif severity == DriftSeverity.MEDIUM:
            recommendations.append(
                "MEDIUM: Moderate architectural drift detected. "
                "Monitor changes and ensure they follow architectural patterns."
            )
        else:
            recommendations.append(
                "LOW: Minor architectural changes detected. "
                "Changes appear to be within acceptable limits."
            )
        
        # Dependency-specific recommendations
        if metrics.new_dependencies > 10:
            recommendations.append(
                f"{metrics.new_dependencies} new dependencies added. "
                "Review for potential coupling issues and circular dependencies."
            )
        
        if metrics.removed_dependencies > 5:
            recommendations.append(
                f"{metrics.removed_dependencies} dependencies removed. "
                "Verify that removed dependencies don't break functionality."
            )
        
        # Complexity recommendations
        if metrics.complexity_delta > 100:
            recommendations.append(
                f"Complexity increased by {metrics.complexity_delta}. "
                "Consider refactoring to maintain code quality."
            )
        elif metrics.complexity_delta < -100:
            recommendations.append(
                f"Complexity decreased by {abs(metrics.complexity_delta)}. "
                "Good progress on code simplification."
            )
        
        # Node change recommendations
        if metrics.new_nodes > 20:
            recommendations.append(
                f"{metrics.new_nodes} new code entities added. "
                "Ensure new entities follow naming conventions and architectural patterns."
            )
        
        if metrics.removed_nodes > 10:
            recommendations.append(
                f"{metrics.removed_nodes} code entities removed. "
                "Update documentation to reflect removed components."
            )
        
        # General recommendation
        if metrics.total_changes > 50:
            recommendations.append(
                "Consider updating the baseline to reflect the current architecture state."
            )
        
        return recommendations
