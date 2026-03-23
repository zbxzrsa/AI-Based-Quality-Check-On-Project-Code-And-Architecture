"""
Database Pool Health Monitoring and Recovery

Background monitoring and automatic recovery for database connection pools.
"""

import logging
import asyncio
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

from app.database.models import HealthState
from app.database.pool_configuration import PoolStats

if TYPE_CHECKING:
    from app.database.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class PoolMonitor:
    """Handles pool health monitoring and automatic recovery"""
    
    def __init__(self, connection_manager: 'ConnectionManager'):
        self.connection_manager = connection_manager
        self._monitoring_tasks = []
    
    async def start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        logger.info("Starting pool monitoring tasks...")
        
        # Start health monitoring task
        health_task = asyncio.create_task(self._pool_health_monitor())
        self._monitoring_tasks.append(health_task)
        
        # Start cleanup monitoring task
        cleanup_task = asyncio.create_task(self._pool_cleanup_monitor())
        self._monitoring_tasks.append(cleanup_task)
        
        logger.info("Background pool monitoring tasks started")
    
    async def stop_monitoring(self) -> None:
        """Stop all monitoring tasks"""
        logger.info("Stopping pool monitoring tasks...")
        
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        logger.info("Pool monitoring tasks stopped")
    
    async def _pool_health_monitor(self) -> None:
        """Background task to monitor pool health and perform maintenance"""
        while True:
            try:
                await asyncio.sleep(self.connection_manager.pool_config.health_check_interval)
                
                if not self.connection_manager._initialized:
                    continue
                
                # Update PostgreSQL pool stats
                if self.connection_manager._postgresql_pool:
                    self.connection_manager.pool_stats['PostgreSQL'].update_from_asyncpg_pool(
                        self.connection_manager._postgresql_pool
                    )
                
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
                await asyncio.sleep(self.connection_manager.pool_config.pool_recycle_time)
                
                if not self.connection_manager._initialized:
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
        """
        for service, stats in self.connection_manager.pool_stats.items():
            # Enhanced health validation beyond basic status checks
            needs_recovery = await self._validate_pool_health(service, stats)
            
            if needs_recovery:
                logger.warning(f"Unhealthy pool detected for {service}, attempting recovery...")
                
                try:
                    if service == 'PostgreSQL' and self.connection_manager._postgresql_pool:
                        await self._recover_postgresql_pool()
                    elif service == 'Neo4j' and self.connection_manager._neo4j_driver:
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
            if self.connection_manager._postgresql_pool:
                await self.connection_manager._postgresql_pool.close()
            
            # Recreate pool
            await self.connection_manager._initialize_postgresql_pool()
            
            logger.info("✅ PostgreSQL pool recovered successfully")
            
        except Exception as e:
            logger.error(f"PostgreSQL pool recovery failed: {str(e)}")
            raise
    
    async def _recover_neo4j_driver(self) -> None:
        """Attempt to recover Neo4j driver"""
        logger.info("Attempting Neo4j driver recovery...")
        
        try:
            # Close existing driver
            if self.connection_manager._neo4j_driver:
                await self.connection_manager._neo4j_driver.close()
                self.connection_manager._neo4j_driver = None
            
            # Recreate driver
            await self.connection_manager._initialize_neo4j_driver()
            
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
        if service == 'PostgreSQL' and self.connection_manager._postgresql_pool:
            try:
                # Test actual pool connectivity
                test_connection = await asyncio.wait_for(
                    self.connection_manager._postgresql_pool.acquire(),
                    timeout=5.0
                )
                await test_connection.close()
                
                # Update last successful connection time
                stats.last_updated = current_time
                
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"{service} pool connectivity test failed: {str(e)}")
                return True
        
        elif service == 'Neo4j' and self.connection_manager._neo4j_driver:
            try:
                # Test Neo4j driver connectivity
                await asyncio.wait_for(
                    self.connection_manager._neo4j_driver.verify_connectivity(),
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
        """
        stats = self.connection_manager.pool_stats[service]
        
        try:
            if service == 'PostgreSQL' and self.connection_manager._postgresql_pool:
                # Test PostgreSQL pool
                test_connection = await asyncio.wait_for(
                    self.connection_manager._postgresql_pool.acquire(),
                    timeout=10.0
                )
                await test_connection.close()
                
                # Update statistics to reflect successful recovery
                stats.health_status = HealthState.HEALTHY
                stats.total_connections_created += 1
                stats.last_updated = datetime.now()
                
                logger.info(f"✅ {service} pool recovery verified successfully")
                
            elif service == 'Neo4j' and self.connection_manager._neo4j_driver:
                # Test Neo4j driver
                await asyncio.wait_for(
                    self.connection_manager._neo4j_driver.verify_connectivity(),
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
            if self.connection_manager._postgresql_pool:
                # Update statistics
                self.connection_manager.pool_stats['PostgreSQL'].update_from_asyncpg_pool(
                    self.connection_manager._postgresql_pool
                )
                
                # Log pool statistics
                stats = self.connection_manager.pool_stats['PostgreSQL']
                logger.debug(
                    f"PostgreSQL pool stats: {stats.active_connections}/{stats.max_size} active, "
                    f"{stats.idle_connections} idle, health: {stats.health_status.value}"
                )
            
            # Neo4j driver maintenance
            if self.connection_manager._neo4j_driver:
                # Verify connectivity
                try:
                    await self.connection_manager._neo4j_driver.verify_connectivity()
                    self.connection_manager.pool_stats['Neo4j'].health_status = HealthState.HEALTHY
                except Exception:
                    self.connection_manager.pool_stats['Neo4j'].health_status = HealthState.UNHEALTHY
            
            logger.debug("Pool maintenance completed")
            
        except Exception as e:
            logger.error(f"Error during pool maintenance: {str(e)}")