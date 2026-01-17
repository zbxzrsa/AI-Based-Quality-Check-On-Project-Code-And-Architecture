"""
AI Reasoning Engine for code review analysis
"""
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError

from app.services.llm_client import get_llm_client, LLMProvider
from app.services.prompts import (
    SYSTEM_PROMPT,
    create_code_review_prompt,
    create_specialized_prompt,
    truncate_diff_smart
)


class ReviewIssue(BaseModel):
    """Single review issue"""
    type: str  # security, logic, architecture, performance, quality
    severity: str  # critical, high, medium, low, info
    confidence: int  # 0-100
    file: str
    line: int
    title: str
    description: str
    suggestion: str
    example: Optional[str] = None


class ReviewResult(BaseModel):
    """Complete review result"""
    issues: List[ReviewIssue]
    summary: str
    risk_score: int  # 0-100
    metadata: Optional[Dict[str, Any]] = None


class AIReasoningEngine:
    """
    AI-powered code review reasoning engine
    """
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        model: Optional[str] = None
    ):
        self.llm_client = get_llm_client(provider)
        if model:
            self.llm_client.model = model
    
    async def analyze_pull_request(
        self,
        repo_name: str,
        pr_title: str,
        pr_description: str,
        diff: str,
        file_count: int,
        language: str = "Python",
        dependency_context: Optional[str] = None,
        baseline_rules: Optional[str] = None,
        focus: Optional[str] = None
    ) -> ReviewResult:
        """
        Analyze pull request and generate review
        
        Args:
            repo_name: Repository name
            pr_title: PR title
            pr_description: PR description
            diff: Git diff content
            file_count: Number of files changed
            language: Primary language
            dependency_context: Dependency graph summary
            baseline_rules: Architectural constraints
            focus: Optional focus area (security, performance, architecture)
            
        Returns:
            ReviewResult with issues and summary
        """
        # Truncate diff if too large
        truncated_diff = truncate_diff_smart(diff, max_lines=800)
        
        # Create prompts
        if focus:
            system_prompt, user_prompt = create_specialized_prompt(
                focus=focus,
                repo_name=repo_name,
                pr_title=pr_title,
                pr_description=pr_description,
                file_count=file_count,
                diff=truncated_diff,
                dependency_context=dependency_context or "",
                baseline_rules=baseline_rules or "",
                language=language
            )
        else:
            system_prompt = SYSTEM_PROMPT
            user_prompt = create_code_review_prompt(
                repo_name=repo_name,
                pr_title=pr_title,
                pr_description=pr_description,
                file_count=file_count,
                diff=truncated_diff,
                dependency_context=dependency_context or "",
                baseline_rules=baseline_rules or "",
                language=language
            )
        
        # Generate review
        try:
            response = await self.llm_client.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=4000,
                json_mode=True
            )
            
            # Parse response
            result = self._parse_response(response['content'])
            
            # Add metadata
            result.metadata = {
                "llm_provider": response['provider'],
                "llm_model": response['model'],
                "tokens": response['tokens'],
                "cost": response['cost']
            }
            
            return result
            
        except Exception as e:
            # Fallback to basic analysis
            return self._fallback_analysis(str(e))
    
    def _parse_response(self, content: str) -> ReviewResult:
        """Parse LLM response into structured format"""
        try:
            # Parse JSON
            data = json.loads(content)
            
            # Validate using Pydantic
            result = ReviewResult(**data)
            
            # Post-process: ensure constraints
            for issue in result.issues:
                # Clamp confidence to 0-100
                issue.confidence = max(0, min(100, issue.confidence))
                
                # Validate severity
                if issue.severity not in ['critical', 'high', 'medium', 'low', 'info']:
                    issue.severity = 'medium'
                
                # Validate type
                if issue.type not in ['security', 'logic', 'architecture', 'performance', 'quality']:
                    issue.type = 'quality'
            
            # Clamp risk score
            result.risk_score = max(0, min(100, result.risk_score))
            
            return result
            
        except (json.JSONDecodeError, ValidationError) as e:
            # Try to extract partial information
            return self._fallback_parsing(content, str(e))
    
    def _fallback_parsing(self, content: str, error: str) -> ReviewResult:
        """Fallback parsing when JSON parsing fails"""
        # Try to extract issues from malformed JSON
        issues = []
        
        # Look for common patterns
        if "security" in content.lower():
            issues.append(ReviewIssue(
                type="quality",
                severity="info",
                confidence=50,
                file="unknown",
                line=0,
                title="Review parsing failed",
                description=f"LLM response could not be parsed: {error}",
                suggestion="Manual review recommended"
            ))
        
        return ReviewResult(
            issues=issues,
            summary="Automated review encountered parsing errors. Manual review recommended.",
            risk_score=50
        )
    
    def _fallback_analysis(self, error: str) -> ReviewResult:
        """Fallback when LLM call fails"""
        return ReviewResult(
            issues=[
                ReviewIssue(
                    type="quality",
                    severity="info",
                    confidence=0,
                    file="unknown",
                    line=0,
                    title="AI analysis unavailable",
                    description=f"LLM API error: {error}",
                    suggestion="Fallback to rule-based analysis or manual review"
                )
            ],
            summary=f"AI-powered review failed: {error}. Fallback analysis recommended.",
            risk_score=50
        )
    
    async def assemble_context(
        self,
        project_id: str,
        pr_id: str
    ) -> Dict[str, Any]:
        """
        Assemble context for code review including dependency graph from Neo4j

        Args:
            project_id: Project ID
            pr_id: Pull request ID

        Returns:
            Context dictionary with all assembled data
        """
        from app.services.neo4j_ast_service import Neo4jASTService
        from app.database.neo4j_db import get_neo4j_driver
        from app.database.postgresql import get_db
        from app.models import PullRequest, Project
        from sqlalchemy import select

        context = {}

        # Get PR data from PostgreSQL
        from app.database.postgresql import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            stmt = select(PullRequest).where(PullRequest.id == pr_id)
            result = await db.execute(stmt)
            pr = result.scalar_one_or_none()

            if pr:
                context['pr_title'] = pr.title
                context['pr_description'] = pr.description
                context['file_count'] = pr.files_changed

            # Get project data
            stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if project:
                context['repo_name'] = project.name
                context['language'] = project.language

        # Get comprehensive dependency graph context from Neo4j
        driver = await get_neo4j_driver()
        neo4j_service = Neo4jASTService(driver)

        try:
            # Get full dependency graph
            graph = await neo4j_service.get_dependency_graph(project_id)
            context['dependency_node_count'] = graph['metadata']['node_count']
            context['dependency_edge_count'] = graph['metadata']['edge_count']

            # Build detailed dependency summary
            dependency_sections = []

            # Component count summary
            dependency_sections.append(f"Project contains {graph['metadata']['node_count']} architectural components with {graph['metadata']['edge_count']} dependencies.")

            # Get circular dependencies with details
            cycles = await neo4j_service.find_circular_deps(project_id)
            if cycles:
                context['circular_deps_count'] = len(cycles)
                cycle_details = []
                for cycle in cycles[:5]:  # Limit to first 5 cycles
                    cycle_details.append(f"Cycle length {cycle['cycleLength']}: {' -> '.join(cycle['cyclePath'][:5])}...")
                dependency_sections.append(f"⚠️  WARNING: {len(cycles)} circular dependencies detected. Examples: {'; '.join(cycle_details)}")
                context['circular_dependencies'] = cycles
            else:
                dependency_sections.append("✅ No circular dependencies detected.")

            # Get coupling metrics
            metrics = await neo4j_service.calculate_metrics(project_id)
            if metrics.get('coupling_metrics'):
                unstable_modules = [m for m in metrics['coupling_metrics'] if m.get('instability', 0) > 0.8]
                if unstable_modules:
                    unstable_names = [m['module'] for m in unstable_modules[:3]]
                    dependency_sections.append(f"⚠️  High instability modules (instability > 0.8): {', '.join(unstable_names)}")

            context['complexity_summary'] = f"Average complexity: {metrics['complexity_metrics']['average_complexity']:.1f}"

            # Create dependency graph subsection for LLM context
            dependency_graph_context = "\n".join(dependency_sections)
            context['dependency_graph_summary'] = dependency_graph_context

            # Store full graph data for detailed analysis
            context['full_dependency_graph'] = graph

        except Exception as e:
            context['dependency_summary'] = f"Dependency context unavailable: {str(e)}"
            context['dependency_graph_summary'] = "Unable to fetch dependency graph from Neo4j. Analysis will proceed without architectural context."

        return context
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        return self.llm_client.get_usage_stats()
