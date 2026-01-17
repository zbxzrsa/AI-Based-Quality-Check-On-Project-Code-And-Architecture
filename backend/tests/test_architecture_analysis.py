"""
Pytest template for testing Architecture Analysis endpoint

Tests the complete flow: Python file input → AST parsing → Neo4j node creation → API response
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from httpx import AsyncClient

from app.main import app
from app.database.postgresql import get_db
from app.core.config import settings


# Sample Python code for testing
SAMPLE_PYTHON_CODE = '''
"""Sample Python module for architecture analysis"""

import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class User:
    """User data class"""
    id: int
    name: str
    email: str

class UserService:
    """Service layer for user operations"""

    def __init__(self):
        self.users = {}

    def create_user(self, name: str, email: str) -> User:
        """Create a new user"""
        user_id = len(self.users) + 1
        user = User(id=user_id, name=name, email=email)
        self.users[user_id] = user
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)

    def list_users(self) -> List[User]:
        """List all users"""
        return list(self.users.values())

class UserController:
    """Controller layer for user HTTP endpoints"""

    def __init__(self, service: UserService):
        self.service = service

    def create_user_endpoint(self, name: str, email: str) -> Dict:
        """HTTP endpoint for creating users"""
        try:
            user = self.service.create_user(name, email)
            return {
                "status": "success",
                "data": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_user_endpoint(self, user_id: int) -> Dict:
        """HTTP endpoint for getting users"""
        user = self.service.get_user(user_id)
        if user:
            return {
                "status": "success",
                "data": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                }
            }
        return {"status": "error", "message": "User not found"}

def main():
    """Main application entry point"""
    service = UserService()
    controller = UserController(service)

    # Example usage
    result = controller.create_user_endpoint("John Doe", "john@example.com")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j session for testing"""
    session = AsyncMock()

    # Mock successful query execution
    mock_result = AsyncMock()
    mock_result.data.return_value = [
        {"module": "user_service", "nodes_created": 5, "relationships_created": 8},
        {"module": "user_controller", "nodes_created": 3, "relationships_created": 4}
    ]
    mock_result.single.return_value = {"count": 12}

    session.run.return_value = mock_result
    session.execute_query.return_value = ([], mock_result)
    session.execute_write.return_value = None

    return session


@pytest.fixture
def mock_neo4j_driver(mock_neo4j_session):
    """Mock Neo4j driver"""
    driver = AsyncMock()
    driver.session.return_value = mock_neo4j_session
    driver.verify_connectivity.return_value = None
    return driver


@pytest.fixture
async def client():
    """Test client with mocked dependencies"""
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    # Mock Neo4j driver
    with patch('app.database.neo4j_db.get_neo4j_driver') as mock_get_driver:
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Mock query results
        mock_result = AsyncMock()
        mock_result.data.return_value = [
            {
                "module": "test_module",
                "classes": ["UserService", "UserController"],
                "functions": ["create_user", "get_user"],
                "imports": ["os", "sys", "typing"]
            }
        ]
        mock_result.single.return_value = {"nodes_created": 8, "relationships_created": 12}

        mock_session.run.return_value = mock_result
        mock_session.execute_query.return_value = ([], mock_result)
        mock_driver.session.return_value = mock_session

        mock_get_driver.return_value = mock_driver

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


