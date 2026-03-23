"""
Neo4j Client Integration Example

This module demonstrates how to integrate the enhanced Neo4j client
with the existing codebase, replacing direct neo4j_db.py usage.
"""
import logging
logger = logging.getLogger(__name__)


import asyncio
from typing import Optional

from app.core.config import settings
from app.database.models import create_database_config_from_settings
from app.database.retry_manager import RetryManager
from app.database.neo4j_client import Neo4jClient


class Neo4jIntegrationService:
    """
    Service that demonstrates integration of the enhanced Neo4j client
    with existing application patterns.
    """
    
    def __init__(self):
        self.config = create_database_config_from_settings(settings)
        self.retry_manager = RetryManager()
        self.neo4j_client = Neo4jClient(self.config, self.retry_manager)
    
    async def initialize(self) -> bool:
        """
        Initialize the Neo4j service with enhanced error handling.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Test connectivity with the enhanced client
            is_connected = await self.neo4j_client.test_connectivity()
            
            if is_connected:
                logger.info("✅ Neo4j client initialized successfully with enhanced features")
                return True
            else:
                logger.info("❌ Neo4j connectivity test failed")
                return False
                
        except Exception as e:
            logger.info("❌ Neo4j initialization failed: {e}")
            return False
    
    async def create_indexes_with_retry(self) -> bool:
        """
        Create Neo4j indexes using the enhanced client with retry logic.
        
        Returns:
            True if indexes created successfully, False otherwise
        """
        try:
            # Use the enhanced session management
            async with self.neo4j_client.session_manager.get_session() as session:
                # Create indexes with proper error handling
                await session.run(
                    "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.id)"
                )
                await session.run(
                    "CREATE INDEX IF NOT EXISTS FOR (n:Function) ON (n.name)"
                )
                await session.run(
                    "CREATE INDEX IF NOT EXISTS FOR (n:Class) ON (n.name)"
                )
                await session.run(
                    "CREATE INDEX IF NOT EXISTS FOR (n:Module) ON (n.path)"
                )
            
            logger.info("✅ Neo4j indexes created successfully")
            return True
            
        except Exception as e:
            logger.info("❌ Failed to create Neo4j indexes: {e}")
            return False
    
    async def execute_code_analysis_query(self, file_path: str) -> Optional[dict]:
        """
        Example of executing a code analysis query with enhanced error handling.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Query results or None if failed
        """
        try:
            query = """
            MATCH (m:Module {path: $file_path})
            OPTIONAL MATCH (m)-[:CONTAINS]->(f:Function)
            OPTIONAL MATCH (m)-[:CONTAINS]->(c:Class)
            RETURN m.path as module_path,
                   count(f) as function_count,
                   count(c) as class_count
            """
            
            result = await self.neo4j_client.execute_read_query(
                query, 
                {"file_path": file_path}
            )
            
            record = await result.single()
            if record:
                return {
                    "module_path": record["module_path"],
                    "function_count": record["function_count"],
                    "class_count": record["class_count"]
                }
            
            return None
            
        except Exception as e:
            logger.info("❌ Code analysis query failed: {e}")
            return None
    
    async def get_service_health(self) -> dict:
        """
        Get comprehensive health information about the Neo4j service.
        
        Returns:
            Dictionary containing health information
        """
        health_info = await self.neo4j_client.health_check()
        statistics = await self.neo4j_client.get_client_statistics()
        
        return {
            "health": health_info,
            "statistics": statistics,
            "service_name": "neo4j_enhanced_client"
        }
    
    async def close(self) -> None:
        """Close the Neo4j client and clean up resources."""
        await self.neo4j_client.close()
        logger.info("✅ Neo4j integration service closed")


# Example usage function
async def example_usage():
    """
    Example of how to use the enhanced Neo4j client in the application.
    """
    service = Neo4jIntegrationService()
    
    try:
        # Initialize the service
        if not await service.initialize():
            logger.info("Failed to initialize Neo4j service")
            return
        
        # Create indexes
        await service.create_indexes_with_retry()
        
        # Example query
        result = await service.execute_code_analysis_query("app/main.py")
        if result:
            logger.info("Analysis result: {result}")
        
        # Get health information
        health = await service.get_service_health()
        logger.info("Service health: {health['health']['status']}")
        
    finally:
        # Always clean up
        await service.close()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())