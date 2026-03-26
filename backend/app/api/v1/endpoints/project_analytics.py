"""
Project analytics API endpoints.

Provides analytics, architecture insights, and performance metrics for a project.
"""
from typing import Annotated, Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import logging

from app.database.postgresql import get_db
from app.auth import TokenPayload, require_project_access, Permission
from app.models import Project, User
from app.models.code_review import (
    PullRequest,
    CodeReview,
    ReviewComment,
    ArchitectureAnalysis,
    ArchitectureViolation,
    ReviewStatus
)
try:
    from app.services.llm_service import llm_service
except ImportError:
    # Stub llm_service when module is not available
    class _StubLLMService:
        def is_initialized(self): return False
        async def generate_architecture_insights(self, data): return {}
    llm_service = _StubLLMService()
from app.services.project_analysis_service import ProjectAnalysisService  # Added missing import

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_project_and_github_token(
    db: AsyncSession,
    project_id: str,
    user_id: str,
) -> tuple[Project | None, Optional[str]]:
    project_result = await db.execute(select(Project).filter(Project.id == project_id))
    project = project_result.scalar_one_or_none()

    user_result = await db.execute(select(User).filter(User.id == user_id))
    user = user_result.scalar_one_or_none()

    return project, getattr(user, "github_token", None)


async def _fetch_live_github_issues(
    repo_url: str,
    github_token: Optional[str],
    limit: int,
) -> list[Dict[str, Any]]:
    import httpx
    from urllib.parse import urlparse

    normalized_repo_url = repo_url[:-4] if repo_url.endswith(".git") else repo_url
    parsed = urlparse(
        normalized_repo_url if "://" in normalized_repo_url else f"https://{normalized_repo_url}"
    )
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) < 2:
        return []

    repo_full_name = f"{path_parts[-2]}/{path_parts[-1]}"
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/issues",
                headers=headers,
                params={"state": "all", "per_page": max(1, min(limit, 100))},
            )

        if response.status_code != 200:
            logger.warning(
                "Live GitHub issues fetch failed for %s with status %s",
                repo_full_name,
                response.status_code,
            )
            return []

        issues: list[Dict[str, Any]] = []
        for issue in response.json():
            if issue.get("pull_request"):
                continue

            labels = [
                str(label.get("name") or "").strip()
                for label in (issue.get("labels") or [])
                if isinstance(label, dict)
            ]
            labels_lower = [label.lower() for label in labels]

            category = "security" if any(
                keyword in label
                for label in labels_lower
                for keyword in ("security", "vulnerability", "hotspot", "cve")
            ) else "github-issue"

            severity = "high" if category == "security" else "medium" if any(
                keyword in label
                for label in labels_lower
                for keyword in ("bug", "defect", "error")
            ) else "low"

            issues.append(
                {
                    "id": f"github-issue-{issue.get('number')}",
                    "file_path": f"GitHub Issue #{issue.get('number')}",
                    "line_number": None,
                    "message": issue.get("title") or f"Issue #{issue.get('number')}",
                    "severity": severity,
                    "category": category,
                    "rule_id": None,
                    "rule_name": ", ".join(labels[:3]) or "GitHub issue",
                    "suggested_fix": issue.get("body"),
                    "created_at": issue.get("created_at") or datetime.utcnow().isoformat(),
                }
            )

        return issues
    except Exception as exc:
        logger.warning("Live GitHub issues fetch failed: %s", exc)
        return []


