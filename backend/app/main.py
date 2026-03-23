"""
Main FastAPI application entry point
"""
import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging_config import setup_logging, log_request
from app.api.v1.router import api_router
from app.api.exception_handlers import register_exception_handlers
from app.database.postgresql import init_postgres, close_postgres, get_db
from app.database.neo4j_db import init_neo4j, close_neo4j
from app.database.redis_db import init_redis, close_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging(level=settings.LOG_LEVEL, enable_json=True)
    
    # Skip database initialization during testing as it's handled by fixtures
    testing = os.environ.get("TESTING") == "true"
    
    # Initialize OpenTelemetry tracing if enabled (Requirement 18.1) - skip in testing
    if not testing and settings.is_tracing_enabled():
        from app.core.tracing import setup_tracing
        tracing_config = setup_tracing(
            service_name=settings.PROJECT_NAME,
            service_version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            otlp_endpoint=settings.OTLP_ENDPOINT,
            enable_console_export=settings.TRACING_CONSOLE_EXPORT,
            sample_rate=settings.TRACING_SAMPLE_RATE,
        )
        # Instrument HTTP clients
        tracing_config.instrument_httpx()
        tracing_config.instrument_redis()
    
    # Setup graceful shutdown handler (Requirement 12.10)
    from app.services.graceful_shutdown import setup_graceful_shutdown
    shutdown_handler = setup_graceful_shutdown(shutdown_timeout=30)
    
    # testing flag already set above
    
    # Run security validation first (Critical)
    if not testing:
        logger.info("Running security validation...")
        try:
            from app.core.security_validator import SecurityValidator
            SecurityValidator.validate_startup()
            logger.info("✅ Security validation passed")
        except Exception as e:
            logger.error("❌ Security validation failed: %s", str(e))
            if settings.ENVIRONMENT == "production":
                logger.critical("Blocking application startup due to security issues")
                raise e
            else:
                logger.warning("Continuing in development mode despite security issues")
    
    # Run comprehensive startup validation (Requirement 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7)
    if not testing:
        logger.info("Running startup validation...")
        try:
            from app.services.startup_validation import run_startup_validation
            validation_result = await run_startup_validation()
            if validation_result and not validation_result.is_valid:
                logger.warning("Startup validation failed but continuing: %s", validation_result.errors)
        except Exception as e:
            logger.warning("Startup validation error (continuing): %s", str(e))
            validation_result = None
    else:
        logger.info("Testing mode: Skipping startup validation")
        validation_result = None
    
    # Initialize databases with timeout and graceful degradation
    db_status = {}
    postgres_available = False
    
    if not testing:
        # PostgreSQL - Critical for application (增加重试机制)
        postgres_retries = 3
        for attempt in range(postgres_retries):
            try:
                timeout = 30 + (attempt * 15)  # 递增超时时间
                await asyncio.wait_for(init_postgres(), timeout=timeout)
                db_status["PostgreSQL"] = {"is_connected": True, "response_time_ms": 0}
                postgres_available = True
                logger.info("✅ PostgreSQL connected successfully")
                break
            except asyncio.TimeoutError:
                if attempt < postgres_retries - 1:
                    logger.warning(f"⚠️ PostgreSQL connection timeout (attempt {attempt + 1}/{postgres_retries}), retrying...")
                    await asyncio.sleep(5)  # 等待5秒后重试
                else:
                    db_status["PostgreSQL"] = {"is_connected": False, "error": "Connection timeout after retries"}
                    logger.error("❌ PostgreSQL connection timeout after all retries - backend will be degraded")
            except Exception as e:
                if attempt < postgres_retries - 1:
                    logger.warning(f"⚠️ PostgreSQL connection failed (attempt {attempt + 1}/{postgres_retries}): {str(e)[:100]}, retrying...")
                    await asyncio.sleep(5)
                else:
                    db_status["PostgreSQL"] = {"is_connected": False, "error": str(e)[:50]}
                    logger.error("❌ PostgreSQL connection failed after all retries: %s", str(e)[:100])
        
        # Redis - Optional for caching (移到Neo4j之前，因为更重要)
        try:
            await asyncio.wait_for(init_redis(), timeout=15)
            db_status["Redis"] = {"is_connected": True, "response_time_ms": 0}
            logger.info("✅ Redis connected successfully")
        except asyncio.TimeoutError:
            db_status["Redis"] = {"is_connected": False, "error": "Connection timeout"}
            logger.warning("⚠️ Redis connection timeout - caching disabled")
        except Exception as e:
            db_status["Redis"] = {"is_connected": False, "error": str(e)[:50]}
            logger.warning("⚠️ Redis not available: %s", str(e)[:100])
        
        # Neo4j - Optional for graph features
        try:
            await asyncio.wait_for(init_neo4j(), timeout=30)
            db_status["Neo4j"] = {"is_connected": True, "response_time_ms": 0}
            logger.info("✅ Neo4j connected successfully")
        except asyncio.TimeoutError:
            db_status["Neo4j"] = {"is_connected": False, "error": "Connection timeout"}
            logger.warning("⚠️ Neo4j connection timeout - graph features disabled")
        except Exception as e:
            db_status["Neo4j"] = {"is_connected": False, "error": str(e)[:50]}
            logger.warning("⚠️ Neo4j not available: %s", str(e)[:100])
    else:
        logger.info("Testing mode: Skipping database initialization in lifespan")
        postgres_available = True # Assume available as it's handled by fixtures
    
    # Apply database migrations if PostgreSQL is available (skip in testing)
    if postgres_available and not testing:
        try:
            from app.database.migration_manager import get_migration_manager
            migration_manager = get_migration_manager()
            
            logger.info("Checking for pending migrations...")
            migration_status = await migration_manager.get_migration_status()
            logger.info("Migration status: %s", str(migration_status))
            
            if migration_status.pending_count > 0:
                logger.info("Applying %d pending migration(s)...", migration_status.pending_count)
                migration_status = await migration_manager.apply_pending_migrations()
                logger.info("Migration result: %s", str(migration_status))
                
                if migration_status.errors:
                    logger.error("Migration errors: %s", migration_status.errors)
                    for error in migration_status.errors:
                        logger.error("   Error: %s", error)
                    logger.warning("Some migrations failed, but continuing startup")
            else:
                logger.info("Database is up to date")
        except Exception as e:
            logger.warning("Error during migration: %s", str(e), exc_info=True)
    
    # Create default test user if not exists
    if postgres_available and not testing:
        try:
            from sqlalchemy import select
            from app.models import User, UserRole
            from app.utils.password import hash_password
            import uuid
            
            async for db in get_db():
                stmt = select(User).where(User.email == "admin@example.com")
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if not existing_user:
                    default_user = User(
                        id=uuid.uuid4(),
                        email="admin@example.com",
                        password_hash=hash_password("Admin123!"),
                        role=UserRole.ADMIN,
                        full_name="Admin User",
                        is_active=True
                    )
                    db.add(default_user)
                    await db.commit()
                    logger.info("Default test user created: admin@example.com / Admin123!")
                else:
                    logger.info("Default test user already exists")
                break
        except Exception as e:
            logger.warning("Could not create default user: %s", str(e))
    
    # Authentication system uses module-level settings import
    try:
        logger.info("Authentication initialized (JWT expiry: %d hours)", settings.JWT_EXPIRATION_HOURS)
    except Exception as e:
        logger.warning("Authentication initialization warning: %s", str(e))
    
    # Log startup summary (Requirement 11.1, 11.2, 11.3, 11.4, 11.5, 11.6)
    from app.core.logging_config import log_startup_summary, log_database_status
    
    # Log database status with masking
    log_database_status(db_status, logger)
    
    features_enabled = {
        "GitHub Integration": settings.is_github_integration_enabled(),
        "DeepSeek AI": settings.is_deepseek_enabled(),
        "OpenAI": settings.is_openai_enabled(),
        "Anthropic": settings.is_anthropic_enabled(),
        "Ollama Local LLM": settings.is_ollama_enabled(),
        "Celery": settings.is_celery_enabled(),
    }
    
    security_warnings = settings.validate_security_settings()
    
    log_startup_summary(
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        config_file=".env",
        database_status=db_status,
        features_enabled=features_enabled,
        security_warnings=security_warnings if security_warnings else None
    )
    
    yield
    
    logger.info("Application shutdown initiated...")
    
    # The graceful shutdown handler will handle:
    # - Completing in-flight requests
    # - Closing database connections cleanly
    # - Stopping background tasks
    
    # Close database connections (gracefully handled if connections weren't established)
    if not testing:
        try:
            await close_postgres()
        except Exception as e:
            logger.warning(f"Error closing PostgreSQL: {e}")
        
        try:
            await close_neo4j()
        except Exception as e:
            logger.warning(f"Error closing Neo4j: {e}")
        
        try:
            await close_redis()
        except Exception as e:
            logger.warning(f"Error closing Redis: {e}")
    
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
# AI-Based Code Review and Architecture Analysis Platform

