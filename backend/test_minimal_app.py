#!/usr/bin/env python3
"""
Minimal test to check if the application can start without database connections
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
    
    print("\n🎉 Application structure is valid!")
    print("Note: To run the full application, you'll need:")
    print("  - PostgreSQL database")
    print("  - Neo4j database") 
    print("  - Redis server")
    print("  - Or use docker-compose for easy setup")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
