"""
Neo4j Services Module

Provides modular Neo4j services following single responsibility principle.
Each service handles a specific aspect of graph database operations.

Services:
- ASTInsertService: Insert parsed AST data
- DependencyAnalyzer: Analyze dependencies and detect issues
- MetricsCalculator: Calculate architecture metrics
- DriftDetector: Detect architectural drift
- Neo4jServiceFacade: Unified interface for all services
"""

from .ast_insert_service import ASTInsertService
from .dependency_analyzer import DependencyAnalyzer
from .metrics_calculator import MetricsCalculator
from .drift_detector import DriftDetector
from .service_facade import Neo4jServiceFacade, get_neo4j_service

__all__ = [
    'ASTInsertService',
    'DependencyAnalyzer',
    'MetricsCalculator',
    'DriftDetector',
    'Neo4jServiceFacade',
    'get_neo4j_service',
]
