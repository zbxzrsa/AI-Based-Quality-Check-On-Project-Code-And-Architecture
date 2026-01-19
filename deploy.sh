#!/bin/bash

# AI Code Review Platform - Production Deployment Script
# This script handles deployment to production environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="./backups"
LOG_FILE="./deployment.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || error "Docker is not installed"
    command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is not installed"
    
    if [[ ! -f ".env" ]]; then
        error ".env file not found. Please create it from .env.example"
    fi
    
    log "Prerequisites check passed ✓"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="backup_$(date +'%Y%m%d_%H%M%S')"
    
    # Backup database
    docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > "$BACKUP_DIR/$BACKUP_NAME.sql" || warn "Database backup failed"
    
    # Backup Neo4j
    docker-compose -f "$COMPOSE_FILE" exec -T neo4j neo4j-admin dump --database=neo4j --to=/tmp/neo4j_backup.dump || warn "Neo4j backup failed"
    docker cp $(docker-compose -f "$COMPOSE_FILE" ps -q neo4j):/tmp/neo4j_backup.dump "$BACKUP_DIR/$BACKUP_NAME.neo4j.dump" || warn "Neo4j backup copy failed"
    
    log "Backup created: $BACKUP_NAME ✓"
}

# Pull latest code
pull_code() {
    log "Pulling latest code from repository..."
    
    git fetch origin
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    if [[ "$CURRENT_BRANCH" != "main" ]]; then
        warn "Not on main branch. Current branch: $CURRENT_BRANCH"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    git pull origin "$CURRENT_BRANCH"
    
    log "Code updated ✓"
}

# Build containers
build_containers() {
    log "Building Docker containers..."
    
    docker-compose -f "$COMPOSE_FILE" build --no-cache --parallel || error "Build failed"
    
    log "Containers built successfully ✓"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Wait for database to be ready
    sleep 5
    
    docker-compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head || error "Migrations failed"
    
    log "Migrations completed ✓"
}

# Start services
start_services() {
    log "Starting services..."
    
    docker-compose -f "$COMPOSE_FILE" up -d || error "Failed to start services"
    
    log "Services started ✓"
}

# Health check
health_check() {
    log "Running health checks..."
    
    # Wait for services to start
    sleep 10
    
    # Check backend health
    for i in {1..30}; do
        if curl -f http://localhost:8000/api/v1/health &>/dev/null; then
            log "Backend health check passed ✓"
            break
        fi
        
        if [[ $i -eq 30 ]]; then
            error "Backend health check failed after 30 attempts"
        fi
        
        sleep 2
    done
    
    # Check frontend
    if curl -f http://localhost:3000 &>/dev/null; then
        log "Frontend health check passed ✓"
    else
        warn "Frontend health check failed"
    fi
    
    log "Health checks completed ✓"
}

# Show service status
show_status() {
    log "Service status:"
    docker-compose -f "$COMPOSE_FILE" ps
}

# Cleanup old images
cleanup() {
    log "Cleaning up old images..."
    
    docker image prune -f
    
    log "Cleanup completed ✓"
}

# Main deployment process
main() {
    log "========================================="
    log "Starting deployment process"
    log "========================================="
    
    check_prerequisites
    create_backup
    pull_code
    build_containers
    start_services
    run_migrations
    health_check
    show_status
    cleanup
    
    log "========================================="
    log "Deployment completed successfully! 🎉"
    log "========================================="
    
    echo ""
    echo "Next steps:"
    echo "1. Verify the application at https://your-domain.com"
    echo "2. Check logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "3. Monitor metrics in Grafana"
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    backup)
        create_backup
        ;;
    rollback)
        log "Rolling back to previous version..."
        docker-compose -f "$COMPOSE_FILE" down
        # Restore backup logic here
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {deploy|backup|rollback|status}"
        exit 1
        ;;
esac
