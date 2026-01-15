"""
Health check endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "ai-code-review-api",
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    from app.database.postgresql import test_postgres_connection
    from app.database.neo4j_db import test_neo4j_connection
    from app.database.redis_db import test_redis_connection
    
    postgres_status = await test_postgres_connection()
    neo4j_status = await test_neo4j_connection()
    redis_status = await test_redis_connection()
    
    all_healthy = all([postgres_status, neo4j_status, redis_status])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            "postgresql": "healthy" if postgres_status else "unhealthy",
            "neo4j": "healthy" if neo4j_status else "unhealthy",
            "redis": "healthy" if redis_status else "unhealthy",
        }
    }
