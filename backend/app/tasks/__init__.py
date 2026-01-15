"""
Celery tasks for async processing
"""
import json
from datetime import datetime
from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_config import celery_app
from app.database.postgresql import AsyncSessionLocal
from app.models import PullRequest, Project, ReviewResult, PRStatus
from app.services.ai_reasoning import AIReasoningEngine
from app.services.github_client import get_github_client
from app.services.parsers.factory import ParserFactory
from app.services.neo4j_ast_service import Neo4jASTService
from app.database.neo4j_db import get_neo4j_driver


class DatabaseTask(Task):
    """Base task with database session"""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = AsyncSessionLocal()
        return self._db


@celery_app.task(
    bind=True,
    name='app.tasks.analyze_pull_request',
    max_retries=3,
    default_retry_delay=60
)
def analyze_pull_request(self, pr_id: str, project_id: str):
    """
    Analyze pull request using AI reasoning engine
    
    Args:
        pr_id: Pull request ID
        project_id: Project ID
    """
    import asyncio
    
    async def _analyze():
        async with AsyncSessionLocal() as db:
            try:
                # Update status to analyzing
                stmt = select(PullRequest).where(PullRequest.id == pr_id)
                result = await db.execute(stmt)
                pr = result.scalar_one_or_none()
                
                if not pr:
                    raise ValueError(f"Pull request {pr_id} not found")
                
                pr.status = PRStatus.analyzing
                await db.commit()
                
                # Get project
                stmt = select(Project).where(Project.id == project_id)
                result = await db.execute(stmt)
                project = result.scalar_one_or_none()
                
                if not project:
                    raise ValueError(f"Project {project_id} not found")
                
                # Get PR files from GitHub
                github_client = get_github_client()
                repo_full_name = '/'.join(project.github_repo_url.rsplit('/', 2)[-2:])
                
                pr_data = await github_client.get_pull_request(
                    repo_full_name,
                    pr.github_pr_number
                )
                
                files = await github_client.get_pr_files(
                    repo_full_name,
                    pr.github_pr_number
                )
                
                # Combine diffs
                full_diff = "\n\n".join([
                    f"diff --git a/{f['filename']} b/{f['filename']}\n{f.get('patch', '')}"
                    for f in files if f.get('patch')
                ])
                
                # Parse changed files with AST parser
                driver = await get_neo4j_driver()
                neo4j_service = Neo4jASTService(driver)
                
                for file_data in files:
                    if file_data['status'] in ['added', 'modified']:
                        # Get file content
                        try:
                            content = await github_client.get_file_content(
                                repo_full_name,
                                file_data['filename'],
                                pr.commit_sha
                            )
                            
                            # Parse with appropriate parser
                            parser = ParserFactory.get_parser_by_filename(file_data['filename'])
                            if parser:
                                parsed = parser.parse_file(
                                    file_data['filename'],
                                    content=content
                                )
                                
                                # Insert into Neo4j
                                await neo4j_service.insert_ast_nodes(parsed, project_id)
                        except Exception as e:
                            print(f"Error parsing {file_data['filename']}: {e}")
                
                # Run AI analysis
                ai_engine = AIReasoningEngine()
                
                # Assemble context
                context = await ai_engine.assemble_context(project_id, pr_id)
                
                # Analyze PR
                review = await ai_engine.analyze_pull_request(
                    repo_name=context.get('repo_name', 'Unknown'),
                    pr_title=pr.title,
                    pr_description=pr.description or "",
                    diff=full_diff,
                    file_count=pr.files_changed,
                    language=context.get('language', 'Python'),
                    dependency_context=context.get('dependency_summary'),
                    baseline_rules=None
                )
                
                # Store results in PostgreSQL
                review_result = ReviewResult(
                    pull_request_id=pr.id,
                    ai_suggestions=json.dumps([issue.dict() for issue in review.issues]),
                    confidence_score=sum(issue.confidence for issue in review.issues) / len(review.issues) if review.issues else 0,
                    total_issues=len(review.issues),
                    critical_issues=sum(1 for issue in review.issues if issue.severity == 'critical')
                )
                
                db.add(review_result)
                
                # Update PR
                pr.status = PRStatus.reviewed
                pr.risk_score = review.risk_score / 100.0
                pr.analyzed_at = datetime.utcnow()
                
                await db.commit()
                
                # Update GitHub PR status
                await github_client.update_pr_status(
                    repo_full_name,
                    pr.commit_sha,
                    state='success' if review.risk_score < 70 else 'failure',
                    description=f"AI Review: {len(review.issues)} issues found (Risk: {review.risk_score}/100)",
                    context='ai-code-review'
                )
                
                return {
                    'pr_id': pr_id,
                    'status': 'completed',
                    'issues_found': len(review.issues),
                    'risk_score': review.risk_score
                }
                
            except Exception as e:
                # Mark as failed
                pr.status = PRStatus.pending
                await db.commit()
                
                # Retry
                raise self.retry(exc=e)
    
    # Run async function
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_analyze())


@celery_app.task(
    name='app.tasks.detect_architectural_drift',
    max_retries=2
)
def detect_architectural_drift(project_id: str, baseline_version: str = "latest"):
    """
    Detect architectural drift for a project
    
    Args:
        project_id: Project ID
        baseline_version: Baseline version to compare against
    """
    import asyncio
    
    async def _detect():
        driver = await get_neo4j_driver()
        neo4j_service = Neo4jASTService(driver)
        
        # Detect drift
        drift_report = await neo4j_service.detect_drift(project_id, baseline_version)
        
        # Store report in PostgreSQL
        # (Implementation depends on schema)
        
        return drift_report
    
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_detect())


@celery_app.task(
    name='app.tasks.generate_project_documentation',
    max_retries=1
)
def generate_project_documentation(project_id: str):
    """
    Generate comprehensive project documentation
    
    Args:
        project_id: Project ID
    """
    import asyncio
    
    async def _generate():
        async with AsyncSessionLocal() as db:
            # Get project
            stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get architecture metrics
            driver = await get_neo4j_driver()
            neo4j_service = Neo4jASTService(driver)
            metrics = await neo4j_service.calculate_metrics(project_id)
            
            # Generate documentation
            documentation = {
                'project_name': project.name,
                'description': project.description,
                'language': project.language,
                'metrics': metrics,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return documentation
    
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_generate())


# Task monitoring
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing"""
    print(f'Request: {self.request!r}')
    return {'status': 'ok'}
