"""
Main FastAPI application entry point
"""
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging_config import setup_logging, log_request, log_exception
from app.api.v1.router import api_router
from app.database.postgresql import init_postgres, close_postgres
from app.database.neo4j_db import init_neo4j, close_neo4j
from app.database.redis_db import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging(level=settings.LOG_LEVEL, enable_json=True)
    
    await init_postgres()
    await init_neo4j()
    await init_redis()
    print("✅ All database connections initialized")
    
    yield
    
    # Shutdown
    await close_postgres()
    await close_neo4j()
    await close_redis()
    print("✅ All database connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered code review and architecture analysis platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request Logging Middleware
app.middleware("http")(log_request)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_exception(exc, {"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-code-review-api",
        "version": settings.VERSION,
    }
