"""
Pull request analysis tasks
Handles async analysis of PRs using Celery

This module implements the complete PR analysis workflow:
1. parse_pull_request_files: Parse PR files using AST parser
2. build_dependency_graph: Build dependency graph in Neo4j
3. analyze_with_llm: Analyze code with LLM
4. post_review_comments: Post review comments to GitHub

These tasks can be chained together to form a complete workflow.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from celery import chain

from app.celery_config import celery_app
from app.database.postgresql import AsyncSessionLocal
from app.models import PullRequest, Project, ReviewResult, PRStatus
from app.services.ai_reasoning import AIReasoningEngine
from app.services.github_client import get_github_client
from app.services.parsers.factory import ParserFactory
from app.services.neo4j_ast_service import Neo4jASTService
from app.services.optimized_parser import OptimizedParser
from app.services.graph_builder.service import GraphBuilderService
from app.services.code_entity_extractor import CodeEntityExtractor
from app.services.llm.orchestrator import LLMOrchestrator, OrchestratorConfig
from app.services.llm.base import LLMRequest, LLMProviderType
from app.services.llm.prompts import PromptManager
from app.database.neo4j_db import get_neo4j_driver
from app.tasks.task_monitoring import MonitoredTask, TaskProgressStage
from sqlalchemy import select

logger = logging.getLogger(__name__)


# ========================================
# WORKFLOW TASKS
# ========================================

@celery_app.task(
    bind=True,
    base=MonitoredTask,
    name='app.tasks.pull_request_analysis.parse_pull_request_files',
    max_retries=3,
    default_retry_delay=60,
    queue='high_priority'
)
def parse_pull_request_files(self, pr_id: str, project_id: str) -> Dict[str, Any]:
    """
    Task 1: Parse PR files using AST parser
    
    This task:
    1. Fetches PR details and files from GitHub
    2. Parses changed files with optimized AST parser
    3. Extracts code entities (functions, classes, methods)
    4. Returns parsed entities for next task
    
    Args:
        pr_id: Pull request database ID
        project_id: Project database ID
        
    Returns:
        Dict with parsed_entities, pr_data, and project_data
        
    Validates Requirements: 1.1, 1.2
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_parse_pr_files(pr_id, project_id, self))
    finally:
        loop.close()


