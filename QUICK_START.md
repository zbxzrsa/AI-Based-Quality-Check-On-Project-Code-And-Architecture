# Quick Start Guide

## Current Status

✅ **Infrastructure Services Running:**
- PostgreSQL 16 (port 5432) - Healthy
- Redis 7 (port 6379) - Healthy  
- Neo4j 5.15 (ports 7474, 7687) - Starting

✅ **Backend Already Running:**
- FastAPI backend is running on port 8000

## Next Steps

### 1. Test the Backend Authentication

Run the test script to verify auth is working:

```bash
python test-auth.py
```

This will:
- Register a test user (test@example.com / Test@1234)
- Login and get access token
- Fetch user details

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:3000

### 3. Test the Full Flow

1. Open http://localhost:3000 in your browser
2. Try to sign in (you'll be redirected to the sign-in page)
3. Use the test credentials:
   - Email: test@example.com
   - Password: Test@1234

## Troubleshooting

### If Backend is Not Responding

Check if it's running:
```bash
curl http://localhost:8000/health
```

If not running, start it:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### If You Get 500 Errors

1. Check backend logs
2. Verify all infrastructure services are healthy:
   ```bash
   docker-compose ps
   ```
3. Run the service check script:
   ```bash
   python check-services.py
   ```

### Clean Orphan Containers

If you see warnings about orphan containers:
```bash
docker-compose down --remove-orphans
docker-compose up -d postgres redis neo4j
```

## API Endpoints

- Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- Register: POST http://localhost:8000/api/v1/auth/register
- Login: POST http://localhost:8000/api/v1/auth/login
- Get User: GET http://localhost:8000/api/v1/auth/me

## Environment Files

### Frontend (.env.local)
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-key-change-in-production-min-32-chars-required
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
```

### Backend (.env)
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_code_review
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=password

JWT_SECRET=test_secret_key_for_development_only
```

## What Was Fixed

1. ✅ NextAuth API endpoint paths corrected
2. ✅ Response format handling fixed
3. ✅ TypeScript types added
4. ✅ Duplicate PullRequest model removed
5. ✅ PostgreSQL version updated to 16
6. ✅ Neo4j healthcheck fixed

See `NEXTAUTH_SETUP_GUIDE.md` for detailed information.
