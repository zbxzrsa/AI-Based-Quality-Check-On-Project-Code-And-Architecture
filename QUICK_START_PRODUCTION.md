# Quick Start - Production Deployment

## Prerequisites
- Docker Engine 24.0+
- Docker Compose 2.20+
- 8GB RAM minimum (16GB recommended)
- 50GB disk space

## 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd AI-Based-Quality-Check-On-Project-Code-And-Architecture

# Copy production environment template
cp .env.production.template .env.production

# Generate secure keys
openssl rand -hex 32  # Use for JWT_SECRET
openssl rand -hex 32  # Use for SECRET_KEY
openssl rand -hex 32  # Use for SESSION_SECRET

# Edit .env.production with your values
nano .env.production
```

## 2. SSL Certificates

### For Development (Self-Signed)
```bash
# Already configured - certificates exist in nginx/ssl/
# Skip to step 3
```

### For Production (Let's Encrypt)
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com

# Copy to nginx directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
```

## 3. Deploy

### Option A: Development/Testing
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Option B: Production
```bash
# Build production images
docker build -f backend/Dockerfile.prod -t ai-review-backend:prod ./backend
docker build -f frontend/Dockerfile.prod -t ai-review-frontend:prod ./frontend

# Start with production configuration
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

## 4. Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend health
curl http://localhost:6066/api/health

# Access services
# Frontend: http://localhost:6066
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474
# pgAdmin: http://localhost:5050
```

## 5. Run Database Migrations

```bash
# Development
docker-compose exec backend alembic upgrade head

# Production
docker-compose -f docker-compose.production.yml exec backend alembic upgrade head
```

## Common Commands

### Service Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend

# Check resource usage
docker stats
```

### Database Operations
```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U postgres ai_review > backup.sql

# PostgreSQL restore
cat backup.sql | docker-compose exec -T postgres psql -U postgres ai_review

# Access PostgreSQL
docker-compose exec postgres psql -U postgres ai_review

# Access Neo4j shell
docker-compose exec neo4j cypher-shell -u neo4j -p your_password
```

### Troubleshooting
```bash
# Check all container status
docker-compose ps

# View all logs
docker-compose logs -f

# Restart all services
docker-compose restart

# Clean restart (removes volumes - WARNING: data loss)
docker-compose down -v
docker-compose up -d
```

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:6066 | - |
| Backend API | http://localhost:8000 | - |
| API Documentation | http://localhost:8000/docs | - |
| Neo4j Browser | http://localhost:7474 | neo4j / (from .env) |
| pgAdmin | http://localhost:5050 | admin@example.com / (from .env) |
| Nginx (HTTP) | http://localhost:8080 | - |
| Nginx (HTTPS) | https://localhost:8443 | - |

## Environment Variables

Key variables to configure in `.env.production`:

```bash
# Database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_review_prod

# Security
JWT_SECRET=your_jwt_secret_here
SECRET_KEY=your_secret_key_here
SESSION_SECRET=your_session_secret_here

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_TOKEN=your_github_token

# Neo4j
NEO4J_AUTH=neo4j/your_neo4j_password
```

## Health Checks

All services include health checks:
- **Backend**: Checks every 30s, starts after 40s
- **Frontend**: Checks every 30s, starts after 10s
- **PostgreSQL**: Checks every 5s, starts after 10s
- **Redis**: Checks every 5s
- **Neo4j**: Checks every 10s, starts after 60s

## Resource Limits (Production)

| Service | Memory | CPU |
|---------|--------|-----|
| Backend | 1GB | 2 cores |
| Frontend | 512MB | 1 core |
| PostgreSQL | 1GB | 1 core |
| Neo4j | 512MB | 1 core |
| Redis | 256MB | 0.5 cores |
| Celery Worker | 1GB | 1 core |

## Backup Strategy

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# PostgreSQL
docker-compose exec -T postgres pg_dump -U postgres ai_review | \
  gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Neo4j
docker-compose exec neo4j neo4j-admin database dump neo4j \
  --to-path=/backups

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

# Run backup
./backup.sh

# Schedule daily backups (crontab)
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

## Monitoring

### Performance Dashboard
Access at: http://localhost:6066/performance

Monitors:
- API response times
- Database query performance
- Cache hit rates
- System resource usage

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Follow with timestamps
docker-compose logs -f -t backend
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure random keys
- [ ] Configure GitHub OAuth credentials
- [ ] Set up SSL certificates (production)
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Review security headers in nginx.conf
- [ ] Set up automated backups
- [ ] Configure monitoring and alerting

## Next Steps

1. Review [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment guide
2. Check [PRODUCTION_CHANGES.md](./PRODUCTION_CHANGES.md) for all changes
3. Set up monitoring and alerting
4. Configure automated backups
5. Implement CI/CD pipeline

## Support

- **Documentation**: See `/docs` directory
- **Logs**: `docker-compose logs -f`
- **Health**: Check `/health` and `/api/health` endpoints
- **Performance**: Access `/performance` dashboard

## Troubleshooting Quick Fixes

### Services won't start
```bash
docker-compose down
docker-compose up -d
docker-compose logs -f
```

### Database connection errors
```bash
docker-compose restart postgres
docker-compose exec postgres pg_isready
```

### High memory usage
```bash
docker stats
# Adjust limits in docker-compose.yml
docker-compose up -d
```

### SSL certificate errors
```bash
# Regenerate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem
docker-compose restart nginx
```
