#!/bin/bash

# AI Code Review Platform Development Setup Script

set -e

echo "🚀 Setting up AI Code Review Platform development environment..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18 or higher is required. Current version: $(node -v)"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update the .env file with your actual configuration values"
fi

# Install root dependencies
echo "📦 Installing root dependencies..."
npm install

# Install dependencies for all services
echo "📦 Installing service dependencies..."
npm run build --workspaces

# Create logs directories
echo "📁 Creating log directories..."
mkdir -p services/api-gateway/logs
mkdir -p services/auth-service/logs
mkdir -p services/code-review-engine/logs
mkdir -p services/architecture-analyzer/logs
mkdir -p services/agentic-ai/logs
mkdir -p services/project-manager/logs

# Create certificates directory
echo "🔐 Creating certificates directory..."
mkdir -p certs

# Generate self-signed certificates for SAML (development only)
if [ ! -f certs/saml.crt ]; then
    echo "🔑 Generating self-signed SAML certificates for development..."
    openssl req -x509 -newkey rsa:2048 -keyout certs/saml.key -out certs/saml.crt -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
fi

# Start infrastructure services
echo "🐳 Starting infrastructure services (PostgreSQL, Redis, Neo4j)..."
docker-compose up -d postgres redis neo4j

# Wait for services to be ready
echo "⏳ Waiting for infrastructure services to be ready..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."
docker-compose ps

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Update the .env file with your API keys and configuration"
echo "2. Start all services: npm run docker:up"
echo "3. Or start individual services in development mode:"
echo "   - npm run dev:api-gateway"
echo "   - npm run dev:auth-service"
echo "   - npm run dev:code-review-engine"
echo "   - npm run dev:architecture-analyzer"
echo "   - npm run dev:agentic-ai"
echo "   - npm run dev:project-manager"
echo ""
echo "📊 Service URLs:"
echo "- API Gateway: http://localhost:3000"
echo "- Auth Service: http://localhost:3001"
echo "- Code Review Engine: http://localhost:3002"
echo "- Architecture Analyzer: http://localhost:3003"
echo "- Agentic AI: http://localhost:3004"
echo "- Project Manager: http://localhost:3005"
echo ""
echo "🗄️ Database URLs:"
echo "- PostgreSQL: postgresql://postgres:postgres@localhost:5432/ai_code_review"
echo "- Redis: redis://localhost:6379"
echo "- Neo4j: bolt://localhost:7687 (neo4j/password)"
echo "- Neo4j Browser: http://localhost:7474"