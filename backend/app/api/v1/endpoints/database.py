"""
Database testing and management endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/test/postgres")
async def test_postgres():
    """Test PostgreSQL connection"""
    from app.database.postgresql import test_postgres_connection
    
    success = await test_postgres_connection()
    return {
        "database": "PostgreSQL",
        "status": "connected" if success else "failed",
        "success": success,
    }


@router.get("/test/neo4j")
async def test_neo4j():
    """Test Neo4j connection"""
    from app.database.neo4j_db import test_neo4j_connection
    
    success = await test_neo4j_connection()
    return {
        "database": "Neo4j",
        "status": "connected" if success else "failed",
        "success": success,
    }


@router.get("/test/redis")
async def test_redis():
    """Test Redis connection"""
    from app.database.redis_db import test_redis_connection
    
    success = await test_redis_connection()
    return {
        "database": "Redis",
        "status": "connected" if success else "failed",
        "success": success,
    }


@router.get("/test/all")
async def test_all_databases():
    """Test all database connections"""
    from app.database.postgresql import test_postgres_connection
    from app.database.neo4j_db import test_neo4j_connection
    from app.database.redis_db import test_redis_connection
    
    postgres = await test_postgres_connection()
    neo4j = await test_neo4j_connection()
    redis = await test_redis_connection()
    
    return {
        "databases": {
            "postgresql": {
                "status": "connected" if postgres else "failed",
                "success": postgres,
            },
            "neo4j": {
                "status": "connected" if neo4j else "failed",
                "success": neo4j,
            },
            "redis": {
                "status": "connected" if redis else "failed",
                "success": redis,
            },
        },
        "all_connected": all([postgres, neo4j, redis]),
    }
