"""
AI-Augmented PR Review Service

This module implements the core logic for AI-based pull request review,
performing contextual analysis against design standards and architectural patterns.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import openai
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    VIOLATION = "VIOLATION"


@dataclass
class ReviewResult:
    """Result of AI PR review."""
    safety_score: int  # 0-100
    compliance_status: ComplianceStatus
    refactoring_suggestions: List[str]
    architectural_issues: List[str]
    security_issues: List[str]
    code_quality_issues: List[str]


class AIPRReviewer:
    """AI-powered Pull Request Reviewer."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4"):
        """
        Initialize the AI PR Reviewer.
        
        Args:
            openai_api_key: OpenAI API key
            model: OpenAI model to use for analysis
        """
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model,
            temperature=0.1  # Low temperature for consistent, analytical responses
        )
        
        # Initialize prompt templates
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Setup LangChain prompt templates for different analysis types."""
        
        # Main analysis prompt
        self.analysis_prompt = PromptTemplate(
            input_variables=["git_diff", "design_standard", "architectural_patterns"],
            template="""
You are an expert code reviewer specializing in architectural compliance and code quality.
Analyze the following Git diff against the provided design standards and architectural patterns.

Git Diff:
{git_diff}

Design Standard:
{design_standard}

Architectural Patterns:
{architectural_patterns}

Please provide a comprehensive analysis focusing on:
1. Architectural compliance (layer violations, pattern adherence)
2. Security vulnerabilities
3. Code quality issues
4. Performance implications
5. Maintainability concerns

Return your analysis in JSON format with the following structure:
{{
    "architectural_issues": ["List of architectural violations"],
    "security_issues": ["List of security concerns"],
    "code_quality_issues": ["List of code quality problems"],
    "suggestions": ["Specific refactoring suggestions"]
}}
"""
        )
        
        # Safety scoring prompt
        self.safety_prompt = PromptTemplate(
            input_variables=["analysis", "git_diff"],
            template="""
Based on the following analysis of a Git diff, assign a safety score from 0-100.

Analysis:
{analysis}

Git Diff:
{git_diff}

Consider these factors in your scoring:
- Architectural compliance (40%)
- Security vulnerabilities (30%)
- Code quality (20%)
- Performance impact (10%)

Return only the numerical score (0-100).
"""
        )
    
    def analyze_pr(
        self, 
        git_diff: str, 
        design_standard: str,
        architectural_patterns: Optional[Dict] = None
    ) -> ReviewResult:
        """
        Perform comprehensive PR analysis.
        
        Args:
            git_diff: Git diff string to analyze
            design_standard: Text describing design standards
            architectural_patterns: Optional architectural patterns to check against
            
        Returns:
            ReviewResult containing analysis results
        """
        try:
            # Prepare architectural patterns
            if architectural_patterns is None:
                architectural_patterns = self._get_default_architectural_patterns()
            
            # Perform main analysis
            analysis_result = self.llm.invoke(
                self.analysis_prompt.format(
                    git_diff=git_diff,
                    design_standard=design_standard,
                    architectural_patterns=json.dumps(architectural_patterns, indent=2)
                )
            ).content
            
            # Parse analysis result
            analysis_data = self._parse_analysis_result(analysis_result)
            
            # Calculate safety score
            safety_score = self._calculate_safety_score(analysis_data, git_diff)
            
            # Determine compliance status
            compliance_status = self._determine_compliance_status(safety_score)
            
            return ReviewResult(
                safety_score=safety_score,
                compliance_status=compliance_status,
                refactoring_suggestions=analysis_data.get("suggestions", []),
                architectural_issues=analysis_data.get("architectural_issues", []),
                security_issues=analysis_data.get("security_issues", []),
                code_quality_issues=analysis_data.get("code_quality_issues", [])
            )
            
        except Exception as e:
            logger.error(f"Error during PR analysis: {e}")
            raise
    
    def _get_default_architectural_patterns(self) -> Dict:
        """Get default architectural patterns to check against."""
        return {
            "layer_violations": [
                "UI components calling database directly",
                "Business logic in presentation layer",
                "Data access in service layer without repository pattern",
                "Direct database queries in controllers"
            ],
            "security_patterns": [
                "SQL injection vulnerabilities",
                "Hardcoded secrets",
                "Missing input validation",
                "Insecure authentication patterns"
            ],
            "code_quality_patterns": [
                "Long methods (>50 lines)",
                "Deep nesting (>4 levels)",
                "Magic numbers/strings",
                "Missing error handling"
            ]
        }
    
    def _parse_analysis_result(self, analysis_text: str) -> Dict:
        """Parse the LLM analysis result into structured data."""
        try:
            # Try to extract JSON from the response
            json_start = analysis_text.find("{")
            json_end = analysis_text.rfind("}") + 1
            
            if json_start != -1 and json_end != -1:
                json_str = analysis_text[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback: parse as plain text
                return self._parse_text_analysis(analysis_text)
                
        except json.JSONDecodeError:
            return self._parse_text_analysis(analysis_text)
    
    def _parse_text_analysis(self, analysis_text: str) -> Dict:
        """Parse analysis text when JSON parsing fails."""
        result = {
            "architectural_issues": [],
            "security_issues": [],
            "code_quality_issues": [],
            "suggestions": []
        }
        
        # Simple text parsing based on common patterns
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "Architectural" in line and "issues" in line.lower():
                current_section = "architectural_issues"
            elif "Security" in line and "issues" in line.lower():
                current_section = "security_issues"
            elif "Code quality" in line.lower():
                current_section = "code_quality_issues"
            elif "Suggestions" in line.lower() or "Recommendations" in line.lower():
                current_section = "suggestions"
            elif line.startswith("- ") and current_section:
                result[current_section].append(line[2:])
        
        return result
    
    def _calculate_safety_score(self, analysis_data: Dict, git_diff: str) -> int:
        """Calculate safety score based on analysis results."""
        base_score = 100
        
        # Deduct points for architectural violations
        arch_violations = len(analysis_data.get("architectural_issues", []))
        base_score -= arch_violations * 15
        
        # Deduct points for security issues
        security_issues = len(analysis_data.get("security_issues", []))
        base_score -= security_issues * 25
        
        # Deduct points for code quality issues
        quality_issues = len(analysis_data.get("code_quality_issues", []))
        base_score -= quality_issues * 5
        
        # Additional deductions based on diff complexity
        diff_lines = len(git_diff.split('\n'))
        if diff_lines > 500:
            base_score -= 10
        elif diff_lines > 1000:
            base_score -= 20
        
        # Ensure score is within bounds
        return max(0, min(100, base_score))
    
    def _determine_compliance_status(self, safety_score: int) -> ComplianceStatus:
        """Determine compliance status based on safety score."""
        if safety_score >= 85:
            return ComplianceStatus.COMPLIANT
        elif safety_score >= 60:
            return ComplianceStatus.WARNING
        else:
            return ComplianceStatus.VIOLATION
    
    def generate_markdown_report(self, result: ReviewResult) -> str:
        """
        Generate a markdown report from review results.
        
        Args:
            result: ReviewResult containing analysis data
            
        Returns:
            Markdown formatted report string
        """
        report = f"""# AI PR Review Report

