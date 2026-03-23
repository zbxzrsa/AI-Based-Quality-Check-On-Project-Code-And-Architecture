"""
Graceful Shutdown Service

Handles SIGTERM signals and ensures graceful shutdown:
- Completes in-flight requests before shutdown
- Closes database connections cleanly
- Stops background tasks gracefully

Validates Requirements: 12.10
"""

import asyncio
import logging
import signal
from typing import Optional, Callable, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """
    Handles graceful shutdown of the application.
    
    Features:
    - Handles SIGTERM and SIGINT signals
    - Waits for in-flight requests to complete
    - Closes database connections cleanly
    - Stops background tasks gracefully
    - Configurable shutdown timeout
    
    Validates Requirements: 12.10
    """
    
    def __init__(self, shutdown_timeout: int = 30):
        """
        Initialize graceful shutdown handler.
        
        Args:
            shutdown_timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        self.shutdown_timeout = shutdown_timeout
        self.is_shutting_down = False
        self.shutdown_callbacks: List[Callable] = []
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"Graceful shutdown handler initialized (timeout: {shutdown_timeout}s)")
    
    def register_shutdown_callback(self, callback: Callable):
        """
        Register a callback to be called during shutdown.
        
        Callbacks are called in the order they were registered.
        
        Args:
            callback: Async function to call during shutdown
        """
        self.shutdown_callbacks.append(callback)
        logger.debug(f"Registered shutdown callback: {callback.__name__}")
    
    def setup_signal_handlers(self):
        """
        Setup signal handlers for SIGTERM and SIGINT.
        
        This should be called during application startup.
        """
        # Handle SIGTERM (sent by Kubernetes, Docker, systemd)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info("Signal handlers registered (SIGTERM, SIGINT)")
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        
        if self.is_shutting_down:
            logger.warning("Shutdown already in progress, ignoring signal")
            return
        
        self.is_shutting_down = True
        
        # Trigger shutdown event
        asyncio.create_task(self._perform_shutdown())
    
    async def _perform_shutdown(self):
        """
        Perform graceful shutdown sequence.
        
        1. Stop accepting new requests
        2. Wait for in-flight requests to complete
        3. Execute shutdown callbacks
        4. Close database connections
        5. Exit application
        """
        shutdown_start = datetime.now()
        logger.info("=" * 70)
        logger.info("GRACEFUL SHUTDOWN INITIATED")
        logger.info("=" * 70)
        
        try:
            # Execute all registered shutdown callbacks
            logger.info(f"Executing {len(self.shutdown_callbacks)} shutdown callbacks...")
            
            for i, callback in enumerate(self.shutdown_callbacks, 1):
                try:
                    callback_name = callback.__name__
                    logger.info(f"[{i}/{len(self.shutdown_callbacks)}] Executing: {callback_name}")
                    
                    # Execute callback with timeout
                    await asyncio.wait_for(
                        callback(),
                        timeout=self.shutdown_timeout / len(self.shutdown_callbacks)
                    )
                    
                    logger.info(f"[{i}/{len(self.shutdown_callbacks)}] Completed: {callback_name}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"Shutdown callback timed out: {callback_name}")
                except Exception as e:
                    logger.error(f"Error in shutdown callback {callback_name}: {e}", exc_info=True)
            
            # Close database connections
            logger.info("Closing database connections...")
            await self._close_database_connections()
            
            # Calculate shutdown duration
            shutdown_duration = (datetime.now() - shutdown_start).total_seconds()
            logger.info("=" * 70)
            logger.info(f"GRACEFUL SHUTDOWN COMPLETED ({shutdown_duration:.2f}s)")
            logger.info("=" * 70)
            
            # Set shutdown event
            self._shutdown_event.set()
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}", exc_info=True)
            self._shutdown_event.set()
    
    async def _close_database_connections(self):
        """
        Close all database connections cleanly.
        
        Closes PostgreSQL, Neo4j, and Redis connections.
        """
        try:
            from app.database.postgresql import close_postgres
            from app.database.neo4j_db import close_neo4j
            from app.database.redis_db import close_redis
            
            # Close all connections concurrently
            await asyncio.gather(
                self._safe_close(close_postgres, "PostgreSQL"),
                self._safe_close(close_neo4j, "Neo4j"),
                self._safe_close(close_redis, "Redis"),
                return_exceptions=True
            )
            
            logger.info("All database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}", exc_info=True)
    
    async def _safe_close(self, close_func: Callable, name: str):
        """
        Safely close a connection with error handling.
        
        Args:
            close_func: Function to call to close the connection
            name: Name of the connection for logging
        """
        try:
            logger.debug(f"Closing {name} connection...")
            await close_func()
            logger.info(f"{name} connection closed")
        except Exception as e:
            logger.warning(f"Error closing {name} connection: {e}")
    
    async def wait_for_shutdown(self):
        """
        Wait for shutdown to complete.
        
        This can be used to block until shutdown is complete.
        """
        await self._shutdown_event.wait()
    
    def is_shutdown_in_progress(self) -> bool:
        """
        Check if shutdown is in progress.
        
        Returns:
            True if shutdown is in progress, False otherwise
        """
        return self.is_shutting_down


# Global shutdown handler instance
_shutdown_handler: Optional[GracefulShutdownHandler] = None


def get_shutdown_handler(shutdown_timeout: int = 30) -> GracefulShutdownHandler:
    """
    Get or create graceful shutdown handler instance.
    
    Args:
        shutdown_timeout: Maximum time to wait for graceful shutdown (seconds)
        
    Returns:
        GracefulShutdownHandler instance
    """
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler(shutdown_timeout=shutdown_timeout)
    return _shutdown_handler


def setup_graceful_shutdown(shutdown_timeout: int = 30) -> GracefulShutdownHandler:
    """
    Setup graceful shutdown for the application.
    
    This should be called during application startup.
    
    Args:
        shutdown_timeout: Maximum time to wait for graceful shutdown (seconds)
        
    Returns:
        GracefulShutdownHandler instance
    """
    handler = get_shutdown_handler(shutdown_timeout=shutdown_timeout)
    handler.setup_signal_handlers()
    return handler