def _default_project_analytics(project_id: str) -> Dict[str, Any]:
    return {
        "project_id": project_id,
        "metrics": {
            "code_quality": 75,
            "security_rating": 80,
            "architecture_health": 75,
            "test_coverage": 70,
            "overall_health": 75
        },
        "dependency_stats": {
            "total": 0,
            "circular": 0,
            "outdated": 0,
            "dependency_issues": 0
        },
        "performance_metrics": {
            "avg_build_time": "0m",
            "avg_test_time": "0m",
            "avg_analysis_time": "2m",
            "pr_review_time_avg": "0h"
        },
        "issue_stats": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "security": 0,
            "performance": 0,
            "code_style": 0,
            "best_practices": 0,
            "total": 0
        },
        "trends": {
            "code_quality_change": 0,
            "test_coverage_change": 0,
            "issues_change": 0
        },
        "recent_reviews": [],
        "total_prs": 0,
        "reviewed_prs": 0,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


async def _get_project_pull_requests(db: AsyncSession, project_id: str) -> list[PullRequest]:
    pr_result = await db.execute(
        select(PullRequest).filter(PullRequest.project_id == project_id)
    )
    return list(pr_result.scalars().all())


async def _get_project_architecture_violations(
    db: AsyncSession,
    prs: list[PullRequest],
) -> list[ArchitectureViolation]:
    if not prs:
        return []

    violations_result = await db.execute(
        select(ArchitectureViolation)
        .join(ArchitectureAnalysis)
        .filter(ArchitectureAnalysis.pull_request_id.in_(pr.id for pr in prs))
    )
    return list(violations_result.scalars().all())


async def _build_project_architecture_context(
    db: AsyncSession,
    project_id: str,
    analytics: Dict[str, Any],
) -> tuple[list[PullRequest], list[ArchitectureViolation], Dict[str, Any]]:
    prs = await _get_project_pull_requests(db, project_id)
    violations = await _get_project_architecture_violations(db, prs)
    architecture_data = {
        "project_id": project_id,
        "total_prs": len(prs),
        "analyzed_prs": sum(1 for pr in prs if getattr(pr, 'analyzed_at', None) is not None),
        "violations_count": len(violations),
        "metrics": analytics.get("metrics", {}),
        "dependency_stats": analytics.get("dependency_stats", {}),
        "issue_stats": analytics.get("issue_stats", {}),
    }
    return prs, violations, architecture_data


class ProjectMetrics(BaseModel):
    """Project metrics response model."""
    code_quality: int
    security_rating: int
    architecture_health: int
    test_coverage: int
    overall_health: int


class ProjectAnalytics(BaseModel):
    """Project analytics response model."""
    project_id: str
    metrics: ProjectMetrics
    total_prs: int
    reviewed_prs: int
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    architecture_violations: int
    recent_reviews: list


@router.get("/{project_id}/analytics", response_model=Dict[str, Any])
async def get_project_analytics(
    project_id: str,
    current_user: Annotated[TokenPayload, Depends(require_project_access(Permission.VIEW_PROJECT))],
    db: AsyncSession = Depends(get_db)
):
    """
    Return the aggregated analytics payload for a project.
    
    Includes code quality, security, architecture, testing, issue, dependency,
    performance, review history, and trend information.

    Falls back to a default analytics payload when the analysis service fails.
    """
    try:
        # Prefer the consolidated project analysis service for the full payload.
        service = ProjectAnalysisService(db)
        analytics = await service.get_complete_project_analytics(project_id)
        return analytics
    except Exception as e:
        import logging
        logging.error(f"Error fetching analytics for project {project_id}: {str(e)}")
        return _default_project_analytics(project_id)