## Summary
- **Safety Score**: {result.safety_score}/100
- **Compliance Status**: {result.compliance_status.value}

## Architectural Issues
"""
        
        if result.architectural_issues:
            for issue in result.architectural_issues:
                report += f"- ❌ {issue}\n"
        else:
            report += "- ✅ No architectural violations detected\n"
        
        report += "\n## Security Issues\n"
        
        if result.security_issues:
            for issue in result.security_issues:
                report += f"- ⚠️ {issue}\n"
        else:
            report += "- ✅ No security concerns detected\n"
        
        report += "\n## Code Quality Issues\n"
        
        if result.code_quality_issues:
            for issue in result.code_quality_issues:
                report += f"- 📝 {issue}\n"
        else:
            report += "- ✅ No code quality issues detected\n"
        
        report += "\n## Refactoring Suggestions\n"
        
        if result.refactoring_suggestions:
            for suggestion in result.refactoring_suggestions:
                report += f"- 💡 {suggestion}\n"
        else:
            report += "- ✅ No refactoring suggestions\n"
        
        report += """
---
*Generated by AI PR Reviewer*
"""
        
        return report


def create_design_standard_file():
    """Create a sample design standard file for testing."""
    design_standard = """
# Design Standards

## Architecture
- Follow Clean Architecture principles
- Use Repository pattern for data access
- Implement proper separation of concerns
- UI layer should not directly access database
- Business logic should be in service layer

## Security
- Never hardcode secrets or API keys
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Follow OWASP security guidelines

## Code Quality
- Methods should not exceed 50 lines
- Avoid deep nesting (max 4 levels)
- Use meaningful variable and function names
- Add proper error handling
- Write unit tests for business logic

## Performance
- Optimize database queries
- Use caching appropriately
- Avoid N+1 query problems
- Implement pagination for large datasets
- Minimize memory usage in loops
"""
    
    with open("design_standard.txt", "w") as f:
        f.write(design_standard)
    
    print("Created design_standard.txt")


if __name__ == "__main__":
    # Example usage
    import os
    
    # Load environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("Please set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Create sample design standard
    create_design_standard_file()
    
    # Sample git diff
    sample_diff = """
diff --git a/src/components/UserComponent.tsx b/src/components/UserComponent.tsx
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/src/components/UserComponent.tsx
@@ -0,0 +1,50 @@
+import React, { useState, useEffect } from 'react';
+import { User } from '../types';
+
+// Direct database access - VIOLATION!
+const db = new DatabaseConnection('mysql://localhost:3306/app');
+
+interface UserComponentProps {
+    userId: string;
+}
+
+export const UserComponent: React.FC<UserComponentProps> = ({ userId }) => {
+    const [user, setUser] = useState<User | null>(null);
+    const [loading, setLoading] = useState(false);
+
+    useEffect(() => {
+        fetchUser();
+    }, [userId]);
+
+    const fetchUser = async () => {
+        setLoading(true);
+        try {
+            // Hardcoded SQL query - SECURITY ISSUE!
+            const query = `SELECT * FROM users WHERE id = ${userId}`;
+            const result = await db.query(query);
+            setUser(result[0]);
+        } catch (error) {
+            console.error('Error fetching user:', error);
+        } finally {
+            setLoading(false);
+        }
+    };
+
+    if (loading) return <div>Loading...</div>;
+    if (!user) return <div>User not found</div>;
+
+    return (
+        <div>
+            <h2>{user.name}</h2>
+            <p>Email: {user.email}</p>
+            <p>Role: {user.role}</p>
+        </div>
+    );
+};
+
+export default UserComponent;
"""
    
    # Read design standard
    with open("design_standard.txt", "r") as f:
        design_standard = f.read()
    
    # Initialize reviewer
    reviewer = AIPRReviewer(openai_api_key)
    
    # Perform analysis
    result = reviewer.analyze_pr(sample_diff, design_standard)
    
    # Generate report
    report = reviewer.generate_markdown_report(result)
    
    print("=== AI PR Review Report ===")
    print(report)
    
    # Save report
    with open("pr_review_report.md", "w") as f:
        f.write(report)
    
    print("\nReport saved to pr_review_report.md")
