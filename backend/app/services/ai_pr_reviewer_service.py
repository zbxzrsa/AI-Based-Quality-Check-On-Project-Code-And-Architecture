"""
AI PR Reviewer Service

This module provides a complete service for AI-powered pull request review
that integrates with the existing system architecture.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from app.services.llm_client import LLMClient, LLMProvider
from app.services.ai_pr_reviewer import AIPRReviewer, ReviewResult, ComplianceStatus
import logging
logger = logging.getLogger(__name__)

@dataclass
class ReviewRequest:
    """Request for AI PR review."""
    diff_content: str
    design_standards: Optional[Dict] = None
    project_id: Optional[str] = None
    pr_id: Optional[str] = None
    reviewer_id: Optional[str] = None

@dataclass
class ReviewResponse:
    """Response from AI PR review."""
    review_id: str
    timestamp: datetime
    review_result: ReviewResult
    report: Dict
    metadata: Dict

class AIReviewService:
    """Service for managing AI-powered PR reviews."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the AI Review Service.
        
        Args:
            llm_client: LLM client for AI analysis
        """
        self.llm_client = llm_client
        # Get API key based on provider
        if llm_client.provider == LLMProvider.OPENAI:
            api_key = getattr(llm_client.client, 'api_key', 'unknown')
        elif llm_client.provider == LLMProvider.ANTHROPIC:
            api_key = getattr(llm_client.client, 'api_key', 'unknown')
        else:
            api_key = "ollama"  # Ollama doesn't need API key
        
        self.ai_reviewer = AIPRReviewer(api_key, llm_client.model)
        self.logger = logger
        
    async def review_pull_request(self, request: ReviewRequest) -> ReviewResponse:
        """
        Perform AI review of a pull request.
        
        Args:
            request: Review request containing diff and metadata
            
        Returns:
            ReviewResponse with complete analysis results
        """
        try:
            self.logger.info(f"Starting AI review for PR {request.pr_id}")
            
            # Perform AI analysis
            review_result = self.ai_reviewer.analyze_diff(
                request.diff_content, 
                request.design_standards
            )
            
            # Generate comprehensive report
            report = self.ai_reviewer.generate_report(review_result)
            
            # Create response
            response = ReviewResponse(
                review_id=self._generate_review_id(),
                timestamp=datetime.utcnow(),
                review_result=review_result,
                report=report,
                metadata={
                    "project_id": request.project_id,
                    "pr_id": request.pr_id,
                    "reviewer_id": request.reviewer_id,
                    "llm_provider": self.llm_client.provider.value,
                    "llm_model": self.llm_client.model,
                    "usage_stats": self.llm_client.get_usage_stats()
                }
            )
            
            self.logger.info(f"AI review completed for PR {request.pr_id} - Score: {review_result.safety_score}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"AI review failed for PR {request.pr_id}: {str(e)}")
            raise

    def _generate_review_id(self) -> str:
        """Generate unique review ID."""
        import uuid
        return f"review_{uuid.uuid4().hex[:16]}"

    async def batch_review(self, requests: List[ReviewRequest]) -> List[ReviewResponse]:
        """
        Perform batch AI review of multiple pull requests.
        
        Args:
            requests: List of review requests
            
        Returns:
            List of review responses
        """
        responses = []
        
        for request in requests:
            try:
                response = await self.review_pull_request(request)
                responses.append(response)
            except Exception as e:
                self.logger.error(f"Batch review failed for PR {request.pr_id}: {str(e)}")
                # Continue with other reviews
                continue
        
        return responses

    def get_review_summary(self, responses: List[ReviewResponse]) -> Dict:
        """
        Generate summary of multiple review responses.
        
        Args:
            responses: List of review responses
            
        Returns:
            Summary statistics
        """
        if not responses:
            return {"error": "No reviews to summarize"}
        
        total_reviews = len(responses)
        compliant_reviews = sum(1 for r in responses if r.review_result.compliance_status == ComplianceStatus.COMPLIANT)
        warning_reviews = sum(1 for r in responses if r.review_result.compliance_status == ComplianceStatus.WARNING)
        non_compliant_reviews = sum(1 for r in responses if r.review_result.compliance_status == ComplianceStatus.NON_COMPLIANT)
        
        avg_safety_score = sum(r.review_result.safety_score for r in responses) / total_reviews
        total_issues = sum(r.report["summary"]["total_issues"] for r in responses)
        
        # Collect all issues
        all_architectural_issues = []
        all_security_issues = []
        all_refactoring_suggestions = []
        
        for response in responses:
            all_architectural_issues.extend(response.review_result.architectural_issues)
            all_security_issues.extend(response.review_result.security_issues)
            all_refactoring_suggestions.extend(response.review_result.refactoring_suggestions)
        
        return {
            "summary": {
                "total_reviews": total_reviews,
                "compliant_reviews": compliant_reviews,
                "warning_reviews": warning_reviews,
                "non_compliant_reviews": non_compliant_reviews,
                "average_safety_score": round(avg_safety_score, 2),
                "total_issues": total_issues,
                "compliance_rate": round((compliant_reviews / total_reviews) * 100, 2)
            },
            "aggregated_issues": {
                "architectural_issues": list(set(all_architectural_issues)),
                "security_issues": list(set(all_security_issues)),
                "refactoring_suggestions": list(set(all_refactoring_suggestions))
            },
            "recommendations": self._generate_batch_recommendations(responses)
        }

    def _generate_batch_recommendations(self, responses: List[ReviewResponse]) -> List[str]:
        """Generate recommendations based on batch review results."""
        recommendations = []
        
        # Count issue types
        issue_counts = self._count_issues_by_type(responses)
        
        # Generate recommendations based on issue counts
        recommendations.extend(self._generate_security_recommendations(issue_counts["security"]))
        recommendations.extend(self._generate_architectural_recommendations(issue_counts["architectural"]))
        recommendations.extend(self._generate_compliance_recommendations(responses))
        recommendations.extend(self._generate_quality_recommendations(responses))
        
        return recommendations

    def _count_issues_by_type(self, responses: List[ReviewResponse]) -> Dict[str, int]:
        """Count issues by type across all responses."""
        return {
            "security": sum(len(r.review_result.security_issues) for r in responses),
            "architectural": sum(len(r.review_result.architectural_issues) for r in responses),
            "refactoring": sum(len(r.review_result.refactoring_suggestions) for r in responses)
        }

    def _generate_security_recommendations(self, security_issues_count: int) -> List[str]:
        """Generate security-specific recommendations."""
        if security_issues_count > 0:
            return ["Prioritize security issue fixes across all reviewed PRs"]
        return []

    def _generate_architectural_recommendations(self, architectural_issues_count: int) -> List[str]:
        """Generate architectural-specific recommendations."""
        if architectural_issues_count > 0:
            return ["Review and update architectural guidelines"]
        return []

    def _generate_compliance_recommendations(self, responses: List[ReviewResponse]) -> List[str]:
        """Generate compliance-specific recommendations."""
        non_compliant_count = sum(1 for r in responses if r.review_result.compliance_status == ComplianceStatus.NON_COMPLIANT)
        if non_compliant_count > len(responses) * 0.3:  # More than 30% non-compliant
            return ["Consider mandatory code review training for the team"]
        return []

    def _generate_quality_recommendations(self, responses: List[ReviewResponse]) -> List[str]:
        """Generate quality-specific recommendations."""
        avg_score = sum(r.review_result.safety_score for r in responses) / len(responses)
        if avg_score < 70:
            return ["Implement stricter quality gates in CI/CD pipeline"]
        return []

    def export_review_report(self, response: ReviewResponse, format: str = "json") -> str:
        """
        Export review report in specified format.
        
        Args:
            response: Review response to export
            format: Export format (json, markdown, html)
            
        Returns:
            Exported report content
        """
        if format.lower() == "json":
            return json.dumps(asdict(response), indent=2, default=str)
        elif format.lower() == "markdown":
            return response.report["markdown_report"]
        elif format.lower() == "html":
            return self._convert_to_html(response.report)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _convert_to_html(self, report: Dict) -> str:
        """Convert report to HTML format."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI PR Review Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .issues {{ margin: 20px 0; }}
                ul {{ padding-left: 20px; }}
                .compliant {{ color: green; }}
                .warning {{ color: orange; }}
                .non-compliant {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI PR Review Report</h1>
                <p><strong>Review ID:</strong> {report.get('review_id', 'N/A')}</p>
                <p><strong>Timestamp:</strong> {report.get('timestamp', 'N/A')}</p>
            </div>
            
            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Safety Score:</strong> {report['summary']['safety_score']}/100</p>
                <p><strong>Compliance Status:</strong> 
                    <span class="{'compliant' if report['summary']['compliance_status'] == 'COMPLIANT' else 'warning' if report['summary']['compliance_status'] == 'WARNING' else 'non-compliant'}">
                        {report['summary']['compliance_status']}
                    </span>
                </p>
                <p><strong>Total Issues:</strong> {report['summary']['total_issues']}</p>
            </div>
            
            <div class="issues">
                <h2>Architectural Issues</h2>
                <ul>
                    {''.join(f'<li>{issue}</li>' for issue in report['architectural_analysis']['issues'])}
                </ul>
            </div>
            
            <div class="issues">
                <h2>Security Issues</h2>
                <ul>
                    {''.join(f'<li>{issue}</li>' for issue in report['security_analysis']['issues'])}
                </ul>
            </div>
            
            <div class="issues">
                <h2>Refactoring Suggestions</h2>
                <ul>
                    {''.join(f'<li>{suggestion}</li>' for suggestion in report['refactoring_suggestions'])}
                </ul>
            </div>
        </body>
        </html>
        """
        return html

    def validate_design_standards(self, standards: Dict) -> List[str]:
        """
        Validate design standards configuration.
        
        Args:
            standards: Design standards to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required sections
        required_sections = ["layer_separation", "security_standards"]
        for section in required_sections:
            if section not in standards:
                errors.append(f"Missing required section: {section}")
        
        # Validate layer separation
        if "layer_separation" in standards:
            layer_separation = standards["layer_separation"]
            required_layers = ["ui_components", "business_logic", "data_access"]
            for layer in required_layers:
                if layer not in layer_separation:
                    errors.append(f"Missing required layer: {layer}")
        
        # Validate security standards
        if "security_standards" in standards:
            security_standards = standards["security_standards"]
            required_security = ["input_validation", "sql_injection_prevention", "xss_prevention"]
            for security_item in required_security:
                if security_item not in security_standards:
                    errors.append(f"Missing required security standard: {security_item}")
        
        return errors

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    # Example usage
    async def main():
        # Create LLM client
        llm_client = LLMClient(LLMProvider.OPENAI)
        
        # Create review service
        review_service = AIReviewService(llm_client)
        
        # Example diff content
        example_diff = """
        diff --git a/frontend/src/components/UserProfile.tsx b/frontend/src/components/UserProfile.tsx
        new file mode 100644
        index 0000000..1234567
        --- /dev/null
        +++ b/frontend/src/components/UserProfile.tsx
        @@ -0,0 +1,20 @@
        +import React from 'react';
        +import { getUserData } from '../services/api';
        +
        +const UserProfile: React.FC = () => {
        +  const [user, setUser] = React.useState(null);
        +
        +  React.useEffect(() => {
        +    // Direct API call from UI component - architectural violation
        +    getUserData().then(setUser);
        +  }, []);
        +
        +  return (
        +    <div>
        +      <h1>User Profile</h1>
        +      {user && <p>Name: {user.name}</p>}
        +    </div>
        +  );
        +};
        +
        +export default UserProfile;
        """
        
        # Example design standards
        example_standards = {
            "layer_separation": {
                "ui_components": ["components/", "pages/", "views/"],
                "business_logic": ["services/", "use_cases/", "domain/"],
                "data_access": ["repositories/", "models/", "dao/"],
                "forbidden_connections": [
                    {"from": "ui_components", "to": "data_access"}
                ]
            },
            "security_standards": {
                "input_validation": True,
                "sql_injection_prevention": True,
                "xss_prevention": True,
                "authentication_required": True
            }
        }
        
        # Create review request
        request = ReviewRequest(
            diff_content=example_diff,
            design_standards=example_standards,
            project_id="example-project",
            pr_id="pr-123",
            reviewer_id="ai-reviewer"
        )
        
        try:
            # Perform review
            response = await review_service.review_pull_request(request)
            
            # Print results
            print("Review completed successfully!")
            print(f"Review ID: {response.review_id}")
            print(f"Safety Score: {response.review_result.safety_score}")
            print(f"Compliance Status: {response.review_result.compliance_status}")
            print(f"Total Issues: {response.report['summary']['total_issues']}")
            
            # Export report
            json_report = review_service.export_review_report(response, "json")
            markdown_report = review_service.export_review_report(response, "markdown")
            
            print("\nJSON Report:")
            print(json_report[:500] + "..." if len(json_report) > 500 else json_report)
            
            print("\nMarkdown Report:")
            print(markdown_report[:500] + "..." if len(markdown_report) > 500 else markdown_report)
            
        except Exception as e:
            print(f"Error during review: {e}")
    
    # Run example
    asyncio.run(main())