async def _parse_pr_files(pr_id: str, project_id: str, task) -> Dict[str, Any]:
    """Internal async implementation of PR file parsing"""
    async with AsyncSessionLocal() as db:
        try:
            # Update progress: Starting
            task.update_progress(5, "Fetching pull request details", TaskProgressStage.PARSING_FILES)
            
            # Fetch pull request
            stmt = select(PullRequest).where(PullRequest.id == pr_id)
            result = await db.execute(stmt)
            pr = result.scalar_one_or_none()
            
            if not pr:
                raise ValueError(f"Pull request {pr_id} not found")
            
            # Update status to analyzing
            pr.status = PRStatus.analyzing
            await db.commit()
            
            task.update_progress(10, "Fetching project details", TaskProgressStage.PARSING_FILES)
            
            # Fetch project
            stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            task.update_progress(15, "Fetching PR files from GitHub", TaskProgressStage.PARSING_FILES)
            
            # Get PR files from GitHub
            github_client = get_github_client()
            repo_full_name = '/'.join(project.github_repo_url.rsplit('/', 2)[-2:])
            
            files = await github_client.get_pr_files(
                repo_full_name,
                pr.github_pr_number
            )
            
            task.update_progress(25, f"Parsing {len(files)} files", TaskProgressStage.PARSING_FILES)
            
            # Parse changed files with optimized parser
            parser = OptimizedParser(enable_cache=True)
            extractor = CodeEntityExtractor()
            
            parsed_entities = []
            file_contents = {}
            
            total_files = len([f for f in files if f['status'] in ['added', 'modified', 'renamed']])
            processed_files = 0
            
            for file_data in files:
                if file_data['status'] in ['added', 'modified', 'renamed']:
                    try:
                        # Get file content
                        content = await github_client.get_file_content(
                            repo_full_name,
                            file_data['filename'],
                            pr.commit_sha
                        )
                        
                        file_contents[file_data['filename']] = content
                        
                        # Parse with optimized parser
                        parsed_file, parse_time = parser.parse_file(
                            file_data['filename'],
                            content=content
                        )
                        
                        # Extract code entities
                        entities = extractor.extract_from_parsed_file(parsed_file)
                        
                        # Add to results
                        for entity in entities:
                            parsed_entities.append({
                                'name': entity.name,
                                'entity_type': entity.entity_type,
                                'file_path': entity.file_path,
                                'complexity': entity.complexity,
                                'lines_of_code': entity.lines_of_code,
                                'dependencies': entity.dependencies
                            })
                        
                        processed_files += 1
                        progress = 25 + int((processed_files / total_files) * 50)
                        task.update_progress(
                            progress,
                            f"Parsed {file_data['filename']}: {len(entities)} entities",
                            TaskProgressStage.PARSING_FILES
                        )
                        
                        logger.info("Parsed %s: %d entities in %.2fs", file_data['filename'], len(entities), parse_time)
                        
                    except Exception as e:
                        # Continue with other files on parse error
                        logger.warning("Error parsing %s: %s", file_data['filename'], str(e), exc_info=True)
            
            task.update_progress(80, "Building combined diff", TaskProgressStage.PARSING_FILES)
            
            # Build combined diff for LLM analysis
            full_diff = "\n\n".join([
                f"diff --git a/{f['filename']} b/{f['filename']}\n{f.get('patch', '')}"
                for f in files if f.get('patch')
            ])
            
            task.update_progress(100, f"Parsed {len(parsed_entities)} entities from {processed_files} files", TaskProgressStage.PARSING_FILES)
            
            return {
                'pr_id': pr_id,
                'project_id': project_id,
                'parsed_entities': parsed_entities,
                'file_contents': file_contents,
                'full_diff': full_diff,
                'pr_data': {
                    'title': pr.title,
                    'description': pr.description,
                    'commit_sha': pr.commit_sha,
                    'files_changed': pr.files_changed,
                    'github_pr_number': pr.github_pr_number
                },
                'project_data': {
                    'repo_full_name': repo_full_name,
                    'language': project.language or 'Python'
                }
            }
            
        except Exception as e:
            logger.error("Error parsing PR files %s: %s", pr_id, str(e), exc_info=True)
            
            # Update PR status to pending (revert from analyzing)
            try:
                pr.status = PRStatus.pending
                await db.commit()
            except Exception as commit_error:
                logger.warning(f"Failed to update PR status: {commit_error}")
                pass
            
            # Retry with exponential backoff
            raise task.retry(exc=e, countdown=60 * task.request.retries)


@celery_app.task(
    bind=True,
    base=MonitoredTask,
    name='app.tasks.pull_request_analysis.build_dependency_graph',
    max_retries=3,
    default_retry_delay=60,
    queue='high_priority'
)
def build_dependency_graph(self, parse_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 2: Build dependency graph in Neo4j
    
    This task:
    1. Takes parsed entities from previous task
    2. Creates/updates nodes in Neo4j graph database
    3. Creates dependency relationships between entities
    4. Returns graph statistics and context
    
    Args:
        parse_result: Result from parse_pull_request_files task
        
    Returns:
        Dict with graph_stats and updated parse_result
        
    Validates Requirements: 1.3
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_build_graph(parse_result, self))
    finally:
        loop.close()


