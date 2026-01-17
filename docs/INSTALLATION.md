# Installation Guide

Complete setup instructions for the AI-Based Quality Check system.

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows (WSL2)
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB free space

### Required Software
- **Docker**: 20.10+ with Docker Compose
- **Node.js**: 18.0+ with npm
- **Python**: 3.11+
- **Git**: 2.30+

### Optional (for AI features)
- **Ollama**: For local AI model serving
- **Git LFS**: For large model files

## Quick Start with Docker

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd ai-code-review-system

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Redis Commander**: http://localhost:8081

## Manual Installation

For development or custom deployments:

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the backend server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# Edit .env.local with your configuration

# Start the development server
npm run dev
```

### 3. Database Setup

#### Neo4j
```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5

# Or install locally from https://neo4j.com/download/
```

#### PostgreSQL
```bash
# Using Docker
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=ai_code_review \
  postgres:15

# Or install locally
```

#### Redis
```bash
# Using Docker
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Or install locally
```

### 4. Celery Worker Setup

```bash
# Start Celery worker for async tasks
cd backend
celery -A app.celery_config worker --loglevel=info

# Start Celery Beat for scheduled tasks
celery -A app.celery_config beat --loglevel=info
```

## Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database Configuration
POSTGRES_URL=postgresql+asyncpg://user:password@localhost:5432/ai_code_review
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=your-super-secret-jwt-key-here
OPENAI_API_KEY=sk-your-openai-api-key

# Application
APP_ENV=development
LOG_LEVEL=INFO
```

#### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=development
NEXT_PUBLIC_GITHUB_CLIENT_ID=your-github-client-id
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

### Ollama Setup (Optional)

For AI-powered features:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the required model
ollama pull qwen2.5-coder

# Verify installation
ollama list

# Start Ollama service (runs automatically)
```

## Verification

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connections
curl http://localhost:8000/api/v1/health/db

# Frontend
curl http://localhost:3000
```

### Test Execution

```bash
# Backend tests
cd backend && pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Integration tests
cd backend && python -m pytest tests/ -k "integration"
```

## Production Deployment

### Docker Compose (Recommended)

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d

# Scale workers as needed
docker-compose up -d --scale celery-worker-high=3
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
kubectl get services
```

### Cloud Deployment

#### AWS
```bash
# Using ECS
aws ecs create-cluster --cluster-name ai-review-cluster
aws ecs create-service --cluster ai-review-cluster --service-name ai-review-service --task-definition ai-review-task

# Using EKS
eksctl create cluster -f k8s/cluster.yaml
kubectl apply -f k8s/
```

#### Google Cloud
```bash
# Using Cloud Run
gcloud builds submit --tag gcr.io/project/ai-review
gcloud run deploy ai-review --image gcr.io/project/ai-review

# Using GKE
gcloud container clusters create ai-review-cluster
kubectl apply -f k8s/
```

#### Azure
```bash
# Using AKS
az aks create --resource-group ai-review-rg --name ai-review-cluster
kubectl apply -f k8s/

# Using App Service
az webapp up --name ai-review --resource-group ai-review-rg
```

## Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using ports
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :7687  # Neo4j
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Change ports in docker-compose.yml or .env files
```

#### Database Connection Issues
```bash
# Test Neo4j connection
curl http://localhost:7474/

# Test PostgreSQL connection
psql postgresql://user:password@localhost:5432/ai_code_review

# Test Redis connection
redis-cli ping
```

#### Memory Issues
```bash
# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Advanced

# Add memory limits to docker-compose.yml
services:
  frontend:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

#### Build Failures
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check build logs
docker-compose build --progress=plain
```

### Logs and Debugging

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Backend application logs
docker-compose exec backend tail -f /app/logs/app.log

# Database logs
docker-compose logs -f neo4j
```

### Performance Tuning

```bash
# Database optimization
docker-compose exec neo4j neo4j-admin database info

# Redis monitoring
docker-compose exec redis redis-cli info

# Application profiling
python -m cProfile -s time app/main.py
```

## Security Setup

### SSL/TLS Configuration

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Configure Nginx (if using)
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

### Secrets Management

```bash
# Use Docker secrets
echo "your-secret-password" | docker secret create db_password -

# Or use environment variables with .env files
# Never commit .env files to version control
```

### Firewall Configuration

```bash
# Allow only necessary ports
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw allow 7687  # Neo4j (internal only)
ufw allow 5432  # PostgreSQL (internal only)
ufw allow 6379  # Redis (internal only)
ufw --force enable
```

## Monitoring Setup

### Application Monitoring

```bash
# Install monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3001

# Access Prometheus
open http://localhost:9090
```

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/api/v1/health/db

# Worker health
celery -A app.celery_config inspect active
```

## Backup and Recovery

### Database Backups

```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U postgres ai_code_review > backup.sql

# Neo4j backup
docker-compose exec neo4j neo4j-admin database dump neo4j

# Automated backups
0 2 * * * docker-compose exec postgres pg_dump -U postgres ai_code_review > /backups/$(date +\%Y\%m\%d).sql
```

### Configuration Backup

```bash
# Backup environment files
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env* docker-compose*.yml k8s/
```

## Support

### Getting Help

1. **Check the logs**: `docker-compose logs -f`
2. **Review documentation**: See [docs/](docs/) directory
3. **Check GitHub Issues**: Search existing issues
4. **Create an issue**: If problem persists

### Community Support

- **GitHub Discussions**: For questions and discussions
- **Discord**: Real-time community support
- **Documentation**: Comprehensive guides in [docs/](docs/)

---

## Quick Reference

### Development Commands
```bash
# Start development environment
docker-compose up -d

# Run tests
cd backend && pytest tests/ -v
cd frontend && npm test

# Check health
curl http://localhost:8000/health
curl http://localhost:3000

# View logs
docker-compose logs -f backend
```

### Production Commands
```bash
# Deploy to production
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale celery-worker-high=3

# Update deployment
docker-compose pull && docker-compose up -d

# Backup data
docker-compose exec postgres pg_dump -U postgres ai_code_review > backup.sql
```

### Troubleshooting Commands
```bash
# Check service status
docker-compose ps

# Restart services
docker-compose restart

# Clean up
docker-compose down -v
docker system prune -a

# Debug builds
docker-compose build --progress=plain
```

---

**Installation completed successfully!** 🎉

Visit http://localhost:3000 to access your AI-Based Quality Check system.
