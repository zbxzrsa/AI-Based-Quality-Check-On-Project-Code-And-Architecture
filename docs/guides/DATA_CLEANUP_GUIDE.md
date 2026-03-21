# Data Cleanup Guide

## Overview

This guide explains how to clean up test data, placeholder content, and false information from the AI Code Review Platform.

## Automated Cleanup Script

### Running the Cleanup Script

```bash
# From project root
cd backend
python scripts/cleanup_test_data.py
```

### What Gets Cleaned

The cleanup script performs the following operations:

#### 1. Database Cleanup (PostgreSQL)
- Removes test users (emails containing 'test' or 'example.com')
- Removes orphaned user roles
- Removes orphaned projects
- Removes orphaned analysis results
- Removes orphaned analysis tasks

#### 2. Redis Cleanup
- Removes all keys containing 'test'
- Clears test JWT tokens
- Clears test session data

#### 3. Neo4j Cleanup
- Removes nodes with test project IDs
- Removes test relationships
- Clears test graph data

#### 4. Environment Files
- Clears sensitive data from `.env` files
- Replaces with template values
- Preserves structure for easy configuration

#### 5. Test Files
- Removes standalone test scripts:
  - `test-auth.py`
  - `backend/test_app.py`
  - `backend/test_minimal_app.py`
  - `backend/test_ast_llm_integration.py`
  - `backend/test_bcrypt_config_startup.py`
  - `backend/test_config.py`
  - `backend/test_jwt_revocation_manual.py`
  - `backend/test_token_type_validation.py`

**Note:** Test files in `backend/tests/` directory are preserved as they are part of the test suite.

## Manual Cleanup Steps

### 1. Environment Configuration

After running the cleanup script, update your environment files with real values:

#### `.env` (Root)
```bash
# Database Configuration
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_code_review
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis Configuration
REDIS_PASSWORD=your_redis_password
REDIS_URL=redis://:password@redis:6379

# Neo4j Configuration
NEO4J_PASSWORD=your_neo4j_password

# Security (Generate secure keys!)
JWT_SECRET=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)

# GitHub Integration
GITHUB_TOKEN=ghp_your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# LLM API Keys (Optional)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

#### `backend/.env`
```bash
# Copy and update values from root .env
POSTGRES_PASSWORD=your_secure_password
NEO4J_PASSWORD=your_neo4j_password
JWT_SECRET=your_jwt_secret
```

#### `frontend/.env.local`
```bash
# Generate a secure NextAuth secret
NEXTAUTH_SECRET=$(openssl rand -base64 32)
```

### 2. Generate Secure Keys

```bash
# JWT Secret (32 bytes hex)
openssl rand -hex 32

# NextAuth Secret (base64)
openssl rand -base64 32

# Webhook Secret
openssl rand -hex 20
```

### 3. Database Reset (Optional)

If you want to completely reset databases:

```bash
# PostgreSQL
docker-compose down -v
docker-compose up -d postgres

# Run migrations
cd backend
alembic upgrade head

# Neo4j
docker-compose down -v
docker-compose up -d neo4j

# Redis
docker-compose down -v
docker-compose up -d redis
```

### 4. Verify Cleanup

```bash
# Check for remaining test data
grep -r "test@example.com" backend/
grep -r "changeme" .env*
grep -r "your-.*-here" .env*

# Check database
psql -U postgres -d ai_code_review -c "SELECT email FROM users WHERE email LIKE '%test%' OR email LIKE '%example.com%';"
```

## What NOT to Clean

The following should be preserved:

### Test Suite Files
- `backend/tests/` - Unit and integration tests
- `frontend/src/__tests__/` - Frontend tests
- `services/*/tests/` - Service tests
- `**/jest.config.js` - Test configurations
- `**/pytest.ini` - Test configurations

### Documentation
- All files in `docs/`
- README files
- API documentation
- Architecture diagrams

### Configuration Templates
- `.env.example` files
- `docker-compose.yml`
- Configuration schemas

### Development Tools
- `.eslintrc.js`
- `.prettierrc`
- `tsconfig.json`
- `pyproject.toml`

## Post-Cleanup Checklist

- [ ] All `.env` files updated with real values
- [ ] Secure keys generated and configured
- [ ] Database connections tested
- [ ] No test users in database
- [ ] No placeholder passwords
- [ ] GitHub token configured (if using GitHub integration)
- [ ] LLM API keys configured (if using LLM features)
- [ ] Application starts successfully
- [ ] Health check endpoint returns healthy status

## Verification Commands

```bash
# Test database connections
python backend/check-services.py

# Test API health
curl http://localhost:8000/health

# Test authentication (should fail without valid user)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
# Expected: 401 Unauthorized

# Check environment variables
env | grep -E "(POSTGRES|REDIS|NEO4J|JWT|GITHUB)" | grep -v "PASSWORD"
```

## Troubleshooting

### Cleanup Script Fails

**Issue:** Database connection errors during cleanup

**Solution:**
```bash
# Ensure databases are running
docker-compose up -d postgres redis neo4j

# Wait for databases to be ready
sleep 10

# Run cleanup again
cd backend
python scripts/cleanup_test_data.py
```

### Environment Variables Not Set

**Issue:** Application fails to start after cleanup

**Solution:**
1. Check `.env` files exist and have values
2. Verify no placeholder values remain
3. Ensure all required variables are set
4. Restart services: `docker-compose restart`

### Test Data Remains

**Issue:** Test data still present after cleanup

**Solution:**
```bash
# Manual database cleanup
psql -U postgres -d ai_code_review << EOF
DELETE FROM users WHERE email LIKE '%test%' OR email LIKE '%example.com%';
DELETE FROM user_roles WHERE user_id NOT IN (SELECT id FROM users);
DELETE FROM projects WHERE created_by NOT IN (SELECT id FROM users);
EOF

# Manual Redis cleanup
redis-cli FLUSHDB

# Manual Neo4j cleanup
cypher-shell -u neo4j -p your_password "MATCH (n) WHERE n.projectId CONTAINS 'test' DETACH DELETE n"
```

## Security Recommendations

After cleanup:

1. **Change all default passwords**
2. **Generate new JWT secrets**
3. **Rotate API keys**
4. **Enable HTTPS in production**
5. **Configure firewall rules**
6. **Enable database authentication**
7. **Set up monitoring and logging**
8. **Regular security audits**

## Backup Before Cleanup

Always backup before running cleanup:

```bash
# Backup PostgreSQL
pg_dump -U postgres ai_code_review > backup_$(date +%Y%m%d).sql

# Backup Neo4j
docker exec neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j_$(date +%Y%m%d).dump

# Backup Redis
redis-cli SAVE
cp /var/lib/redis/dump.rdb backup_redis_$(date +%Y%m%d).rdb
```

## Support

If you encounter issues during cleanup:

1. Check logs: `docker-compose logs`
2. Review error messages
3. Consult documentation
4. Create an issue with details
