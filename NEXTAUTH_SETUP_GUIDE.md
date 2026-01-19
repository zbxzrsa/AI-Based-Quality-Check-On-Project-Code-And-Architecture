# NextAuth Backend Integration - Setup Guide

## What Was Fixed

### 1. NextAuth Configuration Issues
- **Fixed API endpoint path**: Changed from `/api/auth/login` to `/api/v1/auth/login`
- **Fixed response handling**: Updated to handle FastAPI's `{access_token, refresh_token}` format
- **Added user data fetching**: Now calls `/api/v1/auth/me` to get complete user details
- **Fixed TypeScript types**: Added proper NextAuth type definitions

### 2. Backend Database Model Issues
- **Removed duplicate PullRequest model**: Was defined in both `__init__.py` and `code_review.py`
- **Unified model definition**: Now using single source from `code_review.py`

### 3. Docker Configuration
- **Fixed Neo4j healthcheck**: Changed from cypher-shell to HTTP check
- **Added start_period**: Gives Neo4j time to fully initialize

## How to Start the Application

### Step 1: Start Infrastructure Services
```bash
docker-compose up -d postgres redis neo4j
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Neo4j (ports 7474, 7687)

### Step 2: Start the FastAPI Backend
```bash
# Option 1: Using the batch script
start-backend.bat

# Option 2: Manual command
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

### Step 3: Test Authentication
```bash
# Run the test script
python test-auth.py
```

This will:
1. Register a test user (test@example.com / Test@1234)
2. Login and get access token
3. Fetch user details using the token

### Step 4: Start the Frontend
```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:3000

## Testing the Integration

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```

### 2. Register a User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

### 3. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### 4. Get User Info
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Environment Variables

### Frontend (.env.local)
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-key-change-in-production-min-32-chars-required
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=development
NODE_ENV=development
```

### Backend (.env)
```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=password

# Security
JWT_SECRET=test_secret_key_for_development_only
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

## Files Modified

1. **frontend/src/app/api/auth/[...nextauth]/route.ts**
   - Fixed API endpoint paths
   - Updated response handling
   - Added proper user data fetching

2. **frontend/src/types/next-auth.d.ts** (NEW)
   - Added TypeScript type definitions for NextAuth

3. **frontend/.env.local**
   - Updated NEXTAUTH_SECRET to meet minimum length requirement

4. **backend/app/models/__init__.py**
   - Removed duplicate PullRequest model
   - Now imports from code_review.py

5. **backend/app/models/code_review.py**
   - Added missing relationships to PullRequest model

6. **docker-compose.yml**
   - Fixed Neo4j healthcheck

## Troubleshooting

### Backend won't start
- Check if ports 8000, 5432, 6379, 7687 are available
- Verify database services are running: `docker-compose ps`
- Check backend logs for errors

### NextAuth 500 errors
- Ensure backend is running on port 8000
- Check NEXTAUTH_SECRET is set and at least 32 characters
- Verify BACKEND_URL in frontend/.env.local

### Database connection errors
- Ensure docker services are healthy: `docker-compose ps`
- Check credentials match between .env and docker-compose.yml
- Try restarting services: `docker-compose restart`

### Neo4j unhealthy
- Wait 40 seconds for Neo4j to fully start
- Check logs: `docker logs ai-based-quality-check-on-project-code-and-architecture-neo4j-1`
- Verify port 7474 is accessible: `curl http://localhost:7474`

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Next Steps

1. Create a test user using the registration endpoint
2. Test login through the frontend at http://localhost:3000
3. Verify session persistence by refreshing the page
4. Test protected routes and API calls with authentication
