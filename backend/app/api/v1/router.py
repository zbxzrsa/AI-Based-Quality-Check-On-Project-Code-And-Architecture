"""
API v1 router configuration
"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, database, auth, github, pull_request, analyze

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(database.router, prefix="/database", tags=["Database"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub Integration"])
api_router.include_router(pull_request.router, prefix="/analysis", tags=["PR Analysis"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["Architecture Analysis"])
