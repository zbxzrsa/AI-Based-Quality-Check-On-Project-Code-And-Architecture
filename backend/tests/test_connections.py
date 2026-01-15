"""
Database connection test script
Run this script to verify all database connections are working properly
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.postgresql import init_postgres, test_postgres_connection, close_postgres
from app.database.neo4j_db import init_neo4j, test_neo4j_connection, close_neo4j
from app.database.redis_db import init_redis, test_redis_connection, close_redis


async def test_all_connections():
    """Test all database connections"""
    print("\n" + "="*60)
    print("Testing Database Connections")
    print("="*60 + "\n")
    
    results = {
        "PostgreSQL": False,
        "Neo4j": False,
        "Redis": False
    }
    
    try:
        # Initialize and test PostgreSQL
        print("Initializing PostgreSQL...")
        await init_postgres()
        results["PostgreSQL"] = await test_postgres_connection()
        
        # Initialize and test Neo4j
        print("\nInitializing Neo4j...")
        await init_neo4j()
        results["Neo4j"] = await test_neo4j_connection()
        
        # Initialize and test Redis
        print("\nInitializing Redis...")
        await init_redis()
        results["Redis"] = await test_redis_connection()
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
    
    finally:
        # Cleanup
        print("\n" + "-"*60)
        print("Cleaning up connections...")
        print("-"*60)
        await close_postgres()
        await close_neo4j()
        await close_redis()
    
    # Print summary
    print("\n" + "="*60)
    print("Connection Test Summary")
    print("="*60)
    for db, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{db:20} {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✅ All database connections successful!")
    else:
        print("❌ Some database connections failed. Check configuration.")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_all_connections())
    sys.exit(0 if success else 1)
