"""
Drift Detector Service

Handles detection of architectural drift by comparing current state
with baseline architecture.
"""
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.core.config import settings


class DriftDetector:
    """
    Service for detecting architectural drift.
    
    Responsibilities:
    - Compare current architecture with baseline
    - Calculate drift scores
    - Generate drift reports
    - Track architectural changes over time
    """
    
    def __init__(self, driver, dependency_analyzer, metrics_calculator):
        """
        Initialize drift detector.
        
        Args:
            driver: Neo4j async driver
            dependency_analyzer: Dependency analyzer service
            metrics_calculator: Metrics calculator service
        """
        self.driver = driver
        self.dependency_analyzer = dependency_analyzer
        self.metrics_calculator = metrics_calculator
    
    async def detect_drift(
        self,
        project_id: str,
        baseline_version: str = "latest"
    ) -> Dict[str, Any]:
        """
        Comprehensive drift detection.
        
        Args:
            project_id: Project identifier
            baseline_version: Baseline version to compare against
            
        Returns:
            Comprehensive drift report
        """
        import asyncio
        
        # Run all detection tasks in parallel
        cycles, violations, metrics = await asyncio.gather(
            self.dependency_analyzer.find_circular_dependencies(project_id),
            self.dependency_analyzer.detect_layer_violations(project_id),
            self.metrics_calculator.calculate_all_metrics(project_id)
        )
        
        # Calculate drift score
        drift_score = self._calculate_drift_score(cycles, violations, metrics)
        
        # Generate comprehensive report
        report = {
            'project_id': project_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'baseline_version': baseline_version,
            'cyclic_dependencies': {
                'count': len(cycles),
                'details': cycles[:10],  # Limit to top 10
                'severity': self._get_max_severity(cycles)
            },
            'layer_violations': {
                'count': len(violations),
                'details': violations[:10],  # Limit to top 10
                'severity': 'HIGH' if violations else 'NONE'
            },
            'metrics': metrics,
            'drift_score': drift_score,
            'drift_level': self._score_to_level(drift_score),
            'status': 'completed'
        }
        
        return report
    
    async def generate_weekly_drift_report(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive weekly drift report.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Weekly drift report
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            # Get summary statistics
            result = await session.run("""
                MATCH (p:Project {projectId: $projectId})
                OPTIONAL MATCH (p)-[:CONTAINS*]->(m:Module)
                OPTIONAL MATCH (m)-[:DEPENDS_ON*2..]->(m)
                WITH p, count(DISTINCT m) AS cycleCount
                OPTIONAL MATCH (p)-[:CONTAINS*]->(source:Module)
                MATCH (source)-[:DEPENDS_ON]->(target:Module)
                WHERE source.layerRank > target.layerRank + 1
                WITH p, cycleCount, count(*) AS violationCount
                OPTIONAL MATCH (p)-[:CONTAINS]->(mod:Module)
                OPTIONAL MATCH (mod)-[:DEPENDS_ON]->(out)
                WITH p, cycleCount, violationCount, mod, count(DISTINCT out) AS efferent
                OPTIONAL MATCH (mod)<-[:DEPENDS_ON]-(inc)
                WITH p, cycleCount, violationCount, mod, efferent, count(DISTINCT inc) AS afferent,
                     CASE
                         WHEN efferent + count(DISTINCT inc) = 0 THEN 0.0
                         ELSE toFloat(efferent) / (efferent + count(DISTINCT inc))
                     END AS instability
                RETURN cycleCount,
                       violationCount,
                       avg(instability) AS avgInstability,
                       sum(CASE WHEN instability > 0.7 THEN 1 ELSE 0 END) AS unstableModules
            """, projectId=project_id)
            
            data = await result.single()
            
            if not data:
                return {
                    'cycle_count': 0,
                    'violation_count': 0,
                    'average_instability': 0.0,
                    'unstable_modules': 0
                }
            
            return {
                'project_id': project_id,
                'cycle_count': data['cycleCount'] or 0,
                'violation_count': data['violationCount'] or 0,
                'average_instability': float(data['avgInstability']) if data['avgInstability'] else 0.0,
                'unstable_modules': data['unstableModules'] or 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _calculate_drift_score(
        self,
        cycles: List[Dict],
        violations: List[Dict],
        metrics: Dict
    ) -> float:
        """
        Calculate overall architectural drift score (0-100).
        
        0 = No drift, 100 = Severe drift
        
        Args:
            cycles: List of circular dependencies
            violations: List of layer violations
            metrics: Architecture metrics
            
        Returns:
            Drift score
        """
        score = 0.0
        
        # Cycles contribute to score
        direct_cycles = sum(1 for c in cycles if c.get('cycleLength') == 2)
        indirect_cycles = sum(1 for c in cycles if c.get('cycleLength', 0) > 2)
        
        score += direct_cycles * 15  # Direct cycles are critical
        score += indirect_cycles * 8
        
        # Layer violations contribute
        score += len(violations) * 10
        
        # High instability modules
        coupling_metrics = metrics.get('coupling_metrics', {})
        high_instability = coupling_metrics.get('high_instability_count', 0)
        score += high_instability * 5
        
        # High complexity functions
        complexity_metrics = metrics.get('complexity_metrics', {})
        high_complexity = complexity_metrics.get('high_complexity_count', 0)
        score += high_complexity * 3
        
        # Cap at 100
        return min(score, 100.0)
    
    def _get_max_severity(self, cycles: List[Dict]) -> str:
        """Get maximum severity from cycles"""
        if not cycles:
            return 'NONE'
        
        severities = [c.get('severity', 'LOW') for c in cycles]
        
        if 'CRITICAL' in severities:
            return 'CRITICAL'
        elif 'HIGH' in severities:
            return 'HIGH'
        elif 'MEDIUM' in severities:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _score_to_level(self, score: float) -> str:
        """Convert drift score to level"""
        if score >= 75:
            return 'CRITICAL'
        elif score >= 50:
            return 'HIGH'
        elif score >= 25:
            return 'MEDIUM'
        elif score > 0:
            return 'LOW'
        else:
            return 'NONE'
