# AI Code Review Platform

A full-stack web application for AI-powered code review and architecture analysis with graph database visualization.

## 🏗️ Technology Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Form Management**: React Hook Form + Zod
- **Graph Visualization**: React Force Graph, D3.js
- **Real-time**: Socket.io Client

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn with async support
- **Task Queue**: Celery + Redis
- **Authentication**: JWT (python-jose)
- **Code Analysis**: AST parsers, tree-sitter

### Databases
- **PostgreSQL**: User data, projects, audit logs, review history
- **Neo4j**: AST graphs, dependency graphs, architectural relationships
- **Redis**: Session cache, task queues, temporary analysis results

### DevOps
- **Containerization**: Docker + Docker Compose
- **Code Quality**: ESLint, Prettier, Black, isort, mypy

## 📋 Prerequisites

- **Docker** and **Docker Compose** (v2.0+)
- **Node.js** 18+ (for local development)
- **Python** 3.11+ (for local development)
- **Git**

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AI-Based\ Quality\ Check\ On\ Project\ Code\ And\ Architecture
```

### 2. Configure Environment Variables

Copy the example environment file and update with your values:

```bash
cp .env.example .env
```

**Important**: Update the following variables in `.env`:
- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `NEO4J_PASSWORD`: Strong password for Neo4j
- `REDIS_PASSWORD`: Strong password for Redis
- `JWT_SECRET`: Random secret key for JWT (use: `openssl rand -hex 32`)
- `GITHUB_TOKEN`: Your GitHub personal access token
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: Your AI API key

### 3. Start All Services with Docker Compose

```bash
docker-compose up -d
```

This will start:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Neo4j Browser**: http://localhost:7474
- **Redis**: localhost:6379

### 4. Verify Services

```bash
# Check all containers are running
docker-compose ps

# View logs
docker-compose logs -f

# Check individual service logs
docker-compose logs backend
docker-compose logs frontend
```

### 5. Test Database Connections

Access the backend container and run the test script:

```bash
docker-compose exec backend python tests/test_connections.py
```

You should see:
```
✅ PostgreSQL connection successful
✅ Neo4j connection successful
✅ Redis connection successful
```

## 🧪 Testing the API

### Health Check

```bash
curl http://localhost:8000/health
```

### Detailed Health Check

```bash
curl http://localhost:8000/api/v1/health/detailed
```

### Test All Databases

```bash
curl http://localhost:8000/api/v1/database/test/all
```

### Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI with all available endpoints.

## 📁 Project Structure

```
.
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/             # Next.js app router pages
│   │   ├── components/      # React components
│   │   ├── lib/             # Utilities and API client
│   │   ├── hooks/           # Custom React hooks
│   │   ├── types/           # TypeScript type definitions
│   │   └── styles/          # Global styles
│   ├── public/              # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
│
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── api/             # API routes
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       └── router.py
│   │   ├── core/            # Core configuration
│   │   │   └── config.py
│   │   ├── database/        # Database connections
│   │   │   ├── postgresql.py
│   │   │   ├── neo4j_db.py
│   │   │   └── redis_db.py
│   │   ├── models/          # Data models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Celery tasks
│   │   └── main.py          # FastAPI app entry point
│   ├── database/
│   │   └── init_scripts/    # Database initialization SQL
│   ├── tests/
│   │   └── test_connections.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml        # Multi-service orchestration
├── .env.example             # Environment variables template
├── .gitignore
└── README.md
```

## 💻 Local Development (Without Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start databases with Docker (or use local installations)
docker-compose up -d postgres neo4j redis

# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (in another terminal)
celery -A app.tasks.celery_app worker --loglevel=info
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

## 🔧 Development Commands

### Frontend

```bash
cd frontend

npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run format       # Format code with Prettier
npm run type-check   # TypeScript type checking
```

### Backend

```bash
cd backend

# Code formatting
black .
isort .

# Type checking
mypy app

# Linting
flake8 app
pylint app

# Run tests
pytest
pytest --cov=app tests/
```

## 🗄️ Database Management

### PostgreSQL

```bash
# Access PostgreSQL CLI
docker-compose exec postgres psql -U admin -d ai_code_review

# Backup database
docker-compose exec postgres pg_dump -U admin ai_code_review > backup.sql

# Restore database
docker-compose exec -T postgres psql -U admin ai_code_review < backup.sql
```

### Neo4j

Access Neo4j Browser at http://localhost:7474
- Username: `neo4j`
- Password: (from `.env` file)

```cypher
// Create sample node
CREATE (n:CodeNode {id: 'test', name: 'TestNode'}) RETURN n;

// Query all nodes
MATCH (n) RETURN n LIMIT 25;
```

### Redis

```bash
# Access Redis CLI
docker-compose exec redis redis-cli -a your_redis_password

# Test commands
SET test "Hello Redis"
GET test
```

## 🚢 Production Deployment

### Build Production Images

```bash
docker-compose -f docker-compose.yml build --no-cache
```

### AWS EC2 Deployment

1. **Launch EC2 Instance**: Ubuntu 22.04 LTS, t3.medium or larger
2. **Install Docker and Docker Compose**
3. **Configure Security Groups**: Open ports 80, 443, 3000, 8000
4. **Set up environment variables** in `.env`
5. **Deploy**:

```bash
docker-compose up -d
```

6. **Set up Nginx reverse proxy** (optional but recommended)
7. **Configure SSL with Let's Encrypt**

## 📊 System Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture diagram and component descriptions.

## 🔐 Security Considerations

- Change all default passwords in `.env`
- Use strong JWT secrets
- Enable HTTPS in production
- Implement rate limiting
- Regular security updates
- Backup databases regularly
- Use environment-specific configurations

## 📝 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

[Your License Here]

## 🆘 Troubleshooting

### Container Issues

```bash
# Stop all containers
docker-compose down

# Remove all containers and volumes (⚠️ WARNING: Deletes all data)
docker-compose down -v

# Rebuild containers
docker-compose up -d --build
```

### Database Connection Issues

1. Check if containers are running: `docker-compose ps`
2. Check logs: `docker-compose logs [service-name]`
3. Verify environment variables in `.env`
4. Test connections: `docker-compose exec backend python tests/test_connections.py`

### Frontend Build Issues

```bash
cd frontend
rm -rf node_modules .next
npm install
npm run build
```

## 📧 Support

For support, please open an issue in the GitHub repository.
