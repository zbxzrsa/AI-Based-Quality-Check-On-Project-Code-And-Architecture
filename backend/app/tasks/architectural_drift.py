"""
Architectural drift detection tasks
Detects cyclic dependencies, layer violations, and other drift patterns
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.celery_config import celery_app
from app.database.neo4j_db import get_neo4j_driver
from app.services.neo4j_ast_service import Neo4jASTService
from app.services.architectural_drift_detector import ArchitecturalDriftDetector
from app.database.postgresql import AsyncSessionLocal
from app.models import Project
from sqlalchemy import select


@celery_app.task(
    bind=True,
    name='app.tasks.detect_architectural_drift',
    max_retries=2,
    queue='low_priority'
)
def detect_architectural_drift(
    self,
    project_id: str,
    baseline_version: str = "latest"
) -> Dict[str, Any]:
    """
    Detect architectural drift in a project
    
    Compares current architecture against baseline to detect:
    - Cyclic dependencies
    - Layer violations
    - Unexpected dependencies
    - Coupling increases
    
    Args:
        project_id: Project ID
        baseline_version: Baseline version to compare against (default: latest)
        
    Returns:
        Dict with drift detection results
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_detect_drift(project_id, baseline_version))
    finally:
        loop.close()


async def _detect_drift(project_id: str, baseline_version: str) -> Dict[str, Any]:
    """Internal async implementation of drift detection"""
    try:
        driver = await get_neo4j_driver()
        neo4j_service = Neo4jASTService(driver)
        
        # Detect cyclic dependencies
        cycles = await detect_cyclic_dependencies_impl(neo4j_service, project_id)
        
        # Detect layer violations
        violations = await detect_layer_violations_impl(neo4j_service, project_id)
        
        # Build drift report
        drift_report = {
            'project_id': project_id,
            'timestamp': datetime.utcnow().isoformat(),
            'baseline_version': baseline_version,
            'cyclic_dependencies': cycles,
            'layer_violations': violations,
            'total_issues': len(cycles) + len(violations),
            'status': 'completed'
        }
        
        return drift_report
        
    except Exception as e:
        print(f"❌ Error detecting drift for project {project_id}: {e}")
        raise


@celery_app.task(
    name='app.tasks.detect_cyclic_dependencies',
    max_retries=1,
    queue='low_priority'
)
def detect_cyclic_dependencies(project_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect cyclic dependencies in module dependency graph
    
    Finds cycles where Module A depends on B, B depends on C, and C depends on A
    
    Args:
        project_id: Project ID
        
    Returns:
        Dict with detected cycles and analysis details
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_detect_cycles(project_id))
    finally:
        loop.close()


async def detect_cyclic_dependencies_impl(
    neo4j_service: Neo4jASTService,
    project_id: str
) -> List[Dict[str, Any]]:
    """
    Internal implementation for cyclic dependency detection
    
    Cypher Query Explanation:
    - MATCH (p:Project {projectId: $projectId}) - Find project
    - MATCH path = (m1)-[:DEPENDS_ON*]->(m1) - Find paths that start and end on same node
    - This creates cycles of any length >= 2
    - RETURN with ordering by cycle length for prioritization
    """
    cypher_query = """
    MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
    MATCH path = (m1)-[:DEPENDS_ON*]->(m1)
    WHERE length(path) > 1
    WITH m1, path, relationships(path) as rels
    RETURN m1.name AS module,
           [n IN nodes(path) | n.name] AS cycle_path,
           length(path) AS cycle_length,
           [r IN relationships(path) | type(r)] AS relationship_types,
           [r IN relationships(path) | r.reason] AS dependency_reasons
    ORDER BY cycle_length ASC
    LIMIT 100
    """
    
    try:
        result = await neo4j_service.run_query(cypher_query, projectId=project_id)
        
        cycles = []
        for record in result:
            cycle = {
                'module': record.get('module'),
                'cycle_path': record.get('cycle_path', []),
                'cycle_length': record.get('cycle_length'),
                'dependency_reasons': record.get('dependency_reasons', []),
                'severity': 'critical' if record.get('cycle_length', 0) == 2 else 'high',
                'description': f"Cyclic dependency detected: {' -> '.join(record.get('cycle_path', []))} -> {record.get('module')}"
            }
            cycles.append(cycle)
        
        return cycles
        
    except Exception as e:
        print(f"⚠️  Error in cyclic dependency detection: {e}")
        return []