async def _build_graph(parse_result: Dict[str, Any], task) -> Dict[str, Any]:
    """Internal async implementation of graph building"""
    try:
        task.update_progress(10, "Initializing graph builder", TaskProgressStage.BUILDING_GRAPH)
        
        project_id = parse_result['project_id']
        parsed_entities = parse_result['parsed_entities']
        
        # Initialize graph builder service
        graph_builder = GraphBuilderService()
        
        task.update_progress(20, f"Converting {len(parsed_entities)} entities", TaskProgressStage.BUILDING_GRAPH)
        
        # Convert parsed entities to CodeEntity objects
        from app.services.code_entity_extractor import CodeEntity
        entities = []
        for entity_data in parsed_entities:
            entity = CodeEntity(
                name=entity_data['name'],
                entity_type=entity_data['entity_type'],
                file_path=entity_data['file_path'],
                complexity=entity_data['complexity'],
                lines_of_code=entity_data['lines_of_code'],
                dependencies=entity_data['dependencies']
            )
            entities.append(entity)
        
        task.update_progress(40, "Creating entity nodes in Neo4j", TaskProgressStage.BUILDING_GRAPH)
        
        # Create entity nodes in batch
        nodes_result = await graph_builder.create_or_update_entity_nodes_batch(
            entities,
            project_id=project_id
        )
        
        task.update_progress(60, "Building dependency relationships", TaskProgressStage.BUILDING_GRAPH)
        
        # Build dependency relationships
        relationships = []
        entity_map = {e.name: e for e in entities}
        
        for entity in entities:
            for dep_name in entity.dependencies:
                if dep_name in entity_map:
                    target = entity_map[dep_name]
                    relationships.append((entity, target, 'DEPENDS_ON', {'weight': 1.0}))
        
        task.update_progress(80, f"Creating {len(relationships)} relationships", TaskProgressStage.BUILDING_GRAPH)
        
        # Create relationships in batch
        rels_result = await graph_builder.create_dependency_relationships_batch(
            relationships,
            project_id=project_id
        )
        
        # Combine results
        graph_stats = {
            'nodes_created': nodes_result.nodes_created,
            'nodes_updated': nodes_result.nodes_updated,
            'relationships_created': rels_result.relationships_created,
            'relationships_updated': rels_result.relationships_updated,
            'errors': nodes_result.errors + rels_result.errors
        }
        
        task.update_progress(
            100,
            f"Graph built: {graph_stats['nodes_created']} nodes, {graph_stats['relationships_created']} relationships",
            TaskProgressStage.BUILDING_GRAPH
        )
        
        logger.info("Built graph: %d nodes, %d relationships", graph_stats['nodes_created'], graph_stats['relationships_created'])
        
        # Return updated result with graph stats
        return {
            **parse_result,
            'graph_stats': graph_stats
        }
        
    except Exception as e:
        logger.error("Error building dependency graph: %s", str(e), exc_info=True)
        raise task.retry(exc=e, countdown=60 * task.request.retries)


@celery_app.task(
    bind=True,
    base=MonitoredTask,
    name='app.tasks.pull_request_analysis.analyze_with_llm',
    max_retries=3,
    default_retry_delay=60,
    queue='high_priority'
)
def analyze_with_llm(self, graph_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 3: Analyze code with LLM
    
    This task:
    1. Takes parsed entities and graph context
    2. Constructs analysis prompt with code context
    3. Calls LLM orchestrator with primary/fallback pattern
    4. Parses LLM response into structured review
    5. Returns analysis results
    
    Args:
        graph_result: Result from build_dependency_graph task
        
    Returns:
        Dict with llm_analysis and updated graph_result
        
    Validates Requirements: 1.4, 2.2, 2.3
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze_with_llm(graph_result, self))
    finally:
        loop.close()


async def _analyze_with_llm(graph_result: Dict[str, Any], task) -> Dict[str, Any]:
    """Internal async implementation of LLM analysis"""
    try:
        task.update_progress(10, "Preparing analysis context", TaskProgressStage.ANALYZING_LLM)
        
        pr_data = graph_result['pr_data']
        project_data = graph_result['project_data']
        full_diff = graph_result['full_diff']
        parsed_entities = graph_result['parsed_entities']
        graph_stats = graph_result['graph_stats']
        
        task.update_progress(20, "Initializing LLM orchestrator", TaskProgressStage.ANALYZING_LLM)
        
        # Initialize LLM orchestrator with primary/fallback pattern
        orchestrator_config = OrchestratorConfig(
            primary_provider=LLMProviderType.OPENAI,
            fallback_provider=LLMProviderType.ANTHROPIC,
            timeout=30
        )
        orchestrator = LLMOrchestrator(orchestrator_config)
        
        # Initialize prompt manager
        prompt_manager = PromptManager()
        
        task.update_progress(30, "Building context summary", TaskProgressStage.ANALYZING_LLM)
        
        # Build context summary
        context_summary = f"""
Repository: {project_data['repo_full_name']}
Language: {project_data['language']}
Files Changed: {pr_data['files_changed']}
Entities Analyzed: {len(parsed_entities)}
Graph Nodes: {graph_stats['nodes_created'] + graph_stats['nodes_updated']}
Dependencies: {graph_stats['relationships_created'] + graph_stats['relationships_updated']}
"""
        
        task.update_progress(40, "Constructing analysis prompt", TaskProgressStage.ANALYZING_LLM)
        
        # Construct analysis prompt
        prompt = prompt_manager.get_prompt(
            'code_review',
            pr_title=pr_data['title'],
            pr_description=pr_data['description'] or 'No description provided',
            diff=full_diff,
            context=context_summary,
            language=project_data['language']
        )
        
        # Create LLM request
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3,
            system_prompt="You are an expert code reviewer. Analyze the pull request and provide actionable feedback."
        )
        
        task.update_progress(50, "Calling LLM API (with automatic failover)", TaskProgressStage.ANALYZING_LLM)
        
        # Call LLM with automatic failover
        llm_response = await orchestrator.generate(llm_request, use_fallback=True)
        
        task.update_progress(80, "Parsing LLM response", TaskProgressStage.ANALYZING_LLM)
        
        # Parse response into structured format
        from app.services.llm.response_parser import ResponseParser
        parser = ResponseParser()
        
        review_data = parser.parse_code_review_response(llm_response.content)
        
        # Calculate metrics
        total_issues = len(review_data.get('issues', []))
        critical_issues = sum(1 for issue in review_data.get('issues', []) 
                            if issue.get('severity') == 'critical')
        risk_score = review_data.get('risk_score', 50)
        
        llm_analysis = {
            'issues': review_data.get('issues', []),
            'summary': review_data.get('summary', ''),
            'risk_score': risk_score,
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'provider_used': llm_response.provider,
            'tokens_used': llm_response.tokens['total'],
            'cost': llm_response.cost
        }
        
        task.update_progress(
            100,
            f"Analysis complete: {total_issues} issues found (Risk: {risk_score}/100)",
            TaskProgressStage.ANALYZING_LLM
        )
        
        logger.info("LLM analysis complete: %d issues found (Risk: %d/100)", total_issues, risk_score)
        
        # Return updated result with LLM analysis
        return {
            **graph_result,
            'llm_analysis': llm_analysis
        }
        
    except Exception as e:
        logger.error("Error analyzing with LLM: %s", str(e), exc_info=True)
        raise task.retry(exc=e, countdown=60 * task.request.retries)


