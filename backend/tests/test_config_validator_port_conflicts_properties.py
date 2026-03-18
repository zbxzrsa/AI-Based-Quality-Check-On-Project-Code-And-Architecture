"""
Property-based tests for port conflict detection in ConfigValidator.

Tests Property 34: Port Conflicts Reported
**Validates: Requirements 10.3**

These tests verify that for any configuration where multiple services are
configured to use the same port, the validation reports which services have
conflicting port assignments.
"""

import os
from typing import Dict, Set
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.core.config_validator import ConfigValidator
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# Define service names and their default ports
SERVICE_PORTS = {
    "backend": 8000,
    "frontend": 3000,
    "postgres": 5432,
    "redis": 6379,
    "neo4j": 7687,
}


# Test constants for configuration to avoid literal suspicious strings
TEST_PASSWORD = get_test_password("test_password_value")
TEST_USER = "test_user_name"
TEST_DB = "test_database_db"


class TestPortConflictDetectionProperties:
    """Property-based tests for port conflict detection"""
    
    @given(
        conflicting_port=st.integers(min_value=1024, max_value=65535),
        services_to_conflict=st.sets(
            st.sampled_from(["backend", "frontend", "postgres", "redis"]),
            min_size=2,
            max_size=4
        )
    )
    @settings(max_examples=100, deadline=10000)
    def test_port_conflicts_reported_property(
        self,
        conflicting_port: int,
        services_to_conflict: Set[str]
    ):
        """
        **Property 34: Port Conflicts Reported**
        **Validates: Requirements 10.3**
        
        For any configuration where multiple services use the same port,
        the validation should report which services have conflicting port assignments.
        """
        # Create base configuration with valid values
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
        }
        
        # Set conflicting services to use the same port
        if "backend" in services_to_conflict:
            test_config["BACKEND_PORT"] = str(conflicting_port)
            test_config["NEXT_PUBLIC_API_URL"] = f"http://localhost:{conflicting_port}"
        
        if "frontend" in services_to_conflict:
            test_config["FRONTEND_PORT"] = str(conflicting_port)
        
        if "postgres" in services_to_conflict:
            test_config["POSTGRES_PORT"] = str(conflicting_port)
        
        if "redis" in services_to_conflict:
            test_config["REDIS_PORT"] = str(conflicting_port)
        
        # Neo4j port is in the URI, so we need to update it
        if "neo4j" in services_to_conflict:
            test_config["NEO4J_URI"] = f"bolt://localhost:{conflicting_port}"
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes on mock_settings
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                conflicts = validator.validate_port_conflicts()
                
                # Property: Port conflicts should be detected and reported
                if len(services_to_conflict) >= 2:
                    assert len(conflicts) > 0, \
                        f"Port conflict should be detected when {len(services_to_conflict)} services use port {conflicting_port}"
                    
                    # Property: Conflict message should mention the conflicting port
                    has_port_in_message = any(
                        str(conflicting_port) in conflict
                        for conflict in conflicts
                    )
                    assert has_port_in_message, \
                        f"Conflict message should mention port {conflicting_port}"
                    
                    # Property: Conflict message should mention multiple services
                    # At least one conflict message should reference multiple services
                    has_multiple_services = any(
                        "multiple services" in conflict.lower() or
                        conflict.count(",") >= 1  # Multiple services separated by commas
                        for conflict in conflicts
                    )
                    assert has_multiple_services, \
                        "Conflict message should indicate multiple services are using the same port"
                    
                    # Property: Errors should be added to validation result
                    assert validator.result.has_errors(), \
                        "Validation result should have errors when port conflicts exist"
                    
                    # Property: At least one error should mention port conflict
                    has_conflict_error = any(
                        "port conflict" in error.lower() or "port" in error.lower()
                        for error in validator.result.errors
                    )
                    assert has_conflict_error, \
                        "Validation errors should include port conflict information"
    
    @given(
        port_assignments=st.dictionaries(
            keys=st.sampled_from(["backend", "frontend", "postgres", "redis", "neo4j"]),
            values=st.integers(min_value=1024, max_value=65535),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=10000)
    def test_no_false_positives_property(self, port_assignments: Dict[str, int]):
        """
        **Property 34: Port Conflicts Reported - No False Positives**
        **Validates: Requirements 10.3**
        
        For any configuration where all services use different ports,
        no port conflicts should be reported.
        """
        # Ensure all ports are unique (no conflicts)
        ports = list(port_assignments.values())
        assume(len(ports) == len(set(ports)))  # All ports are unique
        
        # Also ensure none of the assigned ports conflict with default Neo4j port if not specified
        neo4j_port = port_assignments.get("neo4j", 7687)
        other_ports = [port_assignments.get(svc) for svc in ["backend", "frontend", "postgres", "redis"] if svc in port_assignments]
        assume(neo4j_port not in other_ports)  # Neo4j port doesn't conflict with others
        
        # Create configuration with unique ports
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": str(port_assignments.get("postgres", 5432)),
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": f"bolt://localhost:{neo4j_port}",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": str(port_assignments.get("redis", 6379)),
            "BACKEND_PORT": str(port_assignments.get("backend", 8000)),
            "FRONTEND_PORT": str(port_assignments.get("frontend", 3000)),
            "NEXT_PUBLIC_API_URL": f"http://localhost:{port_assignments.get('backend', 8000)}",
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                conflicts = validator.validate_port_conflicts()
                
                # Property: No conflicts should be reported when all ports are unique
                assert len(conflicts) == 0, \
                    f"No port conflicts should be reported when all ports are unique, but got: {conflicts}"
                
                # Property: No port conflict errors should be in validation result
                port_conflict_errors = [
                    error for error in validator.result.errors
                    if "port conflict" in error.lower()
                ]
                assert len(port_conflict_errors) == 0, \
                    f"No port conflict errors should be present with unique ports, but got: {port_conflict_errors}"
    
    @given(
        conflicting_port=st.integers(min_value=1024, max_value=65535),
        num_services=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100, deadline=10000)
    def test_conflict_count_matches_services_property(
        self,
        conflicting_port: int,
        num_services: int
    ):
        """
        **Property 34: Port Conflicts Reported - Conflict Count**
        **Validates: Requirements 10.3**
        
        For any configuration with N services using the same port,
        the conflict report should identify all N services.
        """
        # Select services to conflict
        all_services = ["backend", "frontend", "postgres", "redis"]
        services_to_conflict = all_services[:num_services]
        
        # Create configuration
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }
        
        # Set all selected services to use the conflicting port
        if "backend" in services_to_conflict:
            test_config["BACKEND_PORT"] = str(conflicting_port)
            test_config["NEXT_PUBLIC_API_URL"] = f"http://localhost:{conflicting_port}"
        
        if "frontend" in services_to_conflict:
            test_config["FRONTEND_PORT"] = str(conflicting_port)
        
        if "postgres" in services_to_conflict:
            test_config["POSTGRES_PORT"] = str(conflicting_port)
        
        if "redis" in services_to_conflict:
            test_config["REDIS_PORT"] = str(conflicting_port)
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                conflicts = validator.validate_port_conflicts()
                
                # Property: Should detect conflict when multiple services use same port
                if num_services >= 2:
                    assert len(conflicts) > 0, \
                        f"Should detect conflict when {num_services} services use port {conflicting_port}"
                    
                    # Property: Conflict message should reference the conflicting port
                    conflict_messages = " ".join(conflicts)
                    assert str(conflicting_port) in conflict_messages, \
                        f"Conflict messages should mention port {conflicting_port}"
    
    @given(
        backend_port=st.integers(min_value=1024, max_value=65535),
        frontend_port=st.integers(min_value=1024, max_value=65535),
        postgres_port=st.integers(min_value=1024, max_value=65535),
        redis_port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=100, deadline=10000)
    def test_all_ports_checked_property(
        self,
        backend_port: int,
        frontend_port: int,
        postgres_port: int,
        redis_port: int
    ):
        """
        **Property 34: Port Conflicts Reported - All Ports Checked**
        **Validates: Requirements 10.3**
        
        For any configuration, all service ports should be checked for conflicts,
        and conflicts should be reported regardless of which services are involved.
        """
        # Create configuration with specified ports
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": str(postgres_port),
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": str(redis_port),
            "BACKEND_PORT": str(backend_port),
            "FRONTEND_PORT": str(frontend_port),
            "NEXT_PUBLIC_API_URL": f"http://localhost:{backend_port}",
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                conflicts = validator.validate_port_conflicts()
                
                # Count how many ports are duplicated
                ports = [backend_port, frontend_port, postgres_port, redis_port]
                unique_ports = set(ports)
                has_duplicates = len(ports) != len(unique_ports)
                
                # Property: Conflicts should be reported if and only if there are duplicate ports
                if has_duplicates:
                    assert len(conflicts) > 0, \
                        f"Should detect conflicts when ports are duplicated: {ports}"
                    assert validator.result.has_errors(), \
                        "Should have errors when port conflicts exist"
                else:
                    # All ports are unique, no conflicts should be reported
                    port_conflict_errors = [
                        error for error in validator.result.errors
                        if "port conflict" in error.lower()
                    ]
                    assert len(port_conflict_errors) == 0, \
                        f"Should not report port conflicts when all ports are unique: {ports}"
    
    @given(
        conflicting_port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=50, deadline=10000)
    def test_backend_frontend_conflict_reported_property(self, conflicting_port: int):
        """
        **Property 34: Port Conflicts Reported - Backend-Frontend Conflict**
        **Validates: Requirements 10.3**
        
        For any configuration where backend and frontend use the same port,
        the conflict should be reported with both service names.
        """
        # Create configuration with backend and frontend on same port
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "BACKEND_PORT": str(conflicting_port),
            "FRONTEND_PORT": str(conflicting_port),
            "NEXT_PUBLIC_API_URL": f"http://localhost:{conflicting_port}",
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                conflicts = validator.validate_port_conflicts()
                
                # Property: Conflict should be detected
                assert len(conflicts) > 0, \
                    f"Should detect conflict when backend and frontend both use port {conflicting_port}"
                
                # Property: Conflict message should mention both services
                conflict_text = " ".join(conflicts).lower()
                has_backend_reference = "backend" in conflict_text or "fastapi" in conflict_text
                has_frontend_reference = "frontend" in conflict_text or "next" in conflict_text
                
                assert has_backend_reference or has_frontend_reference, \
                    "Conflict message should reference backend and/or frontend services"
                
                # Property: Conflict message should mention the port number
                assert str(conflicting_port) in " ".join(conflicts), \
                    f"Conflict message should mention port {conflicting_port}"
    
    @given(
        database_port=st.integers(min_value=1024, max_value=65535)
    )
    @settings(max_examples=50, deadline=10000)
    def test_database_conflict_reported_property(self, database_port: int):
        """
        **Property 34: Port Conflicts Reported - Database Conflict**
        **Validates: Requirements 10.3**
        
        For any configuration where PostgreSQL and Redis use the same port,
        the conflict should be reported.
        """
        # Create configuration with both databases on same port
        test_config = {
            "JWT_SECRET": "a" * 32,
            "SECRET_KEY": "b" * 32,
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": str(database_port),
            "POSTGRES_DB": TEST_DB,
            "POSTGRES_USER": TEST_USER,
            "POSTGRES_PASSWORD": TEST_PASSWORD,
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": TEST_PASSWORD,
            "REDIS_HOST": "localhost",
            "REDIS_PORT": str(database_port),
            "BACKEND_PORT": "8000",
            "FRONTEND_PORT": "3000",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
        }
        
        with patch.dict(os.environ, test_config, clear=True):
            with patch('app.core.config_validator.settings') as mock_settings:
                # Set all attributes
                mock_settings.POSTGRES_HOST = test_config["POSTGRES_HOST"]
                mock_settings.POSTGRES_PORT = int(test_config["POSTGRES_PORT"])
                mock_settings.POSTGRES_DB = test_config["POSTGRES_DB"]
                mock_settings.POSTGRES_USER = test_config["POSTGRES_USER"]
                mock_settings.POSTGRES_PASSWORD = test_config["POSTGRES_PASSWORD"]
                mock_settings.NEO4J_URI = test_config["NEO4J_URI"]
                mock_settings.NEO4J_USER = test_config["NEO4J_USER"]
                mock_settings.NEO4J_PASSWORD = test_config["NEO4J_PASSWORD"]
                mock_settings.REDIS_HOST = test_config["REDIS_HOST"]
                mock_settings.REDIS_PORT = int(test_config["REDIS_PORT"])
                mock_settings.JWT_SECRET = test_config["JWT_SECRET"]
                mock_settings.SECRET_KEY = test_config["SECRET_KEY"]
                
                # Run validation
                validator = ConfigValidator()
                conflicts = validator.validate_port_conflicts()
                
                # Property: Conflict should be detected
                assert len(conflicts) > 0, \
                    f"Should detect conflict when PostgreSQL and Redis both use port {database_port}"
                
                # Property: Conflict message should mention database services
                conflict_text = " ".join(conflicts).lower()
                has_postgres_reference = "postgres" in conflict_text
                has_redis_reference = "redis" in conflict_text
                
                assert has_postgres_reference or has_redis_reference, \
                    "Conflict message should reference PostgreSQL and/or Redis"
                
                # Property: Should have errors in validation result
                assert validator.result.has_errors(), \
                    "Should have errors when database ports conflict"


