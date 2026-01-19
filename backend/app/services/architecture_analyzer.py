"""
Architecture Analyzer Service

Handles architectural analysis and drift detection using graph-based analysis.
"""
from typing import Dict, List, Optional, Set, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import networkx as nx

from neo4j import AsyncSession

from app.database.neo4j_db import get_neo4j_session
from app.schemas.architecture import (
    ArchitectureComponent,
    ArchitectureViolation,
    ArchitectureMetric,
    ArchitectureReport,
    ComponentType,
    ViolationType,
    DependencyType
)

logger = logging.getLogger(__name__)

class ArchitectureAnalyzer:
    """Service for analyzing software architecture using graph-based analysis"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.dependency_graph = nx.DiGraph()
    
    async def analyze_architecture(self, project_id: str) -> ArchitectureReport:
        """
        Analyze the architecture of a project
        
        Args:
            project_id: ID of the project to analyze
            
        Returns:
            ArchitectureReport containing analysis results
        """
        report = ArchitectureReport(project_id=project_id)
        
        try:
            # Load project components and dependencies
            components = await self._load_components(project_id)
            dependencies = await self._load_dependencies(project_id)
            
            # Build dependency graph
            self._build_dependency_graph(components, dependencies)
            
            # Perform architectural analysis
            report.violations = await self._detect_architectural_violations()
            report.metrics = await self._calculate_architecture_metrics()
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(report)
            
        except Exception as e:
            logger.error(f"Error analyzing architecture: {str(e)}")
            report.error = str(e)
        
        return report
    
    async def detect_architectural_drift(
        self,
        project_id: str,
        target_architecture: Dict
    ) -> List[ArchitectureViolation]:
        """
        Detect drift between current and target architecture
        
        Args:
            project_id: ID of the project
            target_architecture: Target architecture definition
            
        Returns:
            List of architectural violations
        """
        violations = []
        
        # Get current architecture
        current_components = await self._load_components(project_id)
        current_dependencies = await self._load_dependencies(project_id)
        
        # Check for missing components
        target_components = set(target_architecture.get('components', []))
        current_component_names = {c.name for c in current_components}
        
        for component in target_components - current_component_names:
            violations.append(ArchitectureViolation(
                type=ViolationType.MISSING_COMPONENT,
                component=component,
                message=f"Component '{component}' is missing"
            ))
        
        # Check for extra components
        for component in current_component_names - target_components:
            violations.append(ArchitectureViolation(
                type=ViolationType.UNAUTHORIZED_COMPONENT,
                component=component,
                message=f"Unauthorized component '{component}' found"
            ))
        
        # Check for dependency violations
        allowed_dependencies = target_architecture.get('allowed_dependencies', {})
        for source, deps in allowed_dependencies.items():
            if source not in current_component_names:
                continue
                
            for dep in deps:
                if dep not in current_component_names:
                    violations.append(ArchitectureViolation(
                        type=ViolationType.INVALID_DEPENDENCY,
                        component=source,
                        related_component=dep,
                        message=f"Component '{source}' has an invalid dependency on missing component '{dep}'"
                    ))
        
        return violations
    
    async def _load_components(self, project_id: str) -> List[ArchitectureComponent]:
        """Load architecture components from the database"""
        # Implementation for loading components from Neo4j
        pass
    
    async def _load_dependencies(self, project_id: str) -> List[Tuple[str, str, Dict]]:
        """Load component dependencies from the database"""
        # Implementation for loading dependencies from Neo4j
        pass
    
    def _build_dependency_graph(
        self,
        components: List[ArchitectureComponent],
        dependencies: List[Tuple[str, str, Dict]]
    ) -> None:
        """Build a directed graph of component dependencies"""
        self.dependency_graph = nx.DiGraph()
        
        # Add nodes (components)
        for component in components:
            self.dependency_graph.add_node(
                component.name,
                type=component.type,
                properties=component.properties
            )
        
        # Add edges (dependencies)
        for source, target, attrs in dependencies:
            self.dependency_graph.add_edge(source, target, **attrs)
    
    async def _detect_architectural_violations(self) -> List[ArchitectureViolation]:
        """Detect architectural violations in the dependency graph"""
        violations = []
        
        # Check for circular dependencies
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            for cycle in cycles:
                if len(cycle) > 1:  # Ignore self-loops
                    violations.append(ArchitectureViolation(
                        type=ViolationType.CIRCULAR_DEPENDENCY,
                        component=cycle[0],
                        related_component=cycle[-1],
                        message=f"Circular dependency detected: {' -> '.join(cycle + [cycle[0]])}"
                    ))
        except Exception as e:
            logger.error(f"Error detecting cycles: {str(e)}")
        
        # Check for dependency violations based on component types
        for source, target, attrs in self.dependency_graph.edges(data=True):
            source_type = self.dependency_graph.nodes[source].get('type')
            target_type = self.dependency_graph.nodes[target].get('type')
            
            # Example rule: Domain components should not depend on UI components
            if (source_type == ComponentType.DOMAIN and 
                target_type == ComponentType.UI):
                violations.append(ArchitectureViolation(
                    type=ViolationType.DEPENDENCY_VIOLATION,
                    component=source,
                    related_component=target,
                    message=f"Domain component '{source}' should not depend on UI component '{target}'"
                ))
            
            # Add more architectural rules here
            
        return violations
    
    async def _calculate_architecture_metrics(self) -> List[ArchitectureMetric]:
        """Calculate various architecture metrics"""
        metrics = []
        
        # Calculate coupling metrics
        metrics.append(ArchitectureMetric(
            name="afferent_coupling",
            value=self.dependency_graph.in_degree(),
            description="Number of components that depend on this component"
        ))
        
        metrics.append(ArchitectureMetric(
            name="efferent_coupling",
            value=self.dependency_graph.out_degree(),
            description="Number of components this component depends on"
        ))
        
        # Calculate instability
        for node in self.dependency_graph.nodes():
            fan_out = self.dependency_graph.out_degree(node)
            fan_in = self.dependency_graph.in_degree(node)
            
            instability = fan_out / (fan_in + fan_out) if (fan_in + fan_out) > 0 else 0
            
            metrics.append(ArchitectureMetric(
                name=f"instability_{node}",
                value=instability,
                description=f"Instability metric for component {node}"
            ))
        
        # Calculate abstractness (simplified)
        total_components = len(self.dependency_graph.nodes())
        if total_components > 0:
            abstract_components = sum(
                1 for _, data in self.dependency_graph.nodes(data=True)
                if data.get('is_abstract', False)
            )
            
            metrics.append(ArchitectureMetric(
                name="abstractness",
                value=abstract_components / total_components,
                description="Ratio of abstract components to total components"
            ))
        
        return metrics
    
    def _generate_recommendations(self, report: ArchitectureReport) -> List[str]:
        """Generate architectural recommendations based on analysis"""
        recommendations = []
        
        # Add recommendations based on violations
        for violation in report.violations:
            if violation.type == ViolationType.CIRCULAR_DEPENDENCY:
                recommendations.append(
                    f"Break circular dependency between {violation.component} and {violation.related_component} "
                    "by introducing an interface or using dependency inversion."
                )
            elif violation.type == ViolationType.DEPENDENCY_VIOLATION:
                recommendations.append(
                    f"Refactor to remove the dependency from {violation.component} to {violation.related_component}. "
                    "Consider using interfaces or an event bus for cross-layer communication."
                )
        
        # Add general recommendations based on metrics
        for metric in report.metrics:
            if metric.name == "abstractness" and metric.value < 0.3:
                recommendations.append(
                    "Consider increasing the level of abstraction in your architecture "
                    "by introducing more interfaces and abstract base classes to reduce coupling."
                )
        
        return recommendations
    
    async def visualize_architecture(self, output_format: str = "svg") -> bytes:
        """
        Generate a visualization of the architecture
        
        Args:
            output_format: Output format ('svg', 'png', 'dot')
            
        Returns:
            Bytes containing the visualization
        """
        try:
            # Use pygraphviz for better layout control
            import pygraphviz as pgv
            
            # Create a PyGraphviz graph from the NetworkX graph
            g = pgv.AGraph(directed=True, strict=False, rankdir="TB")
            
            # Add nodes with styling based on type
            for node, data in self.dependency_graph.nodes(data=True):
                node_type = data.get('type', 'unknown')
                style = {
                    'shape': 'box',
                    'style': 'filled',
                    'fillcolor': self._get_node_color(node_type),
                    'fontname': 'Arial',
                    'fontsize': '10'
                }
                g.add_node(node, **style)
            
            # Add edges
            for src, dst, data in self.dependency_graph.edges(data=True):
                g.add_edge(src, dst, **{
                    'fontname': 'Arial',
                    'fontsize': '8',
                    'label': data.get('type', 'depends')
                })
            
            # Generate the graph
            g.layout(prog='dot')
            
            # Return in the requested format
            if output_format == 'dot':
                return g.string().encode('utf-8')
            else:
                return g.draw(format=output_format, prog='dot')
                
        except ImportError:
            logger.warning("PyGraphviz not installed, using NetworkX drawing")
            import matplotlib.pyplot as plt
            from io import BytesIO
            
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(self.dependency_graph)
            
            # Draw nodes with colors based on type
            node_colors = [
                self._get_node_color(data.get('type', 'unknown'))
                for _, data in self.dependency_graph.nodes(data=True)
            ]
            
            nx.draw_networkx_nodes(
                self.dependency_graph, pos,
                node_color=node_colors,
                node_size=2000
            )
            
            # Draw edges
            nx.draw_networkx_edges(
                self.dependency_graph, pos,
                arrowstyle='-|>',
                arrowsize=10
            )
            
            # Draw labels
            nx.draw_networkx_labels(
                self.dependency_graph, pos,
                font_size=8,
                font_family='sans-serif'
            )
            
            # Save to bytes
            buf = BytesIO()
            plt.savefig(buf, format=output_format)
            plt.close()
            return buf.getvalue()
    
    @staticmethod
    def _get_node_color(node_type: str) -> str:
        """Get color for a node based on its type"""
        colors = {
            'service': '#A4C2F4',  # Light blue
            'controller': '#B6D7A8',  # Light green
            'repository': '#F9CB9C',  # Light orange
            'model': '#D5A6BD',  # Light purple
            'util': '#D9D9D9',  # Light gray
            'component': '#FFE599',  # Light yellow
            'api': '#9FC5E8',  # Blue
            'ui': '#B6D7A8',  # Green
            'domain': '#D5A6BD',  # Purple
            'infrastructure': '#F9CB9C',  # Orange
        }
        return colors.get(node_type.lower(), '#E6E6E6')  # Default light gray
