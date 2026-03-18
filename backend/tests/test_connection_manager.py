"""
Unit Tests for Connection Manager

Tests database connection verification including:
- PostgreSQL connection verification
- Neo4j connection verification
- Redis connection verification
- Connection status reporting
- Error handling and timeouts

Validates Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.database.connection_manager import (
    ConnectionManager,
    ConnectionStatus,
    get_connection_manager,
)
from backend.tests.utils.secure_test_data import get_test_password, get_test_jwt_secret, get_test_api_key


# constants for testing to avoid hard-coded credentials in literal strings
TEST_PASSWORD = get_test_password("test_password_123")
TEST_USER = "test_user_name"
TEST_DB = "test_database_db"


class TestConnectionStatus:
    """Tests for ConnectionStatus dataclass"""
    
    def test_connection_status_connected(self):
        """Test connection status when connected"""
        status = ConnectionStatus(
            service="PostgreSQL",
            is_connected=True,
            response_time_ms=50.0,
            is_critical=True
        )
        
        assert status.service == "PostgreSQL"
        assert status.is_connected is True
        assert status.response_time_ms == 50.0
        assert status.is_critical is True
        assert "✅" in str(status)
        assert "50" in str(status)
    
    def test_connection_status_disconnected(self):
        """Test connection status when disconnected"""
        status = ConnectionStatus(
            service="Neo4j",
            is_connected=False,
            error="Connection refused",
            is_critical=False
        )
        
        assert status.service == "Neo4j"
        assert status.is_connected is False
        assert status.error == "Connection refused"
        assert status.is_critical is False
        assert "❌" in str(status)
        assert "Connection refused" in str(status)
    
    def test_connection_status_no_error_message(self):
        """Test connection status string when no error message"""
        status = ConnectionStatus(
            service="Redis",
            is_connected=False,
            error=None,
            is_critical=False
        )
        
        assert "❌" in str(status)
        assert "Unknown error" in str(status)


class TestConnectionManager:
    """Tests for ConnectionManager class"""
    
    def test_connection_manager_initialization(self):
        """Test connection manager initialization"""
        manager = ConnectionManager()
        
        assert manager is not None
        assert manager.CONNECTION_TIMEOUT == 5
    
    @pytest.mark.asyncio
    async def test_verify_postgres_success(self):
        """Test successful PostgreSQL connection"""
        manager = ConnectionManager()
        
        # Mock SQLAlchemy
        with patch('app.database.connection_manager.create_engine') as mock_engine:
            mock_engine_instance = MagicMock()
            mock_engine.return_value = mock_engine_instance
            
            # Mock connection
            mock_connection = MagicMock()
            mock_engine_instance.connect.return_value.__enter__ = MagicMock(
                return_value=mock_connection
            )
            mock_engine_instance.connect.return_value.__exit__ = MagicMock(
                return_value=None
            )
            
            status = await manager.verify_postgres()
            
            assert status.service == "PostgreSQL"
            assert status.is_connected is True
            assert status.is_critical is True
            assert status.response_time_ms > 0
            assert status.error is None
    
    @pytest.mark.asyncio
    async def test_verify_postgres_connection_refused(self):
        """Test PostgreSQL connection refused"""
        manager = ConnectionManager()
        
        # Mock SQLAlchemy to raise connection refused
        with patch('app.database.connection_manager.create_engine') as mock_engine:
            mock_engine.side_effect = Exception("Connection refused")
            
            status = await manager.verify_postgres()
            
            assert status.service == "PostgreSQL"
            assert status.is_connected is False
            assert status.is_critical is True
            assert status.error is not None
    
    @pytest.mark.asyncio
    async def test_verify_postgres_authentication_failed(self):
        """Test PostgreSQL authentication failure"""
        manager = ConnectionManager()
        
        # Mock SQLAlchemy to raise authentication error
        with patch('app.database.connection_manager.create_engine') as mock_engine:
            mock_engine.side_effect = Exception("FATAL: password authentication failed")
            
            status = await manager.verify_postgres()
            
            assert status.service == "PostgreSQL"
            assert status.is_connected is False
            assert "Authentication failed" in status.error
    
    @pytest.mark.asyncio
    async def test_verify_postgres_timeout(self):
        """Test PostgreSQL connection timeout"""
        manager = ConnectionManager()
        
        # Mock SQLAlchemy to raise timeout
        with patch('app.database.connection_manager.create_engine') as mock_engine:
            mock_engine.side_effect = asyncio.TimeoutError()
            
            status = await manager.verify_postgres()
            
            assert status.service == "PostgreSQL"
            assert status.is_connected is False
            assert "timeout" in status.error.lower()
    
    @pytest.mark.asyncio
    async def test_verify_neo4j_success(self):
        """Test successful Neo4j connection"""
        manager = ConnectionManager()
        
        # Mock the initialization to prevent actual database connections
        manager._initialized = True
        
        # Mock Neo4j client's test_connectivity method
        with patch.object(manager.neo4j_client, 'test_connectivity', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = True
            
            # Mock get_auth_statistics
            with patch.object(manager.neo4j_client, 'get_auth_statistics', new_callable=AsyncMock) as mock_stats:
                mock_stats.return_value = {
                    'total_failures': 0,
                    'consecutive_failures': 0,
                    'rate_limit_detected': False
                }
                
                status = await manager.verify_neo4j()
                
                assert status.service == "Neo4j"
                assert status.is_connected is True
                assert status.is_critical is False
                assert status.response_time_ms > 0
                assert status.error is None
    
    @pytest.mark.asyncio
    async def test_verify_neo4j_connection_refused(self):
        """Test Neo4j connection refused"""
        manager = ConnectionManager()
        manager._initialized = True
        
        # Mock Neo4j client to raise connection error
        with patch.object(manager.neo4j_client, 'test_connectivity', new_callable=AsyncMock) as mock_test:
            mock_test.side_effect = Exception("Connection refused")
            
            status = await manager.verify_neo4j()
            
            assert status.service == "Neo4j"
            assert status.is_connected is False
            assert status.is_critical is False
            assert status.error is not None
    
    @pytest.mark.asyncio
    async def test_verify_neo4j_authentication_failed(self):
        """Test Neo4j authentication failure"""
        manager = ConnectionManager()
        manager._initialized = True
        
        # Mock Neo4j client to return False for connectivity test
        with patch.object(manager.neo4j_client, 'test_connectivity', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = False
            
            status = await manager.verify_neo4j()
            
            assert status.service == "Neo4j"
            assert status.is_connected is False
            assert status.error is not None
    
    @pytest.mark.asyncio
    async def test_verify_neo4j_timeout(self):
        """Test Neo4j connection timeout"""
        manager = ConnectionManager()
        manager._initialized = True
        
        # Mock Neo4j client to raise timeout
        with patch.object(manager.neo4j_client, 'test_connectivity', new_callable=AsyncMock) as mock_test:
            mock_test.side_effect = asyncio.TimeoutError()
            
            status = await manager.verify_neo4j()
            
            assert status.service == "Neo4j"
            assert status.is_connected is False
            assert "timeout" in status.error.lower()
    
    @pytest.mark.asyncio
    async def test_verify_redis_success(self):
        """Test successful Redis connection"""
        manager = ConnectionManager()
        
        # Mock Redis client
        with patch('app.database.connection_manager.redis.Redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            
            status = await manager.verify_redis()
            
            assert status.service == "Redis"
            assert status.is_connected is True
            assert status.is_critical is False
            assert status.response_time_ms > 0
            assert status.error is None
            
            # Verify ping was called
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_redis_connection_refused(self):
        """Test Redis connection refused"""
        manager = ConnectionManager()
        
        # Mock Redis client to raise connection error
        with patch('app.database.connection_manager.redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")
            
            status = await manager.verify_redis()
            
            assert status.service == "Redis"
            assert status.is_connected is False
            assert status.is_critical is False
            assert status.error is not None
    
    @pytest.mark.asyncio
    async def test_verify_redis_authentication_failed(self):
        """Test Redis authentication failure"""
        manager = ConnectionManager()
        
        # Mock Redis client to raise authentication error
        with patch('app.database.connection_manager.redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("WRONGPASS invalid username-password pair")
            
            status = await manager.verify_redis()
            
            assert status.service == "Redis"
            assert status.is_connected is False
            assert "Authentication failed" in status.error
    
    @pytest.mark.asyncio
    async def test_verify_redis_timeout(self):
        """Test Redis connection timeout"""
        manager = ConnectionManager()
        
        # Mock Redis client to raise timeout
        with patch('app.database.connection_manager.redis.Redis') as mock_redis:
            mock_redis.side_effect = asyncio.TimeoutError()
            
            status = await manager.verify_redis()
            
            assert status.service == "Redis"
            assert status.is_connected is False
            assert "timeout" in status.error.lower()
    
    @pytest.mark.asyncio
    async def test_verify_all_all_connected(self):
        """Test verify_all with all databases connected"""
        manager = ConnectionManager()
        
        # Mock all verifications
        with patch.object(manager, 'verify_postgres', new_callable=AsyncMock) as mock_pg:
            with patch.object(manager, 'verify_neo4j', new_callable=AsyncMock) as mock_neo4j:
                with patch.object(manager, 'verify_redis', new_callable=AsyncMock) as mock_redis:
                    mock_pg.return_value = ConnectionStatus(
                        service="PostgreSQL",
                        is_connected=True,
                        response_time_ms=50.0,
                        is_critical=True
                    )
                    mock_neo4j.return_value = ConnectionStatus(
                        service="Neo4j",
                        is_connected=True,
                        response_time_ms=100.0,
                        is_critical=False
                    )
                    mock_redis.return_value = ConnectionStatus(
                        service="Redis",
                        is_connected=True,
                        response_time_ms=30.0,
                        is_critical=False
                    )
                    
                    status_dict = await manager.verify_all()
                    
                    assert len(status_dict) == 3
                    assert status_dict["PostgreSQL"].is_connected is True
                    assert status_dict["Neo4j"].is_connected is True
                    assert status_dict["Redis"].is_connected is True
    
    @pytest.mark.asyncio
    async def test_verify_all_some_disconnected(self):
        """Test verify_all with some databases disconnected"""
        manager = ConnectionManager()
        
        # Mock all verifications
        with patch.object(manager, 'verify_postgres', new_callable=AsyncMock) as mock_pg:
            with patch.object(manager, 'verify_neo4j', new_callable=AsyncMock) as mock_neo4j:
                with patch.object(manager, 'verify_redis', new_callable=AsyncMock) as mock_redis:
                    mock_pg.return_value = ConnectionStatus(
                        service="PostgreSQL",
                        is_connected=True,
                        response_time_ms=50.0,
                        is_critical=True
                    )
                    mock_neo4j.return_value = ConnectionStatus(
                        service="Neo4j",
                        is_connected=False,
                        error="Connection refused",
                        is_critical=False
                    )
                    mock_redis.return_value = ConnectionStatus(
                        service="Redis",
                        is_connected=False,
                        error="Connection refused",
                        is_critical=False
                    )
                    
                    status_dict = await manager.verify_all()
                    
                    assert len(status_dict) == 3
                    assert status_dict["PostgreSQL"].is_connected is True
                    assert status_dict["Neo4j"].is_connected is False
                    assert status_dict["Redis"].is_connected is False
    
    def test_get_connection_error_message_connection_refused(self):
        """Test error message for connection refused"""
        error = Exception("Connection refused")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "Connection refused"
    
    def test_get_connection_error_message_authentication_failed(self):
        """Test error message for authentication failure"""
        error = Exception("FATAL: password authentication failed")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "Authentication failed"
    
    def test_get_connection_error_message_timeout(self):
        """Test error message for timeout"""
        error = Exception("Connection timeout")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "Connection timeout"
    
    def test_get_connection_error_message_hostname_resolution(self):
        """Test error message for hostname resolution failure"""
        error = Exception("Cannot resolve hostname")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "Cannot resolve hostname"
    
    def test_get_connection_error_message_connection_reset(self):
        """Test error message for connection reset"""
        error = Exception("Connection reset by peer")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "Connection reset by peer"
    
    def test_get_connection_error_message_no_route(self):
        """Test error message for no route to host"""
        error = Exception("No route to host")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "No route to host"
    
    def test_get_connection_error_message_permission_denied(self):
        """Test error message for permission denied"""
        error = Exception("Permission denied")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert message == "Permission denied"
    
    def test_get_connection_error_message_unknown(self):
        """Test error message for unknown error"""
        error = Exception("Some unknown error that is very long and should be truncated")
        message = ConnectionManager._get_connection_error_message(error)
        
        assert "unknown" in message.lower()
        assert len(message) <= 100
    
    def test_format_connection_error(self):
        """Test formatting connection error"""
        status = ConnectionStatus(
            service="PostgreSQL",
            is_connected=False,
            error="Connection refused",
            is_critical=True
        )
        
        error_msg = ConnectionManager.format_connection_error(
            service="PostgreSQL",
            status=status,
            connection_string=f"postgresql://{TEST_USER}:{TEST_PASSWORD}@localhost:5432/{TEST_DB}"
        )
        
        assert "PostgreSQL" in error_msg
        assert "Connection refused" in error_msg or "ERROR" in error_msg


class TestConnectionManagerGlobal:
    """Tests for global connection manager instance"""
    
    def test_get_connection_manager_singleton(self):
        """Test that get_connection_manager returns singleton"""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()
        
        assert manager1 is manager2
    
    def test_get_connection_manager_creates_instance(self):
        """Test that get_connection_manager creates instance"""
        # Reset global instance
        import app.database.connection_manager as cm_module

        cm_module._connection_manager = None
        
        manager = get_connection_manager()
        
        assert manager is not None
        assert isinstance(manager, ConnectionManager)


class TestConnectionManagerIntegration:
    """Integration tests for connection manager"""
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test concurrent connection verification"""
        manager = ConnectionManager()
        
        # Mock all verifications
        with patch.object(manager, 'verify_postgres', new_callable=AsyncMock) as mock_pg:
            with patch.object(manager, 'verify_neo4j', new_callable=AsyncMock) as mock_neo4j:
                with patch.object(manager, 'verify_redis', new_callable=AsyncMock) as mock_redis:
                    # Add delays to simulate real connections
                    async def delayed_postgres():
                        await asyncio.sleep(0.01)
                        return ConnectionStatus(
                            service="PostgreSQL",
                            is_connected=True,
                            response_time_ms=50.0,
                            is_critical=True
                        )
                    
                    async def delayed_neo4j():
                        await asyncio.sleep(0.02)
                        return ConnectionStatus(
                            service="Neo4j",
                            is_connected=True,
                            response_time_ms=100.0,
                            is_critical=False
                        )
                    
                    async def delayed_redis():
                        await asyncio.sleep(0.015)
                        return ConnectionStatus(
                            service="Redis",
                            is_connected=True,
                            response_time_ms=30.0,
                            is_critical=False
                        )
                    
                    mock_pg.side_effect = delayed_postgres
                    mock_neo4j.side_effect = delayed_neo4j
                    mock_redis.side_effect = delayed_redis
                    
                    # Verify all should complete quickly due to concurrency
                    status_dict = await manager.verify_all()
                    
                    assert len(status_dict) == 3
                    assert all(s.is_connected for s in status_dict.values())