@celery_app.task(
    bind=True,
    base=MonitoredTask,
    name='app.tasks.pull_request_analysis.post_review_comments',
    max_retries=3,
    default_retry_delay=60,
    queue='high_priority'
)
def post_review_comments(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 4: Post review comments to GitHub
    
    This task:
    1. Takes LLM analysis results
    2. Formats review comments for GitHub
    3. Posts comments to PR using GitHub API
    4. Updates PR status check
    5. Stores results in database
    
    Args:
        analysis_result: Result from analyze_with_llm task
        
    Returns:
        Dict with final workflow results
        
    Validates Requirements: 1.5
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_post_comments(analysis_result, self))
    finally:
        loop.close()


async def _post_comments(analysis_result: Dict[str, Any], task) -> Dict[str, Any]:
    """Internal async implementation of posting comments"""
    async with AsyncSessionLocal() as db:
        try:
            task.update_progress(10, "Fetching pull request", TaskProgressStage.POSTING_COMMENTS)
            
            pr_id = analysis_result['pr_id']
            pr_data = analysis_result['pr_data']
            project_data = analysis_result['project_data']
            llm_analysis = analysis_result['llm_analysis']
            
            # Fetch pull request
            stmt = select(PullRequest).where(PullRequest.id == pr_id)
            result = await db.execute(stmt)
            pr = result.scalar_one_or_none()
            
            if not pr:
                raise ValueError(f"Pull request {pr_id} not found")
            
            task.update_progress(20, "Initializing GitHub client", TaskProgressStage.POSTING_COMMENTS)
            
            # Get GitHub client
            github_client = get_github_client()
            repo_full_name = project_data['repo_full_name']
            
            task.update_progress(30, f"Posting {len(llm_analysis['issues'])} review comments", TaskProgressStage.POSTING_COMMENTS)
            
            # Post review comments for each issue
            comments_posted = 0
            total_issues = len(llm_analysis['issues'])
            
            for idx, issue in enumerate(llm_analysis['issues']):
                try:
                    # Only post comments for issues with file/line information
                    if 'file' in issue and 'line' in issue:
                        await github_client.post_review_comment(
                            repo_full_name=repo_full_name,
                            pr_number=pr_data['github_pr_number'],
                            body=f"**{issue.get('severity', 'info').upper()}**: {issue.get('message', '')}",
                            commit_id=pr_data['commit_sha'],
                            path=issue['file'],
                            line=issue['line']
                        )
                        comments_posted += 1
                        
                        # Update progress
                        progress = 30 + int((idx / total_issues) * 40)
                        task.update_progress(
                            progress,
                            f"Posted {comments_posted}/{total_issues} comments",
                            TaskProgressStage.POSTING_COMMENTS
                        )
                except Exception as e:
                    logger.warning("Error posting comment: %s", str(e), exc_info=True)
            
            task.update_progress(70, "Updating PR status check", TaskProgressStage.POSTING_COMMENTS)
            
            # Update PR status check
            risk_score = llm_analysis['risk_score']
            state = 'success' if risk_score < 70 else 'failure'
            description = f"AI Review: {llm_analysis['total_issues']} issues (Risk: {risk_score}/100)"
            
            await github_client.update_pr_status(
                repo_full_name=repo_full_name,
                commit_sha=pr_data['commit_sha'],
                state=state,
                description=description,
                context='ai-code-review'
            )
            
            task.update_progress(85, "Storing review results in database", TaskProgressStage.POSTING_COMMENTS)
            
            # Store review results in database
            review_result = ReviewResult(
                pull_request_id=pr.id,
                ai_suggestions=json.dumps(llm_analysis['issues']),
                confidence_score=100.0 - risk_score,  # Convert risk to confidence
                total_issues=llm_analysis['total_issues'],
                critical_issues=llm_analysis['critical_issues']
            )
            
            db.add(review_result)
            
            # Update PR with results
            pr.status = PRStatus.reviewed
            pr.risk_score = risk_score / 100.0
            pr.analyzed_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            task.update_progress(
                100,
                f"Completed: Posted {comments_posted} comments",
                TaskProgressStage.COMPLETED
            )
            
            logger.info("Posted %d comments and updated PR status", comments_posted)
            
            return {
                'pr_id': pr_id,
                'status': 'completed',
                'comments_posted': comments_posted,
                'issues_found': llm_analysis['total_issues'],
                'risk_score': risk_score,
                'provider_used': llm_analysis['provider_used'],
                'tokens_used': llm_analysis['tokens_used'],
                'cost': llm_analysis['cost']
            }
            
        except Exception as e:
            logger.error("Error posting review comments: %s", str(e), exc_info=True)
            
            # Update PR status to pending (revert from analyzing)
            try:
                pr.status = PRStatus.pending
                await db.commit()
            except Exception as commit_error:
                logger.warning(f"Failed to update PR status: {commit_error}")
                pass
            
            raise task.retry(exc=e, countdown=60 * task.request.retries)


