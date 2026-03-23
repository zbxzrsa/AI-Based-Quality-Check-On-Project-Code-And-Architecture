"""
Health check endpoints

Provides Kubernetes-style health probes:
- /health: Overall health status (200 if healthy, 503 if degraded/unhealthy)
- /health/ready: Readiness probe (200 only if all required dependencies ready)
- /health/live: Liveness probe (200 if process running)

Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""
from fastapi import APIRouter, Response
from app.services.health_service import get_health_service, HealthStatus

router = APIRouter()


@router.get("/", response_model=dict)
async def health_check(response: Response):
    """
    Overall health check endpoint.
    
    Returns 200 if healthy, 503 if degraded or unhealthy.
    Includes database connection status, version, and environment.
    
    Validates Requirements: 12.1, 12.2, 12.3, 12.4
    """
    health_service = get_health_service()
    health_status = await health_service.get_health_status()
    
    # Set status code based on health
    if health_status.status == HealthStatus.HEALTHY.value:
        response.status_code = 200
    elif health_status.status == HealthStatus.DEGRADED.value:
        response.status_code = 503
    else:  # UNHEALTHY
        response.status_code = 503
    
    return health_status.to_dict()


@router.get("/ready", response_model=dict)
async def readiness_check(response: Response):
    """
    Readiness probe endpoint (Kubernetes readiness probe).
    
    Returns 200 only if all required dependencies are ready:
    - PostgreSQL connected
    - Migrations applied
    
    Returns 503 if not ready.
    
    Validates Requirement: 12.5
    """
    health_service = get_health_service()
    readiness_status = await health_service.get_readiness_status()
    
    # Set status code based on readiness
    if readiness_status.ready:
        response.status_code = 200
    else:
        response.status_code = 503
    
    return readiness_status.to_dict()


@router.get("/live", response_model=dict)
async def liveness_check(response: Response):
    """
    Liveness probe endpoint (Kubernetes liveness probe).
    
    Returns 200 if the application process is running.
    This is a simple check that doesn't verify dependencies.
    
    Validates Requirement: 12.6
    """
    health_service = get_health_service()
    liveness_status = await health_service.get_liveness_status()
    
    # Always return 200 if we can respond
    response.status_code = 200
    
    return liveness_status.to_dict()


@router.get("/detailed", response_model=dict)
async def detailed_health_check(response: Response):
    """
    Detailed health check with component status.
    
    Deprecated: Use /health instead.
    """
    health_service = get_health_service()
    health_status = await health_service.get_health_status()
    
    # Set status code based on health
    if health_status.status == HealthStatus.HEALTHY.value:
        response.status_code = 200
    else:
        response.status_code = 503
    
    return health_status.to_dict()
