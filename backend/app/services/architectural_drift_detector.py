"""
Architectural Drift Detection Service

This module provides functionality to detect architectural drift by comparing
current code structure against expected architectural patterns and constraints.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from app.services.neo4j_ast_service_extended import Neo4jASTService
from app.services.architecture_golden_standard import GoldenStandardManager
from app.core.logging_config import logger

class DriftSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class DriftViolation:
    """Represents a detected architectural drift violation."""
    node_id: str
    node_name: str
    node_type: str
    violation_type: str
    severity: DriftSeverity
    description: str
    expected_pattern: str
    actual_pattern: str
    location: str
    suggested_fix: Optional[str] = None

@dataclass
class DriftSummary:
    """Summary of architectural drift analysis."""
    total_violations: int
    severity_breakdown: Dict[str, int]
    critical_violations: List[DriftViolation]
    layer_violations: List[DriftViolation]
    dependency_violations: List[DriftViolation]
    pattern_violations: List[DriftViolation]
    overall_health_score: float

class ArchitecturalDriftDetector:
    """Service for detecting architectural drift in codebases."""
    
    def __init__(self, neo4j_service: Neo4jASTService, golden_standard_manager: GoldenStandardManager):
        self.neo4j_service = neo4j_service
        self.golden_standard = golden_standard_manager
        self.logger = logger

    async def detect_drift(self, project_id: str) -> DriftSummary:
        """Main method to detect architectural drift for a project."""
        try:
            self.logger.info(f"Starting drift detection for project: {project_id}")
            
            # Get current architecture from Neo4j
            current_architecture = await self._get_current_architecture(project_id)
            
            # Get expected architecture from golden standard
            expected_architecture = await self.golden_standard.get_golden_standard(project_id)
            
            if not expected_architecture:
                self.logger.warning(f"No golden standard found for project: {project_id}")
                return DriftSummary(
                    total_violations=0,
                    severity_breakdown={},
                    critical_violations=[],
                    layer_violations=[],
                    dependency_violations=[],
                    pattern_violations=[],
                    overall_health_score=100.0
                )

            # Detect different types of violations
            violations = []
            violations.extend(await self._detect_layer_violations(current_architecture, expected_architecture))
            violations.extend(await self._detect_dependency_violations(current_architecture, expected_architecture))
            violations.extend(await self._detect_pattern_violations(current_architecture, expected_architecture))
            violations.extend(await self._detect_complexity_drift(current_architecture, expected_architecture))

            # Calculate summary statistics
            severity_breakdown = self._calculate_severity_breakdown(violations)
            critical_violations = [v for v in violations if v.severity == DriftSeverity.CRITICAL]
            layer_violations = [v for v in violations if v.violation_type == "layer_violation"]
            dependency_violations = [v for v in violations if v.violation_type == "dependency_violation"]
            pattern_violations = [v for v in violations if v.violation_type == "pattern_violation"]

            overall_health_score = self._calculate_health_score(violations, current_architecture)

            summary = DriftSummary(
                total_violations=len(violations),
                severity_breakdown=severity_breakdown,
                critical_violations=critical_violations,
                layer_violations=layer_violations,
                dependency_violations=dependency_violations,
                pattern_violations=pattern_violations,
                overall_health_score=overall_health_score
            )

            self.logger.info(f"Drift detection completed for project {project_id}: {len(violations)} violations found")
            return summary

        except Exception as e:
            self.logger.error(f"Error during drift detection for project {project_id}: {str(e)}")
            raise

    async def _get_current_architecture(self, project_id: str) -> Dict[str, Any]:
        """Retrieve current architecture from Neo4j database."""
        try:
            # Query to get all nodes and their relationships
            query = """
            MATCH (p:Project {projectId: $project_id})-[:CONTAINS]->(m:Module)
            OPTIONAL MATCH (m)-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
            OPTIONAL MATCH (c)-[:CONTAINS]->(meth:Method)
            OPTIONAL MATCH (m)-[:DEPENDS_ON]->(target:Module)
            RETURN 
                p.name as project_name,
                collect(DISTINCT m) as modules,
                collect(DISTINCT f) as files,
                collect(DISTINCT c) as classes,
                collect(DISTINCT meth) as methods,
                collect(DISTINCT target) as dependencies
            """
            
            result = await self.neo4j_service.run_query(query, {"project_id": project_id})
            
            if not result:
                return {"modules": [], "files": [], "classes": [], "methods": [], "dependencies": []}
            
            record = result[0]
            return {
                "project_name": record["project_name"],
                "modules": [dict(m) for m in record["modules"]],
                "files": [dict(f) for f in record["files"]],
                "classes": [dict(c) for c in record["classes"]],
                "methods": [dict(meth) for meth in record["methods"]],
                "dependencies": [dict(d) for d in record["dependencies"]]
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving current architecture: {str(e)}")
            return {"modules": [], "files": [], "classes": [], "methods": [], "dependencies": []}

    async def _detect_layer_violations(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Detect violations of layer architecture constraints."""
        violations = []
        
        try:
            # Get expected layer structure
            expected_layers = expected.get("layers", {})
            layer_constraints = expected.get("layer_constraints", {})
            
            # Check each module against expected layer constraints
            for module in current.get("modules", []):
                module_name = module.get("name", "")
                module_layer = module.get("layer", "")
                
                # Check if module is in correct layer
                if module_layer not in expected_layers:
                    violations.append(DriftViolation(
                        node_id=module.get("id", ""),
                        node_name=module_name,
                        node_type="module",
                        violation_type="layer_violation",
                        severity=DriftSeverity.HIGH,
                        description=f"Module '{module_name}' is in unexpected layer '{module_layer}'",
                        expected_pattern=f"Module should be in one of: {list(expected_layers.keys())}",
                        actual_pattern=f"Module is in layer: {module_layer}",
                        location=f"Module: {module_name}",
                        suggested_fix=f"Move module '{module_name}' to appropriate layer"
                    ))
                
                # Check layer dependency constraints
                violations.extend(self._check_layer_dependencies(module, current, layer_constraints))
                
        except Exception as e:
            self.logger.error(f"Error detecting layer violations: {str(e)}")
            
        return violations

    def _check_layer_dependencies(self, module: Dict[str, Any], current: Dict[str, Any], layer_constraints: Dict[str, Any]) -> List[DriftViolation]:
        """Check if module dependencies violate layer constraints."""
        violations = []
        module_name = module.get("name", "")
        module_layer = module.get("layer", "")
        
        # Get dependencies of this module
        dependencies = [d for d in current.get("dependencies", []) if d.get("source") == module.get("id")]
        
        for dep in dependencies:
            target_module_id = dep.get("target", "")
            target_module = next((m for m in current.get("modules", []) if m.get("id") == target_module_id), None)
            
            if target_module:
                target_layer = target_module.get("layer", "")
                
                # Check if dependency violates layer constraints
                allowed_layers = layer_constraints.get(module_layer, {}).get("can_depend_on", [])
                
                if target_layer not in allowed_layers and allowed_layers:  # Only check if constraints exist
                    violations.append(DriftViolation(
                        node_id=module.get("id", ""),
                        node_name=module_name,
                        node_type="module",
                        violation_type="layer_violation",
                        severity=DriftSeverity.CRITICAL,
                        description=f"Module '{module_name}' in layer '{module_layer}' depends on '{target_module.get('name')}' in layer '{target_layer}'",
                        expected_pattern=f"Layer '{module_layer}' can only depend on: {allowed_layers}",
                        actual_pattern=f"Layer '{module_layer}' depends on layer '{target_layer}'",
                        location=f"Dependency: {module_name} -> {target_module.get('name')}",
                        suggested_fix=f"Remove dependency from '{module_name}' to '{target_module.get('name')}' or refactor architecture"
                    ))
                    
        return violations

    async def _detect_dependency_violations(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Detect violations of dependency constraints."""
        violations = []
        
        try:
            # Check for circular dependencies
            violations.extend(self._detect_circular_dependencies(current))
            
            # Check for forbidden dependencies
            violations.extend(self._detect_forbidden_dependencies(current, expected))
            
            # Check for missing required dependencies
            violations.extend(self._detect_missing_dependencies(current, expected))
            
        except Exception as e:
            self.logger.error(f"Error detecting dependency violations: {str(e)}")
            
        return violations

    def _detect_circular_dependencies(self, current: Dict[str, Any]) -> List[DriftViolation]:
        """Detect circular dependencies between modules."""
        violations = []
        modules = current.get("modules", [])
        dependencies = current.get("dependencies", [])
        
        # Simple cycle detection (in practice, you'd use more sophisticated algorithms)
        for module in modules:
            module_id = module.get("id", "")
            module_name = module.get("name", "")
            
            # Look for direct cycles (A -> B -> A)
            for dep in dependencies:
                if dep.get("source") == module_id:
                    target_id = dep.get("target", "")
                    # Check if target depends back on source
                    for back_dep in dependencies:
                        if back_dep.get("source") == target_id and back_dep.get("target") == module_id:
                            target_module = next((m for m in modules if m.get("id") == target_id), None)
                            if target_module:
                                violations.append(DriftViolation(
                                    node_id=module_id,
                                    node_name=module_name,
                                    node_type="module",
                                    violation_type="dependency_violation",
                                    severity=DriftSeverity.CRITICAL,
                                    description=f"Circular dependency detected: {module_name} <-> {target_module.get('name')}",
                                    expected_pattern="No circular dependencies allowed",
                                    actual_pattern=f"{module_name} depends on {target_module.get('name')} and vice versa",
                                    location=f"Modules: {module_name}, {target_module.get('name')}",
                                    suggested_fix=f"Break circular dependency by introducing interface or moving shared code to common module"
                                ))
                                
        return violations

    def _detect_forbidden_dependencies(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Detect dependencies that are explicitly forbidden."""
        violations = []
        forbidden_deps = expected.get("forbidden_dependencies", [])
        modules = current.get("modules", [])
        dependencies = current.get("dependencies", [])
        
        for forbidden in forbidden_deps:
            source_pattern = forbidden.get("source_pattern", "")
            target_pattern = forbidden.get("target_pattern", "")
            reason = forbidden.get("reason", "No reason provided")
            
            for dep in dependencies:
                source_module = next((m for m in modules if m.get("id") == dep.get("source")), None)
                target_module = next((m for m in modules if m.get("id") == dep.get("target")), None)
                
                if source_module and target_module:
                    source_name = source_module.get("name", "")
                    target_name = target_module.get("name", "")
                    
                    # Simple pattern matching (in practice, you'd use regex)
                    if (source_pattern in source_name and target_pattern in target_name):
                        violations.append(DriftViolation(
                            node_id=source_module.get("id", ""),
                            node_name=source_name,
                            node_type="module",
                            violation_type="dependency_violation",
                            severity=DriftSeverity.HIGH,
                            description=f"Forbidden dependency: {source_name} -> {target_name}",
                            expected_pattern=f"Dependency from '{source_pattern}' to '{target_pattern}' is forbidden: {reason}",
                            actual_pattern=f"{source_name} depends on {target_name}",
                            location=f"Dependency: {source_name} -> {target_name}",
                            suggested_fix=f"Remove dependency or refactor to use allowed pattern"
                        ))
                        
        return violations

    def _detect_missing_dependencies(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Detect missing required dependencies."""
        violations = []
        required_deps = expected.get("required_dependencies", [])
        modules = current.get("modules", [])
        dependencies = current.get("dependencies", [])
        
        for required in required_deps:
            source_pattern = required.get("source_pattern", "")
            target_pattern = required.get("target_pattern", "")
            reason = required.get("reason", "No reason provided")
            
            # Check if required dependency exists
            found = False
            for dep in dependencies:
                source_module = next((m for m in modules if m.get("id") == dep.get("source")), None)
                target_module = next((m for m in modules if m.get("id") == dep.get("target")), None)
                
                if source_module and target_module:
                    source_name = source_module.get("name", "")
                    target_name = target_module.get("name", "")
                    
                    if (source_pattern in source_name and target_pattern in target_name):
                        found = True
                        break
            
            if not found:
                violations.append(DriftViolation(
                    node_id="",
                    node_name=f"{source_pattern} -> {target_pattern}",
                    node_type="dependency",
                    violation_type="dependency_violation",
                    severity=DriftSeverity.MEDIUM,
                    description=f"Missing required dependency: {source_pattern} -> {target_pattern}",
                    expected_pattern=f"Dependency from '{source_pattern}' to '{target_pattern}' is required: {reason}",
                    actual_pattern="Required dependency not found",
                    location=f"Expected dependency: {source_pattern} -> {target_pattern}",
                    suggested_fix=f"Add dependency from '{source_pattern}' to '{target_pattern}'"
                ))
                
        return violations

    async def _detect_pattern_violations(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Detect violations of architectural patterns."""
        violations = []
        
        try:
            expected_patterns = expected.get("architectural_patterns", [])
            
            # Check naming conventions
            violations.extend(self._check_naming_conventions(current, expected))
            
            # Check structural patterns
            violations.extend(self._check_structural_patterns(current, expected))
            
        except Exception as e:
            self.logger.error(f"Error detecting pattern violations: {str(e)}")
            
        return violations

    def _check_naming_conventions(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Check naming convention violations."""
        violations = []
        naming_rules = expected.get("naming_conventions", {})
        modules = current.get("modules", [])
        classes = current.get("classes", [])
        files = current.get("files", [])
        
        # Check module naming
        module_pattern = naming_rules.get("module_pattern", "")
        for module in modules:
            module_name = module.get("name", "")
            if module_pattern and not self._matches_pattern(module_name, module_pattern):
                violations.append(DriftViolation(
                    node_id=module.get("id", ""),
                    node_name=module_name,
                    node_type="module",
                    violation_type="pattern_violation",
                    severity=DriftSeverity.LOW,
                    description=f"Module naming convention violation: {module_name}",
                    expected_pattern=f"Module names should match pattern: {module_pattern}",
                    actual_pattern=f"Module name: {module_name}",
                    location=f"Module: {module_name}",
                    suggested_fix=f"Rename module to match pattern: {module_pattern}"
                ))
                
        # Check class naming
        class_pattern = naming_rules.get("class_pattern", "")
        for cls in classes:
            class_name = cls.get("name", "")
            if class_pattern and not self._matches_pattern(class_name, class_pattern):
                violations.append(DriftViolation(
                    node_id=cls.get("id", ""),
                    node_name=class_name,
                    node_type="class",
                    violation_type="pattern_violation",
                    severity=DriftSeverity.LOW,
                    description=f"Class naming convention violation: {class_name}",
                    expected_pattern=f"Class names should match pattern: {class_pattern}",
                    actual_pattern=f"Class name: {class_name}",
                    location=f"Class: {class_name}",
                    suggested_fix=f"Rename class to match pattern: {class_pattern}"
                ))
                
        return violations

    def _check_structural_patterns(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Check structural architectural pattern violations."""
        violations = []
        structural_rules = expected.get("structural_rules", {})
        modules = current.get("modules", [])
        classes = current.get("classes", [])
        
        # Check module structure rules
        max_classes_per_module = structural_rules.get("max_classes_per_module", 0)
        if max_classes_per_module > 0:
            for module in modules:
                module_classes = [c for c in classes if c.get("module_id") == module.get("id")]
                if len(module_classes) > max_classes_per_module:
                    violations.append(DriftViolation(
                        node_id=module.get("id", ""),
                        node_name=module.get("name", ""),
                        node_type="module",
                        violation_type="pattern_violation",
                        severity=DriftSeverity.MEDIUM,
                        description=f"Module has too many classes: {len(module_classes)} > {max_classes_per_module}",
                        expected_pattern=f"Module should have at most {max_classes_per_module} classes",
                        actual_pattern=f"Module has {len(module_classes)} classes",
                        location=f"Module: {module.get('name', '')}",
                        suggested_fix=f"Split module into smaller modules or move classes to appropriate modules"
                    ))
                    
        return violations

    async def _detect_complexity_drift(self, current: Dict[str, Any], expected: Dict[str, Any]) -> List[DriftViolation]:
        """Detect complexity-related architectural drift."""
        violations = []
        
        try:
            complexity_rules = expected.get("complexity_rules", {})
            max_complexity = complexity_rules.get("max_complexity", 0)
            max_coupling = complexity_rules.get("max_coupling", 0)
            
            # Check complexity violations
            violations.extend(self._check_complexity_violations(current, max_complexity))
            violations.extend(self._check_coupling_violations(current, max_coupling))
            
        except Exception as e:
            self.logger.error(f"Error detecting complexity drift: {str(e)}")
            
        return violations

    def _check_complexity_violations(self, current: Dict[str, Any], max_complexity: int) -> List[DriftViolation]:
        """Check for complexity violations."""
        violations = []
        classes = current.get("classes", [])
        methods = current.get("methods", [])
        
        # Check class complexity
        for cls in classes:
            complexity = cls.get("complexity", 0)
            if max_complexity > 0 and complexity > max_complexity:
                violations.append(DriftViolation(
                    node_id=cls.get("id", ""),
                    node_name=cls.get("name", ""),
                    node_type="class",
                    violation_type="complexity_violation",
                    severity=DriftSeverity.MEDIUM if complexity <= max_complexity * 1.5 else DriftSeverity.HIGH,
                    description=f"Class complexity too high: {complexity} > {max_complexity}",
                    expected_pattern=f"Class complexity should be <= {max_complexity}",
                    actual_pattern=f"Class complexity: {complexity}",
                    location=f"Class: {cls.get('name', '')}",
                    suggested_fix="Refactor class to reduce complexity by extracting methods or splitting class"
                ))
                
        # Check method complexity
        for method in methods:
            complexity = method.get("complexity", 0)
            if max_complexity > 0 and complexity > max_complexity:
                violations.append(DriftViolation(
                    node_id=method.get("id", ""),
                    node_name=method.get("name", ""),
                    node_type="method",
                    violation_type="complexity_violation",
                    severity=DriftSeverity.LOW if complexity <= max_complexity * 1.5 else DriftSeverity.MEDIUM,
                    description=f"Method complexity too high: {complexity} > {max_complexity}",
                    expected_pattern=f"Method complexity should be <= {max_complexity}",
                    actual_pattern=f"Method complexity: {complexity}",
                    location=f"Method: {method.get('name', '')}",
                    suggested_fix="Refactor method to reduce complexity by extracting smaller methods"
                ))
                
        return violations

    def _check_coupling_violations(self, current: Dict[str, Any], max_coupling: int) -> List[DriftViolation]:
        """Check for coupling violations."""
        violations = []
        modules = current.get("modules", [])
        dependencies = current.get("dependencies", [])
        
        # Calculate coupling for each module
        for module in modules:
            module_id = module.get("id", "")
            module_name = module.get("name", "")
            
            # Count incoming and outgoing dependencies
            incoming = len([d for d in dependencies if d.get("target") == module_id])
            outgoing = len([d for d in dependencies if d.get("source") == module_id])
            total_coupling = incoming + outgoing
            
            if max_coupling > 0 and total_coupling > max_coupling:
                violations.append(DriftViolation(
                    node_id=module_id,
                    node_name=module_name,
                    node_type="module",
                    violation_type="coupling_violation",
                    severity=DriftSeverity.MEDIUM if total_coupling <= max_coupling * 1.5 else DriftSeverity.HIGH,
                    description=f"Module coupling too high: {total_coupling} > {max_coupling}",
                    expected_pattern=f"Module coupling should be <= {max_coupling}",
                    actual_pattern=f"Module coupling: {total_coupling} (incoming: {incoming}, outgoing: {outgoing})",
                    location=f"Module: {module_name}",
                    suggested_fix="Reduce module dependencies by introducing interfaces or reducing responsibilities"
                ))
                
        return violations

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Simple pattern matching (in practice, you'd use regex)."""
        # This is a simplified implementation
        # In practice, you'd use proper regex matching
        return pattern in name or name.endswith(pattern.replace("*", ""))

    def _calculate_severity_breakdown(self, violations: List[DriftViolation]) -> Dict[str, int]:
        """Calculate breakdown of violations by severity."""
        breakdown = {severity.value: 0 for severity in DriftSeverity}
        for violation in violations:
            breakdown[violation.severity.value] += 1
        return breakdown

    def _calculate_health_score(self, violations: List[DriftViolation], current: Dict[str, Any]) -> float:
        """Calculate overall architectural health score (0-100)."""
        if not violations:
            return 100.0
            
        # Assign weights to different violation types and severities
        weights = {
            DriftSeverity.CRITICAL: 10.0,
            DriftSeverity.HIGH: 5.0,
            DriftSeverity.MEDIUM: 2.0,
            DriftSeverity.LOW: 0.5
        }
        
        total_penalty = 0.0
        for violation in violations:
            total_penalty += weights.get(violation.severity, 1.0)
            
        # Calculate score (base 100, subtract penalties)
        score = max(0.0, 100.0 - total_penalty)
        
        # Adjust score based on project size (larger projects can tolerate more violations)
        module_count = len(current.get("modules", []))
        if module_count > 0:
            size_factor = min(1.0, module_count / 20.0)  # Normalize to 0-1 based on 20 modules
            score = min(100.0, score + (size_factor * 5.0))  # Add up to 5 points for larger projects
            
        return round(score, 1)

    async def generate_drift_report(self, project_id: str) -> Dict[str, Any]:
        """Generate a comprehensive drift detection report."""
        try:
            summary = await self.detect_drift(project_id)
            
            report = {
                "project_id": project_id,
                "detection_date": "2024-01-01T00:00:00Z",  # In practice, use actual timestamp
                "summary": {
                    "total_violations": summary.total_violations,
                    "severity_breakdown": summary.severity_breakdown,
                    "overall_health_score": summary.overall_health_score
                },
                "violations": {
                    "critical": [self._violation_to_dict(v) for v in summary.critical_violations],
                    "layer_violations": [self._violation_to_dict(v) for v in summary.layer_violations],
                    "dependency_violations": [self._violation_to_dict(v) for v in summary.dependency_violations],
                    "pattern_violations": [self._violation_to_dict(v) for v in summary.pattern_violations]
                },
                "recommendations": self._generate_recommendations(summary)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating drift report: {str(e)}")
            return {"error": str(e)}

    def _violation_to_dict(self, violation: DriftViolation) -> Dict[str, Any]:
        """Convert violation to dictionary for JSON serialization."""
        return {
            "node_id": violation.node_id,
            "node_name": violation.node_name,
            "node_type": violation.node_type,
            "violation_type": violation.violation_type,
            "severity": violation.severity.value,
            "description": violation.description,
            "expected_pattern": violation.expected_pattern,
            "actual_pattern": violation.actual_pattern,
            "location": violation.location,
            "suggested_fix": violation.suggested_fix
        }

    def _generate_recommendations(self, summary: DriftSummary) -> List[str]:
        """Generate recommendations based on drift analysis."""
        recommendations = []
        
        if summary.critical_violations:
            recommendations.append("Address critical violations immediately as they pose significant architectural risks")
            
        if summary.layer_violations:
            recommendations.append("Review and enforce layer architecture constraints")
            
        if summary.dependency_violations:
            recommendations.append("Fix dependency violations to improve modularity")
            
        if summary.pattern_violations:
            recommendations.append("Enforce architectural patterns and naming conventions")
            
        if summary.overall_health_score < 70:
            recommendations.append("Consider architectural refactoring to improve overall codebase health")
            
        return recommendations
