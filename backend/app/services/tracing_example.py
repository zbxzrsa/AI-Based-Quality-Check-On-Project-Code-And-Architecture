"""
Example service demonstrating custom OpenTelemetry spans for business logic.

This module shows how to add custom spans to track business operations
and add contextual attributes for better observability.

Validates Requirement 18.1: Custom spans for business logic
"""
from typing import Dict, Any
from opentelemetry.trace import Status, StatusCode

from app.core.tracing import get_tracer


class AnalysisService:
    """Example service with custom tracing spans"""
    
    def __init__(self):
        self.tracer = get_tracer(__name__)
    
    async def analyze_repository(self, repo_url: str, user_id: int) -> Dict[str, Any]:
        """
        Analyze a repository with distributed tracing.
        
        Args:
            repo_url: Repository URL to analyze
            user_id: User ID requesting the analysis
            
        Returns:
            Analysis results
        """
        # Create a custom span for the entire analysis operation
        with self.tracer.start_as_current_span("analyze_repository") as span:
            # Add attributes to the span for context
            span.set_attribute("repository.url", repo_url)
            span.set_attribute("user.id", user_id)
            
            try:
                # Step 1: Clone repository
                with self.tracer.start_as_current_span("clone_repository") as clone_span:
                    clone_span.set_attribute("repository.url", repo_url)
                    # Simulate cloning
                    repo_path = await self._clone_repository(repo_url)
                    clone_span.set_attribute("repository.path", repo_path)
                
                # Step 2: Parse files
                with self.tracer.start_as_current_span("parse_files") as parse_span:
                    files = await self._parse_files(repo_path)
                    parse_span.set_attribute("files.count", len(files))
                    parse_span.set_attribute("files.total_lines", sum(f["lines"] for f in files))
                
                # Step 3: Build dependency graph
                with self.tracer.start_as_current_span("build_graph") as graph_span:
                    graph = await self._build_dependency_graph(files)
                    graph_span.set_attribute("graph.nodes", graph["node_count"])
                    graph_span.set_attribute("graph.edges", graph["edge_count"])
                
                # Step 4: Detect issues
                with self.tracer.start_as_current_span("detect_issues") as issues_span:
                    issues = await self._detect_issues(graph)
                    issues_span.set_attribute("issues.count", len(issues))
                    issues_span.set_attribute("issues.critical", sum(1 for i in issues if i["severity"] == "critical"))
                
                # Step 5: Generate report
                with self.tracer.start_as_current_span("generate_report") as report_span:
                    report = await self._generate_report(files, graph, issues)
                    report_span.set_attribute("report.size_bytes", len(str(report)))
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("analysis.status", "success")
                
                return {
                    "status": "success",
                    "repository": repo_url,
                    "files_analyzed": len(files),
                    "issues_found": len(issues),
                    "report": report,
                }
                
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("analysis.status", "failed")
                span.set_attribute("error.type", type(e).__name__)
                raise
    
    async def _clone_repository(self, repo_url: str) -> str:
        """Clone repository (simulated)"""
        # In real implementation, this would clone the repo
        return f"/tmp/repos/{repo_url.split('/')[-1]}"
    
    async def _parse_files(self, repo_path: str) -> list:
        """Parse files in repository (simulated)"""
        # In real implementation, this would use AST parser
        return [
            {"path": "src/main.py", "lines": 150},
            {"path": "src/utils.py", "lines": 80},
            {"path": "tests/test_main.py", "lines": 120},
        ]
    
    async def _build_dependency_graph(self, files: list) -> Dict[str, int]:
        """Build dependency graph (simulated)"""
        # In real implementation, this would build Neo4j graph
        return {
            "node_count": len(files),
            "edge_count": len(files) * 2,
        }
    
    async def _detect_issues(self, graph: Dict[str, int]) -> list:
        """Detect issues in code (simulated)"""
        # In real implementation, this would run analysis
        return [
            {"type": "circular_dependency", "severity": "critical"},
            {"type": "unused_import", "severity": "low"},
        ]
    
    async def _generate_report(self, files: list, graph: Dict[str, int], issues: list) -> Dict[str, Any]:
        """Generate analysis report (simulated)"""
        return {
            "summary": {
                "files": len(files),
                "nodes": graph["node_count"],
                "edges": graph["edge_count"],
                "issues": len(issues),
            },
            "issues": issues,
        }


class LLMService:
    """Example LLM service with custom tracing"""
    
    def __init__(self):
        self.tracer = get_tracer(__name__)
    
    async def generate_review(self, code: str, context: str) -> str:
        """
        Generate code review using LLM with tracing.
        
        Args:
            code: Code to review
            context: Additional context
            
        Returns:
            Review text
        """
        with self.tracer.start_as_current_span("llm_generate_review") as span:
            # Add attributes
            span.set_attribute("code.length", len(code))
            span.set_attribute("context.length", len(context))
            
            try:
                # Step 1: Prepare prompt
                with self.tracer.start_as_current_span("prepare_prompt") as prompt_span:
                    prompt = await self._prepare_prompt(code, context)
                    prompt_span.set_attribute("prompt.length", len(prompt))
                
                # Step 2: Call LLM API
                with self.tracer.start_as_current_span("call_llm_api") as api_span:
                    api_span.set_attribute("llm.provider", "openai")
                    api_span.set_attribute("llm.model", "gpt-4")
                    
                    response = await self._call_llm_api(prompt)
                    
                    api_span.set_attribute("response.length", len(response))
                    api_span.set_attribute("response.tokens", len(response.split()))
                
                # Step 3: Parse response
                with self.tracer.start_as_current_span("parse_response") as parse_span:
                    review = await self._parse_response(response)
                    parse_span.set_attribute("review.length", len(review))
                
                span.set_status(Status(StatusCode.OK))
                return review
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    async def _prepare_prompt(self, code: str, context: str) -> str:
        """Prepare LLM prompt"""
        return f"Review this code:\n\n{code}\n\nContext: {context}"
    
    async def _call_llm_api(self, prompt: str) -> str:
        """Call LLM API (simulated)"""
        # In real implementation, this would call OpenAI/Anthropic
        return "This code looks good. Consider adding error handling."
    
    async def _parse_response(self, response: str) -> str:
        """Parse LLM response"""
        return response.strip()