An intelligent web-based platform that automates code review and architectural analysis using:
- **AST Parsing**: Abstract Syntax Tree analysis for code structure
- **Neo4j Graph Database**: Dependency graphs and architectural relationships
- **LLM Integration**: GPT-4, Claude 3.5, and Ollama for intelligent analysis
- **GitHub Integration**: Automated PR reviews via webhooks

## Features

- 🔍 **Automated Code Review**: AI-powered analysis of pull requests
- 🏗️ **Architecture Analysis**: Detect patterns, circular dependencies, and drift
- 📊 **Metrics & Visualization**: Interactive dependency graphs and quality metrics
- 🔐 **Enterprise Security**: RBAC, JWT authentication, audit logging
- 📈 **Monitoring**: Prometheus metrics, distributed tracing, health checks

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### Getting Started with Authentication

1. **Register a new user** (if you don't have an account):
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register" \\
     -H "Content-Type: application/json" \\
     -d '{
       "email": "user@example.com",
       "password": "SecurePassword123!",
       "full_name": "John Doe"
     }'
   ```

2. **Login to get your JWT token**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{
       "email": "user@example.com",
       "password": "SecurePassword123!"
     }'
   ```

   Response:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in": 86400
   }
   ```

3. **Use the token in subsequent requests**:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/projects" \\
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```

