"""
Architecture Analyzer Service

This module provides architectural analysis capabilities including:
- Architecture analysis and violation detection (ArchitectureAnalyzer)
- Baseline snapshot creation and management (BaselineManager)
- Architectural drift detection and comparison (DriftDetector)
- Drift metrics calculation and severity assessment
- ISO/IEC 25010 compliance verification (ComplianceVerifier)

Implements Requirement 1.9: ISO/IEC 25010 compliance verification
"""

from .analyzer import ArchitectureAnalyzer
from .baseline import ArchitectureBaseline, BaselineManager
from .compliance import (
    ComplianceReport,
    ComplianceStatus,
    ComplianceVerifier,
    ComplianceViolation,
    QualityCharacteristic,
    ViolationSeverity,
)
from .drift_detector import DriftDetector, DriftMetrics, DriftResult, DriftSeverity

__all__ = [
    "ArchitectureAnalyzer",
    "BaselineManager",
    "ArchitectureBaseline",
    "DriftDetector",
    "DriftResult",
    "DriftMetrics",
    "DriftSeverity",
    "ComplianceVerifier",
    "ComplianceReport",
    "ComplianceStatus",
    "QualityCharacteristic",
    "ComplianceViolation",
    "ViolationSeverity",
]
