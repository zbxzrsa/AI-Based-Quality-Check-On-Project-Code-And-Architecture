"""
GitHub Comment Generator Service

Formats code review findings as GitHub review comments and posts them to PRs.
Implements rate limiting, retries, and error handling for GitHub API interactions.

Validates Requirements: 1.5
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from github import GithubException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.services.github_client import GitHubAPIClient, get_github_client
from app.services.security_scanner import SecurityFinding
from app.services.standards_classifier import ClassifiedFinding

logger = logging.getLogger(__name__)


@dataclass
class CommentResult:
    """Result of posting a comment"""
    success: bool
    comment_id: Optional[int] = None
    error: Optional[str] = None
    finding_id: Optional[str] = None
    retry_count: int = 0


@dataclass
class CommentBatchResult:
    """Result of posting multiple comments"""
    total_comments: int
    successful_comments: int
    failed_comments: int
    results: List[CommentResult]
    total_time: float
    rate_limit_hits: int


class GitHubCommentGenerator:
    """
    Service for generating and posting GitHub review comments.
    
    Features:
    - Formats findings as actionable GitHub comments
    - Posts comments to specific lines in PR files
    - Handles GitHub API rate limits with exponential backoff
    - Implements retry logic for transient failures
    - Batches comments to avoid overwhelming the API
    """
    
    def __init__(
        self,
        github_client: Optional[GitHubAPIClient] = None,
        max_retries: int = 3,
        batch_size: int = 10,
        batch_delay: float = 1.0
    ):
        """
        Initialize comment generator.
        
        Args:
            github_client: GitHub API client (uses singleton if None)
            max_retries: Maximum number of retries for failed comments
            batch_size: Number of comments to post before pausing
            batch_delay: Delay between batches in seconds
        """
        self.github_client = github_client or get_github_client()
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self.rate_limit_hits = 0
    
    def format_security_finding(
        self,
        finding: SecurityFinding,
        include_owasp: bool = True
    ) -> str:
        """
        Format a security finding as a GitHub comment.
        
        Args:
            finding: Security finding to format
            include_owasp: Whether to include OWASP reference
            
        Returns:
            Formatted comment body in Markdown
        """
        # Severity emoji mapping
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🔵',
            'info': 'ℹ️'
        }
        
        emoji = severity_emoji.get(finding.severity.lower(), '⚠️')
        
        # Build comment
        lines = [
            f"## {emoji} Security Issue: {finding.issue_type.replace('_', ' ').title()}",
            f"",
            f"**Severity:** {finding.severity.upper()}",
            f"",
            f"### Description",
            finding.description,
            f""
        ]
        
        # Add code snippet if available
        if finding.code_snippet:
            lines.extend([
                f"### Code",
                f"```python",
                finding.code_snippet,
                f"```",
                f""
            ])
        
        # Add suggestion
        if finding.suggestion:
            lines.extend([
                f"### 💡 Suggestion",
                finding.suggestion,
                f""
            ])
        
        # Add OWASP reference if available and requested
        if include_owasp and finding.owasp_reference:
            lines.extend([
                f"### 🛡️ OWASP Top 10 Reference",
                f"**{finding.owasp_reference}: {finding.owasp_name}**",
                f"",
                finding.owasp_description or "",
                f""
            ])
            
            # Add mitigations
            if finding.owasp_mitigations:
                lines.append(f"**Recommended Mitigations:**")
                for mitigation in finding.owasp_mitigations:
                    lines.append(f"- {mitigation}")
                lines.append(f"")
        
        # Add standards classification
        if finding.iso_25010_characteristic:
            lines.extend([
                f"### 📋 Standards Classification",
                f"- **ISO/IEC 25010:** {finding.iso_25010_characteristic}"
            ])
            if finding.iso_25010_sub_characteristic:
                lines.append(f"  - Sub-characteristic: {finding.iso_25010_sub_characteristic}")
            
            if finding.iso_23396_practice:
                lines.append(f"- **ISO/IEC 23396:** {finding.iso_23396_practice}")
            
            lines.append(f"")
        
        # Add footer
        lines.extend([
            f"---",
            f"*Generated by AI Code Review Platform*"
        ])
        
        return "\n".join(lines)
    
    def format_classified_finding(
        self,
        finding: ClassifiedFinding,
        include_standards: bool = True
    ) -> str:
        """
        Format a classified finding as a GitHub comment.
        
        Args:
            finding: Classified finding to format
            include_standards: Whether to include standards references
            
        Returns:
            Formatted comment body in Markdown
        """
        # Severity emoji mapping
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🔵',
            'info': 'ℹ️'
        }
        
        emoji = severity_emoji.get(finding.severity.lower(), '⚠️')
        
        # Build comment
        lines = [
            f"## {emoji} Code Quality Issue: {finding.category.replace('_', ' ').title()}",
            f"",
            f"**Severity:** {finding.severity.upper()}",
            f"",
            f"### Description",
            finding.message,
            f""
        ]
        
        # Add suggested fix if available
        if finding.suggested_fix:
            lines.extend([
                f"### 💡 Suggested Fix",
                finding.suggested_fix,
                f""
            ])
        
        # Add OWASP reference if available (for security findings)
        if finding.owasp_reference:
            lines.extend([
                f"### 🛡️ OWASP Top 10 Reference",
                f"**{finding.owasp_reference}**",
                f""
            ])
        
        # Add standards classification if requested
        if include_standards:
            lines.extend([
                f"### 📋 Standards Classification"
            ])
            
            if finding.iso_25010_characteristic:
                lines.append(f"- **ISO/IEC 25010:** {finding.iso_25010_characteristic}")
                if finding.iso_25010_sub_characteristic:
                    lines.append(f"  - Sub-characteristic: {finding.iso_25010_sub_characteristic}")
            
            if finding.iso_23396_practice:
                lines.append(f"- **ISO/IEC 23396:** {finding.iso_23396_practice}")
            
            lines.append(f"")
        
        # Add rule information if available
        if finding.rule_id or finding.rule_name:
            lines.extend([
                f"### 📏 Rule Information"
            ])
            if finding.rule_id:
                lines.append(f"- **Rule ID:** {finding.rule_id}")
            if finding.rule_name:
                lines.append(f"- **Rule Name:** {finding.rule_name}")
            lines.append(f"")
        
        # Add footer
        lines.extend([
            f"---",
            f"*Generated by AI Code Review Platform*"
        ])
        
        return "\n".join(lines)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(GithubException)
    )
    async def post_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        file_path: str,
        line_number: int,
        comment_body: str
    ) -> CommentResult:
        """
        Post a review comment to a PR with retry logic.
        
        Args:
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            commit_sha: Commit SHA
            file_path: Path to file
            line_number: Line number for comment
            comment_body: Comment body in Markdown
            
        Returns:
            CommentResult with success status
        """
        try:
            result = await self.github_client.post_review_comment(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                body=comment_body,
                commit_id=commit_sha,
                path=file_path,
                line=line_number
            )
            
            logger.info(
                f"Posted comment to {file_path}:{line_number} on PR #{pr_number}",
                extra={
                    'comment_id': result['id'],
                    'pr_number': pr_number,
                    'file_path': file_path
                }
            )
            
            return CommentResult(
                success=True,
                comment_id=result['id']
            )
            
        except GithubException as e:
            # Check if it's a rate limit error
            if e.status == 403 and 'rate limit' in str(e).lower():
                self.rate_limit_hits += 1
                logger.warning(
                    f"GitHub API rate limit hit, will retry",
                    extra={'pr_number': pr_number}
                )
                # Wait longer for rate limit
                await asyncio.sleep(60)
                raise  # Retry
            
            # Check if it's a validation error (line not in diff)
            if e.status == 422:
                logger.warning(
                    f"Cannot comment on line {line_number} in {file_path}: "
                    f"line not in diff",
                    extra={
                        'pr_number': pr_number,
                        'file_path': file_path,
                        'line_number': line_number
                    }
                )
                return CommentResult(
                    success=False,
                    error="Line not in PR diff"
                )
            
            logger.error(
                f"Failed to post comment: {str(e)}",
                extra={
                    'pr_number': pr_number,
                    'file_path': file_path,
                    'error': str(e)
                }
            )
            
            return CommentResult(
                success=False,
                error=str(e)
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected error posting comment: {str(e)}",
                extra={
                    'pr_number': pr_number,
                    'file_path': file_path
                }
            )
            
            return CommentResult(
                success=False,
                error=str(e)
            )
    
    async def post_security_findings(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        findings: List[SecurityFinding]
    ) -> CommentBatchResult:
        """
        Post multiple security findings as review comments.
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            commit_sha: Commit SHA
            findings: List of security findings
            
        Returns:
            CommentBatchResult with posting statistics
        """
        start_time = time.time()
        results = []
        
        logger.info(
            f"Posting {len(findings)} security findings to PR #{pr_number}",
            extra={
                'pr_number': pr_number,
                'finding_count': len(findings)
            }
        )
        
        for i, finding in enumerate(findings):
            # Extract file path and line number from location
            file_path, line_number = self._parse_location(finding.location)
            
            if not file_path or line_number == 0:
                logger.warning(
                    f"Skipping finding with invalid location: {finding.location}"
                )
                results.append(CommentResult(
                    success=False,
                    error="Invalid location"
                ))
                continue
            
            # Format comment
            comment_body = self.format_security_finding(finding)
            
            # Post comment
            result = await self.post_comment(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                commit_sha=commit_sha,
                file_path=file_path,
                line_number=line_number,
                comment_body=comment_body
            )
            
            results.append(result)
            
            # Batch delay to avoid rate limits
            if (i + 1) % self.batch_size == 0 and i < len(findings) - 1:
                logger.debug(f"Batch delay: waiting {self.batch_delay}s")
                await asyncio.sleep(self.batch_delay)
        
        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = time.time() - start_time
        
        logger.info(
            f"Posted {successful}/{len(findings)} comments successfully in {total_time:.2f}s",
            extra={
                'pr_number': pr_number,
                'successful': successful,
                'failed': failed,
                'total_time': total_time,
                'rate_limit_hits': self.rate_limit_hits
            }
        )
        
        return CommentBatchResult(
            total_comments=len(findings),
            successful_comments=successful,
            failed_comments=failed,
            results=results,
            total_time=total_time,
            rate_limit_hits=self.rate_limit_hits
        )
    
    async def post_classified_findings(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        findings: List[ClassifiedFinding]
    ) -> CommentBatchResult:
        """
        Post multiple classified findings as review comments.
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            commit_sha: Commit SHA
            findings: List of classified findings
            
        Returns:
            CommentBatchResult with posting statistics
        """
        start_time = time.time()
        results = []
        
        logger.info(
            f"Posting {len(findings)} classified findings to PR #{pr_number}",
            extra={
                'pr_number': pr_number,
                'finding_count': len(findings)
            }
        )
        
        for i, finding in enumerate(findings):
            # Use file_path and line_number from finding
            if not finding.file_path or finding.line_number == 0:
                logger.warning(
                    f"Skipping finding with invalid location: {finding.file_path}:{finding.line_number}"
                )
                results.append(CommentResult(
                    success=False,
                    error="Invalid location"
                ))
                continue
            
            # Format comment
            comment_body = self.format_classified_finding(finding)
            
            # Post comment
            result = await self.post_comment(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                commit_sha=commit_sha,
                file_path=finding.file_path,
                line_number=finding.line_number,
                comment_body=comment_body
            )
            
            results.append(result)
            
            # Batch delay to avoid rate limits
            if (i + 1) % self.batch_size == 0 and i < len(findings) - 1:
                logger.debug(f"Batch delay: waiting {self.batch_delay}s")
                await asyncio.sleep(self.batch_delay)
        
        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = time.time() - start_time
        
        logger.info(
            f"Posted {successful}/{len(findings)} comments successfully in {total_time:.2f}s",
            extra={
                'pr_number': pr_number,
                'successful': successful,
                'failed': failed,
                'total_time': total_time,
                'rate_limit_hits': self.rate_limit_hits
            }
        )
        
        return CommentBatchResult(
            total_comments=len(findings),
            successful_comments=successful,
            failed_comments=failed,
            results=results,
            total_time=total_time,
            rate_limit_hits=self.rate_limit_hits
        )
    
    def _parse_location(self, location: str) -> tuple[str, int]:
        """
        Parse location string to extract file path and line number.
        
        Args:
            location: Location string (e.g., "file.py:42")
            
        Returns:
            Tuple of (file_path, line_number)
        """
        try:
            if ':' in location:
                parts = location.rsplit(':', 1)
                file_path = parts[0]
                line_number = int(parts[1])
                return file_path, line_number
        except (ValueError, IndexError):
            pass
        
        return "", 0
    
    async def post_summary_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        summary: Dict[str, Any]
    ) -> CommentResult:
        """
        Post a summary comment to the PR (not tied to a specific line).
        
        Args:
            repo_full_name: Repository full name
            pr_number: Pull request number
            summary: Summary data to format
            
        Returns:
            CommentResult
        """
        # Format summary comment
        comment_body = self._format_summary(summary)
        
        try:
            # Post as a general PR comment (not a review comment)
            repo = self.github_client.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            issue = pr.as_issue()
            comment = issue.create_comment(comment_body)
            
            logger.info(
                f"Posted summary comment to PR #{pr_number}",
                extra={
                    'comment_id': comment.id,
                    'pr_number': pr_number
                }
            )
            
            return CommentResult(
                success=True,
                comment_id=comment.id
            )
            
        except Exception as e:
            logger.error(
                f"Failed to post summary comment: {str(e)}",
                extra={'pr_number': pr_number}
            )
            
            return CommentResult(
                success=False,
                error=str(e)
            )
    
    def _format_summary(self, summary: Dict[str, Any]) -> str:
        """Format summary data as a GitHub comment"""
        lines = [
            f"## 🤖 AI Code Review Summary",
            f"",
            f"### 📊 Analysis Results",
            f"- **Total Issues:** {summary.get('total_issues', 0)}",
            f"- **Critical:** {summary.get('critical_issues', 0)}",
            f"- **High:** {summary.get('high_issues', 0)}",
            f"- **Medium:** {summary.get('medium_issues', 0)}",
            f"- **Low:** {summary.get('low_issues', 0)}",
            f""
        ]
        
        # Add OWASP coverage if available
        if 'owasp_coverage' in summary and summary['owasp_coverage']:
            lines.extend([
                f"### 🛡️ OWASP Top 10 Coverage",
                f"Found issues in {len(summary['owasp_coverage'])} OWASP categories:",
                f""
            ])
            for owasp_id, count in summary['owasp_coverage'].items():
                lines.append(f"- **{owasp_id}:** {count} issue(s)")
            lines.append(f"")
        
        # Add security score if available
        if 'security_score' in summary:
            score = summary['security_score']
            score_emoji = '🟢' if score >= 80 else '🟡' if score >= 60 else '🔴'
            lines.extend([
                f"### {score_emoji} Security Score",
                f"**{score:.1f}/100**",
                f""
            ])
        
        lines.extend([
            f"---",
            f"*Generated by AI Code Review Platform*"
        ])
        
        return "\n".join(lines)


# Singleton instance
_comment_generator_instance: Optional[GitHubCommentGenerator] = None


def get_comment_generator() -> GitHubCommentGenerator:
    """Get or create the singleton GitHubCommentGenerator instance"""
    global _comment_generator_instance
    if _comment_generator_instance is None:
        _comment_generator_instance = GitHubCommentGenerator()
    return _comment_generator_instance
