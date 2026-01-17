"""
Test cases for AI PR Reviewer

This module contains comprehensive test cases for the AI PR reviewer functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List

from app.services.ai_pr_reviewer import AIPRReviewer, ReviewResult, ComplianceStatus
from app.services.llm_client import LLMClient, LLMProvider
from app.services.architectural_drift_detector import ArchitecturalDriftDetector
from app.services.security_compliance_service import SecurityComplianceService


class TestAIPRReviewer:
    """Test cases for AIPRReviewer class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock_client = Mock(spec=LLMClient)
        mock_client.generate_completion = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_drift_detector(self):
        """Create a mock drift detector."""
        mock_detector = Mock(spec=ArchitecturalDriftDetector)
        return mock_detector
    
    @pytest.fixture
    def mock_security_service(self):
        """Create a mock security service."""
        mock_service = Mock(spec=SecurityComplianceService)
        return mock_service
    
    @pytest.fixture
    def reviewer(self, mock_llm_client, mock_drift_detector, mock_security_service):
        """Create an AIPRReviewer instance with mocked dependencies."""
        reviewer = AIPRReviewer(mock_llm_client)
        reviewer.drift_detector = mock_drift_detector
        reviewer.security_service = mock_security_service
        return reviewer
    
    @pytest.fixture
    def sample_diff(self):
        """Sample git diff content for testing."""
        return """
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
    
    @pytest.fixture
    def sample_standards(self):
        """Sample design standards for testing."""
        return {
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
    
    @pytest.fixture
    def mock_ai_response(self):
        """Mock AI response for testing."""
        return {
            "content": '{"code_quality_issues": ["Missing error handling"], "architecture_violations": ["UI component calling API directly"], "security_concerns": ["No input validation"], "best_practices": ["Add error boundaries", "Use proper state management"], "complexity_assessment": {"cyclomatic_complexity": "low", "maintainability": "medium", "readability": "high"}}'
        }
    
    def test_init(self, mock_llm_client):
        """Test AIPRReviewer initialization."""
        reviewer = AIPRReviewer(mock_llm_client)
        
        assert reviewer.llm_client == mock_llm_client
        assert reviewer.design_standards is not None
        assert "layer_separation" in reviewer.design_standards
        assert "security_standards" in reviewer.design_standards
    
    @pytest.mark.asyncio
    async def test_analyze_diff_success(self, reviewer, sample_diff, sample_standards, mock_ai_response):
        """Test successful diff analysis."""
        # Setup mocks
        reviewer.drift_detector._check_layer_violations.return_value = ["UI component calling API directly"]
        reviewer.drift_detector._check_circular_dependencies.return_value = []
        reviewer.security_service._check_security_patterns.return_value = ["Missing input validation"]
        reviewer.security_service._check_sensitive_data.return_value = []
        
        reviewer.llm_client.generate_completion.return_value = mock_ai_response
        
        # Perform analysis
        result = await reviewer.analyze_diff(sample_diff, sample_standards)
        
        # Verify results
        assert isinstance(result, ReviewResult)
        assert result.safety_score > 0
        assert result.safety_score <= 100
        assert result.compliance_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING, ComplianceStatus.NON_COMPLIANT]
        assert len(result.architectural_issues) > 0
        assert len(result.security_issues) > 0
        assert len(result.refactoring_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_diff_with_default_standards(self, reviewer, sample_diff):
        """Test diff analysis with default design standards."""
        # Setup mocks
        reviewer.drift_detector._check_layer_violations.return_value = []
        reviewer.drift_detector._check_circular_dependencies.return_value = []
        reviewer.security_service._check_security_patterns.return_value = []
        reviewer.security_service._check_sensitive_data.return_value = []
        
        reviewer.llm_client.generate_completion.return_value = {"content": '{"code_quality_issues": [], "architecture_violations": [], "security_concerns": [], "best_practices": [], "complexity_assessment": {"cyclomatic_complexity": "low", "maintainability": "high", "readability": "high"}}'}
        
        # Perform analysis without custom standards
        result = await reviewer.analyze_diff(sample_diff)
        
        # Verify results
        assert isinstance(result, ReviewResult)
        assert result.safety_score == 100.0  # No issues found
        assert result.compliance_status == ComplianceStatus.COMPLIANT
    
    @pytest.mark.asyncio
    async def test_analyze_diff_ai_failure(self, reviewer, sample_diff, sample_standards):
        """Test diff analysis when AI analysis fails."""
        # Setup mocks
        reviewer.drift_detector._check_layer_violations.return_value = []
        reviewer.drift_detector._check_circular_dependencies.return_value = []
        reviewer.security_service._check_security_patterns.return_value = []
        reviewer.security_service._check_sensitive_data.return_value = []
        
        reviewer.llm_client.generate_completion.side_effect = Exception("AI service unavailable")
        
        # Perform analysis
        result = await reviewer.analyze_diff(sample_diff, sample_standards)
        
        # Verify results
        assert isinstance(result, ReviewResult)
        assert result.safety_score == 100.0  # No issues from AI failure
        assert result.detailed_analysis["error"] == "AI service unavailable"
    
    def test_check_layer_violations(self, reviewer, sample_standards):
        """Test layer violation detection."""
        file_paths = ["frontend/src/components/UserProfile.tsx"]
        
        violations = reviewer._check_layer_violations(
            file_paths, 
            sample_standards["layer_separation"]
        )
        
        assert len(violations) == 1
        assert "UI component" in violations[0]
        assert "data layer" in violations[0]
    
    def test_check_circular_dependencies(self, reviewer):
        """Test circular dependency detection."""
        diff_content = """
        import ComponentA from './ComponentA';
        import ComponentB from './ComponentB';
        """
        
        violations = reviewer._check_circular_dependencies(diff_content)
        
        assert len(violations) == 0  # No actual circular dependency in this simple case
    
    def test_check_security_patterns(self, reviewer, sample_standards):
        """Test security pattern checking."""
        diff_content = """
        const userInput = request.params.input;
        const query = `SELECT * FROM users WHERE name = '${userInput}'`;
        """
        
        violations = reviewer._check_security_patterns(
            diff_content,
            sample_standards["security_standards"]
        )
        
        assert len(violations) > 0
        assert any("SQL injection" in violation for violation in violations)
        assert any("input validation" in violation for violation in violations)
    
    def test_check_sensitive_data(self, reviewer):
        """Test sensitive data detection."""
        diff_content = """
        const apiKey = "sk-1234567890abcdef";
        console.log("API Key:", apiKey);
        """
        
        violations = reviewer._check_sensitive_data(diff_content)
        
        assert len(violations) > 0
        assert any("hardcoded" in violation for violation in violations)
        assert any("API keys" in violation for violation in violations)
    
    def test_calculate_safety_score(self, reviewer):
        """Test safety score calculation."""
        architectural_issues = ["Layer violation"]
        security_issues = ["SQL injection risk"]
        ai_analysis = {"code_quality_issues": ["Missing error handling"]}
        
        score = reviewer._calculate_safety_score(
            architectural_issues,
            security_issues,
            ai_analysis
        )
        
        expected_score = 100.0 - (1 * 10) - (1 * 15) - (1 * 5)
        assert score == expected_score
    
    def test_determine_compliance_status(self, reviewer):
        """Test compliance status determination."""
        # High score, no issues
        status = reviewer._determine_compliance_status([], [], 90.0)
        assert status == ComplianceStatus.COMPLIANT
        
        # Medium score
        status = reviewer._determine_compliance_status([], [], 70.0)
        assert status == ComplianceStatus.WARNING
        
        # Low score
        status = reviewer._determine_compliance_status([], [], 50.0)
        assert status == ComplianceStatus.NON_COMPLIANT
        
        # High score but with issues
        status = reviewer._determine_compliance_status(["issue"], ["issue"], 90.0)
        assert status == ComplianceStatus.NON_COMPLIANT
    
    def test_generate_refactoring_suggestions(self, reviewer):
        """Test refactoring suggestion generation."""
        architectural_issues = ["Layer violation"]
        security_issues = ["SQL injection risk"]
        ai_analysis = {"best_practices": ["Use proper state management"]}
        
        suggestions = reviewer._generate_refactoring_suggestions(
            architectural_issues,
            security_issues,
            ai_analysis
        )
        
        assert len(suggestions) == 3
        assert any("Refactor: Layer violation" in suggestion for suggestion in suggestions)
        assert any("Security fix: SQL injection risk" in suggestion for suggestion in suggestions)
        assert any("Use proper state management" in suggestion for suggestion in suggestions)
    
    def test_extract_file_paths(self, reviewer):
        """Test file path extraction from diff."""
        diff_content = """
        diff --git a/frontend/src/components/UserProfile.tsx b/frontend/src/components/UserProfile.tsx
        new file mode 100644
        index 0000000..1234567
        --- /dev/null
        +++ b/frontend/src/components/UserProfile.tsx
        @@ -0,0 +1,20 @@
        diff --git a/backend/models/user.py b/backend/models/user.py
        new file mode 100644
        index 0000000..abcdef
        --- /dev/null
        +++ b/backend/models/user.py
        @@ -0,0 +1,15 @@
        """
        
        file_paths = reviewer._extract_file_paths(diff_content)
        
        assert len(file_paths) == 2
        assert "frontend/src/components/UserProfile.tsx" in file_paths
        assert "backend/models/user.py" in file_paths
    
    def test_generate_report(self, reviewer):
        """Test report generation."""
        result = ReviewResult(
            safety_score=75.0,
            compliance_status=ComplianceStatus.WARNING,
            refactoring_suggestions=["Add error handling"],
            architectural_issues=["Layer violation"],
            security_issues=["Missing validation"],
            detailed_analysis={"test": "data"}
        )
        
        report = reviewer.generate_report(result)
        
        assert "summary" in report
        assert "architectural_analysis" in report
        assert "security_analysis" in report
        assert "ai_analysis" in report
        assert "refactoring_suggestions" in report
        assert "markdown_report" in report
        
        assert report["summary"]["safety_score"] == 75.0
        assert report["summary"]["compliance_status"] == "WARNING"
        assert report["summary"]["total_issues"] == 2
    
    def test_generate_markdown_report(self, reviewer):
        """Test markdown report generation."""
        result = ReviewResult(
            safety_score=85.0,
            compliance_status=ComplianceStatus.COMPLIANT,
            refactoring_suggestions=["Add tests"],
            architectural_issues=[],
            security_issues=[],
            detailed_analysis={"complexity": "low"}
        )
        
        markdown = reviewer._generate_markdown_report(result)
        
        assert "# AI PR Review Report" in markdown
        assert "Safety Score: 85.0/100" in markdown
        assert "Compliance Status: COMPLIANT" in markdown
        assert "No architectural issues found" in markdown
        assert "No security issues found" in markdown
        assert "Add tests" in markdown


class TestAIReviewService:
    """Test cases for AIReviewService class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock_client = Mock(spec=LLMClient)
        mock_client.provider = Mock()
        mock_client.provider.value = "openai"
        mock_client.model = "gpt-4"
        mock_client.get_usage_stats = Mock(return_value={"total_tokens": 1000, "total_cost": 0.10})
        return mock_client
    
    @pytest.fixture
    def review_service(self, mock_llm_client):
        """Create an AIReviewService instance."""
        return AIReviewService(mock_llm_client)
    
    @pytest.fixture
    def sample_review_request(self):
        """Sample review request for testing."""
        from app.services.ai_pr_reviewer_service import ReviewRequest, ReviewResponse
        
        return ReviewRequest(
            diff_content="sample diff content",
            design_standards={"layer_separation": {}, "security_standards": {}},
            project_id="test-project",
            pr_id="pr-123",
            reviewer_id="test-reviewer"
        )
    
    @pytest.mark.asyncio
    async def test_review_pull_request(self, review_service, sample_review_request):
        """Test pull request review."""
        # Mock the AI reviewer
        with patch.object(review_service.ai_reviewer, 'analyze_diff') as mock_analyze, \
             patch.object(review_service.ai_reviewer, 'generate_report') as mock_generate:
            
            mock_analyze.return_value = ReviewResult(
                safety_score=80.0,
                compliance_status=ComplianceStatus.COMPLIANT,
                refactoring_suggestions=[],
                architectural_issues=[],
                security_issues=[],
                detailed_analysis={}
            )
            
            mock_generate.return_value = {
                "summary": {"safety_score": 80.0, "compliance_status": "COMPLIANT", "total_issues": 0}
            }
            
            # Perform review
            response = await review_service.review_pull_request(sample_review_request)
            
            # Verify response
            assert response.review_id is not None
            assert response.review_result.safety_score == 80.0
            assert response.review_result.compliance_status == ComplianceStatus.COMPLIANT
            assert response.metadata["project_id"] == "test-project"
            assert response.metadata["pr_id"] == "pr-123"
    
    @pytest.mark.asyncio
    async def test_batch_review(self, review_service, sample_review_request):
        """Test batch review of multiple requests."""
        requests = [sample_review_request, sample_review_request]
        
        with patch.object(review_service, 'review_pull_request') as mock_review:
            mock_review.side_effect = [
                Mock(review_id="review-1", review_result=Mock(safety_score=80.0, compliance_status=ComplianceStatus.COMPLIANT)),
                Mock(review_id="review-2", review_result=Mock(safety_score=70.0, compliance_status=ComplianceStatus.WARNING))
            ]
            
            responses = await review_service.batch_review(requests)
            
            assert len(responses) == 2
            assert responses[0].review_id == "review-1"
            assert responses[1].review_id == "review-2"
    
    def test_get_review_summary(self, review_service):
        """Test review summary generation."""
        from app.services.ai_pr_reviewer_service import ReviewResponse
        
        from datetime import datetime
        
        responses = [
            ReviewResponse(
                review_id="review-1",
                timestamp=datetime.utcnow(),
                review_result=ReviewResult(80.0, ComplianceStatus.COMPLIANT, [], [], [], {}),
                report={"summary": {"total_issues": 0}},
                metadata={}
            ),
            ReviewResponse(
                review_id="review-2",
                timestamp=datetime.utcnow(),
                review_result=ReviewResult(70.0, ComplianceStatus.WARNING, [], [], [], {}),
                report={"summary": {"total_issues": 2}},
                metadata={}
            )
        ]
        
        summary = review_service.get_review_summary(responses)
        
        assert summary["summary"]["total_reviews"] == 2
        assert summary["summary"]["compliant_reviews"] == 1
        assert summary["summary"]["warning_reviews"] == 1
        assert summary["summary"]["non_compliant_reviews"] == 0
        assert summary["summary"]["average_safety_score"] == 75.0
        assert summary["summary"]["total_issues"] == 2
    
    def test_export_review_report(self, review_service):
        """Test report export functionality."""
        from app.services.ai_pr_reviewer_service import ReviewResponse
        
        from datetime import datetime
        
        response = ReviewResponse(
            review_id="test-review",
            timestamp=datetime.utcnow(),
            review_result=ReviewResult(80.0, ComplianceStatus.COMPLIANT, [], [], [], {}),
            report={"summary": {"safety_score": 80.0, "compliance_status": "COMPLIANT", "total_issues": 0}},
            metadata={}
        )
        
        # Test JSON export
        json_content = review_service.export_review_report(response, "json")
        assert "test-review" in json_content
        assert "80.0" in json_content
        
        # Test markdown export
        markdown_content = review_service.export_review_report(response, "markdown")
        assert "# AI PR Review Report" in markdown_content
        assert "Safety Score: 80.0/100" in markdown_content
    
    def test_validate_design_standards(self, review_service):
        """Test design standards validation."""
        # Valid standards
        valid_standards = {
            "layer_separation": {
                "ui_components": [],
                "business_logic": [],
                "data_access": []
            },
            "security_standards": {
                "input_validation": True,
                "sql_injection_prevention": True,
                "xss_prevention": True
            }
        }
        
        errors = review_service.validate_design_standards(valid_standards)
        assert len(errors) == 0
        
        # Invalid standards
        invalid_standards = {
            "layer_separation": {
                "ui_components": []
                # Missing business_logic and data_access
            }
            # Missing security_standards
        }
        
        errors = review_service.validate_design_standards(invalid_standards)
        assert len(errors) > 0
        assert "Missing required section: security_standards" in errors
        assert "Missing required layer: business_logic" in errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