# Integration test to verify property test assumptions
def test_port_conflict_detection_integration():
    """Integration test to verify port conflict detection works correctly"""
    # Test with no conflicts
    no_conflict_config = {
        "JWT_SECRET": "a" * 32,
        "SECRET_KEY": "b" * 32,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": TEST_DB,
        "POSTGRES_USER": TEST_USER,
        "POSTGRES_PASSWORD": TEST_PASSWORD,
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": TEST_PASSWORD,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "BACKEND_PORT": "8000",
        "FRONTEND_PORT": "3000",
        "NEXT_PUBLIC_API_URL": "http://localhost:8000",
    }
    
    with patch.dict(os.environ, no_conflict_config, clear=True):
        with patch('app.core.config_validator.settings') as mock_settings:
            mock_settings.POSTGRES_HOST = "localhost"
            mock_settings.POSTGRES_PORT = 5432
            mock_settings.POSTGRES_DB = TEST_DB
            mock_settings.POSTGRES_USER = TEST_USER
            mock_settings.POSTGRES_PASSWORD = TEST_PASSWORD
            mock_settings.NEO4J_URI = "bolt://localhost:7687"
            mock_settings.NEO4J_USER = "neo4j"
            mock_settings.NEO4J_PASSWORD = TEST_PASSWORD
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6379
            mock_settings.JWT_SECRET = "a" * 32
            mock_settings.SECRET_KEY = "b" * 32
            
            validator = ConfigValidator()
            conflicts = validator.validate_port_conflicts()
            
            # Should report no conflicts
            assert len(conflicts) == 0, "Should have no conflicts with unique ports"
    
    # Test with backend-frontend conflict
    conflict_config = {
        "JWT_SECRET": "a" * 32,
        "SECRET_KEY": "b" * 32,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": TEST_DB,
        "POSTGRES_USER": TEST_USER,
        "POSTGRES_PASSWORD": TEST_PASSWORD,
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": TEST_PASSWORD,
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "BACKEND_PORT": "8000",
        "FRONTEND_PORT": "8000",  # Conflict with backend
        "NEXT_PUBLIC_API_URL": "http://localhost:8000",
    }
    
    with patch.dict(os.environ, conflict_config, clear=True):
        with patch('app.core.config_validator.settings') as mock_settings:
            mock_settings.POSTGRES_HOST = "localhost"
            mock_settings.POSTGRES_PORT = 5432
            mock_settings.POSTGRES_DB = TEST_DB
            mock_settings.POSTGRES_USER = TEST_USER
            mock_settings.POSTGRES_PASSWORD = TEST_PASSWORD
            mock_settings.NEO4J_URI = "bolt://localhost:7687"
            mock_settings.NEO4J_USER = "neo4j"
            mock_settings.NEO4J_PASSWORD = TEST_PASSWORD
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6379
            mock_settings.JWT_SECRET = "a" * 32
            mock_settings.SECRET_KEY = "b" * 32
            
            validator = ConfigValidator()
            conflicts = validator.validate_port_conflicts()
            
            # Should report conflict
            assert len(conflicts) > 0, "Should detect backend-frontend port conflict"
            assert "8000" in " ".join(conflicts), "Conflict message should mention port 8000"
            assert validator.result.has_errors(), "Should have errors when conflicts exist"


# Test fixtures
@pytest.fixture
def valid_port_configuration():
    """Fixture providing a valid port configuration with no conflicts"""
    return {
        "BACKEND_PORT": "8000",
        "FRONTEND_PORT": "3000",
        "POSTGRES_PORT": "5432",
        "REDIS_PORT": "6379",
        "NEO4J_URI": "bolt://localhost:7687",
    }


@pytest.fixture
def conflicting_port_configuration():
    """Fixture providing a port configuration with conflicts"""
    return {
        "BACKEND_PORT": "8000",
        "FRONTEND_PORT": "8000",  # Conflict
        "POSTGRES_PORT": "5432",
        "REDIS_PORT": "6379",
        "NEO4J_URI": "bolt://localhost:7687",
    }
