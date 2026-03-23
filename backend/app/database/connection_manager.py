"""
Database Connection Manager

Enhanced connection manager with advanced pool management, configurable limits,
timeout handling, and retry integration for robust database connectivity.

Validates Requirements: 4.1, 4.2, 4.3, 4.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import logging
import asyncio
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from weakref import WeakSet

import asyncpg
import neo4j

from app.core.config import settings
from app.core.error_reporter import ErrorReporter
from app.database.models import (
    DatabaseConfig, 
    HealthStatus, 
    HealthState,
    create_database_config_from_settings
)
from app.database.retry_manager import RetryManager, OperationType
from app.database.postgresql_client import PostgreSQLClient
from app.database.neo4j_client import Neo4jClient
from app.database.connection_status import ConnectionStatus
from app.database.pool_configuration import PoolConfiguration, PoolStats
from app.database.pool_monitor import PoolMonitor

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Enhanced connection manager with advanced pool management, configurable limits,
    timeout handling, and retry integration for robust database connectivity.
    
    Features:
    - Advanced connection pooling for PostgreSQL and Neo4j
    - Configurable pool limits and timeout handling
    - Integration with retry manager for connection failures
    - Pool health monitoring and automatic recovery
    - Comprehensive error handling and logging
    - Connection statistics and monitoring
    
    Validates Requirements: 4.1, 4.2, 4.3, 4.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize enhanced connection manager with advanced pooling.
        
        Args:
            config: Optional database configuration, defaults to settings-based config
        """
        self.config = config or create_database_config_from_settings(settings)
        self.retry_manager = RetryManager(self.config.retry_config)
        self.error_reporter = ErrorReporter()
        
        # Enhanced clients with retry integration
        self.postgresql_client = PostgreSQLClient(
            connection_manager=self,
            retry_manager=self.retry_manager
        )
        self.neo4j_client = Neo4jClient(
            config=self.config,
            retry_manager=self.retry_manager
        )
        
        # Connection pools and management
        self._postgresql_pool: Optional[asyncpg.Pool] = None
        self._neo4j_driver: Optional[neo4j.AsyncDriver] = None
        self._redis_client = None  # Keep existing Redis functionality
        
        # Pool configuration
        self.pool_config = PoolConfiguration(
            min_size=self.config.pool_min_size,
            max_size=self.config.pool_max_size,
            connection_timeout=self.config.connection_timeout,
            command_timeout=self.config.connection_timeout,
        )
        
        # Pool statistics and monitoring
        self.pool_stats = {
            'PostgreSQL': PoolStats(
                service='PostgreSQL',
                max_size=self.pool_config.max_size,
                min_size=self.pool_config.min_size
            ),
            'Neo4j': PoolStats(
                service='Neo4j',
                max_size=self.pool_config.max_size,
                min_size=self.pool_config.min_size
            )
        }
        
        # Pool monitor for health checking and recovery
        self.pool_monitor = PoolMonitor(self)
        
        # Connection management
        self._pool_lock = asyncio.Lock()
        self._active_connections: WeakSet = WeakSet()
        self._health_check_task: Optional[asyncio.Task] = None
        self._pool_cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # Legacy timeout for backward compatibility
        self.CONNECTION_TIMEOUT = self.config.connection_timeout
    
    async def initialize_pools(self) -> None:
        """
        Initialize connection pools with validation and error handling.
        
        Raises:
            Exception: If pool initialization fails
        """
        if self._initialized:
            logger.debug("Connection pools already initialized")
            return
        
        logger.info("Initializing enhanced connection pools...")
        
        async with self._pool_lock:
            try:
                # Initialize PostgreSQL pool with retry logic
                await self._initialize_postgresql_pool()
                
                # Initialize Neo4j driver with retry logic
                await self._initialize_neo4j_driver()
                
                # Start background tasks
                await self.pool_monitor.start_monitoring()
                
                self._initialized = True
                logger.info("✅ Enhanced connection pools initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize connection pools: {str(e)}")
                await self._cleanup_failed_initialization()
                raise
    
    async def _initialize_postgresql_pool(self) -> None:
        """Initialize PostgreSQL connection pool with advanced configuration"""
        logger.info("Initializing PostgreSQL connection pool...")
        
        try:
            # Validate compatibility first
            await self.postgresql_client.validate_compatibility()
            
            # Create pool with retry logic
            self._postgresql_pool = await self.retry_manager.execute_with_retry(
                self._create_postgresql_pool,
                OperationType.POSTGRESQL_CONNECTION,
                operation_id="postgresql_pool_creation"
            )
            
            # Update pool statistics
            self.pool_stats['PostgreSQL'].update_from_asyncpg_pool(self._postgresql_pool)
            self.pool_stats['PostgreSQL'].total_connections_created = self._postgresql_pool.get_size()
            
            logger.info(
                f"✅ PostgreSQL pool initialized: "
                f"{self.pool_stats['PostgreSQL'].size}/{self.pool_config.max_size} connections"
            )
            
        except Exception as e:
            self.pool_stats['PostgreSQL'].failed_connections += 1
            self.pool_stats['PostgreSQL'].health_status = HealthState.UNHEALTHY
            logger.error(f"Failed to initialize PostgreSQL pool: {str(e)}")
            raise
    
    async def _create_postgresql_pool(self) -> asyncpg.Pool:
        """Create PostgreSQL connection pool with advanced configuration"""
        pool_config = {
            'min_size': self.pool_config.min_size,
            'max_size': self.pool_config.max_size,
            'command_timeout': self.pool_config.command_timeout,
            'server_settings': {
                'application_name': 'ai_code_review_platform',
                'timezone': 'UTC'
            },
            'setup': self._setup_postgresql_connection,
            'max_queries': self.pool_config.max_queries,
            'max_inactive_connection_lifetime': self.pool_config.max_inactive_connection_lifetime,
        }
        
        return await asyncpg.create_pool(self.config.postgresql_dsn, **pool_config)
    
    async def _setup_postgresql_connection(self, connection: asyncpg.Connection) -> None:
        """Setup function called for each new PostgreSQL connection"""
        try:
            # Set connection-specific settings
            await connection.execute("SET timezone = 'UTC'")
            await connection.execute("SET statement_timeout = '30s'")
            
            logger.debug("PostgreSQL connection setup completed")
            
        except Exception as e:
            logger.warning(f"PostgreSQL connection setup failed: {str(e)}")
            # Don't raise - connection can still be used
    
    async def _initialize_neo4j_driver(self) -> None:
        """Initialize Neo4j driver with advanced configuration"""
        logger.info("Initializing Neo4j driver...")
        
        try:
            # Get driver through Neo4j client (includes retry logic)
            self._neo4j_driver = await self.neo4j_client.get_driver()
            
            # Update pool statistics (Neo4j doesn't expose detailed pool stats)
            self.pool_stats['Neo4j'].size = self.pool_config.max_size  # Estimated
            self.pool_stats['Neo4j'].max_size = self.pool_config.max_size
            self.pool_stats['Neo4j'].health_status = HealthState.HEALTHY
            self.pool_stats['Neo4j'].total_connections_created += 1
            
            logger.info("✅ Neo4j driver initialized successfully")
            
        except Exception as e:
            self.pool_stats['Neo4j'].failed_connections += 1
            self.pool_stats['Neo4j'].health_status = HealthState.UNHEALTHY
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
            raise
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks for pool monitoring and cleanup"""
        # Start pool health monitoring
        self._health_check_task = asyncio.create_task(
            self._pool_health_monitor(),
            name="pool_health_monitor"
        )
        
        # Start pool cleanup task
        self._pool_cleanup_task = asyncio.create_task(
            self._pool_cleanup_monitor(),
            name="pool_cleanup_monitor"
        )
        
        logger.info("Background pool monitoring tasks started")
    
    async def _pool_health_monitor(self) -> None:
        """Background task to monitor pool health and perform maintenance"""
        while True:
            try:
                await asyncio.sleep(self.pool_config.health_check_interval)
                
                if not self._initialized:
                    continue
                
                # Update PostgreSQL pool stats
                if self._postgresql_pool:
                    self.pool_stats['PostgreSQL'].update_from_asyncpg_pool(self._postgresql_pool)
                
                # Check for unhealthy pools and attempt recovery
                await self._check_and_recover_pools()
                
            except asyncio.CancelledError:
                logger.info("Pool health monitor task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in pool health monitor: {str(e)}")
                # Continue monitoring despite errors
    
    async def _pool_cleanup_monitor(self) -> None:
        """Background task to clean up idle connections and perform maintenance"""
        while True:
            try:
                await asyncio.sleep(self.pool_config.pool_recycle_time)
                
                if not self._initialized:
                    continue
                
                # Perform pool maintenance
                await self._perform_pool_maintenance()
                
            except asyncio.CancelledError:
                logger.info("Pool cleanup monitor task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in pool cleanup monitor: {str(e)}")
    
    async def _check_and_recover_pools(self) -> None:
        """
        Check pool health and attempt recovery for unhealthy pools.
        Enhanced with automatic connection recreation for failed connections.
        
        Validates Requirements: 4.5
        """
        for service, stats in self.pool_stats.items():
            # Enhanced health validation beyond basic status checks
            needs_recovery = await self._validate_pool_health(service, stats)
            
            if needs_recovery:
                logger.warning(f"Unhealthy pool detected for {service}, attempting recovery...")
                
                try:
                    if service == 'PostgreSQL' and self._postgresql_pool:
                        await self._recover_postgresql_pool()
                    elif service == 'Neo4j' and self._neo4j_driver:
                        await self._recover_neo4j_driver()
                        
                    # Verify recovery was successful
                    await self._verify_pool_recovery(service)
                        
                except Exception as e:
                    logger.error(f"Failed to recover {service} pool: {str(e)}")
                    # Mark pool as failed for monitoring
                    stats.health_status = HealthState.UNHEALTHY
                    stats.failed_connections += 1
    
    async def _recover_postgresql_pool(self) -> None:
        """Attempt to recover PostgreSQL pool"""
        logger.info("Attempting PostgreSQL pool recovery...")
        
        try:
            # Close existing pool
            if self._postgresql_pool:
                await self._postgresql_pool.close()
            
            # Recreate pool
            await self._initialize_postgresql_pool()
            
            logger.info("✅ PostgreSQL pool recovered successfully")
            
        except Exception as e:
            logger.error(f"PostgreSQL pool recovery failed: {str(e)}")
            raise
    
    async def _recover_neo4j_driver(self) -> None:
        """Attempt to recover Neo4j driver"""
        logger.info("Attempting Neo4j driver recovery...")
        
        try:
            # Close existing driver
            if self._neo4j_driver:
                await self._neo4j_driver.close()
                self._neo4j_driver = None
            
            # Recreate driver
            await self._initialize_neo4j_driver()
            
            logger.info("✅ Neo4j driver recovered successfully")
            
        except Exception as e:
            logger.error(f"Neo4j driver recovery failed: {str(e)}")
            raise
    
    async def _validate_pool_health(self, service: str, stats: PoolStats) -> bool:
        """
        Enhanced pool health validation beyond current health checks.
        
        Args:
            service: Service name ('PostgreSQL' or 'Neo4j')
            stats: Current pool statistics
            
        Returns:
            True if pool needs recovery, False otherwise
            
        Validates Requirements: 4.5
        """
        # Basic health status check
        if stats.health_status == HealthState.UNHEALTHY:
            return True
        
        # Enhanced validation criteria
        current_time = datetime.now()
        
        # Check for excessive connection failures
        failure_rate = stats.failed_connections / max(1, stats.total_connections_created + stats.failed_connections)
        if failure_rate > 0.5:  # More than 50% failure rate
            logger.warning(f"{service} pool has high failure rate: {failure_rate:.2%}")
            return True
        
        # Check for excessive timeouts
        if stats.connection_timeouts > 10:  # Arbitrary threshold
            logger.warning(f"{service} pool has excessive timeouts: {stats.connection_timeouts}")
            return True
        
        # Check pool utilization and stagnation
        if service == 'PostgreSQL' and self._postgresql_pool:
            try:
                # Test actual pool connectivity
                test_connection = await asyncio.wait_for(
                    self._postgresql_pool.acquire(),
                    timeout=5.0
                )
                await test_connection.close()
                
                # Update last successful connection time
                stats.last_updated = current_time
                
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"{service} pool connectivity test failed: {str(e)}")
                return True
        
        elif service == 'Neo4j' and self._neo4j_driver:
            try:
                # Test Neo4j driver connectivity
                await asyncio.wait_for(
                    self._neo4j_driver.verify_connectivity(),
                    timeout=5.0
                )
                
                # Update last successful connection time
                stats.last_updated = current_time
                
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"{service} driver connectivity test failed: {str(e)}")
                return True
        
        # Check for stale connections (no activity for extended period)
        time_since_update = current_time - stats.last_updated
        if time_since_update > timedelta(minutes=30):  # 30 minutes without activity
            logger.warning(f"{service} pool appears stale, last update: {stats.last_updated}")
            return True
        
        return False
    
    async def _verify_pool_recovery(self, service: str) -> None:
        """
        Verify that pool recovery was successful.
        
        Args:
            service: Service name that was recovered
            
        Validates Requirements: 4.5
        """
        stats = self.pool_stats[service]
        
        try:
            if service == 'PostgreSQL' and self._postgresql_pool:
                # Test PostgreSQL pool
                test_connection = await asyncio.wait_for(
                    self._postgresql_pool.acquire(),
                    timeout=10.0
                )
                await test_connection.close()
                
                # Update statistics to reflect successful recovery
                stats.health_status = HealthState.HEALTHY
                stats.total_connections_created += 1
                stats.last_updated = datetime.now()
                
                logger.info(f"✅ {service} pool recovery verified successfully")
                
            elif service == 'Neo4j' and self._neo4j_driver:
                # Test Neo4j driver
                await asyncio.wait_for(
                    self._neo4j_driver.verify_connectivity(),
                    timeout=10.0
                )
                
                # Update statistics to reflect successful recovery
                stats.health_status = HealthState.HEALTHY
                stats.total_connections_created += 1
                stats.last_updated = datetime.now()
                
                logger.info(f"✅ {service} driver recovery verified successfully")
                
        except Exception as e:
            logger.error(f"Failed to verify {service} recovery: {str(e)}")
            stats.health_status = HealthState.UNHEALTHY
            stats.failed_connections += 1
            raise
    
    async def _perform_pool_maintenance(self) -> None:
        """Perform routine pool maintenance"""
        logger.debug("Performing pool maintenance...")
        
        try:
            # PostgreSQL pool maintenance
            if self._postgresql_pool:
                # Update statistics
                self.pool_stats['PostgreSQL'].update_from_asyncpg_pool(self._postgresql_pool)
                
                # Log pool statistics
                stats = self.pool_stats['PostgreSQL']
                logger.debug(
                    f"PostgreSQL pool stats: {stats.active_connections}/{stats.max_size} active, "
                    f"{stats.idle_connections} idle, health: {stats.health_status.value}"
                )
            
            # Neo4j driver maintenance
            if self._neo4j_driver:
                # Verify connectivity
                try:
                    await self._neo4j_driver.verify_connectivity()
                    self.pool_stats['Neo4j'].health_status = HealthState.HEALTHY
                except Exception as e:
                    logger.warning(f"Neo4j connectivity check failed: {e}")
                    self.pool_stats['Neo4j'].health_status = HealthState.UNHEALTHY
            
        except Exception as e:
            logger.error(f"Pool maintenance failed: {str(e)}")
    
    @asynccontextmanager
    async def get_postgresql_connection(self):
        """
        Get PostgreSQL connection from pool with retry logic, timeout handling,
        and automatic connection recreation for failed connections.
        
        Yields:
            asyncpg.Connection: Database connection
            
        Raises:
            Exception: If connection acquisition fails
            
        Validates Requirements: 4.5
        """
        if not self._initialized:
            await self.initialize_pools()
        
        connection = None
        start_time = time.time()
        max_recreation_attempts = 3
        recreation_attempt = 0
        
        while recreation_attempt < max_recreation_attempts:
            try:
                # Get connection with retry logic
                connection = await self.retry_manager.execute_with_retry(
                    self._acquire_postgresql_connection,
                    OperationType.POSTGRESQL_CONNECTION,
                    operation_id=f"pg_connection_{id(self)}_{recreation_attempt}"
                )
                
                # Test connection health before returning
                if await self._test_connection_health(connection):
                    # Track connection
                    self._active_connections.add(connection)
                    self.pool_stats['PostgreSQL'].pool_hits += 1
                    
                    # Update response time
                    response_time = (time.time() - start_time) * 1000
                    logger.debug(f"PostgreSQL connection acquired in {response_time:.1f}ms")
                    
                    yield connection
                    break
                else:
                    # Connection is unhealthy, attempt recreation
                    logger.warning(f"Unhealthy PostgreSQL connection detected, attempting recreation (attempt {recreation_attempt + 1})")
                    if connection:
                        try:
                            await connection.close()
                        except Exception as e:
                            logger.warning(f"Error closing PostgreSQL connection: {e}")
                    connection = None
                    recreation_attempt += 1
                    
                    if recreation_attempt < max_recreation_attempts:
                        # Trigger pool recovery
                        await self._recover_postgresql_pool()
                        await asyncio.sleep(1)  # Brief delay before retry
                    
            except asyncio.TimeoutError:
                self.pool_stats['PostgreSQL'].connection_timeouts += 1
                self.pool_stats['PostgreSQL'].pool_misses += 1
                logger.error("PostgreSQL connection acquisition timeout")
                
                # Attempt pool recovery on timeout
                if recreation_attempt < max_recreation_attempts - 1:
                    recreation_attempt += 1
                    logger.info("Attempting pool recovery due to timeout...")
                    try:
                        await self._recover_postgresql_pool()
                        await asyncio.sleep(2)  # Longer delay after recovery
                        continue
                    except Exception as recovery_error:
                        logger.error(f"Pool recovery failed: {str(recovery_error)}")
                
                raise
                
            except Exception as e:
                self.pool_stats['PostgreSQL'].failed_connections += 1
                self.pool_stats['PostgreSQL'].pool_misses += 1
                logger.error(f"Failed to acquire PostgreSQL connection: {str(e)}")
                
                # Attempt pool recovery on connection failure
                if recreation_attempt < max_recreation_attempts - 1:
                    recreation_attempt += 1
                    logger.info("Attempting pool recovery due to connection failure...")
                    try:
                        await self._recover_postgresql_pool()
                        await asyncio.sleep(2)  # Longer delay after recovery
                        continue
                    except Exception as recovery_error:
                        logger.error(f"Pool recovery failed: {str(recovery_error)}")
                
                raise
                
        if recreation_attempt >= max_recreation_attempts:
            logger.error("Exhausted all connection recreation attempts")
            raise RuntimeError("Failed to acquire healthy PostgreSQL connection after multiple attempts")
            
        # Connection cleanup in finally block
        if connection:
            try:
                await connection.close()
                logger.debug("PostgreSQL connection returned to pool")
            except Exception as e:
                logger.warning(f"Error returning PostgreSQL connection to pool: {str(e)}")
    
    async def _test_connection_health(self, connection) -> bool:
        """
        Test if a database connection is healthy.
        
        Args:
            connection: Database connection to test
            
        Returns:
            True if connection is healthy, False otherwise
            
        Validates Requirements: 4.5
        """
        try:
            # Simple health check query
            await asyncio.wait_for(
                connection.execute("SELECT 1"),
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.debug(f"Connection health check failed: {str(e)}")
            return False
    
    async def _acquire_postgresql_connection(self) -> asyncpg.Connection:
        """Acquire PostgreSQL connection from pool"""
        if not self._postgresql_pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        return await asyncio.wait_for(
            self._postgresql_pool.acquire(),
            timeout=self.pool_config.connection_timeout
        )
    
    @asynccontextmanager
    async def get_neo4j_session(self, database: Optional[str] = None):
        """
        Get Neo4j session with retry logic and enhanced session management.
        
        Args:
            database: Optional database name
            
        Yields:
            neo4j.AsyncSession: Database session
            
        Raises:
            Exception: If session acquisition fails
        """
        if not self._initialized:
            await self.initialize_pools()
        
        # Use Neo4j client's enhanced session management
        async with self.neo4j_client.session_manager.get_session(database) as session:
            self.pool_stats['Neo4j'].pool_hits += 1
            yield session
    
    async def verify_postgres(self) -> ConnectionStatus:
        """
        Verify PostgreSQL connection with enhanced pool management and retry logic.
        
        Returns:
            ConnectionStatus with PostgreSQL connection information
            
        Validates Requirements: 6.1, 6.4, 6.5, 6.6, 4.1, 4.2, 4.3
        """
        logger.info("Verifying PostgreSQL connection with enhanced pool management...")
        start_time = time.time()
        
        try:
            # Ensure pools are initialized
            if not self._initialized:
                await self.initialize_pools()
            
            # Test connection using enhanced client
            status = await self.postgresql_client.test_connection()
            
            # Update with pool statistics
            if self._postgresql_pool:
                pool_stats = self.pool_stats['PostgreSQL'].to_dict()
                status.pool_stats = pool_stats
            
            response_time_ms = (time.time() - start_time) * 1000
            status.response_time_ms = response_time_ms
            
            if status.is_connected:
                logger.info(f"PostgreSQL connection successful ({response_time_ms:.0f}ms)")
                self.pool_stats['PostgreSQL'].health_status = HealthState.HEALTHY
            else:
                logger.error(f"PostgreSQL connection failed: {status.error}")
                self.pool_stats['PostgreSQL'].health_status = HealthState.UNHEALTHY
                self.pool_stats['PostgreSQL'].failed_connections += 1
            
            return status
            
        except asyncio.TimeoutError:
            error_msg = f"Connection timeout (>{self.CONNECTION_TIMEOUT}s)"
            logger.error(f"PostgreSQL connection timeout: {error_msg}")
            self.pool_stats['PostgreSQL'].connection_timeouts += 1
            self.pool_stats['PostgreSQL'].health_status = HealthState.UNHEALTHY
            
            return ConnectionStatus(
                service="PostgreSQL",
                is_connected=False,
                error=error_msg,
                is_critical=True,
                last_attempt=datetime.now()
            )
        
        except Exception as e:
            error_msg = self._get_connection_error_message(e)
            logger.error(f"PostgreSQL connection failed: {error_msg}")
            self.pool_stats['PostgreSQL'].failed_connections += 1
            self.pool_stats['PostgreSQL'].health_status = HealthState.UNHEALTHY
            
            return ConnectionStatus(
                service="PostgreSQL",
                is_connected=False,
                error=error_msg,
                is_critical=True,
                last_attempt=datetime.now()
            )
    
    async def verify_neo4j(self) -> ConnectionStatus:
        """
        Verify Neo4j connection with enhanced authentication resilience and retry logic.
        
        Returns:
            ConnectionStatus with Neo4j connection information
            
        Validates Requirements: 6.2, 6.4, 6.5, 6.6, 2.1, 2.2, 2.4, 2.5
        """
        logger.info("Verifying Neo4j connection with enhanced authentication resilience...")
        start_time = time.time()
        
        try:
            # Ensure pools are initialized
            if not self._initialized:
                await self.initialize_pools()
            
            # Test connectivity using enhanced client
            connectivity_result = await self.neo4j_client.test_connectivity()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if connectivity_result:
                logger.info(f"Neo4j connection successful ({response_time_ms:.0f}ms)")
                self.pool_stats['Neo4j'].health_status = HealthState.HEALTHY
                
                # Get authentication statistics
                auth_stats = await self.neo4j_client.get_auth_statistics()
                
                return ConnectionStatus(
                    service="Neo4j",
                    is_connected=True,
                    response_time_ms=response_time_ms,
                    is_critical=False,  # Neo4j is optional
                    last_attempt=datetime.now(),
                    pool_stats={
                        'auth_failures': auth_stats.get('total_failures', 0),
                        'consecutive_failures': auth_stats.get('consecutive_failures', 0),
                        'rate_limit_detected': auth_stats.get('rate_limit_detected', False)
                    }
                )
            else:
                error_msg = "Connectivity test failed"
                logger.warning(f"Neo4j connection failed: {error_msg}")
                self.pool_stats['Neo4j'].failed_connections += 1
                self.pool_stats['Neo4j'].health_status = HealthState.UNHEALTHY
                
                return ConnectionStatus(
                    service="Neo4j",
                    is_connected=False,
                    error=error_msg,
                    is_critical=False,
                    response_time_ms=response_time_ms,
                    last_attempt=datetime.now()
                )
            
        except asyncio.TimeoutError:
            error_msg = f"Connection timeout (>{self.CONNECTION_TIMEOUT}s)"
            logger.warning(f"Neo4j connection timeout: {error_msg}")
            self.pool_stats['Neo4j'].connection_timeouts += 1
            self.pool_stats['Neo4j'].health_status = HealthState.UNHEALTHY
            
            return ConnectionStatus(
                service="Neo4j",
                is_connected=False,
                error=error_msg,
                is_critical=False,
                last_attempt=datetime.now()
            )
        
        except Exception as e:
            error_msg = self._get_connection_error_message(e)
            logger.warning(f"Neo4j connection failed: {error_msg}")
            self.pool_stats['Neo4j'].failed_connections += 1
            self.pool_stats['Neo4j'].health_status = HealthState.UNHEALTHY
            
            # Handle authentication failures specifically
            if "auth" in error_msg.lower():
                self.neo4j_client.handle_auth_failure(e)
            
            return ConnectionStatus(
                service="Neo4j",
                is_connected=False,
                error=error_msg,
                is_critical=False,
                last_attempt=datetime.now()
            )
    
    async def verify_redis(self) -> ConnectionStatus:
        """
        Verify Redis connection.
        
        Returns:
            ConnectionStatus with Redis connection information
            
        Validates Requirements: 6.3, 6.4, 6.5, 6.6
        """
        logger.info("Verifying Redis connection...")
        start_time = time.time()
        
        try:
            import redis
            
            # Create Redis client
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                socket_connect_timeout=self.CONNECTION_TIMEOUT,
                socket_timeout=self.CONNECTION_TIMEOUT,
                decode_responses=True
            )
            
            # Test connection
            redis_client.ping()
            redis_client.close()
            
            response_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Redis connection successful ({response_time_ms:.0f}ms)")
            
            return ConnectionStatus(
                service="Redis",
                is_connected=True,
                response_time_ms=response_time_ms,
                is_critical=False  # Redis is optional
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Connection timeout (>{self.CONNECTION_TIMEOUT}s)"
            logger.warning(f"Redis connection timeout: {error_msg}")
            return ConnectionStatus(
                service="Redis",
                is_connected=False,
                error=error_msg,
                is_critical=False
            )
        
        except Exception as e:
            error_msg = self._get_connection_error_message(e)
            logger.warning(f"Redis connection failed: {error_msg}")
            
            return ConnectionStatus(
                service="Redis",
                is_connected=False,
                error=error_msg,
                is_critical=False
            )
    
    async def verify_all(self) -> Dict[str, ConnectionStatus]:
        """
        Verify all database connections with enhanced pool management.
        
        Returns:
            Dictionary mapping service names to ConnectionStatus objects
            
        Validates Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 4.1, 4.2, 4.3
        """
        logger.info("Verifying all database connections with enhanced pool management...")
        
        # Run all verifications concurrently
        postgres_status, neo4j_status, redis_status = await asyncio.gather(
            self.verify_postgres(),
            self.verify_neo4j(),
            self.verify_redis(),
            return_exceptions=False
        )
        
        status_dict = {
            "PostgreSQL": postgres_status,
            "Neo4j": neo4j_status,
            "Redis": redis_status,
        }
        
        # Log summary with pool information
        connected = [s.service for s in status_dict.values() if s.is_connected]
        disconnected = [s.service for s in status_dict.values() if not s.is_connected]
        
        if connected:
            logger.info(f"Connected databases: {', '.join(connected)}")
        if disconnected:
            logger.warning(f"Disconnected databases: {', '.join(disconnected)}")
        
        # Log pool statistics
        await self._log_pool_statistics()
        
        return status_dict
    
    async def get_pool_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive pool statistics for monitoring.
        Enhanced with additional monitoring capabilities.
        
        Returns:
            Dictionary containing pool statistics for all services
            
        Validates Requirements: 4.5
        """
        stats = {}
        
        for service, pool_stats in self.pool_stats.items():
            service_stats = pool_stats.to_dict()
            
            # Add enhanced monitoring data
            service_stats.update(await self._get_enhanced_pool_metrics(service, pool_stats))
            
            stats[service] = service_stats
        
        # Add retry statistics
        for service in ['PostgreSQL', 'Neo4j']:
            operation_type = (
                OperationType.POSTGRESQL_CONNECTION if service == 'PostgreSQL'
                else OperationType.NEO4J_CONNECTION
            )
            retry_stats = self.retry_manager.get_retry_statistics(operation_type)
            stats[service]['retry_stats'] = retry_stats
        
        # Add overall system health metrics
        stats['system'] = await self._get_system_health_metrics()
        
        return stats
    
    async def get_health_status(self) -> Dict[str, HealthStatus]:
        """
        Get comprehensive health status for all database components.
        
        Returns:
            Dictionary mapping service names to HealthStatus objects
        """
        health_statuses = {}
        
        # PostgreSQL health
        pg_stats = self.pool_stats['PostgreSQL']
        pg_health = HealthStatus(
            component="PostgreSQL",
            status=pg_stats.health_status,
            message=f"Pool: {pg_stats.active_connections}/{pg_stats.max_size} active connections",
            details=pg_stats.to_dict(),
            timestamp=datetime.now(),
            response_time_ms=None
        )
        health_statuses["PostgreSQL"] = pg_health
        
        # Neo4j health
        neo4j_stats = self.pool_stats['Neo4j']
        neo4j_health = HealthStatus(
            component="Neo4j",
            status=neo4j_stats.health_status,
            message=f"Driver status: {neo4j_stats.health_status.value}",
            details=neo4j_stats.to_dict(),
            timestamp=datetime.now(),
            response_time_ms=None
        )
        health_statuses["Neo4j"] = neo4j_health
        
        return health_statuses
    
    async def close_all_connections(self) -> None:
        """
        Gracefully close all database connections and clean up resources.
        
        Validates Requirements: 4.5
        """
        logger.info("Closing all database connections and cleaning up resources...")
        
        try:
            # Cancel background tasks
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self._pool_cleanup_task:
                self._pool_cleanup_task.cancel()
                try:
                    await self._pool_cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close PostgreSQL pool
            if self._postgresql_pool:
                logger.info("Closing PostgreSQL connection pool...")
                await self._postgresql_pool.close()
                self._postgresql_pool = None
                self.pool_stats['PostgreSQL'].size = 0
                self.pool_stats['PostgreSQL'].active_connections = 0
                self.pool_stats['PostgreSQL'].idle_connections = 0
            
            # Close Neo4j client
            if self.neo4j_client:
                logger.info("Closing Neo4j client...")
                await self.neo4j_client.close()
                self._neo4j_driver = None
                self.pool_stats['Neo4j'].size = 0
            
            # Close PostgreSQL client
            if self.postgresql_client:
                logger.info("Closing PostgreSQL client...")
                await self.postgresql_client.close()
            
            # Clear active connections tracking
            self._active_connections.clear()
            
            self._initialized = False
            
            logger.info("✅ All database connections closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")
            raise
    
    async def _cleanup_failed_initialization(self) -> None:
        """Clean up resources after failed initialization"""
        logger.warning("Cleaning up after failed initialization...")
        
        try:
            if self._postgresql_pool:
                await self._postgresql_pool.close()
                self._postgresql_pool = None
            
            if self._neo4j_driver:
                await self._neo4j_driver.close()
                self._neo4j_driver = None
            
            if self._health_check_task:
                self._health_check_task.cancel()
            
            if self._pool_cleanup_task:
                self._pool_cleanup_task.cancel()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def _log_pool_statistics(self) -> None:
        """Log current pool statistics for monitoring"""
        for service, stats in self.pool_stats.items():
            if stats.size > 0 or stats.failed_connections > 0:
                logger.info(
                    f"{service} pool stats: "
                    f"{stats.active_connections}/{stats.max_size} active, "
                    f"{stats.idle_connections} idle, "
                    f"{stats.failed_connections} failed, "
                    f"health: {stats.health_status.value}"
                )
    
    async def _get_enhanced_pool_metrics(self, service: str, stats: PoolStats) -> Dict[str, Any]:
        """
        Get enhanced pool metrics for comprehensive monitoring.
        
        Args:
            service: Service name
            stats: Current pool statistics
            
        Returns:
            Dictionary with enhanced metrics
            
        Validates Requirements: 4.5
        """
        metrics = {}
        current_time = datetime.now()
        
        # Calculate performance metrics
        total_operations = stats.pool_hits + stats.pool_misses
        if total_operations > 0:
            metrics['success_rate'] = round((stats.pool_hits / total_operations) * 100, 2)
            metrics['failure_rate'] = round((stats.pool_misses / total_operations) * 100, 2)
        else:
            metrics['success_rate'] = 0.0
            metrics['failure_rate'] = 0.0
        
        # Calculate connection metrics
        total_connection_attempts = stats.total_connections_created + stats.failed_connections
        if total_connection_attempts > 0:
            metrics['connection_success_rate'] = round(
                (stats.total_connections_created / total_connection_attempts) * 100, 2
            )
        else:
            metrics['connection_success_rate'] = 0.0
        
        # Time-based metrics
        time_since_update = current_time - stats.last_updated
        metrics['seconds_since_last_update'] = int(time_since_update.total_seconds())
        metrics['is_stale'] = time_since_update > timedelta(minutes=30)
        
        # Health assessment
        metrics['health_score'] = await self._calculate_health_score(service, stats)
        metrics['needs_attention'] = metrics['health_score'] < 70
        
        # Service-specific metrics
        if service == 'PostgreSQL' and self._postgresql_pool:
            try:
                # Get real-time pool information
                metrics['actual_pool_size'] = self._postgresql_pool.get_size()
                metrics['actual_idle_size'] = self._postgresql_pool.get_idle_size()
                metrics['actual_active_size'] = metrics['actual_pool_size'] - metrics['actual_idle_size']
                
                # Pool efficiency metrics
                if stats.max_size > 0:
                    metrics['pool_utilization'] = round(
                        (metrics['actual_active_size'] / stats.max_size) * 100, 1
                    )
                
            except Exception as e:
                logger.debug(f"Could not get real-time PostgreSQL pool metrics: {str(e)}")
                metrics['actual_pool_size'] = stats.size
                metrics['actual_idle_size'] = stats.idle_connections
                metrics['actual_active_size'] = stats.active_connections
        
        elif service == 'Neo4j' and self._neo4j_driver:
            try:
                # Test connectivity for health metrics
                start_time = time.time()
                await asyncio.wait_for(
                    self._neo4j_driver.verify_connectivity(),
                    timeout=5.0
                )
                response_time = (time.time() - start_time) * 1000
                metrics['connectivity_response_time_ms'] = round(response_time, 1)
                metrics['connectivity_healthy'] = True
                
            except Exception as e:
                logger.debug(f"Neo4j connectivity test failed: {str(e)}")
                metrics['connectivity_response_time_ms'] = None
                metrics['connectivity_healthy'] = False
        
        return metrics
    
    async def _calculate_health_score(self, service: str, stats: PoolStats) -> int:
        """
        Calculate a health score (0-100) for a service pool.
        
        Args:
            service: Service name
            stats: Pool statistics
            
        Returns:
            Health score from 0 (unhealthy) to 100 (perfect health)
            
        Validates Requirements: 4.5
        """
        score = 100
        
        # Deduct points for failures
        total_attempts = stats.total_connections_created + stats.failed_connections
        if total_attempts > 0:
            failure_rate = stats.failed_connections / total_attempts
            score -= int(failure_rate * 50)  # Up to 50 points for failures
        
        # Deduct points for timeouts
        if stats.connection_timeouts > 0:
            timeout_penalty = min(stats.connection_timeouts * 2, 20)  # Up to 20 points
            score -= timeout_penalty
        
        # Deduct points for poor utilization
        if stats.max_size > 0:
            utilization = stats.active_connections / stats.max_size
            if utilization > 0.95:  # Over-utilized
                score -= 15
            elif utilization < 0.1 and stats.total_connections_created > 0:  # Under-utilized
                score -= 10
        
        # Deduct points for staleness
        current_time = datetime.now()
        time_since_update = current_time - stats.last_updated
        if time_since_update > timedelta(minutes=30):
            score -= 25
        elif time_since_update > timedelta(minutes=10):
            score -= 10
        
        # Health status penalty
        if stats.health_status == HealthState.UNHEALTHY:
            score -= 30
        elif stats.health_status == HealthState.DEGRADED:
            score -= 15
        
        return max(0, score)
    
    async def _get_system_health_metrics(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.
        
        Returns:
            Dictionary with system-wide health metrics
            
        Validates Requirements: 4.5
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'initialized': self._initialized,
            'background_tasks_running': (
                self._health_check_task is not None and not self._health_check_task.done()
            ) and (
                self._pool_cleanup_task is not None and not self._pool_cleanup_task.done()
            ),
            'active_connections_tracked': len(self._active_connections),
        }
        
        # Calculate overall health scores
        health_scores = []
        for service, stats in self.pool_stats.items():
            score = await self._calculate_health_score(service, stats)
            health_scores.append(score)
            metrics[f'{service.lower()}_health_score'] = score
        
        if health_scores:
            metrics['overall_health_score'] = round(sum(health_scores) / len(health_scores), 1)
            metrics['overall_health_status'] = (
                'healthy' if metrics['overall_health_score'] >= 80 else
                'degraded' if metrics['overall_health_score'] >= 60 else
                'unhealthy'
            )
        else:
            metrics['overall_health_score'] = 0
            metrics['overall_health_status'] = 'unknown'
        
        return metrics
    
    async def get_detailed_pool_report(self) -> Dict[str, Any]:
        """
        Get a detailed pool health and performance report.
        
        Returns:
            Comprehensive report with recommendations
            
        Validates Requirements: 4.5
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'services': {},
            'recommendations': []
        }
        
        # Get enhanced statistics
        stats = await self.get_pool_statistics()
        
        # Analyze each service
        for service, service_stats in stats.items():
            if service == 'system':
                report['summary'] = service_stats
                continue
            
            service_report = {
                'status': service_stats.get('health_status', 'unknown'),
                'health_score': service_stats.get('health_score', 0),
                'performance': {
                    'success_rate': service_stats.get('success_rate', 0),
                    'connection_success_rate': service_stats.get('connection_success_rate', 0),
                    'utilization': service_stats.get('utilization_percent', 0),
                },
                'issues': [],
                'metrics': service_stats
            }
            
            # Identify issues and recommendations
            if service_stats.get('health_score', 0) < 70:
                service_report['issues'].append('Low health score')
                report['recommendations'].append(f"Investigate {service} connection issues")
            
            if service_stats.get('connection_success_rate', 0) < 90:
                service_report['issues'].append('High connection failure rate')
                report['recommendations'].append(f"Check {service} server availability and configuration")
            
            if service_stats.get('connection_timeouts', 0) > 5:
                service_report['issues'].append('Excessive connection timeouts')
                report['recommendations'].append(f"Consider increasing {service} connection timeout or checking network")
            
            if service_stats.get('is_stale', False):
                service_report['issues'].append('Stale connection pool')
                report['recommendations'].append(f"Pool for {service} appears inactive, consider restarting")
            
            utilization = service_stats.get('utilization_percent', 0)
            if utilization > 90:
                service_report['issues'].append('High pool utilization')
                report['recommendations'].append(f"Consider increasing {service} pool size")
            elif utilization < 10 and service_stats.get('total_connections_created', 0) > 0:
                service_report['issues'].append('Low pool utilization')
                report['recommendations'].append(f"Consider reducing {service} pool size")
            
            report['services'][service] = service_report
        
        return report
    
    def get_retry_manager(self) -> RetryManager:
        """Get the retry manager instance for external use"""
        return self.retry_manager
    
    def get_postgresql_client(self) -> PostgreSQLClient:
        """Get the PostgreSQL client instance for external use"""
        return self.postgresql_client
    
    def get_neo4j_client(self) -> Neo4jClient:
        """Get the Neo4j client instance for external use"""
        return self.neo4j_client
    
    def is_initialized(self) -> bool:
        """Check if connection manager is initialized"""
        return self._initialized
    
    @staticmethod
    def _get_connection_error_message(error: Exception) -> str:
        """
        Get a human-readable connection error message.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Human-readable error message
            
        Validates Requirement: 6.4
        """
        error_str = str(error).lower()
        
        if "connection refused" in error_str or "errno 111" in error_str:
            return "Connection refused"
        elif "authentication" in error_str or "password" in error_str or "auth" in error_str:
            return "Authentication failed"
        elif "timeout" in error_str:
            return "Connection timeout"
        elif "could not translate host name" in error_str or "name or service not known" in error_str or "nodename nor servname provided" in error_str:
            return "Cannot resolve hostname"
        elif "connection reset" in error_str:
            return "Connection reset by peer"
        elif "no route" in error_str:
            return "No route to host"
        elif "permission denied" in error_str:
            return "Permission denied"
        elif "service unavailable" in error_str:
            return "Service unavailable"
        else:
            # Return first 100 characters of error
            return error_str[:100] if error_str else "Unknown error"
    
    @staticmethod
    def format_connection_error(
        service: str,
        status: ConnectionStatus,
        connection_string: Optional[str] = None
    ) -> str:
        """
        Format a connection error message.
        
        Args:
            service: Name of the service
            status: ConnectionStatus object
            connection_string: Optional connection string (will be masked)
            
        Returns:
            Formatted error message
            
        Validates Requirement: 6.4
        """
        return ErrorReporter.format_connection_error(
            service=service,
            error=Exception(status.error or "Unknown error"),
            connection_string=connection_string,
            is_critical=status.is_critical
        )


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create enhanced connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


async def initialize_connection_manager(config: Optional[DatabaseConfig] = None) -> ConnectionManager:
    """
    Initialize connection manager with enhanced pooling capabilities.
    
    Args:
        config: Optional database configuration
        
    Returns:
        Initialized connection manager
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager(config)
    
    await _connection_manager.initialize_pools()
    return _connection_manager


async def close_connection_manager() -> None:
    """Close global connection manager and clean up resources"""
    global _connection_manager
    if _connection_manager is not None:
        await _connection_manager.close_all_connections()
        _connection_manager = None
