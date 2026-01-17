"""
Pull request analysis tasks
Handles async analysis of PRs using Celery
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from app.celery_config import celery_app
from app.database.postgresql import AsyncSessionLocal
from app.models import PullRequest, Project, ReviewResult, PRStatus
from app.services.ai_reasoning import AIReasoningEngine
from app.services.github_client import get_github_client
from app.services.parsers.factory import ParserFactory
from app.services.neo4j_ast_service import Neo4jASTService
from app.database.neo4j_db import get_neo4j_driver
from sqlalchemy import select


@celery_app.task(
    bind=True,
    name='app.tasks.analyze_pull_request',
    max_retries=3,
    default_retry_delay=60,
    queue='high_priority'
)
def analyze_pull_request(self, pr_id: str, project_id: str) -> Dict[str, Any]:
    """
    Asynchronous task to analyze a pull request using AI reasoning
    
    This task:
    1. Fetches PR details and files from GitHub
    2. Parses changed files with AST parser
    3. Builds dependency graph in Neo4j
    4. Runs AI reasoning engine for analysis
    5. Stores results in PostgreSQL
    6. Updates GitHub PR status with analysis results
    
    Args:
        pr_id: Pull request database ID
        project_id: Project database ID
        
    Returns:
        Dict with analysis results: pr_id, status, issues_found, risk_score
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze_pr(pr_id, project_id, self))
    finally:
        loop.close()


async def _analyze_pr(pr_id: str, project_id: str, task) -> Dict[str, Any]:
    """Internal async implementation of PR analysis"""
    async with AsyncSessionLocal() as db:
        try:
            # Fetch pull request
            stmt = select(PullRequest).where(PullRequest.id == pr_id)
            result = await db.execute(stmt)
            pr = result.scalar_one_or_none()
            
            if not pr:
                raise ValueError(f"Pull request {pr_id} not found")
            
            # Update status to analyzing
            pr.status = PRStatus.analyzing
            await db.commit()
            
            # Fetch project
            stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get PR files from GitHub
            github_client = get_github_client()
            repo_full_name = '/'.join(project.github_repo_url.rsplit('/', 2)[-2:])
            
            files = await github_client.get_pr_files(
                repo_full_name,
                pr.github_pr_number
            )
            
            # Build combined diff
            full_diff = "\n\n".join([
                f"diff --git a/{f['filename']} b/{f['filename']}\n{f.get('patch', '')}"
                for f in files if f.get('patch')
            ])
            
            # Parse changed files and build AST in Neo4j
            driver = await get_neo4j_driver()
            neo4j_service = Neo4jASTService(driver)
            
            for file_data in files:
                if file_data['status'] in ['added', 'modified', 'renamed']:
                    try:
                        # Get file content
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
                        # Continue with other files on parse error
                        print(f"⚠️  Error parsing {file_data['filename']}: {e}")
            
            # Run AI analysis
            ai_engine = AIReasoningEngine()
            
            # Assemble context from Neo4j
            context = await ai_engine.assemble_context(project_id, pr_id)
            
            # Analyze PR with AI
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
            
            # Store review results in PostgreSQL
            review_result = ReviewResult(
                pull_request_id=pr.id,
                ai_suggestions=json.dumps([issue.dict() for issue in review.issues]),
                confidence_score=sum(issue.confidence for issue in review.issues) / len(review.issues) if review.issues else 0.0,
                total_issues=len(review.issues),
                critical_issues=sum(1 for issue in review.issues if issue.severity == 'critical')
            )
            
            db.add(review_result)
            
            # Update PR with results
            pr.status = PRStatus.reviewed
            pr.risk_score = review.risk_score / 100.0
            pr.analyzed_at = datetime.utcnow()
            
            await db.commit()
            
            # Update GitHub PR status check
            await github_client.update_pr_status(
                repo_full_name,
                pr.commit_sha,
                state='success' if review.risk_score < 70 else 'failure',
                description=f"AI Review: {len(review.issues)} issues (Risk: {review.risk_score:.0f}/100)",
                context='ai-code-review'
            )
            
            return {
                'pr_id': pr_id,
                'status': 'completed',
                'issues_found': len(review.issues),
                'risk_score': review.risk_score,
                'confidence_score': review_result.confidence_score
            }
            
        except Exception as e:
            print(f"❌ Error analyzing PR {pr_id}: {e}")
            
            # Update PR status to pending (revert from analyzing)
            try:
                pr.status = PRStatus.pending
                await db.commit()
            except:
                pass
            
            # Retry with exponential backoff
            raise task.retry(exc=e, countdown=60 * task.request.retries)


def analyze_pull_request_sync(pr_id: str, project_id: str) -> Dict[str, Any]:
    """
    Synchronous wrapper to queue the async PR analysis task
    
    Use this in your API endpoints to queue the task without waiting for results
    
    Args:
        pr_id: Pull request database ID
        project_id: Project database ID
        
    Returns:
        Task info with task_id for polling
    """
    task = analyze_pull_request.apply_async(
        args=[pr_id, project_id],
        queue='high_priority',
        expires=3600  # 1 hour
    )
    
    return {
        'task_id': task.id,
        'status': 'PENDING',
        'pr_id': pr_id,
        'message': 'PR analysis queued and will begin shortly'
    }