async def _detect_cycles(project_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Wrapper for cyclic dependency detection"""
    driver = await get_neo4j_driver()
    neo4j_service = Neo4jASTService(driver)
    
    cycles = await detect_cyclic_dependencies_impl(neo4j_service, project_id)
    
    return {
        'project_id': project_id,
        'cycles_found': len(cycles),
        'cycles': cycles,
        'timestamp': datetime.utcnow().isoformat()
    }


@celery_app.task(
    name='app.tasks.detect_layer_violations',
    max_retries=1,
    queue='low_priority'
)
def detect_layer_violations(
    project_id: str,
    layer_definitions: Dict[str, List[str]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect layer violations in architecture
    
    Checks if modules skip intermediate layers, e.g., Controller directly to Repository
    
    Args:
        project_id: Project ID
        layer_definitions: Optional dict defining layer names and their module patterns
                          Default: {'controller': [...], 'service': [...], 'repository': [...]}
                          
    Returns:
        Dict with detected layer violations
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_detect_violations(project_id, layer_definitions))
    finally:
        loop.close()


async def detect_layer_violations_impl(
    neo4j_service: Neo4jASTService,
    project_id: str,
    layer_definitions: Optional[Dict[str, List[str]]] = None
) -> List[Dict[str, Any]]:
    """
    Internal implementation for layer violation detection
    
    Cypher Query Explanation:
    - MATCH (p:Project)-[:CONTAINS]->(m1:Module) - Get all modules
    - MATCH (m1)-[:DEPENDS_ON*2..]->(m3:Module) - Find dependencies with 2+ hops
    - WHERE NOT (m1)-[:DEPENDS_ON]->(m2:Module)-[:DEPENDS_ON]->(m3) 
    - This checks that there's NO intermediate layer (service)
    - If this WHERE clause succeeds, it means layer was violated (skipped)
    """
    
    # Default layer detection based on naming conventions
    if not layer_definitions:
        layer_definitions = {
            'controller': ['*controller*', '*handler*'],
            'service': ['*service*', '*business*'],
            'repository': ['*repository*', '*dao*', '*model*']
        }
    
    cypher_query = """
    MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
    MATCH (m1)-[d1:DEPENDS_ON]->(m2:Module)
    MATCH (m2)-[d2:DEPENDS_ON]->(m3:Module)
    MATCH (m3)-[:DEPENDS_ON]->(m4:Module)
    
    // Check for direct controller -> repository connection (skipping service)
    WHERE (toLower(m1.name) CONTAINS 'controller' OR toLower(m1.type) CONTAINS 'controller')
    AND (toLower(m3.name) CONTAINS 'repository' OR toLower(m3.type) CONTAINS 'repository')
    
    // Verify there's no intermediate service layer
    AND NOT EXISTS {
        MATCH (m1)-[:DEPENDS_ON]->(svc:Module)
        WHERE (toLower(svc.name) CONTAINS 'service' OR toLower(svc.type) CONTAINS 'service')
        AND (svc)-[:DEPENDS_ON]->(m3)
    }
    
    RETURN DISTINCT
        m1.name AS source_module,
        m1.type AS source_type,
        m3.name AS target_module,
        m3.type AS target_type,
        [n IN nodes([m1, m2, m3, m4]) | n.name] AS violation_path,
        [r IN relationships([d1, d2]) | r.reason] AS reasons
    LIMIT 50
    """
    
    try:
        result = await neo4j_service.run_query(cypher_query, projectId=project_id)
        
        violations = []
        for record in result:
            violation = {
                'source_module': record.get('source_module'),
                'source_type': record.get('source_type', 'Unknown'),
                'target_module': record.get('target_module'),
                'target_type': record.get('target_type', 'Unknown'),
                'violation_path': record.get('violation_path', []),
                'violation_type': 'layer_skip',
                'severity': 'high',
                'description': f"Layer violation: {record.get('source_module')} (Controller) bypasses Service layer and directly depends on {record.get('target_module')} (Repository)",
                'recommendation': 'Add intermediate Service layer to maintain proper architecture layers'
            }
            violations.append(violation)
        
        return violations
        
    except Exception as e:
        print(f"⚠️  Error in layer violation detection: {e}")
        return []


async def _detect_violations(
    project_id: str,
    layer_definitions: Optional[Dict[str, List[str]]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Wrapper for layer violation detection"""
    driver = await get_neo4j_driver()
    neo4j_service = Neo4jASTService(driver)

    violations = await detect_layer_violations_impl(neo4j_service, project_id, layer_definitions)

    return {
        'project_id': project_id,
        'violations_found': len(violations),
        'violations': violations,
        'timestamp': datetime.utcnow().isoformat()
    }


@celery_app.task(
    bind=True,
    name='app.tasks.detect_golden_standard_drift',
    max_retries=2,
    queue='high_priority'
)
def detect_golden_standard_drift(
    self,
    project_id: str,
    repo_full_name: Optional[str] = None,
    commit_sha: Optional[str] = None,
    golden_standard_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect architectural drift against golden standard schema

    This task:
    1. Compares current Neo4j AST graph against golden standard
    2. Identifies layer violations and cyclic dependencies
    3. Generates drift alerts and calculates drift score
    4. Updates GitHub status check if repo/commit provided
    5. Fails CI if drift exceeds thresholds

    Args:
        project_id: Project identifier
        repo_full_name: Optional GitHub repository full name for status updates
        commit_sha: Optional commit SHA for status updates
        golden_standard_path: Optional path to custom golden standard JSON

    Returns:
        Comprehensive drift analysis report
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_detect_golden_standard_drift(
            project_id, repo_full_name, commit_sha, golden_standard_path, self
        ))
    finally:
        loop.close()


async def _detect_golden_standard_drift(
    project_id: str,
    repo_full_name: Optional[str],
    commit_sha: Optional[str],
    golden_standard_path: Optional[str],
    task
) -> Dict[str, Any]:
    """Internal async implementation of golden standard drift detection"""
    try:
        # Initialize drift detector
        detector = ArchitecturalDriftDetector(golden_standard_path)

        # Run drift detection first
        drift_report = await detector.detect_drift(project_id)

        if drift_report.get("status") == "failed":
            print(f"❌ Drift analysis failed: {drift_report.get('error')}")
            return drift_report

        # Generate alerts
        alerts = await detector.generate_drift_alerts(drift_report)
        drift_report["alerts"] = alerts

        # Check if CI should fail
        should_fail, reason = await detector.should_fail_ci(drift_report)
        drift_report["should_fail_ci"] = should_fail
        drift_report["failure_reason"] = reason

        # Check if we should fail the CI
        should_fail = drift_report.get("should_fail_ci", False)
        if should_fail:
            failure_reason = drift_report.get("failure_reason", "Architectural drift exceeds thresholds")
            print(f"🚨 CI will fail: {failure_reason}")

            # Retry with exponential backoff if this is a recoverable error
            if "connection" in failure_reason.lower() or "timeout" in failure_reason.lower():
                raise task.retry(exc=Exception(failure_reason), countdown=60)
            else:
                # For architectural violations, don't retry - fail immediately
                raise Exception(failure_reason)

        return drift_report

    except Exception as e:
        print(f"❌ Error in golden standard drift detection for project {project_id}: {e}")

        # Create error result
        error_result = {
            "project_id": project_id,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "should_fail_ci": True,
            "failure_reason": f"Drift detection failed: {str(e)}"
        }

        # Still try to update GitHub status if possible
        if repo_full_name and commit_sha:
            try:
                detector = ArchitecturalDriftDetector(golden_standard_path)
                await detector.update_github_status(
                    repo_full_name=repo_full_name,
                    commit_sha=commit_sha,
                    drift_report={"drift_score": 100, "violation_counts": {"critical": 1}},
                    context="architectural-drift"
                )
            except Exception as status_error:
                print(f"⚠️  Failed to update GitHub status: {status_error}")

        raise


def detect_golden_standard_drift_sync(
    project_id: str,
    repo_full_name: Optional[str] = None,
    commit_sha: Optional[str] = None,
    golden_standard_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for golden standard drift detection

    Use this to queue the drift detection task without waiting for results

    Args:
        project_id: Project identifier
        repo_full_name: Optional GitHub repository full name
        commit_sha: Optional commit SHA
        golden_standard_path: Optional path to golden standard JSON

    Returns:
        Task info with task_id for polling
    """
    task = detect_golden_standard_drift.apply_async(
        args=[project_id, repo_full_name, commit_sha, golden_standard_path],
        queue='high_priority',
        expires=1800  # 30 minutes
    )

    return {
        'task_id': task.id,
        'status': 'PENDING',
        'project_id': project_id,
        'message': 'Architectural drift analysis queued and will begin shortly'
    }
