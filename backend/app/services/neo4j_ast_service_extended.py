"""
Extended Neo4j AST Service with Drift Detection
Provides methods to run Cypher queries and analyze architectural drift
"""
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.services import cypher_queries

logger = logging.getLogger(__name__)


class Neo4jASTService:
    """Enhanced Neo4j service for AST and architecture analysis"""
    
    def __init__(self, driver: AsyncDriver):
        self.driver = driver
    
    async def run_query(
        self,
        query: str,
        **parameters
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results
        
        Args:
            query: Cypher query string
            **parameters: Query parameters
            
        Returns:
            List of result records
        """
        try:
            async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(query, parameters)
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Error running Cypher query: {e}")
            raise
    
    async def detect_cyclic_dependencies(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Detect cyclic dependencies in the project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of detected cycles with details
        """
        results = await self.run_query(
            cypher_queries.CYCLIC_DEPENDENCY_QUERY,
            projectId=project_id
        )
        
        cycles = []
        for record in results:
            cycle = {
                'module': record.get('module'),
                'cycle_path': record.get('cycle_path', []),
                'cycle_length': record.get('cycle_length'),
                'severity': 'CRITICAL' if record.get('cycle_length') == 2 else 'HIGH',
                'dependency_reasons': record.get('dependency_reasons', [])
            }
            cycles.append(cycle)
        
        return cycles
    
    async def detect_layer_violations(
        self,
        project_id: str,
        layer_definitions: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect layer violations (e.g., Controller directly to Repository)
        
        Args:
            project_id: Project ID
            layer_definitions: Optional custom layer definitions
            
        Returns:
            List of detected layer violations
        """
        results = await self.run_query(
            cypher_queries.LAYER_VIOLATION_QUERY,
            projectId=project_id
        )
        
        violations = []
        for record in results:
            violation = {
                'source_module': record.get('source_module'),
                'source_type': record.get('source_type', 'Unknown'),
                'target_module': record.get('target_module'),
                'target_type': record.get('target_type', 'Unknown'),
                'violation_path': record.get('violation_path', []),
                'violation_type': 'layer_skip',
                'severity': 'HIGH',
                'reasons': record.get('reasons', [])
            }
            violations.append(violation)
        
        return violations
    
    async def detect_direct_cycles(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Detect only direct 2-hop cyclic dependencies (most critical)
        
        Args:
            project_id: Project ID
            
        Returns:
            List of direct cycles (Module A -> B -> A)
        """
        results = await self.run_query(
            cypher_queries.DIRECT_CYCLES_QUERY,
            projectId=project_id
        )
        
        return [
            {
                'module_a': r.get('module_a'),
                'module_b': r.get('module_b'),
                'type': 'DIRECT_CYCLE',
                'severity': 'CRITICAL'
            }
            for r in results
        ]
    
    async def find_cyclic_services(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Find cycles specifically in Service layer
        
        Args:
            project_id: Project ID
            
        Returns:
            List of cyclic service dependencies
        """
        results = await self.run_query(
            cypher_queries.CYCLIC_SERVICE_QUERY,
            projectId=project_id
        )
        
        return results
    
    async def detect_all_layer_violations(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Detect all layer violations (not just Controller->Repository)
        
        Args:
            project_id: Project ID
            
        Returns:
            List of all layer violations
        """
        results = await self.run_query(
            cypher_queries.ALL_LAYER_VIOLATIONS_QUERY,
            projectId=project_id
        )
        
        return results
    
    async def calculate_coupling_metrics(self, project_id: str) -> Dict[str, Any]:
        """
        Calculate coupling metrics for all modules
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict with efferent, afferent, and instability metrics
        """
        # Get efferent coupling
        efferent_results = await self.run_query(
            cypher_queries.EFFERENT_COUPLING_QUERY,
            projectId=project_id
        )
        
        # Get afferent coupling
        afferent_results = await self.run_query(
            cypher_queries.AFFERENT_COUPLING_QUERY,
            projectId=project_id
        )
        
        # Get instability index
        instability_results = await self.run_query(
            cypher_queries.INSTABILITY_INDEX_QUERY,
            projectId=project_id
        )
        
        return {
            'efferent_coupling': efferent_results,
            'afferent_coupling': afferent_results,
            'instability_metrics': instability_results
        }
    
    async def find_longest_dependency_paths(
        self,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find longest dependency paths (refactoring candidates)
        
        Args:
            project_id: Project ID
            limit: Maximum number of paths to return
            
        Returns:
            List of dependency paths ordered by length
        """
        # Modify query to include limit
        query = cypher_queries.LONGEST_DEPENDENCY_PATHS_QUERY.replace(
            'LIMIT 20',
            f'LIMIT {limit}'
        )
        
        results = await self.run_query(query, projectId=project_id)
        return results
    
    async def generate_weekly_drift_report(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive weekly drift report
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict with cycle count, violation count, instability metrics
        """
        results = await self.run_query(
            cypher_queries.WEEKLY_DRIFT_REPORT_QUERY,
            projectId=project_id
        )
        
        if results:
            return dict(results[0])
        
        return {
            'cycle_count': 0,
            'violation_count': 0,
            'average_instability': 0.0,
            'unstable_modules': 0
        }
    
    async def insert_ast_nodes(
        self,
        parsed_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, int]:
        """
        Insert AST nodes into Neo4j
        
        Args:
            parsed_data: Parsed AST data from parser
            project_id: Project ID
            
        Returns:
            Dict with count of inserted nodes
        """
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            inserted = {
                'modules': 0,
                'classes': 0,
                'functions': 0,
                'dependencies': 0
            }
            
            # Implementation would depend on parsed_data structure
            # This is a placeholder for integration with actual parser
            
            return inserted
    
    async def detect_drift(
        self,
        project_id: str,
        baseline_version: str = "latest"
    ) -> Dict[str, Any]:
        """
        Comprehensive drift detection
        
        Args:
            project_id: Project ID
            baseline_version: Baseline version to compare
            
        Returns:
            Comprehensive drift report
        """
        import asyncio
        
        # Run all detection tasks in parallel
        cycles, violations, metrics = await asyncio.gather(
            self.detect_cyclic_dependencies(project_id),
            self.detect_layer_violations(project_id),
            self.calculate_coupling_metrics(project_id)
        )
        
        # Generate comprehensive report
        report = {
            'project_id': project_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'baseline_version': baseline_version,
            'cyclic_dependencies': {
                'count': len(cycles),
                'details': cycles,
                'severity': max([c['severity'] for c in cycles]) if cycles else 'NONE'
            },
            'layer_violations': {
                'count': len(violations),
                'details': violations,
                'severity': 'HIGH' if violations else 'NONE'
            },
            'coupling_metrics': metrics,
            'overall_score': self._calculate_drift_score(cycles, violations, metrics),
            'status': 'completed'
        }
        
        return report
    
    def _calculate_drift_score(
        self,
        cycles: List[Dict],
        violations: List[Dict],
        metrics: Dict
    ) -> float:
        """
        Calculate overall architectural drift score (0-100)
        
        0 = No drift, 100 = Severe drift
        """
        score = 0.0
        
        # Cycles contribute to score
        direct_cycles = sum(1 for c in cycles if c.get('cycle_length') == 2)
        indirect_cycles = sum(1 for c in cycles if c.get('cycle_length', 0) > 2)
        
        score += direct_cycles * 15  # Direct cycles are critical
        score += indirect_cycles * 8
        
        # Layer violations contribute
        score += len(violations) * 10
        
        # High instability modules
        unstable_modules = metrics.get('instability_metrics', [])
        high_instability = sum(1 for m in unstable_modules 
                              if m.get('instability_index', 0) > 0.7)
        score += high_instability * 5
        
        # Cap at 100
        return min(score, 100.0)


# Helper function
async def get_neo4j_ast_service() -> Neo4jASTService:
    """Get Neo4j AST service instance"""
    from app.database.neo4j_db import get_neo4j_driver
    driver = await get_neo4j_driver()
    return Neo4jASTService(driver)
