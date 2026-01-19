# Troubleshooting Guide

## Current Issue: Backend Module Errors

The Docker backend container is missing Python dependencies (`networkx` and potentially others). The local Python environment has all dependencies installed.

## Solution: Run Backend Locally

### Step 1: Stop Docker Backend

```bash
docker stop ai-review-backend
```

### Step 2: Ensure Infrastructure is Running

```bash
docker-compose ps
```

You should see:
- ✅ postgres - healthy
- ✅ redis - healthy
- ✅ neo4j - healthy (or starting)

If not running:
```bash
docker-compose up -d postgres redis neo4j
```

### Step 3: Start Backend Locally

**Option A: Using the batch file**
```bash
START_BACKEND_LOCAL.bat
```

**Option B: Manual command**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Verify Backend is Running

Open a new terminal and test:
```bash
curl http://localhost:8000/health
```

You should see:
```json
{
  "status": "healthy",
  "service": "ai-code-review-api",
  "version": "1.0.0"
}
```

### Step 5: Test Authentication

```bash
python test-auth.py
```

### Step 6: Start Frontend

```bash
cd frontend
npm run dev
```

## Common Errors and Solutions

### Error: "ModuleNotFoundError: No module named 'X'"

**Cause:** Missing Python dependencies

**Solution:** Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Error: "Connection refused" when accessing backend

**Cause:** Backend not running or wrong port

**Solution:**
1. Check if backend is running: `curl http://localhost:8000/health`
2. Check if port 8000 is in use: `netstat -ano | findstr :8000`
3. Restart backend

### Error: "Database connection failed"

**Cause:** PostgreSQL not running or wrong credentials

**Solution:**
1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Verify credentials in `backend/.env` match `docker-compose.yml`
3. Test connection:
   ```bash
   python check-services.py
   ```

### Error: NextAuth "Unexpected token '<'"

**Cause:** Backend returning HTML error page instead of JSON

**Solution:**
1. Check backend logs for errors
2. Verify backend is accessible: `curl http://localhost:8000/api/v1/auth/me`
3. Check CORS settings in backend
4. Verify `BACKEND_URL` in `frontend/.env.local` is correct

### Error: "Neo4j connection failed"

**Cause:** Neo4j not fully started or wrong credentials

**Solution:**
1. Wait 40 seconds for Neo4j to fully start
2. Check Neo4j browser: http://localhost:7474
3. Verify credentials: neo4j/password
4. Check logs: `docker logs ai-based-quality-check-on-project-code-and-architecture-neo4j-1`

### Error: "Redis connection failed"

**Cause:** Redis not running or wrong password

**Solution:**
1. Check Redis is running: `docker-compose ps redis`
2. Test connection: `docker exec -it ai-based-quality-check-on-project-code-and-architecture-redis-1 redis-cli -a password ping`
3. Should return: `PONG`

## Files Modified to Fix Issues

### 1. backend/app/services/code_reviewer.py
**Issue:** Importing non-existent `ast_parser` module

**Fix:** Changed to use `ParserFactory` from `app.services.parsers.factory`

```python
# Before
from app.services.ast_parser import ASTParser
self.ast_parser = ASTParser()

# After
from app.services.parsers.factory import ParserFactory
self.parser_factory = ParserFactory
```

### 2. docker-compose.yml
**Issue:** PostgreSQL version mismatch (15 vs 16)

**Fix:** Updated to postgres:16-alpine

### 3. docker-compose.yml
**Issue:** Neo4j healthcheck failing

**Fix:** Changed healthcheck from cypher-shell to HTTP check

### 4. frontend/src/app/api/auth/[...nextauth]/route.ts
**Issue:** Wrong API endpoints and response handling

**Fix:** 
- Changed `/api/auth/login` to `/api/v1/auth/login`
- Added call to `/api/v1/auth/me` to get user details
- Fixed response format handling

### 5. backend/app/models/__init__.py
**Issue:** Duplicate PullRequest model definition

**Fix:** Removed duplicate, now imports from `code_review.py`

## Verification Checklist

Before testing the full application:

- [ ] Infrastructure services running (postgres, redis, neo4j)
- [ ] Backend running locally on port 8000
- [ ] Backend health check passes
- [ ] Test authentication script passes
- [ ] Frontend running on port 3000
- [ ] Can access frontend in browser
- [ ] Can login with test credentials

## Quick Commands Reference

```bash
# Check all services
python check-services.py

# Start infrastructure
docker-compose up -d postgres redis neo4j

# Start backend locally
START_BACKEND_LOCAL.bat

# Test auth
python test-auth.py

# Start frontend
cd frontend && npm run dev

# Check backend health
curl http://localhost:8000/health

# Check backend API docs
# Open: http://localhost:8000/docs

# View Docker logs
docker logs ai-based-quality-check-on-project-code-and-architecture-postgres-1
docker logs ai-based-quality-check-on-project-code-and-architecture-redis-1
docker logs ai-based-quality-check-on-project-code-and-architecture-neo4j-1

# Restart infrastructure
docker-compose restart postgres redis neo4j

# Clean restart
docker-compose down
docker-compose up -d postgres redis neo4j
```

## Getting Help

If you're still experiencing issues:

1. Check the backend terminal for error messages
2. Check browser console for frontend errors
3. Run `python check-services.py` to verify all services
4. Check the logs of failing services
5. Verify all environment variables are set correctly

## Next Steps After Fixing

Once everything is running:

1. Register a new user via the frontend
2. Test login functionality
3. Verify session persistence
4. Test protected routes
5. Check that API calls include authentication headers
