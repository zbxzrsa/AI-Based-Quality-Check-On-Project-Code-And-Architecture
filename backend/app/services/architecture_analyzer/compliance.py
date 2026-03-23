"""
ISO/IEC 25010 Compliance Verification

This module implements compliance verification against ISO/IEC 25010 quality standards.
It checks code against 8 quality characteristics and generates compliance reports.

ISO/IEC 25010 Quality Characteristics:
1. Functional Suitability - Completeness, correctness, appropriateness
2. Performance Efficiency - Time behavior, resource utilization, capacity
3. Compatibility - Co-existence, interoperability
4. Usability - Appropriateness recognizability, learnability, operability
5. Reliability - Maturity, availability, fault tolerance, recoverability
6. Security - Confidentiality, integrity, non-repudiation, accountability, authenticity
7. Maintainability - Modularity, reusability, analyzability, modifiability, testability
8. Portability - Adaptability, installability, replaceability

Implements Requirements 1.9 and 15.8
"""
import logging
logger = logging.getLogger(__name__)


from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from app.database.neo4j_db import get_neo4j_driver
from app.core.config import settings


class ComplianceStatus(str, Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"           # Score >= 80
    PARTIALLY_COMPLIANT = "partially_compliant"  # Score 60-79
    NON_COMPLIANT = "non_compliant"   # Score < 60


class ViolationSeverity(str, Enum):
    """Severity levels for compliance violations"""
    CRITICAL = "critical"  # Score impact > 20 points
    HIGH = "high"          # Score impact 10-20 points
    MEDIUM = "medium"      # Score impact 5-10 points
    LOW = "low"            # Score impact < 5 points


@dataclass
class QualityCharacteristic:
    """Represents a quality characteristic score"""
    name: str
    score: int  # 0-100
    max_score: int
    violations: List[Dict[str, Any]]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    characteristic: str
    severity: ViolationSeverity
    entity_name: str
    entity_type: str
    description: str
    metric_value: Any
    threshold: Any
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "characteristic": self.characteristic,
            "severity": self.severity.value,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "description": self.description,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "recommendation": self.recommendation
        }


@dataclass
class ComplianceReport:
    """Complete compliance verification report"""
    project_id: str
    timestamp: str
    overall_score: int  # 0-100
    compliance_status: ComplianceStatus
    characteristics: Dict[str, QualityCharacteristic]
    violations: List[ComplianceViolation]
    summary: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "project_id": self.project_id,
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "compliance_status": self.compliance_status.value,
            "characteristics": {
                name: char.to_dict() 
                for name, char in self.characteristics.items()
            },
            "violations": [v.to_dict() for v in self.violations],
            "summary": self.summary,
            "recommendations": self.recommendations
        }