@router.get("/{project_id}/issues", response_model=Dict[str, Any])
async def get_project_issues(
    project_id: str,
    current_user: Annotated[TokenPayload, Depends(require_project_access(Permission.VIEW_PROJECT))],
    db: AsyncSession = Depends(get_db),
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
):
    """
    Return issue records for all pull requests that belong to the project.
    
    Supports optional severity and category filtering.
    """
    # Load all pull requests that belong to the project.
    prs = await _get_project_pull_requests(db, project_id)
    pr_ids = [pr.id for pr in prs]
    
    if not pr_ids:
        project, github_token = await _get_project_and_github_token(db, project_id, current_user.user_id)
        live_issues = (
            await _fetch_live_github_issues(project.github_repo_url, github_token, limit)
            if project and project.github_repo_url
            else []
        )

        if severity:
            live_issues = [issue for issue in live_issues if issue.get("severity") == severity]
        if category:
            live_issues = [issue for issue in live_issues if issue.get("category") == category]

        return {
            'issues': live_issues,
            'total': len(live_issues)
        }
    
    # Build the issue query.
    query = select(ReviewComment).join(CodeReview).filter(
        CodeReview.pull_request_id.in_(pr_ids)
    )
    
    if severity:
        query = query.filter(ReviewComment.severity == severity)
    
    if category:
        query = query.filter(ReviewComment.category == category)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    issues = []
    for comment in comments:
        issues.append({
            'id': str(comment.id),
            'file_path': comment.file_path,
            'line_number': comment.line_number,
            'message': comment.message,
            'severity': comment.severity,
            'category': comment.category,
            'rule_id': comment.rule_id,
            'rule_name': comment.rule_name,
            'suggested_fix': comment.suggested_fix,
            'created_at': comment.created_at.isoformat()
        })
    
    if not issues:
        project, github_token = await _get_project_and_github_token(db, project_id, current_user.user_id)
        live_issues = (
            await _fetch_live_github_issues(project.github_repo_url, github_token, limit)
            if project and project.github_repo_url
            else []
        )

        if severity:
            live_issues = [issue for issue in live_issues if issue.get("severity") == severity]
        if category:
            live_issues = [issue for issue in live_issues if issue.get("category") == category]

        return {
            'issues': live_issues,
            'total': len(live_issues)
        }

    return {
        'issues': issues,
        'total': len(issues)
    }


@router.get("/{project_id}/architecture", response_model=Dict[str, Any])
async def get_project_architecture(
    project_id: str,
    current_user: Annotated[TokenPayload, Depends(require_project_access(Permission.VIEW_PROJECT))],
    db: AsyncSession = Depends(get_db)
):
    """
    Return architecture violations for the project.
    """
    # Load all pull requests that belong to the project.
    prs = await _get_project_pull_requests(db, project_id)
    pr_ids = [pr.id for pr in prs]
    
    if not pr_ids:
        return {
            'violations': [],
            'total': 0,
            'by_type': {},
            'by_severity': {}
        }
    
    # Load architecture violations linked to the project pull requests.
    violations = await _get_project_architecture_violations(db, prs)
    
    # Aggregate violations by type and severity.
    by_type = {}
    by_severity = {}
    
    violations_list = []
    for violation in violations:
        violations_list.append({
            'id': str(violation.id),
            'type': violation.type,
            'component': violation.component,
            'related_component': violation.related_component,
            'message': violation.message,
            'severity': violation.severity,
            'file_path': violation.file_path,
            'line_number': violation.line_number,
            'suggested_fix': violation.suggested_fix
        })
        
        # Update aggregate counters.
        by_type[violation.type] = by_type.get(violation.type, 0) + 1
        by_severity[violation.severity] = by_severity.get(violation.severity, 0) + 1
    
    return {
        'violations': violations_list,
        'total': len(violations),
        'by_type': by_type,
        'by_severity': by_severity
    }


# Performance Metrics Models
class PerformanceMetric(BaseModel):
    """Single performance metric data point."""
    timestamp: str
    metric_name: str
    value: float = Field(..., ge=0, description="Metric value must be non-negative")
    unit: str
    tags: Optional[Dict[str, str]] = None


