@echo off
echo ========================================
echo Starting FastAPI Backend Locally
echo ========================================
echo.
echo Make sure Docker infrastructure is running:
echo   - PostgreSQL (port 5432)
echo   - Redis (port 6379)
echo   - Neo4j (ports 7474, 7687)
echo.
echo Press Ctrl+C to stop the backend
echo ========================================
echo.

cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
