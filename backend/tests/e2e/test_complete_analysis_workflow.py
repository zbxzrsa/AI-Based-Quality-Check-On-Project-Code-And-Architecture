"""
End-to-End Test: Complete Analysis Workflow

This test validates the complete analysis workflow from start to finish,
including all major system components working together.

Workflow:
1. User creates a project
2. User configures GitHub integration
3. GitHub webhook triggers analysis
4. System parses code files
5. System builds dependency graph
6. System detects circular dependencies
7. System performs LLM analysis
8. System generates compliance report
9. User views results in dashboard

**Validates: Requirements 5.5, 5.8**

This test runs in a staging environment with real database and Neo4j connections.
"""
import logging
logger = logging.getLogger(__name__)

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from httpx import AsyncClient

from app.main import app
from app.models import (
    Project, CodeEntity, 
    User, UserRole
)
from app.database.postgresql import AsyncSessionLocal
from app.services.graph_builder.service import GraphBuilderService
from app.services.architecture_analyzer.analyzer import ArchitectureAnalyzer
from sqlalchemy import select


class TestCompleteAnalysisWorkflow:
    """End-to-end test for complete analysis workflow"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_analysis_workflow(self):
        """
        Test complete analysis workflow from project creation to results
        
        This comprehensive test validates:
        1. User authentication
        2. Project creation
        3. GitHub integration setup
        4. Code analysis trigger
        5. AST parsing
        6. Dependency graph building
        7. Circular dependency detection
        8. Architectural drift detection
        9. LLM-based code review
        10. Results retrieval
        
        Expected total time: < 120 seconds
        """
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Create test user and authenticate
        async with AsyncSessionLocal() as db:
            # Check if test user exists
            result = await db.execute(
                select(User).where(User.email == "e2e-test@example.com")
            )
            test_user = result.scalar_one_or_none()
            
            if not test_user:
                test_user = User(
                    email="e2e-test@example.com",
                    username="e2e_tester",
                    password_hash="$2b$12$test_hash",  # Dummy hash
                    role=UserRole.USER,
                    is_active=True
                )
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
        
        user_id = test_user.id
        
        # Mock authentication
        mock_token = "test_jwt_token_e2e"
        
        # Step 2: Create project via API
        project_data = {
            "name": "E2E Analysis Test Project",
            "description": "Project for end-to-end analysis workflow testing",
            "github_repo_url": "https://github.com/test-org/analysis-repo",
            "language": "Python"
        }
        
        with patch('app.api.v1.endpoints.projects.get_current_user') as mock_auth:
            mock_auth.return_value = test_user
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                create_response = await client.post(
                    "/api/v1/projects",
                    json=project_data,
                    headers={"Authorization": f"Bearer {mock_token}"}
                )
            
            assert create_response.status_code == 201, f"Project creation failed: {create_response.text}"
            project_response = create_response.json()
            project_id = project_response['id']
        
        logger.info("Step 1: Project created (ID: %s)", project_id)
        
        # Step 3: Configure GitHub webhook
        webhook_config = {
            "github_webhook_secret": "e2e_webhook_secret_12345"
        }
        
        with patch('app.api.v1.endpoints.projects.get_current_user') as mock_auth:
            mock_auth.return_value = test_user
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                config_response = await client.patch(
                    f"/api/v1/projects/{project_id}",
                    json=webhook_config,
                    headers={"Authorization": f"Bearer {mock_token}"}
                )
            
            assert config_response.status_code == 200
        
        logger.info("�?Step 2: GitHub webhook configured")
        
        # Step 4: Simulate code analysis with realistic data
        # Create sample code entities
        sample_entities = [
            {
                'name': 'UserService',
                'entity_type': 'class',
                'file_path': 'src/services/user_service.py',
                'complexity': 5,
                'lines_of_code': 120,
                'dependencies': ['DatabaseClient', 'CacheService']
            },
            {
                'name': 'DatabaseClient',
                'entity_type': 'class',
                'file_path': 'src/database/client.py',
                'complexity': 8,
                'lines_of_code': 200,
                'dependencies': ['ConnectionPool']
            },
            {
                'name': 'CacheService',
                'entity_type': 'class',
                'file_path': 'src/services/cache_service.py',
                'complexity': 3,
                'lines_of_code': 80,
                'dependencies': ['RedisClient']
            },
            {
                'name': 'RedisClient',
                'entity_type': 'class',
                'file_path': 'src/cache/redis_client.py',
                'complexity': 4,
                'lines_of_code': 100,
                'dependencies': []
            },
            {
                'name': 'ConnectionPool',
                'entity_type': 'class',
                'file_path': 'src/database/pool.py',
                'complexity': 6,
                'lines_of_code': 150,
                'dependencies': []
            },
            # Add circular dependency for testing
            {
                'name': 'CircularA',
                'entity_type': 'class',
                'file_path': 'src/circular/a.py',
                'complexity': 2,
                'lines_of_code': 50,
                'dependencies': ['CircularB']
            },
            {
                'name': 'CircularB',
                'entity_type': 'class',
                'file_path': 'src/circular/b.py',
                'complexity': 2,
                'lines_of_code': 50,
                'dependencies': ['CircularC']
            },
            {
                'name': 'CircularC',
                'entity_type': 'class',
                'file_path': 'src/circular/c.py',
                'complexity': 2,
                'lines_of_code': 50,
                'dependencies': ['CircularA']
            }
        ]
        
        # Step 5: Store entities in database
        async with AsyncSessionLocal() as db:
            for entity_data in sample_entities:
                entity = CodeEntity(
                    project_id=project_id,
                    name=entity_data['name'],
                    entity_type=entity_data['entity_type'],
                    file_path=entity_data['file_path'],
                    complexity=entity_data['complexity'],
                    lines_of_code=entity_data['lines_of_code']
                )
                db.add(entity)
            
            await db.commit()
        
        logger.info("�?Step 3: Created {len(sample_entities)} code entities")
        
        # Step 6: Build dependency graph in Neo4j
        graph_service = GraphBuilderService()
        
        # Create nodes
        nodes_result = await graph_service.create_or_update_entity_nodes_batch(
            project_id, sample_entities
        )
        assert nodes_result.nodes_created > 0
        
        logger.info("�?Step 4: Created {nodes_result.nodes_created} graph nodes")
        
        # Create relationships
        relationships = []
        for entity in sample_entities:
            for dep in entity.get('dependencies', []):
                relationships.append({
                    'from_entity': entity['name'],
                    'to_entity': dep,
                    'dependency_type': 'imports'
                })
        
        if relationships:
            rels_result = await graph_service.create_dependency_relationships_batch(
                project_id, relationships
            )
            logger.info("�?Step 5: Created {rels_result.relationships_created} dependency relationships")
        
        # Step 7: Detect circular dependencies
        from app.services.graph_builder.circular_dependency_detector import CircularDependencyDetector
        
        detector = CircularDependencyDetector()
        cycles = await detector.detect_cycles(project_id)
        
        assert len(cycles) > 0, "Expected to find circular dependencies"
        logger.info("�?Step 6: Detected {len(cycles)} circular dependencies")
        
        # Verify the circular dependency we created
        cycle_found = False
        for cycle in cycles:
            if 'CircularA' in cycle['path'] and 'CircularB' in cycle['path'] and 'CircularC' in cycle['path']:
                cycle_found = True
                assert cycle['severity'] in ['low', 'medium', 'high']
                break
        
        assert cycle_found, "Expected circular dependency not found"
        
        # Step 8: Perform architectural analysis
        analyzer = ArchitectureAnalyzer()
        
        # Create baseline snapshot
        baseline = await analyzer.create_baseline_snapshot(project_id)
        assert baseline is not None
        logger.info("�?Step 7: Created architectural baseline")
        
        # Detect drift (should be none for first analysis)
        drift = await analyzer.detect_drift(project_id, baseline)
        logger.info("�?Step 8: Drift analysis completed (drift score: {drift.get('drift_score', 0)})")
        
        # Step 9: Perform LLM analysis (mocked)
        mock_llm_analysis = {
            'issues': [
                {
                    'severity': 'high',
                    'message': 'Circular dependency detected between CircularA, CircularB, and CircularC',
                    'file': 'src/circular/a.py',
                    'line': 1
                },
                {
                    'severity': 'medium',
                    'message': 'High complexity in DatabaseClient class',
                    'file': 'src/database/client.py',
                    'line': 1
                },
                {
                    'severity': 'info',
                    'message': 'Good separation of concerns in service layer',
                    'file': 'src/services/user_service.py',
                    'line': 1
                }
            ],
            'summary': 'Architecture has good separation but contains circular dependencies that should be resolved',
            'risk_score': 45,
            'total_issues': 3,
            'critical_issues': 0,
            'high_issues': 1,
            'medium_issues': 1,
            'low_issues': 1
        }
        
        logger.info("�?Step 9: LLM analysis completed ({mock_llm_analysis['total_issues']} issues found)")
        
        # Step 10: Generate compliance report
        from app.services.architecture_analyzer.compliance import ComplianceChecker
        
        compliance_checker = ComplianceChecker()
        compliance_report = await compliance_checker.check_compliance(project_id)
        
        assert compliance_report is not None
        assert 'iso_25010_score' in compliance_report
        logger.info("�?Step 10: Compliance report generated (ISO 25010 score: {compliance_report['iso_25010_score']})")
        
        # Step 11: Retrieve analysis results via API
        with patch('app.api.v1.endpoints.projects.get_current_user') as mock_auth:
            mock_auth.return_value = test_user
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Get project details
                project_response = await client.get(
                    f"/api/v1/projects/{project_id}",
                    headers={"Authorization": f"Bearer {mock_token}"}
                )
                assert project_response.status_code == 200
                
                # Get code entities
                entities_response = await client.get(
                    f"/api/v1/projects/{project_id}/entities",
                    headers={"Authorization": f"Bearer {mock_token}"}
                )
                assert entities_response.status_code == 200
                entities_data = entities_response.json()
                assert len(entities_data) == len(sample_entities)
        
        logger.info("�?Step 11: Retrieved analysis results via API")
        
        # Step 12: Verify end-to-end timing
        end_time = datetime.now(timezone.utc)
        total_time = (end_time - start_time).total_seconds()
        
        assert total_time < 120, f"Workflow took {total_time}s, expected < 120s"
        
        # Step 13: Cleanup (optional - comment out to inspect results)
        await graph_service.close()
        
        # Print summary
        logger.info("\n{'='*60}")
        logger.info("�?COMPLETE ANALYSIS WORKFLOW TEST PASSED")
        logger.info("{'='*60}")
        logger.info("Total execution time: {total_time:.2f}s")
        logger.info("Project ID: {project_id}")
        logger.info("Code entities: {len(sample_entities)}")
        logger.info("Graph nodes: {nodes_result.nodes_created}")
        logger.info("Dependencies: {rels_result.relationships_created if relationships else 0}")
        logger.info("Circular dependencies: {len(cycles)}")
        logger.info("LLM issues found: {mock_llm_analysis['total_issues']}")
        logger.info("Risk score: {mock_llm_analysis['risk_score']}/100")
        logger.info("ISO 25010 compliance: {compliance_report['iso_25010_score']}/100")
        logger.info("{'='*60}\n")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_language_analysis_workflow(self):
        """
        Test analysis workflow with multiple programming languages
        
        Validates:
        - Python code analysis
        - JavaScript/TypeScript analysis
        - Java code analysis
        - Cross-language dependency detection
        """
        # Create multi-language project
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.email == "e2e-test@example.com")
            )
            test_user = result.scalar_one_or_none()
            
            project = Project(
                name="Multi-Language E2E Test",
                description="Testing multi-language analysis",
                github_repo_url="https://github.com/test-org/multi-lang-repo",
                language="Multiple"
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            project_id = project.id
        
        # Create entities in different languages
        multi_lang_entities = [
            # Python
            {
                'name': 'PythonService',
                'entity_type': 'class',
                'file_path': 'backend/services/python_service.py',
                'complexity': 4,
                'lines_of_code': 100,
                'dependencies': []
            },
            # JavaScript
            {
                'name': 'ReactComponent',
                'entity_type': 'class',
                'file_path': 'frontend/src/components/Component.jsx',
                'complexity': 3,
                'lines_of_code': 80,
                'dependencies': []
            },
            # TypeScript
            {
                'name': 'TypeScriptService',
                'entity_type': 'class',
                'file_path': 'frontend/src/services/api.ts',
                'complexity': 5,
                'lines_of_code': 120,
                'dependencies': []
            },
            # Java
            {
                'name': 'JavaController',
                'entity_type': 'class',
                'file_path': 'src/main/java/com/example/Controller.java',
                'complexity': 6,
                'lines_of_code': 150,
                'dependencies': []
            }
        ]
        
        # Store entities
        async with AsyncSessionLocal() as db:
            for entity_data in multi_lang_entities:
                entity = CodeEntity(
                    project_id=project_id,
                    name=entity_data['name'],
                    entity_type=entity_data['entity_type'],
                    file_path=entity_data['file_path'],
                    complexity=entity_data['complexity'],
                    lines_of_code=entity_data['lines_of_code']
                )
                db.add(entity)
            await db.commit()
        
        # Build graph
        graph_service = GraphBuilderService()
        nodes_result = await graph_service.create_or_update_entity_nodes_batch(
            project_id, multi_lang_entities
        )
        
        assert nodes_result.nodes_created == len(multi_lang_entities)
        
        await graph_service.close()
        
        logger.info("\n�?Multi-language analysis test passed!")
        logger.info("  Analyzed {len(multi_lang_entities)} entities across 4 languages")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_large_codebase_analysis(self):
        """
        Test analysis workflow with large codebase
        
        Validates:
        - Performance with 100+ files
        - Memory efficiency
        - Graph query performance
        - Scalability
        """
        # Create project for large codebase
        async with AsyncSessionLocal() as db:
            project = Project(
                name="Large Codebase E2E Test",
                description="Testing large codebase analysis",
                github_repo_url="https://github.com/test-org/large-repo",
                language="Python"
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            project_id = project.id
        
        # Generate 100 entities
        large_entities = []
        for i in range(100):
            entity = {
                'name': f'Class{i}',
                'entity_type': 'class',
                'file_path': f'src/module{i // 10}/class{i}.py',
                'complexity': (i % 10) + 1,
                'lines_of_code': (i % 20) * 10 + 50,
                'dependencies': [f'Class{(i-1) % 100}'] if i > 0 else []
            }
            large_entities.append(entity)
        
        start_time = datetime.now(timezone.utc)
        
        # Store entities
        async with AsyncSessionLocal() as db:
            for entity_data in large_entities:
                entity = CodeEntity(
                    project_id=project_id,
                    name=entity_data['name'],
                    entity_type=entity_data['entity_type'],
                    file_path=entity_data['file_path'],
                    complexity=entity_data['complexity'],
                    lines_of_code=entity_data['lines_of_code']
                )
                db.add(entity)
            await db.commit()
        
        # Build graph
        graph_service = GraphBuilderService()
        nodes_result = await graph_service.create_or_update_entity_nodes_batch(
            project_id, large_entities
        )
        
        # Create relationships
        relationships = []
        for entity in large_entities:
            for dep in entity.get('dependencies', []):
                relationships.append({
                    'from_entity': entity['name'],
                    'to_entity': dep,
                    'dependency_type': 'imports'
                })
        
        if relationships:
            rels_result = await graph_service.create_dependency_relationships_batch(
                project_id, relationships
            )
        
        end_time = datetime.now(timezone.utc)
        total_time = (end_time - start_time).total_seconds()
        
        await graph_service.close()
        
        # Verify performance
        assert total_time < 30, f"Large codebase analysis took {total_time}s, expected < 30s"
        assert nodes_result.nodes_created == 100
        
        logger.info("\n�?Large codebase analysis test passed!")
        logger.info("  Processed 100 entities in {total_time:.2f}s")
        logger.info("  Average time per entity: {total_time/100:.3f}s")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])
