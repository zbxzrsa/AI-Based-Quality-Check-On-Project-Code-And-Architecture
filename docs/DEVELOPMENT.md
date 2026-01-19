# Development Guide

This guide covers the development setup and workflow for the AI-powered code review and architecture analysis platform.

## Prerequisites

- Node.js 18 or higher
- Docker and Docker Compose
- Git
- OpenSSL (for generating development certificates)

## Quick Start

1. **Clone and setup the project:**
   ```bash
   # Run the setup script
   ./scripts/setup-dev.sh  # Linux/macOS
   # or
   .\scripts\setup-dev.ps1  # Windows PowerShell
   ```

2. **Configure environment variables:**
   ```bash
   # Copy and edit the environment file
   cp .env.example .env
   # Update with your API keys and configuration
   ```

3. **Start the development environment:**
   ```bash
   # Start all services with Docker
   npm run docker:up
   
   # Or start services individually in development mode
   npm run dev:api-gateway
   npm run dev:auth-service
   npm run dev:code-review-engine
   npm run dev:architecture-analyzer
   npm run dev:agentic-ai
   npm run dev:project-manager
   ```

## Architecture Overview

The platform follows a microservices architecture with the following services:

### Core Services

- **API Gateway** (Port 3000): Entry point, routing, authentication
- **Auth Service** (Port 3001): User authentication and authorization
- **Code Review Engine** (Port 3002): Code analysis and review generation
- **Architecture Analyzer** (Port 3003): Dependency analysis and graph management
- **Agentic AI** (Port 3004): AI-powered analysis and recommendations
- **Project Manager** (Port 3005): Project lifecycle and task management

### Infrastructure Services

- **PostgreSQL** (Port 5432): Primary database for users, projects, and analysis results
- **Redis** (Port 6379): Caching and message queues
- **Neo4j** (Port 7474/7687): Graph database for architectural relationships

## Development Workflow

### Service Development

Each service is independently developed and can be run in isolation:

```bash
# Navigate to a service directory
cd services/api-gateway

# Install dependencies
npm install

# Run in development mode
npm run dev

# Run tests
npm test

# Run property-based tests
npm run test:property

# Build for production
npm run build
```

### Shared Code

Common types and interfaces are located in the `shared/` directory:

- `shared/types/`: TypeScript type definitions
- `shared/interfaces/`: Service interface definitions

### Database Management

The PostgreSQL database is automatically initialized with the schema defined in `scripts/init-db.sql`.

To connect to the database:
```bash
# Using psql
psql postgresql://postgres:postgres@localhost:5432/ai_code_review

# Using Docker
docker-compose exec postgres psql -U postgres -d ai_code_review
```

### Graph Database (Neo4j)

Neo4j is used for storing architectural relationships and dependencies.

Access the Neo4j browser at: http://localhost:7474
- Username: neo4j
- Password: password

### Redis

Redis is used for caching and inter-service communication.

Connect to Redis:
```bash
# Using redis-cli
redis-cli -h localhost -p 6379

# Using Docker
docker-compose exec redis redis-cli
```

## Testing

The platform uses a comprehensive testing strategy:

### Unit Tests

```bash
# Run all unit tests
npm test

# Run tests for a specific service
npm test -w services/api-gateway

# Run tests in watch mode
npm run test:watch
```

### Property-Based Tests

Property-based tests validate universal correctness properties:

```bash
# Run all property-based tests
npm run test:property

# Run property tests for a specific service
npm run test:property -w services/code-review-engine
```

### Integration Tests

Integration tests verify end-to-end functionality:

```bash
# Start all services first
npm run docker:up

# Run integration tests
npm run test:integration
```

## Code Quality

### Linting and Formatting

```bash
# Lint all services
npm run lint

# Format all code
npm run format

# Fix linting issues
npm run lint -- --fix
```

### TypeScript

All services use strict TypeScript configuration:
- Strict type checking enabled
- No implicit any
- Unused variables/parameters detection
- Exact optional property types

## Environment Configuration

Key environment variables:

### Database Configuration
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_code_review
REDIS_URL=redis://localhost:6379
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### API Keys
```env
GITHUB_ACCESS_TOKEN=your-github-token
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### Security
```env
JWT_SECRET=your-jwt-secret
GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

## Service Communication

Services communicate through:

1. **HTTP APIs**: Synchronous request/response
2. **Redis Pub/Sub**: Asynchronous messaging
3. **Shared Database**: Data persistence

### API Gateway Routing

The API Gateway routes requests to appropriate services:

- `/api/auth/*` → Auth Service
- `/api/code-review/*` → Code Review Engine
- `/api/architecture/*` → Architecture Analyzer
- `/api/ai/*` → Agentic AI Service
- `/api/projects/*` → Project Manager

### Authentication Flow

1. Client authenticates with Auth Service
2. Auth Service returns JWT token
3. API Gateway validates token for protected routes
4. User context is passed to downstream services

## Debugging

### Service Logs

Each service logs to its own directory:
```bash
# View logs
tail -f services/api-gateway/logs/combined.log
tail -f services/auth-service/logs/error.log
```

### Docker Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api-gateway
```

### Health Checks

Each service provides health check endpoints:
- http://localhost:3000/health (API Gateway)
- http://localhost:3001/health (Auth Service)
- http://localhost:3002/health (Code Review Engine)
- http://localhost:3003/health (Architecture Analyzer)
- http://localhost:3004/health (Agentic AI)
- http://localhost:3005/health (Project Manager)

## Performance Monitoring

### Metrics Collection

Services expose metrics for monitoring:
- Request/response times
- Error rates
- Database query performance
- Queue processing metrics

### Load Testing

```bash
# Install load testing tools
npm install -g artillery

# Run load tests
artillery run tests/load/api-gateway.yml
```

## Deployment

### Docker Build

```bash
# Build all services
npm run docker:build

# Build specific service
docker build -t ai-code-review/api-gateway services/api-gateway
```

### Production Configuration

For production deployment:
1. Use environment-specific configuration
2. Enable HTTPS/TLS
3. Configure proper secrets management
4. Set up monitoring and alerting
5. Configure backup strategies

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000-3005, 5432, 6379, 7474, 7687 are available
2. **Docker issues**: Restart Docker daemon, check disk space
3. **Database connection**: Verify PostgreSQL is running and accessible
4. **Redis connection**: Check Redis service status
5. **Neo4j connection**: Ensure Neo4j is started and credentials are correct

### Service Dependencies

Service startup order:
1. Infrastructure services (PostgreSQL, Redis, Neo4j)
2. Auth Service
3. Other application services
4. API Gateway

### Memory Requirements

Minimum system requirements:
- 8GB RAM
- 4 CPU cores
- 20GB disk space

## Contributing

1. Follow the established code style and patterns
2. Write comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all services pass health checks
5. Test integration between services

## Support

For development support:
- Check service logs for error details
- Verify environment configuration
- Ensure all dependencies are installed
- Test individual services in isolation