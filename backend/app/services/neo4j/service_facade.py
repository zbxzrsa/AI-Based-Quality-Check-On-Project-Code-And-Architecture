"""
Neo4j Service Facade

Provides a unified interface to all Neo4j services while maintaining
separation of concerns. This facade simplifies usage for clients.
"""
import logging
logger = logging.getLogger(__name__)

from typing import Dict, Any, List, Optional

from app.database.neo4j_db import get_neo4j_driver
from .ast_insert_service import ASTInsertService
from .dependency_analyzer import DependencyAnalyzer
from .metrics_calculator import MetricsCalculator
from .drift_detector import DriftDetector
from app.schemas.ast_models import ParsedFile


class Neo4jServiceFacade:
    """
    Facade providing unified access to all Neo4j services.
    
    This class delegates to specialized services while providing
    a simple interface for clients.
    """
    
    def __init__(self, driver=None):
        """
        Initialize Neo4j service facade.
        
        Args:
            driver: Optional Neo4j driver (will be fetched if not provided)
        """
        self.driver = driver
        self._ast_insert_service = None
        self._dependency_analyzer = None
        self._metrics_calculator = None
        self._drift_detector = None
    
    async def _ensure_driver(self):
        """Ensure driver is initialized"""
        if self.driver is None:
            self.driver = await get_neo4j_driver()
    
    @property
    async def ast_insert_service(self) -> ASTInsertService:
        """Get AST insert service"""
        if self._ast_insert_service is None:
            await self._ensure_driver()
            self._ast_insert_service = ASTInsertService(self.driver)
        return self._ast_insert_service
    
    @property
    async def dependency_analyzer(self) -> DependencyAnalyzer:
        """Get dependency analyzer"""
        if self._dependency_analyzer is None:
            await self._ensure_driver()
            self._dependency_analyzer = DependencyAnalyzer(self.driver)
        return self._dependency_analyzer
    
    @property
    async def metrics_calculator(self) -> MetricsCalculator:
        """Get metrics calculator"""
        if self._metrics_calculator is None:
            await self._ensure_driver()
            self._metrics_calculator = MetricsCalculator(self.driver)
        return self._metrics_calculator
    
    @property
    async def drift_detector(self) -> DriftDetector:
        """Get drift detector"""
        if self._drift_detector is None:
            await self._ensure_driver()
            dep_analyzer = await self.dependency_analyzer
            metrics_calc = await self.metrics_calculator
            self._drift_detector = DriftDetector(
                self.driver,
                dep_analyzer,
                metrics_calc
            )
        return self._drift_detector
    
    # AST Operations
    async def insert_ast_nodes(
        self,
        parsed_data: ParsedFile,
        project_id: str
    ) -> bool:
        """Insert parsed AST data into Neo4j graph"""
        service = await self.ast_insert_service
        return await service.insert_ast_nodes(parsed_data, project_id)
    
    # Dependency Analysis
    async def find_circular_dependencies(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Find circular dependencies"""
        analyzer = await self.dependency_analyzer
        return await analyzer.find_circular_dependencies(project_id)
    
    async def detect_direct_cycles(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Detect direct 2-hop cycles"""
        analyzer = await self.dependency_analyzer
        return await analyzer.detect_direct_cycles(project_id)
    
    async def detect_layer_violations(
        self,
        project_id: str,
        layer_definitions: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """Detect layer violations"""
        analyzer = await self.dependency_analyzer
        return await analyzer.detect_layer_violations(project_id, layer_definitions)
    
    async def calculate_coupling_metrics(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Calculate coupling metrics"""
        analyzer = await self.dependency_analyzer
        return await analyzer.calculate_coupling_metrics(project_id)
    
    async def find_longest_dependency_paths(
        self,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find longest dependency paths"""
        analyzer = await self.dependency_analyzer
        return await analyzer.find_longest_dependency_paths(project_id, limit)
    
    async def get_dependency_graph(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Export dependency graph for visualization"""
        analyzer = await self.dependency_analyzer
        return await analyzer.get_dependency_graph(project_id)
    
    # Metrics Calculation
    async def calculate_metrics(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Calculate comprehensive architecture metrics"""
        calculator = await self.metrics_calculator
        return await calculator.calculate_all_metrics(project_id)
    
    async def calculate_quality_score(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Calculate overall quality score"""
        calculator = await self.metrics_calculator
        return await calculator.calculate_quality_score(project_id)
    
    # Drift Detection
    async def detect_drift(
        self,
        project_id: str,
        baseline_version: str = "latest"
    ) -> Dict[str, Any]:
        """Detect architectural drift"""
        detector = await self.drift_detector
        return await detector.detect_drift(project_id, baseline_version)
    
    async def generate_weekly_drift_report(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Generate weekly drift report"""
        detector = await self.drift_detector
        return await detector.generate_weekly_drift_report(project_id)
    
    # Utility Operations
    async def delete_project_graph(
        self,
        project_id: str
    ) -> bool:
        """Delete all graph data for a project"""
        await self._ensure_driver()
        
        from app.core.config import settings
        async with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            try:
                await session.run("""
                    MATCH (p:Project {projectId: $projectId})
                    OPTIONAL MATCH (p)-[:CONTAINS*0..]->(child)
                    DETACH DELETE p, child
                """, projectId=project_id)
                return True
            except Exception as e:
                logger.info("Error deleting project graph: {e}")
                return False


# Global service instance
_neo4j_service: Optional[Neo4jServiceFacade] = None


def get_neo4j_service() -> Neo4jServiceFacade:
    """
    Get global Neo4j service facade instance.
    
    Returns:
        Neo4j service facade
    """
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jServiceFacade()
    return _neo4j_service