class TimeRange(BaseModel):
    """Requested metrics time range."""
    start: str
    end: str
    
    @field_validator('start', 'end')
    @classmethod
    def validate_datetime(cls, v: str) -> str:
        """Validate ISO 8601 datetime strings."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid datetime format: {v}. Expected ISO 8601 format.")


class MetricsCollection(BaseModel):
    """Collection of performance metric series."""
    response_time: List[PerformanceMetric] = []
    throughput: List[PerformanceMetric] = []
    error_rate: List[PerformanceMetric] = []
    cpu_usage: List[PerformanceMetric] = []
    memory_usage: List[PerformanceMetric] = []


class MetricsAggregations(BaseModel):
    """Aggregated performance metric values."""
    avg_response_time: float = Field(..., ge=0, le=10000, description="Average response time in ms (0-10000)")
    p95_response_time: float = Field(..., ge=0, le=10000, description="P95 response time in ms (0-10000)")
    p99_response_time: float = Field(..., ge=0, le=10000, description="P99 response time in ms (0-10000)")
    total_requests: int = Field(..., ge=0, description="Total requests must be non-negative")
    total_errors: int = Field(..., ge=0, description="Total errors must be non-negative")


class PerformanceDashboardData(BaseModel):
    """Performance dashboard response model."""
    api_version: str = "1.0.0"
    project_id: str
    time_range: TimeRange
    metrics: MetricsCollection
    aggregations: MetricsAggregations


@router.get("/{project_id}/metrics", response_model=PerformanceDashboardData)
async def get_performance_metrics(
    project_id: str,
    current_user: Annotated[TokenPayload, Depends(require_project_access(Permission.VIEW_PROJECT))],
    db: AsyncSession = Depends(get_db),
    start_time: Optional[str] = Query(
        None,
        description="Start time in ISO 8601 format (e.g., 2024-01-01T00:00:00Z)"
    ),
    end_time: Optional[str] = Query(
        None,
        description="End time in ISO 8601 format (e.g., 2024-01-31T23:59:59Z)"
    )
):
    """
    Return time-series performance metrics for the project.
    
    Includes response time, throughput, error rate, CPU usage, and memory usage.
    
    Supports a bounded time range and defaults to the most recent seven days.
    
    Requirements: 2.4, 3.7
    """
    
    # Validate and parse time range parameters
    try:
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = datetime.utcnow() - timedelta(days=7)
            
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = datetime.utcnow()
            
        # Validate time range
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be before end_time"
            )
            
        # Validate time range is not too large (max 90 days)
        if (end_dt - start_dt).days > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time range cannot exceed 90 days"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {str(e)}. Expected ISO 8601 format."
        )
    
    # Get project PRs within time range
    pr_result = await db.execute(
        select(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.created_at >= start_dt,
            PullRequest.created_at <= end_dt
        )
    )
    prs = pr_result.scalars().all()
    
    # Generate time series data points (daily aggregation)
    current_date = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    response_time_metrics = []
    throughput_metrics = []
    error_rate_metrics = []
    cpu_usage_metrics = []
    memory_usage_metrics = []
    
    all_response_times = []
    total_requests = 0
    total_errors = 0
    
    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)
        
        # Filter PRs for this day
        day_prs = [pr for pr in prs if current_date <= pr.created_at.replace(tzinfo=None) < next_date]
        
        if day_prs:
            # Calculate metrics for this day
            # Response time: based on PR analysis time (simulated)
            analyzed_prs = [pr for pr in day_prs if pr.analyzed_at is not None]
            avg_analysis_time = sum((pr.analyzed_at.replace(tzinfo=None) - pr.created_at.replace(tzinfo=None)).total_seconds() * 1000 
                                   for pr in analyzed_prs) / len(day_prs) if analyzed_prs else 150.0
            avg_analysis_time = max(50.0, min(avg_analysis_time, 5000.0))  # Clamp between 50-5000ms
            
            response_time_metrics.append(PerformanceMetric(
                timestamp=current_date.isoformat() + 'Z',
                metric_name='response_time',
                value=round(avg_analysis_time, 2),
                unit='ms',
                tags={'aggregation': 'avg'}
            ))
            
            all_response_times.extend([avg_analysis_time] * len(day_prs))
            
            # Throughput: number of PRs analyzed per day
            throughput = len(analyzed_prs)
            throughput_metrics.append(PerformanceMetric(
                timestamp=current_date.isoformat() + 'Z',
                metric_name='throughput',
                value=float(throughput),
                unit='requests/day',
                tags={'aggregation': 'sum'}
            ))
            
            total_requests += len(day_prs)
            
            # Error rate: PRs with failed status
            failed_prs = len([pr for pr in day_prs if getattr(pr, 'status', None) == ReviewStatus.FAILED])
            error_rate = (failed_prs / len(day_prs) * 100) if day_prs else 0.0
            error_rate = max(0.0, min(error_rate, 100.0))  # Clamp between 0-100%
            
            error_rate_metrics.append(PerformanceMetric(
                timestamp=current_date.isoformat() + 'Z',
                metric_name='error_rate',
                value=round(error_rate, 2),
                unit='percent',
                tags={'aggregation': 'avg'}
            ))
            
            total_errors += failed_prs
            
            # CPU usage: simulated based on PR complexity (files changed)
            avg_files = float(sum(getattr(pr, 'files_changed', 0) for pr in day_prs) / len(day_prs)) if day_prs else 0.0
            cpu_usage = min(30.0 + (avg_files * 2.0), 100.0)  # Simulate CPU usage
            cpu_usage = max(0.0, min(cpu_usage, 100.0))  # Clamp between 0-100%
            
            cpu_usage_metrics.append(PerformanceMetric(
                timestamp=current_date.isoformat() + 'Z',
                metric_name='cpu_usage',
                value=round(cpu_usage, 2),
                unit='percent',
                tags={'aggregation': 'avg'}
            ))
            
            # Memory usage: simulated based on lines changed
            avg_lines = float(sum(getattr(pr, 'lines_added', 0) + getattr(pr, 'lines_deleted', 0) for pr in day_prs) / len(day_prs)) if day_prs else 0.0
            memory_usage = min(40.0 + (avg_lines / 100.0), 100.0)  # Simulate memory usage
            memory_usage = max(0.0, min(memory_usage, 100.0))  # Clamp between 0-100%
            
            memory_usage_metrics.append(PerformanceMetric(
                timestamp=current_date.isoformat() + 'Z',
                metric_name='memory_usage',
                value=round(memory_usage, 2),
                unit='percent',
                tags={'aggregation': 'avg'}
            ))
        
        current_date = next_date
    
    # Calculate aggregations
    if all_response_times:
        sorted_times = sorted(all_response_times)
        avg_response_time = sum(sorted_times) / len(sorted_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]
        p99_response_time = sorted_times[min(p99_index, len(sorted_times) - 1)]
    else:
        avg_response_time = 0.0
        p95_response_time = 0.0
        p99_response_time = 0.0
    
    # Ensure aggregations are within valid ranges
    avg_response_time = max(0.0, min(avg_response_time, 10000.0))
    p95_response_time = max(0.0, min(p95_response_time, 10000.0))
    p99_response_time = max(0.0, min(p99_response_time, 10000.0))
    
    return PerformanceDashboardData(
        api_version="1.0.0",
        project_id=project_id,
        time_range=TimeRange(
            start=start_dt.isoformat() + 'Z',
            end=end_dt.isoformat() + 'Z'
        ),
        metrics=MetricsCollection(
            response_time=response_time_metrics,
            throughput=throughput_metrics,
            error_rate=error_rate_metrics,
            cpu_usage=cpu_usage_metrics,
            memory_usage=memory_usage_metrics
        ),
        aggregations=MetricsAggregations(
            avg_response_time=round(avg_response_time, 2),
            p95_response_time=round(p95_response_time, 2),
            p99_response_time=round(p99_response_time, 2),
            total_requests=total_requests,
            total_errors=total_errors
        )
    )


@router.get("/{project_id}/architecture-analysis", response_model=Dict[str, Any])
async def get_project_architecture_analysis(
    project_id: str,
    current_user: Annotated[TokenPayload, Depends(require_project_access(Permission.VIEW_PROJECT))],
    db: AsyncSession = Depends(get_db)
):
    """
    Generate project architecture strengths and recommendations.
    """
    try:
        # Load project analytics and architecture context for AI analysis.
        service = ProjectAnalysisService(db)
        analytics = await service.get_complete_project_analytics(project_id)

        # Load project pull requests and architecture violations for AI analysis.
        _, violations, architecture_data = await _build_project_architecture_context(
            db,
            project_id,
            analytics,
        )

        # useAIgeneratearchitectureanalyze
        if llm_service.is_initialized():
            try:
                ai_insights = await llm_service.generate_architecture_insights(architecture_data)

                # Normalize the AI response into a stable payload shape.
                strengths = ai_insights.get("strengths", [])
                recommendations = ai_insights.get("recommendations", [])

                return {
                    "strengths": strengths,
                    "recommendations": recommendations,
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "ai_generated": True
                }
            except Exception as ai_error:
                logger.warning(f"AI architecture analysis failed: {ai_error}")
                # Fall back to rule-based analysis when AI generation fails.

        # Use rule-based analysis when AI is unavailable.
        strengths, recommendations = await _generate_rule_based_architecture_analysis(analytics, list(violations))

        return {
            "strengths": strengths,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "ai_generated": False
        }

    except Exception as e:
        logger.error(f"Error generating architecture analysis for project {project_id}: {str(e)}")
        # Return a stable fallback analysis payload.
        return {
            "strengths": [
                "The project structure is organized and easy to follow.",
                "Code ownership and module boundaries are reasonably clear.",
            ],
            "recommendations": [
                "Expand integration test coverage for critical workflows.",
                "Schedule regular pull request reviews to keep quality stable.",
            ],
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "ai_generated": False
        }


async def _generate_rule_based_architecture_analysis(
    analytics: Dict[str, Any], violations: List[Any]
) -> tuple[list[str], list[str]]:
    """Generate architecture strengths and recommendations from analytics signals."""
    strengths = []
    recommendations = []

    metrics = analytics.get("metrics", {})
    dependency_stats = analytics.get("dependency_stats", {})
    issue_stats = analytics.get("issue_stats", {})

    if metrics.get("code_quality", 0) > 75:
        strengths.append("Code quality is strong and aligns with current best practices.")

    if metrics.get("security_rating", 0) > 80:
        strengths.append("Security posture is strong with limited visible risk exposure.")

    if metrics.get("architecture_health", 0) > 70:
        strengths.append("Architecture health is stable and the current design is coherent.")

    if metrics.get("test_coverage", 0) > 60:
        strengths.append("Test coverage is at a healthy baseline for ongoing delivery.")

    if dependency_stats.get("circular", 0) == 0:
        strengths.append("No circular dependencies were detected, which keeps the architecture readable.")

    if issue_stats.get("critical", 0) > 0:
        recommendations.append("Address critical issues immediately to reduce delivery and security risk.")

    if dependency_stats.get("outdated", 0) > 0:
        recommendations.append("Update outdated dependencies to avoid unsupported versions and known defects.")

    if len(violations) > 0:
        recommendations.append("Review recorded architecture violations and resolve the highest-impact ones first.")

    if metrics.get("test_coverage", 100) < 70:
        recommendations.append("Increase test coverage for critical paths before the next release cycle.")

    if not strengths:
        strengths = [
            "The project structure is serviceable and easy to navigate.",
            "Code is grouped into consistent modules that support maintenance.",
        ]

    if not recommendations:
        recommendations = [
            "Keep a regular pull request review cadence to maintain code quality.",
            "Preserve current test coverage as new features are added.",
        ]

    return strengths, recommendations


# Global instance
# llm_service = LLMService()
