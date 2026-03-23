"""
API v1 router configuration
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    health, 
    database, 
    auth, 
    github, 
    pull_request, 
    analyze, 
    libraries, 
    code_review_webhook,
    webhooks,
    rbac_users,
    rbac_projects,
    rbac_audit,
    audit_logs,
    user_data,
    metrics,
    project_analytics,
    architecture,
    user_settings,
    code_review,
    errors,
    monitoring,
)
from app.api.v1 import repositories

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(database.router, prefix="/database", tags=["Database"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub Integration"])
api_router.include_router(code_review_webhook.router, prefix="/code-review", tags=["Code Review"])
api_router.include_router(pull_request.router, prefix="/analysis", tags=["PR Analysis"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["Architecture Analysis"])
api_router.include_router(libraries.router, prefix="/libraries", tags=["Library Management"])
api_router.include_router(repositories.router, tags=["Repository Management"])

# RBAC User Management endpoints
api_router.include_router(rbac_users.router, prefix="/rbac/users", tags=["RBAC User Management"])
api_router.include_router(rbac_projects.router, prefix="/rbac/projects", tags=["RBAC Project Management"])
api_router.include_router(rbac_audit.router, prefix="/rbac/audit", tags=["RBAC Audit Logs"])

# Project Analytics endpoints (AI reviewData)
api_router.include_router(project_analytics.router, prefix="/projects", tags=["Project Analytics"])

# Architecture Visualization endpoints (architecture可视化)
api_router.include_router(architecture.router, prefix="/architecture", tags=["Architecture Visualization"])

# User Settings endpoints (userset)
api_router.include_router(user_settings.router, prefix="/user/settings", tags=["User Settings"])

# Code Review endpoints (codereview - useuser API config)
api_router.include_router(code_review.router, prefix="/code-review", tags=["Code Review"])

# Audit Logging endpoints
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])

# User Data Management endpoints (GDPR compliance)
api_router.include_router(user_data.router, prefix="/users", tags=["User Data Management"])

# Prometheus Metrics endpoint
api_router.include_router(metrics.router, tags=["Metrics"])

# Client Error Reporting endpoint (Requirement 7.4)
api_router.include_router(errors.router, tags=["Error Reporting"])

# Monitoring endpoints
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