# ========================================
# WORKFLOW ORCHESTRATION
# ========================================

def analyze_pull_request_workflow(pr_id: str, project_id: str) -> Dict[str, Any]:
    """
    Chain all workflow tasks into complete PR analysis workflow
    
    This function chains the following tasks:
    1. parse_pull_request_files: Parse PR files with AST
    2. build_dependency_graph: Build graph in Neo4j
    3. analyze_with_llm: Analyze with LLM
    4. post_review_comments: Post comments to GitHub
    
    Args:
        pr_id: Pull request database ID
        project_id: Project database ID
        
    Returns:
        Task info with task_id for polling
        
    Example:
        >>> result = analyze_pull_request_workflow(pr_id="123", project_id="456")
        >>> logger.info(str(result['task_id']))  # Use this to poll for results
    """
    # Create task chain
    workflow = chain(
        parse_pull_request_files.s(pr_id, project_id),
        build_dependency_graph.s(),
        analyze_with_llm.s(),
        post_review_comments.s()
    )
    
    # Execute workflow
    result = workflow.apply_async(
        queue='high_priority',
        expires=3600  # 1 hour
    )
    
    return {
        'task_id': result.id,
        'status': 'PENDING',
        'pr_id': pr_id,
        'project_id': project_id,
        'message': 'PR analysis workflow queued and will begin shortly',
        'workflow_tasks': [
            'parse_pull_request_files',
            'build_dependency_graph',
            'analyze_with_llm',
            'post_review_comments'
        ]
    }


# ========================================
# LEGACY TASK (kept for backward compatibility)
# ========================================

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
                        logger.warning("Error parsing %s: %s", file_data['filename'], str(e), exc_info=True)
            
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
            pr.analyzed_at = datetime.now(timezone.utc)
            
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
            logger.error("Error analyzing PR %s: %s", pr_id, str(e), exc_info=True)
            
            # Update PR status to pending (revert from analyzing)
            try:
                pr.status = PRStatus.pending
                await db.commit()
            except Exception as commit_error:
                logger.warning(f"Failed to update PR status: {commit_error}")
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
