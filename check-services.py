"""
Check if all required services are running and healthy
"""
import requests
import psycopg2
import redis
from neo4j import GraphDatabase
import sys

def check_postgres():
    """Check PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="ai_code_review",
            user="postgres",
            password="postgres"
        )
        conn.close()
        print("✅ PostgreSQL: Connected")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: Failed - {e}")
        return False

def check_redis():
    """Check Redis connection"""
    try:
        r = redis.Redis(host='localhost', port=6379, password='password', db=0)
        r.ping()
        print("✅ Redis: Connected")
        return True
    except Exception as e:
        print(f"❌ Redis: Failed - {e}")
        return False

def check_neo4j():
    """Check Neo4j connection"""
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
        driver.close()
        print("✅ Neo4j: Connected")
        return True
    except Exception as e:
        print(f"❌ Neo4j: Failed - {e}")
        return False

def check_backend():
    """Check FastAPI backend"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI Backend: Running")
            return True
        else:
            print(f"❌ FastAPI Backend: Unhealthy (status {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ FastAPI Backend: Not running")
        return False
    except Exception as e:
        print(f"❌ FastAPI Backend: Failed - {e}")
        return False

def check_frontend():
    """Check Next.js frontend"""
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Next.js Frontend: Running")
            return True
        else:
            print(f"⚠️  Next.js Frontend: Responding but status {response.status_code}")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Next.js Frontend: Not running")
        return False
    except Exception as e:
        print(f"❌ Next.js Frontend: Failed - {e}")
        return False

def main():
    print("Checking Services Status")
    print("=" * 50)
    
    results = {
        "PostgreSQL": check_postgres(),
        "Redis": check_redis(),
        "Neo4j": check_neo4j(),
        "Backend": check_backend(),
        "Frontend": check_frontend()
    }
    
    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)
    
    all_good = all(results.values())
    
    if all_good:
        print("✅ All services are running!")
    else:
        print("⚠️  Some services are not running:")
        for service, status in results.items():
            if not status:
                print(f"   - {service}")
        
        print("\nTo start missing services:")
        if not results["PostgreSQL"] or not results["Redis"] or not results["Neo4j"]:
            print("   docker-compose up -d postgres redis neo4j")
        if not results["Backend"]:
            print("   cd backend && python -m uvicorn app.main:app --reload")
        if not results["Frontend"]:
            print("   cd frontend && npm run dev")
    
    sys.exit(0 if all_good else 1)

if __name__ == "__main__":
    main()
