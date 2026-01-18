#!/usr/bin/env python3
"""
Simple test script to check if the configuration can be loaded
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test importing config
    from app.core.config import settings
    print("✅ Successfully imported config")
    
    # Test accessing properties
    print(f"✅ Project name: {settings.PROJECT_NAME}")
    print(f"✅ Version: {settings.VERSION}")
    print(f"✅ API prefix: {settings.API_V1_STR}")
    
    # Test computed properties
    print(f"✅ Redis URL: {settings.redis_url}")
    print(f"✅ Postgres URL: {settings.postgres_url}")
    
    print("\n🎉 Configuration loaded successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)
