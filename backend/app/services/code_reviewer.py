"""
Code Review Service

Handles automated code review using LLM analysis
"""
from typing import Dict, List, Optional
import asyncio
from dataclasses import dataclass
from enum import Enum
import logging

from app.services.llm_client import get_llm_client
from app.services.ast_parser import ASTParser
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.schemas.code_review import CodeReviewResult, ReviewComment, ReviewSeverity

logger = logging.getLogger(__name__)

class CodeReviewer:
    """Service for performing code reviews using LLM analysis"""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm = get_llm_client(llm_provider)
        self.ast_parser = ASTParser()
        self.arch_analyzer = ArchitectureAnalyzer()
    
    async def review_pull_request(
        self, 
        pr_data: Dict[str, any],
        project_id: str,
        diff_content: str
    ) -> CodeReviewResult:
        """
        Review a pull request and provide feedback
        
        Args:
            pr_data: PR metadata
            project_id: Project identifier
            diff_content: Unified diff of changes
            
        Returns:
            CodeReviewResult containing review comments and metrics
        """
        # Parse diff to get changed files and hunks
        file_changes = self._parse_diff(diff_content)
        
        # Initialize review result
        review_result = CodeReviewResult(
            pr_id=pr_data['id'],
            project_id=project_id,
            commit_sha=pr_data['head_sha'],
            comments=[]
        )
        
        # Analyze each changed file
        tasks = []
        for file_change in file_changes:
            task = self._analyze_file_changes(
                file_change=file_change,
                pr_data=pr_data,
                project_id=project_id
            )
            tasks.append(task)
        
        # Process files in parallel
        file_reviews = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for file_review in file_reviews:
            if isinstance(file_review, Exception):
                logger.error(f"Error reviewing file: {file_review}")
                continue
                
            review_result.comments.extend(file_review.comments)
            
            # Update metrics
            if file_review.metrics:
                for k, v in file_review.metrics.items():
                    review_result.metrics[k] = review_result.metrics.get(k, 0) + v
        
        # Perform architectural analysis
        await self._perform_architectural_analysis(review_result, project_id)
        
        return review_result
    
    def _parse_diff(self, diff_content: str) -> List[Dict]:
        """Parse unified diff into structured format"""
        # Implementation for parsing diff content
        # Returns list of file changes with hunks
        pass
    
    async def _analyze_file_changes(
        self,
        file_change: Dict,
        pr_data: Dict,
        project_id: str
    ) -> CodeReviewResult:
        """Analyze changes in a single file"""
        file_review = CodeReviewResult(
            pr_id=pr_data['id'],
            project_id=project_id,
            file_path=file_change['file_path']
        )
        
        try:
            # Parse AST for the file
            ast_info = await self.ast_parser.parse_file(file_change['file_path'])
            
            # Generate LLM prompt for code review
            prompt = self._create_review_prompt(
                file_change=file_change,
                ast_info=ast_info,
                pr_data=pr_data
            )
            
            # Get LLM analysis
            analysis = await self.llm.generate(prompt)
            
            # Process LLM response
            comments = self._process_llm_response(analysis, file_change['file_path'])
            file_review.comments = comments
            
            # Calculate metrics
            file_review.metrics = {
                'issues_found': len(comments),
                'critical_issues': sum(1 for c in comments if c.severity == ReviewSeverity.CRITICAL),
                'major_issues': sum(1 for c in comments if c.severity == ReviewSeverity.HIGH),
                'minor_issues': sum(1 for c in comments if c.severity == ReviewSeverity.MEDIUM),
                'info_issues': sum(1 for c in comments if c.severity == ReviewSeverity.LOW)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {file_change['file_path']}: {str(e)}")
            file_review.comments.append(ReviewComment(
                file_path=file_change['file_path'],
                line=0,
                message=f"Error during analysis: {str(e)}",
                severity=ReviewSeverity.ERROR
            ))
        
        return file_review
    
    def _create_review_prompt(self, file_change: Dict, ast_info: Dict, pr_data: Dict) -> str:
        """Create prompt for LLM code review"""
        # Implementation for creating review prompt
        pass
    
    def _process_llm_response(self, response: str, file_path: str) -> List[ReviewComment]:
        """Process LLM response into structured review comments"""
        # Implementation for processing LLM response
        pass
    
    async def _perform_architectural_analysis(
        self,
        review_result: CodeReviewResult,
        project_id: str
    ) -> None:
        """Perform architectural analysis on the codebase"""
        try:
            # Get architectural dependencies
            deps = await self.arch_analyzer.analyze_dependencies(project_id)
            
            # Check for architectural violations
            violations = await self.arch_analyzer.detect_violations(
                project_id=project_id,
                changes=review_result.comments
            )
            
            # Add architectural issues to review
            for violation in violations:
                review_result.comments.append(ReviewComment(
                    file_path=violation['file_path'],
                    line=violation.get('line', 0),
                    message=violation['message'],
                    severity=ReviewSeverity.HIGH,
                    category='architecture'
                ))
                
        except Exception as e:
            logger.error(f"Error in architectural analysis: {str(e)}")
            review_result.comments.append(ReviewComment(
                file_path="",
                line=0,
                message=f"Architectural analysis failed: {str(e)}",
                severity=ReviewSeverity.ERROR
            ))
