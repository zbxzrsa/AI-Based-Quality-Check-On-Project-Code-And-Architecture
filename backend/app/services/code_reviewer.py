"""
Code Review Service

Handles automated code review using LLM analysis with standards classification
"""
from typing import Dict, List, Optional
import asyncio
import logging

from app.services.llm_client import get_llm_client
from app.services.parsers.factory import ParserFactory
from app.services.architecture_analyzer import ArchitectureAnalyzer
from app.services.standards_classifier import get_standards_classifier
from app.schemas.code_review import CodeReviewResult, ReviewComment, ReviewSeverity, ReviewCategory

logger = logging.getLogger(__name__)

class CodeReviewer:
    """Service for performing code reviews using LLM analysis"""
    
    def __init__(
        self, 
        llm_provider: str = "openai",
        agentic_ai_service: Optional[any] = None
    ):
        self.llm = get_llm_client(llm_provider)
        self.parser_factory = ParserFactory
        self.arch_analyzer = ArchitectureAnalyzer()
        self.standards_classifier = get_standards_classifier()
        self.agentic_ai_service = agentic_ai_service
        
        if agentic_ai_service:
            logger.info("Code Reviewer initialized with Agentic AI Service integration")
        else:
            logger.info("Code Reviewer initialized without Agentic AI Service")
    
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
            # Parse AST for the file - get appropriate parser based on file extension
            parser = self.parser_factory.get_parser_by_filename(file_change['file_path'])
            
            if parser:
                ast_info = await parser.parse_file(file_change['file_path'])
            else:
                # No parser available for this file type, skip AST analysis
                ast_info = None
            
            # Generate LLM prompt for code review
            prompt = self._create_review_prompt(
                file_change=file_change,
                ast_info=ast_info,
                pr_data=pr_data
            )
            
            # Get LLM analysis
            analysis = await self.llm.generate_completion(prompt)
            
            # Process LLM response
            comments = self._process_llm_response(analysis, file_change['file_path'])
            
            # Apply standards classification to all comments
            comments = self._apply_standards_classification(comments)
            
            # Query Agentic AI Service for complex analysis if available
            if self.agentic_ai_service and file_change.get('content'):
                try:
                    ai_comments = await self._query_agentic_ai_for_complex_analysis(
                        file_path=file_change['file_path'],
                        code_content=file_change['content'],
                        repository=pr_data.get('repository', project_id),
                        existing_comments=comments
                    )
                    
                    # Apply standards classification to AI-generated comments
                    if ai_comments:
                        ai_comments = self._apply_standards_classification(ai_comments)
                        comments.extend(ai_comments)
                        logger.info(
                            f"Added {len(ai_comments)} AI-generated comments for {file_change['file_path']}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error querying Agentic AI Service for {file_change['file_path']}: {str(e)}"
                    )
                    # Continue with existing comments even if AI service fails
            
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
    
    def _apply_standards_classification(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        """
        Apply standards classification to review comments.
        
        Args:
            comments: List of review comments to classify
            
        Returns:
            List of review comments with standards fields populated
        """
        for comment in comments:
            # Classify the finding
            classified = self.standards_classifier.classify_finding(
                category=comment.category or "code_quality",
                message=comment.message,
                severity=comment.severity.value if hasattr(comment.severity, 'value') else str(comment.severity),
                file_path=comment.file_path,
                line_number=comment.line or 0,
                suggested_fix=comment.suggestion if hasattr(comment, 'suggestion') else None
            )
            
            # Apply standards mappings to comment
            comment.iso_25010_characteristic = classified.iso_25010_characteristic
            comment.iso_25010_sub_characteristic = classified.iso_25010_sub_characteristic
            comment.iso_23396_practice = classified.iso_23396_practice
            comment.owasp_reference = classified.owasp_reference
            
            logger.debug(
                f"Applied standards to comment in {comment.file_path}:{comment.line} - "
                f"ISO25010: {comment.iso_25010_characteristic}, "
                f"ISO23396: {comment.iso_23396_practice}, "
                f"OWASP: {comment.owasp_reference}"
            )
        
        return comments
    
    async def _query_agentic_ai_for_complex_analysis(
        self,
        file_path: str,
        code_content: str,
        repository: str,
        existing_comments: List[ReviewComment]
    ) -> List[ReviewComment]:
        """
        Query Agentic AI Service for complex code pattern analysis.
        
        This method integrates with the Agentic AI Service to:
        1. Analyze Clean Code principle violations
        2. Perform contextual reasoning with graph database
        3. Generate natural language explanations
        
        Validates Requirements: 1.2
        
        Args:
            file_path: Path to the file being analyzed
            code_content: Content of the code file
            repository: Repository name
            existing_comments: Existing review comments from basic analysis
            
        Returns:
            List of additional review comments from AI analysis
        """
        ai_comments = []
        
        try:
            # 1. Analyze Clean Code violations
            logger.info(f"Querying Agentic AI for Clean Code violations in {file_path}")
            clean_code_violations = await self.agentic_ai_service.analyze_clean_code_violations(
                code=code_content,
                file_path=file_path,
                language=self._detect_language(file_path)
            )
            
            # Convert Clean Code violations to review comments
            for violation in clean_code_violations:
                severity_map = {
                    'critical': ReviewSeverity.CRITICAL,
                    'high': ReviewSeverity.HIGH,
                    'medium': ReviewSeverity.MEDIUM,
                    'low': ReviewSeverity.LOW
                }
                
                # Use MAINTAINABILITY category for Clean Code violations
                comment = ReviewComment(
                    file_path=file_path,
                    line=self._extract_line_number(violation.location),
                    message=f"Clean Code Violation ({violation.principle.value}): {violation.description}",
                    severity=severity_map.get(violation.severity, ReviewSeverity.MEDIUM),
                    category=ReviewCategory.MAINTAINABILITY,
                    suggested_fix=violation.suggestion
                )
                
                if violation.example_fix:
                    comment.suggested_fix = f"{comment.suggested_fix}\n\nExample fix:\n{violation.example_fix}"
                
                ai_comments.append(comment)
                logger.debug(
                    f"Added Clean Code violation: {violation.principle.value} at {violation.location}"
                )
            
            # 2. Perform contextual reasoning with graph database
            logger.info(f"Querying Agentic AI for architectural context analysis of {file_path}")
            architectural_analysis = await self.agentic_ai_service.analyze_with_graph_context(
                code=code_content,
                file_path=file_path,
                repository=repository
            )
            
            # Extract architectural recommendations and convert to comments
            if architectural_analysis.get('recommendations'):
                for recommendation in architectural_analysis['recommendations']:
                    comment = ReviewComment(
                        file_path=file_path,
                        line=recommendation.get('line', 0),
                        message=f"Architectural Concern: {recommendation.get('message', 'See details')}",
                        severity=self._map_severity(recommendation.get('severity', 'medium')),
                        category=ReviewCategory.ARCHITECTURE,
                        suggested_fix=recommendation.get('suggestion', '')
                    )
                    ai_comments.append(comment)
                    logger.debug(f"Added architectural recommendation at line {comment.line}")
            
            # 3. Generate natural language explanations for complex findings
            # Identify complex findings that need better explanations
            complex_findings = [
                c for c in existing_comments 
                if c.severity in [ReviewSeverity.CRITICAL, ReviewSeverity.HIGH]
                and c.category in [ReviewCategory.SECURITY, ReviewCategory.ARCHITECTURE]
            ]
            
            if complex_findings:
                logger.info(
                    f"Generating natural language explanations for {len(complex_findings)} complex findings"
                )
                
                for finding in complex_findings[:3]:  # Limit to top 3 to avoid excessive API calls
                    try:
                        explanation = await self.agentic_ai_service.generate_natural_language_explanation(
                            technical_finding=finding.message,
                            context={
                                'file_path': file_path,
                                'line': finding.line,
                                'category': finding.category.value,
                                'severity': finding.severity.value
                            }
                        )
                        
                        # Create an enhanced comment with natural language explanation
                        # Use OTHER category with a note that this is an explained version
                        enhanced_comment = ReviewComment(
                            file_path=file_path,
                            line=finding.line,
                            message=f"[AI Explanation] {explanation.developer_explanation}",
                            severity=finding.severity,
                            category=ReviewCategory.OTHER,
                            suggested_fix=explanation.how_to_fix
                        )
                        
                        # Add why it matters as additional context
                        if explanation.why_it_matters:
                            enhanced_comment.suggested_fix = (
                                f"Why this matters: {explanation.why_it_matters}\n\n"
                                f"{enhanced_comment.suggested_fix}"
                            )
                        
                        # Add code example if available
                        if explanation.code_example:
                            enhanced_comment.suggested_fix = (
                                f"{enhanced_comment.suggested_fix}\n\n"
                                f"Example:\n{explanation.code_example}"
                            )
                        
                        ai_comments.append(enhanced_comment)
                        logger.debug(
                            f"Generated natural language explanation for finding at line {finding.line}"
                        )
                        
                    except Exception as e:
                        logger.warning(
                            f"Failed to generate explanation for finding at line {finding.line}: {e}"
                        )
                        # Continue with other findings
            
            logger.info(
                f"Agentic AI analysis complete for {file_path}: "
                f"{len(clean_code_violations)} Clean Code violations, "
                f"{len(architectural_analysis.get('recommendations', []))} architectural recommendations, "
                f"total {len(ai_comments)} AI-generated comments"
            )
            
        except Exception as e:
            logger.error(
                f"Error during Agentic AI analysis for {file_path}: {str(e)}",
                exc_info=True
            )
            # Return partial results if any were collected
        
        return ai_comments
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
        }
        
        for ext, lang in extension_map.items():
            if file_path.endswith(ext):
                return lang
        
        return 'unknown'
    
    def _extract_line_number(self, location: str) -> int:
        """Extract line number from location string (e.g., 'file.py:42')"""
        try:
            if ':' in location:
                return int(location.split(':')[-1])
        except (ValueError, IndexError):
            pass
        return 0
    
    def _map_severity(self, severity_str: str) -> ReviewSeverity:
        """Map severity string to ReviewSeverity enum"""
        severity_map = {
            'critical': ReviewSeverity.CRITICAL,
            'high': ReviewSeverity.HIGH,
            'medium': ReviewSeverity.MEDIUM,
            'low': ReviewSeverity.LOW,
            'info': ReviewSeverity.LOW,
        }
        return severity_map.get(severity_str.lower(), ReviewSeverity.MEDIUM)
    
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
            
            # Add architectural issues to review with standards classification
            arch_comments = []
            for violation in violations:
                comment = ReviewComment(
                    file_path=violation['file_path'],
                    line=violation.get('line', 0),
                    message=violation['message'],
                    severity=ReviewSeverity.HIGH,
                    category='architecture'
                )
                arch_comments.append(comment)
            
            # Apply standards classification to architectural comments
            if arch_comments:
                arch_comments = self._apply_standards_classification(arch_comments)
                review_result.comments.extend(arch_comments)
                
        except Exception as e:
            logger.error(f"Error in architectural analysis: {str(e)}")
            review_result.comments.append(ReviewComment(
                file_path="",
                line=0,
                message=f"Architectural analysis failed: {str(e)}",
                severity=ReviewSeverity.ERROR
            ))
