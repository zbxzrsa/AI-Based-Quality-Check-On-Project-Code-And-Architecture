"""
Prometheus metrics endpoint.

Exposes /metrics endpoint for Prometheus scraping.

Implements Requirement 7.3: Collect metrics for API response times, error rates, and throughput.
"""
from fastapi import APIRouter, Response
from app.core.prometheus_metrics import get_metrics, get_content_type


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint.
    
    This endpoint exposes metrics in Prometheus text format for scraping.
    
    Metrics include:
    - HTTP request duration, count, and in-progress requests
    - Error rates by type and endpoint
    - Database operation metrics
    - Code analysis metrics
    - LLM API metrics
    - Cache metrics
    - Celery task metrics
    - Authentication metrics
    - GitHub integration metrics
    
    Returns:
        Response: Prometheus metrics in text format
        
    Example Prometheus scrape config:
        ```yaml
        scrape_configs:
          - job_name: 'fastapi'
            static_configs:
              - targets: ['localhost:8000']
            metrics_path: '/api/v1/metrics'
            scrape_interval: 15s
        ```
    """
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=get_content_type()
    )