class ComplianceVerifier:
    """
    Verifies code compliance against ISO/IEC 25010 quality standards
    
    Features:
    - Check all 8 quality characteristics
    - Calculate compliance scores (0-100)
    - Identify violations with severity
    - Generate actionable recommendations
    - Produce comprehensive compliance reports
    """
    
    # Thresholds for quality metrics
    COMPLEXITY_THRESHOLD = 10  # Cyclomatic complexity
    LOC_THRESHOLD = 300  # Lines of code per entity
    DEPENDENCY_THRESHOLD = 10  # Max dependencies per entity
    DEPTH_THRESHOLD = 5  # Max inheritance/nesting depth
    
    def __init__(self):
        """Initialize compliance verifier"""
        pass
    
    async def verify_compliance(self, project_id: str) -> ComplianceReport:
        """
        Verify compliance against ISO/IEC 25010 standards
        
        Args:
            project_id: Project identifier
        
        Returns:
            ComplianceReport with scores and violations
        """
        driver = await get_neo4j_driver()
        
        # Get project data
        nodes = await self._get_project_nodes(driver, project_id)
        relationships = await self._get_project_relationships(driver, project_id)
        
        # Check each quality characteristic
        characteristics = {}
        all_violations = []
        
        # 1. Functional Suitability
        func_suit = await self._check_functional_suitability(nodes, relationships)
        characteristics["functional_suitability"] = func_suit
        all_violations.extend(self._extract_violations(func_suit, "functional_suitability"))
        
        # 2. Performance Efficiency
        perf_eff = await self._check_performance_efficiency(nodes, relationships)
        characteristics["performance_efficiency"] = perf_eff
        all_violations.extend(self._extract_violations(perf_eff, "performance_efficiency"))
        
        # 3. Compatibility
        compat = await self._check_compatibility(nodes, relationships)
        characteristics["compatibility"] = compat
        all_violations.extend(self._extract_violations(compat, "compatibility"))
        
        # 4. Usability
        usability = await self._check_usability(nodes, relationships)
        characteristics["usability"] = usability
        all_violations.extend(self._extract_violations(usability, "usability"))
        
        # 5. Reliability
        reliability = await self._check_reliability(nodes, relationships)
        characteristics["reliability"] = reliability
        all_violations.extend(self._extract_violations(reliability, "reliability"))
        
        # 6. Security
        security = await self._check_security(nodes, relationships)
        characteristics["security"] = security
        all_violations.extend(self._extract_violations(security, "security"))
        
        # 7. Maintainability
        maintainability = await self._check_maintainability(nodes, relationships)
        characteristics["maintainability"] = maintainability
        all_violations.extend(self._extract_violations(maintainability, "maintainability"))
        
        # 8. Portability
        portability = await self._check_portability(nodes, relationships)
        characteristics["portability"] = portability
        all_violations.extend(self._extract_violations(portability, "portability"))
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(characteristics)
        
        # Determine compliance status
        compliance_status = self._determine_compliance_status(overall_score)
        
        # Generate summary and recommendations
        summary = self._generate_summary(overall_score, compliance_status, characteristics)
        recommendations = self._generate_recommendations(characteristics, all_violations)
        
        return ComplianceReport(
            project_id=project_id,
            timestamp=datetime.utcnow().isoformat(),
            overall_score=overall_score,
            compliance_status=compliance_status,
            characteristics=characteristics,
            violations=all_violations,
            summary=summary,
            recommendations=recommendations
        )

    
    async def _get_project_nodes(
        self,
        driver: Any,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get all nodes for the project"""
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
            logger.info("Error getting project nodes: {str(e)}")
        
        return nodes
    
    async def _get_project_relationships(
        self,
        driver: Any,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get all relationships for the project"""
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
            logger.info("Error getting project relationships: {str(e)}")
        
        return relationships

    
    async def _check_functional_suitability(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Functional Suitability (Completeness, Correctness, Appropriateness)
        
        Checks:
        - Complete implementations (no empty functions)
        - Proper error handling
        - Appropriate function/class design
        """
        violations = []
        recommendations = []
        score = 100
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown")
            node_type = props.get("type", "unknown")
            
            # Check for empty implementations
            loc = props.get("lines_of_code", 0)
            if node_type in ["function", "method"] and loc <= 2:
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": "Empty or minimal implementation",
                    "severity": "high",
                    "metric": f"{loc} LOC"
                })
                score -= 5
            
            # Check for error handling indicators
            has_error_handling = props.get("has_error_handling", False)
            if node_type in ["function", "method"] and not has_error_handling and loc > 10:
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": "Missing error handling",
                    "severity": "medium",
                    "metric": "No try-catch or error checks"
                })
                score -= 3
        
        if violations:
            recommendations.append(
                "Implement proper error handling in all functions with business logic"
            )
            recommendations.append(
                "Complete all empty or stub implementations"
            )
        
        return QualityCharacteristic(
            name="Functional Suitability",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    async def _check_performance_efficiency(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Performance Efficiency (Time behavior, Resource utilization, Capacity)
        
        Checks:
        - High complexity functions (performance bottlenecks)
        - Large functions (resource intensive)
        - Excessive dependencies (coupling issues)
        """
        violations = []
        recommendations = []
        score = 100
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown")
            node_type = props.get("type", "unknown")
            
            # Check complexity
            complexity = props.get("complexity", 0)
            if complexity > self.COMPLEXITY_THRESHOLD:
                severity = "critical" if complexity > 20 else "high"
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": f"High cyclomatic complexity ({complexity})",
                    "severity": severity,
                    "metric": f"Complexity: {complexity}, Threshold: {self.COMPLEXITY_THRESHOLD}"
                })
                score -= min(10, (complexity - self.COMPLEXITY_THRESHOLD) // 2)
            
            # Check function size
            loc = props.get("lines_of_code", 0)
            if loc > self.LOC_THRESHOLD:
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": f"Large function/class ({loc} LOC)",
                    "severity": "medium",
                    "metric": f"LOC: {loc}, Threshold: {self.LOC_THRESHOLD}"
                })
                score -= 3
        
        # Check for excessive dependencies
        dependency_count = {}
        for rel in relationships:
            source = rel["source_name"]
            dependency_count[source] = dependency_count.get(source, 0) + 1
        
        for entity, count in dependency_count.items():
            if count > self.DEPENDENCY_THRESHOLD:
                violations.append({
                    "entity": entity,
                    "type": "dependency",
                    "issue": f"Excessive dependencies ({count})",
                    "severity": "medium",
                    "metric": f"Dependencies: {count}, Threshold: {self.DEPENDENCY_THRESHOLD}"
                })
                score -= 2
        
        if violations:
            recommendations.append(
                "Refactor high-complexity functions to improve performance"
            )
            recommendations.append(
                "Break down large functions into smaller, focused units"
            )
            recommendations.append(
                "Reduce coupling by minimizing dependencies"
            )
        
        return QualityCharacteristic(
            name="Performance Efficiency",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    async def _check_compatibility(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Compatibility (Co-existence, Interoperability)
        
        Checks:
        - Proper interfaces and abstractions
        - Dependency management
        - Module boundaries
        """
        violations = []
        recommendations = []
        score = 100
        
        # Check for circular dependencies (compatibility issue)
        circular_deps = await self._detect_circular_dependencies(relationships)
        
        for cycle in circular_deps:
            violations.append({
                "entity": " -> ".join(cycle),
                "type": "circular_dependency",
                "issue": "Circular dependency detected",
                "severity": "high",
                "metric": f"Cycle length: {len(cycle)}"
            })
            score -= 10
        
        # Check for proper interface usage
        interface_count = sum(1 for n in nodes 
                            if n["properties"].get("type") == "interface")
        class_count = sum(1 for n in nodes 
                         if n["properties"].get("type") == "class")
        
        if class_count > 10 and interface_count == 0:
            violations.append({
                "entity": "project",
                "type": "architecture",
                "issue": "No interfaces defined for large codebase",
                "severity": "medium",
                "metric": f"{class_count} classes, 0 interfaces"
            })
            score -= 5
            recommendations.append(
                "Define interfaces to improve interoperability and testability"
            )
        
        if circular_deps:
            recommendations.append(
                "Resolve circular dependencies to improve module independence"
            )
        
        return QualityCharacteristic(
            name="Compatibility",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )
    
    async def _detect_circular_dependencies(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        # Build adjacency list
        graph = {}
        for rel in relationships:
            source = rel["source_name"]
            target = rel["target_name"]
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        # DFS to detect cycles
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        if len(cycle) <= 10:  # Only report small cycles
                            cycles.append(cycle)
                        return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles[:5]  # Return max 5 cycles

    
    async def _check_usability(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Usability (Recognizability, Learnability, Operability)
        
        Checks:
        - Naming conventions
        - Code documentation
        - API design
        """
        violations = []
        recommendations = []
        score = 100
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown")
            node_type = props.get("type", "unknown")
            
            # Check naming conventions
            if node_type == "class":
                if not name[0].isupper():
                    violations.append({
                        "entity": name,
                        "type": node_type,
                        "issue": "Class name should start with uppercase",
                        "severity": "low",
                        "metric": f"Name: {name}"
                    })
                    score -= 1
            
            # Check for documentation
            has_docstring = props.get("has_docstring", False)
            if node_type in ["class", "function"] and not has_docstring:
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": "Missing documentation",
                    "severity": "low",
                    "metric": "No docstring"
                })
                score -= 1
            
            # Check for overly short names (< 3 chars, excluding common ones)
            if len(name) < 3 and name not in ["id", "x", "y", "i", "j", "k"]:
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": "Name too short, not descriptive",
                    "severity": "low",
                    "metric": f"Length: {len(name)}"
                })
                score -= 1
        
        if violations:
            recommendations.append(
                "Follow naming conventions for better code readability"
            )
            recommendations.append(
                "Add documentation to all public classes and functions"
            )
        
        return QualityCharacteristic(
            name="Usability",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    async def _check_reliability(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Reliability (Maturity, Availability, Fault tolerance, Recoverability)
        
        Checks:
        - Error handling patterns
        - Fault tolerance mechanisms
        - Recovery procedures
        """
        violations = []
        recommendations = []
        score = 100
        
        functions_with_error_handling = 0
        total_functions = 0
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown")
            node_type = props.get("type", "unknown")
            
            if node_type in ["function", "method"]:
                total_functions += 1
                has_error_handling = props.get("has_error_handling", False)
                
                if has_error_handling:
                    functions_with_error_handling += 1
                else:
                    loc = props.get("lines_of_code", 0)
                    if loc > 20:  # Only flag larger functions
                        violations.append({
                            "entity": name,
                            "type": node_type,
                            "issue": "Missing error handling in substantial function",
                            "severity": "medium",
                            "metric": f"{loc} LOC, no error handling"
                        })
                        score -= 2
        
        # Calculate error handling coverage
        if total_functions > 0:
            error_handling_coverage = (functions_with_error_handling / total_functions) * 100
            if error_handling_coverage < 50:
                violations.append({
                    "entity": "project",
                    "type": "architecture",
                    "issue": f"Low error handling coverage ({error_handling_coverage:.1f}%)",
                    "severity": "high",
                    "metric": f"{functions_with_error_handling}/{total_functions} functions"
                })
                score -= 15
        
        if violations:
            recommendations.append(
                "Implement comprehensive error handling in all critical functions"
            )
            recommendations.append(
                "Add fault tolerance mechanisms for external service calls"
            )
            recommendations.append(
                "Implement recovery procedures for failure scenarios"
            )
        
        return QualityCharacteristic(
            name="Reliability",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    async def _check_security(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Security (Confidentiality, Integrity, Non-repudiation, Accountability, Authenticity)
        
        Checks:
        - Security-sensitive function patterns
        - Authentication/authorization indicators
        - Input validation
        """
        violations = []
        recommendations = []
        score = 100
        
        # Security-sensitive keywords
        security_keywords = [
            "password", "token", "secret", "key", "auth", "login",
            "credential", "session", "encrypt", "decrypt"
        ]
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown").lower()
            node_type = props.get("type", "unknown")
            
            # Check if security-sensitive function has proper handling
            is_security_sensitive = any(keyword in name for keyword in security_keywords)
            
            if is_security_sensitive:
                has_error_handling = props.get("has_error_handling", False)
                if not has_error_handling:
                    violations.append({
                        "entity": props.get("name", "unknown"),
                        "type": node_type,
                        "issue": "Security-sensitive function lacks error handling",
                        "severity": "critical",
                        "metric": "No error handling"
                    })
                    score -= 10
                
                # Check for proper validation
                has_validation = props.get("has_validation", False)
                if not has_validation:
                    violations.append({
                        "entity": props.get("name", "unknown"),
                        "type": node_type,
                        "issue": "Security-sensitive function may lack input validation",
                        "severity": "high",
                        "metric": "No validation detected"
                    })
                    score -= 5
        
        # Check for authentication/authorization patterns
        auth_functions = sum(1 for n in nodes 
                           if any(kw in n["properties"].get("name", "").lower() 
                                 for kw in ["auth", "login", "verify"]))
        
        if len(nodes) > 50 and auth_functions == 0:
            violations.append({
                "entity": "project",
                "type": "architecture",
                "issue": "No authentication functions detected in large codebase",
                "severity": "high",
                "metric": f"{len(nodes)} entities, 0 auth functions"
            })
            score -= 10
        
        if violations:
            recommendations.append(
                "Implement proper error handling in all security-sensitive functions"
            )
            recommendations.append(
                "Add input validation to prevent injection attacks"
            )
            recommendations.append(
                "Implement authentication and authorization mechanisms"
            )
        
        return QualityCharacteristic(
            name="Security",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    async def _check_maintainability(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Maintainability (Modularity, Reusability, Analyzability, Modifiability, Testability)
        
        Checks:
        - Code complexity
        - Module size
        - Code duplication indicators
        - Testability patterns
        """
        violations = []
        recommendations = []
        score = 100
        
        high_complexity_count = 0
        large_entity_count = 0
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown")
            node_type = props.get("type", "unknown")
            
            # Check complexity (maintainability issue)
            complexity = props.get("complexity", 0)
            if complexity > 15:
                high_complexity_count += 1
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": f"High complexity reduces maintainability",
                    "severity": "high",
                    "metric": f"Complexity: {complexity}"
                })
                score -= 3
            
            # Check entity size
            loc = props.get("lines_of_code", 0)
            if loc > self.LOC_THRESHOLD:
                large_entity_count += 1
                violations.append({
                    "entity": name,
                    "type": node_type,
                    "issue": "Large entity difficult to maintain",
                    "severity": "medium",
                    "metric": f"{loc} LOC"
                })
                score -= 2
        
        # Check modularity (coupling)
        avg_dependencies = len(relationships) / len(nodes) if nodes else 0
        if avg_dependencies > 5:
            violations.append({
                "entity": "project",
                "type": "architecture",
                "issue": "High coupling reduces maintainability",
                "severity": "medium",
                "metric": f"Avg {avg_dependencies:.1f} dependencies per entity"
            })
            score -= 10
        
        if violations:
            recommendations.append(
                "Refactor high-complexity functions to improve maintainability"
            )
            recommendations.append(
                "Break down large entities into smaller, focused modules"
            )
            recommendations.append(
                "Reduce coupling between modules"
            )
            recommendations.append(
                "Add unit tests to improve testability"
            )
        
        return QualityCharacteristic(
            name="Maintainability",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    async def _check_portability(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> QualityCharacteristic:
        """
        Check Portability (Adaptability, Installability, Replaceability)
        
        Checks:
        - Platform-specific code
        - Hardcoded paths
        - Environment dependencies
        """
        violations = []
        recommendations = []
        score = 100
        
        # Platform-specific indicators
        platform_keywords = [
            "windows", "linux", "darwin", "win32", "posix",
            "c:\\", "/usr/", "/home/", "d:\\"
        ]
        
        for node in nodes:
            props = node["properties"]
            name = props.get("name", "unknown").lower()
            file_path = props.get("file_path", "").lower()
            
            # Check for platform-specific code
            has_platform_code = any(keyword in name or keyword in file_path 
                                   for keyword in platform_keywords)
            
            if has_platform_code:
                violations.append({
                    "entity": props.get("name", "unknown"),
                    "type": props.get("type", "unknown"),
                    "issue": "Potential platform-specific code",
                    "severity": "low",
                    "metric": "Platform-specific keywords detected"
                })
                score -= 2
        
        # Check for hardcoded paths (basic check)
        hardcoded_path_count = 0
        for node in nodes:
            props = node["properties"]
            file_path = props.get("file_path", "")
            
            # Simple heuristic: absolute paths in code
            if any(indicator in file_path for indicator in ["c:\\", "d:\\", "/usr/", "/home/"]):
                hardcoded_path_count += 1
        
        if hardcoded_path_count > 0:
            violations.append({
                "entity": "project",
                "type": "architecture",
                "issue": f"Hardcoded paths detected ({hardcoded_path_count})",
                "severity": "medium",
                "metric": f"{hardcoded_path_count} instances"
            })
            score -= 5
        
        if violations:
            recommendations.append(
                "Use environment variables or configuration files instead of hardcoded paths"
            )
            recommendations.append(
                "Abstract platform-specific code behind interfaces"
            )
            recommendations.append(
                "Use cross-platform libraries and APIs"
            )
        
        return QualityCharacteristic(
            name="Portability",
            score=max(0, score),
            max_score=100,
            violations=violations,
            recommendations=recommendations
        )

    
    def _extract_violations(
        self,
        characteristic: QualityCharacteristic,
        char_name: str
    ) -> List[ComplianceViolation]:
        """Extract violations from a quality characteristic"""
        violations = []
        
        for v in characteristic.violations:
            severity_map = {
                "critical": ViolationSeverity.CRITICAL,
                "high": ViolationSeverity.HIGH,
                "medium": ViolationSeverity.MEDIUM,
                "low": ViolationSeverity.LOW
            }
            
            severity = severity_map.get(v.get("severity", "low"), ViolationSeverity.LOW)
            
            violations.append(ComplianceViolation(
                characteristic=char_name,
                severity=severity,
                entity_name=v.get("entity", "unknown"),
                entity_type=v.get("type", "unknown"),
                description=v.get("issue", ""),
                metric_value=v.get("metric", ""),
                threshold="N/A",
                recommendation=self._get_violation_recommendation(v)
            ))
        
        return violations
    
    def _get_violation_recommendation(self, violation: Dict[str, Any]) -> str:
        """Get specific recommendation for a violation"""
        issue = violation.get("issue", "").lower()
        
        if "complexity" in issue:
            return "Refactor to reduce cyclomatic complexity"
        elif "error handling" in issue:
            return "Add try-catch blocks and proper error handling"
        elif "documentation" in issue:
            return "Add docstrings and comments"
        elif "naming" in issue:
            return "Follow naming conventions"
        elif "circular dependency" in issue:
            return "Refactor to break circular dependency"
        elif "security" in issue:
            return "Implement security best practices"
        elif "large" in issue or "loc" in issue:
            return "Break down into smaller units"
        else:
            return "Review and improve code quality"
    
    def _calculate_overall_score(
        self,
        characteristics: Dict[str, QualityCharacteristic]
    ) -> int:
        """Calculate overall compliance score (weighted average)"""
        # Equal weights for all characteristics
        total_score = sum(char.score for char in characteristics.values())
        overall_score = total_score // len(characteristics)
        
        return overall_score
    
    def _determine_compliance_status(self, overall_score: int) -> ComplianceStatus:
        """Determine compliance status based on overall score"""
        if overall_score >= 80:
            return ComplianceStatus.COMPLIANT
        elif overall_score >= 60:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            return ComplianceStatus.NON_COMPLIANT

    
    def _generate_summary(
        self,
        overall_score: int,
        compliance_status: ComplianceStatus,
        characteristics: Dict[str, QualityCharacteristic]
    ) -> str:
        """Generate human-readable summary"""
        summary_parts = [
            f"ISO/IEC 25010 Compliance Verification: {compliance_status.value.upper()}",
            f"Overall Score: {overall_score}/100"
        ]
        
        # Add characteristic scores
        char_scores = []
        for name, char in characteristics.items():
            char_scores.append(f"{char.name}: {char.score}/100")
        
        summary_parts.append("Characteristic Scores: " + ", ".join(char_scores))
        
        # Count violations by severity
        all_violations = []
        for char in characteristics.values():
            all_violations.extend(char.violations)
        
        critical_count = sum(1 for v in all_violations if v.get("severity") == "critical")
        high_count = sum(1 for v in all_violations if v.get("severity") == "high")
        medium_count = sum(1 for v in all_violations if v.get("severity") == "medium")
        low_count = sum(1 for v in all_violations if v.get("severity") == "low")
        
        if critical_count > 0:
            summary_parts.append(f"CRITICAL: {critical_count} critical violations found")
        if high_count > 0:
            summary_parts.append(f"HIGH: {high_count} high-severity violations")
        if medium_count > 0:
            summary_parts.append(f"MEDIUM: {medium_count} medium-severity violations")
        if low_count > 0:
            summary_parts.append(f"LOW: {low_count} low-severity violations")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_recommendations(
        self,
        characteristics: Dict[str, QualityCharacteristic],
        violations: List[ComplianceViolation]
    ) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Add characteristic-specific recommendations
        for char in characteristics.values():
            if char.score < 80 and char.recommendations:
                recommendations.extend(char.recommendations)
        
        # Add priority recommendations based on violations
        critical_violations = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
        high_violations = [v for v in violations if v.severity == ViolationSeverity.HIGH]
        
        if critical_violations:
            recommendations.insert(0, 
                f"URGENT: Address {len(critical_violations)} critical violations immediately"
            )
        
        if high_violations:
            recommendations.insert(1 if critical_violations else 0,
                f"HIGH PRIORITY: Resolve {len(high_violations)} high-severity issues"
            )
        
        # Deduplicate recommendations
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:10]  # Return top 10 recommendations