### Using Authentication in Swagger UI

1. Click the **"Authorize"** button at the top right
2. Enter your JWT token in the format: `Bearer <your_token>`
3. Click **"Authorize"** to apply the token to all requests
4. The lock icon (🔒) will turn closed, indicating you're authenticated

### Token Expiration

- Access tokens expire after 24 hours
- Use the `/api/v1/auth/refresh` endpoint to get a new token without re-authenticating
- Refresh tokens are valid for 7 days

## Rate Limiting

API endpoints are rate-limited to 100 requests per minute per user.
Exceeding this limit will result in HTTP 429 responses.

## Error Responses

All endpoints return standardized error responses:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

Common HTTP status codes:
- **400**: Bad Request - Invalid input
- **401**: Unauthorized - Missing or invalid authentication
- **403**: Forbidden - Insufficient permissions
- **404**: Not Found - Resource doesn't exist
- **429**: Too Many Requests - Rate limit exceeded
- **500**: Internal Server Error - Server-side error
- **503**: Service Unavailable - Service temporarily unavailable
    """,
    # Disable API documentation in production for security
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check endpoints for monitoring service status and readiness"
        },
        {
            "name": "Authentication",
            "description": "User authentication endpoints (register, login, logout, token refresh)"
        },
        {
            "name": "RBAC Authentication",
            "description": "Role-Based Access Control authentication with enterprise features"
        },
        {
            "name": "RBAC User Management",
            "description": "User management with role-based permissions"
        },
        {
            "name": "RBAC Project Management",
            "description": "Project management with access control"
        },
        {
            "name": "RBAC Audit Logs",
            "description": "Audit log queries for RBAC operations"
        },
        {
            "name": "Webhooks",
            "description": "GitHub webhook handlers for automated PR analysis"
        },
        {
            "name": "GitHub Integration",
            "description": "GitHub API integration for repository and PR management"
        },
        {
            "name": "Code Review",
            "description": "Automated code review endpoints"
        },
        {
            "name": "PR Analysis",
            "description": "Pull request analysis and review generation"
        },
        {
            "name": "Architecture Analysis",
            "description": "Repository architecture analysis and pattern detection"
        },
        {
            "name": "Local LLM",
            "description": "Local LLM (Ollama) integration for code analysis"
        },
        {
            "name": "Library Management",
            "description": "Manage code libraries and dependencies"
        },
        {
            "name": "Repository Management",
            "description": "Repository CRUD operations and management"
        },
        {
            "name": "Audit Logs",
            "description": "System-wide audit log queries and compliance reporting"
        },
        {
            "name": "User Data Management",
            "description": "User data export and deletion (GDPR compliance)"
        },
        {
            "name": "Metrics",
            "description": "Prometheus metrics endpoint for monitoring"
        },
        {
            "name": "Database",
            "description": "Database management and migration endpoints"
        },
    ],
)

# Instrument FastAPI for OpenTelemetry tracing (Requirement 18.1)
if settings.is_tracing_enabled():
    from app.core.tracing import get_tracing_config
    tracing_config = get_tracing_config()
    if tracing_config:
        tracing_config.instrument_fastapi(app)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware - must be last in middleware chain (Requirement 8.5)
# Configure CORS to restrict allowed origins based on environment
# In production, only allow requests from authorized domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=settings.CORS_EXPOSE_HEADERS,
    max_age=settings.CORS_MAX_AGE,
)

# Security headers middleware (Requirement 8.5)
# Add security response headers to protect against common vulnerabilities
from app.middleware.security_headers import configure_security_headers
configure_security_headers(
    app,
    enable_hsts=settings.ENABLE_HSTS,
    hsts_max_age=settings.HSTS_MAX_AGE,
    enable_csp=settings.ENABLE_CSP,
    environment=settings.ENVIRONMENT,
)

# Rate limiting middleware (Requirement 8.3)
from app.middleware.rate_limiting import configure_rate_limiting
configure_rate_limiting(app)

# Prometheus metrics middleware (Requirement 7.3)
from app.middleware.prometheus_middleware import configure_prometheus_middleware
configure_prometheus_middleware(app)

# Initialize application info metric
from app.core.prometheus_metrics import set_app_info
set_app_info(version=settings.VERSION, environment=settings.ENVIRONMENT)


# Request Logging Middleware
app.middleware("http")(log_request)

# Register exception handlers (Requirement 2.5, 12.1, 12.3)
register_exception_handlers(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Code Review Platform API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint - returns overall health status.
    
    Returns 200 with health status (healthy, degraded, unhealthy).
    Includes database and service status information.
    
    Validates Requirements: 1.1, 1.2, 1.4, 1.5, 1.6
    """
    from app.services.health_service import get_health_service
    
    health_service = get_health_service()
    health_status = await health_service.get_health_status()
    
    # Return appropriate status code based on health
    status_code = 200 if health_status.status == "healthy" else 503
    
    response_content = health_status.to_dict()
    if status_code == 503:
        # Add basic diagnosis if not healthy
        response_content["detail"] = "One or more critical dependencies are unhealthy"
    
    return JSONResponse(
        status_code=status_code,
        content=response_content
    )


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness probe endpoint - Kubernetes readiness probe.
    
    Returns 200 only if all required dependencies are ready:
    - PostgreSQL connected
    - Migrations applied
    
    Validates Requirements: 1.1, 1.2, 2.1, 2.4, 2.5
    """
    
    from app.services.health_service import get_health_service
    health_service = get_health_service()
    readiness_status = await health_service.get_readiness_status()
    
    status_code = 200 if readiness_status.ready else 503
    
    return JSONResponse(
        status_code=status_code,
        content=readiness_status.to_dict()
    )


@app.get("/health/live")
async def liveness_check():
    """
    Liveness probe endpoint - Kubernetes liveness probe.
    
    Returns 200 if the application process is running.
    This is a simple check that doesn't verify dependencies.
    
    Validates Requirements: 1.1, 1.2, 2.5
    """
    
    from app.services.health_service import get_health_service
    health_service = get_health_service()
    liveness_status = await health_service.get_liveness_status()
    
    return JSONResponse(
        status_code=200,
        content=liveness_status.to_dict()
    )
