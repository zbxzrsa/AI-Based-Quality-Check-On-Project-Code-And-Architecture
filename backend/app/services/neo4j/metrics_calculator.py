"""
Metrics Calculator Service

Handles calculation of architecture metrics including complexity,
component counts, and quality indicators.
"""
from typing import Dict, Any
from datetime import datetime, timezone

from app.core.config import settings


class MetricsCalculator:
    """
    Service for calculating architecture metrics.
    
    Responsibilities:
    - Calculate complexity metrics
    - Count components
    - Calculate quality indicators
    - Generate metric reports
    """
    
    def __init__(self, driver):
        """
        Initialize metrics calculator.
        
        Args:
            driver: Neo4j async driver
        """
        self.driver = driver
    
    async def calculate_all_metrics(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive architecture metrics for the project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Comprehensive metrics dictionary
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            # Get all metrics in parallel
            component_counts = await self._get_component_counts(session, project_id)
            complexity_metrics = await self._get_complexity_metrics(session, project_id)
            coupling_metrics = await self._get_coupling_summary(session, project_id)
            
            return {
                "project_id": project_id,
                "component_counts": component_counts,
                "complexity_metrics": complexity_metrics,
                "coupling_metrics": coupling_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _get_component_counts(
        self,
        session,
        project_id: str
    ) -> Dict[str, int]:
        """Get counts of different component types"""
        result = await session.run("""
            MATCH (p:Project {projectId: $projectId})
            OPTIONAL MATCH (p)-[:CONTAINS]->(m:Module)
            OPTIONAL MATCH (p)-[:CONTAINS*]->(c:Class)
            OPTIONAL MATCH (p)-[:CONTAINS*]->(f:Function)
            OPTIONAL MATCH (p)-[:CONTAINS]->(file:File)
            RETURN count(DISTINCT m) AS modules,
                   count(DISTINCT c) AS classes,
                   count(DISTINCT f) AS functions,
                   count(DISTINCT file) AS files
        """, projectId=project_id)
        
        data = await result.single()
        
        return {
            "modules": data['modules'] if data else 0,
            "classes": data['classes'] if data else 0,
            "functions": data['functions'] if data else 0,
            "files": data['files'] if data else 0
        }
    
    async def _get_complexity_metrics(
        self,
        session,
        project_id: str
    ) -> Dict[str, Any]:
        """Get complexity metrics"""
        result = await session.run("""
            MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(f:Function)
            RETURN avg(f.complexity) AS avgComplexity,
                   max(f.complexity) AS maxComplexity,
                   count(f) AS totalFunctions,
                   sum(f.complexity) AS totalComplexity,
                   percentileCont(f.complexity, 0.95) AS p95Complexity
        """, projectId=project_id)
        
        data = await result.single()
        
        if not data:
            return {
                "average_complexity": 0,
                "max_complexity": 0,
                "total_complexity": 0,
                "p95_complexity": 0,
                "high_complexity_count": 0
            }
        
        # Count high complexity functions (>10)
        high_complexity_result = await session.run("""
            MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(f:Function)
            WHERE f.complexity > 10
            RETURN count(f) AS highComplexityCount
        """, projectId=project_id)
        
        high_complexity_data = await high_complexity_result.single()
        
        return {
            "average_complexity": float(data['avgComplexity']) if data['avgComplexity'] else 0,
            "max_complexity": data['maxComplexity'] if data['maxComplexity'] else 0,
            "total_complexity": data['totalComplexity'] if data['totalComplexity'] else 0,
            "p95_complexity": float(data['p95Complexity']) if data['p95Complexity'] else 0,
            "high_complexity_count": high_complexity_data['highComplexityCount'] if high_complexity_data else 0
        }
    
    async def _get_coupling_summary(
        self,
        session,
        project_id: str
    ) -> Dict[str, Any]:
        """Get coupling metrics summary"""
        result = await session.run("""
            MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
            OPTIONAL MATCH (m)-[:DEPENDS_ON]->(out)
            WITH m, count(DISTINCT out) AS efferent
            OPTIONAL MATCH (m)<-[:DEPENDS_ON]-(inc)
            WITH m, efferent, count(DISTINCT inc) AS afferent,
                 CASE
                     WHEN efferent + count(DISTINCT inc) = 0 THEN 0.0
                     ELSE toFloat(efferent) / (efferent + count(DISTINCT inc))
                 END AS instability
            RETURN avg(instability) AS avgInstability,
                   max(instability) AS maxInstability,
                   count(m) AS totalModules,
                   sum(CASE WHEN instability > 0.7 THEN 1 ELSE 0 END) AS highInstabilityCount
        """, projectId=project_id)
        
        data = await result.single()
        
        if not data:
            return {
                "average_instability": 0,
                "max_instability": 0,
                "high_instability_count": 0
            }
        
        return {
            "average_instability": float(data['avgInstability']) if data['avgInstability'] else 0,
            "max_instability": float(data['maxInstability']) if data['maxInstability'] else 0,
            "high_instability_count": data['highInstabilityCount'] if data['highInstabilityCount'] else 0
        }
    
    async def calculate_quality_score(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Calculate overall quality score based on metrics.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Quality score and breakdown
        """
        metrics = await self.calculate_all_metrics(project_id)
        
        # Calculate sub-scores (0-100)
        complexity_score = self._calculate_complexity_score(
            metrics['complexity_metrics']
        )
        coupling_score = self._calculate_coupling_score(
            metrics['coupling_metrics']
        )
        
        # Overall score (weighted average)
        overall_score = (complexity_score * 0.5 + coupling_score * 0.5)
        
        return {
            "project_id": project_id,
            "overall_score": round(overall_score, 2),
            "complexity_score": round(complexity_score, 2),
            "coupling_score": round(coupling_score, 2),
            "grade": self._score_to_grade(overall_score),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_complexity_score(
        self,
        complexity_metrics: Dict[str, Any]
    ) -> float:
        """Calculate complexity score (0-100, higher is better)"""
        avg_complexity = complexity_metrics.get('average_complexity', 0)
        high_complexity_count = complexity_metrics.get('high_complexity_count', 0)
        
        # Penalize high average complexity
        score = 100
        if avg_complexity > 5:
            score -= (avg_complexity - 5) * 5
        
        # Penalize high complexity functions
        score -= high_complexity_count * 2
        
        return max(0, min(100, score))
    
    def _calculate_coupling_score(
        self,
        coupling_metrics: Dict[str, Any]
    ) -> float:
        """Calculate coupling score (0-100, higher is better)"""
        avg_instability = coupling_metrics.get('average_instability', 0)
        high_instability_count = coupling_metrics.get('high_instability_count', 0)
        
        # Penalize high instability
        score = 100
        if avg_instability > 0.5:
            score -= (avg_instability - 0.5) * 100
        
        # Penalize modules with high instability
        score -= high_instability_count * 5
        
        return max(0, min(100, score))
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
