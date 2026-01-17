"""
Architectural Drift Detection Service
Compares current Neo4j AST graph against Golden Standard Architecture Schema
Generates drift alerts and GitHub status check failures when violations exceed thresholds
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import fnmatch

from app.database.neo4j_db import get_neo4j_driver
from app.services.neo4j_ast_service import Neo4jASTService
from app.services.github_client import get_github_client
from app.core.config import settings


class ArchitecturalDriftDetector:
    """
    Detects architectural drift by comparing current code structure
    against a predefined golden standard architecture schema.
    """

    def __init__(self, golden_standard_path: Optional[str] = None):
        """
        Initialize the drift detector with golden standard schema

        Args:
            golden_standard_path: Path to golden standard JSON file
        """
        self.golden_standard_path = golden_standard_path or str(
            Path(__file__).parent / "architecture_golden_standard.json"
        )
        self.golden_standard = self._load_golden_standard()

    def _load_golden_standard(self) -> Dict[str, Any]:
        """Load the golden standard architecture schema"""
        try:
            with open(self.golden_standard_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Golden standard file not found: {self.golden_standard_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in golden standard file: {e}")

    def _classify_file_layer(self, file_path: str, file_name: str) -> Optional[str]:
        """
        Classify a file into its architectural layer based on patterns

        Args:
            file_path: Full file path
            file_name: File name (without path)

        Returns:
            Layer name or None if unclassified
        """
        file_name_lower = file_name.lower()

        for layer_name, layer_config in self.golden_standard["layers"].items():
            patterns = layer_config.get("file_patterns", [])

            # Check file name patterns
            for pattern in patterns:
                if fnmatch.fnmatch(file_name_lower, f"*{pattern}*"):
                    return layer_name

            # Check path patterns (for directories)
            file_path_lower = file_path.lower()
            for pattern in patterns:
                if pattern in file_path_lower:
                    return layer_name

        return None

    def _is_dependency_allowed(self, source_layer: str, target_layer: str) -> Tuple[bool, str]:
        """
        Check if a dependency between layers is allowed

        Args:
            source_layer: Source architectural layer
            target_layer: Target architectural layer

        Returns:
            Tuple of (is_allowed, reason)
        """
        if source_layer not in self.golden_standard["layers"]:
            return True, "Source layer not defined in golden standard"

        if target_layer not in self.golden_standard["layers"]:
            return True, "Target layer not defined in golden standard"

        source_config = self.golden_standard["layers"][source_layer]
        allowed_deps = source_config.get("allowed_dependencies", [])
        forbidden_deps = source_config.get("forbidden_dependencies", [])

        # Check forbidden dependencies first
        if target_layer in forbidden_deps:
            return False, f"Layer '{source_layer}' is forbidden from depending on '{target_layer}'"

        # Check allowed dependencies
        if target_layer not in allowed_deps:
            return False, f"Layer '{source_layer}' may only depend on: {', '.join(allowed_deps)}"

        return True, "Dependency allowed"

    async def _execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        driver = await get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, parameters if parameters is not None else {})
            records = await result.data()
            return records

    async def detect_drift(self, project_id: str) -> Dict[str, Any]:
        """
        Detect architectural drift by comparing current graph against golden standard

        Args:
            project_id: Project identifier

        Returns:
            Comprehensive drift report
        """
        drift_report = {
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "golden_standard_version": self.golden_standard.get("version", "unknown"),
            "violations": [],
            "layer_classification": {},
            "drift_score": 0.0,
            "status": "analyzing"
        }

        try:
            # Step 1: Get all files and classify them by layer
            files_query = """
            MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(f:File)
            RETURN f.fileId AS fileId, f.path AS path
            """

            files_result = await self._execute_query(files_query, {"projectId": project_id})

            layer_classification = {}
            for record in files_result:
                file_id = record.get("fileId", "")
                file_path = record.get("path", "")

                if "::" in file_id:
                    file_name = file_id.split("::")[-1]
                else:
                    file_name = file_path.split("/")[-1] if "/" in file_path else file_path

                layer = self._classify_file_layer(file_path, file_name)
                layer_classification[file_id] = {
                    "path": file_path,
                    "layer": layer,
                    "file_name": file_name
                }

            drift_report["layer_classification"] = layer_classification

            # Step 2: Analyze dependencies for layer violations
            dependencies_query = """
            MATCH (p:Project {projectId: $projectId})-[:CONTAINS*]->(source:File)
            MATCH (source)-[dep:DEPENDS_ON]->(target)
            WHERE target:File OR target:Module
            RETURN source.fileId AS sourceFile,
                   source.path AS sourcePath,
                   target.fileId AS targetFile,
                   target.path AS targetPath,
                   target.moduleId AS targetModule,
                   dep.type AS dependencyType,
                   dep.reason AS dependencyReason
            """

            deps_result = await self._execute_query(dependencies_query, {"projectId": project_id})

            violations = []

            for dep in deps_result:
                source_file = dep.get("sourceFile", "")
                target_file = dep.get("targetFile", "")
                target_module = dep.get("targetModule", "")

                # Classify source layer
                source_layer = layer_classification.get(source_file, {}).get("layer")

                # Classify target layer
                target_layer = None
                if target_file and target_file in layer_classification:
                    target_layer = layer_classification[target_file]["layer"]
                elif target_module:
                    # For module dependencies, try to infer layer from module name
                    target_layer = self._classify_file_layer("", target_module)

                # Skip if we can't classify either layer
                if not source_layer or not target_layer:
                    continue

                # Check if dependency is allowed
                is_allowed, reason = self._is_dependency_allowed(source_layer, target_layer)

                if not is_allowed:
                    violation = {
                        "type": "layer_violation",
                        "severity": "high",
                        "source_file": source_file,
                        "source_layer": source_layer,
                        "target_file": target_file or target_module,
                        "target_layer": target_layer,
                        "dependency_type": dep.get("dependencyType", "unknown"),
                        "reason": reason,
                        "description": f"Architectural violation: {layer_classification.get(source_file, {}).get('path', source_file)} ({source_layer}) illegally depends on {target_file or target_module} ({target_layer})",
                        "recommendation": f"Refactor to maintain layer isolation. {reason}"
                    }
                    violations.append(violation)

            # Step 3: Check for cyclic dependencies (critical violations)
            cycles_query = """
            MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(f1:File)
            MATCH path = (f1)-[:DEPENDS_ON*2..10]->(f1)
            WHERE length(path) > 1
            RETURN f1.fileId AS startFile,
                   [n IN nodes(path) | n.fileId] AS cycleFiles,
                   length(path) AS cycleLength
            LIMIT 20
            """

            cycles_result = await self._execute_query(cycles_query, {"projectId": project_id})

            for cycle in cycles_result:
                violation = {
                    "type": "cyclic_dependency",
                    "severity": "critical",
                    "source_file": cycle.get("startFile"),
                    "cycle_files": cycle.get("cycleFiles", []),
                    "cycle_length": cycle.get("cycleLength", 0),
                    "reason": "Circular dependency detected",
                    "description": f"Critical: Circular dependency involving {len(cycle.get('cycleFiles', []))} files",
                    "recommendation": "Break the circular dependency by introducing an interface or mediator pattern"
                }
                violations.append(violation)

            # Step 4: Calculate drift score and status
            drift_report["violations"] = violations

            # Count violations by severity
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for violation in violations:
                severity = violation.get("severity", "low")
                severity_counts[severity] += 1

            drift_report["violation_counts"] = severity_counts

            # Calculate drift score (0-100, higher = more drift)
            thresholds = self.golden_standard.get("drift_thresholds", {})
            drift_score = 0.0

            if severity_counts["critical"] > thresholds.get("critical_violations", 0):
                drift_score += 100
            elif severity_counts["high"] > thresholds.get("high_violations", 3):
                drift_score += 75
            elif severity_counts["medium"] > thresholds.get("medium_violations", 10):
                drift_score += 50
            elif severity_counts["low"] > thresholds.get("low_violations", 25):
                drift_score += 25

            # Additional scoring based on total violations
            total_violations = sum(severity_counts.values())
            if total_violations > 50:
                drift_score = min(100, drift_score + 25)
            elif total_violations > 25:
                drift_score = min(100, drift_score + 15)
            elif total_violations > 10:
                drift_score = min(100, drift_score + 5)

            drift_report["drift_score"] = drift_score
            drift_report["status"] = "completed"

            return drift_report

        except Exception as e:
            drift_report["status"] = "failed"
            drift_report["error"] = str(e)
            return drift_report

    async def generate_drift_alerts(self, drift_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate formatted drift alerts from the drift report

        Args:
            drift_report: Drift detection report

        Returns:
            List of formatted alert messages
        """
        alerts = []

        violations = drift_report.get("violations", [])
        severity_counts = drift_report.get("violation_counts", {})

        if not violations:
            alerts.append({
                "type": "success",
                "title": "🏗️ Architecture Compliance",
                "message": "✅ No architectural violations detected. Code structure aligns with golden standard.",
                "severity": "success"
            })
            return alerts

        # Critical violations
        critical_violations = [v for v in violations if v.get("severity") == "critical"]
        if critical_violations:
            alerts.append({
                "type": "error",
                "title": "🚨 Critical Architecture Violations",
                "message": f"🚨 {len(critical_violations)} critical violations detected! Immediate refactoring required.",
                "severity": "critical",
                "details": [v.get("description", "") for v in critical_violations[:3]]
            })

        # High violations
        high_violations = [v for v in violations if v.get("severity") == "high"]
        if high_violations:
            alerts.append({
                "type": "warning",
                "title": "⚠️ High Priority Architecture Issues",
                "message": f"⚠️ {len(high_violations)} high-priority violations detected. Layer isolation compromised.",
                "severity": "high",
                "details": [v.get("description", "") for v in high_violations[:3]]
            })

        # Summary
        drift_score = drift_report.get("drift_score", 0)
        if drift_score >= 75:
            status_message = "🔴 Severe architectural drift detected"
        elif drift_score >= 50:
            status_message = "🟠 Moderate architectural drift detected"
        elif drift_score >= 25:
            status_message = "🟡 Minor architectural drift detected"
        else:
            status_message = "🟢 Architecture mostly compliant"

        alerts.append({
            "type": "summary",
            "title": "📊 Architectural Drift Summary",
            "message": f"{status_message} - Score: {drift_score:.1f}/100 - Total violations: {sum(severity_counts.values())}",
            "severity": "info",
            "metrics": severity_counts
        })

        return alerts

    async def should_fail_ci(self, drift_report: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if CI should fail based on drift thresholds

        Args:
            drift_report: Drift detection report

        Returns:
            Tuple of (should_fail, reason)
        """
        severity_counts = drift_report.get("violation_counts", {})
        thresholds = self.golden_standard.get("drift_thresholds", {})

        # Critical violations - always fail
        if severity_counts.get("critical", 0) > thresholds.get("critical_violations", 0):
            return True, f"🚨 {severity_counts['critical']} critical architectural violations exceed threshold"

        # High violations
        if severity_counts.get("high", 0) > thresholds.get("high_violations", 3):
            return True, f"⚠️ {severity_counts['high']} high-priority violations exceed threshold"

        # Drift score too high
        drift_score = drift_report.get("drift_score", 0)
        if drift_score >= 75:
            return True, f"🔴 Architectural drift score ({drift_score:.1f}/100) too high"

        return False, "✅ Architecture within acceptable drift limits"

    async def update_github_status(
        self,
        repo_full_name: str,
        commit_sha: str,
        drift_report: Dict[str, Any],
        context: str = "architectural-drift"
    ) -> bool:
        """
        Update GitHub status check based on drift results

        Args:
            repo_full_name: GitHub repository full name
            commit_sha: Commit SHA to update
            drift_report: Drift detection report
            context: Status check context

        Returns:
            Success status
        """
        try:
            github_client = get_github_client()

            should_fail, reason = await self.should_fail_ci(drift_report)

            severity_counts = drift_report.get("violation_counts", {})
            total_violations = sum(severity_counts.values())
            drift_score = drift_report.get("drift_score", 0)

            description = f"Drift: {drift_score:.1f}/100 - Violations: {total_violations}"

            if len(description) > 140:  # GitHub description limit
                description = f"Drift: {drift_score:.1f}/100 - {total_violations} issues"

            state = "failure" if should_fail else "success"

            await github_client.update_pr_status(
                repo_full_name=repo_full_name,
                commit_sha=commit_sha,
                state=state,
                description=description,
                context=context
            )

            return True

        except Exception as e:
            print(f"❌ Failed to update GitHub status: {e}")
            return False

    async def run_full_drift_analysis(
        self,
        project_id: str,
        repo_full_name: str = None,
        commit_sha: str = None
    ) -> Dict[str, Any]:
        """
        Run complete architectural drift analysis and optionally update GitHub status

        Args:
            project_id: Project identifier
            repo_full_name: Optional GitHub repo for status updates
            commit_sha: Optional commit SHA for status updates

        Returns:
            Complete analysis result
        """
        print(f"🏗️ Starting architectural drift analysis for project {project_id}")

        # Run drift detection
        drift_report = await self.detect_drift(project_id)

        if drift_report.get("status") == "failed":
            print(f"❌ Drift analysis failed: {drift_report.get('error')}")
            return drift_report

        # Generate alerts
        alerts = await self.generate_drift_alerts(drift_report)
        drift_report["alerts"] = alerts

        # Check if CI should fail
        should_fail, reason = await self.should_fail_ci(drift_report)
        drift_report["should_fail_ci"] = should_fail
        drift_report["failure_reason"] = reason

        # Update GitHub status if provided
        if repo_full_name and commit_sha:
            status_updated = await self.update_github_status(
                repo_full_name, commit_sha, drift_report
            )
            drift_report["github_status_updated"] = status_updated

        # Log results
        severity_counts = drift_report.get("violation_counts", {})
        total_violations = sum(severity_counts.values())
        drift_score = drift_report.get("drift_score", 0)

        print(f"📊 Drift Analysis Complete:")
        print(f"   - Total violations: {total_violations}")
        print(f"   - Critical: {severity_counts.get('critical', 0)}")
        print(f"   - High: {severity_counts.get('high', 0)}")
        print(f"   - Drift score: {drift_score:.1f}/100")
        print(f"   - CI {'will fail' if should_fail else 'will pass'}")

        return drift_report