class TestArchitectureAnalysisAPI:
    """Test suite for Architecture Analysis endpoint"""

    def test_endpoint_accepts_valid_request(self, client):
        """Test that endpoint accepts valid Python code input"""
        request_data = {
            "project_id": "test-project-123",
            "files": [
                {
                    "filename": "user_service.py",
                    "content": SAMPLE_PYTHON_CODE,
                    "language": "python"
                }
            ],
            "analysis_options": {
                "include_dependencies": True,
                "detect_cycles": True,
                "layer_analysis": True
            }
        }

        response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)

        # Should return 202 Accepted with task_id
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] == "PENDING"

    def test_endpoint_validates_required_fields(self, client):
        """Test endpoint validation for required fields"""
        # Missing project_id
        request_data = {
            "files": [{"filename": "test.py", "content": "print('hello')"}]
        }

        response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_endpoint_handles_empty_files(self, client):
        """Test endpoint handles empty file list"""
        request_data = {
            "project_id": "test-project-123",
            "files": [],
            "analysis_options": {"include_dependencies": True}
        }

        response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)
        assert response.status_code == 400
        assert "files" in response.json()["detail"].lower()

    def test_task_status_endpoint(self, client):
        """Test task status checking endpoint"""
        # First create a task
        request_data = {
            "project_id": "test-project-123",
            "files": [{"filename": "test.py", "content": "print('hello')"}]
        }

        create_response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)
        task_id = create_response.json()["task_id"]

        # Check status
        status_response = client.get(f"/api/v1/analysis/{task_id}/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert "status" in status_data
        assert "task_id" in status_data

    def test_reanalyze_endpoint(self, client):
        """Test PR reanalysis endpoint"""
        pr_data = {
            "pr_number": 123,
            "branch": "feature/new-feature",
            "files_changed": ["user_service.py", "user_controller.py"]
        }

        response = client.post("/api/v1/analysis/projects/test-project-123/pull-requests/123/reanalyze", json=pr_data)

        # Should return task_id for reanalysis
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data


class TestASTParsingIntegration:
    """Test AST parsing and Neo4j integration"""

    @patch('app.services.parsers.python_parser.PythonASTParser.parse_file')
    @patch('app.database.neo4j_db.get_neo4j_driver')
    def test_ast_parser_creates_correct_nodes(self, mock_get_driver, mock_parse_file):
        """Test that AST parser creates correct Neo4j nodes"""
        from app.services.parsers.python_parser import PythonASTParser
        from app.services.neo4j_ast_service_extended import Neo4jASTService

        # Mock AST parser response
        mock_ast_result = MagicMock()
        mock_ast_result.module.name = "user_service"
        mock_ast_result.module.classes = [
            MagicMock(name="UserService", methods=["create_user", "get_user"]),
            MagicMock(name="UserController", methods=["create_user_endpoint"])
        ]
        mock_ast_result.module.functions = [
            MagicMock(name="main", is_async=False)
        ]
        mock_ast_result.module.imports = [
            MagicMock(module_name="os"),
            MagicMock(module_name="sys"),
            MagicMock(module_name="typing")
        ]
        mock_parse_file.return_value = mock_ast_result

        # Mock Neo4j driver
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock node creation results
        mock_result.single.side_effect = [
            {"count": 1},  # Module node
            {"count": 1},  # UserService class
            {"count": 1},  # UserController class
            {"count": 2},  # Methods created
            {"count": 1},  # Function created
            {"count": 3},  # Imports created
        ]

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value = mock_session
        mock_get_driver.return_value = mock_driver

        # Test the integration
        parser = PythonASTParser()
        neo4j_service = Neo4jASTService(mock_driver)

        # Parse the sample code
        ast_result = parser.parse_file("user_service.py", content=SAMPLE_PYTHON_CODE)

        # Create nodes in Neo4j
        import asyncio
        async def test_node_creation():
            module_count = await neo4j_service.create_module_node(ast_result.module)
            class_count = 0
            for cls in ast_result.module.classes:
                class_count += await neo4j_service.create_class_node(cls, "user_service.py")
            function_count = 0
            for func in ast_result.module.functions:
                function_count += await neo4j_service.create_function_node(func, "user_service.py")
            import_count = 0
            for imp in ast_result.module.imports:
                import_count += await neo4j_service.create_import_node(imp, "user_service.py")

            # Verify correct number of nodes created
            assert module_count == 1
            assert class_count == 2  # UserService + UserController
            assert function_count == 1  # main function
            assert import_count == 3  # os, sys, typing

        asyncio.run(test_node_creation())

    def test_cyclic_dependency_detection(self, mock_neo4j_driver):
        """Test cyclic dependency detection in parsed AST"""
        from app.services.cypher_queries import CYCLIC_DEPENDENCY_QUERY
        from app.services.neo4j_ast_service_extended import Neo4jASTService

        neo4j_service = Neo4jASTService(mock_neo4j_driver)

        # Test the query execution
        import asyncio

        async def test_cycle_detection():
            results = await neo4j_service.run_query(CYCLIC_DEPENDENCY_QUERY, projectId="test-project")

            # Should return cycle data
            assert isinstance(results, list)
            # Results would contain cycle information if any exist

        asyncio.run(test_cycle_detection())


class TestErrorHandling:
    """Test error handling in architecture analysis"""

    def test_invalid_python_syntax(self, client):
        """Test handling of invalid Python syntax"""
        request_data = {
            "project_id": "test-project-123",
            "files": [
                {
                    "filename": "invalid.py",
                    "content": "def broken function(:\n    invalid syntax here",
                    "language": "python"
                }
            ]
        }

        response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)

        # Should handle gracefully or return appropriate error
        # Either 202 (accepted but will fail) or 400 (validation error)
        assert response.status_code in [202, 400]

    def test_neo4j_connection_failure(self, client):
        """Test handling of Neo4j connection failures"""
        with patch('app.database.neo4j_db.get_neo4j_driver') as mock_get_driver:
            from neo4j.exceptions import ServiceUnavailable
            mock_get_driver.side_effect = ServiceUnavailable("Connection refused")

            request_data = {
                "project_id": "test-project-123",
                "files": [{"filename": "test.py", "content": "print('hello')"}]
            }

            response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)

            # Should still accept the request but task will fail
            assert response.status_code == 202

    def test_large_file_handling(self, client):
        """Test handling of large Python files"""
        large_code = "print('line')\n" * 10000  # 10k lines

        request_data = {
            "project_id": "test-project-123",
            "files": [
                {
                    "filename": "large.py",
                    "content": large_code,
                    "language": "python"
                }
            ]
        }

        response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)

        # Should handle large files appropriately
        assert response.status_code in [202, 413]  # Accepted or too large


class TestPerformance:
    """Performance tests for architecture analysis"""

    def test_analysis_completes_within_timeout(self, client):
        """Ensure analysis completes within reasonable time"""
        import time

        request_data = {
            "project_id": "test-project-123",
            "files": [
                {
                    "filename": "user_service.py",
                    "content": SAMPLE_PYTHON_CODE,
                    "language": "python"
                }
            ]
        }

        start_time = time.time()
        response = client.post("/api/v1/analysis/projects/test-project-123/analyze", json=request_data)
        end_time = time.time()

        # API call should be fast (< 100ms)
        assert end_time - start_time < 0.1
        assert response.status_code == 202


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
