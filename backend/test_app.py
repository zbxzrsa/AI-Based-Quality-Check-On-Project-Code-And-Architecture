#!/usr/bin/env python3
"""
Simple test script to check if the application can start
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test importing the main app
    from app.main import app
    print("✅ Successfully imported app.main")
    
    # Test importing config
    from app.core.config import settings
    print("✅ Successfully imported config")
    
    # Test database imports
    from app.database.postgresql import init_postgres, close_postgres
    from app.database.neo4j_db import init_neo4j, close_neo4j
    from app.database.redis_db import init_redis, close_redis
    print("✅ Successfully imported database modules")
    
    print("\n🎉 All imports successful! The application structure is valid.")
    print("Note: Database connections will be tested when the app starts.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
