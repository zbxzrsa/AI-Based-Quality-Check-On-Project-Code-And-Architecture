# AI Code Review Platform Development Setup Script (PowerShell)

Write-Host "🚀 Setting up AI Code Review Platform development environment..." -ForegroundColor Green

# Check if Node.js is installed
try {
    $nodeVersion = node -v
    $versionNumber = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
    if ($versionNumber -lt 18) {
        Write-Host "❌ Node.js version 18 or higher is required. Current version: $nodeVersion" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Node.js version check passed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js is not installed. Please install Node.js 18 or higher." -ForegroundColor Red
    exit 1
}

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed. Please install Docker." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose." -ForegroundColor Red
    exit 1
}

# Create environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please update the .env file with your actual configuration values" -ForegroundColor Yellow
}

# Install root dependencies
Write-Host "📦 Installing root dependencies..." -ForegroundColor Blue
npm install

# Install dependencies for all services
Write-Host "📦 Installing service dependencies..." -ForegroundColor Blue
npm run build --workspaces

# Create logs directories
Write-Host "📁 Creating log directories..." -ForegroundColor Blue
$logDirs = @(
    "services/api-gateway/logs",
    "services/auth-service/logs", 
    "services/code-review-engine/logs",
    "services/architecture-analyzer/logs",
    "services/agentic-ai/logs",
    "services/project-manager/logs"
)

foreach ($dir in $logDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Create certificates directory
Write-Host "🔐 Creating certificates directory..." -ForegroundColor Blue
if (-not (Test-Path "certs")) {
    New-Item -ItemType Directory -Path "certs" -Force | Out-Null
}

# Generate self-signed certificates for SAML (development only)
if (-not (Test-Path "certs/saml.crt")) {
    Write-Host "🔑 Generating self-signed SAML certificates for development..." -ForegroundColor Blue
    try {
        openssl req -x509 -newkey rsa:2048 -keyout certs/saml.key -out certs/saml.crt -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    } catch {
        Write-Host "⚠️  OpenSSL not found. Please install OpenSSL or create certificates manually." -ForegroundColor Yellow
    }
}

# Start infrastructure services
Write-Host "🐳 Starting infrastructure services (PostgreSQL, Redis, Neo4j)..." -ForegroundColor Blue
docker-compose up -d postgres redis neo4j

# Wait for services to be ready
Write-Host "⏳ Waiting for infrastructure services to be ready..." -ForegroundColor Blue
Start-Sleep -Seconds 10

# Check if services are healthy
Write-Host "🔍 Checking service health..." -ForegroundColor Blue
docker-compose ps

Write-Host "✅ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 Next steps:" -ForegroundColor Cyan
Write-Host "1. Update the .env file with your API keys and configuration"
Write-Host "2. Start all services: npm run docker:up"
Write-Host "3. Or start individual services in development mode:"
Write-Host "   - npm run dev:api-gateway"
Write-Host "   - npm run dev:auth-service"
Write-Host "   - npm run dev:code-review-engine"
Write-Host "   - npm run dev:architecture-analyzer"
Write-Host "   - npm run dev:agentic-ai"
Write-Host "   - npm run dev:project-manager"
Write-Host ""
Write-Host "📊 Service URLs:" -ForegroundColor Cyan
Write-Host "- API Gateway: http://localhost:3000"
Write-Host "- Auth Service: http://localhost:3001"
Write-Host "- Code Review Engine: http://localhost:3002"
Write-Host "- Architecture Analyzer: http://localhost:3003"
Write-Host "- Agentic AI: http://localhost:3004"
Write-Host "- Project Manager: http://localhost:3005"
Write-Host ""
Write-Host "🗄️ Database URLs:" -ForegroundColor Cyan
Write-Host "- PostgreSQL: postgresql://postgres:postgres@localhost:5432/ai_code_review"
Write-Host "- Redis: redis://localhost:6379"
Write-Host "- Neo4j: bolt://localhost:7687 (neo4j/password)"
Write-Host "- Neo4j Browser: http://localhost:7474"